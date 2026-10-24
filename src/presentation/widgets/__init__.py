"""TUI Widgets - Reusable UI components"""

from collections.abc import Callable
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Input,
    Label,
    ProgressBar,
    Select,
    Static,
)


class FileTable(DataTable):
    """DataTable for displaying file information"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True

    def on_mount(self) -> None:
        self.add_columns("Filename", "Size", "Category", "Destination", "Status")
        self.show_header = True

    def add_file(self, file_info) -> None:
        """Add a file row to the table"""
        size_str = self._format_size(file_info.size)
        category = file_info.matched_rule.category if file_info.matched_rule else "Uncategorized"
        dest = str(file_info.destination_path) if file_info.destination_path else "—"
        status = file_info.status.capitalize()
        self.add_row(
            file_info.filename,
            size_str,
            category,
            dest,
            status,
            key=str(file_info.source_path)
        )

    def update_file_status(self, source_path: Path, status: str) -> None:
        """Update status of a file row"""
        key = str(source_path)
        if key in self.rows:
            self.update_cell(key, "Status", status.capitalize())

    def clear_files(self) -> None:
        """Clear all file rows"""
        self.clear(columns=False)

    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human readable format"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


class StatsBar(Static):
    """Progress bar with statistics"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_bar = ProgressBar(total=100, show_eta=False)
        self.stats_label = Label("")

    def compose(self) -> ComposeResult:
        yield self.progress_bar
        yield self.stats_label

    def update_progress(self, progress) -> None:
        """Update progress from OrganizeProgress"""
        if progress.total_files > 0:
            pct = (progress.processed_files / progress.total_files) * 100
            self.progress_bar.progress = pct
        else:
            self.progress_bar.progress = 0

        self.stats_label.update(
            f"Total: {progress.total_files} | "
            f"Processed: {progress.processed_files} | "
            f"Moved: {progress.moved_files} | "
            f"Skipped: {progress.skipped_files} | "
            f"Errors: {progress.error_files}"
        )

    def reset(self) -> None:
        """Reset progress bar"""
        self.progress_bar.progress = 0
        self.stats_label.update("Ready")


class PathPicker(Static):
    """Path selection widget with browse button"""

    def __init__(self, label: str, value: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_text = label
        self.value = value
        self.input_widget = Input(value=value, placeholder="Enter path...")
        self.browse_button = Button("Browse", variant="primary")

    def compose(self) -> ComposeResult:
        yield Label(self.label_text)
        with Horizontal():
            yield self.input_widget
            yield self.browse_button

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button == self.browse_button:
            self.post_message(self.BrowseRequested(self))

    class BrowseRequested(Message):
        def __init__(self, sender: "PathPicker"):
            super().__init__()
            self.sender = sender
            self.path = sender.input_widget.value

    def watch_value(self, value: str) -> None:
        self.input_widget.value = value


class RuleEditor(Static):
    """Widget for editing a single rule"""

    def __init__(self, rule=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rule = rule
        self.category_input = Input(
            value=rule.category if rule else "",
            placeholder="Category name"
        )
        self.extensions_input = Input(
            value=", ".join(rule.extensions) if rule else "",
            placeholder="Extensions (comma separated): .jpg, .png, .gif"
        )
        self.dest_picker = PathPicker("Destination", str(rule.destination) if rule else "")
        self.enabled_checkbox = Checkbox("Enabled", value=rule.enabled if rule else True)
        self.priority_input = Input(
            value=str(rule.priority) if rule else "0",
            placeholder="Priority (higher = first)"
        )
        self.save_button = Button("Save", variant="success")
        self.delete_button = Button("Delete", variant="error")

    def compose(self) -> ComposeResult:
        yield Label(f"Rule: {self.rule.category if self.rule else 'New'}")
        yield self.category_input
        yield self.extensions_input
        yield self.dest_picker
        with Horizontal():
            yield self.enabled_checkbox
            yield Label("Priority:")
            yield self.priority_input
        with Horizontal():
            yield self.save_button
            yield self.delete_button

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button == self.save_button:
            self.post_message(self.SaveRequested(self))
        elif event.button == self.delete_button:
            self.post_message(self.DeleteRequested(self))

    class SaveRequested(Message):
        def __init__(self, sender: "RuleEditor"):
            super().__init__()
            self.sender = sender

    class DeleteRequested(Message):
        def __init__(self, sender: "RuleEditor"):
            super().__init__()
            self.sender = sender

    def get_rule_data(self) -> dict:
        """Get rule data from inputs"""
        return {
            "category": self.category_input.value.strip(),
            "extensions": [e.strip().lower() for e in self.extensions_input.value.split(",") if e.strip()],
            "destination": Path(self.dest_picker.input_widget.value.strip()),
            "enabled": self.enabled_checkbox.value,
            "priority": int(self.priority_input.value) if self.priority_input.value.isdigit() else 0,
        }


class LogViewer(Static):
    """Log display widget with filtering"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_lines: list[str] = []
        self.max_lines = 1000
        self.filter_level = "INFO"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Filter:")
            yield Select([
                ("DEBUG", "DEBUG"),
                ("INFO", "INFO"),
                ("WARNING", "WARNING"),
                ("ERROR", "ERROR"),
            ], value="INFO", id="log_filter")
            yield Button("Clear", variant="default", id="clear_logs")
        yield Static("", id="log_content", classes="log-content")

    def add_log(self, level: str, message: str) -> None:
        """Add a log entry"""
        if self._should_show(level):
            timestamp = self._get_timestamp()
            self.log_lines.append(f"[{timestamp}] {level}: {message}")
            if len(self.log_lines) > self.max_lines:
                self.log_lines.pop(0)
            self._update_display()

    def _should_show(self, level: str) -> bool:
        levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        return levels.get(level, 0) >= levels.get(self.filter_level, 0)

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def _update_display(self) -> None:
        content = self.query_one("#log_content", Static)
        content.update("\n".join(self.log_lines))
        content.scroll_end(animate=False)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "log_filter":
            self.filter_level = event.value
            self._update_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "clear_logs":
            self.log_lines.clear()
            self._update_display()


class ConfirmDialog(Static):
    """Confirmation dialog"""

    def __init__(self, title: str, message: str, on_confirm: Callable, on_cancel: Callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.message = message
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

    def compose(self) -> ComposeResult:
        with Container(classes="dialog"):
            yield Label(self.title, classes="dialog-title")
            yield Label(self.message, classes="dialog-message")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Confirm", variant="error", id="confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.on_confirm()
        else:
            self.on_cancel()
        self.remove()


class InputDialog(Static):
    """Text input dialog"""

    def __init__(self, title: str, prompt: str, default: str, on_submit: Callable[[str], None], on_cancel: Callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.prompt = prompt
        self.default = default
        self.on_submit = on_submit
        self.on_cancel = on_cancel

    def compose(self) -> ComposeResult:
        with Container(classes="dialog"):
            yield Label(self.title, classes="dialog-title")
            yield Label(self.prompt, classes="dialog-message")
            yield Input(value=self.default, id="input_field")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("OK", variant="primary", id="ok")

    def on_mount(self) -> None:
        self.query_one("#input_field", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            value = self.query_one("#input_field", Input).value
            self.on_submit(value)
        else:
            self.on_cancel()
        self.remove()