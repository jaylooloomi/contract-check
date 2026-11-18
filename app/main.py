"""FastAPI：API 合約見 spec.md §6。啟動：py -3.12 -m uvicorn app.main:app --port 8000"""
import json
import os
import shutil
import tempfile
import urllib.request
from datetime import datetime

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.check import check_contract
from app.db import connect, init_db
from app.extract import extract_text, split_clauses

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("CC_DB", os.path.join(ROOT, "data", "app.db"))

app = FastAPI(title="合約外規檢查")
conn = connect(DB_PATH)
init_db(conn)


# AI 服務探測：可用環境變數 CC_AI_PROBE_URL 覆寫（E2E 用不可達網址模擬「AI 沒開」）
AI_PROBE_URL = os.environ.get("CC_AI_PROBE_URL", "http://localhost:11434/api/tags")
AI_DOWN_DETAIL = "AI 服務未啟動，僅完成規則檢查"
# 「待人工確認」判準：條款提到個資相關字眼，卻沒有任何疑慮，且 AI 沒有成功跑完 → 規則找不到≠沒問題
PD_WORDS = ("個人資料", "個資", "姓名", "電話", "地址", "病歷", "帳號", "資料")


AI_NO_MODEL_DETAIL = "AI 服務有開，但找不到模型 {model}，僅完成規則檢查"


def probe_ai(timeout=3):
    """回傳 (可用?, 原因)。服務要能連上，而且模型真的存在，才算可用。"""
    from app.check import OLLAMA_MODEL
    try:
        with urllib.request.urlopen(AI_PROBE_URL, timeout=timeout) as r:
            if r.status != 200:
                return False, AI_DOWN_DETAIL
            names = {m.get("name", "") for m in json.loads(r.read().decode("utf-8")).get("models", [])}
    except Exception:
        return False, AI_DOWN_DETAIL
    want = OLLAMA_MODEL if ":" in OLLAMA_MODEL else OLLAMA_MODEL + ":latest"
    if want not in names and OLLAMA_MODEL not in names:
        return False, AI_NO_MODEL_DETAIL.format(model=OLLAMA_MODEL)
    return True, None


def law_version_text() -> str | None:
    """例：民國114年11月11日修正｜抓取 2026-11-18"""
    row = conn.execute("SELECT amended_date, fetched_at FROM laws LIMIT 1").fetchone()
    if not row:
        return None
    amended = (row["amended_date"] or "").replace(" ", "")
    return f"{amended}修正｜抓取 {(row['fetched_at'] or '')[:10]}"


def run_check(cid: int, use_ai: bool) -> dict:
    """呼叫 check_contract 並回傳明確狀態。相容 check_contract 回傳 int 或
    {"finding_count", "status": {"ai": ...}}（dict 版若有 status.ai 就以它為準）。"""
    ai_status, ai_detail = "not_requested", None
    if use_ai:
        ok, why = probe_ai()
        if ok:
            ai_status = "ok"
        else:
            use_ai, ai_status, ai_detail = False, "failed", why
    res = check_contract(conn, cid, use_ai=use_ai)
    if isinstance(res, dict):
        n = int(res.get("finding_count", 0))
        status = res.get("status") or {}
        st = status.get("ai")
        if ai_status != "failed":  # 探測已判定 AI 沒開時，以探測結果為準
            if isinstance(st, dict):  # 容許 {"status": ..., "detail": ...} 形式
                ai_status, ai_detail = st.get("status", ai_status), st.get("detail", ai_detail)
            elif isinstance(st, str):
                ai_status, ai_detail = st, status.get("ai_detail", ai_detail)
                errs, total = status.get("ai_errors", 0), status.get("clauses_checked", 0)
                if st == "failed" and not ai_detail:
                    ai_detail = f"AI 呼叫全部失敗（逾時或出錯，{errs}/{total} 條），僅完成規則檢查"
                elif st == "partial" and not ai_detail:
                    ai_detail = f"AI 有 {errs}/{total} 條未完成（逾時或出錯），這些條款只有規則檢查"
    else:
        n = int(res)
    version = law_version_text()
    conn.execute("UPDATE contracts SET rule_status='ok', ai_status=?, ai_detail=?, law_version=? WHERE id=?",
                 (ai_status, ai_detail, version, cid))
    # 引用快照：把當下法條原文與版本凍結在疑慮上，日後法規更新也能追溯當時依據
    conn.execute(
        "UPDATE findings SET article_snapshot=(SELECT a.content FROM articles a"
        " WHERE a.law_id=findings.law_id AND a.article_no=findings.article_no), law_version=?"
        " WHERE contract_id=? AND article_snapshot IS NULL", (version, cid))
    conn.commit()
    return {"finding_count": n, "rule_status": "ok", "ai_status": ai_status, "ai_detail": ai_detail,
            "law_version": version}


def needs_review(clauses, findings, ai_status):
    """回傳每條款的 needs_review／needs_review_reason。舊資料（ai_status 為 NULL）不判定。"""
    flagged = {f["clause_seq"] for f in findings}
    for c in clauses:
        hit = next((w for w in PD_WORDS if w in (c.get("text") or "")), None)
        nr = bool(ai_status and ai_status != "ok" and hit and c["seq"] not in flagged)
        c["needs_review"] = nr
        c["needs_review_reason"] = (f"條款提到「{hit}」但規則未比對到疑慮，且"
                                    f"{'未啟用 AI' if ai_status == 'not_requested' else 'AI 未完成'}，請人工確認"
                                    ) if nr else None
    return clauses


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


