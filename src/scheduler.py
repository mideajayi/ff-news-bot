"""Single entrypoint: polls FF feed on startup and every 2 hours, schedules all notifications."""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings
from src.ff_client import fetch_events
from src.formatter import format_digest, format_reminder, format_warning
from src.models import Event
from src.telegram_client import send_message

log = logging.getLogger(__name__)

POLL_PREFIX = "poll-"
NOTIFY_PREFIX = "notify-"
POLL_MINUTES = 120


def _make_tz() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def _reschedule(sched: BlockingScheduler, tz: ZoneInfo) -> None:
    """Cancel all notification jobs, then re-schedule for current feed events."""
    for job in sched.get_jobs():
        if job.id.startswith(NOTIFY_PREFIX):
            sched.remove_job(job.id)

    now = datetime.now(tz)
    events = fetch_events()
    log.info("Fetched %d events, rescheduling notifications", len(events))

    scheduled: set[str] = set()

    for event in events:
        try:
            event_dt = datetime.fromisoformat(event.date).astimezone(tz)
        except ValueError:
            log.warning("Bad date for %s: %s", event.event_id, event.date)
            continue

        if event_dt <= now:
            continue

        alert = event.impact_level in settings.alert_impact_levels

        # 1-hour-before warning
        if alert:
            warning_dt = event_dt - timedelta(hours=1)
            if warning_dt > now:
                key = f"{event.event_id}:warning"
                if key not in scheduled:
                    sched.add_job(
                        _send_warning,
                        trigger="date",
                        run_date=warning_dt,
                        args=[event, event_dt],
                        id=f"{NOTIFY_PREFIX}{key}",
                    )
                    scheduled.add(key)

        # At-time reminder
        if alert:
            key = f"{event.event_id}:reminder"
            if key not in scheduled:
                sched.add_job(
                    _send_reminder,
                    trigger="date",
                    run_date=event_dt,
                    args=[event],
                    id=f"{NOTIFY_PREFIX}{key}",
                )
                scheduled.add(key)

    # Daily digest: 10pm local, one per calendar day that has events.
    # The callback sends tomorrow's events when it fires.
    days_with_events: set[str] = set()
    for event in events:
        try:
            event_dt = datetime.fromisoformat(event.date).astimezone(tz)
        except ValueError:
            continue
        days_with_events.add(event_dt.date().isoformat())

    tomorrow = (now + timedelta(days=1)).date()
    if tomorrow.isoformat() in days_with_events:
        digest_key = f"digest-{tomorrow.isoformat()}"
        if digest_key not in scheduled:
            digest_hour = min(settings.digest_hour, 23)
            digest_minute = min(settings.digest_minute, 59)
            digest_time = now.replace(
                hour=digest_hour, minute=digest_minute, second=0, microsecond=0
            )
            if digest_time > now:
                sched.add_job(
                    _send_digest,
                    trigger="date",
                    run_date=digest_time,
                    id=f"{NOTIFY_PREFIX}{digest_key}",
                )
                scheduled.add(digest_key)

    log.info("Scheduled %d notification jobs", len(scheduled))


# -- Callbacks ---------------------------------------------------------------


def _send_warning(event: Event, event_dt: datetime) -> None:
    send_message(format_warning(event, event_dt))


def _send_reminder(event: Event) -> None:
    send_message(format_reminder(event))


def _send_digest() -> None:
    tz = _make_tz()
    tomorrow = (datetime.now(tz) + timedelta(days=1)).date()
    events = fetch_events()
    tomorrow_events = [
        e
        for e in events
        if datetime.fromisoformat(e.date).astimezone(tz).date() == tomorrow
    ]
    send_message(format_digest(tomorrow_events, tz))


# -- Main loop ---------------------------------------------------------------


def _poll(sched: BlockingScheduler) -> None:
    tz = _make_tz()
    _reschedule(sched, tz)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    settings.validate()

    sched = BlockingScheduler()
    tz = _make_tz()

    # Immediate startup reschedule + recurring poll every 2 hours.
    sched.add_job(
        _poll,
        trigger="interval",
        minutes=POLL_MINUTES,
        id=f"{POLL_PREFIX}main",
        args=[sched],
    )

    # Run once now, then the interval keeps it going.
    _poll(sched)

    log.info("Scheduler started, polling every %d min", POLL_MINUTES)
    sched.start()


if __name__ == "__main__":
    main()
