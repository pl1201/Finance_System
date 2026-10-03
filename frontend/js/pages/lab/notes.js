/* Trang Thử nghiệm — ghi chú riêng thuật toán dưới banner (nội dung do plugin algos/ cung cấp). */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var S = L.S;

  /**
   * Ghi chú của plugin phụ trách `algorithm` (hook `notes` → [[kind, html], …]).
   * Thuật toán không có ghi chú riêng: ẩn khung.
   */
  function renderAlgoNotes(algorithm, stats, dataStatus, pending) {
    var box = $('#algo-notes');
    if (!box) return;
    var notes = MSL.algos.callFor(algorithm, 'notes', stats, dataStatus, pending, S);
    if (!notes) { box.hidden = true; box.innerHTML = ''; return; }
    box.innerHTML = notes.map(function (n) {
      return '<div class="note note-compact note-' + n[0] + '">' + n[1] + '</div>';
    }).join('');
    box.hidden = false;
  }

  L.renderAlgoNotes = renderAlgoNotes;
})(window.MSL);
