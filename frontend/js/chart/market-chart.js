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
 *   init(mc, st)              tạo series riêng / gắn primitive (chart/primitives.js) bằng mc.attachPrimitive; `st` là
 *                             trạng thái riêng của plugin trên chart này
 *   clear(mc, st)             xoá dữ liệu series riêng (trước khi nạp bộ nến mới)
 *   begin(ctx, st)            đầu mỗi lần setEvents
 *   ownsEvent(type, event)    plugin vẽ sự kiện này (theo loại; hoặc theo thuật toán khi loại dùng chung)
 *   marker(e, ctx, st)        một sự kiện đã xác nhận tại con trỏ → ctx.markers (theo thứ tự sự kiện)
 *   finish(ctx, st)           sau vòng sự kiện → ctx.head (marker đứng trước marker sự kiện)
 *   draw(ctx, st)             vẽ series riêng sau khi marker nến đã đặt
 *   tooltipBar(mc, bar, d, st) / tooltipEvent(e, d)   thêm dòng vào tooltip
 *   tooltipObject(mc, id, bar, d, st)   chuột đang trúng đối tượng `id` của một primitive (hitTest của primitive gắn
 *                             bằng attachPrimitive; không có thì crosshair `hoveredObjectId`): html giải thích đối tượng
 *                             đó — khác '' thì tooltip chỉ hiện khối này (kèm giờ nến nếu có), kể cả ở vùng tương lai
 *                             bên phải nến cuối; '' = không phải của mình
 *   onCrosshair(mc, bar, st)  mỗi lần crosshair đổi: `bar` = nến dưới chuột (null khi rời chart / vùng không có nến)
 *                             — vd dòng trạng thái theo nến đang rê
 *   onRangeChange(mc, st)     khung nhìn đổi (cuộn / zoom)
 * ctx (setEvents) = { chart, layers, opts, cursor (Infinity khi xem toàn lịch sử), timeline, events, pendingState
 *   (opts.pendingState — trạng thái nội bộ lõi tại con trỏ: nến cuối của lần chạy hoặc con trỏ replay), timeByIndex,
 *   selectedId, head, markers }.
 * logicalOf(index) đổi chỉ số nến sang chỉ số logic của LWC cho primitive (vượt nến cuối = vùng tương lai).
 * Chart liên kết (linkWith, khung phụ chart/sub-pane.js): barAtTime(t), crosshairAt(t), canSync(), copyRangeTo(other);
 *   MarketChart.byMouse(p) — crosshair do chuột thật (chỉ khi đó mới đẩy sang chart kia); giao diện chung
 *   MarketChart.baseOptions().
 * attachPrimitive(p) gắn primitive lên series nến VÀ đăng ký để tooltip tự gọi p.hitTest(x, y) đúng vị trí chuột hiện
 *   tại (LWC 4.2 chỉ cập nhật `hoveredObjectId` SAU khi phát crosshair → trễ một nhịp chuột); primitive gắn thẳng vào
 *   series vẫn dùng được qua `hoveredObjectId`.
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

  /** Giao diện chung của chart trong lab (nền, lưới, chữ, trục, crosshair, giờ UTC) — MarketChart và khung phụ dưới chart
   *  (chart/sub-pane.js) dùng cùng bộ này. */
  function baseOptions() {
    return {
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
    };
  }
  /** Crosshair do chuột thật: di chuột (sourceEvent) hoặc rời chart (LWC 4.2.3 phát không có point) — không phải lần LWC
   *  phát lại vị trí cũ khi dữ liệu / khung nhìn đổi (có point, không sourceEvent; time trống nếu chỗ đó không có nến).
   *  Chart liên kết chỉ đẩy crosshair sang chart kia khi đúng (không vòng lặp, không xoá nhầm crosshair của chart kia). */
  function byMouse(p) { return !p || !!p.sourceEvent || p.point === undefined; }

  function MarketChart(container, tooltipEl) {
    this.container = container;
    this.tooltipEl = tooltipEl;
    this.bars = [];
    this._posByIndex = {};
    this._prims = [];
    this.events = [];
    this.timeline = [];
    this.digits = 2;

    this.chart = LWC.createChart(container, baseOptions());

    this.candles = this.chart.addCandlestickSeries({
      upColor: '#26a69a', downColor: '#ef5350',
      borderUpColor: '#26a69a', borderDownColor: '#ef5350',
      wickUpColor: '#26a69a', wickDownColor: '#ef5350'
    });

    // Series riêng của từng plugin (đường mức swing, DC, dải regime…).
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
      var bar = self.barAtTime(param.time);
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
   * dựng lại bằng setEvents. `opts.keepPriceScale` (replay lùi / tua trong cùng phiên): giữ khung giá người dùng
   * đang chỉnh. Độ rộng nến (zoom ngang) luôn giữ nguyên — LWC không đổi khi thay dữ liệu. */
  MarketChart.prototype.setBars = function (bars, opts) {
    this._clearOverlays();
    this.bars = bars || [];
    this._barByTime = {};
    this._posByTime = {};
    this._posByIndex = {};
    var data = [];
    for (var i = 0; i < this.bars.length; i++) {
      var b = this.bars[i];
      this._barByTime[b.time] = b;
      this._posByTime[b.time] = i;
      this._posByIndex[b.index] = i;
      data.push({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
    }
    this.candles.setData(data);
    this._snapIfNoBarInView();
    if (opts && opts.keepPriceScale) {
      this._ensureLastBarPriceInView();
    } else {
      // Dữ liệu mới thay toàn bộ → bật lại tự co giãn trục giá. Kéo / zoom trục giá tay làm LWC tắt autoScale; nếu giữ khung
      // giá cũ (vd 4200–4600 cuối kỳ) khi vào replay từ đầu khoảng (giá ~1970), mọi nến nằm ngoài màn hình, chart như trống.
      try { this.candles.priceScale().applyOptions({ autoScale: true }); } catch (e) { /* chưa có thang giá: bỏ qua */ }
    }
    this._dataChangedAt = Date.now();
  };

  /** Thêm một nến vào cuối (replay tiến từng nến, tránh vẽ lại toàn bộ). Không đổi zoom: nến cuối đang trong khung nhìn
   * thì LWC tự cuộn theo nến mới (shiftVisibleRangeOnNewBar); đang xem lùi về quá khứ thì khung nhìn đứng yên. */
  MarketChart.prototype.appendBar = function (b) {
    this.bars.push(b);
    this._barByTime[b.time] = b;
    if (this._posByTime) this._posByTime[b.time] = this.bars.length - 1;
    if (this._posByIndex) this._posByIndex[b.index] = this.bars.length - 1;
    this.candles.update({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
    this._snapIfNoBarInView();
    this._dataChangedAt = Date.now();
  };

  /** Khung nhìn không còn nến nào (vd vừa vào replay từ giữa lịch sử: dữ liệu ngắn lại, LWC giữ khoảng lệch phải cũ) →
   * đưa nến cuối về mép phải, giữ nguyên độ rộng nến. */
  MarketChart.prototype._snapIfNoBarInView = function () {
    var n = this.bars.length;
    if (!n) return;
    var ts = this.chart.timeScale();
    try {
      var r = ts.getVisibleLogicalRange();
      if (r && r.to >= 0 && r.from <= n - 1) return;
      ts.scrollToPosition(ts.options().rightOffset, false);
    } catch (e) { /* chưa có khung nhìn: bỏ qua */ }
  };

  /** Nến cuối nằm ngoài khung nhìn → cuộn để nó ở mép phải, giữ nguyên độ rộng nến (replay: tua, tới xác nhận kế tiếp). */
  MarketChart.prototype.revealLastBar = function () {
    var n = this.bars.length;
    if (!n) return;
    var ts = this.chart.timeScale();
    try {
      var x = ts.logicalToCoordinate(n - 1);
      if (x !== null && x >= 0 && x <= this.container.clientWidth) return;
      ts.scrollToPosition(ts.options().rightOffset, false);
    } catch (e) { /* chưa có khung nhìn: bỏ qua */ }
  };

  /** Zoom bằng con lăn / pinch giữ mép phải đứng yên (replay: nến mới luôn ở mép phải như Bar Replay của TradingView);
   * tắt = zoom quanh vị trí chuột (mặc định LWC). */
  MarketChart.prototype.setAnchorRight = function (on) {
    this.chart.applyOptions({ timeScale: { rightBarStaysOnScroll: !!on } });
  };

  /** Giữ khung giá người dùng đang chỉnh, trừ khi nến cuối nằm hẳn ngoài khung (chart trông như trống) → bật autoScale. */
  MarketChart.prototype._ensureLastBarPriceInView = function () {
    var n = this.bars.length;
    if (!n) return;
    try {
      var ps = this.candles.priceScale();
      if (ps.options().autoScale) return;
      var last = this.bars[n - 1];
      var yH = this.candles.priceToCoordinate(last.high), yL = this.candles.priceToCoordinate(last.low);
      var paneH = this.container.clientHeight - this.chart.timeScale().height();
      if (yH === null || yL === null || yL < 0 || yH > paneH) ps.applyOptions({ autoScale: true });
    } catch (e) { /* chưa có thang giá: bỏ qua */ }
  };

  /** Gắn primitive (chart/primitives.js) lên series nến; tooltip hitTest trực tiếp các primitive đã đăng ký. */
  MarketChart.prototype.attachPrimitive = function (p) {
    this.candles.attachPrimitive(p);
    this._prims.push(p);
    return p;
  };

  /** id đối tượng primitive dưới điểm `point` (toạ độ pane) — primitive gắn sau (vẽ trên) được hỏi trước. */
  MarketChart.prototype._hitObject = function (point) {
    for (var i = this._prims.length - 1; i >= 0; i--) {
      var p = this._prims[i];
      if (typeof p.hitTest !== 'function') continue;
      var h = p.hitTest(point.x, point.y);
      if (h && h.externalId !== undefined && h.externalId !== null) return h.externalId;
    }
    return null;
  };

  /**
   * Chỉ số logic LWC của nến có `bar.index` = `idx` (vị trí trong dữ liệu đã nạp) — cho primitive vẽ theo nến.
   * Sau nến cuối / trước nến đầu → ngoại suy (vùng tương lai bên phải, «con trỏ + N nến»); số lẻ → nội suy
   * (vd idx − 0.45 = mép trái nến). null khi chưa có nến.
   */
  MarketChart.prototype.logicalOf = function (idx) {
    var n = this.bars.length;
    if (!n || typeof idx !== 'number' || !isFinite(idx)) return null;
    var k = Math.floor(idx), frac = idx - k;
    var first = this.bars[0].index, last = this.bars[n - 1].index;
    if (k >= last) return n - 1 + (k - last) + frac;
    if (k <= first) return k - first + frac;
    var pos = this._posByIndex ? this._posByIndex[k] : undefined;
    if (pos === undefined) {   // chỉ số không có trong dữ liệu đã nạp → nến gần nhất phía trước
      var lo = 0, hi = n - 1;
      while (lo < hi) { var mid = (lo + hi + 1) >> 1; if (this.bars[mid].index <= k) lo = mid; else hi = mid - 1; }
      pos = lo;
    }
    return pos + frac;
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
      chart: this, layers: layers, opts: opts, cursor: cursor, timeline: this.timeline, events: this.events,
      pendingState: opts.pendingState || null,
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
      var p = MSL.algos.forEventType(e.structure_type, e);
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
    function linkRange(src, dst, muteAfterData) {
      src.chart.timeScale().subscribeVisibleLogicalRangeChange(function (r) {
        if (busy || !r || !src.canSync() || !dst.canSync()) return;
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
        if (busy || !dst.canSync() || !byMouse(p)) return;   // lần phát lại do chương trình, không phải chuột
        busy = true;
        dst.crosshairAt(p && p.time);
        busy = false;
      });
    }
    linkRange(a, b, false); linkRange(b, a, true);   // `this` là chart dẫn
    linkCross(a, b); linkCross(b, a);
  };

  /** Nến có time `t` trong dữ liệu đã nạp, null nếu không có. */
  MarketChart.prototype.barAtTime = function (t) { return (this._barByTime && this._barByTime[t]) || null; };

  /** Đang hiện và đã có nến — chart liên kết (linkWith, khung phụ) chỉ đồng bộ sang chart này khi đúng. */
  MarketChart.prototype.canSync = function () { return this.container.offsetParent !== null && this.bars.length > 0; };

  /** Crosshair do chart liên kết đẩy sang (linkWith, khung phụ chart/sub-pane.js): tại close của nến có time `t`; không có
   *  nến (kể cả t null / undefined) → xoá. Tới khi chuột thật vào chart này, tooltip không hiện cho lần LWC phát lại vị trí
   *  đó (_onCrosshair). */
  MarketChart.prototype.crosshairAt = function (t) {
    var bar = this.barAtTime(t);
    this._crossByLink = true;
    try {
      if (bar) this.chart.setCrosshairPosition(bar.close, t, this.candles);
      else this.chart.clearCrosshairPosition();
    } catch (e) { /* bản LWC không hỗ trợ: bỏ đồng bộ crosshair */ }
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
    var self = this;
    var bar = this.barAtTime(param && param.time);
    if (param && param.sourceEvent) this._crossByLink = false;   // chuột thật trên chart này
    this._eachPlugin('onCrosshair', function (c, st) { c.onCrosshair(self, bar, st); });
    var tt = this.tooltipEl;
    if (!tt) return;
    if (this._ttOff) { tt.hidden = true; return; }
    // crosshair do chart kia đẩy sang (crosshairAt) / LWC phát lại vị trí đó khi dữ liệu, khung nhìn đổi — không sourceEvent
    if ((this._linked || this._crossByLink) && param && !param.sourceEvent) { tt.hidden = true; return; }
    if (!param || !param.point || param.point.x < 0 || param.point.y < 0) {
      tt.hidden = true;
      return;
    }
    var d = this.digits;
    // Chuột trúng đối tượng của một primitive (đường vùng, hộp, dải…): tooltip giải thích chính đối tượng đó.
    var obj = '', oid = this._prims.length ? this._hitObject(param.point) : param.hoveredObjectId;
    if (oid !== undefined && oid !== null) {
      this._eachPlugin('tooltipObject', function (c, st) { if (!obj) obj = c.tooltipObject(self, oid, bar, d, st) || ''; });
    }
    if (!bar && !obj) { tt.hidden = true; return; }

    var html;
    if (obj) {
      html = (bar ? '<div class="tt-time">Nến #' + bar.index + ' · ' + fmtTime(bar.time) + '</div>' : '') +
        '<div class="tt-obj">' + obj + '</div>';
      this._showTooltip(html, param.point);
      return;
    }
    html = '<div class="tt-time">Nến #' + bar.index + ' · ' + fmtTime(bar.time) + '</div>';
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
    this._showTooltip(html, param.point);
  };

  MarketChart.prototype._showTooltip = function (html, point) {
    var tt = this.tooltipEl;
    tt.innerHTML = html;
    tt.hidden = false;
    var w = tt.offsetWidth, h = tt.offsetHeight;
    var cw = this.container.clientWidth, ch = this.container.clientHeight;
    var x = point.x + 16, y = point.y + 16;
    if (x + w > cw) x = point.x - w - 16;
    if (y + h > ch) y = Math.max(4, ch - h - 4);
    tt.style.left = x + 'px';
    tt.style.top = y + 'px';
  };

  MarketChart.prototype.screenshot = function () {
    return this.chart.takeScreenshot();
  };

  MarketChart.baseOptions = baseOptions;
  MarketChart.byMouse = byMouse;
  global.MarketChart = MarketChart;
})(window, window.MSL);
