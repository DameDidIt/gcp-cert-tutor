# tests/test_quiz.py
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains, seed_questions
from gcp_tutor.quiz import get_quiz_questions, get_questions_for_domain, record_quiz_answer, get_quiz_score

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
