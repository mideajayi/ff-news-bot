"""Run once, send today's digest. Intended for a daily cron (GitHub Actions or Render cron job)."""
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import settings
from src.ff_client import fetch_events
from src.formatter import format_digest
from src.telegram_client import send_message


def main() -> None:
    settings.validate()
    events = fetch_events()

    tz = ZoneInfo(settings.timezone)
    today = datetime.now(tz).date()
    todays_events = [
        e for e in events
        if datetime.fromisoformat(e.date).astimezone(tz).date() == today
    ]

    message = format_digest(todays_events)
    send_message(message)


if __name__ == "__main__":
    main()
