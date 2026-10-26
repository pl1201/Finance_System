/* Trang Thử nghiệm — ghi chú riêng thuật toán dưới banner (nội dung do plugin algos/ cung cấp) và nút «Ghi chú»
   bật/tắt mọi ghi chú phía trên chart. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var S = L.S;

  var NOTES_KEY = 'msl.lab.notes';   // '1' = hiện ghi chú; mặc định (chưa chọn / không đọc được) = ẩn

  /**
   * Ghi chú của plugin phụ trách `algorithm` (hook `notes` → [[kind, html], …]).
   * Thuật toán không có ghi chú riêng: ẩn khung.
   */
  function renderAlgoNotes(algorithm, stats, dataStatus, pending) {
    var box = $('#algo-notes');
    if (!box) return;
    var notes = MSL.algos.callFor(algorithm, 'notes', stats, dataStatus, pending, S);
    if (!notes) { box.hidden = true; box.innerHTML = ''; syncNotesToggle(); return; }
    box.innerHTML = notes.map(function (n) {
      return '<div class="note note-compact note-' + n[0] + '">' + n[1] + '</div>';
    }).join('');
    box.hidden = false;
    syncNotesToggle();
  }

  /**
   * Nút «Ghi chú (n)» trên thanh công cụ. Tắt (mặc định) → `.main.notes-off`: ẩn dòng chế độ (#mode-note), ghi chú
   * thuật toán (#algo-notes) và banner kết quả / thông tin — chart chiếm phần đó. Banner LỖI / CẢNH BÁO của thao tác
   * vẫn hiện (CSS). n = số ghi chú đang bị ẩn; viền vàng khi trong đó có cảnh báo (vd khoảng trống bất thường).
   */
  function syncNotesToggle() {
    var btn = $('#btn-notes');
    var main = document.querySelector('.main');
    if (!btn || !main) return;
    var on = !!S.notesOn;
    main.classList.toggle('notes-off', !on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    var n = 0, warn = false;
    var mode = $('#mode-note');
    if (mode && mode.textContent.trim()) n++;
    var ban = $('#status-banner');
    if (ban && !ban.hidden && /\bnote-(ok|info)\b/.test(ban.className)) n++;
    var box = $('#algo-notes');
    if (box && !box.hidden) {
      n += box.children.length;
      warn = !!box.querySelector('.note-warn, .note-error');
    }
    btn.textContent = 'Ghi chú (' + n + ')';
    btn.classList.toggle('has-warn', !on && warn);
    btn.title = (on ? 'Ẩn' : 'Hiện') + ' ghi chú phía trên chart (chế độ, kết quả lần chạy, ghi chú thuật toán' +
      (warn ? ' — có cảnh báo' : '') + '). Lỗi và cảnh báo của thao tác luôn hiện.';
  }

  function toggleNotes() {
    S.notesOn = !S.notesOn;
    try { window.localStorage.setItem(NOTES_KEY, S.notesOn ? '1' : '0'); } catch (e) { /* chế độ riêng tư */ }
    syncNotesToggle();   // chart tự giãn theo khung (ResizeObserver trong MarketChart)
  }

  try { S.notesOn = window.localStorage.getItem(NOTES_KEY) === '1'; } catch (e) { S.notesOn = false; }

  L.renderAlgoNotes = renderAlgoNotes;
  L.syncNotesToggle = syncNotesToggle;
  L.toggleNotes = toggleNotes;
})(window.MSL);
