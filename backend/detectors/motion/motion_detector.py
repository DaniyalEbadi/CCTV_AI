"""Motion detection using frame differencing."""

import logging
import time
import cv2
import numpy as np
from typing import List

from ..models import Detection, DetectionType, BoundingBox, Frame
from .base import BaseDetector

logger = logging.getLogger(__name__)


class MotionDetector(BaseDetector):
    """Detects motion using frame differencing (background subtraction)."""
    
    def __init__(
        self,
        threshold: int = 30,
        min_area: int = 500,
        blur_kernel: int = 21,
    ):
        super().__init__("motion_detector")
        self.threshold = threshold
        self.min_area = min_area
        self.blur_kernel = blur_kernel
        self.background_subtractor = None
        self.prev_frame = None
    
    def initialize(self) -> None:
        """Initialize motion detector."""
        try:
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                detectShadows=True
            )
            logger.info("MotionDetector initialized")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize MotionDetector: {e}")
            self.enabled = False
    
    def detect(self, frame: Frame) -> List[Detection]:
        """Detect motion in frame."""
        if not self.enabled or not frame.is_valid():
            return []
        
        try:
            ts = time.time()
            detections = []
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame.data, cv2.COLOR_BGR2GRAY)
            gray = cv2.blur(gray, (self.blur_kernel, self.blur_kernel))
            
            # Apply background subtraction
            fg_mask = self.background_subtractor.apply(gray)
            
            # Threshold
            _, thresh = cv2.threshold(fg_mask, self.threshold, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Filter by minimum area
                if area < self.min_area:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                
                bbox = BoundingBox(
                    x1=float(x),
                    y1=float(y),
                    x2=float(x + w),
                    y2=float(y + h),
                )
                
                det = Detection(
                    type=DetectionType.MOTION,
                    confidence=min(1.0, area / 10000),  # Normalize by area
                    bbox=bbox,
                    timestamp=ts,
                    detector_name=self.detector_name,
                    metadata={"area": int(area)},
                )
                detections.append(det)
            
            return detections
        
        except Exception as e:
            logger.exception(f"MotionDetector error: {e}")
            return []
