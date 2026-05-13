"""
End-to-end test that exercises backend API endpoints and dashboard HTML.
This avoids real FFmpeg/YOLO by using lightweight in-memory stubs.
"""
from contextlib import asynccontextmanager
from typing import Dict, List

import numpy as np
from fastapi.testclient import TestClient

from backend.core.base_detector import Detection, DetectionResult
from backend.main import app as backend_app
from backend.api import routes as api_routes


class DummyPipeline:
    def __init__(self):
        self._enabled = ["person", "vehicle"]

    def run_detections(self, frame: np.ndarray) -> Dict[str, DetectionResult]:
        ts = 0.0
        person = Detection(
            label="person",
            confidence=0.9,
            x1=10,
            y1=20,
            x2=100,
            y2=150,
            timestamp=ts,
        )
        vehicle = Detection(
            label="car",
            confidence=0.8,
            x1=200,
            y1=100,
            x2=300,
            y2=200,
            timestamp=ts,
        )
        return {
            "person": DetectionResult([person], 12.0, frame.shape, "person"),
            "vehicle": DetectionResult([vehicle], 15.0, frame.shape, "vehicle"),
        }

    def get_detector_info(self) -> Dict[str, Dict]:
        return {
            "person": {"enabled": True, "confidence_threshold": 0.5, "name": "person_detector"},
            "vehicle": {"enabled": True, "confidence_threshold": 0.5, "name": "vehicle_detector"},
        }

    def get_enabled_detectors(self) -> List[str]:
        return self._enabled

    def get_all_detectors(self) -> List[str]:
        return ["person", "vehicle"]


class DummyCameraManager:
    def __init__(self):
        self.cameras = {
            "danial ebadi": {
                "name": "danial ebadi",
                "source": ["rtsp://example"],
                "stream_url": "rtsp://127.0.0.1:8554/danial%20ebadi",
                "status": "idle",
            }
        }
        self._running = set()

    def get_camera_list(self):
        return list(self.cameras.values())

    def get_active_cameras(self):
        return list(self._running)

    def get_camera_status(self, camera_name: str):
        if camera_name not in self.cameras:
            return None
        return "running" if camera_name in self._running else "idle"

    def start_camera(self, camera_name: str, stream_url=None):
        if camera_name not in self.cameras:
            return False
        self._running.add(camera_name)
        self.cameras[camera_name]["status"] = "running"
        return True

    def stop_camera(self, camera_name: str):
        if camera_name not in self.cameras:
            return False
        self._running.discard(camera_name)
        self.cameras[camera_name]["status"] = "stopped"
        return True

    def get_frame(self, camera_name: str, auto_start: bool = False):
        if camera_name not in self.cameras:
            return None
        if camera_name not in self._running and auto_start:
            self.start_camera(camera_name)
        if camera_name not in self._running:
            return None
        return np.zeros((240, 320, 3), dtype=np.uint8)


def test_dashboard_end2end():
    @asynccontextmanager
    async def test_lifespan(app):
        yield

    # Disable real startup logic (no YOLO/FFmpeg)
    backend_app.router.lifespan_context = test_lifespan

    # Inject dummy services into API + main module
    dummy_pipeline = DummyPipeline()
    dummy_cameras = DummyCameraManager()
    api_routes.set_pipeline(dummy_pipeline)
    api_routes.set_camera_manager(dummy_cameras)

    import backend.main as main_mod
    main_mod.pipeline = dummy_pipeline
    main_mod.camera_manager = dummy_cameras

    client = TestClient(backend_app)

    # Frontend HTML served by backend
    html = client.get("/static/detection_dashboard.html")
    assert html.status_code == 200
    assert "AI Detection Dashboard" in html.text
    assert "API_BASE" in html.text

    # Backend health
    health = client.get("/api/health")
    assert health.status_code == 200
    assert "detectors" in health.json()

    # Cameras list
    cams = client.get("/api/cameras")
    assert cams.status_code == 200
    assert any(c["name"] == "danial ebadi" for c in cams.json()["cameras"])

    # Start camera
    start = client.post("/api/cameras/danial%20ebadi/start")
    assert start.status_code == 200

    # Run detection
    det = client.post("/api/detect/danial%20ebadi")
    assert det.status_code == 200
    results = det.json().get("results", {})
    assert "person" in results
    assert "vehicle" in results

    # Stop camera
    stop = client.post("/api/cameras/danial%20ebadi/stop")
    assert stop.status_code == 200
