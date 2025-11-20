from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Set, List

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Footer, Header, Label, Static, ListView, ListItem


class FileBrowserScreen(ModalScreen[List[Path]]):
    """
    A modal screen for browsing and selecting multiple files.
    Returns the selected file paths or None if cancelled.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+c", "cancel", "Cancel"),
        ("backspace", "go_up", "Go Up"),
    ]

    DEFAULT_CSS = """
    FileBrowserScreen {
        background: $surface;
    }

    #browser-container {
        width: 95%;
        height: 95%;
        background: #020617;
        border: round #7dd3fc;
        margin: 1;
        layout: horizontal;
    }
    
    #left-pane {
        width: 70%;
        height: 100%;
        border-right: solid #334155;
        layout: vertical;
    }

    #right-pane {
        width: 30%;
        height: 100%;
        layout: vertical;
        background: #0f172a;
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
        margin-bottom: 1;
    }
    
    #tree-container {
        height: 1fr;
        padding: 0 1;
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
    
    #selection-header {
        text-align: center;
        padding: 1;
        background: #1e293b;
        color: #22c55e;
        text-style: bold;
    }
    
    #selection-list {
        height: 1fr;
        padding: 1;
    }
    
    ListItem {
        padding: 1;
        background: #0f172a;
    }
    
    ListItem:hover {
        background: #1e293b;
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
        # Default to home directory or cwd
        if not start_path:
            # Try to get home directory, fallback to CWD
            try:
                self.current_path = Path.home()
            except:
                self.current_path = Path.cwd()
        else:
            self.current_path = Path(start_path)
            
        self.selected_files: Set[Path] = set()

    def compose(self) -> ComposeResult:
        """Create the file browser layout."""
        with Horizontal(id="browser-container"):
            # Left Pane: Navigation
            with Vertical(id="left-pane"):
                with Horizontal(id="header-row"):
                    yield Static("📁 Browser", id="title")
                    yield Button("⬆ Up", id="btn-up", variant="primary", classes="-compact")
                
                yield Label(f"Path: {self.current_path}", id="current-path")
                
                with VerticalScroll(id="tree-container"):
                    yield DirectoryTree(str(self.current_path), id="dir-tree")
                
                with Horizontal(id="button-row"):
                    yield Button("Upload Selected", id="btn-select", variant="success", disabled=True)
                    yield Button("Cancel", id="btn-cancel", variant="error")

            # Right Pane: Selection List
            with Vertical(id="right-pane"):
                yield Static("Selected Files", id="selection-header")
                yield ListView(id="selection-list")

    def on_mount(self) -> None:
        """Focus the directory tree when mounted."""
        self.query_one(DirectoryTree).focus()

    @on(DirectoryTree.FileSelected)
    def on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection (toggle)."""
        path = event.path
        
        if path in self.selected_files:
            self.selected_files.remove(path)
        else:
            self.selected_files.add(path)
        
        self._update_selection_ui()

    @on(DirectoryTree.DirectorySelected)
    def on_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Update path display when entering a directory."""
        # DirectoryTree handles traversal internally, we just update the label
        # Note: DirectoryTree expands, it doesn't "enter" in the sense of changing root.
        # But if we wanted to change root:
        # self.current_path = event.path
        # self.query_one(DirectoryTree).path = str(event.path) # (Re-mount/reload needed usually)
        pass

    @on(Button.Pressed, "#btn-up")
    def action_go_up(self) -> None:
        """Go to parent directory."""
        parent = self.current_path.parent
        if parent != self.current_path:
            self.current_path = parent
            # Re-mount directory tree at new path
            tree = self.query_one(DirectoryTree)
            tree.path = str(self.current_path)
            tree.reload()
            self.query_one("#current-path").update(f"Path: {self.current_path}")

    def _update_selection_ui(self) -> None:
        """Update the right pane list view."""
        list_view = self.query_one("#selection-list", ListView)
        list_view.clear()
        
        for path in self.selected_files:
            list_view.append(ListItem(Label(path.name)))
        
        # Enable/disable select button
        has_selection = len(self.selected_files) > 0
        self.query_one("#btn-select", Button).disabled = not has_selection
        self.query_one("#selection-header").update(f"Selected Files ({len(self.selected_files)})")

    @on(Button.Pressed, "#btn-select")
    def handle_select(self) -> None:
        """Return the selected file paths."""
        if self.selected_files:
            self.dismiss(list(self.selected_files))

    @on(Button.Pressed, "#btn-cancel")
    def handle_cancel(self) -> None:
        """Cancel without selecting."""
        self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel action for key bindings."""
        self.dismiss(None)
