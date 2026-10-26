/* Trang Gán nhãn — khoảng đề xuất theo ngày giờ UTC ↔ chỉ số nến. */
(function (MSL) {
  'use strict';

  var G = MSL.label;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = G.S;

  // ---- Khoảng đề xuất theo NGÀY GIỜ (UTC). Backend vẫn nhận chỉ số nến; việc
  // ánh xạ ngày giờ -> nến làm ở đây, trên chính các nến của dataset đang mở.

  function pad2(n) { return String(n).padStart(2, '0'); }

  /** Unix giây -> giá trị ô datetime-local, hiểu là giờ UTC. */
  function tsToInput(ts) {
    var d = new Date(ts * 1000);
    return d.getUTCFullYear() + '-' + pad2(d.getUTCMonth() + 1) + '-' + pad2(d.getUTCDate()) +
      'T' + pad2(d.getUTCHours()) + ':' + pad2(d.getUTCMinutes());
  }

  function inputToTs(v) {
    if (!v) return NaN;
    return Date.parse(v.length === 16 ? v + ':00Z' : v + 'Z') / 1000;
  }

  function tsText(ts) { return tsToInput(ts).replace('T', ' ') + ' UTC'; }

  function setRangeByIndex(a, b) {
    var ba = G.barByIndex(a);
    var bb = G.barByIndex(b);
    if (ba) $('#auto-start').value = tsToInput(ba.time);
    if (bb) $('#auto-end').value = tsToInput(bb.time);
    updateRangeHint();
  }

  /**
   * Ngày giờ đang nhập -> khoảng nến: nến đầu = nến đầu tiên có thời gian >= "Từ",
   * nến cuối = nến cuối cùng có thời gian <= "Đến".
   */
  function rangeFromInputs() {
    var t1 = inputToTs($('#auto-start').value);
    var t2 = inputToTs($('#auto-end').value);
    if (isNaN(t1) || isNaN(t2)) return { error: 'Chọn đủ ngày giờ bắt đầu và kết thúc.' };
    if (t1 > t2) return { error: 'Ngày bắt đầu đang sau ngày kết thúc.' };
    var a = null;
    var b = null;
    for (var i = 0; i < S.bars.length; i++) {
      var t = S.bars[i].time;
      if (a === null && t >= t1) a = S.bars[i];
      if (t <= t2) b = S.bars[i];
    }
    if (!a || !b || a.index > b.index) return { error: 'Không có nến nào trong khoảng ngày này.' };
    return { start: a.index, end: b.index, n: b.index - a.index + 1, startTs: a.time, endTs: b.time };
  }

  function updateRangeHint() {
    var el = $('#auto-range-hint');
    if (!S.dataset || !S.bars.length) { el.textContent = 'Chọn dataset để đặt khoảng.'; return; }
    var r = rangeFromInputs();
    if (r.error) { el.innerHTML = '<span class="st-removed">' + esc(r.error) + '</span>'; return; }
    el.textContent = r.n + ' nến ' + S.dataset.timeframe + ': ' + tsText(r.startTs) + ' → ' +
      tsText(r.endTs) + ' (nến #' + r.start + ' → #' + r.end + ').';
  }

  function resetAutoRange() {
    var has = !!(S.dataset && S.bars.length);
    var first = has ? S.bars[0] : null;
    var last = has ? S.bars[S.bars.length - 1] : null;
    $('#auto-start').min = $('#auto-end').min = first ? tsToInput(first.time) : '';
    $('#auto-start').max = $('#auto-end').max = last ? tsToInput(last.time) : '';
    if (!has) {
      $('#auto-start').value = '';
      $('#auto-end').value = '';
    } else if (S.auto && G.barByIndex(S.auto.start) && G.barByIndex(S.auto.end)) {
      setRangeByIndex(S.auto.start, S.auto.end);
    } else {
      setRangeByIndex(first.index, last.index);
    }
    updateRangeHint();
    $('#auto-run').disabled = !has || !S.autoAlgos.length;
  }

  function rangeText(a, b) {
    var ba = G.barByIndex(a);
    var bb = G.barByIndex(b);
    if (!ba || !bb) return 'nến ' + a + ' → ' + b;
    return tsText(ba.time) + ' → ' + tsText(bb.time);
  }

  G.rangeFromInputs = rangeFromInputs;
  G.rangeText = rangeText;
  G.resetAutoRange = resetAutoRange;
  G.setRangeByIndex = setRangeByIndex;
  G.updateRangeHint = updateRangeHint;
})(window.MSL);
