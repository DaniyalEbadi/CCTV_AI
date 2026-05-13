"""
Vehicle Detection using YOLOv8.
Detects cars, trucks, buses, motorcycles.
"""
import logging
import os
import time
from typing import List
import numpy as np
from ultralytics import YOLO

from backend.core import BaseDetector, Detection, DetectionResult

logger = logging.getLogger(__name__)

# COCO class IDs for vehicles
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


class VehicleDetector(BaseDetector):
    """Detects vehicles using YOLOv8."""

    def __init__(self, confidence_threshold: float = 0.35, device: str = "cpu"):
        super().__init__(
            name="vehicle_detector",
            enabled=True,
            confidence_threshold=confidence_threshold,
        )
        self.device = device
        self.model_name = os.getenv("YOLO_MODEL_WEIGHTS", "yolov8s.pt")
        self.imgsz = int(os.getenv("YOLO_IMGSZ", "640"))
        self.iou = float(os.getenv("YOLO_IOU", "0.45"))
        self.model = None

    def load_model(self) -> None:
        """Load YOLOv8 nano model."""
        try:
            self.model = YOLO(self.model_name)
            logger.info(
                "VehicleDetector loaded on %s | model=%s imgsz=%s iou=%s",
                self.device,
                self.model_name,
                self.imgsz,
                self.iou,
            )
        except Exception as e:
            logger.error(f"Failed to load vehicle detector: {e}")
            raise

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Detect vehicles in frame."""
        start_time = time.time()

        if not self.enabled or self.model is None:
            return DetectionResult([], 0, frame.shape, self.name)

        try:
            frame_rgb = frame[:, :, ::-1]

            results = self.model.predict(
                source=frame_rgb,
                conf=self.confidence_threshold,
                iou=self.iou,
                imgsz=self.imgsz,
                device=self.device if self.device == "cpu" else 0,
                verbose=False,
            )[0]

            detections: List[Detection] = []
            timestamp = time.time()

            for box in results.boxes.data.tolist():
                x1, y1, x2, y2, confidence, class_id = box
                class_id = int(class_id)

                if class_id in VEHICLE_CLASSES:
                    detections.append(
                        Detection(
                            label=VEHICLE_CLASSES[class_id],
                            confidence=float(confidence),
                            x1=int(x1),
                            y1=int(y1),
                            x2=int(x2),
                            y2=int(y2),
                            timestamp=timestamp,
                        )
                    )

            inference_time = (time.time() - start_time) * 1000
            return DetectionResult(detections, inference_time, frame.shape, self.name)

        except Exception as e:
            logger.exception(f"Vehicle detection error: {e}")
            return DetectionResult([], 0, frame.shape, self.name)

    def unload_model(self) -> None:
        """Release model resources."""
        if self.model:
            del self.model
            self.model = None
            logger.info("VehicleDetector unloaded")
