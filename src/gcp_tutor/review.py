"""Weak area identification and review session logic."""
from gcp_tutor.db import get_connection


def get_weak_subtopics(db_path: str, threshold: float = 70.0) -> list[dict]:
    """Get subtopics where error rate is above threshold (sorted worst first)."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT s.id, s.name, s.domain_id, d.name as domain_name,
            COUNT(*) as total,
            SUM(CASE WHEN r.is_correct = 0 THEN 1 ELSE 0 END) as errors
        FROM quiz_results r
        JOIN quiz_questions q ON r.quiz_question_id = q.id
        JOIN subtopics s ON q.subtopic_id = s.id
        JOIN domains d ON s.domain_id = d.id
        GROUP BY s.id
        HAVING (CAST(errors AS REAL) / total) * 100 > ?
        ORDER BY (CAST(errors AS REAL) / total) DESC""",
        (100 - threshold,),
    ).fetchall()
    conn.close()
    return [
        {
            "subtopic_id": r["id"],
            "subtopic_name": r["name"],
            "domain_id": r["domain_id"],
            "domain_name": r["domain_name"],
            "total": r["total"],
            "errors": r["errors"],
            "error_rate": round((r["errors"] / r["total"]) * 100, 1),
        }
        for r in rows
    ]


def get_weak_domains(db_path: str, threshold: float = 70.0) -> list[dict]:
    """Get domains where score is below threshold."""
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT d.id, d.name, d.section_number,
            COUNT(*) as total,
            SUM(r.is_correct) as correct
        FROM quiz_results r
        JOIN quiz_questions q ON r.quiz_question_id = q.id
        JOIN domains d ON q.domain_id = d.id
        GROUP BY d.id
        HAVING (CAST(correct AS REAL) / total) * 100 < ?
        ORDER BY (CAST(correct AS REAL) / total) ASC""",
        (threshold,),
    ).fetchall()
    conn.close()
    return [
        {
            "domain_id": r["id"],
            "domain_name": r["name"],
            "section_number": r["section_number"],
            "total": r["total"],
            "correct": r["correct"],
            "score": round((r["correct"] / r["total"]) * 100, 1),
        }
        for r in rows
    ]
