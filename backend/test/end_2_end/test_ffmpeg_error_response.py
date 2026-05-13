import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.api import routes
from backend.main import app as fastapi_app
from backend.core.base_detector import DetectionResult


class DummyDetector:
    enabled = True
    confidence_threshold = 0.5
    name = "dummy"

    def load_model(self): ...

    def unload_model(self): ...

    def detect(self, frame):
        return DetectionResult([], 0, frame.shape, self.name)


class DummyPipeline:
    def __init__(self):
        self.detectors = {"dummy": DummyDetector()}

    def run_detections(self, frame):
        return {"dummy": DetectionResult([], 0, frame.shape, "dummy")}

    def get_all_detectors(self):
        return list(self.detectors.keys())

    def get_detector_info(self):
        return {"dummy": {"enabled": True, "confidence_threshold": 0.5, "name": "dummy"}}

    def get_enabled_detectors(self):
        return list(self.detectors.keys())

    def enable_detector(self, name): ...

    def disable_detector(self, name): ...


class DummyCameraManager:
    def __init__(self):
        self.cameras = {"cam": {"name": "cam", "stream_url": "rtsp://example", "status": "idle"}}

    def get_camera_list(self):
        return list(self.cameras.values())

    def get_active_cameras(self):
        return []

    def get_camera_status(self, camera_name):
        return "idle"

    def start_camera(self, camera_name, stream_url=None):
        return False

    def stop_camera(self, camera_name):
        return True

    def get_frame(self, camera_name, auto_start=False):
        return None

    def get_last_error(self, camera_name):
        return "FFmpeg initialization failed"


@pytest.fixture
def client(monkeypatch):
    routes._last_detect_autostart_attempt.clear()
    pipeline = DummyPipeline()
    cameras = DummyCameraManager()
    routes.set_pipeline(pipeline)
    routes.set_camera_manager(cameras)
    yield TestClient(fastapi_app)


def test_detect_returns_ffmpeg_error(client):
    resp = client.post("/api/detect/cam")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ffmpeg_error"
    assert "FFmpeg initialization failed" in data["message"]
