"""Main Textual Application"""

from typing import ClassVar

from textual.app import App, ComposeResult

from ..application.config_service import ConfigService
from ..application.organizer_service import OrganizerService
from ..application.watch_service import WatchService
from ..infrastructure.logger import LogCapture, get_logger, setup_logging
from .screens.config_screen import ConfigScreen
from .screens.dashboard import DashboardScreen
from .screens.logs_screen import LogsScreen

logger = get_logger("app")


class FileOrganizerApp(App):
    """Main File Organizer TUI Application"""

    CSS = """
    Screen {
        background: $surface;
    }

    #main_container {
        layout: vertical;
        padding: 1;
        height: 100%;
    }

    #config_container {
        layout: vertical;
        padding: 1;
        height: 100%;
    }

    #logs_container {
        layout: vertical;
        padding: 1;
        height: 100%;
    }

    .section-title {
        text-style: bold;
        color: $primary;
        margin: 1 0;
        padding: 0 1;
    }

    #source_section {
        height: auto;
        min-height: 5;
    }

    #source_paths {
        height: auto;
    }

    #mode_section {
        height: 3;
        margin: 1 0;
    }

    #actions {
        height: 3;
        margin: 1 0;
    }

    #progress_section {
        height: 5;
        margin: 1 0;
    }

    #file_table_section {
        height: 1fr;
        min-height: 10;
        margin: 1 0;
    }

    #log_section {
        height: 1fr;
        min-height: 10;
        margin: 1 0;
    }

    #global_options, #watch_options, #rules_section {
        margin: 1 0;
        padding: 1;
        border: solid $primary;
    }

    #config_actions {
        height: 3;
        margin: 1 0;
    }

    #log_controls {
        height: 3;
        margin: 1 0;
    }

    .dialog {
        width: 60%;
        height: auto;
        padding: 2;
        border: thick $primary;
        background: $surface;
        align: center middle;
    }

    .dialog-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    .dialog-message {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    .dialog-buttons {
        width: 100%;
        align: center middle;
    }

    .log-content {
        height: 1fr;
        overflow-y: scroll;
        padding: 1;
        background: $background;
    }

    PathPicker {
        width: 100%;
    }

    PathPicker > Horizontal {
        width: 100%;
    }

    PathPicker Input {
        width: 1fr;
    }

    RuleEditor {
        margin: 1 0;
        padding: 1;
        border: solid $primary;
    }

    RuleEditor > Horizontal {
        margin: 1 0;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("ctrl+q", "quit", "Quit"),
        ("f1", "help", "Help"),
        ("f2", "switch_screen('config')", "Config"),
        ("f3", "switch_screen('logs')", "Logs"),
    ]

    def __init__(self, config_path=None):
        super().__init__()
        self.config_service = ConfigService(config_path)
        self.config = self.config_service.load()
        self.organizer_service = OrganizerService(self.config)
        self.watch_service = WatchService(self.config)
        self.log_capture = LogCapture()

        # Setup logging with capture
        self.logger = setup_logging(log_file=None)
        self.log_capture.install(self.logger)

    def on_mount(self) -> None:
        """Initialize app"""
        self.install_screen(DashboardScreen(self.config, self.config_service), name="dashboard")
        self.install_screen(ConfigScreen(self.config, self.config_service, self.organizer_service), name="config")
        self.install_screen(LogsScreen(), name="logs")
        self.push_screen("dashboard")
        logger.info("File Organizer started")

    def on_unmount(self) -> None:
        """Cleanup on exit"""
        self.watch_service.stop()
        self.log_capture.uninstall(self.logger)
        logger.info("File Organizer stopped")

    def action_help(self) -> None:
        """Show help"""
        self.notify(
            "F1: Help | F2: Config | F3: Logs | F5: Scan | F6: Organize | F7: Watch | Ctrl+C: Cancel | Ctrl+Q: Quit",
            title="Keyboard Shortcuts",
            severity="information"
        )

    def get_log_viewer(self):
        """Get the log viewer widget"""
        try:
            logs_screen = self.get_screen("logs")
            return logs_screen.query_one("#log_viewer")
        except LookupError:
            return None

    def log_to_tui(self, level: str, message: str) -> None:
        """Send log to TUI log viewer"""
        log_viewer = self.get_log_viewer()
        if log_viewer:
            log_viewer.add_log(level, message)