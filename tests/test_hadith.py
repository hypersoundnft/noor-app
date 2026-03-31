import pytest
from unittest.mock import patch, MagicMock
from hadith import fetch_hadith, _fetch_en, _fetch_id


def _cdn_mock(text="Narrated Abu Hurairah: ...", arab="حَدَّثَنَا"):
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "hadiths": [{"text": text, "arab": arab}],
        "metadata": {"name": "Sahih al-Bukhari"},
    }
    return mock


def _gading_mock(id_text="Diriwayatkan oleh Abu Hurairah...", arab="حَدَّثَنَا"):
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "name": "Hadits Bukhari",
        "hadiths": {"number": 1, "arab": arab, "id": id_text},
    }
    return mock


# ── _fetch_en ─────────────────────────────────────────────────────────────────

def test_fetch_en_returns_expected_keys():
    with patch("hadith.requests.get", return_value=_cdn_mock()):
        result = _fetch_en("Imam Bukhari", "eng-bukhari", 100)
    assert result["text"] == "Narrated Abu Hurairah: ..."
    assert result["arab"] == "حَدَّثَنَا"
    assert result["collection_name"] == "Imam Bukhari"
    assert 1 <= result["number"] <= 100


def test_fetch_en_raises_on_http_error():
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("404")
    with patch("hadith.requests.get", return_value=mock):
        with pytest.raises(Exception):
            _fetch_en("Imam Bukhari", "eng-bukhari", 100)


# ── _fetch_id ─────────────────────────────────────────────────────────────────

def test_fetch_id_returns_expected_keys():
    with patch("hadith.requests.get", return_value=_gading_mock()):
        result = _fetch_id("Imam Bukhari", "bukhari", 100)
    assert result["text"] == "Diriwayatkan oleh Abu Hurairah..."
    assert result["arab"] == "حَدَّثَنَا"
    assert result["collection_name"] == "Imam Bukhari"
    assert 1 <= result["number"] <= 100


def test_fetch_id_raises_on_http_error():
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("503")
    with patch("hadith.requests.get", return_value=mock):
        with pytest.raises(Exception):
            _fetch_id("Imam Bukhari", "bukhari", 100)


# ── fetch_hadith ──────────────────────────────────────────────────────────────

def test_fetch_hadith_english_returns_dict():
    with patch("hadith.requests.get", return_value=_cdn_mock()):
        result = fetch_hadith("en")
    assert result is not None
    assert "text" in result
    assert "collection_name" in result


def test_fetch_hadith_indonesian_uses_gading():
    with patch("hadith.requests.get", return_value=_gading_mock()) as mock_get:
        result = fetch_hadith("id")
    assert result is not None
    assert result["text"] == "Diriwayatkan oleh Abu Hurairah..."
    called_url = mock_get.call_args[0][0]
    assert "hadith.gading.dev" in called_url


def test_fetch_hadith_indonesian_falls_back_to_english():
    gading_fail = MagicMock()
    gading_fail.raise_for_status.side_effect = Exception("503")
    with patch("hadith.requests.get", side_effect=[gading_fail, _cdn_mock()]):
        result = fetch_hadith("id")
    assert result is not None
    assert result["text"] == "Narrated Abu Hurairah: ..."


def test_fetch_hadith_returns_none_on_total_failure():
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("503")
    with patch("hadith.requests.get", return_value=mock):
        result = fetch_hadith("en")
    assert result is None


def test_fetch_hadith_unknown_language_uses_english():
    with patch("hadith.requests.get", return_value=_cdn_mock()) as mock_get:
        result = fetch_hadith("fr")
    assert result is not None
    called_url = mock_get.call_args[0][0]
    assert "cdn.jsdelivr.net" in called_url
