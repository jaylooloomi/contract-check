"""檢查引擎：規則檢查 + 本機 AI（Ollama）檢查 + 引用驗證。介面見 spec.md §4。"""
import json
import re
import urllib.request
from datetime import datetime

LAW_ID = "I0050021"  # 個人資料保護法
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"

# 規則 v2：(命中的正規表示式, 排除的正規表示式（命中就不算疑慮）, 疑慮標題, 理由, 條號)
# v1 只有 3 條規則、沒有排除條件，實測誤報偏高；v2 依實測分析加入排除條件與 2 條新規則。
_PERMIT = r"(非經|未經).{0,10}同意|不得|除依|僅於法令|依法"  # 「限制」而不是「允許」的寫法
RULES = [
    (r"(提供|轉交|揭露|分享|共享).{0,14}(關係企業|第三人|第三方|他人|合作夥伴|廣告商)"
     r"|(關係企業|第三人|合作夥伴|廣告商).{0,12}(行銷|推廣|推銷|推送)",
     _PERMIT,
     "提供第三人作原目的以外使用",
     "條款允許將資料提供他人或用於行銷，可能超出原蒐集之特定目的，需確認是否符合目的外利用之例外（如當事人同意）。",
     "20"),
    (r"(永久|無限期|不限期|不設期限|長期).{0,8}(保存|保留|留存|保管)|(繼續|仍得).{0,4}留存|不因.{0,6}(銷毀|刪除)",
     r"(日內|期限屆滿).{0,6}(刪除|銷毀|返還)",
     "目的消失後仍保存資料",
     "約定無期限保存，可能與特定目的消失或期限屆滿應刪除、停止處理之要求衝突。",
     "11"),
    # OCR 會把「洩」誤認成「浅」、漏掉「須」，所以這裡放寬比對
    (r"(外洩|洩漏|外泄|泄漏|外浅|外流|竊取|侵害|入侵|未經授權之?存取).{0,20}(無|不|免|毋).{0,3}(另行)?通知",
     None,
     "資料外洩不通知當事人",
     "排除外洩通知義務，可能與查明後應通知當事人之規定衝突。",
     "12"),
    (r"病歷|醫療|基因|性生活|健康檢查|犯罪前科",
     r"不得(蒐集|處理)",
     "蒐集特種個人資料",
     "涉及病歷、醫療、基因、性生活、健康檢查或犯罪前科等特種資料，原則上不得蒐集、處理或利用，需確認是否符合法定例外。",
     "6"),
    (r"境外|國外|海外|跨境",
     None,
     "個人資料國際傳輸",
     "涉及將資料傳輸至境外，需確認是否受主管機關限制，並宜約定告知傳輸地點。",
     "21"),
]


def _finding(seq, source, title, reason, article_no):
    return {"clause_seq": seq, "source": source, "title": title, "reason": reason,
            "law_id": LAW_ID, "article_no": str(article_no)}


def rule_check(clause, conn=None):
    out = []
    for pat, exclude, title, reason, art in RULES:
        t = clause["text"]
        if re.search(pat, t) and not (exclude and re.search(exclude, t)):
            out.append(_finding(clause["seq"], "rule", title, reason, art))
    return out


PROMPT = """/no_think
你是協助法務人員的合約審閱助理。請判斷下列合約條款是否可能與候選法條有疑慮。
規則：
1. 只能引用下方「候選法條」中的條號，不得引用其他條號。
2. 只回傳 JSON 陣列，不要任何其他文字。格式：[{{"title":"疑慮標題","reason":"理由（一句）","article_no":"條號"}}]
3. 使用繁體中文。
4. 不確定或沒有疑慮時回傳 []。

合約條款：{clause}

候選法條：
{cands}
"""


def _call_ollama(prompt, timeout=90):
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                       "format": "json", "keep_alive": "2h",
                       "options": {"temperature": 0}}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))["response"]


def _parse(raw):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    data = json.loads(raw)
    if isinstance(data, dict):  # format=json 有時包一層
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data] if "article_no" in data else []
    return data if isinstance(data, list) else []


def ai_check(clause, candidates, caller=None):
    """失敗（Ollama 沒開、逾時、格式錯）一律回傳 []，不中斷流程（AT7）。"""
    if not candidates:
        return []
    cands = "\n".join(f"第{c['article_no']}條：{c['content'][:300]}" for c in candidates)
    try:
        raw = (caller or _call_ollama)(PROMPT.format(clause=clause["text"], cands=cands))
        items = _parse(raw)
    except Exception:
        return []
    out = []
    allowed = {str(c["article_no"]) for c in candidates}
    for it in items:
        if not isinstance(it, dict):
            continue
        no = re.sub(r"[第條\s]", "", str(it.get("article_no", "")))
        if no not in allowed:  # 只能引用候選法條
            continue
        out.append(_finding(clause["seq"], "ai", str(it.get("title", "AI 提示疑慮"))[:60],
                            str(it.get("reason", ""))[:300], no))
    return out


def validate_citations(findings, conn):
    """只保留條號真的存在於資料庫的 Finding（AT5）。"""
    keep = []
    for f in findings:
        row = conn.execute("SELECT 1 FROM articles WHERE law_id=? AND article_no=?",
                           (f["law_id"], f["article_no"])).fetchone()
        if row:
            keep.append(f)
    return keep


# 條款文字 → 檢索用關鍵詞（FTS trigram 需 ≥3 字）
SEARCH_TERMS = ["個人資料", "當事人", "第三人", "特定目的", "刪除", "通知當事人",
                "行銷", "保存", "安全維護", "委託", "洩漏", "竊取"]


def candidates_for(clause, conn, limit=4):
    from app.laws import search_articles
    seen, out = set(), []
    terms = [t for t in SEARCH_TERMS if t[:2] in clause["text"]] or ["個人資料"]
    for t in terms:
        for a in search_articles(conn, t, limit=limit):
            if a["article_no"] not in seen:
                seen.add(a["article_no"])
                out.append(a)
    return out[:6]


def check_contract(conn, contract_id, use_ai=True):
    clauses = conn.execute("SELECT * FROM clauses WHERE contract_id=? ORDER BY seq",
                           (contract_id,)).fetchall()
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    total = 0
    for row in clauses:
        c = dict(row)
        fs = rule_check(c, conn)
        if use_ai:
            ai = ai_check(c, candidates_for(c, conn))
            have = {f["article_no"] for f in fs}
            fs += [f for f in ai if f["article_no"] not in have]  # 規則已命中同條就不重複
        for f in validate_citations(fs, conn):
            conn.execute(
                "INSERT INTO findings(contract_id,clause_id,source,title,reason,law_id,article_no,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (contract_id, c["id"], f["source"], f["title"], f["reason"], f["law_id"], f["article_no"], now))
            total += 1
    conn.commit()
    return total
