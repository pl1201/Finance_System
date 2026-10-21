/* ict_structure 0.6.0 — lớp nhận diện: phần dựng hình THUẦN (MSL.ictNdView). Không vẽ, không DOM, không gọi LWC → chạy
 * được trong node (tests/frontend/test_ict_nhan_dien_display.py). Nạp SAU algos/ict_structure_view.js (dùng mô hình M của
 * MSL.ictView.buildModel — M.tl, M.tlList, M.list — và hasOwn / finite / rgba / fp / fpRange / COL).
 *
 * Chỉ ĐỌC lõi (core/algorithms/ict_structure/nhan_dien.py; đặc tả docs/algorithms/thuat_toan_nhan_dien.md):
 *   - trạng thái sau mỗi nến: cột timeline nd_trang_thai / nd_tu / nd_range_tu / nd_range_hi / nd_range_lo;
 *   - lúc đổi trạng thái: sự kiện STATE_* (details: cửa sổ, ER, biên, lần chạm…);
 *   - «Đang theo dõi»: pending_state.nhan_dien (trạng thái kèm lý do, ứng viên đang chờ đủ nến).
 * Nhân quả: mọi thứ từ M (timeline ≤ con trỏ, sự kiện confirmed ≤ con trỏ).
 *
 *   has(M)                         kết quả có lớp nhận diện (≥ 0.6.0, nd_bat)
 *   meta(type)                     {state, short, color} của sự kiện STATE_* | null
 *   bandBars(M, logicalOf)         dải «trạng thái» theo nến cho MSL.primitives.Band
 *   episodes(M)                    đoạn trạng thái liên tiếp ≤ con trỏ, kèm sự kiện mở đoạn (tính một lần mỗi M)
 *   drawing(M, logicalOf)          {segments, boxes}: hộp range đang có + range gần nhất đã qua
 *   statusAt(M, i)                 {key, color, text, title} cho dòng trạng thái | null
 *   info(M, id)                    tooltip [{head, body, more}] cho id «nd:…»
 *   eventText(e, digits)           câu giải thích một sự kiện STATE_* | null
 *   pendingLines(ps, digits)       [{kind, text}] «Đang theo dõi» từ pending_state.nhan_dien
 */
