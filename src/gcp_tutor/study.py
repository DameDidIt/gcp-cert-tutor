"""Study session management and progress tracking."""
from datetime import date, datetime
from gcp_tutor.db import get_connection


def get_setting(db_path: str, key: str, default: str = None) -> str | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT value FROM user_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(db_path: str, key: str, value: str) -> None:
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO user_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?",
        (key, value, value),
    )
    conn.commit()
    conn.close()


def get_start_date(db_path: str) -> str | None:
    return get_setting(db_path, "start_date")


def get_current_session_day(db_path: str) -> int:
    return int(get_setting(db_path, "current_session_day", "1"))


def get_total_sessions(db_path: str) -> int:
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM study_days").fetchone()[0]
    conn.close()
    return count


def get_todays_plan(db_path: str) -> dict | None:
    day = get_current_session_day(db_path)
    conn = get_connection(db_path)
    plan = conn.execute(
        """SELECT sd.*, d.name as domain_name
        FROM study_days sd
        LEFT JOIN domains d ON sd.domain_id = d.id
        WHERE sd.day_number = ?""",
        (day,),
    ).fetchone()
    conn.close()
    return dict(plan) if plan else None


def start_new_session(db_path: str) -> dict:
    day = get_current_session_day(db_path)
    if not get_start_date(db_path):
        set_setting(db_path, "start_date", date.today().isoformat())
    conn = get_connection(db_path)
    existing = conn.execute("SELECT * FROM user_progress WHERE session_day = ?", (day,)).fetchone()
    if existing:
        conn.close()
        return dict(existing)
    conn.execute(
        "INSERT INTO user_progress (session_day, calendar_date) VALUES (?, ?)",
        (day, date.today().isoformat()),
    )
    conn.commit()
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = ?", (day,)).fetchone()
    conn.close()
    return dict(progress)


def complete_session_component(db_path: str, session_day: int, component: str) -> None:
    valid = {"reading": "reading_done", "flashcards": "flashcards_done", "quiz": "quiz_done"}
    column = valid[component]
    conn = get_connection(db_path)
    conn.execute(
        f"UPDATE user_progress SET {column} = 1 WHERE session_day = ?",
        (session_day,),
    )
    # Check if all components done
    progress = conn.execute("SELECT * FROM user_progress WHERE session_day = ?", (session_day,)).fetchone()
    if progress["reading_done"] and progress["flashcards_done"] and progress["quiz_done"]:
        conn.execute(
            "UPDATE user_progress SET completed_at = ? WHERE session_day = ?",
            (datetime.now().isoformat(), session_day),
        )
        # Advance session day
        conn.execute(
            "INSERT INTO user_settings (key, value) VALUES ('current_session_day', ?) ON CONFLICT(key) DO UPDATE SET value=?",
            (str(session_day + 1), str(session_day + 1)),
        )
    conn.commit()
    conn.close()


def complete_reading(db_path: str, session_day: int) -> None:
    """Convenience wrapper for completing the reading component."""
    complete_session_component(db_path, session_day, "reading")


def get_calendar_days_elapsed(db_path: str) -> int:
    start = get_start_date(db_path)
    if not start:
        return 0
    start_date = date.fromisoformat(start)
    return (date.today() - start_date).days + 1


def get_completed_sessions(db_path: str) -> int:
    conn = get_connection(db_path)
    count = conn.execute("SELECT COUNT(*) FROM user_progress WHERE completed_at IS NOT NULL").fetchone()[0]
    conn.close()
    return count
