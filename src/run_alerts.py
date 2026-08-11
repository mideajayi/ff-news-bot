"""Long-running poller: checks the FF feed on an interval, alerts on new events.

Meant to run as an always-on worker (Render background worker), not a cron job.
"""
import logging
import time

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings
from src.ff_client import fetch_events
from src.formatter import format_alert
from src.store import diff_new_events
from src.telegram_client import send_message

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ff-alerts")


def poll_once() -> None:
    events = fetch_events()
    alertable = [e for e in events if e.impact_level in settings.alert_impact_levels]
    new_events = diff_new_events(alertable)

    for event in new_events:
        send_message(format_alert(event))
        log.info("Sent alert: %s", event.event_id)

    if not new_events:
        log.info("No new events this poll.")


def main() -> None:
    settings.validate()
    scheduler = BlockingScheduler(timezone=settings.timezone)
    scheduler.add_job(poll_once, "interval", minutes=settings.poll_interval_minutes)
    log.info("Starting poller every %s minutes", settings.poll_interval_minutes)
    poll_once()  # run immediately on boot
    scheduler.start()


if __name__ == "__main__":
    main()
