"""APScheduler setup and per-user job management."""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

from prayer_times import get_prayer_times

logger = logging.getLogger(__name__)

PRAYER_SLOTS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

PRAYER_NAMES = {
    "id": {
        "fajr": "Subuh", "dhuhr": "Dzuhur", "asr": "Ashar",
        "maghrib": "Maghrib", "isha": "Isya",
    },
    "en": {
        "fajr": "Fajr", "dhuhr": "Dhuhr", "asr": "Asr",
        "maghrib": "Maghrib", "isha": "Isha",
    },
}

scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(url="sqlite:///scheduler.db")}
)


def _parse_hhmm(t: str) -> tuple:
    """Parse 'HH:MM' string into (hour, minute) integers."""
    h, m = t.split(":")
    return int(h), int(m)


async def _send_verse(bot, user_id: int, slot: str, db_module) -> None:
    """Fetch and send the next verse for a user. Increments verse_index on success."""
    from verse_service import fetch_verse_data, format_message
    from quran_index import verse_index_to_surah_ayah
    from hadith import fetch_hadith
    from telegram.error import Forbidden

    user = db_module.get_user(user_id)
    if not user or user["status"] != "active":
        return
    surah, ayah = verse_index_to_surah_ayah(user["verse_index"])
    lang = user["language"]
    prayer_name = PRAYER_NAMES[lang][slot]
    try:
        verse = fetch_verse_data(surah, ayah, lang)
        hadith = fetch_hadith(lang)
        msg = format_message(verse, prayer_name, lang, hadith=hadith)
        await bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
        db_module.increment_verse_index(user_id)
    except Forbidden:
        logger.warning("User %s blocked the bot — setting stopped and removing jobs.", user_id)
        db_module.set_user_status(user_id, "stopped")
        remove_user_jobs(user_id)
    except Exception as e:
        logger.error("Failed to send verse to user %s: %s", user_id, e)


async def _refresh_prayer_times(bot, user_id: int, db_module) -> None:
    """Midnight job: re-fetch prayer times and reschedule prayer jobs."""
    user = db_module.get_user(user_id)
    if not user or user["status"] != "active":
        return
    try:
        times = get_prayer_times(user["lat"], user["lon"], user["timezone"])
        reschedule_prayer_jobs(user_id, times, user["timezone"])
    except Exception as e:
        logger.warning("Could not refresh prayer times for user %s: %s", user_id, e)


def add_user_jobs(bot, user: dict, prayer_times: dict, db_module) -> None:
    """Register 5 prayer jobs + 1 midnight refresh job for a user."""
    user_id = user["user_id"]
    tz = user["timezone"]
    for slot in PRAYER_SLOTS:
        hour, minute = _parse_hhmm(prayer_times[slot])
        scheduler.add_job(
            _send_verse,
            CronTrigger(hour=hour, minute=minute, timezone=tz),
            id=f"send_{user_id}_{slot}",
            args=[bot, user_id, slot, db_module],
            replace_existing=True,
        )
    scheduler.add_job(
        _refresh_prayer_times,
        CronTrigger(hour=0, minute=1, timezone=tz),
        id=f"refresh_{user_id}",
        args=[bot, user_id, db_module],
        replace_existing=True,
    )


def remove_user_jobs(user_id: int) -> None:
    """Cancel all scheduled jobs for a user."""
    for slot in PRAYER_SLOTS:
        try:
            scheduler.remove_job(f"send_{user_id}_{slot}")
        except Exception:
            pass
    try:
        scheduler.remove_job(f"refresh_{user_id}")
    except Exception:
        pass


def reschedule_prayer_jobs(user_id: int, prayer_times: dict, tz: str) -> None:
    """Update the cron triggers for existing prayer jobs without removing them."""
    for slot in PRAYER_SLOTS:
        hour, minute = _parse_hhmm(prayer_times[slot])
        try:
            scheduler.reschedule_job(
                f"send_{user_id}_{slot}",
                trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
            )
        except Exception as e:
            logger.warning("Could not reschedule %s for user %s: %s", slot, user_id, e)


def load_user_jobs(bot, user: dict, db_module) -> None:
    """Re-register jobs for a user on bot startup. Fetches fresh prayer times."""
    try:
        times = get_prayer_times(user["lat"], user["lon"], user["timezone"])
        add_user_jobs(bot, user, times, db_module)
    except Exception as e:
        logger.warning(
            "Could not load jobs for user %s at startup: %s", user["user_id"], e
        )
