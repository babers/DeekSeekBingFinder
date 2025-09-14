"""Utilities for resolving application paths in both dev and packaged builds.

This module centralizes logic for locating writable app data directories and
resolving resource paths when bundled with PyInstaller.
"""

from __future__ import annotations

import os
import sys
from typing import Optional


APP_NAME = "DeekSeekBingFinder"


def get_app_data_dir(create: bool = True) -> str:
    """Return a per-user writable app data directory.

    On Windows: %LOCALAPPDATA%/DeekSeekBingFinder
    On macOS: ~/Library/Application Support/DeekSeekBingFinder
    On Linux: ~/.local/share/DeekSeekBingFinder
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.path.expanduser("~/.local/share")

    path = os.path.join(base, APP_NAME)
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def resource_path(relative_path: str) -> str:
    """Resolve a resource path that works for dev and PyInstaller builds.

    If running from a PyInstaller bundle, files added via --add-data are unpacked
    into a temporary folder pointed to by sys._MEIPASS.
    """
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return os.path.join(base_path, relative_path)

    # Fallback to repository/root-relative alongside this module's parent
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, relative_path)
