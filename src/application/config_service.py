"""Config Service - Manages configuration operations"""

from pathlib import Path

from ..domain.models import DEFAULT_RULES, AppConfig
from ..domain.rules import RulesEngine
from ..infrastructure.config_store import ConfigLoadError, ConfigSaveError, ConfigStore
from ..infrastructure.logger import get_logger

logger = get_logger("config_service")


class ConfigService:
    """Service for configuration management"""

    def __init__(self, config_path: Path | None = None):
        self.store = ConfigStore(config_path)
        self._config: AppConfig | None = None

    def load(self) -> AppConfig:
        """Load configuration from storage"""
        try:
            self._config = self.store.load()
            logger.info("Configuration loaded successfully")
            return self._config
        except ConfigLoadError as e:
            logger.error(f"Failed to load config: {e}")
            # Return default config on error
            self._config = AppConfig(rules=DEFAULT_RULES.copy())
            return self._config

    def save(self, config: AppConfig | None = None) -> bool:
        """Save configuration to storage"""
        if config is not None:
            self._config = config

        if self._config is None:
            logger.error("No configuration to save")
            return False

        try:
            self.store.save(self._config)
            logger.info("Configuration saved successfully")
            return True
        except ConfigSaveError as e:
            logger.error(f"Failed to save config: {e}")
            return False

    @property
    def config(self) -> AppConfig:
        """Get current configuration (loads if needed)"""
        if self._config is None:
            return self.load()
        return self._config

    def get_rules_engine(self) -> RulesEngine:
        """Get rules engine for current config"""
        return RulesEngine(self.config)

    def add_source_path(self, path: Path) -> bool:
        """Add a source path"""
        if path not in self.config.source_paths:
            self.config.source_paths.append(path)
            return True
        return False

    def remove_source_path(self, path: Path) -> bool:
        """Remove a source path"""
        if path in self.config.source_paths:
            self.config.source_paths.remove(path)
            return True
        return False

    def update_options(self, **kwargs) -> None:
        """Update organizer options"""
        for key, value in kwargs.items():
            if hasattr(self.config.options, key):
                setattr(self.config.options, key, value)

    def update_watch_config(self, **kwargs) -> None:
        """Update watch configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config.watch, key):
                setattr(self.config.watch, key, value)

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._config = AppConfig(rules=DEFAULT_RULES.copy())
        logger.info("Configuration reset to defaults")

    def export_config(self, path: Path) -> bool:
        """Export configuration to file"""
        try:
            self.store.config_path = path
            self.store.save(self.config)
            return True
        except (OSError, ConfigSaveError) as e:
            logger.error(f"Failed to export config: {e}")
            return False

    def import_config(self, path: Path) -> bool:
        """Import configuration from file"""
        try:
            old_path = self.store.config_path
            self.store.config_path = path
            self._config = self.store.load()
            self.store.config_path = old_path
            logger.info("Configuration imported successfully")
            return True
        except (OSError, ConfigLoadError) as e:
            logger.error(f"Failed to import config: {e}")
            return False