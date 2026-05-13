"""YOLOv8 object detection backend (CPU and GPU variants)."""
import logging
from typing import List, Literal

import numpy as np

from ...models import Detection
from .base import BaseBackend

logger = logging.getLogger("ai.backends.yolov8")

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    import torch
except ImportError:
    torch = None


class YOLOv8Backend(BaseBackend):
    """
    YOLOv8 object detection backend.
    
    Supports both CPU and GPU inference (auto-detected).
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.5,
        device: Literal["auto", "cpu", "gpu"] = "auto",
    ):
        """
        Args:
            model_path: Path to YOLO model file
            conf_threshold: Confidence threshold for detections
            device: "auto", "cpu", or "gpu"
        """
        if YOLO is None:
            raise RuntimeError(
                "ultralytics required for YOLO backend. "
                "Install with: pip install ultralytics"
            )

        self.conf_threshold = conf_threshold
        self.device = self._resolve_device(device)
        self.model = YOLO(model_path)

        logger.info(
            "YOLOv8Backend initialized | model=%s device=%s conf=%s",
            model_path,
            self.device,
            conf_threshold,
        )

    @staticmethod
    def _resolve_device(device: str) -> str:
        """Resolve device: auto → cpu/gpu based on availability."""
        if device != "auto":
            return device

        if torch and torch.cuda.is_available():
            logger.info("CUDA available, using GPU")
            return "gpu"

        return "cpu"

    @property
    def is_available(self) -> bool:
        return YOLO is not None

    @property
    def name(self) -> str:
        return f"yolov8_{self.device}"

    def process(self, frame_bgr: np.ndarray) -> List[Detection]:
        """Run YOLO inference on frame."""
        try:
            # Ensure frame is uint8 (YOLOv8 requirement)
            if frame_bgr.dtype != np.uint8:
                frame_bgr = np.clip(frame_bgr, 0, 255).astype(np.uint8)
            
            device_arg = 0 if self.device == "gpu" else "cpu"

            # YOLOv8 expects BGR/RGB, convert to RGB for inference
            frame_rgb = frame_bgr[:, :, ::-1]  # BGR to RGB

            results = self.model.predict(
                source=frame_rgb,
                conf=self.conf_threshold,
                device=device_arg,
                verbose=False,
            )[0]

            dets: List[Detection] = []

            for box in results.boxes.data.tolist():
                x1, y1, x2, y2, score, cls_id = box

                # COCO dataset: class 0 = person
                if int(cls_id) != 0:
                    continue

                dets.append(
                    Detection(
                        label="person",
                        bounding_box=(
                            int(x1),
                            int(y1),
                            int(x2 - x1),
                            int(y2 - y1),
                        ),
                        confidence=float(score),
                    )
                )

            return dets

        except Exception as e:
            logger.exception("YOLO inference error")
            return []


# Convenience aliases
YOLOv8CPUBackend = YOLOv8Backend
YOLOv8GPUBackend = YOLOv8Backend
