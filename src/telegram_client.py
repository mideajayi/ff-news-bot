import httpx
from src.config import settings


def send_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = httpx.post(url, json=payload, timeout=15)
    resp.raise_for_status()
