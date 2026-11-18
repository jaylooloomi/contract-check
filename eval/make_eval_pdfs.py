"""Generate eval PDFs: text version for all contracts, 200dpi image-only scan for c_cloud."""
import sys
from pathlib import Path
import fitz
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from contracts import CONTRACTS
OUT = HERE / "pdfs"

def text_pdf(title, clauses, path):
    doc = fitz.open(); page = doc.new_page(width=595, height=842); font = "china-t"
    page.insert_textbox(fitz.Rect(60, 60, 535, 110), title, fontname=font, fontsize=18, align=1)
    y = 120
    for c in clauses:
        rc = page.insert_textbox(fitz.Rect(60, y, 535, y + 80), c, fontname=font, fontsize=13)
        assert rc >= 0, c
        y += 80 - rc + 12
    doc.save(path); doc.close()

def scan_pdf(src_path, path):
    src = fitz.open(src_path); scan = fitz.open()
    for pg in src:
        pix = pg.get_pixmap(dpi=200)
        p = scan.new_page(width=pg.rect.width, height=pg.rect.height)
        p.insert_image(p.rect, stream=pix.tobytes("png"))
    scan.save(path); scan.close(); src.close()

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for k, (t, cl) in CONTRACTS.items():
        text_pdf(t, cl, OUT / f"{k}_text.pdf")
    scan_pdf(OUT / "c_cloud_text.pdf", OUT / "c_cloud_scan.pdf")
    print("written", sorted(p.name for p in OUT.iterdir()))
