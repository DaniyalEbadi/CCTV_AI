"""Frame model for video processing."""

from dataclasses import dataclass
import time
import numpy as np


@dataclass
class Frame:
    """Video frame container."""
    data: np.ndarray  # BGR format
    timestamp: float
    frame_id: int
    camera_id: str
    width: int
    height: int
    
    @property
    def age_ms(self) -> float:
        """Age of frame in milliseconds."""
        return (time.time() - self.timestamp) * 1000
    
    @property
    def shape(self) -> tuple:
        """Frame shape (H, W, C)."""
        return self.data.shape
    
    def is_valid(self) -> bool:
        """Check if frame is valid for processing."""
        return (
            self.data is not None
            and self.data.size > 0
            and len(self.data.shape) == 3
            and self.data.shape[2] == 3  # BGR
        )
