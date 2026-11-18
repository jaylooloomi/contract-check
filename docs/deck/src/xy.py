# XY 矩陣圖（Apple 極簡配色）。位置是「我的判斷」，不是量測數據；圖上有註明。
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Microsoft JhengHei'
BLUE, GREY, INK, MUTE = '#0071e3', '#aeaeb2', '#1d1d1f', '#6e6e73'

def matrix(path, pts, xl, yl, quads):
    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=200)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axhline(.5, color='#e5e5ea', lw=1.5, zorder=0); ax.axvline(.5, color='#e5e5ea', lw=1.5, zorder=0)
    for (x, y, t, c) in quads:
        ax.text(x, y, t, fontsize=17, color=c, fontweight='bold', ha='left' if x < .5 else 'right', va='top' if y > .5 else 'bottom', alpha=.85)
    for (x, y, label, chosen, dx, dy) in pts:
        ax.scatter([x], [y], s=260, color=BLUE if chosen else 'white', edgecolor=BLUE if chosen else GREY, lw=2.2, zorder=3)
        ax.text(x + dx, y + dy, label, fontsize=16, color=INK if chosen else MUTE, fontweight='bold' if chosen else 'normal',
                ha='left' if dx >= 0 else 'right', va='center', zorder=4)
    ax.set_xlabel(xl, fontsize=16, color=MUTE, labelpad=10); ax.set_ylabel(yl, fontsize=16, color=MUTE, labelpad=10)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_color('#d2d2d7')
    ax.annotate('', xy=(1, -.06), xytext=(0, -.06), xycoords='axes fraction', arrowprops=dict(arrowstyle='->', color=MUTE))
    ax.annotate('', xy=(-.04, 1), xytext=(-.04, 0), xycoords='axes fraction', arrowprops=dict(arrowstyle='->', color=MUTE))
    plt.tight_layout(); plt.savefig(path, transparent=False, facecolor='white'); plt.close()

# ② 技術棧：X＝兩小時內做得完（越右越容易），Y＝適合這個題目（越上越適合）
matrix('img/xy_tech.png', [
    (.86, .80, 'SQLite＋全文檢索（FTS5）', True, .03, 0),
    (.26, .64, 'PostgreSQL＋向量', False, .03, 0),
    (.84, .66, 'FastAPI（Python）', True, .03, 0),
    (.40, .55, 'Next.js 全端', False, .03, 0),
    (.62, .88, 'PaddleOCR（繁中準）', True, .03, 0),
    (.62, .44, 'Tesseract', False, .03, 0),
    (.30, .76, '雲端 OCR（沒 key）', False, .03, 0),
    (.78, .56, '本機 AI qwen3:8b', True, .03, -.035),
    (.12, .86, 'Claude API（沒 key）', False, .03, 0),
], '兩小時內做得完 →（越右越容易）', '適合這個題目 →', [
    (.98, .98, '● 選這區', BLUE), (.02, .02, '不考慮', GREY), (.98, .02, '備案', GREY), (.02, .98, '之後再換', GREY)])

# ③ 開發項目：X＝要花的時間（越右越久），Y＝對考題的價值（越上越重要）
matrix('img/xy_items.png', [
    (.20, .93, '法律存進資料庫', True, .03, 0),
    (.14, .84, '引用驗證', True, .03, 0),
    (.30, .78, '關鍵字比對（規則）', True, .03, 0),
    (.12, .70, 'PDF 讀文字', True, .03, 0),
    (.36, .64, '人員複核畫面', True, .03, 0),
    (.56, .86, '出考卷考自己（盲測）', True, .03, 0),
    (.62, .74, '看圖認字（OCR）', True, .03, 0),
    (.70, .62, '本機 AI 檢查', True, .03, 0),
    (.22, .32, '看過的合約清單', True, .03, 0),
    (.62, .34, '更多種法律', False, .03, 0),
    (.78, .42, '用意思找（向量）', False, -.03, 0),
    (.72, .16, '登入帳號', False, .03, 0),
    (.88, .26, '放上網路', False, -.03, 0),
], '要花的時間 →（越右越久）', '對考題的價值 →', [
    (.02, .98, '先做', BLUE), (.98, .98, '值得花時間', BLUE), (.02, .02, '順手做', GREY), (.98, .02, '先不做', GREY)])
print('xy ok')
