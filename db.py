import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

TIMEZONE = ZoneInfo("Europe/Athens")
DB_PATH = Path("tracker.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS team_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            day TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            updated_by TEXT,
            updated_at TEXT,
            UNIQUE(task_name, day)
        )
        """
    )

    conn.commit()
    conn.close()


def ensure_day_tasks(day: str, task_names: list[str]) -> None:
    conn = get_connection()
    cur = conn.cursor()

    for task_name in task_names:
        cur.execute(
            """
            INSERT OR IGNORE INTO team_completions (
                task_name, day, completed, updated_by, updated_at
            )
            VALUES (?, ?, 0, NULL, NULL)
            """,
            (task_name, day),
        )

    conn.commit()
    conn.close()


def get_task_statuses(day: str, task_names: list[str]):
    ensure_day_tasks(day, task_names)

    conn = get_connection()
    cur = conn.cursor()

    placeholders = ",".join(["?"] * len(task_names))
    cur.execute(
        f"""
        SELECT task_name, completed, updated_by, updated_at
        FROM team_completions
        WHERE day = ? AND task_name IN ({placeholders})
        ORDER BY CASE task_name
            WHEN ? THEN 1
            WHEN ? THEN 2
            WHEN ? THEN 3
            ELSE 99
        END
        """,
        [day, *task_names, *(
            task_names + ["", "", ""] if len(task_names) < 3 else task_names[:3]
        )[:3]],
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def set_task_completion(day: str, task_name: str, completed: bool, updated_by: str) -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO team_completions (
            task_name, day, completed, updated_by, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(task_name, day) DO UPDATE SET
            completed = excluded.completed,
            updated_by = excluded.updated_by,
            updated_at = excluded.updated_at
        """,
        (
            task_name,
            day,
            1 if completed else 0,
            updated_by if completed else None,
            datetime.now(TIMEZONE).isoformat(timespec="seconds"),
        ),
    )

    conn.commit()
    conn.close()


def get_team_progress(day: str, task_names: list[str]) -> tuple[int, int, int]:
    rows = get_task_statuses(day, task_names)
    total = len(rows)
    completed = sum(int(row["completed"]) for row in rows)
    pct = round((completed / total) * 100) if total else 0
    return completed, total, pct