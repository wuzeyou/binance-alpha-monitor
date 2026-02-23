# Binance Alpha Airdrop Monitor

Monitors [Binance Alpha](https://www.binance.com/) airdrop announcements and sends real-time Telegram notifications when new airdrops are detected or existing ones are updated.

## How It Works

1. **Data source**: Fetches airdrop data from [alpha123.uk](https://alpha123.uk) API (a third-party Binance Alpha aggregator)
2. **Change detection**: Compares against `state.json` to detect new airdrops or field changes (time, amount, points, type, status)
3. **Notification**: Sends Telegram messages via Bot API when changes are found
4. **State persistence**: Commits updated `state.json` back to the repo via GitHub Actions

## Architecture

```
GitHub Actions (every 5 min)
  → monitor.py fetches alpha123.uk/api/data
  → Compares with state.json
  → New/updated airdrops → Telegram Bot API → Your DM
  → Commits state.json back to repo
```

No local resources needed. Runs entirely on GitHub's free tier.

## Setup

### 1. Fork or clone this repo

### 2. Set GitHub Secrets

Go to repo **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|--------|-------|
| `TG_BOT_TOKEN` | Your Telegram bot token (from @BotFather) |
| `TG_CHAT_ID` | Your Telegram user ID (numeric) |

### 3. Enable GitHub Actions

The workflow runs automatically every 5 minutes. You can also trigger it manually from the **Actions** tab.

## Local Usage

```bash
# Install dependencies
pip install cloudscraper requests

# Initialize state (records current airdrops without notifying)
python monitor.py --init

# Run a single check
python monitor.py

# Dump raw airdrop data from API
python monitor.py --dump
```

### Output Format

- No changes: `OK: 没有新空投或更新`
- New airdrop: JSON line with `{"type": "new", "text": "...", "token": "..."}`
- Updated airdrop: JSON line with `{"type": "update", "text": "...", "token": "..."}`

## Monitored Fields

| Field | Description |
|-------|-------------|
| `token` | Token symbol (e.g. BLESS) |
| `name` | Project name |
| `date` | Airdrop date |
| `time` | Airdrop time |
| `amount` | Airdrop amount |
| `points` | Required Alpha points |
| `type` | Type: `tge` / `grab` (first-come) / `warning` (prediction) |
| `phase` | Phase number (1 or 2) |
| `completed` | Whether the airdrop is finished |

## Deduplication

Each airdrop is keyed by `{token}_{date}_P{phase}`. The monitor tracks 6 fields for changes: `name`, `time`, `amount`, `points`, `type`, `completed`.

## Notification Examples

**New airdrop:**
```
🎁 新 Alpha 空投: BLESS
项目: Bless
时间: 2026-01-08 20:00
数量: 2500
积分: 251
类型: 先到先得
详情: https://alpha123.uk/zh/
```

**Updated airdrop:**
```
📢 空投信息更新: BLESS
  时间: 待公布 → 20:00
  积分: 待公布 → 251
详情: https://alpha123.uk/zh/
```

## Notes

- **Cloudflare**: alpha123.uk uses Cloudflare protection. The script uses `cloudscraper` to bypass it. If it stops working, may need to update cloudscraper or switch to a headless browser approach.
- **Rate limits**: The API may rate-limit aggressive polling. 5-minute intervals work fine.
- **GitHub Actions free tier**: 2000 minutes/month for private repos. At ~30s per run × 288 runs/day ≈ 144 min/day ≈ 4320 min/month. This exceeds the free tier for private repos. Consider making the repo public or reducing frequency to every 10 minutes.

## License

MIT
