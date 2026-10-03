/* Plugin hiển thị dc_atr_structure: pivot DC theo close + đường nối, ứng viên (nét đứt) và mức xác nhận,
 * biên Range khoá, dải trạng thái regime ở đáy chart, ẩn chữ nhãn khi zoom xa; tooltip, ghi chú,
 * chỉ số hành vi, trạng thái replay, panel chi tiết sự kiện, khung «Thuật toán đang làm gì»,
 * so sánh baseline pivot 3/3 và ánh xạ chấm chéo ở trang Đánh giá.
 */
(function (MSL) {
  'use strict';

  var LWC = window.LightweightCharts;
  var series = MSL.series;
  var isFiniteNum = MSL.format.isFiniteNum;
  var fmtIso = MSL.format.fmtIso;
  var esc = MSL.dom.esc;
  var TRANSPARENT = series.TRANSPARENT;

  var COLORS = {
    dcLine: 'rgba(236,239,241,.85)',
    dcCand: 'rgba(236,239,241,.55)',
    dcHigh: '#ff8a65',
    dcLow: '#64b5f6',
    dcConfirm: '#fff176',
    dcLevel: 'rgba(255,241,118,.8)',
    rangeLine: 'rgba(251,192,45,.85)',
    dataq: '#607d8b'
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
    return series.rangeSeriesData(rows, 'lvl', 'lid', cursor);
  }

  // ------------------------------------------------------------------ chart

  /** Mật độ hiển thị hiện tại: true khi các marker DC trong khung nhìn dày hơn ~1 / COMPACT_PX_PER_LABEL px. */
  function isCompactNow(mc, st) {
    var r = null;
    try { r = mc.chart.timeScale().getVisibleLogicalRange(); } catch (e) { r = null; }
    if (!r || !st.markerPos.length) return false;
    var n = 0;
    for (var i = 0; i < st.markerPos.length; i++) {
      var q = st.markerPos[i];
      if (q >= r.from && q <= r.to) n++;
    }
    return n > 1 && (mc.container.clientWidth / n) < COMPACT_PX_PER_LABEL;
  }

  /** Chỉ đổi phần vẽ (chữ trên marker), không đổi dữ liệu hay sự kiện. */
  function applyMarkers(mc, st) {
    var strip = function (list) {
      return list.map(function (m) { var x = Object.assign({}, m); x.text = ''; return x; });
    };
    st.line.setMarkers(mc._compact ? strip(st.markers) : st.markers);
    st.cand.setMarkers(mc._compact ? strip(st.candMarkers) : st.candMarkers);
  }

  var chart = {
    /** Đường nối pivot close đã xác nhận, đoạn tới ứng viên (nét đứt), biên Range khoá, dải regime ở đáy. */
    init: function (mc, st) {
      st.line = mc.chart.addLineSeries(series.simpleLineOpts(COLORS.dcLine, 2, LWC.LineStyle.Solid));
      st.cand = mc.chart.addLineSeries(series.simpleLineOpts(COLORS.dcCand, 1, LWC.LineStyle.Dashed));
      st.level = mc.chart.addLineSeries(series.stepLineOpts(COLORS.dcLevel, 1, LWC.LineStyle.Dotted));
      st.rangeUpper = mc.chart.addLineSeries(series.stepLineOpts(COLORS.rangeLine, 1, LWC.LineStyle.LargeDashed));
      st.rangeLower = mc.chart.addLineSeries(series.stepLineOpts(COLORS.rangeLine, 1, LWC.LineStyle.LargeDashed));
      st.regimeBand = mc.chart.addHistogramSeries({
        priceScaleId: 'regime', priceLineVisible: false, lastValueVisible: false, base: 0,
        priceFormat: { type: 'custom', formatter: function () { return ''; } }
      });
      mc.chart.priceScale('regime').applyOptions({ scaleMargins: { top: 0.955, bottom: 0 }, visible: false });
      st.timelineByIndex = {};
      st.markers = [];
      st.candMarkers = [];
      st.markerPos = [];
    },

    clear: function (mc, st) {
      [st.line, st.cand, st.level, st.rangeUpper, st.rangeLower, st.regimeBand].forEach(function (s) { s.setData([]); });
      st.line.setMarkers([]);
      st.cand.setMarkers([]);
    },

    begin: function (ctx, st) {
      st.pivots = [];
    },

    ownsEvent: function (t) { return !!DC_EVENT_TYPES[t]; },

    /** Pivot: gom lại để vẽ ở draw(); ô xác nhận / gap vào marker nến. Regime event: chỉ dải trạng thái + tooltip. */
    marker: function (e, ctx, st) {
      var t = e.structure_type;
      var layers = ctx.layers;
      if (t === 'DC_HIGH' || t === 'DC_LOW') {
        st.pivots.push(e);
        if (layers.dc_confirm || e.event_id === ctx.selectedId) {
          // inBar trên nến = đúng close của nến xác nhận (confirmation_close).
          ctx.markers.push({
            time: ctx.timeByIndex[e.confirmed_bar_index], position: 'inBar', color: COLORS.dcConfirm,
            shape: 'square', text: e.event_id === ctx.selectedId ? '✓ xác nhận' : '✓', size: 0.6
          });
        }
      } else if ((t === 'DC_SEGMENT_GAP' || t === 'DC_GAP_BRIDGED') && layers.regime) {
        ctx.markers.push({
          time: ctx.timeByIndex[e.confirmed_bar_index], position: 'belowBar', color: COLORS.dataq,
          shape: t === 'DC_SEGMENT_GAP' ? 'square' : 'circle',
          text: t === 'DC_SEGMENT_GAP' ? 'gap' : 'nối', size: 0.5
        });
      }
    },

    /**
     * Đường nối pivot CLOSE đã xác nhận (chỉ khi cả hai đầu đã xác nhận ≤ con trỏ), đoạn nét đứt
     * tới ứng viên, biên Range khoá (từ nến sau lúc vào Range tới exit), dải trạng thái theo
     * timeline lõi (bắt đầu lúc biết). Không nối qua gap: điểm cuối mỗi segment trong suốt nên
     * đoạn đi ra bị ẩn.
     */
    draw: function (ctx, st) {
      var mc = ctx.chart;
      var layers = ctx.layers, cursor = ctx.cursor, timeByIndex = ctx.timeByIndex, selectedId = ctx.selectedId;
      var tl = ctx.timeline || [];
      var isDc = tl.length && Object.prototype.hasOwnProperty.call(tl[tl.length - 1], 'dc_phase');
      st.timelineByIndex = {};
      if (!isDc) {
        st.line.setMarkers([]); series.setLineData(st.line, []);
        st.cand.setMarkers([]); series.setLineData(st.cand, []);
        series.setGapLineData(st.level, []);
        series.setGapLineData(st.rangeUpper, []); series.setGapLineData(st.rangeLower, []);
        st.regimeBand.setData([]);
        return;
      }
      var lastPt = null;
      for (var j = 0; j < tl.length; j++) {
        if (tl[j].bar_index > cursor) break;
        st.timelineByIndex[tl[j].bar_index] = tl[j];
        lastPt = tl[j];
      }

      // --- đường nối pivot + marker tại đúng giá close ---
      var dcPivots = st.pivots;
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
      st.line.applyOptions({ visible: pts.length > 1 || mks.length > 0 });
      st.line.setData(pts);
      st.markers = mks;
      var posMap = mc._posByTime || {};
      st.markerPos = mks.map(function (m) { return posMap[m.time]; })
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
      st.cand.applyOptions({ visible: cand.length > 0 });
      st.cand.setData(cand);
      st.candMarkers = candMk;
      mc._compact = isCompactNow(mc, st);
      applyMarkers(mc, st);

      // --- mức xác nhận của ứng viên (ứng viên ∓ Δ đã khoá), từ nến sau lúc đặt ---
      series.setGapLineData(st.level, layers.dc_candidate ? candidateLevelData(tl, cursor) : []);

      // --- Range khoá ---
      series.setGapLineData(st.rangeUpper, layers.range ? series.rangeSeriesData(tl, 'range_upper', 'range_id', cursor) : []);
      series.setGapLineData(st.rangeLower, layers.range ? series.rangeSeriesData(tl, 'range_lower', 'range_id', cursor) : []);

      // --- dải trạng thái ---
      var band = [];
      if (layers.regime) {
        for (var r = 0; r < tl.length; r++) {
          var q = tl[r];
          if (q.bar_index > cursor) break;
          band.push({ time: q.time, value: 1, color: REGIME_COLORS[q.regime] || REGIME_COLORS.UNKNOWN });
        }
      }
      st.regimeBand.setData(band);
    },

    /** Zoom / cuộn: bật-tắt chữ nhãn theo mật độ marker trong khung nhìn. */
    onRangeChange: function (mc, st) {
      var c = isCompactNow(mc, st);
      if (c === mc._compact) return;
      mc._compact = c;
      applyMarkers(mc, st);
      if (mc._onCompactChange) mc._onCompactChange(c);
    },

    /** Dòng trạng thái regime sau nến (theo timeline lõi tới con trỏ). */
    tooltipBar: function (mc, bar, d, st) {
      var tp = st.timelineByIndex && st.timelineByIndex[bar.index];
      if (!tp) return '';
      return '<div class="tt-rule">Trạng thái sau nến này (theo swing DC đã xác nhận): <b>' +
        (REGIME_TEXT_VI[tp.regime] || tp.regime) + '</b>' +
        (isFiniteNum(tp.atr) ? ' · ATR ' + tp.atr.toFixed(d) : ' · chưa có ATR') +
        (isFiniteNum(tp.range_upper) ? '<br>Range khoá [' + tp.range_lower.toFixed(d) + ', ' + tp.range_upper.toFixed(d) +
          '], buffer ' + tp.range_buffer.toFixed(d) : '') + '</div>';
    },

    tooltipEvent: function (e, d) {
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
  };

  // ------------------------------------------------------------------ trang Thử nghiệm

  /** Ghi chú: close vs wick, gap/segment, warm-up, UNKNOWN, nhãn, baseline. */
  function notes(stats, dataStatus, pending, S) {
    var m = (stats && stats.chi_so_thuat_toan) || null;
    var ps = pending || {};
    var out = [];
    out.push(['info', '<strong>DC theo CLOSE</strong>: đỉnh/đáy là close của nến cực trị, xác nhận khi close đảo chiều ≥ Δ (k×ATR hoặc % khoá tại cực trị). ' +
      'Trend/Range là <strong>định nghĩa vận hành của lab</strong> (HH+HL, LH+LL, cụm đỉnh/đáy) — không phải dự báo hay tín hiệu giao dịch.']);
    if (S.dataset && S.dataset.is_synthetic) {
      out.push(['warn', 'Dataset <strong>MÔ PHỎNG</strong> — số liệu chỉ để thử công cụ, không mô tả thị trường thật.']);
    }
    if (dataStatus === 'WARMUP_INSUFFICIENT') {
      out.push(['warn', '<strong>Warm-up:</strong> cần ATR period + 1 nến liên tục trong MỖI segment trước khi detector khởi tạo.']);
    }
    var gaps = m ? m.so_gap : ps.so_gap;
    var segs = m ? m.so_segment : ps.so_segment;
    var bridged = m ? m.so_gap_noi : ps.so_gap_noi;
    var policy = (m && m.gap_policy) || ps.gap_policy || 'reset';
    if (policy === 'bridge_short') {
      var hrs = S.run && S.run.params ? S.run.params.bridge_max_gap_hours : '?';
      out.push(['warn', '<strong>Gap dữ liệu (gap_policy=bridge_short, ≤ ' + esc(hrs) + ' giờ):</strong> ' + (bridged || 0) +
        ' gap ngắn được NỐI (giữ ứng viên, ATR, lịch sử; TR tính cả bước nhảy qua gap; marker «nối»), ' + (gaps || 0) +
        ' gap dài bị reset → ' + segs + ' segment. Nối là lựa chọn phương pháp, không phải dữ liệu liền mạch. Chưa dùng lịch phiên broker.']);
    } else if (gaps) {
      out.push(['warn', '<strong>Gap dữ liệu:</strong> ' + gaps + ' gap → ' + segs + ' segment (gap_policy=reset). ' +
        'Mỗi gap — kể cả nghỉ phiên hằng ngày và cuối tuần — bỏ ứng viên, ATR, lịch sử trend/range và warm-up lại; không nối swing qua gap. ' +
        'Chưa suy đoán lịch phiên broker, nên mỗi phiên bắt đầu ở «Chưa rõ». Có thể thử gap_policy=bridge_short.']);
    }
    if (m && m.regime_ty_le_thoi_gian && m.regime_ty_le_thoi_gian.UNKNOWN !== null && m.regime_ty_le_thoi_gian.UNKNOWN > 0.5) {
      out.push(['info', '«Chưa rõ» chiếm <strong>' + (m.regime_ty_le_thoi_gian.UNKNOWN * 100).toFixed(1) + '%</strong> thời gian sau warm-up: thiếu hoặc mâu thuẫn bằng chứng swing — không bị ép thành Range.']);
    }
    if (m && m.so_pivot_xac_nhan === 0) {
      out.push(['warn', 'Không có pivot DC xác nhận. Không phải lỗi dữ liệu — thử giảm k hoặc dùng khoảng dài hơn.']);
    }
    if (S.baseline && S.layers.baseline) {
      out.push(['warn', '<strong>So sánh baseline:</strong> pivot baseline (swing_pivot 3/3, run <code>' + esc(S.baseline.run_id || '(không lưu)') + '</code>) theo <strong>WICK</strong>, DC theo <strong>CLOSE</strong> — ' +
        'chênh giá marker là khác định nghĩa, không phải lỗi. Đây là so sánh trải nghiệm tổng thể (khác cả ngưỡng lẫn nguồn giá).']);
    }
    out.push(['info', 'Chưa có nhãn tham chiếu cho swing close / đoạn regime — không hiển thị F1 hay confusion matrix.']);
    return out;
  }

  function runWarning(res) {
    var n = res.events.filter(function (e) { return e.structure_type === 'DC_HIGH' || e.structure_type === 'DC_LOW'; }).length;
    if (n !== 0) return null;
    return 'Chạy xong nhưng <strong>chưa có pivot DC nào được xác nhận</strong>. Dữ liệu vẫn hợp lệ — có thể ngưỡng quá lớn so với biên độ, hoặc mỗi segment (giữa hai gap) quá ngắn sau warm-up. Xem ghi chú phía trên.';
  }

  /** Metric không cần nhãn — mô tả hành vi, không phải accuracy. */
  function statsHtml(m) {
    function box(k, v, title) {
      return '<div class="stat-box"' + (title ? ' title="' + esc(title) + '"' : '') + '><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }
    function num(x, dg) { return x === null || x === undefined ? '—' : Number(x).toFixed(dg === undefined ? 2 : dg); }
    function sm(s, dg) { return s && s.n ? num(s.trung_vi, dg) + ' / ' + num(s.p90, dg) + ' (n=' + s.n + ')' : '—'; }
    var TXT = REGIME_TEXT_VI, COL = REGIME_COLORS;
    var share = m.regime_ty_le_thoi_gian || {};
    var html = '<div class="section-title">DC + regime (không cần nhãn — mô tả hành vi, không phải accuracy)</div>';
    html += '<div class="stat-grid">' +
      box('Pivot xác nhận', m.so_pivot_xac_nhan + ' (' + m.so_dinh + ' đỉnh / ' + m.so_day + ' đáy)') +
      box('Mật độ / 1.000 nến', num(m.mat_do_tren_1000_nen, 1), m.mat_do_ghi_chu_vi) +
      box('Trễ xác nhận (nến) TV / P90', sm(m.do_tre_nen, 1)) +
      box('Trễ (phút) TV / P90', sm(m.do_tre_phut, 0)) +
      box('Đảo chiều / ATR cực trị TV / P90', sm(m.reversal_distance_atr), m.reversal_ghi_chu_vi) +
      box('Biên độ nhịp / ATR TV / P90', sm(m.bien_do_nhip_atr), m.bien_do_ghi_chu_vi) +
      box('Lần chuyển trạng thái', m.so_lan_chuyen_trang_thai) +
      box('Độ dài đoạn TV (nến)', num(m.do_dai_doan_trung_vi_tat_ca, 0)) +
      box('Gap reset / nối / segment', m.so_gap + ' / ' + (m.so_gap_noi || 0) + ' / ' + m.so_segment, 'gap_policy=' + (m.gap_policy || 'reset')) +
      box('Nến đủ điều kiện / tổng', m.so_nen_du_dieu_kien + ' / ' + m.so_nen) +
      '</div>';
    html += '<div class="section-title">Tỷ lệ thời gian theo trạng thái (sau warm-up, không tính gap)</div>';
    html += '<div class="regime-share" role="img" aria-label="Tỷ lệ thời gian theo trạng thái">';
    ['UPTREND', 'DOWNTREND', 'RANGE', 'UNKNOWN'].forEach(function (k) {
      var v = share[k] || 0;
      if (v > 0) html += '<span style="width:' + (v * 100).toFixed(2) + '%;background:' + COL[k] + '" title="' + esc(TXT[k]) + ' ' + (v * 100).toFixed(1) + '%"></span>';
    });
    html += '</div><table class="data-table"><thead><tr><th>Trạng thái</th><th>Số nến</th><th>Tỷ lệ</th><th>Độ dài đoạn TV (nến)</th></tr></thead><tbody>';
    ['UPTREND', 'DOWNTREND', 'RANGE', 'UNKNOWN'].forEach(function (k) {
      html += '<tr><td>' + esc(TXT[k]) + '</td><td class="num">' + ((m.regime_so_nen || {})[k] || 0) + '</td>' +
        '<td class="num">' + (share[k] === null || share[k] === undefined ? '—' : (share[k] * 100).toFixed(1) + '%') + '</td>' +
        '<td class="num">' + num((m.do_dai_doan_trung_vi_nen || {})[k], 0) + '</td></tr>';
    });
    html += '</tbody></table>';
    var labs = m.nhan_so_sanh || {};
    html += '<p class="hint">Nhãn swing: ' + Object.keys(labs).sort().map(function (k) { return esc(k) + ' ' + labs[k]; }).join(' · ') + '</p>';
    html += '<p class="hint">' + esc((m.nhan_tham_chieu || {}).ghi_chu_vi || '') + ' ' + esc(m.ghi_chu_vi || '') + '</p>';
    return html;
  }

  /** Trạng thái nội bộ tại con trỏ replay: dựng lại từ đầu khi lùi, không đọc trạng thái cuối run. */
  function pendingHtml(ps, d) {
    if (!ps.dc) return null;
    function f(x) { return x === null || x === undefined ? '—' : Number(x).toFixed(d); }
    var dc = ps.dc || {}, c = dc.ung_vien, cl = ps.classifier || {}, rg = cl.range;
    return '<div class="info-card"><dl>' +
      '<dt>Trạng thái (theo swing đã xác nhận)</dt><dd><strong>' + esc(ps.regime_vi) + '</strong> — ' + esc(cl.ly_do_vi || '') + '</dd>' +
      '<dt>Pha detector</dt><dd>' + esc(dc.phase_vi || dc.phase) + (dc.ly_do_cho ? ' · ' + esc(dc.ly_do_cho) : '') + '</dd>' +
      '<dt>ATR hiện tại</dt><dd class="mono">' + f(ps.atr_hien_tai) + '</dd>' +
      (dc.anchor ? '<dt>Anchor</dt><dd class="mono">' + f(dc.anchor.price) + ' ± ' + f(dc.anchor.delta) + ' (nến #' + dc.anchor.index + ')</dd>' : '') +
      '<dt>Ứng viên (chưa xác nhận)</dt><dd class="mono">' + (c
        ? (c.side === 'high' ? 'đỉnh ' : 'đáy ') + f(c.candidate_price) + ' @ #' + c.candidate_index + ' · Δ khoá ' + f(c.delta_e) +
          ' (ATR ' + f(c.candidate_atr) + ') · xác nhận khi close ' + (c.side === 'high' ? '≤ ' : '≥ ') + f(c.muc_xac_nhan)
        : '— không có —') + '</dd>' +
      '<dt>Range đang khoá</dt><dd class="mono">' + (rg ? '[' + f(rg.lower) + ', ' + f(rg.upper) + '] · buffer ' + f(rg.buffer) + ' · từ #' + rg.start_index : '—') + '</dd>' +
      '<dt>Pivot trong segment</dt><dd>' + (cl.so_dinh_xac_nhan || 0) + ' đỉnh (' + esc(cl.nhan_dinh_gan_nhat || '—') + ') · ' + (cl.so_day_xac_nhan || 0) + ' đáy (' + esc(cl.nhan_day_gan_nhat || '—') + ')</dd>' +
      '<dt>Segment / gap</dt><dd>#' + ps.segment + ' (từ nến #' + ps.segment_bat_dau_tu_nen + ') · ' + ps.so_gap + ' gap reset · ' + (ps.so_gap_noi || 0) + ' gap nối (' + esc(ps.gap_policy) + ')</dd>' +
      '</dl><p class="hint">' + esc(ps.ghi_chu_vi || '') + '</p></div>';
  }

  /** Panel giải thích một sự kiện: công thức với số thực tế, tham chiếu, lúc biết. */
  function eventDetail(e, S) {
    var x = e.details || {};
    var d = S.digits;
    var f = function (v) { return v === null || v === undefined ? '—' : Number(v).toFixed(d); };
    var TXT = REGIME_TEXT_VI;
    var rows = [];
    function row(k, v) { rows.push('<dt>' + esc(k) + '</dt><dd>' + v + '</dd>'); }
    row('Loại', esc(e.structure_type) + ' — ' + esc(e.structure_text_vi || ''));
    row('Nến sự kiện', '#' + e.event_bar_index + ' · ' + esc(fmtIso(e.event_time)));
    row('Biết lúc (confirmed_at)', '#' + e.confirmed_bar_index + ' · ' + esc(fmtIso(e.confirmed_at)) + ' · trễ ' + e.confirmation_lag_bars + ' nến');
    row('Segment', esc(x.segment));
    if (e.structure_type === 'DC_HIGH' || e.structure_type === 'DC_LOW') {
      row('Giá (theo close)', f(e.price) + ' — không phải ' + (e.structure_type === 'DC_HIGH' ? 'high' : 'low') + ' của nến');
      row('Ngưỡng khoá', esc(x.cong_thuc_nguong) + ' · đặt lúc ' + esc(fmtIso(x.threshold_set_at)));
      row('Điều kiện xác nhận', esc(x.dieu_kien_xac_nhan));
      row('Khoảng đảo chiều', f(x.reversal_distance) + ' = ' + Number(x.reversal_distance_atr).toFixed(2) + ' × ATR tại cực trị');
      row('Nhãn so sánh', x.nhan
        ? esc(x.nhan) + ': ' + f(x.nhan_gia_nay) + ' so với ' + f(x.nhan_gia_truoc) + ' (chênh ' + f(x.nhan_chenh_lech) + ', dung sai ±' + f(x.nhan_dung_sai) + ' = ' + esc(S.run && S.run.params ? S.run.params.label_tolerance_atr : '') + ' × ATR tại cực trị)'
        : 'Pivot đầu cùng loại trong segment — chưa so sánh');
      row('Tham chiếu', esc(e.reference_event_id || '—'));
      if (x.nhip) row('Nhịp từ pivot trước', f(x.nhip.bien_do) + ' = ' + Number(x.nhip.bien_do_atr).toFixed(2) + ' × ATR pivot đầu nhịp');
    } else if (e.structure_type === 'DC_GAP_BRIDGED') {
      row('Gap được nối', (x.khoang_cach_giay / 60) + ' phút (≤ ' + esc(x.bridge_max_gap_hours) + ' giờ) · không reset segment');
      row('Bước nhảy', 'open − close trước gap = ' + f(x.buoc_nhay_open) + ' (tính vào TR/ATR)');
      row('Ứng viên giữ nguyên', x.ung_vien_giu_nguyen ? f(x.ung_vien_giu_nguyen.candidate_price) + ' (nến #' + x.ung_vien_giu_nguyen.candidate_index + ')' : '—');
    } else if (e.structure_type === 'DC_SEGMENT_GAP') {
      row('Gap', (x.khoang_cach_giay / 60) + ' phút (' + Number(x.so_buoc_khung).toFixed(2) + ' bước khung)');
      row('Trước gap', 'nến #' + x.nen_truoc_gap + ' · trạng thái ' + esc(TXT[x.regime_truoc_gap] || x.regime_truoc_gap));
      row('Ứng viên bị bỏ', x.ung_vien_bi_bo ? f(x.ung_vien_bi_bo.candidate_price) + ' (nến #' + x.ung_vien_bi_bo.candidate_index + ')' : '—');
    } else {
      row('Chuyển trạng thái', esc(TXT[x.tu_trang_thai] || x.tu_trang_thai) + ' → <b>' + esc(TXT[x.sang_trang_thai] || x.sang_trang_thai) + '</b>');
      row('Giải thích', esc(x.giai_thich_vi || ''));
      if (x.bang_chung && x.bang_chung.length) row('Bằng chứng', esc(x.bang_chung.join(', ')));
      var rg = x.range || x.range_dong;
      if (rg) row(x.range ? 'Range' : 'Range vừa đóng', '[' + f(rg.lower) + ', ' + f(rg.upper) + '] · buffer ' + f(rg.buffer) + ' · ATR khoá ' + f(rg.atr_luc_vao) + ' · từ nến #' + rg.start_index);
      if (x.kiem_tra_range && !x.kiem_tra_range.dat) row('Range không đạt', esc(x.kiem_tra_range.ly_do_vi || ''));
      if (x.close_pha !== undefined) row('Close phá', f(x.close_pha) + ' vs ngưỡng ' + f(x.nguong_pha) + ' · xét lại từ nến #' + x.chi_xet_lai_tu_nen);
    }
    return '<h4>Chi tiết sự kiện được chọn</h4><dl>' + rows.join('') + '</dl>';
  }

  /** Khung «Thuật toán đang làm gì» tại nến `bar` (= con trỏ replay) — chỉ đọc snapshot/sự kiện đã có. */
  function explain(r, bar, S) {
    function f2(x) { return x === null || x === undefined || !isFinite(x) ? '—' : Number(x).toFixed(S.digits); }
    var i = r.cursor;
    var snap = r.snapshot, ps = snap.pending_state || {}, dc = ps.dc || {}, cl = ps.classifier || {};
    var params = snap.params || {};
    var out = [];
    function add(kind, html) { out.push('<div class="xp xp-' + kind + '">' + html + '</div>'); }

    // 1. Điều gì vừa xảy ra ở nến này
    out.push('<div class="xp-sec">Nến này: close = ' + f2(bar.close) + ' (chỉ dùng CLOSE; high/low chỉ để tính ATR)</div>');
    var here = [];
    for (var k = r.events.length - 1; k >= 0 && r.events[k].confirmed_bar_index >= i; k--) {
      if (r.events[k].confirmed_bar_index === i) here.unshift(r.events[k]);
    }
    var pivotHere = false;
    here.forEach(function (e) {
      var x = e.details || {};
      if (e.structure_type === 'DC_HIGH' || e.structure_type === 'DC_LOW') {
        pivotHere = true;
        var hi = e.structure_type === 'DC_HIGH';
        add('ok', '<b>Xác nhận ' + (hi ? 'ĐỈNH' : 'ĐÁY') + ' DC</b> tại nến #' + e.event_bar_index + ' (close ' + f2(e.price) + '): ' +
          esc(x.dieu_kien_xac_nhan) + '. Biết sau ' + e.confirmation_lag_bars + ' nến. ' +
          (x.nhan
            ? 'Nhãn <b>' + esc(x.nhan) + '</b>: so với ' + (hi ? 'đỉnh' : 'đáy') + ' trước ' + f2(x.nhan_gia_truoc) + ', chênh ' + f2(x.nhan_chenh_lech) + ' (dung sai ±' + f2(x.nhan_dung_sai) + ').'
            : 'Là ' + (hi ? 'đỉnh' : 'đáy') + ' đầu tiên trong segment nên chưa có nhãn so sánh.') +
          ' Từ nến này chuyển sang theo dõi ' + (hi ? 'ĐÁY' : 'ĐỈNH') + ', ứng viên mới = close hiện tại.');
      } else if (e.structure_type === 'DC_SEGMENT_GAP') {
        add('warn', '<b>Gap ' + Math.round(x.khoang_cach_giay / 60) + ' phút</b> → reset segment: bỏ ứng viên, ATR, lịch sử pivot/trạng thái; warm-up lại từ nến này.');
      } else if (e.structure_type === 'DC_GAP_BRIDGED') {
        add('info', '<b>Gap ' + Math.round(x.khoang_cach_giay / 60) + ' phút được NỐI</b> (≤ ' + esc(x.bridge_max_gap_hours) + ' giờ): giữ ứng viên, ATR, lịch sử; bước nhảy ' + f2(x.buoc_nhay_open) + ' được tính vào ATR.');
      } else {
        var TXT = REGIME_TEXT_VI;
        add('info', '<b>Trạng thái: ' + esc(TXT[x.tu_trang_thai] || x.tu_trang_thai) + ' → ' + esc(TXT[x.sang_trang_thai] || x.sang_trang_thai) + '</b>. ' + esc(x.giai_thich_vi || ''));
      }
    });
    var prev = r.prev && r.prev.cursor === i - 1 && r.prev.pending ? r.prev.pending : null;
    var pdc = prev ? (prev.dc || {}) : null, c = dc.ung_vien, pc = pdc ? pdc.ung_vien : null;
    if (prev && !pivotHere) {
      if (pdc.phase === 'WARMUP' && dc.phase === 'SEEK_DIRECTION' && dc.anchor) {
        add('info', 'ATR vừa đủ → đặt <b>anchor</b> = close ' + f2(dc.anchor.price) + ', Δ = ' + f2(dc.anchor.delta) + '. Không phát pivot ở anchor; chờ giá đi đủ Δ để chọn hướng.');
      } else if (pdc.phase === 'SEEK_DIRECTION' && c) {
        add('info', 'Close ' + f2(bar.close) + (c.side === 'high' ? ' ≥ anchor + Δ' : ' ≤ anchor − Δ') + ' → chọn hướng <b>' + (c.side === 'high' ? 'LÊN' : 'XUỐNG') +
          '</b>: bắt đầu theo dõi ' + (c.side === 'high' ? 'đỉnh' : 'đáy') + ' với ứng viên = close nến này.');
      } else if (c && pc && c.side === pc.side && c.candidate_index !== pc.candidate_index) {
        add('info', 'Close ' + f2(bar.close) + (c.side === 'high' ? ' > ' : ' < ') + 'ứng viên cũ ' + f2(pc.candidate_price) +
          ' → <b>ứng viên dời</b> sang nến này; Δ khoá lại = ' + f2(c.delta_e) + ' (ATR ' + f2(c.candidate_atr) + ').');
      } else if (c && pc && c.candidate_index === pc.candidate_index) {
        add('muted', 'Không đổi: close chưa ' + (c.side === 'high' ? 'cao hơn' : 'thấp hơn') + ' ứng viên và chưa chạm mức xác nhận. Δ vẫn giữ giá trị đã khoá dù ATR đổi.');
      } else if (pdc.phase === 'SEEK_DIRECTION' && dc.phase === 'SEEK_DIRECTION') {
        add('muted', 'Không đổi: close ' + f2(bar.close) + ' vẫn nằm trong anchor ± Δ nên chưa chọn hướng.');
      } else if (dc.phase === 'WARMUP') {
        add('muted', 'Đang warm-up: chưa đủ nến để có ATR, detector chưa làm gì.');
      }
    } else if (!prev && !here.length) {
      add('muted', 'Vừa nhảy tới nến này (không phải bước 1 nến) — chỉ mô tả trạng thái hiện tại.');
    }

    // 2. Trạng thái hiện tại của detector
    out.push('<div class="xp-sec">Detector DC (' + esc(dc.phase_vi || dc.phase || '') + ')</div>');
    if (dc.phase === 'WARMUP') {
      add('state', 'Warm-up ATR: cần ' + ((params.atr_period || 14) + 1) + ' nến liên tục trong segment (segment bắt đầu ở nến #' + ps.segment_bat_dau_tu_nen + '). Chưa tìm cực trị.');
    } else if (dc.phase === 'WAIT_ATR') {
      add('state', esc(dc.ly_do_cho || 'Chờ ATR > 0.'));
    } else if (dc.phase === 'SEEK_DIRECTION' && dc.anchor) {
      var a = dc.anchor;
      add('state', 'Chờ chọn hướng: anchor ' + f2(a.price) + ' ± Δ ' + f2(a.delta) + ' → cần close ≥ <b>' + f2(a.price + a.delta) + '</b> (lên) hoặc ≤ <b>' + f2(a.price - a.delta) + '</b> (xuống).');
    } else if (c) {
      var hi2 = c.side === 'high';
      var gap = hi2 ? bar.close - c.muc_xac_nhan : c.muc_xac_nhan - bar.close;
      var moved = hi2 ? c.candidate_price - bar.close : bar.close - c.candidate_price;
      var pct = Math.max(0, Math.min(1, c.delta_e > 0 ? moved / c.delta_e : 0));
      add('state', 'Đang theo dõi <b>' + (hi2 ? 'ĐỈNH' : 'ĐÁY') + '</b>: ứng viên close ' + f2(c.candidate_price) + ' @ nến #' + c.candidate_index +
        ' (chưa phải pivot — có thể còn dời).<br>Δ khoá = ' + f2(c.delta_e) +
        (params.threshold_mode === 'percent' ? ' (' + esc(params.reversal_pct) + '% close ứng viên)' : ' = ' + esc(params.atr_multiplier) + ' × ATR ' + f2(c.candidate_atr)) +
        '.<br>Xác nhận khi close ' + (hi2 ? '≤ ' : '≥ ') + '<b>' + f2(c.muc_xac_nhan) + '</b> (đường chấm vàng) — ' +
        (gap > 0 ? 'close hiện tại còn cách ' + f2(gap) + '.' : 'đã chạm.') +
        '<div class="rp-progress" title="Đã đảo chiều ' + Math.round(pct * 100) + '% ngưỡng Δ"><span style="width:' + (pct * 100).toFixed(0) + '%"></span></div>' +
        '<span class="muted">Đã đảo chiều ' + Math.round(pct * 100) + '% Δ. Nếu close ' + (hi2 ? 'vượt lên trên ' : 'xuống dưới ') + f2(c.candidate_price) + ' thì ứng viên dời theo.</span>');
    }
    // 3. Trạng thái Trend/Range
    out.push('<div class="xp-sec">Trạng thái (theo swing đã xác nhận)</div>');
    var rg = cl.range;
    add('state', '<b>' + esc(ps.regime_vi || '') + '</b> — ' + esc(cl.ly_do_vi || '') +
      (cl.so_dinh_xac_nhan !== undefined ? '<br><span class="muted">Segment có ' + cl.so_dinh_xac_nhan + ' đỉnh (gần nhất ' + esc(cl.nhan_dinh_gan_nhat || '—') + '), ' +
        cl.so_day_xac_nhan + ' đáy (gần nhất ' + esc(cl.nhan_day_gan_nhat || '—') + '). Tăng cần HH + HL, Giảm cần LH + LL.</span>' : '') +
      (rg ? '<br>Range khoá [' + f2(rg.lower) + ', ' + f2(rg.upper) + '], thoát khi close vượt ' + f2(rg.bien_tren_pha) + ' hoặc thủng ' + f2(rg.bien_duoi_pha) + '.' : ''));
    return out.join('');
  }

  /** Chú giải DC dưới chart + ghi chú «chữ nhãn đang ẩn vì zoom xa». */
  function syncLegend(timeline, events, S) {
    var isDc = !!(timeline && timeline.length && timeline[0].dc_phase !== undefined);
    document.querySelector('#dc-legend').hidden = !isDc;
    document.querySelector('#dc-compact-note').hidden = !(isDc && S.chart.isCompact());
  }

  function bindChart(chartObj) {
    chartObj.onCompactChange(function (c) { document.querySelector('#dc-compact-note').hidden = !c; });
  }

  MSL.algos.register({
    id: 'dc_atr',
    algorithms: ['dc_atr_structure'],
    title: 'DC theo close + ATR',
    // Mặc định bật khung chính; nhãn chữ, xác nhận, ứng viên, baseline tắt.
    layers: {
      dc: true, regime: true, range: true, dc_labels: false, dc_confirm: false,
      dc_candidate: false, baseline: false
    },
    panels: ['#dc-layers', '#btn-baseline'],
    layerHints: {
      dc_atr_structure: 'DC: marker nằm ĐÚNG giá close (không snap lên wick). Đường nối chỉ giữa hai pivot đã xác nhận; ứng viên là nét đứt. Dải đáy = trạng thái theo swing đã xác nhận, bắt đầu từ lúc biết. Chữ nhãn tự ẩn khi zoom xa (nhãn DC dày hơn ~1 nhãn / 26 px).'
    },
    chart: chart,
    notes: notes,
    runWarning: runWarning,
    statsHtml: statsHtml,
    pendingHtml: pendingHtml,
    eventDetail: eventDetail,
    selectEventOnChart: true,   // chọn dòng sự kiện → hiện điểm xác nhận của pivot đó
    explain: explain,
    replayLayers: ['dc_candidate'],
    baselineCompare: {
      pivotTypes: ['DC_HIGH', 'DC_LOW'],
      label: 'DC (close)',
      unsavedLabel: 'DC chưa lưu',
      labelsLayer: 'dc_labels'   // lớp quyết định hiện chữ HH/LH… trên panel baseline riêng
    },
    syncLegend: syncLegend,
    bindChart: bindChart,
    /** Trang Đánh giá: chấm pivot DC (close) như swing cấp 1 (thường theo wick) — ánh xạ khai báo rõ. */
    evalCrossMap: {
      checkbox: '#chk-map-dc',
      target: 'swing_nho',
      map: { SWING_HIGH: 'SWING_HIGH', SWING_LOW: 'SWING_LOW', DC_HIGH: 'SWING_HIGH', DC_LOW: 'SWING_LOW' },
      isActive: function (m) { return !!(m && m.DC_HIGH); },
      warning: ' ⚠ Đang chấm pivot DC theo CLOSE với nhãn swing (thường theo WICK): so sánh CHÉO ĐỊNH NGHĨA — ' +
        'chênh giá do khác nguồn giá là bình thường; nên nới dung sai giá hoặc chỉ chấm theo thời gian, và ghi rõ khi báo cáo.'
    },
    REGIME_TEXT_VI: REGIME_TEXT_VI,
    REGIME_COLORS: REGIME_COLORS
  });
})(window.MSL);
