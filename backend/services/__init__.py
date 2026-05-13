"""Backend services module."""
from .detection_pipeline import DetectionPipeline
from .camera_manager import CameraManager

__all__ = ["DetectionPipeline", "CameraManager"]
