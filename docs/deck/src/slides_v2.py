exec(open('build.py', encoding='utf-8').read())  # helpers, chart, prs, N

def table(s, x, y, w, rows, widths, sz=18, rowh=0.6):
    t = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(rowh*len(rows))).table
    for i, cw in enumerate(widths): t.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        t.rows[r].height = Inches(rowh)
        for c, v in enumerate(row):
            cell = t.cell(r, c); cell.text = v; cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            setfont(cell.text_frame.paragraphs[0].runs[0], sz, r == 0 or c == 0, WH if r == 0 else DK)
            cell.fill.solid(); cell.fill.fore_color.rgb = A if r == 0 else (RGBColor(0xf1, 0xf5, 0xf9) if r % 2 else WH)
    return t

# 0a cover
s = prs.slides.add_slide(L)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = A; bg.line.fill.background()
tb(s, 1.0, 2.2, 11.3, 1.2, '合約外規檢查', 60, True, WH)
tb(s, 1.0, 3.5, 11.3, 0.8, '電腦先幫法務找出合約裡可能有問題的地方，最後由人決定', 26, False, WH)
tb(s, 1.0, 5.6, 11.3, 0.5, '面試作品｜2 小時 Prototype｜2026-11-18', 18, False, RGBColor(0xdb, 0xea, 0xfe))
notes(s, '（開場前停在這頁。）謝謝給我這兩小時。我會用大約 10 分鐘，說明我做了什麼、怎麼做、做得好不好，中間會實際操作給你看。')

# 0b agenda
s = prs.slides.add_slide(L); head(s, '目錄', '今天要講的 4 件事', '大約 10 分鐘，中間有 3 分鐘實際操作')
agenda = [('1', '做了什麼', '一句話說清楚，先問了哪些問題', '第 1–2 頁'),
          ('2', '怎麼做', '整個流程、法律從哪裡來', '第 3–4 頁'),
          ('3', '用起來怎樣', '好用的畫面＋現場操作', '第 5 頁'),
          ('4', '做得好不好', '準不準、做到哪裡、接下來', '第 6–7 頁')]
for i, (n_, t, d, pg) in enumerate(agenda):
    y = 2.0 + i*1.15
    box(s, 0.9, y, 0.85, 0.85, n_, fill=A, line=A, sz=28, color=WH, shape=MSO_SHAPE.OVAL)
    tb(s, 2.0, y+0.02, 5.0, 0.6, t, 28, True, DK)
    tb(s, 6.2, y+0.12, 4.9, 0.6, d, 20, False, GR)
    tb(s, 11.0, y+0.12, 1.9, 0.6, pg, 18, False, A)
tb(s, 0.9, 6.7, 12, 0.5, '附表與備用頁：完成度清單、怎麼檢查 AI、時間線、練習合約（被問到再看）', 16, False, GR)
notes(s, '今天分 4 段：做了什麼、怎麼做、用起來怎樣、做得好不好。第 3 段我會直接操作給你看。後面還有附表和備用頁，有問題我們再翻。')

# 1 one-liner
s = prs.slides.add_slide(L); head(s, '1 / 7', '我做了什麼', '電腦幫法務先找出合約裡「可能有問題」的地方，最後由人決定')
steps = [('放上合約', '電腦檔或掃描檔都可以'), ('電腦標出問題', '旁邊附上法律原文'), ('人來決定', '是問題／不是問題')]
for i, (a, b_) in enumerate(steps):
    x = 0.9 + i*4.1
    box(s, x, 2.3, 3.3, 1.5, [a, b_], fill=A if i == 2 else RGBColor(0xdb, 0xea, 0xfe), color=WH if i == 2 else DK, sz=24)
    if i < 2: arrow(s, x+3.3, 3.05, x+4.1, 3.05)
for i, (num, lab_) in enumerate([('66 條', '真的個資法'), ('4 種', '好用的畫面'), ('4 份', '練習用的假合約')]):
    x = 0.9 + i*4.1
    tb(s, x, 4.6, 3.3, 0.9, num, 44, True, A, PP_ALIGN.CENTER)
    tb(s, x, 5.55, 3.3, 0.5, lab_, 20, False, GR, PP_ALIGN.CENTER)
