import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.db import connect, init_db  # noqa: E402
from app.laws import LAW_ID, get_article, import_law, parse_law_html, search_articles  # noqa: E402

RAW = ROOT / "data" / "raw" / f"{LAW_ID}_LawAll.html"


@pytest.fixture(scope="module")
def ctx():
    parsed = parse_law_html(RAW.read_text(encoding="utf-8"))
    conn = connect(":memory:")
    init_db(conn)
    n = import_law(conn, parsed)
    return conn, parsed, n


def test_count_matches_source(ctx):
    conn, parsed, n = ctx
    # independent count straight from the raw official HTML
    raw_count = len(re.findall(r'class="col-no">\s*<a href="LawSingle\.aspx\?pcode=I0050021(?:&amp;|&)flno=',
                               RAW.read_text(encoding="utf-8")))
    assert n == raw_count == len(parsed["articles"])
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == n
    assert 55 <= n <= 90


def test_idempotent(ctx):
    conn, parsed, n = ctx
    assert import_law(conn, parsed) == n
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == n


@pytest.mark.parametrize("no,phrase", [("11", "個人資料"), ("12", "通知當事人"), ("20", "利用")])
def test_sample_articles(ctx, no, phrase):
    a = get_article(ctx[0], LAW_ID, no)
    assert a and phrase in a["content"]


def test_missing_article(ctx):
    assert get_article(ctx[0], LAW_ID, "999") is None


def test_search(ctx):
    res = search_articles(ctx[0], "當事人同意")
    assert res and all("當事人同意" in r["content"] for r in res)
    assert search_articles(ctx[0], "同意")
