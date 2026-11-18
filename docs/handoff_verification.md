# 交接驗證紀錄（Clean-room 重做）

> **本次重做由另一個 AI 代理在乾淨的 venv 中依文件執行；尚未由人類工程師在另一台電腦驗證。**

日期：2026-11-18

## 環境
- OS：Windows 11 Home 10.0.26200（與原作者是**同一台**電腦）
- Python：3.12.10（`py -3.12 -m venv`，venv 內從空的 site-packages 開始，只有 pip 25.0.1）
- 位置：`%TEMP%\cc_cleanroom_20261118_214638\contract-check`，用 `git clone <worktree>` 取得已 commit 的檔案（不是 GitHub；這次的修改還沒 push）
- CPU 執行，沒有用 GPU
- 本機有 Ollama + `qwen3:8b` 在跑，所以 eval 的 rule+ai 模式有實際呼叫 LLM

## 執行步驟與結果

| # | 步驟（依 docs/SETUP.md） | 時間 | 結果 |
|---|---|---|---|
| 1 | clone、`py -3.12 -m venv .venv`、啟用、升級 pip | 27 秒 | OK |
| 2 | `pip install -r requirements-dev.txt` | 239 秒 | OK，venv 約 1,017 MB |
| 2b | `python -m playwright install chromium` | 17 秒 | OK（本機快取已有 chromium-1208，沒有重新下載） |
| 3 | `python scripts/check_env.py` | 數秒 | **第一次失敗**：`import paddle` → `No module named 'setuptools'`（問題 1）。修正後 `OK` |
| 4 | 啟動 uvicorn，打 `/api/law` | 啟動 2 秒 | port 8000 → 誤判（問題 2）；改 port 8001：`article_count=66`，上傳 demo/01 得到 `finding_count=5` |
| 5a | `pytest tests -m "not e2e" -q` | 9 秒 | **17 passed, 29 deselected** |
| 5b | `pytest tests/e2e -m e2e -q` | 31 秒 | **29 passed** |
| 5c | OCR 測試在空的模型快取下跑（`USERPROFILE` 指到空資料夾） | 12 秒 | 3 passed；自動下載模型 17.2 MB |
| 5d | `python eval/run_eval.py` | 621 秒 | exit 0，8 行結果（見下） |

eval 結果（hits＝找到的疑慮／預期數；fp＝誤報）：

| 合約 | rule | rule+ai |
|---|---|---|
| a_marketing（文字） | 3/3，fp 0 | 3/3，fp 3 |
| b_hr（文字） | 3/3，fp 0 | 3/3，fp 2 |
| c_cloud（文字） | 3/3，fp 0 | 3/3，fp 2 |
| c_cloud（掃描） | 2/3，fp 1 | 2/3，fp 3 |

規則模式的結果是固定的。rule+ai 的誤報數由 LLM 產生，每次執行可能不同，不能拿來比對 `eval/results.json` 的逐字內容。

對照：同一天用全域 `py -3.12` 跑 `scripts/run_acceptance.ps1`：check_env OK／17 passed／29 passed／eval 680 秒，結果一致。

## 發現的問題與修正

1. **缺 setuptools（會讓整套 OCR 無法使用）**：Python 3.12 建立的 venv 不再內建 setuptools，但 paddle 2.6.2 執行時需要它，而且沒有把它列為相依套件。原作者的全域環境剛好有裝，所以一直沒發現。→ `requirements.txt` 加上 `setuptools==81.0.0`，SETUP 的疑難排解加一列。修正後從 check_env 開始重跑都通過。
2. **port 8000 被佔用時會誤判**：uvicorn 綁定失敗（`Errno 10048`），但 `/api/law` 仍然有回應，因為回應的是另一份已經在跑的伺服器。→ SETUP 疑難排解加一列，請改用 `--port 8001`。
3. **模型大小寫錯**：寫的是約 33 MB，實測空快取只下載 17.2 MB。33 MB 是加上繁中模型後的累計大小。→ 已修正文字。
4. **eval 時間沒寫清楚**：有 Ollama 時約 10–11 分鐘。→ 已補上實測數字。
5. **測試的副作用**：E2E 會覆寫 `docs/wizard/*.png`，eval 會覆寫 `eval/results.json`，兩者都是 repo 追蹤的檔案。→ SETUP 已註明怎麼還原。

## 未驗證／限制
- 沒有在另一台電腦驗證，也沒有由人類工程師驗證。
- 沒有測「完全沒有 Playwright 快取」的情況：chromium 下載約 150 MB 是估計值。
- pip 下載量約 300–400 MB 是估計值（pip 有本機快取，實際下載量可能比較少）。
- 沒有測「沒有 Ollama」的路徑（本機 Ollama 開著）。單元測試的 AT7 有用模擬的方式涵蓋這條路徑。
- macOS／Linux 和 `scripts/run_acceptance.sh` 都沒有測過。
- 在 clean-room 中沒有執行 `run_acceptance.ps1` 本身，而是手動逐一執行同樣的四個指令。這支腳本是在全域環境中執行過的。
