"""錄製操作說明影片：py -3.12 docs/video/record.py
自起隔離伺服器（port 8013、DB 副本），Playwright 錄 1280x720 webm，再用 ffmpeg 轉成 操作說明.mp4。"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PORT = 8013
BASE = f"http://127.0.0.1:{PORT}"
PDF1 = os.path.join(ROOT, "demo", "01_委外行銷_文字版.pdf")
PDF2 = os.path.join(ROOT, "demo", "02_員工資料_掃描版.pdf")

CAP_JS = """(t)=>{let d=document.getElementById('__cap');if(!d){d=document.createElement('div');d.id='__cap';
d.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:99999;background:rgba(15,23,42,.88);color:#fff;'+
'font:600 28px/1.45 "Microsoft JhengHei","微軟正黑體",sans-serif;padding:14px 32px;text-align:center;pointer-events:none';
document.body.appendChild(d)}d.textContent=t}"""
shots = []


def cap(page, text, hold=2.5):
    page.evaluate(CAP_JS, text)
    page.wait_for_timeout(int(hold * 1000))


def shot(page, n, desc):
    path = os.path.join(HERE, f"step_{n:02d}.png")
    page.screenshot(path=path)
    shots.append((n, desc))


def flash(page, selector):
    page.evaluate("""(s)=>{const e=document.querySelector(s);if(!e)return;e.scrollIntoView({block:'center'});
      e.style.outline='4px solid #ef4444';e.style.outlineOffset='3px'}""", selector)


def run(page):
    t_start = time.time()
    # 1 版本 A 首頁
    page.goto(BASE + "/")
    page.wait_for_load_state("networkidle")
    cap(page, "① 版本 A「分割檢視」：右上角顯示法規庫（個資法條數、修正日期、官方來源）", 4)
    flash(page, "#law")
    cap(page, "法條內容全部取自全國法規資料庫原文", 3)
    shot(page, 1, "版本 A 首頁：上傳區、法規庫資訊（個資法條數、修正日期、來源連結）")

    # 2 上傳文字版
    cap(page, "② 選擇 demo/01 委外行銷合約（文字版 PDF），不勾 AI，按「開始檢查」", 3)
    page.set_input_files("[data-testid='upload-input']", PDF1)
    t0 = time.time()
    page.click("[data-testid='submit-button']")
    page.wait_for_selector("[data-testid='status-message']:has-text('完成')", timeout=60000)
    secs = time.time() - t0
    cap(page, f"文字版不需 OCR，約 {secs:.0f} 秒完成：8 段條款，找到 5 項可能疑慮", 4.5)
    shot(page, 2, "上傳文字版合約後：5 項可能疑慮，左為條款（黃底＝有疑慮）、右為疑慮與法條")

    # 3 點條款、確認、駁回
    cap(page, "③ 點左邊黃底條款，右邊只留該條款的疑慮，下方附個資法條文原文", 3)
    page.locator(".clause.flag").first.click()
    page.wait_for_timeout(1200)
    flash(page, "#findings .law")
    cap(page, "法條原文直接放在疑慮旁，不必另外開網頁查", 3.5)
    shot(page, 3, "點條款篩選：右側顯示該條款疑慮與個資法原文")
    page.locator(".clause.flag").first.click()  # 取消篩選
    cap(page, "按「確認疑慮」：這一項要寫進審閱意見", 2.5)
    page.locator("[data-testid='finding-card']").nth(0).locator("[data-testid='confirm-button']").click()
    page.wait_for_timeout(800)
    cap(page, "按「駁回」：判斷沒有問題。每次決定都存檔，「已複核」數字跟著增加", 3.5)
    page.locator("[data-testid='finding-card']").nth(1).locator("[data-testid='reject-button']").click()
    page.wait_for_timeout(1200)
    cid = page.evaluate("data.contract.id")

    # 4 版本 B
    page.goto(f"{BASE}/v/b?id={cid}")
    page.wait_for_selector("[data-testid='finding-card']")
    cap(page, "④ 切到版本 B「審閱工作佇列」：一次一筆，預設只顯示「待複核」", 3.5)
    flash(page, ".sum")
    cap(page, "上方固定顯示：風險數、待複核／已確認／已駁回，以及進度條", 3.5)
    shot(page, 4, "版本 B：摘要列與進度條、一次一筆的待複核卡片")
    cap(page, "鍵盤 J 下一筆、K 上一筆", 2)
    page.keyboard.press("j"); page.wait_for_timeout(900)
    page.keyboard.press("k"); page.wait_for_timeout(900)
    cap(page, "按 Y：確認疑慮，自動跳到下一筆，進度條前進", 2.5)
    page.keyboard.press("y"); page.wait_for_timeout(1200)
    cap(page, "按 N：游標直接進入駁回理由欄，打字後按 Enter 送出", 2.5)
    page.keyboard.press("n"); page.wait_for_timeout(500)
    page.keyboard.type("已另簽當事人書面同意書", delay=120)
    shot(page, 5, "按 N 駁回：填寫駁回理由（會留在稽核紀錄），Enter 送出")
    page.keyboard.press("Enter"); page.wait_for_timeout(1200)
    cap(page, "按「匯出 CSV」：下載審閱結果，Excel 開啟中文不亂碼", 2.5)
    with page.expect_download() as dl:
        page.click("[data-testid='export-button']")
    dl.value.save_as(os.path.join(tempfile.gettempdir(), "cc_demo_export.csv"))
    cap(page, f"已下載：{dl.value.suggested_filename}", 3)

    # 5 版本 C
    page.goto(f"{BASE}/v/c?id={cid}")
    page.wait_for_selector("[data-testid='finding-highlight']")
    cap(page, "⑤ 切到版本 C「全文標註」：像讀紙本合約一樣，有疑慮的條款直接上色", 4)
    page.locator("[data-testid='finding-highlight']").nth(2).click()
    page.wait_for_timeout(1000)
    cap(page, "點標註，右側抽屜打開：疑慮理由、法條原文、確認／駁回按鈕", 4)
    shot(page, 6, "版本 C：點標註開啟抽屜，顯示疑慮理由與法條原文")
    page.click("[data-testid='drawer-close']")
    page.wait_for_timeout(800)

    # 6 掃描版 OCR
    page.goto(f"{BASE}/v/c")
    cap(page, "⑥ 改上傳 demo/02 員工資料合約：這是「掃描版」PDF，沒有文字層", 3.5)
    page.set_input_files("[data-testid='upload-input']", PDF2)
    page.click("[data-testid='submit-button']")
    page.evaluate(CAP_JS, "系統自動改走 OCR 文字辨識，畫面顯示已等待秒數，避免誤以為當機")
    page.wait_for_selector("[data-testid='status-message']:has-text('完成')", timeout=240000)
    page.wait_for_timeout(1500)
    cap(page, "OCR 完成：埋了 3 個問題，系統只找到 2 項", 3.5)
    page.evaluate("""()=>{const p=[...document.querySelectorAll('.cl')].find(e=>e.textContent.includes('第三條'));
      if(p){p.scrollIntoView({block:'center'});p.style.outline='4px dashed #ef4444';p.style.outlineOffset='4px'}}""")
    cap(page, "第三條（資料轉交合作夥伴推銷保險，應對應 §20）沒被標出：OCR 把字讀錯，規則比對不到", 5)
    shot(page, 7, "掃描版 OCR 結果：紅框的第三條因 OCR 錯字漏報 §20，需人工複核")
    cap(page, "所以掃描檔一定要由法務人員對照原始 PDF 複核", 3.5)

    # 7 免責聲明
    page.evaluate("window.scrollTo(0,0)")
    flash(page, "[data-testid='disclaimer']")
    cap(page, "⑦ 系統只列出「可能疑慮」，供法務複核，不構成法律意見或違法判定", 5)
    shot(page, 8, "頁首常駐免責聲明：只提示可能疑慮，不判定違法")
    print(f"script time {time.time() - t_start:.1f}s")


def main():
    tmpd = tempfile.mkdtemp(prefix="cc_video_")
    db = os.path.join(tmpd, "video.db")
    shutil.copy(os.path.join(ROOT, "data", "app.db"), db)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)], cwd=ROOT,
                            env={**os.environ, "CC_DB": db}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(BASE + "/api/law", timeout=2); break
            except Exception:
                time.sleep(0.5)
        vdir = os.path.join(tmpd, "vid")
        with sync_playwright() as p:
            b = p.chromium.launch(slow_mo=400)
            ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=vdir,
                                record_video_size={"width": 1280, "height": 720}, accept_downloads=True)
            page = ctx.new_page()
            run(page)
            webm = page.video.path()
            ctx.close(); b.close()
        out = os.path.join(HERE, "操作說明.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", webm, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "23", "-preset", "medium", "-movflags", "+faststart", out], check=True)
        print("OK", out)
    finally:
        proc.terminate()
        proc.wait(10)


if __name__ == "__main__":
    main()
