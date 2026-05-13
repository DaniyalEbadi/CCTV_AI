"""
Camera Manager Service - Integrates with go2rtc.
Manages camera streams and their associated frame sources.
"""
import asyncio
import logging
import threading
from typing import Dict, Optional, List
from urllib.parse import quote
import yaml
import numpy as np

from backend.core import FrameSource

logger = logging.getLogger(__name__)


class CameraManager:
    """Manages camera streams from go2rtc."""

    def __init__(
        self,
        go2rtc_config_path: str = "go2rtc.yaml",
        rtsp_base_url: Optional[str] = None,
    ):
        """
        Initialize camera manager.

        Args:
            go2rtc_config_path: Path to go2rtc.yaml configuration
            rtsp_base_url: Optional go2rtc RTSP base URL (e.g., rtsp://127.0.0.1:8554)
        """
        self.config_path = go2rtc_config_path
        self.rtsp_base_url = rtsp_base_url.rstrip("/") if rtsp_base_url else None
        self.cameras: Dict[str, Dict] = {}
        self.frame_sources: Dict[str, FrameSource] = {}
        self.last_errors: Dict[str, str] = {}
        self._sources_lock = threading.RLock()
        self._starting_cameras: set[str] = set()
        self._load_go2rtc_config()

    def _parse_go2rtc_config(self) -> Dict[str, Dict]:
        """Parse go2rtc.yaml and return camera definitions."""
        cameras: Dict[str, Dict] = {}
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            streams = config.get("streams", {})

            for stream_name, stream_config in streams.items():
                # Prefer go2rtc RTSP output when base URL is provided
                stream_url = None
                if self.rtsp_base_url:
                    stream_url = f"{self.rtsp_base_url}/{quote(stream_name)}"
                    logger.debug(f"Using go2rtc RTSP for {stream_name}: {stream_url}")
                else:
                    # Extract the base stream URL without FFmpeg transcoding parameters
                    if isinstance(stream_config, list):
                        for url in stream_config:
                            if isinstance(url, str):
                                # Remove FFmpeg transcoding parameters (e.g., #video=h264#audio=aac)
                                if url.startswith("ffmpeg:"):
                                    url = url[7:]  # Remove "ffmpeg:" prefix
                                
                                # Remove FFmpeg parameters (everything after #)
                                if "#" in url:
                                    url = url.split("#")[0]
                                
                                stream_url = url
                                logger.debug(f"Extracted stream URL for {stream_name}: {stream_url[:80]}...")
                                break

                cameras[stream_name] = {
                    "name": stream_name,
                    "source": stream_config,
                    "stream_url": stream_url,
                    "status": "idle",
                }
                logger.info(f"Loaded camera: {stream_name}")

            logger.info(f"Parsed {len(cameras)} cameras from go2rtc config")
            return cameras
        except FileNotFoundError:
            logger.error(f"go2rtc config not found at {self.config_path}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load go2rtc config: {e}")
            return {}

    def _load_go2rtc_config(self) -> None:
        """Load camera configuration from go2rtc.yaml."""
        self.cameras = self._parse_go2rtc_config()
        logger.info(f"Loaded {len(self.cameras)} cameras into manager")

    def reload_config(self) -> Dict[str, int]:
        """Reload go2rtc.yaml and update camera list."""
        old_names = set(self.cameras.keys())
        new_cameras = self._parse_go2rtc_config()
        new_names = set(new_cameras.keys())

        added = new_names - old_names
        removed = old_names - new_names

        # Stop removed cameras if they are running
        for name in removed:
            if name in self.frame_sources:
                logger.info("Stopping removed camera | camera=%s", name)
                self.stop_camera(name)

        # Preserve running status for active cameras
        for name in new_cameras.keys():
            if name in self.frame_sources:
                new_cameras[name]["status"] = "running"

        self.cameras = new_cameras

        summary = {
            "total": len(self.cameras),
            "added": len(added),
            "removed": len(removed),
            "running": len(self.frame_sources),
        }
        logger.info(
            "Reloaded cameras | total=%d added=%d removed=%d running=%d",
            summary["total"],
            summary["added"],
            summary["removed"],
            summary["running"],
        )
        return summary

    def start_camera(self, camera_name: str, stream_url: Optional[str] = None) -> bool:
        """
        Start frame source for a camera.

        Args:
            camera_name: Name of camera from go2rtc config
            stream_url: Optional override URL. If None, uses configured stream URL

        Returns:
            True if successful, False otherwise
        """
        if camera_name not in self.cameras:
            logger.error(f"Camera {camera_name} not found in config")
            return False

        with self._sources_lock:
            # Prevent duplicate starts from concurrent requests.
            if camera_name in self._starting_cameras:
                logger.info("Camera start already in progress | camera=%s", camera_name)
                return True

            # If already running, don't spawn duplicate FFmpeg processes.
            existing = self.frame_sources.get(camera_name)
            if existing and getattr(existing, "_running", False):
                logger.info("Camera already running | camera=%s", camera_name)
                return True
            if existing:
                # Stale source object (reader exited). Clean and recreate.
                try:
                    existing.stop()
                except Exception:
                    pass
                self.frame_sources.pop(camera_name, None)

        # Use provided URL or default to configured stream URL
        if stream_url is None:
            stream_url = self.cameras[camera_name].get("stream_url")
            if not stream_url:
                logger.error("No stream URL configured | camera=%s", camera_name)
                logger.error(f"No stream URL configured for camera {camera_name}")
                return False

        frame_source = None
        try:
            with self._sources_lock:
                self._starting_cameras.add(camera_name)
                self.cameras[camera_name]["status"] = "starting"

            logger.info("Starting camera stream | camera=%s url=%s", camera_name, stream_url)
            frame_source = FrameSource(stream_url)
            frame_source.start()

            with self._sources_lock:
                self.frame_sources[camera_name] = frame_source
                self.last_errors.pop(camera_name, None)
                if camera_name in self.cameras:
                    self.cameras[camera_name]["status"] = "running"

            logger.info(f"Started frame source for camera: {camera_name}")
            return True

        except Exception as e:
            with self._sources_lock:
                if frame_source and self.frame_sources.get(camera_name) is frame_source:
                    self.frame_sources.pop(camera_name, None)
                if camera_name in self.cameras:
                    self.cameras[camera_name]["status"] = "stopped"
                if isinstance(e, RuntimeError):
                    self.last_errors[camera_name] = getattr(frame_source, "last_error", str(e)) if frame_source else str(e)
                else:
                    self.last_errors[camera_name] = str(e)
            logger.error(f"Failed to start camera {camera_name}: {e}")
            return False
        finally:
            with self._sources_lock:
                self._starting_cameras.discard(camera_name)

    def stop_camera(self, camera_name: str) -> bool:
        """Stop frame source for a camera."""
        with self._sources_lock:
            source = self.frame_sources.get(camera_name)
            if source is None:
                logger.warning(f"Camera {camera_name} not running")
                return False

        try:
            source.stop()
            with self._sources_lock:
                self.frame_sources.pop(camera_name, None)
                self.last_errors.pop(camera_name, None)
                self._starting_cameras.discard(camera_name)

                if camera_name in self.cameras:
                    self.cameras[camera_name]["status"] = "stopped"

            logger.info(f"Stopped frame source for camera: {camera_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop camera {camera_name}: {e}")
            return False

    def get_frame(self, camera_name: str, auto_start: bool = False) -> Optional[np.ndarray]:
        """
        Get latest frame from camera.

        Args:
            camera_name: Name of camera
            auto_start: If True and camera not running, attempt to start it

        Returns:
            Frame as numpy array or None if not available
        """
        with self._sources_lock:
            source = self.frame_sources.get(camera_name)

        if source is None:
            if auto_start and camera_name in self.cameras:
                logger.info(f"Auto-starting camera: {camera_name}")
                self.start_camera(camera_name)
            else:
                logger.debug(f"Camera {camera_name} not running")
                return None

        with self._sources_lock:
            source = self.frame_sources.get(camera_name)

        if source is None:
            return None

        # Source died after startup: mark stopped so callers can decide restart once.
        if not getattr(source, "_running", False):
            self.cameras[camera_name]["status"] = "stopped"
            return None

        return source.get_frame()

    def get_last_error(self, camera_name: str) -> Optional[str]:
        """Get last FFmpeg/frame source error for a camera."""
        if camera_name in self.frame_sources:
            err = getattr(self.frame_sources[camera_name], "last_error", None)
            if err:
                return err
        return self.last_errors.get(camera_name)

    async def get_frame_async(self, camera_name: str) -> Optional[np.ndarray]:
        """Get latest frame asynchronously."""
        frame = await asyncio.to_thread(self.get_frame, camera_name)
        return frame

    def stop_all_cameras(self) -> None:
        """Stop all active camera frame sources."""
        for camera_name in list(self.frame_sources.keys()):
            try:
                self.stop_camera(camera_name)
            except Exception as e:
                logger.error(f"Error stopping {camera_name}: {e}")

    def get_camera_list(self) -> List[Dict]:
        """Get list of all available cameras."""
        return list(self.cameras.values())

    def get_camera_status(self, camera_name: str) -> Optional[str]:
        """Get status of a specific camera."""
        if camera_name in self.cameras:
            return self.cameras[camera_name]["status"]
        return None

    def get_active_cameras(self) -> List[str]:
        """Get list of active (running) camera names."""
        return [name for name in self.frame_sources.keys()]
