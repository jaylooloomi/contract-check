"""檢查狀態橫幅（四個版本＋歷史）E2E。AI 失敗用 server_ai_down（CC_AI_PROBE_URL 不可達）。"""
import os

import pytest
from playwright.sync_api import expect

from conftest import PDF_TEXT, ROOT

pytestmark = pytest.mark.e2e
PAGES = {"A": "/?id={}", "B": "/v/b?id={}", "C": "/v/c?id={}", "D": "/v/wizard?id={}"}
SHOTS = os.path.join(ROOT, "docs")


def _upload(request_ctx, base, use_ai):
    with open(PDF_TEXT, "rb") as f:
        r = request_ctx.post(f"{base}/api/contracts?use_ai={use_ai}", multipart={
            "file": {"name": "01_委外行銷_文字版.pdf", "mimeType": "application/pdf", "buffer": f.read()}})
    assert r.ok, r.text()
    return r.json()


@pytest.fixture
def down_page(browser, server_ai_down):
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    p = ctx.new_page()
    p.errors = []
    p.on("pageerror", lambda e: p.errors.append(str(e)))
    yield p, ctx, server_ai_down
    ctx.close()


@pytest.mark.parametrize("ver", list(PAGES))
def test_ai_failed_banner(down_page, ver):
    p, ctx, base = down_page
    d = _upload(ctx.request, base, "true")
    assert d["ai_status"] == "failed" and d["finding_count"] == 5
    p.goto(base + PAGES[ver].format(d["contract_id"]))
    st = p.locator("[data-testid='check-status']:visible").first
    expect(st).to_contain_text("✓ 規則檢查完成")
    expect(st.locator("[data-testid='ai-status']")).to_contain_text("AI 未完成（AI 服務未啟動，僅完成規則檢查）")
    expect(st).to_contain_text("請人工確認")
    expect(st).to_contain_text("法規版本：民國114年11月11日修正｜抓取")
    p.screenshot(path=os.path.join(SHOTS, f"status_ui_{ver}_ai_failed.png"))
    assert not p.errors


@pytest.mark.parametrize("ver", list(PAGES))
def test_rules_only_banner(page, context, server, ver):
    d = _upload(context.request, server, "false")
    page.goto(PAGES[ver].format(d["contract_id"]))
    st = page.locator("[data-testid='check-status']:visible").first
    expect(st.locator("[data-testid='ai-status']")).to_have_text("AI 未啟用（僅規則檢查）")
    if ver == "B":
        expect(page.locator("[data-testid='law-version']")).to_contain_text("法規版本：民國114年11月11日修正")
    page.screenshot(path=os.path.join(SHOTS, f"status_ui_{ver}_rules_only.png"))
    assert not page.console_errors


def test_wizard_history_shows_status(down_page):
    p, ctx, base = down_page
    d = _upload(ctx.request, base, "true")
    p.goto(base + "/v/wizard")
    item = p.locator(f"[data-testid='history-item'][data-contract-id='{d['contract_id']}']")
    expect(item.locator("[data-testid='ai-status']")).to_have_text("⚠ AI 未完成")
    p.goto(base + "/history")
    item = p.locator(f"[data-testid='history-item'][data-contract-id='{d['contract_id']}']")
    expect(item.locator("[data-testid='ai-status']")).to_have_text("⚠ AI 未完成")
    p.screenshot(path=os.path.join(SHOTS, "status_ui_history.png"))
