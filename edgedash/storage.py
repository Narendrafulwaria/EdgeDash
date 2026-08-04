"""
The ONLY module that may import sqlite3.

All other modules interact with the database through the functions here.
Swapping SQLite for Postgres in week 4 means editing this file only —
function signatures and return types stay the same.
"""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Sequence

from edgedash._schema import SCHEMA

Row = dict[str, Any]

_db_path: str = ""


def configure(path: str) -> None:
    """Set the database path before any other function is called."""
    global _db_path
    _db_path = path


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    if not _db_path:
        raise RuntimeError("Call storage.configure(path) before use.")
    con = sqlite3.connect(_db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db(path: str) -> None:
    """Create all tables if absent, then configure the module."""
    configure(path)
    with _conn() as con:
        con.executescript(SCHEMA)


def make_listing_id(source: str, url: str) -> str:
    """Return a stable SHA-256 hash of source + url for deduplication."""
    return hashlib.sha256(f"{source}::{url}".encode()).hexdigest()


def upsert_listings(rows: Sequence[Row]) -> int:
    """Insert listings, skipping rows whose id already exists.

    Returns the count of genuinely NEW rows inserted (not the total passed in),
    so deduplication is visible to the caller.
    """
    if not rows:
        return 0

    sql = """
        INSERT OR IGNORE INTO listings
            (id, title, company, location, url, description,
             source, posted_at, fetched_at)
        VALUES
            (:id, :title, :company, :location, :url, :description,
             :source, :posted_at, :fetched_at)
    """
    with _conn() as con:
        before: int = con.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        con.executemany(sql, rows)
        after: int = con.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    return after - before


def count_unscored() -> int:
    """Return the number of listings that have not yet been scored."""
    with _conn() as con:
        result = con.execute(
            "SELECT COUNT(*) FROM listings WHERE fit_score IS NULL"
        ).fetchone()
    return int(result[0])


def last_fetch_time() -> datetime | None:
    """Return the most recent fetched_at timestamp, or None if no rows exist."""
    with _conn() as con:
        result = con.execute("SELECT MAX(fetched_at) FROM listings").fetchone()
    raw: str | None = result[0]
    return datetime.fromisoformat(raw) if raw else None


def get_listings(limit: int = 50, min_score: int = 0) -> list[Row]:
    """Return scored listings at or above min_score, newest fetched first."""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT * FROM listings
            WHERE fit_score IS NOT NULL AND fit_score >= :min_score
            ORDER BY fetched_at DESC
            LIMIT :limit
            """,
            {"min_score": min_score, "limit": limit},
        ).fetchall()
    return [dict(r) for r in rows]


def log_cycle(
    agent: str,
    started_at: datetime,
    finished_at: datetime,
    records_touched: int,
    status: str,
    notes: str | None = None,
) -> None:
    """Write one row to cycle_log for a completed agent run."""
    with _conn() as con:
        con.execute(
            """
            INSERT INTO cycle_log
                (agent, started_at, finished_at, records_touched, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agent, started_at.isoformat(), finished_at.isoformat(),
             records_touched, status, notes),
        )
