# ff-news-bot

Telegram bot that posts ForexFactory economic calendar events: a daily digest plus real-time alerts when new events appear on the calendar.

## Architecture

Two separate processes, because they have different runtime needs:

| Piece | What it does | Where it runs | Trigger |
|---|---|---|---|
| `src/run_digest.py` | Fetches today's events, sends one formatted summary | GitHub Actions | Daily cron (`.github/workflows/daily-digest.yml`) |
| `src/run_alerts.py` | Polls the feed every N minutes, alerts on anything new | Render (background worker) | Always-on, `render.yaml` |

Both pull from ForexFactory's unofficial weekly export feed (`ff_calendar_thisweek.json`), not scraped HTML — see caveats below.

## Setup

1. Copy `.env.example` to `.env` and fill in:
   - `TELEGRAM_BOT_TOKEN` — from @BotFather
   - `TELEGRAM_CHAT_ID` — your chat/channel ID (message @userinfobot or your bot to find it)
2. `pip install -r requirements.txt`
3. Test locally:
   ```
   python -m src.run_digest
   python -m src.run_alerts
   ```

## Deploying

**Digest (GitHub Actions):**
Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as repo secrets (Settings → Secrets and variables → Actions). The workflow runs on its own once pushed.

**Alerts (Render):**
Connect the repo, Render will read `render.yaml` and provision a background worker. Set the two secret env vars in the Render dashboard.

## Known gaps to close before this is production-ready

- **Verify the FF feed schema.** The field names in `src/ff_client.py` (`title`, `country`, `date`, `impact`, `forecast`, `previous`) are based on community scraper projects — pull a live response from `https://nfs.faireconomy.media/ff_calendar_thisweek.json` and confirm field names/date format match before relying on filtering logic in `run_digest.py`.
- **Date filtering in `run_digest.py`** assumes a specific date string format (`"Mon Aug 11"`) — this needs to be checked against the real feed and likely rewritten with proper date parsing.
- **No "actual" values.** The export feed only has forecast/previous, not released actuals — if you want actuals later, that requires scraping the calendar HTML page instead (see fallback options discussed separately).
- **`data/seen_events.json`** persists between GitHub Actions runs only if committed back to the repo (Actions containers are ephemeral) — not an issue for `run_alerts.py` since it's a long-running Render process with a persistent disk, but worth knowing.
- No tests yet — `tests/` is scaffolded but empty.

## Rate limits

ForexFactory limits the export feed to 2 requests / 5 minutes across all formats. `POLL_INTERVAL_MINUTES` defaults to 5 — don't lower this without checking you're not also hitting the feed from elsewhere (e.g. manual testing) in the same window.
