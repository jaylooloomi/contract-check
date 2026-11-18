import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import update_law  # noqa: E402
from app import laws  # noqa: E402
from app.db import connect, init_db  # noqa: E402

RAW = ROOT / "data" / "raw" / f"{laws.LAW_ID}_LawAll.html"


@pytest.fixture
def env(tmp_path):
    db = tmp_path / "app.db"
    conn = connect(str(db))
    init_db(conn)
    laws.import_law(conn, laws.parse_law_html(RAW.read_text(encoding="utf-8")), fetched_at="2026-01-01T00:00:00+08:00")
    conn.close()
    return {"db": db, "log": tmp_path / "log.jsonl", "raw_dir": tmp_path / "raw", "tmp": tmp_path}


def run(env, **kw):
    return update_law.run_update(env["db"], log_path=env["log"], raw_dir=env["raw_dir"], **kw)


def snapshot(db):
    c = sqlite3.connect(db)
    out = {}
    for t in ("laws", "articles", "law_versions", "article_history"):
        try:
            out[t] = c.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()
        except sqlite3.OperationalError:
            out[t] = None
    c.close()
    return out


def counts(db):
    c = sqlite3.connect(db)
    r = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("articles", "law_versions", "article_history")}
    c.close()
    return r


def modified_html(tmp_path) -> tuple[Path, str]:
    """修改第 20 條內容，並刪除最後一條。"""
    s = BeautifulSoup(RAW.read_text(encoding="utf-8"), "html.parser")
    rows = [r for r in s.select("div.law-reg-content > div.row") if r.select_one(".col-no a")]
    def no(r):
        a = r.select_one(".col-no a")
        return a.get("name") or a.get_text()
    r20 = next(r for r in rows if no(r) == "20")
    first = r20.select_one(".law-article > div")
    first.string = first.get_text() + "（測試修正文字）"
    removed = no(rows[-1])
    rows[-1].decompose()
    p = tmp_path / "modified.html"
    p.write_text(str(s), encoding="utf-8")
    return p, removed


def test_first_run_initializes_v1_and_rerun_is_idempotent(env):
    code, e = run(env, from_file=RAW)
    assert code == 0 and e["result"] == "NOCHANGE" and e["version_no"] == 1
    n = counts(env["db"])
    assert n["law_versions"] == 1 and n["article_history"] == n["articles"]
    before = snapshot(env["db"])
    code, e = run(env, from_file=RAW)
    assert code == 0 and e["result"] == "NOCHANGE"
    after = snapshot(env["db"])
    for t in ("articles", "law_versions", "article_history"):
        assert before[t] == after[t]
    logs = [json.loads(x) for x in env["log"].read_text(encoding="utf-8").splitlines()]
    assert [x["result"] for x in logs] == ["NOCHANGE", "NOCHANGE"]


def test_changed_article_creates_version_2(env):
    run(env, from_file=RAW)
    n0 = counts(env["db"])
    path, removed = modified_html(env["tmp"])
    code, e = run(env, from_file=path)
    assert code == 0 and e["result"] == "OK" and e["version_no"] == 2
    assert e["counts"]["changed"] == 1 and e["counts"]["removed"] == 1 and e["counts"]["added"] == 0
    assert e["changed"] == ["20"] and e["removed"] == [removed]
    conn = connect(str(env["db"]))
    assert "測試修正文字" in laws.get_article(conn, laws.LAW_ID, "20")["content"]
    assert laws.get_article(conn, laws.LAW_ID, removed) is None
    assert laws.search_articles(conn, "測試修正文字")[0]["article_no"] == "20"  # FTS 已同步
    hist = conn.execute("SELECT version_no, content, valid_to FROM article_history WHERE article_no='20' "
                        "ORDER BY version_no").fetchall()
    assert [h["version_no"] for h in hist] == [1, 2]
    assert hist[0]["valid_to"] is not None and hist[1]["valid_to"] is None
    assert "測試修正文字" not in hist[0]["content"]
    gone = conn.execute("SELECT valid_to FROM article_history WHERE article_no=?", (removed,)).fetchone()
    assert gone["valid_to"] is not None
    assert counts(env["db"])["articles"] == n0["articles"] - 1
    assert [v["version_no"] for v in laws.law_history(conn)] == [2, 1]
    conn.close()
    # 再跑一次同樣的新內容 → 不會出現第 3 版
    code, e = run(env, from_file=path)
    assert e["result"] == "NOCHANGE" and e["version_no"] == 2
    assert counts(env["db"])["law_versions"] == 2


def test_dry_run_writes_nothing(env):
    run(env, from_file=RAW)
    before = snapshot(env["db"])
    path, _ = modified_html(env["tmp"])
    code, e = run(env, from_file=path, dry_run=True)
    assert code == 0 and e["result"] == "OK" and e["counts"]["changed"] == 1
    assert snapshot(env["db"]) == before


@pytest.mark.parametrize("html", ["<html><body>維護中</body></html>", "BROKEN<<<"])
def test_broken_html_fails_and_db_untouched(env, html):
    before = snapshot(env["db"])
    p = env["tmp"] / "broken.html"
    p.write_text(html, encoding="utf-8")
    code, e = run(env, from_file=p)
    assert code == 2 and e["result"] == "FAIL" and "驗證未通過" in e["error"]
    assert snapshot(env["db"]) == before
    assert json.loads(env["log"].read_text(encoding="utf-8").splitlines()[-1])["result"] == "FAIL"


def test_too_few_articles_fails(env):
    s = BeautifulSoup(RAW.read_text(encoding="utf-8"), "html.parser")
    rows = s.select("div.law-reg-content > div.row")
    for r in rows[len(rows) // 2:]:
        r.decompose()
    p = env["tmp"] / "half.html"
    p.write_text(str(s), encoding="utf-8")
    before = snapshot(env["db"])
    code, e = run(env, from_file=p)
    assert code == 2 and "條數" in e["error"]
    assert snapshot(env["db"]) == before


def test_network_error_fails_and_db_untouched(env, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("抓取失敗（已重試 2 次）：timed out")
    monkeypatch.setattr(laws, "fetch_law_html", boom)
    before = snapshot(env["db"])
    code, e = run(env)
    assert code == 2 and e["result"] == "FAIL" and "timed out" in e["error"]
    assert snapshot(env["db"]) == before
    assert json.loads(env["log"].read_text(encoding="utf-8").splitlines()[-1])["error"]


def test_fetch_retries_with_backoff(monkeypatch):
    calls, sleeps = [], []
    def fake_urlopen(req, timeout):
        calls.append(timeout)
        raise OSError("down")
    monkeypatch.setattr(laws.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(laws.time, "sleep", sleeps.append)
    with pytest.raises(RuntimeError):
        laws.fetch_law_html("http://x", timeout=5, retries=2, backoff=1)
    assert len(calls) == 3 and sleeps == [1, 2]


def test_live_fetch_saves_raw(env, monkeypatch):
    monkeypatch.setattr(laws, "fetch_law_html", lambda *a, **k: RAW.read_bytes())
    code, e = run(env)
    assert code == 0 and Path(e["raw_path"]).exists() and Path(e["raw_path"]).parent == env["raw_dir"]


def test_validate_rules():
    good = laws.parse_law_html(RAW.read_text(encoding="utf-8"))
    assert laws.validate_parsed(good, len(good["articles"])) == []
    bad = dict(good, amended_date=None, articles=[a for a in good["articles"] if a["article_no"] != "2"])
    errs = laws.validate_parsed(bad, 100)
    assert any("第 2 條" in x for x in errs) and any("修正日期" in x for x in errs) and any("±" in x for x in errs)
