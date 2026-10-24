"""Configuration Screen - Manage rules and options"""


from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Select

from ...application.config_service import ConfigService
from ...application.organizer_service import OrganizerService
from ...domain.models import AppConfig, FileRule
from ..widgets import RuleEditor


class ConfigScreen(Screen):
    """Configuration screen"""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back", "Back"),
        Binding("f1", "help", "Help"),
        Binding("ctrl+s", "save", "Save"),
        Binding("n", "new_rule", "New Rule"),
    ]

    def __init__(self, config: AppConfig, config_service: ConfigService, organizer_service: OrganizerService, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.config_service = config_service
        self.organizer_service = organizer_service
        self.rules_container = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="config_container"):
            # Global options
            with Vertical(id="global_options"):
                yield Label("Global Options", classes="section-title")
                with Horizontal():
                    yield Checkbox("Create date subfolders (YYYY-MM)", value=self.config.options.create_subfolders_by_date, id="opt_date_folders")
                    yield Input(value=self.config.options.date_format, placeholder="Date format", id="opt_date_format")
                with Horizontal():
                    yield Select(
                        [("Rename", "rename"), ("Skip", "skip"), ("Overwrite", "overwrite")],
                        value=self.config.options.handle_duplicates.value,
                        id="opt_duplicates"
                    )
                    yield Label("Duplicate handling")
                with Horizontal():
                    yield Checkbox("Recursive scan", value=self.config.options.recursive, id="opt_recursive")
                    yield Input(value=str(self.config.options.min_file_size), placeholder="Min size (bytes)", id="opt_min_size")
                    yield Input(value=str(self.config.options.max_file_size) if self.config.options.max_file_size else "", placeholder="Max size (bytes)", id="opt_max_size")

            # Watch options
            with Vertical(id="watch_options"):
                yield Label("Watch Options", classes="section-title")
                with Horizontal():
                    yield Checkbox("Enable watch mode", value=self.config.watch.enabled, id="opt_watch_enabled")
                    yield Input(value=str(self.config.watch.debounce_seconds), placeholder="Debounce (seconds)", id="opt_debounce")

            # Rules
            with Vertical(id="rules_section"):
                yield Label("Classification Rules", classes="section-title")
                with Horizontal():
                    yield Button("Add Rule (N)", variant="primary", id="add_rule")
                    yield Button("Reset to Defaults", variant="warning", id="reset_rules")
                yield ScrollableContainer(id="rules_container")

            # Action buttons
            with Horizontal(id="config_actions"):
                yield Button("Save (Ctrl+S)", variant="success", id="save_config")
                yield Button("Cancel (Esc)", variant="default", id="cancel_config")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen with current rules"""
        self.rules_container = self.query_one("#rules_container", ScrollableContainer)
        self._refresh_rules()

    def _refresh_rules(self) -> None:
        """Refresh rules display"""
        self.rules_container.remove_children()
        for rule in self.config.rules:
            editor = RuleEditor(rule=rule)
            self.rules_container.mount(editor)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        btn_id = event.button.id

        if btn_id == "add_rule":
            self.action_new_rule()
        elif btn_id == "reset_rules":
            self.action_reset_rules()
        elif btn_id == "save_config":
            self.action_save()
        elif btn_id == "cancel_config":
            self.action_back()

    async def on_rule_editor_save_requested(self, event) -> None:
        """Handle rule save request"""
        editor = event.sender
        rule_data = editor.get_rule_data()

        # Validate
        errors = self.config_service.get_rules_engine().validate_rule(
            FileRule(**rule_data)
        )
        if errors:
            self.app.notify("\n".join(errors), severity="error")
            return

        # Update or create rule
        if editor.rule:
            self.config_service.get_rules_engine().update_rule(editor.rule.category, **rule_data)
        else:
            self.config_service.get_rules_engine().add_rule(FileRule(**rule_data))

        self._refresh_rules()
        self.organizer_service.refresh_config(self.config)
        self.app.notify("Rule saved", severity="information")

    async def on_rule_editor_delete_requested(self, event) -> None:
        """Handle rule delete request"""
        editor = event.sender
        if editor.rule:
            self.config_service.get_rules_engine().remove_rule(editor.rule.category)
            self._refresh_rules()
            self.organizer_service.refresh_config(self.config)
            self.app.notify("Rule deleted", severity="information")

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes"""
        if event.checkbox.id == "opt_date_folders":
            self.config.options.create_subfolders_by_date = event.value
        elif event.checkbox.id == "opt_recursive":
            self.config.options.recursive = event.value
        elif event.checkbox.id == "opt_watch_enabled":
            self.config.watch.enabled = event.value

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes"""
        if event.input.id == "opt_date_format":
            self.config.options.date_format = event.value
        elif event.input.id == "opt_min_size":
            try:
                self.config.options.min_file_size = int(event.value) if event.value else 0
            except ValueError:
                pass
        elif event.input.id == "opt_max_size":
            try:
                self.config.options.max_file_size = int(event.value) if event.value else None
            except ValueError:
                pass
        elif event.input.id == "opt_debounce":
            try:
                self.config.watch.debounce_seconds = float(event.value)
            except ValueError:
                pass

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes"""
        if event.select.id == "opt_duplicates":
            from ...domain.models import DuplicateHandling
            self.config.options.handle_duplicates = DuplicateHandling(event.value)

    def action_new_rule(self) -> None:
        """Add new rule"""
        editor = RuleEditor()
        self.rules_container.mount(editor)
        editor.focus()

    def action_reset_rules(self) -> None:
        """Reset rules to defaults"""
        self.config_service.reset_to_defaults()
        self._refresh_rules()
        self.organizer_service.refresh_config(self.config)
        self.app.notify("Rules reset to defaults", severity="information")

    def action_save(self) -> None:
        """Save configuration"""
        if self.config_service.save():
            self.app.notify("Configuration saved", severity="information")
        else:
            self.app.notify("Failed to save configuration", severity="error")

    def action_back(self) -> None:
        """Go back to dashboard"""
        self.app.switch_screen("dashboard")

    def action_help(self) -> None:
        """Show help"""
        self.app.notify("N: New Rule | Ctrl+S: Save | Esc: Back", severity="information")