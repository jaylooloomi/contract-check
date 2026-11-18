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


# ---------------------------------------------------------------------------
# 可重新爬取的更新流程（re-crawl pipeline）：抓取 → 驗證 → 逐條比對 → 單一交易寫入
# ---------------------------------------------------------------------------
import hashlib  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
import urllib.request  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

KEY_ARTICLES = ("1", "2", "20")
MIN_ARTICLES = 50
COUNT_TOLERANCE = 0.10

VERSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS law_versions(id INTEGER PRIMARY KEY, law_id TEXT, version_no INTEGER, amended_date TEXT,
  fetched_at TEXT, source_url TEXT, raw_path TEXT, content_hash TEXT, article_count INTEGER, status TEXT,
  summary_json TEXT, UNIQUE(law_id, version_no));
CREATE TABLE IF NOT EXISTS article_history(id INTEGER PRIMARY KEY, law_id TEXT, article_no TEXT, version_no INTEGER,
  content TEXT, content_hash TEXT, valid_from TEXT, valid_to TEXT, UNIQUE(law_id, article_no, version_no));
"""


def now_tw() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def normalize(text: str) -> str:
    """比對前正規化：去掉所有空白差異，避免排版變動被誤判為修法。"""
    return re.sub(r"\s+", "", text or "")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def article_hash(content: str) -> str:
    return sha256(normalize(content))


def law_hash(articles) -> str:
    """整部法規的指紋：依條號排序後的 (條號, 單條 hash)。"""
    pairs = sorted((a["article_no"], article_hash(a["content"])) for a in articles)
    return sha256(json.dumps(pairs, ensure_ascii=False))


def fetch_law_html(url: str = SOURCE_URL, timeout: float = 30, retries: int = 2, backoff: float = 2.0) -> bytes:
    """抓取官方頁面；失敗重試 retries 次（等待 backoff, backoff*2 秒）。全部失敗則拋出最後的錯誤。"""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (contract-check law updater)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - 任何網路錯誤都要重試
            last = e
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
    raise RuntimeError(f"抓取失敗（已重試 {retries} 次）：{last!r}")


def validate_parsed(parsed: dict, current_count: int | None) -> list[str]:
    """寫入前的檢查；回傳錯誤清單（空清單代表通過）。"""
    errs = []
    arts = parsed.get("articles") or []
    n = len(arts)
    if n < MIN_ARTICLES:
        errs.append(f"條數過少：{n} < {MIN_ARTICLES}")
    if current_count and abs(n - current_count) > current_count * COUNT_TOLERANCE:
        errs.append(f"條數變動超過 ±{int(COUNT_TOLERANCE * 100)}%：資料庫 {current_count} → 新抓 {n}")
    nos = [a["article_no"] for a in arts]
    for k in KEY_ARTICLES:
        if k not in nos:
            errs.append(f"缺少關鍵條文：第 {k} 條")
    empty = [a["article_no"] for a in arts if not normalize(a["content"])]
    if empty:
        errs.append(f"內容為空的條文：{', '.join(empty[:10])}")
    dup = sorted({x for x in nos if nos.count(x) > 1})
    if dup:
        errs.append(f"重複條號：{', '.join(dup)}")
    if not parsed.get("amended_date") or not re.search(r"\d+\s*年", parsed["amended_date"]):
        errs.append("無法解析修正日期")
    return errs


def ensure_versioning(conn: sqlite3.Connection, law_id: str = LAW_ID, raw_path: str | None = None) -> None:
    """建立版本表；第一次執行時把目前資料庫內的條文登錄為第 1 版（不提交，交由呼叫端交易處理）。"""
    for stmt in VERSION_SCHEMA.split(";"):  # 不用 executescript：它會先 COMMIT，破壞單一交易
        if stmt.strip():
            conn.execute(stmt)
    if conn.execute("SELECT 1 FROM law_versions WHERE law_id=?", (law_id,)).fetchone():
        return
    rows = [dict(r) for r in conn.execute(
        "SELECT article_no, content FROM articles WHERE law_id=? ORDER BY id", (law_id,))]
    if not rows:
        return
    law = conn.execute("SELECT amended_date, fetched_at, source_url FROM laws WHERE id=?", (law_id,)).fetchone()
    valid_from = (law["fetched_at"] if law else None) or now_tw()
    conn.execute(
        "INSERT INTO law_versions(law_id,version_no,amended_date,fetched_at,source_url,raw_path,content_hash,"
        "article_count,status,summary_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (law_id, 1, law["amended_date"] if law else None, valid_from, law["source_url"] if law else SOURCE_URL,
         raw_path, law_hash(rows), len(rows), "initial",
         json.dumps({"note": "由既有資料庫初始化", "added": len(rows)}, ensure_ascii=False)))
    conn.executemany(
        "INSERT INTO article_history(law_id,article_no,version_no,content,content_hash,valid_from,valid_to) "
        "VALUES(?,?,?,?,?,?,NULL)",
        [(law_id, r["article_no"], 1, r["content"], article_hash(r["content"]), valid_from) for r in rows])


def diff_articles(old: dict, new_articles: list[dict]) -> dict:
    """old: {條號: 內容}；回傳各類條號清單。"""
    new = {a["article_no"]: a["content"] for a in new_articles}
    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    changed = [k for k in new if k in old and article_hash(new[k]) != article_hash(old[k])]
    unchanged = [k for k in new if k in old and k not in changed]
    return {"added": added, "changed": changed, "removed": removed, "unchanged": unchanged}


def latest_version(conn: sqlite3.Connection, law_id: str = LAW_ID) -> dict | None:
    r = conn.execute("SELECT * FROM law_versions WHERE law_id=? ORDER BY version_no DESC LIMIT 1", (law_id,)).fetchone()
    return dict(r) if r else None


def apply_law_update(conn: sqlite3.Connection, parsed: dict, *, source_url: str = SOURCE_URL,
                     raw_path: str | None = None, fetched_at: str | None = None, dry_run: bool = False) -> dict:
    """在單一交易內完成：初始化第 1 版（若需要）→ 比對 → 寫入新版本。
    回傳 {result: NOCHANGE|OK, version_no, diff counts, ...}；dry_run 時一律 rollback。"""
    law_id = parsed["law_id"]
    fetched_at = fetched_at or now_tw()
    conn.commit()  # 清掉呼叫端未提交的狀態，確保下面是一個乾淨的交易
    try:
        conn.execute("BEGIN IMMEDIATE")
        ensure_versioning(conn, law_id)
        old = {r["article_no"]: r["content"] for r in conn.execute(
            "SELECT article_no, content FROM articles WHERE law_id=?", (law_id,))}
        d = diff_articles(old, parsed["articles"])
        counts = {k: len(v) for k, v in d.items()}
        new_hash = law_hash(parsed["articles"])
        prev = latest_version(conn, law_id)
        res = {"law_id": law_id, "content_hash": new_hash, "counts": counts,
               "changed": d["changed"], "added": d["added"], "removed": d["removed"],
               "amended_date": parsed["amended_date"], "article_count": len(parsed["articles"])}
        if prev and prev["content_hash"] == new_hash:
            res.update(result="NOCHANGE", version_no=prev["version_no"])
            conn.execute("UPDATE laws SET fetched_at=? WHERE id=?", (fetched_at, law_id))  # 只記錄「最後確認時間」
        else:
            vno = (prev["version_no"] if prev else 0) + 1
            res.update(result="OK", version_no=vno)
            summary = {k: res[k] for k in ("counts", "changed", "added", "removed")}
            conn.execute(
                "INSERT INTO law_versions(law_id,version_no,amended_date,fetched_at,source_url,raw_path,content_hash,"
                "article_count,status,summary_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (law_id, vno, parsed["amended_date"], fetched_at, source_url, raw_path, new_hash,
                 len(parsed["articles"]), "active", json.dumps(summary, ensure_ascii=False)))
            conn.execute("UPDATE law_versions SET status='superseded' WHERE law_id=? AND version_no<?", (law_id, vno))
            # 歷史：舊條文結束有效期間；新增或修改的條文寫入新列；未變動的條文沿用舊列
            for no in d["changed"] + d["removed"]:
                conn.execute("UPDATE article_history SET valid_to=? WHERE law_id=? AND article_no=? AND valid_to IS NULL",
                             (fetched_at, law_id, no))
            new_map = {a["article_no"]: a for a in parsed["articles"]}
            conn.executemany(
                "INSERT INTO article_history(law_id,article_no,version_no,content,content_hash,valid_from,valid_to) "
                "VALUES(?,?,?,?,?,?,NULL)",
                [(law_id, no, vno, new_map[no]["content"], article_hash(new_map[no]["content"]), fetched_at)
                 for no in d["added"] + d["changed"]])
            # 現行條文表（觸發器同步 FTS）
            conn.executemany("DELETE FROM articles WHERE law_id=? AND article_no=?", [(law_id, no) for no in d["removed"]])
            conn.executemany("UPDATE articles SET content=?, chapter=? WHERE law_id=? AND article_no=?",
                             [(new_map[no]["content"], new_map[no]["chapter"], law_id, no) for no in d["changed"]])
            conn.executemany("INSERT INTO articles(law_id,article_no,chapter,content) VALUES(?,?,?,?)",
                             [(law_id, no, new_map[no]["chapter"], new_map[no]["content"]) for no in d["added"]])
            conn.execute(
                "INSERT INTO laws(id,name,source_url,amended_date,fetched_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, source_url=excluded.source_url, "
                "amended_date=excluded.amended_date, fetched_at=excluded.fetched_at",
                (law_id, parsed["name"], source_url, parsed["amended_date"], fetched_at))
        if dry_run:
            conn.rollback()
            res["dry_run"] = True
        else:
            conn.commit()
        return res
    except Exception:
        conn.rollback()
        raise


def law_history(conn: sqlite3.Connection, law_id: str = LAW_ID) -> list[dict]:
    try:
        rows = conn.execute("SELECT version_no, amended_date, fetched_at, source_url, content_hash, article_count, "
                            "status, summary_json FROM law_versions WHERE law_id=? ORDER BY version_no DESC",
                            (law_id,)).fetchall()
    except sqlite3.OperationalError:  # 尚未執行過更新流程
        return []
    out = []
    for r in rows:
        d = dict(r)
        d["summary"] = json.loads(d.pop("summary_json") or "{}")
        out.append(d)
    return out