notes(s, N[0])

# 2 clarify
s = prs.slides.add_slide(L); head(s, '2 / 7', '先問清楚，再動手', '動手之前，先問 3 個問題')
items = [('誰要用？', '法務人員', '所以每個問題都附法律原文'), ('合約長什麼樣？', 'PDF，常常是掃描的', '所以電腦要會看圖認字'), ('要比對什麼？', '先做個資法', '只有 66 條，兩小時做得完')]
for i, (q, a, why) in enumerate(items):
    x = 0.7 + i*4.15
    box(s, x+1.3, 2.0, 1.0, 1.0, str(i+1), fill=A, line=A, sz=28, color=WH, shape=MSO_SHAPE.OVAL)
    tb(s, x, 3.15, 3.6, 0.5, q, 18, False, GR, PP_ALIGN.CENTER)
    tb(s, x, 3.6, 3.6, 0.6, a, 26, True, DK, PP_ALIGN.CENTER)
    tb(s, x, 4.3, 3.6, 0.5, why, 18, False, GR, PP_ALIGN.CENTER)
box(s, 0.7, 5.5, 11.9, 0.9, '沒有雲端 AI 的鑰匙 → 改用自己電腦上的 AI，合約也不會被傳出去', fill=RGBColor(0xef, 0xf6, 0xff), sz=22)
notes(s, N[1])

# 3 architecture
s = prs.slides.add_slide(L); head(s, '3 / 7', '整個流程怎麼跑', '先讓整條路走得通：只做一部法律，但每一步都做到')
s.shapes.add_picture('img/arch.png', Inches(0.5), Inches(1.9), width=Inches(8.4))
table(s, 9.1, 1.9, 3.95, [('先做', '之後再做'), ('一部法律', '很多部法律'), ('自己電腦的 AI', '雲端 AI'), ('用關鍵字找', '用意思找'), ('人來決定', '登入帳號')], [2.15, 1.8], 18, 0.62)
tb(s, 9.1, 5.3, 3.95, 1.6, ['不讓 AI 亂講的三道關：', '只能從找到的法律裡選', '→ 檢查號碼是真的 → 人決定'], 18, True, A)
notes(s, N[2])

# 4 law source + tables
s = prs.slides.add_slide(L); head(s, '4 / 7', '法律從哪裡來', '法律是從政府網站抓下來的，不是 AI 背出來的')
tb(s, 0.6, 1.95, 5.6, 3.5, ['• 來源：法務部的法律網站', '• 原始網頁也存下來，查得到', '• 數了三次都是 66 條', '• 人工對了 3 條原文'], 22)
x0 = 6.9
box(s, x0, 2.0, 2.6, 0.85, ['法律', '例：個資法'], sz=18); box(s, x0+3.2, 2.0, 2.6, 0.85, ['每一條', '第幾條＋內容'], sz=18)
arrow(s, x0+2.6, 2.42, x0+3.2, 2.42)
ys = [3.35, 4.35, 5.35]
for (en, zh), y in zip([('合約', '放上來的檔案'), ('條款', '合約的第幾條'), ('可能的問題', '電腦標出來的')], ys):
    box(s, x0, y, 2.6, 0.75, [en, zh], sz=18)
for y in ys[:-1]: arrow(s, x0+1.3, y+0.75, x0+1.3, y+1.0)
box(s, x0+3.2, 5.35, 2.6, 0.75, ['人的決定', '只會加，不會改'], fill=RGBColor(0xfe, 0xf3, 0xc7), line=RGBColor(0xd9, 0x77, 0x06), sz=18)
arrow(s, x0+2.6, 5.72, x0+3.2, 5.72); arrow(s, x0+4.5, 2.85, x0+2.65, 5.4)
tb(s, x0, 6.3, 6, 0.5, '每次「是／不是」都留下紀錄，以後查得到', 16, False, GR)
notes(s, N[3])

