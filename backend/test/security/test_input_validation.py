"""
Security tests for input validation and injection prevention.
Tests API endpoint security, configuration validation, and data sanitization.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from backend.config.config import AppConfig


class TestConfigurationSecurity:
    """Test configuration security and validation."""

    def test_config_port_range_validation(self):
        """Test port number is within valid range."""
        # Valid ports
        for port in [1, 80, 443, 8000, 65535]:
            config = AppConfig(api_port=port)
            config.validate()

        # Invalid ports
        for port in [0, -1, 65536, 100000]:
            config = AppConfig(api_port=port)
            with pytest.raises(ValueError):
                config.validate()

    def test_config_confidence_range_validation(self):
        """Test confidence threshold is between 0 and 1."""
        # Valid values
        for conf in [0.0, 0.25, 0.5, 0.75, 1.0]:
            config = AppConfig(ai_confidence=conf)
            config.validate()

        # Invalid values
        for conf in [-0.1, 1.1, 2.0, -1.0]:
            config = AppConfig(ai_confidence=conf)
            with pytest.raises(ValueError):
                config.validate()

    def test_config_fps_range_validation(self):
        """Test FPS is within reasonable range."""
        # Valid values
        for fps in [1, 5, 15, 30, 60]:
            config = AppConfig(ai_fps=fps)
            config.validate()

        # Invalid values
        for fps in [0, -1, 61, 120]:
            config = AppConfig(ai_fps=fps)
            with pytest.raises(ValueError):
                config.validate()

    def test_config_backend_whitelist(self):
        """Test AI backend is from whitelist."""
        # Valid backends
        for backend in ["auto", "cpu", "gpu"]:
            config = AppConfig(ai_backend=backend)
            config.validate()

        # Invalid backends
        for backend in ["tpu", "xpu", "custom", "unknown"]:
            config = AppConfig(ai_backend=backend)
            with pytest.raises(ValueError):
                config.validate()

    def test_config_host_validation(self):
        """Test API host is valid."""
        # Valid hosts
        valid_hosts = ["127.0.0.1", "0.0.0.0", "192.168.1.1", "localhost"]
        for host in valid_hosts:
            config = AppConfig(api_host=host)
            # Should not raise
            config.validate()

    def test_config_multiple_validation_errors(self):
        """Test multiple validation errors are reported."""
        config = AppConfig(
            api_port=70000,
            ai_fps=100,
            ai_confidence=2.0,
            ai_backend="invalid",
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value)
        assert "Configuration errors" in error_msg
        assert "API_PORT" in error_msg
        assert "AI_FPS" in error_msg
        assert "AI_CONF" in error_msg
        assert "AI_BACKEND" in error_msg


class TestDetectorInputValidation:
    """Test detector input validation."""

    def test_detector_frame_type_validation(self):
        """Test detector validates frame type."""
        from backend.detectors.motion.detector import MotionDetector
        
        detector = MotionDetector()
        detector.load_model()
        
        # Valid frame
        valid_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = detector.detect(valid_frame)
        assert result is not None

    def test_detector_frame_shape_validation(self):
        """Test detector handles various frame shapes."""
        from backend.detectors.motion.detector import MotionDetector
        
        detector = MotionDetector()
        detector.load_model()
        
        # Valid shapes
        valid_shapes = [(240, 320, 3), (480, 640, 3), (1080, 1920, 3)]
        for shape in valid_shapes:
            frame = np.random.randint(0, 255, shape, dtype=np.uint8)
            result = detector.detect(frame)
            assert result.frame_shape == shape

    def test_detector_confidence_threshold_bounds(self):
        """Test detector confidence threshold is bounded."""
        from backend.detectors.motion.detector import MotionDetector
        
        # Valid thresholds
        for threshold in [0.0, 0.1, 0.5, 0.9, 1.0]:
            detector = MotionDetector(confidence_threshold=threshold)
            assert 0.0 <= detector.confidence_threshold <= 1.0

    def test_detector_min_area_positive(self):
        """Test detector minimum area is positive."""
        from backend.detectors.motion.detector import MotionDetector
        
        # Valid areas
        for area in [1, 100, 500, 1000]:
            detector = MotionDetector(min_area=area)
            assert detector.min_area > 0

    def test_detector_blur_kernel_odd(self):
        """Test detector blur kernel is odd."""
        from backend.detectors.motion.detector import MotionDetector
        
        # Valid kernels (odd numbers)
        for kernel in [3, 5, 7, 9]:
            detector = MotionDetector(blur_kernel=kernel)
            assert detector.blur_kernel % 2 == 1


class TestCameraManagerSecurity:
    """Test camera manager security."""

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_invalid_camera_name(self, mock_fs):
        """Test camera manager rejects invalid camera names."""
        import yaml
        from pathlib import Path
        from backend.services.camera_manager import CameraManager
        
        # Create temp config
        config = {"streams": {"camera1": "rtsp://test"}}
        config_file = Path("/tmp/test_go2rtc.yaml")
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        manager = CameraManager(str(config_file))
        
        # Try to access nonexistent camera
        status = manager.get_camera_status("../../etc/passwd")
        assert status is None
        
        # Try to start nonexistent camera
        success = manager.start_camera("../../etc/passwd")
        assert success is False

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_sql_injection_attempt(self, mock_fs):
        """Test camera manager rejects SQL injection attempts."""
        import yaml
        from pathlib import Path
        from backend.services.camera_manager import CameraManager
        
        config = {"streams": {"camera1": "rtsp://test"}}
        config_file = Path("/tmp/test_go2rtc.yaml")
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        manager = CameraManager(str(config_file))
        
        # Try SQL injection
        malicious_name = "camera1'; DROP TABLE cameras; --"
        status = manager.get_camera_status(malicious_name)
        assert status is None

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_path_traversal_attempt(self, mock_fs):
        """Test camera manager rejects path traversal attempts."""
        import yaml
        from pathlib import Path
        from backend.services.camera_manager import CameraManager
        
        config = {"streams": {"camera1": "rtsp://test"}}
        config_file = Path("/tmp/test_go2rtc.yaml")
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        manager = CameraManager(str(config_file))
        
        # Try path traversal
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "camera1/../../sensitive",
        ]
        
        for name in malicious_names:
            status = manager.get_camera_status(name)
            assert status is None


class TestDetectionPipelineSecurity:
    """Test detection pipeline security."""

    def test_pipeline_detector_name_validation(self):
        """Test pipeline validates detector names."""
        with patch("backend.services.detection_pipeline.PersonDetector"), \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            from backend.services.detection_pipeline import DetectionPipeline
            
            pipeline = DetectionPipeline()
            
            # Try to enable nonexistent detector
            success = pipeline.enable_detector("malicious_detector")
            assert success is False
            
            # Try to disable nonexistent detector
            success = pipeline.disable_detector("malicious_detector")
            assert success is False

    def test_pipeline_frame_validation(self):
        """Test pipeline validates frame input."""
        with patch("backend.services.detection_pipeline.PersonDetector") as mock_person, \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            from backend.services.detection_pipeline import DetectionPipeline
            from backend.core.base_detector import DetectionResult
            
            mock_person_instance = MagicMock()
            mock_person_instance.enabled = True
            mock_person_instance.detect.return_value = DetectionResult([], 0, (480, 640, 3), "person")
            mock_person.return_value = mock_person_instance
            
            pipeline = DetectionPipeline()
            
            # Valid frame
            valid_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            results = pipeline.run_detections(valid_frame)
            assert results is not None

    def test_pipeline_confidence_threshold_bounds(self):
        """Test pipeline respects confidence threshold bounds."""
        with patch("backend.services.detection_pipeline.PersonDetector") as mock_person, \
             patch("backend.services.detection_pipeline.VehicleDetector"), \
             patch("backend.services.detection_pipeline.FaceDetector"), \
             patch("backend.services.detection_pipeline.LicensePlateDetector"), \
             patch("backend.services.detection_pipeline.MotionDetector"):
            
            from backend.services.detection_pipeline import DetectionPipeline
            
            mock_person_instance = MagicMock()
            mock_person_instance.confidence_threshold = 0.5
            mock_person.return_value = mock_person_instance
            
            pipeline = DetectionPipeline()
            
            # Confidence should be between 0 and 1
            assert 0.0 <= pipeline.detectors["person"].confidence_threshold <= 1.0
