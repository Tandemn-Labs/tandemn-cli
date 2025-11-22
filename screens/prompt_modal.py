from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea, Static
from textual.reactive import reactive


class PromptModal(ModalScreen):
    """
    Modal screen for submitting prompts to the solver API.
    
    Features:
    - Text area with 500 character limit
    - Character counter display
    - Submit button and Enter key support
    - Cancel/Escape to dismiss
    """

    DEFAULT_CSS = """
    PromptModal {
        align: center middle;
    }

    #modal-container {
        width: 80;
        height: auto;
        background: #1e293b;
        border: thick #3b82f6;
        padding: 1 2;
    }

    #modal-title {
        color: #60a5fa;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #modal-description {
        color: #94a3b8;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #prompt-textarea {
        width: 100%;
        height: 12;
        margin-bottom: 1;
        border: solid #475569;
    }

    #prompt-textarea:focus {
        border: solid #3b82f6;
    }

    #char-counter {
        color: #94a3b8;
        text-align: right;
        width: 100%;
        margin-bottom: 1;
    }

    #char-counter.warning {
        color: #fb923c;
    }

    #char-counter.error {
        color: #ef4444;
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

    char_count: reactive[int] = reactive(0)
    MAX_CHARS = 500

    def compose(self) -> ComposeResult:
        """Create the modal layout."""
        with Container(id="modal-container"):
            yield Label("Submit Prompt to Solver", id="modal-title")
            yield Static(
                "Describe your job requirements (max 500 characters)",
                id="modal-description"
            )
            yield TextArea(
                id="prompt-textarea",
                language="markdown",
                theme="dracula",
                show_line_numbers=False,
            )
            yield Label(f"0 / {self.MAX_CHARS} characters", id="char-counter")
            with Horizontal(id="button-container"):
                yield Button("Submit", id="btn-submit", variant="success")
                yield Button("Cancel", id="btn-cancel", variant="default")

    def on_mount(self) -> None:
        """Focus the textarea when modal opens."""
        self.query_one("#prompt-textarea", TextArea).focus()

    @on(TextArea.Changed, "#prompt-textarea")
    def handle_text_changed(self, event: TextArea.Changed) -> None:
        """Update character counter when text changes."""
        text = event.text_area.text
        self.char_count = len(text)
        
        counter_label = self.query_one("#char-counter", Label)
        counter_label.update(f"{self.char_count} / {self.MAX_CHARS} characters")
        
        # Update counter color based on character count
        counter_label.remove_class("warning", "error")
        if self.char_count > self.MAX_CHARS:
            counter_label.add_class("error")
        elif self.char_count > self.MAX_CHARS * 0.9:  # 90% threshold
            counter_label.add_class("warning")

    @on(Button.Pressed, "#btn-submit")
    def handle_submit(self) -> None:
        """Handle submit button press."""
        textarea = self.query_one("#prompt-textarea", TextArea)
        text = textarea.text.strip()
        
        # Validate input
        if not text:
            # Show error feedback
            self.notify("Please enter a prompt", severity="warning")
            return
        
        if len(text) > self.MAX_CHARS:
            # Show error feedback
            self.notify(
                f"Prompt exceeds {self.MAX_CHARS} character limit",
                severity="error"
            )
            return
        
        # Return the prompt text and dismiss modal
        self.dismiss(text)

    @on(Button.Pressed, "#btn-cancel")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        self.dismiss(None)

    def action_cancel(self) -> None:
        """Handle escape key."""
        self.dismiss(None)

