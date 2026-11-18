"""分段實測（per-stage evaluation）：每個埋設問題逐段記錄
擷取（extraction）→ 檢索（retrieval）→ 規則（rule）→ AI → 最終（final），並記錄乾淨條款的誤報。

用法：
  py -3.12 eval/run_stages.py --set abc --set d --out eval/stages_before.json [--no-ai]
  py -3.12 eval/run_stages.py --key eval/holdout_e/answer_key.json --out eval/stages_e.json
答案卷每個問題可用 expected_article_no（單一條號）或 acceptable_articles（多個可接受條號）。
"""
import argparse, json, os, re, sys, time
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ROOT))
from app.db import connect
from app.extract import extract_text, split_clauses
import app.check as chk


def _norm(no):
    return re.sub(r"[第條\s]", "", str(no))


def _accept(issue):
    if issue.get("acceptable_articles"):
        return {_norm(a) for a in issue["acceptable_articles"]}
    if issue.get("expected_article_no") is not None:
        return {_norm(issue["expected_article_no"])}
    return set()


def _cases_from_key(path):
    """答案卷（answer_key.json 格式）→ cases。PDF 依序找：case['pdf'] / pdfs/<name>_text.pdf / <name>.pdf。"""
    key = json.load(open(path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(path))
    cases = []
    for name, k in key.items():
        if name.startswith("_") or not isinstance(k, dict):
            continue
        clauses = None
        # 有 PDF 就走 PDF（連擷取一起測）；沒有才用答案卷內嵌的條款文字
        cand = [k.get("pdf") and os.path.join(base, k["pdf"]),
                os.path.join(base, "pdfs", f"{name}_text.pdf"),
                os.path.join(base, "pdfs", f"{name}.pdf"),
                os.path.join(base, f"{name}.pdf")]
        pdf = next((p for p in cand if p and os.path.exists(p)), None)
        if pdf:
            src = os.path.relpath(pdf, os.path.dirname(ROOT))
        elif isinstance(k.get("clauses"), list):
            clauses = [{"seq": i, "text": t} for i, t in enumerate(k["clauses"], 1)]
            src = "inline"
        else:
            print(f"[skip] {name}: 找不到 PDF", file=sys.stderr)
            continue
        if k.get("clause_count") is None and isinstance(k.get("clauses"), list):
            k["clause_count"] = len(k["clauses"])
        issues = [{"seq": int(i["clause_seq"]), "accept": sorted(_accept(i)), "issue": i.get("issue", "")}
                  for i in k.get("issues", []) if _accept(i)]
        cases.append({"name": name, "source": src, "clauses": clauses, "pdf": None if clauses else pdf,
                      "clause_count": k.get("clause_count"), "issues": issues,
                      "clean": [int(x) for x in k.get("clean", [])]})
    return cases


def _case_d():
    d = json.load(open(os.path.join(ROOT, "holdout", "holdout_d.json"), encoding="utf-8"))
    issues = [{"seq": int(s), "accept": [_norm(a)], "issue": ""}
              for s, a in d["answer_key"]["issues"].items() if re.fullmatch(r"[\d-]+", str(a))]
    return [{"name": "d_holdout", "source": "inline", "pdf": None,
             "clauses": [{"seq": i, "text": t} for i, t in enumerate(d["clauses"], 1)],
             "clause_count": len(d["clauses"]), "issues": issues,
             "clean": d["answer_key"]["clean"]}]


def _ai_raw(clause, cands):
    """新版有 ai_check_raw（失敗回 None）；舊版只有 ai_check（失敗回 []，無法分辨）。"""
    if hasattr(chk, "ai_check_raw"):
        return chk.ai_check_raw(clause, cands)
    return chk.ai_check(clause, cands)


def run_case(case, conn, use_ai):
    t0 = time.time()
    if case["clauses"] is not None:
        clauses = case["clauses"]
        method = "inline"
    else:
        r = extract_text(case["pdf"])
        clauses, method = split_clauses(r["text"]), r["method"]
    by_seq = {c["seq"]: c for c in clauses}
    per = {}
    ai_errors = 0
    for c in clauses:
        cands = chk.candidates_for(c, conn)
        rules = chk.rule_check(c)
        ai = None
        if use_ai:
            ai = _ai_raw(c, cands)
            if ai is None:
                ai_errors += 1
        merged = list(rules)
        have = {f["article_no"] for f in rules}
        merged += [f for f in (ai or []) if f["article_no"] not in have]
        final = chk.validate_citations(merged, conn)
        per[c["seq"]] = {"cands": [a["article_no"] for a in cands],
                         "rule": [f["article_no"] for f in rules],
                         "ai": None if ai is None else [f["article_no"] for f in ai],
                         "final": [(f["article_no"], f["source"], f["title"]) for f in final]}
    rows = []
    for i in case["issues"]:
        p = per.get(i["seq"])
        acc = set(i["accept"])
        hit = lambda xs: bool(xs) and bool(acc & set(xs))
        rows.append({"seq": i["seq"], "accept": i["accept"], "issue": i["issue"],
                     "extraction_ok": p is not None,
                     "retrieval_hit": bool(p) and hit(p["cands"]),
                     "rule_hit": bool(p) and hit(p["rule"]),
                     "ai_hit": None if not use_ai else (bool(p) and hit(p["ai"] or [])),
                     "final_hit": bool(p) and hit([x[0] for x in p["final"]]),
                     "final_articles": [] if not p else [x[0] for x in p["final"]]})
    fps = []
    for s in case["clean"]:
        for no, src, title in (per.get(s, {}).get("final") or []):
            fps.append({"seq": s, "art": no, "src": src, "title": title})
    # 埋設問題條款上多報的「錯條號」也記下（不計入 FP 主指標）
    extra = []
    for i in case["issues"]:
        for no, src, title in (per.get(i["seq"], {}).get("final") or []):
            if no not in i["accept"]:
                extra.append({"seq": i["seq"], "art": no, "src": src})
    return {"case": case["name"], "source": case["source"], "method": method, "mode": "rule+ai" if use_ai else "rule",
            "clauses_found": len(clauses), "clauses_expected": case["clause_count"],
            "issues": rows, "false_positives": fps, "off_target_on_issue_clauses": extra,
            "ai_errors": ai_errors, "seconds": round(time.time() - t0, 1), "per_clause": per}


def summarize(results):
    s = {}
    for r in results:
        k = f'{r["case"]}|{r["mode"]}'
        n = len(r["issues"])
        s[k] = {m: sum(1 for i in r["issues"] if i[m]) for m in
                ("extraction_ok", "retrieval_hit", "rule_hit", "ai_hit", "final_hit")}
        s[k].update(issues=n, fp=len(r["false_positives"]), ai_errors=r["ai_errors"], seconds=r["seconds"])
    return s


def markdown(results):
    L = ["| 案例 | 模式 | 條 | 預期 | 擷取 | 檢索 | 規則 | AI | 最終 | 最終條號 |", "|---|---|---|---|---|---|---|---|---|---|"]
    yn = lambda v: "-" if v is None else ("✓" if v else "✗")
    for r in results:
        for i in r["issues"]:
            L.append(f'| {r["case"]} | {r["mode"]} | {i["seq"]} | {"/".join(i["accept"])} | {yn(i["extraction_ok"])} | '
                     f'{yn(i["retrieval_hit"])} | {yn(i["rule_hit"])} | {yn(i["ai_hit"])} | {yn(i["final_hit"])} | '
                     f'{",".join(i["final_articles"]) or "—"} |')
    L += ["", "| 案例 | 模式 | 條款數(實際/預期) | 命中 | 誤報(乾淨條款) | AI 失敗次數 | 秒 |", "|---|---|---|---|---|---|---|"]
    for r in results:
        L.append(f'| {r["case"]} | {r["mode"]} | {r["clauses_found"]}/{r["clauses_expected"]} | '
                 f'{sum(i["final_hit"] for i in r["issues"])}/{len(r["issues"])} | '
                 f'{len(r["false_positives"])} {"; ".join(f"{f["seq"]}→{f["art"]}({f["src"]})" for f in r["false_positives"])} | '
                 f'{r["ai_errors"]} | {r["seconds"]} |')
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", choices=["abc", "d"], default=[])
    ap.add_argument("--key", action="append", default=[], help="其他答案卷路徑")
    ap.add_argument("--modes", default="rule,rule+ai")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cases = []
    if "abc" in a.set:
        cases += _cases_from_key(os.path.join(ROOT, "answer_key.json"))
    if "d" in a.set:
        cases += _case_d()
    for k in a.key:
        cases += _cases_from_key(k)
    conn = connect(os.path.join(ROOT, "..", "data", "app.db"))
    results = []
    for case in cases:
        for m in a.modes.split(","):
            r = run_case(case, conn, use_ai=(m == "rule+ai"))
            results.append(r)
            print(r["case"], r["mode"], [(i["seq"], i["final_hit"]) for i in r["issues"]],
                  "fp", len(r["false_positives"]), "aierr", r["ai_errors"], r["seconds"], "s", flush=True)
    out = {"summary": summarize(results), "results": results}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.splitext(a.out)[0] + ".md", "w", encoding="utf-8").write(markdown(results))


if __name__ == "__main__":
    main()
