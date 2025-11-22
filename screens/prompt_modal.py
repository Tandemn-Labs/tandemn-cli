from __future__ import annotations

from typing import Optional

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, TextArea, Static, LoadingIndicator
from textual.reactive import reactive


class PromptModal(ModalScreen[Optional[dict]]):
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

    #loading-container {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1;
        display: none;
    }

    #loading-container.visible {
        display: block;
    }

    #loading-status {
        color: #60a5fa;
        text-align: center;
        margin-top: 1;
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
            with Container(id="loading-container"):
                yield LoadingIndicator()
                yield Label("Processing prompt...", id="loading-status")
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
    @work
    async def handle_submit(self) -> None:
        """Handle submit button press and call API."""
        textarea = self.query_one("#prompt-textarea", TextArea)
        text = textarea.text.strip()
        
        # Validate input
        if not text:
            self.notify("Please enter a prompt", severity="warning")
            return
        
        if len(text) > self.MAX_CHARS:
            self.notify(
                f"Prompt exceeds {self.MAX_CHARS} character limit",
                severity="error"
            )
            return
        
        # Show loading indicator
        loading = self.query_one("#loading-container")
        loading.add_class("visible")
        
        # Disable buttons during API call
        submit_btn = self.query_one("#btn-submit", Button)
        cancel_btn = self.query_one("#btn-cancel", Button)
        submit_btn.disabled = True
        cancel_btn.disabled = True
        
        try:
            # Get session info from app
            session = self.app.session if hasattr(self.app, 'session') else None
            if not session or not session.user_id:
                self.notify("User ID missing from session", severity="error")
                return
            
            # Call the solver API
            result = await self.app.api.submit_solver_prompt(text, session.user_id)
            
            # Check result and dismiss with data
            if result.get("success"):
                # Check if it's batched_inference
                config = result.get("config", {})
                task_type = config.get("task", {}).get("type", "")
                
                if task_type == "batched_inference":
                    # Hide loading, keep modal open for file selection
                    loading.remove_class("visible")
                    submit_btn.disabled = False
                    cancel_btn.disabled = False
                    
                    self.notify("Detected Batched Inference - please select a file to proceed", severity="information")
                    
                    # Fetch user files and show file selector
                    try:
                        files_result = await self.app.api.list_files(session.user_id)
                        files = files_result.get("files", [])
                        
                        if not files:
                            self.notify("No files found in storage. Please upload a file first.", severity="warning")
                            self.dismiss(None)
                            return
                        
                        # Import here to avoid circular dependency
                        from screens.file_list import FileListScreen
                        
                        # Open file selector in selection mode
                        selected_file = await self.app.push_screen_wait(
                            FileListScreen(files, session.user_id, self.app.api, selection_mode=True)
                        )
                        
                        if selected_file:
                            # Add selected file to result
                            result["selected_file"] = selected_file
                            self.notify(f"File selected: {selected_file.split('/')[-1]}", severity="information")
                            self.dismiss(result)
                        else:
                            self.notify("No file selected, cancelling", severity="warning")
                            self.dismiss(None)
                    except Exception as e:
                        error_str = str(e).replace("[", "\\[").replace("{", "\\{").replace("}", "\\}")
                        self.notify(f"Error loading files: {error_str}", severity="error")
                        self.dismiss(None)
                else:
                    # Not batched_inference, return immediately
                    self.dismiss(result)
            else:
                error_msg = result.get("error", "Unknown error")
                # Escape markup characters
                escaped = error_msg.replace("[", "\\[").replace("{", "\\{").replace("}", "\\}")
                self.notify(f"Error: {escaped}", severity="error")
                self.dismiss(None)
        except Exception as e:
            error_str = str(e).replace("[", "\\[").replace("{", "\\{").replace("}", "\\}")
            self.notify(f"Error: {error_str}", severity="error")
            self.dismiss(None)
        finally:
            # Hide loading and re-enable buttons
            loading.remove_class("visible")
            submit_btn.disabled = False
            cancel_btn.disabled = False

    @on(Button.Pressed, "#btn-cancel")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        self.dismiss(None)

    def action_cancel(self) -> None:
        """Handle escape key."""
        self.dismiss(None)

