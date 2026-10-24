"""File Classifier - Maps file extensions to categories"""

from pathlib import Path

from ..domain.models import AppConfig, FileInfo, FileRule
from ..infrastructure.logger import get_logger

logger = get_logger("classifier")


class FileClassifier:
    """Classifies files based on extension rules"""

    def __init__(self, config: AppConfig):
        self.config = config
        self._extension_map: dict[str, FileRule] = {}
        self._build_extension_map()

    def _build_extension_map(self) -> None:
        """Build extension to rule mapping (first match wins due to priority sorting)"""
        self._extension_map.clear()
        for rule in self.config.rules:
            if not rule.enabled:
                continue
            for ext in rule.extensions:
                if ext not in self._extension_map:
                    self._extension_map[ext.lower()] = rule

    def classify(self, file_info: FileInfo) -> FileRule | None:
        """Classify a file and return matching rule"""
        rule = self._extension_map.get(file_info.extension.lower())
        if rule:
            logger.debug(f"Classified {file_info.filename} as {rule.category}")
        else:
            logger.debug(f"No rule for {file_info.filename} ({file_info.extension})")
        return rule

    def classify_batch(self, files: list[FileInfo]) -> list[FileInfo]:
        """Classify multiple files"""
        for file_info in files:
            rule = self.classify(file_info)
            if rule:
                file_info.matched_rule = rule
                # Build destination path
                dest_dir = Path(rule.destination)
                if self.config.options.create_subfolders_by_date:
                    from datetime import datetime
                    date_subfolder = datetime.now().strftime(self.config.options.date_format)
                    dest_dir = dest_dir / date_subfolder
                file_info.destination_path = dest_dir / file_info.filename
        return files

    def refresh(self, config: AppConfig) -> None:
        """Refresh classifier with new config"""
        self.config = config
        self._build_extension_map()

    def get_supported_extensions(self) -> list[str]:
        """Get all supported extensions"""
        return list(self._extension_map.keys())

    def get_categories(self) -> list[str]:
        """Get all categories"""
        return list({rule.category for rule in self.config.rules if rule.enabled})