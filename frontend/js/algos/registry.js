/* Sổ đăng ký plugin hiển thị theo thuật toán (MSL.algos).
 *
 * Mỗi file algos/<tên>.js gọi MSL.algos.register({...}). Trang và lõi chart chỉ hỏi sổ này,
 * không so tên thuật toán. Thứ tự đăng ký (thứ tự <script> trong HTML) là thứ tự tạo series
 * trên chart và thứ tự gọi hook. Các khoá một plugin có thể khai báo (đều tuỳ chọn):
 *
 *   id               tên ngắn của plugin
 *   algorithms       [tên thuật toán Python plugin phụ trách] — dùng cho hook theo thuật toán
 *   fallback         true: nhận loại sự kiện không plugin nào nhận, và chạy sau cùng ở pick()
 *   layers           {lớp: bật mặc định} — trạng thái lớp hiển thị ở trang Thử nghiệm
 *   panels           [selector] chỉ hiện khi thuật toán đang chọn thuộc plugin (vd khung lớp riêng)
 *   layerHints       {thuật toán: câu gợi ý dưới khung lớp}
 *   labelTypes       [{id, label, sw, short}] — loại nhãn tay (trang Gán nhãn), theo thứ tự hiện
 *   labelPrice(type, bar)          giá mặc định cho nhãn loại `type`; undefined = quy tắc chung
 *   chart            hook vẽ trên MarketChart: init, clear, begin, ownsEvent(type, event), marker, finish, draw,
 *                    tooltipBar, tooltipEvent, onRangeChange (xem chart/market-chart.js)
 *   notes(stats, dataStatus, pending, S)    [[kind, html], …] ghi chú dưới banner; null = ẩn
 *   runWarning(res)                         html cảnh báo khi chạy xong (thay câu «không có sự kiện»)
 *   statsHtml(m, res) / afterStats(res)     khối chỉ số riêng ở tab Thống kê / gắn sự kiện cho khối đó
 *   pendingHtml(ps, digits)                 trạng thái nội bộ tại con trỏ replay; null = không phải của mình
 *   eventDetail(e, S)                       html panel chi tiết sự kiện được chọn; null = ẩn
 *   selectEventOnChart                      true: chọn dòng sự kiện thì vẽ lại chart (đánh dấu sự kiện chọn)
 *   explain(r, bar, S) / explainName        khung «Thuật toán đang làm gì» khi replay
 *   replayLayers     [lớp] bật sẵn khi «Replay từ vùng đang xem»
 *   baselineCompare  {pivotTypes:[a, b], label} — cho phép so với baseline swing_pivot 3/3
 *   syncLegend(timeline, events, S)         bật/tắt chú giải riêng dưới chart
 *   bindChart(chart)                        gắn callback lên chart chính của trang Thử nghiệm
 *   evalCrossMap     ánh xạ chấm chéo ở trang Đánh giá (xem algos/dc_atr.js)
 */
(function (MSL) {
  'use strict';

  var plugins = [];

  function register(plugin) {
    plugins.push(plugin);
    return plugin;
  }

  function list() { return plugins.slice(); }

  function get(id) {
    for (var i = 0; i < plugins.length; i++) if (plugins[i].id === id) return plugins[i];
    return null;
  }

  /** Plugin phụ trách thuật toán `name` (null nếu không có). */
  function forAlgorithm(name) {
    for (var i = 0; i < plugins.length; i++) {
      if ((plugins[i].algorithms || []).indexOf(name) !== -1) return plugins[i];
    }
    return null;
  }

  /** Gọi hook `hook` của plugin phụ trách `algorithm`; không có thì trả null. */
  function callFor(algorithm, hook) {
    var p = forAlgorithm(algorithm);
    if (!p || typeof p[hook] !== 'function') return null;
    return p[hook].apply(p, Array.prototype.slice.call(arguments, 2));
  }

  /** Plugin vẽ sự kiện loại `type` (plugin fallback nếu không ai nhận). `event` (tuỳ chọn) cho plugin
   * nhận theo thuật toán khi loại dùng chung (vd SWING_HIGH_L2 của swing_hierarchy và ict_structure). */
  function forEventType(type, event) {
    var fb = null;
    for (var i = 0; i < plugins.length; i++) {
      var c = plugins[i].chart;
      if (!c) continue;
      if (c.ownsEvent && c.ownsEvent(type, event)) return plugins[i];
      if (plugins[i].fallback && !fb) fb = plugins[i];
    }
    return fb;
  }

  /** Kết quả khác null đầu tiên của hook `hook` — plugin thường trước, plugin fallback sau. */
  function pick(hook) {
    var args = Array.prototype.slice.call(arguments, 1);
    var order = plugins.filter(function (p) { return !p.fallback; })
      .concat(plugins.filter(function (p) { return p.fallback; }));
    for (var i = 0; i < order.length; i++) {
      if (typeof order[i][hook] !== 'function') continue;
      var v = order[i][hook].apply(order[i], args);
      if (v !== null && v !== undefined) return v;
    }
    return null;
  }

  /** Gọi hook `hook` của mọi plugin có nó, theo thứ tự đăng ký. */
  function each(hook) {
    var args = Array.prototype.slice.call(arguments, 1);
    plugins.forEach(function (p) {
      if (typeof p[hook] === 'function') p[hook].apply(p, args);
    });
  }

  /** Trạng thái lớp mặc định gộp từ mọi plugin. */
  function defaultLayers() {
    var out = {};
    plugins.forEach(function (p) {
      var l = p.layers || {};
      Object.keys(l).forEach(function (k) { out[k] = l[k]; });
    });
    return out;
  }

  /** Loại nhãn tay gộp từ mọi plugin: [{id, label, sw, short}]. */
  function labelTypes() {
    var out = [];
    plugins.forEach(function (p) { out = out.concat(p.labelTypes || []); });
    return out;
  }

  /** Giá mặc định khi gán nhãn `type` ở nến `bar`: plugin quyết trước, rồi quy tắc chung (LOW/DOWN → low). */
  function labelPrice(type, bar) {
    for (var i = 0; i < plugins.length; i++) {
      if (typeof plugins[i].labelPrice !== 'function') continue;
      var v = plugins[i].labelPrice(type, bar);
      if (v !== undefined) return v;
    }
    if (String(type).indexOf('LOW') !== -1 || String(type).indexOf('DOWN') !== -1) return bar.low;
    return bar.high;
  }

  MSL.algos = {
    register: register,
    list: list,
    get: get,
    forAlgorithm: forAlgorithm,
    callFor: callFor,
    forEventType: forEventType,
    pick: pick,
    each: each,
    defaultLayers: defaultLayers,
    labelTypes: labelTypes,
    labelPrice: labelPrice
  };
})(window.MSL);
