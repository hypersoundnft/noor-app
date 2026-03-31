import sqlite3
from datetime import datetime, timezone as tz_utc
from typing import Dict, List, Optional

DB_PATH = "muslim_agent.db"


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, timeout=10)


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                status      TEXT NOT NULL CHECK(status IN ('active','paused','stopped')),
                verse_index INTEGER NOT NULL DEFAULT 0,
                start_date  TEXT NOT NULL,
                city_name   TEXT NOT NULL,
                lat         REAL NOT NULL,
                lon         REAL NOT NULL,
                timezone    TEXT NOT NULL,
                language    TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)


def _now() -> str:
    return datetime.now(tz_utc.utc).isoformat()


def upsert_user(
    user_id: int,
    status: str,
    verse_index: int,
    start_date: str,
    city_name: str,
    lat: float,
    lon: float,
    timezone: str,
    language: str,
) -> None:
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users
                (user_id, status, verse_index, start_date, city_name,
                 lat, lon, timezone, language, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                status=excluded.status,
                verse_index=excluded.verse_index,
                start_date=excluded.start_date,
                city_name=excluded.city_name,
                lat=excluded.lat,
                lon=excluded.lon,
                timezone=excluded.timezone,
                language=excluded.language,
                updated_at=excluded.updated_at
            """,
            (user_id, status, verse_index, start_date, city_name,
             lat, lon, timezone, language, now, now),
        )


def get_user(user_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_active_users() -> List[Dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM users WHERE status = 'active'"
        ).fetchall()
        return [dict(r) for r in rows]


def set_user_status(user_id: int, status: str) -> None:
    """Update user status. No-op if user_id does not exist."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET status=?, updated_at=? WHERE user_id=?",
            (status, _now(), user_id),
        )


def increment_verse_index(user_id: int) -> None:
    """Increment user verse index. No-op if user_id does not exist."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET verse_index=(verse_index+1)%6236, updated_at=? WHERE user_id=?",
            (_now(), user_id),
        )


def reset_verse_index(user_id: int) -> None:
    """Reset user verse index to 0. No-op if user_id does not exist."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET verse_index=0, updated_at=? WHERE user_id=?",
            (_now(), user_id),
        )
