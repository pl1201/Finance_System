/* Trang Đánh giá — trạng thái dùng chung (S) và định dạng số / thông báo lỗi. */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage = MSL.evalPage || {};
  var $ = MSL.dom.$;

  var S = {
    datasets: [],
    dataset: null,
    runs: [],
    selectedIds: {},
    baselineId: '',
    result: null,
    saved: [],
    selectedRunId: null,
    selectedEvent: null,
    labels: [],
    chart: null,
    barsCache: {},
    digits: 2,
    meta: null
  };

  function fmtNum(x, d) {
    if (x === null || x === undefined || x === '') return '—';
    var n = Number(x);
    if (!isFinite(n)) return '—';
    return n.toFixed(d);
  }

  function fmtDelta(x, d, invert) {
    if (x === null || x === undefined) return '';
    var n = Number(x);
    if (!isFinite(n)) return '';
    var good = invert ? n < 0 : n > 0;
    var cls = n === 0 ? 'flat' : (good ? 'up' : 'dn');
    var sign = n > 0 ? '+' : '';
    return '<span class="' + cls + '">' + sign + n.toFixed(d) + ' vs baseline</span>';
  }

  function paramsStr(p) {
    if (!p) return '—';
    try { return JSON.stringify(p); } catch (e) { return String(p); }
  }

  /** Trang này kẹp số chữ số thập phân tối đa 5 (trang Thử nghiệm: 6). */
  function detectDigits(bars) {
    return MSL.format.detectDigits(bars, 5);
  }

  function showError(msg) {
    var el = $('#eval-error');
    if (!msg) { el.hidden = true; el.textContent = ''; return; }
    el.hidden = false;
    el.textContent = msg;
  }

  E.S = S;
  E.detectDigits = detectDigits;
  E.fmtDelta = fmtDelta;
  E.fmtNum = fmtNum;
  E.paramsStr = paramsStr;
  E.showError = showError;
})(window.MSL);
