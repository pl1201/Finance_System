/* Khung phụ dưới chart chính (window.SubPane) — chart Lightweight Charts thấp, CÙNG chuỗi nến với MarketChart: mỗi series
 * nhận đúng một phần tử cho mỗi nến của chart chính, cùng thứ tự (nến không có giá trị = khoảng trống {time}) → cùng chỉ số
 * logic, nên cuộn / zoom / crosshair đồng bộ theo chỉ số logic. Không biết thuật toán: nội dung do hook `pane` của plugin đổ
 * vào (hợp đồng ở đầu algos/registry.js; trang tạo khung và gọi hook qua chart/pane-host.js — trang Thử nghiệm, trang Live MT5).
 *
 * Giao diện chung MarketChart.baseOptions(); trục thời gian ẩn (chart chính đã có); trục giá không ghi số, rộng đúng bằng
 * trục giá chart chính để nến thẳng hàng (khung theo chart chính, không đổi tuỳ chọn của chart chính); thang dọc do series tự
 * khai (autoscaleInfoProvider của LWC — vd khung trạng thái cố định); kéo trục giá bị tắt (LWC sẽ tắt autoScale → mất thang
 * series đã khai).
 *
 *   new SubPane(container, {wrap})   wrap: phần tử ẩn / hiện cùng khung (mặc định container)
 *   addHistogram(key, opts)          tạo histogram series (opts = tuỳ chọn series LWC), trả series LWC
 *   draw(data, append)               data = {key: [một phần tử mỗi nến của chart chính]} — append: thêm vào cuối (replay tiến
 *                                    một nến), không thì thay cả chuỗi; key chưa tạo → bỏ qua
 *   reset()                          gỡ mọi series (đổi plugin vẽ khung / ẩn khung)
 *   linkWith(mc)                     đồng bộ hai chiều khoảng logic đang xem + crosshair với MarketChart `mc`
 *   onCrosshair(fn)                  fn(bar | null) — nến của chart chính dưới chuột (ở khung này hoặc ở chart chính); null
 *                                    khi rời chart / vùng không có nến
 *   setVisible(on)                   ẩn / hiện wrap; đang hiện → kích thước + khoảng nhìn + trục giá theo chart chính
 *   setAnchorRight(on)               zoom giữ mép phải (replay) — như MarketChart.setAnchorRight
 *
 * Đồng bộ: LWC 4.2.3 áp setVisibleLogicalRange ở khung hình sau và không cho biết khung nhìn đổi do chuột hay do dữ liệu →
 * bên «dẫn» theo con trỏ: đang bấm / lăn chuột trên khung này (và LEAD_MS sau khi thả) thì khung này đẩy khoảng nhìn sang
 * chart chính, còn lại chart chính dẫn — không vọng lại, không giật khi kéo; trang vẽ lại thì chart chính dẫn ngay. Crosshair:
 * khung → chart chính chỉ khi do chuột thật (MarketChart.byMouse), chart chính → khung cả lần LWC phát lại vị trí khi dữ liệu
 * / khung nhìn đổi (setCrosshairPosition của LWC 4.2.3 không phát sự kiện → không vòng lặp). Bỏ qua khi khung ẩn / chart
 * chính chưa có nến (MarketChart.canSync).
 */
