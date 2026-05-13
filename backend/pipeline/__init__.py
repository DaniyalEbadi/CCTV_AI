"""Detection pipeline - orchestrates multiple detectors."""

import logging
import asyncio
from typing import List, Dict
import numpy as np

from ..models import Detection, Frame
from ..detectors import (
    BaseDetector,
    PersonDetector,
    VehicleDetector,
    MotionDetector,
)
from ..config import AppConfig

logger = logging.getLogger(__name__)


class DetectionPipeline:
    """Orchestrates detection across multiple detector instances."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.detectors: Dict[str, BaseDetector] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize all configured detectors."""
        try:
            # Load person detector
            person = PersonDetector(
                model_name=self.config.yolo_model,
                confidence=self.config.person_confidence,
            )
            person.initialize()
            if person.enabled:
                self.detectors["person"] = person
                logger.info("PersonDetector ready")
            
            # Load vehicle detector
            vehicle = VehicleDetector(
                model_name=self.config.yolo_model,
                confidence=self.config.vehicle_confidence,
            )
            vehicle.initialize()
            if vehicle.enabled:
                self.detectors["vehicle"] = vehicle
                logger.info("VehicleDetector ready")
            
            # Load motion detector
            motion = MotionDetector(
                threshold=self.config.motion_threshold,
                min_area=self.config.motion_min_area,
            )
            motion.initialize()
            if motion.enabled:
                self.detectors["motion"] = motion
                logger.info("MotionDetector ready")
            
            if not self.detectors:
                logger.warning("No detectors initialized")
                return
            
            self._initialized = True
            logger.info(f"DetectionPipeline ready with {len(self.detectors)} detectors")
        
        except Exception as e:
            logger.exception(f"Failed to initialize DetectionPipeline: {e}")
    
    async def process(self, frame: Frame) -> List[Detection]:
        """Run all detectors on frame concurrently."""
        if not self._initialized or not self.detectors:
            return []
        
        try:
            # Run all detectors in parallel
            tasks = [
                asyncio.to_thread(detector.detect, frame)
                for detector in self.detectors.values()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect all detections
            all_detections = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Detector error: {result}")
                elif isinstance(result, list):
                    all_detections.extend(result)
            
            # Apply NMS (non-maximum suppression) to reduce duplicates
            if self.config.enable_nms:
                all_detections = self._apply_nms(all_detections)
            
            return all_detections
        
        except Exception as e:
            logger.exception(f"Pipeline processing error: {e}")
            return []
    
    def process_sync(self, frame: Frame) -> List[Detection]:
        """Run all detectors on frame sequentially (for sync contexts)."""
        if not self._initialized or not self.detectors:
            return []
        
        try:
            all_detections = []
            
            for detector in self.detectors.values():
                try:
                    detections = detector.detect(frame)
                    if detections:
                        all_detections.extend(detections)
                except Exception as e:
                    logger.error(f"Detector error: {e}")
            
            # Apply NMS
            if self.config.enable_nms:
                all_detections = self._apply_nms(all_detections)
            
            return all_detections
        
        except Exception as e:
            logger.exception(f"Pipeline processing error: {e}")
            return []
    
    @staticmethod
    def _apply_nms(detections: List[Detection], iou_threshold: float = 0.5) -> List[Detection]:
        """Apply non-maximum suppression to filter overlapping detections."""
        if not detections:
            return []
        
        # Sort by confidence descending
        sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
        keep = []
        
        for det in sorted_dets:
            # Check overlap with kept detections
            overlaps = False
            for kept in keep:
                # Only compare same type
                if det.type != kept.type:
                    continue
                
                iou = det.bbox.iou(kept.bbox)
                if iou > iou_threshold:
                    overlaps = True
                    break
            
            if not overlaps:
                keep.append(det)
        
        return keep
    
    def cleanup(self) -> None:
        """Cleanup detector resources."""
        for detector in self.detectors.values():
            try:
                detector.cleanup()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        
        self.detectors.clear()
        self._initialized = False
