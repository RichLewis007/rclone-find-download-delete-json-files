"""Find, download and delete JSON files from cloud drives."""

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.widgets import Footer

from .rclone_service import JsonFileStats, RcloneService
from .screens import RemoteSelectScreen


class RcloneCleanupJsonApp(App[None]):
    """Find, download and delete JSON files from cloud drives."""

    TITLE = "Find, download and delete JSON files from cloud drives"

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


def main() -> None:
    """Entry point for the application."""
    app = RcloneCleanupJsonApp()
    app.run()


if __name__ == "__main__":
    main()
