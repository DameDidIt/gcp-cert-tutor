# tests/test_integration.py
"""End-to-end test of the core workflow."""
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.study import (
    get_current_session_day, get_todays_plan, start_new_session,
    complete_session_component,
)
from gcp_tutor.flashcards import get_cards_for_domain, record_flashcard_result
from gcp_tutor.quiz import get_questions_for_domain, record_quiz_answer
from gcp_tutor.dashboard import calc_readiness_score, get_domain_scores, get_study_stats
from gcp_tutor.review import get_weak_domains


def test_full_session_workflow(tmp_db):
    """Simulate a complete study session and verify all systems work together."""
    # Setup
    init_db(tmp_db)
    seed_all(tmp_db)

    # Day 1
    assert get_current_session_day(tmp_db) == 1
    plan = get_todays_plan(tmp_db)
    assert plan["domain_id"] == 3

    progress = start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")

    # Flashcards
    cards = get_cards_for_domain(tmp_db, plan["domain_id"], limit=5)
    for c in cards:
        record_flashcard_result(tmp_db, c["id"], rating=4)
    complete_session_component(tmp_db, 1, "flashcards")

    # Quiz
    questions = get_questions_for_domain(tmp_db, plan["domain_id"], count=5)
    for q in questions[:3]:
        record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    for q in questions[3:]:
        wrong = "b" if q["correct_answer"] != "b" else "c"
        record_quiz_answer(tmp_db, q["id"], wrong)
    complete_session_component(tmp_db, 1, "quiz")

    # Verify advancement
    assert get_current_session_day(tmp_db) == 2

    # Dashboard
    score = calc_readiness_score(tmp_db)
    assert score > 0
    domain_scores = get_domain_scores(tmp_db)
    assert len(domain_scores) == 5
    stats = get_study_stats(tmp_db)
    assert stats["sessions_completed"] == 1
    assert stats["flashcards_reviewed"] == 5

    # Weak areas (we got 2 wrong)
    weak = get_weak_domains(tmp_db, threshold=80)
    # Domain 3 should show up as weak (60% correct)
    assert any(w["domain_id"] == 3 for w in weak)
