"""Find, download and delete JSON files from cloud drives."""

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from .rclone_service import JsonFileStats, RcloneService
from .screens import RemoteSelectScreen


class RcloneCleanupJsonApp(App[None]):
    """Find, download and delete JSON files from cloud drives."""

    TITLE = "Find, download and delete JSON files from cloud drives"

    BINDINGS = [
        Binding("escape", "escape_back_or_exit", "Exit", priority=True),
    ]

    CSS = """
    Screen {
        align: center middle;
    }

    Screen > Header {
        dock: top;
    }

    .title {
        width: 100%;
        text-align: center;
        margin: 1 0;
        text-style: bold;
    }

    .error {
        color: red;
        width: 100%;
        margin: 1 0;
    }

    #main {
        width: auto;
        min-width: 50;
        padding: 1 2;
        border: solid $primary;
    }

    #buttons {
        margin-top: 1;
        height: auto;
    }

    #hint {
        width: 100%;
        max-width: 100%;
    }

    #path_row {
        margin: 1 0;
    }

    #path_row Input {
        width: 1fr;
        min-width: 10;
    }

    #path_row #browse {
        width: auto;
        min-width: 8;
    }

    #loading_row {
        margin: 0 0 1 0;
        height: auto;
        min-height: 2;
        align-horizontal: center;
    }

    LoadingIndicator {
        min-height: 2;
        min-width: 8;
    }

    #loading_label {
        margin-left: 1;
        color: $text-muted;
    }

    ListView {
        height: 15;
        width: 50;
        margin: 1 0;
    }

    ConfirmScreen Container {
        width: 60;
        padding: 2;
        border: solid $primary;
    }

    #dialog {
        width: auto;
        min-width: 40;
    }

    .footer-hint {
        dock: bottom;
        content-align: center middle;
        height: 1;
        padding: 0 1;
        width: 100%;
    }
    """

    def __init__(self, rclone: RcloneService | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.rclone = rclone or RcloneService()
        self.remote: str = ""
        self.remote_path: str = ""
        self.base_dest: Path = Path(".")
        self.dest_folder: Path = Path(".")
        self.stats: JsonFileStats = JsonFileStats(0, 0)

    def compose(self) -> ComposeResult:
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(RemoteSelectScreen(self.rclone))

    def action_escape_back_or_exit(self) -> None:
        """Exit on first screen; otherwise pop or dismiss.

        Priority binding overrides ListView behavior.
        """
        from textual.screen import ModalScreen

        from .screens import MoveProgressScreen, ProgressScreen, RemoteSelectScreen

        top = self.screen_stack[-1]
        if isinstance(top, RemoteSelectScreen):
            self.exit()
        elif isinstance(top, ModalScreen):
            top.dismiss(None)
        elif isinstance(top, (ProgressScreen, MoveProgressScreen)):
            pass  # ESC disabled during progress
        else:
            self.pop_screen()


def main() -> None:
    """Entry point for the application."""
    app = RcloneCleanupJsonApp()
    app.run()


if __name__ == "__main__":
    main()
