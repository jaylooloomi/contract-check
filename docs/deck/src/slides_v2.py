exec(open('build.py', encoding='utf-8').read())  # helpers, chart, prs, N
exec(open('xy.py', encoding='utf-8').read())

def table(s, x, y, w, rows, widths, sz=18, rowh=0.6):
    t = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(rowh*len(rows))).table
    for i, cw in enumerate(widths): t.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        t.rows[r].height = Inches(rowh)
        for c, v in enumerate(row):
            cell = t.cell(r, c); cell.text = v; cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            setfont(cell.text_frame.paragraphs[0].runs[0], sz, r == 0 or c == 0, WH if r == 0 else DK)
            cell.fill.solid(); cell.fill.fore_color.rgb = A if r == 0 else (RGBColor(0xf5, 0xf5, 0xf7) if r % 2 else WH)
    return t

# 0a cover（插圖取自 Codex 版 v3/img/cover.png）
s = prs.slides.add_slide(L)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = WH; bg.line.fill.background()
tb(s, 0.8, 2.3, 6.5, 0.5, '面試作品｜2 小時 Prototype｜2026-11-18', 16, True, A)
tb(s, 0.8, 2.85, 6.5, 1.3, '合約外規檢查', 60, True, DK)
tb(s, 0.8, 4.25, 6.4, 1.2, ['電腦先找出合約裡可能有問題的地方，', '最後由人決定'], 22, False, GR)
s.shapes.add_picture('v3/img/cover.png', Inches(7.3), Inches(0.9), height=Inches(5.7))
notes(s, '')

# 0b agenda
s = prs.slides.add_slide(L); head(s, '目錄', '今天的 9 個段落', '從需求到驗收：我怎麼在兩小時內做出來、怎麼確認它做對了')
ag = [('1', '確認需求', '先問 3 個問題', 'P4'), ('2', '挑技術', 'XY 矩陣：快又合適', 'P5'), ('3', '挑要做什麼', 'XY 矩陣：價值×時間', 'P6'),
      ('4', '系統架構', '整條路怎麼走', 'P7'), ('5', '畫面調整', '為什麼改＋現場操作', 'P8'), ('6', '實作與修正', '準不準？怎麼檢查 AI', 'P9–10'),
      ('7', '如何驗收', '怎麼確認做完了', 'P11'), ('8', '做到哪裡', '完成、未完成、接下來', 'P12'), ('9', '時間線', '兩小時怎麼用', 'P13')]
for i, (n_, t, d, pg) in enumerate(ag):
    col, row = (0, i) if i < 5 else (1, i - 5)
    x, y = 0.7 + col*6.3, 1.95 + row*1.0
    box(s, x, y, 0.7, 0.7, n_, fill=A, sz=22, color=WH, shape=MSO_SHAPE.OVAL)
    for x_, w_, txt, sz_, b_, c_ in [(x+0.9, 1.9, t, 22, True, DK), (x+2.8, 2.6, d, 15, False, GR), (x+5.4, 0.8, pg, 13, False, A)]:
        t_ = tb(s, x_, y, w_, 0.7, txt, sz_, b_, c_)
        tf_ = t_.text_frame; tf_.vertical_anchor = MSO_ANCHOR.MIDDLE; tf_.margin_top = tf_.margin_bottom = 0; tf_.paragraphs[0].space_after = Pt(0)
notes(s, '')

# 1 one-liner
s = prs.slides.add_slide(L); head(s, '開場', '我做了什麼', '電腦先找出合約裡「可能有問題」的地方，人來決定')
steps = [('放上合約', '電腦檔或掃描檔都可以'), ('電腦標出問題', '旁邊附上法律原文'), ('人來決定', '是問題／不是問題')]
for i, (a, b_) in enumerate(steps):
    x = 0.9 + i*4.1
    box(s, x, 2.0, 3.3, 2.1, '', fill=A if i == 2 else RGBColor(0xf5, 0xf5, 0xf7))
    s.shapes.add_picture(f'v3/img/step-{i+1}.png', Inches(x+1.3), Inches(2.15), height=Inches(0.7))
    tb(s, x, 2.95, 3.3, 1.0, [a, b_], 22, True, WH if i == 2 else DK, PP_ALIGN.CENTER)
    if i < 2: arrow(s, x+3.3, 3.05, x+4.1, 3.05)
