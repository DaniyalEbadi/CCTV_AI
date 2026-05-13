"""Stub detectors for face and license plate detection."""

import logging
from typing import List
from ..models import Detection, Frame
from .base import BaseDetector

logger = logging.getLogger(__name__)


class FaceDetector(BaseDetector):
    """Face detection (stub - implement with face_recognition or dlib)."""
    
    def __init__(self):
        super().__init__("face_detector")
        self.enabled = False  # Disabled by default
    
    def initialize(self) -> None:
        """Initialize face detector."""
        logger.warning("FaceDetector not implemented - use face_recognition library")
        self._initialized = True
    
    def detect(self, frame: Frame) -> List[Detection]:
        """Detect faces in frame."""
        return []  # Not implemented


class LicensePlateDetector(BaseDetector):
    """License plate detection (stub - implement with specialized model)."""
    
    def __init__(self):
        super().__init__("license_plate_detector")
        self.enabled = False  # Disabled by default
    
    def initialize(self) -> None:
        """Initialize license plate detector."""
        logger.warning("LicensePlateDetector not implemented")
        self._initialized = True
    
    def detect(self, frame: Frame) -> List[Detection]:
        """Detect license plates in frame."""
        return []  # Not implemented
