"""Textual screens for rclone-cleanup-json-files."""

import sys
from pathlib import Path

from textual import on, work
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Label, ListItem, ListView, Log, Static
from textual_fspicker import SelectDirectory

from .rclone_service import (
    JsonFileStats,
    RcloneError,
    RcloneNotFoundError,
    RcloneService,
)


class RemoteSelectScreen(Screen[None]):
    """Screen for selecting an rclone remote."""

    BINDINGS = [("escape", "app.exit", "Exit")]

    def __init__(self, rclone: RcloneService, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rclone = rclone
        self._remotes: list[str] = []

    def compose(self) -> None:
        yield Vertical(
            Label("Select rclone remote", classes="title"),
            Static(id="error", classes="error"),
            ListView(id="remotes"),
            Horizontal(
                Button("Refresh", id="refresh"),
                Button("Exit", id="exit"),
                id="buttons",
            ),
            id="main",
        )

    def on_mount(self) -> None:
        self._load_remotes()

    @on(Button.Pressed, "#exit")
    def _exit(self) -> None:
        self.app.exit()

    def _load_remotes(self) -> None:
        error_widget = self.query_one("#error", Static)
        error_widget.update("")
        list_view = self.query_one("#remotes", ListView)
        list_view.clear()
        try:
            self._remotes = self._rclone.list_remotes()
            if not self._remotes:
                error_widget.update("No remotes configured. Run 'rclone config' first.")
                return
            for r in self._remotes:
                list_view.append(ListItem(Label(r)))
        except RcloneNotFoundError as e:
            error_widget.update(str(e))
        except RcloneError as e:
            error_widget.update(str(e))

    @on(Button.Pressed, "#refresh")
    def _refresh(self) -> None:
        self._load_remotes()

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._remotes):
            remote = self._remotes[idx]
            self.app.remote = remote  # type: ignore[attr-defined]
            self.app.push_screen(RemotePathScreen(self._rclone, remote=remote))


