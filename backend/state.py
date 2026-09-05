"""
Tracks when the last successful edition was generated, so each run only
asks Claude to search since then (falling back to the last 3 days for
the very first edition), per the "search only since the previous
successful run" requirement.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"


def load_since() -> str:
    """Returns an ISO-8601 timestamp to search from."""
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
