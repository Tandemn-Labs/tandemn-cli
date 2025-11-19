from __future__ import annotations

import asyncio
from typing import Optional

from textual import on
from textual.app import App
from textual.binding import Binding

from api import TandemnAPI, Session
from screens.login import LoginScreen
# import logging

# # Configure logging to write to a file
# logging.basicConfig(
#     level=logging.INFO,
#     filename="debug.log",
#     filemode="w",
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )

# # Enable verbose logging for httpx to see request/response details
# logging.getLogger("httpx").setLevel(logging.DEBUG)
# logging.getLogger("httpcore").setLevel(logging.DEBUG)

class TandemnCLIApp(App[None]):
    """
    Entry point for Tandemn CLI (Textual).
    RN only the login screen is implemented. 
    """

    CSS_PATH = None  # We embed CSS in the LoginScreen for now.
    TITLE = "Tandemn CLI"
    SUB_TITLE = "Embrace the Heterogenous Future"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
    ]

    api: TandemnAPI
    session: Optional[Session] = None

    def __init__(self, api_base_url: str = "https://api.tandemn.com/api/cli") -> None:
        super().__init__()
        # make the tandemn api based on the base url that is provided
        self.api = TandemnAPI(api_base_url)

    async def on_mount(self) -> None:
        """
        Called when the app is ready. Here we push the LoginScreen so it
        becomes the active screen and renders its UI.
        """
        login = LoginScreen(id="login")
        login.set_api(self.api)
        await self.push_screen(login)

    @on(LoginScreen.LoggedIn)
    async def handle_logged_in(self, message: LoginScreen.LoggedIn) -> None:
        """Called when login + cluster selection succeeded."""
        self.session = message.session
        # For now just log to console; later you can switch screens.
        self.log(
            f"Session established: cluster={self.session.clusters}, "
            f"token_expires={self.session.expires_at}"
        )

    async def on_shutdown(self) -> None:
        await self.api.aclose()


if __name__ == "__main__":
    # asyncio.run(TandemnCLIApp().run_async())
    TandemnCLIApp().run()