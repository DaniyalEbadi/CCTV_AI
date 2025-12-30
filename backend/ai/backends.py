import os
from typing import List, Tuple

import numpy as np

from ..models import Detection

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None


class BaseBackend:
    def process(self, frame_bgr: np.ndarray) -> List[Detection]:
        return []


class MotionBackendCPU(BaseBackend):
    def __init__(self, min_area: int = 500):
        self.min_area = min_area
        self.bg = cv2.createBackgroundSubtractorMOG2() if cv2 else None

    def process(self, frame_bgr: np.ndarray) -> List[Detection]:
        if cv2 is None or self.bg is None:
            return []
        fg = self.bg.apply(frame_bgr)
        fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)[1]
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dets: List[Detection] = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w * h < self.min_area:
                continue
            dets.append(
                Detection(
                    label="motion",
                    bounding_box=(x, y, w, h),
                    confidence=0.5,
                )
            )
        return dets


def select_backend(preference: str = "auto") -> BaseBackend:
    if preference == "cpu":
        return MotionBackendCPU()
    if preference == "gpu":
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                return MotionBackendCPU()
        except Exception:
            pass
        return MotionBackendCPU()
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            return MotionBackendCPU()
    except Exception:
        pass
    return MotionBackendCPU()

