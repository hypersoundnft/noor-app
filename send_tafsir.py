"""Daily Quran Tafsir broadcaster — sends one verse per prayer slot to Telegram."""

import argparse
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

from quran_index import TOTAL_AYAHS, verse_index_to_surah_ayah

START_DATE = date(2026, 3, 16)  # slot 0 = Al-Fatiha 1:1

PRAYER_NAMES = ["Subuh", "Dzuhur", "Ashar", "Maghrib", "Isya"]

API_BASE = "https://quran-api-id.vercel.app"


def get_verse_for_slot(today: date, slot: int) -> tuple[int, int]:
    """Return (surah_number, ayah_number) for a given date and prayer slot (0–4)."""
    if today < START_DATE:
        raise ValueError(f"today ({today}) is before START_DATE ({START_DATE})")
    days_elapsed = (today - START_DATE).days
    verse_index = (days_elapsed * 5 + slot) % TOTAL_AYAHS
    return verse_index_to_surah_ayah(verse_index)


def fetch_verse_data(surah: int, ayah: int) -> dict:
    """Fetch verse from API and return a normalized dict.

    Keys: arabic, translation, tafsir, surah_name, surah_number, ayah_number
    Raises on HTTP error.
    """
    url = f"{API_BASE}/surah/{surah}/{ayah}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()["data"]
    return {
        "arabic": data["text"]["arab"],
        "translation": data["translation"]["id"],
        "tafsir": data["tafsir"]["id"]["short"],
        "surah_name": data["surah"]["name"]["transliteration"]["id"],
        "surah_number": data["surah"]["number"],
        "ayah_number": data["number"]["inSurah"],
    }


def format_message(verse: dict, slot: int) -> str:
    """Format a Telegram HTML message for the given verse and prayer slot.

    Uses HTML parse_mode so bold markers work without escaping Arabic/Indonesian text.
    """
    prayer = PRAYER_NAMES[slot]
    lines = [
        "🕌 <b>Tadabbur Al-Quran Harian</b>",
        "",
        f"📖 <b>Surah {verse['surah_name']} ({verse['surah_number']}) : Ayat {verse['ayah_number']}</b>",
        "",
        "﷽",
        verse["arabic"],
        "",
        "📝 <b>Terjemahan:</b>",
        verse["translation"],
        "",
        "💡 <b>Tafsir Al-Jalalain:</b>",
        verse["tafsir"],
        "",
        "—",
        f"🌙 Waktu: {prayer}",
    ]
    return "\n".join(lines)


def send_to_telegram(text: str, bot_token: str, channel_id: str) -> None:
    """Send an HTML-formatted message to a Telegram channel. Raises RuntimeError on failure."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "HTML",
    }
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result.get('description', 'unknown')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send daily Quran tafsir to Telegram")
    parser.add_argument("--slot", type=int, required=True, choices=range(5),
                        help="Prayer slot: 0=Subuh 1=Dzuhur 2=Ashar 3=Maghrib 4=Isya")
    args = parser.parse_args()

    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]

    today_wib = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    surah, ayah = get_verse_for_slot(today_wib, args.slot)
    verse = fetch_verse_data(surah, ayah)
    message = format_message(verse, args.slot)
    send_to_telegram(message, bot_token, channel_id)

    print(f"Sent: Surah {surah} Ayah {ayah} ({PRAYER_NAMES[args.slot]})")


if __name__ == "__main__":
    main()
