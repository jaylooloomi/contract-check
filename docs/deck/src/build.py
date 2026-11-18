import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
F = 'Microsoft JhengHei'; A = RGBColor(0x00, 0x71, 0xe3); DK = RGBColor(0x1d, 0x1d, 0x1f); GR = RGBColor(0x6e, 0x6e, 0x73)  # Apple 極簡
WH = RGBColor(255, 255, 255)
plt.rcParams['font.family'] = 'Microsoft JhengHei'

# ---- chart (numbers from eval/report.md) ----
lab = ['第一版\n關鍵字(規則)', '第一版\n關鍵字+AI', '第二版關鍵字\n(照考古題改過)', '新考卷\n關鍵字', '新考卷\nAI']
rec = [2/9, 4/9, 9/9, 0, 0]; frac = ['2/9', '4/9', '9/9', '0/3', '0/3']; fp = [3, 8, 0, 0, 1]
fig, ax = plt.subplots(figsize=(11, 5.8), dpi=200)
cols = ['#c7dcf7', '#c7dcf7', '#0071e3', '#ff3b30', '#ff3b30']
ax.axvspan(2.5, 4.5, color='#fff1f0', alpha=1, zorder=0)
ax.bar(range(5), [r*100 for r in rec], color=cols, width=0.6, zorder=2)
for i, (r, f, e) in enumerate(zip(rec, frac, fp)):
    ax.text(i, r*100+2.5, f'抓到 {f}', ha='center', fontsize=17, fontweight='bold', color='#1d1d1f')
ax.set_xticks(range(5)); ax.set_xticklabels([f'{l}\n誤會(誤報) {e} 次' for l, e in zip(lab, fp)], fontsize=15)
ax.set_ylim(0, 120); ax.set_yticks([0, 50, 100]); ax.set_yticklabels(['0%', '50%', '100%'], fontsize=13)
ax.annotate('只會考古題（過度擬合）：\n練習過的全對', xy=(1.75, 100), xytext=(0.5, 88), fontsize=15, color='#0071e3',
            ha='center', fontweight='bold', arrowprops=dict(arrowstyle='->', color='#0071e3', lw=1.8))
ax.text(3.5, 55, '新考卷（盲測）：換個說法\n就全部沒抓到', ha='center', fontsize=18, color='#ff3b30', fontweight='bold')
for sp in ['top', 'right', 'left']: ax.spines[sp].set_visible(False)
ax.set_ylabel('抓到幾成', fontsize=14); plt.tight_layout(); plt.savefig('img/eval.png'); plt.close()

prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
L = prs.slide_layouts[6]

def setfont(r, sz, bold, color):
    f = r.font; f.size = Pt(sz); f.bold = bold; f.color.rgb = color; f.name = F
    rp = r._r.get_or_add_rPr(); ea = rp.makeelement(qn('a:ea'), {}); ea.set('typeface', F); rp.append(ea)

def tb(s, x, y, w, h, text, sz=18, bold=False, color=DK, align=PP_ALIGN.LEFT):
    t = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = t.text_frame; tf.word_wrap = True
    for i, line in enumerate(text if isinstance(text, list) else [text]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align; p.space_after = Pt(8)
        r = p.add_run(); r.text = line; setfont(r, sz, bold, color)
    return t

def box(s, x, y, w, h, text, fill=RGBColor(0xf5, 0xf5, 0xf7), line=None, sz=18, bold=True, color=DK, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    b = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = fill; b.shadow.inherit = False
    if line is None: b.line.fill.background()
    else: b.line.color.rgb = line; b.line.width = Pt(1.25)
    tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, l in enumerate(text if isinstance(text, list) else [text]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = l; setfont(r, sz if i == 0 else sz-3, bold if i == 0 else False, color)
    return b

def arrow(s, x1, y1, x2, y2):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = GR; c.line.width = Pt(2)
    ln = c.line._get_or_add_ln(); ln.append(ln.makeelement(qn('a:tailEnd'), {'type': 'triangle'}))

def head(s, n, kicker, title):
    tb(s, 0.6, 0.4, 10, 0.5, f'{kicker}', 16, True, A)
    tb(s, 0.6, 0.8, 12.2, 1.0, title, 32, True)
    tb(s, 11.6, 7.0, 1.4, 0.35, n, 11, False, GR, PP_ALIGN.RIGHT)

N = open('notes.txt', encoding='utf-8').read().split('\n===\n')
def notes(s, t): s.notes_slide.notes_text_frame.text = t.strip()

