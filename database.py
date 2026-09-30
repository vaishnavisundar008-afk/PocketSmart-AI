import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from app.config import settings


DB_PATH = Path(settings.database_path)


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recommendation_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                planner TEXT NOT NULL,
                summary TEXT NOT NULL,
                request_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS history_by_user_date
                ON recommendation_history(user_id, created_at DESC);
            """
        )


def create_user(name: str, email: str, password_hash: str) -> dict[str, str] | None:
    user = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "email": email.strip().lower(),
        "password_hash": password_hash,
        "created_at": datetime.now(UTC).isoformat(),
    }
    try:
        with _connection() as connection:
            connection.execute(
                "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (user["id"], user["name"], user["email"], user["password_hash"], user["created_at"]),
            )
    except sqlite3.IntegrityError:
        return None
    return user


def get_user_by_email(email: str) -> dict[str, str] | None:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict[str, str] | None:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def save_recommendation(user_id: str, planner: str, request_data: dict, result: dict) -> str:
    entry_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    result["id"] = entry_id
    result["created_at"] = created_at
    with _connection() as connection:
        connection.execute(
            """INSERT INTO recommendation_history
               (id, user_id, planner, summary, request_json, result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entry_id,
                user_id,
                planner,
                str(result["summary"]),
                json.dumps(request_data),
                json.dumps(result),
                created_at,
            ),
        )
    return entry_id


def list_recommendations(user_id: str, limit: int = 50) -> list[dict]:
    with _connection() as connection:
        rows = connection.execute(
            """SELECT id, planner, summary, request_json, result_json, created_at
               FROM recommendation_history WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "planner": row["planner"],
            "summary": row["summary"],
            "request": json.loads(row["request_json"]),
            "result": json.loads(row["result_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_recommendation(user_id: str, entry_id: str) -> dict | None:
    with _connection() as connection:
        row = connection.execute(
            """SELECT id, planner, summary, request_json, result_json, created_at
               FROM recommendation_history WHERE user_id = ? AND id = ?""",
            (user_id, entry_id),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "planner": row["planner"],
        "summary": row["summary"],
        "request": json.loads(row["request_json"]),
        "result": json.loads(row["result_json"]),
        "created_at": row["created_at"],
    }


def count_recommendations(user_id: str) -> int:
    with _connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM recommendation_history WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row["count"])