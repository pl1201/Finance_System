/* Trang Live MT5 — trạng thái dùng chung (S) và tiện ích hiển thị: banner, đang tải. */
(function (MSL) {
  'use strict';

  var V = MSL.live = MSL.live || {};
  var $ = MSL.dom.$;

  var S = {
    chart: null,
    pane: null,             // khung phụ dưới chart (chart/pane-host.js)
    layers: MSL.algos.defaultLayers(),   // lớp hiển thị, mặc định do plugin khai báo (khung lớp ở partials/ict-layers.html)
    digits: 2,
    dataset: null,          // plugin đọc S.dataset (nhãn MÔ PHỎNG): snapshot.dataset của luồng — nến MT5 thật
    selectedEventId: null,
    // Luồng đang xem (main.js mở, view.js vẽ): {sid, bars, cursor, events, timeline, snapshot, prev, renderedCursor, timer,
    // busy, fwdKey}. Con trỏ luôn ở nến cuối — không tiến / lùi.
    session: null,
    info: { algorithm: null, hasPkg: true }   // GET /api/live: thuật toán của luồng live (backend chọn), gói MetaTrader5 có cài
  };

  function banner(kind, html) {
    var el = $('#status-banner');
    if (!kind) { el.hidden = true; el.innerHTML = ''; return; }
    el.className = 'note note-' + kind;
    el.innerHTML = html;
    el.hidden = false;
  }

  function loading(on) { $('#chart-loading').hidden = !on; }

  V.S = S;
  V.banner = banner;
  V.loading = loading;
})(window.MSL);
