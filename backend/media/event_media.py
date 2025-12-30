import os
import subprocess
from typing import Optional

import numpy as np

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None


def save_snapshot(frame_bgr: np.ndarray, path: str) -> Optional[str]:
    if cv2 is None:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, frame_bgr)
    return path


def save_event_clip(rtsp_url: str, out_path: str, seconds: int = 15) -> Optional[str]:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-rtsp_transport",
        "tcp",
        "-i",
        rtsp_url,
        "-t",
        str(seconds),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True)
        return out_path
    except Exception:
        return None

