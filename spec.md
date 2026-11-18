# 規格書：合約外規檢查 Prototype（SDD）

版本 v0.1｜2026-11-18 19:56｜本文件是所有模組的介面依據，實作要和這裡一致；要改介面，先改這份文件。

## 1. 目標與範圍
- **使用者**：法務人員。
- **輸入**：合約 PDF，可以是文字版或掃描版。
- **外規**：法條庫。本版只收錄 個人資料保護法（pcode I0050021）。
- **輸出**：每條款的「可能疑慮」清單，每項都附上存在於資料庫的法條條號與原文，由法務人員確認或駁回。
- **定位**：系統只提示可能疑慮，供人員複核，**不判定是否違法**。
- **本版不做**：多部法規、法規自動更新、帳號權限、正式部署。

## 2. 流程
```
PDF → extract_text（有文字層就直接讀／掃描檔走 OCR）→ split_clauses
    → 每條款：search_articles（找相關法條）→ rule_check + ai_check
    → validate_citations（引用的條號必須存在資料庫）→ 寫入 findings
    → 審閱頁：確認／駁回 → 寫入 reviews
```

## 3. 資料表（SQLite）
| 表 | 欄位 | 說明 |
|---|---|---|
| laws | id(pcode) PK, name, source_url, amended_date, fetched_at | 法規本身，以及資料來源、抓取時間 |
| articles | id PK, law_id FK, article_no("20","6-1"), chapter, content, UNIQUE(law_id, article_no) | 一筆就是一條法條 |
| articles_fts | FTS5(content), tokenize=trigram | 中文全文檢索 |
| contracts | id PK, filename, uploaded_at, extract_method('text'/'ocr'), raw_text | 上傳的合約 |
| clauses | id PK, contract_id FK, seq, title, text | 合約條款 |
| findings | id PK, contract_id, clause_id FK, source('rule'/'ai'), title, reason, law_id, article_no, created_at | 可能疑慮 |
| reviews | id PK, finding_id FK, decision('confirm'/'reject'), note, reviewed_at | 人員複核紀錄。保留每一次決定，以最新一筆為準 |

選擇 SQLite 的理由：單一檔案、不需要另外架伺服器、內建 FTS5，2 小時內能完成並展示。正式版可以換成 PostgreSQL，並加上 pgvector 做語意檢索。

## 4. 模組介面
| 模組 | 函式 | 回傳 |
|---|---|---|
| app/db.py | `connect(path)`, `init_db(conn)` | sqlite3.Connection |
| app/laws.py | `import_law(conn, src) -> int` | 匯入的條數 |
| | `search_articles(conn, query, limit=5)` | `[{law_id, article_no, content, score}]` |
| | `get_article(conn, law_id, article_no)` | dict 或 None |
| app/extract.py | `extract_text(pdf_path)` | `{text, method:'text'/'ocr', pages}` |
| | `split_clauses(text)` | `[{seq, title, text}]` |
| app/check.py | `rule_check(clause, conn)` | `[Finding]` |
| | `ai_check(clause, candidates)` | `[Finding]`；Ollama 不可用時回傳 `[]`，不丟例外 |
| | `validate_citations(findings, conn)` | 只保留條號存在的 Finding |
| | `check_contract(conn, contract_id, use_ai=True)` | 寫入 findings，回傳筆數 |

Finding 的格式：`{clause_seq, source, title, reason, law_id, article_no}`

## 5. AI 檢查
- 模型：本機 Ollama **qwen3:8b**，不需要 API key、資料不會離開本機；之後要換成 Claude API，只要替換 `ai_check` 的內部實作。
- 提示詞的限制：
  1. 只能從「本次檢索到的候選法條」裡引用條號。
  2. 只能回傳 JSON。
  3. 用繁體中文。
  4. 不確定時回傳空陣列。
- 防止 AI 亂講：用 `validate_citations` 把資料庫裡不存在的條號丟掉，並記錄丟掉的筆數。
- 已知限制：在本機跑一次大約 5–40 秒，示範時建議只對 1 份合約啟用。

## 6. API（FastAPI）
| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | /api/contracts | 上傳 PDF（multipart，欄位名 `file`，參數 `use_ai` 為 bool）→ `{contract_id, extract_method, clause_count, finding_count}` |
| GET | /api/contracts/{id} | `{contract, clauses[], findings[ +article_content +latest_review ]}` |
| POST | /api/findings/{id}/review | 內容 `{decision, note?}` → `{ok}` |
| GET | /api/law | `{name, source_url, amended_date, fetched_at, article_count}` |
| GET | / | 審閱頁（web/index.html） |

## 7. 驗收標準（每條都對應一個測試）
| # | 標準 | 測試檔 |
|---|---|---|
| AT1 | 個資法條數與官方來源一致；抽查第 11、12、20 條，內容包含官方原文 | tests/test_law.py |
| AT2 | 文字版 PDF：method=text，切出 5 條 | tests/test_extract.py |
| AT3 | 掃描版 PDF：method=ocr，包含關鍵詞，切出至少 4 條 | tests/test_extract.py（slow） |
| AT4 | 範例合約埋了 3 個問題（第 2、4、5 條款），規則檢查至少找到 2 個 | tests/test_check.py |
| AT5 | 所有疑慮引用的條號都存在資料庫（100%）；故意造一個假條號會被濾掉 | tests/test_check.py |
| AT6 | 確認或駁回之後重新查詢，紀錄仍在 | tests/test_api.py |
| AT7 | Ollama 不可用時，ai_check 回傳 `[]`，整個流程不會中斷 | tests/test_check.py |
