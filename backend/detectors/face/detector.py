"""
Face detection.
Default backend is OpenCV Haar cascade (CPU-friendly), with optional RetinaFace.
"""
import logging
import os
import threading
import time
from typing import List
import cv2
import numpy as np

from backend.core import BaseDetector, Detection, DetectionResult

logger = logging.getLogger(__name__)


class FaceDetector(BaseDetector):
    """Detects faces using OpenCV (default) or RetinaFace."""

    def __init__(self, confidence_threshold: float = 0.35, device: str = "cpu"):
        super().__init__(
            name="face_detector",
            enabled=True,
            confidence_threshold=confidence_threshold,
        )
        self.device = device
        self.detector = None
        # Default to OpenCV for real-time CPU usage; RetinaFace is optional and slower.
        self.backend = os.getenv("FACE_DETECTOR_BACKEND", "opencv").strip().lower()
        self.upscale_factor = float(os.getenv("FACE_UPSCALE_FACTOR", "1.5"))
        self.min_face_size = int(os.getenv("FACE_MIN_SIZE", "20"))
        self.max_faces = int(os.getenv("FACE_MAX_DETECTIONS", "30"))
        self.opencv_scale_factor = float(os.getenv("FACE_OPENCV_SCALE_FACTOR", "1.08"))
        self.opencv_min_neighbors = int(os.getenv("FACE_OPENCV_MIN_NEIGHBORS", "4"))
        self.opencv_profile_min_neighbors = int(
            os.getenv("FACE_OPENCV_PROFILE_MIN_NEIGHBORS", "3")
        )
        self.face_nms_iou = float(os.getenv("FACE_NMS_IOU", "0.35"))
        self.face_duplicate_overlap = float(os.getenv("FACE_DUPLICATE_OVERLAP", "0.85"))
        self.require_eyes = os.getenv("FACE_REQUIRE_EYES", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        )
        self.eye_scale_factor = float(os.getenv("FACE_EYE_SCALE_FACTOR", "1.10"))
        self.eye_min_neighbors = int(os.getenv("FACE_EYE_MIN_NEIGHBORS", "3"))
        self.retinaface_timeout_ms = float(os.getenv("FACE_RETINAFACE_TIMEOUT_MS", "1500"))
        self._retinaface_slow_warning_emitted = False
        self._retinaface_module = None
        self._cascade = None
        self._profile_cascade = None
        self._eye_cascade = None
        self._detect_lock = threading.Lock()
        if self.backend == "retinaface":
            self._import_retinaface()
        elif self.backend != "opencv":
            logger.warning(
                "Unknown FACE_DETECTOR_BACKEND=%s, falling back to opencv",
                self.backend,
            )
            self.backend = "opencv"

    def _import_retinaface(self):
        """Lazy import retinaface to avoid hard dependency."""
        try:
            from retinaface import RetinaFace

            self._retinaface_module = RetinaFace
        except ImportError:
            logger.warning(
                "RetinaFace not installed. Install with: pip install retina-face"
            )
            self._retinaface_module = None

    def load_model(self) -> None:
        """Load face detector backend."""
        try:
            if self.backend == "retinaface":
                if self._retinaface_module is None:
                    logger.warning(
                        "RetinaFace module not available. Falling back to OpenCV face detector."
                    )
                    self.backend = "opencv"
                else:
                    logger.info(
                        "FaceDetector model ready (backend=retinaface, upscale=%.2f, min_face=%d)",
                        self.upscale_factor,
                        self.min_face_size,
                    )
                    self._load_opencv_fallback_cascades(required=False)
                    return

            self._load_opencv_fallback_cascades(required=True)
            logger.info("FaceDetector model ready (backend=opencv_haar)")
        except Exception as e:
            logger.error(f"Failed to load face detector: {e}")
            raise

    def _load_opencv_fallback_cascades(self, required: bool) -> None:
        """Load OpenCV frontal/profile cascades for primary or fallback detection."""
        frontal_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(frontal_path)
        if self._cascade.empty():
            self._cascade = None
            if required:
                raise RuntimeError(f"Failed to load OpenCV frontal cascade: {frontal_path}")
            logger.warning("OpenCV frontal cascade unavailable: %s", frontal_path)

        profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
        self._profile_cascade = cv2.CascadeClassifier(profile_path)
        if self._profile_cascade.empty():
            self._profile_cascade = None
            logger.warning("OpenCV profile cascade unavailable: %s", profile_path)

        eye_path = cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
        self._eye_cascade = cv2.CascadeClassifier(eye_path)
        if self._eye_cascade.empty():
            self._eye_cascade = None
            logger.warning("OpenCV eye cascade unavailable: %s", eye_path)

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Detect faces in frame."""
        with self._detect_lock:
            start_time = time.time()

            if not self.enabled:
                return DetectionResult([], 0, frame.shape, self.name)

            if self.backend == "retinaface":
                return self._detect_with_retinaface(frame, start_time)
            return self._detect_with_opencv(frame, start_time)

    def _detect_with_retinaface(self, frame: np.ndarray, start_time: float) -> DetectionResult:
        """Detect faces using RetinaFace backend."""
        if self._retinaface_module is None:
            return DetectionResult([], 0, frame.shape, self.name)

        try:
            frame_rgb = frame[:, :, ::-1]

            # RetinaFace detection with lower threshold for better recall.
            faces = self._retinaface_module.detect_faces(
                frame_rgb,
                threshold=self.confidence_threshold,
            )
            scale = 1.0

            # Recovery pass for small/far faces: run on upscaled image.
            if (not isinstance(faces, dict) or len(faces) == 0) and self.upscale_factor > 1.0:
                up_w = max(1, int(frame_rgb.shape[1] * self.upscale_factor))
                up_h = max(1, int(frame_rgb.shape[0] * self.upscale_factor))
                upscaled = cv2.resize(frame_rgb, (up_w, up_h), interpolation=cv2.INTER_CUBIC)
                faces = self._retinaface_module.detect_faces(
                    upscaled,
                    threshold=max(0.2, self.confidence_threshold - 0.1),
                )
                scale = self.upscale_factor

            detections: List[Detection] = []
            timestamp = time.time()

            if isinstance(faces, dict):
                for face_id, face_data in faces.items():
                    facial_area = face_data.get("facial_area", [])
                    confidence = face_data.get("confidence", 0)

                    if len(facial_area) >= 4 and confidence >= self.confidence_threshold:
                        x1, y1, x2, y2 = facial_area[:4]
                        if scale != 1.0:
                            x1, y1, x2, y2 = (
                                int(x1 / scale),
                                int(y1 / scale),
                                int(x2 / scale),
                                int(y2 / scale),
                            )

                        width = max(0, int(x2) - int(x1))
                        height = max(0, int(y2) - int(y1))
                        if width < self.min_face_size or height < self.min_face_size:
                            continue

                        detections.append(
                            Detection(
                                label="face",
                                confidence=float(confidence),
                                x1=int(x1),
                                y1=int(y1),
                                x2=int(x2),
                                y2=int(y2),
                                timestamp=timestamp,
                                metadata={"backend": "retinaface"},
                            )
                        )
                        if len(detections) >= self.max_faces:
                            break

            if len(detections) == 0:
                detections = self._detect_with_opencv_fallback(frame, timestamp)
            else:
                detections = self._dedupe_detection_objects(detections)

            inference_time = (time.time() - start_time) * 1000
            if inference_time > self.retinaface_timeout_ms:
                if not self._retinaface_slow_warning_emitted:
                    logger.warning(
                        "RetinaFace is slow on this system (%.1fms). "
                        "Switching to OpenCV backend for real-time mode. "
                        "Set FACE_DETECTOR_BACKEND=retinaface to force it.",
                        inference_time,
                    )
                    self._retinaface_slow_warning_emitted = True
                self.backend = "opencv"
                if self._cascade is None and self._profile_cascade is None:
                    self._load_opencv_fallback_cascades(required=True)
            return DetectionResult(detections, inference_time, frame.shape, self.name)

        except Exception as e:
            logger.exception(f"Face detection error: {e}")
            return DetectionResult([], 0, frame.shape, self.name)

    def _detect_with_opencv(self, frame: np.ndarray, start_time: float) -> DetectionResult:
        """Detect faces using OpenCV Haar cascade backend (CPU-friendly)."""
        if self._cascade is None and self._profile_cascade is None:
            return DetectionResult([], 0, frame.shape, self.name)

        try:
            timestamp = time.time()
            detections = self._detect_with_opencv_fallback(frame, timestamp)
            detections = detections[: self.max_faces]
            inference_time = (time.time() - start_time) * 1000
            return DetectionResult(detections, inference_time, frame.shape, self.name)
        except Exception as e:
            logger.exception(f"Face detection (OpenCV) error: {e}")
            return DetectionResult([], 0, frame.shape, self.name)

    def _detect_with_opencv_fallback(self, frame: np.ndarray, timestamp: float) -> List[Detection]:
        """Fallback detector using frontal + profile Haar cascades (both directions)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        min_size = (self.min_face_size, self.min_face_size)
        frame_h, frame_w = gray.shape[:2]
        boxes: List[tuple[int, int, int, int, float]] = []

        if self._cascade is not None:
            try:
                frontal = self._cascade.detectMultiScale(
                    gray,
                    scaleFactor=self.opencv_scale_factor,
                    minNeighbors=self.opencv_min_neighbors,
                    minSize=min_size,
                )
                for (x, y, w, h) in frontal:
                    if not self._is_plausible_face_box(x, y, w, h, frame_w, frame_h):
                        continue
                    if not self._verify_face_roi(gray, x, y, w, h):
                        continue
                    boxes.append((int(x), int(y), int(w), int(h), 0.82))
            except cv2.error as e:
                logger.warning("OpenCV frontal cascade failed, disabling it: %s", e)
                self._cascade = None

        if self._profile_cascade is not None:
            try:
                profile_left = self._profile_cascade.detectMultiScale(
                    gray,
                    scaleFactor=self.opencv_scale_factor,
                    minNeighbors=self.opencv_profile_min_neighbors,
                    minSize=min_size,
                )
                for (x, y, w, h) in profile_left:
                    if not self._is_plausible_face_box(x, y, w, h, frame_w, frame_h):
                        continue
                    boxes.append((int(x), int(y), int(w), int(h), 0.72))

                # Detect right profiles by running profile detector on flipped frame.
                gray_flip = cv2.flip(gray, 1)
                profile_right_flip = self._profile_cascade.detectMultiScale(
                    gray_flip,
                    scaleFactor=self.opencv_scale_factor,
                    minNeighbors=self.opencv_profile_min_neighbors,
                    minSize=min_size,
                )
                width = gray.shape[1]
                for (x, y, w, h) in profile_right_flip:
                    x_orig = width - (x + w)
                    if not self._is_plausible_face_box(x_orig, y, w, h, frame_w, frame_h):
                        continue
                    boxes.append((int(x_orig), int(y), int(w), int(h), 0.72))
            except cv2.error as e:
                logger.warning("OpenCV profile cascade failed, disabling it: %s", e)
                self._profile_cascade = None

        if not boxes and self.upscale_factor > 1.0:
            up_w = max(1, int(gray.shape[1] * self.upscale_factor))
            up_h = max(1, int(gray.shape[0] * self.upscale_factor))
            gray_up = cv2.resize(gray, (up_w, up_h), interpolation=cv2.INTER_CUBIC)
            up_boxes: List[tuple[int, int, int, int, float]] = []

            if self._cascade is not None:
                try:
                    frontal_up = self._cascade.detectMultiScale(
                        gray_up,
                        scaleFactor=self.opencv_scale_factor,
                        minNeighbors=max(3, self.opencv_min_neighbors - 1),
                        minSize=(
                            int(self.min_face_size * self.upscale_factor),
                            int(self.min_face_size * self.upscale_factor),
                        ),
                    )
                    for (x, y, w, h) in frontal_up:
                        if not self._is_plausible_face_box(x, y, w, h, up_w, up_h):
                            continue
                        if not self._verify_face_roi(gray_up, x, y, w, h):
                            continue
                        up_boxes.append((int(x), int(y), int(w), int(h), 0.75))
                except cv2.error as e:
                    logger.warning("OpenCV frontal upscale pass failed: %s", e)

            if self._profile_cascade is not None:
                try:
                    profile_up = self._profile_cascade.detectMultiScale(
                        gray_up,
                        scaleFactor=self.opencv_scale_factor,
                        minNeighbors=max(3, self.opencv_min_neighbors - 1),
                        minSize=(
                            int(self.min_face_size * self.upscale_factor),
                            int(self.min_face_size * self.upscale_factor),
                        ),
                    )
                    for (x, y, w, h) in profile_up:
                        if not self._is_plausible_face_box(x, y, w, h, up_w, up_h):
                            continue
                        up_boxes.append((int(x), int(y), int(w), int(h), 0.68))
                except cv2.error as e:
                    logger.warning("OpenCV profile upscale pass failed: %s", e)

            scale = self.upscale_factor
            for (x, y, w, h, conf) in up_boxes:
                boxes.append((int(x / scale), int(y / scale), int(w / scale), int(h / scale), conf))

        boxes = self._dedupe_raw_boxes(boxes)
        # Keep strongest boxes first.
        boxes.sort(key=lambda b: (b[4], b[2] * b[3]), reverse=True)
        detections: List[Detection] = []
        for (x, y, w, h, conf) in boxes[: self.max_faces]:
            if w < self.min_face_size or h < self.min_face_size:
                continue
            detections.append(
                Detection(
                    label="face",
                    confidence=float(conf),
                    x1=int(x),
                    y1=int(y),
                    x2=int(x + w),
                    y2=int(y + h),
                    timestamp=timestamp,
                    metadata={"backend": "opencv_fallback"},
                )
            )
        return detections

    @staticmethod
    def _iou_xywh(a: tuple[int, int, int, int, float], b: tuple[int, int, int, int, float]) -> float:
        """Compute IoU for two xywh boxes."""
        ax1, ay1, aw, ah, _ = a
        bx1, by1, bw, bh, _ = b
        ax2, ay2 = ax1 + aw, ay1 + ah
        bx2, by2 = bx1 + bw, by1 + bh

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        if inter_area == 0:
            return 0.0

        area_a = aw * ah
        area_b = bw * bh
        union = max(1, area_a + area_b - inter_area)
        return inter_area / union

    @staticmethod
    def _overlap_ratio_xywh(a: tuple[int, int, int, int, float], b: tuple[int, int, int, int, float]) -> float:
        """Intersection area ratio against the smaller box."""
        ax1, ay1, aw, ah, _ = a
        bx1, by1, bw, bh, _ = b
        ax2, ay2 = ax1 + aw, ay1 + ah
        bx2, by2 = bx1 + bw, by1 + bh

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        if inter_area == 0:
            return 0.0
        area_a = max(1, aw * ah)
        area_b = max(1, bw * bh)
        return inter_area / min(area_a, area_b)

    def _dedupe_raw_boxes(self, boxes: List[tuple[int, int, int, int, float]]) -> List[tuple[int, int, int, int, float]]:
        """
        Non-maximum suppression + overlap dedupe for face candidates.
        Helps prevent one real face being counted many times.
        """
        if not boxes:
            return []

        candidates = sorted(boxes, key=lambda b: (b[4], b[2] * b[3]), reverse=True)
        kept: List[tuple[int, int, int, int, float]] = []
        for candidate in candidates:
            drop = False
            for existing in kept:
                if self._iou_xywh(candidate, existing) >= self.face_nms_iou:
                    drop = True
                    break
                if self._overlap_ratio_xywh(candidate, existing) >= self.face_duplicate_overlap:
                    drop = True
                    break
            if not drop:
                kept.append(candidate)
        return kept

    def _dedupe_detection_objects(self, detections: List[Detection]) -> List[Detection]:
        """Apply same dedupe logic to `Detection` objects (e.g., RetinaFace path)."""
        raw_boxes = [
            (
                int(d.x1),
                int(d.y1),
                max(0, int(d.x2) - int(d.x1)),
                max(0, int(d.y2) - int(d.y1)),
                float(d.confidence),
            )
            for d in detections
        ]
        deduped = self._dedupe_raw_boxes(raw_boxes)
        kept: List[Detection] = []
        for x, y, w, h, conf in deduped:
            kept.append(
                Detection(
                    label="face",
                    confidence=float(conf),
                    x1=int(x),
                    y1=int(y),
                    x2=int(x + w),
                    y2=int(y + h),
                    timestamp=time.time(),
                    metadata={"backend": self.backend},
                )
            )
        return kept

    def _is_plausible_face_box(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        frame_w: int,
        frame_h: int,
    ) -> bool:
        """Reject impossible face geometry to reduce false positives."""
        if w <= 0 or h <= 0:
            return False
        if x < 0 or y < 0 or x + w > frame_w or y + h > frame_h:
            return False
        if w < self.min_face_size or h < self.min_face_size:
            return False

        aspect = w / max(1.0, float(h))
        if aspect < 0.45 or aspect > 1.55:
            return False

        area = w * h
        max_area = int(frame_w * frame_h * 0.85)
        if area > max_area:
            return False
        return True

    def _verify_face_roi(self, gray: np.ndarray, x: int, y: int, w: int, h: int) -> bool:
        """
        Optional eye verification for frontal detections.
        Helps reject chair/table patterns that trigger Haar face false positives.
        """
        if not self.require_eyes or self._eye_cascade is None:
            return True
        if w < 28 or h < 28:
            return True

        roi = gray[y : y + h, x : x + w]
        if roi.size == 0:
            return False
        try:
            eyes = self._eye_cascade.detectMultiScale(
                roi,
                scaleFactor=self.eye_scale_factor,
                minNeighbors=self.eye_min_neighbors,
                minSize=(8, 8),
            )
        except cv2.error:
            # Don't block detections if eye model fails on this frame.
            return True
        return len(eyes) >= 1

    def unload_model(self) -> None:
        """Release model resources."""
        self._cascade = None
        self._profile_cascade = None
        self._eye_cascade = None
        logger.info("FaceDetector unloaded")
