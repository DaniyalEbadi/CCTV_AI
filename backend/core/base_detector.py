"""
Base detector interface - all detectors inherit from this.
Follows dependency inversion principle.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class Detection:
    """Single detection result."""
    label: str  # e.g., "person", "car", "face"
    confidence: float  # 0.0-1.0
    x1: int  # bounding box top-left x
    y1: int  # bounding box top-left y
    x2: int  # bounding box bottom-right x
    y2: int  # bounding box bottom-right y
    timestamp: float  # Unix timestamp
    metadata: dict = None  # Extra info (e.g., license plate text)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DetectionResult:
    """Result from a detection run."""
    detections: List[Detection]
    inference_time_ms: float
    frame_shape: tuple  # (height, width, channels)
    detector_name: str


class BaseDetector(ABC):
    """Abstract base class for all detectors."""

    def __init__(self, name: str, enabled: bool = True, confidence_threshold: float = 0.5):
        """
        Args:
            name: Detector identifier (e.g., "person_detector", "vehicle_detector")
            enabled: Whether detector is active
            confidence_threshold: Minimum confidence to return detection
        """
        self.name = name
        self.enabled = enabled
        self.confidence_threshold = confidence_threshold

    @abstractmethod
    def load_model(self) -> None:
        """Load and initialize detector model."""
        pass

    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Run detection on frame.
        
        Args:
            frame: BGR numpy array (H, W, 3)
            
        Returns:
            DetectionResult with all detections
        """
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """Clean up and release resources."""
        pass

    def __enter__(self):
        """Context manager support."""
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.unload_model()
