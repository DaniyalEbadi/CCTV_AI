"""
Unit tests for Detection model.
Tests bounding box calculations, IoU, and serialization.
"""
import pytest
import numpy as np
from backend.core.base_detector import Detection, DetectionResult
from backend.models.detection import BoundingBox


class TestBoundingBox:
    """Test BoundingBox class."""

    def test_bbox_creation(self):
        """Test creating a bounding box."""
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=150)
        assert bbox.x1 == 10
        assert bbox.y1 == 20
        assert bbox.x2 == 100
        assert bbox.y2 == 150

    def test_bbox_width(self):
        """Test bounding box width calculation."""
        bbox = BoundingBox(x1=10, y1=20, x2=110, y2=150)
        assert bbox.width == 100

    def test_bbox_height(self):
        """Test bounding box height calculation."""
        bbox = BoundingBox(x1=10, y1=20, x2=110, y2=170)
        assert bbox.height == 150

    def test_bbox_area(self):
        """Test bounding box area calculation."""
        bbox = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        assert bbox.area == 10000

    def test_bbox_center(self):
        """Test bounding box center calculation."""
        bbox = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        center_x, center_y = bbox.center
        assert center_x == 50
        assert center_y == 50

    def test_bbox_iou_perfect_overlap(self):
        """Test IoU with perfect overlap."""
        bbox1 = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        bbox2 = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        assert bbox1.iou(bbox2) == 1.0

    def test_bbox_iou_no_overlap(self):
        """Test IoU with no overlap."""
        bbox1 = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        bbox2 = BoundingBox(x1=200, y1=200, x2=300, y2=300)
        assert bbox1.iou(bbox2) == 0.0

    def test_bbox_iou_partial_overlap(self):
        """Test IoU with partial overlap."""
        bbox1 = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        bbox2 = BoundingBox(x1=50, y1=50, x2=150, y2=150)
        iou = bbox1.iou(bbox2)
        assert 0 < iou < 1
        # Intersection: 50x50 = 2500
        # Union: 10000 + 10000 - 2500 = 17500
        # IoU: 2500/17500 ≈ 0.1428
        assert abs(iou - 2500/17500) < 0.001

    def test_bbox_iou_edge_case_zero_area(self):
        """Test IoU with zero area boxes."""
        bbox1 = BoundingBox(x1=0, y1=0, x2=0, y2=0)
        bbox2 = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        assert bbox1.iou(bbox2) == 0.0


class TestDetection:
    """Test Detection class."""

    def test_detection_creation(self):
        """Test creating a detection."""
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=150)
        detection = Detection(
            type="person",
            confidence=0.95,
            bbox=bbox,
            timestamp=1234567890.0,
            detector_name="person_detector",
        )
        assert detection.type == "person"
        assert detection.confidence == 0.95
        assert detection.detector_name == "person_detector"

    def test_detection_metadata(self):
        """Test detection with metadata."""
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=150)
        metadata = {"age": 25, "gender": "male"}
        detection = Detection(
            type="face",
            confidence=0.92,
            bbox=bbox,
            timestamp=1234567890.0,
            detector_name="face_detector",
            metadata=metadata,
        )
        assert detection.metadata == metadata
        assert detection.metadata["age"] == 25

    def test_detection_to_dict(self):
        """Test detection serialization to dict."""
        bbox = BoundingBox(x1=10.5, y1=20.3, x2=100.7, y2=150.2)
        detection = Detection(
            type="car",
            confidence=0.87,
            bbox=bbox,
            timestamp=1234567890.0,
            detector_name="vehicle_detector",
            metadata={"color": "red"},
        )
        result_dict = detection.to_dict()
        
        assert result_dict["type"] == "car"
        assert result_dict["confidence"] == 0.87
        assert result_dict["detector"] == "vehicle_detector"
        assert result_dict["bbox"]["x1"] == 10.5
        assert result_dict["metadata"]["color"] == "red"

    def test_detection_confidence_rounding(self):
        """Test confidence rounding in serialization."""
        bbox = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        detection = Detection(
            type="person",
            confidence=0.123456789,
            bbox=bbox,
            timestamp=1234567890.0,
            detector_name="person_detector",
        )
        result_dict = detection.to_dict()
        assert result_dict["confidence"] == 0.123


class TestDetectionResult:
    """Test DetectionResult class."""

    def test_detection_result_creation(self):
        """Test creating a detection result."""
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=150)
        detection = Detection(
            type="person",
            confidence=0.95,
            bbox=bbox,
            timestamp=1234567890.0,
            detector_name="person_detector",
        )
        result = DetectionResult(
            detections=[detection],
            inference_time_ms=45.2,
            frame_shape=(480, 640, 3),
            detector_name="person_detector",
        )
        
        assert len(result.detections) == 1
        assert result.inference_time_ms == 45.2
        assert result.frame_shape == (480, 640, 3)
        assert result.detector_name == "person_detector"

    def test_detection_result_empty(self):
        """Test detection result with no detections."""
        result = DetectionResult(
            detections=[],
            inference_time_ms=10.5,
            frame_shape=(480, 640, 3),
            detector_name="person_detector",
        )
        
        assert len(result.detections) == 0
        assert result.inference_time_ms == 10.5

    def test_detection_result_multiple_detections(self):
        """Test detection result with multiple detections."""
        detections = []
        for i in range(5):
            bbox = BoundingBox(x1=i*100, y1=i*100, x2=(i+1)*100, y2=(i+1)*100)
            detection = Detection(
                type="person",
                confidence=0.9 - i*0.05,
                bbox=bbox,
                timestamp=1234567890.0 + i,
                detector_name="person_detector",
            )
            detections.append(detection)
        
        result = DetectionResult(
            detections=detections,
            inference_time_ms=100.0,
            frame_shape=(480, 640, 3),
            detector_name="person_detector",
        )
        
        assert len(result.detections) == 5
        assert result.detections[0].confidence == 0.9
        assert result.detections[4].confidence == 0.7