(function (global) {
  'use strict';

  var LWC = global.LightweightCharts;
  var MC = global.MarketChart;
  var LEAD_MS = 250;   // sau khi thả / lăn chuột trên khung: khung vẫn dẫn (khoảng nhìn cuối áp ở khung hình sau)

  function SubPane(container, opts) {
    var self = this;
    this.container = container;
    this.wrap = (opts && opts.wrap) || container;
    this._series = {};
    this._first = null;
    this._main = null;
    this._onCross = null;
    this._leadUntil = 0;
    this._axisW = 0;

    this.chart = LWC.createChart(container, MC.baseOptions());
    this.chart.applyOptions({
      layout: { attributionLogo: false },   // logo TradingView đã có ở chart chính + liên kết ở chân trang
      grid: { horzLines: { visible: false } },
      rightPriceScale: { scaleMargins: { top: 0.03, bottom: 0.03 } },
      timeScale: { visible: false },
      crosshair: { vertLine: { labelVisible: false }, horzLine: { visible: false, labelVisible: false } },
      localization: { priceFormatter: function () { return ''; } },   // ý nghĩa ở dòng chú giải trên khung
      handleScroll: { vertTouchDrag: false },
      handleScale: { axisPressedMouseMove: { time: true, price: false } },
      kineticScroll: { mouse: false, touch: false }   // trôi quán tính = khung nhìn đổi khi đã thôi «dẫn»
    });

    this._resizeObs = new ResizeObserver(function () { self._resize(); });
    this._resizeObs.observe(container);
    this._resize();

    function soon() { return Date.now() + LEAD_MS; }
    function release() { if (self._leadUntil === Infinity) self._leadUntil = soon(); }
    container.addEventListener('pointerdown', function () { self._leadUntil = Infinity; });
    container.addEventListener('wheel', function () { self._leadUntil = Math.max(self._leadUntil, soon()); }, { passive: true });
    global.addEventListener('pointerup', release);
    global.addEventListener('pointercancel', release);
    global.addEventListener('blur', release);
    // Mất pointerup (thả chuột ngoài cửa sổ…): lần rê chuột kế tiếp không giữ nút nào → thôi «dẫn».
    global.addEventListener('pointermove', function (e) { if (!e.buttons) release(); }, { passive: true });

    // Chú giải theo mọi lần crosshair đổi; chỉ đẩy sang chart chính khi do chuột thật (lần phát lại không đẩy → hai chart
    // không đẩy qua lại kể cả với bản LWC có phát sự kiện cho setCrosshairPosition).
    this.chart.subscribeCrosshairMove(function (p) {
      var mc = self._main;
      self._emit(p);
      if (MC.byMouse(p) && mc && mc.canSync()) mc.crosshairAt(p && p.time);
    });
    this.chart.timeScale().subscribeVisibleLogicalRangeChange(function (r) {
      var mc = self._main;
      if (!r || self.wrap.hidden || !self._lead() || !mc || !mc.canSync()) return;
      try { mc.chart.timeScale().setVisibleLogicalRange(r); } catch (e) { /* series rỗng */ }
    });
  }

  /** Kích thước theo container; đang ẩn (0 × 0) thì bỏ qua (kích thước không đổi thì LWC tự bỏ qua). */
  SubPane.prototype._resize = function () {
    var w = this.container.clientWidth, h = this.container.clientHeight;
    if (w > 0 && h > 0) this.chart.applyOptions({ width: w, height: h });
  };

  /** Người dùng đang bấm giữ trên khung (Infinity) hoặc vừa thả / lăn chuột < LEAD_MS → khung này dẫn khoảng nhìn. */
  SubPane.prototype._lead = function () { return Date.now() < this._leadUntil; };

  SubPane.prototype.addHistogram = function (key, opts) {
    var s = this.chart.addHistogramSeries(Object.assign({ priceLineVisible: false, lastValueVisible: false }, opts));
    this._series[key] = s;
    if (!this._first) this._first = s;
    return s;
  };

  SubPane.prototype.draw = function (data, append) {
    for (var k in data) {
      var s = this._series[k];
      if (!s) continue;
      if (append) data[k].forEach(function (x) { s.update(x); });
      else s.setData(data[k]);
    }
  };

  SubPane.prototype.reset = function () {
    for (var k in this._series) this.chart.removeSeries(this._series[k]);
    this._series = {};
    this._first = null;
  };

  SubPane.prototype.onCrosshair = function (fn) { this._onCross = fn; };

  /** Báo nến của chart chính dưới crosshair `p` (của khung này hay của chart chính — cùng time). */
  SubPane.prototype._emit = function (p) {
    if (this._onCross) this._onCross(this._main ? this._main.barAtTime(p && p.time) : null);
  };

  SubPane.prototype.setVisible = function (on) {
    var was = !this.wrap.hidden;
    this.wrap.hidden = !on;
    if (!on) return;
    if (!was) this._resize();
    if (this._leadUntil !== Infinity) this._leadUntil = 0;   // trang vẽ lại → chart chính dẫn, trừ khi đang bấm giữ trên khung
    this._align();
  };

  SubPane.prototype.setAnchorRight = MC.prototype.setAnchorRight;   // cùng tuỳ chọn LWC trên this.chart

  /** Trục giá rộng đúng bằng trục giá chart chính — khung không ghi số nên tự nhiên hẹp hơn, minimumWidth kéo về đúng bề
   *  rộng đó (cả hai do LWC làm tròn lên số chẵn — cùng quy tắc). Chart chính chưa vẽ (0) → chờ lần đổi kích thước sau. */
  SubPane.prototype._matchAxis = function () {
    var w = this._main.chart.priceScale('right').width();
    if (!(w > 0) || w === this._axisW) return;
    this._axisW = w;
    this.chart.applyOptions({ rightPriceScale: { minimumWidth: w } });
  };

  /** Theo chart chính: bề rộng trục giá; khoảng logic đang xem — trừ khi người dùng đang kéo / lăn trên khung này. */
  SubPane.prototype._align = function () {
    var mc = this._main;
    if (!mc || this.wrap.hidden) return;
    this._matchAxis();
    if (!this._lead()) mc.copyRangeTo(this);
  };

  SubPane.prototype.linkWith = function (mc) {
    var self = this;
    this._main = mc;
    mc.chart.timeScale().subscribeVisibleLogicalRangeChange(function () { self._align(); });
    // Trục giá chart chính đổi bề rộng (nhãn giá dài hơn) → vùng vẽ hẹp lại: theo bề rộng mới để nến vẫn thẳng hàng.
    mc.chart.timeScale().subscribeSizeChange(function () { if (!self.wrap.hidden) self._matchAxis(); });
    // Chart chính → khung: cả lần LWC phát lại (nến dưới chuột đổi khi replay thêm nến / cuộn) để khung không lệch một nến.
    mc.chart.subscribeCrosshairMove(function (p) {
      var t = p ? p.time : undefined;
      self._emit(p);
      if (self.wrap.hidden || !self._first) return;
      try {
        if (t !== undefined) self.chart.setCrosshairPosition(0, t, self._first);
        else self.chart.clearCrosshairPosition();
      } catch (e) { /* thang giá chưa có giá trị trong khung nhìn (LWC: «Value is null») */ }
    });
    this._align();
  };

  global.SubPane = SubPane;
})(window);
