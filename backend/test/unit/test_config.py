"""
Unit tests for Configuration management.
Tests config loading, validation, and environment variable handling.
"""
import pytest
import os
from unittest.mock import patch
from backend.config.config import AppConfig, get_config, set_config


class TestAppConfig:
    """Test AppConfig class."""

    def test_config_default_values(self):
        """Test default configuration values."""
        config = AppConfig()
        assert config.api_host == "127.0.0.1"
        assert config.api_port == 8000
        assert config.debug is False
        assert config.ai_backend == "auto"
        assert config.ai_confidence == 0.5

    def test_config_custom_values(self):
        """Test creating config with custom values."""
        config = AppConfig(
            api_host="0.0.0.0",
            api_port=9000,
            debug=True,
            ai_backend="gpu",
            ai_confidence=0.7,
        )
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 9000
        assert config.debug is True
        assert config.ai_backend == "gpu"
        assert config.ai_confidence == 0.7

    @patch.dict(os.environ, {
        "API_HOST": "192.168.1.1",
        "API_PORT": "5000",
        "DEBUG": "true",
        "AI_BACKEND": "cpu",
        "AI_CONF": "0.8",
        "AI_FPS": "10",
    })
    def test_config_from_env(self):
        """Test loading config from environment variables."""
        config = AppConfig.from_env()
        assert config.api_host == "192.168.1.1"
        assert config.api_port == 5000
        assert config.debug is True
        assert config.ai_backend == "cpu"
        assert config.ai_confidence == 0.8
        assert config.ai_fps == 10

    def test_config_validation_valid(self):
        """Test validation with valid config."""
        config = AppConfig(
            api_port=8000,
            ai_fps=5,
            ai_confidence=0.5,
            ai_backend="cpu",
        )
        # Should not raise
        config.validate()

    def test_config_validation_invalid_port(self):
        """Test validation with invalid port."""
        config = AppConfig(api_port=70000)
        with pytest.raises(ValueError, match="API_PORT must be 1-65535"):
            config.validate()

    def test_config_validation_invalid_fps(self):
        """Test validation with invalid FPS."""
        config = AppConfig(ai_fps=100)
        with pytest.raises(ValueError, match="AI_FPS must be 1-60"):
            config.validate()

    def test_config_validation_invalid_confidence(self):
        """Test validation with invalid confidence."""
        config = AppConfig(ai_confidence=1.5)
        with pytest.raises(ValueError, match="AI_CONF must be 0-1"):
            config.validate()

    def test_config_validation_invalid_backend(self):
        """Test validation with invalid backend."""
        config = AppConfig(ai_backend="tpu")
        with pytest.raises(ValueError, match="AI_BACKEND must be auto/cpu/gpu"):
            config.validate()

    def test_config_validation_multiple_errors(self):
        """Test validation with multiple errors."""
        config = AppConfig(
            api_port=70000,
            ai_fps=100,
            ai_confidence=2.0,
        )
        with pytest.raises(ValueError, match="Configuration errors"):
            config.validate()

    def test_config_validation_edge_cases(self):
        """Test validation with edge case values."""
        # Valid edge cases
        config = AppConfig(
            api_port=1,
            ai_fps=1,
            ai_confidence=0.0,
        )
        config.validate()

        config = AppConfig(
            api_port=65535,
            ai_fps=60,
            ai_confidence=1.0,
        )
        config.validate()


class TestConfigGlobal:
    """Test global config management."""

    def test_get_config_singleton(self):
        """Test that get_config returns singleton."""
        # Reset global config
        import backend.config.config as config_module
        config_module._config = None
        
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_set_config(self):
        """Test setting global config."""
        import backend.config.config as config_module
        config_module._config = None
        
        custom_config = AppConfig(api_port=9999)
        set_config(custom_config)
        
        retrieved_config = get_config()
        assert retrieved_config.api_port == 9999

    def test_config_isolation(self):
        """Test that config instances are isolated."""
        config1 = AppConfig(api_port=8000)
        config2 = AppConfig(api_port=9000)
        
        assert config1.api_port == 8000
        assert config2.api_port == 9000
        assert config1 is not config2
