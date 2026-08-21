import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config.settings import settings
from .models.db_check import DBHealthResponse, DBCheckRow

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    distance_km REAL NOT NULL DEFAULT 0.0,
    duration_sec INTEGER NOT NULL DEFAULT 0,
    avg_speed_kmh REAL NOT NULL DEFAULT 0.0,
    max_speed_kmh REAL NOT NULL DEFAULT 0.0,
    start_latitude REAL,
    start_longitude REAL,
    end_latitude REAL,
    end_longitude REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS db_check (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_date TEXT NOT NULL,
    created_by TEXT NOT NULL
);
"""


def _ensure_database() -> Path:
    """Create the database directory and file if they do not exist."""
    db_file = settings.database_file
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_file


def init_db() -> None:
    """Create the database file and all tables if they do not exist."""
    db_file = _ensure_database()
    with sqlite3.connect(db_file) as conn:
        # Migrate old trips table schema if needed
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trips'"
        )
        if cursor.fetchone():
            cursor = conn.execute("PRAGMA table_info(trips)")
            columns = [row[1] for row in cursor.fetchall()]
            if "trim_name" in columns:
                conn.execute("DROP TABLE trips")
        conn.executescript(SCHEMA_SQL)


@contextmanager
def get_db_connection():
    """Yield a SQLite connection with row access by column name."""
    db_file = _ensure_database()
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_db_health() -> DBHealthResponse:
    """Open SQLite, insert a db_check row, select it back, verify, and return health status."""
    from datetime import datetime

    check_date = datetime.now().astimezone().isoformat()
    created_by = "healthcheck"

    with get_db_connection() as conn:
        # Insert a health-check row
        cursor = conn.execute(
            "INSERT INTO db_check (check_date, created_by) VALUES (?, ?)",
            (check_date, created_by),
        )
        inserted_id = cursor.lastrowid

        # Select the inserted row back to verify
        cursor = conn.execute(
            "SELECT id, check_date, created_by FROM db_check WHERE id = ?",
            (inserted_id,),
        )
        row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Database health check failed: inserted row could not be verified")

    db_check_row = DBCheckRow(
        id=row["id"],
        check_date=row["check_date"],
        created_by=row["created_by"],
    )

    return DBHealthResponse(
        status="healthy",
        database="sqlite",
        check_date=db_check_row.check_date,
        created_by=db_check_row.created_by,
    )


# Ensure the database and tables exist when the module is imported.
# Tolerate failures so the app can still start and /healthcheck/db reports 503.
try:
    init_db()
except Exception:
    pass
