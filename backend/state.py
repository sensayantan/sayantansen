"""
Tracks when the last successful edition was generated, so each run only
asks Claude to search since then (falling back to the last 3 days for
the very first edition), per the "search only since the previous
successful run" requirement.
"""

from __future__ import annotations  # so `int | None` works on Python 3.9

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"


def load_since(force_lookback_days: int | None = None) -> str:
    """
    Returns an ISO-8601 timestamp to search from.

    Pass force_lookback_days to ignore state.json and search back that many
    days instead — useful when testing/re-running by hand, since otherwise
    every manual re-run narrows the window to "since the last manual run a
    few minutes ago" rather than a realistic daily window.
    """
    if force_lookback_days is not None:
        return (datetime.now(timezone.utc) - timedelta(days=force_lookback_days)).isoformat()

    if STATE_PATH.exists():
        data = json.loads(STATE_PATH.read_text())
        last_success = data.get("last_success_at")
        if last_success:
            return last_success

    first_run_since = datetime.now(timezone.utc) - timedelta(days=3)
    return first_run_since.isoformat()


def save_success() -> None:
    STATE_PATH.write_text(
        json.dumps({"last_success_at": datetime.now(timezone.utc).isoformat()}, indent=2)
    )
