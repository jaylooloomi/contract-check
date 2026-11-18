import os
import shutil
import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DB = os.path.join(ROOT, "data", "app.db")
PDF = os.path.join(ROOT, "tests", "fixtures", "sample_text.pdf")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    if not os.path.exists(SRC_DB):
        pytest.skip("法條資料庫尚未建立")
    db = tmp_path_factory.mktemp("db") / "test.db"
    shutil.copy(SRC_DB, db)  # 用副本，不污染展示資料庫
    os.environ["CC_DB"] = str(db)
    import importlib
    import app.main as m
    importlib.reload(m)
    from fastapi.testclient import TestClient
    return TestClient(m.app)


def test_upload_and_findings(client):
    with open(PDF, "rb") as f:
        r = client.post("/api/contracts", files={"file": ("t.pdf", f, "application/pdf")})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["clause_count"] == 5 and d["finding_count"] >= 2
    detail = client.get(f"/api/contracts/{d['contract_id']}").json()
    assert all(f["article_content"] for f in detail["findings"])  # 條號都能取回原文


def test_AT6_review_persists(client):
    with open(PDF, "rb") as f:
        cid = client.post("/api/contracts", files={"file": ("t.pdf", f, "application/pdf")}).json()["contract_id"]
    fid = client.get(f"/api/contracts/{cid}").json()["findings"][0]["id"]
    assert client.post(f"/api/findings/{fid}/review", json={"decision": "reject", "note": "已有同意書"}).json()["ok"]
    again = client.get(f"/api/contracts/{cid}").json()["findings"][0]
    assert again["latest_review"]["decision"] == "reject"
    assert client.post(f"/api/findings/{fid}/review", json={"decision": "bad"}).status_code == 400


def test_law_info(client):
    d = client.get("/api/law").json()
    assert d["article_count"] == 66 and d["source_url"].startswith("https://law.moj.gov.tw")
