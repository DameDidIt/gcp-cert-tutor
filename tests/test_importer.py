# tests/test_importer.py
from pathlib import Path
from gcp_tutor.db import init_db, get_connection
from gcp_tutor.seed import seed_domains
from gcp_tutor.importer import read_file_content, categorize_content, import_file

def test_read_txt_file(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("IAM roles are important for access control in GCP.")
    content = read_file_content(str(f))
    assert "IAM roles" in content

def test_read_md_file(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("# GKE\n\nKubernetes Engine manages containers.")
    content = read_file_content(str(f))
    assert "Kubernetes" in content

def test_read_json_file(tmp_path):
    f = tmp_path / "notes.json"
    f.write_text('{"notes": "VPC networking fundamentals"}')
    content = read_file_content(str(f))
    assert "VPC" in content

def test_categorize_content():
    text = "gcloud compute instances create my-vm --zone=us-central1-a"
    domain_id = categorize_content(text)
    assert domain_id == 3  # Deploying & implementing

def test_categorize_iam_content():
    text = "IAM policies and service accounts for security"
    domain_id = categorize_content(text)
    assert domain_id == 5  # Access & security

def test_import_file(tmp_path, tmp_db):
    init_db(tmp_db)
    seed_domains(tmp_db)
    f = tmp_path / "study.txt"
    f.write_text("Cloud Monitoring alerts help ensure operational success.")
    import_file(tmp_db, str(f))
    conn = get_connection(tmp_db)
    imported = conn.execute("SELECT * FROM imported_content").fetchall()
    assert len(imported) == 1
    assert "Cloud Monitoring" in imported[0]["content_text"]
    conn.close()
