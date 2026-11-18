"""版本 D（精靈式引導 /v/wizard）的 Playwright E2E。執行：py -3.12 -m pytest tests/e2e -m e2e"""
import csv
import io
import os

import pytest
from playwright.sync_api import expect

from conftest import PDF_TEXT, ROOT

pytestmark = pytest.mark.e2e
URL = "/v/wizard"
SHOTS = os.path.join(ROOT, "docs", "wizard")


def T(name):
    return f"[data-testid='{name}']"


def tid(page, name):
    return page.locator(T(name))


def active_step(page):
    return page.locator(f"{T('wizard-step')}[aria-current='step']")


def test_full_four_step_flow(page):
    os.makedirs(SHOTS, exist_ok=True)
    page.goto(URL)
    page.wait_for_load_state("networkidle")
    expect(active_step(page)).to_have_attribute("data-step", "1")
    expect(tid(page, "disclaimer")).to_be_visible()
    expect(tid(page, "dropzone")).to_be_visible()
    expect(tid(page, "version-switcher")).to_contain_text("D")
    expect(tid(page, "submit-button")).to_be_disabled()
    page.screenshot(path=os.path.join(SHOTS, "step_1.png"))
    tid(page, "upload-input").set_input_files(PDF_TEXT)
    expect(tid(page, "ai-checkbox")).not_to_be_checked()
    # 攔住上傳回應以截到第 ② 步
    held = []
    page.route("**/api/contracts?*", lambda r: held.append(r))
    tid(page, "submit-button").click()
    expect(active_step(page)).to_have_attribute("data-step", "2")
    page.wait_for_timeout(2600)
    page.screenshot(path=os.path.join(SHOTS, "step_2.png"))
    assert held
    held[0].continue_()
    expect(active_step(page)).to_have_attribute("data-step", "3", timeout=60_000)
    expect(tid(page, "queue-position")).to_have_text("1 / 5")
    expect(tid(page, "finding-source")).to_have_text("規則")
    tid(page, "law-toggle").click()
    expect(page.locator("#lawTxt")).to_be_visible()
    page.screenshot(path=os.path.join(SHOTS, "step_3.png"))
    for _ in range(5):
        tid(page, "confirm-button").click()
        page.wait_for_timeout(150)
    expect(active_step(page)).to_have_attribute("data-step", "4")
    expect(tid(page, "all-done")).to_be_visible()
    expect(tid(page, "count-total")).to_have_text("5")
    expect(tid(page, "count-confirmed")).to_have_text("5")
    page.screenshot(path=os.path.join(SHOTS, "step_4.png"))
    page.locator(f"#s4 {T('restart-button')}").click()
    expect(active_step(page)).to_have_attribute("data-step", "1")
    assert page.console_errors == []


def test_keyboard_to_all_done(page, uploaded):
    page.goto(f"{URL}?id={uploaded}")
    expect(active_step(page)).to_have_attribute("data-step", "3")
    first = tid(page, "finding-card").get_attribute("data-finding-id")
    page.keyboard.press("j")
    assert tid(page, "finding-card").get_attribute("data-finding-id") != first
    page.keyboard.press("k")
    expect(tid(page, "finding-card")).to_have_attribute("data-finding-id", first)
    page.keyboard.press("y")
    expect(tid(page, "queue-position")).to_have_text("2 / 5")
    page.keyboard.press("n")
    expect(tid(page, "reject-note")).to_be_focused()
    page.keyboard.type("鍵盤理由")
    page.keyboard.press("Enter")
    expect(tid(page, "queue-position")).to_have_text("3 / 5")
    for pos in ("4 / 5", "5 / 5"):
        page.keyboard.press("y")
        expect(tid(page, "queue-position")).to_have_text(pos)
    page.keyboard.press("y")
    expect(tid(page, "all-done")).to_be_visible()
    expect(tid(page, "count-confirmed")).to_have_text("4")
    expect(tid(page, "count-rejected")).to_have_text("1")
    expect(tid(page, "progress-bar")).to_have_attribute("aria-valuenow", "100")
    assert page.console_errors == []


