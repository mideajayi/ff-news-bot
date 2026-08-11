import json
from pathlib import Path
from src.models import Event

_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "seen_events.json"


def load_seen_ids() -> set[str]:
    if not _CACHE_PATH.exists():
        return set()
    return set(json.loads(_CACHE_PATH.read_text()))


def save_seen_ids(ids: set[str]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(sorted(ids)))


def diff_new_events(events: list[Event]) -> list[Event]:
    """Return events not seen in a previous run, and persist the updated set."""
    seen = load_seen_ids()
    current_ids = {e.event_id for e in events}
    new_events = [e for e in events if e.event_id not in seen]
    save_seen_ids(seen | current_ids)
    return new_events
