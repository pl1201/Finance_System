/* Plugin hiển thị swing_pivot / swing_hierarchy: pivot cấp 1 / cấp 2, nhãn HH/HL/LH/LL và EQH/EQL,
 * sự kiện BOS / CHoCH, đường mức swing đang hoạt động (timeline lõi), loại nhãn tay swing.
 *
 * Là plugin `fallback`: loại sự kiện không plugin nào nhận được vẽ như pivot (gom theo nến + phía),
 * và khung trạng thái replay mặc định (mức swing đang hoạt động) là của plugin này.
 */
(function (MSL) {
  'use strict';

  var LWC = window.LightweightCharts;
  var series = MSL.series;
  var isFiniteNum = MSL.format.isFiniteNum;

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

  var BREAK_TYPES = {
    BOS_UP: 1, BOS_DOWN: 1, BOS_INTERNAL_UP: 1, BOS_INTERNAL_DOWN: 1, CHOCH_UP: 1, CHOCH_DOWN: 1
  };
  var HIGH_TYPES = {
    SWING_HIGH: 1, SWING_HIGH_L2: 1, HH: 1, LH: 1, EQH: 1
  };

  var chart = {
    /** Hai đường mức swing đang hoạt động (do lõi thuật toán sinh, timeline_point). */
    init: function (mc, st) {
      st.levelHigh = mc.chart.addLineSeries({
        color: COLORS.levelHigh, lineWidth: 1, lineStyle: LWC.LineStyle.Dashed,
        lineType: LWC.LineType.WithSteps, priceLineVisible: false,
        lastValueVisible: false, crosshairMarkerVisible: false, title: ''
      });
      st.levelLow = mc.chart.addLineSeries({
        color: COLORS.levelLow, lineWidth: 1, lineStyle: LWC.LineStyle.Dashed,
        lineType: LWC.LineType.WithSteps, priceLineVisible: false,
        lastValueVisible: false, crosshairMarkerVisible: false, title: ''
      });
    },

    clear: function (mc, st) {
      st.levelHigh.setData([]);
      st.levelLow.setData([]);
    },

    begin: function (ctx, st) {
      st.groups = {};   // key: index + '|' + side
    },

    ownsEvent: function (t) { return !!BREAK_TYPES[t]; },

    marker: function (e, ctx, st) {
      var t = e.structure_type;
      var layers = ctx.layers;
      if (BREAK_TYPES[t]) {
        var isChoch = t.indexOf('CHOCH') === 0;
        var isInt = t.indexOf('INTERNAL') !== -1;
        if (isChoch && !layers.choch) return;
        if (!isChoch && !layers.bos) return;
        var up = t.slice(-2) === 'UP';
        var color = isChoch ? (up ? COLORS.chochUp : COLORS.chochDown)
          : (isInt ? (up ? COLORS.bosIntUp : COLORS.bosIntDown) : (up ? COLORS.bosUp : COLORS.bosDown));
        var text = isChoch ? (up ? 'CHoCH↑' : 'CHoCH↓') : (isInt ? (up ? 'iBOS↑' : 'iBOS↓') : (up ? 'BOS↑' : 'BOS↓'));
        ctx.markers.push({
          time: ctx.timeByIndex[e.confirmed_bar_index],
          position: up ? 'belowBar' : 'aboveBar',
          color: color,
          shape: up ? 'arrowUp' : 'arrowDown',
          text: text,
          size: 1
        });
        return;
      }

      var side = HIGH_TYPES[t] ? 'high' : 'low';
      var idx = ctx.opts.markerAtConfirm ? e.confirmed_bar_index : e.event_bar_index;
      var key = idx + '|' + side;
      var g = st.groups[key] || (st.groups[key] = {
        index: idx, side: side, labels: [], hasSwing: false, hasL2: false
      });
      if (t === 'SWING_HIGH' || t === 'SWING_LOW') g.hasSwing = true;
      else if (t === 'SWING_HIGH_L2' || t === 'SWING_LOW_L2') g.hasL2 = true;
      else if (t === 'EQH' || t === 'EQL') { if (layers.eq) g.labels.push(t); }
      else if (layers.hhll) g.labels.push(t);
    },

    /** Pivot gom theo nến + phía → marker đầu danh sách (trước marker theo thứ tự sự kiện). */
    finish: function (ctx, st) {
      var layers = ctx.layers;
      var scale = ctx.chart._markerScale || 1;
      Object.keys(st.groups).forEach(function (key) {
        var g = st.groups[key];
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
        ctx.head.push({
          time: ctx.timeByIndex[g.index],
          position: isHigh ? 'aboveBar' : 'belowBar',
          color: color,
          shape: showL2 ? 'square' : 'circle',
          text: label,
          size: (showL2 ? 2 : 1) * scale
        });
      });
    },

    /**
     * Đường mức swing đang hoạt động. Baseline không có muc_high/low (nhiều điểm null). Đưa null
     * vào LineType.WithSteps rồi setVisibleRange → Lightweight Charts ném "Value is null".
     */
    draw: function (ctx, st) {
      if (ctx.layers.levels) {
        var hi = [], lo = [], sma = [];
        for (var j = 0; j < ctx.timeline.length; j++) {
          var p = ctx.timeline[j];
          if (p.bar_index > ctx.cursor) break;
          if (isFiniteNum(p.muc_high)) hi.push({ time: p.time, value: p.muc_high });
          if (isFiniteNum(p.muc_low)) lo.push({ time: p.time, value: p.muc_low });
          if (isFiniteNum(p.sma)) sma.push({ time: p.time, value: p.sma });
        }
        if (!hi.length && sma.length) {
          series.setLineData(st.levelHigh, sma, { lineType: LWC.LineType.Simple });
        } else {
          series.setLineData(st.levelHigh, hi, { lineType: LWC.LineType.WithSteps });
        }
        series.setLineData(st.levelLow, lo, { lineType: LWC.LineType.WithSteps });
      } else {
        series.setLineData(st.levelHigh, []);
        series.setLineData(st.levelLow, []);
      }
    }
  };

  MSL.algos.register({
    id: 'swing',
    algorithms: ['swing_pivot', 'swing_hierarchy'],
    fallback: true,
    layers: { swing: true, swing_l2: true, hhll: true, eq: true, levels: true, bos: true, choch: true },
    layerHints: {
      swing_hierarchy: 'Cấp 2 = ô vuông. HH/LH chỉ so hai đỉnh/đáy cấp 2 liên tiếp. Không gồm BOS. Đường mức = cấp 2 gần nhất.',
      swing_pivot: 'HH/LH so từng đỉnh cấp 1. BOS/CHoCH là sự kiện phá vỡ riêng — không trộn với nhãn HH.'
    },
    labelTypes: [
      { id: 'SWING_HIGH', label: 'Đỉnh cấp 1', sw: COLORS.swingHigh, short: 'H' },
      { id: 'SWING_LOW', label: 'Đáy cấp 1', sw: COLORS.swingLow, short: 'L' },
      { id: 'SWING_HIGH_L2', label: 'Đỉnh cấp 2', sw: COLORS.swingHighL2, short: 'H2' },
      { id: 'SWING_LOW_L2', label: 'Đáy cấp 2', sw: COLORS.swingLowL2, short: 'L2' },
      { id: 'BOS_UP', label: 'BOS lên', sw: COLORS.bosUp, short: 'BU' },
      { id: 'BOS_DOWN', label: 'BOS xuống', sw: COLORS.bosDown, short: 'BD' },
      { id: 'CHOCH_UP', label: 'CHoCH lên', sw: COLORS.chochUp, short: 'CU' },
      { id: 'CHOCH_DOWN', label: 'CHoCH xuống', sw: COLORS.chochDown, short: 'CD' },
      { id: 'BOS_INTERNAL_UP', label: 'BOS nội bộ lên', sw: COLORS.bosIntUp, short: 'IU' },
      { id: 'BOS_INTERNAL_DOWN', label: 'BOS nội bộ xuống', sw: COLORS.bosIntDown, short: 'ID' }
    ],
    chart: chart,

    /** Trạng thái replay mặc định: mức swing đang hoạt động (thuật toán khác không có thì hiện «—»). */
    pendingHtml: function (ps, d) {
      return '<div class="info-card"><dl>' +
        '<dt>Mức swing high đang hoạt động</dt><dd class="mono">' + (ps.muc_swing_high_dang_hoat_dong ? Number(ps.muc_swing_high_dang_hoat_dong.gia).toFixed(d) + ' (nến #' + ps.muc_swing_high_dang_hoat_dong.nen + ')' : '— chưa có —') + '</dd>' +
        '<dt>Mức swing low đang hoạt động</dt><dd class="mono">' + (ps.muc_swing_low_dang_hoat_dong ? Number(ps.muc_swing_low_dang_hoat_dong.gia).toFixed(d) + ' (nến #' + ps.muc_swing_low_dang_hoat_dong.nen + ')' : '— chưa có —') + '</dd>' +
        '<dt>Số mức high đã bị phá</dt><dd>' + (ps.so_muc_high_da_pha !== undefined ? ps.so_muc_high_da_pha : '—') + '</dd>' +
        '<dt>Số mức low đã bị phá</dt><dd>' + (ps.so_muc_low_da_pha !== undefined ? ps.so_muc_low_da_pha : '—') + '</dd>' +
        '<dt>Nến chưa đủ cửa sổ phải</dt><dd class="mono">' + ((ps.nen_dang_cho_xac_nhan || []).join(', ') || '—') + '</dd>' +
        '</dl></div>';
    },

    /** Chú giải cấp 2 dưới chart: chỉ hiện khi lần chạy (của thuật toán plugin này vẽ) có pivot cấp 2.
     * Thuật toán khác dùng chung loại SWING_*_L2 (vd ict_structure) có cách vẽ và chú giải riêng. */
    syncLegend: function (timeline, events) {
      var legend = document.querySelector('#chart-legend');
      if (!legend) return;
      var mine = this.algorithms;
      var hasL2 = (events || []).some(function (e) {
        return (e.structure_type === 'SWING_HIGH_L2' || e.structure_type === 'SWING_LOW_L2') &&
          (!e.algorithm || mine.indexOf(e.algorithm) !== -1);
      });
      legend.hidden = !hasL2;
    }
  });
})(window.MSL);
