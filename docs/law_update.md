# 法條定期更新說明

資料來源：全國法規資料庫（law.moj.gov.tw）個人資料保護法頁面 `LawAll.aspx?pcode=I0050021`，以網頁擷取（HTML scraping）方式取得。

## 一、怎麼運作

指令：

```
py -3.12 scripts/update_law.py              # 上網抓最新版並更新
py -3.12 scripts/update_law.py --dry-run    # 只比對、不寫入
py -3.12 scripts/update_law.py --from-file data/raw/I0050021_LawAll.html   # 用本機檔案（離線測試）
```

每次執行依序做五件事：

1. **抓取（fetch）**：逾時 30 秒，失敗會再試 2 次（間隔 2 秒、4 秒）。抓到的原始網頁一律存成 `data/raw/I0050021_<時間>.html`，之後要追查可以拿原檔比對。
2. **解析與驗證（validate）**：寫入資料庫之前先檢查，任何一項不通過就整次放棄、不寫任何東西：
   - 條數至少 50 條，且與資料庫現有條數相差不超過 ±10%（防止網頁改版只抓到一半）
   - 必須包含第 1、2、20 條（關鍵條文）
   - 不可有內容為空的條文、不可有重複條號
   - 必須解析得出修正日期
3. **逐條比對（diff）**：每條內容先去掉空白差異（正規化，normalize），再算 SHA-256 指紋（hash），分成新增／修改／刪除／未變。
4. **單一交易寫入（transaction）**：
   - 整部法規的指紋和最新版本相同 → 判定「無變動」，不建立新版本。所以**重跑幾次都不會產生重複資料**。
   - 有變動 → 在 `law_versions` 新增一版；`article_history` 把舊條文的有效期限（valid_to）結束，再寫入新條文；`articles`（現行條文，含全文檢索 FTS）同步更新。全部在同一個交易裡，中途出錯會整筆還原（rollback）。
   - 第一次執行時，會先把資料庫現有條文登錄為第 1 版。
5. **記錄（log）**：每次執行都在 `data/law_update_log.jsonl` 加一行 JSON：時間、結果（OK／NOCHANGE／FAIL）、各類條數、變動條號、錯誤訊息。

**過去的審查結果不受影響**：每筆疑慮（findings）在產生時已經存下當時的條文原文（article_snapshot）與法規版本（law_version），法條更新後仍看得到當時依據的是哪一版、哪段文字。

版本紀錄可由 `GET /api/law/history` 查看。

## 二、怎麼排程

不需要額外的排程系統，用作業系統內建的即可。建議每週一次（法規修正頻率很低）。

**Windows 工作排程器（Task Scheduler）**，每週一早上 6 點：

```
schtasks /Create /TN "contract-check 法條更新" /SC WEEKLY /D MON /ST 06:00 ^
  /TR "cmd /c cd /d D:\path\to\contract-check && py -3.12 scripts\update_law.py >> data\law_update_stdout.log 2>&1"
```

**Linux／macOS cron**，每週一早上 6 點：

```
0 6 * * 1 cd /path/to/contract-check && python3.12 scripts/update_law.py >> data/law_update_stdout.log 2>&1
```

## 三、失敗怎麼發現

- **結束代碼（exit code）**：0 = 成功（有更新或無變動）；2 = 失敗（網路錯誤、網頁結構改變、驗證未通過），此時資料庫完全沒被改動，系統繼續用舊版條文。
- **記錄檔**：`data/law_update_log.jsonl` 的 `result` 為 `FAIL` 時，`error` 欄寫明原因（例如「驗證未通過：缺少關鍵條文：第 20 條」）。
- **要監看什麼**：
  - 連續兩次以上 `FAIL` → 多半是官方網頁改版，需要調整解析程式。
  - 太久沒有任何一筆紀錄（例如超過 8 天）→ 排程本身沒在跑。
  - 出現 `OK`（有新版本）→ 通知法務人員看變動條號。
- 排程器可設定「結束代碼非 0 時通知」，或由監控程式讀記錄檔最後一行。

## 四、新結果怎麼驗證

1. **自動驗證**：上面第 2 步的檢查，沒過就不寫入。
2. **變動摘要**：執行結果會列出「修改條號：20」等清單，可先用 `--dry-run` 看摘要再決定是否正式寫入；也可拿 `data/raw` 裡新舊兩份原始檔對照官方網頁。
3. **重跑評估（eval）**：有新版本時，重新執行專案的評估集（eval），確認審查結果的命中率沒有退步，並確認被引用的條號仍存在。
4. **單元測試**：`py -3.12 -m pytest -q tests/test_law.py tests/test_law_update.py`。

## 五、限制

- 網頁擷取依賴官方頁面的 HTML 結構（例如 `law-reg-content`、`col-no` 等標記）；官方改版時解析會失敗。此時驗證會擋下、不會寫入錯誤資料，但需要人工修改解析程式。
- 「整部法規相同就不建版」只比對條文內容；若官方只改了章節名稱或修正日期而條文不變，不會產生新版本（會更新最後確認時間）。
- 條文若整條改號（例如第 6 條拆成 6、6-1），會被記為「刪除＋新增」，不會自動對應。
- 未來可改用全國法規資料庫的開放資料 API（Open Data，JSON／XML 格式），結構較穩定，比對與驗證流程可以沿用。
