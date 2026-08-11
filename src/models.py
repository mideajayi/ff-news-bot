from pydantic import BaseModel


class Event(BaseModel):
    title: str
    country: str
    date: str       # raw date string from FF feed
    impact: str      # High / Medium / Low / Holiday
    forecast: str | None = None
    previous: str | None = None
    url: str | None = None

    @property
    def event_id(self) -> str:
        """Stable-ish key for diffing runs: same event, same date+time."""
        return f"{self.country}|{self.title}|{self.date}"

    @property
    def impact_level(self) -> str:
        return self.impact.strip().lower()
