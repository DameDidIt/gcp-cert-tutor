"""Readiness dashboard scoring and statistics."""
from gcp_tutor.db import get_connection
from gcp_tutor.study import get_completed_sessions, get_total_sessions


def get_readiness_label(score: float) -> str:
    if score >= 80:
        return "READY"
    elif score >= 65:
        return "LIKELY"
    elif score >= 50:
        return "NEEDS WORK"
    return "NOT READY"


def get_readiness_color(score: float) -> str:
    if score >= 80:
        return "green"
    elif score >= 65:
        return "yellow"
    elif score >= 50:
        return "dark_orange"
    return "red"


def _quiz_score(db_path: str) -> float:
    conn = get_connection(db_path)
    row = conn.execute("SELECT COUNT(*) as t, SUM(is_correct) as c FROM quiz_results").fetchone()
    conn.close()
    if not row["t"]:
        return 0.0
    return (row["c"] / row["t"]) * 100


def _flashcard_retention(db_path: str) -> float:
    conn = get_connection(db_path)
    row = conn.execute("SELECT COUNT(*) as t, SUM(CASE WHEN rating >= 3 THEN 1 ELSE 0 END) as c FROM flashcard_results").fetchone()
    conn.close()
    if not row["t"]:
        return 0.0
    return (row["c"] / row["t"]) * 100


def _study_completion(db_path: str) -> float:
    completed = get_completed_sessions(db_path)
    total = get_total_sessions(db_path)
    if total == 0:
        return 0.0
    return (completed / total) * 100


def calc_readiness_score(db_path: str) -> float:
    quiz = _quiz_score(db_path)
    flash = _flashcard_retention(db_path)
    study = _study_completion(db_path)
    # Weighted: quiz 50%, flashcard 30%, study 20%
    score = quiz * 0.5 + flash * 0.3 + study * 0.2
    return round(score, 1)


def get_domain_scores(db_path: str) -> list[dict]:
    conn = get_connection(db_path)
    domains = conn.execute("SELECT * FROM domains ORDER BY section_number").fetchall()
    results = []
    for d in domains:
        row = conn.execute(
            """SELECT COUNT(*) as t, SUM(r.is_correct) as c
            FROM quiz_results r JOIN quiz_questions q ON r.quiz_question_id = q.id
            WHERE q.domain_id = ?""",
            (d["id"],),
        ).fetchone()
        quiz_pct = (row["c"] / row["t"] * 100) if row["t"] else 0.0
        flash_row = conn.execute(
            """SELECT COUNT(*) as t, SUM(CASE WHEN fr.rating >= 3 THEN 1 ELSE 0 END) as c
            FROM flashcard_results fr JOIN flashcards f ON fr.flashcard_id = f.id
            WHERE f.domain_id = ?""",
            (d["id"],),
        ).fetchone()
        flash_pct = (flash_row["c"] / flash_row["t"] * 100) if flash_row["t"] else 0.0
        combined = quiz_pct * 0.6 + flash_pct * 0.4
        results.append({
            "domain_id": d["id"],
            "name": d["name"],
            "section_number": d["section_number"],
            "score": round(combined, 1),
            "label": get_readiness_label(combined),
        })
    conn.close()
    return results


def get_study_stats(db_path: str) -> dict:
    conn = get_connection(db_path)
    sessions = conn.execute("SELECT COUNT(*) FROM user_progress WHERE completed_at IS NOT NULL").fetchone()[0]
    flashcards = conn.execute("SELECT COUNT(*) FROM flashcard_results").fetchone()[0]
    quizzes = conn.execute("SELECT COUNT(DISTINCT answered_at) FROM quiz_results").fetchone()[0]
    avg_row = conn.execute("SELECT AVG(is_correct) * 100 as avg FROM quiz_results").fetchone()
    avg_quiz = round(avg_row["avg"], 1) if avg_row["avg"] else 0.0
    conn.close()
    return {
        "sessions_completed": sessions,
        "flashcards_reviewed": flashcards,
        "quizzes_taken": quizzes,
        "avg_quiz_score": avg_quiz,
    }
