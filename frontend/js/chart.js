/* Lớp bọc TradingView Lightweight Charts cho Market Structure Lab.
 *
 * Quy ước hiển thị:
 *  - Marker pivot đặt tại NẾN CHỨA CẤU TRÚC (event_time). Ở chế độ replay, marker
 *    chỉ được đưa vào sau khi con trỏ replay đã vượt qua nến XÁC NHẬN.
 *  - Marker BOS đặt tại nến xác nhận vì BOS dùng close của chính nến đó.
 *  - Hai đường mức swing là chuỗi "mức đang hoạt động" do LÕI THUẬT TOÁN sinh ra
 *    (timeline_point), nên chúng cũng chỉ chứa thông tin đã khả dụng tại mỗi nến.
 */
(function (global) {
  'use strict';

  var LWC = global.LightweightCharts;

  var COLORS = {
    swingHigh: '#ffb74d',
    swingLow: '#4dd0e1',
    swingHighL2: '#ffe082',
    swingLowL2: '#80deea',
    hhll: '#ba68c8',
    eq: '#b0bec5',
    bosUp: '#66bb6a',
    bosDown: '#ef5350',
    chochUp: '#26c6da',
    chochDown: '#ff7043',
    bosIntUp: '#9ccc65',
    bosIntDown: '#ef9a9a',
    levelHigh: 'rgba(255,183,77,.55)',
    levelLow: 'rgba(77,208,225,.55)',
    // c2_cisd_research
    c2Up: '#00e676',
    c2Down: '#ff5252',
    cisdUp: '#69f0ae',
    cisdDown: '#ff8a80',
    earlyUp: 'rgba(105,240,174,.7)',
    earlyDown: 'rgba(255,138,128,.7)',
    trackUp: 'rgba(105,240,174,.35)',
    trackDown: 'rgba(255,138,128,.35)',
    extreme: 'rgba(255,213,79,.6)',
    dead: '#e53935',
    c4inv: '#ffa726',
    ended: '#90a4ae',
    dataq: '#607d8b',
    // dc_atr_structure
    dcLine: 'rgba(236,239,241,.85)',
    dcCand: 'rgba(236,239,241,.55)',
    dcHigh: '#ff8a65',
    dcLow: '#64b5f6',
    dcConfirm: '#fff176',
    dcLevel: 'rgba(255,241,118,.8)',
    rangeLine: 'rgba(251,192,45,.85)',
    baseline: 'rgba(176,190,197,.9)'
  };

  /** Màu dải trạng thái regime (luôn kèm chữ trong legend/tooltip, không chỉ màu). */
  var REGIME_COLORS = {
    UPTREND: 'rgba(67,160,71,.85)',
    DOWNTREND: 'rgba(229,57,53,.85)',
    RANGE: 'rgba(249,168,37,.85)',
    UNKNOWN: 'rgba(120,144,156,.55)',
    WARMUP: 'rgba(55,71,79,.35)'
  };
  var REGIME_TEXT_VI = {
    UPTREND: 'Tăng', DOWNTREND: 'Giảm', RANGE: 'Range', UNKNOWN: 'Chưa rõ', WARMUP: 'Warm-up / sau gap'
  };
  /**
   * Khi khoảng cách TRUNG BÌNH giữa các marker DC trong khung nhìn nhỏ hơn số px
   * này, chữ trên marker bị ẩn để không đè nhau (marker vẫn giữ). Tính theo mật độ
   * nhãn thực tế chứ không theo px/nến, vì pivot DC thưa hơn nến rất nhiều.
   */
  var COMPACT_PX_PER_LABEL = 26;

  var DC_EVENT_TYPES = {
    DC_HIGH: 1, DC_LOW: 1, DC_REGIME_UP: 1, DC_REGIME_DOWN: 1, DC_REGIME_UNKNOWN: 1,
    DC_RANGE_START: 1, DC_RANGE_EXIT: 1, DC_SEGMENT_GAP: 1, DC_GAP_BRIDGED: 1
  };

  /** Sự kiện của c2_cisd_research: lớp hiển thị, nhãn marker, vị trí neo. */
  var C2CISD = {
    C2_CONFIRMED_UP: { layer: 'c2', up: true, text: 'C2↑', color: 'c2Up', shape: 'arrowUp', at: 'event' },
    C2_CONFIRMED_DOWN: { layer: 'c2', up: false, text: 'C2↓', color: 'c2Down', shape: 'arrowDown', at: 'event' },
    CISD_CONFIRMED_UP: { layer: 'cisd', up: true, text: '+CISD', color: 'cisdUp', shape: 'circle', at: 'event' },
    CISD_CONFIRMED_DOWN: { layer: 'cisd', up: false, text: '-CISD', color: 'cisdDown', shape: 'circle', at: 'event' },
    EARLY_CISD_UP: { layer: 'cisd', up: true, text: 'e+', color: 'earlyUp', shape: 'circle', at: 'event', size: 0.6 },
    EARLY_CISD_DOWN: { layer: 'cisd', up: false, text: 'e−', color: 'earlyDown', shape: 'circle', at: 'event', size: 0.6 },
    CISD_LEVEL_SET_UP: null,
    CISD_LEVEL_SET_DOWN: null,
    SETUP_INVALIDATED: { layer: 'lifecycle', text: 'X', color: 'dead', shape: 'square', at: 'confirm' },
    SETUP_C4_INVALIDATED: { layer: 'lifecycle', text: 'XC4', color: 'c4inv', shape: 'circle', at: 'confirm', size: 0.7 },
    SETUP_EXPIRED: { layer: 'lifecycle', text: 'hết', color: 'ended', shape: 'circle', at: 'confirm', size: 0.7 },
    SETUP_SUPERSEDED: { layer: 'lifecycle', text: 'thay', color: 'ended', shape: 'circle', at: 'confirm', size: 0.7 },
    SETUP_DATA_GAP: { layer: 'lifecycle', text: 'gap', color: 'dataq', shape: 'square', at: 'confirm', size: 0.7 },
    HTF_BUCKET_INCOMPLETE: { layer: 'dataq', up: false, text: 'H4 thiếu', color: 'dataq', shape: 'square', at: 'confirm', size: 0.5 }
  };

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

  function setLineData(series, points, extraOpts) {
    var clean = [];
    for (var i = 0; i < (points || []).length; i++) {
      var p = points[i];
      if (p && p.time != null && isFiniteNum(p.value)) {
        clean.push({ time: p.time, value: p.value });
      }
    }
    var opts = { visible: clean.length > 0 };
    if (extraOpts) {
      var k;
      for (k in extraOpts) {
        if (Object.prototype.hasOwnProperty.call(extraOpts, k)) opts[k] = extraOpts[k];
      }
    }
    series.applyOptions(opts);
    series.setData(clean);
  }

  var TRANSPARENT = 'rgba(0,0,0,0)';

  /**
   * Chuỗi mức có ngắt cho đường bậc thang. LWC 4.2 vẽ nối qua điểm khoảng trắng,
   * nên ngắt bằng điểm màu trong suốt: đoạn ngang lấy màu điểm đầu, đoạn dọc lấy
   * màu điểm cuối. Điểm tại nến xác lập mức (hoặc đổi ``idKey``) trong suốt →
   * đường chỉ hiện từ nến SAU lúc mức được biết, không nối sang mức/setup khác.
   */
  function levelSeriesData(timeline, key, cursor, idKey) {
    var out = [];
    var prevVal = null, prevId = null, lastVal = null;
    for (var j = 0; j < timeline.length; j++) {
      var p = timeline[j];
      if (p.bar_index > cursor) break;
      var v = p[key];
      var id = idKey ? p[idKey] : null;
      if (!isFiniteNum(v)) {
        if (lastVal !== null) out.push({ time: p.time, value: lastVal, color: TRANSPARENT });
        prevVal = null; prevId = null;
        continue;
      }
      if (prevVal === null || v !== prevVal || id !== prevId) {
        out.push({ time: p.time, value: v, color: TRANSPARENT });
      } else {
        out.push({ time: p.time, value: v });
      }
      prevVal = v; prevId = id; lastVal = v;
    }
    return out;
  }

  /**
   * Biên Range: chỉ có điểm khi Range đang hoạt động (không kéo mức cũ qua các nến
   * sau exit — tránh làm giãn autoscale). Điểm đầu mỗi Range trong suốt (đường
   * bắt đầu từ nến SAU lúc biết); điểm cuối mỗi Range trong suốt để không nối
   * sang Range kế tiếp.
   */
  function rangeSeriesData(timeline, key, idKey, cursor) {
    var out = [], prevId = null;
    for (var j = 0; j < timeline.length; j++) {
      var p = timeline[j];
      if (p.bar_index > cursor) break;
      var v = p[key], id = p[idKey];
      if (!isFiniteNum(v)) {
        if (prevId !== null && out.length) out[out.length - 1].color = TRANSPARENT;
        prevId = null;
        continue;
      }
      if (id !== prevId) {
        if (out.length) out[out.length - 1].color = TRANSPARENT;
        out.push({ time: p.time, value: v, color: TRANSPARENT });
      } else {
        out.push({ time: p.time, value: v });
      }
      prevId = id;
    }
    return out;
  }

  /**
   * Mức xác nhận theo timeline: đỉnh → ứng viên − Δ, đáy → ứng viên + Δ. Mỗi lần
   * ứng viên dời (id = side + nến ứng viên) là một đoạn mới, không nối với đoạn cũ.
   */
  function candidateLevelData(timeline, cursor) {
    var rows = [];
    for (var j = 0; j < timeline.length; j++) {
      var p = timeline[j];
      if (p.bar_index > cursor) break;
      var ok = isFiniteNum(p.dc_cand_price) && isFiniteNum(p.dc_threshold);
      rows.push({
        bar_index: p.bar_index, time: p.time,
        lvl: ok ? (p.dc_cand_side === 'high' ? p.dc_cand_price - p.dc_threshold : p.dc_cand_price + p.dc_threshold) : null,
        lid: ok ? p.dc_cand_side + p.dc_cand_index : null
      });
    }
    return rangeSeriesData(rows, 'lvl', 'lid', cursor);
  }

  function setGapLineData(series, points) {
    var any = false;
    for (var i = 0; i < points.length; i++) if (!points[i].color) { any = true; break; }
    series.applyOptions({ visible: any });
    series.setData(any ? points : []);
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

    this.levelHigh = this.chart.addLineSeries({
      color: COLORS.levelHigh, lineWidth: 1, lineStyle: LWC.LineStyle.Dashed,
      lineType: LWC.LineType.WithSteps, priceLineVisible: false,
      lastValueVisible: false, crosshairMarkerVisible: false, title: ''
    });
    this.levelLow = this.chart.addLineSeries({
      color: COLORS.levelLow, lineWidth: 1, lineStyle: LWC.LineStyle.Dashed,
      lineType: LWC.LineType.WithSteps, priceLineVisible: false,
      lastValueVisible: false, crosshairMarkerVisible: false, title: ''
    });

    // c2_cisd_research: mức CISD đang theo dõi, mức CISD của setup, cực trị C2.
    var lineOpts = function (color, width, style) {
      return {
        color: color, lineWidth: width, lineStyle: style, lineType: LWC.LineType.WithSteps,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: ''
      };
    };
    this.cisdTrackUp = this.chart.addLineSeries(lineOpts(COLORS.trackUp, 1, LWC.LineStyle.Dotted));
    this.cisdTrackDown = this.chart.addLineSeries(lineOpts(COLORS.trackDown, 1, LWC.LineStyle.Dotted));
    this.setupLevelUp = this.chart.addLineSeries(lineOpts(COLORS.cisdUp, 2, LWC.LineStyle.Solid));
    this.setupLevelDown = this.chart.addLineSeries(lineOpts(COLORS.cisdDown, 2, LWC.LineStyle.Solid));
    this.setupExtremeUp = this.chart.addLineSeries(lineOpts(COLORS.extreme, 1, LWC.LineStyle.Dashed));
    this.setupExtremeDown = this.chart.addLineSeries(lineOpts(COLORS.extreme, 1, LWC.LineStyle.Dashed));

    // dc_atr_structure: đường nối pivot close đã xác nhận, đoạn tới ứng viên
    // (nét đứt), biên Range khoá, dải trạng thái regime ở đáy chart.
    var simpleOpts = function (color, width, style) {
      return {
        color: color, lineWidth: width, lineStyle: style, lineType: LWC.LineType.Simple,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: ''
      };
    };
    this.dcLine = this.chart.addLineSeries(simpleOpts(COLORS.dcLine, 2, LWC.LineStyle.Solid));
    this.dcCand = this.chart.addLineSeries(simpleOpts(COLORS.dcCand, 1, LWC.LineStyle.Dashed));
    this.dcLevel = this.chart.addLineSeries(lineOpts(COLORS.dcLevel, 1, LWC.LineStyle.Dotted));
    this.rangeUpper = this.chart.addLineSeries(lineOpts(COLORS.rangeLine, 1, LWC.LineStyle.LargeDashed));
    this.rangeLower = this.chart.addLineSeries(lineOpts(COLORS.rangeLine, 1, LWC.LineStyle.LargeDashed));
    this.regimeBand = this.chart.addHistogramSeries({
      priceScaleId: 'regime', priceLineVisible: false, lastValueVisible: false, base: 0,
      priceFormat: { type: 'custom', formatter: function () { return ''; } }
    });
    this.chart.priceScale('regime').applyOptions({ scaleMargins: { top: 0.955, bottom: 0 }, visible: false });
    this.timelineByIndex = {};

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
    this._dcMarkers = [];
    this._dcCandMarkers = [];
    this._dcMarkerPos = [];
    this.chart.timeScale().subscribeVisibleLogicalRangeChange(function () { self._updateCompact(); });
    this.chart.subscribeClick(function (param) {
      if (!self._onBarClick || !param || param.time === undefined) return;
      var bar = self._barByTime && self._barByTime[param.time];
      var src = param.sourceEvent || {};
      if (bar) self._onBarClick(bar, { shift: !!src.shiftKey, point: param.point || null });
    });
  }

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
   * Xoá mọi lớp phủ (đường mức, DC, Range, dải trạng thái, marker). Gọi TRƯỚC khi nạp bộ nến mới:
   * lớp phủ cũ mang mốc thời gian của bộ nến trước — LWC 4.2.3 đánh lại chỉ số trục thời gian theo
   * cả hai bộ mốc rồi vẽ nến lỗi «Value is null» (gặp khi đổi dataset sau một lần chạy).
   */
  MarketChart.prototype._clearOverlays = function () {
    var series = [this.levelHigh, this.levelLow, this.cisdTrackUp, this.cisdTrackDown,
      this.setupLevelUp, this.setupLevelDown, this.setupExtremeUp, this.setupExtremeDown,
      this.dcLine, this.dcCand, this.dcLevel, this.rangeUpper, this.rangeLower, this.regimeBand];
    for (var i = 0; i < series.length; i++) if (series[i]) series[i].setData([]);
    if (this.dcLine) this.dcLine.setMarkers([]);
    if (this.dcCand) this.dcCand.setMarkers([]);
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
   * Cập nhật marker và đường mức.
   * opts = { layers: {swing,swing_l2,hhll,eq,levels,bos,choch}, markerAtConfirm: bool, replayCursor: int|null }
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

    // --- dựng marker ---
    var pivotGroups = {};   // key: index + '|' + side
    var bosMarkers = [];
    var dcPivots = [];
    var selectedId = opts.selectedEventId || null;

    for (var k = 0; k < this.events.length; k++) {
      var e = this.events[k];
      if (e.confirmed_bar_index > cursor) continue;   // chưa xác nhận tại thời điểm replay
      push(this.eventsAtBar, e.event_bar_index, e);
      if (e.confirmed_bar_index !== e.event_bar_index) push(this.eventsAtBar, e.confirmed_bar_index, e);

      var t = e.structure_type;
      if (DC_EVENT_TYPES[t]) {
        if (t === 'DC_HIGH' || t === 'DC_LOW') {
          dcPivots.push(e);
          if (layers.dc_confirm || e.event_id === selectedId) {
            // inBar trên nến = đúng close của nến xác nhận (confirmation_close).
            bosMarkers.push({
              time: timeByIndex[e.confirmed_bar_index], position: 'inBar', color: COLORS.dcConfirm,
              shape: 'square', text: e.event_id === selectedId ? '✓ xác nhận' : '✓', size: 0.6
            });
          }
        } else if ((t === 'DC_SEGMENT_GAP' || t === 'DC_GAP_BRIDGED') && layers.regime) {
          bosMarkers.push({
            time: timeByIndex[e.confirmed_bar_index], position: 'belowBar', color: COLORS.dataq,
            shape: t === 'DC_SEGMENT_GAP' ? 'square' : 'circle',
            text: t === 'DC_SEGMENT_GAP' ? 'gap' : 'nối', size: 0.5
          });
        }
        continue;   // regime event: thể hiện bằng dải trạng thái + tooltip
      }
      if (Object.prototype.hasOwnProperty.call(C2CISD, t)) {
        var spec = C2CISD[t];
        if (!spec || !layers[spec.layer]) continue;
        var upDir = spec.up !== undefined ? spec.up : e.direction === 'up';
        var at = (spec.at === 'confirm' || opts.markerAtConfirm) ? e.confirmed_bar_index : e.event_bar_index;
        var txt = spec.text;
        if ((t === 'C2_CONFIRMED_UP' || t === 'C2_CONFIRMED_DOWN') && e.details && e.details.outside_bar_ambiguous) txt += '?';
        if ((t === 'CISD_CONFIRMED_UP' || t === 'CISD_CONFIRMED_DOWN') && e.details && e.details.early) txt += '(e)';
        bosMarkers.push({
          time: timeByIndex[at],
          position: upDir ? 'belowBar' : 'aboveBar',
          color: COLORS[spec.color],
          shape: spec.shape,
          text: txt,
          size: spec.size || 1
        });
        continue;
      }
      if (t === 'BOS_UP' || t === 'BOS_DOWN' || t === 'BOS_INTERNAL_UP' || t === 'BOS_INTERNAL_DOWN'
          || t === 'CHOCH_UP' || t === 'CHOCH_DOWN') {
        var isChoch = t.indexOf('CHOCH') === 0;
        var isInt = t.indexOf('INTERNAL') !== -1;
        if (isChoch && !layers.choch) continue;
        if (!isChoch && !layers.bos) continue;
        var up = t.slice(-2) === 'UP';
        var color = isChoch ? (up ? COLORS.chochUp : COLORS.chochDown)
          : (isInt ? (up ? COLORS.bosIntUp : COLORS.bosIntDown) : (up ? COLORS.bosUp : COLORS.bosDown));
        var text = isChoch ? (up ? 'CHoCH↑' : 'CHoCH↓') : (isInt ? (up ? 'iBOS↑' : 'iBOS↓') : (up ? 'BOS↑' : 'BOS↓'));
        bosMarkers.push({
          time: timeByIndex[e.confirmed_bar_index],
          position: up ? 'belowBar' : 'aboveBar',
          color: color,
          shape: up ? 'arrowUp' : 'arrowDown',
          text: text,
          size: 1
        });
        continue;
      }

      if (t.indexOf('BASELINE_') === 0 || t === 'HMM_STATE_CHANGE') {
        if (!layers.bos) continue;
        var upB = t === 'BASELINE_UP';
        var downB = t === 'BASELINE_DOWN';
        bosMarkers.push({
          time: timeByIndex[e.confirmed_bar_index],
          position: downB ? 'aboveBar' : 'belowBar',
          color: upB ? COLORS.bosUp : (downB ? COLORS.bosDown : COLORS.eq),
          shape: upB ? 'arrowUp' : (downB ? 'arrowDown' : 'circle'),
          text: t.replace('BASELINE_', 'BL ').replace('HMM_STATE_CHANGE', 'HMM'),
          size: 1
        });
        continue;
      }

      var highTypes = {
        SWING_HIGH: 1, SWING_HIGH_L2: 1, HH: 1, LH: 1, EQH: 1
      };
      var side = highTypes[t] ? 'high' : 'low';
      var idx = opts.markerAtConfirm ? e.confirmed_bar_index : e.event_bar_index;
      var key = idx + '|' + side;
      var g = pivotGroups[key] || (pivotGroups[key] = {
        index: idx, side: side, labels: [], hasSwing: false, hasL2: false
      });
      if (t === 'SWING_HIGH' || t === 'SWING_LOW') g.hasSwing = true;
      else if (t === 'SWING_HIGH_L2' || t === 'SWING_LOW_L2') g.hasL2 = true;
      else if (t === 'EQH' || t === 'EQL') { if (layers.eq) g.labels.push(t); }
      else if (layers.hhll) g.labels.push(t);
    }

    var markers = [];
    Object.keys(pivotGroups).forEach(function (key) {
      var g = pivotGroups[key];
      var showL2 = g.hasL2 && layers.swing_l2 !== false;
      var showL1 = g.hasSwing && layers.swing && !showL2;
      if (!showL1 && !showL2 && !g.labels.length) return;
      var isHigh = g.side === 'high';
      var label = g.labels[0] || '';
      var color;
      if (showL2) {
        color = (label === 'EQH' || label === 'EQL')
          ? COLORS.eq
          : (isHigh ? COLORS.swingHighL2 : COLORS.swingLowL2);
      } else {
        color = label
          ? ((label === 'EQH' || label === 'EQL') ? COLORS.eq : COLORS.hhll)
          : (isHigh ? COLORS.swingHigh : COLORS.swingLow);
      }
      markers.push({
        time: timeByIndex[g.index],
        position: isHigh ? 'aboveBar' : 'belowBar',
        color: color,
        shape: showL2 ? 'square' : 'circle',
        text: label,
        size: (showL2 ? 2 : 1) * (self._markerScale || 1)
      });
    });

    // Baseline so sánh (pivot wick của một run khác) — cùng quy tắc lúc biết.
    var baseEvs = opts.baselineEvents || [];
    if (layers.baseline) {
      for (var bi = 0; bi < baseEvs.length; bi++) {
        var be = baseEvs[bi];
        if (be.confirmed_bar_index > cursor) continue;
        if (be.structure_type !== 'SWING_HIGH' && be.structure_type !== 'SWING_LOW') continue;
        var bHigh = be.structure_type === 'SWING_HIGH';
        bosMarkers.push({
          time: timeByIndex[be.event_bar_index], position: bHigh ? 'aboveBar' : 'belowBar',
          color: COLORS.baseline, shape: bHigh ? 'arrowDown' : 'arrowUp', text: 'B', size: 0.7
        });
        push(this.eventsAtBar, be.event_bar_index, Object.assign({}, be, { _baseline: true }));
      }
    }

    markers = markers.concat(bosMarkers).filter(function (m) {
      return m.time != null && isFiniteNum(m.time);
    });
    markers.sort(function (a, b) { return a.time - b.time; });
    this.candles.setMarkers(markers);

    this._drawDc(dcPivots, layers, cursor, timeByIndex, selectedId);

    // --- đường mức swing đang hoạt động (do lõi thuật toán sinh) ---
    // Baseline không có muc_high/low (nhiều điểm null). Đưa null vào
    // LineType.WithSteps rồi setVisibleRange → Lightweight Charts ném "Value is null".
    if (layers.levels) {
      var hi = [], lo = [], sma = [];
      for (var j = 0; j < this.timeline.length; j++) {
        var p = this.timeline[j];
        if (p.bar_index > cursor) break;
        if (isFiniteNum(p.muc_high)) hi.push({ time: p.time, value: p.muc_high });
        if (isFiniteNum(p.muc_low)) lo.push({ time: p.time, value: p.muc_low });
        if (isFiniteNum(p.sma)) sma.push({ time: p.time, value: p.sma });
      }
      if (!hi.length && sma.length) {
        setLineData(this.levelHigh, sma, { lineType: LWC.LineType.Simple });
      } else {
        setLineData(this.levelHigh, hi, { lineType: LWC.LineType.WithSteps });
      }
      setLineData(this.levelLow, lo, { lineType: LWC.LineType.WithSteps });
    } else {
      setLineData(this.levelHigh, []);
      setLineData(this.levelLow, []);
    }

    // --- c2_cisd_research: đường mức CISD / cực trị setup (timeline lõi) ---
    var tl = this.timeline;
    var hasC2 = tl.length && Object.prototype.hasOwnProperty.call(tl[tl.length - 1], 'cisd_up');
    var showTrack = hasC2 && layers.cisd;
    var showSetup = hasC2 && layers.c2;
    setGapLineData(this.cisdTrackUp, showTrack ? levelSeriesData(tl, 'cisd_up', cursor) : []);
    setGapLineData(this.cisdTrackDown, showTrack ? levelSeriesData(tl, 'cisd_down', cursor) : []);
    setGapLineData(this.setupLevelUp, showSetup && layers.cisd ? levelSeriesData(tl, 'setup_up_level', cursor, 'setup_up_id') : []);
    setGapLineData(this.setupLevelDown, showSetup && layers.cisd ? levelSeriesData(tl, 'setup_down_level', cursor, 'setup_down_id') : []);
    setGapLineData(this.setupExtremeUp, showSetup ? levelSeriesData(tl, 'setup_up_extreme', cursor, 'setup_up_id') : []);
    setGapLineData(this.setupExtremeDown, showSetup ? levelSeriesData(tl, 'setup_down_extreme', cursor, 'setup_down_id') : []);
  };

  /**
   * dc_atr_structure: đường nối pivot CLOSE đã xác nhận (chỉ khi cả hai đầu đã
   * xác nhận ≤ con trỏ), đoạn nét đứt tới ứng viên, biên Range khoá (từ nến sau
   * lúc vào Range tới exit), dải trạng thái theo timeline lõi (bắt đầu lúc biết).
   * Không nối qua gap: điểm cuối mỗi segment trong suốt nên đoạn đi ra bị ẩn.
   */
  MarketChart.prototype._drawDc = function (dcPivots, layers, cursor, timeByIndex, selectedId) {
    var tl = this.timeline || [];
    var isDc = tl.length && Object.prototype.hasOwnProperty.call(tl[tl.length - 1], 'dc_phase');
    this.timelineByIndex = {};
    if (!isDc) {
      this.dcLine.setMarkers([]); setLineData(this.dcLine, []);
      this.dcCand.setMarkers([]); setLineData(this.dcCand, []);
      setGapLineData(this.dcLevel, []);
      setGapLineData(this.rangeUpper, []); setGapLineData(this.rangeLower, []);
      this.regimeBand.setData([]);
      return;
    }
    var lastPt = null;
    for (var j = 0; j < tl.length; j++) {
      if (tl[j].bar_index > cursor) break;
      this.timelineByIndex[tl[j].bar_index] = tl[j];
      lastPt = tl[j];
    }

    // --- đường nối pivot + marker tại đúng giá close ---
    dcPivots.sort(function (a, b) { return a.event_bar_index - b.event_bar_index; });
    var pts = [], mks = [];
    if (layers.dc) {
      for (var i = 0; i < dcPivots.length; i++) {
        var p = dcPivots[i], nx = dcPivots[i + 1];
        var tm = timeByIndex[p.event_bar_index];
        if (tm == null) continue;
        var pt = { time: tm, value: p.price };
        if (nx && (nx.details || {}).segment !== (p.details || {}).segment) pt.color = TRANSPARENT;
        pts.push(pt);
        var hi = p.structure_type === 'DC_HIGH';
        var lbl = (layers.dc_labels && p.details && p.details.nhan) ? p.details.nhan : '';
        mks.push({
          time: tm, position: 'inBar', color: hi ? COLORS.dcHigh : COLORS.dcLow,
          shape: p.event_id === selectedId ? 'square' : 'circle', text: lbl,
          size: p.event_id === selectedId ? 1.6 : 0.9
        });
      }
    }
    this.dcLine.applyOptions({ visible: pts.length > 1 || mks.length > 0 });
    this.dcLine.setData(pts);
    this._dcMarkers = mks;
    var posMap = this._posByTime || {};
    this._dcMarkerPos = mks.map(function (m) { return posMap[m.time]; })
      .filter(function (x) { return x !== undefined; });

    // --- ứng viên (nét đứt, có thể thay đổi) ---
    var cand = [], candMk = [];
    if (layers.dc_candidate && lastPt && lastPt.dc_cand_time != null && isFiniteNum(lastPt.dc_cand_price)) {
      if (lastPt.dc_last_pivot_time != null && lastPt.dc_last_pivot_time < lastPt.dc_cand_time) {
        cand.push({ time: lastPt.dc_last_pivot_time, value: lastPt.dc_last_pivot_price });
      }
      cand.push({ time: lastPt.dc_cand_time, value: lastPt.dc_cand_price });
      candMk.push({
        time: lastPt.dc_cand_time, position: 'inBar', color: COLORS.dcCand, shape: 'circle',
        text: 'ứng viên (có thể đổi)', size: 0.8
      });
    }
    this.dcCand.applyOptions({ visible: cand.length > 0 });
    this.dcCand.setData(cand);
    this._dcCandMarkers = candMk;
    this._compact = this._isCompact();
    this._applyDcMarkers();

    // --- mức xác nhận của ứng viên (ứng viên ∓ Δ đã khoá), từ nến sau lúc đặt ---
    setGapLineData(this.dcLevel, layers.dc_candidate ? candidateLevelData(tl, cursor) : []);

    // --- Range khoá ---
    setGapLineData(this.rangeUpper, layers.range ? rangeSeriesData(tl, 'range_upper', 'range_id', cursor) : []);
    setGapLineData(this.rangeLower, layers.range ? rangeSeriesData(tl, 'range_lower', 'range_id', cursor) : []);

    // --- dải trạng thái ---
    var band = [];
    if (layers.regime) {
      for (var r = 0; r < tl.length; r++) {
        var q = tl[r];
        if (q.bar_index > cursor) break;
        band.push({ time: q.time, value: 1, color: REGIME_COLORS[q.regime] || REGIME_COLORS.UNKNOWN });
      }
    }
    this.regimeBand.setData(band);
  };

  /** Mật độ hiển thị hiện tại: true khi mỗi nến hẹp hơn COMPACT_PX_PER_BAR pixel. */
  MarketChart.prototype._isCompact = function () {
    var r = null;
    try { r = this.chart.timeScale().getVisibleLogicalRange(); } catch (e) { r = null; }
    if (!r || !this._dcMarkerPos.length) return false;
    var n = 0;
    for (var i = 0; i < this._dcMarkerPos.length; i++) {
      var q = this._dcMarkerPos[i];
      if (q >= r.from && q <= r.to) n++;
    }
    return n > 1 && (this.container.clientWidth / n) < COMPACT_PX_PER_LABEL;
  };

  MarketChart.prototype.isCompact = function () { return this._compact; };

  MarketChart.prototype._updateCompact = function () {
    var c = this._isCompact();
    if (c === this._compact) return;
    this._compact = c;
    this._applyDcMarkers();
    if (this._onCompactChange) this._onCompactChange(c);
  };

  /** fn(compact) — gọi khi chế độ ẩn chữ nhãn đổi do zoom. */
  MarketChart.prototype.onCompactChange = function (fn) { this._onCompactChange = fn; };

  /** Chỉ đổi phần vẽ (chữ trên marker), không đổi dữ liệu hay sự kiện. */
  MarketChart.prototype._applyDcMarkers = function () {
    var strip = function (list) {
      return list.map(function (m) { var x = Object.assign({}, m); x.text = ''; return x; });
    };
    this.dcLine.setMarkers(this._compact ? strip(this._dcMarkers) : this._dcMarkers);
    this.dcCand.setMarkers(this._compact ? strip(this._dcCandMarkers) : this._dcCandMarkers);
  };

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

  /**
   * Overlay đánh giá: TP / FP / FN / nhãn tham chiếu trên cùng nến.
   * opts = { matches, false_positives, false_negatives, labels, selected }
   * selected = { role, event_id?, label_seq?, bar_index }
   */
  MarketChart.prototype.setEvalOverlay = function (opts) {
    opts = opts || {};
    var timeByIndex = {};
    for (var i = 0; i < this.bars.length; i++) timeByIndex[this.bars[i].index] = this.bars[i].time;

    var selected = opts.selected || null;
    function isSel(role, bar, extra) {
      if (!selected) return false;
      if (selected.role && selected.role !== role) return false;
      if (selected.bar_index !== undefined && selected.bar_index !== bar) return false;
      if (extra && selected.event_id && extra.event_id && selected.event_id !== extra.event_id) return false;
      if (extra && selected.label_seq !== undefined && extra.label_seq !== undefined
          && selected.label_seq !== extra.label_seq) return false;
      return true;
    }

    var markers = [];
    function add(barIndex, sideHigh, color, shape, text, size) {
      var t = timeByIndex[barIndex];
      if (t === undefined) return;
      markers.push({
        time: t,
        position: sideHigh ? 'aboveBar' : 'belowBar',
        color: color,
        shape: shape,
        text: text,
        size: size
      });
    }
    function highSide(stype) {
      return !stype || String(stype).indexOf('LOW') === -1 && String(stype).indexOf('DOWN') === -1;
    }

    var labels = opts.labels || [];
    for (var li = 0; li < labels.length; li++) {
      var lb = labels[li];
      add(lb.bar_index, highSide(lb.structure_type), '#78909c', 'circle', 'N', 1);
    }
    var fns = opts.false_negatives || [];
    for (var f = 0; f < fns.length; f++) {
      var fn = fns[f];
      add(fn.bar_index, highSide(fn.structure_type), '#ffca6b', 'square', 'FN',
          isSel('fn', fn.bar_index, fn) ? 2 : 1);
    }
    var fps = opts.false_positives || [];
    for (var p = 0; p < fps.length; p++) {
      var fp = fps[p];
      add(fp.event_bar_index, highSide(fp.structure_type), '#ff8a80', 'arrowDown', 'FP',
          isSel('fp', fp.event_bar_index, fp) ? 2 : 1);
    }
    var tps = opts.matches || [];
    for (var m = 0; m < tps.length; m++) {
      var tp = tps[m];
      add(tp.event_bar_index, highSide(tp.structure_type), '#7fd3a8', 'arrowUp', 'TP',
          isSel('tp', tp.event_bar_index, tp) ? 2 : 1);
    }
    markers = markers.filter(function (x) { return x.time !== undefined; });
    markers.sort(function (a, b) { return a.time - b.time; });
    this.candles.setMarkers(markers);
    this.eventsAtBar = {};
    var self = this;
    function pushBar(idx, item) {
      (self.eventsAtBar[idx] = self.eventsAtBar[idx] || []).push(item);
    }
    tps.forEach(function (e) {
      pushBar(e.event_bar_index, {
        structure_type: e.structure_type, structure_text_vi: 'Ghép đúng (TP)',
        price: e.price, event_bar_index: e.event_bar_index,
        confirmed_bar_index: e.confirmed_bar_index, event_time: '',
        confirmed_at: '', confirmation_lag_bars: e.lag,
        reason_text_vi: 'Nhãn #' + e.label_seq + ' · Δnến ' + e.delta_bars
      });
    });
    fps.forEach(function (e) {
      pushBar(e.event_bar_index, {
        structure_type: e.structure_type, structure_text_vi: 'Sự kiện thừa (FP)',
        price: e.price, event_bar_index: e.event_bar_index,
        confirmed_bar_index: e.confirmed_bar_index, event_time: '',
        confirmed_at: '', confirmation_lag_bars: e.lag,
        reason_text_vi: 'Không ghép được nhãn trong dung sai protocol.'
      });
    });
    fns.forEach(function (e) {
      pushBar(e.bar_index, {
        structure_type: e.structure_type, structure_text_vi: 'Bỏ sót (FN)',
        price: e.price, event_bar_index: e.bar_index,
        confirmed_bar_index: e.bar_index, event_time: '',
        confirmed_at: '', confirmation_lag_bars: 0,
        reason_text_vi: 'Nhãn seq ' + e.label_seq + ' không có sự kiện tương ứng.'
      });
    });
  };

  /**
   * Overlay nhãn người gán (trang Gán nhãn). Không hiện TP/FP — chưa chấm.
   * opts = { labels, selected: { bar_index, structure_type },
   *          suggestions: [{structure_type, bar_index, price, current, source_algorithm}] }
   * Đề xuất auto label vẽ bằng chấm tròn xám (đang duyệt: vàng, to hơn) để
   * không lẫn với nhãn đã vào bộ nháp.
   */
  MarketChart.prototype.setLabelOverlay = function (opts) {
    opts = opts || {};
    var timeByIndex = {};
    for (var i = 0; i < this.bars.length; i++) timeByIndex[this.bars[i].index] = this.bars[i].time;
    var selected = opts.selected || null;
    var colorOf = {
      SWING_HIGH: COLORS.swingHigh, SWING_LOW: COLORS.swingLow,
      SWING_HIGH_L2: COLORS.swingHighL2, SWING_LOW_L2: COLORS.swingLowL2,
      BOS_UP: COLORS.bosUp, BOS_DOWN: COLORS.bosDown,
      CHOCH_UP: COLORS.chochUp, CHOCH_DOWN: COLORS.chochDown,
      BOS_INTERNAL_UP: COLORS.bosIntUp, BOS_INTERNAL_DOWN: COLORS.bosIntDown
    };
    var shortOf = {
      SWING_HIGH: 'H', SWING_LOW: 'L', SWING_HIGH_L2: 'H2', SWING_LOW_L2: 'L2',
      BOS_UP: 'BU', BOS_DOWN: 'BD', CHOCH_UP: 'CU', CHOCH_DOWN: 'CD',
      BOS_INTERNAL_UP: 'IU', BOS_INTERNAL_DOWN: 'ID'
    };
    function highSide(stype) {
      return !stype || String(stype).indexOf('LOW') === -1 && String(stype).indexOf('DOWN') === -1;
    }
    var barAt = {};
    for (var bi = 0; bi < this.bars.length; bi++) barAt[this.bars[bi].index] = this.bars[bi];
    function openIso(idx) { return barAt[idx] ? barAt[idx].bar_time : ''; }
    function closeIso(idx) { return barAt[idx] ? barAt[idx].close_time : ''; }
    var clickHint = ' Bấm vào nến để sửa / đổi loại / xoá.';
    var markers = [];
    var labels = opts.labels || [];
    this.eventsAtBar = {};
    for (var li = 0; li < labels.length; li++) {
      var lb = labels[li];
      var t = timeByIndex[lb.bar_index];
      if (t === undefined) continue;
      var st = lb.structure_type;
      var sel = selected && selected.bar_index === lb.bar_index && selected.structure_type === st;
      markers.push({
        time: t,
        position: highSide(st) ? 'aboveBar' : 'belowBar',
        color: colorOf[st] || '#78909c',
        shape: highSide(st) ? 'arrowDown' : 'arrowUp',
        text: shortOf[st] || 'N',
        size: sel ? 2 : 1
      });
      (this.eventsAtBar[lb.bar_index] = this.eventsAtBar[lb.bar_index] || []).push({
        structure_type: st,
        structure_text_vi: lb.source && lb.source !== 'human'
          ? 'Nhãn trong nháp (từ đề xuất ' + (lb.source_algorithm || '?') + ')'
          : 'Nhãn trong nháp (người gán)',
        price: lb.price,
        event_bar_index: lb.bar_index,
        confirmed_bar_index: lb.bar_index,
        event_time: openIso(lb.bar_index),
        confirmed_at: '',
        confirmation_lag_bars: 0,
        no_confirm: true,   // nhãn người gán không có "xác nhận lúc"
        reason_text_vi: (lb.notes ? lb.notes + ' · ' : '') +
          (lb.source === 'auto_edited' ? 'Người đã sửa sau khi chấp nhận. ' : '') +
          'Chưa chấm F1 trên trang này.' + clickHint
      });
    }
    var sugs = opts.suggestions || [];
    for (var si = 0; si < sugs.length; si++) {
      var sg = sugs[si];
      var ts = timeByIndex[sg.bar_index];
      if (ts === undefined) continue;
      markers.push({
        time: ts,
        position: highSide(sg.structure_type) ? 'aboveBar' : 'belowBar',
        color: sg.current ? '#ffd54f' : 'rgba(176,190,197,.85)',
        shape: 'circle',
        text: (sg.current ? '▶ ' : '?') + (shortOf[sg.structure_type] || 'N'),
        size: sg.current ? 2 : 1
      });
      (this.eventsAtBar[sg.bar_index] = this.eventsAtBar[sg.bar_index] || []).push({
        structure_type: sg.structure_type,
        structure_text_vi: 'ĐỀ XUẤT chưa duyệt (' + (sg.source_algorithm || 'auto') + ')',
        price: sg.price,
        event_bar_index: sg.bar_index,
        confirmed_bar_index: sg.confirmed_bar_index != null ? sg.confirmed_bar_index : sg.bar_index,
        event_time: openIso(sg.bar_index),
        confirmed_at: closeIso(sg.confirmed_bar_index != null ? sg.confirmed_bar_index : sg.bar_index),
        confirmation_lag_bars: sg.confirmation_lag_bars || 0,
        reason_text_vi: (sg.reason_text_vi || '') +
          ' — Chưa phải nhãn. Bấm vào nến để chấp nhận / đổi loại / bỏ.'
      });
    }
    markers.sort(function (a, b) { return a.time - b.time; });
    this.candles.setMarkers(markers);
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

    var d = this.digits;
    var html = '<div class="tt-time">Nến #' + bar.index + ' · ' + fmtTime(bar.time) + '</div>';
    html += '<div class="tt-ohlc">O ' + bar.open.toFixed(d) + '  H ' + bar.high.toFixed(d) +
            '  L ' + bar.low.toFixed(d) + '  C ' + bar.close.toFixed(d) + '</div>';
    html += '<div class="tt-rule">Đóng nến lúc: ' + fmtIso(bar.close_time) + '</div>';
    var tp = this.timelineByIndex && this.timelineByIndex[bar.index];
    if (tp) {
      html += '<div class="tt-rule">Trạng thái sau nến này (theo swing DC đã xác nhận): <b>' +
        (REGIME_TEXT_VI[tp.regime] || tp.regime) + '</b>' +
        (isFiniteNum(tp.atr) ? ' · ATR ' + tp.atr.toFixed(d) : ' · chưa có ATR') +
        (isFiniteNum(tp.range_upper) ? '<br>Range khoá [' + tp.range_lower.toFixed(d) + ', ' + tp.range_upper.toFixed(d) +
          '], buffer ' + tp.range_buffer.toFixed(d) : '') + '</div>';
    }

    var list = (this.eventsAtBar && this.eventsAtBar[bar.index]) || [];
    for (var i = 0; i < list.length && i < 6; i++) {
      var e = list[i];
      var role = e._baseline
        ? 'Baseline pivot 3/3 theo WICK (run so sánh), không phải DC'
        : (e.event_bar_index === bar.index)
        ? 'Sự kiện tại nến này'
        : 'Được XÁC NHẬN tại nến này';
      html += '<div class="tt-ev"><b>' + e.structure_type + '</b> — ' + (e.structure_text_vi || '') +
              '<br>Giá: <span class="mono">' + Number(e.price).toFixed(d) + '</span>' +
              (e.no_confirm ? '' :
                '<br>' + role +
                '<br>Nến sự kiện: #' + e.event_bar_index + ' (' + fmtIso(e.event_time) + ')' +
                '<br>Xác nhận lúc: ' + fmtIso(e.confirmed_at) + ' — trễ ' + e.confirmation_lag_bars + ' nến') +
              c2cisdDetails(e, d) + dcDetails(e, d) +
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

  function c2cisdDetails(e, d) {
    var x = e.details || {};
    if (e.algorithm !== 'c2_cisd_research') return '';
    var out = [];
    if (x.setup_id) out.push('Setup: <span class="mono">' + x.setup_id + '</span>' + (x.phase ? ' · pha ' + x.phase : '') +
      (x.terminal === true ? ' · KẾT THÚC' : ''));
    if (x.candidate_id) out.push('Ứng viên: <span class="mono">' + x.candidate_id + '</span> (chưa phải setup)');
    if (isFiniteNum(x.cisd_level) && e.structure_type.indexOf('CISD_LEVEL_SET') !== 0) {
      out.push('Mức CISD: ' + Number(x.cisd_level).toFixed(d) +
        (x.cisd_level_source_bar_index != null ? ' (nến nguồn #' + x.cisd_level_source_bar_index + ')' : ''));
    }
    if (x.branch) out.push('Nhánh chọn mức: ' + x.branch + (x.scan_i ? ' (i=' + x.scan_i + ')' : '') + ' · revision ' + x.revision);
    if (x.evidence_bar_index != null) out.push('Close bằng chứng: nến #' + x.evidence_bar_index + ' = ' + Number(x.evidence_close).toFixed(d));
    if (x.early === true) out.push('Early: reclaim trước khi C2 đóng');
    if (isFiniteNum(x.extreme)) out.push('Cực trị C2: ' + Number(x.extreme).toFixed(d));
    if (x.outside_bar_ambiguous) out.push('⚠ Outside bar: C2 đạt cả hai hướng');
    if (x.bucket_start && e.structure_type === 'HTF_BUCKET_INCOMPLETE') {
      out.push('Kỳ H4 ' + fmtIso(x.bucket_start) + ': thấy ' + x.n_bars_seen + '/' + x.expected_bars + ' nến M15 (tới lúc phát hiện)');
    }
    if (x.missing_ltf_bars != null) out.push('Thiếu ' + x.missing_ltf_bars + ' nến M15');
    return out.length ? '<br>' + out.join('<br>') : '';
  }

  function dcDetails(e, d) {
    var x = e.details || {};
    if (e.algorithm !== 'dc_atr_structure') return '';
    var out = [];
    var f = function (v) { return isFiniteNum(v) ? Number(v).toFixed(d) : '—'; };
    if (e.structure_type === 'DC_HIGH' || e.structure_type === 'DC_LOW') {
      out.push('<b>' + (e.structure_type === 'DC_HIGH' ? 'Đỉnh' : 'Đáy') + ' theo CLOSE</b> (không phải wick) · segment ' + x.segment);
      out.push(x.cong_thuc_nguong + ' (khoá lúc ' + fmtIso(x.threshold_set_at) + ')');
      out.push('Xác nhận: ' + x.dieu_kien_xac_nhan);
      if (x.nhan) {
        out.push('Nhãn ' + x.nhan + ': so với ' + f(x.nhan_gia_truoc) + ', chênh ' + f(x.nhan_chenh_lech) +
          ', dung sai ±' + f(x.nhan_dung_sai));
      } else {
        out.push('Pivot đầu tiên cùng loại trong segment — chưa có nhãn so sánh.');
      }
    } else if (e.structure_type === 'DC_GAP_BRIDGED') {
      out.push('Gap ' + (x.khoang_cach_giay / 60) + ' phút được NỐI (≤ ' + x.bridge_max_gap_hours +
        ' giờ): giữ ứng viên, ATR, lịch sử; bước nhảy open − close trước gap = ' + f(x.buoc_nhay_open));
    } else if (e.structure_type === 'DC_SEGMENT_GAP') {
      out.push('Gap ' + (x.khoang_cach_giay / 60) + ' phút: segment ' + x.segment_cu + ' → ' + x.segment_moi +
        '; trạng thái trước gap: ' + (REGIME_TEXT_VI[x.regime_truoc_gap] || x.regime_truoc_gap));
    } else {
      out.push((REGIME_TEXT_VI[x.tu_trang_thai] || x.tu_trang_thai) + ' → <b>' +
        (REGIME_TEXT_VI[x.sang_trang_thai] || x.sang_trang_thai) + '</b>: ' + (x.giai_thich_vi || ''));
    }
    return '<br>' + out.join('<br>');
  }

  MarketChart.prototype.screenshot = function () {
    return this.chart.takeScreenshot();
  };

  global.MarketChart = MarketChart;
  global.chartUtils = {
    fmtTime: fmtTime, fmtIso: fmtIso, REGIME_TEXT_VI: REGIME_TEXT_VI, REGIME_COLORS: REGIME_COLORS
  };
})(window);
