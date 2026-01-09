from __future__ import annotations

import json
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea, Static


class JsonEditorScreen(ModalScreen[Optional[dict]]):
    """
    Modal screen for viewing and editing JSON config.
    User can review and modify the config before submission.
    """

    DEFAULT_CSS = """
    JsonEditorScreen {
        align: center middle;
    }

    #editor-container {
        width: 90%;
        height: 90%;
        background: #1e293b;
        border: thick #3b82f6;
        padding: 1 2;
    }

    #editor-title {
        color: #60a5fa;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #editor-description {
        color: #94a3b8;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #json-textarea {
        width: 100%;
        height: 1fr;
        margin-bottom: 1;
        border: solid #475569;
    }

    #json-textarea:focus {
        border: solid #3b82f6;
    }

    #status-label {
        color: #94a3b8;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #status-label.error {
        color: #ef4444;
    }

    #status-label.success {
        color: #22c55e;
    }

    #button-container {
        width: 100%;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, config_data: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config_data = config_data
        self.json_text = json.dumps(config_data, indent=2)

    def compose(self) -> ComposeResult:
        """Create the editor layout."""
        with Container(id="editor-container"):
            yield Label("Review & Edit Job Configuration", id="editor-title")
            yield Static(
                "Review the configuration below. You can edit it before confirming.",
                id="editor-description"
            )
            yield TextArea(
                self.json_text,
                id="json-textarea",
                language="json",
                theme="dracula",
                show_line_numbers=True,
            )
            yield Label("", id="status-label")
            with Horizontal(id="button-container"):
                yield Button("✅ Confirm", id="btn-confirm", variant="success")
                yield Button("❌ Cancel", id="btn-cancel", variant="error")

    def on_mount(self) -> None:
        """Focus the textarea when modal opens."""
        self.query_one("#json-textarea", TextArea).focus()

    @on(TextArea.Changed, "#json-textarea")
    def handle_text_changed(self, event: TextArea.Changed) -> None:
        """Validate JSON as user types."""
        text = event.text_area.text
        status_label = self.query_one("#status-label", Label)
        
        try:
            json.loads(text)
            status_label.update("✓ Valid JSON")
            status_label.remove_class("error")
            status_label.add_class("success")
        except json.JSONDecodeError as e:
            status_label.update(f"✗ Invalid JSON: {str(e)}")
            status_label.remove_class("success")
            status_label.add_class("error")

    @on(Button.Pressed, "#btn-confirm")
    def handle_confirm(self) -> None:
        """Validate and return the edited JSON."""
        textarea = self.query_one("#json-textarea", TextArea)
        text = textarea.text.strip()
        
        try:
            parsed_data = json.loads(text)
            self.dismiss(parsed_data)
        except json.JSONDecodeError as e:
            self.notify(f"Invalid JSON: {str(e)}", severity="error")

    @on(Button.Pressed, "#btn-cancel")
    def handle_cancel(self) -> None:
        """Cancel without saving."""
        self.dismiss(None)

    def action_cancel(self) -> None:
        """Handle escape key."""
        self.dismiss(None)


