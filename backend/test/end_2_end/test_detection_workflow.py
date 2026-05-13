"""
End-to-end tests for complete detection workflows.
Tests full pipeline from camera frame to detection results.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from backend.core.base_detector import Detection, DetectionResult


class TestCompleteDetectionWorkflow:
    """Test complete detection workflows."""

    @patch("backend.services.detection_pipeline.PersonDetector")
    @patch("backend.services.detection_pipeline.VehicleDetector")
    @patch("backend.services.detection_pipeline.FaceDetector")
    @patch("backend.services.detection_pipeline.LicensePlateDetector")
    @patch("backend.services.detection_pipeline.MotionDetector")
    def test_full_detection_pipeline(self, mock_motion, mock_lp, mock_face, mock_vehicle, mock_person):
        """Test complete detection pipeline workflow."""
        from backend.services.detection_pipeline import DetectionPipeline
        
        # Setup mock detectors
        mock_person_instance = MagicMock()
        mock_person_instance.enabled = True
        mock_person_instance.name = "person_detector"
        mock_person_instance.confidence_threshold = 0.5
        person_detection = Detection(
            label="person",
            confidence=0.95,
            x1=10,
            y1=20,
            x2=100,
            y2=150,
            timestamp=0,
        )
        mock_person_instance.detect.return_value = DetectionResult(
            [person_detection], 45.0, (480, 640, 3), "person"
        )
        mock_person.return_value = mock_person_instance
        
        mock_vehicle_instance = MagicMock()
        mock_vehicle_instance.enabled = True
        mock_vehicle_instance.name = "vehicle_detector"
        mock_vehicle_instance.confidence_threshold = 0.5
        vehicle_detection = Detection(
            label="car",
            confidence=0.87,
            x1=200,
            y1=100,
            x2=400,
            y2=300,
            timestamp=0,
        )
        mock_vehicle_instance.detect.return_value = DetectionResult(
            [vehicle_detection], 50.0, (480, 640, 3), "vehicle"
        )
        mock_vehicle.return_value = mock_vehicle_instance
        
        mock_motion_instance = MagicMock()
        mock_motion_instance.enabled = True
        mock_motion_instance.name = "motion_detector"
        mock_motion_instance.confidence_threshold = 0.1
        mock_motion_instance.detect.return_value = DetectionResult(
            [], 10.0, (480, 640, 3), "motion"
        )
        mock_motion.return_value = mock_motion_instance
        
        mock_face.return_value = MagicMock(enabled=False)
        mock_lp.return_value = MagicMock(enabled=False)
        
        # Create pipeline
        pipeline = DetectionPipeline(device="cpu")
        
        # Run detection
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        results = pipeline.run_detections(frame)
        
        # Verify results
        assert "person" in results
        assert "vehicle" in results
        assert len(results["person"].detections) == 1
        assert len(results["vehicle"].detections) == 1
        assert results["person"].detections[0].label == "person"
        assert results["vehicle"].detections[0].label == "car"

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_to_detection_workflow(self, mock_frame_source):
        """Test workflow from camera frame to detection."""
        import yaml
        from pathlib import Path
        from backend.services.camera_manager import CameraManager
        
        # Create temp config
        config = {"streams": {"camera1": "rtsp://test"}}
        config_file = Path("/tmp/test_go2rtc.yaml")
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        # Setup camera manager
        manager = CameraManager(str(config_file))
        
        # Mock frame source
        mock_fs = MagicMock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_fs.get_frame.return_value = test_frame
        mock_frame_source.return_value = mock_fs
        
        # Start camera
        success = manager.start_camera("camera1")
        assert success is True
        
        # Get frame
        frame = manager.get_frame("camera1")
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        np.testing.assert_array_equal(frame, test_frame)

    @patch("backend.services.detection_pipeline.PersonDetector")
    @patch("backend.services.detection_pipeline.VehicleDetector")
    @patch("backend.services.detection_pipeline.FaceDetector")
    @patch("backend.services.detection_pipeline.LicensePlateDetector")
    @patch("backend.services.detection_pipeline.MotionDetector")
    def test_multiple_frame_detection(self, mock_motion, mock_lp, mock_face, mock_vehicle, mock_person):
        """Test detection on multiple sequential frames."""
        from backend.services.detection_pipeline import DetectionPipeline
        
        # Setup mock detectors
        mock_person_instance = MagicMock()
        mock_person_instance.enabled = True
        mock_person_instance.name = "person_detector"
        mock_person_instance.confidence_threshold = 0.5
        mock_person_instance.detect.return_value = DetectionResult([], 45.0, (480, 640, 3), "person")
        mock_person.return_value = mock_person_instance
        
        mock_vehicle_instance = MagicMock()
        mock_vehicle_instance.enabled = True
        mock_vehicle_instance.name = "vehicle_detector"
        mock_vehicle_instance.confidence_threshold = 0.5
        mock_vehicle_instance.detect.return_value = DetectionResult([], 50.0, (480, 640, 3), "vehicle")
        mock_vehicle.return_value = mock_vehicle_instance
        
        mock_motion_instance = MagicMock()
        mock_motion_instance.enabled = True
        mock_motion_instance.name = "motion_detector"
        mock_motion_instance.confidence_threshold = 0.1
        mock_motion_instance.detect.return_value = DetectionResult([], 10.0, (480, 640, 3), "motion")
        mock_motion.return_value = mock_motion_instance
        
        mock_face.return_value = MagicMock(enabled=False)
        mock_lp.return_value = MagicMock(enabled=False)
        
        pipeline = DetectionPipeline()
        
        # Process multiple frames
        for i in range(10):
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            results = pipeline.run_detections(frame)
            
            assert "person" in results
            assert "vehicle" in results
            assert results["person"].frame_shape == (480, 640, 3)

    @patch("backend.services.detection_pipeline.PersonDetector")
    @patch("backend.services.detection_pipeline.VehicleDetector")
    @patch("backend.services.detection_pipeline.FaceDetector")
    @patch("backend.services.detection_pipeline.LicensePlateDetector")
    @patch("backend.services.detection_pipeline.MotionDetector")
    def test_detector_enable_disable_workflow(self, mock_motion, mock_lp, mock_face, mock_vehicle, mock_person):
        """Test enabling/disabling detectors during operation."""
        from backend.services.detection_pipeline import DetectionPipeline
        
        # Setup mocks
        for mock_cls in [mock_person, mock_vehicle, mock_face, mock_lp, mock_motion]:
            mock_instance = MagicMock()
            mock_instance.enabled = True
            mock_instance.name = "test_detector"
            mock_instance.confidence_threshold = 0.5
            mock_instance.detect.return_value = DetectionResult([], 10.0, (480, 640, 3), "test")
            mock_cls.return_value = mock_instance
        
        pipeline = DetectionPipeline()
        
        # All detectors enabled
        enabled = pipeline.get_enabled_detectors()
        assert len(enabled) == 5
        
        # Disable some detectors
        pipeline.disable_detector("person")
        pipeline.disable_detector("vehicle")
        
        enabled = pipeline.get_enabled_detectors()
        assert "person" not in enabled
        assert "vehicle" not in enabled
        assert "motion" in enabled
        
        # Re-enable
        pipeline.enable_detector("person")
        enabled = pipeline.get_enabled_detectors()
        assert "person" in enabled

    @patch("backend.services.detection_pipeline.PersonDetector")
    @patch("backend.services.detection_pipeline.VehicleDetector")
    @patch("backend.services.detection_pipeline.FaceDetector")
    @patch("backend.services.detection_pipeline.LicensePlateDetector")
    @patch("backend.services.detection_pipeline.MotionDetector")
    def test_detection_with_different_frame_sizes(self, mock_motion, mock_lp, mock_face, mock_vehicle, mock_person):
        """Test detection pipeline with different frame sizes."""
        from backend.services.detection_pipeline import DetectionPipeline
        
        # Setup mocks
        for mock_cls in [mock_person, mock_vehicle, mock_face, mock_lp, mock_motion]:
            mock_instance = MagicMock()
            mock_instance.enabled = True
            mock_instance.name = "test_detector"
            mock_instance.confidence_threshold = 0.5
            
            def make_detect(size):
                def detect(frame):
                    return DetectionResult([], 10.0, size, "test")
                return detect
            
            mock_instance.detect.side_effect = lambda f: DetectionResult([], 10.0, f.shape, "test")
            mock_cls.return_value = mock_instance
        
        pipeline = DetectionPipeline()
        
        # Test different frame sizes
        sizes = [(240, 320, 3), (480, 640, 3), (1080, 1920, 3)]
        for size in sizes:
            frame = np.random.randint(0, 255, size, dtype=np.uint8)
            results = pipeline.run_detections(frame)
            
            for detector_name, result in results.items():
                assert result.frame_shape == size

    @patch("backend.services.detection_pipeline.PersonDetector")
    @patch("backend.services.detection_pipeline.VehicleDetector")
    @patch("backend.services.detection_pipeline.FaceDetector")
    @patch("backend.services.detection_pipeline.LicensePlateDetector")
    @patch("backend.services.detection_pipeline.MotionDetector")
    def test_detection_error_handling(self, mock_motion, mock_lp, mock_face, mock_vehicle, mock_person):
        """Test detection pipeline handles detector errors gracefully."""
        from backend.services.detection_pipeline import DetectionPipeline
        
        # Setup mock that raises exception
        mock_person_instance = MagicMock()
        mock_person_instance.enabled = True
        mock_person_instance.name = "person_detector"
        mock_person_instance.detect.side_effect = Exception("Model error")
        mock_person.return_value = mock_person_instance
        
        # Setup other mocks normally
        for mock_cls in [mock_vehicle, mock_face, mock_lp, mock_motion]:
            mock_instance = MagicMock()
            mock_instance.enabled = True
            mock_instance.name = "test_detector"
            mock_instance.detect.return_value = DetectionResult([], 10.0, (480, 640, 3), "test")
            mock_cls.return_value = mock_instance
        
        pipeline = DetectionPipeline()
        
        # Should handle error gracefully
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        results = pipeline.run_detections(frame)
        
        # Should still have results from other detectors
        assert "person" in results
        assert len(results["person"].detections) == 0  # Error detector returns empty
