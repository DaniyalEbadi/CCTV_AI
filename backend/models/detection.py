"""Detection result models."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np


class DetectionType(str, Enum):
    """Supported detection types."""
    PERSON = "person"
    CAR = "car"
    TRUCK = "truck"
    BUS = "bus"
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    FACE = "face"
    LICENSE_PLATE = "license_plate"
    MOTION = "motion"
    CUSTOM = "custom"


@dataclass
class BoundingBox:
    """Bounding box coordinates and dimensions."""
    x1: float
    y1: float
    x2: float
    y2: float
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1
    
    @property
    def center(self) -> tuple:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    def iou(self, other: "BoundingBox") -> float:
        """Calculate Intersection over Union with another box."""
        x1_inter = max(self.x1, other.x1)
        y1_inter = max(self.y1, other.y1)
        x2_inter = min(self.x2, other.x2)
        y2_inter = min(self.y2, other.y2)
        
        if x2_inter < x1_inter or y2_inter < y1_inter:
            return 0.0
        
        inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        union_area = self.area + other.area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0


@dataclass
class Detection:
    """Single detection result."""
    type: DetectionType
    confidence: float
    bbox: BoundingBox
    timestamp: float
    detector_name: str
    metadata: dict = None  # Custom data per detector
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "confidence": round(self.confidence, 3),
            "bbox": {
                "x1": round(self.bbox.x1, 2),
                "y1": round(self.bbox.y1, 2),
                "x2": round(self.bbox.x2, 2),
                "y2": round(self.bbox.y2, 2),
            },
            "timestamp": self.timestamp,
            "detector": self.detector_name,
            "metadata": self.metadata,
        }
