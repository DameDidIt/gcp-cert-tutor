"""Smart import for various file formats."""
import json
from datetime import datetime
from pathlib import Path
from gcp_tutor.db import get_connection

# Keyword mapping for auto-categorization
DOMAIN_KEYWORDS = {
    1: ["project", "billing", "organization", "quota", "cloud identity", "resource hierarchy", "org policy", "apis enable"],
    2: ["planning", "machine type", "spot vm", "storage class", "nearline", "coldline", "archive", "load balancing", "network service tier", "bigtable", "spanner", "cloud sql"],
    3: ["deploy", "compute instance", "gcloud compute", "kubectl", "gke", "kubernetes", "cloud run", "cloud functions", "eventarc", "pub/sub", "dataflow", "vpc", "subnet", "firewall", "vpn", "peering", "terraform", "helm", "instance template", "managed instance group"],
    4: ["snapshot", "image", "monitoring", "logging", "alert", "ops agent", "prometheus", "cloud nat", "cloud dns", "traffic splitting", "node pool", "lifecycle", "log router", "audit log", "autoscal"],
    5: ["iam", "service account", "role", "permission", "impersonat", "credential", "access control", "policy binding", "custom role"],
}


def read_file_content(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return path.read_text()
    elif suffix == ".json":
        data = json.loads(path.read_text())
        return json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
    elif suffix in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(path.read_text())
        return str(data)
    elif suffix == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    elif suffix in (".html", ".htm"):
        from bs4 import BeautifulSoup
        html = path.read_text()
        return BeautifulSoup(html, "html.parser").get_text()
    else:
        # Try reading as plain text
        return path.read_text()


def categorize_content(text: str) -> int | None:
    """Auto-categorize content into a domain by keyword matching. Returns domain_id or None."""
    text_lower = text.lower()
    scores = {}
    for domain_id, keywords in DOMAIN_KEYWORDS.items():
        scores[domain_id] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def import_file(db_path: str, file_path: str, domain_id: int | None = None) -> dict:
    """Import a file into the database. Auto-categorizes if domain_id not provided."""
    content = read_file_content(file_path)
    if domain_id is None:
        domain_id = categorize_content(content)
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO imported_content (filename, domain_id, content_text, imported_at) VALUES (?, ?, ?, ?)",
        (Path(file_path).name, domain_id, content, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"filename": Path(file_path).name, "domain_id": domain_id, "length": len(content)}
