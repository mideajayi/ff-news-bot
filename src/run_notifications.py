"""Stateless notification runner for GitHub Actions.

Reads/writes data/sent_log.json to track which notifications have already been sent.
Designed to run every few minutes via cron — each invocation picks up anything that
fell in the window since the last run.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import settings
from src.ff_client import fetch_events
from src.formatter import format_digest, format_reminder, format_warning
from src.models import Event
from src.telegram_client import send_message

log = logging.getLogger(__name__)

SENT_LOG = Path(__file__).resolve().parent.parent / "data" / "sent_log.json"
PRUNE_HOURS = 48


# -- State -------------------------------------------------------------------


def _load_state() -> tuple[datetime, set[str]]:
    tz = ZoneInfo(settings.timezone)
    if SENT_LOG.exists():
        data = json.loads(SENT_LOG.read_text())
        last_run = datetime.fromisoformat(data["last_run"]).astimezone(tz)
        return last_run, set(data.get("sent", []))
    # First run: pretend we ran one interval ago.
    now = datetime.now(tz)
    fallback = now - timedelta(minutes=settings.poll_interval_minutes)
    return fallback, set()


def _save_state(last_run: datetime, sent: set[str]) -> None:
    SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    SENT_LOG.write_text(
        json.dumps(
            {"last_run": last_run.isoformat(), "sent": sorted(sent)},
            indent=2,
        )
    )


# -- Pruning -----------------------------------------------------------------


def _parse_key_date(key: str) -> datetime | None:
    """Extract the datetime from a sent-log key for pruning."""
    tz = ZoneInfo(settings.timezone)
    # Event key: country|title|2026-08-12T08:30:00-04:00:warning
    # Digest key: digest-2026-08-12
    if key.startswith("digest-"):
        date_str = key.removeprefix("digest-")
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
        except ValueError:
            return None
    # Strip the :type suffix, then extract the ISO date from the event_id portion.
    id_part = key.rsplit(":", 1)[0] if ":" in key else key
    parts = id_part.split("|")
    if len(parts) >= 3:
        try:
            return datetime.fromisoformat(parts[2]).astimezone(tz)
        except ValueError:
            return None
    return None


def _prune(sent: set[str], now: datetime) -> set[str]:
    cutoff = now - timedelta(hours=PRUNE_HOURS)
    pruned: set[str] = set()
    for key in sent:
        dt = _parse_key_date(key)
        if dt is None or dt >= cutoff:
            pruned.add(key)
    return pruned


# -- Notifications -----------------------------------------------------------


def _send(event: Event, key: str, send_fn) -> None:
    send_fn()
    log.info("Sent %s", key)


def _check_event(event: Event, last_run: datetime, now: datetime, sent: set[str]) -> None:
    try:
        event_dt = datetime.fromisoformat(event.date).astimezone(now.tzinfo)
    except ValueError:
        return

    alert = event.impact_level in settings.alert_impact_levels

    # 1-hour-before warning
    if alert:
        warning_dt = event_dt - timedelta(hours=1)
        key = f"{event.event_id}:warning"
        if last_run < warning_dt <= now and key not in sent:
            _send(event, key, lambda: send_message(format_warning(event, event_dt)))
            sent.add(key)

    # At-time reminder
    if alert:
        key = f"{event.event_id}:reminder"
        if last_run < event_dt <= now and key not in sent:
            _send(event, key, lambda: send_message(format_reminder(event)))
            sent.add(key)


def _check_digest(last_run: datetime, now: datetime, sent: set[str], events: list[Event]) -> None:
    """Send tomorrow's digest if 10pm local has passed since last_run."""
    tz = now.tzinfo
    today = now.date()
    digest_time = now.replace(
        hour=min(settings.digest_hour, 23),
        minute=min(settings.digest_minute, 59),
        second=0,
        microsecond=0,
    )

    # Only fire if today's 10pm is within the window.
    if last_run < digest_time <= now:
        digest_key = f"digest-{today.isoformat()}"
        if digest_key not in sent:
            tomorrow = today + timedelta(days=1)
            tomorrow_events = [
                e
                for e in events
                if datetime.fromisoformat(e.date).astimezone(tz).date() == tomorrow
            ]
            send_message(format_digest(tomorrow_events, tz))
            log.info("Sent %s", digest_key)
            sent.add(digest_key)


# -- Main entrypoint ---------------------------------------------------------


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    settings.validate()

    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    last_run, sent = _load_state()

    log.info("Run window: %s → %s", last_run.isoformat(), now.isoformat())

    events = fetch_events()
    for event in events:
        _check_event(event, last_run, now, sent)

    _check_digest(last_run, now, sent, events)

    sent = _prune(sent, now)
    _save_state(now, sent)
    log.info("Done. %d keys in sent log.", len(sent))


if __name__ == "__main__":
    main()