for i, (num, lab_) in enumerate([('66 條', '真的個資法'), ('4 種', '好用的畫面'), ('4 份', '練習用的假合約')]):
    x = 0.9 + i*4.1
    tb(s, x, 4.6, 3.3, 0.9, num, 44, True, A, PP_ALIGN.CENTER)
    tb(s, x, 5.55, 3.3, 0.5, lab_, 20, False, GR, PP_ALIGN.CENTER)
notes(s, N[0])

# 2 clarify
s = prs.slides.add_slide(L); head(s, '1', '① 確認需求', '動手之前，先問 3 個問題')
items = [('誰要用？', '法務人員', '所以每個問題都附法律原文'), ('合約長什麼樣？', 'PDF，常常是掃描的', '要會看圖認字（OCR）'), ('要比對什麼？', '先做個資法', '只有 66 條，兩小時做得完')]
for i, (q, a, why) in enumerate(items):
    x = 0.7 + i*4.15
    box(s, x+1.3, 2.0, 1.0, 1.0, str(i+1), fill=A, line=A, sz=28, color=WH, shape=MSO_SHAPE.OVAL)
    tb(s, x, 3.15, 3.6, 0.5, q, 18, False, GR, PP_ALIGN.CENTER)
    tb(s, x, 3.6, 3.6, 0.6, a, 26, True, DK, PP_ALIGN.CENTER)
    tb(s, x, 4.3, 3.6, 0.5, why, 18, False, GR, PP_ALIGN.CENTER)
s.shapes.add_picture('v3/img/questions.png', Inches(11.3), Inches(0.35), height=Inches(1.3))
box(s, 0.7, 5.5, 11.9, 0.9, '沒有雲端 AI 鑰匙（API key）→ 改用本機 AI，合約不外傳', fill=RGBColor(0xf5, 0xf5, 0xf7), sz=22)
notes(s, N[1])

# 2 tech stack XY
s = prs.slides.add_slide(L); head(s, '2', '② 挑技術', '選「兩小時做得完」又「適合這題」的右上角')
s.shapes.add_picture('img/xy_tech.png', Inches(0.5), Inches(1.75), width=Inches(8.6))
tb(s, 9.3, 1.9, 3.8, 3.6, ['選了（藍點）', '• 資料庫：SQLite＋全文檢索', '• 後端：FastAPI', '• 看圖認字：PaddleOCR', '• AI：本機 qwen3:8b'], 17)
tb(s, 9.3, 4.4, 3.8, 2.0, ['為什麼', '一個檔案就能跑、已裝好、', '繁體中文認得準、', '沒有 key 也能做、資料不外傳'], 15, False, GR)
tb(s, 0.6, 6.95, 10, 0.35, '※ 點的位置是我的判斷，不是量測數據', 11, False, GR)
notes(s, '')

# 3 dev items XY
s = prs.slides.add_slide(L); head(s, '3', '③ 挑要做什麼', '先做「價值高、花時間少」的；沒做的都是故意的')
s.shapes.add_picture('img/xy_items.png', Inches(0.5), Inches(1.75), width=Inches(8.6))
tb(s, 9.3, 1.9, 3.8, 2.4, ['藍點＝做了', '灰點＝先不做'], 17, True)
tb(s, 9.3, 3.0, 3.8, 3.3, ['原則', '① 考題一定要的先做：', '　真法律、引用驗證、人複核', '② 證明準不準：出考卷考自己', '③ 登入、上網、更多法律：', '　跟「找得準不準」無關，先不做'], 15, False, DK)
tb(s, 0.6, 6.95, 10, 0.35, '※ 點的位置是我的判斷，不是量測數據', 11, False, GR)
notes(s, '')

