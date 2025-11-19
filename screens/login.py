from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from textual import events, on
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from api import TandemnAPI, Cluster, LoginResponse, Session


@dataclass
class AuthState:
    api_key: str = ""
    login_result: Optional[LoginResponse] = None
    session: Optional[Session] = None


class LoginScreen(Screen):
    """
    Textual UI for:
      1. Entering API key
      2. Authenticating
      3. Selecting a cluster
      4. Creating a CLI session (sessionToken)
    """

    BINDINGS = [("ctrl+c", "app.quit", "Quit")]

    DEFAULT_CSS = """
    LoginScreen {
        background: $surface;
        color: $text;
    }

    #root {
        width: 100%;
        height: 100%;
        padding: 1 2;
        layout: vertical;
        background: #121826;
    }

    #card {
        margin: 1;
        width: 80%;
        max-width: 90;
        border: round #7dd3fc;
        background: #020617;
        padding: 2 3;
        layout: vertical;
    }

    #title {
        content-align: center middle;
        color: #e5e7eb;
        text-style: bold;
        margin-bottom: 1;
    }

    #subtitle {
        content-align: center middle;
        color: #9ca3af;
        margin-bottom: 1;
    }

    Input {
        border: heavy #22c55e;
        background: #020617;
        color: #e5e7eb;
    }

    Button {
        margin-top: 1;
    }

    #login-row {
        layout: horizontal;
        height: auto;
    }

    #api-section {
        width: 1fr;
        layout: vertical;
    }

    #cluster-section {
        width: 1fr;
        layout: vertical;
    }

    #cluster-list {
        border: round #4b5563;
        height: 8;
    }

    #status {
        height: 3;
        margin-top: 1;
        color: #e5e7eb;
    }

    .ok {
        color: #22c55e;
    }

    .warn {
        color: #eab308;
    }

    .err {
        color: #f97373;
    }
    """

    class LoggedIn(Message):
        """Emitted when the user has a valid session token and cluster."""

        def __init__(self, session: Session) -> None:
            self.session = session
            super().__init__()

    state: reactive[AuthState] = reactive(AuthState())
    api: TandemnAPI | None = None

    def set_api(self, api: TandemnAPI) -> None:
        self.api = api

    def compose(self):
        yield Header(show_clock=True)
        with Container(id="root"):
            with Container(id="card"):
                yield Static("Tandemn CLI", id="title")
                yield Static(
                    "Paste your API key (as from api.tandemn.com/keys). "
                    "We'll authenticate and show clusters you can use.",
                    id="subtitle",
                )

                with Container(id="login-row"):
                    # Left: API key and login
                    with Container(id="api-section"):
                        yield Label("API Key", classes="section-label")
                        self.api_input = Input(
                            placeholder="gk-************************",
                            password=True,
                            id="api-input",
                        )
                        yield self.api_input
                        yield Button("Authenticate", id="btn-auth", variant="success")

                        self.user_info = Static("", id="user-info")
                        yield self.user_info

                    # Right: clusters
                    with Container(id="cluster-section"):
                        yield Label("Available Clusters", classes="section-label")
                        self.cluster_list = ListView(id="cluster-list")
                        yield self.cluster_list
                        yield Button(
                            "Connect to Selected Cluster",
                            id="btn-connect",
                            variant="primary",
                            disabled=True,
                        )

                self.status = Static("", id="status")
                yield self.status

        yield Footer()

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    async def on_mount(self) -> None:
        self.api_input.focus()
        self.status.update("Enter your Tandemn API key to begin.")

    @on(Button.Pressed, "#btn-auth")
    async def handle_auth_button(self) -> None:
        await self._perform_login()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-input":
            await self._perform_login()

    async def _perform_login(self) -> None:
        if not self.api:
            self.status.update("[err]Internal error: API client missing[/]")
            return

        api_key = self.api_input.value.strip()
        if not api_key:
            self.status.update("[err]API key is required[/]")
            self.api_input.focus()
            return

        self.status.update("Authenticating…")
        self.cluster_list.clear()
        self.query_one("#btn-connect", Button).disabled = True

        try:
            result = await self.api.login(api_key)
        except Exception as exc:  # noqa: BLE001
            self.status.update(f"[err]Login failed: {exc}[/]")
            return

        # Save in state
        self.state = AuthState(api_key=api_key, login_result=result)

        # Update UI
        self.user_info.update(
            f"[ok]Authenticated as [b]{result.email or result.user_id}[/b] • "
            f"Credits: {result.credits:.3f}[/]"
        )
        if not result.clusters:
            self.status.update("[warn]No clusters available for this user.[/]")
        else:
            for c in result.clusters:
                item = ListItem(
                    Static(f"{c.name} — {c.description}", expand=True)
                )
                # stash cluster object
                item.data = c
                self.cluster_list.append(item)
            self.status.update(
                "[ok]Select a cluster on the right and press "
                "[b]'Connect to Selected Cluster'[/b]."
            )
            self.query_one("#btn-connect", Button).disabled = False

    @on(Button.Pressed, "#btn-connect")
    async def handle_connect(self) -> None:
        if not self.api or not self.state.login_result:
            self.status.update("[err]Login required first[/]")
            return

        selected = self.cluster_list.highlighted_child
        if not selected or not hasattr(selected, "data"):
            self.status.update("[warn]Select a cluster first.[/]")
            return

        cluster: Cluster = selected.data
        api_key = self.state.api_key

        self.status.update(f"Connecting to cluster [b]{cluster.name}[/b]…")

        try:
            session = await self.api.select_cluster(api_key, cluster.name)
        except Exception as exc:  # noqa: BLE001
            self.status.update(f"[err]Cluster connect failed: {exc}[/]")
            return

        # fuse login + session info
        full_session = Session(
            success=session.success,
            session_token=session.session_token,
            clusters=session.clusters,  # API returns the list of clusters connected
            expires_at=session.expires_at,
            message=session.message,
            error=session.error
        )
        self.state.session = full_session

        self.status.update(
            f"[ok]Connected to [b]{full_session.clusters}[/b]. "
            f"Session expires at {full_session.expires_at}."
        )

        # Notify the App so it can route subsequent API calls
        self.post_message(self.LoggedIn(full_session))