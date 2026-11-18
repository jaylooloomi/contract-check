/* 四個版本共用：檢查狀態橫幅、待人工確認條款、法條快照。
   原則：使用者絕不能把「AI 失敗」誤認為「已檢查、沒問題」。 */
(function () {
  const e = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const CSS = `.cc-st{border-radius:8px;padding:10px 14px;margin:10px 0;font-size:14px;line-height:1.7;border:1px solid}
.cc-st.ok{background:#ecfdf5;border-color:#6ee7b7;color:#065f46}.cc-st.warn{background:#fffbeb;border-color:#f59e0b;color:#78350f}
.cc-st.na{background:#f1f5f9;border-color:#cbd5e1;color:#334155}.cc-st b{font-weight:700}
.cc-nr{margin:6px 0 0;padding-left:18px}.cc-nr li{margin:2px 0}
.cc-badge{display:inline-block;font-size:12px;border-radius:4px;padding:0 6px;margin-left:6px}
.cc-badge.ok{background:#d1fae5;color:#065f46}.cc-badge.warn{background:#fef3c7;color:#92400e}.cc-badge.na{background:#e2e8f0;color:#334155}
.cc-ver{font-size:12px;color:#64748b;margin-top:4px}`;
  const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);

  function aiText(d) {
    const a = d.ai_status;
    if (a === 'ok') return {cls: 'ok', txt: '✓ AI 檢查完成'};
    if (a === 'not_requested') return {cls: 'na', txt: 'AI 未啟用（僅規則檢查）'};
    if (a === 'failed' || a === 'partial')
      return {cls: 'warn', txt: `⚠ AI 未完成（${d.ai_detail || (a === 'partial' ? '部分條款未完成' : '原因不明')}）— 結果可能不完整，請人工確認`};
    return {cls: 'na', txt: '檢查狀態未記錄（舊資料）'};
  }
  // d = GET /api/contracts/{id} 回應
  window.ccStatus = function (d) {
    const a = aiText(d), n = (d.findings || []).length, aiOk = d.ai_status === 'ok' || d.ai_status === 'not_requested';
    const rule = d.rule_status === 'ok' ? '✓ 規則檢查完成' : (d.rule_status ? '⚠ 規則檢查未完成' : '');
    const zero = (!n && d.ai_status) ? `<div data-testid="zero-result"><b>${e(window.ccZeroText(d))}</b></div>` : '';
    const nr = (d.clauses || []).filter(c => c.needs_review);
    const nrHtml = nr.length ? `<div data-testid="needs-review"><b>待人工確認（${nr.length} 條）：</b><ul class="cc-nr">${
      nr.map(c => `<li data-testid="needs-review-item" data-clause-seq="${e(c.seq)}">${e(c.title || ('條款 ' + c.seq))}：${e(c.needs_review_reason)}</li>`).join('')}</ul></div>` : '';
    const cls = a.cls === 'warn' ? 'warn' : (a.cls === 'ok' ? 'ok' : 'na');
    return `<div class="cc-st ${cls}" data-testid="check-status" data-ai-status="${e(d.ai_status || '')}" role="status">
      <div>${rule ? e(rule) + '｜' : ''}<span data-testid="ai-status">${e(a.txt)}</span></div>${zero}${nrHtml}
      ${d.law_version ? `<div class="cc-ver">法規版本：${e(d.law_version)}</div>` : ''}</div>`;
  };
  window.ccZeroText = function (d) {
    if (d.ai_status === 'failed' || d.ai_status === 'partial') return '僅完成規則檢查，未發現疑慮；AI 未完成，請人工確認';
    return d.ai_status ? '已完成檢查，未發現疑慮' : '此合約未發現疑慮（舊資料，未記錄檢查狀態）';
  };
  // 歷史列表用的小徽章（c = /api/contracts 列表項）
  window.ccBadge = function (c) {
    const a = aiText(c), short = {ok: 'AI ✓', not_requested: '僅規則', failed: '⚠ AI 未完成', partial: '⚠ AI 未完成'}[c.ai_status] || '狀態未記錄';
    return `<span class="cc-badge ${a.cls}" data-testid="ai-status" title="${e(a.txt)}">${e(short)}</span>`;
  };
  // 法條：優先顯示檢查當下快照，退回目前法條原文，附版本列
  window.ccLaw = function (f) {
    const txt = f.article_snapshot || f.article_content || '（查無法條原文）';
    return `${e(txt)}${f.law_version ? `<div class="cc-ver" data-testid="law-version">法規版本：${e(f.law_version)}</div>` : ''}`;
  };
})();
