import os
import subprocess
from typing import Dict, Optional

from ..models import Camera


class RecorderManager:
    def __init__(self, output_dir: str = "storage/recordings", segment_seconds: int = 300):
        self.output_dir = output_dir
        self.segment_seconds = segment_seconds
        self._procs: Dict[str, subprocess.Popen] = {}
        os.makedirs(self.output_dir, exist_ok=True)

    def start(self, camera: Camera) -> None:
        if camera.id in self._procs:
            return
        cam_dir = os.path.join(self.output_dir, camera.id)
        os.makedirs(cam_dir, exist_ok=True)
        outfile_pattern = os.path.join(cam_dir, "%Y%m%d_%H%M%S.mp4")
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-i",
            camera.rtsp_url,
            "-c",
            "copy",
            "-f",
            "segment",
            "-segment_time",
            str(self.segment_seconds),
            "-reset_timestamps",
            "1",
            outfile_pattern,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self._procs[camera.id] = proc

    def stop(self, camera_id: str) -> None:
        proc = self._procs.pop(camera_id, None)
        if proc:
            try:
                proc.kill()
            except Exception:
                pass

    def stop_all(self) -> None:
        for cam_id in list(self._procs.keys()):
            self.stop(cam_id)

