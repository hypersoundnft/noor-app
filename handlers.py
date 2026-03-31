"""Telegram command and conversation handlers."""

import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import db
from prayer_times import geocode_city, get_prayer_times, language_for_country
from quran_index import verse_index_to_surah_ayah
from send_tafsir import fetch_verse_data, format_message
from scheduler import add_user_jobs, remove_user_jobs, PRAYER_NAMES

logger = logging.getLogger(__name__)

WAITING_FOR_CITY = 0
DONE = ConversationHandler.END

MESSAGES = {
    "already_active": {
        "en": "You are already subscribed.",
        "id": "Kamu sudah berlangganan.",
    },
    "paused_redirect": {
        "en": "You have a paused subscription. Use /resume to continue.",
        "id": "Langgananmu sedang dijeda. Ketik /resume untuk melanjutkan.",
    },
    "ask_city": "What city are you in? (e.g. Jakarta, London, New York)",
    "city_not_found": "City not found. Please try again.",
    "city_not_found_final": (
        "Still couldn't find that city. Try the format: City, Country (e.g. 'Springfield, US')."
    ),
    "aladhan_error": {
        "en": "Could not fetch prayer times for {city}. Please try again later.",
        "id": "Tidak dapat mengambil waktu sholat untuk {city}. Silakan coba lagi nanti.",
    },
    "start_success": {
        "en": "Subscribed! You'll receive daily Quran verses at your prayer times in {city}. Here's your first verse:",
        "id": "Berlangganan! Kamu akan menerima ayat Al-Quran harian pada waktu sholat di {city}. Ini ayat pertamamu:",
    },
    "stop": {
        "en": "Subscription stopped. Your progress has been reset. Type /start to begin again from the first verse.",
        "id": "Langganan dihentikan. Progresmu telah direset. Ketik /start untuk mulai lagi dari ayat pertama.",
    },
    "pause": {
        "en": "Paused at Surah {surah} Ayah {ayah}. Type /resume to continue from where you left off.",
        "id": "Dijeda di Surah {surah} Ayah {ayah}. Ketik /resume untuk melanjutkan dari ayat yang sama.",
    },
    "resume_success": {
        "en": "Resumed! You will receive the next verse at your next prayer time.",
        "id": "Dilanjutkan! Kamu akan menerima ayat berikutnya pada waktu sholat berikutnya.",
    },
    "resume_already_active": {
        "en": "You are already receiving daily verses.",
        "id": "Kamu sudah menerima ayat harian.",
    },
    "resume_not_subscribed": {
        "en": "You don't have an active subscription. Type /start to begin.",
        "id": "Kamu belum berlangganan. Ketik /start untuk memulai.",
    },
    "help": {
        "en": (
            "Available commands:\n"
            "/start — Subscribe and start receiving daily Quran verses\n"
            "/stop — Unsubscribe and reset your progress\n"
            "/pause — Pause delivery (progress saved)\n"
            "/resume — Resume from where you paused\n"
            "/help — Show this message"
        ),
        "id": (
            "Perintah yang tersedia:\n"
            "/start — Berlangganan dan mulai menerima ayat Al-Quran harian\n"
            "/stop — Berhenti berlangganan dan reset progres\n"
            "/pause — Jeda pengiriman (progres tersimpan)\n"
            "/resume — Lanjutkan dari ayat yang terakhir\n"
            "/help — Tampilkan pesan ini"
        ),
    },
}


def _lang(user) -> str:
    return user["language"] if user else "en"


def _msg(key: str, lang: str, **kwargs) -> str:
    template = MESSAGES[key]
    if isinstance(template, dict):
        text = template.get(lang, template["en"])
    else:
        text = template
    return text.format(**kwargs) if kwargs else text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if user and user["status"] == "active":
        await update.message.reply_text(_msg("already_active", _lang(user)))
        return DONE
    if user and user["status"] == "paused":
        await update.message.reply_text(_msg("paused_redirect", _lang(user)))
        return DONE
    context.user_data["attempts"] = 0
    await update.message.reply_text(MESSAGES["ask_city"])
    return WAITING_FOR_CITY


async def receive_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city_input = update.message.text.strip()
    user_id = update.effective_user.id

    geo = geocode_city(city_input)
    if geo is None:
        attempts = context.user_data.get("attempts", 0) + 1
        context.user_data["attempts"] = attempts
        if attempts >= 3:
            await update.message.reply_text(MESSAGES["city_not_found_final"])
            return DONE
        await update.message.reply_text(MESSAGES["city_not_found"])
        return WAITING_FOR_CITY

    lang = language_for_country(geo["country_code"])
    try:
        prayer_times = get_prayer_times(geo["lat"], geo["lon"], geo["timezone"])
    except Exception as e:
        logger.error("Failed to fetch prayer times for city %s: %s", geo["city_name"], e)
        await update.message.reply_text(
            _msg("aladhan_error", lang, city=geo["city_name"])
        )
        return DONE

    today = date.today().isoformat()
    db.upsert_user(
        user_id=user_id,
        status="active",
        verse_index=0,
        start_date=today,
        city_name=geo["city_name"],
        lat=geo["lat"],
        lon=geo["lon"],
        timezone=geo["timezone"],
        language=lang,
    )

    user = db.get_user(user_id)
    add_user_jobs(context.bot, user, prayer_times, db)

    await update.message.reply_text(_msg("start_success", lang, city=geo["city_name"]))

    # Send first verse immediately
    surah, ayah = verse_index_to_surah_ayah(0)
    try:
        verse = fetch_verse_data(surah, ayah, lang)
        prayer_name = PRAYER_NAMES[lang]["fajr"]
        msg = format_message(verse, prayer_name, lang)
        await update.message.reply_text(msg, parse_mode="HTML")
        db.increment_verse_index(user_id)
    except Exception as e:
        logger.error("Failed to send first verse to %s: %s", user_id, e)

    return DONE


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("You don't have an active subscription. Type /start to begin.")
        return
    lang = _lang(user)
    remove_user_jobs(user_id)
    db.set_user_status(user_id, "stopped")
    db.reset_verse_index(user_id)
    await update.message.reply_text(_msg("stop", lang))


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("You don't have an active subscription. Type /start to begin.")
        return
    lang = _lang(user)
    remove_user_jobs(user_id)
    db.set_user_status(user_id, "paused")
    surah, ayah = verse_index_to_surah_ayah(user["verse_index"])
    await update.message.reply_text(_msg("pause", lang, surah=surah, ayah=ayah))


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    lang = _lang(user)

    if not user or user["status"] == "stopped":
        await update.message.reply_text(_msg("resume_not_subscribed", lang))
        return
    if user["status"] == "active":
        await update.message.reply_text(_msg("resume_already_active", lang))
        return

    # status == "paused"
    try:
        prayer_times = get_prayer_times(user["lat"], user["lon"], user["timezone"])
    except Exception:
        await update.message.reply_text(
            _msg("aladhan_error", lang, city=user["city_name"])
        )
        return

    db.set_user_status(user_id, "active")
    add_user_jobs(context.bot, user, prayer_times, db)
    await update.message.reply_text(_msg("resume_success", lang))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    await update.message.reply_text(_msg("help", _lang(user)))
