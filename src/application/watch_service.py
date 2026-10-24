"""Watch Service - Continuous file monitoring using watchdog"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..domain.classifier import FileClassifier
from ..domain.models import AppConfig, FileInfo
from ..domain.mover import FileMover
from ..infrastructure.filesystem import FileSystem
from ..infrastructure.logger import get_logger

logger = get_logger("watch_service")


@dataclass
class WatchStatus:
    """Watch service status"""
    is_running: bool = False
    watched_paths: list[Path] = None
    files_processed: int = 0
    last_event_time: float = 0
    error: str | None = None

    def __post_init__(self):
        if self.watched_paths is None:
            self.watched_paths = []


class DebouncedEventHandler(FileSystemEventHandler):
    """File system event handler with debouncing"""

    def __init__(
        self,
        callback: Callable[[Path], None],
        debounce_seconds: float = 2.0,
    ):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._pending_events: dict[str, float] = {}
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_event(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._schedule_event(event.dest_path)

    def _schedule_event(self, path: str) -> None:
        """Schedule event with debouncing"""
        with self._lock:
            self._pending_events[path] = time.time()
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._process_events)
            self._timer.start()

    def _process_events(self) -> None:
        """Process debounced events"""
        with self._lock:
            now = time.time()
            ready_events = [
                path for path, timestamp in self._pending_events.items()
                if now - timestamp >= self.debounce_seconds
            ]
            for path in ready_events:
                del self._pending_events[path]

        for path in ready_events:
            try:
                self.callback(Path(path))
            except OSError as e:
                logger.error(f"Error processing event for {path}: {e}")


class WatchService:
    """Manages continuous file watching and organization"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.observer: Observer | None = None
        self.handler: DebouncedEventHandler | None = None
        self.classifier: FileClassifier | None = None
        self.mover: FileMover | None = None
        self.filesystem = FileSystem()
        self.status = WatchStatus()
        self._status_callback: Callable[[WatchStatus], None] | None = None
        self._lock = threading.Lock()

    def set_status_callback(self, callback: Callable[[WatchStatus], None]) -> None:
        """Set callback for status updates"""
        self._status_callback = callback

    def _update_status(self, **kwargs) -> None:
        """Update status and notify callback"""
        for key, value in kwargs.items():
            if hasattr(self.status, key):
                setattr(self.status, key, value)
        if self._status_callback:
            self._status_callback(self.status)

    def start(self) -> bool:
        """Start watching configured paths"""
        with self._lock:
            if self.observer is not None:
                logger.warning("Watch service already running")
                return False

            if not self.config.source_paths:
                self._update_status(error="No source paths configured")
                return False

            # Initialize classifier and mover
            self.classifier = FileClassifier(self.config)
            self.mover = FileMover(self.config.options)

            # Create event handler
            self.handler = DebouncedEventHandler(
                callback=self._process_file,
                debounce_seconds=self.config.watch.debounce_seconds,
            )

            # Create observer
            self.observer = Observer()

            # Schedule watches for each source path
            watched = []
            for path in self.config.source_paths:
                if path.exists() and path.is_dir():
                    self.observer.schedule(self.handler, str(path), recursive=self.config.options.recursive)
                    watched.append(path)
                    logger.info(f"Watching: {path}")
                else:
                    logger.warning(f"Source path does not exist: {path}")

            if not watched:
                self._update_status(error="No valid source paths to watch")
                return False

            self.observer.start()
            self._update_status(
                is_running=True,
                watched_paths=watched,
                error=None,
                files_processed=0,
            )
            logger.info(f"Watch service started on {len(watched)} paths")
            return True

    def stop(self) -> None:
        """Stop watching"""
        with self._lock:
            if self.observer is None:
                return

            self.observer.stop()
            self.observer.join(timeout=5.0)
            self.observer = None
            self.handler = None
            self.classifier = None
            self.mover = None
            self._update_status(is_running=False)
            logger.info("Watch service stopped")

    def _process_file(self, file_path: Path) -> None:
        """Process a single file event"""
        try:
            if not file_path.exists() or not file_path.is_file():
                return

            # Check file size constraints
            stat = file_path.stat()
            if stat.st_size < self.config.options.min_file_size:
                return
            if self.config.options.max_file_size and stat.st_size > self.config.options.max_file_size:
                return

            # Create file info
            file_info = FileInfo(
                source_path=file_path,
                filename=file_path.name,
                extension=file_path.suffix.lower(),
                size=stat.st_size,
            )

            # Classify
            rule = self.classifier.classify(file_info)
            if not rule:
                return

            # Build destination
            dest_dir = Path(rule.destination)
            if self.config.options.create_subfolders_by_date:
                from datetime import datetime
                date_subfolder = datetime.now().strftime(self.config.options.date_format)
                dest_dir = dest_dir / date_subfolder

            file_info.matched_rule = rule
            file_info.destination_path = dest_dir / file_info.filename

            # Move file
            success = self.mover.move_file(file_info)
            if success:
                self.status.files_processed += 1
                self._update_status(
                    files_processed=self.status.files_processed,
                    last_event_time=time.time(),
                )

        except OSError as e:
            logger.error(f"Error processing file {file_path}: {e}")

    def refresh_config(self, config: AppConfig) -> None:
        """Refresh with new config (restart if running)"""
        was_running = self.status.is_running
        if was_running:
            self.stop()
        self.config = config
        if was_running:
            self.start()

    def is_running(self) -> bool:
        return self.status.is_running