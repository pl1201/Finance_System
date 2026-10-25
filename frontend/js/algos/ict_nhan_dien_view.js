/* ict_structure ≥ 0.6.0 — lớp nhận diện: phần dựng hình THUẦN (MSL.ictNdView). Không vẽ, không DOM, không gọi LWC → chạy
 * được trong node (tests/frontend/test_ict_nhan_dien_display.py). Nạp SAU algos/ict_structure_view.js (dùng mô hình M của
 * MSL.ictView.buildModel — M.tl, M.tlList, M.list — và hasOwn / finite / rgba / fp / fpRange / COL).
 *
 * Chỉ ĐỌC lõi (core/algorithms/ict_structure/nhan_dien.py; đặc tả docs/algorithms/thuat_toan_nhan_dien.md):
 *   - trạng thái sau mỗi nến: cột timeline nd_trang_thai / nd_tu / nd_range_tu / nd_range_hi / nd_range_lo;
 *   - lúc đổi trạng thái: sự kiện STATE_* (details: cửa sổ, ER, biên, lần chạm…);
 *   - khoảng 80% / 50% mỗi tầm và xác suất chạm vùng gần nhất sau mỗi nến: cột nd_<tầm>_lo80… / nd_p_tren_<tầm>…;
 *   - 0.7.0: xác suất trạng thái còn giữ nd_giu_<tầm>, thời gian còn lại nd_con_lai (nến), phá biên range nd_pha_<tầm>;
 *   - 0.8.0: mức kèm xác suất chạm có thêm PDH / PDL còn nguyên; điểm theo loại mức có chạm thật / kỳ vọng (p_tb);
 *   - 0.9.0 (trạng thái v2, nd_kieu = v2): 4 trạng thái + cờ nén nd_nen, độ mạnh nd_do_manh; details có ly_do / thoat,
 *     adx, cau_truc_m15 / _h1, tham_tren / tham_duoi (range). v1 (nd_kieu = v1, run cũ) giữ chữ cũ;
 *   - «Đang theo dõi»: pending_state.nhan_dien (trạng thái kèm lý do, ứng viên, khoảng, mức, điểm thật tới nến này;
 *     0.7.0: khối thoi_gian = {con_giu, pha_bien, diem_that}) — lõi đóng dấu nến (`nen`); mức và điểm thật chỉ dùng khi
 *     nến đó là con trỏ (không tô ngược).
 * Nhân quả: mọi thứ từ M (timeline ≤ con trỏ, sự kiện confirmed ≤ con trỏ).
 *
 *   has(M)                         kết quả có lớp nhận diện (≥ 0.6.0, nd_bat)
 *   meta(type)                     {state, short, color} của sự kiện STATE_* | null
 *   bandBars(M, logicalOf)         dải «trạng thái» theo nến cho MSL.primitives.Band
 *   episodes(M)                    đoạn trạng thái liên tiếp ≤ con trỏ, kèm sự kiện mở đoạn (tính một lần mỗi M)
 *   drawing(M, logicalOf, opts)    {segments, boxes}: hộp range đang có + range gần nhất đã qua (opts.all: mọi range —
 *                                  chế độ xem lại); đường giữa chấm, biên đã qua tô theo chiều phá (kiểu Range Detector)
 *   bandDrawing(M, logicalOf)      {segments, boxes}: khoảng 80% / 50% của mỗi tầm = vùng LỒNG NHAU cùng bắt đầu ở con trỏ
 *                                  (tầm dài nhạt, rộng, dài; tầm ngắn đậm hơn, nằm trong), nhãn giá ở mép phải — đúng số
 *                                  của lõi + mức kèm xác suất chạm (shownLevels: trong khoảng 80% tầm dài, p ≥ 10%, ≤ 2 mỗi phía)
 *   squeezeBars(M, logicalOf)      dải mỏng «nén» (cờ nd_nen của lõi v2) cho MSL.primitives.Band
 *   hasLine(M) / trendLine(M)      «đường trend» (cột nd_duong, lõi ≥ 0.9.1): điểm {time, value, color} cho line series
 *                                  bậc thang — xanh dưới giá (trend ↑), đỏ trên giá (trend ↓), chàm giữa hộp (range); ngắt
 *                                  ở nhiễu và ở nến đầu mỗi đoạn mới (không nối hai đoạn)
 *   Khung trạng thái dưới chart (hook `pane` của algos/ict_structure.js, lớp ict_nd_pane) — nhận thẳng timeline (một hàng
 *   mỗi nến, không cần M), mọi thứ từ hàng timeline của chính nến đó:
 *   paneHas(timeline)              kết quả có cột trạng thái (lõi ≥ 0.6.0, nd_bat) → có khung
 *   statePaneSeries(tl, bars, c)   {a, b, nen}: một phần tử mỗi nến của `bars` (nến chart chính, cùng thứ tự) — a: cột trạng
 *                                  thái, b: nửa dưới đối xứng của range / nhiễu, nen: dải cờ nd_nen (độ cao: PANE). Nến sau
 *                                  con trỏ c / không có hàng / trạng thái null = khoảng trống {time}
 *   statePaneLegend(tl)            [{sym, word, color}] chú giải màu (run v1 không có cột nd_nen: «sideway nén» là trạng
 *                                  thái, không có cờ nén)
 *   statePaneText(tl, i, c)        «#455 · trend lên · mạnh 0.57 · 21 nến (từ #435) · nén» — trạng thái ở nến i (mặc định /
 *                                  vượt con trỏ → nến con trỏ; c không hữu hạn → nến cuối của timeline) | null
 *   panel(M)                       {title, rows: [{k, v, title}]} bảng «Nhận diện» ở nến con trỏ | null
 *   statusAt(M, i, show)           {key, color, text, title} hàng 3 của dòng trạng thái ở nến i — show.state: trạng thái,
 *                                  show.band: khoảng 4h của nến i | null
 *   info(M, id)                    tooltip [{head, body, more}] cho id «nd:…» (khoảng / mức kèm điểm thật)
 *   eventText(e, digits)           câu giải thích một sự kiện STATE_* | null
 *   pendingLines(ps, digits)       [{kind, text}] «Đang theo dõi» từ pending_state.nhan_dien (người gọi đưa pending của
 *                                  chính nến đang giải thích — ảnh chụp replay)
 *   statsRows(st)                  [{k, v, title}] ô «điểm thật» cho tab Thống kê từ run_stats.nhan_dien
 */
