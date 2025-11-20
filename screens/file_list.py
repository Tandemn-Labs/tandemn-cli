from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static


class FileListScreen(ModalScreen[None]):
    """
    A modal screen for viewing all user files in storage.
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("ctrl+c", "close", "Close"),
    ]

    DEFAULT_CSS = """
    FileListScreen {
        background: $surface;
    }

    #list-container {
        width: 80%;
        height: 80%;
        background: #020617;
        border: round #7dd3fc;
        margin: 2;
    }

    #header {
        height: 3;
        padding: 1;
        background: #1e293b;
        border-bottom: solid #334155;
        text-align: center;
        color: #e5e7eb;
        text-style: bold;
    }

    #file-list {
        height: 1fr;
        padding: 1;
        background: #020617;
    }

    ListItem {
        padding: 1;
        background: #0f172a;
    }

    ListItem:hover {
        background: #1e293b;
    }

    #button-row {
        height: 3;
        padding: 1;
        background: #1e293b;
        border-top: solid #334155;
        align: center middle;
    }

    #selected-file {
        color: #22c55e;
        text-align: center;
        padding: 0 2;
    }
    """

    def __init__(self, files: list, **kwargs) -> None:
        super().__init__(**kwargs)
        self.files = files

    def compose(self) -> ComposeResult:
        """Create the file list layout."""
        with Vertical(id="list-container"):
            yield Static(f"📁 Your Files ({len(self.files)})", id="header")
            
            with VerticalScroll(id="file-list"):
                # Create ListView with items directly in compose
                items = []
                for file_path in self.files:
                    # Extract just the filename from s3:// path
                    filename = file_path.split("/")[-1] if "/" in file_path else file_path
                    item = ListItem(Label(filename))
                    item.file_path = file_path  # Store full path
                    items.append(item)
                yield ListView(*items)
            
            yield Static("Click a file to view its name", id="selected-file")
            
            with Vertical(id="button-row"):
                yield Button("Close", id="btn-close", variant="error")

    @on(ListView.Selected)
    def on_file_selected(self, event: ListView.Selected) -> None:
        """Handle file selection."""
        item = event.item
        if hasattr(item, 'file_path'):
            filename = item.file_path.split("/")[-1]
            self.query_one("#selected-file").update(f"Selected: {filename}")
            print(f"Selected file: {filename}")

    @on(Button.Pressed, "#btn-close")
    def handle_close(self) -> None:
        """Close the screen."""
        self.dismiss()

    def action_close(self) -> None:
        """Close action for key bindings."""
        self.dismiss()

