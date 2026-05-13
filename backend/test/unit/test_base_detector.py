"""
Unit tests for BaseDetector abstract class.
Tests detector interface and context manager functionality.
"""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from backend.core.base_detector import BaseDetector, Detection, DetectionResult, BoundingBox


class ConcreteDetector(BaseDetector):
    """Concrete implementation of BaseDetector for testing."""

    def __init__(self, name="test_detector", enabled=True, confidence_threshold=0.5):
        super().__init__(name, enabled, confidence_threshold)
        self.model_loaded = False
        self.model_unloaded = False

    def load_model(self):
        """Load model."""
        self.model_loaded = True

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Run detection."""
        if not self.enabled:
            return DetectionResult([], 0, frame.shape, self.name)
        
        # Return a dummy detection
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=150)
        detection = Detection(
            label="test",
            confidence=0.9,
            x1=10,
            y1=20,
            x2=100,
            y2=150,
            timestamp=0,
        )
        return DetectionResult([detection], 10.0, frame.shape, self.name)

    def unload_model(self):
        """Unload model."""
        self.model_unloaded = True


class TestBaseDetector:
    """Test BaseDetector class."""

    def test_detector_initialization(self):
        """Test detector initialization."""
        detector = ConcreteDetector(
            name="person_detector",
            enabled=True,
            confidence_threshold=0.7,
        )
        assert detector.name == "person_detector"
        assert detector.enabled is True
        assert detector.confidence_threshold == 0.7

    def test_detector_disabled(self):
        """Test disabled detector returns empty results."""
        detector = ConcreteDetector(enabled=False)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        result = detector.detect(frame)
        assert len(result.detections) == 0
        assert result.detector_name == detector.name

    def test_detector_enabled(self):
        """Test enabled detector returns detections."""
        detector = ConcreteDetector(enabled=True)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        result = detector.detect(frame)
        assert len(result.detections) == 1
        assert result.detections[0].label == "test"

    def test_detector_context_manager(self):
        """Test detector as context manager."""
        detector = ConcreteDetector()
        
        assert detector.model_loaded is False
        assert detector.model_unloaded is False
        
        with detector:
            assert detector.model_loaded is True
            assert detector.model_unloaded is False
        
        assert detector.model_unloaded is True

    def test_detector_context_manager_exception(self):
        """Test detector context manager with exception."""
        detector = ConcreteDetector()
        
        try:
            with detector:
                assert detector.model_loaded is True
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should still unload even with exception
        assert detector.model_unloaded is True

    def test_detector_confidence_threshold_range(self):
        """Test detector with various confidence thresholds."""
        for threshold in [0.0, 0.25, 0.5, 0.75, 1.0]:
            detector = ConcreteDetector(confidence_threshold=threshold)
            assert detector.confidence_threshold == threshold

    def test_detector_enable_disable(self):
        """Test enabling and disabling detector."""
        detector = ConcreteDetector(enabled=True)
        assert detector.enabled is True
        
        detector.enabled = False
        assert detector.enabled is False
        
        detector.enabled = True
        assert detector.enabled is True

    def test_detector_multiple_frames(self):
        """Test detector on multiple frames."""
        detector = ConcreteDetector()
        
        for i in range(5):
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            result = detector.detect(frame)
            assert result.frame_shape == (480, 640, 3)
            assert len(result.detections) == 1

    def test_detector_different_frame_sizes(self):
        """Test detector with different frame sizes."""
        detector = ConcreteDetector()
        
        sizes = [(240, 320, 3), (480, 640, 3), (1080, 1920, 3)]
        for size in sizes:
            frame = np.random.randint(0, 255, size, dtype=np.uint8)
            result = detector.detect(frame)
            assert result.frame_shape == size

    def test_detector_name_uniqueness(self):
        """Test detector names are unique."""
        detector1 = ConcreteDetector(name="detector_1")
        detector2 = ConcreteDetector(name="detector_2")
        
        assert detector1.name != detector2.name
        assert detector1.name == "detector_1"
        assert detector2.name == "detector_2"
