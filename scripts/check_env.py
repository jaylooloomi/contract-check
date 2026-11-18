"""Environment check. Usage: python scripts/check_env.py   (exit code 1 if a required item fails)."""
import importlib
import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
fails = 0


def mark(ok, label, detail="", required=True):
    global fails
    sym = "✓" if ok else ("✗" if required else "–")
    if not ok and required:
        fails += 1
    print(f" {sym} {label}" + (f"  ({detail})" if detail else "") + ("" if required else "  [optional]"))


mark(sys.version_info[:2] == (3, 12), "Python 3.12", f"{sys.version.split()[0]} @ {sys.executable}")
for mod in ["fastapi", "uvicorn", "multipart", "pydantic", "fitz", "bs4", "numpy", "paddle",
            "paddleocr", "pytest", "httpx", "playwright"]:
    try:
        m = importlib.import_module(mod)
        mark(True, f"import {mod}", str(getattr(m, "__version__", "")))
    except Exception as e:
        mark(False, f"import {mod}", f"{type(e).__name__}: {e}"[:120])

try:
    n = sqlite3.connect(ROOT / "data" / "app.db").execute("SELECT count(*) FROM articles").fetchone()[0]
    mark(n == 66, "law DB data/app.db", f"{n} articles, expected 66")
except Exception as e:
    mark(False, "law DB data/app.db", str(e))

ocr = Path.home() / ".paddleocr" / "whl"
ok = all((ocr / d).is_dir() for d in ("det", "rec", "cls"))
mark(ok, "PaddleOCR models in ~/.paddleocr/whl",
     "present" if ok else "missing; auto-downloaded (~33 MB) on first OCR run", required=False)

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        exe = p.chromium.executable_path
    mark(os.path.exists(exe), "Playwright chromium",
         exe if os.path.exists(exe) else "run: python -m playwright install chromium")
except Exception as e:
    mark(False, "Playwright chromium", f"{type(e).__name__}: {e}"[:120])

try:
    with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
        names = [m["name"] for m in json.load(r).get("models", [])]
    mark(True, "Ollama reachable", "localhost:11434", required=False)
    mark("qwen3:8b" in names, "Ollama model qwen3:8b",
         "" if "qwen3:8b" in names else "run: ollama pull qwen3:8b", required=False)
except Exception:
    mark(False, "Ollama reachable", "not running; app falls back to rules-only", required=False)

print("\nOK" if fails == 0 else f"\n{fails} required check(s) failed")
sys.exit(1 if fails else 0)
