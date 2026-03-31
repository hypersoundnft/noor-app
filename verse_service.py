"""Bilingual Quran verse fetching and message formatting for the personal bot."""

import requests

API_ID_BASE = "https://quran-api-id.vercel.app"
API_EN_BASE = "https://api.alquran.cloud/v1/ayah"

LABELS = {
    "id": {
        "header": "Tadabbur Al-Quran Harian",
        "translation": "Terjemahan:",
        "tafsir": "Tafsir Al-Jalalain:",
        "time": "Waktu:",
        "verse_label": "Ayat",
        "hadith_header": "Hadits Pilihan",
        "hadith_source": "Sumber",
    },
    "en": {
        "header": "Daily Quran Reflection",
        "translation": "Translation:",
        "tafsir": None,
        "time": "Time:",
        "verse_label": "Verse",
        "hadith_header": "Hadith of the Prayer",
        "hadith_source": "Source",
    },
}


def fetch_verse_data(surah: int, ayah: int, language: str) -> dict:
    """Fetch verse and return normalised dict.

    Keys: arabic, translation, tafsir, surah_name, surah_number, ayah_number.
    """
    if language not in LABELS:
        raise ValueError(f"Unsupported language: {language!r}")
    if language == "id":
        return _fetch_id(surah, ayah)
    return _fetch_en(surah, ayah)


def _fetch_id(surah: int, ayah: int) -> dict:
    url = f"{API_ID_BASE}/surah/{surah}/{ayah}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()["data"]
    return {
        "arabic": data["text"]["arab"],
        "translation": data["translation"]["id"],
        "tafsir": data["tafsir"]["id"]["short"],
        "surah_name": data["surah"]["name"]["transliteration"]["id"],
        "surah_number": data["surah"]["number"],
        "ayah_number": data["number"]["inSurah"],
    }


def _fetch_en(surah: int, ayah: int) -> dict:
    ref = f"{surah}:{ayah}"
    t_resp = requests.get(f"{API_EN_BASE}/{ref}/en.asad", timeout=10)
    t_resp.raise_for_status()
    t_data = t_resp.json()["data"]
    a_resp = requests.get(f"{API_EN_BASE}/{ref}/ar.alafasy", timeout=10)
    a_resp.raise_for_status()
    return {
        "arabic": a_resp.json()["data"]["text"],
        "translation": t_data["text"],
        "tafsir": "",
        "surah_name": t_data["surah"]["englishName"],
        "surah_number": t_data["surah"]["number"],
        "ayah_number": t_data["numberInSurah"],
    }


def format_message(verse: dict, prayer_name: str, language: str, hadith=None) -> str:
    """Format an HTML Telegram message for the given verse, prayer name, and language."""
    L = LABELS[language]
    lines = [
        f"🕌 <b>{L['header']}</b>",
        "",
        f"📖 <b>Surah {verse['surah_name']} ({verse['surah_number']}) : {L['verse_label']} {verse['ayah_number']}</b>",
        "",
        "﷽",
        verse["arabic"],
        "",
        f"📝 <b>{L['translation']}</b>",
        verse["translation"],
    ]
    if verse.get("tafsir"):
        lines += [
            "",
            f"💡 <b>{L['tafsir']}</b>",
            verse["tafsir"],
        ]
    if hadith and hadith.get("text"):
        lines += [
            "",
            f"📜 <b>{L['hadith_header']}</b>",
            "",
        ]
        if hadith.get("arab"):
            lines += [hadith["arab"], ""]
        lines += [
            hadith["text"],
            "",
            f"<i>— {L['hadith_source']}: {hadith['collection_name']}, No. {hadith['number']}</i>",
        ]
    lines += [
        "",
        "—",
        f"🌙 {L['time']} {prayer_name}",
    ]
    return "\n".join(lines)
