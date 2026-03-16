# Daily Tafsir Agent — Design Spec

**Date:** 2026-03-16
**Status:** Approved

---

## Overview

A Telegram channel bot that automatically broadcasts one Quran verse (Arabic text + Indonesian translation + Al-Jalalain tafsir in Indonesian) five times per day, aligned with the five daily prayer times (WIB/UTC+7). Verses progress sequentially through the Quran, calculated statelessly from a fixed start date.

---

## Goals

- Deliver daily Quranic reflection to subscribers via a read-only Telegram channel
- Cover Arabic text, Indonesian translation, and Al-Jalalain tafsir in every message
- Require zero manual operation after initial setup
- No server, no database — runs entirely on GitHub Actions (free tier)

---

## Architecture

```
GitHub Actions (5 cron jobs)
         ↓
send_tafsir.py --slot <0-4>
         ↓
quran-api-id.vercel.app API  →  Arabic + Indonesian translation + Al-Jalalain tafsir
         ↓
Telegram Bot API  →  Channel broadcast (read-only for subscribers)
```

---

## Verse Selection (Stateless)

The Quran has 6,236 total ayahs. Verse selection is deterministic — no state file or database needed.

```python
START_DATE   = date(2026, 3, 17)   # Slot 0 = Al-Fatiha 1:1
days_elapsed = (today - START_DATE).days
verse_index  = (days_elapsed * 5 + slot) % 6236
```

`verse_index` is mapped to `(surah_number, ayah_number)` via a hardcoded lookup table of cumulative ayah offsets per surah. This mapping is precomputed and stored in `quran_index.py`.

If GitHub Actions misses a run, the next run automatically sends the correct verse for that time — no manual correction needed.

---

## Schedule

Five cron triggers per day (times in WIB = UTC+7):

| Slot | Prayer  | WIB Time | UTC Cron       |
|------|---------|----------|----------------|
| 0    | Subuh   | 06:00    | `0 23 * * *`   |
| 1    | Dzuhur  | 13:00    | `0 6 * * *`    |
| 2    | Ashar   | 16:00    | `0 9 * * *`    |
| 3    | Maghrib | 18:30    | `30 11 * * *`  |
| 4    | Isya    | 19:30    | `30 12 * * *`  |

---

## Data Source

**API:** `https://quran-api-id.vercel.app`
**Endpoint:** `GET /surahs/{surah}/ayahs/{ayah}`

Response provides:
- Arabic text of the verse
- Indonesian translation (Kemenag)
- Al-Jalalain tafsir in Indonesian

---

## Message Format

```
🕌 *Tadabbur Al-Quran Harian*

📖 *Surah Al-Baqarah (2) : Ayat 255*

﷽
[Arabic text]

📝 *Terjemahan:*
[Indonesian translation]

💡 *Tafsir Al-Jalalain:*
[Indonesian tafsir]

—
🌙 Waktu: Ashar
```

Sent using Telegram MarkdownV2 formatting. Arabic text is rendered right-to-left naturally in Telegram clients.

---

## Telegram Setup

- **Bot**: Created via @BotFather, token stored as GitHub Secret `TELEGRAM_BOT_TOKEN`
- **Channel**: Public read-only Telegram channel; bot added as admin with post permission
- **Channel ID**: Stored as GitHub Secret `TELEGRAM_CHANNEL_ID` (e.g., `@tafsir_harian_id`)
- **Subscriber experience**: Users join the channel link, receive messages passively, cannot reply

---

## Repository Structure

```
muslim-agent/
├── .github/
│   └── workflows/
│       └── daily-tafsir.yml     # 5 cron triggers, each calls send_tafsir.py --slot N
├── send_tafsir.py               # Core script: calculate verse, fetch API, send to Telegram
├── quran_index.py               # Hardcoded surah ayah offset lookup table (6236 ayahs)
├── requirements.txt             # requests
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-03-16-daily-tafsir-agent-design.md
```

---

## Error Handling

- If the API call fails (network error, timeout), the script exits with a non-zero code — GitHub Actions marks the run as failed and sends an email notification to the repo owner
- No retry logic needed: the next scheduled slot will send its own verse correctly regardless
- Telegram send failures are also propagated as non-zero exit codes

---

## GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | Channel username or numeric ID |

---

## Out of Scope

- User commands (`/start`, `/stop`, `/today`)
- Audio recitation
- Push notifications beyond Telegram
- Multiple language support (English, Arabic UI)
- Admin dashboard or verse management UI
