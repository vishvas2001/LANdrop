from contextlib import closing
import sqlite3
from typing import Any


def get_connection(db_path: str = "landrop.db") -> sqlite3.Connection:
    """Open a SQLite connection configured to return dict-like Row objects."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path: str = "landrop.db") -> None:
    """Create the files table if it does not already exist."""
    query = """
        CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            original_name TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """
    with closing(get_connection(db_path)) as con:
        with con:
            con.execute(query)


def insert_file(file_record: dict[str, Any], db_path: str = "landrop.db") -> None:
    """Insert a new file metadata record into the database."""
    query = """
        INSERT INTO files (file_id, original_name, stored_path, size_bytes, created_at, expires_at)
        VALUES (:file_id, :original_name, :stored_path, :size_bytes, :created_at, :expires_at)
    """
    with closing(get_connection(db_path)) as con:
        with con:
            con.execute(query, file_record)


def get_file(file_id: str, db_path: str = "landrop.db") -> dict[str, Any] | None:
    """Fetch a single file record by its file_id, or return None if not found."""
    query = "SELECT * FROM files WHERE file_id = ?"

    with closing(get_connection(db_path)) as con:
        row = con.execute(query, (file_id,)).fetchone()
        return dict(row) if row is not None else None


def list_files(db_path: str = "landrop.db") -> list[dict[str, Any]]:
    """Return all file records ordered from newest to oldest."""
    query = "SELECT * FROM files ORDER BY created_at DESC"

    with closing(get_connection(db_path)) as con:
        rows = con.execute(query).fetchall()
        return [dict(row) for row in rows]


def delete_expired_files(now_iso: str, db_path: str = "landrop.db") -> list[dict[str, Any]]:
    """Find all expired file rows, delete them from SQLite, and return their metadata."""
    select_query = "SELECT * FROM files WHERE expires_at <= ?"
    delete_query = "DELETE FROM files WHERE expires_at <= ?"

    with closing(get_connection(db_path)) as con:
        rows = con.execute(select_query, (now_iso,)).fetchall()
        expired = [dict(row) for row in rows]

        if expired:
            with con:
                con.execute(delete_query, (now_iso,))

        return expired