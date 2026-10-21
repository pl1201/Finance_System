/* ict_structure ≥ 0.6.0 — lớp nhận diện: phần dựng hình THUẦN (MSL.ictNdView). Không vẽ, không DOM, không gọi LWC → chạy
 * được trong node (tests/frontend/test_ict_nhan_dien_display.py). Nạp SAU algos/ict_structure_view.js (dùng mô hình M của
 * MSL.ictView.buildModel — M.tl, M.tlList, M.list — và hasOwn / finite / rgba / fp / fpRange / COL).
 *
 * Chỉ ĐỌC lõi (core/algorithms/ict_structure/nhan_dien.py; đặc tả docs/algorithms/thuat_toan_nhan_dien.md):
 *   - trạng thái sau mỗi nến: cột timeline nd_trang_thai / nd_tu / nd_range_tu / nd_range_hi / nd_range_lo;
 *   - lúc đổi trạng thái: sự kiện STATE_* (details: cửa sổ, ER, biên, lần chạm…);
 *   - khoảng 80% / 50% mỗi tầm và xác suất chạm vùng gần nhất sau mỗi nến: cột nd_<tầm>_lo80… / nd_p_tren_<tầm>…;
 *   - 0.7.0: xác suất trạng thái còn giữ nd_giu_<tầm>, thời gian còn lại nd_con_lai (nến), phá biên range nd_pha_<tầm>;
 *   - «Đang theo dõi»: pending_state.nhan_dien (trạng thái kèm lý do, ứng viên, khoảng, mức, điểm thật tới nến này;
 *     0.7.0: khối thoi_gian = {con_giu, pha_bien, diem_that}) — lõi đóng dấu nến (`nen`); mức và điểm thật chỉ dùng khi
 *     nến đó là con trỏ (không tô ngược).
 * Nhân quả: mọi thứ từ M (timeline ≤ con trỏ, sự kiện confirmed ≤ con trỏ).
 *
 *   has(M)                         kết quả có lớp nhận diện (≥ 0.6.0, nd_bat)
 *   meta(type)                     {state, short, color} của sự kiện STATE_* | null
 *   bandBars(M, logicalOf)         dải «trạng thái» theo nến cho MSL.primitives.Band
 *   episodes(M)                    đoạn trạng thái liên tiếp ≤ con trỏ, kèm sự kiện mở đoạn (tính một lần mỗi M)
 *   drawing(M, logicalOf)          {segments, boxes}: hộp range đang có + range gần nhất đã qua
 *   bandDrawing(M, logicalOf)      {segments, boxes}: khoảng 1h / 4h phía trước con trỏ + mức kèm xác suất chạm
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
        label: { text: live ? 'Range' + breakText(M) : 'Range (đã qua)', pos: 'right', priority: 6.7, size: 10, alpha: live ? 0.95 : 0.65 } });
    }
    return out;
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
        (n ? ' · ' + n + ' nến (từ #' + p.nd_tu + ')' : '') + tt : 'Trạng thái: chưa đủ nến (sau khoảng trống / khởi động)');
      if (s) title.push('Trạng thái là mô tả, không phải dự báo hướng: ' + REASON[k] + '.' + (tt
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
  /** Kiểu hộp: tầm dài (vẽ trước, nhạt) / tầm ngắn (đè lên). */
  var BAND_STYLE = [
    { fill80: V.rgba(COL_BAND, 0.06), border: V.rgba(COL_BAND, 0.6), fill50: V.rgba(COL_BAND, 0.12) },
    { fill80: V.rgba(COL_BAND, 0.09), border: V.rgba(COL_BAND, 0.8), fill50: V.rgba(COL_BAND, 0.16) }
  ];
  /** Mức kèm xác suất chạm (pending.nhan_dien.muc của lõi). */
  var LEVEL = {
    vung_tren: { word: 'vùng trên gần nhất (BSL)', col: V.COL.bsl },
    vung_duoi: { word: 'vùng dưới gần nhất (SSL)', col: V.COL.ssl },
    range_tren: { word: 'biên trên range', col: COL_RANGE },
    range_duoi: { word: 'biên dưới range', col: COL_RANGE }
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
  /** Điểm thật của xác suất còn giữ / phá biên mỗi tầm: «4h Brier 0.26 (B0 0.25, 300 lần)» ('' khi chưa chấm). */
  function probScores(sc) {
    return Object.keys(sc || {}).map(function (k) { return sc[k] && sc[k].n ? k + ' ' + brierText(sc[k]) : null; })
      .filter(Boolean).join(' · ');
  }
  /** « · giữ 4h 62% · còn ~6 nến (1.5h)» từ timeline nến p (tầm k) — '' khi lõi chưa có xác suất còn giữ. */
  function timeText(M, p, k) {
    var g = p['nd_giu_' + k], r = p.nd_con_lai;
    if (!finite(g)) return '';
    return ' · giữ ' + k + ' ' + pct(g) + (finite(r) ? ' · còn ~' + num(r, 0) + ' nến' +
      (M.step ? ' (' + num(r * M.step / 3600, 1) + 'h)' : '') : '');
  }
  /** « · phá 4h 35%» cho range đang có (tầm dài nhất, cột timeline ở con trỏ). */
  function breakText(M) {
    var h = horizons(M)[0], b = h && (M.tl[M.cursor] || {})['nd_pha_' + h.k];
    return finite(b) ? ' · phá ' + h.k + ' ' + pct(b) : '';
  }

  function bandDrawing(M, logicalOf) {
    var out = { segments: [], boxes: [] }, c = M.cursor, la = logicalOf(c) + 0.5, far = null;
    horizons(M).forEach(function (h, j) {
      var b = bandAt(M, h.k);
      if (!b) return;
      var l2 = logicalOf(c + h.bars) + 0.45, id = 'nd:band:' + h.k, st = BAND_STYLE[Math.min(j, 1)];
      if (far === null) far = l2;
      out.boxes.push({ id: id, l1: la, l2: l2, p1: b.lo80, p2: b.hi80, fill: st.fill80, border: st.border, borderStyle: 'dashed',
        autoscale: false });
      out.boxes.push({ id: id, l1: la, l2: l2, p1: b.lo50, p2: b.hi50, fill: st.fill50, autoscale: false });
      out.segments.push({ id: id, noLine: true, l1: l2, l2: l2, p1: b.hi80, p2: b.hi80, color: COL_BAND, autoscale: false,
        label: { text: h.k + ' 80%', pos: 'right', priority: 6.8, size: 10, alpha: 0.85 } });
    });
    if (far === null) return out;                  // chưa có khoảng (khởi động) → cũng chưa có xác suất chạm
    levelsAt(M).forEach(function (m) {
      out.segments.push({ id: 'nd:muc:' + m.loai, l1: la, l2: far, p1: m.gia, p2: m.gia, color: LEVEL[m.loai].col, width: 1,
        style: 'dotted', alpha: 0.75, autoscale: false,
        label: { text: 'chạm ' + touchText(m), pos: 'right', priority: 6.9, size: 10, alpha: 0.9 } });
    });
    return out;
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
        ' (' + kh.n_mau + ' mẫu gần nhất) nhân ATR' : '') + ' — không nói giá sẽ đi lên hay xuống.',
      more: scoreText((nd.diem_that || {})[k]) }];
  }

  function levelTip(M, loai) {
    var m = levelsAt(M).filter(function (x) { return x.loai === loai; })[0], sc = ndAt(M).diem_that || {};
    if (!m) return null;
    var br = Object.keys(sc).map(function (k) {
      var r = (sc[k].cham || {})[loai];
      return r && r.n ? k + ' ' + brierText(r) : null;
    }).filter(Boolean);
    return [{ head: 'Xác suất chạm ' + LEVEL[loai].word + ' ' + V.fp(m.gia, M.digits) + ': ' + touchText(m),
      body: 'Tỷ lệ mẫu có biên ≥ khoảng cách hiện tại tới mức (' + sourceText(ndAt(M)) + ') — xác suất bị chạm, không phải ' +
        'xác suất giá dừng ở đó.',
      more: br.length ? 'Điểm thật tới nến này: ' + br.join(' · ') + '. Brier nhỏ hơn B0 = tốt hơn mẫu bỏ giờ NY.'
        : 'Điểm thật: chưa đủ kết cục để chấm.' }];
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

  /** id «nd:state:<nến>» (dải), «nd:range:<nến đầu đoạn>» (hộp range) → đoạn chứa nến đó (mới nhất trước);
   *  «nd:band:<tầm>» / «nd:muc:<loại mức>» → khoảng / mức kèm điểm thật. */
  function info(M, id) {
    if (!M || typeof id !== 'string' || id.indexOf('nd:') !== 0) return null;
    var parts = id.split(':');
    if (parts[1] === 'band') return bandTip(M, parts[2]);
    if (parts[1] === 'muc') return levelTip(M, parts[2]);
    var i = +parts[2], eps = episodes(M), ep = null;
    for (var j = eps.length - 1; j >= 0 && !ep; j--) if (eps[j].from <= i && i <= eps[j].to) ep = eps[j];
    if (!ep) return [{ head: 'Trạng thái: chưa đủ nến', body: 'Sau khoảng trống dài hoặc lúc khởi động, lõi chưa đủ nến để xét.' }];
    var ev = ep.ev, x = (ev && ev.details) || {}, live = ep.to === M.cursor;
    var rows = [{ head: 'Trạng thái: ' + STATE[ep.key].word + ' · #' + ep.from + ' → #' + ep.to + (live ? ' (đang có)' : ''),
      body: ev ? stateBody(x, ep.key, M.digits) + ' Đổi trạng thái khi ứng viên giữ đủ ' + x.giu_nen + ' nến (xác nhận ở #' +
        ev.confirmed_bar_index + ').' : REASON[ep.key] + '.',
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
      : 'Trạng thái: chưa đủ nến (sau khoảng trống / khởi động).' });
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
    (nd.muc || []).forEach(function (m) {
      if (!LEVEL[m.loai]) return;
      out.push({ kind: 'state', text: 'Xác suất chạm ' + LEVEL[m.loai].word + ' ' + V.fp(m.gia, d) + ' (cách ' + num(m.kc_atr, 1) +
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
      if (ct && ct.n) {                              // ô tiêu đề: gộp mọi loại mức (lõi tính), từng loại ở title
        rows.push({ k: 'Xác suất chạm ' + k + ' — Brier (B0)', v: brierPair(ct),
          title: 'Gộp mọi mức, ' + ct.n + ' lần. ' + Object.keys(ch).map(function (kind) {
            return (LEVEL[kind] ? LEVEL[kind].word : kind) + ': ' + brierText(ch[kind]);
          }).join(' · ') });
      }
    });
    var tg = st.thoi_gian || {}, b0 = tg.b0_vi || {};
    probRows(rows, 'Còn giữ', tg.con_giu, 'trạng thái đang hiện vẫn còn sau tầm', b0.con_giu);
    probRows(rows, 'Phá biên range', tg.pha_bien, 'close ra ngoài biên range trong tầm', b0.pha_bien);
    var ts = st.trang_thai || {}, tt = ts.ty_le_thoi_gian || {};
    rows.push({ k: 'Thời gian: trend ↑ / ↓ / range / nén / nhiễu',
      v: Object.keys(STATE).map(function (k) { return pct(tt[k]); }).join(' / '),
      title: 'Tỷ lệ nến theo trạng thái đang hiện (mô tả). Đổi trạng thái ' + (ts.so_lan_doi || 0) + ' lần.' });
    return rows;
  }

  MSL.ictNdView = {
    has: has, meta: meta, isType: function (t) { return !!BY_TYPE[t]; },
    bandBars: bandBars, episodes: episodes, drawing: drawing, bandDrawing: bandDrawing, statusAt: statusAt, info: info,
    eventText: eventText, pendingLines: pendingLines, statsRows: statsRows
  };
})(window.MSL);
