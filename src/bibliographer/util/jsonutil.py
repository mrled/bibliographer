"""JSON utilities
"""

import json
import pathlib


def load_json(path: pathlib.Path) -> dict:
    """Load JSON from a file. If file doesn't exist, return empty dict."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: pathlib.Path, data: dict):
    """Save JSON to a file, overwriting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def merge_json(old_data: dict, new_data: dict) -> dict:
    """Merge new_data into old_data, overwriting conflicts but preserving keys not in new_data."""
    merged = dict(old_data)  # shallow copy
    for k, v in new_data.items():
        merged[k] = v
    return merged