class RemotePathScreen(Screen[None]):
    """Screen for selecting remote path (top-level dir or root)."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    ROOT_LABEL = "(root - entire remote)"

    def __init__(self, rclone: RcloneService, remote: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rclone = rclone
        self._remote = remote
        self._dirs: list[str] = []

    def compose(self) -> None:
        yield Vertical(
            Label(f"Select path on {self._remote}", classes="title"),
            Static(id="error", classes="error"),
            ListView(
                ListItem(Label(self.ROOT_LABEL)),
                id="paths",
            ),
            Horizontal(
                Button("Back", id="back"),
                id="buttons",
            ),
            id="main",
        )

    def on_mount(self) -> None:
        self._load_dirs()

    def _load_dirs(self) -> None:
        error_widget = self.query_one("#error", Static)
        error_widget.update("")
        list_view = self.query_one("#paths", ListView)
        list_view.clear()
        list_view.append(ListItem(Label(self.ROOT_LABEL)))
        try:
            self._dirs = self._rclone.list_remote_dirs(self._remote)
            for d in self._dirs:
                list_view.append(ListItem(Label(d)))
        except RcloneError as e:
            error_widget.update(str(e))

    @on(Button.Pressed, "#back")
    def _back(self) -> None:
        self.app.pop_screen()

    @on(ListView.Selected)
    def _on_selected(self, event: ListView.Selected) -> None:
        list_view = event.list_view
        idx = list_view.index
        if idx is None or idx < 0:
            return
        if idx == 0:
            path = ""
        elif idx - 1 < len(self._dirs):
            path = self._dirs[idx - 1]
        else:
            return
        self.app.remote_path = path  # type: ignore[attr-defined]
        self.app.push_screen(DestPathScreen(self._rclone, self._remote, path))


class DestPathScreen(Screen[None]):
    """Screen for selecting local destination path."""

    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(
        self,
        rclone: RcloneService,
        remote: str,
        remote_path: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._rclone = rclone
        self._remote = remote
        self._remote_path = remote_path

    def compose(self) -> None:
        dest_name = (
            f"{self._remote}-{self._remote_path}" if self._remote_path else self._remote
        )
        yield Vertical(
            Label("Select local destination folder", classes="title"),
            Label(
                f"Files will be saved to: .../{dest_name}/",
                id="hint",
            ),
            Static(id="error", classes="error"),
            Horizontal(
                Input(placeholder="Enter path or click Browse", id="path_input"),
                Button("Browse", id="browse"),
                id="path_row",
            ),
            Horizontal(
                Button("Back", id="back"),
                Button("Continue", id="continue", variant="primary"),
                id="buttons",
            ),
            id="main",
        )

    @on(Button.Pressed, "#back")
    def _back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#browse")
    @work
    async def _browse(self) -> None:
        if path := await self.push_screen_wait(SelectDirectory()):
            self.query_one("#path_input", Input).value = str(path)
            self.query_one("#error", Static).update("")

    @on(Button.Pressed, "#continue")
    def _continue(self) -> None:
        error_widget = self.query_one("#error", Static)
        raw = self.query_one("#path_input", Input).value.strip()
        if not raw:
            error_widget.update("Please enter or select a path.")
            return
        p = Path(raw).expanduser().resolve()
        if not p.exists():
            error_widget.update("Path does not exist.")
            return
        if not p.is_dir():
            error_widget.update("Path is not a directory.")
            return
        try:
            test_file = p / ".rclone_cleanup_json_files_write_test"
            test_file.touch()
            test_file.unlink()
        except OSError:
            error_widget.update("Path is not writable.")
            return
        error_widget.update("")
        try:
            stats = self._rclone.find_json_files(self._remote, self._remote_path)
        except RcloneError as e:
            error_widget.update(str(e))
            return
        self.app.push_screen(
            ProgressScreen(
                self._rclone,
                self._remote,
                self._remote_path,
                p,
                stats,
            )
        )


class ProgressScreen(Screen[None]):
    """Screen showing download progress."""

    BINDINGS = [("escape", "", "Wait")]  # Disable escape during operation

    def __init__(
        self,
        rclone: RcloneService,
        remote: str,
        remote_path: str,
        base_dest: Path,
        stats: JsonFileStats,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._rclone = rclone
        self._remote = remote
        self._remote_path = remote_path
        self._base_dest = base_dest
        self._stats = stats
        dest_name = f"{remote}-{remote_path}" if remote_path else remote
        self._dest_folder = base_dest / dest_name

    def compose(self) -> None:
        yield Vertical(
            Label("Downloading JSON files", classes="title"),
            Static(
                f"Files: {self._stats.file_count} | "
                f"Folders: {self._stats.folder_count}",
                id="stats",
            ),
            Log(highlight=True, id="log"),
            Horizontal(
                Button("Back", id="back"),
                id="error_buttons",
            ),
            id="main",
        )

    def on_mount(self) -> None:
        self._dest_folder.mkdir(parents=True, exist_ok=True)
        self.query_one("#error_buttons", Horizontal).display = False
        self.run_worker(self._do_copy())

    def _show_back_button(self) -> None:
        self.query_one("#error_buttons", Horizontal).display = True

    @on(Button.Pressed, "#back")
    def _back(self) -> None:
        self.app.pop_screen()

    @work
    async def _do_copy(self) -> None:
        log = self.query_one("#log", Log)
        try:
            for line in self._rclone.run_copy_streaming(
                self._remote,
                self._remote_path,
                self._dest_folder,
            ):
                self.call_from_thread(log.write_line, line)
            self.app.base_dest = self._base_dest  # type: ignore[attr-defined]
            self.app.dest_folder = self._dest_folder  # type: ignore[attr-defined]
            self.app.stats = self._stats  # type: ignore[attr-defined]
            self.app.push_screen(CompleteScreen())
        except RcloneError as e:
            self.call_from_thread(log.write_line, f"Error: {e}")
            self.call_from_thread(self._show_back_button)
        except Exception as e:
            self.call_from_thread(log.write_line, f"Error: {e}")
            self.call_from_thread(self._show_back_button)


class MoveProgressScreen(Screen[None]):
    """Screen showing move-to-backup progress."""

    BINDINGS = [("escape", "", "Wait")]

    def __init__(
        self,
        rclone: RcloneService,
        remote: str,
        remote_path: str,
        dry_run: bool,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._rclone = rclone
        self._remote = remote
        self._remote_path = remote_path
        self._dry_run = dry_run

    def compose(self) -> None:
        mode = "Dry run: " if self._dry_run else ""
        yield Vertical(
            Label(f"{mode}Moving JSON files to deleted-json-files", classes="title"),
            Log(highlight=True, id="log"),
            Horizontal(
                Button("Close", id="close"),
                id="error_buttons",
            ),
            id="main",
        )

    def on_mount(self) -> None:
        self.query_one("#error_buttons", Horizontal).display = False
        self.run_worker(self._do_move())

    def _show_close_button(self) -> None:
        self.query_one("#error_buttons", Horizontal).display = True

    @on(Button.Pressed, "#close")
    def _close(self) -> None:
        self.dismiss(False)

    @work
    async def _do_move(self) -> None:
        log = self.query_one("#log", Log)
        try:
            for line in self._rclone.run_move_streaming(
                self._remote,
                self._remote_path,
                dry_run=self._dry_run,
            ):
                self.call_from_thread(log.write_line, line)
            self.call_from_thread(self.dismiss, True)
        except RcloneError as e:
            self.call_from_thread(log.write_line, f"Error: {e}")
            self.call_from_thread(self._show_close_button)
        except Exception as e:
            self.call_from_thread(log.write_line, f"Error: {e}")
            self.call_from_thread(self._show_close_button)


class CompleteScreen(Screen[None]):
    """Completion screen with Open Finder and Delete options."""

    BINDINGS = [("escape", "app.exit", "Exit")]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self) -> None:
        yield Vertical(
            Label("Download complete", classes="title"),
            Static(id="summary"),
            Horizontal(
                Button("Open in Finder", id="finder"),
                Button("Delete from remote", id="delete"),
                Button("Quit", id="quit"),
                id="buttons",
            ),
            id="main",
        )

    def on_mount(self) -> None:
        base = getattr(self.app, "base_dest", None)
        dest = getattr(self.app, "dest_folder", None)
        stats = getattr(self.app, "stats", None)
        summary = self.query_one("#summary", Static)
        if base and dest and stats:
            summary.update(
                f"Saved {stats.file_count} files from {stats.folder_count} "
                f"folders to:\n{dest}"
            )
        else:
            summary.update("Download completed.")
        finder_btn = self.query_one("#finder", Button)
        if not self._is_darwin():
            finder_btn.display = False

    def _is_darwin(self) -> bool:
        return sys.platform == "darwin"

    @on(Button.Pressed, "#finder")
    def _open_finder(self) -> None:
        import subprocess

        base = getattr(self.app, "base_dest", None)
        if base and self._is_darwin():
            subprocess.run(["open", str(base)], check=False)  # noqa: S603

    @on(Button.Pressed, "#delete")
    @work
    async def _delete(self) -> None:
        confirm = await self.push_screen_wait(
            ConfirmScreen(
                "Delete JSON files from remote? "
                "They will be moved to remote:deleted-json-files."
            )
        )
        if confirm is not True:
            return
        dry_run = await self.push_screen_wait(ConfirmScreen("Run dry-run first?"))
        if dry_run is None:
            return
        rclone = getattr(self.app, "rclone", None)
        remote = getattr(self.app, "remote", None)
        remote_path = getattr(self.app, "remote_path", "")
        if not rclone or not remote:
            self.notify("No remote selected.")
            return
        move_ok = await self.push_screen_wait(
            MoveProgressScreen(rclone, remote, remote_path or "", dry_run=dry_run)
        )
        if move_ok is False:
            self.notify("Move to deleted-json-files failed. See log for details.")
            return
        if dry_run:
            do_real = await self.push_screen_wait(
                ConfirmScreen("Dry run complete. Proceed for real?")
            )
            if do_real:
                real_ok = await self.push_screen_wait(
                    MoveProgressScreen(
                        rclone, remote, remote_path or "", dry_run=False
                    )
                )
                if real_ok is False:
                    self.notify(
                        "Move to deleted-json-files failed. See log for details."
                    )

    @on(Button.Pressed, "#quit")
    def _quit(self) -> None:
        self.app.exit()


class ConfirmScreen(ModalScreen[bool | None]):
    """Simple Yes/No modal."""

    BINDINGS = [("escape", "dismiss_none", "Cancel")]

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._message = message

    def action_dismiss_none(self) -> None:
        """Dismiss with None (cancel) on ESC."""
        self.dismiss(None)

    def compose(self) -> None:
        yield Container(
            Label(self._message, id="msg"),
            Horizontal(
                Button("Yes", id="yes", variant="primary"),
                Button("No", id="no"),
                Button("Cancel", id="cancel"),
                id="buttons",
            ),
            id="dialog",
        )

    @on(Button.Pressed, "#yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def _no(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)
