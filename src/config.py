import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [v.strip().lower() for v in value.split(",") if v.strip()]


@dataclass
class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    ff_calendar_url: str = os.getenv(
        "FF_CALENDAR_URL", "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    )
    digest_hour: int = int(os.getenv("DIGEST_HOUR", "6"))
    digest_minute: int = int(os.getenv("DIGEST_MINUTE", "0"))
    timezone: str = os.getenv("TIMEZONE", "Africa/Lagos")
    poll_interval_minutes: int = int(os.getenv("POLL_INTERVAL_MINUTES", "5"))
    alert_impact_levels: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("ALERT_IMPACT_LEVELS", "high,medium,low"))
    )

    def validate(self) -> None:
        missing = [
            name
            for name, val in [
                ("TELEGRAM_BOT_TOKEN", self.telegram_bot_token),
                ("TELEGRAM_CHAT_ID", self.telegram_chat_id),
            ]
            if not val
        ]
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


settings = Settings()
