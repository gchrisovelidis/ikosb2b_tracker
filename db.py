import sqlite3
from datetime import datetime
from pathlib import Path

from auth import hash_password

DB_PATH = Path("tracker.db")


DEFAULT_USERS = [
    ("gmichailidis", "gmich59853", 0),
    ("nmichailidou", "nmich47291", 0),
    ("oemichailidou", "oemic38476", 0),
    ("nspanopoulou", "nspan91824", 0),
    ("idimopoulos", "idimo56317", 0),
    ("ggatidis", "ggati24068", 0),
    ("edkorderi", "edkor85193", 0),
    ("rkougioumtzidou", "rkoug41756", 0),
    ("gchrisovelidis", "gchrisovelidis22193", 1),
]

DEFAULT_TASKS = [
    "Occupancy Charts 2026",
    "Occupancy Charts 2027",
    "Out of Order Report",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            display_order INTEGER NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, task_id, day),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )
        """
    )

    conn.commit()
    seed_users(conn)
    seed_tasks(conn)
    conn.close()


def seed_users(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    count = cur.fetchone()["cnt"]

    if count == 0:
        for username, password, is_admin in DEFAULT_USERS:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, is_admin)
                VALUES (?, ?, ?)
                """,
                (username, hash_password(password), is_admin),
            )
        conn.commit()


def seed_tasks(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM tasks")
    count = cur.fetchone()["cnt"]

    if count == 0:
        for idx, task_name in enumerate(DEFAULT_TASKS, start=1):
            cur.execute(
                """
                INSERT INTO tasks (task_name, display_order)
                VALUES (?, ?)
                """,
                (task_name, idx),
            )
        conn.commit()


def get_user_by_username(username: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash, is_admin FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, is_admin
        FROM users
        ORDER BY is_admin DESC, username ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_regular_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, is_admin
        FROM users
        WHERE is_admin = 0
        ORDER BY username ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_tasks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, task_name, display_order
        FROM tasks
        ORDER BY display_order ASC, id ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def update_task(task_id: int, new_name: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET task_name = ? WHERE id = ?",
        (new_name.strip(), task_id),
    )
    conn.commit()
    conn.close()


def ensure_daily_rows(user_id: int, day: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    tasks = get_tasks()

    for task in tasks:
        cur.execute(
            """
            INSERT OR IGNORE INTO completions (user_id, task_id, day, completed, updated_at)
            VALUES (?, ?, ?, 0, ?)
            """,
            (user_id, task["id"], day, datetime.now().isoformat()),
        )

    conn.commit()
    conn.close()


def get_user_task_status(user_id: int, day: str):
    ensure_daily_rows(user_id, day)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            t.id AS task_id,
            t.task_name,
            t.display_order,
            COALESCE(c.completed, 0) AS completed
        FROM tasks t
        LEFT JOIN completions c
            ON t.id = c.task_id
            AND c.user_id = ?
            AND c.day = ?
        ORDER BY t.display_order ASC, t.id ASC
        """,
        (user_id, day),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def set_task_completion(user_id: int, task_id: int, day: str, completed: bool) -> None:
    ensure_daily_rows(user_id, day)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE completions
        SET completed = ?, updated_at = ?
        WHERE user_id = ? AND task_id = ? AND day = ?
        """,
        (1 if completed else 0, datetime.now().isoformat(), user_id, task_id, day),
    )
    conn.commit()
    conn.close()


def get_user_progress(user_id: int, day: str):
    ensure_daily_rows(user_id, day)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            SUM(completed) AS completed_count,
            COUNT(*) AS total_count
        FROM completions
        WHERE user_id = ? AND day = ?
        """,
        (user_id, day),
    )
    row = cur.fetchone()
    conn.close()
    completed = row["completed_count"] or 0
    total = row["total_count"] or 0
    return completed, total


def get_leaderboard(day: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            u.username,
            COALESCE(SUM(c.completed), 0) AS completed_count,
            COUNT(t.id) AS total_count,
            MAX(c.updated_at) AS last_update
        FROM users u
        CROSS JOIN tasks t
        LEFT JOIN completions c
            ON c.user_id = u.id
            AND c.task_id = t.id
            AND c.day = ?
        WHERE u.is_admin = 0
        GROUP BY u.id, u.username
        ORDER BY completed_count DESC, last_update ASC, u.username ASC
        """,
        (day,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_team_average(day: str) -> float:
    leaderboard = get_leaderboard(day)
    if not leaderboard:
        return 0.0

    percentages = []
    for row in leaderboard:
        total = row["total_count"] or 0
        completed = row["completed_count"] or 0
        pct = (completed / total) * 100 if total else 0
        percentages.append(pct)

    return sum(percentages) / len(percentages)