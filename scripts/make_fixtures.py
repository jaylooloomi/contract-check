"""Generate fictional contract fixtures: text PDF, image-only scan PDF, plain text."""
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"

TITLE = "委外資料處理合約（虛構）"
CLAUSES = [
    "第一條　甲方委託乙方處理甲方客戶之姓名、電話及地址等資料，以進行會員服務。",
    "第二條　乙方得將前條資料提供予其關係企業，用於行銷推廣。",
    "第三條　乙方應採取適當安全措施，防止資料被竊取或洩漏。",
    "第四條　合約終止後，乙方得永久保存前述資料，以備日後查核。",
    "第五條　資料如有外洩，乙方無須通知甲方或當事人。",
]
CONTRACT = TITLE + "\n" + "\n".join(CLAUSES) + "\n"


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / "sample_contract.txt").write_text(CONTRACT, encoding="utf-8")

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    font = "china-t"
    page.insert_textbox(fitz.Rect(60, 60, 535, 110), TITLE, fontname=font, fontsize=18, align=1)
    y = 120
    for c in CLAUSES:
        r = fitz.Rect(60, y, 535, y + 60)
        rc = page.insert_textbox(r, c, fontname=font, fontsize=13)
        assert rc >= 0, f"textbox overflow: {c}"
        y += 60 - rc + 12
    text_pdf = FIX / "sample_text.pdf"
    doc.save(text_pdf)
    doc.close()

    src = fitz.open(text_pdf)
    pix = src[0].get_pixmap(dpi=200)
    png = FIX / "sample_scan.png"
    pix.save(png)
    scan = fitz.open()
    p = scan.new_page(width=src[0].rect.width, height=src[0].rect.height)
    p.insert_image(p.rect, filename=str(png))
    scan.save(FIX / "sample_scan.pdf")
    scan.close()
    src.close()
    png.unlink()
    print("fixtures written to", FIX)


if __name__ == "__main__":
    main()
