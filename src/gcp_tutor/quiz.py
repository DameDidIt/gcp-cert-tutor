"""Quiz engine for practice questions."""
from datetime import datetime
from gcp_tutor.db import get_connection


def get_quiz_questions(db_path: str, count: int = 10) -> list:
    conn = get_connection(db_path)
    questions = conn.execute(
        "SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT ?", (count,)
    ).fetchall()
    conn.close()
    return questions


def get_questions_for_domain(db_path: str, domain_id: int, count: int = 10) -> list:
    conn = get_connection(db_path)
    questions = conn.execute(
        "SELECT * FROM quiz_questions WHERE domain_id = ? ORDER BY RANDOM() LIMIT ?",
        (domain_id, count),
    ).fetchall()
    conn.close()
    return questions


def get_questions_for_subtopic(db_path: str, subtopic_id: int, count: int = 10) -> list:
    conn = get_connection(db_path)
    questions = conn.execute(
        "SELECT * FROM quiz_questions WHERE subtopic_id = ? ORDER BY RANDOM() LIMIT ?",
        (subtopic_id, count),
    ).fetchall()
    conn.close()
    return questions


def record_quiz_answer(db_path: str, question_id: int, user_answer: str) -> bool:
    conn = get_connection(db_path)
    question = conn.execute(
        "SELECT correct_answer FROM quiz_questions WHERE id = ?", (question_id,)
    ).fetchone()
    is_correct = user_answer.lower().strip() == question["correct_answer"].lower().strip()
    conn.execute(
        "INSERT INTO quiz_results (quiz_question_id, user_answer, is_correct, answered_at) VALUES (?, ?, ?, ?)",
        (question_id, user_answer, int(is_correct), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return is_correct


def get_quiz_score(db_path: str) -> float:
    """Overall quiz score as percentage."""
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT COUNT(*) as total, SUM(is_correct) as correct FROM quiz_results"
    ).fetchone()
    conn.close()
    if row["total"] == 0:
        return 0.0
    return round((row["correct"] / row["total"]) * 100, 1)


def get_domain_quiz_scores(db_path: str) -> dict:
    """Quiz scores broken down by domain."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT q.domain_id, COUNT(*) as total, SUM(r.is_correct) as correct
        FROM quiz_results r
        JOIN quiz_questions q ON r.quiz_question_id = q.id
        GROUP BY q.domain_id"""
    ).fetchall()
    conn.close()
    return {
        row["domain_id"]: round((row["correct"] / row["total"]) * 100, 1)
        for row in rows
    }
