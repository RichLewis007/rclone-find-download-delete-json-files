# Find, download and delete JSON files from cloud drives

Textual TUI for finding, downloading, and optionally deleting JSON files from rclone remotes.

## Requirements

- Python 3.10+
- [rclone](https://rclone.org/) installed and configured
- macOS for "Open in Finder" (optional)

## Installation

```bash
pip install -e .
```

Or with uv:

```bash
uv pip install -e .
```

## Usage

```bash
rclone-cleanup-json-files
```

Or:

```bash
python -m rclone_cleanup_json_files.app
```

From the project root (with `src` on PYTHONPATH or after `pip install -e .`).

## Flow

1. Select an rclone remote from the list
2. Select a top-level path on the remote (or root)
3. Enter or browse to a local destination folder
4. JSON files are downloaded to `{dest}/{remote}-{path}/`
5. Optionally open in Finder (macOS)
6. Optionally delete from remote (moved to `remote:deleted-json-files`)

## Author

Rich Lewis - GitHub: [@RichLewis007](https://github.com/RichLewis007)
