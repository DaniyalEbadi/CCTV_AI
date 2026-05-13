"""
Configuration management for the backend.
Handles environment variables and default settings.
"""
import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Backend settings."""

    # Server
    HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    # Inference
    DEVICE: str = os.getenv("INFERENCE_DEVICE", "cpu")  # "cpu" or "cuda"
    CONFIDENCE_THRESHOLD: float = float(
        os.getenv("CONFIDENCE_THRESHOLD", "0.5")
    )

    # go2rtc
    GO2RTC_CONFIG: str = os.getenv(
        "GO2RTC_CONFIG", "go2rtc.yaml"
    )
    GO2RTC_HOST: str = os.getenv("GO2RTC_HOST", "127.0.0.1")
    GO2RTC_PORT: int = int(os.getenv("GO2RTC_PORT", "1984"))
    GO2RTC_RTSP_PORT: int = int(os.getenv("GO2RTC_RTSP_PORT", "8554"))

    # Detectors
    ENABLED_DETECTORS: str = os.getenv(
        "ENABLED_DETECTORS", "person,vehicle,motion"
    )

    # FFmpeg
    FFMPEG_TIMEOUT: int = int(os.getenv("FFMPEG_TIMEOUT", "30"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def go2rtc_api_url(self) -> str:
        """Get go2rtc API base URL."""
        return f"http://{self.GO2RTC_HOST}:{self.GO2RTC_PORT}"

    @property
    def go2rtc_rtsp_url(self) -> str:
        """Get go2rtc RTSP base URL."""
        return f"rtsp://{self.GO2RTC_HOST}:{self.GO2RTC_RTSP_PORT}"

    @property
    def enabled_detectors_list(self) -> list[str]:
        """Get list of enabled detectors."""
        return [d.strip() for d in self.ENABLED_DETECTORS.split(",")]

    def __post_init__(self):
        """Validate settings after initialization."""
        if self.DEVICE not in ("cpu", "cuda"):
            logger.warning(f"Invalid device {self.DEVICE}, using cpu")
            self.DEVICE = "cpu"

        if not 0 <= self.CONFIDENCE_THRESHOLD <= 1.0:
            logger.warning(f"Invalid confidence threshold, using 0.5")
            self.CONFIDENCE_THRESHOLD = 0.5


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get global settings instance."""
    return settings


def log_settings() -> None:
    """Log current settings (without sensitive info)."""
    logger.info(f"Backend running on {settings.HOST}:{settings.PORT}")
    logger.info(f"Inference device: {settings.DEVICE}")
    logger.info(f"Confidence threshold: {settings.CONFIDENCE_THRESHOLD}")
    logger.info(f"go2rtc API: {settings.go2rtc_api_url}")
    logger.info(f"go2rtc RTSP: {settings.go2rtc_rtsp_url}")
    logger.info(f"Enabled detectors: {settings.enabled_detectors_list}")
