"""Configuration management."""

import os
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration from environment."""
    
    # Server
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    debug: bool = False
    
    # go2rtc
    go2rtc_api: str = "http://127.0.0.1:1984"
    go2rtc_rtsp: str = "rtsp://127.0.0.1:8554"
    
    # AI
    ai_backend: str = "auto"  # auto, cpu, gpu
    ai_fps: int = 5
    ai_resolution: str = "640x360"
    ai_confidence: float = 0.5
    
    # Storage
    storage_dir: str = "storage"
    recording_enabled: bool = True
    recording_segment_seconds: int = 300
    snapshot_retention_days: int = 7
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        return cls(
            api_host=os.getenv("API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("API_PORT", 8000)),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            go2rtc_api=os.getenv("GO2RTC_API", "http://127.0.0.1:1984"),
            go2rtc_rtsp=os.getenv("GO2RTC_RTSP", "rtsp://127.0.0.1:8554"),
            ai_backend=os.getenv("AI_BACKEND", "auto"),
            ai_fps=int(os.getenv("AI_FPS", 5)),
            ai_resolution=os.getenv("AI_RESOLUTION", "640x360"),
            ai_confidence=float(os.getenv("AI_CONF", 0.5)),
        )
    
    def validate(self) -> None:
        """Validate configuration."""
        errors = []
        
        if not (1 <= self.api_port <= 65535):
            errors.append(f"API_PORT must be 1-65535, got {self.api_port}")
        
        if not (1 <= self.ai_fps <= 60):
            errors.append(f"AI_FPS must be 1-60, got {self.ai_fps}")
        
        if not (0 <= self.ai_confidence <= 1):
            errors.append(f"AI_CONF must be 0-1, got {self.ai_confidence}")
        
        if self.ai_backend not in ("auto", "cpu", "gpu"):
            errors.append(f"AI_BACKEND must be auto/cpu/gpu, got {self.ai_backend}")
        
        if errors:
            error_msg = "\n".join(f"  - {e}" for e in errors)
            raise ValueError(f"Configuration errors:\n{error_msg}")
        
        logger.info("Configuration validated successfully")


# Global config instance
_config: AppConfig = None


def get_config() -> AppConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
        _config.validate()
    return _config


def set_config(config: AppConfig) -> None:
    """Set global configuration (mainly for testing)."""
    global _config
    _config = config
