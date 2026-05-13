"""Core detection infrastructure."""
from .base_detector import BaseDetector, Detection, DetectionResult
from .frame_source import FrameSource

__all__ = [
    "BaseDetector",
    "Detection",
    "DetectionResult",
    "FrameSource",
]
