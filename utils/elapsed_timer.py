"""Simple elapsed timer used to measure time between start and stop events.

This module provides a tiny, process-global timer API used by the GUI and
BrowserController to measure how long the search session took to reach the
configured rewards target. It intentionally keeps a minimal API so callers
can start/stop/reset and query elapsed seconds.
"""
from __future__ import annotations

import time
from typing import Optional

_start_ts: Optional[float] = None
_stop_ts: Optional[float] = None


def start() -> None:
    global _start_ts, _stop_ts
    _start_ts = time.monotonic()
    _stop_ts = None


def stop() -> float:
    """Stop the timer and return elapsed seconds. If timer wasn't started,
    returns 0.0."""
    global _start_ts, _stop_ts
    if _start_ts is None:
        return 0.0
    if _stop_ts is None:
        _stop_ts = time.monotonic()
    elapsed = _stop_ts - _start_ts
    return elapsed


def get_elapsed() -> float:
    """Return elapsed seconds without stopping the timer. Returns 0.0 if
    not started."""
    if _start_ts is None:
        return 0.0
    if _stop_ts is None:
        return time.monotonic() - _start_ts
    return _stop_ts - _start_ts


def reset() -> None:
    global _start_ts, _stop_ts
    _start_ts = None
    _stop_ts = None


def is_running() -> bool:
    return _start_ts is not None and _stop_ts is None
