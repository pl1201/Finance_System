/* ict_structure 0.5.0 — order block + OTE: phần dựng hình THUẦN (MSL.ictObOteView). Không vẽ, không DOM, không gọi LWC →
 * chạy được trong node (tests/frontend/test_ict_ob_ote_display.py). Nạp SAU algos/ict_structure_view.js (dùng mô hình M của
 * MSL.ictView.buildModel — M.list, M.tl, M.ev — và các hàm finite / withDefaults / fvgDist / rgba / fp). Plugin
 * algos/ict_structure.js gọi các hàm này rồi đưa kết quả cho lớp vẽ chung chart/primitives.js.
 *
 * Chỉ ĐỌC sự kiện / timeline / pending_state lõi đã tính (core/components/order_block.py, ote.py) — không tính lại quy tắc:
 *   - OB: ORDER_BLOCK_* (vùng; biết ở nến xác nhận = nến giá vượt đầu xa) + kết cục đầu tiên OB_TAP_* / OB_FAIL_* /
 *     OB_EXPIRED (reference_event_id = OB);
 *   - OTE đang chờ: cột timeline ote_* TẠI con trỏ (vùng sẽ xét ở nến sau; null = nhịp chưa đủ lớn; ote_neo = nến SHIFT);
 *     OTE đã kết thúc: OTE_ENTRY_* / OTE_FAIL_* (x, h, vùng, độ sâu).
 * Nhân quả: mọi thứ từ M (sự kiện confirmed ≤ con trỏ, timeline ≤ con trỏ).
 *
 *   meta(type)                    {group: 'ob'|'ote', end: null|'tap'|'fail'|'expired'|'entry', mark} | null
 *   select(M, opts)               «Hiện tại»: OB còn mở (≤ obPerSide gần giá nhất mỗi chiều) + OB kết thúc trong `recent` nến
 *                                 (≤ endedPerSide mỗi chiều); nhịp OTE đang chờ + OTE vào / hỏng trong `recent` nến. Kết cục
 *                                 gần nhất (OB mỗi chiều, OTE) luôn giữ dù cũ hơn `recent` — như shift gần nhất của lớp Shift
 *   drawing(M, sel, logicalOf, o) {segments, boxes}; o.ob / o.ote bật lớp; o.ext, o.near (khoảng giá «gần»)
 *   info(M, id)                   tooltip [{head, body, more}] cho id «ob:…» / «ote:…»
 *   eventText(e, digits)          câu giải thích một sự kiện OB / OTE (chữ thuần) | null
 *   pendingLines(ps, digits)      [{kind, text}] «Đang theo dõi» từ pending_state.order_block / .ote
 */
