# SETUP — 從零重現驗收

目標：另一位工程師在自己的電腦上，照這份文件逐步做，就能得到與原作者相同的驗收結果。
已測環境：Windows 11、Python 3.12.10、CPU（不需要 GPU）。macOS／Linux 未測。
所有指令都在 **PowerShell、repo 根目錄** 執行。

## 0. 先決條件

| 項目 | 必要？ | 說明 |
|---|---|---|
| Python 3.12 | 必要 | `py -3.12 --version` 要印出 `Python 3.12.x`。paddlepaddle 2.6.2 沒有 3.13 的 wheel。 |
| Git | 必要 | 取得原始碼 |
| 網路 | 必要（第一次） | pip 下載約 300–400 MB（paddlepaddle CPU wheel 約 100 MB、opencv 兩套約 90 MB、scipy／scikit-image 等）；Playwright chromium 約 150 MB；PaddleOCR 模型第一次 OCR 時自動下載約 17 MB（中文模型；另有繁中辨識模型時合計約 33 MB）到 `%USERPROFILE%\.paddleocr\whl` |
| Ollama + `qwen3:8b` | 選用 | AI 輔助檢查用，模型約 5.2 GB。沒裝也能跑：系統自動只做規則檢查，所有測試都不依賴它。 |

> ⚠ **`python` 與 `py -3.12` 陷阱**：Windows 上 `python` 可能指向別的版本（3.13、Microsoft Store 版，或沒有套件的另一份安裝）。
> 本文件一律先建 venv，**啟用 venv 後**才用 `python`。沒有啟用 venv 時請用 `py -3.12`，不要用 `python`。
> 用 `python -c "import sys; print(sys.executable)"` 確認目前用的是哪一份。

## 1. 取得原始碼、建立 venv

```powershell
git clone https://github.com/jaylooloomi/contract-check.git
cd contract-check
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```
若 `Activate.ps1` 因執行原則被擋：`Set-ExecutionPolicy -Scope Process Bypass`，再啟用一次（只影響目前視窗）。
不想啟用的話，以下所有 `python` 都換成 `.\.venv\Scripts\python.exe`。

## 2. 安裝相依套件

```powershell
python -m pip install -r requirements-dev.txt     # 含 requirements.txt；實測 4 分鐘，venv 約 1 GB
python -m playwright install chromium             # E2E 測試用瀏覽器，約 150 MB
```
- `requirements.txt`：執行期（FastAPI、PyMuPDF、PaddleOCR…）。只要跑系統、不跑測試，裝這個就夠。
- `requirements-dev.txt`：再加 pytest、httpx、playwright。
- E2E 測試會重新截圖覆寫 `docs/wizard/*.png`，屬正常；不想留下變更就 `git checkout docs/wizard`。
- 版本都已釘死；`numpy` 必須 < 2（paddle 2.6 的限制）。

選用（AI 輔助）：安裝 Ollama（https://ollama.com），然後 `ollama pull qwen3:8b`。

## 3. 檢查環境

```powershell
python scripts/check_env.py
```
預期：每個必要項目都是 `✓`，最後一行 `OK`，exit code 0。`–` 標記的是選用項目（Ollama、PaddleOCR 模型快取），不影響結果。
法規資料庫 `data/app.db` 已隨 repo 提供，需顯示 `66 articles`。

## 4. 啟動伺服器、用展示資料試用

```powershell
python -m uvicorn app.main:app --port 8000
```
- 瀏覽器開 http://localhost:8000
- 另開一個視窗確認 API：`Invoke-RestMethod http://localhost:8000/api/law` 應回傳個資法的 JSON（含 `article_count` 66 等欄位）。
- 展示資料在 `demo/`（說明見 `demo/README.md`）：
  - `demo/01_委外行銷_文字版.pdf` → 找出 5 項疑慮
  - `demo/02_員工資料_掃描版.pdf` → 走 OCR；第一次會下載模型，約慢 10–30 秒
