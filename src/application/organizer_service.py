"""Organizer Service - Orchestrates scan, classify, and move operations"""

from collections.abc import Callable
from dataclasses import dataclass

from ..domain.classifier import FileClassifier
from ..domain.models import AppConfig, FileInfo, OrganizeResult
from ..domain.mover import FileMover
from ..domain.rules import RulesEngine
from ..infrastructure.filesystem import FileSystem
from ..infrastructure.logger import get_logger

logger = get_logger("organizer_service")


@dataclass
class OrganizeProgress:
    """Progress tracking for organize operation"""
    total_files: int = 0
    processed_files: int = 0
    moved_files: int = 0
    skipped_files: int = 0
    error_files: int = 0
    current_file: str = ""
    is_running: bool = False
    is_cancelled: bool = False


class OrganizerService:
    """Main service for organizing files"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.filesystem = FileSystem()
        self.classifier = FileClassifier(config)
        self.mover = FileMover(config.options)
        self.rules_engine = RulesEngine(config)
        self._progress = OrganizeProgress()
        self._progress_callback: Callable[[OrganizeProgress], None] | None = None

    @property
    def progress(self) -> OrganizeProgress:
        return self._progress

    def set_progress_callback(self, callback: Callable[[OrganizeProgress], None]) -> None:
        """Set callback for progress updates"""
        self._progress_callback = callback

    def _update_progress(self, **kwargs) -> None:
        """Update progress and notify callback"""
        for key, value in kwargs.items():
            if hasattr(self._progress, key):
                setattr(self._progress, key, value)
        if self._progress_callback:
            self._progress_callback(self._progress)

    def scan_files(self) -> list[FileInfo]:
        """Scan source paths for files to organize"""
        self._update_progress(is_running=True, is_cancelled=False)
        files = list(self.filesystem.scan_files(
            source_paths=self.config.source_paths,
            recursive=self.config.options.recursive,
            min_size=self.config.options.min_file_size,
            max_size=self.config.options.max_file_size,
        ))
        self._update_progress(total_files=len(files))
        logger.info(f"Scanned {len(files)} files from {len(self.config.source_paths)} paths")
        return files

    def organize(self, files: list[FileInfo] | None = None) -> OrganizeResult:
        """Organize files: classify and move"""
        if files is None:
            files = self.scan_files()

        if not files:
            logger.info("No files to organize")
            return OrganizeResult(total_files=0)

        # Classify files
        self._update_progress(current_file="Classifying files...")
        files = self.classifier.classify_batch(files)

        # Filter only files with matched rules
        files_to_move = [f for f in files if f.matched_rule is not None]
        logger.info(f"Classified {len(files_to_move)} files for moving")

        # Move files
        self._update_progress(processed_files=0, current_file="Moving files...")
        result = self.mover.move_batch(files_to_move)

        # Update progress with final counts
        self._update_progress(
            processed_files=result.total_files,
            moved_files=result.moved_files,
            skipped_files=result.skipped_files,
            error_files=result.error_files,
            is_running=False,
            current_file="Complete"
        )

        return result

    def cancel(self) -> None:
        """Cancel ongoing operation"""
        self._progress.is_cancelled = True
        logger.info("Organize operation cancelled")

    def refresh_config(self, config: AppConfig) -> None:
        """Refresh service with new config"""
        self.config = config
        self.classifier.refresh(config)
        self.mover = FileMover(config.options)
        self.rules_engine = RulesEngine(config)
        logger.info("Service config refreshed")


class OrganizeStats:
    """Statistics for organize operations"""

    def __init__(self):
        self.total_scans = 0
        self.total_files_processed = 0
        self.total_files_moved = 0
        self.total_errors = 0

    def record_result(self, result: OrganizeResult) -> None:
        self.total_scans += 1
        self.total_files_processed += result.total_files
        self.total_files_moved += result.moved_files
        self.total_errors += result.error_files