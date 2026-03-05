"""Rclone subprocess wrappers for listing, copying, and moving JSON files."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Generator


class RcloneError(Exception):
    """Raised when an rclone command fails."""

    pass


class RcloneNotFoundError(RcloneError):
    """Raised when rclone executable is not found."""

    pass


@dataclass
class JsonFileStats:
    """Stats about JSON files found on remote."""

    file_count: int
    folder_count: int


class RcloneService:
    """Service for running rclone commands."""

    def __init__(self, rclone_cmd: str = "rclone") -> None:
        self._rclone = rclone_cmd

    def list_remotes(self) -> list[str]:
        """Return list of configured rclone remote names."""
        try:
            result = run(
                [self._rclone, "listremotes"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as e:
            raise RcloneNotFoundError("rclone executable not found in PATH") from e
        except CalledProcessError as e:
            raise RcloneError(
                f"rclone listremotes failed: {e.stderr or ''}"
            ) from e

        lines = [
            line.strip().rstrip(":") for line in result.stdout.strip().splitlines()
        ]
        return [r for r in lines if r]

    def list_remote_dirs(self, remote: str) -> list[str]:
        """Return top-level directories under remote (stripped of trailing slashes)."""
        try:
            result = run(
                [self._rclone, "lsf", f"{remote}:", "--dirs-only"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as e:
            raise RcloneNotFoundError("rclone executable not found in PATH") from e
        except CalledProcessError as e:
            raise RcloneError(
                f"rclone lsf failed: {e.stderr or ''}"
            ) from e

        dirs = [
            line.rstrip("/").strip()
            for line in result.stdout.strip().splitlines()
            if line.strip()
        ]
        return sorted(dirs)

    def find_json_files(self, remote: str, path: str) -> JsonFileStats:
        """Find all JSON files under remote:path, return stats."""
        src = f"{remote}:{path}" if path else f"{remote}:"
        try:
            result = run(
                [
                    self._rclone,
                    "lsf",
                    "-R",
                    "--files-only",
                    "--include",
                    "*.json",
                    "--ignore-case",
                    src,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as e:
            raise RcloneNotFoundError("rclone executable not found in PATH") from e
        except CalledProcessError as e:
            raise RcloneError(
                f"rclone lsf failed: {e.stderr or ''}"
            ) from e

        paths = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        folders: set[str] = set()
        for p in paths:
            if "/" in p:
                folders.add(p.rsplit("/", 1)[0])
            else:
                folders.add(".")
        return JsonFileStats(
            file_count=len(paths),
            folder_count=len(folders),
        )

    def run_copy_streaming(
        self,
        remote: str,
        remote_path: str,
        local_dest: Path,
    ) -> Generator[str, None, None]:
        """Run copy and yield output lines for streaming display."""
        src = f"{remote}:{remote_path}" if remote_path else f"{remote}:"
        cmd = [
            self._rclone,
            "copy",
            src,
            str(local_dest),
            "--include",
            "*.json",
            "--ignore-case",
            "-P",
        ]
        yield from self._run_and_yield_lines(cmd)

    def run_move_streaming(
        self,
        remote: str,
        remote_path: str,
        dry_run: bool = False,
    ) -> Generator[str, None, None]:
        """Sync with --backup-dir; JSON files move to backup, not deleted."""
        dest = f"{remote}:{remote_path}" if remote_path else f"{remote}:"
        backup_subdir = remote_path if remote_path else "root"
        backup_dir = f"{remote}:deleted-json-files/{backup_subdir}"

        with tempfile.TemporaryDirectory(prefix="rclone_empty_") as empty_dir:
            cmd = [
                self._rclone,
                "sync",
                empty_dir,
                dest,
                "--include",
                "*.json",
                "--ignore-case",
                "--backup-dir",
                backup_dir,
                "-P",
            ]
            if dry_run:
                cmd.append("--dry-run")
            yield from self._run_and_yield_lines(cmd)

        # Remove empty dirs from remote (only when not dry-run)
        if not dry_run:
            rmdirs_cmd = [self._rclone, "rmdirs", dest, "-P"]
            yield from self._run_and_yield_lines(rmdirs_cmd)

    def _run_and_yield_lines(self, cmd: list[str]) -> Generator[str, None, None]:
        """Run command and yield stdout/stderr lines as they're produced."""
        try:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as e:
            raise RcloneNotFoundError("rclone executable not found in PATH") from e

        assert proc.stdout is not None
        for line in proc.stdout:
            yield line.rstrip()

        proc.wait()
        if proc.returncode != 0:
            raise RcloneError(f"rclone exited with code {proc.returncode}")
