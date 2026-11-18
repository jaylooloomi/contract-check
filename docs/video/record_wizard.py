"""錄製精靈版（/v/wizard）操作說明影片：py -3.12 docs/video/record_wizard.py
自起隔離伺服器（port 8014、data/app.db 的副本），Playwright 錄 1280x720，再用 ffmpeg 轉成 精靈版操作說明.mp4。
不碰 port 8000 與 data/app.db。"""
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
PORT = 8014
BASE = f"http://127.0.0.1:{PORT}"
PDF1 = os.path.join(ROOT, "demo", "01_委外行銷_文字版.pdf")

# 字幕列在底部；同時給 body 加 padding-bottom，避免字幕蓋住主要按鈕
CAP_JS = """(t)=>{let d=document.getElementById('__cap');if(!d){d=document.createElement('div');d.id='__cap';
d.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:99999;background:rgba(15,23,42,.88);color:#fff;'+
'font:600 26px/1.4 "Microsoft JhengHei","微軟正黑體",sans-serif;padding:12px 32px;text-align:center;pointer-events:none';
document.body.appendChild(d);document.body.style.paddingBottom='120px'}d.textContent=t}"""
shots = []


def T(n):
    return f"[data-testid='{n}']"


def cap(page, text, hold=2.5):
    page.evaluate(CAP_JS, text)
    page.wait_for_timeout(int(hold * 1000))


def center(page, sel):
    page.evaluate("(s)=>{const e=document.querySelector(s);if(e)e.scrollIntoView({block:'center'})}", sel)


def shot(page, n, desc):
    page.screenshot(path=os.path.join(HERE, f"wizard_step_{n:02d}.png"))
    shots.append((n, desc))


def step_is(page, n, timeout=60000):
    page.wait_for_selector(f"{T('wizard-step')}[aria-current='step'][data-step='{n}']", timeout=timeout)


