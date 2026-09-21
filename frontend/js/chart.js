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
    levelLow: 'rgba(77,208,225,.55)'
  };

  function fmtTime(ts) {
    var d = new Date(ts * 1000);
    var p = function (n) { return String(n).padStart(2, '0'); };
    return d.getUTCFullYear() + '-' + p(d.getUTCMonth() + 1) + '-' + p(d.getUTCDate()) +
           ' ' + p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()) + ' UTC';
  }

  function fmtIso(iso) {
    if (!iso) return '—';
    return String(iso).replace('T', ' ').replace('+00:00', ' UTC').slice(0, 22);
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
    this.chart.subscribeClick(function (param) {
      if (!self._onBarClick || !param || param.time === undefined) return;
      var bar = self._barByTime && self._barByTime[param.time];
      if (bar) self._onBarClick(bar);
    });
  }

  MarketChart.prototype.setBarClickHandler = function (fn) { this._onBarClick = fn; };

  MarketChart.prototype.setDigits = function (d) { this.digits = d; };

  /** Nạp nến. `bars` là mảng {time, open, high, low, close, index}. */
  MarketChart.prototype.setBars = function (bars) {
    this.bars = bars || [];
    this._barByTime = {};
    var data = [];
    for (var i = 0; i < this.bars.length; i++) {
      var b = this.bars[i];
      this._barByTime[b.time] = b;
      data.push({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
    }
    this.candles.setData(data);
  };

  /** Thêm một nến vào cuối (dùng khi replay tiến từng nến, tránh vẽ lại toàn bộ). */
  MarketChart.prototype.appendBar = function (b) {
    this.bars.push(b);
    this._barByTime[b.time] = b;
    this.candles.update({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
  };

  MarketChart.prototype.fit = function () { this.chart.timeScale().fitContent(); };

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
    var from = this.bars.length - n;
    this.chart.timeScale().setVisibleRange({
      from: this.bars[from].time,
      to: this.bars[this.bars.length - 1].time
    });
  };

  MarketChart.prototype.scrollToIndex = function (idx) {
    if (!this.bars.length) return;
    var i = Math.max(0, Math.min(idx, this.bars.length - 1));
    var from = Math.max(0, i - 120);
    this.chart.timeScale().setVisibleRange({
      from: this.bars[from].time,
      to: this.bars[i].time + 1
    });
  };

  MarketChart.prototype.focusEvent = function (ev) {
    var t = null;
    for (var i = 0; i < this.bars.length; i++) {
      if (this.bars[i].index === ev.event_bar_index) { t = i; break; }
    }
    if (t === null) return;
    var from = Math.max(0, t - 70);
    var to = Math.min(this.bars.length - 1, t + 70);
    this.chart.timeScale().setVisibleRange({ from: this.bars[from].time, to: this.bars[to].time });
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

    for (var k = 0; k < this.events.length; k++) {
      var e = this.events[k];
      if (e.confirmed_bar_index > cursor) continue;   // chưa xác nhận tại thời điểm replay
      push(this.eventsAtBar, e.event_bar_index, e);
      if (e.confirmed_bar_index !== e.event_bar_index) push(this.eventsAtBar, e.confirmed_bar_index, e);

      var t = e.structure_type;
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
        size: showL2 ? 2 : 1
      });
    });

    markers = markers.concat(bosMarkers).filter(function (m) { return m.time !== undefined; });
    markers.sort(function (a, b) { return a.time - b.time; });
    this.candles.setMarkers(markers);

    // --- đường mức swing đang hoạt động (do lõi thuật toán sinh) ---
    if (layers.levels) {
      var hi = [], lo = [];
      for (var j = 0; j < this.timeline.length; j++) {
        var p = this.timeline[j];
        if (p.bar_index > cursor) break;
        if (p.muc_high !== null && p.muc_high !== undefined) hi.push({ time: p.time, value: p.muc_high });
        if (p.muc_low !== null && p.muc_low !== undefined) lo.push({ time: p.time, value: p.muc_low });
      }
      this.levelHigh.setData(hi);
      this.levelLow.setData(lo);
    } else {
      this.levelHigh.setData([]);
      this.levelLow.setData([]);
    }
  };

  MarketChart.prototype._onCrosshair = function (param) {
    var tt = this.tooltipEl;
    if (!tt) return;
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

    var list = (this.eventsAtBar && this.eventsAtBar[bar.index]) || [];
    for (var i = 0; i < list.length && i < 6; i++) {
      var e = list[i];
      var role = (e.event_bar_index === bar.index)
        ? 'Sự kiện tại nến này'
        : 'Được XÁC NHẬN tại nến này';
      html += '<div class="tt-ev"><b>' + e.structure_type + '</b> — ' + (e.structure_text_vi || '') +
              '<br>Giá: <span class="mono">' + Number(e.price).toFixed(d) + '</span>' +
              '<br>' + role +
              '<br>Nến sự kiện: #' + e.event_bar_index + ' (' + fmtIso(e.event_time) + ')' +
              '<br>Xác nhận lúc: ' + fmtIso(e.confirmed_at) + ' — trễ ' + e.confirmation_lag_bars + ' nến' +
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
  global.chartUtils = { fmtTime: fmtTime, fmtIso: fmtIso };
})(window);
