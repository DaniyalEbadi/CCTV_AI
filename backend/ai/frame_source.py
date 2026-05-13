"""
Frame source abstraction layer for low-latency frame acquisition.

Design:
- FFmpeg subprocess → background thread → bounded queue (maxsize=1)
- Latest-frame-wins backpressure strategy
- Non-blocking async interface
"""
import asyncio
import logging
import os
import shutil
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from queue import Queue, Empty
from typing import Optional

import numpy as np

from .exceptions import FrameSourceError
from .frame import Frame

logger = logging.getLogger("ai.frame_source")


class FrameSource(ABC):
    """Abstract base for frame sources."""

    @abstractmethod
    def start(self) -> None:
        """Start frame acquisition."""
        pass

    @abstractmethod
    async def get_frame(self) -> Optional[np.ndarray]:
        """Get next frame (non-blocking, async-safe)."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop frame acquisition and cleanup."""
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if source is actively providing frames."""
        pass


class FFmpegRawVideoSource(FrameSource):
    """
    Low-latency frame source using FFmpeg rawvideo output.
    
    Eliminates MJPEG boundary parsing overhead and double-decoding.
    Uses FFmpeg low-latency flags for minimal delay.
    """

    def __init__(
        self,
        stream_url: str,
        width: int = 640,
        height: int = 360,
        fps: int = 10,
    ):
        """
        Args:
            stream_url: RTSP URL or camera ID
            width, height: Output frame dimensions
            fps: Target frames per second
        """
        self.stream_url = stream_url
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_size = width * height * 3  # BGR24

        self.proc: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._frame_queue: Queue = Queue(maxsize=1)
        self._running = False
        self._sequence_number = 0
        self._dropped_count = 0

        logger.info(
            "FFmpegRawVideoSource initialized | url=%s res=%sx%s fps=%s",
            stream_url,
            width,
            height,
            fps,
        )

    def start(self) -> None:
        """Start FFmpeg subprocess and reader thread."""
        if self._running:
            logger.warning("Source already running")
            return

        try:
            self._start_ffmpeg()
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                daemon=True,
                name="FFmpegReader",
            )
            self._reader_thread.start()
            logger.info("Frame source started")
        except Exception as e:
            logger.exception("Failed to start frame source")
            self.stop()
            raise FrameSourceError(f"Failed to start frame source: {e}") from e

    def _start_ffmpeg(self) -> None:
        """Spawn FFmpeg subprocess with low-latency optimizations."""
        # Find ffmpeg executable - try multiple locations
        ffmpeg_path = shutil.which("ffmpeg")
        
        # Fallback to winget installation location
        if not ffmpeg_path:
            winget_path = os.path.expanduser(
                r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
            )
            if os.path.exists(winget_path):
                ffmpeg_path = winget_path
        
        if not ffmpeg_path:
            raise RuntimeError(
                "ffmpeg not found. Install via: winget install ffmpeg"
            )
        
        cmd = [
            ffmpeg_path,
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-rtsp_transport", "tcp",
            "-i", self.stream_url,
            "-vf", f"fps={self.fps},scale={self.width}:{self.height},format=bgr24",
            "-reorder_queue_size", "0",
            "-max_delay", "0",
            "-c:v", "rawvideo",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-an", "-sn", "-dn",
            "pipe:1",
            "-hide_banner",
            "-loglevel", "error",
        ]

        logger.debug("Starting FFmpeg: %s", " ".join(cmd))

        # Prepare environment with proper PATH
        env = os.environ.copy()

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
            env=env,
        )

        if self.proc.poll() is not None:
            raise RuntimeError("FFmpeg process failed to start")

        logger.info("FFmpeg subprocess started | pid=%s", self.proc.pid)

    def _reader_loop(self) -> None:
        """Background thread: reads frames from FFmpeg stdout."""
        try:
            while self._running and self.proc and self.proc.poll() is None:
                ts_start = time.time()
                frame_data = self.proc.stdout.read(self.frame_size)

                if len(frame_data) != self.frame_size:
                    logger.warning("Incomplete frame: got %d bytes", len(frame_data))
                    break

                ts_decoded = time.time()
                
                # Convert to numpy
                arr = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                    (self.height, self.width, 3)
                )

                # Create frame with metadata
                frame = Frame(
                    data=arr.copy(),
                    sequence_number=self._sequence_number,
                    timestamp_acquired=ts_start,
                    timestamp_decoded=ts_decoded,
                    source_id=self.stream_url,
                )
                self._sequence_number += 1

                # Latest-frame-wins: drop old frame if queue full
                try:
                    self._frame_queue.put_nowait(frame)
                except Exception:
                    # Queue full, drop old frame
                    try:
                        old_frame = self._frame_queue.get_nowait()
                        self._dropped_count += 1
                        logger.debug(
                            "Dropped frame | seq=%d age_ms=%.1f",
                            old_frame.sequence_number,
                            old_frame.age_ms,
                        )
                        self._frame_queue.put_nowait(frame)
                    except Exception:
                        pass

        except Exception as e:
            logger.exception("Reader thread error: %s", e)
        finally:
            logger.info("Reader thread exiting | dropped=%d", self._dropped_count)

    async def get_frame(self) -> Optional[Frame]:
        """Get most recent frame from queue (non-blocking)."""
        try:
            frame = self._frame_queue.get_nowait()
            
            # Warn if frame is too old
            if frame.is_stale(max_age_ms=200):
                logger.warning(
                    "Stale frame detected | age_ms=%.1f seq=%d",
                    frame.age_ms,
                    frame.sequence_number,
                )
            
            return frame
        except Empty:
            return None
        except Exception as e:
            logger.exception("Error getting frame: %s", e)
            return None
    
    def get_metrics(self) -> dict:
        """Get frame source metrics."""
        return {
            "dropped_frames": self._dropped_count,
            "sequence_number": self._sequence_number,
            "queue_size": self._frame_queue.qsize(),
        }

    def stop(self) -> None:
        """Gracefully stop FFmpeg and reader thread."""
        self._running = False

        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            finally:
                self.proc = None

        if self._reader_thread:
            try:
                self._reader_thread.join(timeout=1)
            except Exception:
                pass
            finally:
                self._reader_thread = None

        logger.info("Frame source stopped")

    @property
    def is_running(self) -> bool:
        """Check if source is actively providing frames."""
        return (
            self._running
            and self.proc
            and self.proc.poll() is None
            and self._reader_thread
            and self._reader_thread.is_alive()
        )
