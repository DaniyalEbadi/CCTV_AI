"""Detectors module - collection of AI detection models."""

from .base import BaseDetector
from .person import PersonDetector
from .vehicle import VehicleDetector
from .motion import MotionDetector
from .face import FaceDetector

__all__ = [
    "BaseDetector",
    "PersonDetector",
    "VehicleDetector",
    "MotionDetector",
    "FaceDetector",
]
