"""Hadith fetching from popular Imam collections.

English: fawazahmed0/hadith-api via jsDelivr CDN
Indonesian: api.hadith.gading.dev
Falls back to English if the Indonesian API fails.
"""

import random
import requests

_CDN = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions"
_GADING = "https://api.hadith.gading.dev/books"

# (display_name, cdn_edition, hadith_count)
_EN_COLLECTIONS = [
    ("Imam Bukhari", "eng-bukhari", 7563),
    ("Imam Muslim", "eng-muslim", 5362),
    ("Abu Dawud", "eng-abudawud", 5274),
    ("Imam Tirmidhi", "eng-tirmidhi", 3956),
]

# (display_name, gading_book_id, hadith_count)
_ID_COLLECTIONS = [
    ("Imam Bukhari", "bukhari", 7563),
    ("Imam Muslim", "muslim", 7453),
    ("Abu Dawud", "abu-daud", 5274),
    ("Imam Tirmidhi", "tirmidzi", 3956),
]


def _fetch_en(name: str, edition: str, size: int) -> dict:
    number = random.randint(1, size)
    url = f"{_CDN}/{edition}/{number}.min.json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    hadith = data["hadiths"][0]
    return {
        "text": hadith.get("text", ""),
        "arab": hadith.get("arab", ""),
        "collection_name": name,
        "number": number,
    }


def _fetch_id(name: str, book: str, size: int) -> dict:
    number = random.randint(1, size)
    url = f"{_GADING}/{book}/{number}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    h = data["hadiths"]  # single object (not a list) in this API
    return {
        "text": h.get("id", ""),
        "arab": h.get("arab", ""),
        "collection_name": name,
        "number": number,
    }


def fetch_hadith(language: str):
    """Return a random hadith dict or None on failure.

    Dict keys: text, arab, collection_name, number.
    """
    if language == "id":
        name, book, size = random.choice(_ID_COLLECTIONS)
        try:
            return _fetch_id(name, book, size)
        except Exception:
            pass  # fall through to English

    name, edition, size = random.choice(_EN_COLLECTIONS)
    try:
        return _fetch_en(name, edition, size)
    except Exception:
        return None