(function (MSL) {
  'use strict';

  var V = MSL.ictView, finite = V.finite;
  var COL = { up: V.COL.up, down: V.COL.down, ote: '#d4af37' };
  var DEF = { ext: 5, recent: 60, obPerSide: 3, endedPerSide: 2, oteRecent: 2, near: null };
  /** Ưu tiên nhãn (cùng thang PRI của MSL.ictView): sau FVG của shift, trước FVG thô. */
  var PRI = { ote: 6.55, ob: 6.6, oteRoot: 7.05 };
  /** Mọi loại sự kiện OB / OTE: nhóm, kết cục (null = OB mới xác nhận), chữ marker khi chọn ở bảng. */
  var META = {
    ORDER_BLOCK_UP: { group: 'ob', end: null, mark: 'OB' }, ORDER_BLOCK_DOWN: { group: 'ob', end: null, mark: 'OB' },
    OB_TAP_UP: { group: 'ob', end: 'tap', mark: 'chạm OB' }, OB_TAP_DOWN: { group: 'ob', end: 'tap', mark: 'chạm OB' },
    OB_FAIL_UP: { group: 'ob', end: 'fail', mark: 'OB hỏng' }, OB_FAIL_DOWN: { group: 'ob', end: 'fail', mark: 'OB hỏng' },
    OB_EXPIRED: { group: 'ob', end: 'expired', mark: 'OB hết hạn' },
    OTE_ENTRY_UP: { group: 'ote', end: 'entry', mark: 'OTE' }, OTE_ENTRY_DOWN: { group: 'ote', end: 'entry', mark: 'OTE' },
    OTE_FAIL_UP: { group: 'ote', end: 'fail', mark: 'OTE hỏng' }, OTE_FAIL_DOWN: { group: 'ote', end: 'fail', mark: 'OTE hỏng' },
    OTE_EXPIRED: { group: 'ote', end: 'expired', mark: 'OTE hết hạn' }
  };
  var END_WORD = { tap: 'chạm', fail: 'hỏng', expired: 'hết hạn' };

  function opt(o) { return V.withDefaults(DEF, o); }
  function meta(t) { return META[t] || null; }
  function isType(t) { return !!META[t]; }
  function arrow(dir) { return dir === 'down' ? '↓' : '↑'; }
  function word(dir) { return dir === 'down' ? 'giảm' : 'tăng'; }
  var pct = V.pct;
  var rng = V.fpRange;

  /** Sự kiện OB / OTE của M (≤ con trỏ, theo thứ tự phát): OB, kết cục đầu tiên theo id OB, OTE đã kết thúc.
   *  Tính một lần cho mỗi M (M dựng lại mỗi lần đổi con trỏ). */
  function collect(M) {
    if (M.obOte) return M.obOte;
    var obs = [], ends = {}, otes = [];
    (M.list || []).forEach(function (e) {
      var m = META[e.structure_type];
      if (!m) return;
      if (m.group === 'ote') otes.push(e);
      else if (!m.end) obs.push(e);
      else if (e.reference_event_id && !ends[e.reference_event_id]) ends[e.reference_event_id] = e;
    });
    M.obOte = { obs: obs, ends: ends, otes: otes };
    return M.obOte;
  }

  /** Nhịp OTE đang chờ tại con trỏ (timeline); null khi không có nhịp chờ hoặc kết quả cũ (chưa có cột). */
  function pendingOte(M) {
    var p = M.tl[M.cursor];
    if (!p || !p.ote_dir) return null;
    var ps = (M.pending && M.pending.ote) || {};
    return { dir: p.ote_dir, anchor: finite(p.ote_neo) ? p.ote_neo : null, x: p.ote_x, h: p.ote_h, lo: p.ote_lo, hi: p.ote_hi,
      tu: finite(ps.tu) ? ps.tu : 0.62, den: finite(ps.den) ? ps.den : 0.79 };
  }

  function select(M, opts) {
    var o = opt(opts), c = M.cursor, C = collect(M);
    var close = finite(o.close) ? o.close : null;
    var open = { up: [], down: [] }, ended = { up: [], down: [] };
    C.obs.forEach(function (e) {
      var dir = e.direction === 'down' ? 'down' : 'up', end = C.ends[e.event_id] || null;
      (end ? ended : open)[dir].push({ ev: e, end: end, dir: dir });
    });
    function dist(it) { return close === null ? 0 : V.fvgDist(it.ev, close); }
    function recent(e) { return e.confirmed_bar_index >= c - o.recent; }
    var obs = [];
    ['up', 'down'].forEach(function (d) {   // cùng thứ tự với lõi (OrderBlockTracker.ranked): gần close, rồi OB mới hơn
      obs = obs.concat(open[d].sort(function (a, b) {
        return (dist(a) - dist(b)) || ((b.ev.details || {}).nen_neo - (a.ev.details || {}).nen_neo);
      }).slice(0, o.obPerSide));
      obs = obs.concat(ended[d].sort(function (a, b) {
        return b.end.confirmed_bar_index - a.end.confirmed_bar_index;
      }).filter(function (it, k) { return k === 0 || recent(it.end); }).slice(0, o.endedPerSide));
    });
    var done = C.otes.filter(function (e) { return META[e.structure_type].end !== 'expired'; });
    var otes = done.filter(function (e, k) { return k === done.length - 1 || recent(e); }).slice(-o.oteRecent);
    return { obs: obs, otePending: pendingOte(M), otes: otes };
  }

  function obDrawing(sel, logicalOf, o, lEnd, out) {
    sel.obs.forEach(function (it) {
      var e = it.ev, x = e.details || {}, up = it.dir === 'up', col = up ? COL.up : COL.down;
      if (!finite(x.lo) || !finite(x.hi)) return;
      var kind = it.end ? META[it.end.structure_type].end : null, faded = kind === 'fail' || kind === 'expired';
      var id = 'ob:' + e.event_id, mid = (x.lo + x.hi) / 2;
      var l1 = logicalOf(finite(x.nen_dau) ? x.nen_dau : e.event_bar_index) - 0.45;
      var l2 = it.end ? logicalOf(it.end.event_bar_index) + 0.45 : lEnd;
      out.boxes.push({ id: id, l1: l1, l2: l2, p1: x.lo, p2: x.hi, fill: V.rgba(col, faded ? 0.06 : 0.15),
        border: V.rgba(col, faded ? 0.45 : 0.85), borderWidth: 1.5,
        borderStyle: kind === 'tap' ? 'dashed' : (faded ? 'dotted' : 'solid'), autoscale: 'near', near: o.near });
      // mean threshold (chấm) + chữ trong hộp ngay sau nến xác nhận, trượt dọc khi bị chiếm
      out.segments.push({ id: id, l1: l1, l2: l2, p1: mid, p2: mid, color: col, width: 1, style: 'dotted',
        alpha: faded ? 0.35 : 0.6, autoscale: false,
        label: { text: 'OB ' + arrow(it.dir) + (kind ? ' · ' + END_WORD[kind] : ''), pos: 'start',
          at: logicalOf(e.confirmed_bar_index) + 0.6, priority: PRI.ob, size: 11, strict: true, alpha: faded ? 0.7 : 0.95 } });
    });
  }

  function oteDrawing(sel, logicalOf, o, lEnd, out) {
    var P = sel.otePending;
    if (P && finite(P.anchor)) {
      var la = logicalOf(P.anchor) - 0.45;
      if (finite(P.lo) && finite(P.hi)) {
        var m = (P.lo + P.hi) / 2;     // điểm ngọt = giữa vùng (mức hồi tuyến tính theo nhịp)
        out.boxes.push({ id: 'ote:pending', l1: la, l2: lEnd, p1: P.lo, p2: P.hi, fill: V.rgba(COL.ote, 0.14),
          border: V.rgba(COL.ote, 0.85), borderStyle: 'dashed', autoscale: 'near', near: o.near });
        out.segments.push({ id: 'ote:pending', l1: la, l2: lEnd, p1: m, p2: m, color: COL.ote, width: 1, style: 'dotted',
          alpha: 0.8, autoscale: false,
          label: { text: 'OTE ' + arrow(P.dir) + ' ' + Math.round(100 * P.tu) + '–' + Math.round(100 * P.den) + '%', pos: 'right',
            priority: PRI.ote, size: 11 } });
      }
      if (finite(P.x)) {
        out.segments.push({ id: 'ote:pending', l1: la, l2: lEnd, p1: P.x, p2: P.x, color: COL.ote, width: 1, style: 'dashed',
          alpha: 0.45, autoscale: 'near', near: o.near,
          label: { text: finite(P.lo) ? 'gốc nhịp' : 'gốc nhịp · chờ nhịp đủ lớn', pos: 'right', priority: PRI.oteRoot, size: 10,
            alpha: 0.75 } });
      }
    }
    sel.otes.forEach(function (e) {
      var x = e.details || {}, entry = META[e.structure_type].end === 'entry';
      if (!finite(x.vung_lo) || !finite(x.vung_hi) || !finite(x.nen_neo)) return;
      var id = 'ote:' + e.event_id, l1 = logicalOf(x.nen_neo) - 0.45, l2 = logicalOf(e.event_bar_index) + 0.45;
      var m = (x.vung_lo + x.vung_hi) / 2;
      out.boxes.push({ id: id, l1: l1, l2: l2, p1: x.vung_lo, p2: x.vung_hi, fill: V.rgba(COL.ote, entry ? 0.12 : 0.05),
        border: V.rgba(COL.ote, entry ? 0.7 : 0.4), borderStyle: entry ? 'solid' : 'dotted', autoscale: 'near', near: o.near });
      out.segments.push({ id: id, noLine: true, l1: l2, l2: l2, p1: m, p2: m, color: COL.ote, autoscale: false,
        label: { text: 'OTE ' + arrow(e.direction) + (entry ? ' · vào ' + pct(x.do_sau) : ' · hỏng'), pos: 'right',
          priority: PRI.ote, size: 10, alpha: entry ? 0.95 : 0.7 } });
    });
  }

  function drawing(M, sel, logicalOf, opts) {
    var o = opt(opts), lEnd = logicalOf(M.cursor + o.ext);
    var out = { segments: [], boxes: [] };
    if (o.ob) obDrawing(sel, logicalOf, o, lEnd, out);
    if (o.ote) oteDrawing(sel, logicalOf, o, lEnd, out);
    return out;
  }

  // ------------------------------------------------------------------ chữ

  function obHead(x, dir, d) { return 'Order block ' + word(dir) + ' ' + rng(x.lo, x.hi, d); }
  function anchorText(neo, bar) { return (neo === 'displacement' ? 'nến #' : 'SHIFT #') + bar; }
  function obBody(x, dir) {
    var src = x.bien_the === 'nen_cuoi_rau'
      ? 'nến ' + (dir === 'down' ? 'tăng' : 'giảm') + ' cuối #' + x.nen_cuoi + ' (cả râu)'
      : 'chuỗi ' + x.so_nen + ' nến ' + (dir === 'down' ? 'tăng' : 'giảm') + ' #' + x.nen_dau + '–#' + x.nen_cuoi + ' (chỉ thân)';
    return src + ' trước displacement của ' + anchorText(x.neo, x.nen_neo) +
      '; xác nhận ở nến #' + x.nen_xac_nhan + ' khi giá vượt ' + (dir === 'down' ? 'mép dưới' : 'mép trên') + '.';
  }
  function obEndText(end) {
    var k = META[end.structure_type].end, x = end.details || {};
    if (k === 'tap') return 'Chạm lần đầu ở nến #' + end.event_bar_index + ' (' + x.so_nen_tu_tao + ' nến sau mốc).';
    if (k === 'fail') return 'Hỏng ở nến #' + end.event_bar_index + ': lần chạm đầu có close vượt mép xa.';
    return 'Hết hạn ở nến #' + end.event_bar_index + (end.reason_code === 'OB_EXPIRED_OPPOSITE_SHIFT'
      ? ' — có SHIFT ngược chiều trước khi được chạm.' : ' — quá hạn chưa được chạm.');
  }

  function info(M, id) {
    if (!M || typeof id !== 'string') return null;
    var d = M.digits;
    if (id.indexOf('ob:') === 0) {
      var e = M.ev[id.slice(3)];
      if (!e) return null;
      var x = e.details || {}, end = collect(M).ends[e.event_id];
      return [{ head: obHead(x, e.direction, d), body: obBody(x, e.direction) + ' ' +
        (end ? obEndText(end) : 'Còn mở — chờ chạm (hết hạn ở nến #' + x.han_nen + ').'),
        more: 'Mean threshold ' + V.fp(x.mean_threshold, d) + '. Chỉ tính lần chạm đầu; close vượt mép xa = hỏng. Mô tả, chưa phải tín hiệu.' }];
    }
    if (id === 'ote:pending') {
      var P = pendingOte(M);
      if (!P) return null;
      var L = Math.abs(P.h - P.x), near = P.h - P.tu * (P.h - P.x);
      return [{ head: 'OTE ' + word(P.dir) + ' đang chờ' + (finite(P.lo) ? ' ' + rng(P.lo, P.hi, d) : ''),
        body: 'Nhịp từ gốc ' + V.fp(P.x, d) + ' (cực trị cú quét của SHIFT #' + P.anchor + ') tới ' + V.fp(P.h, d) + ', dài ' +
          V.fp(L, d) + '. ' + (finite(P.lo)
            ? 'Vào khi giá ' + (P.dir === 'down' ? 'lên tới ' : 'hồi về ') + V.fp(near, d) + '; hỏng khi ' +
              (P.dir === 'down' ? 'vượt ' : 'thủng ') + V.fp(P.x, d) + '.'
            : 'Nhịp chưa đủ lớn so với ATR — chưa có vùng.'),
        more: 'Đầu nhịp lấy tới nến trước (nhân quả); SHIFT mới thay nhịp. Mô tả, chưa phải tín hiệu.' }];
    }
    if (id.indexOf('ote:') === 0) {
      var t = M.ev[id.slice(4)];
      if (!t) return null;
      var tx = t.details || {};
      return [{ head: 'OTE ' + word(t.direction) + ' ' + rng(tx.vung_lo, tx.vung_hi, d), body: eventText(t, d) || '' }];
    }
    return null;
  }

  /** Câu giải thích một sự kiện OB / OTE (chữ thuần, chưa thoát HTML); khác loại → null. */
  function eventText(e, d) {
    var m = e && META[e.structure_type], x = (e && e.details) || {};
    if (!m) return null;
    if (m.group === 'ob') {
      return m.end ? 'OB ' + word(x.chieu_ob) + ' ' + rng(x.lo, x.hi, d) + ': ' + obEndText(e)
        : obHead(x, e.direction, d) + ': ' + obBody(x, e.direction);
    }
    var zone = rng(x.vung_lo, x.vung_hi, d);
    if (m.end === 'entry') {
      return 'Giá vào vùng OTE ' + word(e.direction) + ' ' + zone + ', độ sâu hồi ' + pct(x.do_sau) + ' của nhịp ' +
        V.fp(x.x, d) + ' → ' + V.fp(x.h, d) + ' (' + (finite(x.nhip_atr) ? x.nhip_atr.toFixed(1) : '—') + ' ATR) sau SHIFT #' +
        x.nen_neo + (x.ob ? '; OB cùng shift ' + (x.ob_giao_vung ? 'giao' : 'không giao') + ' vùng OTE' : '') + '.';
    }
    if (m.end === 'fail') return 'Nhịp OTE ' + word(e.direction) + ' hỏng: giá ' + (e.direction === 'down' ? 'vượt' : 'thủng') +
      ' gốc nhịp ' + V.fp(x.x, d) + ' trước khi vào vùng ' + zone + '.';
    return 'Nhịp OTE ' + word(e.direction) + ' (SHIFT #' + x.nen_neo + ') hết hạn: ' + (x.ket_cuc_vi || '') + '.';
  }

  /** «Đang theo dõi» từ pending_state (lõi 0.5.0): OB còn mở gần giá nhất, nhịp OTE đang chờ. Kết quả cũ → []. */
  function pendingLines(ps, d) {
    var out = [], ob = ps && ps.order_block, ote = ps && ps.ote;
    ((ob && ob.dang_mo) || []).forEach(function (r) {
      out.push({ kind: 'state', text: 'OB ' + word(r.chieu) + ' ' + rng(r.lo, r.hi, d) + ' (' + anchorText(ob.neo, r.nen_neo) +
        ', còn ' + r.con_lai_nen + ' nến): cần ' + r.can + '.' });
    });
    var p = ote && ote.dang_cho;
    if (p) {
      out.push({ kind: 'state', text: 'Nhịp OTE ' + word(p.chieu) + ' ' + V.fp(p.x, d) + ' → ' + V.fp(p.h, d) +
        (p.vung_hieu_luc ? ', vùng ' + rng(p.vung_lo, p.vung_hi, d) : '') + ' (còn ' + p.con_lai_nen + ' nến): ' + p.can + '.' });
    }
    return out;
  }

  MSL.ictObOteView = {
    COL: COL, DEFAULTS: DEF, PRIORITY: PRI, meta: meta, isType: isType,
    collect: collect, select: select, drawing: drawing, info: info, eventText: eventText, pendingLines: pendingLines
  };
})(window.MSL);
