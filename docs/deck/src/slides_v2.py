exec(open('build.py', encoding='utf-8').read())  # helpers, chart, prs, N

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

# 0a cover
s = prs.slides.add_slide(L)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = RGBColor(0xfb, 0xfb, 0xfd); bg.line.fill.background()
tb(s, 1.0, 2.9, 11.3, 1.3, '合約外規檢查', 66, True, DK, PP_ALIGN.CENTER)
tb(s, 1.0, 4.3, 11.3, 0.8, '電腦先幫法務找出合約裡可能有問題的地方，最後由人決定', 26, False, GR, PP_ALIGN.CENTER)
tb(s, 1.0, 2.3, 11.3, 0.5, '面試作品｜2 小時 Prototype｜2026-11-18', 18, True, A, PP_ALIGN.CENTER)
notes(s, '（開場前停在這頁。）謝謝給我這兩小時。我會用大約 10 分鐘，說明我做了什麼、怎麼做、做得好不好，中間會實際操作給你看。')

# 0b agenda
s = prs.slides.add_slide(L); head(s, '目錄', '今天要講的 4 件事', '大約 10 分鐘，中間有 3 分鐘實際操作')
agenda = [('1', '做了什麼', '一句話說清楚，先問了哪些問題', '第 1–2 頁'),
          ('2', '怎麼做', '整個流程、法律從哪裡來', '第 3 頁'),
          ('3', '用起來怎樣', '好用的畫面＋現場操作', '第 4 頁'),
          ('4', '做得好不好', '準不準、怎麼檢查 AI、做到哪裡', '第 5–7 頁')]
for i, (n_, t, d, pg) in enumerate(agenda):
    y = 2.0 + i*1.15
    box(s, 0.9, y, 0.85, 0.85, n_, fill=A, line=A, sz=28, color=WH, shape=MSO_SHAPE.OVAL)
    tb(s, 2.0, y+0.02, 5.0, 0.6, t, 28, True, DK)
    tb(s, 6.2, y+0.12, 4.9, 0.6, d, 20, False, GR)
    tb(s, 11.0, y+0.12, 1.9, 0.6, pg, 18, False, A)
tb(s, 0.9, 6.7, 12, 0.5, '備用頁：兩小時的時間線（被問到再看）', 16, False, GR)
notes(s, '今天分 4 段：做了什麼、怎麼做、用起來怎樣、做得好不好。第 3 段我會直接操作給你看。後面還有附表和備用頁，有問題我們再翻。')

# 1 one-liner
s = prs.slides.add_slide(L); head(s, '1 / 7', '我做了什麼', '電腦先找出合約裡「可能有問題」的地方，人來決定')
steps = [('放上合約', '電腦檔或掃描檔都可以'), ('電腦標出問題', '旁邊附上法律原文'), ('人來決定', '是問題／不是問題')]
for i, (a, b_) in enumerate(steps):
    x = 0.9 + i*4.1
    box(s, x, 2.3, 3.3, 1.5, [a, b_], fill=A if i == 2 else RGBColor(0xf5, 0xf5, 0xf7), color=WH if i == 2 else DK, sz=24)
    if i < 2: arrow(s, x+3.3, 3.05, x+4.1, 3.05)
for i, (num, lab_) in enumerate([('66 條', '真的個資法'), ('4 種', '好用的畫面'), ('4 份', '練習用的假合約')]):
    x = 0.9 + i*4.1
    tb(s, x, 4.6, 3.3, 0.9, num, 44, True, A, PP_ALIGN.CENTER)
    tb(s, x, 5.55, 3.3, 0.5, lab_, 20, False, GR, PP_ALIGN.CENTER)
notes(s, N[0])

# 2 clarify
s = prs.slides.add_slide(L); head(s, '2 / 7', '先問清楚，再動手', '動手之前，先問 3 個問題')
items = [('誰要用？', '法務人員', '所以每個問題都附法律原文'), ('合約長什麼樣？', 'PDF，常常是掃描的', '要會看圖認字（OCR）'), ('要比對什麼？', '先做個資法', '只有 66 條，兩小時做得完')]
for i, (q, a, why) in enumerate(items):
    x = 0.7 + i*4.15
    box(s, x+1.3, 2.0, 1.0, 1.0, str(i+1), fill=A, line=A, sz=28, color=WH, shape=MSO_SHAPE.OVAL)
    tb(s, x, 3.15, 3.6, 0.5, q, 18, False, GR, PP_ALIGN.CENTER)
    tb(s, x, 3.6, 3.6, 0.6, a, 26, True, DK, PP_ALIGN.CENTER)
    tb(s, x, 4.3, 3.6, 0.5, why, 18, False, GR, PP_ALIGN.CENTER)
box(s, 0.7, 5.5, 11.9, 0.9, '沒有雲端 AI 鑰匙（API key）→ 改用本機 AI，合約不外傳', fill=RGBColor(0xf5, 0xf5, 0xf7), sz=22)
notes(s, N[1])

