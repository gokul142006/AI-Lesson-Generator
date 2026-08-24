"""
database.py
----------------
SQLite persistence layer for the AI Lesson Plan Generator.

The database is created automatically on first use. Each saved lesson
stores the four teacher inputs plus the *final edited* lesson content
(serialized as JSON) so the full, teacher-approved lesson can always be
reloaded exactly as it was left.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils import now_timestamp

DB_PATH = Path(__file__).parent / "lessons.db"


class DatabaseError(Exception):
    """Raised for any database failure, with a friendly message."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


@contextmanager
def _get_connection():
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        if conn:
            conn.rollback()
        raise DatabaseError(f"A database error occurred: {exc}")
    finally:
        if conn:
            conn.close()


def init_db() -> None:
    """Create the lessons table if it does not already exist."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lessons (
                lesson_id   TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                subject     TEXT NOT NULL,
                grade       TEXT NOT NULL,
                topic       TEXT NOT NULL,
                duration    TEXT NOT NULL,
                lesson_json TEXT NOT NULL
            )
            """
        )


def save_lesson(
    lesson_id: str,
    subject: str,
    grade: str,
    topic: str,
    duration: str,
    lesson: Dict[str, Any],
) -> None:
    """Insert or update (upsert) a lesson record."""
    lesson_json = json.dumps(lesson, ensure_ascii=False)
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO lessons (lesson_id, created_at, subject, grade, topic, duration, lesson_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(lesson_id) DO UPDATE SET
                subject = excluded.subject,
                grade = excluded.grade,
                topic = excluded.topic,
                duration = excluded.duration,
                lesson_json = excluded.lesson_json
            """,
            (lesson_id, now_timestamp(), subject, grade, topic, duration, lesson_json),
        )


def get_all_lessons() -> List[Dict[str, Any]]:
    """Return all saved lessons, most recent first."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT lesson_id, created_at, subject, grade, topic, duration "
            "FROM lessons ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def search_lessons(
    subject: Optional[str] = None,
    grade: Optional[str] = None,
    topic: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search saved lessons by subject / grade / topic (case-insensitive, partial match)."""
    query = (
        "SELECT lesson_id, created_at, subject, grade, topic, duration "
        "FROM lessons WHERE 1=1"
    )
    params: List[str] = []

    if subject:
        query += " AND subject LIKE ?"
        params.append(f"%{subject}%")
    if grade:
        query += " AND grade LIKE ?"
        params.append(f"%{grade}%")
    if topic:
        query += " AND topic LIKE ?"
        params.append(f"%{topic}%")

    query += " ORDER BY created_at DESC"

    with _get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_lesson(lesson_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single lesson (including full content) by its ID."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)
        ).fetchone()

    if row is None:
        return None

    record = dict(row)
    record["lesson"] = json.loads(record.pop("lesson_json"))
    return record


def delete_lesson(lesson_id: str) -> None:
    """Delete a lesson by its ID."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM lessons WHERE lesson_id = ?", (lesson_id,))
