/* Lớp bọc TradingView Lightweight Charts cho Market Structure Lab (window.MarketChart).
 *
 * Quy ước hiển thị:
 *  - Marker pivot đặt tại NẾN CHỨA CẤU TRÚC (event_time). Ở chế độ replay, marker
 *    chỉ được đưa vào sau khi con trỏ replay đã vượt qua nến XÁC NHẬN.
 *  - Marker BOS đặt tại nến xác nhận vì BOS dùng close của chính nến đó.
 *  - Đường mức là chuỗi "mức đang hoạt động" do LÕI THUẬT TOÁN sinh ra (timeline_point),
 *    nên chúng cũng chỉ chứa thông tin đã khả dụng tại mỗi nến.
 *
 * Lõi chỉ biết nến, khung nhìn, marker chung và tooltip. Phần riêng từng thuật toán (series phụ,
 * marker, đường mức, dòng tooltip) nằm ở plugin algos/<tên>.js qua các hook `chart`:
 *   init(mc, st)              tạo series riêng; `st` là trạng thái riêng của plugin trên chart này
 *   clear(mc, st)             xoá dữ liệu series riêng (trước khi nạp bộ nến mới)
 *   begin(ctx, st)            đầu mỗi lần setEvents
 *   ownsEvent(type)           plugin vẽ loại sự kiện này
 *   marker(e, ctx, st)        một sự kiện đã xác nhận tại con trỏ → ctx.markers (theo thứ tự sự kiện)
 *   finish(ctx, st)           sau vòng sự kiện → ctx.head (marker đứng trước marker sự kiện)
 *   draw(ctx, st)             vẽ series riêng sau khi marker nến đã đặt
 *   tooltipBar(mc, bar, d, st) / tooltipEvent(e, d)   thêm dòng vào tooltip
 *   onRangeChange(mc, st)     khung nhìn đổi (cuộn / zoom)
 */
