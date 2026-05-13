"""
Integration tests for Detection Pipeline.
Tests detector orchestration, model loading, and result aggregation.
"""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from backend.services.detection_pipeline import DetectionPipeline
from backend.core.base_detector import Detection, DetectionResult, BoundingBox


class TestDetectionPipeline:
    """Test DetectionPipeline class."""

    def test_pipeline_initialization_default(self):
        """Test pipeline initialization with default detectors."""
        with patch("backend.services.detection_pipeline.PersonDetector"), \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            pipeline = DetectionPipeline()
            
            assert pipeline.device == "cpu"
            assert len(pipeline.detectors) == 5
            assert "person" in pipeline.detectors
            assert "vehicle" in pipeline.detectors
            assert "face" in pipeline.detectors
            assert "license_plate" in pipeline.detectors
            assert "motion" in pipeline.detectors

    def test_pipeline_initialization_custom_device(self):
        """Test pipeline initialization with custom device."""
        with patch("backend.services.detection_pipeline.PersonDetector"), \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            pipeline = DetectionPipeline(device="cuda")
            
            assert pipeline.device == "cuda"

    def test_pipeline_initialization_enabled_detectors(self):
        """Test pipeline with specific enabled detectors."""
        with patch("backend.services.detection_pipeline.PersonDetector"), \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            enabled = ["person", "motion"]
            pipeline = DetectionPipeline(enabled_detectors=enabled)
            
            assert len(pipeline.detectors) == 2
            assert "person" in pipeline.detectors
            assert "motion" in pipeline.detectors
            assert "vehicle" not in pipeline.detectors

    def test_pipeline_get_all_detectors(self):
        """Test getting all detector names."""
        with patch("backend.services.detection_pipeline.PersonDetector"), \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            pipeline = DetectionPipeline()
            detectors = pipeline.get_all_detectors()
            
            assert len(detectors) == 5
            assert "person" in detectors
            assert "vehicle" in detectors

    def test_pipeline_get_enabled_detectors(self):
        """Test getting enabled detector names."""
        with patch("backend.services.detection_pipeline.PersonDetector") as mock_person, \
             patch("backend.services.detection_pipeline.VehicleDetector") as mock_vehicle, \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            pipeline = DetectionPipeline()
            
            # Disable some detectors
            pipeline.detectors["person"].enabled = True
            pipeline.detectors["vehicle"].enabled = False
            pipeline.detectors["face"].enabled = True
            
            enabled = pipeline.get_enabled_detectors()
            
            assert "person" in enabled
            assert "face" in enabled
            assert "vehicle" not in enabled

    def test_pipeline_enable_detector(self):
        """Test enabling a detector."""
        with patch("backend.services.detection_pipeline.PersonDetector"), \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            pipeline = DetectionPipeline()
            pipeline.detectors["person"].enabled = False
            
            success = pipeline.enable_detector("person")
            
            assert success is True
            assert pipeline.detectors["person"].enabled is True

    def test_pipeline_enable_nonexistent_detector(self):
        """Test enabling nonexistent detector."""
        with patch("backend.services.detection_pipeline.PersonDetector"), \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            pipeline = DetectionPipeline()
            success = pipeline.enable_detector("nonexistent")
            
            assert success is False

    def test_pipeline_disable_detector(self):
        """Test disabling a detector."""
        with patch("backend.services.detection_pipeline.PersonDetector"), \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            pipeline = DetectionPipeline()
            pipeline.detectors["person"].enabled = True
            
            success = pipeline.disable_detector("person")
            
            assert success is True
            assert pipeline.detectors["person"].enabled is False

    def test_pipeline_run_detections(self):
        """Test running detections on frame."""
        with patch("backend.services.detection_pipeline.PersonDetector") as mock_person, \
             patch("backend.services.detection_pipeline.VehicleDetector") as mock_vehicle, \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            # Create mock detectors
            mock_person_instance = MagicMock()
            mock_person_instance.enabled = True
            mock_person_instance.detect.return_value = DetectionResult([], 10.0, (480, 640, 3), "person")
            mock_person.return_value = mock_person_instance
            
            mock_vehicle_instance = MagicMock()
            mock_vehicle_instance.enabled = True
            mock_vehicle_instance.detect.return_value = DetectionResult([], 15.0, (480, 640, 3), "vehicle")
            mock_vehicle.return_value = mock_vehicle_instance
            
            pipeline = DetectionPipeline()
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            results = pipeline.run_detections(frame)
            
            assert "person" in results
            assert "vehicle" in results

    def test_pipeline_run_detections_disabled_detector(self):
        """Test running detections with disabled detector."""
        with patch("backend.services.detection_pipeline.PersonDetector") as mock_person, \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            mock_person_instance = MagicMock()
            mock_person_instance.enabled = False
            mock_person.return_value = mock_person_instance
            
            pipeline = DetectionPipeline()
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            results = pipeline.run_detections(frame)
            
            # Disabled detector should not be in results
            assert "person" not in results or results["person"].detections == []

    def test_pipeline_get_detector_info(self):
        """Test getting detector information."""
        with patch("backend.services.detection_pipeline.PersonDetector") as mock_person, \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            mock_person_instance = MagicMock()
            mock_person_instance.enabled = True
            mock_person_instance.confidence_threshold = 0.5
            mock_person_instance.name = "person_detector"
            mock_person.return_value = mock_person_instance
            
            pipeline = DetectionPipeline()
            info = pipeline.get_detector_info()
            
            assert "person" in info
            assert info["person"]["enabled"] is True
            assert info["person"]["confidence_threshold"] == 0.5

    def test_pipeline_load_all_models(self):
        """Test loading all detector models."""
        with patch("backend.services.detection_pipeline.PersonDetector") as mock_person, \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            mock_person_instance = MagicMock()
            mock_person.return_value = mock_person_instance
            
            pipeline = DetectionPipeline()
            pipeline.load_all_models()
            
            # All detectors should have load_model called
            for detector in pipeline.detectors.values():
                detector.load_model.assert_called()

    def test_pipeline_unload_all_models(self):
        """Test unloading all detector models."""
        with patch("backend.services.detection_pipeline.PersonDetector") as mock_person, \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            mock_person_instance = MagicMock()
            mock_person.return_value = mock_person_instance
            
            pipeline = DetectionPipeline()
            pipeline.unload_all_models()
            
            # All detectors should have unload_model called
            for detector in pipeline.detectors.values():
                detector.unload_model.assert_called()
