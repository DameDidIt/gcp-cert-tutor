# tests/test_review.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_all
from gcp_tutor.quiz import get_quiz_questions, record_quiz_answer
from gcp_tutor.flashcards import get_due_cards, record_flashcard_result
from gcp_tutor.review import get_weak_subtopics, get_weak_domains

def test_get_weak_subtopics_empty(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    weak = get_weak_subtopics(tmp_db)
    assert weak == []  # no results yet, nothing is "weak"

def test_get_weak_subtopics_with_errors(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    # Answer questions wrong for domain 3
    questions = get_quiz_questions(tmp_db, count=5)
    for q in questions:
        wrong = "b" if q["correct_answer"] != "b" else "c"
        record_quiz_answer(tmp_db, q["id"], wrong)
    weak = get_weak_subtopics(tmp_db)
    assert len(weak) > 0
    assert weak[0]["error_rate"] > 0

def test_get_weak_domains(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    questions = get_quiz_questions(tmp_db, count=5)
    for q in questions:
        wrong = "b" if q["correct_answer"] != "b" else "c"
        record_quiz_answer(tmp_db, q["id"], wrong)
    weak = get_weak_domains(tmp_db)
    assert len(weak) > 0
