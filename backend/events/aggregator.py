import time
from typing import Dict, List, Optional, Tuple

from ..models import Detection, Event


def iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    xa = max(x1, x2)
    ya = max(y1, y2)
    xb = min(x1 + w1, x2 + w2)
    yb = min(y1 + h1, y2 + h2)
    inter = max(0, xb - xa) * max(0, yb - ya)
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union else 0.0


class EventAggregator:
    def __init__(self, debounce_seconds: float = 2.0, iou_threshold: float = 0.5):
        self.debounce_seconds = debounce_seconds
        self.iou_threshold = iou_threshold
        self._last: Dict[str, Dict[str, Tuple[float, Tuple[int, int, int, int]]]] = {}

    def ingest(
        self, camera_id: str, detections: List[Detection], ts: float
    ) -> List[Event]:
        emitted: List[Event] = []
        camera_map = self._last.setdefault(camera_id, {})
        for d in detections:
            prev = camera_map.get(d.label)
            if prev:
                prev_ts, prev_box = prev
                if ts - prev_ts < self.debounce_seconds and iou(prev_box, d.bounding_box) > self.iou_threshold:
                    continue
            camera_map[d.label] = (ts, d.bounding_box)
            emitted.append(
                Event(
                    camera_id=camera_id,
                    timestamp=ts,
                    label=d.label,
                    bounding_box=d.bounding_box,
                    confidence=d.confidence,
                )
            )
        return emitted

