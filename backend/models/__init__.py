"""Data models and schemas for detection results."""

from .detection import Detection, DetectionType, BoundingBox
from .frame import Frame
from .camera import CameraConfig

__all__ = [
    "Detection",
    "DetectionType",
    "BoundingBox",
    "Frame",
    "CameraConfig",
]
