"""
Video frame acquisition from RTSP/HTTP streams via FFmpeg.
Handles real-time frame buffering with latest-frame-wins strategy.
"""
import logging
import os
import shutil
import subprocess
import threading
import time
from collections import deque
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class FrameSource:
    """Acquires frames from video stream using FFmpeg."""

    def __init__(
        self,
        stream_url: str,
        width: int = 640,
        height: int = 360,
        fps: int = 5,
    ):
        """
        Args:
            stream_url: RTSP/HTTP stream URL
            width: Output frame width
            height: Output frame height
            fps: Target frames per second
        """
        self.stream_url = stream_url
        self.width = width
        self.height = height
        self.fps = fps
        self.proc = None
        self._running = False
        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._reader_thread = None
        self._stderr_thread = None
        self._stderr_lines = deque(maxlen=40)
        self.last_error: Optional[str] = None

    def start(self) -> None:
        """Start FFmpeg subprocess and reader thread."""
        if self._running:
            return
        with self._frame_lock:
            self._latest_frame = None

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            # Fallback to winget installation
            ffmpeg_path = os.path.expanduser(
                r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
            )
            if not os.path.exists(ffmpeg_path):
                raise RuntimeError("FFmpeg not found. Install with: winget install ffmpeg")

        cmd = [
            ffmpeg_path,
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-rtsp_transport", "tcp",
            "-i", self.stream_url,
            "-vf", f"fps={self.fps},scale={self.width}:{self.height},format=bgr24",
            "-c:v", "rawvideo",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-an", "-sn", "-dn",
            "pipe:1",
            "-hide_banner",
            "-loglevel", "warning",
        ]

        logger.info(f"Starting FFmpeg for {self.stream_url}")
        logger.debug(f"FFmpeg cmd: {' '.join(cmd)}")

        env = os.environ.copy()
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            env=env,
        )

        self._running = True
        self._stderr_thread = threading.Thread(target=self._stderr_loop, daemon=True)
        self._stderr_thread.start()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        logger.info(f"Frame source started | url={self.stream_url}")
        
        # Check if process exited immediately (connection error)
        time.sleep(0.2)
        if self.proc.poll() is not None:
            self.last_error = self._build_process_error("FFmpeg initialization failed")
            logger.error(self.last_error)
            self._running = False
            raise RuntimeError(self.last_error)


    def _reader_loop(self) -> None:
        """Background thread: reads frames from FFmpeg stdout."""
        try:
            # Check for FFmpeg errors on startup
            time.sleep(1)
            if self.proc.poll() is not None:
                # Process already exited
                self.last_error = self._build_process_error("FFmpeg process exited before first frame")
                logger.error(self.last_error)
                self._running = False
                return

            logger.info(f"Frame reader loop starting | fps={self.fps}, {self.width}x{self.height}")
            frame_size = self.width * self.height * 3  # BGR
            frame_count = 0
            
            while self._running:
                frame_data = self._read_exact(frame_size)
                
                if len(frame_data) == 0:
                    # Small wait helps capture exit code/stderr from just-finished process.
                    if self.proc.poll() is None:
                        time.sleep(0.1)
                    if self.proc.poll() is not None:
                        self.last_error = self._build_process_error("FFmpeg stdout closed")
                    else:
                        self.last_error = "FFmpeg stdout closed (0 bytes read)"
                    logger.warning(self.last_error)
                    break
                    
                if len(frame_data) != frame_size:
                    self.last_error = f"Incomplete frame before EOF: got {len(frame_data)} of {frame_size} bytes"
                    logger.warning(self.last_error)
                    break

                frame = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                    self.height, self.width, 3
                )
                frame_count += 1
                self.last_error = None
                
                if frame_count == 1:
                    logger.info(f"First frame received! {self.width}x{self.height}")
                elif frame_count % 10 == 0:
                    logger.debug(f"Frame {frame_count} received")

                with self._frame_lock:
                    # Latest-frame-wins buffer; supports multiple consumers.
                    self._latest_frame = frame

        except Exception as e:
            self.last_error = str(e)
            logger.exception(f"Frame reader error: {e}")
        finally:
            self._running = False
            if self.proc and self.proc.poll() is not None and not self.last_error:
                self.last_error = self._build_process_error("FFmpeg exited")
            logger.info(f"Frame reader stopped | {frame_count if 'frame_count' in locals() else 0} frames captured")

    def _read_exact(self, size: int) -> bytes:
        """Read exactly `size` bytes from stdout unless EOF/stop occurs."""
        if not self.proc or not self.proc.stdout:
            return b""

        chunks = bytearray()
        while self._running and len(chunks) < size:
            part = self.proc.stdout.read(size - len(chunks))
            if not part:
                break
            chunks.extend(part)
        return bytes(chunks)

    def _stderr_loop(self) -> None:
        """Drain FFmpeg stderr to avoid pipe backpressure and keep recent errors."""
        if not self.proc or not self.proc.stderr:
            return

        try:
            while True:
                line = self.proc.stderr.readline()
                if not line:
                    if self.proc.poll() is not None:
                        break
                    if not self._running:
                        break
                    continue

                text = line.decode("utf-8", errors="ignore").strip()
                if not text:
                    continue
                self._stderr_lines.append(text)
                logger.debug(f"FFmpeg stderr: {text}")
        except Exception as e:
            logger.debug(f"FFmpeg stderr reader stopped: {e}")

    def _build_process_error(self, prefix: str) -> str:
        """Build a compact error message with process code and stderr tail."""
        code = self.proc.returncode if self.proc else None
        tail = " | ".join(self._stderr_lines)
        if tail:
            if code is None:
                return f"{prefix}: {tail}"
            return f"{prefix} (code={code}): {tail}"
        if code is None:
            return prefix
        return f"{prefix} (code={code})"

    def get_frame(self) -> Optional[np.ndarray]:
        """Get latest frame (non-blocking)."""
        with self._frame_lock:
            return self._latest_frame

    def stop(self) -> None:
        """Stop FFmpeg and reader thread."""
        self._running = False
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1)
        if self._stderr_thread and self._stderr_thread.is_alive():
            self._stderr_thread.join(timeout=1)
        with self._frame_lock:
            self._latest_frame = None
        logger.info(f"Frame source stopped | url={self.stream_url}")
