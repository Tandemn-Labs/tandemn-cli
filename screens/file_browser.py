from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Footer, Header, Label, Static


class FileBrowserScreen(ModalScreen[Optional[str]]):
    """
    A modal screen for browsing and selecting files.
    Returns the selected file path or None if cancelled.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+c", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    FileBrowserScreen {
        background: $surface;
    }

    #browser-container {
        width: 90%;
        height: 90%;
        background: #020617;
        border: round #7dd3fc;
        margin: 1;
    }

    #header-row {
        height: 3;
        padding: 1;
        background: #1e293b;
        border-bottom: solid #334155;
    }

    #title {
        color: #e5e7eb;
        text-style: bold;
    }

    #current-path {
        color: #94a3b8;
        padding: 0 2;
    }

    #tree-container {
        height: 1fr;
        padding: 1;
        background: #020617;
    }

    DirectoryTree {
        background: #020617;
        color: #e5e7eb;
    }

    #button-row {
        height: 4;
        padding: 1;
        background: #1e293b;
        border-top: solid #334155;
        align: center middle;
    }

    #selected-file {
        color: #22c55e;
        padding: 0 2;
        text-overflow: ellipsis;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, start_path: str = None) -> None:
        """Initialize the file browser.
        
        Args:
            start_path: Starting directory path. Defaults to current directory.
        """
        super().__init__()
        self.start_path = Path(start_path) if start_path else Path.cwd()
        self.selected_file: Optional[Path] = None

    def compose(self) -> ComposeResult:
        """Create the file browser layout."""
        with VerticalScroll(id="browser-container"):
            # Header with title
            with Horizontal(id="header-row"):
                yield Static("📁 Select a File to Upload", id="title")
            
            # Current path display
            yield Label(f"Path: {self.start_path}", id="current-path")
            
            # File tree
            with VerticalScroll(id="tree-container"):
                yield DirectoryTree(str(self.start_path))
            
            # Selected file display
            yield Static("No file selected", id="selected-file")
            
            # Button row
            with Horizontal(id="button-row"):
                yield Button("Select", id="btn-select", variant="success", disabled=True)
                yield Button("Cancel", id="btn-cancel", variant="error")

    def on_mount(self) -> None:
        """Focus the directory tree when mounted."""
        self.query_one(DirectoryTree).focus()

    @on(DirectoryTree.FileSelected)
    def on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection in the tree."""
        self.selected_file = event.path
        relative_path = self._get_relative_path(event.path)
        
        # Update UI
        self.query_one("#selected-file").update(f"✓ Selected: {relative_path}")
        self.query_one("#btn-select", Button).disabled = False
        
        # Update current path display
        self.query_one("#current-path").update(f"Path: {event.path.parent}")

    @on(DirectoryTree.DirectorySelected)
    def on_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle directory selection in the tree."""
        # Update current path display
        self.query_one("#current-path").update(f"Path: {event.path}")
        
        # Clear file selection
        self.selected_file = None
        self.query_one("#selected-file").update("No file selected")
        self.query_one("#btn-select", Button).disabled = True

    @on(Button.Pressed, "#btn-select")
    def handle_select(self) -> None:
        """Return the selected file path."""
        if self.selected_file:
            relative_path = self._get_relative_path(self.selected_file)
            self.dismiss(str(relative_path))

    @on(Button.Pressed, "#btn-cancel")
    def handle_cancel(self) -> None:
        """Cancel without selecting."""
        self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel action for key bindings."""
        self.dismiss(None)

    def _get_relative_path(self, path: Path) -> str:
        """Get relative path from current working directory."""
        try:
            return str(path.relative_to(Path.cwd()))
        except ValueError:
            # If not relative to cwd, return absolute path
            return str(path)
