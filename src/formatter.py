from src.models import Event

_IMPACT_EMOJI = {
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
    "holiday": "⚪️",
}


def _icon(event: Event) -> str:
    return _IMPACT_EMOJI.get(event.impact_level, "⚪️")


def format_digest(events: list[Event]) -> str:
    if not events:
        return "<b>ForexFactory Daily Digest</b>\nNo events scheduled today."

    lines = ["<b>ForexFactory Daily Digest</b>"]
    for e in events:
        line = f"{_icon(e)} {e.date} — <b>{e.country}</b> {e.title}"
        if e.forecast or e.previous:
            line += f" (f: {e.forecast or '-'}, p: {e.previous or '-'})"
        lines.append(line)
    return "\n".join(lines)


def format_alert(event: Event) -> str:
    line = f"{_icon(event)} <b>New event</b>\n{event.date} — <b>{event.country}</b> {event.title}"
    if event.forecast or event.previous:
        line += f"\nForecast: {event.forecast or '-'} | Previous: {event.previous or '-'}"
    return line
