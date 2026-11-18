"""獨立實測：依 answer_key.json（先定答案、後跑程式）計算找到率與誤報。
用法：py -3.12 eval/run_eval.py   → 輸出 eval/results.json
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import connect
from app.extract import extract_text, split_clauses
from app.check import rule_check, ai_check, candidates_for, validate_citations

ROOT = os.path.dirname(os.path.abspath(__file__))
key = json.load(open(os.path.join(ROOT, "answer_key.json"), encoding="utf-8"))
conn = connect(os.path.join(ROOT, "..", "data", "app.db"))
RUNS = [("a_marketing", "text"), ("b_hr", "text"), ("c_cloud", "text"), ("c_cloud", "scan")]
out = []
for name, kind in RUNS:
    k = key[name]
    t0 = time.time()
    r = extract_text(os.path.join(ROOT, "pdfs", f"{name}_{kind}.pdf"))
    clauses = split_clauses(r["text"])
    t_ext = time.time() - t0
    for mode in ("rule", "rule+ai"):
        t1 = time.time()
        fs, dropped = [], 0
        for c in clauses:
            f = rule_check(c)
            if mode == "rule+ai":
                ai = ai_check(c, candidates_for(c, conn))
                have = {x["article_no"] for x in f}
                f += [x for x in ai if x["article_no"] not in have]
            v = validate_citations(f, conn)
            dropped += len(f) - len(v)
            fs += v
        expect = {i["clause_seq"]: i["expected_article_no"] for i in k["issues"]}
        hits = {f["clause_seq"] for f in fs if expect.get(f["clause_seq"]) == f["article_no"]}
        fp = [f for f in fs if expect.get(f["clause_seq"]) != f["article_no"]]
        out.append({"contract": name, "pdf": kind, "mode": mode, "method": r["method"],
                    "clauses": len(clauses), "clauses_expected": k["clause_count"],
                    "hits": sorted(hits), "issues": len(expect),
                    "misses": sorted(set(expect) - hits),
                    "false_positives": [{"seq": f["clause_seq"], "src": f["source"], "art": f["article_no"],
                                         "title": f["title"]} for f in fp],
                    "citations_dropped": dropped,
                    "seconds": round(time.time() - t1 + t_ext, 1)})
        print(json.dumps(out[-1], ensure_ascii=False))
json.dump(out, open(os.path.join(ROOT, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
