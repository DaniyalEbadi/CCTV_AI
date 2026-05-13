"""
License Plate Detection and Recognition using YOLOv8 and EasyOCR.
Detects and recognizes license plates in video frames.
"""
import logging
import time
from typing import List
import numpy as np
from ultralytics import YOLO

from backend.core import BaseDetector, Detection, DetectionResult

logger = logging.getLogger(__name__)


class LicensePlateDetector(BaseDetector):
    """Detects and recognizes license plates using YOLOv8 and EasyOCR."""

    def __init__(self, confidence_threshold: float = 0.5, device: str = "cpu"):
        super().__init__(
            name="license_plate_detector",
            enabled=True,
            confidence_threshold=confidence_threshold,
        )
        self.device = device
        self.model = None
        self.reader = None
        self._import_easyocr()

    def _import_easyocr(self):
        """Lazy import EasyOCR to avoid hard dependency."""
        try:
            import easyocr

            self._easyocr_module = easyocr
        except ImportError:
            logger.warning(
                "EasyOCR not installed. Install with: pip install easyocr"
            )
            self._easyocr_module = None

    def load_model(self) -> None:
        """Load YOLOv8 model for license plate detection."""
        try:
            # Using standard YOLOv8 for now; ideally use specialized license plate model
            self.model = YOLO("yolov8n.pt")

            # Initialize EasyOCR reader if available
            if self._easyocr_module:
                try:
                    self.reader = self._easyocr_module.Reader(
                        ["en"], gpu=(self.device != "cpu")
                    )
                    logger.info(
                        "LicensePlateDetector loaded with OCR on device: cpu"
                    )
                except Exception as e:
                    logger.warning(f"Failed to load OCR reader: {e}")
                    self.reader = None
            else:
                logger.info("LicensePlateDetector loaded (OCR not available)")

        except Exception as e:
            logger.error(f"Failed to load license plate detector: {e}")
            raise

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Detect license plates in frame."""
        start_time = time.time()

        if not self.enabled or self.model is None:
            return DetectionResult([], 0, frame.shape, self.name)

        try:
            frame_rgb = frame[:, :, ::-1]

            # YOLOv8 detection
            results = self.model.predict(
                source=frame_rgb,
                conf=self.confidence_threshold,
                device=self.device if self.device == "cpu" else 0,
                verbose=False,
            )[0]

            detections: List[Detection] = []
            timestamp = time.time()

            for box in results.boxes.data.tolist():
                x1, y1, x2, y2, confidence, class_id = box

                # For now, detect all boxes and label as license_plate
                # In production, use specialized license plate detection model
                plate_text = "unknown"

                # If OCR available, try to recognize text
                if self.reader:
                    try:
                        crop = frame[int(y1) : int(y2), int(x1) : int(x2)]
                        if crop.size > 0:
                            ocr_results = self.reader.readtext(crop)
                            if ocr_results:
                                plate_text = " ".join(
                                    [text[1] for text in ocr_results]
                                )
                    except Exception as e:
                        logger.debug(f"OCR error: {e}")

                detections.append(
                    Detection(
                        label="license_plate",
                        confidence=float(confidence),
                        x1=int(x1),
                        y1=int(y1),
                        x2=int(x2),
                        y2=int(y2),
                        timestamp=timestamp,
                        metadata={"plate_text": plate_text},
                    )
                )

            inference_time = (time.time() - start_time) * 1000
            return DetectionResult(detections, inference_time, frame.shape, self.name)

        except Exception as e:
            logger.exception(f"License plate detection error: {e}")
            return DetectionResult([], 0, frame.shape, self.name)

    def unload_model(self) -> None:
        """Release model resources."""
        if self.model:
            del self.model
            self.model = None
        if self.reader:
            del self.reader
            self.reader = None
        logger.info("LicensePlateDetector unloaded")
