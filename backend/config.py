"""
Configuration schema for the entire backend application.
Centralizes all settings, validates at startup, and provides type safety.
"""
import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("config")


@dataclass
class Go2RTCConfig:
    """go2rtc integration settings."""
    api_url: str
    rtsp_url: str
    login: Optional[str] = None
    password: Optional[str] = None


@dataclass
class AIConfig:
    """AI inference settings."""
    backend: str = "auto"  # "auto", "cpu", "gpu", "motion"
    fps: int = 5
    resolution: str = "640x360"
    confidence_threshold: float = 0.5


@dataclass
class RecordingConfig:
    """Video recording settings."""
    enabled: bool = True
    output_dir: str = "storage/recordings"
    segment_seconds: int = 300


@dataclass
class MediaConfig:
    """Media storage settings."""
    snapshot_dir: str = "storage/snapshots"
    clips_dir: str = "storage/clips"
    event_clip_seconds: int = 15


@dataclass
class AppConfig:
    """Complete application configuration."""
    go2rtc: Go2RTCConfig
    ai: AIConfig
    recording: RecordingConfig
    media: MediaConfig
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    debug: bool = False

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        return cls(
            go2rtc=Go2RTCConfig(
                api_url=os.environ.get("GO2RTC_API", "http://127.0.0.1:1984"),
                rtsp_url=os.environ.get("GO2RTC_RTSP", "rtsp://127.0.0.1:8554"),
                login=os.environ.get("GO2RTC_LOGIN"),
                password=os.environ.get("GO2RTC_PASSWORD"),
            ),
            ai=AIConfig(
                backend=os.environ.get("AI_BACKEND", "auto"),
                fps=int(os.environ.get("AI_FPS", "5")),
                resolution=os.environ.get("AI_RESOLUTION", "640x360"),
                confidence_threshold=float(os.environ.get("AI_CONF", "0.5")),
            ),
            recording=RecordingConfig(
                enabled=os.environ.get("RECORDING_ENABLED", "true").lower() == "true",
                output_dir=os.environ.get("RECORDING_DIR", "storage/recordings"),
                segment_seconds=int(os.environ.get("RECORDING_SEGMENT", "300")),
            ),
            media=MediaConfig(
                snapshot_dir=os.environ.get("SNAPSHOT_DIR", "storage/snapshots"),
                clips_dir=os.environ.get("CLIPS_DIR", "storage/clips"),
                event_clip_seconds=int(os.environ.get("EVENT_CLIP_SECONDS", "15")),
            ),
            api_host=os.environ.get("API_HOST", "127.0.0.1"),
            api_port=int(os.environ.get("API_PORT", "8000")),
            debug=os.environ.get("DEBUG", "false").lower() == "true",
        )

    def validate(self) -> None:
        """Validate configuration at startup."""
        errors = []
        
        if self.ai.fps <= 0 or self.ai.fps > 60:
            errors.append("AI_FPS must be in range [1, 60]")
        
        if not (0 <= self.ai.confidence_threshold <= 1):
            errors.append("AI_CONF must be in [0, 1]")
        
        if not (1 <= self.api_port <= 65535):
            errors.append("API_PORT must be in [1, 65535]")
        
        if self.go2rtc.login and not self.go2rtc.password:
            errors.append("GO2RTC_PASSWORD required if GO2RTC_LOGIN set")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"- {e}" for e in errors))
        
        logger.info("Configuration validated successfully")
