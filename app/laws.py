"""Parse 全國法規資料庫 LawAll.aspx HTML and store/search articles."""
import re
import sqlite3
from pathlib import Path

from bs4 import BeautifulSoup

LAW_ID = "I0050021"
SOURCE_URL = f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={LAW_ID}"


def parse_law_html(html: str) -> dict:
    s = BeautifulSoup(html, "html.parser")
    name_el = s.find(id="hlLawName")
    name = name_el.get_text(strip=True) if name_el else "個人資料保護法"
    date_el = s.select_one("#trLNNDate td")
    amended = re.sub(r"\s+", " ", date_el.get_text()).strip() if date_el else None
    articles, chapter = [], None
    for el in s.select("div.law-reg-content > div"):
        cls = el.get("class") or []
        if "h3" in cls:
            chapter = re.sub(r"\s+", " ", el.get_text()).strip()
        elif "row" in cls:
            a = el.select_one(".col-no a")
            if not a:
                continue
            no = a.get("name") or re.sub(r"[第條\s]", "", a.get_text())
            lines = [d.get_text().strip() for d in el.select(".law-article > div")]
            articles.append({"article_no": no, "chapter": chapter,
                             "content": "\n".join(x for x in lines if x)})
    return {"law_id": LAW_ID, "name": name, "amended_date": amended, "articles": articles}


def import_law(conn: sqlite3.Connection, raw_path_or_data, source_url=SOURCE_URL, fetched_at=None) -> int:
    data = raw_path_or_data
    if isinstance(data, (str, Path)):
        data = parse_law_html(Path(data).read_text(encoding="utf-8"))
    conn.execute(
        "INSERT INTO laws(id,name,source_url,amended_date,fetched_at) VALUES(?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, source_url=excluded.source_url, "
        "amended_date=excluded.amended_date, fetched_at=excluded.fetched_at",
        (data["law_id"], data["name"], source_url, data["amended_date"], fetched_at),
    )
    conn.execute("DELETE FROM articles WHERE law_id=?", (data["law_id"],))
    conn.executemany(
        "INSERT INTO articles(law_id,article_no,chapter,content) VALUES(?,?,?,?)",
        [(data["law_id"], a["article_no"], a["chapter"], a["content"]) for a in data["articles"]],
    )
    conn.commit()
    return len(data["articles"])


def search_articles(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[dict]:
    q = (query or "").strip()
    if not q:
        return []
    if len(q) >= 3:
        rows = conn.execute(
            "SELECT a.law_id, a.article_no, a.content, -bm25(articles_fts) AS score FROM articles_fts "
            "JOIN articles a ON a.id = articles_fts.rowid WHERE articles_fts MATCH ? "
            "ORDER BY bm25(articles_fts) LIMIT ?",
            ('"' + q.replace('"', '""') + '"', limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT law_id, article_no, content, 1.0 AS score FROM articles WHERE content LIKE ? ORDER BY id LIMIT ?",
            (f"%{q}%", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_article(conn: sqlite3.Connection, law_id: str, article_no: str) -> dict | None:
    r = conn.execute(
        "SELECT law_id, article_no, chapter, content FROM articles WHERE law_id=? AND article_no=?",
        (law_id, str(article_no)),
    ).fetchone()
    return dict(r) if r else None