(function (global, MSL) {
  'use strict';

  var LWC = global.LightweightCharts;
  var fmtTime = MSL.format.fmtTime;
  var fmtIso = MSL.format.fmtIso;
  var isFiniteNum = MSL.format.isFiniteNum;

  var COLORS = {
    baseline: 'rgba(176,190,197,.9)'
  };

  /** Plugin có hook vẽ, theo thứ tự đăng ký (= thứ tự tạo series). */
  function chartPlugins() {
    return MSL.algos.list().filter(function (p) { return !!p.chart; });
  }

  function MarketChart(container, tooltipEl) {
    this.container = container;
    this.tooltipEl = tooltipEl;
    this.bars = [];
    this.events = [];
    this.timeline = [];
    this.digits = 2;

    this.chart = LWC.createChart(container, {
      layout: { background: { color: '#0f1419' }, textColor: '#9aa7b4', fontSize: 11 },
      grid: { vertLines: { color: '#1b232c' }, horzLines: { color: '#1b232c' } },
      rightPriceScale: { borderColor: '#2a3441' },
      timeScale: { borderColor: '#2a3441', timeVisible: true, secondsVisible: false, rightOffset: 6 },
      crosshair: { mode: LWC.CrosshairMode.Normal },
      localization: {
        locale: 'vi-VN',
        timeFormatter: function (t) { return fmtTime(t); }
      },
      handleScroll: true,
      handleScale: true
    });

    this.candles = this.chart.addCandlestickSeries({
      upColor: '#26a69a', downColor: '#ef5350',
      borderUpColor: '#26a69a', borderDownColor: '#ef5350',
      wickUpColor: '#26a69a', wickDownColor: '#ef5350'
    });

    // Series riêng của từng plugin (đường mức swing, CISD, DC, dải regime…).
    this._plugins = chartPlugins();
    this._st = {};
    for (var i = 0; i < this._plugins.length; i++) {
      var p = this._plugins[i];
      this._st[p.id] = {};
      if (p.chart.init) p.chart.init(this, this._st[p.id]);
    }

    var self = this;
    this._resizeObs = new ResizeObserver(function () {
      self.chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight
      });
    });
    this._resizeObs.observe(container);
    this.chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });

    this.chart.subscribeCrosshairMove(function (param) { self._onCrosshair(param); });
    this._compact = false;
    this.chart.timeScale().subscribeVisibleLogicalRangeChange(function () { self._onRangeChange(); });
    this.chart.subscribeClick(function (param) {
      if (!self._onBarClick || !param || param.time === undefined) return;
      var bar = self._barByTime && self._barByTime[param.time];
      var src = param.sourceEvent || {};
      if (bar) self._onBarClick(bar, { shift: !!src.shiftKey, point: param.point || null });
    });
  }

  /** Gọi hook `name` của mọi plugin vẽ: fn(plugin.chart, trạng thái riêng). */
  MarketChart.prototype._eachPlugin = function (name, fn) {
    for (var i = 0; i < this._plugins.length; i++) {
      var p = this._plugins[i];
      if (p.chart[name]) fn(p.chart, this._st[p.id]);
    }
  };

  /** fn(bar, { shift, point }) — `shift` là trạng thái phím Shift lúc click. */
  MarketChart.prototype.setBarClickHandler = function (fn) { this._onBarClick = fn; };

  /** Gọi fn() mỗi khi khung nhìn đổi (cuộn / zoom / đổi kích thước). */
  MarketChart.prototype.onViewChange = function (fn) {
    this.chart.timeScale().subscribeVisibleLogicalRangeChange(function () { fn(); });
    this.chart.timeScale().subscribeSizeChange(function () { fn(); });
  };

  /**
   * Toạ độ điểm ảnh của nến `idx` trong khung chart: { x, yHigh, yLow }.
   * Trả null nếu nến không có hoặc đang nằm ngoài khung nhìn.
   */
  MarketChart.prototype.barCoords = function (idx) {
    var b = null;
    for (var i = 0; i < this.bars.length; i++) if (this.bars[i].index === idx) { b = this.bars[i]; break; }
    if (!b) return null;
    var x = this.chart.timeScale().timeToCoordinate(b.time);
    var yH = this.candles.priceToCoordinate(b.high);
    var yL = this.candles.priceToCoordinate(b.low);
    if (x === null || yH === null || yL === null) return null;
    if (x < 0 || x > this.container.clientWidth) return null;
    return { x: x, yHigh: yH, yLow: yL };
  };

  /** Tắt tooltip khi đang mở bảng thao tác, để hai khung không đè nhau. */
  MarketChart.prototype.setTooltipSuppressed = function (on) {
    this._ttOff = !!on;
    if (on && this.tooltipEl) this.tooltipEl.hidden = true;
  };

  MarketChart.prototype.setDigits = function (d) { this.digits = d; };

  /**
   * Xoá mọi lớp phủ (series của plugin, marker). Gọi TRƯỚC khi nạp bộ nến mới:
   * lớp phủ cũ mang mốc thời gian của bộ nến trước — LWC 4.2.3 đánh lại chỉ số trục thời gian theo
   * cả hai bộ mốc rồi vẽ nến lỗi «Value is null» (gặp khi đổi dataset sau một lần chạy).
   */
  MarketChart.prototype._clearOverlays = function () {
    var self = this;
    this._eachPlugin('clear', function (c, st) { c.clear(self, st); });
    this.candles.setMarkers([]);
  };

  /** Nạp nến. `bars` là mảng {time, open, high, low, close, index}. Lớp phủ cũ bị xoá — người gọi
   * dựng lại bằng setEvents. */
  MarketChart.prototype.setBars = function (bars) {
    this._clearOverlays();
    this.bars = bars || [];
    this._barByTime = {};
    this._posByTime = {};
    var data = [];
    for (var i = 0; i < this.bars.length; i++) {
      var b = this.bars[i];
      this._barByTime[b.time] = b;
      this._posByTime[b.time] = i;
      data.push({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
    }
    this.candles.setData(data);
    this._dataChangedAt = Date.now();
  };

  /** Thêm một nến vào cuối (dùng khi replay tiến từng nến, tránh vẽ lại toàn bộ). */
  MarketChart.prototype.appendBar = function (b) {
    this.bars.push(b);
    this._barByTime[b.time] = b;
    if (this._posByTime) this._posByTime[b.time] = this.bars.length - 1;
    this.candles.update({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
    this._dataChangedAt = Date.now();
  };

  MarketChart.prototype.fit = function () {
    try { this.chart.timeScale().fitContent(); } catch (e) { /* series rỗng: bỏ qua */ }
  };

  MarketChart.prototype._setVisibleSpan = function (fromIdx, toIdx) {
    if (!this.bars.length) return;
    var a = Math.max(0, fromIdx);
    var b = Math.min(this.bars.length - 1, toIdx);
    if (b < a) return;
    var ts = this.chart.timeScale();
    try {
      ts.setVisibleLogicalRange({ from: a, to: b });
    } catch (e) {
      try {
        ts.setVisibleRange({ from: this.bars[a].time, to: this.bars[b].time });
      } catch (e2) {
        this.fit();
      }
    }
  };

  /** Replay: ít nến thì bung full chart; nhiều nến thì neo 120 nến cuối. */
  MarketChart.prototype.followReplay = function () {
    if (!this.bars.length) return;
    if (this.bars.length < 80) { this.fit(); return; }
    this.showLast(Math.min(120, this.bars.length));
  };

  /** Hiển thị `n` nến cuối. Zoom-out toàn bộ vài nghìn nến làm marker chồng lên nhau. */
  MarketChart.prototype.showLast = function (n) {
    if (!this.bars.length) return;
    if (this.bars.length <= n) { this.fit(); return; }
    this._setVisibleSpan(this.bars.length - n, this.bars.length - 1);
  };

  /** Khoảng nến (theo `bar.index` của dataset) đang nằm trong khung nhìn. */
  MarketChart.prototype.visibleIndexRange = function () {
    if (!this.bars.length) return null;
    var r = null;
    try { r = this.chart.timeScale().getVisibleLogicalRange(); } catch (e) { r = null; }
    if (!r) return { start: this.bars[0].index, end: this.bars[this.bars.length - 1].index };
    var a = Math.max(0, Math.min(this.bars.length - 1, Math.ceil(r.from)));
    var b = Math.max(0, Math.min(this.bars.length - 1, Math.floor(r.to)));
    if (b < a) { var t = a; a = b; b = t; }
    return { start: this.bars[a].index, end: this.bars[b].index };
  };

  /** Đưa nến `idx` vào giữa khung nhìn (dùng khi duyệt từng đề xuất). */
  MarketChart.prototype.centerOnIndex = function (idx, half) {
    if (!this.bars.length) return;
    var h = half || 45;
    var pos = -1;
    for (var i = 0; i < this.bars.length; i++) {
      if (this.bars[i].index === idx) { pos = i; break; }
    }
    if (pos < 0) return;
    this._setVisibleSpan(pos - h, pos + h);
  };

  MarketChart.prototype.scrollToIndex = function (idx) {
    if (!this.bars.length) return;
    var i = Math.max(0, Math.min(idx, this.bars.length - 1));
    this._setVisibleSpan(Math.max(0, i - 120), i);
  };

  MarketChart.prototype.focusEvent = function (ev) {
    var t = null;
    for (var i = 0; i < this.bars.length; i++) {
      if (this.bars[i].index === ev.event_bar_index) { t = i; break; }
    }
    if (t === null) return;
    this._setVisibleSpan(Math.max(0, t - 70), Math.min(this.bars.length - 1, t + 70));
  };

  /**
   * Cập nhật marker và lớp phủ của plugin.
   * opts = { layers: {lớp: bật}, markerAtConfirm: bool, replayCursor: int|null,
   *          baselineEvents: [sự kiện run baseline], selectedEventId }
   */
  MarketChart.prototype.setEvents = function (events, timeline, opts) {
    opts = opts || {};
    var layers = opts.layers || {};
    var cursor = (opts.replayCursor === undefined || opts.replayCursor === null) ? Infinity : opts.replayCursor;
    this.events = events || [];
    this.timeline = timeline || [];

    var timeByIndex = {};
    for (var i = 0; i < this.bars.length; i++) timeByIndex[this.bars[i].index] = this.bars[i].time;

    // --- gom sự kiện theo nến để tooltip tra cứu nhanh ---
    this.eventsAtBar = {};
    var self = this;
    function push(map, key, val) { (map[key] = map[key] || []).push(val); }

    var ctx = {
      chart: this, layers: layers, opts: opts, cursor: cursor, timeline: this.timeline,
      timeByIndex: timeByIndex, selectedId: opts.selectedEventId || null,
      head: [],      // marker đứng đầu (pivot gom theo nến)
      markers: []    // marker theo thứ tự sự kiện
    };
    this._eachPlugin('begin', function (c, st) { c.begin(ctx, st); });

    for (var k = 0; k < this.events.length; k++) {
      var e = this.events[k];
      if (e.confirmed_bar_index > cursor) continue;   // chưa xác nhận tại thời điểm replay
      push(this.eventsAtBar, e.event_bar_index, e);
      if (e.confirmed_bar_index !== e.event_bar_index) push(this.eventsAtBar, e.confirmed_bar_index, e);
      var p = MSL.algos.forEventType(e.structure_type);
      if (p && p.chart.marker) p.chart.marker(e, ctx, this._st[p.id]);
    }
    this._eachPlugin('finish', function (c, st) { c.finish(ctx, st); });

    // Baseline so sánh (pivot wick của một run khác) — cùng quy tắc lúc biết.
    var baseEvs = opts.baselineEvents || [];
    if (layers.baseline) {
      for (var bi = 0; bi < baseEvs.length; bi++) {
        var be = baseEvs[bi];
        if (be.confirmed_bar_index > cursor) continue;
        if (be.structure_type !== 'SWING_HIGH' && be.structure_type !== 'SWING_LOW') continue;
        var bHigh = be.structure_type === 'SWING_HIGH';
        ctx.markers.push({
          time: timeByIndex[be.event_bar_index], position: bHigh ? 'aboveBar' : 'belowBar',
          color: COLORS.baseline, shape: bHigh ? 'arrowDown' : 'arrowUp', text: 'B', size: 0.7
        });
        push(this.eventsAtBar, be.event_bar_index, Object.assign({}, be, { _baseline: true }));
      }
    }

    var markers = ctx.head.concat(ctx.markers).filter(function (m) {
      return m.time != null && isFiniteNum(m.time);
    });
    markers.sort(function (a, b) { return a.time - b.time; });
    this.candles.setMarkers(markers);

    this._eachPlugin('draw', function (c, st) { c.draw(ctx, st); });
  };

  MarketChart.prototype.isCompact = function () { return this._compact; };

  MarketChart.prototype._onRangeChange = function () {
    var self = this;
    this._eachPlugin('onRangeChange', function (c, st) { c.onRangeChange(self, st); });
  };

  /** fn(compact) — gọi khi chế độ ẩn chữ nhãn đổi do zoom. */
  MarketChart.prototype.onCompactChange = function (fn) { this._onCompactChange = fn; };

  /**
   * Liên kết hai chart có CÙNG chuỗi nến: cuộn/zoom (theo logical range) và
   * crosshair đi theo nhau. Chỉ truyền sự kiện do chuột người dùng (sourceEvent)
   * để tránh vòng lặp; chart bị ẩn thì bỏ qua.
   */
  MarketChart.prototype.linkWith = function (other) {
    var a = this, b = other, busy = false;
    [a, b].forEach(function (c) {
      c._linked = true;
      c.chart.applyOptions({ rightPriceScale: { minimumWidth: 84 } });
    });
    function visible(c) { return c.container.offsetParent !== null && c.bars.length > 0; }
    function linkRange(src, dst, muteAfterData) {
      src.chart.timeScale().subscribeVisibleLogicalRangeChange(function (r) {
        if (busy || !r || !visible(src) || !visible(dst)) return;
        // Chart phụ vừa nạp nến: khung nhìn đổi do thư viện chứ không do người dùng —
        // không đẩy ngược về chart chính (app đồng bộ tường minh bằng copyRangeTo).
        if (muteAfterData && Date.now() - (src._dataChangedAt || 0) < 300) return;
        busy = true;
        try { dst.chart.timeScale().setVisibleLogicalRange(r); } catch (e) { /* series rỗng */ }
        busy = false;
      });
    }
    function linkCross(src, dst) {
      src.chart.subscribeCrosshairMove(function (p) {
        if (busy || !visible(dst)) return;
        if (p && p.time !== undefined && !p.sourceEvent) return;   // do chương trình, không phải chuột
        busy = true;
        try {
          var bar = p && p.time !== undefined && dst._barByTime ? dst._barByTime[p.time] : null;
          if (bar) dst.chart.setCrosshairPosition(bar.close, p.time, dst.candles);
          else dst.chart.clearCrosshairPosition();
        } catch (e) { /* bản LWC không hỗ trợ: bỏ đồng bộ crosshair */ }
        busy = false;
      });
    }
    linkRange(a, b, false); linkRange(b, a, true);   // `this` là chart dẫn
    linkCross(a, b); linkCross(b, a);
  };

  /**
   * Panel thấp: giảm lề trục giá và cỡ marker để nến không bị ép (autoscale của
   * LWC chừa chỗ cho marker theo pixel, chiếm tỉ lệ lớn khi panel thấp).
   */
  MarketChart.prototype.setCompactPane = function () {
    this._markerScale = 0.6;
    this.chart.applyOptions({ rightPriceScale: { scaleMargins: { top: 0.06, bottom: 0.04 } } });
  };

  /** Đặt khung nhìn của `other` bằng khung nhìn hiện tại của chart này. */
  MarketChart.prototype.copyRangeTo = function (other) {
    var r = null;
    try { r = this.chart.timeScale().getVisibleLogicalRange(); } catch (e) { r = null; }
    if (r) { try { other.chart.timeScale().setVisibleLogicalRange(r); } catch (e) { /* rỗng */ } }
  };

  MarketChart.prototype._onCrosshair = function (param) {
    var tt = this.tooltipEl;
    if (!tt) return;
    if (this._ttOff) { tt.hidden = true; return; }
    if (this._linked && param && !param.sourceEvent) { tt.hidden = true; return; }   // crosshair do chart kia đẩy sang
    if (!param || !param.time || !param.point || param.point.x < 0 || param.point.y < 0) {
      tt.hidden = true;
      return;
    }
    var bar = this._barByTime && this._barByTime[param.time];
    if (!bar) { tt.hidden = true; return; }

    var self = this;
    var d = this.digits;
    var html = '<div class="tt-time">Nến #' + bar.index + ' · ' + fmtTime(bar.time) + '</div>';
    html += '<div class="tt-ohlc">O ' + bar.open.toFixed(d) + '  H ' + bar.high.toFixed(d) +
            '  L ' + bar.low.toFixed(d) + '  C ' + bar.close.toFixed(d) + '</div>';
    html += '<div class="tt-rule">Đóng nến lúc: ' + fmtIso(bar.close_time) + '</div>';
    this._eachPlugin('tooltipBar', function (c, st) { html += c.tooltipBar(self, bar, d, st); });

    var list = (this.eventsAtBar && this.eventsAtBar[bar.index]) || [];
    for (var i = 0; i < list.length && i < 6; i++) {
      var e = list[i];
      var role = e._baseline
        ? 'Baseline pivot 3/3 theo WICK (run so sánh), không phải DC'
        : (e.event_bar_index === bar.index)
        ? 'Sự kiện tại nến này'
        : 'Được XÁC NHẬN tại nến này';
      var extra = '';
      this._eachPlugin('tooltipEvent', function (c) { extra += c.tooltipEvent(e, d); });
      html += '<div class="tt-ev"><b>' + e.structure_type + '</b> — ' + (e.structure_text_vi || '') +
              '<br>Giá: <span class="mono">' + Number(e.price).toFixed(d) + '</span>' +
              (e.no_confirm ? '' :
                '<br>' + role +
                '<br>Nến sự kiện: #' + e.event_bar_index + ' (' + fmtIso(e.event_time) + ')' +
                '<br>Xác nhận lúc: ' + fmtIso(e.confirmed_at) + ' — trễ ' + e.confirmation_lag_bars + ' nến') +
              extra +
              '<div class="tt-rule">' + (e.reason_text_vi || e.reason_code) + '</div></div>';
    }
    if (list.length > 6) html += '<div class="tt-rule">… và ' + (list.length - 6) + ' sự kiện khác.</div>';

    tt.innerHTML = html;
    tt.hidden = false;
    var w = tt.offsetWidth, h = tt.offsetHeight;
    var cw = this.container.clientWidth, ch = this.container.clientHeight;
    var x = param.point.x + 16, y = param.point.y + 16;
    if (x + w > cw) x = param.point.x - w - 16;
    if (y + h > ch) y = Math.max(4, ch - h - 4);
    tt.style.left = x + 'px';
    tt.style.top = y + 'px';
  };

  MarketChart.prototype.screenshot = function () {
    return this.chart.takeScreenshot();
  };

  global.MarketChart = MarketChart;
})(window, window.MSL);
