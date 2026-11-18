"""重新爬取個人資料保護法並安全更新資料庫（可重複執行，不會產生重複資料）。

Usage: py -3.12 scripts/update_law.py [--from-file PATH] [--dry-run] [--db PATH]
Exit code: 0 = 有更新或無變動；2 = 抓取/解析/驗證失敗（資料庫未被修改）。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import laws  # noqa: E402
from app.db import connect, init_db  # noqa: E402

DB = ROOT / "data" / "app.db"
RAW_DIR = ROOT / "data" / "raw"
LOG = ROOT / "data" / "law_update_log.jsonl"


def write_log(log_path: Path, entry: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_update(db_path=DB, from_file=None, dry_run=False, raw_dir=RAW_DIR, log_path=LOG,
               source_url=laws.SOURCE_URL) -> tuple[int, dict]:
    started = laws.now_tw()
    entry = {"time": started, "law_id": laws.LAW_ID, "source": str(from_file) if from_file else source_url,
             "dry_run": dry_run}
    try:
        # 1. 抓取（或讀離線檔），原始檔一律留存，方便事後追查
        if from_file:
            raw = Path(from_file).read_bytes()
            raw_path = str(from_file)
        else:
            raw = laws.fetch_law_html(source_url)
            Path(raw_dir).mkdir(parents=True, exist_ok=True)
            stamp = started.replace(":", "").replace("-", "")[:15]
            rp = Path(raw_dir) / f"{laws.LAW_ID}_{stamp}.html"
            rp.write_bytes(raw)
            raw_path = str(rp)
        entry["raw_path"] = raw_path
        # 2. 解析 + 驗證（任何一項不通過 → 不寫入）
        parsed = laws.parse_law_html(raw.decode("utf-8", errors="replace"))
        conn = connect(str(db_path))
        try:
            init_db(conn)
            cur = conn.execute("SELECT COUNT(*) FROM articles WHERE law_id=?", (laws.LAW_ID,)).fetchone()[0]
            errs = laws.validate_parsed(parsed, cur or None)
            if errs:
                raise ValueError("驗證未通過：" + "；".join(errs))
            # 3+4. 比對並在單一交易內寫入
            res = laws.apply_law_update(conn, parsed, source_url=source_url, raw_path=raw_path,
                                        fetched_at=started, dry_run=dry_run)
        finally:
            conn.close()
        entry.update(result=res["result"], version_no=res["version_no"], counts=res["counts"],
                     article_count=res["article_count"], amended_date=res["amended_date"],
                     changed=res["changed"], added=res["added"], removed=res["removed"], error=None)
        code = 0
    except Exception as e:  # noqa: BLE001
        entry.update(result="FAIL", error=f"{type(e).__name__}: {e}")
        code = 2
    write_log(Path(log_path), entry)
    return code, entry


def summary_text(e: dict) -> str:
    tag = "（試跑，未寫入）" if e.get("dry_run") else ""
    if e["result"] == "FAIL":
        return f"[失敗] 法規更新失敗，資料庫未變動。\n原因：{e['error']}"
    c = e["counts"]
    head = (f"[無變動]{tag} 內容與第 {e['version_no']} 版相同，不建立新版本。" if e["result"] == "NOCHANGE"
            else f"[已更新]{tag} 建立第 {e['version_no']} 版（修正日期：{e['amended_date']}）。")
    lines = [head, f"條數 {e['article_count']}：新增 {c['added']}、修改 {c['changed']}、刪除 {c['removed']}、未變 {c['unchanged']}"]
    for k, label in (("changed", "修改"), ("added", "新增"), ("removed", "刪除")):
        if e.get(k):
            lines.append(f"  {label}條號：{', '.join(e[k])}")
    if e["result"] == "OK":
        lines.append("建議：執行 eval 確認審查結果未退步（見 docs/law_update.md）。")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="重新爬取並更新法條")
    ap.add_argument("--from-file", help="改用本機 HTML（離線測試）")
    ap.add_argument("--dry-run", action="store_true", help="只比對不寫入")
    ap.add_argument("--db", default=str(DB))
    a = ap.parse_args(argv)
    code, entry = run_update(a.db, a.from_file, a.dry_run)
    sys.stdout.reconfigure(encoding="utf-8")
    print(summary_text(entry))
    return code


if __name__ == "__main__":
    sys.exit(main())
