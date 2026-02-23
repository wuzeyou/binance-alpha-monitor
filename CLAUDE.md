# CLAUDE.md - Development Guide

## Project Overview

Binance Alpha airdrop monitor. Polls alpha123.uk API every 5 minutes via GitHub Actions, detects new/updated airdrops, sends Telegram notifications.

## File Structure

```
monitor.py                      # Main script — fetch, diff, output
state.json                      # Persistent state (tracked in git, auto-committed by Actions)
.github/workflows/monitor.yml   # GitHub Actions workflow
```

## Key Design Decisions

- **Data source is alpha123.uk, not Binance official API.** Binance stopped publishing Alpha airdrop announcements via their CMS API (catalogId=48) around Nov 2025. Alpha airdrops are now only visible in-app. alpha123.uk is a third-party aggregator that scrapes this data.
- **cloudscraper for Cloudflare bypass.** alpha123.uk has Cloudflare protection. Plain requests/curl get 403. cloudscraper handles JS challenges. If it breaks, fallback to headless browser (Playwright).
- **State committed to git.** GitHub Actions checks out the repo, runs the script, commits state.json back. This avoids needing external storage. `[skip ci]` in commit message prevents infinite loops.
- **Telegram Bot API called directly.** No dependency on OpenClaw or any framework. Just curl/requests to `api.telegram.org`.

## API Details

**Endpoint:** `https://alpha123.uk/api/data?fresh=1`

**Response:**
```json
{
  "airdrops": [
    {
      "token": "BLESS",
      "name": "Bless",
      "date": "2026-01-08",
      "time": "20:00",
      "amount": "2500",
      "points": "251",
      "type": "grab",
      "phase": 1,
      "completed": false
    }
  ],
  "alpha_checkins": [...],
  "bnb_price_usd": 597.75,
  ...
}
```

- `airdrops` array is empty when no active/upcoming airdrops exist (normal)
- `type`: `tge` (token generation event), `grab` (first-come-first-served), `warning` (predicted, unconfirmed)
- `phase`: 1 = first round, 2 = second round

## Dedup Key

`{token}_{date}_P{phase}` — e.g. `BLESS_2026-01-08_P1`

## Change Detection

Monitors 6 fields: `name`, `time`, `amount`, `points`, `type`, `completed`. Values are normalized (None/"-"/empty → "", bools → "是"/"否") before comparison.

## GitHub Actions

- **Schedule:** `*/5 * * * *` (every 5 min)
- **Secrets needed:** `TG_BOT_TOKEN`, `TG_CHAT_ID`
- **Permissions:** `contents: write` (for committing state.json)
- **Error handling:** Script failures are logged as warnings, don't fail the workflow

## Common Tasks

### Add a new notification channel
Edit the workflow's "Run monitor" step. The script outputs JSON lines to stdout — parse and send to any channel.

### Change polling frequency
Edit `.github/workflows/monitor.yml` cron expression.

### Add field monitoring
Add field name to `MONITOR_FIELDS` list and `FIELD_NAMES` dict in `monitor.py`.

### Debug API issues
```bash
python monitor.py --dump  # Raw API output
```

### Reset state (re-trigger all notifications)
```bash
echo '{}' > state.json
git add state.json && git commit -m "Reset state" && git push
```

## Known Issues

- **Cloudflare may block GitHub Actions IPs.** If cloudscraper stops working on Actions, may need to add retry logic or use a proxy.
- **GitHub Actions free tier limit.** Private repos get 2000 min/month. At 5-min intervals, this project uses ~4300 min/month. Either make the repo public (unlimited) or increase interval to 10+ min.
- **API returns empty when no airdrops.** This is normal behavior, not an error. Airdrops only appear when scheduled.

## Telegram Bot

- **Bot:** @laoliu (老六) — same bot as OpenClaw
- **Chat ID:** 156593700 (Joe's DM)
- Notifications are plain text, no markdown parsing
