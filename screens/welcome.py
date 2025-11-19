from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Static

from models.login import Session


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
   @@@@@@         @@@      @@@@      @@@@    @@@       @@@@  @@@@      @@@@@   @@@@     @@@@   @@@       @@       @@@  @@@       @@@@                 
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
            
        yield Footer()

