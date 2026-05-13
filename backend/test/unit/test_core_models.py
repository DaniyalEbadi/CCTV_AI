"""
Unit Tests for Core Components

Tests individual components in isolation:
- BaseDetector abstract class
- Detection and DetectionResult models
- Configuration settings
- Motion detection algorithm
"""
import pytest
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch

from backend.core import BaseDetector, Detection, DetectionResult
from backend.config import Settings, get_settings
from backend.detectors.motion import MotionDetector


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_frame():
    """Generate a sample test frame (480x640x3 BGR)."""
    return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def sample_detection():
    """Generate a sample Detection object."""
    return Detection(
        label="person",
        confidence=0.95,
        x1=100,
        y1=200,
        x2=150,
        y2=300,
        timestamp=datetime.now().timestamp(),
        metadata={"source": "test"}
    )


@pytest.fixture
def sample_detection_result(sample_detection):
    """Generate a sample DetectionResult object."""
    return DetectionResult(
        detections=[sample_detection],
        inference_time_ms=45.2,
        frame_shape=(480, 640, 3),
        detector_name="test_detector"
    )


# ============================================================================
# DETECTION MODEL TESTS
# ============================================================================

class TestDetectionModel:
    """Test Detection dataclass"""

    def test_detection_creation(self):
        """Test Detection object creation with all fields"""
        detection = Detection(
            label="car",
            confidence=0.87,
            x1=50,
            y1=100,
            x2=200,
            y2=300,
            timestamp=1000.0,
            metadata={"type": "vehicle"}
        )
        assert detection.label == "car"
        assert detection.confidence == 0.87
        assert detection.x1 == 50
        assert detection.metadata["type"] == "vehicle"

    def test_detection_default_metadata(self):
        """Test Detection with default metadata (None)"""
        detection = Detection(
            label="person",
            confidence=0.9,
            x1=0,
            y1=0,
            x2=100,
            y2=100,
            timestamp=1000.0
        )
        assert detection.metadata is None

    def test_detection_bounding_box_coordinates(self):
        """Test bounding box coordinates are valid integers"""
        detection = Detection(
            label="motion",
            confidence=0.5,
            x1=100,
            y1=200,
            x2=300,
            y2=400,
            timestamp=1000.0
        )
        assert isinstance(detection.x1, int)
        assert detection.x2 > detection.x1  # x2 should be > x1
        assert detection.y2 > detection.y1  # y2 should be > y1

    def test_detection_confidence_range(self):
        """Test confidence score is between 0 and 1"""
        # Valid values
        for conf in [0.0, 0.5, 0.99, 1.0]:
            detection = Detection(
                label="test",
                confidence=conf,
                x1=0, y1=0, x2=100, y2=100,
                timestamp=1000.0
            )
            assert 0.0 <= detection.confidence <= 1.0


class TestDetectionResultModel:
    """Test DetectionResult dataclass"""

    def test_detection_result_creation(self, sample_detection):
        """Test DetectionResult object creation"""
        result = DetectionResult(
            detections=[sample_detection],
            inference_time_ms=50.0,
            frame_shape=(480, 640, 3),
            detector_name="person_detector"
        )
        assert result.detector_name == "person_detector"
        assert len(result.detections) == 1
        assert result.inference_time_ms == 50.0

    def test_detection_result_multiple_detections(self):
        """Test DetectionResult with multiple detections"""
        detections = [
            Detection("person", 0.9, 0, 0, 100, 100, 1000.0),
            Detection("car", 0.85, 150, 150, 300, 300, 1000.0),
            Detection("person", 0.78, 350, 50, 400, 200, 1000.0),
        ]
        result = DetectionResult(
            detections=detections,
            inference_time_ms=45.0,
            frame_shape=(480, 640, 3),
            detector_name="yolov8"
        )
        assert len(result.detections) == 3
        assert result.detections[0].label == "person"
        assert result.detections[2].confidence == 0.78

    def test_detection_result_empty_detections(self):
        """Test DetectionResult with no detections"""
        result = DetectionResult(
            detections=[],
            inference_time_ms=10.0,
            frame_shape=(480, 640, 3),
            detector_name="motion_detector"
        )
        assert len(result.detections) == 0
        assert result.inference_time_ms == 10.0

    def test_detection_result_frame_shape(self):
        """Test frame_shape is tuple of 3 integers (H, W, C)"""
        result = DetectionResult(
            detections=[],
            inference_time_ms=25.0,
            frame_shape=(1080, 1920, 3),
            detector_name="test"
        )
        assert result.frame_shape == (1080, 1920, 3)
        assert len(result.frame_shape) == 3


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestConfigSettings:
    """Test Settings dataclass and configuration management"""

    def test_settings_default_values(self):
        """Test Settings has correct default values"""
        with patch.dict('os.environ', {}, clear=True):
            settings = Settings()
            assert settings.HOST == "127.0.0.1"
            assert settings.PORT == 8000
            assert settings.DEVICE == "cpu"
            assert settings.CONFIDENCE_THRESHOLD == 0.5

    def test_settings_env_var_override(self):
        """Test Settings can be overridden by environment variables"""
        env_vars = {
            'BACKEND_HOST': '0.0.0.0',
            'BACKEND_PORT': '9000',
            'INFERENCE_DEVICE': 'cuda',
            'CONFIDENCE_THRESHOLD': '0.7'
        }
        with patch.dict('os.environ', env_vars):
            settings = Settings()
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 9000
            assert settings.DEVICE == "cuda"
            assert settings.CONFIDENCE_THRESHOLD == 0.7

    def test_settings_go2rtc_url_property(self):
        """Test go2rtc_api_url property construction"""
        with patch.dict('os.environ', {
            'GO2RTC_HOST': '192.168.1.1',
            'GO2RTC_PORT': '1984'
        }):
            settings = Settings()
            assert settings.go2rtc_api_url == "http://192.168.1.1:1984"

    def test_settings_enabled_detectors_list(self):
        """Test enabled_detectors_list property parsing"""
        with patch.dict('os.environ', {
            'ENABLED_DETECTORS': 'person,vehicle,motion'
        }):
            settings = Settings()
            detectors = settings.enabled_detectors_list
            assert detectors == ['person', 'vehicle', 'motion']

    def test_settings_invalid_device(self):
        """Test Settings validates device value"""
        with patch.dict('os.environ', {'INFERENCE_DEVICE': 'invalid_device'}):
            settings = Settings()
            # Should default to cpu if invalid
            assert settings.DEVICE in ['cpu', 'cuda']


