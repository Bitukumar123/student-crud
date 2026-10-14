"""SQLite connection handling and schema creation."""
import os
import sqlite3
from pathlib import Path
from typing import Iterator

DEFAULT_DB = Path(__file__).resolve().parent.parent / "students.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    date_of_birth   TEXT NOT NULL,              -- ISO format: YYYY-MM-DD
    email           TEXT UNIQUE COLLATE NOCASE, -- NULLs are allowed, duplicates are not
    phone           TEXT,
    course          TEXT,
    address         TEXT,
    enrollment_date TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_db_path() -> str:
    """Read the path at call time so tests can point to a temporary file."""
    return os.environ.get("STUDENTS_DB", str(DEFAULT_DB))


def connect() -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may run a request's dependency and
    # endpoint in different worker threads. Each request has its own connection.
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, always closed."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