- 結束：在伺服器視窗按 `Ctrl+C`。
- 注意：上傳的合約會寫進 `data/app.db`（repo 內追蹤的檔案）。想保持乾淨可以設 `$env:CC_DB="$env:TEMP\cc_demo.db"`，並先 `Copy-Item data\app.db $env:TEMP\cc_demo.db`。

## 5. 執行測試

```powershell
python -m pytest tests -m "not e2e" -q      # 驗收測試 AT1–AT7
python -m pytest tests/e2e -m e2e -q        # Playwright 端對端（自起 port 8013 伺服器，用 DB 副本）
python eval/run_eval.py                     # 準確度實測（含答案卷）
```

預期輸出（2026-11-18，Windows 11）：

| 指令 | 預期 | 時間 |
|---|---|---|
| 單元／驗收 | `17 passed, 29 deselected`（含 OCR 測試；第一次會下載模型，實測空快取也只多幾秒） | 約 10–40 秒 |
| E2E | `29 passed` | 約 35 秒 |
| eval | 印出 8 行 JSON（4 份 PDF × rule / rule+ai），寫入 `eval/results.json` | 沒有 Ollama：約 1–2 分鐘；有 Ollama + qwen3:8b：約 11 分鐘（實測 680 秒） |

- warnings 很多（paddle／protobuf 的 DeprecationWarning）屬正常。
- eval 會覆寫 repo 內追蹤的 `eval/results.json`；不想留下變更就 `git checkout eval/results.json`。
- 沒有 Ollama 時 rule+ai 的結果會等於 rule（AI 呼叫失敗一律回傳空，AT7）。

### 一鍵跑完
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_acceptance.ps1
```
依序跑 check_env → 單元 → E2E → eval，紀錄寫到 `acceptance_logs\acceptance_<時間>.log`，最後印出每步 exit code 與秒數。
會自動用目前啟用的 venv（或 `.venv\`），否則退回 `py -3.12`；也可指定 `-Python <python.exe>`。
macOS／Linux 有 `scripts/run_acceptance.sh`（未測試）。

## 6. 疑難排解

| 症狀 | 原因／解法 |
|---|---|
| `ModuleNotFoundError: fastapi`（或其他） | 用錯 Python。啟用 venv，或改用 `.\.venv\Scripts\python.exe`；不要用裸的 `python`。 |
| pip 找不到 `paddlepaddle==2.6.2` | Python 不是 3.12（或是 32 位元）。重建 3.12 64-bit venv。 |
| `import paddle` 報 `No module named 'setuptools'` | Python 3.12 的 venv 預設不含 setuptools，paddle 執行期會用到。已列在 `requirements.txt`；舊版 clone 請 `python -m pip install setuptools==81.0.0`。 |
| `numpy` 相關錯誤／`_ARRAY_API not found` | 裝到 numpy 2.x。`python -m pip install numpy==1.26.4`。 |
| E2E 報 `Executable doesn't exist ... chromium` | 沒跑 `python -m playwright install chromium`（要在同一個 venv 裡跑）。 |
| 啟動時 `[Errno 10048]`／`address already in use`，但 `/api/law` 仍有回應 | port 8000 已被別的程式（例如另一份本專案）佔用，你連到的是**那一個**伺服器。改 `--port 8001`。 |
| E2E 報 `server not ready` | port 8013 被佔用。設 `$env:CC_E2E_PORT=8023` 再跑。 |
| OCR 測試很慢或卡住 | 第一次在下載模型到 `~/.paddleocr`；需要網路。公司 proxy 擋下載時，可從已跑過的機器複製整個 `.paddleocr` 資料夾。 |
| 終端機中文／✓ 變亂碼 | `$env:PYTHONIOENCODING="utf-8"`；或用 Windows Terminal。 |
| AI 輔助沒有作用 | Ollama 沒開或沒有 `qwen3:8b`；`check_env.py` 會顯示。系統仍會正常做規則檢查。 |
