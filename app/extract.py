"""PDF text extraction (text layer, OCR fallback) and clause splitting."""
from __future__ import annotations

import re
import time

import fitz  # PyMuPDF

MIN_CHARS = 20
OCR_DPI = 200
_ocr_engine = None
LAST_OCR_SECONDS: list[float] = []  # per-page OCR timings of the last call


def _get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR

        # "ch" (PP-OCRv4) measured more accurate on our traditional-Chinese scan than
        # "chinese_cht" (v3): 93% vs 91% char match, and cht misreads 關係企業 -> 關條企業.
        try:
            _ocr_engine = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
        except Exception:
            _ocr_engine = PaddleOCR(lang="chinese_cht", use_angle_cls=True, show_log=False)
    return _ocr_engine


def _ocr_page(page) -> str:
    import numpy as np

    pix = page.get_pixmap(dpi=OCR_DPI)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    img = img[:, :, ::-1].copy()  # RGB -> BGR
    result = _get_ocr().ocr(img, cls=True)
    boxes = (result or [None])[0] or []
    items = []
    for box, (txt, _conf) in boxes:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append((min(ys), max(ys), min(xs), txt))
    items.sort(key=lambda t: (t[0], t[2]))
    # group into lines by vertical overlap, then left-to-right
    lines: list[list] = []
    for it in items:
        if lines:
            last = lines[-1]
            top, bot = last[0][0], last[0][1]
            if it[0] < (top + bot) / 2:
                last.append(it)
                continue
        lines.append([it])
    return "\n".join("".join(t[3] for t in sorted(l, key=lambda t: t[2])) for l in lines)


def extract_text(pdf_path: str) -> dict:
    LAST_OCR_SECONDS.clear()
    used_ocr = False
    parts = []
    with fitz.open(pdf_path) as doc:
        n = doc.page_count
        for page in doc:
            t = page.get_text("text")
            if len(re.sub(r"\s", "", t)) < MIN_CHARS:
                t0 = time.perf_counter()
                t = _ocr_page(page)
                LAST_OCR_SECONDS.append(time.perf_counter() - t0)
                used_ocr = True
            parts.append(t)
    return {"text": "\n".join(parts), "method": "ocr" if used_ocr else "text", "pages": n}


_HEADING = re.compile(r"^[ \t　]*(第[ \t　]*[一二三四五六七八九十百零〇\d]+[ \t　]*條)", re.M)


def split_clauses(text: str) -> list[dict]:
    matches = list(_HEADING.finditer(text))
    if not matches:
        return [{"seq": 1, "title": "全文", "text": text.strip()}]
    clauses = []
    preamble = text[: matches[0].start()].strip()
    # preamble that is more than a short title line is kept as its own clause
    if preamble and (len(preamble.splitlines()) > 2 or len(preamble) > 60):
        clauses.append({"title": "前言", "text": preamble})
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end].strip()
        body = re.sub(r"\n(?!\n)", "", body)  # rejoin wrapped lines
        clauses.append({"title": re.sub(r"\s", "", m.group(1)), "text": body})
    return [{"seq": i + 1, **c} for i, c in enumerate(clauses)]
