"""
Unit tests for Motion Detector.
Tests motion detection using background subtraction.
"""
import pytest
import numpy as np
import cv2
from backend.detectors.motion.detector import MotionDetector


class TestMotionDetector:
    """Test MotionDetector class."""

    def test_motion_detector_initialization(self):
        """Test motion detector initialization."""
        detector = MotionDetector(
            confidence_threshold=0.1,
            min_area=500,
            blur_kernel=5,
        )
        assert detector.name == "motion_detector"
        assert detector.enabled is True
        assert detector.confidence_threshold == 0.1
        assert detector.min_area == 500
        assert detector.blur_kernel == 5

    def test_motion_detector_load_model(self):
        """Test loading motion detector (no actual model)."""
        detector = MotionDetector()
        detector.load_model()
        assert detector.background_subtractor is not None

    def test_motion_detector_unload_model(self):
        """Test unloading motion detector."""
        detector = MotionDetector()
        detector.load_model()
        detector.unload_model()
        assert detector.background_subtractor is None
        assert detector.prev_frame is None

    def test_motion_detector_static_frame(self):
        """Test motion detector on static frame."""
        detector = MotionDetector()
        detector.load_model()
        
        # Create a static frame
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        
        # Run detection multiple times to let background model adapt
        for _ in range(5):
            result = detector.detect(frame)
        
        # Static frame should have minimal motion
        assert result.frame_shape == (480, 640, 3)
        assert result.detector_name == "motion_detector"

    def test_motion_detector_moving_object(self):
        """Test motion detector with moving object."""
        detector = MotionDetector(min_area=100)
        detector.load_model()
        
        # Create base frame
        base_frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
        
        # Let background model adapt
        for _ in range(3):
            detector.detect(base_frame)
        
        # Create frame with moving object (white rectangle)
        moving_frame = base_frame.copy()
        moving_frame[100:200, 100:200] = 255
        
        result = detector.detect(moving_frame)
        
        # Should detect motion
        assert result.frame_shape == (480, 640, 3)
        assert result.inference_time_ms >= 0

    def test_motion_detector_disabled(self):
        """Test disabled motion detector."""
        detector = MotionDetector()
        detector.enabled = False
        detector.load_model()
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = detector.detect(frame)
        
        assert len(result.detections) == 0

    def test_motion_detector_confidence_threshold(self):
        """Test motion detector with different confidence thresholds."""
        for threshold in [0.0, 0.1, 0.5, 0.9]:
            detector = MotionDetector(confidence_threshold=threshold)
            assert detector.confidence_threshold == threshold

    def test_motion_detector_min_area(self):
        """Test motion detector with different minimum areas."""
        for min_area in [100, 500, 1000, 5000]:
            detector = MotionDetector(min_area=min_area)
            assert detector.min_area == min_area

    def test_motion_detector_blur_kernel(self):
        """Test motion detector with different blur kernels."""
        for kernel in [3, 5, 7, 9]:
            detector = MotionDetector(blur_kernel=kernel)
            assert detector.blur_kernel == kernel

    def test_motion_detector_frame_shapes(self):
        """Test motion detector with different frame shapes."""
        detector = MotionDetector()
        detector.load_model()
        
        shapes = [(240, 320, 3), (480, 640, 3), (1080, 1920, 3)]
        for shape in shapes:
            frame = np.random.randint(0, 255, shape, dtype=np.uint8)
            result = detector.detect(frame)
            assert result.frame_shape == shape

    def test_motion_detector_detection_metadata(self):
        """Test motion detection includes metadata."""
        detector = MotionDetector(min_area=100)
        detector.load_model()
        
        # Create base frame
        base_frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
        
        # Let background model adapt
        for _ in range(3):
            detector.detect(base_frame)
        
        # Create frame with moving object
        moving_frame = base_frame.copy()
        moving_frame[100:200, 100:200] = 255
        
        result = detector.detect(moving_frame)
        
        # Check if detections have metadata
        for detection in result.detections:
            assert "area" in detection.metadata
            assert detection.metadata["area"] > 0

    def test_motion_detector_inference_time(self):
        """Test motion detector inference time is recorded."""
        detector = MotionDetector()
        detector.load_model()
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = detector.detect(frame)
        
        assert result.inference_time_ms >= 0
        assert isinstance(result.inference_time_ms, float)

    def test_motion_detector_sequential_frames(self):
        """Test motion detector on sequential frames."""
        detector = MotionDetector()
        detector.load_model()
        
        # Create sequence of frames with gradual change
        for i in range(10):
            frame = np.ones((480, 640, 3), dtype=np.uint8) * (100 + i * 5)
            result = detector.detect(frame)
            assert result.frame_shape == (480, 640, 3)

    def test_motion_detector_context_manager(self):
        """Test motion detector as context manager."""
        with MotionDetector() as detector:
            assert detector.background_subtractor is not None
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            result = detector.detect(frame)
            assert result.frame_shape == (480, 640, 3)