# 3 flow + law source (merged)
s = prs.slides.add_slide(L); head(s, '4', '④ 系統架構', '法律從政府網站抓下來存好，每份合約進來都走同一條路')
s.shapes.add_picture('img/arch.png', Inches(0.5), Inches(1.9), width=Inches(8.4))
tb(s, 9.1, 1.95, 4.0, 2.4, ['法律從哪來', '• 法務部全國法規資料庫', '• 原始網頁也存下來', '• 數了三次都是 66 條'], 18)
tb(s, 9.1, 4.45, 4.0, 2.4, ['不讓 AI 亂講的三道關', '① 只能從找到的法律裡選', '② 檢查號碼是真的（引用驗證）', '③ 最後由人決定'], 18, True, A)
notes(s, N[2] + N[3])

# 5 screens: before / after
s = prs.slides.add_slide(L); head(s, '5', '⑤ 畫面調整', '從「一次看全部」改成「一步一步帶著做」')
RED = RGBColor(0xff, 0x3b, 0x30); GRN = RGBColor(0x24, 0x8a, 0x3d)
cols5 = [(0.6, '之前：一次看全部（A 版）', GR, 'img/ui_a.png',
          ['✕ 條款和問題全擠在一頁，不知道從哪開始', '✕ 看不出還剩幾題沒看', '✕ 等檢查時畫面沒反應，以為當機', '✕ 看過的合約要重新上傳、再等一次'], RED),
         (6.95, '之後：一步一步帶著做（D 版，精靈）', A, 'img/ui_d3.png',
          ['✓ 一次只看一題，旁邊就是法律原文', '✓ 上方步驟條＋「3 / 5」，知道做到哪', '✓ 大按鈕「是問題／不是」，鍵盤 Y／N 也行', '✓ 看過的合約點一下就打開，不用再等'], GRN)]
for x, ttl, c, img, pts, pc in cols5:
    tb(s, x, 1.75, 5.8, 0.45, ttl, 20, True, c)
    pic = s.shapes.add_picture(img, Inches(x), Inches(2.25), width=Inches(4.3)); pic.line.color.rgb = RGBColor(0xd2, 0xd2, 0xd7)
    t_ = s.shapes.add_textbox(Inches(x), Inches(5.0), Inches(5.8), Inches(1.4)); tf = t_.text_frame; tf.word_wrap = True
    for j, line_ in enumerate(pts):
        p_ = tf.paragraphs[0] if j == 0 else tf.add_paragraph(); p_.space_after = Pt(2)
        r1 = p_.add_run(); r1.text = line_[0] + ' '; setfont(r1, 16, True, pc)
        r2 = p_.add_run(); r2.text = line_[2:]; setfont(r2, 16, False, DK)
arrow(s, 5.2, 3.6, 6.7, 3.6)
box(s, 0.6, 6.45, 12.1, 0.6, '為什麼這樣改：法務一天要看很多份合約 → 一次只做一件事、隨時知道進度、少一次等待，就少一次出錯', fill=RGBColor(0xf5, 0xf5, 0xf7), sz=16, bold=False)
tb(s, 0.6, 7.07, 10.5, 0.3, '另外保留 B 審閱佇列（大量快速過）、C 全文標註（從頭讀）給不同習慣的人；精靈版尚未給真的法務試用', 11, False, GR)
notes(s, '這頁我想講「為什麼改」，不是只秀畫面。左邊是我第一版做的畫面：條款和問題全擠在一起，法務一打開不知道從哪開始，也看不出還剩幾題；檢查要等十幾秒，畫面沒反應會以為當機；看過的合約還得重新上傳。'
         '右邊是改過的精靈版：一次只看一題，法律原文就在旁邊；上面有步驟條和「第幾題／共幾題」；兩顆大按鈕，鍵盤 Y、N 也能按；看過的合約在首頁點一下就打開。'
         '設計原則只有一個：法務一天要看很多份，每少一個要記住的東西、少一次等待，就少一次出錯。要誠實說，這還沒給真的法務試用過，下一步要做易用性測試。'
         '（接著切到瀏覽器現場操作。）')

