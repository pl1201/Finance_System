/* Plugin hiển thị ict_structure (giai đoạn 1): ITH/ITL (+ nhãn HH/HL/LH/LL/EQ), STH/STL, LTH/LTL,
 * mức được bảo vệ (đỏ khi close đã vượt — chỉ là cờ), dealing range + EQ, khoảng trống bất thường;
 * tooltip, ghi chú, thống kê, trạng thái replay, panel chi tiết sự kiện.
 * Chỉ đọc details / timeline / pending_state do lõi tính — không tính lại logic ở đây.
 */
(function (MSL) {
  'use strict';

  var LWC = window.LightweightCharts;
  var series = MSL.series;
  var isFiniteNum = MSL.format.isFiniteNum;
  var fmtIso = MSL.format.fmtIso;
  var esc = MSL.dom.esc;
  var TRANSPARENT = series.TRANSPARENT;
  var ALGO = 'ict_structure';

  var COLORS = {
    ith: '#ffd54f',
    itl: '#4fc3f7',
    lth: '#ff8f00',
    ltl: '#0288d1',
    sth: 'rgba(176,190,197,.8)',
    protected: '#ce93d8',
    broken: '#ef5350',
    range: 'rgba(176,190,197,.6)',
    eq: 'rgba(176,190,197,.35)',
    gap: '#ff7043'
  };
  var LEVEL_OF = {
    SWING_HIGH: 1, SWING_LOW: 1, SWING_HIGH_L2: 2, SWING_LOW_L2: 2, SWING_HIGH_L3: 3, SWING_LOW_L3: 3
  };
  var SHORT = { 1: ['STH', 'STL'], 2: ['ITH', 'ITL'], 3: ['LTH', 'LTL'] };
  var ORDER_VI = { '1': 'tăng (HH + HL)', '-1': 'giảm (LH + LL)', '0': 'lẫn lộn', 'null': 'chưa đủ swing' };
  var ZONE_VI = { premium: 'premium (trên EQ)', discount: 'discount (dưới EQ)', eq: 'đúng EQ' };
  var GAP_VI = {
    nghi_phien: 'nghỉ hằng ngày', cuoi_tuan: 'cuối tuần', nghi_le: 'nghỉ lễ',
    thieu_trong_phien: 'THIẾU DỮ LIỆU trong phiên', ngoai_lich: 'ngoài phạm vi lịch',
    khong_ro_lich: 'chưa chọn lịch', lech_buoc: 'lệch bước khung'
  };

  function orderVi(o) { return ORDER_VI[String(o === undefined ? null : o)] || String(o); }

  function isIctTimeline(tl) {
    return tl.length && Object.prototype.hasOwnProperty.call(tl[tl.length - 1], 'dealing_hi');
  }

  /** Mức được bảo vệ: như levelSeriesData (bắt đầu từ nến SAU lúc biết, ngắt khi đổi mức) nhưng tô
   * đỏ phần sau khi close đã vượt. */
  function protectedData(tl, cursor) {
    var out = [], prevId = null, lastVal = null;
    for (var j = 0; j < tl.length; j++) {
      var p = tl[j];
      if (p.bar_index > cursor) break;
      var v = p.protected;
      if (!isFiniteNum(v)) {
        if (lastVal !== null) out.push({ time: p.time, value: lastVal, color: TRANSPARENT });
        prevId = null;
        continue;
      }
      if (p.protected_id !== prevId) out.push({ time: p.time, value: v, color: TRANSPARENT });
      else out.push({ time: p.time, value: v, color: p.protected_broken ? COLORS.broken : COLORS.protected });
      prevId = p.protected_id;
      lastVal = v;
    }
    return out;
  }

  function setColoredLine(s, points) {
    var any = points.some(function (p) { return p.color !== TRANSPARENT; });
    s.applyOptions({ visible: any });
    s.setData(any ? points : []);
  }

  var chart = {
    init: function (mc, st) {
      st.protected = mc.chart.addLineSeries(series.stepLineOpts(COLORS.protected, 2, LWC.LineStyle.Dotted));
      st.hi = mc.chart.addLineSeries(series.stepLineOpts(COLORS.range, 1, LWC.LineStyle.Dashed));
      st.lo = mc.chart.addLineSeries(series.stepLineOpts(COLORS.range, 1, LWC.LineStyle.Dashed));
      st.eq = mc.chart.addLineSeries(series.stepLineOpts(COLORS.eq, 1, LWC.LineStyle.SparseDotted));
      st.timelineByIndex = {};
    },

    clear: function (mc, st) {
      [st.protected, st.hi, st.lo, st.eq].forEach(function (s) { s.setData([]); });
    },

    /** Sự kiện của ict_structure (STH/ITH dùng chung loại SWING_* với thuật toán swing). */
    ownsEvent: function (t, e) { return !!e && e.algorithm === ALGO; },

    marker: function (e, ctx) {
      var t = e.structure_type, L = ctx.layers, x = e.details || {};
      if (t === 'ICT_GAP') {
        if (!L.ict_gap || !x.bat_thuong) return;
        ctx.markers.push({
          time: ctx.timeByIndex[e.event_bar_index], position: 'belowBar', color: COLORS.gap,
          shape: 'square', text: 'thiếu', size: 0.6
        });
        return;
      }
      var lvl = LEVEL_OF[t];
      if (!lvl) return;
      var high = t.indexOf('HIGH') !== -1;
      var at = ctx.opts.markerAtConfirm ? e.confirmed_bar_index : e.event_bar_index;
      var scale = (ctx.chart._markerScale || 1) * (e.event_id === ctx.selectedId ? 1.6 : 1);
      if (lvl === 1) {
        if (!L.ict_sth) return;
        ctx.markers.push({
          time: ctx.timeByIndex[at], position: high ? 'aboveBar' : 'belowBar', color: COLORS.sth,
          shape: 'circle', text: '', size: 0.4 * scale
        });
        return;
      }
      if ((lvl === 2 && !L.ict_ith) || (lvl === 3 && !L.ict_lth)) return;
      var text = (L.ict_labels && x.nhan) ? x.nhan : (lvl === 3 ? SHORT[3][high ? 0 : 1] : '');
      ctx.markers.push({
        time: ctx.timeByIndex[at], position: high ? 'aboveBar' : 'belowBar',
        color: lvl === 3 ? (high ? COLORS.lth : COLORS.ltl) : (high ? COLORS.ith : COLORS.itl),
        shape: 'square', text: text, size: (lvl === 3 ? 1.4 : 1) * scale
      });
    },

    draw: function (ctx, st) {
      var tl = ctx.timeline || [], cursor = ctx.cursor, L = ctx.layers;
      st.timelineByIndex = {};
      if (!isIctTimeline(tl)) {
        [st.protected, st.hi, st.lo, st.eq].forEach(function (s) { series.setGapLineData(s, []); });
        return;
      }
      for (var j = 0; j < tl.length; j++) {
        if (tl[j].bar_index > cursor) break;
        st.timelineByIndex[tl[j].bar_index] = tl[j];
      }
      setColoredLine(st.protected, L.ict_protected ? protectedData(tl, cursor) : []);
      var lv = series.levelSeriesData;
      series.setGapLineData(st.hi, L.ict_range ? lv(tl, 'dealing_hi', cursor, 'dealing_id') : []);
      series.setGapLineData(st.lo, L.ict_range ? lv(tl, 'dealing_lo', cursor, 'dealing_id') : []);
      series.setGapLineData(st.eq, L.ict_range ? lv(tl, 'dealing_eq', cursor, 'dealing_id') : []);
    },

    tooltipBar: function (mc, bar, d, st) {
      var p = st.timelineByIndex && st.timelineByIndex[bar.index];
      if (!p) return '';
      var s = 'Thứ tự (cấu trúc) sau nến này: <b>' + orderVi(p.order) + '</b>';
      if (isFiniteNum(p.protected)) {
        s += '<br>Mức được bảo vệ (' + (p.protected_side === 'low' ? 'đáy' : 'đỉnh') + ') ' + p.protected.toFixed(d) +
          (p.protected_broken ? ' — <b>close đã vượt</b> (cờ, không phải sự kiện)' : '');
      }
      if (isFiniteNum(p.dealing_hi) && isFiniteNum(p.dealing_lo)) {
        s += '<br>Dealing range [' + p.dealing_lo.toFixed(d) + ', ' + p.dealing_hi.toFixed(d) + '] · EQ ' +
          p.dealing_eq.toFixed(d) + ' · ' + (ZONE_VI[p.zone] || '') +
          (isFiniteNum(p.range_pos) ? ' · vị trí ' + (p.range_pos * 100).toFixed(0) + '%' : '');
      }
      s += isFiniteNum(p.atr) ? '<br>ATR ' + p.atr.toFixed(d) : '<br>Chưa có ATR';
      if (p.gap) s += ' · trước nến này: khoảng trống ' + (GAP_VI[p.gap] || p.gap);
      return '<div class="tt-rule">' + s + '</div>';
    },

    tooltipEvent: function (e, d) {
      if (e.algorithm !== ALGO) return '';
      var x = e.details || {}, out = [];
      if (e.structure_type === 'ICT_GAP') {
        out.push('Khoảng trống ' + esc(GAP_VI[x.loai] || x.loai) + ': ' + x.so_o_thieu + ' ô nến' +
          (x.so_o_trong_phien ? ' (' + x.so_o_trong_phien + ' ô trong phiên)' : '') + ' · lịch ' + esc(x.lich_phien));
      } else {
        out.push('<b>' + esc(x.ten || '') + '</b> (cấp ' + x.cap + ')' + (x.cap_cau_truc ? ' — cấp cấu trúc' : ''));
        if (x.cap_cau_truc) {
          out.push(x.nhan
            ? 'Nhãn ' + esc(x.nhan) + ': so với ' + Number(x.gia_truoc).toFixed(d) + ', chênh ' +
              Number(x.chenh_lech).toFixed(d) + ', dung sai ±' + Number(x.dung_sai).toFixed(d)
            : 'Chưa so: ' + esc(x.ly_do_chua_so || ''));
          out.push('Thứ tự sau swing: ' + esc(x.order_sau_vi || orderVi(x.order_sau)) +
            (isFiniteNum(x.muc_bao_ve_sau) ? ' · mức được bảo vệ ' + Number(x.muc_bao_ve_sau).toFixed(d) : ''));
        }
      }
      return '<br>' + out.join('<br>');
    }
  };

  // ------------------------------------------------------------------ trang Thử nghiệm

  function notes(stats, dataStatus, pending, S) {
    var m = (stats && stats.chi_so_thuat_toan) || null;
    var ps = pending || {};
    var out = [];
    out.push(['info', '<strong>Giai đoạn 1</strong>: STH/STL (pivot 1/1) → ITH/ITL (cấp 2) → thứ tự đỉnh/đáy, mức ' +
      'được bảo vệ, dealing range. <strong>Không có BOS/CHoCH</strong> (quyết định B1): close vượt mức được bảo vệ ' +
      'chỉ bật cờ, không đổi thứ tự. Sweep, shift, FVG, khung lớn ở giai đoạn 2–3.']);
    var cal = (m && m.lich_phien) || ps.lich_phien;
    if (!cal || cal === 'none' || cal === 'auto') {
      out.push(['warn', 'Chưa chọn lịch phiên — mọi khoảng trống là «chưa chọn lịch», không phân biệt nghỉ phiên với thiếu dữ liệu.']);
    } else {
      out.push(['info', 'Khoảng trống phân loại theo lịch khai báo <code>' + esc(cal) + '</code>: giữ mức qua mọi khoảng ' +
        'trống, chặn cửa sổ pivot vắt qua khoảng trống (D1).']);
    }
    var gaps = (m && m.khoang_trong) || ps.khoang_trong || {};
    var bad = (gaps.thieu_trong_phien || 0) + (gaps.lech_buoc || 0);
    if (bad) {
      out.push(['warn', '<strong>' + bad + '</strong> khoảng trống bất thường (thiếu dữ liệu trong phiên / lệch bước) — ' +
        'marker «thiếu». Không tự lấp; không gộp thành Range.']);
    }
    if (m && m.so_nen && m.nen_ngoai_phien > 0.2 * m.so_nen) {
      out.push(['warn', m.nen_ngoai_phien + ' / ' + m.so_nen + ' nến nằm ngoài giờ phiên theo lịch — dữ liệu không theo ' +
        'lịch này (vd dataset mô phỏng chạy 24/7). Số «mỗi ngày» kém tin cậy.']);
    }
    if (S.dataset && S.dataset.is_synthetic) {
      out.push(['warn', 'Dataset <strong>MÔ PHỎNG</strong> — chỉ để thử công cụ.']);
    }
    out.push(['info', 'Chưa có nhãn tham chiếu ITH/ITL (D8) — chưa có F1. Thống kê ở tab Thống kê là mô tả hành vi.']);
    return out;
  }

  function pct(x) { return x === null || x === undefined ? '—' : (x * 100).toFixed(1) + '%'; }
  function num(x, dg) { return x === null || x === undefined ? '—' : Number(x).toFixed(dg === undefined ? 2 : dg); }

  function statsHtml(m) {
    function box(k, v, title) {
      return '<div class="stat-box"' + (title ? ' title="' + esc(title) + '"' : '') + '><div class="k">' + esc(k) +
        '</div><div class="v">' + esc(v) + '</div></div>';
    }
    var sw = m.swing || {};
    function rate(a, b) {
      return num((sw[a] || {}).moi_ngay, 2) + ' / ' + num((sw[b] || {}).moi_ngay, 2);
    }
    function count(a, b) {
      return (sw[a] || {}).so + ' / ' + (sw[b] || {}).so + ' swing trong khoảng chạy';
    }
    var o = m.ty_le_thoi_gian_order || {};
    var g = m.khoang_trong || {};
    var html = '<div class="section-title">Cấu trúc ICT — giai đoạn 1 (mô tả hành vi, không phải accuracy)</div>';
    html += '<div class="stat-grid">' +
      box('ITH / ITL mỗi ngày', rate('ITH', 'ITL'), count('ITH', 'ITL')) +
      box('STH / STL mỗi ngày', rate('STH', 'STL'), count('STH', 'STL')) +
      ((sw.LTH && sw.LTH.so) || (sw.LTL && sw.LTL.so) ? box('LTH / LTL mỗi ngày', rate('LTH', 'LTL'), count('LTH', 'LTL')) : '') +
      box('Ngày giao dịch', m.so_ngay_giao_dich, 'Tính theo ' + (m.ngay_tinh_theo || '')) +
      box('Thứ tự tăng / giảm / lẫn lộn', pct(o['1']) + ' / ' + pct(o['-1']) + ' / ' + pct(o['0']),
        'Tỷ lệ thời gian (trạng thái sau mỗi nến). Chưa đủ swing: ' + pct(o.none)) +
      box('Mức bảo vệ bị close vượt', pct(m.ty_le_muc_bao_ve_bi_vuot_khi_co_muc),
        'Trong thời gian có mức được bảo vệ; trên tổng thời gian: ' + pct(m.ty_le_muc_bao_ve_bi_vuot_tren_tong_nen)) +
      box('Khoảng trống: nghỉ / cuối tuần / lễ', (g.nghi_phien || 0) + ' / ' + (g.cuoi_tuan || 0) + ' / ' + (g.nghi_le || 0)) +
      box('Khoảng trống bất thường', (g.thieu_trong_phien || 0) + (g.lech_buoc || 0) +
        ((g.ngoai_lich || g.khong_ro_lich) ? ' · không phân loại ' + ((g.ngoai_lich || 0) + (g.khong_ro_lich || 0)) : '')) +
      box('Pivot bị chặn vì khoảng trống', (m.pivot_bi_chan_vi_gap || {}).high + ' đỉnh / ' + (m.pivot_bi_chan_vi_gap || {}).low + ' đáy') +
      '</div>';
    var ab = m.khoang_trong_bat_thuong || [];
    if (ab.length) {
      html += '<table class="data-table"><thead><tr><th>Nến</th><th>Từ</th><th>Đến</th><th>Loại</th><th class="num">Ô trong phiên</th></tr></thead><tbody>' +
        ab.slice(0, 20).map(function (r) {
          return '<tr><td class="num">' + r.nen + '</td><td class="mono">' + esc(fmtIso(r.tu)) + '</td><td class="mono">' +
            esc(fmtIso(r.den)) + '</td><td>' + esc(GAP_VI[r.loai] || r.loai) + '</td><td class="num">' +
            (r.so_o_trong_phien == null ? '—' : r.so_o_trong_phien) + '</td></tr>';
        }).join('') + '</tbody></table>';
    }
    html += '<p class="hint">' + esc(m.ghi_chu_vi || '') + '</p>';
    return html;
  }

  function pendingHtml(ps, d) {
    if (!ps.ict) return null;
    function f(x) { return x === null || x === undefined ? '—' : Number(x).toFixed(d); }
    function sw(x) { return x ? f(x.gia) + ' (nến #' + x.nen + ', biết lúc #' + x.xac_nhan_tai + ')' : '— chưa có —'; }
    var c = ps.cau_truc || {}, r = ps.dealing_range || {}, mb = c.muc_bao_ve;
    var cmpVi = function (v, hi) { return v === null || v === undefined ? '—' : (v === 1 ? (hi ? 'HH' : 'HL') : (v === -1 ? (hi ? 'LH' : 'LL') : (hi ? 'EQH' : 'EQL'))); };
    var gaps = Object.keys(ps.khoang_trong || {}).map(function (k) { return (GAP_VI[k] || k) + ' ' + ps.khoang_trong[k]; }).join(' · ');
    return '<div class="info-card"><dl>' +
      '<dt>Thứ tự (cấp ' + esc(ps.cap_cau_truc) + ')</dt><dd><strong>' + esc(c.order_vi || orderVi(c.order)) + '</strong> · so đỉnh ' +
        cmpVi(c.hh, true) + ' · so đáy ' + cmpVi(c.hl, false) + '</dd>' +
      '<dt>Đỉnh / đáy cấu trúc gần nhất</dt><dd class="mono">' + sw(c.dinh_gan_nhat) + ' / ' + sw(c.day_gan_nhat) + '</dd>' +
      '<dt>Mức được bảo vệ</dt><dd class="mono">' + (mb ? (mb.phia === 'low' ? 'đáy ' : 'đỉnh ') + sw(mb) +
        (c.muc_bao_ve_bi_vuot ? ' — close đã vượt ở nến #' + c.bi_vuot_tai_nen : '') : '— không có (thứ tự lẫn lộn / chưa đủ) —') + '</dd>' +
      '<dt>Dealing range</dt><dd class="mono">' + (r && r.hi !== null && r.hi !== undefined
        ? '[' + f(r.lo) + ', ' + f(r.hi) + '] · EQ ' + f(r.eq) + ' · ' + esc(ZONE_VI[r.zone] || '') + ' · ' + (r.range_pos * 100).toFixed(0) + '%'
        : '— chưa đủ đỉnh và đáy —') + '</dd>' +
      '<dt>ATR</dt><dd class="mono">' + f(ps.atr_hien_tai) + '</dd>' +
      '<dt>Khoảng trống (lịch ' + esc(ps.lich_phien) + ')</dt><dd>' + (gaps || '—') + '</dd>' +
      '</dl><p class="hint">' + esc(ps.ghi_chu_vi || '') + '</p></div>';
  }

  function eventDetail(e, S) {
    var x = e.details || {}, d = S.digits, rows = [];
    function row(k, v) { rows.push('<dt>' + esc(k) + '</dt><dd>' + v + '</dd>'); }
    function f(v) { return v === null || v === undefined ? '—' : Number(v).toFixed(d); }
    row('Loại', esc(e.structure_type) + ' — ' + esc(e.structure_text_vi || ''));
    row('Nến sự kiện', '#' + e.event_bar_index + ' · ' + esc(fmtIso(e.event_time)));
    row('Biết lúc', '#' + e.confirmed_bar_index + ' · ' + esc(fmtIso(e.confirmed_at)) + ' · trễ ' + e.confirmation_lag_bars + ' nến');
    if (e.structure_type === 'ICT_GAP') {
      row('Khoảng trống', esc(GAP_VI[x.loai] || x.loai) + (x.bat_thuong ? ' — <b>bất thường</b>' : ''));
      row('Từ → đến', esc(fmtIso(x.tu)) + ' → ' + esc(fmtIso(x.den)) + ' (' + x.so_o_thieu + ' ô nến)');
      if (x.so_o_trong_phien !== null && x.so_o_trong_phien !== undefined) row('Ô thiếu trong phiên', String(x.so_o_trong_phien));
      row('Chính sách', esc(x.chinh_sach || ''));
    } else {
      row('Cấp', esc(x.ten) + ' (cấp ' + x.cap + ')' + (x.cap_cau_truc ? ' — cấp cấu trúc' : ''));
      row('Quy tắc', esc(x.quy_tac || ''));
      if (x.basis) row('Ba swing cấp dưới', f(x.gia_trai) + ' · <b>' + f(x.gia_giua) + '</b> · ' + f(x.gia_phai) +
        ' (nến #' + x.nen_trai + ', #' + x.nen_giua + ', #' + x.nen_phai + ')');
      if (x.cap_cau_truc) {
        row('So với swing cùng phía trước', x.nhan
          ? esc(x.nhan) + ': ' + f(x.gia_truoc) + ' → ' + f(e.price) + ' (chênh ' + f(x.chenh_lech) + ', dung sai ±' + f(x.dung_sai) + ' = ' +
            esc(S.run && S.run.params ? S.run.params.eq_tol_atr : '') + ' × ATR ' + f(x.atr_luc_xac_nhan) + ')'
          : 'chưa so — ' + esc(x.ly_do_chua_so || ''));
        row('Thứ tự sau swing', esc(x.order_sau_vi || orderVi(x.order_sau)) +
          (isFiniteNum(x.muc_bao_ve_sau) ? ' · mức được bảo vệ ' + f(x.muc_bao_ve_sau) : ''));
      }
      if (e.reference_event_id) row('Tham chiếu', '<span class="mono">' + esc(e.reference_event_id) + '</span>');
    }
    return '<h4>Chi tiết sự kiện được chọn</h4><dl>' + rows.join('') + '</dl>';
  }

  MSL.algos.register({
    id: 'ict_structure',
    algorithms: [ALGO],
    title: 'Cấu trúc ICT phân tầng',
    layers: {
      ict_ith: true, ict_labels: true, ict_sth: false, ict_lth: true, ict_protected: true, ict_range: true, ict_gap: true
    },
    panels: ['#ict-layers'],
    layerHints: {
      ict_structure: 'ITH/ITL = ô vuông (chữ HH/HL/LH/LL/EQ khi bật nhãn). Đường tím chấm = mức được bảo vệ, chuyển đỏ khi ' +
        'close đã vượt (chỉ là cờ, không phải BOS). Nét đứt xám = dealing range, chấm thưa = EQ. Mọi đường chỉ hiện từ nến ' +
        'sau lúc biết.'
    },
    chart: chart,
    notes: notes,
    statsHtml: statsHtml,
    pendingHtml: pendingHtml,
    eventDetail: eventDetail,
    selectEventOnChart: true
  });
})(window.MSL);
