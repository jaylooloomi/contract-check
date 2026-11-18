"""Generate fictional demo contracts (text PDF / image-only scan PDF + .txt sources).

Usage:  py -3.12 demo/make_demo.py
All parties and content are FICTIONAL.
"""
from pathlib import Path

import fitz  # PyMuPDF

DEMO = Path(__file__).resolve().parent

CONTRACTS = {
 "01_委外行銷_文字版": ("會員行銷委外服務合約（虛構）", [
  "立約人：星河科技股份有限公司（虛構，下稱甲方）、晨光行銷顧問有限公司（虛構，下稱乙方）。",
  "第一條　甲方委託乙方辦理會員電子報與活動推播，乙方因此處理會員之姓名、電子郵件及手機號碼。",
  "第二條　乙方得將會員名單提供予其關係企業，用於行銷推廣其自有商品。",
  "第三條　為提供健康講座服務，乙方得蒐集會員之病歷摘要及健康檢查結果。",
  "第四條　乙方得將會員資料備份至境外資料中心，其所在地由乙方自行決定。",
  "第五條　本約終止後，乙方得永久保存會員資料，以備日後查核。",
  "第六條　會員資料如有外洩，乙方無須通知甲方或會員。",
  "第七條　雙方因本約所生之爭議，以臺灣臺北地方法院為第一審管轄法院。",
 ]),
 "02_員工資料_掃描版": ("人事薪資作業委外合約（虛構）", [
  "立約人：月影餐飲股份有限公司（虛構，下稱甲方）、王小明人力顧問社（虛構，下稱乙方）。",
  "第一條　甲方委託乙方辦理員工薪資計算及勞健保投保作業，乙方因此處理員工姓名、身分證統一編號及薪資帳戶。",
  "第二條　乙方為評估員工之適任性，得另行蒐集員工之犯罪前科紀錄。",
  "第三條　乙方得將員工通訊資料轉交其合作夥伴，作為推銷團體保險商品之用。",
  "第四條　員工離職後，其人事資料由乙方長期保管，不因離職而銷毀。",
  "第五條　乙方應指定專人負責資料安全，並每半年稽核存取權限一次。",
  "第六條　本約有效期間為二年，期滿前一個月經雙方書面同意得續約。",
 ]),
 "03_合規範本_文字版": ("客戶服務委外合約（虛構範本）", [
  "立約人：甲方與乙方（均為虛構）。",
  "第一條　甲方委託乙方辦理客服專線作業，乙方僅得於前述委託目的之必要範圍內處理客戶之姓名及聯絡電話。",
  "第二條　乙方非經甲方及客戶事前書面同意，不得將客戶資料提供予任何第三人，亦不得為委託目的以外之利用。",
  "第三條　乙方應採取存取控制、加密傳輸及操作紀錄等適當安全措施，並接受甲方定期稽核。",
  "第四條　乙方發現客戶資料遭竊取或洩漏時，應立即通知甲方，並於知悉後七十二小時內協助甲方通知受影響之客戶。",
  "第五條　客戶依法請求查詢、更正或刪除其資料時，乙方應於收受甲方通知後五日內配合辦理。",
  "第六條　本約終止或委託目的消失時，乙方應於三十日內刪除或返還全部客戶資料，並出具銷毀證明。",
  "第七條　雙方因本約所生之爭議，以臺灣臺北地方法院為第一審管轄法院。",
 ]),
 "04_換句話說_文字版": ("會員數據合作合約（虛構）", [
  "立約人：銀杏電商股份有限公司（虛構，下稱甲方）、極光數據有限公司（虛構，下稱乙方）。",
  "第一條　甲方委託乙方分析會員之姓名、消費紀錄及聯絡方式，以改善購物體驗。",
  "第二條　乙方得將會員名單出售予廣告公司，所得價金由雙方平分。",
  "第三條　乙方得將會員資料移轉至設於新加坡之子公司集中處理。",
  "第四條　會員請求刪除其資料時，乙方得拒絕之。",
  "第五條　會員資料保存至乙方認為已無必要時為止。",
  "第六條　為提供保險優惠，乙方得蒐集會員之體檢報告。",
  "第七條　發生資安事件時，乙方得自行決定是否告知會員。",
 ]),
}

FONT = "china-t"


def make_text_pdf(path: Path, title: str, clauses: list[str]) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_textbox(fitz.Rect(60, 60, 535, 110), title, fontname=FONT, fontsize=18, align=1)
    y = 120
    for c in clauses:
        rc = page.insert_textbox(fitz.Rect(60, y, 535, y + 200), c, fontname=FONT, fontsize=13)
        assert rc >= 0, f"textbox overflow: {c}"
        y += 200 - rc + 12
        assert y < 800, "page overflow"
    doc.save(path)
    doc.close()


def to_scan(text_pdf: Path, out: Path) -> None:
    src = fitz.open(text_pdf)
    scan = fitz.open()
    for pg in src:
        pix = pg.get_pixmap(dpi=200)
        p = scan.new_page(width=pg.rect.width, height=pg.rect.height)
        p.insert_image(p.rect, stream=pix.tobytes("png"))
    scan.save(out)
    scan.close()
    src.close()


def main() -> None:
    for name, (title, clauses) in CONTRACTS.items():
        (DEMO / f"{name}.txt").write_text(title + "\n" + "\n".join(clauses) + "\n", encoding="utf-8")
        pdf = DEMO / f"{name}.pdf"
        if "掃描" in name:
            tmp = DEMO / f"_{name}_tmp.pdf"
            make_text_pdf(tmp, title, clauses)
            to_scan(tmp, pdf)
            tmp.unlink()
        else:
            make_text_pdf(pdf, title, clauses)
        print("wrote", pdf.name)


if __name__ == "__main__":
    main()
