"""Fetch 個人資料保護法 from law.moj.gov.tw (HTML scrape) and import into data/app.db.
Usage: py -3.12 scripts/import_law.py [--no-fetch]
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.db import connect, init_db  # noqa: E402
from app.laws import LAW_ID, SOURCE_URL, import_law, parse_law_html  # noqa: E402

RAW = ROOT / "data" / "raw" / f"{LAW_ID}_LawAll.html"


def main():
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if "--no-fetch" not in sys.argv or not RAW.exists():
        req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
        RAW.write_bytes(urllib.request.urlopen(req, timeout=30).read())
    fetched_at = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    data = parse_law_html(RAW.read_text(encoding="utf-8"))
    conn = connect(str(ROOT / "data" / "app.db"))
    init_db(conn)
    n = import_law(conn, data, SOURCE_URL, fetched_at)
    (ROOT / "data" / "law_source.json").write_text(json.dumps({
        "source_url": SOURCE_URL, "method": "html_scrape (LawAll.aspx)", "fetched_at": fetched_at,
        "amended_date": data["amended_date"], "article_count": n, "raw_file": "data/raw/" + RAW.name,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"articles imported: {n}")


if __name__ == "__main__":
    main()
