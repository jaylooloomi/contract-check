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


def test_AT7_ai_raw_distinguishes_failure_from_no_issue():
    from app.check import ai_check_raw
    cands = [{"article_no": "20", "content": "x"}]
    def boom(prompt):
        raise TimeoutError("slow")
    assert ai_check_raw({"seq": 1, "text": "x"}, cands, caller=boom) is None
    assert ai_check_raw({"seq": 1, "text": "x"}, cands, caller=lambda p: '{"judgments":[]}') == []
    assert ai_check_raw({"seq": 1, "text": "x"}, cands, caller=lambda p: "not json") is None


def test_ai_per_candidate_judgments_filter_false():
    from app.check import ai_check_raw
    cands = [{"article_no": "20", "content": "x"}, {"article_no": "11", "content": "y"}]
    raw = ('{"judgments":[{"article_no":"20","reason":"r","violates":true,"title":"t"},'
           '{"article_no":"11","reason":"r","violates":false}]}')
    out = ai_check_raw({"seq": 3, "text": "x"}, cands, caller=lambda p: raw)
    assert [f["article_no"] for f in out] == ["20"]


@pytest.mark.parametrize("text,art", [
    ("乙方得將會員資料販售予廣告業者。", "20"),
    ("乙方得將客戶名單有償提供給其他公司。", "20"),
    ("當事人請求刪除其個人資料者，乙方得不予受理。", "11"),
    ("乙方得拒絕當事人停止處理之請求。", "11"),
    ("乙方得將資料傳輸至美國之伺服器存放。", "21"),
    ("乙方得將資料存放於海外機房。", "21"),
])
def test_rule_synonyms(text, art):
    assert art in [f["article_no"] for f in rule_check({"seq": 1, "text": text})]


@pytest.mark.parametrize("text", [
    "乙方不得出售或轉售任何會員資料。",
    "當事人請求刪除時，乙方不得拒絕。",
    "乙方不得將資料傳輸至境外。",
])
def test_rule_negation_not_flagged(text):
    assert rule_check({"seq": 1, "text": text}) == []


def test_candidates_include_core(conn):
    from app.check import candidates_for, CORE_ARTICLES
    got = [a["article_no"] for a in candidates_for({"seq": 1, "text": "雙方合意管轄法院。"}, conn)]
    assert set(CORE_ARTICLES) <= set(got) and len(got) == len(set(got)) <= 10


def test_check_contract_returns_status(monkeypatch):
    import sqlite3
    import app.check as chk
    mem = sqlite3.connect(":memory:")
    mem.row_factory = sqlite3.Row
    mem.executescript(
        "CREATE TABLE clauses(id INTEGER PRIMARY KEY, contract_id INT, seq INT, text TEXT);"
        "CREATE TABLE findings(id INTEGER PRIMARY KEY, contract_id, clause_id, source, title, reason,"
        " law_id, article_no, created_at);"
        "CREATE TABLE articles(law_id, article_no);")
    mem.executemany("INSERT INTO articles VALUES(?,?)", [(LAW_ID, "20"), (LAW_ID, "11"), (LAW_ID, "12")])
    for i, t in enumerate(CLAUSES, 1):
        mem.execute("INSERT INTO clauses(contract_id,seq,text) VALUES(1,?,?)", (i, t))
    monkeypatch.setattr(chk, "candidates_for", lambda c, conn: [{"article_no": "20", "content": "x"}])
    r = chk.check_contract(mem, 1, use_ai=False)
    assert r["status"] == {"ai": "not_requested", "ai_errors": 0, "clauses_checked": 5}
    assert r["finding_count"] >= 2

    def down(prompt):
        raise ConnectionError("ollama down")
    monkeypatch.setattr(chk, "_call_ollama", down)
    r = chk.check_contract(mem, 1, use_ai=True)
    assert r["status"]["ai"] == "failed" and r["status"]["ai_errors"] == 5
