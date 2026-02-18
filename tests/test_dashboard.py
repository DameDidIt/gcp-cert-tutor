# tests/test_dashboard.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.study import start_new_session, complete_session_component
from gcp_tutor.quiz import record_quiz_answer, get_quiz_questions
from gcp_tutor.flashcards import get_due_cards, record_flashcard_result
from gcp_tutor.dashboard import (
    calc_readiness_score, get_readiness_label, get_domain_scores,
    get_study_stats,
)

def test_readiness_score_zero_with_no_data(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    score = calc_readiness_score(tmp_db)
    assert score == 0.0

def test_readiness_label():
    assert get_readiness_label(85) == "READY"
    assert get_readiness_label(70) == "LIKELY"
    assert get_readiness_label(55) == "NEEDS WORK"
    assert get_readiness_label(40) == "NOT READY"

def test_readiness_score_with_data(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    # Complete a session
    start_new_session(tmp_db)
    complete_session_component(tmp_db, 1, "reading")
    complete_session_component(tmp_db, 1, "flashcards")
    complete_session_component(tmp_db, 1, "quiz")
    # Answer some quiz questions
    questions = get_quiz_questions(tmp_db, count=5)
    for q in questions:
        record_quiz_answer(tmp_db, q["id"], q["correct_answer"])
    # Review some flashcards
    cards = get_due_cards(tmp_db, limit=5)
    for c in cards:
        record_flashcard_result(tmp_db, c["id"], rating=4)
    score = calc_readiness_score(tmp_db)
    assert 0 < score <= 100

def test_get_study_stats(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    stats = get_study_stats(tmp_db)
    assert "sessions_completed" in stats
    assert "flashcards_reviewed" in stats
    assert "quizzes_taken" in stats
