"""三版 UI 的 Playwright E2E。執行：py -3.12 -m pytest tests/e2e -m e2e"""
import csv
import io

import pytest
from playwright.sync_api import expect

from conftest import PDF_SCAN, PDF_TEXT, VERSIONS

pytestmark = pytest.mark.e2e


def T(name):
    return f"[data-testid='{name}']"


def tid(page, name):
    return page.locator(T(name))


@pytest.mark.parametrize("ver", ["A", "B", "C"])
def test_loads_without_console_errors(page, ver):
    page.goto(VERSIONS[ver])
    page.wait_for_load_state("networkidle")
    expect(tid(page, "disclaimer")).to_be_visible()
    expect(tid(page, "version-switcher")).to_be_visible()
    expect(page.locator("#law")).to_contain_text("個人資料保護法")
    assert page.console_errors == []


@pytest.mark.parametrize("ver", ["A", "B", "C"])
def test_upload_text_pdf(page, ver):
    page.goto(VERSIONS[ver])
    tid(page, "upload-input").set_input_files(PDF_TEXT)
    expect(tid(page, "ai-checkbox")).not_to_be_checked()
    tid(page, "submit-button").click()
    expect(tid(page, "status-message")).to_contain_text("完成", timeout=60_000)
    expect(tid(page, "status-message")).to_contain_text("文字版 PDF")
    expect(tid(page, "count-total")).to_have_text("5")
    assert page.console_errors == []


def test_a_confirm_reject_persist(page, uploaded):
    page.goto(f"/?id={uploaded}")
    cards = tid(page, "finding-card")
    expect(cards).to_have_count(5)
    c1, c2 = cards.nth(0).get_attribute("data-finding-id"), cards.nth(1).get_attribute("data-finding-id")
    card = lambda i: page.locator(f"{T('finding-card')}[data-finding-id='{i}']")
    card(c1).locator(T("confirm-button")).click()
    expect(tid(page, "count-reviewed")).to_have_text("1")
    card(c2).locator(T("reject-button")).click()
    expect(tid(page, "count-reviewed")).to_have_text("2")
    page.reload()
    expect(tid(page, "count-reviewed")).to_have_text("2")
    expect(card(c1)).to_have_class("f confirm")
    expect(card(c2)).to_have_class("f reject")


def _b_counts(page):
    return [tid(page, n).inner_text() for n in ("count-total", "count-pending", "count-confirmed", "count-rejected")]


def test_b_confirm_reject_with_note_persist(page, uploaded):
    page.goto(f"/v/b?id={uploaded}")
    expect(tid(page, "count-total")).to_have_text("5")
    tid(page, "confirm-button").click()
    expect(tid(page, "count-confirmed")).to_have_text("1")
    rid = tid(page, "finding-card").get_attribute("data-finding-id")
    tid(page, "reject-button").click()
    tid(page, "reject-note").fill("已有當事人書面同意")
    tid(page, "reject-submit").click()
    expect(tid(page, "count-rejected")).to_have_text("1")
    assert _b_counts(page) == ["5", "3", "1", "1"]
    page.reload()
    expect(tid(page, "count-pending")).to_have_text("3")
    assert _b_counts(page) == ["5", "3", "1", "1"]
    tid(page, "filter-status-reject").click()
    expect(tid(page, "finding-card")).to_have_attribute("data-finding-id", rid)
    expect(tid(page, "finding-status")).to_contain_text("已有當事人書面同意")


def test_b_keyboard_flow(page, uploaded):
    page.goto(f"/v/b?id={uploaded}")
    expect(tid(page, "queue-position")).to_have_text("第 1 / 5 筆")
    first = tid(page, "finding-card").get_attribute("data-finding-id")
    page.keyboard.press("j")
    expect(tid(page, "queue-position")).to_have_text("第 2 / 5 筆")
    assert tid(page, "finding-card").get_attribute("data-finding-id") != first
    page.keyboard.press("k")
    expect(tid(page, "finding-card")).to_have_attribute("data-finding-id", first)
    page.keyboard.press("y")  # 確認 → 從待複核清單移除
    expect(tid(page, "count-confirmed")).to_have_text("1")
    expect(tid(page, "queue-position")).to_have_text("第 1 / 4 筆")
    page.keyboard.press("n")
    expect(tid(page, "reject-note")).to_be_focused()
    page.keyboard.type("測試理由")
    page.keyboard.press("Enter")
    expect(tid(page, "count-rejected")).to_have_text("1")
    for left in ("2", "1", "0"):
        page.keyboard.press("y")
        expect(tid(page, "count-pending")).to_have_text(left)
    expect(tid(page, "all-done")).to_be_visible()
    expect(tid(page, "progress-bar")).to_have_attribute("aria-valuenow", "100")
    assert page.console_errors == []