@app.get("/")
def index():
    return FileResponse(os.path.join(ROOT, "web", "index.html"))


@app.get("/v/b")
def version_b():
    return FileResponse(os.path.join(ROOT, "web", "v_b.html"))


@app.get("/v/c")
def version_c():
    return FileResponse(os.path.join(ROOT, "web", "v_c.html"))


@app.get("/v/wizard")
def version_wizard():
    return FileResponse(os.path.join(ROOT, "web", "v_wizard.html"))


@app.get("/api/law")
def law():
    row = conn.execute("SELECT * FROM laws LIMIT 1").fetchone()
    if not row:
        raise HTTPException(404, "法條尚未匯入")
    n = conn.execute("SELECT COUNT(*) FROM articles WHERE law_id=?", (row["id"],)).fetchone()[0]
    return {**dict(row), "article_count": n}


@app.post("/api/contracts")
def upload(file: UploadFile = File(...), use_ai: bool = False):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "只接受 PDF")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
    try:
        r = extract_text(tmp.name)
    finally:
        os.unlink(tmp.name)
    cur = conn.execute("INSERT INTO contracts(filename,uploaded_at,extract_method,raw_text) VALUES(?,?,?,?)",
                       (file.filename, now(), r["method"], r["text"]))
    cid = cur.lastrowid
    clauses = split_clauses(r["text"])
    for c in clauses:
        conn.execute("INSERT INTO clauses(contract_id,seq,title,text) VALUES(?,?,?,?)",
                     (cid, c["seq"], c["title"], c["text"]))
    conn.commit()
    st = run_check(cid, use_ai)
    return {"contract_id": cid, "extract_method": r["method"], "clause_count": len(clauses), **st}


@app.get("/api/contracts")
def list_contracts(limit: int = 50):
    """歷史列表：最新的在前，附疑慮數與待複核數，方便直接打開不必重跑。"""
    rows = conn.execute(
        "SELECT c.id, c.filename, c.uploaded_at, c.extract_method, c.rule_status, c.ai_status, c.ai_detail, c.law_version,"
        " (SELECT COUNT(*) FROM clauses WHERE contract_id=c.id) AS clause_count,"
        " (SELECT COUNT(*) FROM findings WHERE contract_id=c.id) AS finding_count,"
        " (SELECT COUNT(*) FROM findings f WHERE f.contract_id=c.id"
        "   AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.finding_id=f.id)) AS pending_count"
        " FROM contracts c ORDER BY c.id DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
    return [dict(r) for r in rows]


@app.get("/static/status.js")
def status_js():
    return FileResponse(os.path.join(ROOT, "web", "status.js"), media_type="text/javascript")


@app.get("/static/apple.css")
def apple_css():
    return FileResponse(os.path.join(ROOT, "web", "apple.css"), media_type="text/css")


@app.get("/history")
def history_page():
    return FileResponse(os.path.join(ROOT, "web", "history.html"))


@app.get("/api/contracts/{cid}")
def get_contract(cid: int):
    c = conn.execute("SELECT id,filename,uploaded_at,extract_method,rule_status,ai_status,ai_detail,law_version FROM contracts WHERE id=?", (cid,)).fetchone()
    if not c:
        raise HTTPException(404, "找不到合約")
    clauses = [dict(r) for r in conn.execute("SELECT * FROM clauses WHERE contract_id=? ORDER BY seq", (cid,))]
    findings = []
    for f in conn.execute(
            "SELECT f.*, cl.seq AS clause_seq, a.content AS article_content FROM findings f "
            "JOIN clauses cl ON cl.id=f.clause_id "
            "LEFT JOIN articles a ON a.law_id=f.law_id AND a.article_no=f.article_no "
            "WHERE f.contract_id=? ORDER BY cl.seq, f.id", (cid,)):
        d = dict(f)
        rv = conn.execute("SELECT decision,note,reviewed_at FROM reviews WHERE finding_id=? ORDER BY id DESC LIMIT 1",
                          (d["id"],)).fetchone()
        d["latest_review"] = dict(rv) if rv else None
        findings.append(d)
    needs_review(clauses, findings, c["ai_status"])
    return {"contract": dict(c), "clauses": clauses, "findings": findings,
            "rule_status": c["rule_status"], "ai_status": c["ai_status"], "ai_detail": c["ai_detail"],
            "law_version": c["law_version"]}


class Review(BaseModel):
    decision: str
    note: str | None = None


@app.post("/api/findings/{fid}/review")
def review(fid: int, body: Review):
    if body.decision not in ("confirm", "reject"):
        raise HTTPException(400, "decision 只能是 confirm 或 reject")
    if not conn.execute("SELECT 1 FROM findings WHERE id=?", (fid,)).fetchone():
        raise HTTPException(404, "找不到疑慮")
    conn.execute("INSERT INTO reviews(finding_id,decision,note,reviewed_at) VALUES(?,?,?,?)",
                 (fid, body.decision, body.note, now()))
    conn.commit()
    return {"ok": True}


@app.get("/api/law/history")
def law_history_api():
    from app.laws import LAW_ID, law_history
    return {"law_id": LAW_ID, "versions": law_history(conn, LAW_ID)}