# 5 screens (wizard + A/B/C)
s = prs.slides.add_slide(L); head(s, '5 / 7', '好用的畫面', '一步一步帶著做：放合約 → 等一下 → 一題一題回答')
p_ = s.shapes.add_picture('img/ui_d3.png', Inches(0.6), Inches(1.9), width=Inches(7.6)); p_.line.color.rgb = RGBColor(0xd1, 0xd5, 0xdb)
tb(s, 0.6, 6.7, 7.6, 0.5, '新版：一次只看一題，按「是問題」或「不是」就好', 16, False, GR, PP_ALIGN.CENTER)
rows_ = [('D 一步一步帶著做', '新手也會用（主推）', A), ('A 一眼看全部', '短合約', DK), ('B 一題一題快速過', '很多合約要看', DK), ('C 像讀紙本一樣', '從頭讀到尾', DK)]
for i, (t, d, c) in enumerate(rows_):
    y = 1.95 + i*1.0
    tb(s, 8.6, y, 4.4, 0.5, t, 22, True, c)
    tb(s, 8.6, y+0.45, 4.4, 0.45, d, 16, False, GR)
box(s, 8.6, 6.0, 4.3, 0.95, ['看過的合約點一下就打開', '不用再等一次'], fill=RGBColor(0xef, 0xf6, 0xff), sz=18)
notes(s, N[4])

# 6 verification
s = prs.slides.add_slide(L); head(s, '6 / 7', '準不準？', '練習過的題目全對，換一張新考卷就一題都沒抓到')
s.shapes.add_picture('img/eval.png', Inches(0.4), Inches(1.85), width=Inches(8.9))
tb(s, 9.5, 2.0, 3.6, 5.0, ['• 功能都會動：', '  自動檢查 17 項全過', '  模擬真人操作 29 次全過', '• 但會動 ≠ 找得準', '• 新考卷的結果，', '  老實寫出來'], 18)
notes(s, N[5])

# 7 status
s = prs.slides.add_slide(L); head(s, '7 / 7', '做到哪裡了', '整條路已經走得通；找得準不準，要用真的合約來證明')
cols_ = [('✓ 做好了', RGBColor(0x16, 0xa3, 0x4a), RGBColor(0xdc, 0xfc, 0xe7), ['存好法律、會看掃描檔', '自動標出問題、人來決定', '4 種畫面、自動測試、影片']),
         ('○ 還沒做', GR, RGBColor(0xf3, 0xf4, 0xf6), ['更多種法律', '合約上鎖、到期刪除', '登入帳號、放上網路']),
         ('? 還不知道', RGBColor(0xd9, 0x77, 0x06), RGBColor(0xfe, 0xf3, 0xc7), ['用真的合約找得準不準', '法務用起來順不順', '很長的合約跑多快'])]
for i, (t, c, bg, its) in enumerate(cols_):
    x = 0.6 + i*4.13
    box(s, x, 1.85, 3.9, 0.65, t, fill=c, line=c, sz=22, color=WH, shape=MSO_SHAPE.RECTANGLE)
    box(s, x, 2.5, 3.9, 2.0, '', fill=bg, line=c, shape=MSO_SHAPE.RECTANGLE)
    tb(s, x+0.2, 2.65, 3.6, 1.9, its, 18)
tb(s, 0.6, 4.7, 12.2, 0.9, ['接下來：① 拿 20 份真的合約（去掉個資），請法務給答案　② 換更聰明的 AI 再考一次', '　　　　③ 把法務「是／不是」的紀錄拿來讓電腦變更準'], 18)
box(s, 0.6, 6.0, 12.1, 0.95, '電腦負責提醒，每個提醒都附法律原文，最後由人決定', fill=A, line=A, sz=26, color=WH, shape=MSO_SHAPE.RECTANGLE)
notes(s, N[6])

# 完成度清單（表格截圖自 docs/status.html）
s = prs.slides.add_slide(L); head(s, '附表 1', '做好了什麼', '先做的都是「少了它就不能用」的東西，而且都有證明')
s.shapes.add_picture('img/status_done.png', Inches(0.6), Inches(1.95), width=Inches(12.1))
notes(s, '這張表回答「為什麼先做這些」。原則只有一個：少了它，這個工具就不能用。'
         '沒有真的法律，就沒東西可以比對；看不懂掃描檔，法務就用不了；沒有人來決定，就變成電腦在判定違法。'
         '每一項我都寫了「怎麼知道真的做好」，不是只說做好了。')
