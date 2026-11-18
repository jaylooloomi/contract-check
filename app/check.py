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
_SALE_VERB = r"(出售|販售|販賣|轉售|轉賣|有償提供|讓與|出租|兜售)"
_DATA = r"(資料|個資|紀錄|名單|檔案|資訊)"
_SALE = _DATA + r".{0,12}" + _SALE_VERB + "|" + _SALE_VERB + r".{0,12}" + _DATA
# 拒絕當事人刪除／停止處理請求
_DEL = r"(刪除|停止(蒐集|處理|利用))"
_REFUSE = (r"(拒絕|不予|無須|不須|毋須|毋庸|得不).{0,6}" + _DEL
           + "|" + _DEL + r".{0,15}(得拒絕|得不予|不予受理|不受理|得不)")
_REFUSE_EX = r"不得(拒絕|不予)"
# 國際傳輸：境外類詞，或「移轉／傳輸／存放」附近出現國家或地區名
_REGIONS = (r"(新加坡|東南亞|東北亞|美國|加拿大|中國大陸|大陸地區|中國|香港|澳門|日本|韓國|歐盟|歐洲|英國|"
            r"印度|越南|菲律賓|馬來西亞|泰國|印尼|澳洲)")
_MOVE = r"(移轉|轉移|傳輸|傳送|存放|儲存|備份|處理|託管)"
_XBORDER = (r"境外|國外|海外|跨境|" + _MOVE + r".{0,15}" + _REGIONS + "|" + _REGIONS + r".{0,15}" + _MOVE)
_XBORDER_EX = r"(不得|禁止).{0,12}" + _MOVE + r".{0,12}(境外|國外|海外)"
RULES = [
    (r"(提供|轉交|揭露|分享|共享).{0,14}(關係企業|第三人|第三方|他人|合作夥伴|廣告商)"
     r"|(關係企業|第三人|合作夥伴|廣告商).{0,12}(行銷|推廣|推銷|推送)",
     _PERMIT,
     "提供第三人作原目的以外使用",
     "條款允許將資料提供他人或用於行銷，可能超出原蒐集之特定目的，需確認是否符合目的外利用之例外（如當事人同意）。",
     "20"),
    # 有償或無償轉出資料（出售類同義詞）：不論對象是誰都屬目的外利用
    (_SALE,
     r"不得.{0,6}" + _SALE_VERB,
     "出售或讓與個人資料",
     "條款允許出售、轉售或讓與個人資料，屬原蒐集目的以外之利用，需確認是否符合目的外利用之例外。",
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
    (_REFUSE, _REFUSE_EX,
     "拒絕當事人刪除請求",
     "條款允許拒絕當事人刪除或停止處理之請求，可能違反特定目的消失或當事人請求時應刪除之規定。",
     "11"),
    (_REFUSE, _REFUSE_EX,
     "限制當事人行使權利",
     "當事人請求刪除等權利不得預先拋棄或以特約限制，條款拒絕刪除請求可能牴觸此規定。",
     "3"),
    (_XBORDER,
     _XBORDER_EX,
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
你是協助法務人員的合約審閱助理。請逐一判斷下列合約條款是否可能違反或牴觸每一條「候選法條」。
規則：
1. 對每一條候選法條各回答一次：先用一句話說明理由，再判斷 violates 為 true 或 false。
2. 只有條款內容「允許、要求或排除」了該法條所規範的義務或權利時才判 true；條款只是一般敘述、或已在限制自己時判 false。
3. 只能使用下方候選法條的條號。
4. 只回傳 JSON，不要其他文字。格式：
{{"judgments":[{{"article_no":"條號","reason":"理由（一句）","violates":true或false,"title":"疑慮標題（violates 為 true 時填）"}}]}}
5. 使用繁體中文。

合約條款：{clause}

候選法條：
{cands}
"""


def _call_ollama(prompt, timeout=180):
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
    if not isinstance(data, list):
        raise ValueError("unexpected AI output shape")
    return data


def _truthy(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "yes", "1", "是", "有")


def ai_check_raw(clause, candidates, caller=None):
    """AI 檢查。成功回傳 list（可能是空的＝沒有疑慮）；失敗（Ollama 沒開、逾時、格式錯）回傳 None。"""
    if not candidates:
        return []
    cands = "\n".join(f"第{c['article_no']}條：{c['content'][:260]}" for c in candidates)
    try:
        raw = (caller or _call_ollama)(PROMPT.format(clause=clause["text"], cands=cands))
        items = _parse(raw)
    except Exception:
        return None
    out, seen = [], set()
    allowed = {str(c["article_no"]) for c in candidates}
    for it in items:
        if not isinstance(it, dict):
            continue
        if "violates" in it and not _truthy(it["violates"]):
            continue  # 逐條判斷為「沒有疑慮」
        no = re.sub(r"[第條\s]", "", str(it.get("article_no", "")))
        if no not in allowed or no in seen:  # 只能引用候選法條
            continue
        seen.add(no)
        out.append(_finding(clause["seq"], "ai", str(it.get("title") or "AI 提示疑慮")[:60],
                            str(it.get("reason", ""))[:300], no))
    return out


def ai_check(clause, candidates, caller=None):
    """相容包裝：失敗時回傳 []，不中斷流程（AT7）。要分辨失敗請用 ai_check_raw。"""
    r = ai_check_raw(clause, candidates, caller)
    return [] if r is None else r


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
                "行銷", "保存", "安全維護", "委託", "洩漏", "竊取", "國際傳輸", "停止處理"]
# 合約審閱最常相關的條文：一律放進候選，避免關鍵詞沒對到就漏掉正確法條
CORE_ARTICLES = ["3", "5", "6", "8", "11", "12", "19", "20", "21", "27"]
CANDIDATE_CAP = 10


def candidates_for(clause, conn, limit=4, cap=CANDIDATE_CAP):
    from app.laws import search_articles, get_article
    seen, out = set(), []
    for no in CORE_ARTICLES:
        a = get_article(conn, LAW_ID, no)
        if a and a["article_no"] not in seen:
            seen.add(a["article_no"])
            out.append(a)
    terms = [t for t in SEARCH_TERMS if t[:2] in clause["text"]]
    for t in terms:
        for a in search_articles(conn, t, limit=limit):
            if a["article_no"] not in seen and len(out) < cap:
                seen.add(a["article_no"])
                out.append(a)
    return out[:cap]


def check_contract(conn, contract_id, use_ai=True):
    """回傳 {"finding_count": int, "status": {"ai": "not_requested"|"ok"|"partial"|"failed",
    "ai_errors": int, "clauses_checked": int}}。"""
    clauses = conn.execute("SELECT * FROM clauses WHERE contract_id=? ORDER BY seq",
                           (contract_id,)).fetchall()
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    total, ai_errors, ai_calls = 0, 0, 0
    for row in clauses:
        c = dict(row)
        fs = rule_check(c, conn)
        if use_ai:
            ai_calls += 1
            ai = ai_check_raw(c, candidates_for(c, conn))
            if ai is None:
                ai_errors += 1
                ai = []
            have = {f["article_no"] for f in fs}
            fs += [f for f in ai if f["article_no"] not in have]  # 規則已命中同條就不重複
        for f in validate_citations(fs, conn):
            conn.execute(
                "INSERT INTO findings(contract_id,clause_id,source,title,reason,law_id,article_no,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (contract_id, c["id"], f["source"], f["title"], f["reason"], f["law_id"], f["article_no"], now))
            total += 1
    conn.commit()
    if not use_ai:
        ai = "not_requested"
    elif ai_errors == 0:
        ai = "ok"
    elif ai_errors < ai_calls:
        ai = "partial"
    else:
        ai = "failed"
    return {"finding_count": total,
            "status": {"ai": ai, "ai_errors": ai_errors, "clauses_checked": len(clauses)}}
