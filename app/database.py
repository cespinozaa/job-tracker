import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "job_tracker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS resume (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    job_description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'applied',
    date_applied DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gap_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    matched_keywords TEXT NOT NULL,
    missing_keywords TEXT NOT NULL,
    suggestions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id)
);
"""


def get_connection() -> sqlite3.Connection:
    """
    Returns a new SQLite connection with foreign keys enabled and
    row access by column name (instead of index).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Creates tables if they don't already exist. Safe to call every startup."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_resume() -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM resume ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row


def save_resume(filename: str, raw_text: str) -> None:
    """Replaces the existing resume (only the latest is kept, no history)."""
    conn = get_connection()
    conn.execute("DELETE FROM resume")
    conn.execute(
        "INSERT INTO resume (filename, raw_text) VALUES (?, ?)",
        (filename, raw_text),
    )
    conn.commit()
    conn.close()


def create_application(
    company: str, title: str, job_description: str, notes: str | None = None
) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO applications (company, title, job_description, notes) "
        "VALUES (?, ?, ?, ?)",
        (company, title, job_description, notes),
    )
    conn.commit()
    application_id = cur.lastrowid
    conn.close()
    return application_id


def get_applications() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM applications ORDER BY date_applied DESC, id DESC"
    ).fetchall()
    conn.close()
    return rows


def get_application(application_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM applications WHERE id = ?", (application_id,)
    ).fetchone()
    conn.close()
    return row