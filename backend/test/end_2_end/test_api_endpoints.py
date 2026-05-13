"""
End-to-end tests for API endpoints.
Tests complete workflows from HTTP request to response.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime


@pytest.fixture
def mock_app():
    """Create a test FastAPI app with mocked dependencies."""
    from fastapi import FastAPI
    from backend.api.routes import router, set_pipeline, set_camera_manager
    
    app = FastAPI()
    app.include_router(router)
    
    # Create mock pipeline and camera manager
    mock_pipeline = MagicMock()
    mock_pipeline.get_all_detectors.return_value = ["person", "vehicle", "motion"]
    mock_pipeline.get_enabled_detectors.return_value = ["person", "vehicle"]
    mock_pipeline.get_detector_info.return_value = {
        "person": {"enabled": True, "confidence_threshold": 0.5, "name": "person_detector"},
        "vehicle": {"enabled": True, "confidence_threshold": 0.5, "name": "vehicle_detector"},
        "motion": {"enabled": False, "confidence_threshold": 0.1, "name": "motion_detector"},
    }
    
    mock_camera_manager = MagicMock()
    mock_camera_manager.get_camera_list.return_value = [
        {"name": "camera1", "status": "idle"},
        {"name": "camera2", "status": "idle"},
    ]
    mock_camera_manager.get_camera_status.return_value = "idle"
    mock_camera_manager.get_active_cameras.return_value = []
    mock_camera_manager.get_frame.return_value = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    set_pipeline(mock_pipeline)
    set_camera_manager(mock_camera_manager)
    
    return app, mock_pipeline, mock_camera_manager


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_success(self, mock_app):
        """Test health check returns healthy status."""
        app, mock_pipeline, mock_camera_manager = mock_app
        client = TestClient(app)
        
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "detectors" in data
        assert "cameras" in data

    def test_health_check_includes_detectors(self, mock_app):
        """Test health check includes detector list."""
        app, mock_pipeline, mock_camera_manager = mock_app
        client = TestClient(app)
        
        response = client.get("/api/health")
        data = response.json()
        
        assert len(data["detectors"]) == 3
        assert "person" in data["detectors"]

    def test_health_check_includes_cameras(self, mock_app):
        """Test health check includes camera list."""
        app, mock_pipeline, mock_camera_manager = mock_app
        client = TestClient(app)
        
        response = client.get("/api/health")
        data = response.json()
        
        assert len(data["cameras"]) == 2
        assert "camera1" in data["cameras"]


class TestCameraEndpoints:
    """Test camera management endpoints."""

    def test_list_cameras(self, mock_app):
        """Test listing all cameras."""
        app, mock_pipeline, mock_camera_manager = mock_app
        client = TestClient(app)
        
        response = client.get("/api/cameras")
        
        assert response.status_code == 200
        data = response.json()
        assert "cameras" in data
        assert "total" in data
        assert "active" in data
        assert data["total"] == 2

    def test_camera_status(self, mock_app):
        """Test getting camera status."""
        app, mock_pipeline, mock_camera_manager = mock_app
        client = TestClient(app)
        
        response = client.get("/api/cameras/camera1/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["camera"] == "camera1"
        assert data["status"] == "idle"

    def test_camera_status_not_found(self, mock_app):
        """Test getting status of nonexistent camera."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_camera_manager.get_camera_status.return_value = None
        client = TestClient(app)
        
        response = client.get("/api/cameras/nonexistent/status")
        
        assert response.status_code == 404

    def test_start_camera(self, mock_app):
        """Test starting a camera."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_camera_manager.start_camera.return_value = True
        mock_camera_manager.get_camera_status.return_value = "idle"
        client = TestClient(app)
        
        response = client.post("/api/cameras/camera1/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["camera"] == "camera1"

    def test_start_camera_already_running(self, mock_app):
        """Test starting already running camera."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_camera_manager.get_camera_status.return_value = "running"
        client = TestClient(app)
        
        response = client.post("/api/cameras/camera1/start")
        
        assert response.status_code == 400

    def test_stop_camera(self, mock_app):
        """Test stopping a camera."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_camera_manager.stop_camera.return_value = True
        client = TestClient(app)
        
        response = client.post("/api/cameras/camera1/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["camera"] == "camera1"

    def test_stop_camera_failure(self, mock_app):
        """Test stopping camera that fails."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_camera_manager.stop_camera.return_value = False
        client = TestClient(app)
        
        response = client.post("/api/cameras/camera1/stop")
        
        assert response.status_code == 400


