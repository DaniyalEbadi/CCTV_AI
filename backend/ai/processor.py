import asyncio
import os
import shlex
import subprocess
import time
from typing import Callable, List, Optional, Tuple

import numpy as np

from ..models import Camera, Detection
from .backends import BaseBackend, select_backend


class FFmpegReader:
    def __init__(self, rtsp_url: str, fps: int, width: int, height: int) -> None:
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.width = width
        self.height = height
        self.proc: Optional[subprocess.Popen] = None
        self.frame_size = self.width * self.height * 3

    def start(self) -> None:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-i",
            self.rtsp_url,
            "-vf",
            f"fps={self.fps},scale={self.width}:{self.height}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-",
        ]
        self.proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=self.frame_size
        )

    def read(self) -> Optional[np.ndarray]:
        if not self.proc or not self.proc.stdout:
            return None
        data = self.proc.stdout.read(self.frame_size)
        if not data or len(data) != self.frame_size:
            return None
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = arr.reshape((self.height, self.width, 3))
        return frame

    def stop(self) -> None:
        if self.proc:
            try:
                self.proc.kill()
            except Exception:
                pass
            self.proc = None


class AIProcessor:
    def __init__(
        self,
        camera: Camera,
        fps: int = 5,
        resolution: str = "640x360",
        backend_pref: str = "auto",
        on_detections: Optional[Callable[[List[Detection], float, np.ndarray], None]] = None,
    ) -> None:
        self.camera = camera
        w, h = [int(x) for x in resolution.split("x")]
        self.reader = FFmpegReader(camera.rtsp_url, fps=fps, width=w, height=h)
        self.backend: BaseBackend = select_backend(backend_pref)
        self.on_detections = on_detections
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def run(self) -> None:
        self._running = True
        self.reader.start()
        try:
            while self._running:
                frame = self.reader.read()
                if frame is None:
                    await asyncio.sleep(0.05)
                    continue
                ts = time.time()
                dets = self.backend.process(frame)
                if self.on_detections:
                    try:
                        self.on_detections(dets, ts, frame)
                    except Exception:
                        pass
        finally:
            self.reader.stop()
            self._running = False

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._task = loop.create_task(self.run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=2)
            except Exception:
                pass

