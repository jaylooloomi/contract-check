"""檢查狀態（rule/ai_status）、待人工確認、引用快照。AI 一律以 monkeypatch 模擬，不需真的 Ollama。"""
import importlib
import os
import shutil

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DB = os.path.join(ROOT, "data", "app.db")
PDF = os.path.join(ROOT, "tests", "fixtures", "sample_text.pdf")


@pytest.fixture(scope="module")
def m(tmp_path_factory):
    if not os.path.exists(SRC_DB):
        pytest.skip("法條資料庫尚未建立")
    db = tmp_path_factory.mktemp("db") / "status.db"
    shutil.copy(SRC_DB, db)
    os.environ["CC_DB"] = str(db)
    import app.main as mod
    importlib.reload(mod)
    return mod


@pytest.fixture
def client(m):
    from fastapi.testclient import TestClient
    return TestClient(m.app)


def upload(client, use_ai):
    with open(PDF, "rb") as f:
        r = client.post(f"/api/contracts?use_ai={str(use_ai).lower()}", files={"file": ("t.pdf", f, "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()


def test_migration_idempotent(m):
    from app.db import init_db
    init_db(m.conn)
    init_db(m.conn)
    cols = {r[1] for r in m.conn.execute("PRAGMA table_info(contracts)")}
    assert {"rule_status", "ai_status", "ai_detail", "law_version"} <= cols
    cols = {r[1] for r in m.conn.execute("PRAGMA table_info(findings)")}
    assert {"article_snapshot", "law_version"} <= cols


def test_ai_probe_fails_marks_failed(m, client, monkeypatch):
    monkeypatch.setattr(m, "probe_ai", lambda timeout=3: False)
    calls = []
    real = m.check_contract
    monkeypatch.setattr(m, "check_contract", lambda conn, cid, use_ai=True: calls.append(use_ai) or real(conn, cid, use_ai=use_ai))
    d = upload(client, True)
    assert calls == [False]  # 探測失敗就只跑規則，不再等 Ollama 逾時
    assert d["ai_status"] == "failed" and d["ai_detail"] == m.AI_DOWN_DETAIL and d["rule_status"] == "ok"
    det = client.get(f"/api/contracts/{d['contract_id']}").json()
    assert det["ai_status"] == "failed" and det["contract"]["ai_detail"] == m.AI_DOWN_DETAIL
    row = next(c for c in client.get("/api/contracts").json() if c["id"] == d["contract_id"])
    assert row["ai_status"] == "failed" and row["law_version"]


def test_ai_probe_ok(m, client, monkeypatch):
    monkeypatch.setattr(m, "probe_ai", lambda timeout=3: True)
    seen = []
    real = m.check_contract
    monkeypatch.setattr(m, "check_contract", lambda conn, cid, use_ai=True: seen.append(use_ai) or real(conn, cid, use_ai=False))
    d = upload(client, True)
    assert seen == [True] and d["ai_status"] == "ok" and d["ai_detail"] is None


def test_dict_return_uses_status_ai(m, client, monkeypatch):
    monkeypatch.setattr(m, "probe_ai", lambda timeout=3: True)
    monkeypatch.setattr(m, "check_contract", lambda conn, cid, use_ai=True:
                        {"finding_count": 0, "status": {"ai": "partial", "ai_detail": "2 條逾時"}})
    d = upload(client, True)
    assert d["finding_count"] == 0 and d["ai_status"] == "partial" and d["ai_detail"] == "2 條逾時"


def test_not_requested_and_snapshot(m, client):
    d = upload(client, False)
    assert d["ai_status"] == "not_requested" and d["finding_count"] >= 2
    det = client.get(f"/api/contracts/{d['contract_id']}").json()
    assert det["law_version"].startswith("民國114年11月11日修正｜抓取 ")
    for f in det["findings"]:
        assert f["article_snapshot"] == f["article_content"] and f["law_version"] == det["law_version"]


def test_zero_findings_distinguishes(m, client, monkeypatch):
    """0 筆疑慮：AI 失敗時要有待人工確認的條款；AI 成功時沒有。"""
    monkeypatch.setattr(m, "check_contract", lambda conn, cid, use_ai=True: 0)
    monkeypatch.setattr(m, "probe_ai", lambda timeout=3: False)
    bad = client.get(f"/api/contracts/{upload(client, True)['contract_id']}").json()
    assert bad["ai_status"] == "failed" and not bad["findings"]
    nr = [c for c in bad["clauses"] if c["needs_review"]]
    assert nr and all("AI 未完成" in c["needs_review_reason"] for c in nr)
    monkeypatch.setattr(m, "probe_ai", lambda timeout=3: True)
    good = client.get(f"/api/contracts/{upload(client, True)['contract_id']}").json()
    assert good["ai_status"] == "ok" and not any(c["needs_review"] for c in good["clauses"])


def test_needs_review_rules():
    from app.main import needs_review
    cl = [{"seq": 1, "text": "乙方應保護客戶姓名"}, {"seq": 2, "text": "付款條件"}, {"seq": 3, "text": "個人資料"}]
    out = needs_review([dict(c) for c in cl], [{"clause_seq": 3}], "failed")
    assert [c["needs_review"] for c in out] == [True, False, False]
    assert not any(c["needs_review"] for c in needs_review([dict(c) for c in cl], [], None))  # 舊資料不判定
