"""Camera configuration model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CameraConfig:
    """Camera configuration."""
    id: str
    name: str
    rtsp_url: str
    http_flv_url: Optional[str] = None
    width: int = 1920
    height: int = 1080
    fps: int = 30
    enabled: bool = True
    detectors: list = None  # List of detector names to use
    
    def __post_init__(self):
        if self.detectors is None:
            self.detectors = ["person", "vehicle", "motion"]
