"""FastAPI：API 合約見 spec.md §6。啟動：py -3.12 -m uvicorn app.main:app --port 8000"""
import json
import os
import shutil
import tempfile
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
    n = check_contract(conn, cid, use_ai=use_ai)
    return {"contract_id": cid, "extract_method": r["method"], "clause_count": len(clauses), "finding_count": n}


@app.get("/api/contracts")
def list_contracts(limit: int = 50):
    """歷史列表：最新的在前，附疑慮數與待複核數，方便直接打開不必重跑。"""
    rows = conn.execute(
        "SELECT c.id, c.filename, c.uploaded_at, c.extract_method,"
        " (SELECT COUNT(*) FROM clauses WHERE contract_id=c.id) AS clause_count,"
        " (SELECT COUNT(*) FROM findings WHERE contract_id=c.id) AS finding_count,"
        " (SELECT COUNT(*) FROM findings f WHERE f.contract_id=c.id"
        "   AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.finding_id=f.id)) AS pending_count"
        " FROM contracts c ORDER BY c.id DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
    return [dict(r) for r in rows]


@app.get("/static/apple.css")
def apple_css():
    return FileResponse(os.path.join(ROOT, "web", "apple.css"), media_type="text/css")


@app.get("/history")
def history_page():
    return FileResponse(os.path.join(ROOT, "web", "history.html"))


@app.get("/api/contracts/{cid}")
def get_contract(cid: int):
    c = conn.execute("SELECT id,filename,uploaded_at,extract_method FROM contracts WHERE id=?", (cid,)).fetchone()
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
    return {"contract": dict(c), "clauses": clauses, "findings": findings}


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
