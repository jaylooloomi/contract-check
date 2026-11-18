"""E2E fixtures：自起隔離伺服器（port 8013，DB 副本），不碰 port 8000 與 data/app.db。"""
import os
import shutil
import subprocess
import sys
import time
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = int(os.environ.get("CC_E2E_PORT", "8013"))
BASE = f"http://127.0.0.1:{PORT}"
DEMO = os.path.join(ROOT, "demo")
PDF_TEXT = os.path.join(DEMO, "01_委外行銷_文字版.pdf")
PDF_SCAN = os.path.join(DEMO, "02_員工資料_掃描版.pdf")
VERSIONS = {"A": "/", "B": "/v/b", "C": "/v/c"}


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: 瀏覽器端對端測試（Playwright，自起 port 8013 伺服器）")
    config.addinivalue_line("markers", "slow: OCR 等較慢的測試")


def _wait(url, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"server not ready: {url}")


def _serve(tmp_path_factory, port, extra_env=None):
    src = os.path.join(ROOT, "data", "app.db")
    db = tmp_path_factory.mktemp("e2e_db") / "e2e.db"
    shutil.copy(src, db)
    env = {**os.environ, "CC_DB": str(db), "PYTHONIOENCODING": "utf-8", **(extra_env or {})}
    log = open(tmp_path_factory.mktemp("e2e_log") / "server.log", "wb")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    try:
        _wait(base + "/api/law")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    yield from _serve(tmp_path_factory, PORT)


@pytest.fixture(scope="session")
def server_ai_down(tmp_path_factory):
    """第二台隔離伺服器：AI 探測網址指向不可達位址，模擬「Ollama 沒開」。"""
    port = int(os.environ.get("CC_E2E_PORT_AI_DOWN", PORT + 1))
    yield from _serve(tmp_path_factory, port, {"CC_AI_PROBE_URL": "http://127.0.0.1:9/api/tags"})


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def context(browser, server):
    ctx = browser.new_context(base_url=server, viewport={"width": 1280, "height": 800}, accept_downloads=True)
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    p = context.new_page()
    p.console_errors = []
    p.on("console", lambda m: m.type == "error" and p.console_errors.append(m.text))
    p.on("pageerror", lambda e: p.console_errors.append(f"pageerror: {e}"))
    yield p


@pytest.fixture
def uploaded(context):
    """以 API 上傳 demo/01（不經 UI），回傳 contract_id；每個測試一份新合約，互不干擾。"""
    with open(PDF_TEXT, "rb") as f:
        r = context.request.post("/api/contracts?use_ai=false", multipart={
            "file": {"name": "01_委外行銷_文字版.pdf", "mimeType": "application/pdf", "buffer": f.read()}})
    assert r.ok, r.text()
    d = r.json()
    assert d["finding_count"] == 5
    return d["contract_id"]