s = prs.slides.add_slide(L); head(s, '附表 2', '還沒做、還不知道的', '沒做的是故意先不做；做了但還不知道好不好的，我也老實列出來')
s.shapes.add_picture('img/status_todo.png', Inches(1.15), Inches(1.85), width=Inches(11.0))
s.shapes.add_picture('img/status_ver.png', Inches(1.15), Inches(1.85 + 11.0*700/2904 + 0.15), width=Inches(11.0))
notes(s, '上半部是還沒做的，每一項都是故意先不做，也都想好之後怎麼做。我特別想提「合約上鎖、到期自動刪」：'
         '這個工具本身就在處理個資，正式版一定要做到，這也是個資法第 27 條要求的安全維護。'
         '下半部是「做了，但還不知道好不好」，最重要的是準不準：新考卷只有 0/3，要用真的合約和法務給的答案才能證明。')

# Backup A
s = prs.slides.add_slide(L); head(s, '備用 A', '我怎麼檢查 AI 做得對不對', 'AI 說「做完了」，我一定自己再看一次')
table(s, 0.6, 1.95, 12.1, [('時間', '發生什麼事', '我怎麼處理'),
      ('19:50', '電腦裡有兩個版本的 Python，會打架', '統一用同一個版本'),
      ('19:56', '看圖認字把「洩」認成「浅」', '放寬比對，記下這個缺點'),
      ('20:05', 'AI 助手說做完了，其實報告根本不存在', '自己打開檔案檢查，重做一次'),
      ('20:12', '練習過的題目全對', '再出一張新考卷 → 0/3，老實寫出來')], [1.3, 5.6, 5.2], 18, 0.68)
tb(s, 0.6, 5.7, 12.1, 0.6, '工具裡的三道關：AI 只能從找到的法律裡選 → 檢查號碼是真的 → 人決定', 20, True, A)
notes(s, N[7])

# Backup B timeline
s = prs.slides.add_slide(L); head(s, '備用 B', '兩小時怎麼用', '先想清楚、再分工一起做、最後一定檢查')
tl = [('19:43', '問清楚'), ('19:52', '寫計畫書'), ('19:54', '分三組\n一起做'), ('20:00', '整條路\n走得通'), ('20:05', '出考卷\n考自己'), ('20:16', '畫面、影片、\n簡報')]
line = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.9), Inches(3.6), Inches(12.5), Inches(3.6)); line.line.color.rgb = A; line.line.width = Pt(4)
for i, (t, d) in enumerate(tl):
    x = 0.8 + i*2.05
    box(s, x+0.65, 3.35, 0.5, 0.5, '', fill=WH, line=A, shape=MSO_SHAPE.OVAL)
    tb(s, x, 2.5, 1.8, 0.6, t, 22, True, A, PP_ALIGN.CENTER)
    tb(s, x-0.2, 4.1, 2.2, 1.2, d.split('\n'), 18, False, DK, PP_ALIGN.CENTER)
tb(s, 0.9, 5.8, 12, 0.6, '20:05 發現 AI 助手的報告是假的 → 丟掉重做', 20, True, RGBColor(0xdc, 0x26, 0x26))
notes(s, N[8])

# Backup C demo contracts
s = prs.slides.add_slide(L); head(s, '備用 C', '四份練習用的假合約', '每一份都是為了看一種狀況（也包含失敗的）')
table(s, 0.6, 2.0, 12.1, [('合約', '想看什麼', '結果'), ('01 委外行銷', '問題很明顯時', '5 個全抓到'), ('02 員工資料（掃描的）', '看圖認字', '3 個抓到 2 個（認錯一個字）'),
      ('03 寫得很好的合約', '會不會亂標', '0 個，沒有亂標'), ('04 換個說法', '換句話說抓不抓得到', '6 個都沒抓到')], [4.0, 3.6, 4.5], 20, 0.75)
notes(s, N[9])

prs.save('合約外規檢查_簡報.pptx'); print('saved v2')
