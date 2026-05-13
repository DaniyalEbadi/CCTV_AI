"""
Detection Pipeline Service - Orchestrates all detectors.
Manages loading, running inference, and aggregating results.
"""
import asyncio
import logging
import time
from typing import List, Dict, Optional
import numpy as np

from backend.core import FrameSource, Detection, DetectionResult
from backend.detectors.person import PersonDetector
from backend.detectors.vehicle import VehicleDetector
from backend.detectors.face import FaceDetector
from backend.detectors.license_plate import LicensePlateDetector
from backend.detectors.motion import MotionDetector
from backend.detectors.vehicle.detector import VEHICLE_CLASSES

logger = logging.getLogger(__name__)


class DetectionPipeline:
    """Orchestrates all detection models and aggregates results."""

    def __init__(self, device: str = "cpu", enabled_detectors: Optional[List[str]] = None):
        """
        Initialize detection pipeline.

        Args:
            device: "cpu" or "cuda" for inference device
            enabled_detectors: List of detector names to enable. If None, enables all.
        """
        self.device = device
        self.detectors = {}
        self._init_detectors(enabled_detectors)

    def _init_detectors(self, enabled_list: Optional[List[str]] = None):
        """Initialize all detector instances."""
        all_detectors = {
            "person": PersonDetector(device=self.device),
            "vehicle": VehicleDetector(device=self.device),
            "face": FaceDetector(device=self.device),
            "license_plate": LicensePlateDetector(device=self.device),
            "motion": MotionDetector(),  # Motion detector is CPU-only
        }

        # Keep all detectors registered so runtime enable/disable always works.
        self.detectors = all_detectors
        if enabled_list is not None:
            enabled_set = set(enabled_list)
            for name, detector in self.detectors.items():
                detector.enabled = name in enabled_set

        logger.info(f"DetectionPipeline initialized with detectors: {list(self.detectors.keys())}")

    def load_all_models(self) -> None:
        """Load all enabled detector models."""
        for name, detector in self.detectors.items():
            if not detector.enabled:
                logger.info("Skipping disabled detector at startup: %s", name)
                continue
            try:
                detector.load_model()
                logger.info(f"Loaded {name} detector")
            except Exception as e:
                logger.error(f"Failed to load {name} detector: {e}")
                self.detectors[name].enabled = False

    def unload_all_models(self) -> None:
        """Unload all detector models and release resources."""
        for name, detector in self.detectors.items():
            try:
                detector.unload_model()
                logger.info(f"Unloaded {name} detector")
            except Exception as e:
                logger.error(f"Failed to unload {name} detector: {e}")

    def run_detections(self, frame: np.ndarray) -> Dict[str, DetectionResult]:
        """
        Run all enabled detectors on frame.

        Args:
            frame: Input frame (BGR format from OpenCV)

        Returns:
            Dictionary mapping detector name to DetectionResult
        """
        results = {}
        shared_results = self._run_shared_person_vehicle(frame)
        results.update(shared_results)

        for name, detector in self.detectors.items():
            if name in ("person", "vehicle") and name in results:
                continue
            if not detector.enabled:
                continue

            try:
                result = detector.detect(frame)
                results[name] = result
                logger.debug(
                    f"{name}: {len(result.detections)} detections in {result.inference_time_ms:.2f}ms"
                )
            except Exception as e:
                logger.error(f"Error running {name} detector: {e}")
                results[name] = DetectionResult([], 0, frame.shape, name)

        return results

    def _run_shared_person_vehicle(self, frame: np.ndarray) -> Dict[str, DetectionResult]:
        """
        Run one YOLO pass and split outputs into person/vehicle results.
        This avoids running YOLO twice per frame.
        """
        person_detector = self.detectors.get("person")
        vehicle_detector = self.detectors.get("vehicle")

        person_enabled = bool(person_detector and person_detector.enabled)
        vehicle_enabled = bool(vehicle_detector and vehicle_detector.enabled)
        if not person_enabled and not vehicle_enabled:
            return {}

        model_owner = None
        if person_enabled and getattr(person_detector, "model", None) is not None:
            model_owner = person_detector
        elif vehicle_enabled and getattr(vehicle_detector, "model", None) is not None:
            model_owner = vehicle_detector
        if model_owner is None:
            return {}

        try:
            frame_rgb = frame[:, :, ::-1]
            person_conf = getattr(person_detector, "confidence_threshold", 0.5)
            vehicle_conf = getattr(vehicle_detector, "confidence_threshold", 0.5)
            min_conf = min(person_conf, vehicle_conf)

            start_time = time.time()
            yolo_result = model_owner.model.predict(
                source=frame_rgb,
                conf=min_conf,
                iou=getattr(model_owner, "iou", 0.45),
                imgsz=getattr(model_owner, "imgsz", 640),
                device=model_owner.device if getattr(model_owner, "device", "cpu") == "cpu" else 0,
                verbose=False,
            )[0]
            inference_time = (time.time() - start_time) * 1000

            person_detections: List[Detection] = []
            vehicle_detections: List[Detection] = []
            timestamp = time.time()

            for box in yolo_result.boxes.data.tolist():
                x1, y1, x2, y2, confidence, class_id = box
                class_id = int(class_id)
                confidence = float(confidence)

                if person_enabled and class_id == 0 and confidence >= person_conf:
                    person_detections.append(
                        Detection(
                            label="person",
                            confidence=confidence,
                            x1=int(x1),
                            y1=int(y1),
                            x2=int(x2),
                            y2=int(y2),
                            timestamp=timestamp,
                        )
                    )
                    continue

                if vehicle_enabled and class_id in VEHICLE_CLASSES and confidence >= vehicle_conf:
                    vehicle_detections.append(
                        Detection(
                            label=VEHICLE_CLASSES[class_id],
                            confidence=confidence,
                            x1=int(x1),
                            y1=int(y1),
                            x2=int(x2),
                            y2=int(y2),
                            timestamp=timestamp,
                        )
                    )

            results: Dict[str, DetectionResult] = {}
            if person_enabled:
                results["person"] = DetectionResult(
                    person_detections, inference_time, frame.shape, person_detector.name
                )
            if vehicle_enabled:
                results["vehicle"] = DetectionResult(
                    vehicle_detections, inference_time, frame.shape, vehicle_detector.name
                )
            return results
        except Exception as e:
            logger.error("Shared person/vehicle inference failed, falling back: %s", e)
            return {}

    async def run_detections_async(self, frame: np.ndarray) -> Dict[str, DetectionResult]:
        """
        Run all detectors asynchronously (non-blocking).

        Args:
            frame: Input frame (BGR format)

        Returns:
            Dictionary mapping detector name to DetectionResult
        """
        tasks = [
            asyncio.to_thread(detector.detect, frame)
            for detector in self.detectors.values()
            if detector.enabled
        ]

        if not tasks:
            return {}

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for name, detector in self.detectors.items():
            if not detector.enabled:
                continue

            # Find corresponding result
            detector_idx = list(self.detectors.keys()).index(name)
            if detector_idx < len(results_list):
                result = results_list[detector_idx]
                if isinstance(result, Exception):
                    logger.error(f"Error in {name} detector: {result}")
                    results[name] = DetectionResult([], 0, frame.shape, name)
                else:
                    results[name] = result

        return results

    def enable_detector(self, name: str) -> bool:
        """Enable a specific detector."""
        if name in self.detectors:
            detector = self.detectors[name]
            if detector.enabled:
                return True
            try:
                detector.load_model()
            except Exception as e:
                logger.error("Failed to enable %s detector: %s", name, e)
                detector.enabled = False
                return False
            detector.enabled = True
            logger.info(f"Enabled {name} detector")
            return True
        return False

    def disable_detector(self, name: str) -> bool:
        """Disable a specific detector."""
        if name in self.detectors:
            self.detectors[name].enabled = False
            logger.info(f"Disabled {name} detector")
            return True
        return False

    def get_enabled_detectors(self) -> List[str]:
        """Get list of enabled detector names."""
        return [name for name, det in self.detectors.items() if det.enabled]

    def get_all_detectors(self) -> List[str]:
        """Get list of all available detector names."""
        return list(self.detectors.keys())

    def get_detector_info(self) -> Dict[str, Dict]:
        """Get information about all detectors."""
        return {
            name: {
                "enabled": detector.enabled,
                "confidence_threshold": detector.confidence_threshold,
                "name": detector.name,
            }
            for name, detector in self.detectors.items()
        }
