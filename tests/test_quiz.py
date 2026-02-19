# tests/test_quiz.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains, seed_questions
from gcp_tutor.quiz import (
    get_quiz_questions, get_questions_for_domain, get_questions_for_subtopic,
    record_quiz_answer, get_quiz_score, get_domain_quiz_scores,
)


def test_get_quiz_questions(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=10)
    assert len(questions) == 10


def test_get_questions_for_domain(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_questions_for_domain(tmp_db, domain_id=3, count=5)
    assert len(questions) == 5
    assert all(q["domain_id"] == 3 for q in questions)


def test_record_quiz_answer_correct(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    conn = get_connection(tmp_db)
    result = conn.execute("SELECT * FROM quiz_results WHERE quiz_question_id = ?", (q["id"],)).fetchone()
    assert result["is_correct"] == 1
    conn.close()


def test_record_quiz_answer_incorrect(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    wrong = "b" if q["correct_answer"] != "b" else "c"
    record_quiz_answer(tmp_db, q["id"], wrong)
    conn = get_connection(tmp_db)
    result = conn.execute("SELECT * FROM quiz_results WHERE quiz_question_id = ?", (q["id"],)).fetchone()
    assert result["is_correct"] == 0
    conn.close()


def test_get_quiz_score(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=4)
    # Answer 3 correct, 1 wrong
    for q in questions[:3]:
        record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    wrong = "b" if questions[3]["correct_answer"] != "b" else "c"
    record_quiz_answer(tmp_db, questions[3]["id"], wrong)
    score = get_quiz_score(tmp_db)
    assert score == 75.0  # 3/4


# --- Edge case tests ---


def test_get_quiz_questions_empty_db(tmp_db):
    """No questions seeded returns empty list."""
    init_db(tmp_db)
    questions = get_quiz_questions(tmp_db, count=10)
    assert questions == []


def test_get_quiz_questions_count_exceeds_available(tmp_db):
    """Requesting more questions than available returns all available."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    conn = get_connection(tmp_db)
    total = conn.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
    conn.close()
    questions = get_quiz_questions(tmp_db, count=total + 100)
    assert len(questions) == total


def test_get_questions_for_domain_nonexistent(tmp_db):
    """Non-existent domain returns empty list."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_questions_for_domain(tmp_db, domain_id=999, count=5)
    assert questions == []


def test_get_questions_for_each_domain(tmp_db):
    """All 5 domains have quiz questions."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    for domain_id in range(1, 6):
        questions = get_questions_for_domain(tmp_db, domain_id=domain_id, count=3)
        assert len(questions) > 0, f"Domain {domain_id} should have questions"
        assert all(q["domain_id"] == domain_id for q in questions)


def test_get_questions_for_subtopic(tmp_db):
    """Questions can be filtered by subtopic."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    conn = get_connection(tmp_db)
    # Find a subtopic that has questions
    row = conn.execute(
        "SELECT subtopic_id FROM quiz_questions WHERE subtopic_id IS NOT NULL LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        questions = get_questions_for_subtopic(tmp_db, subtopic_id=row["subtopic_id"], count=5)
        assert len(questions) > 0
        assert all(q["subtopic_id"] == row["subtopic_id"] for q in questions)


def test_get_questions_for_subtopic_nonexistent(tmp_db):
    """Non-existent subtopic returns empty list."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_questions_for_subtopic(tmp_db, subtopic_id=999, count=5)
    assert questions == []


def test_record_quiz_answer_case_insensitive(tmp_db):
    """Uppercase answers are accepted as correct."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    is_correct = record_quiz_answer(tmp_db, q["id"], q["correct_answer"].upper())
    assert is_correct is True


def test_record_quiz_answer_with_whitespace(tmp_db):
    """Answers with leading/trailing whitespace are handled."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    is_correct = record_quiz_answer(tmp_db, q["id"], f"  {q['correct_answer']}  ")
    assert is_correct is True


def test_record_quiz_answer_returns_bool(tmp_db):
    """record_quiz_answer returns True for correct, False for incorrect."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    result = record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    assert result is True
    wrong = "b" if q["correct_answer"] != "b" else "c"
    result = record_quiz_answer(tmp_db, q["id"], wrong)
    assert result is False


def test_record_quiz_answer_stores_timestamp(tmp_db):
    """Quiz result has an answered_at timestamp."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    conn = get_connection(tmp_db)
    result = conn.execute("SELECT answered_at FROM quiz_results WHERE quiz_question_id = ?", (q["id"],)).fetchone()
    assert result["answered_at"] is not None
    conn.close()


def test_get_quiz_score_no_results(tmp_db):
    """Score is 0.0 when no quiz results exist."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    score = get_quiz_score(tmp_db)
    assert score == 0.0


def test_get_quiz_score_all_correct(tmp_db):
    """Score is 100.0 when all answers are correct."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=5)
    for q in questions:
        record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    score = get_quiz_score(tmp_db)
    assert score == 100.0


def test_get_quiz_score_all_incorrect(tmp_db):
    """Score is 0.0 when all answers are incorrect."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=5)
    for q in questions:
        wrong = "b" if q["correct_answer"] != "b" else "c"
        record_quiz_answer(tmp_db, q["id"], wrong)
    score = get_quiz_score(tmp_db)
    assert score == 0.0


def test_get_domain_quiz_scores_empty(tmp_db):
    """No results returns empty dict."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    scores = get_domain_quiz_scores(tmp_db)
    assert scores == {}


def test_get_domain_quiz_scores_with_data(tmp_db):
    """Domain scores are computed per domain correctly."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    # Answer all of domain 3 correct
    d3_questions = get_questions_for_domain(tmp_db, domain_id=3, count=5)
    for q in d3_questions:
        record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    # Answer all of domain 1 wrong
    d1_questions = get_questions_for_domain(tmp_db, domain_id=1, count=5)
    for q in d1_questions:
        wrong = "b" if q["correct_answer"] != "b" else "c"
        record_quiz_answer(tmp_db, q["id"], wrong)
    scores = get_domain_quiz_scores(tmp_db)
    assert scores[3] == 100.0
    assert scores[1] == 0.0


def test_same_question_answered_multiple_times(tmp_db):
    """Answering same question multiple times creates multiple result rows."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=1)
    q = questions[0]
    record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    conn = get_connection(tmp_db)
    count = conn.execute(
        "SELECT COUNT(*) FROM quiz_results WHERE quiz_question_id = ?", (q["id"],)
    ).fetchone()[0]
    assert count == 2
    conn.close()


def test_quiz_questions_have_required_fields(tmp_db):
    """Every question has stem, 4 choices, correct_answer, and explanation."""
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    questions = get_quiz_questions(tmp_db, count=20)
    for q in questions:
        assert q["stem"]
        assert q["choice_a"]
        assert q["choice_b"]
        assert q["choice_c"]
        assert q["choice_d"]
        assert q["correct_answer"] in ("a", "b", "c", "d")
        assert q["explanation"]
