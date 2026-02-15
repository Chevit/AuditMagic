"""Application configuration management."""
import json
import os
from typing import Dict, Any

from logger import logger, APP_DATA_DIR

CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")

DEFAULT_CONFIG = {
    "language": "uk",  # Ukrainian by default
    "theme": "Light",  # Theme name from Theme enum (e.g., "Light", "Dark")
    "window": {
        "geometry": None,  # Will store window size/position
        "maximized": False,
    },
    "search": {
        "save_history": True,
        "history_limit": 5,
        "autocomplete_enabled": True,
    },
    "database": {
        "backup_on_startup": False,
        "auto_backup_days": 7,
    },
    "ui": {
        "show_tooltips": True,
        "confirm_delete": True,
        "date_format": "dd.MM.yyyy",
        "time_format": "HH:mm:ss",
    },
}


class Config:
    """Configuration manager for application settings."""

    def __init__(self):
        """Initialize configuration, creating default if needed."""
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file or create default."""
        os.makedirs(APP_DATA_DIR, exist_ok=True)

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                self._config = self._merge_configs(DEFAULT_CONFIG, loaded_config)
                logger.info(f"Configuration loaded from: {CONFIG_FILE}")
            except Exception as e:
                logger.error(f"Failed to load config, using defaults: {e}")
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
            self.save()
            logger.info(f"Default configuration created at: {CONFIG_FILE}")

    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'window.geometry', 'language')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """Set configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'window.geometry')
            value: Value to set
            save: Whether to save immediately (default: True)
        """
        keys = key.split(".")
        config = self._config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value
        logger.debug(f"Config set: {key} = {value}")

        if save:
            self.save()

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = DEFAULT_CONFIG.copy()
        self.save()
        logger.info("Configuration reset to defaults")

    @staticmethod
    def _merge_configs(default: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded config with defaults."""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._merge_configs(result[key], value)
            else:
                result[key] = value
        return result


# Global config instance
config = Config()
