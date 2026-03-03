"""Unit tests for RcloneService."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rclone_cleanup_json_files.rclone_service import (
    RcloneError,
    RcloneNotFoundError,
    RcloneService,
)


@patch("rclone_cleanup_json_files.rclone_service.run")
def test_list_remotes_success(mock_run: MagicMock) -> None:
    """list_remotes returns parsed remote names."""
    mock_run.return_value = MagicMock(
        stdout="gdrive:\nlocal:\ndropbox:\n",
        stderr="",
        returncode=0,
    )
    svc = RcloneService(rclone_cmd="rclone")
    result = svc.list_remotes()
    assert result == ["gdrive", "local", "dropbox"]
    mock_run.assert_called_once_with(
        ["rclone", "listremotes"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("rclone_cleanup_json_files.rclone_service.run")
def test_list_remotes_empty(mock_run: MagicMock) -> None:
    """list_remotes returns empty list when no remotes."""
    mock_run.return_value = MagicMock(stdout="\n", stderr="", returncode=0)
    svc = RcloneService(rclone_cmd="rclone")
    result = svc.list_remotes()
    assert result == []


@patch("rclone_cleanup_json_files.rclone_service.run")
def test_list_remotes_not_found(mock_run: MagicMock) -> None:
    """list_remotes raises RcloneNotFoundError when rclone not in PATH."""
    mock_run.side_effect = FileNotFoundError("rclone not found")
    svc = RcloneService(rclone_cmd="rclone")
    with pytest.raises(RcloneNotFoundError) as exc_info:
        svc.list_remotes()
    assert "not found" in str(exc_info.value)


@patch("rclone_cleanup_json_files.rclone_service.run")
def test_list_remote_dirs_success(mock_run: MagicMock) -> None:
    """list_remote_dirs returns dirs with trailing slashes stripped."""
    mock_run.return_value = MagicMock(
        stdout="backups/\ndocs/\nimages/\n",
        stderr="",
        returncode=0,
    )
    svc = RcloneService(rclone_cmd="rclone")
    result = svc.list_remote_dirs("gdrive")
    assert result == ["backups", "docs", "images"]
    mock_run.assert_called_once_with(
        ["rclone", "lsf", "gdrive:", "--dirs-only"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("rclone_cleanup_json_files.rclone_service.run")
def test_find_json_files(mock_run: MagicMock) -> None:
    """find_json_files returns correct stats."""
    mock_run.return_value = MagicMock(
        stdout="a/file1.json\nb/c/file2.json\nroot.json\n",
        stderr="",
        returncode=0,
    )
    svc = RcloneService(rclone_cmd="rclone")
    result = svc.find_json_files("gdrive", "backups")
    assert result.file_count == 3
    assert result.folder_count == 3  # "a", "b/c", "."
    assert "a/file1.json" in result.file_paths


@patch("rclone_cleanup_json_files.rclone_service.run")
def test_find_json_files_root_path(mock_run: MagicMock) -> None:
    """find_json_files uses remote: when path is empty."""
    mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
    svc = RcloneService(rclone_cmd="rclone")
    svc.find_json_files("gdrive", "")
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "gdrive:" == call_args[-1]


@patch("rclone_cleanup_json_files.rclone_service.subprocess")
def test_run_copy_streaming_yields_lines(mock_subprocess: MagicMock) -> None:
    """run_copy_streaming yields output lines."""

    def make_proc(*args: object, **kwargs: object) -> MagicMock:
        p = MagicMock()
        p.stdout = iter(["line1\n", "line2\n", "line3\n"])
        p.wait.return_value = 0
        p.returncode = 0
        return p

    mock_subprocess.Popen.side_effect = make_proc

    svc = RcloneService(rclone_cmd="rclone")
    lines = list(svc.run_copy_streaming("gdrive", "backups", Path("/tmp/dest")))
    assert lines == ["line1", "line2", "line3"]


@patch("rclone_cleanup_json_files.rclone_service.subprocess")
def test_run_copy_streaming_nonzero_exit_raises(mock_subprocess: MagicMock) -> None:
    """run_copy_streaming raises RcloneError when rclone exits non-zero."""

    def make_proc(*args: object, **kwargs: object) -> MagicMock:
        p = MagicMock()
        p.stdout = iter(["error output\n"])
        p.wait.return_value = 0
        p.returncode = 1
        return p

    mock_subprocess.Popen.side_effect = make_proc

    svc = RcloneService(rclone_cmd="rclone")
    with pytest.raises(RcloneError) as exc_info:
        list(svc.run_copy_streaming("gdrive", "backups", Path("/tmp/dest")))
    assert "exited with code 1" in str(exc_info.value)


@patch("rclone_cleanup_json_files.rclone_service.subprocess")
def test_run_move_streaming_yields_lines(mock_subprocess: MagicMock) -> None:
    """run_move_streaming yields output lines."""

    def make_proc(*args: object, **kwargs: object) -> MagicMock:
        p = MagicMock()
        p.stdout = iter(["Moving file1\n", "Moving file2\n"])
        p.wait.return_value = 0
        p.returncode = 0
        return p

    mock_subprocess.Popen.side_effect = make_proc

    svc = RcloneService(rclone_cmd="rclone")
    lines = list(
        svc.run_move_streaming("gdrive", "backups", dry_run=False)
    )
    assert lines == ["Moving file1", "Moving file2"]


@patch("rclone_cleanup_json_files.rclone_service.run")
def test_list_remote_dirs_not_found(mock_run: MagicMock) -> None:
    """list_remote_dirs raises RcloneNotFoundError when rclone not in PATH."""
    mock_run.side_effect = FileNotFoundError("rclone not found")
    svc = RcloneService(rclone_cmd="rclone")
    with pytest.raises(RcloneNotFoundError) as exc_info:
        svc.list_remote_dirs("gdrive")
    assert "not found" in str(exc_info.value)


@patch("rclone_cleanup_json_files.rclone_service.run")
def test_find_json_files_not_found(mock_run: MagicMock) -> None:
    """find_json_files raises RcloneNotFoundError when rclone not in PATH."""
    mock_run.side_effect = FileNotFoundError("rclone not found")
    svc = RcloneService(rclone_cmd="rclone")
    with pytest.raises(RcloneNotFoundError) as exc_info:
        svc.find_json_files("gdrive", "backups")
    assert "not found" in str(exc_info.value)
