"""Base detector class and utilities."""

import logging
from abc import ABC, abstractmethod
from typing import List
import numpy as np
from ..models import Detection, Frame

logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """Abstract base class for all detectors."""
    
    def __init__(self, detector_name: str, enabled: bool = True):
        """
        Initialize detector.
        
        Args:
            detector_name: Unique identifier for this detector
            enabled: Whether detector is active
        """
        self.detector_name = detector_name
        self.enabled = enabled
        self._initialized = False
        logger.info(f"Initializing {detector_name}")
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize detector resources (models, weights, etc.).
        Called once at startup, not in __init__.
        """
        pass
    
    @abstractmethod
    def detect(self, frame: Frame) -> List[Detection]:
        """
        Run detection on frame.
        
        Args:
            frame: Input video frame
            
        Returns:
            List of detections
        """
        pass
    
    def health_check(self) -> dict:
        """Return health status of detector."""
        return {
            "name": self.detector_name,
            "enabled": self.enabled,
            "initialized": self._initialized,
        }
    
    def cleanup(self) -> None:
        """Cleanup resources (optional)."""
        pass
    
    def __repr__(self) -> str:
        status = "✓" if self.enabled else "✗"
        return f"{status} {self.detector_name}"
