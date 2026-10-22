/* Trang Thử nghiệm — trạng thái dùng chung (S) và tiện ích hiển thị: banner, đang tải, ô ngày giờ. */
(function (MSL) {
  'use strict';

  var L = MSL.lab = MSL.lab || {};
  var $ = MSL.dom.$;

  var S = {
    datasets: [],
    dataset: null,
    algorithms: [],
    algo: null,
    mode: 'full',
    digits: 2,
    run: null,            // kết quả chạy hiện tại {events, timeline, stats, ...}
    allBars: [],          // nến của khoảng đang chọn
    replay: null,         // {sid, cursor, total, events, timeline, playing, timer, renderedCursor}
    notesOn: false,       // nút «Ghi chú»: hiện ghi chú phía trên chart (tắt sẵn = chỉ chart; notes.js)
    runs: [],
    selectedRuns: [],
    layers: MSL.algos.defaultLayers(),   // lớp hiển thị và mặc định do từng plugin algos/ khai báo
    baseline: null,       // run swing_pivot 3/3 phủ lên để so sánh {run_id, events, dataset_id, range}
    selectedEventId: null,
    chart: null,
    pane: null,           // khung phụ dưới chart (hook `pane` của plugin) — pages/lab/run.js renderPane
    draftLabels: [],
    labelSetId: null,
    labelSets: [],
    labelDirty: false,
    labelDraftSaved: null
  };

  function banner(kind, html) {
    var el = $('#status-banner');
    if (!kind) { el.hidden = true; el.innerHTML = ''; if (L.syncNotesToggle) L.syncNotesToggle(); return; }
    el.className = 'note note-' + kind;
    el.innerHTML = html;
    el.hidden = false;
    if (L.syncNotesToggle) L.syncNotesToggle();
  }

  function loading(on) { $('#chart-loading').hidden = !on; }

  function toLocalInput(iso) {
    if (!iso) return '';
    return String(iso).replace('+00:00', '').replace('Z', '').slice(0, 16);
  }

  function fromLocalInput(v) { return v ? v + ':00+00:00' : null; }

  // Dataset dài (vd M1 cả năm, M15 8 năm): chạy/vẽ toàn bộ tạo kết quả hàng trăm MB và hàng
  // trăm nghìn marker — trình duyệt có thể treo. Mặc định chỉ lấy ~DEFAULT_MAX_BARS nến gần nhất.
  var DEFAULT_MAX_BARS = 50000;
  var HEAVY_RUN_BARS = 100000;

  L.DEFAULT_MAX_BARS = DEFAULT_MAX_BARS;
  L.HEAVY_RUN_BARS = HEAVY_RUN_BARS;
  L.S = S;
  L.banner = banner;
  L.fromLocalInput = fromLocalInput;
  L.loading = loading;
  L.toLocalInput = toLocalInput;
})(window.MSL);