def test_reject_note_persists_after_reload(page, uploaded):
    page.goto(f"{URL}?id={uploaded}")
    fid = tid(page, "finding-card").get_attribute("data-finding-id")
    expect(tid(page, "reject-note")).to_be_hidden()
    tid(page, "reject-button").click()
    tid(page, "reject-note").fill("已有當事人書面同意")
    tid(page, "reject-submit").click()
    expect(tid(page, "queue-position")).to_have_text("2 / 5")
    page.reload()
    expect(active_step(page)).to_have_attribute("data-step", "3")
    expect(tid(page, "queue-position")).to_have_text("2 / 5")
    assert tid(page, "finding-card").get_attribute("data-finding-id") != fid
    d = page.request.get(f"/api/contracts/{uploaded}").json()
    f = next(x for x in d["findings"] if str(x["id"]) == fid)
    assert f["latest_review"]["decision"] == "reject"
    assert f["latest_review"]["note"] == "已有當事人書面同意"


def test_id_jumps_to_step3_then_step4_when_all_reviewed(page, uploaded):
    page.goto(f"{URL}?id={uploaded}")
    expect(active_step(page)).to_have_attribute("data-step", "3")
    expect(tid(page, "finding-card")).to_have_count(1)
    d = page.request.get(f"/api/contracts/{uploaded}").json()
    for f in d["findings"]:
        page.request.post(f"/api/findings/{f['id']}/review", data={"decision": "confirm"})
    page.reload()
    expect(active_step(page)).to_have_attribute("data-step", "4")
    expect(tid(page, "count-confirmed")).to_have_text("5")


def test_missing_id_error_retry_restart(page):
    page.goto(f"{URL}?id=99999")
    expect(tid(page, "status-message")).to_contain_text("找不到合約", timeout=10_000)
    expect(active_step(page)).to_have_attribute("data-step", "2")
    retry = page.locator(f"#s2 {T('retry-button')}")
    expect(retry).to_be_visible()
    retry.click()
    expect(tid(page, "status-message")).to_contain_text("找不到合約")
    page.locator(f"#s2 {T('restart-button')}").click()
    expect(active_step(page)).to_have_attribute("data-step", "1")
    assert "id=" not in page.url


def test_export_csv(page, uploaded, tmp_path):
    page.goto(f"{URL}?id={uploaded}")
    tid(page, "confirm-button").click()
    expect(tid(page, "queue-position")).to_have_text("2 / 5")
    for _ in range(4):
        page.keyboard.press("y")
        page.wait_for_timeout(200)
    expect(tid(page, "all-done")).to_be_visible()
    with page.expect_download() as dl:
        tid(page, "export-button").click()
    d = dl.value
    assert d.suggested_filename.endswith(".csv") and "01_委外行銷_文字版" in d.suggested_filename
    p = tmp_path / "out.csv"
    d.save_as(p)
    raw = p.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    assert rows[0][0] == "疑慮ID" and len(rows) == 6
    assert sum(r[6] == "確認疑慮" for r in rows[1:]) == 5


def test_mobile_no_horizontal_scroll(browser, server, uploaded):
    ctx = browser.new_context(base_url=server, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    try:
        p = ctx.new_page()
        for url in (URL, f"{URL}?id={uploaded}"):
            p.goto(url)
            p.wait_for_load_state("networkidle")
            sw, cw = p.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            assert sw <= cw, f"{url} 水平捲動：scrollWidth={sw} > clientWidth={cw}"
        p.locator(T("law-toggle")).click()
        sw, cw = p.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        assert sw <= cw
    finally:
        ctx.close()


def test_dark_mode_screenshot(browser, server, uploaded):
    ctx = browser.new_context(base_url=server, viewport={"width": 1280, "height": 800}, color_scheme="dark")
    try:
        p = ctx.new_page()
        errs = []
        p.on("console", lambda m: m.type == "error" and errs.append(m.text))
        p.goto(f"{URL}?id={uploaded}")
        expect(p.locator(T("finding-card"))).to_be_visible()
        bg = p.evaluate("getComputedStyle(document.body).backgroundColor")
        assert bg != "rgb(255, 255, 255)"
        os.makedirs(SHOTS, exist_ok=True)
        p.screenshot(path=os.path.join(SHOTS, "step_3_dark.png"))
        assert errs == []
    finally:
        ctx.close()
