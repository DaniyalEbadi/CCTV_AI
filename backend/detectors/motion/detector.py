"""
Motion Detection using background subtraction.
Lightweight detector that doesn't require ML models.
"""
import logging
import time
from typing import List
import numpy as np
import cv2

from backend.core import BaseDetector, Detection, DetectionResult

logger = logging.getLogger(__name__)


class MotionDetector(BaseDetector):
    """Detects motion in frames using background subtraction."""

    def __init__(
        self,
        confidence_threshold: float = 0.1,
        min_area: int = 500,
        blur_kernel: int = 5,
    ):
        super().__init__(
            name="motion_detector",
            enabled=True,
            confidence_threshold=confidence_threshold,
        )
        self.min_area = min_area
        self.blur_kernel = blur_kernel
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True
        )
        self.prev_frame = None

    def load_model(self) -> None:
        """Initialize motion detector (no model to load)."""
        logger.info("MotionDetector initialized (background subtraction)")

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Detect motion in frame using background subtraction."""
        start_time = time.time()

        if not self.enabled:
            return DetectionResult([], 0, frame.shape, self.name)

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (self.blur_kernel, self.blur_kernel), 0)

            # Apply background subtraction
            mask = self.background_subtractor.apply(blurred)

            # Dilate to close gaps
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.dilate(mask, kernel, iterations=2)

            # Find contours
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            detections: List[Detection] = []
            timestamp = time.time()

            for contour in contours:
                area = cv2.contourArea(contour)

                if area >= self.min_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    motion_ratio = area / (w * h) if w > 0 and h > 0 else 0
                    confidence = min(1.0, motion_ratio)

                    if confidence >= self.confidence_threshold:
                        detections.append(
                            Detection(
                                label="motion",
                                confidence=float(confidence),
                                x1=x,
                                y1=y,
                                x2=x + w,
                                y2=y + h,
                                timestamp=timestamp,
                                metadata={"area": int(area)},
                            )
                        )

            inference_time = (time.time() - start_time) * 1000
            return DetectionResult(detections, inference_time, frame.shape, self.name)

        except Exception as e:
            logger.exception(f"Motion detection error: {e}")
            return DetectionResult([], 0, frame.shape, self.name)

    def unload_model(self) -> None:
        """Release motion detector resources."""
        self.background_subtractor = None
        self.prev_frame = None
        logger.info("MotionDetector unloaded")
