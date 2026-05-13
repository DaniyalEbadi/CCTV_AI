"""
Integration tests for Camera Manager.
Tests camera loading, frame source management, and go2rtc integration.
"""
import pytest
import numpy as np
import yaml
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from backend.services.camera_manager import CameraManager


class TestCameraManager:
    """Test CameraManager class."""

    @pytest.fixture
    def go2rtc_config(self, tmp_path):
        """Create a temporary go2rtc config file."""
        config = {
            "streams": {
                "camera1": "rtsp://192.168.1.100:554/stream",
                "camera2": "rtsp://192.168.1.101:554/stream",
                "camera3": "http://192.168.1.102:8080/stream",
            }
        }
        config_file = tmp_path / "go2rtc.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        return str(config_file)

    def test_camera_manager_initialization(self, go2rtc_config):
        """Test camera manager initialization."""
        manager = CameraManager(go2rtc_config)
        assert manager.config_path == go2rtc_config
        assert len(manager.cameras) == 3
        assert "camera1" in manager.cameras
        assert "camera2" in manager.cameras
        assert "camera3" in manager.cameras

    def test_camera_manager_load_config(self, go2rtc_config):
        """Test loading go2rtc configuration."""
        manager = CameraManager(go2rtc_config)
        
        assert manager.cameras["camera1"]["name"] == "camera1"
        assert manager.cameras["camera1"]["status"] == "idle"
        assert manager.cameras["camera2"]["name"] == "camera2"
        assert manager.cameras["camera3"]["name"] == "camera3"

    def test_camera_manager_get_camera_list(self, go2rtc_config):
        """Test getting camera list."""
        manager = CameraManager(go2rtc_config)
        cameras = manager.get_camera_list()
        
        assert len(cameras) == 3
        assert all("name" in c for c in cameras)
        assert all("status" in c for c in cameras)

    def test_camera_manager_get_camera_status(self, go2rtc_config):
        """Test getting camera status."""
        manager = CameraManager(go2rtc_config)
        
        status = manager.get_camera_status("camera1")
        assert status == "idle"
        
        status = manager.get_camera_status("nonexistent")
        assert status is None

    def test_camera_manager_get_active_cameras(self, go2rtc_config):
        """Test getting active cameras."""
        manager = CameraManager(go2rtc_config)
        
        active = manager.get_active_cameras()
        assert len(active) == 0  # No cameras started yet

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_start_camera(self, mock_frame_source, go2rtc_config):
        """Test starting a camera."""
        manager = CameraManager(go2rtc_config)
        
        # Mock the frame source
        mock_fs = MagicMock()
        mock_frame_source.return_value = mock_fs
        
        success = manager.start_camera("camera1")
        
        assert success is True
        assert "camera1" in manager.frame_sources
        assert manager.cameras["camera1"]["status"] == "running"
        mock_fs.start.assert_called_once()

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_start_nonexistent_camera(self, mock_frame_source, go2rtc_config):
        """Test starting a nonexistent camera."""
        manager = CameraManager(go2rtc_config)
        
        success = manager.start_camera("nonexistent")
        
        assert success is False
        assert "nonexistent" not in manager.frame_sources

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_stop_camera(self, mock_frame_source, go2rtc_config):
        """Test stopping a camera."""
        manager = CameraManager(go2rtc_config)
        
        # Start camera first
        mock_fs = MagicMock()
        mock_frame_source.return_value = mock_fs
        manager.start_camera("camera1")
        
        # Stop camera
        success = manager.stop_camera("camera1")
        
        assert success is True
        assert "camera1" not in manager.frame_sources
        assert manager.cameras["camera1"]["status"] == "stopped"
        mock_fs.stop.assert_called_once()

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_stop_nonexistent_camera(self, mock_frame_source, go2rtc_config):
        """Test stopping a nonexistent camera."""
        manager = CameraManager(go2rtc_config)
        
        success = manager.stop_camera("nonexistent")
        
        assert success is False

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_get_frame(self, mock_frame_source, go2rtc_config):
        """Test getting frame from camera."""
        manager = CameraManager(go2rtc_config)
        
        # Start camera with mock
        mock_fs = MagicMock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_fs.get_frame.return_value = test_frame
        mock_frame_source.return_value = mock_fs
        
        manager.start_camera("camera1")
        frame = manager.get_frame("camera1")
        
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        np.testing.assert_array_equal(frame, test_frame)

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_get_frame_not_running(self, mock_frame_source, go2rtc_config):
        """Test getting frame from non-running camera."""
        manager = CameraManager(go2rtc_config)
        
        frame = manager.get_frame("camera1")
        
        assert frame is None

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_multiple_cameras(self, mock_frame_source, go2rtc_config):
        """Test managing multiple cameras."""
        manager = CameraManager(go2rtc_config)
        
        # Start multiple cameras
        mock_fs = MagicMock()
        mock_frame_source.return_value = mock_fs
        
        manager.start_camera("camera1")
        manager.start_camera("camera2")
        
        active = manager.get_active_cameras()
        assert len(active) == 2
        assert "camera1" in active
        assert "camera2" in active

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_stop_all_cameras(self, mock_frame_source, go2rtc_config):
        """Test stopping all cameras."""
        manager = CameraManager(go2rtc_config)
        
        # Start multiple cameras
        mock_fs = MagicMock()
        mock_frame_source.return_value = mock_fs
        
        manager.start_camera("camera1")
        manager.start_camera("camera2")
        manager.start_camera("camera3")
        
        assert len(manager.get_active_cameras()) == 3
        
        # Stop all
        manager.stop_all_cameras()
        
        assert len(manager.get_active_cameras()) == 0

    def test_camera_manager_missing_config(self):
        """Test camera manager with missing config file."""
        manager = CameraManager("/nonexistent/path/go2rtc.yaml")
        
        # Should handle gracefully
        assert len(manager.cameras) == 0

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_custom_stream_url(self, mock_frame_source, go2rtc_config):
        """Test starting camera with custom stream URL."""
        manager = CameraManager(go2rtc_config)
        
        mock_fs = MagicMock()
        mock_frame_source.return_value = mock_fs
        
        custom_url = "rtsp://custom.url:554/stream"
        success = manager.start_camera("camera1", stream_url=custom_url)
        
        assert success is True
        mock_frame_source.assert_called_with(custom_url)

    @patch("backend.services.camera_manager.FrameSource")
    def test_camera_manager_frame_source_error(self, mock_frame_source, go2rtc_config):
        """Test handling frame source errors."""
        manager = CameraManager(go2rtc_config)
        
        # Make frame source raise exception
        mock_frame_source.side_effect = Exception("Connection failed")
        
        success = manager.start_camera("camera1")
        
        assert success is False
        assert "camera1" not in manager.frame_sources
