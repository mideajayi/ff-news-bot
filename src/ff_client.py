import httpx
from src.config import settings
from src.models import Event

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ff-news-bot/1.0)"
}


def fetch_events() -> list[Event]:
    """Pull the current week's calendar from ForexFactory's export feed.

    Rate limit: FF allows max 2 requests / 5 min across all export formats.
    Keep POLL_INTERVAL_MINUTES >= 5 in .env to stay well within that.
    """
    resp = httpx.get(settings.ff_calendar_url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    raw = resp.json()

    events: list[Event] = []
    for item in raw:
        events.append(
            Event(
                title=item.get("title", "Untitled"),
                country=item.get("country", ""),
                date=item.get("date", ""),
                impact=item.get("impact", ""),
                forecast=item.get("forecast") or None,
                previous=item.get("previous") or None,
                url=item.get("url") or None,
            )
        )
    return events