(function (MSL) {
  'use strict';

  var V = MSL.ictView, finite = V.finite, hasOwn = V.hasOwn, rng = V.fpRange, pct = V.pct, pct1 = V.pct1;
  /** Màu riêng của lớp (range chàm, nén tím — không trùng BSL cam / SSL xanh ngọc / OTE vàng). */
  var COL_RANGE = '#5c6bc0', COL_SQUEEZE = '#ba68c8', COL_CHOP = '#78909c';
  var STATE = {
    trend_len: { word: 'trend lên', short: 'trend ↑', color: V.rgba(V.COL.up, 0.55), type: 'STATE_TREND_UP' },
    trend_xuong: { word: 'trend xuống', short: 'trend ↓', color: V.rgba(V.COL.down, 0.55), type: 'STATE_TREND_DOWN' },
    range: { word: 'range', short: 'range', color: V.rgba(COL_RANGE, 0.75), type: 'STATE_RANGE' },
    nen: { word: 'sideway nén', short: 'nén', color: V.rgba(COL_SQUEEZE, 0.62), type: 'STATE_SQUEEZE' },
    nhieu: { word: 'sideway nhiễu', short: 'nhiễu', color: V.rgba(COL_CHOP, 0.45), type: 'STATE_CHOP' }
  };
  /** Khoá trạng thái theo thứ tự STATE — run v2: «nén» không phải trạng thái (là cờ nd_nen đi kèm). */
  function stateKeys(v2) { return Object.keys(STATE).filter(function (k) { return !v2 || k !== 'nen'; }); }
  var NOT_READY = 'chưa đủ nến (sau khoảng trống / khởi động)';   // trạng thái null của lõi
  var NONE_COLOR = 'rgba(90,100,110,0.18)';
  var BY_TYPE = {};
  Object.keys(STATE).forEach(function (k) { BY_TYPE[STATE[k].type] = k; });
  var EXT = 5;   // hộp range đang có kéo tới con trỏ + EXT nến
  var REASON = {
    trend_len: 'giá đi một chiều (ER ≥ ngưỡng)', trend_xuong: 'giá đi một chiều (ER ≥ ngưỡng)',
    range: 'mỗi biên bị chạm ≥ 2 lần, ER thấp', nen: 'đỉnh thấp dần, đáy cao dần, biên co lại', nhieu: 'ER thấp, không có biên rõ'
  };
  /** Lý do của trạng thái v2 (lõi 0.9.0, plan_nhan_dien_v2.md §3). */
  var TREND_V2 = ' + lực (ER hoặc ADX) + động lượng cùng chiều; giữ tới CHoCH, thủng kênh hoặc lực tắt';
  var REASON_V2 = {
    trend_len: 'cấu trúc HH-HL' + TREND_V2, trend_xuong: 'cấu trúc LH-LL' + TREND_V2,
    range: 'hộp rộng vừa, mỗi biên được thăm lại; giữ tới khi phá biên (close ra ngoài)', nhieu: 'không trend, không hộp range'
  };
  var ORDER_V2 = { 1: 'HH-HL', '-1': 'LH-LL', 0: 'lẫn lộn' };
  var WHY_V2 = { cau_truc_va_luc: 'cấu trúc cùng chiều + lực', luc_manh: 'ER và ADX cùng mạnh', er_manh: 'ER rất cao',
    hop: 'hộp có biên được thăm lại', con_lai: 'không trend, không hộp', giu: 'giữ' };
  var EXIT_V2 = { choch: 'CHoCH (cấu trúc đổi / mức bảo vệ bị phá)', thung_kenh: 'thủng kênh Donchian', luc_tat: 'lực tắt',
    pha_bien_len: 'range bị phá lên', pha_bien_xuong: 'range bị phá xuống' };
  /** details / chi_tiet của trạng thái v2 (lõi ghi ``kieu``). */
  function isV2(x) { return !!x && x.kieu === 'v2'; }
  /** Lần chạy dùng trạng thái v2? (pending_state.nhan_dien.kieu; run cũ không có → v1). */
  function v2Run(M) { return ((M && M.pending && M.pending.nhan_dien) || {}).kieu === 'v2'; }
  function reasons(M) { return v2Run(M) ? REASON_V2 : REASON; }

  function has(M) { return !!M && paneHas(M.tlList); }
  function meta(t) {
    var k = BY_TYPE[t];
    return k ? { state: k, short: STATE[k].short, color: STATE[k].color } : null;
  }
  function num(x, k) { return finite(x) ? x.toFixed(k) : '—'; }
  /** «1h 90% · 4h 62%» từ {tầm: xác suất}. */
  function pctByKey(o) { return Object.keys(o).map(function (k) { return k + ' ' + pct(o[k]); }).join(' · '); }

  function bandBars(M, logicalOf) {
    var out = [];
    M.tlList.forEach(function (p) {
      if (!hasOwn(p, 'nd_trang_thai')) return;
      var k = p.nd_trang_thai, s = STATE[k];
      out.push({ l: logicalOf(p.bar_index), key: (k || 'none') + '|' + p.nd_tu, color: s ? s.color : NONE_COLOR,
        text: s ? s.short : '', textColor: '#f1f5f8', id: 'nd:state:' + p.bar_index });
    });
    return out;
  }

  /** Đoạn trạng thái liên tiếp (theo nd_tu) ≤ con trỏ: {key, from, to, ev, rfrom, hi, lo} — ev = sự kiện STATE_* mở
   *  đoạn (nến sự kiện = from), rfrom = nến đầu cửa sổ range lúc nhận ra, hi/lo = biên range ở nến cuối đoạn. */
  function episodes(M) {
    if (M.ndEp) return M.ndEp;
    var opening = {};
    (M.list || []).forEach(function (e) {
      var k = BY_TYPE[e.structure_type];
      if (k) opening[k + '|' + e.event_bar_index] = e;
    });
    var out = [], cur = null;
    M.tlList.forEach(function (p) {
      if (!hasOwn(p, 'nd_trang_thai') || !p.nd_trang_thai) { cur = null; return; }
      if (!cur || cur.key !== p.nd_trang_thai || cur.from !== p.nd_tu) {
        var ev = opening[p.nd_trang_thai + '|' + p.nd_tu] || null;
        if (cur && cur.key === 'range' && ev && ev.details) cur.brk = ev.details.thoat || null;   // v2: range kết thúc thế nào
        cur = { key: p.nd_trang_thai, from: p.nd_tu, to: null, ev: ev, rfrom: finite(p.nd_range_tu) ? p.nd_range_tu : null,
          hi: null, lo: null, brk: null };
        out.push(cur);
      }
      cur.to = p.bar_index;
      if (finite(p.nd_range_hi)) { cur.hi = p.nd_range_hi; cur.lo = p.nd_range_lo; }
    });
    M.ndEp = out;
    return out;
  }

  /** Range đã qua bị phá (lõi v2 ghi details.thoat ở trạng thái kế): màu biên, chữ nhãn. */
  var BREAK = { pha_bien_len: { col: V.COL.up, word: ', phá lên' }, pha_bien_xuong: { col: V.COL.down, word: ', phá xuống' } };
  var SQZ_COLOR = V.rgba(COL_SQUEEZE, 0.85);
  var MAX_REVIEW = 40;   // chế độ xem lại: số range đã qua tối đa vẽ

  /** Hộp range kiểu Range Detector: hộp + đường giữa chấm; range đang có nét đứt kéo tới con trỏ + EXT, ghi xác suất phá
   *  biên ở mép phải; range đã qua nét chấm, biên tô xanh / đỏ khi bị phá lên / xuống (lõi v2 ghi details.thoat). */
  function drawing(M, logicalOf, opts) {
    var out = { segments: [], boxes: [] }, eps = episodes(M), all = !!(opts && opts.all), past = 0, max = all ? MAX_REVIEW : 1;
    for (var i = eps.length - 1; i >= 0 && past < max; i--) {
      var ep = eps[i];
      if (ep.key !== 'range' || !finite(ep.hi) || !finite(ep.lo)) continue;
      var live = ep.to === M.cursor, id = 'nd:range:' + ep.from, brk = BREAK[ep.brk], col = brk ? brk.col : COL_RANGE;
      if (!live) past++;
      var l1 = logicalOf(ep.rfrom === null ? ep.from : ep.rfrom) - 0.45;
      var l2 = live ? logicalOf(M.cursor + EXT) : logicalOf(ep.to) + 0.45;
      out.boxes.push({ id: id, l1: l1, l2: l2, p1: ep.lo, p2: ep.hi, fill: V.rgba(COL_RANGE, live ? 0.08 : 0.035),
        border: V.rgba(col, live ? 0.9 : 0.55), borderWidth: 1.5, borderStyle: live ? 'dashed' : 'dotted',
        autoscale: false });
      var mid = (ep.hi + ep.lo) / 2;
      out.segments.push({ id: id, l1: l1, l2: l2, p1: mid, p2: mid, color: COL_RANGE, width: 1, style: 'dotted',
        alpha: live ? 0.55 : 0.3, autoscale: false });
      if (live || !all) {                          // xem lại: range đã qua không ghi nhãn (đỡ rối)
        out.segments.push({ id: id, noLine: true, l1: l2, l2: l2, p1: ep.hi, p2: ep.hi, color: col, autoscale: false,
          label: { text: live ? 'Range' + breakText(M) : 'Range (đã qua' + (brk ? brk.word : '') + ')',
            pos: 'right', priority: 6.7, size: 10, alpha: live ? 0.95 : 0.65 } });
      }
    }
    return out;
  }

  var LINE_COLOR = { trend_len: V.COL.up, trend_xuong: V.COL.down, range: V.rgba(COL_RANGE, 0.9) };
  function hasLine(M) { return has(M) && hasOwn(M.tlList[M.tlList.length - 1], 'nd_duong'); }
  /** Điểm của «đường trend» ≤ con trỏ (lõi tính nd_duong). Điểm không giá trị = khoảng trống của line series. */
  function trendLine(M) {
    var out = [], prev = null;
    M.tlList.forEach(function (p) {
      var key = p.nd_trang_thai + '|' + p.nd_tu, v = p.nd_duong;
      out.push(finite(v) && key === prev ? { time: p.time, value: v, color: LINE_COLOR[p.nd_trang_thai] } : { time: p.time });
      prev = finite(v) ? key : null;
    });
    return out;
  }

  /** Dải mỏng «nén» (cờ nd_nen của lõi v2): chỉ các nến đang nén. */
  function squeezeBars(M, logicalOf) {
    var out = [];
    M.tlList.forEach(function (p) {
      if (p.nd_nen) out.push({ l: logicalOf(p.bar_index), key: 'nen', color: SQZ_COLOR, id: 'nd:nen:' + p.bar_index });
    });
    return out;
  }

  // ------------------------------------------------------------------ khung trạng thái dưới chart (lớp ict_nd_pane)

  /** Độ cao trên khung, thang dọc cố định ±top (hook `pane` khai cho series): trend 0,35 + 0,65 × độ mạnh (chỉ để hiển thị,
   *  không phải xác suất; null → 0,5); range ±0,3, nhiễu ±0,1 đối xứng quanh 0; dải nén sqzBase → sqzTop, trên mọi cột. */
  var PANE = { trendBase: 0.35, trendSpan: 0.65, noStrength: 0.5, range: 0.3, chop: 0.1, sqzBase: 1.05, sqzTop: 1.2, top: 1.3 };
  /** Kiểu cột theo trạng thái — màu như «đường trend» (LINE_COLOR), nhiễu xám, nén tím (SQZ_COLOR); ký hiệu cho chú giải. */
  var PANE_STATE = {
    trend_len: { sign: 1, sym: '▲', color: LINE_COLOR.trend_len },
    trend_xuong: { sign: -1, sym: '▼', color: LINE_COLOR.trend_xuong },
    range: { h: PANE.range, sym: '▬', color: LINE_COLOR.range },
    nhieu: { h: PANE.chop, sym: '·', color: V.rgba(COL_CHOP, 0.8) },
    nen: { h: PANE.chop, sym: '▪', color: V.rgba(COL_SQUEEZE, 0.55) }   // run v1 (nd_kieu = v1): «sideway nén» là trạng thái
  };

  function round4(x) { return Math.round(x * 1e4) / 1e4; }
  /** Hàng timeline của nến i — timeline của lõi liền mạch (một hàng mỗi nến, replay ghép delta nối tiếp) → tra thẳng. */
  function rowAt(tl, i) {
    var p = tl.length ? tl[i - tl[0].bar_index] : null;
    return p && p.bar_index === i ? p : null;
  }
  function paneHas(timeline) {
    var tl = timeline || [];
    return tl.length > 0 && hasOwn(tl[tl.length - 1], 'nd_trang_thai');
  }
  function statePaneSeries(timeline, bars, cursor) {
    var c = finite(cursor) ? cursor : Infinity, tl = timeline || [], out = { a: [], b: [], nen: [] };
    (bars || []).forEach(function (bar) {
      var t = bar.time, p = bar.index <= c ? rowAt(tl, bar.index) : null, s = p ? PANE_STATE[p.nd_trang_thai] : null;
      var a = { time: t }, b = { time: t };
      if (s && s.sign) {
        var m = finite(p.nd_do_manh) ? Math.max(0, Math.min(1, p.nd_do_manh)) : PANE.noStrength;
        a = { time: t, value: s.sign * round4(PANE.trendBase + PANE.trendSpan * m), color: s.color };
      } else if (s) {
        a = { time: t, value: s.h, color: s.color };
        b = { time: t, value: -s.h, color: s.color };
      }
      out.a.push(a);
      out.b.push(b);
      out.nen.push(p && p.nd_nen === true ? { time: t, value: PANE.sqzTop, color: SQZ_COLOR } : { time: t });
    });
    return out;
  }
  function statePaneLegend(timeline) {
    var tl = timeline || [], last = tl[tl.length - 1], v2 = !last || hasOwn(last, 'nd_nen');
    var out = stateKeys(v2).map(function (k) {
      return { sym: PANE_STATE[k].sym, word: STATE[k].word, color: PANE_STATE[k].color };
    });
    if (v2) out.push({ sym: '▔', word: 'nén', color: SQZ_COLOR });
    return out;
  }
  function statePaneText(timeline, index, cursor) {
    var tl = timeline || [];
    if (!tl.length) return null;
    var c = finite(cursor) ? cursor : tl[tl.length - 1].bar_index;
    var i = finite(index) ? Math.min(index, c) : c, p = rowAt(tl, i);
    if (!p || !hasOwn(p, 'nd_trang_thai')) return null;
    var k = p.nd_trang_thai, s = STATE[k], parts = ['#' + i];
    if (!s) return parts.concat(NOT_READY).join(' · ');
    parts.push(s.word);
    if ((k === 'trend_len' || k === 'trend_xuong') && finite(p.nd_do_manh)) parts.push('mạnh ' + num(p.nd_do_manh, 2));
    if (finite(p.nd_tu)) parts.push((i - p.nd_tu + 1) + ' nến (từ #' + p.nd_tu + ')');   // như dòng trạng thái (statusAt)
    if (p.nd_nen) parts.push('nén');
    return parts.join(' · ');
  }

  /** Hàng 3 của dòng trạng thái ở nến i: phần trạng thái (show.state) và / hoặc khoảng 4h của nến i (show.band). */
  function statusAt(M, i, show) {
    var p = M.tl[i];
    if (!p || !hasOwn(p, 'nd_trang_thai') || !show) return null;
    var k = p.nd_trang_thai, s = STATE[k], h = horizons(M)[0], parts = [], title = [];
    var b = show.band && h ? bandAt(M, h.k, i) : null;
    if (show.state) {
      var n = s && finite(p.nd_tu) ? i - p.nd_tu + 1 : null;
      var tt = h ? timeText(M, p, h.k) : '';
      parts.push(s ? 'Trạng thái: ' + s.word + (k === 'range' && finite(p.nd_range_hi) ? ' ' + rng(p.nd_range_lo, p.nd_range_hi, M.digits) : '') +
        (n ? ' · ' + n + ' nến (từ #' + p.nd_tu + ')' : '') + tt : 'Trạng thái: ' + NOT_READY);
      if (p.nd_nen) parts[parts.length - 1] += ' · nén';
      if (s) title.push('Trạng thái là mô tả, không phải dự báo hướng: ' + reasons(M)[k] + '.' +
        (p.nd_nen ? ' «nén» = biến động co lại (BB trong KC, độ rộng BB thấp) — cờ đi kèm, không phải trạng thái.' : '') + (tt
        ? ' «giữ ' + h.k + '» = xác suất trạng thái đang hiện vẫn còn sau ' + h.k + '; «còn» = thời gian còn lại trung vị (từ các đoạn cùng trạng thái đã qua).'
        : ''));
    }
    if (b) {
      parts.push(h.k + ' 80% ' + rng(b.lo80, b.hi80, M.digits));
      title.push('Khoảng ' + h.k + ' 80%: 80% khả năng cả đường giá ' + parseInt(h.k, 10) + ' giờ sau nến này nằm trong khoảng ' +
        '(điểm thật ở tooltip khoảng / tab Thống kê).');
    } else if (show.band) {
      parts.push(h ? 'Khoảng: chưa đủ mẫu (khởi động)' : 'Khoảng: khung này không có tầm 1h / 4h');
    }
    if (!parts.length) return null;
    var own = show.state && s;
    return { key: own ? k : null, color: own ? s.color : null, text: parts.join(' │ '), title: title.join(' ') };
  }

  // ------------------------------------------------------------------ khoảng giá 1h / 4h + xác suất chạm (lớp ict_nd_band)

  var COL_BAND = V.COL.grey;
  var MIN_VERDICT = 100;   // dưới số khoảng đã chấm này không kết luận «tốt hơn / kém hơn B0»
  /** Mức kèm xác suất chạm (pending.nhan_dien.muc của lõi); tag = tên in trên nhãn đường (mức có tên riêng). */
  var LEVEL = {
    vung_tren: { word: 'vùng trên gần nhất (BSL)', short: 'BSL gần', col: V.COL.bsl },
    vung_duoi: { word: 'vùng dưới gần nhất (SSL)', short: 'SSL gần', col: V.COL.ssl },
    pdh: { word: 'PDH (đỉnh ngày trước)', short: 'PDH', tag: 'PDH', col: V.COL.bsl },
    pdl: { word: 'PDL (đáy ngày trước)', short: 'PDL', tag: 'PDL', col: V.COL.ssl },
    range_tren: { word: 'biên trên range', short: 'biên trên', col: COL_RANGE },
    range_duoi: { word: 'biên dưới range', short: 'biên dưới', col: COL_RANGE }
  };

  /** pending_state.nhan_dien của đúng nến con trỏ (lõi đóng dấu `nen`) — {} khi không có / khác nến (không tô ngược). */
  function ndAt(M) {
    var nd = M && M.pending && M.pending.nhan_dien;
    return nd && nd.nen === M.cursor ? nd : {};
  }
  /** Tầm → số nến (pending.nhan_dien.tam_nen, cố định cả lần chạy), tầm dài trước. */
  function horizons(M) {
    var tn = ((M.pending && M.pending.nhan_dien) || {}).tam_nen || {};
    return Object.keys(tn).sort(function (a, b) { return tn[b] - tn[a]; }).map(function (k) { return { k: k, bars: tn[k] }; });
  }
  /** Khoảng của tầm k sau nến i (cột timeline nd_<k>_*, mặc định nến con trỏ) — null khi khởi động / tầm không có. */
  function bandAt(M, k, i) {
    var p = M.tl[i === undefined ? M.cursor : i], pre = 'nd_' + k + '_';
    if (!p || !finite(p[pre + 'lo80'])) return null;
    return { lo80: p[pre + 'lo80'], hi80: p[pre + 'hi80'], lo50: p[pre + 'lo50'], hi50: p[pre + 'hi50'] };
  }
  function levelsAt(M) { return (ndAt(M).muc || []).filter(function (m) { return LEVEL[m.loai]; }); }
  /** Nhóm vẽ chung một đường / một dòng với m: mức có tên riêng (PDH / PDL) cùng phía, cùng giá — cùng khoảng cách nên
   *  cùng xác suất — gộp vào mức không tên (vùng gần nhất, biên range); mức không tên không gộp với nhau (như 0.7.0).
   *  null khi m đã gộp vào mức khác. */
  function groupOf(ms, m) {
    var same = ms.filter(function (x) { return x.phia === m.phia && x.gia === m.gia; });
    if (LEVEL[m.loai].tag) return same.some(function (x) { return !LEVEL[x.loai].tag; }) ? null : [m];
    return [m].concat(same.filter(function (x) { return LEVEL[x.loai].tag; }));
  }
  function levelNames(group, field) { return group.map(function (x) { return LEVEL[x.loai][field || 'word']; }).join(' = '); }
  /** «1h 12% · 4h 40%» theo các tầm lõi có (p_<tầm> của dòng mức, cùng thứ tự). */
  function touchText(m) {
    return Object.keys(m).filter(function (k) { return k.indexOf('p_') === 0; }).map(function (k) {
      return k.slice(2) + ' ' + pct(m[k]);
    }).join(' · ');
  }
  /** Nguồn mẫu của từng tầm: giờ New York (đủ mẫu) hay mẫu chung mọi giờ. */
  function sourceText(nd) {
    var kh = nd.khoang || {};
    return Object.keys(kh).map(function (k) { return k + ' ' + (kh[k].nguon === 'gio' ? 'giờ NY ' + kh[k].gio_ny + 'h' : 'mẫu chung'); }).join(' · ');
  }
  function brierText(r) { return 'Brier ' + num(r.brier, 3) + ' (B0 ' + num(r.brier_b0, 3) + ', ' + r.n + ' lần)'; }
  function brierPair(r) { return num(r.brier, 3) + ' (' + num(r.brier_b0, 3) + ')'; }
  /** Điểm thật mỗi tầm đã chấm: «4h Brier 0.26 (B0 0.25, 300 lần)» ('' khi chưa chấm); fmt thay brierText khi cần. */
  function probScores(sc, fmt) {
    return Object.keys(sc || {}).map(function (k) { return sc[k] && sc[k].n ? k + ' ' + (fmt || brierText)(sc[k]) : null; })
      .filter(Boolean).join(' · ');
  }
  /** « · giữ 4h 62% · còn ~6 nến (1.5h)» từ timeline nến p (tầm k) — '' khi lõi chưa có xác suất còn giữ. */
  function timeText(M, p, k) {
    var g = p['nd_giu_' + k], r = p.nd_con_lai;
    if (!finite(g)) return '';
    return ' · giữ ' + k + ' ' + pct(g) + (finite(r) ? ' · còn ~' + num(r, 0) + ' nến' +
      (M.step ? ' (' + hoursText(M, r) + ')' : '') : '');
  }
  /** Số nến → «1.5h» (khung chạy biết bước) hoặc «6 nến». */
  function hoursText(M, bars) { return M.step ? num(bars * M.step / 3600, 1) + 'h' : num(bars, 0) + ' nến'; }
  /** « · phá 4h 35%» cho range đang có (tầm dài nhất, cột timeline ở con trỏ). */
  function breakText(M) {
    var h = horizons(M)[0], b = h && (M.tl[M.cursor] || {})['nd_pha_' + h.k];
    return finite(b) ? ' · phá ' + h.k + ' ' + pct(b) : '';
  }

  var MIN_P = 0.10;      // mức có xác suất chạm (tầm dài) dưới ngưỡng này không vẽ / không ghi ở bảng (vẫn ở «Đang theo dõi»)
  var MAX_SIDE = 2;      // số mức tối đa mỗi phía trên chart

  /** Mức vẽ trên chart / ghi ở bảng (cùng một bộ chọn): đại diện nhóm trùng giá, p tầm dài ≥ MIN_P, nằm trong khoảng
   *  80% của tầm dài (ngoài nón thì gần như không tới — đỡ rối), tối đa MAX_SIDE mỗi phía, gần trước. */
  function shownLevels(M, k) {
    var b = bandAt(M, k), kL = 'p_' + k, lv = levelsAt(M), shown = { up: 0, down: 0 };
    if (!b) return [];
    return lv.filter(function (m) {
      return groupOf(lv, m) && finite(m[kL]) && m[kL] >= MIN_P && (m.phia === 'up' ? m.gia <= b.hi80 : m.gia >= b.lo80);
    }).sort(function (x, y) { return Math.abs(x.kc_atr) - Math.abs(y.kc_atr); })
      .filter(function (m) { return shown[m.phia]++ < MAX_SIDE; })
      .map(function (m) { return { m: m, group: groupOf(lv, m), p: m[kL] }; });
  }

  /** Khoảng mỗi tầm = vùng xám cùng bắt đầu ở con trỏ, dài tới hết tầm: khoảng của lõi là khoảng của CẢ đường giá nên
   *  đúng ngay từ nến kế tiếp tới hết tầm — vẽ từ con trỏ là đúng nghĩa (nón bậc / nón quạt trước đây: plan_nhan_dien_v2
   *  §4). Tầm dài vẽ trước (nhạt), tầm ngắn đè lên (đậm hơn); lõi 50% đậm hơn 80% (tô chồng); không viền; nhãn giá ở mép
   *  phải (kẹp mép khi ngoài khung giá; đặt sau nhãn «chạm …»); + mức kèm xác suất chạm (shownLevels, nét đậm theo xác suất). */
  function bandDrawing(M, logicalOf) {
    var out = { segments: [], boxes: [] }, c = M.cursor, la = logicalOf(c) + 0.5;
    var anchors = horizons(M).map(function (h) { return { k: h.k, b: bandAt(M, h.k), x2: logicalOf(c + h.bars) + 0.5 }; })
      .filter(function (a) { return a.b; });          // tầm dài trước
    if (!anchors.length) return out;               // chưa có khoảng (khởi động) → cũng chưa có xác suất chạm
    anchors.forEach(function (a, i) {
      var id = 'nd:band:' + a.k, fill = V.rgba(COL_BAND, i ? 0.1 : 0.06);
      out.boxes.push({ id: id, l1: la, l2: a.x2, p1: a.b.lo80, p2: a.b.hi80, fill: fill, autoscale: false });
      out.boxes.push({ id: id, l1: la, l2: a.x2, p1: a.b.lo50, p2: a.b.hi50, fill: fill, autoscale: false });
      ['hi80', 'lo80'].forEach(function (key) {
        var text = a.k + ' ' + V.fp(a.b[key], M.digits);
        out.segments.push({ id: id, noLine: true, l1: a.x2, l2: a.x2, p1: a.b[key], p2: a.b[key], color: COL_BAND, autoscale: false,
          label: { text: text, edgeText: text, pos: 'right', priority: 7.2, size: 9, alpha: 0.85 } });
      });
    });
    shownLevels(M, anchors[0].k).forEach(function (x) {
      var m = x.m, tag = x.group.map(function (g) { return LEVEL[g.loai].tag; }).filter(Boolean).join(' ');
      out.segments.push({ id: 'nd:muc:' + m.loai, l1: la, l2: anchors[0].x2, p1: m.gia, p2: m.gia, color: LEVEL[m.loai].col,
        width: x.p >= 0.5 ? 2 : 1, style: 'dotted', alpha: 0.45 + 0.5 * x.p, autoscale: false,
        label: { text: (tag ? tag + ' ' : '') + 'chạm ' + touchText(m), pos: 'right', priority: 6.9, size: 10, alpha: 0.9 } });
    });
    return out;
  }

  /** Bảng «Nhận diện» (góc phải chart) ở nến con trỏ — mọi con số một chỗ, title ghi điểm thật lõi gửi kèm. */
  function panel(M) {
    var p = M && M.tl[M.cursor];
    if (!p || !hasOwn(p, 'nd_trang_thai')) return null;
    var nd = ndAt(M), h = horizons(M)[0], k = p.nd_trang_thai, s = STATE[k], title = 'Nhận diện · #' + M.cursor;
    var n = s && finite(p.nd_tu) ? M.cursor - p.nd_tu + 1 : null;
    var trend = k === 'trend_len' || k === 'trend_xuong';      // độ mạnh (ER / ADX / động lượng) chỉ có nghĩa với trend
    var rows = [{ k: 'Trạng thái', v: s ? s.word + (n ? ' · ' + hoursText(M, n) : '') +
      (trend && finite(p.nd_do_manh) ? ' · mạnh ' + num(p.nd_do_manh, 2) : '') + (p.nd_nen ? ' · nén' : '') : 'chưa đủ nến',
      title: s ? 'Mô tả, không phải dự báo hướng: ' + reasons(M)[k] + '.' : '' }];
    if (!h) return { title: title, rows: rows };
    var ds = (nd.thoi_gian || {}).diem_that || {}, sc;
    if (finite(p['nd_giu_' + h.k])) {
      sc = probScores(ds.con_giu);
      rows.push({ k: 'Còn giữ ' + h.k, v: pct(p['nd_giu_' + h.k]) + (finite(p.nd_con_lai) ? ' · còn ~' + hoursText(M, p.nd_con_lai) : ''),
        title: 'Xác suất trạng thái đang hiện vẫn còn sau ' + h.k + ' (từ các đoạn đã qua). ' +
          (sc ? 'Điểm thật: ' + sc + '.' : 'Điểm thật: chưa có số liệu ở nến này.') });
    }
    var b = bandAt(M, h.k), bs = (nd.diem_that || {})[h.k];
    if (!b) {
      rows.push({ k: 'Khoảng ' + h.k, v: 'chưa đủ mẫu (khởi động)', title: 'Khoảng và xác suất chạm có khi đủ mẫu biên.' });
      return { title: title, rows: rows };
    }
    rows.push({ k: 'Khoảng ' + h.k + ' 80%', v: rng(b.lo80, b.hi80, M.digits) + (bs && bs.n ? ' · phủ thật ' + pct1(bs.phu_80) : ''),
      title: 'Lõi 50% ' + rng(b.lo50, b.hi50, M.digits) + '. ' + scoreText(bs) });
    var near = shownLevels(M, h.k);
    if (near.length) {
      rows.push({ k: 'Chạm ' + h.k, v: near.map(function (x) { return levelNames(x.group, 'short') + ' ' + pct(x.p); }).join(' · '),
        title: 'Xác suất bị chạm trong ' + h.k + ' (mức bất kỳ cùng khoảng cách, cùng giờ NY — lõi) của các mức đang vẽ ' +
          '(trong khoảng 80%, ≥ ' + pct(MIN_P) + ', tối đa ' + MAX_SIDE + ' mỗi phía). Rê chuột vào đường mức để xem điểm thật.' });
    }
    if (finite(p['nd_pha_' + h.k])) {
      sc = probScores(ds.pha_bien);
      rows.push({ k: 'Phá biên ' + h.k, v: pct(p['nd_pha_' + h.k]), title: 'Xác suất close ra ngoài biên range trong ' + h.k + '. ' +
        (sc ? 'Điểm thật: ' + sc + '.' : 'Điểm thật: chưa có số liệu ở nến này.') });
    }
    return { title: title, rows: rows };
  }

  function scoreText(s) {
    if (!s) return 'Điểm thật: chưa có số liệu ở nến này.';
    if (!s.n) return 'Điểm thật: chưa có khoảng nào đủ kết cục để chấm.';
    var sk = s.skill_so_voi_b0, vsB0 = !finite(sk) ? '' : s.n < MIN_VERDICT ? ', chưa đủ ' + MIN_VERDICT + ' khoảng để so với B0'
      : ', ' + (sk > 0 ? 'tốt hơn' : sk < 0 ? 'kém hơn' : 'ngang') + ' B0 (bỏ giờ NY)' + (sk ? ' ' + pct1(Math.abs(sk)) : '');
    return 'Điểm thật tới nến này (' + s.n + ' khoảng đã có kết cục): phủ 80% thực tế ' + pct1(s.phu_80) + ', phủ 50% ' +
      pct1(s.phu_50) + ', rộng trung bình ' + num(s.rong_80_atr, 1) + ' ATR' + vsB0 + '.';
  }

  function bandTip(M, k) {
    var b = bandAt(M, k), bars = (((M.pending && M.pending.nhan_dien) || {}).tam_nen || {})[k], nd = ndAt(M);
    var kh = (nd.khoang || {})[k], d = M.digits;
    if (!b || !bars) return null;
    return [{ head: 'Khoảng ' + k + ' tới: 80% ' + rng(b.lo80, b.hi80, d) + ' · lõi 50% ' + rng(b.lo50, b.hi50, d),
      body: '80% khả năng CẢ đường giá ' + parseInt(k, 10) + ' giờ tới (' + bars + ' nến) nằm trong khoảng ngoài, 50% trong ' +
        'khoảng lõi' + (kh ? '. Theo mẫu biên ' + (kh.nguon === 'gio' ? 'của giờ New York ' + kh.gio_ny + 'h' : 'chung mọi giờ') +
        ' (' + kh.n_mau + ' mẫu gần nhất) nhân ATR' : '') + ' — không nói giá sẽ đi lên hay xuống. Trên chart: vùng xám từ con trỏ tới hết ' + k +
        ' (tầm ngắn đậm hơn), lõi 50% đậm hơn.',
      more: scoreText((nd.diem_that || {})[k]) }];
  }

  /** «+0.3 điểm» — chạm thật − kỳ vọng của một loại mức (lõi tính: ``chenh``). */
  function attract(r) { return finite(r.chenh) ? (r.chenh >= 0 ? '+' : '−') + Math.abs(100 * r.chenh).toFixed(1) + ' điểm' : '—'; }
  /** Điểm thật của loại mức ``loai`` mỗi tầm: «4h Brier 0.10 (B0 0.11, 300 lần), chạm thật 12.0% / kỳ vọng 10.0%». */
  function touchScores(sc, loai) {
    return probScores(Object.keys(sc).reduce(function (o, k) { o[k] = (sc[k].cham || {})[loai]; return o; }, {}), function (r) {
      return brierText(r) + (finite(r.ty_le_cham) ? ', chạm thật ' + pct1(r.ty_le_cham) + ' / kỳ vọng ' + pct1(r.p_tb) : '');
    });
  }

  /** Mức trùng giá (vd vùng gần nhất = PDH): dòng đầu là xác suất chung, mỗi loại mức một dòng điểm thật riêng. */
  function levelTip(M, loai) {
    var nd = ndAt(M), lv = levelsAt(M), m = lv.filter(function (x) { return x.loai === loai; })[0], sc = nd.diem_that || {};
    if (!m) return null;
    var group = groupOf(lv, m) || [m];
    return group.map(function (x, i) {
      var s = touchScores(sc, x.loai), score = s ? 'Điểm thật tới nến này: ' + s + '. Brier nhỏ hơn B0 = tốt hơn mẫu bỏ giờ ' +
        'NY; chạm thật cao hơn kỳ vọng = loại mức này hút giá hơn một mức bất kỳ.' : 'Điểm thật: chưa đủ kết cục để chấm.';
      if (i) return { head: 'Điểm thật của loại «' + LEVEL[x.loai].word + '»', body: score };
      return { head: 'Xác suất chạm ' + levelNames(group) + ' ' + V.fp(m.gia, M.digits) + ': ' + touchText(m),
        body: 'Tỷ lệ mẫu có biên ≥ khoảng cách hiện tại tới mức (' + sourceText(nd) + ') = xác suất chạm một mức bất kỳ đặt ' +
          'đúng khoảng cách đó — xác suất bị chạm, không phải xác suất giá dừng ở đó.', more: score };
    });
  }

  function stateBody(x, k, d) {
    if (isV2(x)) return stateBodyV2(x, k, d);
    if (k === 'range') {
      return 'Cửa sổ ' + x.cua_so_nen + ' nến: biên ' + rng(x.bien_duoi, x.bien_tren, d) + ', rộng ' + num(x.rong_atr, 1) +
        ' ATR, ER ' + num(x.er, 2) + '; chạm biên trên ' + (x.cham_tren || []).length + ' lần, biên dưới ' +
        (x.cham_duoi || []).length + ' lần (swing 2/2 trong ' + V.fp(x.dung_sai, d) + ').';
    }
    if (k === 'nen') {
      return 'Cửa sổ ' + x.cua_so_nen + ' nến: ba đỉnh ' + (x.dinh || []).map(function (v) { return V.fp(v, d); }).join(' > ') +
        ', ba đáy ' + (x.day || []).map(function (v) { return V.fp(v, d); }).join(' < ') + '; bề rộng cuối / đầu = ' +
        num(x.ty_le_rong, 2) + ', ER ' + num(x.er, 2) + '.';
    }
    if (k === 'trend_len' || k === 'trend_xuong') {
      return 'ER ' + num(x.er, 2) + ' trên ' + x.cua_so_nen + ' nến' +
        (x.thu_tu_cung_chieu === undefined ? '' : '; thứ tự cấu trúc ' + (x.thu_tu_cung_chieu ? 'cùng chiều' : 'chưa cùng chiều')) + '.';
    }
    return 'ER ' + num(x.er, 2) + ' trên ' + x.cua_so_nen + ' nến; không có biên bị chạm lặp lại, không nén.';
  }
  /** Lý do trạng thái v2: vì sao vào (ly_do), vì sao thoát trạng thái trước (thoat), số liệu đã dùng. */
  function stateBodyV2(x, k, d) {
    var ev = 'ER ' + num(x.er, 2) + ' / ' + x.cua_so_nen + ' nến, ADX ' + num(x.adx, 0) + ', động lượng ' + num(x.dong_luong_atr, 1) +
      ' ATR, cấu trúc ' + (ORDER_V2[x.cau_truc] || '—') + (x.cau_truc_pha ? ' (mức bảo vệ đã phá)' : '') + ' · H1 ' +
      (ORDER_V2[x.cau_truc_h1] || '—');
    var head = k === 'range' ? 'Hộp ' + rng(x.bien_duoi, x.bien_tren, d) + ', rộng ' + num(x.rong_atr, 1) + ' ATR; thăm biên trên ' +
      (x.tham_tren || []).length + ' lần, biên dưới ' + (x.tham_duoi || []).length + ' lần; ' + ev
      : (WHY_V2[x.ly_do] || x.ly_do || '') + ': ' + ev;
    return head + (x.thoat ? '. Trạng thái trước kết thúc vì ' + (EXIT_V2[x.thoat] || x.thoat) : '') + (x.nen ? '. Đang nén' : '') + '.';
  }

  /** id «nd:state:<nến>» (dải), «nd:range:<nến đầu đoạn>» (hộp range) → đoạn chứa nến đó (mới nhất trước);
   *  «nd:band:<tầm>» / «nd:muc:<loại mức>» → khoảng / mức kèm điểm thật. */
  function info(M, id) {
    if (!M || typeof id !== 'string' || id.indexOf('nd:') !== 0) return null;
    var parts = id.split(':');
    if (parts[1] === 'band') return bandTip(M, parts[2]);
    if (parts[1] === 'nen') {
      return [{ head: 'Nén · #' + parts[2], body: 'Biến động co lại: Bollinger (20, 2) nằm trong Keltner (20, 1,5) và độ rộng Bollinger ' +
        'thuộc 20% thấp nhất của 500 nến — cờ đi kèm trạng thái, không phải trạng thái, không nói hướng.' }];
    }
    if (parts[1] === 'muc') return levelTip(M, parts[2]);
    var i = +parts[2], eps = episodes(M), ep = null;
    for (var j = eps.length - 1; j >= 0 && !ep; j--) if (eps[j].from <= i && i <= eps[j].to) ep = eps[j];
    if (!ep) return [{ head: 'Trạng thái: chưa đủ nến', body: 'Sau khoảng trống dài hoặc lúc khởi động, lõi chưa đủ nến để xét.' }];
    var ev = ep.ev, x = (ev && ev.details) || {}, live = ep.to === M.cursor;
    var rows = [{ head: 'Trạng thái: ' + STATE[ep.key].word + ' · #' + ep.from + ' → #' + ep.to + (live ? ' (đang có)' :
        BREAK[ep.brk] ? ' (kết thúc: ' + BREAK[ep.brk].word.slice(2) + ')' : ''),
      body: ev ? stateBody(x, ep.key, M.digits) + (x.doi_ngay ? ' Đổi ngay khi sự kiện đã xác nhận' : ' Đổi trạng thái khi ứng viên giữ đủ ' +
        x.giu_nen + ' nến') + ' (xác nhận ở #' +
        ev.confirmed_bar_index + ').' : reasons(M)[ep.key] + '.',
      more: 'Mô tả trạng thái hiện tại, không phải dự báo hướng. Định nghĩa: plan nhận diện §3 (ngưỡng do lab chọn).' }];
    var t = live ? timeLines(ndAt(M), M.digits) : [];
    if (t.length) rows.push({ head: 'Thời gian (dự báo, chấm trên kết cục)', body: t.join(' ') });
    return rows;
  }

  function eventText(e, d) {
    var k = e && BY_TYPE[e.structure_type];
    if (!k) return null;
    return 'Chuyển sang ' + STATE[k].word + ' từ nến #' + e.event_bar_index + ': ' + stateBody(e.details || {}, k, d);
  }

  function pendingLines(ps, d) {
    var nd = ps && ps.nhan_dien, out = [];
    if (!nd) return out;
    var k = nd.trang_thai;
    out.push({ kind: 'state', text: k ? 'Trạng thái ' + STATE[k].word + ' (từ #' + nd.tu_nen + '): ' + stateBody(nd.chi_tiet || {}, k, d)
      : 'Trạng thái: ' + NOT_READY + '.' });
    var c = nd.ung_vien;
    if (c && STATE[c.trang_thai]) {
      out.push({ kind: 'pending', text: 'Ứng viên ' + STATE[c.trang_thai].word + ' từ #' + c.tu_nen + ': ' + c.so_nen + '/' +
        c.can + ' nến — đủ thì đổi trạng thái.' });
    }
    timeLines(nd, d).forEach(function (t) { out.push({ kind: 'state', text: t }); });
    Object.keys(nd.khoang || {}).forEach(function (k) {
      var b = nd.khoang[k], s = (nd.diem_that || {})[k] || {};
      out.push({ kind: 'state', text: 'Khoảng ' + k + ': 80% ' + rng(b.lo80, b.hi80, d) + ', lõi 50% ' + rng(b.lo50, b.hi50, d) +
        (s.n ? ' — phủ 80% thực tế ' + pct1(s.phu_80) + ' trên ' + s.n + ' khoảng đã chấm.' : ' — chưa có khoảng nào đủ kết cục.') });
    });
    var lv = (nd.muc || []).filter(function (m) { return LEVEL[m.loai]; });
    lv.forEach(function (m) {
      var group = groupOf(lv, m);
      if (!group) return;                          // PDH / PDL trùng giá → một dòng ghi đủ tên
      out.push({ kind: 'state', text: 'Xác suất chạm ' + levelNames(group) + ' ' + V.fp(m.gia, d) + ' (cách ' + num(m.kc_atr, 1) +
        ' ATR): ' + touchText(m) + '.' });
    });
    return out;
  }

  /** Câu «thời gian» từ pending.nhan_dien.thoi_gian (0.7.0): còn giữ + thời gian còn lại, phá biên khi range — kèm
   *  điểm thật. Tuổi = số nến trạng thái đã HIỆN (khác «n nến từ #…» của hàng 3: tính từ nến đầu của ứng viên). */
  function timeLines(nd, d) {
    var tg = nd.thoi_gian || {}, ds = tg.diem_that || {}, g = tg.con_giu, pb = tg.pha_bien, out = [], s;
    if (g) {
      s = probScores(ds.con_giu);
      out.push('Còn giữ sau ' + pctByKey(g.giu) + ' (đã hiện ' + g.tuoi_nen + ' nến; còn lại trung vị ' + num(g.con_lai_nen, 1) +
        ' nến; mẫu ' + g.n_doan_con + '/' + g.n_doan + ' đoạn ' + (g.nguon === 'trang_thai' ? 'cùng trạng thái' : 'mọi trạng thái') +
        ' dài ≥ tuổi này)' +
        (s ? ' — điểm thật: ' + s : '') + '.');
    }
    if (pb) {
      s = probScores(ds.pha_bien);
      out.push('Phá biên range ' + rng(pb.lo, pb.hi, d) + ' (close ra ngoài): ' + pctByKey(pb.p) + (s ? ' — điểm thật: ' + s : '') + '.');
    }
    return out;
  }

  /** Ô «<nhãn> <tầm> — Brier (B0)» mỗi tầm đã chấm của một xác suất «thời gian» (run_stats.nhan_dien.thoi_gian). */
  function probRows(rows, label, byK, what, b0) {
    Object.keys(byK || {}).forEach(function (k) {
      var r = byK[k];
      if (r && r.n) {
        rows.push({ k: label + ' ' + k + ' — Brier (B0)', v: brierPair(r), title: r.n + ' lần đã có kết cục; tỷ lệ thật ' +
          pct1(r.ty_le) + ' (' + what + ').' + (b0 ? ' B0 = ' + b0 + '.' : '') + ' Brier nhỏ hơn = tốt hơn.' });
      }
    });
  }

  /** Ô thống kê «điểm thật» (run_stats.nhan_dien): khoảng mỗi tầm, xác suất chạm, tỷ lệ thời gian theo trạng thái. */
  function statsRows(st) {
    if (!st || !st.khoang_va_cham) return [];
    var rows = [];
    Object.keys(st.khoang_va_cham).forEach(function (k) {
      var s = st.khoang_va_cham[k];
      rows.push({ k: 'Khoảng ' + k + ' — phủ thực tế 80% / 50%', v: pct1(s.phu_80) + ' / ' + pct1(s.phu_50),
        title: s.n + ' khoảng đã có kết cục; rộng TB ' + num(s.rong_80_atr, 2) + ' ATR (lõi ' + num(s.rong_50_atr, 2) + ' ATR); ' +
          'skill so với B0 (bỏ giờ NY) ' + pct1(s.skill_so_voi_b0) + '. Mục tiêu: 80% / 50%.' });
      var hrs = (s.phu_80_theo_gio || []).filter(function (r) { return r.n >= MIN_VERDICT; });
      if (hrs.length) {
        var lo = hrs.reduce(function (a, r) { return r.phu_80 < a.phu_80 ? r : a; });
        var hi = hrs.reduce(function (a, r) { return r.phu_80 > a.phu_80 ? r : a; });
        rows.push({ k: 'Khoảng ' + k + ' — phủ 80% theo giờ NY (thấp / cao nhất)',
          v: pct1(lo.phu_80) + ' (' + lo.gio + 'h) / ' + pct1(hi.phu_80) + ' (' + hi.gio + 'h)',
          title: 'Giờ có ≥ ' + MIN_VERDICT + ' khoảng đã chấm: ' + hrs.map(function (r) { return r.gio + 'h ' + pct1(r.phu_80); }).join(' · ') });
      }
      var ct = s.cham_tong, ch = s.cham || {};
      if (ct && ct.n) {                              // ô tiêu đề: Brier gộp các loại lõi chọn (cham_tong_loai), từng loại ở title
        var tk = s.cham_tong_loai;
        rows.push({ k: 'Xác suất chạm ' + k + ' — Brier (B0)', v: brierPair(ct),
          title: 'Gộp ' + (tk ? tk.map(function (kind) { return LEVEL[kind] ? LEVEL[kind].short : kind; }).join(', ') : 'mọi mức') + ', ' +
            ct.n + ' lần. ' + Object.keys(ch).map(function (kind) {
            return (LEVEL[kind] ? LEVEL[kind].word : kind) + ': ' + brierText(ch[kind]);
          }).join(' · ') });
      }
      var ok = Object.keys(ch).filter(function (kind) { return LEVEL[kind] && ch[kind].n >= MIN_VERDICT && finite(ch[kind].chenh); });
      var pd = ['pdh', 'pdl'].filter(function (kind) { return ok.indexOf(kind) >= 0; });
      if (pd.length) {                               // 0.8.0: PDH / PDL có hút giá hơn mức bất kỳ không, so với vùng ICT
        rows.push({ k: 'PDH / PDL ' + k + ' — chạm thật − kỳ vọng',
          v: pd.map(function (kind) { return LEVEL[kind].short + ' ' + attract(ch[kind]); }).join(' · '),
          title: 'Kỳ vọng = xác suất chạm một mức bất kỳ cùng khoảng cách, cùng giờ NY (chính p của lõi); > 0 = hút giá hơn. ' +
            ok.map(function (kind) {
              var r = ch[kind];
              return LEVEL[kind].short + ' ' + attract(r) + ' (' + pct1(r.ty_le_cham) + ' / ' + pct1(r.p_tb) + ', ' + r.n + ' lần)';
            }).join(' · ') + '. Dự báo ở các nến liền nhau chồng lấn — kết luận theo CI khối tuần ở docs/research/khao_sat_pdh_pdl.md.' });
      }
    });
    var tg = st.thoi_gian || {}, b0 = tg.b0_vi || {};
    probRows(rows, 'Còn giữ', tg.con_giu, 'trạng thái đang hiện vẫn còn sau tầm', b0.con_giu);
    probRows(rows, 'Phá biên range', tg.pha_bien, 'close ra ngoài biên range trong tầm', b0.pha_bien);
    var ts = st.trang_thai || {}, tt = ts.ty_le_thoi_gian || {};
    var v2 = ts.kieu === 'v2', keys = stateKeys(v2);
    rows.push({ k: 'Thời gian: trend ↑ / ↓ / range / ' + (v2 ? '' : 'nén / ') + 'nhiễu' + (v2 ? ' · cờ nén' : ''),
      v: keys.map(function (k) { return pct(tt[k]); }).join(' / ') + (v2 ? ' · ' + pct(ts.ty_le_co_nen) : ''),
      title: 'Tỷ lệ nến theo trạng thái đang hiện (mô tả). Đổi trạng thái ' + (ts.so_lan_doi || 0) + ' lần.' +
        (v2 ? ' Nén là cờ đi kèm (biến động co lại), có thể trùng range / nhiễu.' : '') });
    return rows;
  }

  /** Trang Live MT5 — điểm forward của một tầm (core/eval/forward.py `score`): hàng {k, n, v} — độ phủ, skill pinball so
   * với B0, Brier chạm / còn giữ / phá biên so với B0 (cùng định nghĩa với điểm thật trong lần chạy); dưới `min` dự báo đã
   * chấm thì ghi «chưa kết luận». */
  function forwardRows(s, min) {
    function few(n) { return n < min ? ' · chưa kết luận' : ''; }
    function brier(k, r) {
      return { k: k, n: (r && r.n) || 0, v: r && r.n ? num(r.brier, 3) + ' (B0 ' + num(r.brier_b0, 3) + ')' + few(r.n) : '—' };
    }
    return [
      { k: 'Khoảng 80% — độ phủ (mục tiêu 80%)', n: s.n, v: pct1(s.phu_80) + few(s.n) },
      { k: 'Khoảng 50% — độ phủ (mục tiêu 50%)', n: s.n, v: pct1(s.phu_50) },
      { k: 'Khoảng 80% — skill pinball so với B0 (> 0 là hơn B0)', n: s.n, v: pct1(s.skill_so_voi_b0) },
      brier('Chạm mức gần nhất / biên range — Brier', s.cham_tong),
      brier('Còn giữ trạng thái — Brier', s.con_giu),
      brier('Phá biên range — Brier', s.pha_bien)
    ];
  }

  MSL.ictNdView = {
    has: has, meta: meta, isType: function (t) { return !!BY_TYPE[t]; },
    bandBars: bandBars, episodes: episodes, drawing: drawing, bandDrawing: bandDrawing, statusAt: statusAt, info: info,
    squeezeBars: squeezeBars, panel: panel, hasLine: hasLine, trendLine: trendLine,
    eventText: eventText, pendingLines: pendingLines, statsRows: statsRows, forwardRows: forwardRows,
    PANE: PANE, paneHas: paneHas, statePaneSeries: statePaneSeries, statePaneLegend: statePaneLegend, statePaneText: statePaneText
  };
})(window.MSL);
