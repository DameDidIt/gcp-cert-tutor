from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains, seed_study_plan, is_seeded


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
