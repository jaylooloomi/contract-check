from pathlib import Path

import pytest

from app import extract
from app.extract import extract_text, split_clauses

FIX = Path(__file__).parent / "fixtures"


def test_at2_text_pdf():
    r = extract_text(str(FIX / "sample_text.pdf"))
    assert r["method"] == "text" and r["pages"] == 1
    cl = split_clauses(r["text"])
    assert [c["title"] for c in cl] == ["第一條", "第二條", "第三條", "第四條", "第五條"]
    assert [c["seq"] for c in cl] == [1, 2, 3, 4, 5]
    assert "關係企業" in cl[1]["text"]


def test_split_no_heading():
    assert split_clauses("隨便一段文字") == [{"seq": 1, "title": "全文", "text": "隨便一段文字"}]


@pytest.mark.slow
def test_at3_scan_pdf():
    r = extract_text(str(FIX / "sample_scan.pdf"))
    print("OCR seconds/page:", extract.LAST_OCR_SECONDS)
    assert r["method"] == "ocr"
    assert "關係企業" in r["text"] and "永久保存" in r["text"]
    assert len(split_clauses(r["text"])) >= 4
