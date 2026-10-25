/* Trang Thử nghiệm — khung «Thuật toán đang làm gì» khi replay (nội dung do plugin có hook `explain`). */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var fmtIso = MSL.format.fmtIso;
  var S = L.S;

  /** Khung «Thuật toán đang làm gì» — chỉ đọc snapshot/sự kiện đã có tại con trỏ. */
  function renderExplain() {
    var box = $('#rp-explain');
    var r = S.replay;
    var own = r && r.snapshot ? MSL.algos.forAlgorithm(r.snapshot.algorithm) : null;
    var canExplain = !!(own && own.explain);
    var withExplain = MSL.algos.list().filter(function (p) { return typeof p.explain === 'function'; });
    var chk = $('#chk-explain');
    chk.disabled = !!(r && r.snapshot) && !canExplain;
    chk.parentNode.title = chk.disabled
      ? 'Giải thích từng bước hiện có cho ' + withExplain.map(function (p) { return '«' + p.title + '»'; }).join(', ') +
        '. Thuật toán này xem ở tab Thống kê (trạng thái nội bộ).'
      : 'Khung giải thích từng bước trên chart (' + withExplain.map(function (p) { return p.algorithms.join(', '); }).join(', ') + ')';
    if (!r || S.mode !== 'replay' || !canExplain || !$('#chk-explain').checked) { box.hidden = true; return; }
    box.hidden = false;
    var i = r.cursor, bar = i >= 0 ? r.bars[i] : null;
    $('#rp-explain-bar').textContent = bar ? 'nến #' + i + ' · ' + fmtIso(bar.close_time) : '';
    if (!bar) {
      $('#rp-explain-body').innerHTML = '<div class="xp xp-muted">Chưa nạp nến nào. Bấm ▶ hoặc → để nạp nến đầu tiên.</div>';
      return;
    }
    $('#rp-explain-body').innerHTML = own.explain(r, bar, S);
  }

  L.renderExplain = renderExplain;
})(window.MSL);
