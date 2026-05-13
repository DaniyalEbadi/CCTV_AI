from fastapi.testclient import TestClient

from backend.api import routes
from backend.main import app as fastapi_app
from backend.core.base_detector import DetectionResult


class DummyPipeline:
    def run_detections(self, frame):
        return {"dummy": DetectionResult([], 0, frame.shape, "dummy")}

    def get_all_detectors(self):
        return ["dummy"]

    def get_detector_info(self):
        return {"dummy": {"enabled": True, "confidence_threshold": 0.5, "name": "dummy"}}

    def get_enabled_detectors(self):
        return ["dummy"]

    def enable_detector(self, name):
        return True

    def disable_detector(self, name):
        return True


class DummyCameraManager:
    def __init__(self):
        self._status = "idle"
        self.start_calls = 0
        self.cameras = {"cam": {"name": "cam", "stream_url": "rtsp://x", "status": "idle"}}

    def get_camera_list(self):
        return list(self.cameras.values())

    def get_active_cameras(self):
        return ["cam"] if self._status == "running" else []

    def get_camera_status(self, camera_name):
        return self._status if camera_name == "cam" else None

    def start_camera(self, camera_name, stream_url=None):
        self.start_calls += 1
        self._status = "running"
        self.cameras["cam"]["status"] = "running"
        return True

    def stop_camera(self, camera_name):
        self._status = "stopped"
        self.cameras["cam"]["status"] = "stopped"
        return True

    def get_frame(self, camera_name, auto_start=False):
        return None

    def get_last_error(self, camera_name):
        return None

    def reload_config(self):
        return {"total": 1, "added": 0, "removed": 0, "running": 1 if self._status == "running" else 0}


def test_detect_autostarts_only_once():
    routes._last_detect_autostart_attempt.clear()
    routes.set_pipeline(DummyPipeline())
    cameras = DummyCameraManager()
    routes.set_camera_manager(cameras)

    client = TestClient(fastapi_app)
    for _ in range(3):
        resp = client.post("/api/detect/cam")
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_frame_yet"

    assert cameras.start_calls == 1


class DummyCameraManagerFailedStart:
    def __init__(self):
        self._status = "idle"
        self.start_calls = 0
        self.cameras = {"cam": {"name": "cam", "stream_url": "rtsp://x", "status": "idle"}}

    def get_camera_list(self):
        return list(self.cameras.values())

    def get_active_cameras(self):
        return []

    def get_camera_status(self, camera_name):
        return self._status if camera_name == "cam" else None

    def start_camera(self, camera_name, stream_url=None):
        self.start_calls += 1
        return False

    def stop_camera(self, camera_name):
        return True

    def get_frame(self, camera_name, auto_start=False):
        return None

    def get_last_error(self, camera_name):
        return None

    def reload_config(self):
        return {"total": 1, "added": 0, "removed": 0, "running": 0}


def test_detect_autostart_uses_cooldown_when_start_fails():
    routes._last_detect_autostart_attempt.clear()
    routes.set_pipeline(DummyPipeline())
    cameras = DummyCameraManagerFailedStart()
    routes.set_camera_manager(cameras)

    client = TestClient(fastapi_app)
    for _ in range(3):
        resp = client.post("/api/detect/cam")
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_frame_yet"

    assert cameras.start_calls == 1
