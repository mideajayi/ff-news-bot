from collections import defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.models import Event

_IMPACT_EMOJI = {
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
    "holiday": "⚪️",
}


def _icon(event: Event) -> str:
    return _IMPACT_EMOJI.get(event.impact_level, "⚪️")


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _fmt_time(dt: datetime) -> str:
    t = dt.strftime("%-I:%M%p").lstrip("0").lower()
    return t


def format_digest(events: list[Event], tz: ZoneInfo) -> str:
    if not events:
        return "<b>ForexFactory Daily Digest</b>\nNo events scheduled today."

    by_day: dict[date, dict[str, list[tuple[str, str, str]]]] = defaultdict(lambda: defaultdict(list))
    for e in events:
        dt = datetime.fromisoformat(e.date).astimezone(tz)
        by_day[dt.date()][e.country].append((_icon(e), _fmt_time(dt), e.title))

    lines = ["<b>ForexFactory Daily Digest</b>", ""]
    for day in sorted(by_day):
        weekday = day.strftime("%A")
        month = day.strftime("%b")
        lines.append(f"<b>{weekday}, {month} {_ordinal(day.day)}</b>")
        lines.append("")
        first_country = True
        for country in sorted(by_day[day]):
            if not first_country:
                lines.append("")
            first_country = False
            lines.append(f"<b>{country}</b>")
            lines.append("")
            for i, (icon, t, title) in enumerate(by_day[day][country]):
                if i > 0:
                    lines.append("")
                lines.append(f"  {icon} {t} {title}")
    return "\n".join(lines)


def format_alert(event: Event) -> str:
    line = f"{_icon(event)} <b>New event</b>\n{event.date} — <b>{event.country}</b> {event.title}"
    if event.forecast or event.previous:
        line += f"\nForecast: {event.forecast or '-'} | Previous: {event.previous or '-'}"
    return line


def format_warning(event: Event, dt: datetime) -> str:
    time_str = _fmt_time(dt)
    line = f"{_icon(event)} <b>1 hour warning</b>\n<b>{event.country}</b> {event.title} at {time_str}"
    if event.forecast or event.previous:
        line += f"\nForecast: {event.forecast or '-'} | Previous: {event.previous or '-'}"
    return line


def format_reminder(event: Event) -> str:
    line = f"{_icon(event)} <b>Happening now</b>\n<b>{event.country}</b> {event.title}"
    if event.forecast or event.previous:
        line += f"\nForecast: {event.forecast or '-'} | Previous: {event.previous or '-'}"
    return line
