/* Định dạng thời gian / số dùng chung (chart, các trang). */
(function (MSL) {
  'use strict';

  function fmtTime(ts) {
    var d = new Date(ts * 1000);
    var p = function (n) { return String(n).padStart(2, '0'); };
    return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate()) +
           ' ' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ' UTC';
  }

  /** ISO 8601 -> "YYYY-MM-DD HH:MM:SS UTC". Bỏ phần lẻ giây; múi khác UTC giữ nguyên độ lệch. */
  function fmtIso(iso) {
    if (!iso) return '—';
    var s = String(iso);
    var m = /^(\d{4}-\d\d-\d\d)[T ](\d\d:\d\d(?::\d\d)?)(?:\.\d+)?(Z|[+-]\d\d:?\d\d)?$/.exec(s);
    if (!m) return s;
    var tz = !m[3] ? '' : (m[3] === 'Z' || /^[+-]00:?00$/.test(m[3]) ? ' UTC' : ' ' + m[3]);
    return m[1] + ' ' + m[2] + tz;
  }

  function isFiniteNum(x) {
    return typeof x === 'number' && isFinite(x);
  }

  /** Số chữ số thập phân để hiển thị giá: theo close của tối đa 200 nến đầu, kẹp trong [2, maxDigits]. */
  function detectDigits(bars, maxDigits) {
    var cap = maxDigits === undefined ? 6 : maxDigits;
    var maxD = 0;
    for (var i = 0; i < Math.min(bars.length, 200); i++) {
      var v = String(bars[i].close);
      var dot = v.indexOf('.');
      if (dot >= 0) maxD = Math.max(maxD, v.length - dot - 1);
    }
    return Math.max(2, Math.min(maxD, cap));
  }

  MSL.format = { fmtTime: fmtTime, fmtIso: fmtIso, isFiniteNum: isFiniteNum, detectDigits: detectDigits };
})(window.MSL);