def run(page):
    t_start = time.time()
    # 1 首頁
    page.goto(BASE + "/v/wizard")
    page.wait_for_load_state("networkidle")
    cap(page, "① 打開精靈版：上方四個步驟，照順序走就好", 3.5)
    center(page, T("history-list"))
    cap(page, "下方「最近檢查過」：以前檢查過的合約，點了直接看結果", 3.5)
    page.evaluate("window.scrollTo(0,0)")
    shot(page, 1, "精靈版首頁：上方四個步驟，下方「最近檢查過」")

    # 2 選檔、檢查
    cap(page, "② 把合約 PDF 拖進來，或點一下選檔（這裡用 demo/01 委外行銷合約）", 3)
    page.set_input_files(T("upload-input"), PDF1)
    center(page, T("submit-button"))
    cap(page, "選好檔案後按「檢查」", 2)
    shot(page, 2, "選好 PDF 後按「▶ 檢查」")
    held = []
    # 文字版太快，先攔住上傳回應幾秒，讓畫面看得到第②步
    page.route("**/api/contracts?*", lambda r: held.append(r))
    page.click(T("submit-button"))
    step_is(page, 2)
    page.evaluate(CAP_JS, "③ 第②步：顯示已等待幾秒，和三個階段（讀取→切條款→比對法條）")
    page.wait_for_timeout(4500)
    shot(page, 3, "第②步檢查中：等待秒數與三個階段")
    for r in held:
        r.continue_()
    page.unroute("**/api/contracts?*")
    step_is(page, 3)

    # 4 第③步
    page.wait_for_timeout(800)
    cap(page, "④ 第③步複核：一次只看一題，右上角是進度（1 / 5）", 3.5)
    page.click(T("law-toggle"))
    page.wait_for_timeout(600)
    cap(page, "點「個資法 第○條」展開法律原文，不用另外查", 3.5)
    shot(page, 4, "第③步：一次一題，展開個資法原文")
    center(page, T("confirm-button"))
    cap(page, "這題確實有問題 → 按「✓ 是疑慮」", 2.5)
    page.click(T("confirm-button"))
    page.wait_for_timeout(1200)

    # 5 N + 理由
    cap(page, "⑤ 這題沒問題：按鍵盤 N（不是），游標會跳到理由欄", 3)
    page.keyboard.press("n")
    page.wait_for_timeout(500)
    center(page, T("reject-note"))
    page.keyboard.type("已取得當事人書面同意", delay=130)
    page.wait_for_timeout(500)
    cap(page, "打好理由按 Enter 送出（理由會留下紀錄）", 2.5)
    shot(page, 5, "按 N 填理由「已取得當事人書面同意」，Enter 送出")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)

    # 6 Y/N 完成
    cap(page, "⑥ 剩下的用鍵盤：Y＝是疑慮、N＝不是，進度一路往前", 3)
    for _ in range(3):
        page.keyboard.press("y")
        page.wait_for_timeout(1300)
    step_is(page, 4)

    # 7 第④步
    page.wait_for_timeout(800)
    cap(page, "⑦ 第④步完成：統計是疑慮／不是／待複核各幾項", 3.5)
    center(page, T("export-button"))
    cap(page, "按「下載報告」存成 CSV，Excel 直接開", 2.5)
    with page.expect_download() as dl:
        page.click(T("export-button"))
    dl.value.save_as(os.path.join(tempfile.gettempdir(), "cc_wizard_export.csv"))
    cap(page, f"已下載：{dl.value.suggested_filename}", 3)
    shot(page, 6, "第④步：統計結果與「下載報告」（CSV）")

    # 8 再檢查一份 → 最近檢查過
    cap(page, "⑧ 按「再檢查一份」回到首頁", 2.5)
    page.click(f"#s4 {T('restart-button')}")
    step_is(page, 1)
    page.wait_for_timeout(800)
    center(page, T("history-list"))
    page.evaluate("""()=>{const e=document.querySelector("[data-testid='history-item']");
      if(e){e.style.outline='4px solid #ef4444';e.style.outlineOffset='2px'}}""")
    cap(page, "剛才那份已出現在「最近檢查過」最上面", 3)
    shot(page, 7, "回到首頁：剛檢查的合約在「最近檢查過」第一筆")
    page.locator(T("history-item")).first.click()
    step_is(page, 4, 15000)
    page.wait_for_timeout(600)
    cap(page, "點它直接看結果，不用重新跑一次檢查", 3.5)

    # 9 歷史頁
    page.goto(BASE + "/history")
    page.wait_for_load_state("networkidle")
    cap(page, "⑨ 「全部 →」是歷史頁：所有檢查過的合約、疑慮與待複核數量", 4)
    shot(page, 8, "歷史頁：所有檢查過的合約一覽")

    # 10 結尾
    page.goto(BASE + "/v/wizard")
    page.wait_for_load_state("networkidle")
    cap(page, "電腦負責提醒，最後由人決定", 4)
    print(f"script time {time.time() - t_start:.1f}s")


def main():
    tmpd = tempfile.mkdtemp(prefix="cc_wizvid_")
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
            b = p.chromium.launch(slow_mo=300)
            ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=vdir,
                                record_video_size={"width": 1280, "height": 720}, accept_downloads=True)
            page = ctx.new_page()
            run(page)
            webm = page.video.path()
            ctx.close(); b.close()
        out = os.path.join(HERE, "精靈版操作說明.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", webm, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "23", "-preset", "medium", "-movflags", "+faststart", out], check=True)
        with open(os.path.join(HERE, "精靈版操作步驟.md"), "w", encoding="utf-8") as f:
            f.write("# 精靈版（/v/wizard）操作步驟\n\n影片：[精靈版操作說明.mp4](精靈版操作說明.mp4)\n\n")
            for n, desc in shots:
                f.write(f"## {n}. {desc}\n\n![步驟 {n}](wizard_step_{n:02d}.png)\n\n")
            f.write("> 電腦負責提醒，最後由人決定。\n")
        print("OK", out)
    finally:
        proc.terminate()
        proc.wait(10)


if __name__ == "__main__":
    main()
