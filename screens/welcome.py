from __future__ import annotations

import asyncio
import json 
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from models.login import Session
from screens.file_browser import FileBrowserScreen
from screens.file_list import FileListScreen
from screens.prompt_modal import PromptModal


class WelcomeScreen(Screen):
    """
    Welcome screen displayed after successful authentication and cluster connection.
    Shows the Tandemn ASCII logo and connection details.
    """

    BINDINGS = [("ctrl+c", "app.quit", "Quit")]

    LOGO = r"""
                                                                        @@@@                                                                          
 @@               @@@                                                   @@@@                                                                          
@@@@@@            @@@                                                   @@@@                                                                          
   @@@@@@@     @@@@@@@@@@@  @@@@@@@@@@@@@    @@@@@@@@@@@@     @@@@@@@@@@@@@@    @@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@@@   @@@@@@@@@@@@@                  
       @@@@@      @@@      @@@@      @@@@    @@@@      @@@@   @@@@     @@@@@   @@@@     @@@@   @@@@     @@@@@     @@@  @@@@@     @@@@                 
         @@@@@    @@@      @@@        @@@    @@@       @@@@  @@@        @@@@  @@@@@@@@@@@@@@@  @@@      @@@@      @@@  @@@       @@@@                 
       @@@@@      @@@     @@@         @@@    @@@       @@@@  @@@        @@@@  @@@@@@@@@@@@@@@  @@@       @@       @@@  @@@       @@@@                 
   @@@@@@         @@@      @@@@      @@@@    @@@       @@@@  @@@@      @@@@@   @@@@            @@@       @@       @@@  @@@       @@@@                 
@@@@@@             @@@@@@@  @@@@@@@@@@@@@    @@@       @@@@   @@@@@@@@@@@@@@   @@@@@@@@@@@@    @@@       @@       @@@  @@@       @@@@ ****************
 @@                 @@@@@@    @@@@@@@ @@@    @@@       @@@@     @@@@@@@  @@@      @@@@@@@      @@@       @@       @@@  @@@       @@@@  ************** 
    """

    DEFAULT_CSS = """
    WelcomeScreen {
        background: #121826;
        color: $text;
    }

    #welcome-container {
        width: 100%;
        height: 100%;
        layout: vertical;
        align: center middle;
    }

    #logo {
        color: #7dd3fc;
        text-align: center;
        width: 100%;
        margin-bottom: 2;
    }

    #welcome-text {
        color: #22c55e;
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }

    #cluster-info {
        color: #e5e7eb;
        text-align: center;
        width: 100%;
        margin-bottom: 2;
    }
    
    #button-row {
        width: 100%;
        height: auto;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    
    #selected-path {
        color: #94a3b8;
        text-align: center;
        width: 100%;
        margin: 1;
        padding: 1;
        border: round #334155;
        background: #0f172a;
    }
    """

    def __init__(self, session: Session, **kwargs) -> None:
        super().__init__(**kwargs)
        self.session = session

    def compose(self) -> ComposeResult:
        """Create the welcome screen layout."""
        with VerticalScroll(id="welcome-container"):
            yield Static(self.LOGO, id="logo")
            yield Static("✓ Authenticated - Welcome to Tandemn!", id="welcome-text")
            
            # Get cluster name from session
            cluster_name = "Tandemn"
            if self.session.clusters and len(self.session.clusters) > 0:
                cluster_name = self.session.clusters[0].name
            
            yield Static(f"Connected to [b]{cluster_name}[/b] cluster", id="cluster-info")
            
            # Add button row
            with Horizontal(id="button-row"):
                yield Button("📤 UPLOAD", id="btn-upload", variant="success")
                yield Button("📁 FILES", id="btn-files", variant="primary")
                yield Button("✨ SUBMIT", id="btn-submit", variant="warning")
            
            # Selected file path display
            yield Static("No file selected", id="selected-path")
            
        yield Footer()
    
    async def update_upload_status(self, message: str, remaining: int):
        """Callback for upload progress updates."""
        if remaining > 0:
            self.query_one("#selected-path").update(f"{message} | {remaining} files remaining")
        else:
            self.query_one("#selected-path").update(f"{message} | All uploads complete! ✨")
    
    @on(Button.Pressed, "#btn-files")
    @work
    async def handle_files(self) -> None:
        """Open file list screen."""
        user_id = self.session.user_id
        if not user_id:
            self.query_one("#selected-path").update("Error: User ID missing")
            return
        
        try:
            # Fetch files from storage
            result = await self.app.api.list_files(user_id)
            files = result.get("files", [])
            
            if not files:
                self.query_one("#selected-path").update("No files found in storage")
                return
            
            # Show file list screen with user_id and api
            await self.app.push_screen_wait(FileListScreen(files, user_id, self.app.api))
        except Exception as e:
            self.query_one("#selected-path").update(f"Error loading files: {e}")
            self.log(f"Error loading files: {e}")
    
    @on(Button.Pressed, "#btn-upload")
    @work
    async def handle_upload(self) -> None:
        """Open file browser and show selected path."""
        # Push the file browser screen and wait for result
        files = await self.app.push_screen_wait(FileBrowserScreen())
        
        if files:
            count = len(files)
            self.query_one("#selected-path").update(f"🚀 Uploading {count} files...")
            
            # Start upload
            from utils.storage_manager import UploadManager
            # Ensure API is set on singleton or passed. self.app.api is available on TandemnCLIApp
            manager = UploadManager(self.app.api) 
            manager.set_callback(self.update_upload_status)  # Set progress callback
            
            # Use user_id from session
            user_id = self.session.user_id
            if not user_id:
                self.query_one("#selected-path").update("Error: User ID missing from session")
                self.log("Error: User ID missing from session")
                return
                
            await manager.add_files(files, user_id)
            
            self.query_one("#selected-path").update(f"✅ Uploading {count} files in background")
            self.log(f"Started upload for {count} files")
        else:
            # User cancelled
            self.query_one("#selected-path").update("No file selected")
            self.log("File selection cancelled")
    
    @on(Button.Pressed, "#btn-submit")
    @work
    async def handle_submit_prompt(self) -> None:
        """Open prompt modal for solver submission."""
        # Push the prompt modal and wait for result
        prompt_text = await self.app.push_screen_wait(PromptModal())
        
        if prompt_text:
            self.query_one("#selected-path").update(f"📝 Processing prompt: {prompt_text[:50]}...")
            self.log(f"Received prompt: {prompt_text}")
            
            # Get user_id from session
            user_id = self.session.user_id
            if not user_id:
                self.query_one("#selected-path").update("Error: User ID missing from session")
                self.notify("User ID is required", severity="error")
                return
            
            # Call the solver API
            # NOTE: Implement this endpoint on the server side before using
            result = await self.app.api.submit_solver_prompt(prompt_text, user_id)
            
            # Display result
            if result.get("success"):
                config = result.get("config", {})
                self.query_one("#selected-path").update(
                    f"✅ Solver returned config: {config.get('meta', {}).get('description', 'N/A')}"
                )
                self.notify("Prompt processed successfully!", severity="information")
                self.log(f"Solver result: {json.dumps(result, indent=4)}")
            else:
                error_msg = result.get("error", "Unknown error")
                self.query_one("#selected-path").update(f"❌ Solver error: {error_msg}")
                self.notify(f"Solver error: {error_msg}", severity="error")
                
        else:
            # User cancelled
            self.query_one("#selected-path").update("Prompt submission cancelled")
            self.log("Prompt submission cancelled")

