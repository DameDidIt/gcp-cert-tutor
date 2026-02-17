from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains, seed_study_plan, is_seeded, seed_flashcards, seed_questions, seed_all


def test_seed_domains(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    conn = get_connection(tmp_db)
    domains = conn.execute("SELECT * FROM domains").fetchall()
    assert len(domains) == 5
    subtopics = conn.execute("SELECT * FROM subtopics").fetchall()
    assert len(subtopics) == 19  # total subtopics across all domains
    conn.close()


def test_seed_study_plan(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_study_plan(tmp_db)
    conn = get_connection(tmp_db)
    days = conn.execute("SELECT * FROM study_days ORDER BY day_number").fetchall()
    assert len(days) == 30
    # First 6 days should be domain 3 (heaviest weight)
    assert days[0]["domain_id"] == 3
    assert days[5]["domain_id"] == 3
    conn.close()


def test_is_seeded(tmp_db):
    init_db(tmp_db)
    assert not is_seeded(tmp_db)
    seed_domains(tmp_db)
    assert is_seeded(tmp_db)


def test_seed_flashcards(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_flashcards(tmp_db)
    conn = get_connection(tmp_db)
    cards = conn.execute("SELECT * FROM flashcards").fetchall()
    assert len(cards) >= 190
    # Verify all 5 domains have cards
    domain_ids = {c["domain_id"] for c in cards}
    assert domain_ids == {1, 2, 3, 4, 5}
    conn.close()


def test_seed_questions(tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    seed_questions(tmp_db)
    conn = get_connection(tmp_db)
    questions = conn.execute("SELECT * FROM quiz_questions").fetchall()
    assert len(questions) >= 95
    conn.close()


def test_seed_all_idempotent(tmp_db):
    init_db(tmp_db)
    seed_all(tmp_db)
    seed_all(tmp_db)  # second call should be no-op
    conn = get_connection(tmp_db)
    assert conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0] == 5
    conn.close()