# 3 flow + law source (merged)
s = prs.slides.add_slide(L); head(s, '3 / 7', '整個流程怎麼跑', '法律從政府網站抓下來存好，每份合約進來都走同一條路')
s.shapes.add_picture('img/arch.png', Inches(0.5), Inches(1.9), width=Inches(8.4))
tb(s, 9.1, 1.95, 4.0, 2.4, ['法律從哪來', '• 法務部全國法規資料庫', '• 原始網頁也存下來', '• 數了三次都是 66 條'], 18)
tb(s, 9.1, 4.45, 4.0, 2.4, ['不讓 AI 亂講的三道關', '① 只能從找到的法律裡選', '② 檢查號碼是真的（引用驗證）', '③ 最後由人決定'], 18, True, A)
notes(s, N[2] + N[3])

# 5 screens (wizard + A/B/C)
s = prs.slides.add_slide(L); head(s, '4 / 7', '好用的畫面', '一步一步帶著做：放合約 → 等一下 → 一題一題回答')
p_ = s.shapes.add_picture('img/ui_d3.png', Inches(0.6), Inches(1.9), width=Inches(7.6)); p_.line.color.rgb = RGBColor(0xd1, 0xd5, 0xdb)
tb(s, 0.6, 6.7, 7.6, 0.5, '新版：一次只看一題，按「是問題」或「不是」就好', 16, False, GR, PP_ALIGN.CENTER)
rows_ = [('D 一步一步帶著做（精靈）', '新手也會用（主推）', A), ('A 一眼看全部', '短合約', DK), ('B 一題一題快速過（佇列）', '很多合約要看', DK), ('C 像讀紙本一樣', '從頭讀到尾', DK)]
for i, (t, d, c) in enumerate(rows_):
    y = 1.95 + i*1.0
    tb(s, 8.6, y, 4.4, 0.5, t, 22, True, c)
    tb(s, 8.6, y+0.45, 4.4, 0.45, d, 16, False, GR)
box(s, 8.6, 6.0, 4.3, 0.95, ['看過的合約點一下就打開', '不用再等一次'], fill=RGBColor(0xf5, 0xf5, 0xf7), sz=18)
notes(s, N[4])

# 6 verification
s = prs.slides.add_slide(L); head(s, '5 / 7', '準不準？', '練習過的題目全對，換一張新考卷就一題都沒抓到')
s.shapes.add_picture('img/eval.png', Inches(0.4), Inches(1.85), width=Inches(8.9))
tb(s, 9.5, 2.0, 3.6, 5.0, ['• 功能都會動：', '  自動檢查 17 項全過', '  （驗收測試）', '  模擬真人操作 29 次全過', '  （E2E 測試）', '• 但會動 ≠ 找得準', '• 新考卷（盲測）的結果', '  老實寫出來'], 18)
notes(s, N[5])

# 6 how I check AI
s = prs.slides.add_slide(L); head(s, '6 / 7', '我怎麼檢查 AI 做得對不對', 'AI 說「做完了」，我一定自己再看一次')
table(s, 0.6, 1.95, 12.1, [('時間', '發生什麼事', '我怎麼處理'),
      ('19:50', '電腦裡有兩個版本的 Python，會打架', '統一用同一個版本'),
      ('19:56', '看圖認字（OCR）把「洩」認成「浅」', '放寬比對，記下這個缺點'),
      ('20:05', 'AI 助手（子代理）說做完了，其實報告根本不存在', '自己打開檔案檢查，重做一次'),
      ('20:12', '練習過的題目全對', '再出一張新考卷（盲測）→ 0/3，老實寫出來')], [1.3, 5.6, 5.2], 18, 0.68)
tb(s, 0.6, 5.7, 12.1, 0.6, '工具裡的三道關：AI 只能從找到的法律裡選 → 檢查號碼是真的（引用驗證）→ 人決定', 20, True, A)
notes(s, N[7])

# 7 status (merged with 附表)
s = prs.slides.add_slide(L); head(s, '7 / 7', '做到哪裡了', '整條路已經走得通；找得準不準，要用真的合約來證明')
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
s = prs.slides.add_slide(L); head(s, '備用', '兩小時怎麼用', '先想清楚、再分工一起做、最後一定檢查')
tl = [('19:43', '問清楚'), ('19:52', '寫計畫書\n（SDD 規格）'), ('19:54', '分三組\n一起做'), ('20:00', '整條路\n走得通'), ('20:05', '出考卷考自己\n（盲測）'), ('20:16', '畫面、影片、\n簡報')]
line = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.9), Inches(3.6), Inches(12.5), Inches(3.6)); line.line.color.rgb = A; line.line.width = Pt(4)
for i, (t, d) in enumerate(tl):
    x = 0.8 + i*2.05
    box(s, x+0.65, 3.35, 0.5, 0.5, '', fill=WH, line=A, shape=MSO_SHAPE.OVAL)
    tb(s, x, 2.5, 1.8, 0.6, t, 22, True, A, PP_ALIGN.CENTER)
    tb(s, x-0.2, 4.1, 2.2, 1.2, d.split('\n'), 18, False, DK, PP_ALIGN.CENTER)
tb(s, 0.9, 5.8, 12, 0.6, '20:05 發現 AI 助手的報告是假的 → 丟掉重做', 20, True, RGBColor(0xff, 0x3b, 0x30))
notes(s, N[8])

prs.save('合約外規檢查_簡報.pptx'); print('saved v2')