# 6 verification
s = prs.slides.add_slide(L); head(s, '6', '⑥ 實作與修正：準不準？', '練習過的題目全對，換一張新考卷就一題都沒抓到')
s.shapes.add_picture('img/eval.png', Inches(0.4), Inches(1.85), width=Inches(8.9))
tb(s, 9.5, 2.0, 3.6, 5.0, ['• 功能都會動：', '  自動檢查 17 項全過', '  （驗收測試）', '  模擬真人操作 29 次全過', '  （E2E 測試）', '• 但會動 ≠ 找得準', '• 新考卷（盲測）的結果', '  老實寫出來'], 18)
notes(s, N[5])

# 6 how I check AI
s = prs.slides.add_slide(L); head(s, '6', '⑥ 實作與修正：怎麼檢查 AI', 'AI 說「做完了」，我一定自己再看一次')
table(s, 0.6, 1.95, 12.1, [('時間', '發生什麼事', '我怎麼處理'),
      ('19:50', '電腦裡有兩個版本的 Python，會打架', '統一用同一個版本'),
      ('19:56', '看圖認字（OCR）把「洩」認成「浅」', '放寬比對，記下這個缺點'),
      ('20:05', 'AI 助手（子代理）說做完了，其實報告根本不存在', '自己打開檔案檢查，重做一次'),
      ('20:12', '練習過的題目全對', '再出一張新考卷（盲測）→ 0/3，老實寫出來')], [1.3, 5.6, 5.2], 18, 0.68)
tb(s, 0.6, 5.7, 12.1, 0.6, '工具裡的三道關：AI 只能從找到的法律裡選 → 檢查號碼是真的（引用驗證）→ 人決定', 20, True, A)
notes(s, N[7])

# 7 acceptance
s = prs.slides.add_slide(L); head(s, '7', '⑦ 如何驗收', '先寫好「怎樣算做完」，每一條都對應一個自動檢查')
table(s, 0.6, 1.85, 8.3, [('#', '怎樣算做完（驗收標準）', '結果'),
      ('1', '法律條數對、原文對', '✅ 66 條'), ('2', '電腦檔 PDF 切對條款', '✅ 5/5'), ('3', '掃描檔能看圖認字（OCR）', '✅'),
      ('4', '練習合約埋的問題找得到', '✅ 3/3'), ('5', '法條號碼都是真的（引用驗證）', '✅ 假號碼被擋'),
      ('6', '人的決定存得住', '✅'), ('7', 'AI 壞掉也不會當機', '✅')], [0.5, 5.6, 2.2], 15, 0.55)
box(s, 9.3, 1.85, 3.7, 1.5, ['模擬真人操作（E2E）', '29 次全過'], sz=20)
box(s, 9.3, 3.55, 3.7, 1.5, ['新考卷（盲測）', '0/3 → 準確度不算過關'], fill=RGBColor(0xff, 0xf1, 0xf0), sz=20, color=RGBColor(0xc9, 0x34, 0x00))
tb(s, 9.3, 5.25, 3.7, 1.4, ['功能驗收：過了', '準確度驗收：還沒過', '→ 要用真的合約再驗'], 15, True, DK)
tb(s, 0.6, 6.4, 8.3, 0.5, '做法：先寫規格（SDD）→ 寫成 7 條驗收標準 → 每條一個自動測試 → 全過才算完成', 14, False, GR)
notes(s, '')