class TestDetectorEndpoints:
    """Test detector management endpoints."""

    def test_list_detectors(self, mock_app):
        """Test listing all detectors."""
        app, mock_pipeline, mock_camera_manager = mock_app
        client = TestClient(app)
        
        response = client.get("/api/detectors")
        
        assert response.status_code == 200
        data = response.json()
        assert "detectors" in data
        assert "enabled" in data
        assert "total" in data
        assert data["total"] == 3

    def test_enable_detector(self, mock_app):
        """Test enabling a detector."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_pipeline.enable_detector.return_value = True
        client = TestClient(app)
        
        response = client.post("/api/detectors/motion/enable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enabled"
        assert data["detector"] == "motion"

    def test_enable_nonexistent_detector(self, mock_app):
        """Test enabling nonexistent detector."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_pipeline.enable_detector.return_value = False
        client = TestClient(app)
        
        response = client.post("/api/detectors/nonexistent/enable")
        
        assert response.status_code == 404

    def test_disable_detector(self, mock_app):
        """Test disabling a detector."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_pipeline.disable_detector.return_value = True
        client = TestClient(app)
        
        response = client.post("/api/detectors/person/disable")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"
        assert data["detector"] == "person"

    def test_disable_nonexistent_detector(self, mock_app):
        """Test disabling nonexistent detector."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_pipeline.disable_detector.return_value = False
        client = TestClient(app)
        
        response = client.post("/api/detectors/nonexistent/disable")
        
        assert response.status_code == 404


class TestDetectionEndpoints:
    """Test detection inference endpoints."""

    def test_detect_objects(self, mock_app):
        """Test running detection on camera frame."""
        app, mock_pipeline, mock_camera_manager = mock_app
        
        from backend.core.base_detector import Detection, DetectionResult
        
        # Create mock detection result
        detection = Detection(
            label="person",
            confidence=0.95,
            x1=10,
            y1=20,
            x2=100,
            y2=150,
            timestamp=0,
        )
        result = DetectionResult([detection], 45.2, (480, 640, 3), "person")
        mock_pipeline.run_detections.return_value = {"person": result}
        
        client = TestClient(app)
        response = client.post("/api/detect/camera1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["camera"] == "camera1"
        assert "results" in data
        assert "person" in data["results"]

    def test_detect_objects_no_frame(self, mock_app):
        """Test detection when no frame available."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_camera_manager.get_frame.return_value = None
        client = TestClient(app)
        
        response = client.post("/api/detect/camera1")
        
        assert response.status_code == 400

    def test_detect_persons(self, mock_app):
        """Test person detection endpoint."""
        app, mock_pipeline, mock_camera_manager = mock_app
        
        from backend.core.base_detector import Detection, DetectionResult
        
        detection = Detection(
            label="person",
            confidence=0.92,
            x1=50,
            y1=60,
            x2=150,
            y2=300,
            timestamp=0,
        )
        result = DetectionResult([detection], 30.0, (480, 640, 3), "person")
        mock_pipeline.run_detections.return_value = {"person": result}
        
        client = TestClient(app)
        response = client.get("/api/detect/camera1/person")
        
        assert response.status_code == 200
        data = response.json()
        assert data["camera"] == "camera1"
        assert data["detector"] == "person"
        assert data["count"] == 1
        assert len(data["detections"]) == 1

    def test_detect_persons_no_detector(self, mock_app):
        """Test person detection when detector not available."""
        app, mock_pipeline, mock_camera_manager = mock_app
        mock_pipeline.run_detections.return_value = {}
        client = TestClient(app)
        
        response = client.get("/api/detect/camera1/person")
        
        assert response.status_code == 400


class TestSettingsEndpoint:
    """Test settings endpoint."""

    def test_get_settings(self, mock_app):
        """Test getting application settings."""
        app, mock_pipeline, mock_camera_manager = mock_app
        client = TestClient(app)
        
        response = client.get("/api/settings")
        
        assert response.status_code == 200
        data = response.json()
        assert "device" in data
        assert "confidence_threshold" in data
        assert "go2rtc_url" in data
        assert "enabled_detectors" in data
