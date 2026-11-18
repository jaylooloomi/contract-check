# E2E 測試（Playwright）

```
py -3.12 -m pytest tests/e2e -m e2e
```

- 只跑快的：`py -3.12 -m pytest tests/e2e -m "e2e and not slow"`（排除掃描檔 OCR）
- 第一次執行若缺瀏覽器：`py -3.12 -m playwright install chromium`
- 測試會自己起一台伺服器：複製 `data/app.db` 到暫存檔、設 `CC_DB`、在 port 8013 跑 uvicorn，結束時關掉。不會動到 port 8000 與 `data/app.db`。換 port：設環境變數 `CC_E2E_PORT`。
- 已知 app bug（標 xfail）：版本 A 開 `/?id=99999` 時沒檢查 HTTP 狀態，顯示 JS TypeError 而不是「找不到合約」，且結果區被打開。