(function (MSL) {
  'use strict';

  var V = MSL.ictView, finite = V.finite, hasOwn = V.hasOwn, rng = V.fpRange;
  /** Màu riêng của lớp (range chàm, nén tím — không trùng BSL cam / SSL xanh ngọc / OTE vàng). */
  var COL_RANGE = '#5c6bc0', COL_SQUEEZE = '#ba68c8', COL_CHOP = '#78909c';
  var STATE = {
    trend_len: { word: 'trend lên', short: 'trend ↑', color: V.rgba(V.COL.up, 0.55), type: 'STATE_TREND_UP' },
    trend_xuong: { word: 'trend xuống', short: 'trend ↓', color: V.rgba(V.COL.down, 0.55), type: 'STATE_TREND_DOWN' },
    range: { word: 'range biên rõ', short: 'range', color: V.rgba(COL_RANGE, 0.75), type: 'STATE_RANGE' },
    nen: { word: 'sideway nén', short: 'nén', color: V.rgba(COL_SQUEEZE, 0.62), type: 'STATE_SQUEEZE' },
    nhieu: { word: 'sideway nhiễu', short: 'nhiễu', color: V.rgba(COL_CHOP, 0.45), type: 'STATE_CHOP' }
  };
  var NONE_COLOR = 'rgba(90,100,110,0.18)';
  var BY_TYPE = {};
  Object.keys(STATE).forEach(function (k) { BY_TYPE[STATE[k].type] = k; });
  var EXT = 5;   // hộp range đang có kéo tới con trỏ + EXT nến
  var REASON = {
    trend_len: 'giá đi một chiều (ER ≥ ngưỡng)', trend_xuong: 'giá đi một chiều (ER ≥ ngưỡng)',
    range: 'mỗi biên bị chạm ≥ 2 lần, ER thấp', nen: 'đỉnh thấp dần, đáy cao dần, biên co lại', nhieu: 'ER thấp, không có biên rõ'
  };

  function has(M) { return !!M && M.tlList.length > 0 && hasOwn(M.tlList[M.tlList.length - 1], 'nd_trang_thai'); }
  function meta(t) {
    var k = BY_TYPE[t];
    return k ? { state: k, short: STATE[k].short, color: STATE[k].color } : null;
  }
  function num(x, k) { return finite(x) ? x.toFixed(k) : '—'; }

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
        cur = { key: p.nd_trang_thai, from: p.nd_tu, to: null, ev: opening[p.nd_trang_thai + '|' + p.nd_tu] || null,
          rfrom: finite(p.nd_range_tu) ? p.nd_range_tu : null, hi: null, lo: null };
        out.push(cur);
      }
      cur.to = p.bar_index;
      if (finite(p.nd_range_hi)) { cur.hi = p.nd_range_hi; cur.lo = p.nd_range_lo; }
    });
    M.ndEp = out;
    return out;
  }

  function drawing(M, logicalOf) {
    var out = { segments: [], boxes: [] }, eps = episodes(M), past = false;
    for (var i = eps.length - 1; i >= 0 && !past; i--) {         // range đang có (nếu có) + một range gần nhất đã qua
      var ep = eps[i];
      if (ep.key !== 'range' || !finite(ep.hi) || !finite(ep.lo)) continue;
      var live = ep.to === M.cursor, id = 'nd:range:' + ep.from;
      past = !live;
      var l1 = logicalOf(ep.rfrom === null ? ep.from : ep.rfrom) - 0.45;
      var l2 = live ? logicalOf(M.cursor + EXT) : logicalOf(ep.to) + 0.45;
      out.boxes.push({ id: id, l1: l1, l2: l2, p1: ep.lo, p2: ep.hi, fill: V.rgba(COL_RANGE, live ? 0.08 : 0.035),
        border: V.rgba(COL_RANGE, live ? 0.9 : 0.5), borderWidth: 1.5, borderStyle: live ? 'dashed' : 'dotted',
        autoscale: false });
      out.segments.push({ id: id, noLine: true, l1: l2, l2: l2, p1: ep.hi, p2: ep.hi, color: COL_RANGE, autoscale: false,
        label: { text: live ? 'Range' : 'Range (đã qua)', pos: 'right', priority: 6.7, size: 10, alpha: live ? 0.95 : 0.65 } });
    }
    return out;
  }

  function statusAt(M, i) {
    var p = M.tl[i];
    if (!p || !hasOwn(p, 'nd_trang_thai')) return null;
    var k = p.nd_trang_thai, s = STATE[k];
    if (!s) return { key: null, color: null, text: 'Trạng thái: chưa đủ nến (sau khoảng trống / khởi động)', title: '' };
    var n = finite(p.nd_tu) ? i - p.nd_tu + 1 : null;
    var text = 'Trạng thái: ' + s.word + (k === 'range' && finite(p.nd_range_hi) ? ' ' + rng(p.nd_range_lo, p.nd_range_hi, M.digits) : '') +
      (n ? ' · ' + n + ' nến (từ #' + p.nd_tu + ')' : '');
    return { key: k, color: s.color, text: text, title: 'Mô tả, không phải dự báo hướng: ' + REASON[k] + '.' };
  }

  function stateBody(x, k, d) {
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

  /** id «nd:state:<nến>» (dải) hoặc «nd:range:<nến đầu đoạn>» (hộp) → đoạn chứa nến đó (mới nhất trước). */
  function info(M, id) {
    if (!M || typeof id !== 'string' || id.indexOf('nd:') !== 0) return null;
    var i = +id.split(':')[2], eps = episodes(M), ep = null;
    for (var j = eps.length - 1; j >= 0 && !ep; j--) if (eps[j].from <= i && i <= eps[j].to) ep = eps[j];
    if (!ep) return [{ head: 'Trạng thái: chưa đủ nến', body: 'Sau khoảng trống dài hoặc lúc khởi động, lõi chưa đủ nến để xét.' }];
    var ev = ep.ev, x = (ev && ev.details) || {};
    return [{ head: 'Trạng thái: ' + STATE[ep.key].word + ' · #' + ep.from + ' → #' + ep.to + (ep.to === M.cursor ? ' (đang có)' : ''),
      body: ev ? stateBody(x, ep.key, M.digits) + ' Đổi trạng thái khi ứng viên giữ đủ ' + x.giu_nen + ' nến (xác nhận ở #' +
        ev.confirmed_bar_index + ').' : REASON[ep.key] + '.',
      more: 'Mô tả trạng thái hiện tại, không phải dự báo hướng. Định nghĩa: plan nhận diện §3 (ngưỡng do lab chọn).' }];
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
      : 'Trạng thái: chưa đủ nến (sau khoảng trống / khởi động).' });
    var c = nd.ung_vien;
    if (c && STATE[c.trang_thai]) {
      out.push({ kind: 'pending', text: 'Ứng viên ' + STATE[c.trang_thai].word + ' từ #' + c.tu_nen + ': ' + c.so_nen + '/' +
        c.can + ' nến — đủ thì đổi trạng thái.' });
    }
    return out;
  }

  MSL.ictNdView = {
    has: has, meta: meta, isType: function (t) { return !!BY_TYPE[t]; },
    bandBars: bandBars, episodes: episodes, drawing: drawing, statusAt: statusAt, info: info,
    eventText: eventText, pendingLines: pendingLines
  };
})(window.MSL);
