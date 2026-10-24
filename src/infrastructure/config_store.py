"""Configuration storage - JSON file persistence"""

import json
from pathlib import Path
from typing import Any

from ..domain.models import DEFAULT_RULES, AppConfig


class ConfigStore:
    """Handles loading and saving configuration to JSON file"""

    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_dir = Path.home() / ".config" / "file-organizer"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "config.json"
        self.config_path = config_path

    def load(self) -> AppConfig:
        """Load configuration from file, create default if not exists"""
        if not self.config_path.exists():
            return self._create_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig.model_validate(data)
        except (json.JSONDecodeError, OSError) as e:
            # Backup corrupted config and create new default
            backup_path = self.config_path.with_suffix(".json.bak")
            try:
                self.config_path.rename(backup_path)
            except OSError:
                pass
            raise ConfigLoadError(f"Failed to load config: {e}") from e

    def save(self, config: AppConfig) -> None:
        """Save configuration to file"""
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup of existing config
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix(".json.bak")
            try:
                self.config_path.replace(backup_path)
            except OSError:
                pass

        # Write new config
        data = config.model_dump(mode="json")
        # Convert Path objects to strings for JSON serialization
        data = self._convert_paths_to_strings(data)

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise ConfigSaveError(f"Failed to save config: {e}") from e

    def _create_default_config(self) -> AppConfig:
        """Create default configuration with standard rules"""
        config = AppConfig(rules=DEFAULT_RULES)
        self.save(config)
        return config

    def _convert_paths_to_strings(self, obj: Any) -> Any:
        """Recursively convert Path objects to strings for JSON serialization"""
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_paths_to_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_paths_to_strings(item) for item in obj]
        return obj


class ConfigLoadError(Exception):
    """Raised when configuration fails to load"""


class ConfigSaveError(Exception):
    """Raised when configuration fails to save"""
