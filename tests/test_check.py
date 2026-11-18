import os
import pytest
from app.check import rule_check, ai_check, validate_citations, LAW_ID

ROOT = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(ROOT, "data", "app.db")

CLAUSES = [
    "甲方委託乙方處理甲方客戶之姓名、電話及地址等資料，以進行會員服務。",
    "乙方得將前條資料提供予其關係企業，用於行銷推廣。",
    "乙方應採取適當安全措施，防止資料被竊取或洩漏。",
    "合約終止後，乙方得永久保存前述資料，以備日後查核。",
    "資料如有外洩，乙方無須通知甲方或當事人。",
]
PLANTED = {2: "20", 4: "11", 5: "12"}  # 答案卷：條款序號 → 預期法條


def all_findings():
    out = []
    for i, t in enumerate(CLAUSES, 1):
        out += rule_check({"seq": i, "text": t})
    return out


def test_AT4_rule_finds_planted_issues():
    fs = all_findings()
    hit = {f["clause_seq"] for f in fs if PLANTED.get(f["clause_seq"]) == f["article_no"]}
    assert len(hit) >= 2, fs
    false_pos = [f for f in fs if f["clause_seq"] not in PLANTED]
    assert not false_pos, false_pos


@pytest.fixture
def conn():
    if not os.path.exists(DB):
        pytest.skip("法條資料庫尚未建立（A 線）")
    from app.db import connect
    c = connect(DB)
    yield c
    c.close()


def test_AT5_citations_exist_and_fake_filtered(conn):
    fs = all_findings()
    assert validate_citations(fs, conn) == fs  # 規則引用的條號都存在
    fake = dict(fs[0], article_no="999")
    assert validate_citations([fake], conn) == []


def test_AT7_ai_fallback_when_ollama_down():
    def boom(prompt):
        raise ConnectionError("ollama down")
    cands = [{"article_no": "20", "content": "x"}]
    assert ai_check({"seq": 1, "text": CLAUSES[1]}, cands, caller=boom) == []


def test_AT7_ai_rejects_non_candidate_citation():
    cands = [{"article_no": "20", "content": "x"}]
    fake = lambda p: '[{"title":"a","reason":"b","article_no":"20"},{"title":"c","reason":"d","article_no":"88"}]'
    out = ai_check({"seq": 2, "text": CLAUSES[1]}, cands, caller=fake)
    assert [f["article_no"] for f in out] == ["20"]
    assert out[0]["source"] == "ai" and out[0]["law_id"] == LAW_ID
