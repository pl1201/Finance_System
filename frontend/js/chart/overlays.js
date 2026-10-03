/* Chart — lớp phủ của trang Đánh giá (TP / FP / FN / nhãn) và trang Gán nhãn (nhãn nháp + đề xuất).
 * Gắn thêm method vào MarketChart; nạp sau chart/market-chart.js.
 */
(function (MarketChart) {
  'use strict';

  var COLORS = {
    swingHigh: '#ffb74d',
    swingLow: '#4dd0e1',
    swingHighL2: '#ffe082',
    swingLowL2: '#80deea',
    bosUp: '#66bb6a',
    bosDown: '#ef5350',
    chochUp: '#26c6da',
    chochDown: '#ff7043',
    bosIntUp: '#9ccc65',
    bosIntDown: '#ef9a9a'
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
})(window.MarketChart);
