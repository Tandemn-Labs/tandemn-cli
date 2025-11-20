from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
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
        layout: vertical;
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
        height: auto;
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

    def __init__(self, files: list, user_id: str, api, **kwargs) -> None:
        super().__init__(**kwargs)
        self.files = files
        self.user_id = user_id
        self.api = api
        self.selected_file = None

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
            
            yield Static("Select a file to enable actions", id="selected-file")
            
            with Horizontal(id="button-row"):
                yield Button("📥 Download", id="btn-download", variant="success", disabled=True)
                yield Button("🗑️ Delete", id="btn-delete", variant="error", disabled=True)
                yield Button("Close", id="btn-close", variant="default")

    @on(ListView.Selected)
    def on_file_selected(self, event: ListView.Selected) -> None:
        """Handle file selection."""
        item = event.item
        if hasattr(item, 'file_path'):
            self.selected_file = item.file_path
            filename = item.file_path.split("/")[-1]
            self.query_one("#selected-file").update(f"Selected: {filename}")
            self.query_one("#btn-download", Button).disabled = False
            self.query_one("#btn-delete", Button).disabled = False

    @on(Button.Pressed, "#btn-download")
    @work
    async def handle_download(self) -> None:
        """Download selected file."""
        if not self.selected_file:
            return
        
        filename = self.selected_file.split("/")[-1]
        save_path = Path.home() / "Downloads" / filename
        
        try:
            self.query_one("#selected-file").update(f"⬇️ Downloading {filename}...")
            await self.api.download_file(self.user_id, self.selected_file, str(save_path))
            self.query_one("#selected-file").update(f"✅ Downloaded to {save_path}")
        except Exception as e:
            self.query_one("#selected-file").update(f"❌ Download failed: {e}")

    @on(Button.Pressed, "#btn-delete")
    @work
    async def handle_delete(self) -> None:
        """Delete selected file."""
        if not self.selected_file:
            return
        
        filename = self.selected_file.split("/")[-1]
        
        try:
            self.query_one("#selected-file").update(f"🗑️ Deleting {filename}...")
            await self.api.delete_file(self.user_id, self.selected_file)
            
            # Remove from UI
            list_view = self.query_one(ListView)
            for item in list_view.children:
                if hasattr(item, 'file_path') and item.file_path == self.selected_file:
                    await item.remove()
                    break
            
            self.selected_file = None
            self.query_one("#selected-file").update(f"✅ Deleted {filename}")
            self.query_one("#btn-download", Button).disabled = True
            self.query_one("#btn-delete", Button).disabled = True
            
            # Update count
            remaining = len(list(list_view.children))
            self.query_one("#header").update(f"📁 Your Files ({remaining})")
        except Exception as e:
            self.query_one("#selected-file").update(f"❌ Delete failed: {e}")

    @on(Button.Pressed, "#btn-close")
    def handle_close(self) -> None:
        """Close the screen."""
        self.dismiss()

    def action_close(self) -> None:
        """Close action for key bindings."""
        self.dismiss()

