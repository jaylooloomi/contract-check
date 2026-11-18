# 合約外規檢查 Prototype

上傳合約 PDF 後，系統對照**個人資料保護法**標出「可能疑慮」，每一項都附上法條原文，再由法務人員確認或駁回。

> ⚠ 系統只提示可能的疑慮，**不判定是否違法**。所有合約都是虛構的，不含真實客戶資料。

## 啟動（1 個指令）
```powershell
py -3.12 -m uvicorn app.main:app --port 8000
```
啟動後用瀏覽器打開 http://localhost:8000

需要的環境：Python 3.12（FastAPI、PyMuPDF、PaddleOCR）。AI 輔助功能另外需要 Ollama 和 `qwen3:8b`；沒有也能用，系統會自動只跑規則檢查。

## 示範 3 步
1. 上傳 `demo/01_委外行銷_文字版.pdf`，系統找出 5 項疑慮。
2. 點開任一項疑慮查看法條原文，按「確認」或「駁回」。
3. 上方切換 A／B／C 三種畫面；上傳 `demo/02_員工資料_掃描版.pdf` 可以示範 OCR。

| 畫面 | 網址 | 適合 |
|---|---|---|
| A 分割檢視 | `/` | 短合約，一眼看完 |
| B 審閱佇列 | `/v/b` | 大量複核，可用鍵盤 J/K/Y/N |
| C 全文標註 | `/v/c` | 從頭讀合約 |

所有畫面都可以在網址加上 `?id=<合約編號>`，直接打開檢查過的結果。

## 測試
```powershell
py -3.12 -m pytest tests -m "not e2e"
```
```powershell
py -3.12 -m pytest tests/e2e -m e2e
```
```powershell
py -3.12 eval/run_eval.py
```
三個指令依序是：驗收測試 AT1–AT7、Playwright 端對端測試、準確度實測（含答案卷）。

## 文件
| 檔案 | 內容 |
|---|---|
| `spec.md` | 規格：資料表、API、驗收標準（SDD） |
| `docs/architecture.html` | 架構圖 |
| `eval/report.md` | 實測與盲測結果（含過度擬合分析） |
| `docs/ux.md` | 三種畫面的 UX 設計 |
| `docs/timeline.md` | 開發時間線，以及檢查 AI 產出的紀錄 |
| `docs/deck/` | 簡報與講稿 |
| `demo/README.md` | 展示合約說明 |

## 法條來源
法務部全國法規資料庫：https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=I0050021
資料重建：`py -3.12 scripts/import_law.py`。原始 HTML 和抓取紀錄存在 `data/`。

## 已知限制
- 準確度只用虛構合約驗證過；盲測找到 0/3，詳見 `eval/report.md`。
- 上傳的合約存在本機 SQLite，**沒有自動刪除，也沒有加密**，只適合拿來展示。
- OCR 會把部分字認成簡體或認錯字，掃描檔可能因此漏抓疑慮。
- 只收錄個資法 1 部法規；修法後要手動重新匯入。
