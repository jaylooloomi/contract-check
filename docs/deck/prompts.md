# 給 AI 的 Prompt（搭配 ppt-agent.md 使用）

## Prompt A：Codex（在專案資料夾裡執行，產生 .pptx）

```
你在 repo jaylooloomi/contract-check 裡工作。請讀 docs/deck/ppt-agent.md，照裡面的規格做一份 10 頁、16:9 的簡報，輸出到 docs/deck/v3/合約外規檢查_v3.pptx。

硬規則：
1. 所有文字、數字逐字照 ppt-agent.md，不准改寫、不准新增功能或數字。
2. 系統畫面、架構圖、長條圖只能用 ppt-agent.md §2 列的真實圖檔；長條圖可以用 matplotlib 依 §1 第 7 頁的表格重畫，但數字不能動。
3. 需要插圖時（第 1 頁主視覺、第 2 頁四個小圖示、第 3 頁三個卡片圖示、第 4 頁小插圖），用你的生圖工具產生「沒有任何文字」的 PNG（透明或白底），存到 docs/deck/v3/img/。文字一律在 pptx 裡疊上去。
4. 風格：Apple 極簡（白底、#1D1D1F 字、只用 #0071E3 一個強調色、大量留白、大圓角卡片、無框線），中文字型用微軟正黑體。
5. 每頁的講稿備註，從 docs/deck/講稿_v2.md 找到對應段落放進 notes。
6. 用 python-pptx 產生。做完後把每頁轉成 PNG（docs/deck/v3/preview/），逐張檢查：沒有文字溢出、重疊或換行斷字，同一列的元素要垂直置中對齊。有問題就修，修到沒有為止。
7. 最後回報：每頁一句話說明你做了什麼、用了哪些生成的圖、還有哪些問題沒解決。
```

## Prompt B：Canvas（ChatGPT／Claude，產生 HTML 簡報）

```
附件是 ppt-agent.md（簡報規格）和幾張真實截圖（arch.png、ui_a.png、ui_d3.png）。
請用一個單一 HTML 檔做出 10 頁、16:9 的網頁簡報：
- 方向鍵或點擊翻頁，右下角顯示頁碼，按 F 進入全螢幕。
- 風格：Apple 極簡（白底、#1D1D1F、強調色只用 #0071E3、大量留白、20px 圓角卡片、柔和陰影、無框線），字型 "Noto Sans TC"（Google Fonts）。
- 文字和數字逐字照 ppt-agent.md，不准改寫、不准新增。
- 第 7 頁的長條圖用 inline SVG 畫，數字照表格：2/9、4/9、9/9、0/3、0/3。
- 截圖放在用 CSS 畫的筆電外框裡。
- 翻頁時每頁的元素依序淡入（0.3 秒），不要花俏的轉場。
- 插圖用簡單的 inline SVG 線條圖示代替，不要放任何文字圖片。
完成後列出你沒辦法照規格做到的地方。
```

## Prompt C：單張插圖（給任何生圖工具，英文效果較穩）

> 共用結尾（每張都加上）：`isometric soft 3D illustration, white background, single accent color #0071E3 with light grey, minimal, clean, generous negative space, no text, no letters, no numbers, no logos, no human faces`

| 用在 | Prompt |
|---|---|
| 第 1 頁主視覺 | `A paper contract document lying flat, a glowing magnifying glass hovering over it, two highlighted lines in pale yellow, a small floating check-mark and cross-mark toggle beside it,` ＋共用結尾 |
| 第 2 頁圖示 ×4 | `Four matching line icons in a row: a document, a flow of three arrows, a finger tapping a button, a measuring ruler; thin 2px strokes,` ＋共用結尾 |
| 第 3 頁卡片圖示 ×3 | `Three matching rounded-square icons: an upload tray with an arrow, a magnifying glass over a page, a person silhouette with a check mark; thin strokes,` ＋共用結尾 |
| 第 4 頁 | `Three speech bubbles in a row, question marks turning into exclamation marks from left to right, gentle gradient,` ＋共用結尾 |
| 第 9 頁（可選） | `A path made of three stepping stones leading to a doorway of light, calm and hopeful,` ＋共用結尾 |
