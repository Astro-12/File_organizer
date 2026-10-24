"""Logs Screen - View operation logs"""

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Select

from ..widgets import LogViewer


class LogsScreen(Screen):
    """Logs viewing screen"""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back", "Back"),
        Binding("f1", "help", "Help"),
        Binding("c", "clear", "Clear"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="logs_container"):
            with Horizontal(id="log_controls"):
                yield Label("Log Level:")
                yield Select([
                    ("DEBUG", "DEBUG"),
                    ("INFO", "INFO"),
                    ("WARNING", "WARNING"),
                    ("ERROR", "ERROR"),
                ], value="INFO", id="log_level_filter")
                yield Button("Clear (C)", variant="default", id="clear_logs")
                yield Button("Export", variant="primary", id="export_logs")
            yield LogViewer(id="log_viewer")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen"""

    def add_log(self, level: str, message: str) -> None:
        """Add log entry from external source"""
        log_viewer = self.query_one("#log_viewer", LogViewer)
        log_viewer.add_log(level, message)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "clear_logs":
            self.action_clear()
        elif event.button.id == "export_logs":
            self.action_export()

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle filter changes"""
        if event.select.id == "log_level_filter":
            log_viewer = self.query_one("#log_viewer", LogViewer)
            log_viewer.filter_level = event.value

    def action_clear(self) -> None:
        """Clear logs"""
        log_viewer = self.query_one("#log_viewer", LogViewer)
        log_viewer.log_lines.clear()
        log_viewer._update_display()
        self.app.notify("Logs cleared", severity="information")

    def action_export(self) -> None:
        """Export logs to file"""
        # TODO: Implement export
        self.app.notify("Export not implemented yet", severity="warning")

    def action_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_help(self) -> None:
        """Show help"""
        self.app.notify("C: Clear | Esc: Back", severity="information")