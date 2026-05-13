"""Vehicle detection using YOLOv8."""

import logging
import time
from typing import List

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from ..models import Detection, DetectionType, BoundingBox, Frame
from .base import BaseDetector

logger = logging.getLogger(__name__)


class VehicleDetector(BaseDetector):
    """Detects vehicles (cars, trucks, buses) using YOLOv8."""
    
    # COCO class IDs
    VEHICLE_CLASSES = {
        2: DetectionType.CAR,
        5: DetectionType.BUS,
        7: DetectionType.TRUCK,
        3: DetectionType.MOTORCYCLE,
        1: DetectionType.BICYCLE,
    }
    
    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = 0.5):
        super().__init__("vehicle_detector")
        self.model_name = model_name
        self.confidence_threshold = confidence
        self.model = None
        self.device = None
    
    def initialize(self) -> None:
        """Load YOLOv8 model."""
        if YOLO is None:
            logger.error("ultralytics not installed")
            self.enabled = False
            return
        
        try:
            self.model = YOLO(self.model_name)
            self.device = "0" if self._has_cuda() else "cpu"
            logger.info(f"VehicleDetector initialized on {self.device}")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize VehicleDetector: {e}")
            self.enabled = False
    
    def detect(self, frame: Frame) -> List[Detection]:
        """Detect vehicles in frame."""
        if not self.enabled or self.model is None or not frame.is_valid():
            return []
        
        try:
            ts = time.time()
            
            # Convert BGR to RGB
            frame_rgb = frame.data[:, :, ::-1]
            
            # Run inference
            results = self.model.predict(
                source=frame_rgb,
                conf=self.confidence_threshold,
                device=self.device,
                verbose=False,
            )[0]
            
            detections = []
            for box in results.boxes.data.tolist():
                x1, y1, x2, y2, score, cls_id = box
                cls_id = int(cls_id)
                
                # Only return vehicle detections
                if cls_id not in self.VEHICLE_CLASSES:
                    continue
                
                bbox = BoundingBox(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                )
                
                det = Detection(
                    type=self.VEHICLE_CLASSES[cls_id],
                    confidence=float(score),
                    bbox=bbox,
                    timestamp=ts,
                    detector_name=self.detector_name,
                    metadata={"model": self.model_name},
                )
                detections.append(det)
            
            return detections
        
        except Exception as e:
            logger.exception(f"VehicleDetector error: {e}")
            return []
    
    @staticmethod
    def _has_cuda() -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
