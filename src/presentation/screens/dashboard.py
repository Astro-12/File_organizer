"""Dashboard Screen - Main screen for organizing files"""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Label, Select

from ...application.config_service import ConfigService
from ...application.organizer_service import OrganizerService
from ...application.watch_service import WatchService
from ...domain.models import AppConfig
from ..widgets import FileTable, LogViewer, PathPicker, StatsBar


class DashboardScreen(Screen):
    """Main dashboard screen"""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f1", "help", "Help"),
        Binding("f2", "config", "Config"),
        Binding("f3", "logs", "Logs"),
        Binding("f5", "scan", "Scan"),
        Binding("f6", "organize", "Organize"),
        Binding("f7", "watch", "Watch"),
        Binding("ctrl+c", "cancel", "Cancel"),
    ]

    def __init__(self, config: AppConfig, config_service: ConfigService, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.config_service = config_service
        self.organizer_service = OrganizerService(config)
        self.watch_service = WatchService(config)
        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        """Setup progress and status callbacks"""
        self.organizer_service.set_progress_callback(self._on_progress_update)
        self.watch_service.set_status_callback(self._on_watch_status)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_container"):
            # Source paths section
            with Vertical(id="source_section"):
                yield Label("Source Paths", classes="section-title")
                with Horizontal(id="source_paths"):
                    for path in self.config.source_paths:
                        yield PathPicker("", str(path))
                    yield Button("Add Path", variant="primary", id="add_source")
                    yield Button("Remove Selected", variant="default", id="remove_source")

            # Mode selection
            with Horizontal(id="mode_section"):
                yield Label("Mode:", classes="section-title")
                yield Select(
                    [("One-time Scan", "scan"), ("Continuous Watch", "watch")],
                    value="scan" if not self.config.watch.enabled else "watch",
                    id="mode_select"
                )
                yield Checkbox("Dry Run", value=self.config.options.dry_run, id="dry_run")

            # Action buttons
            with Horizontal(id="actions"):
                yield Button("Scan (F5)", variant="primary", id="scan_btn")
                yield Button("Organize (F6)", variant="success", id="organize_btn")
                yield Button("Start Watch (F7)", variant="warning", id="watch_btn")
                yield Button("Cancel (Ctrl+C)", variant="error", id="cancel_btn")

            # Progress and stats
            with Vertical(id="progress_section"):
                yield Label("Progress", classes="section-title")
                yield StatsBar(id="stats_bar")

            # File table
            with Vertical(id="file_table_section"):
                yield Label("Files", classes="section-title")
                yield FileTable(id="file_table")

            # Log viewer
            with Vertical(id="log_section"):
                yield Label("Activity Log", classes="section-title")
                yield LogViewer(id="log_viewer")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen"""
        self._update_watch_button()
        self._log("INFO", "File Organizer ready")

    def _on_progress_update(self, progress) -> None:
        """Handle progress updates from organizer"""
        self.call_from_thread(self._update_progress_ui, progress)

    def _update_progress_ui(self, progress) -> None:
        """Update progress UI (called from main thread)"""
        stats_bar = self.query_one("#stats_bar", StatsBar)
        stats_bar.update_progress(progress)

        if progress.current_file:
            # Update status of current file
            pass

    def _on_watch_status(self, status) -> None:
        """Handle watch status updates"""
        self.call_from_thread(self._update_watch_ui, status)

    def _update_watch_ui(self, status) -> None:
        """Update watch UI (called from main thread)"""
        self._update_watch_button()
        if status.error:
            self._log("ERROR", status.error)

    def _update_watch_button(self) -> None:
        """Update watch button text based on state"""
        watch_btn = self.query_one("#watch_btn", Button)
        if self.watch_service.status.is_running:
            watch_btn.label = "Stop Watch (F7)"
            watch_btn.variant = "error"
        else:
            watch_btn.label = "Start Watch (F7)"
            watch_btn.variant = "warning"

    def _log(self, level: str, message: str) -> None:
        """Add log entry"""
        log_viewer = self.query_one("#log_viewer", LogViewer)
        log_viewer.add_log(level, message)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        btn_id = event.button.id

        if btn_id == "add_source":
            self.action_add_source()
        elif btn_id == "remove_source":
            self.action_remove_source()
        elif btn_id == "scan_btn":
            await self.action_scan()
        elif btn_id == "organize_btn":
            await self.action_organize()
        elif btn_id == "watch_btn":
            await self.action_toggle_watch()
        elif btn_id == "cancel_btn":
            self.action_cancel()

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes"""
        if event.select.id == "mode_select":
            self.config.watch.enabled = (event.value == "watch")
            self._update_watch_button()

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes"""
        if event.checkbox.id == "dry_run":
            self.config.options.dry_run = event.value
            self.organizer_service.mover.options.dry_run = event.value

    async def action_scan(self) -> None:
        """Scan for files"""
        self._log("INFO", "Scanning source paths...")
        self.query_one("#file_table", FileTable).clear_files()

        try:
            files = self.organizer_service.scan_files()
            file_table = self.query_one("#file_table", FileTable)
            for file_info in files:
                file_table.add_file(file_info)
            self._log("INFO", f"Found {len(files)} files")
        except OSError as e:
            self._log("ERROR", f"Scan failed: {e}")

    async def action_organize(self) -> None:
        """Organize files"""
        self._log("INFO", "Starting organization...")
        file_table = self.query_one("#file_table", FileTable)

        # Get files from table (or re-scan)
        if file_table.row_count == 0:
            await self.action_scan()

        result = self.organizer_service.organize()
        self._log("INFO", f"Complete: {result.moved_files} moved, {result.skipped_files} skipped, {result.error_files} errors")

    async def action_toggle_watch(self) -> None:
        """Toggle watch mode"""
        if self.watch_service.status.is_running:
            self.watch_service.stop()
            self._log("INFO", "Watch mode stopped")
        else:
            if self.watch_service.start():
                self._log("INFO", "Watch mode started")
            else:
                self._log("ERROR", "Failed to start watch mode")

    def action_cancel(self) -> None:
        """Cancel current operation"""
        self.organizer_service.cancel()
        if self.watch_service.status.is_running:
            self.watch_service.stop()
        self._log("WARNING", "Operation cancelled")

    def action_add_source(self) -> None:
        """Add source path"""
        # TODO: Show path picker dialog

    def action_remove_source(self) -> None:
        """Remove selected source path"""

    def action_config(self) -> None:
        """Switch to config screen"""
        self.app.switch_screen("config")

    def action_logs(self) -> None:
        """Switch to logs screen"""
        self.app.switch_screen("logs")

    def action_help(self) -> None:
        """Show help"""
        self._log("INFO", "F1:Help F2:Config F3:Logs F5:Scan F6:Organize F7:Watch Ctrl+C:Cancel Ctrl+Q:Quit")