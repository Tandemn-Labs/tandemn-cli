from __future__ import annotations

import asyncio
import json 
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from models.login import Session
from models.solver import JobConfig, SendToCentralServerRequestBatched
from screens.file_browser import FileBrowserScreen
from screens.file_list import FileListScreen
from screens.prompt_modal import PromptModal
from screens.json_editor import JsonEditorScreen


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
            # yield Static("Welcome to Tandemn!", id="welcome-text")
            
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
            # Check if any files were skipped during validation
            skipped = getattr(self, '_skipped_count', 0)
            if skipped > 0:
                self.query_one("#selected-path").update(f"All uploads complete! ⚠️ {skipped} file(s) skipped")
            else:
                self.query_one("#selected-path").update(f"All uploads complete!")
    
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
            result = await self.app.api.list_files(self.session.session_token)
            files = result.get("files", [])
            
            if not files:
                self.query_one("#selected-path").update("No files found in storage")
                return
            
            # Show file list screen with user_id and api
            await self.app.push_screen_wait(FileListScreen(files, self.session.session_token, self.app.api))
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
            self.query_one("#selected-path").update(f"🔍 Validating {count} files...")
            
            # Start upload
            from utils.storage_manager import UploadManager
            manager = UploadManager(self.app.api) 
            manager.set_callback(self.update_upload_status)
            
            # Use user_id from session
            session_token = self.session.session_token
            if not session_token:
                self.query_one("#selected-path").update("Error: User ID missing from session")
                self.log("Error: User ID missing from session")
                return
            
            # Add files and get validation result
            result = await manager.add_files(files, session_token)
            
            queued = result["queued"]
            skipped = result["skipped"]
            self._skipped_count = len(skipped)  # Store for callback
            
            # Show appropriate message based on result
            if skipped and not queued:
                # All files failed validation
                errors = "; ".join([f"{name}: {reason}" for name, reason in skipped])
                self.query_one("#selected-path").update(f"❌ Not uploading - invalid JSONL: {errors}")
                self.notify(f"Validation failed for {len(skipped)} file(s)", severity="error")
            elif skipped:
                # Some files skipped, some queued
                self.query_one("#selected-path").update(
                    f"⚠️ Uploading {len(queued)} files | Skipped {len(skipped)} invalid files"
                )
                self.notify(f"Some files skipped, some queued", severity="warning")
                for name, reason in skipped:
                    self.log(f"Skipped {name}: {reason}")
            else:
                # All files queued successfully
                self.query_one("#selected-path").update(f"✅ Uploading {len(queued)} files in background")
            
            self.log(f"Upload result: {len(queued)} queued, {len(skipped)} skipped")
        else:
            # User cancelled
            self.query_one("#selected-path").update("No file selected")
            self.log("File selection cancelled")
    
    @on(Button.Pressed, "#btn-submit")
    @work
    async def handle_submit_prompt(self) -> None:
        """Open prompt modal for solver submission."""
        # Push the prompt modal and wait for result
        result = await self.app.push_screen_wait(PromptModal())
        
        if not result:
            self.query_one("#selected-path").update("Prompt submission cancelled")
            self.log("Prompt submission cancelled")
            return
            
        # Get config and selected file
        config_dict = result.get("config", {})
        selected_file = result.get("selected_file")
        task_type = config_dict.get("task", {}).get("type", "")
        
        # If batched_inference and file selected, reconstruct JobConfig and show editor
        if task_type == "batched_inference" and selected_file:
            try:
                # Reconstruct JobConfig from the solver response
                job_config = JobConfig(**config_dict)
                
                # Create SendToCentralServerRequestBatched
                batch_request = SendToCentralServerRequestBatched(
                    job_config=job_config,
                    selected_file=selected_file,
                    user_id=self.session.user_id
                )
                
                # Convert to dict for JSON editor
                batch_request_dict = batch_request.model_dump()
                
                # Open JSON editor for user review
                edited_config = await self.app.push_screen_wait(
                    JsonEditorScreen(batch_request_dict)
                )
                
                if edited_config:
                    # User confirmed the config
                    description = edited_config.get("job_config", {}).get("meta", {}).get("description", "N/A")
                    filename = edited_config.get("selected_file", "").split('/')[-1]
                    
                    status_msg = f"✅ Config confirmed: {description} | File: {filename}"
                    self.query_one("#selected-path").update(status_msg)
                    self.notify("Config ready to submit!", severity="information")
                    
                    # Pretty print to console
                    print(f"\n{'='*80}")
                    print(f"BATCHED INFERENCE JOB CONFIG:")
                    print(json.dumps(edited_config, indent=2))
                    print(f"{'='*80}\n")
                    
                    # TODO: Send to central server API
                    # await self.app.api.submit_batched_job(edited_config)
                    
                else:
                    self.query_one("#selected-path").update("Config editing cancelled")
                    self.log("Config editing cancelled")
                    
            except Exception as e:
                error_msg = f"Error processing config: {str(e)}"
                self.query_one("#selected-path").update(error_msg)
                self.notify(error_msg, severity="error")
                self.log(error_msg)
        else:
            # Not batched inference or no file selected
            description = config_dict.get('meta', {}).get('description', 'N/A')
            status_msg = f"✅ Config ready: {description}"
            
            self.query_one("#selected-path").update(status_msg)
            self.notify("Prompt processed successfully!", severity="information")
            
            log_data = {"config": config_dict}
            self.log(f"Solver result: {json.dumps(log_data, indent=4)}")