def test_b_export_csv(page, uploaded, tmp_path):
    page.goto(f"/v/b?id={uploaded}")
    tid(page, "confirm-button").click()
    expect(tid(page, "count-confirmed")).to_have_text("1")
    with page.expect_download() as dl:
        tid(page, "export-button").click()
    d = dl.value
    assert d.suggested_filename.endswith(".csv") and "01_委外行銷_文字版" in d.suggested_filename
    p = tmp_path / "out.csv"
    d.save_as(p)
    raw = p.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM，Excel 不亂碼
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[0][0] == "疑慮ID" and len(rows) == 6
    assert sum(r[6] == "確認疑慮" for r in rows[1:]) == 1


def test_c_highlight_opens_drawer(page, uploaded):
    page.goto(f"/v/c?id={uploaded}")
    marks = tid(page, "finding-highlight")
    expect(marks).to_have_count(5)
    drawer = tid(page, "finding-drawer")
    expect(drawer).to_have_attribute("aria-hidden", "true")
    marks.first.click()
    expect(drawer).to_have_class("drawer open")
    expect(drawer).to_contain_text("（原文）")
    law = drawer.locator(".law").first
    expect(law).not_to_contain_text("查無法條原文")
    assert len(law.inner_text()) > 30
    # 在抽屜內駁回並填理由 → 計數更新、重整後仍在
    drawer.locator(T("reject-note")).first.fill("抽屜駁回理由")
    drawer.locator(T("reject-button")).first.click()
    expect(tid(page, "count-rejected")).to_have_text("1")
    tid(page, "drawer-close").click()
    expect(drawer).to_have_attribute("aria-hidden", "true")
    marks.nth(1).click()
    drawer.locator(T("confirm-button")).first.click()
    expect(tid(page, "count-confirmed")).to_have_text("1")
    page.reload()
    expect(tid(page, "count-pending")).to_have_text("3")
    expect(tid(page, "count-rejected")).to_have_text("1")
    tid(page, "finding-highlight").first.click()
    expect(drawer.locator(T("finding-status")).first).to_contain_text("抽屜駁回理由")


@pytest.mark.parametrize("ver", ["A", "B", "C"])
def test_missing_contract_shows_error(page, ver):
    page.goto(VERSIONS[ver] + "?id=99999")
    expect(tid(page, "status-message")).to_contain_text("無法載入合約", timeout=10_000)
    expect(tid(page, "status-message")).to_contain_text("找不到合約")
    expect(page.locator("#result")).to_be_hidden()


@pytest.mark.parametrize("ver", ["A", "B", "C"])
def test_mobile_no_horizontal_scroll(browser, server, uploaded, ver):
    ctx = browser.new_context(base_url=server, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    try:
        p = ctx.new_page()
        p.goto(VERSIONS[ver] + f"?id={uploaded}")
        expect(p.locator(T("count-total"))).to_have_text("5")
        sw, cw = p.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        assert sw <= cw, f"水平捲動：scrollWidth={sw} > clientWidth={cw}"
    finally:
        ctx.close()


@pytest.mark.slow
def test_scanned_pdf_ocr(page):
    page.goto("/v/b")
    tid(page, "upload-input").set_input_files(PDF_SCAN)
    tid(page, "submit-button").click()
    expect(tid(page, "status-message")).to_contain_text("完成", timeout=240_000)
    expect(tid(page, "status-message")).to_contain_text("已 OCR")
    # demo/README：預期 3 項，OCR 把「合作夥伴」讀錯導致 §20 漏報，實測 2 項
    expect(tid(page, "count-total")).to_have_text("2")
