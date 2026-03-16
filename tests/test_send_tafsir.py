import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from send_tafsir import (
    get_verse_for_slot,
    fetch_verse_data,
    format_message,
    send_to_telegram,
    PRAYER_NAMES,
    START_DATE,
)


# ── get_verse_for_slot ────────────────────────────────────────────────────────

def test_get_verse_for_slot_start_date_slot_0():
    """Day 0, slot 0 → verse_index 0 → Surah 1, Ayah 1."""
    surah, ayah = get_verse_for_slot(START_DATE, 0)
    assert surah == 1
    assert ayah == 1

def test_get_verse_for_slot_start_date_slot_4():
    """Day 0, slot 4 → verse_index 4 → Surah 1, Ayah 5."""
    surah, ayah = get_verse_for_slot(START_DATE, 4)
    assert surah == 1
    assert ayah == 5

def test_get_verse_for_slot_day_1_slot_0():
    """Day 1, slot 0 → verse_index 5 → Surah 1, Ayah 6."""
    d = date(START_DATE.year, START_DATE.month, START_DATE.day)
    from datetime import timedelta
    d = d + timedelta(days=1)
    surah, ayah = get_verse_for_slot(d, 0)
    assert surah == 1
    assert ayah == 6

def test_get_verse_for_slot_wraps():
    """After all 6236 ayahs, wraps back to Surah 1 Ayah 1."""
    from datetime import timedelta
    # 1247*5+1 = 6236 → index 0 after %
    d = START_DATE + timedelta(days=1247)
    surah, ayah = get_verse_for_slot(d, 1)
    assert surah == 1
    assert ayah == 1


# ── fetch_verse_data ──────────────────────────────────────────────────────────

def test_fetch_verse_data_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "text": {"arab": "بِسْمِ اللَّهِ"},
            "translation": {"id": "Dengan nama Allah"},
            "tafsir": {"id": {"short": "Tafsir pendek"}},
            "surah": {
                "number": 1,
                "name": {"transliteration": {"id": "Al-Fatihah"}},
            },
            "number": {"inSurah": 1},
        }
    }
    with patch("send_tafsir.requests.get", return_value=mock_response):
        result = fetch_verse_data(1, 1)
    assert result["arabic"] == "بِسْمِ اللَّهِ"
    assert result["translation"] == "Dengan nama Allah"
    assert result["tafsir"] == "Tafsir pendek"
    assert result["surah_name"] == "Al-Fatihah"
    assert result["surah_number"] == 1
    assert result["ayah_number"] == 1


def test_fetch_verse_data_raises_on_http_error():
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("404 Not Found")
    with patch("send_tafsir.requests.get", return_value=mock_response):
        with pytest.raises(Exception):
            fetch_verse_data(1, 1)


# ── format_message ────────────────────────────────────────────────────────────

def test_format_message_contains_required_parts():
    verse = {
        "arabic": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "translation": "Dengan nama Allah Yang Maha Pengasih, Maha Penyayang.",
        "tafsir": "Tafsir singkat.",
        "surah_name": "Al-Fatihah",
        "surah_number": 1,
        "ayah_number": 1,
    }
    msg = format_message(verse, slot=0)
    assert "🕌 <b>Tadabbur Al-Quran Harian</b>" in msg
    assert "<b>Surah Al-Fatihah (1) : Ayat 1</b>" in msg
    assert "بِسْمِ اللَّهِ" in msg
    assert "<b>Terjemahan:</b>" in msg
    assert "Dengan nama Allah" in msg
    assert "<b>Tafsir Al-Jalalain:</b>" in msg
    assert "Tafsir singkat." in msg
    assert PRAYER_NAMES[0] in msg  # "Subuh"


# ── send_to_telegram ──────────────────────────────────────────────────────────

def test_send_to_telegram_calls_api():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    with patch("send_tafsir.requests.post", return_value=mock_response) as mock_post:
        send_to_telegram("Hello", "BOT_TOKEN", "CHANNEL_ID")
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "BOT_TOKEN" in call_args[0][0]
    assert call_args[1]["json"]["chat_id"] == "CHANNEL_ID"
    assert call_args[1]["json"]["text"] == "Hello"
    assert call_args[1]["json"]["parse_mode"] == "HTML"


def test_send_to_telegram_raises_on_failure():
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "description": "Bad Request"}
    mock_response.status_code = 400
    with patch("send_tafsir.requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="Telegram API error"):
            send_to_telegram("Hello", "BOT_TOKEN", "CHANNEL_ID")