# 7 status (merged with 附表)
s = prs.slides.add_slide(L); head(s, '8', '⑧ 做到哪裡', '整條路已經走得通；找得準不準，要用真的合約來證明')
cols_ = [('✓ 做好了', RGBColor(0x24, 0x8a, 0x3d), RGBColor(0xf2, 0xfa, 0xf4), ['存好法律', '　沒法律就沒得比', '看得懂掃描檔（OCR）', '　合約常是掃描的', '人來決定', '　電腦會出錯']),
         ('○ 還沒做', GR, RGBColor(0xf5, 0xf5, 0xf7), ['更多種法律', '　先證明一部可行', '合約上鎖、到期刪除', '　正式版一定要做', '登入、放上網路', '　跟準不準無關']),
         ('? 還不知道', RGBColor(0xc9, 0x34, 0x00), RGBColor(0xff, 0xf7, 0xed), ['真的合約準不準', '　考卷是我自己出的', '法務用起來順不順', '　還沒人試用', '很長的合約多快', '　只試過 1–2 頁'])]
for i, (t, c, bg, its) in enumerate(cols_):
    x = 0.6 + i*4.13
    box(s, x, 1.85, 3.9, 0.65, t, fill=c, sz=22, color=WH)
    box(s, x, 2.6, 3.9, 2.65, '', fill=bg)
    t_ = s.shapes.add_textbox(Inches(x+0.2), Inches(2.6), Inches(3.6), Inches(2.6)); tf = t_.text_frame; tf.word_wrap = True
    for j, line_ in enumerate(its):
        p_ = tf.paragraphs[0] if j == 0 else tf.add_paragraph(); r_ = p_.add_run(); r_.text = line_
        setfont(r_, 18 if j % 2 == 0 else 15, j % 2 == 0, DK if j % 2 == 0 else GR)
tb(s, 0.6, 5.4, 12.2, 0.6, '接下來：① 20 份真的合約（去識別化）請法務給答案　② 換更聰明的 AI 再考一次　③ 用法務的紀錄讓電腦變更準', 16)
box(s, 0.6, 6.15, 12.1, 0.85, '電腦負責提醒，每個提醒都附法律原文，最後由人決定', fill=A, sz=24, color=WH)
notes(s, N[6] + '（被問到細節時：沒做的都是故意先不做，最重要的是合約加密與自動刪除，這是個資法第 27 條的安全維護要求。）')

# Backup B timeline
s = prs.slides.add_slide(L); head(s, '9', '⑨ 時間線：兩小時怎麼用', '先想清楚、再分工一起做、最後一定檢查')
tl = [('19:43', '問清楚'), ('19:52', '寫計畫書\n（SDD 規格）'), ('19:54', '分三組\n一起做'), ('20:00', '整條路\n走得通'), ('20:05', '出考卷考自己\n（盲測）'), ('20:16', '畫面、影片、\n簡報')]
line = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.9), Inches(3.6), Inches(12.5), Inches(3.6)); line.line.color.rgb = A; line.line.width = Pt(4)
for i, (t, d) in enumerate(tl):
    x = 0.8 + i*2.05
    box(s, x+0.65, 3.35, 0.5, 0.5, '', fill=WH, line=A, shape=MSO_SHAPE.OVAL)
    tb(s, x, 2.5, 1.8, 0.6, t, 22, True, A, PP_ALIGN.CENTER)
    tb(s, x-0.2, 4.1, 2.2, 1.2, d.split('\n'), 18, False, DK, PP_ALIGN.CENTER)
tb(s, 0.9, 5.8, 12, 0.6, '20:05 發現 AI 助手的報告是假的 → 丟掉重做', 20, True, RGBColor(0xff, 0x3b, 0x30))
notes(s, N[8])

# 備註欄以 講稿_v2.md 的「## P1」~「## P13」為準（改講稿只改 md）
import re as _re
_md = open('講稿_v2.md', encoding='utf-8').read()
_secs = {int(m.group(1)): m.group(2) for m in _re.finditer(r'^## P(\d+)[^\n]*\n(.*?)(?=^## |\Z)', _md, _re.S | _re.M)}
for _i, _sl in enumerate(prs.slides, 1):
    if _i in _secs:
        _t = '\n'.join(l.strip() for l in _secs[_i].strip().splitlines() if l.strip() and not l.startswith('---'))
        _sl.notes_slide.notes_text_frame.text = _t
print('notes from md:', sorted(_secs))

prs.save('合約外規檢查_簡報_v4.pptx'); print('saved v2')
