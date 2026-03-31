"""Nominatim geocoding and Aladhan prayer time fetching."""

import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
ALADHAN_URL = "https://api.aladhan.com/v1/timings"
HEADERS = {"User-Agent": "muslim-agent-bot/1.0"}


def geocode_city(city: str):
    """Geocode a city string via Nominatim.

    Returns dict with keys: lat, lon, city_name, country_code, timezone.
    Returns None if city not found.
    """
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": city, "format": "json", "limit": 1, "addressdetails": 1},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    r = results[0]
    lat = float(r["lat"])
    lon = float(r["lon"])
    country_code = r.get("address", {}).get("country_code", "")
    tz = TimezoneFinder().timezone_at(lat=lat, lng=lon) or "UTC"
    return {
        "lat": lat,
        "lon": lon,
        "city_name": r["display_name"],
        "country_code": country_code,
        "timezone": tz,
    }


def language_for_country(country_code: str) -> str:
    """Return 'id' for Indonesia, 'en' for all other countries."""
    return "id" if country_code == "id" else "en"


def get_prayer_times(lat: float, lon: float, timezone: str, date=None):
    """Fetch prayer times from Aladhan for the given coordinates and date.

    Returns dict: {'fajr': 'HH:MM', 'dhuhr': ..., 'asr': ..., 'maghrib': ..., 'isha': ...}
    Raises on HTTP error.
    """
    if date is None:
        date = datetime.now(ZoneInfo(timezone))
    midnight = date.replace(hour=0, minute=0, second=0, microsecond=0)
    ts = int(midnight.timestamp())
    resp = requests.get(
        f"{ALADHAN_URL}/{ts}",
        params={"latitude": lat, "longitude": lon, "method": 2},
        timeout=10,
    )
    resp.raise_for_status()
    timings = resp.json()["data"]["timings"]
    return {
        "fajr": timings["Fajr"],
        "dhuhr": timings["Dhuhr"],
        "asr": timings["Asr"],
        "maghrib": timings["Maghrib"],
        "isha": timings["Isha"],
    }