# ============================================================================
# MOTION DETECTOR TESTS
# ============================================================================

class TestMotionDetector:
    """Test MotionDetector component"""

    def test_motion_detector_initialization(self):
        """Test MotionDetector initializes with correct attributes"""
        detector = MotionDetector(
            confidence_threshold=0.6,
            min_area=500,
            blur_kernel=5
        )
        assert detector.name == "motion_detector"
        assert detector.enabled == True
        assert detector.confidence_threshold == 0.6
        assert detector.min_area == 500
        assert detector.blur_kernel == 5

    def test_motion_detector_load_model(self):
        """Test MotionDetector load_model initializes background subtractor"""
        detector = MotionDetector()
        detector.load_model()
        assert detector.background_subtractor is not None

    def test_motion_detector_detect_returns_detection_result(self, sample_frame):
        """Test MotionDetector.detect returns DetectionResult"""
        detector = MotionDetector()
        detector.load_model()

        result = detector.detect(sample_frame)

        assert isinstance(result, DetectionResult)
        assert result.detector_name == "motion_detector"
        assert result.frame_shape == sample_frame.shape
        assert isinstance(result.detections, list)

    def test_motion_detector_detect_performance(self, sample_frame):
        """Test MotionDetector inference is fast (< 50ms)"""
        detector = MotionDetector()
        detector.load_model()

        result = detector.detect(sample_frame)

        # Motion detection should be fast (< 50ms)
        assert result.inference_time_ms < 50, \
            f"Motion detection took {result.inference_time_ms}ms, should be < 50ms"

    def test_motion_detector_unload_model(self):
        """Test MotionDetector cleanup"""
        detector = MotionDetector()
        detector.load_model()
        detector.unload_model()
        # Should complete without error

    def test_motion_detector_detection_format(self, sample_frame):
        """Test Motion detection returns properly formatted detections"""
        detector = MotionDetector()
        detector.load_model()

        # Generate frame with actual motion (frame differences)
        frame1 = np.ones((480, 640, 3), dtype=np.uint8) * 100
        frame2 = frame1.copy()
        frame2[100:200, 100:200] = 200  # Create motion region

        # Run detection multiple times to establish background
        for _ in range(5):
            detector.detect(frame1)

        result = detector.detect(frame2)

        # Check detection format
        for detection in result.detections:
            assert detection.label == "motion"
            assert 0.0 <= detection.confidence <= 1.0
            assert detection.x1 >= 0
            assert detection.y1 >= 0
            assert detection.x2 > detection.x1
            assert detection.y2 > detection.y1

    def test_motion_detector_disabled(self, sample_frame):
        """Test MotionDetector returns empty results when disabled"""
        detector = MotionDetector()
        detector.load_model()
        detector.enabled = False

        result = detector.detect(sample_frame)

        assert len(result.detections) == 0


# ============================================================================
# BASE DETECTOR ABSTRACT CLASS TESTS
# ============================================================================

class TestBaseDetectorInterface:
    """Test BaseDetector abstract interface"""

    def test_motion_detector_inherits_base_detector(self):
        """Test MotionDetector implements BaseDetector interface"""
        detector = MotionDetector()
        assert isinstance(detector, BaseDetector)

    def test_detector_has_required_methods(self):
        """Test detector has all required methods"""
        detector = MotionDetector()
        assert hasattr(detector, 'load_model')
        assert hasattr(detector, 'detect')
        assert hasattr(detector, 'unload_model')
        assert callable(detector.load_model)
        assert callable(detector.detect)
        assert callable(detector.unload_model)

    def test_detector_has_required_attributes(self):
        """Test detector has all required attributes"""
        detector = MotionDetector()
        assert hasattr(detector, 'name')
        assert hasattr(detector, 'enabled')
        assert hasattr(detector, 'confidence_threshold')


# ============================================================================
# INTEGRATION BETWEEN MODELS
# ============================================================================

class TestModelIntegration:
    """Test integration between Detection, DetectionResult, and Detector"""

    def test_detection_result_contains_valid_detections(self):
        """Test DetectionResult properly contains Detection objects"""
        detections = [
            Detection("person", 0.9, 0, 0, 100, 100, 1000.0),
            Detection("car", 0.85, 150, 150, 300, 300, 1000.0),
        ]
        result = DetectionResult(
            detections=detections,
            inference_time_ms=45.0,
            frame_shape=(480, 640, 3),
            detector_name="test"
        )

        for i, detection in enumerate(result.detections):
            assert isinstance(detection, Detection)
            assert detection.label == detections[i].label
            assert detection.confidence == detections[i].confidence

    def test_detector_to_detection_result_pipeline(self, sample_frame):
        """Test complete flow: Detector -> Detection -> DetectionResult"""
        detector = MotionDetector()
        detector.load_model()

        result = detector.detect(sample_frame)

        # Verify result structure
        assert isinstance(result, DetectionResult)
        assert all(isinstance(d, Detection) for d in result.detections)
        assert result.detector_name == detector.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
