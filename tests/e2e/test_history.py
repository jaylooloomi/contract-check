"""歷史列表：精靈版第①步的「最近檢查過」與 /history 頁。執行：py -3.12 -m pytest tests/e2e -m e2e"""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def T(n):
    return f"[data-testid='{n}']"


def test_api_list_newest_first(context, uploaded):
    L = context.request.get("/api/contracts?limit=5").json()
    assert L[0]["id"] == uploaded
    assert L[0]["finding_count"] == 5 and L[0]["pending_count"] == 5
    assert {"filename", "uploaded_at", "extract_method", "clause_count"} <= set(L[0])


def test_wizard_history_opens_without_rerun(page, uploaded):
    page.goto("/v/wizard")
    item = page.locator(f"{T('history-item')}[data-contract-id='{uploaded}']")
    expect(item).to_be_visible()
    expect(item).to_contain_text("5 疑慮")
    item.click()
    expect(page.locator(f"{T('wizard-step')}[aria-current='step']")).to_have_attribute("data-step", "3")
    expect(page).to_have_url(f"/v/wizard?id={uploaded}")
    assert not page.console_errors, page.console_errors


def test_history_page_links(page, uploaded):
    page.goto("/history")
    row = page.locator(f"{T('history-item')}[data-contract-id='{uploaded}']")
    expect(row).to_be_visible()
    row.locator("a", has_text="C").click()
    expect(page).to_have_url(f"/v/c?id={uploaded}")
    expect(page.locator(T("finding-highlight")).first).to_be_visible()
    assert not page.console_errors, page.console_errors
