/* ict_structure — phần dựng hình THUẦN của chế độ Gọn (MSL.ictView). Không vẽ, không DOM, không gọi LWC → chạy được
 * trong node (tests/frontend/test_ict_display.py). Plugin algos/ict_structure.js gọi các hàm này rồi đưa kết quả
 * cho lớp vẽ chung chart/primitives.js. Không đăng ký plugin.
 *
 * Chỉ ĐỌC sự kiện, timeline, pending_state lõi đã tính — không tính lại quy tắc nào:
 *   - vùng thanh khoản: tạo / gộp EQ từ details.vung_thanh_khoan của ITH/ITL (nến gốc = event_bar_index, biết =
 *     confirmed_bar_index, mức đổi khi gộp); kết cục từ details.pools của LIQ_* (nến lấy nen_lay, kết cục ở
 *     confirmed_bar_index, cực trị cuc_tri_cu_quet); đang chờ từ pending_state.thanh_khoan.dang_cho_sweep_run;
 *   - shift + FVG từ SHIFT_*, SHIFT_FVG_*, FVG_FILLED; order flow từ timeline + ORDER_FLOW_*;
 *   - lõi 0.10.0: MSS_* / MSS_FVG_* thay shift (cùng danh sách M.shifts / M.shiftFvg — sự kiện đổi hướng); M.flip = 'MSS' khi
 *     timeline có cột pending_mss, không thì 'shift' (chữ «Đổi khi: …», DOL, tooltip order flow theo đó).
 *   - Chi tiết: FVG + vòng đời từ FVG_UP/DOWN, FVG_TOUCHED, FVG_FILLED; ITH/ITL/STH/STL + nhãn HH… từ SWING_* (details.nhan);
 *     displacement từ DISPLACEMENT_*; mức được bảo vệ (protected, protected_side, protected_id, protected_broken) và
 *     dealing range (dealing_hi/lo/eq/id) đọc từ timeline TẠI con trỏ.
 * Nhân quả: mọi thứ lọc theo confirmed_bar_index ≤ con trỏ; trạng thái ở nến h ≤ con trỏ dựng lại từ các mốc đó.
 *
 *   buildModel(events, timeline, pendingState, cursor, digits) → model | null (không phải timeline ICT); giá trong chữ
 *                                lấy displayDigits(digits, ATR con trỏ) chữ số (XAU: 2040.02, EURUSD: 1.08234)
 *   poolAt(pool, h)              trạng thái một vùng ở nến h: intact | pending | sweep | run | unresolved (null: chưa biết)
 *   nearestIntact(model, h)      {BSL: [...], SSL: [...]} vùng còn nguyên, gần nhất trước (đúng thứ tự heap của lõi)
 *   selectCurrent(model, opts)   chế độ «Hiện tại» tại con trỏ (2 vùng còn nguyên gần nhất mỗi phía, ≤ 3 nhóm vùng đã
 *                                kết cục gần con trỏ nhất mỗi phía trong 60 nến, vùng của shift đang hiện, vùng đang chờ);
 *                                opts.history = «Lịch sử» (mọi vùng / shift / FVG tới con
 *                                trỏ); opts.allIntact = mọi vùng còn nguyên; opts.close = close ở con trỏ (FVG gần giá nhất)
 *   structureAt(model)           mức được bảo vệ + dealing range tại con trỏ (đọc timeline)
 *   groupPools(states, atr, opts)  gộp vùng trùng (cùng phía, kết cục, nến lấy, cách ≤ 0.5 ATR)
 *   buildDrawing(model, sel, logicalOf, opts)  → {segments, boxes, counts} cho MSL.primitives; opts.detail =
 *                                {protected, range, fvg, ith, sth, labels, disp} (lớp Chi tiết), opts.barOf(i) → nến
 *                                (cho displacement); Lịch sử: đối tượng mờ dần theo tuổi (ageBars)
 *   bandBars(model, logicalOf)   dải order flow có chữ
 *   statusAt(model, h, close)    dòng trạng thái 2 hàng ở nến h
 *   objectInfo(model, id, opts)  tooltip khi rê vào đối tượng (id do buildDrawing / bandBars đặt); opts.prot = lớp
 *                                «Mức được bảo vệ» đang hiện (vùng trùng mức được bảo vệ → ghi cả hai)
 *
 * Khung lớn (lõi 0.4.0 — giai đoạn 3; đặc tả §4.13–§4.19, §11):
 *   - vùng theo TẦNG: tier của vùng = details.vung_thanh_khoan.tang (M15 = khung chạy, kể cả dataset M5 — quy ước lõi; H1,
 *     H4; D = PDH/PDL; W = PWH/PWL). poolName: «BSL» / «BSL H1» / «EQH H4» / «PDH» / «PWL»; nét đậm dần theo tầng (TIER);
 *     tooltip ghi tầng, nguồn (nến H4 nào / kỳ ngày nào), lúc biết (known_at);
 *   - lớp phủ khung lớn (opts.htf = {swing, range, fvg, levels, forming, h1}): ITH/ITL H4 (H1 khi h1) từ HTF_SWING_*;
 *     dealing range H4 + EQ đọc timeline htf_H4_dealing_hi/lo TẠI con trỏ (mốc = ITH/ITL H4 gần nhất); FVG H4 (H1) từ
 *     HTF_FVG_* — mở tới PD_* đầu tiên có details.fvg = id FVG; PDH/PDL/PWH/PWL hiện hành từ HTF_PERIOD_*; nến H4 đang
 *     hình thành (formingAt) gộp từ nến khung chạy ≤ con trỏ theo mốc ny_1700 (giờ New York) — chỉ để vẽ;
 *   - dòng trạng thái (htfStatusAt) đọc cột timeline htf_*, pd_bias*, dol_* ở nến h; khung «Thuật toán đang làm gì»
 *     (htfExplain) đọc pending_state.khung_lon / pd / dol. KHÔNG đọc details.htf (lõi có thể bỏ nó ở sự kiện phụ).
 *   selectHtf(model, opts)       đối tượng khung lớn «Hiện tại» / «Lịch sử» (dùng trong selectCurrent khi opts.htf)
 *   formingAt(model, h, barOf)   nến H4 đang hình thành ở nến h (chỉ nến ≤ h) | null
 *   htfStatusAt(model, h)        {text, title} ngữ cảnh khung lớn gọn cho dòng trạng thái | null (kết quả cũ)
 *   htfExplain(pendingState, digits)  [{kind, text}] — mỗi thành phần khung lớn một dòng (chữ thuần, chưa thoát HTML)
 *   htfEventText(event, digits)  câu giải thích một sự kiện HTF_* / PD_* / DOL_REACHED (chữ thuần) | null
 */
(function (MSL) {
  'use strict';

  var COL = { bsl: '#f0a03c', ssl: '#4dd0e1', grey: '#90a4ae', up: '#26a69a', down: '#ef5350' };
  /** Màu dải order flow theo trạng thái (luôn kèm chữ trên dải / dòng trạng thái). */
  var OF_COLORS = {
    '1': 'rgba(67,160,71,.85)',
    '-1': 'rgba(229,57,53,.85)',
    '0': 'rgba(120,144,156,.55)',
    'null': 'rgba(55,71,79,.35)'
  };
  var OF_TEXT = {
    run_tang: '↑ run BSL', shift_tang: '↑ shift', run_giam: '↓ run SSL', shift_giam: '↓ shift',
    run_nguoc_chieu: '? run ngược', hai_chieu_cung_nen: '? 2 chiều',
    mss_tang: '↑ MSS', mss_giam: '↓ MSS', ob_hong: '? OB hỏng'
  };
  var OF_WORD = { '1': 'TĂNG', '-1': 'GIẢM', '0': 'CHƯA RÕ', 'null': 'CHƯA CÓ' };
  var OF_REASON = {
    run_tang: 'run lên', run_giam: 'run xuống', shift_tang: 'shift tăng', shift_giam: 'shift giảm',
    run_nguoc_chieu: 'run phía ngược chiều', hai_chieu_cung_nen: 'run/shift hai chiều cùng nến',
    mss_tang: 'MSS tăng', mss_giam: 'MSS giảm', ob_hong: 'order block giữ order flow bị hỏng'
  };
  /** Sự kiện đổi hướng (shift ≤ 0.9.x, MSS ≥ 0.10.0). */
  function isFlip(t) { return t === 'SHIFT_UP' || t === 'SHIFT_DOWN' || t === 'MSS_UP' || t === 'MSS_DOWN'; }
  function isMss(e) { return /^MSS_/.test(e.structure_type); }
  /** Sự kiện đổi hướng của lần chạy, đọc từ khoá lõi ghi: pending_state / details DOL có «mss» (0.10.0) hay «shift». */
  function flipOf(o) { return hasOwn(o, 'mss') ? { key: 'mss', name: 'MSS' } : { key: 'shift', name: 'shift' }; }
  var GAP_VI = {
    nghi_phien: 'nghỉ hằng ngày', cuoi_tuan: 'cuối tuần', nghi_le: 'nghỉ lễ',
    thieu_trong_phien: 'THIẾU DỮ LIỆU trong phiên', ngoai_lich: 'ngoài phạm vi lịch',
    khong_ro_lich: 'chưa chọn lịch', lech_buoc: 'lệch bước khung'
  };
  var DEF = { ext: 5, recent: 60, nearest: 2, outcomePerSide: 3, groupAtr: 0.5, farAtr: 3, fvgPerSide: 3, fvgRecent: 200,
    fvgFarAtr: 5, protExt: 20, ageBars: 300, minFade: 0.3,
    // khung lớn: ITH/ITL gần nhất mỗi (khung, phía); FVG khung lớn còn mở cách close ≤ htfFvgFarAtr × ATR khung chạy, tối đa
    // htfFvgPerSide mỗi (khung, chiều)
    htfSwingsPerSide: 4, htfFvgPerSide: 2, htfFvgFarAtr: 10 };
  /** Ưu tiên nhãn (nhỏ = đặt trước, thắng chỗ): shift gần nhất > «bị lấy · chờ» > BSL/SSL còn nguyên gần nhất > Protected >
   * PDH/PDL… (lớp khung lớn) > sweep/run gần con trỏ nhất (theo thứ tự gần → xa) > shift cũ > vùng còn nguyên khác > nến H4 đang
   * hình thành > FVG / range > HH… */
  var PRI = { shiftLast: 1, pending: 2, intact: 3, prot: 3.5, htfLevel: 3.6, outcome: 4, shift: 5, intactFar: 6, forming: 6.2,
    fvgShift: 6.5, htfFvg: 6.8, fvg: 7, range: 7, htfRange: 7.2, htfLevelOld: 7.4, htfSwing: 7.8, swing: 8 };
  var DCOL = { ith: '#ffd54f', itl: '#4fc3f7', sth: 'rgba(176,190,197,.85)', prot: '#ce93d8', broken: '#ef5350', range: '#b0bec5' };
  /** Màu lớp phủ khung lớn (ITH/ITL, dealing range, nến đang hình thành) — khác mọi màu của khung chạy; FVG khung lớn vẫn
   * xanh/đỏ theo chiều (màu chỉ một nghĩa), phân biệt bằng viền dày + chữ «FVG H4». */
  var HCOL = { H4: '#b388ff', H1: '#9fa8da' };
  /** Tầng vùng thanh khoản (lõi `tang`): thứ hạng như TIER_RANK của lõi, bề dày nét. «M15» = khung chạy (lõi ghi M15 kể cả
   * dataset M5 — đặc tả §6), không có chữ tầng. D / W đổi tên phía: PDH/PDL, PWH/PWL. */
  var TIER = { M15: { rank: 0, w: 1.5 }, H1: { rank: 1, w: 1.9 }, H4: { rank: 2, w: 2.3 }, D: { rank: 3, w: 2.3 },
    W: { rank: 4, w: 2.7 } };
  var PERIOD_NAME = { D: { BSL: 'PDH', SSL: 'PDL' }, W: { BSL: 'PWH', SSL: 'PWL' } };
  var TIER_VI = { H1: 'tầng H1 (ITH/ITL H1)', H4: 'tầng H4 (ITH/ITL H4)', D: 'mức ngày (D)', W: 'mức tuần (W)' };
  var LIQ_KIND = {
    LIQ_SWEEP_BSL: 'sweep', LIQ_SWEEP_SSL: 'sweep', LIQ_RUN_UP: 'run', LIQ_RUN_DOWN: 'run', LIQ_UNRESOLVED: 'unresolved'
  };
  var SWING_KIND = {
    SWING_HIGH_L2: 'ITH', SWING_LOW_L2: 'ITL', SWING_HIGH_L3: 'LTH', SWING_LOW_L3: 'LTL',
    SWING_HIGH: 'STH', SWING_LOW: 'STL'
  };
  var OUTCOME = { sweep: 1, run: 1, unresolved: 1 };
  var PD_TYPES = { PD_RESPECT_UP: 1, PD_RESPECT_DOWN: 1, PD_DISRESPECT_UP: 1, PD_DISRESPECT_DOWN: 1 };
  var ARROW = { '1': '↑', '-1': '↓', '0': '↕', 'null': '–' };
  var DIR_WORD = { '1': 'tăng', '-1': 'giảm', '0': 'lẫn lộn', 'null': 'chưa có' };

  function hasOwn(o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); }
  /** «[lo – hi]» với giá làm tròn như fp (dùng chung cho các view phụ). */
  function fpRange(lo, hi, d) { return '[' + fp(lo, d) + ' – ' + fp(hi, d) + ']'; }
  /** Tỷ lệ → «42%» / «41.7%» (không hữu hạn → «—»). */
  function pct(x) { return finite(x) ? Math.round(100 * x) + '%' : '—'; }
  function pct1(x) { return finite(x) ? (100 * x).toFixed(1) + '%' : '—'; }
  function finite(x) { return typeof x === 'number' && isFinite(x); }
  function ofKey(v) { return v === 1 || v === -1 || v === 0 ? String(v) : 'null'; }
  /** Bản sao `def` ghi đè bởi các khoá khác undefined của `o`. */
  function withDefaults(def, o) {
    var out = {}, k;
    for (k in def) out[k] = def[k];
    for (k in (o || {})) if (o[k] !== undefined) out[k] = o[k];
    return out;
  }
  function opt(o) { return withDefaults(DEF, o); }
  function rgba(hex, a) {
    var n = parseInt(String(hex).slice(1), 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }
  /** Giá làm tròn nửa lên (2040.015 → 2040.02 như mô tả trong tài liệu, tránh lỗi nhị phân của toFixed). */
  function fp(x, d) {
    if (!finite(x)) return '—';
    var dg = d === undefined || d === null ? 2 : d;
    return (x + (x >= 0 ? 1 : -1) * Math.pow(10, -dg - 3)).toFixed(dg);
  }
  /** Số chữ số thập phân cho chữ trên chart / dòng trạng thái / tooltip đối tượng: đủ phân biệt 1/50 ATR, tối thiểu 2
   * (hoặc `digits` nếu ít hơn), tối đa `digits` của dữ liệu — XAU M5/M15: 2 (2040.02), EURUSD: 5. */
  function displayDigits(digits, atr) {
    var dmax = digits === undefined || digits === null ? 2 : digits;
    if (!finite(atr) || atr <= 0) return dmax;
    var d = Math.ceil(-Math.log10(atr / 50) - 1e-9);
    return Math.min(dmax, Math.max(Math.min(2, dmax), d));
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  /** «09/01 14:05» (UTC — như trục thời gian của lab). */
  function fmtShort(sec) {
    if (!finite(sec)) return '';
    var d = new Date(sec * 1000);
    return pad(d.getUTCDate()) + '/' + pad(d.getUTCMonth() + 1) + ' ' + pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes());
  }
  function fmtHM(sec) { return fmtShort(sec).slice(6); }
  /** ISO của lõi («2024-01-09T13:00:00+00:00») → giây UTC; sai → null. */
  function isoSec(s) { var t = s ? Date.parse(s) : NaN; return isFinite(t) ? t / 1000 : null; }
  function fmtIsoShort(s) { var t = isoSec(s); return t === null ? '' : fmtShort(t); }
  /** «ict:SWING_HIGH_L2@1561>1564» → {type, bar, conf, sfx}; khác mẫu → null. sfx = hậu tố khung («H4», «D», «H1.1234»). */
  function parseId(id) {
    var m = /^ict:([A-Z0-9_]+)@(\d+)(?:>(\d+))?(?::([A-Za-z0-9.]+))?/.exec(String(id || ''));
    return m ? { type: m[1], bar: Number(m[2]), conf: m[3] ? Number(m[3]) : Number(m[2]), sfx: m[4] || null } : null;
  }
  function seqOf(id) { var n = parseInt(String(id).slice(1), 10); return isFinite(n) ? n : 0; }
  /** Vùng của khung chạy (lõi ghi «M15» cho mọi dataset — đặc tả §6) hay vùng cũ chưa có tầng. */
  function runTier(t) { return !t || t === 'M15'; }
  function tierRank(t) { return (TIER[t] || TIER.M15).rank; }
  function tierWidth(t) { return (TIER[t] || TIER.M15).w; }
  /** Khung lớn của ITH/ITL / FVG (details.khung, dự phòng hậu tố id). */
  function frameOf(e) {
    var x = (e && e.details) || {};
    if (x.khung) return x.khung;
    var p = parseId(e && e.event_id);
    return p && p.sfx ? p.sfx.split('.')[0] : null;
  }
  /** Bước nến khung chạy (giây) = khoảng cách nhỏ nhất giữa hai nến liền nhau của timeline; tên khung nếu chuẩn. */
  function stepOf(list) {
    var best = null;
    for (var i = 1; i < Math.min(list.length, 400); i++) {
      var dt = list[i].time - list[i - 1].time;
      if (finite(dt) && dt > 0 && (best === null || dt < best)) best = dt;
    }
    return best;
  }
  var TF_NAME = { 60: 'M1', 300: 'M5', 900: 'M15', 1800: 'M30', 3600: 'H1', 14400: 'H4' };

  // ------------------------------------------------------------------ giờ New York (mốc ny_1700 của nến H4 đang hình thành)
  var nyFmt = null, nyCache = {};
  /** Độ lệch giờ New York so với UTC (giây, âm) tại thời điểm `sec` — theo Intl (có đổi giờ mùa hè); null nếu không có Intl. */
  function nyOffset(sec) {
    var key = Math.floor(sec / 3600);
    if (hasOwn(nyCache, key)) return nyCache[key];
    var off = null;
    try {
      if (!nyFmt) {
        nyFmt = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hourCycle: 'h23', year: 'numeric', month: '2-digit',
          day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
      }
      var parts = {};
      nyFmt.formatToParts(new Date(key * 3600 * 1000)).forEach(function (q) { parts[q.type] = q.value; });
      var loc = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour % 24, +parts.minute, +parts.second) / 1000;
      off = loc - key * 3600;
    } catch (err) { off = null; }
    nyCache[key] = off;
    return off;
  }
  /** Ô H4 mốc ny_1700 (17, 21, 01, 05, 09, 13 giờ New York) chứa nến mở lúc `sec`: {id, end (giây UTC)}; null nếu không có Intl. */
  function h4Bucket(sec) {
    var off = nyOffset(sec);
    if (off === null) return null;
    var id = Math.floor((sec + off - 17 * 3600) / 14400);
    var endLocal = (id + 1) * 14400 + 17 * 3600;
    var offEnd = nyOffset(endLocal - off);
    return { id: id, end: endLocal - (offEnd === null ? off : offEnd) };
  }

  // ------------------------------------------------------------------ mô hình

  function newPool(id, side, tier) {
    return {
      id: id, seq: seqOf(id), side: side, tier: tier || null, origin: null, known: null, sources: [], levels: [],
      taken: null, outcome: null, resolved: null, extreme: null, sweepBars: null, pen: null, atrLocked: null,
      touches: null, gapKind: null, eventId: null, pendingLeft: null, stub: false
    };
  }

  /** Vùng chỉ thấy trong LIQ_* / pending_state (thiếu sự kiện ITH/ITL — kết quả cắt khúc): dựng từ bản tóm tắt. */
  function stubPool(M, q) {
    var p = newPool(q.id, q.phia, q.tang);
    p.stub = true;
    (q.nguon || []).forEach(function (sid) {
      var s = parseId(sid);
      if (!s) return;
      p.sources.push({ id: sid, kind: srcKind(s.type, null, s.sfx), type: s.type, ev: null, bar: s.bar, known: s.conf, price: null,
        time: null });
      if (p.origin === null) p.origin = s.bar;
    });
    p.known = finite(q.biet_tai_nen) ? q.biet_tai_nen : (p.sources.length ? p.sources[0].known : q.nen_lay);
    if (p.origin === null) p.origin = p.known;
    p.levels.push({ from: p.known, level: q.muc });
    M.pools[q.id] = p;
    return p;
  }

  /** Tên nguồn của vùng: «ITH» (khung chạy), «ITH H4», «PDH»… — từ loại sự kiện (+ details / hậu tố khung). */
  function srcKind(type, x, sfx) {
    var d = x || {}, f = d.khung || (sfx ? String(sfx).split('.')[0] : '');
    if (/^HTF_SWING_/.test(type)) return (d.ten || (/HIGH$/.test(type) ? 'ITH' : 'ITL')) + (f ? ' ' + f : '');
    if (/^HTF_PERIOD_/.test(type)) return d.ten || ((PERIOD_NAME[f] || {})[/HIGH$/.test(type) ? 'BSL' : 'SSL']) || type;
    return SWING_KIND[type] || type;
  }

  function buildModel(events, timeline, pendingState, cursor, digits) {
    var tl = timeline || [];
    if (!tl.length || !hasOwn(tl[tl.length - 1], 'dealing_hi')) return null;
    var last = tl[tl.length - 1].bar_index;
    var c = finite(cursor) ? Math.min(cursor, last) : last;
    var M = {
      cursor: c, digits: digits === undefined ? 2 : digits, tl: {}, tlList: [], ev: {}, pools: {}, shifts: [],
      shiftFvg: {}, fvgFilled: {}, fvgTouched: {}, fvgs: [], swings: [], disps: [], ofAt: {}, W: null, hasOrderFlow: false,
      // khung lớn (0.4.0): ITH/ITL H1/H4, FVG H1/H4 + PD_* kết thúc nó, PDH/PDL/PWH/PWL, PD_*, DOL_REACHED, nến degraded
      htfSwings: [], htfFvgs: [], htfFvgEnd: {}, periods: [], pds: [], dols: [], htfBad: [], hasHtf: false,
      // mọi sự kiện ≤ con trỏ theo thứ tự phát — view phụ (algos/ict_ob_ote_view.js) tự lọc loại của mình
      list: [],
      pending: pendingState || null, step: null, runTf: null
    };
    tl.forEach(function (p) {
      if (p.bar_index > c) return;
      M.tl[p.bar_index] = p;
      M.tlList.push(p);
    });
    var lastPt = M.tl[c] || M.tlList[M.tlList.length - 1];
    M.hasOrderFlow = hasOwn(lastPt, 'order_flow');
    M.hasHtf = hasOwn(lastPt, 'htf_H4_order');
    M.step = stepOf(M.tlList);
    M.flip = hasOwn(lastPt, 'pending_mss') ? 'MSS' : 'shift';      // lõi 0.10.0: sự kiện đổi hướng của lần chạy
    M.runTf = TF_NAME[M.step] || null;
    M.digits = displayDigits(M.digits, atrAt(M, c));
    (events || []).forEach(function (e) {
      if (!e || !(e.confirmed_bar_index <= c)) return;   // nhân quả: chỉ sự kiện đã xác nhận tới con trỏ
      M.ev[e.event_id] = e;
      M.list.push(e);
      var t = e.structure_type, x = e.details || {};
      if (SWING_KIND[t]) M.swings.push(e);
      else if (t === 'HTF_SWING_HIGH' || t === 'HTF_SWING_LOW') M.htfSwings.push(e);
      else if (t === 'HTF_PERIOD_HIGH' || t === 'HTF_PERIOD_LOW') M.periods.push(e);
      var v = x.vung_thanh_khoan;
      if (v && v.vung) {
        var p = M.pools[v.vung];
        if (!p) {
          p = newPool(v.vung, v.phia, v.tang);
          p.origin = e.event_bar_index;
          p.known = e.confirmed_bar_index;
          M.pools[v.vung] = p;
        }
        p.sources.push({
          id: e.event_id, kind: srcKind(t, x), type: t, ev: e, bar: e.event_bar_index, known: e.confirmed_bar_index,
          price: e.price, status: v.trang_thai
        });
        p.levels.push({ from: e.confirmed_bar_index, level: finite(v.muc_vung) ? v.muc_vung : e.price });
        return;
      }
      if (t === 'HTF_FVG_UP' || t === 'HTF_FVG_DOWN') { M.htfFvgs.push(e); return; }
      if (PD_TYPES[t]) {
        M.pds.push(e);
        var fz = x.fvg || e.reference_event_id;   // một kết quả mỗi vùng → PD_* đầu tiên kết thúc FVG
        if (fz && !M.htfFvgEnd[fz]) M.htfFvgEnd[fz] = e;
        return;
      }
      if (t === 'DOL_REACHED') { M.dols.push(e); return; }
      if (t === 'HTF_BAR_DEGRADED') { M.htfBad.push(e); return; }
      var kind = LIQ_KIND[t];
      if (kind) {
        var list = x.pools && x.pools.length ? x.pools : (x.vung ? [{
          id: x.vung, phia: x.phia, muc: x.muc, tang: x.tang, nen_lay: x.nen_lay, cuc_tri_cu_quet: x.cuc_tri_cu_quet,
          atr_khoa: x.atr_khoa, xuyen_atr: x.xuyen_atr, sweep_bars: x.sweep_bars, nguon: e.reference_event_id ? [e.reference_event_id] : []
        }] : []);
        list.forEach(function (q) {
          if (!q || !q.id) return;
          var pl = M.pools[q.id] || stubPool(M, q);
          pl.taken = finite(q.nen_lay) ? q.nen_lay : x.nen_lay;
          pl.outcome = kind;
          pl.resolved = e.confirmed_bar_index;
          pl.extreme = finite(q.cuc_tri_cu_quet) ? q.cuc_tri_cu_quet : x.cuc_tri_cu_quet;
          pl.sweepBars = finite(q.sweep_bars) ? q.sweep_bars : (kind === 'sweep' && finite(pl.taken) ? e.confirmed_bar_index - pl.taken : null);
          pl.pen = finite(q.xuyen_atr) ? q.xuyen_atr : null;
          pl.atrLocked = finite(q.atr_khoa) ? q.atr_khoa : null;
          pl.touches = finite(q.so_lan_cham) ? q.so_lan_cham : null;
          pl.gapKind = x.loai_khoang_trong || null;
          pl.eventId = e.event_id;
          if (!pl.levels.length && finite(q.muc)) pl.levels.push({ from: pl.known, level: q.muc });
        });
        if (M.W === null && finite(x.cua_so)) M.W = x.cua_so;
        return;
      }
      if (isFlip(t)) { M.shifts.push(e); return; }
      if (t === 'SHIFT_FVG_UP' || t === 'SHIFT_FVG_DOWN') { if (x.shift) M.shiftFvg[x.shift] = e; return; }
      if (t === 'MSS_FVG_UP' || t === 'MSS_FVG_DOWN') { if (x.mss) M.shiftFvg[x.mss] = e; return; }
      if (t === 'FVG_FILLED') { var f = e.reference_event_id || x.fvg; if (f && !M.fvgFilled[f]) M.fvgFilled[f] = e; return; }
      if (t === 'FVG_TOUCHED') { var ft = e.reference_event_id || x.fvg; if (ft && !M.fvgTouched[ft]) M.fvgTouched[ft] = e; return; }
      if (t === 'FVG_UP' || t === 'FVG_DOWN') { M.fvgs.push(e); return; }
      if (t === 'DISPLACEMENT_UP' || t === 'DISPLACEMENT_DOWN') { M.disps.push(e); return; }
      if (t === 'ORDER_FLOW_UP' || t === 'ORDER_FLOW_DOWN' || t === 'ORDER_FLOW_UNCLEAR') M.ofAt[e.confirmed_bar_index] = e;
    });
    // Đang chờ sweep/run tại con trỏ: chỉ pending_state biết (chưa có sự kiện nào).
    var pend = ((pendingState || {}).thanh_khoan || {}).dang_cho_sweep_run || [];
    pend.forEach(function (d) {
      if (!d || !d.id || !(d.nen_lay <= c)) return;
      var p = M.pools[d.id] || stubPool(M, d);
      if (p.outcome) return;
      p.taken = d.nen_lay;
      p.extreme = finite(d.cuc_tri_cu_quet) ? d.cuc_tri_cu_quet : null;
      p.pendingLeft = finite(d.con_lai_nen) ? d.con_lai_nen : null;
      p.pen = finite(d.xuyen_atr) ? d.xuyen_atr : null;
      p.atrLocked = finite(d.atr_khoa) ? d.atr_khoa : null;
      p.touches = finite(d.so_lan_cham) ? d.so_lan_cham : null;
      if (M.W === null && finite(d.con_lai_nen)) M.W = d.con_lai_nen + c - d.nen_lay;
    });
    M.shifts.sort(function (a, b) { return a.event_bar_index - b.event_bar_index; });
    var byConf = function (a, b) { return (a.confirmed_bar_index - b.confirmed_bar_index) || (a.event_bar_index - b.event_bar_index); };
    M.htfSwings.sort(byConf);
    M.periods.sort(byConf);
    M.pds.sort(byConf);
    M.poolList = Object.keys(M.pools).map(function (k) { return M.pools[k]; })
      .sort(function (a, b) { return a.seq - b.seq; });
    return M;
  }

  /** Trạng thái vùng ở nến h (sau nến h, như timeline); null nếu vùng chưa được biết ở h. */
  function poolAt(p, h) {
    if (!p || !(p.known <= h)) return null;
    var level = null, n = 0, i;
    for (i = 0; i < p.levels.length; i++) if (p.levels[i].from <= h) level = p.levels[i].level;
    for (i = 0; i < p.sources.length; i++) if (p.sources[i].known <= h) n++;
    if (!finite(level)) return null;
    var state = 'intact';
    if (finite(p.taken) && p.taken <= h) state = p.outcome && p.resolved <= h ? p.outcome : 'pending';
    return { pool: p, id: p.id, seq: p.seq, side: p.side, tier: p.tier, level: level, eq: n >= 2, nSrc: n, state: state };
  }

  function statesAt(M, h) {
    var out = [];
    M.poolList.forEach(function (p) { var s = poolAt(p, h); if (s) out.push(s); });
    return out;
  }

  /** Vùng còn nguyên ở nến h: BSL mức thấp nhất trước, SSL mức cao nhất trước (cùng mức → id nhỏ trước) — như heap lõi. */
  function nearestIntact(M, h, states) {
    var all = states || statesAt(M, h);
    var bsl = all.filter(function (s) { return s.state === 'intact' && s.side === 'BSL'; })
      .sort(function (a, b) { return (a.level - b.level) || (a.seq - b.seq); });
    var ssl = all.filter(function (s) { return s.state === 'intact' && s.side === 'SSL'; })
      .sort(function (a, b) { return (b.level - a.level) || (a.seq - b.seq); });
    return { BSL: bsl, SSL: ssl };
  }

  function atrAt(M, h) {
    for (var i = h; i >= h - 50; i--) { var p = M.tl[i]; if (p && finite(p.atr)) return p.atr; }
    return null;
  }

  /** «Hiện tại» tại con trỏ: 2 vùng còn nguyên gần nhất mỗi phía + vùng có kết cục trong `recent` nến cuối + vùng bị
   * quét của shift đang hiện + vùng đang chờ; shift gần nhất + shift trong `recent` nến cuối. */
  function selectCurrent(M, opts) {
    var o = opt(opts), c = M.cursor;
    var states = statesAt(M, c), byId = {}, pick = {}, nearIds = {};
    states.forEach(function (s) { byId[s.id] = s; });
    var near = nearestIntact(M, c, states);
    // `nearest` MỨC còn nguyên gần nhất mỗi phía (0.4.0: cùng một đỉnh/đáy thường sinh vùng ở nhiều tầng — M15, H1, H4, PDH… —
    // cùng mức; các vùng cùng mức gộp thành một đường, tính là một)
    ['BSL', 'SSL'].forEach(function (side) {
      var lv = [];
      near[side].forEach(function (s) {
        if (lv.indexOf(s.level) < 0) { if (lv.length >= o.nearest) return; lv.push(s.level); }
        pick[s.id] = s;
        nearIds[s.id] = 1;
      });
    });
    var recentOut = [];
    states.forEach(function (s) {
      if (o.history || s.state === 'pending') pick[s.id] = s;
      else if (OUTCOME[s.state] && s.pool.resolved >= c - o.recent) recentOut.push(s);
      else if (o.allIntact && s.state === 'intact') pick[s.id] = s;
    });
    // Kết cục trong `recent` nến: giữ `outcomePerSide` nhóm (vùng gộp tính một) gần con trỏ nhất mỗi phía.
    if (!o.history) {
      var og = groupPools(recentOut, atrAt(M, c), o);
      ['BSL', 'SSL'].forEach(function (side) {
        og.filter(function (g) { return g.side === side; }).sort(function (a, b) {
          return (lastResolved(b) - lastResolved(a)) || (b.main.pool.taken - a.main.pool.taken) || (a.main.seq - b.main.seq);
        }).slice(0, o.outcomePerSide).forEach(function (g) { g.members.forEach(function (m) { pick[m.id] = m; }); });
      });
    }
    var shifts = M.shifts.filter(function (e, k) {
      return o.history || k === M.shifts.length - 1 || e.event_bar_index >= c - o.recent;
    });
    shifts.forEach(function (e) {
      ((e.details || {}).swept || []).forEach(function (w) {
        var s = byId[w.vung];
        if (s && s.state !== 'intact') pick[w.vung] = s;
      });
    });
    var pools = Object.keys(pick).map(function (k) { return pick[k]; }).sort(function (a, b) { return a.seq - b.seq; });
    return { pools: pools, shifts: shifts, near: near, byId: byId, nearIds: nearIds, history: !!o.history,
      fvgs: selectFvgs(M, o), htf: o.htf ? selectHtf(M, o) : null };
  }

  /** Lớp phủ khung lớn tại con trỏ (opts.htf = {h1, …}; mọi thứ đã lọc confirmed ≤ con trỏ ở buildModel):
   *   swings  — ITH/ITL H4 (+ H1 khi h1): «Hiện tại» = htfSwingsPerSide gần nhất mỗi (khung, phía); Lịch sử = mọi;
   *   fvgs    — FVG H4 (+ H1): «Hiện tại» = còn mở (chưa có PD_*), cách close ≤ htfFvgFarAtr × ATR, ≤ htfFvgPerSide gần giá
   *             nhất mỗi (khung, chiều); Lịch sử = mọi. Luôn kèm FVG của PD_* gần nhất (nguồn pd_bias hiện tại, mọi khung);
   *   pdSrc   — id FVG của PD_* gần nhất (cùng nến) — nguồn pd_bias tại con trỏ;
   *   periods — PDH/PDL/PWH/PWL: «Hiện tại» = kỳ gần nhất mỗi tên; Lịch sử = mọi kỳ. */
  function selectHtf(M, opts) {
    var o = opt(opts), h = o.htf || {}, frames = { H4: 1 }, c = M.cursor;
    if (h.h1) frames.H1 = 1;
    var out = { swings: [], fvgs: [], pdSrc: {}, periods: [] };
    // ITH/ITL
    var bucket = {};
    M.htfSwings.forEach(function (e) {
      var f = frameOf(e);
      if (!frames[f]) return;
      var k = f + '|' + e.structure_type;
      (bucket[k] = bucket[k] || []).push(e);
    });
    Object.keys(bucket).forEach(function (k) {
      var L = bucket[k];
      out.swings = out.swings.concat(o.history ? L : L.slice(-o.htfSwingsPerSide));
    });
    out.swings.sort(function (a, b) { return a.confirmed_bar_index - b.confirmed_bar_index; });
    // nguồn pd_bias hiện tại = mọi PD_* ở nến xác nhận cuối cùng
    var lastPd = M.pds.length ? M.pds[M.pds.length - 1].confirmed_bar_index : null;
    M.pds.forEach(function (e) {
      if (e.confirmed_bar_index !== lastPd) return;
      var fz = (e.details || {}).fvg || e.reference_event_id;
      if (fz) out.pdSrc[fz] = e.event_id;
    });
    // FVG khung lớn
    var close = o.close, atr = atrAt(M, c), far = finite(close) && finite(atr) ? o.htfFvgFarAtr * atr : null;
    var pick = {}, groups = {};
    M.htfFvgs.forEach(function (e) {
      var f = frameOf(e);
      if (out.pdSrc[e.event_id]) { pick[e.event_id] = e; return; }
      if (!frames[f]) return;
      if (o.history) { pick[e.event_id] = e; return; }
      if (M.htfFvgEnd[e.event_id]) return;                       // đã respect / disrespect
      if (far !== null && fvgDist(e, close) > far) return;
      var k = f + '|' + e.structure_type;
      (groups[k] = groups[k] || []).push(e);
    });
    Object.keys(groups).forEach(function (k) {
      groups[k].sort(function (a, b) {
        if (finite(close)) {
          var da = fvgDist(a, close), db = fvgDist(b, close);
          if (da !== db) return da - db;
        }
        return b.confirmed_bar_index - a.confirmed_bar_index;
      }).slice(0, o.htfFvgPerSide).forEach(function (e) { pick[e.event_id] = e; });
    });
    out.fvgs = Object.keys(pick).map(function (k) { return pick[k]; })
      .sort(function (a, b) { return (a.confirmed_bar_index - b.confirmed_bar_index) || (a.event_bar_index - b.event_bar_index); });
    // PDH/PDL/PWH/PWL
    if (o.history) out.periods = M.periods.slice();
    else {
      var latest = {};
      M.periods.forEach(function (e) { var n = (e.details || {}).ten || e.event_id; latest[n] = e; });
      out.periods = Object.keys(latest).map(function (k) { return latest[k]; })
        .sort(function (a, b) { return a.confirmed_bar_index - b.confirmed_bar_index; });
    }
    return out;
  }

  /** Dealing range H4 tại con trỏ: hi / lo đọc timeline (htf_H4_dealing_hi/lo — chỉ đổi khi nến H4 chốt); mốc vẽ = ITH / ITL
   * H4 gần nhất đã biết (cùng mốc của lõi), không có sự kiện thì nến bắt đầu giá trị hiện tại. */
  function htfRangeAt(M) {
    var L = M.tlList, n = L.length;
    if (!n) return null;
    var p = L[n - 1];
    if (!finite(p.htf_H4_dealing_hi) || !finite(p.htf_H4_dealing_lo)) return null;
    var i = n - 1;
    while (i > 0 && L[i - 1].htf_H4_dealing_hi === p.htf_H4_dealing_hi && L[i - 1].htf_H4_dealing_lo === p.htf_H4_dealing_lo) i--;
    var hiA = null, loA = null;
    M.htfSwings.forEach(function (e) {
      if (frameOf(e) !== 'H4') return;
      if (e.structure_type === 'HTF_SWING_HIGH') hiA = e; else loA = e;
    });
    var start = hiA && loA ? Math.min(hiA.event_bar_index, loA.event_bar_index) : L[i].bar_index;
    return {
      hi: p.htf_H4_dealing_hi, lo: p.htf_H4_dealing_lo, eq: (p.htf_H4_dealing_hi + p.htf_H4_dealing_lo) / 2,
      zone: p.htf_H4_zone || null, pos: finite(p.htf_H4_range_pos) ? p.htf_H4_range_pos : null, since: L[i].bar_index,
      start: start, hiAnchor: hiA, loAnchor: loA, order: hasOwn(p, 'htf_H4_order') ? p.htf_H4_order : null
    };
  }

  /** Nến H4 đang hình thành ở nến h (CHỈ để vẽ — lõi không dùng): các nến khung chạy ≤ h cùng ô H4 mốc ny_1700 (giờ New York)
   * với nến h, OHLC gộp từ barOf(i) (i ≤ h). Nến h đóng đúng / sau mốc đóng ô → nến H4 vừa chốt, không có nến đang hình thành;
   * lõi chốt ở h (timeline htf_H4_age = 0) khi nến trước cùng ô → chốt sớm theo lịch phiên (ngày đóng sớm) → cũng không có.
   * Ở đúng con trỏ có pending_state.khung_lon.H4.dang_hinh_thanh thì lấy thêm period_end / số nến kỳ vọng của lõi.
   * → {start, end (nến cuối dự kiến), open, high, low, close, n, expected, periodEnd (giây), from: 'lõi' | 'gộp'} | null. */
  function formingAt(M, h, barOf) {
    var p = M.tl[h];
    if (!p || !M.hasHtf || !finite(p.time) || typeof barOf !== 'function' || !finite(M.step)) return null;
    if (p.htf_H4_order === undefined) return null;
    var bk = h4Bucket(p.time);
    if (!bk || p.time + M.step >= bk.end) return null;   // nến h đóng ô H4 → vừa chốt
    if (p.htf_H4_age === 0 && h > 0) {                    // lõi chốt H4 ở h giữa ô danh nghĩa (period_end theo lịch, đóng sớm)
      var pv = M.tl[h - 1], pbk = pv && finite(pv.time) ? h4Bucket(pv.time) : null;
      if (pbk && pbk.id === bk.id) return null;           // (nến trước khác ô = chốt muộn ô trước — nến h mở ô mới, vẫn vẽ)
    }
    var start = h;
    for (var i = h - 1; i >= 0 && i >= h - 400; i--) {
      var q = M.tl[i];
      if (!q || !finite(q.time)) break;
      var b2 = h4Bucket(q.time);
      if (!b2 || b2.id !== bk.id) break;
      start = i;
    }
    var o = null, hi = -Infinity, lo = Infinity, cl = null, n = 0;
    for (var j = start; j <= h; j++) {
      var b = barOf(j);
      if (!b) continue;
      if (o === null) o = b.open;
      if (b.high > hi) hi = b.high;
      if (b.low < lo) lo = b.low;
      cl = b.close;
      n++;
    }
    if (!n) return null;
    var expected = Math.max(n, Math.round((bk.end - M.tl[start].time) / M.step));
    var out = { start: start, end: start + expected - 1, open: o, high: hi, low: lo, close: cl, n: n, expected: expected,
      periodEnd: bk.end, from: 'gộp' };
    var kl = h === M.cursor && M.pending && M.pending.khung_lon, f = kl && kl.H4 && kl.H4.dang_hinh_thanh;
    if (f && f.nen_cuoi === h && f.nen_dau === start) {
      out.expected = Math.max(n, f.expected_bars || expected);
      out.end = start + out.expected - 1;
      out.periodEnd = isoSec(f.period_end) || bk.end;
      out.from = 'lõi';
    }
    return out;
  }

  /** FVG tại con trỏ: Lịch sử → mọi FVG đã biết; Hiện tại → FVG còn mở (chưa lấp), biết trong `fvgRecent` (200) nến gần
   * con trỏ VÀ cách close ≤ `fvgFarAtr` (5) × ATR con trỏ, tối đa `fvgPerSide` (3) gần giá nhất mỗi chiều. FVG cũ / xa hơn
   * chỉ hiện ở Lịch sử; FVG của shift đi cùng shift. */
  function selectFvgs(M, o) {
    if (o.history) return M.fvgs.slice();
    var close = o.close, out = [], c = M.cursor, atr = atrAt(M, c);
    var far = finite(close) && finite(atr) ? o.fvgFarAtr * atr : null;
    ['FVG_UP', 'FVG_DOWN'].forEach(function (t) {
      var open = M.fvgs.filter(function (e) {
        return e.structure_type === t && !M.fvgFilled[e.event_id] && e.confirmed_bar_index >= c - o.fvgRecent &&
          (far === null || fvgDist(e, close) <= far);
      });
      open.sort(function (a, b) {
        if (finite(close)) {
          var da = fvgDist(a, close), db = fvgDist(b, close);
          if (da !== db) return da - db;
        }
        return b.confirmed_bar_index - a.confirmed_bar_index;
      });
      out = out.concat(open.slice(0, o.fvgPerSide));
    });
    return out.sort(function (a, b) { return a.confirmed_bar_index - b.confirmed_bar_index; });
  }
  function fvgDist(e, close) {
    var x = e.details || {};
    return close > x.hi ? close - x.hi : (close < x.lo ? x.lo - close : 0);
  }

  /** Mức được bảo vệ + dealing range tại con trỏ, đọc timeline: đoạn liên tiếp cùng protected_id / dealing_id. */
  function structureAt(M) {
    var L = M.tlList, n = L.length, out = { prot: null, range: null, order: null };
    if (!n) return out;
    var p = L[n - 1], i, j;
    out.order = p.order === undefined ? null : p.order;
    if (finite(p.protected) && p.protected_id) {
      for (i = n - 1; i > 0 && L[i - 1].protected_id === p.protected_id && finite(L[i - 1].protected); i--) { /* lùi */ }
      var brokenAt = null;
      for (j = i; j < n; j++) if (L[j].protected_broken) { brokenAt = L[j].bar_index; break; }
      var sb = parseInt(String(p.protected_id).slice(1), 10);
      out.prot = {
        id: String(p.protected_id), price: p.protected, side: p.protected_side, swingBar: isFinite(sb) ? sb : L[i].bar_index,
        since: L[i].bar_index, brokenAt: brokenAt, broken: !!p.protected_broken, order: out.order
      };
    }
    if (finite(p.dealing_hi) && finite(p.dealing_lo) && p.dealing_id) {
      for (i = n - 1; i > 0 && L[i - 1].dealing_id === p.dealing_id; i--) { /* lùi */ }
      var parts = String(p.dealing_id).split('-'), a = parseInt(parts[0], 10), b = parseInt(parts[1], 10);
      out.range = {
        id: String(p.dealing_id), hi: p.dealing_hi, lo: p.dealing_lo, eq: finite(p.dealing_eq) ? p.dealing_eq : (p.dealing_hi + p.dealing_lo) / 2,
        hiBar: isFinite(a) ? a : null, loBar: isFinite(b) ? b : null,
        start: isFinite(a) && isFinite(b) ? Math.min(a, b) : L[i].bar_index, since: L[i].bar_index,
        zone: p.zone || null, pos: finite(p.range_pos) ? p.range_pos : null
      };
    }
    return out;
  }

  function fade(o, age) { return Math.max(o.minFade, 1 - Math.max(0, age) / o.ageBars); }
  function swingLevel(t) { return /_L2$/.test(t) ? 2 : (/_L3$/.test(t) ? 3 : 1); }

  /** Tên vùng trên chart (H2 — thuật ngữ ICT ngắn): khung chạy «BSL» / «EQH»; H1/H4 «BSL H1» / «EQH H4»; D «PDH» / «PDL»;
   * W «PWH» / «PWL». */
  function poolName(s) {
    var t = s.pool ? s.pool.tier : s.tier;
    if (PERIOD_NAME[t]) return PERIOD_NAME[t][s.side];
    var base = s.eq ? (s.side === 'BSL' ? 'EQH' : 'EQL') : s.side;
    return runTier(t) ? base : base + ' ' + t;
  }
  /** Chữ tầng sau «sweep / run / chưa rõ»: khung chạy → «EQH» khi gộp EQ, không thì rỗng; H1/H4 → «H1» (gộp EQ: «EQH H1»);
   * D/W → «PDH»… */
  function tierTag(s) {
    var t = s.pool.tier;
    if (PERIOD_NAME[t]) return PERIOD_NAME[t][s.side];
    if (runTier(t)) return s.eq ? poolName(s) : '';
    return s.eq ? poolName(s) : t;
  }
  /** Thành viên tầng cao nhất của nhóm vùng gộp (bằng tầng → thành viên chính). */
  function topOf(g) {
    var top = g.main;
    g.members.forEach(function (m) { if (tierRank(m.pool.tier) > tierRank(top.pool.tier)) top = m; });
    return top;
  }
  function lastResolved(g) { return Math.max.apply(null, g.members.map(function (x) { return x.pool.resolved; })); }

  /** Gộp vùng cùng phía, cùng kết cục (hoặc cùng đang chờ), cùng nến lấy, cách nhau ≤ groupAtr × ATR → một đường
   * «sweep ×2» / «SSL bị lấy · chờ ×2»; vùng còn nguyên cùng phía, ĐÚNG cùng mức (cùng đỉnh/đáy ở nhiều tầng) → một đường mang
   * tên tầng cao nhất. `n` = số MỨC khác nhau trong nhóm (chữ «×n»), `count` = số vùng. */
  function groupPools(states, atr, opts) {
    var o = opt(opts), groups = [], idx = {};
    states.forEach(function (s) {
      if (s.state === 'intact') {
        var ki = s.side + '|intact|' + s.level;
        if (idx[ki]) { idx[ki].push(s); return; }
        idx[ki] = [s];
        groups.push(idx[ki]);
        return;
      }
      if (!(OUTCOME[s.state] || s.state === 'pending') || !finite(atr)) { groups.push([s]); return; }
      var key = s.side + '|' + s.state + '|' + s.pool.taken, g = idx[key];
      if (g && g.some(function (x) { return Math.abs(x.level - s.level) <= o.groupAtr * atr; })) { g.push(s); return; }
      idx[key] = [s];
      groups.push(idx[key]);
    });
    return groups.map(function (g) {
      g.sort(function (a, b) { return (b.pool.origin - a.pool.origin) || (a.seq - b.seq); });   // gốc muộn nhất → đường ngắn nhất
      var ids = g.map(function (x) { return x.id; }).sort(function (a, b) { return seqOf(a) - seqOf(b); });
      var lv = [];
      g.forEach(function (x) { if (lv.indexOf(x.level) < 0) lv.push(x.level); });
      return { id: 'pool:' + ids.join('+'), members: g, main: g[0], state: g[0].state, side: g[0].side, n: lv.length, count: g.length };
    });
  }

  /** Đối tượng vẽ cho MSL.primitives. logicalOf(chỉ số nến) → chỉ số logic (số lẻ được; sau nến cuối = tương lai).
   * opts: {flow, shift} bật lớp; ext/recent/nearest/groupAtr/farAtr như DEF; detail = lớp Chi tiết; htf = lớp khung lớn
   * ({swing, range, fvg, levels, forming, h1}; cần sel từ selectCurrent(…, {htf}) và opts.barOf cho nến đang hình thành).
   * Vùng theo tầng: nét đậm dần M15 < H1 < H4 = D < W, chữ «BSL H1» / «PDH»…; nhóm gộp nhiều tầng ghi tầng cao nhất. */
  function buildDrawing(M, sel, logicalOf, opts) {
    var o = opt(opts), c = M.cursor, d = M.digits;
    var atr = atrAt(M, c), near = finite(atr) ? o.farAtr * atr : null;
    var localNear = function (h) { var a = atrAt(M, h); return finite(a) ? o.farAtr * a : near; };
    o.localNear = localNear;
    var segments = [], boxes = [], drawnPools = {};
    var counts = { intact: 0, pending: 0, sweep: 0, run: 0, unresolved: 0, lines: 0, grouped: 0, sweepBox: 0, shift: 0, fvg: 0, fvgFilled: 0,
      htfTier: 0 };
    var Lc = logicalOf(c);
    if (o.flow !== false) {
      var groups = groupPools(sel.pools, atr, o);
      // thứ tự gần con trỏ của các nhóm đã kết cục → ưu tiên nhãn sweep/run (gần trước)
      var rank = {};
      groups.filter(function (g) { return OUTCOME[g.state]; }).sort(function (a, b) {
        return (lastResolved(b) - lastResolved(a)) || (b.main.pool.taken - a.main.pool.taken);
      }).forEach(function (g, i) { rank[g.id] = i; });
      groups.forEach(function (g) {
        var s = g.main, p = s.pool, up = s.side === 'BSL', col = up ? COL.bsl : COL.ssl;
        var top = topOf(g), topTag = tierTag(top);
        var name = poolName(top);
        var tag = g.n > 1 ? ' ×' + g.n + (runTier(top.pool.tier) ? '' : ' · ' + topTag) : (topTag ? ' ' + topTag : '');
        var l1 = logicalOf(p.origin);
        if (!finite(l1)) return;
        g.members.forEach(function (m) { drawnPools[m.id] = 1; });
        // Lịch sử: «gần» theo ATR lúc vùng được biết (ATR nhiều năm sau lớn hơn hẳn → trục giá bị giãn khi xem quá khứ)
        var nearP = o.history ? localNear(p.known) : near;
        var w = tierWidth(top.pool.tier);
        var item = { id: g.id, l1: l1, p1: s.level, p2: s.level, color: col, width: w, autoscale: 'near', near: nearP };
        var nearOne = !!(sel.nearIds && sel.nearIds[s.id]) || !sel.nearIds;
        counts[g.state] += g.count;
        counts.lines++;
        if (g.count > 1) counts.grouped += g.count;
        if (!runTier(top.pool.tier)) counts.htfTier++;
        var lt = logicalOf(p.taken);
        if (g.state === 'intact') {
          item.l2 = logicalOf(c + o.ext);
          item.style = 'solid';
          item.alpha = 0.95;
          item.label = { text: name, pos: 'right', priority: PRI.intact, edgeText: name + ' ' + fp(s.level, d),
            weight: runTier(top.pool.tier) ? 600 : 700 };
          if (!nearOne) {   // Lịch sử / «mọi vùng còn nguyên»: vùng không thuộc 2 gần nhất mỗi phía — mảnh, mờ, không nhãn mép
            item.alpha = 0.5;
            item.width = Math.max(1, w - 0.5);
            item.label = { text: name, pos: 'right', priority: PRI.intactFar, size: 10, alpha: 0.75 };
          }
        } else if (g.state === 'pending') {
          item.l2 = Lc + 1;
          item.style = 'dashed';
          item.label = { text: name + ' bị lấy · chờ' + (g.n > 1 ? ' ×' + g.n : ''), pos: 'right', priority: PRI.pending,
            edgeText: name + ' ' + fp(s.level, d) + ' bị lấy', fallback: '…' };
          var plv = g.members.map(function (x) { return x.level; });
          var pex = g.members.map(function (x) { return x.pool.extreme; }).filter(finite);
          if (pex.length) {
            boxes.push({
              id: g.id, l1: lt - 0.45, l2: Lc + 0.45, p1: up ? Math.min.apply(null, plv) : Math.max.apply(null, plv),
              p2: up ? Math.max.apply(null, pex) : Math.min.apply(null, pex), minH: 3, grow: up ? 'up' : 'down',
              fill: rgba(col, 0.16), border: rgba(col, 0.7), borderStyle: 'dashed', autoscale: 'near', near: nearP
            });
          }
        } else if (g.state === 'sweep') {
          item.l2 = lt;
          item.style = 'dotted';
          item.width = Math.max(1.6, w);
          item.alpha = 0.85;
          item.label = { text: 'sweep' + tag, pos: 'end', side: up ? 'above' : 'below', priority: PRI.outcome + 0.01 * rank[g.id], fallback: '✕' };
          var lv = g.members.map(function (x) { return x.level; });
          var ex = g.members.map(function (x) { return x.pool.extreme; }).filter(finite);
          var rs = g.members.map(function (x) { return x.pool.resolved; });
          if (ex.length) {
            boxes.push({
              id: g.id, l1: lt - 0.45, l2: logicalOf(Math.max.apply(null, rs)) + 0.45,
              p1: up ? Math.min.apply(null, lv) : Math.max.apply(null, lv),
              p2: up ? Math.max.apply(null, ex) : Math.min.apply(null, ex),
              minH: 4, grow: up ? 'up' : 'down', fill: rgba(col, 0.28), border: rgba(col, 0.85), borderStyle: 'solid',
              autoscale: 'near', near: nearP
            });
            counts.sweepBox++;
          }
        } else if (g.state === 'run') {
          item.l2 = lt;
          item.style = 'solid';
          item.alpha = 0.55;
          item.label = { text: 'run' + tag, pos: 'end', side: up ? 'above' : 'below', priority: PRI.outcome + 0.01 * rank[g.id], color: rgba(col, 0.95),
            fallback: '»' };
        } else {   // unresolved: gặp khoảng trống trước khi rõ
          item.l2 = lt;
          item.style = 'dotted';
          item.color = COL.grey;
          item.alpha = 0.85;
          item.label = { text: 'chưa rõ' + tag, pos: 'end', side: up ? 'above' : 'below', priority: PRI.outcome + 0.01 * rank[g.id], color: COL.grey,
            fallback: '?' };
        }
        if (o.history && OUTCOME[g.state]) {   // Lịch sử: mờ dần theo tuổi kết cục
          var f = fade(o, c - Math.max.apply(null, g.members.map(function (x) { return x.pool.resolved; })));
          item.alpha = (item.alpha == null ? 1 : item.alpha) * f;
          item.label.alpha = (item.label.alpha == null ? 1 : item.label.alpha) * f;
          var lastBox = boxes[boxes.length - 1];   // hộp sweep (nếu có) vừa thêm cho chính nhóm này
          if (lastBox && lastBox.id === g.id) lastBox.alpha = f;
        }
        segments.push(item);
      });
    }
    if (o.shift !== false) {
      var lastShift = sel.shifts.length ? sel.shifts[sel.shifts.length - 1].event_id : null;
      sel.shifts.forEach(function (e) {
        var x = e.details || {}, mss = isMss(e), upDir = /_UP$/.test(e.structure_type), col = upDir ? COL.up : COL.down;
        var takes = (x.swept || []).map(function (w) { return w.nen_lay; }).filter(finite);
        // MSS: đoạn ngang tại mốc bị phá (STL / STH), từ nến mốc tới nến phá; shift: tại mức bị quét, từ nến lấy tới displacement
        var start = mss ? (finite(x.nen_moc_pha) ? x.nen_moc_pha : e.event_bar_index)
          : (takes.length ? Math.min.apply(null, takes) : (finite(x.nen_sweep) ? x.nen_sweep : e.event_bar_index));
        var lvl = mss ? x.moc_pha : x.muc_bi_quet;
        if (!finite(lvl)) return;
        counts.shift++;
        var sf = o.history ? fade(o, c - e.event_bar_index) : null;
        var shItem = {
          id: 'shift:' + e.event_id, l1: logicalOf(start) - 0.45, l2: logicalOf(e.event_bar_index) + 0.45,
          p1: lvl, p2: lvl, color: col, width: 2.2, style: 'solid',
          label: { text: (mss ? 'MSS ' : 'Shift ') + (upDir ? '↑' : '↓'), pos: 'mid', side: upDir ? 'below' : 'above', size: 12,
            weight: 700,
            priority: e.event_id === lastShift ? PRI.shiftLast : PRI.shift, fallback: upDir ? '▴' : '▾' }
        };
        if (sf !== null) { shItem.alpha = sf; shItem.label.alpha = sf; }
        segments.push(shItem);
        var fv = M.shiftFvg[e.event_id];
        if (!fv) return;
        var fx = fv.details || {};
        if (!finite(fx.lo) || !finite(fx.hi)) return;
        var filled = M.fvgFilled[fx.fvg];
        var end = filled ? logicalOf(filled.event_bar_index) + 0.45 : logicalOf(c + o.ext);
        counts.fvg++;
        if (filled) counts.fvgFilled++;
        var fbox = {
          id: 'fvg:' + fv.event_id,
          l1: logicalOf(finite(fx.nen_displacement) ? fx.nen_displacement : finite(fx.nen_pha) ? fx.nen_pha : e.event_bar_index) - 0.45,
          l2: end, p1: fx.lo, p2: fx.hi, fill: rgba(col, filled ? 0.10 : 0.20), border: rgba(col, filled ? 0.55 : 0.8),
          borderStyle: filled ? 'dotted' : 'solid', autoscale: 'near', near: o.history ? localNear(e.event_bar_index) : near
        };
        var mid = (fx.lo + fx.hi) / 2;
        var flab = {
          id: 'fvg:' + fv.event_id, noLine: true, l1: end, l2: end, p1: mid, p2: mid, color: col, autoscale: false,
          label: { text: 'FVG', pos: 'right', priority: PRI.fvgShift, size: 11, alpha: filled ? 0.7 : 0.95 }
        };
        if (sf !== null) { fbox.alpha = sf; flab.label.alpha *= sf; }
        boxes.push(fbox);
        segments.push(flab);
      });
    }
    var det = o.detail || null;
    if (det) detailDrawing(M, sel, logicalOf, o, det, near, segments, boxes, counts);
    if (o.htf) htfDrawing(M, sel, logicalOf, o, near, segments, boxes, counts, drawnPools);
    return { segments: segments, boxes: boxes, counts: counts };
  }

  /** Lớp khung lớn: ITH/ITL H4 (H1) = vòng tròn rỗng + «HH H4»; dealing range H4 = hai đường nét đứt + EQ chấm («Range H4»,
   * «EQ H4»); FVG H4 (H1) = hộp viền dày + CE chấm, «FVG H4» — dừng ở PD_* đầu tiên («· respect» / «· disrespect»);
   * PDH/PDL/PWH/PWL hiện hành (bỏ qua mức mà lớp Gọn đã vẽ thành vùng); nến H4 đang hình thành = khung nét đứt mờ + thân
   * mờ, chữ «H4 đang hình thành — chưa dùng». Mọi thứ chỉ từ sự kiện đã xác nhận / timeline tại con trỏ. */
  function htfDrawing(M, sel, logicalOf, o, near, segments, boxes, counts, drawnPools) {
    var H = o.htf, c = M.cursor, d = M.digits, hs = sel.htf || selectHtf(M, o), localNear = o.localNear;
    var lEnd = logicalOf(c + o.ext);
    counts.htfSwing = 0; counts.htfRange = 0; counts.htfFvg = 0; counts.htfLevel = 0; counts.forming = 0;
    if (H.swing) {
      hs.swings.forEach(function (e) {
        var x = e.details || {}, f = frameOf(e), high = e.structure_type === 'HTF_SWING_HIGH', col = HCOL[f] || HCOL.H4;
        var l = logicalOf(e.event_bar_index);
        if (!finite(l)) return;
        var fa = o.history ? fade(o, c - e.confirmed_bar_index) : 1;
        segments.push({ id: 'htfsw:' + e.event_id, noLine: true, l1: l, l2: l, p1: e.price, p2: e.price, color: col, autoscale: false,
          dot: { r: f === 'H4' ? 4.5 : 3.6, color: col, alpha: 0.95 * fa, ring: true, width: f === 'H4' ? 2 : 1.5 },
          label: { text: (x.nhan || x.ten || (high ? 'ITH' : 'ITL')) + ' ' + f, pos: 'mid', side: high ? 'above' : 'below', strict: true,
            size: 10, bg: false, weight: 700, priority: PRI.htfSwing, color: col, alpha: fa } });
        counts.htfSwing++;
      });
    }
    if (H.range) {
      var r = htfRangeAt(M);
      if (r && r.hi > r.lo) {
        var ls = logicalOf(r.start) - 0.45, at = logicalOf(r.start) + 0.6;
        var base = { color: HCOL.H4, autoscale: 'near', near: near };
        segments.push(Object.assign({ id: 'htfrange:H4:hi', l1: ls, l2: lEnd, p1: r.hi, p2: r.hi, width: 1.2, style: 'dashed', alpha: 0.75,
          label: { text: 'Range H4', pos: 'start', at: at, priority: PRI.htfRange, size: 10, strict: true } }, base));
        segments.push(Object.assign({ id: 'htfrange:H4:lo', l1: ls, l2: lEnd, p1: r.lo, p2: r.lo, width: 1.2, style: 'dashed', alpha: 0.75 }, base));
        segments.push(Object.assign({ id: 'htfrange:H4:eq', l1: ls, l2: lEnd, p1: r.eq, p2: r.eq, width: 1.4, style: 'dotted', alpha: 0.9,
          label: { text: 'EQ H4', pos: 'start', at: at, priority: PRI.htfRange, size: 10, strict: true } }, base));
        counts.htfRange = 1;
      }
    }
    if (H.fvg) {
      hs.fvgs.forEach(function (e) {
        var x = e.details || {}, f = frameOf(e), up = e.structure_type === 'HTF_FVG_UP', col = up ? COL.up : COL.down;
        if (!finite(x.lo) || !finite(x.hi)) return;
        var end = M.htfFvgEnd[e.event_id];
        var res = end ? (/^PD_RESPECT/.test(end.structure_type) ? 'respect' : 'disrespect') : '';
        var l1 = logicalOf(finite(x.nen_giua_tu) ? x.nen_giua_tu : e.event_bar_index) - 0.45;
        var l2 = end ? logicalOf(end.event_bar_index) + 0.45 : lEnd;
        var fa = o.history && end ? fade(o, c - end.event_bar_index) : 1;
        var id = 'htffvg:' + e.event_id, ce = finite(x.ce) ? x.ce : (x.lo + x.hi) / 2;
        boxes.push({ id: id, l1: l1, l2: l2, p1: x.lo, p2: x.hi, fill: rgba(col, end ? 0.05 : 0.09), border: rgba(col, end ? 0.5 : 0.85),
          borderStyle: end ? 'dotted' : 'solid', borderWidth: f === 'H4' ? 2 : 1.5, alpha: fa, autoscale: 'near',
          near: o.history ? localNear(e.confirmed_bar_index) : near });
        segments.push({ id: id, l1: l1, l2: l2, p1: ce, p2: ce, color: col, width: 1, style: 'dotted', alpha: 0.55 * fa, autoscale: false,
          label: { text: 'FVG ' + f + (res ? ' · ' + res : ''), pos: 'start', at: logicalOf(e.confirmed_bar_index) + 0.6,
            priority: PRI.htfFvg, size: 10, strict: true, alpha: (end ? 0.75 : 0.95) * fa } });
        counts.htfFvg++;
      });
    }
    if (H.levels) {
      var nextOf = {};   // Lịch sử: mức cũ dừng ở lúc mức cùng tên mới được biết
      hs.periods.forEach(function (e) { var n = (e.details || {}).ten; if (n) nextOf[n] = nextOf[n] || []; if (n) nextOf[n].push(e); });
      hs.periods.forEach(function (e) {
        var x = e.details || {}, v = x.vung_thanh_khoan || {}, name = x.ten || srcKind(e.structure_type, x);
        var hi = e.structure_type === 'HTF_PERIOD_HIGH', col = hi ? COL.bsl : COL.ssl, f = x.khung || 'D';
        if (v.vung && drawnPools[v.vung]) return;          // lớp Gọn đã vẽ vùng này (chữ PDH…)
        var s = v.vung && M.pools[v.vung] ? poolAt(M.pools[v.vung], c) : null;
        var taken = s && s.state !== 'intact' ? s.pool.taken : (v.trang_thai === 'khong_tao' ? e.confirmed_bar_index : null);
        var list = nextOf[name] || [], k = list.indexOf(e), repl = k >= 0 && k < list.length - 1 ? list[k + 1].confirmed_bar_index : null;
        var l1 = logicalOf(e.event_bar_index);
        if (!finite(l1)) return;
        var fa = o.history && repl !== null ? fade(o, c - repl) : 1;
        var it = { id: 'lvl:' + e.event_id, l1: l1, p1: e.price, p2: e.price, color: col, width: tierWidth(f), style: 'solid',
          alpha: 0.9 * fa, autoscale: 'near', near: o.history ? localNear(e.confirmed_bar_index) : near };
        if (repl !== null) {   // mức của kỳ cũ (chỉ ở Lịch sử): dừng ở nến lấy hoặc lúc kỳ sau được biết, chữ nhỏ mờ
          it.l2 = logicalOf(taken !== null ? Math.min(taken, repl) : repl);
          it.label = { text: name, pos: 'end', side: hi ? 'above' : 'below', priority: PRI.htfLevelOld, size: 10, alpha: 0.8 * fa };
          segments.push(it);
        } else if (taken === null) {   // mức hiện hành còn nguyên
          it.l2 = lEnd;
          it.label = { text: name, pos: 'right', priority: PRI.htfLevel, weight: 700, edgeText: name + ' ' + fp(e.price, d) };
          segments.push(it);
        } else {   // mức hiện hành đã bị lấy: liền tới nến lấy, rồi chấm mờ tới con trỏ (vẫn là mức tham chiếu của kỳ)
          it.l2 = logicalOf(taken);
          segments.push(it);
          segments.push({ id: 'lvl:' + e.event_id, l1: it.l2, l2: lEnd, p1: e.price, p2: e.price, color: col, width: 1.2, style: 'dotted',
            alpha: 0.5, autoscale: false,
            label: { text: name + ' · đã lấy', pos: 'right', priority: PRI.htfLevelOld, size: 10, alpha: 0.85 } });
        }
        counts.htfLevel++;
      });
    }
    if (H.forming) {
      var fm = formingAt(M, c, o.barOf);
      if (fm) {
        var la = logicalOf(fm.start) - 0.45, lb = logicalOf(fm.end) + 0.45, upC = fm.close >= fm.open, cc = upC ? COL.up : COL.down;
        var inset = (lb - la) * 0.3;
        boxes.push({ id: 'forming:H4', l1: la, l2: lb, p1: fm.low, p2: fm.high, fill: rgba(HCOL.H4, 0.05), border: rgba(HCOL.H4, 0.6),
          borderStyle: 'dashed', autoscale: false });
        boxes.push({ id: 'forming:H4', l1: la + inset, l2: lb - inset, p1: fm.open, p2: fm.close, minH: 2, fill: rgba(cc, 0.16),
          border: rgba(cc, 0.45), borderStyle: 'dashed', autoscale: false });
        segments.push({ id: 'forming:H4', noLine: true, l1: (la + lb) / 2, l2: (la + lb) / 2, p1: fm.high, p2: fm.high, color: HCOL.H4,
          autoscale: false, label: { text: 'H4 đang hình thành — chưa dùng', pos: 'mid', side: 'above', size: 10, priority: PRI.forming,
            fallback: '◌', alpha: 0.9 } });
        counts.forming = 1;
      }
    }
  }

  /** Lớp Chi tiết: mức được bảo vệ, dealing range (3 dải), FVG + CE, ITH/ITL/STH/STL (chấm + nhãn HH…), displacement. */
  function detailDrawing(M, sel, logicalOf, o, det, near, segments, boxes, counts) {
    var c = M.cursor, d = M.digits, Lc = logicalOf(c), localNear = o.localNear;
    var st = structureAt(M);
    counts.protected = 0; counts.range = 0; counts.fvgBox = 0; counts.swing = 0; counts.disp = 0;
    if (det.protected && st.prot) {
      var pr = st.prot, name = pr.side === 'high' ? 'Protected High' : 'Protected Low';
      var l0 = logicalOf(pr.swingBar), lEnd = logicalOf(c + o.protExt);
      var base = { id: 'prot:' + pr.id, l1: l0, p1: pr.price, p2: pr.price, color: DCOL.prot, width: 1.6, autoscale: 'near', near: near };
      if (pr.brokenAt === null) {
        segments.push(Object.assign({}, base, { l2: lEnd, style: 'solid',
          label: { text: name, pos: 'right', priority: PRI.prot, size: 11, edgeText: name + ' ' + fp(pr.price, d) } }));
      } else {
        var lb = logicalOf(pr.brokenAt);
        segments.push(Object.assign({}, base, { l2: lb, style: 'solid' }));
        segments.push(Object.assign({}, base, { l1: lb, l2: lEnd, color: DCOL.broken, style: 'dashed',
          label: { text: name + ' · broken', pos: 'right', priority: PRI.prot, size: 11, color: DCOL.broken,
            edgeText: name + ' ' + fp(pr.price, d) + ' · broken' } }));
      }
      counts.protected = 1;
    }
    if (det.range && st.range && st.range.hi > st.range.lo) {
      var r = st.range, hgt = r.hi - r.lo, ls = logicalOf(r.start) - 0.45, le = Lc + 0.45;
      [['premium', 'Premium', r.hi - 0.05 * hgt, r.hi], ['eq', 'EQ', r.lo + 0.475 * hgt, r.lo + 0.525 * hgt],
        ['discount', 'Discount', r.lo, r.lo + 0.05 * hgt]].forEach(function (b) {
        var id = 'range:' + r.id + ':' + b[0];
        boxes.push({ id: id, l1: ls, l2: le, p1: b[2], p2: b[3], fill: rgba(DCOL.range, 0.14), minH: 2, autoscale: 'near', near: near });
        var m = (b[2] + b[3]) / 2;
        // chữ ở đầu TRÁI dải (sau nến mốc), trượt dọc dải khi bị chiếm — không tranh mép phải với nhãn BSL/SSL
        segments.push({ id: id, noLine: true, l1: ls, l2: le, p1: m, p2: m, color: DCOL.range, autoscale: false,
          label: { text: b[1], pos: 'start', at: logicalOf(r.start) + 0.6, priority: PRI.range, size: 10, strict: true } });
      });
      counts.range = 1;
    }
    if (det.fvg) {
      // FVG do chính nến displacement của shift: đã vẽ cùng shift (lớp Shift) — không vẽ lại.
      var skip = {};
      if (o.shift !== false) sel.shifts.forEach(function (e) { var fv = M.shiftFvg[e.event_id]; if (fv && fv.details) skip[fv.details.fvg] = 1; });
      sel.fvgs.forEach(function (e) {
        if (skip[e.event_id]) return;
        var x = e.details || {}, up = e.structure_type === 'FVG_UP', col = up ? COL.up : COL.down;
        if (!finite(x.lo) || !finite(x.hi)) return;
        var filled = M.fvgFilled[e.event_id], touched = M.fvgTouched[e.event_id];
        var l1 = logicalOf(finite(x.nen_giua) ? x.nen_giua : e.event_bar_index) - 0.45;
        var l2 = filled ? logicalOf(filled.event_bar_index) + 0.45 : logicalOf(c + o.ext);
        var f = o.history && filled ? fade(o, c - filled.event_bar_index) : 1;
        var id = 'fvg:' + e.event_id, mid = (x.lo + x.hi) / 2;
        boxes.push({ id: id, l1: l1, l2: l2, p1: x.lo, p2: x.hi, fill: rgba(col, filled ? 0.06 : 0.13),
          border: rgba(col, filled ? 0.45 : 0.7), borderStyle: filled ? 'dotted' : (touched ? 'dashed' : 'solid'),
          alpha: f, autoscale: 'near', near: o.history ? localNear(e.confirmed_bar_index) : near });
        var ce = { id: id, l1: l1, l2: l2, p1: mid, p2: mid, color: col, width: 1, style: 'dashed', alpha: 0.5 * f, autoscale: false };
        // chữ trong hộp ngay sau nến 3 của FVG (FVG còn mở: chưa nến nào lấp vào đó), trượt dọc CE khi bị chiếm
        if (!filled) {
          ce.label = { text: 'FVG', pos: 'start', at: logicalOf(finite(x.nen_3) ? x.nen_3 : e.confirmed_bar_index) + 0.6,
            priority: PRI.fvg, size: 10, alpha: 0.9, strict: true };
        }
        segments.push(ce);
        counts.fvgBox++;
      });
    }
    if (det.ith || det.sth) {
      M.swings.forEach(function (e) {
        var lvl = swingLevel(e.structure_type);
        if (lvl === 3 || (lvl === 2 && !det.ith) || (lvl === 1 && !det.sth)) return;
        var high = e.structure_type.indexOf('HIGH') !== -1, x = e.details || {};
        var col = lvl === 2 ? (high ? DCOL.ith : DCOL.itl) : DCOL.sth;
        var l = logicalOf(e.event_bar_index);
        var it = { id: 'swing:' + e.event_id, noLine: true, l1: l, l2: l, p1: e.price, p2: e.price, color: col, autoscale: false,
          dot: { r: lvl === 2 ? 2.6 : 1.7, color: col, alpha: lvl === 2 ? 0.95 : 0.8 } };
        if (lvl === 2 && det.labels && x.nhan) {
          it.label = { text: x.nhan, pos: 'mid', side: high ? 'above' : 'below', strict: true, size: 10, bg: false, priority: PRI.swing, color: col };
        }
        segments.push(it);
        counts.swing++;
      });
    }
    if (det.disp && typeof o.barOf === 'function') {
      // quầng nhạt sau cả cây nến (rộng hơn thân, cao hơn râu 0.15 ATR) — dưới nến, không che nến
      var padD = finite(atrAt(M, c)) ? 0.15 * atrAt(M, c) : 0;
      M.disps.forEach(function (e) {
        var b = o.barOf(e.event_bar_index);
        if (!b) return;
        var l = logicalOf(e.event_bar_index), col = e.structure_type === 'DISPLACEMENT_UP' ? COL.up : COL.down;
        boxes.push({ id: 'disp:' + e.event_id, l1: l - 0.55, l2: l + 0.55, p1: b.low - padD, p2: b.high + padD, fill: rgba(col, 0.26), autoscale: false });
        counts.disp++;
      });
    }
  }

  /** Dải order flow: một mục / nến (timeline tới con trỏ); chữ ở nến đầu đoạn theo lý do. Kết quả cũ → rỗng. */
  function bandBars(M, logicalOf) {
    var out = [];
    M.tlList.forEach(function (p) {
      if (!hasOwn(p, 'order_flow')) return;
      var k = ofKey(p.order_flow), since = finite(p.order_flow_since) ? p.order_flow_since : null;
      var start = (since !== null && M.tl[since]) || p;
      var reason = start.order_flow_reason || p.order_flow_reason;
      out.push({
        l: logicalOf(p.bar_index), key: k + '|' + since, color: OF_COLORS[k],
        text: k === 'null' ? 'chưa có' : (OF_TEXT[reason] || ''),
        textColor: k === 'null' ? '#9aa7b4' : '#f1f5f8',
        id: 'of:' + (since === null ? 'none' : since) + ':' + k
      });
    });
    return out;
  }

  // ------------------------------------------------------------------ chữ: dòng trạng thái + tooltip

  /** Vì sao order flow có giá trị hiện tại (đọc ORDER_FLOW_* ở nến bắt đầu + sự kiện kích hoạt). */
  function ofWhy(M, p) {
    var d = M.digits, reason = p.order_flow_reason, oe = M.ofAt[p.order_flow_since];
    var ref = oe && oe.reference_event_id ? M.ev[oe.reference_event_id] : null;
    if (reason === 'hai_chieu_cung_nen') return 'run/' + M.flip + ' hai chiều cùng nến';
    if (reason === 'ob_hong' && ref) {                       // lõi 0.10.0: OB giữ order flow hỏng
      var ox = ref.details || {};
      return 'OB ' + (ox.chieu_ob === 'down' ? 'giảm' : 'tăng') + ' ' + fp(ox.lo, d) + '–' + fp(ox.hi, d) + ' hỏng (close ' + fp(ox.close, d) + ')';
    }
    if (ref && /^LIQ_RUN_/.test(ref.structure_type)) {
      var x = ref.details || {};
      var s = 'run ' + (x.phia || '') + ' ' + fp(x.muc, d);
      if (reason === 'run_nguoc_chieu') s += ' ngược chiều, đang ' + ((oe.details || {}).tu_vi || '');
      return s;
    }
    if (ref && /^SHIFT_/.test(ref.structure_type)) {
      return (ref.structure_type === 'SHIFT_UP' ? 'shift tăng: quét SSL ' : 'shift giảm: quét BSL ') +
        fp((ref.details || {}).muc_bi_quet, d);
    }
    if (ref && /^MSS_/.test(ref.structure_type)) {
      var mx = ref.details || {}, mu = ref.structure_type === 'MSS_UP';
      return (mu ? 'MSS tăng: quét SSL ' : 'MSS giảm: quét BSL ') + fp(mx.muc_bi_quet, d) + ', phá ' + (mx.moc_pha_ten || '') + ' ' +
        fp(mx.moc_pha, d);
    }
    return OF_REASON[reason] || reason || '';
  }

  function zoneText(M, h, side, level, id, close, atr) {
    if (!finite(level)) return null;
    var s = M.pools[id] ? poolAt(M.pools[id], h) : null;
    var name = s ? poolName(s) : side;
    var dist = finite(close) && finite(atr) && atr > 0
      ? ' (cách ' + ((side === 'BSL' ? level - close : close - level) / atr).toFixed(1) + ' ATR)' : '';
    return { name: name, price: fp(level, M.digits), txt: name + ' ' + fp(level, M.digits) + dist };
  }

  /** Dòng trạng thái ở nến h (≤ con trỏ). close: close của nến h (để tính khoảng cách theo ATR). */
  function statusAt(M, h, close) {
    var p = M.tl[h];
    if (!p) return null;
    var d = M.digits, hasOF = hasOwn(p, 'order_flow'), k = ofKey(p.order_flow);
    var res = { bar: h, hasOF: hasOF, key: k, word: OF_WORD[k], since: null, sinceBar: null, why: '', near: '', change: '', pending: '' };
    if (hasOF && finite(p.order_flow_since)) {
      res.sinceBar = p.order_flow_since;
      var tp = M.tl[p.order_flow_since];
      res.since = tp ? fmtShort(tp.time) : '#' + p.order_flow_since;
      res.why = ofWhy(M, p);
    }
    var zb = zoneText(M, h, 'BSL', p.liq_above, p.liq_above_id, close, p.atr);
    var zs = zoneText(M, h, 'SSL', p.liq_below, p.liq_below_id, close, p.atr);
    if (!hasOwn(p, 'liq_above')) {
      res.near = 'Kết quả giai đoạn 1 — chưa có vùng thanh khoản';
    } else if (hasOF && k === '1') {
      res.near = 'Vùng trên gần nhất: ' + (zb ? zb.txt : 'không còn BSL nguyên');
      res.change = 'Đổi khi: run ' + (zs ? zs.name + ' ' + zs.price : 'SSL') + ' → chưa rõ · ' + M.flip + ' giảm → giảm';
    } else if (hasOF && k === '-1') {
      res.near = 'Vùng dưới gần nhất: ' + (zs ? zs.txt : 'không còn SSL nguyên');
      res.change = 'Đổi khi: run ' + (zb ? zb.name + ' ' + zb.price : 'BSL') + ' → chưa rõ · ' + M.flip + ' tăng → tăng';
    } else {
      res.near = 'Vùng gần nhất: trên ' + (zb ? zb.txt : '— hết BSL nguyên') + ' · dưới ' + (zs ? zs.txt : '— hết SSL nguyên');
      if (hasOF) {
        res.change = k === '0' ? 'Đổi khi: run/' + M.flip + ' kế tiếp đặt chiều (lên → tăng, xuống → giảm)'
          : 'Đổi khi: run/' + M.flip + ' đầu tiên đặt chiều';
      }
    }
    // Đang chờ sweep/run ở h, gom theo nến lấy: «SSL 2026.69, SSL 2027.15 bị lấy lúc 05:45, ≤ 1 nến nữa …».
    var byTake = {}, takes = [];
    statesAt(M, h).forEach(function (s) {
      if (s.state !== 'pending') return;
      var k = s.pool.taken;
      if (!byTake[k]) { byTake[k] = []; takes.push(k); }
      byTake[k].push(s);
    });
    if (takes.length) {
      res.pending = 'Đang chờ: ' + takes.sort(function (a, b) { return a - b; }).map(function (k) {
        var tp2 = M.tl[k], left = M.W !== null ? k + M.W - h : null;
        return byTake[k].map(function (s) { return poolName(s) + ' ' + fp(s.level, d); }).join(', ') +
          ' bị lấy lúc ' + (tp2 ? fmtHM(tp2.time) : '#' + k) + (left !== null ? ', ≤ ' + left + ' nến nữa biết sweep hay run' : '');
      }).join('; ');
    }
    res.htf = htfStatusAt(M, h);
    return res;
  }

  /** Nến bắt đầu giá trị hiện tại của các cột `keys` ở nến h (lùi timeline tối đa `lim` nến). */
  function sinceOf(M, h, keys, lim) {
    var p = M.tl[h], i = h, stop = h - (lim || 5000);
    while (i - 1 >= stop) {
      var q = M.tl[i - 1];
      if (!q || keys.some(function (k) { return q[k] !== p[k]; })) break;
      i--;
    }
    return i;
  }

  /** Vùng còn nguyên ở nến h có đúng mức + tầng (đích DOL của lõi: dol_target, dol_tier) — tên + nguồn. */
  function poolByLevel(M, h, level, tier) {
    if (!finite(level)) return null;
    for (var i = 0; i < M.poolList.length; i++) {
      var p = M.poolList[i];
      if (p.tier !== tier) continue;
      var s = poolAt(p, h);
      if (s && s.level === level && s.state === 'intact') return s;
    }
    return null;
  }

  /** Ngữ cảnh khung lớn ở nến h cho dòng trạng thái — đọc cột timeline (trạng thái SAU nến h, chỉ nến khung lớn đã chốt):
   * «H4 ↑ · discount 31% · pd ↓ H1 · DOL ↑ BSL H1 2341.00 (4.2 ATR)»; title = câu đầy đủ tiếng Việt. Kết quả trước 0.4.0
   * (không có cột htf_*) → null. */
  function htfStatusAt(M, h) {
    var p = M.tl[h];
    if (!p || !hasOwn(p, 'htf_H4_order')) return null;
    var d = M.digits, parts = [], why = [];
    var o4 = ofKey(p.htf_H4_order), o1 = hasOwn(p, 'htf_H1_order') ? ofKey(p.htf_H1_order) : null;
    var s4 = sinceOf(M, h, ['htf_H4_order']);
    parts.push('H4 ' + ARROW[o4]);
    why.push('thứ tự H4 ' + DIR_WORD[o4] + (o4 !== 'null' && M.tl[s4] ? ' (từ ' + fmtShort(M.tl[s4].time) + ')' : '') +
      (o1 !== null ? ', H1 ' + DIR_WORD[o1] : ''));
    if (p.htf_H4_zone && finite(p.htf_H4_range_pos)) {
      var pct = Math.round(p.htf_H4_range_pos * 100);
      parts.push(p.htf_H4_zone + ' ' + pct + '%');
      why.push('giá ở ' + p.htf_H4_zone + ' ' + pct + '% của dealing range H4 ' + fp(p.htf_H4_dealing_lo, d) + '–' +
        fp(p.htf_H4_dealing_hi, d) + (pct < 0 || pct > 100 ? ' (đã ra ngoài range từ lần chốt H4 gần nhất)' : ''));
    }
    var pk = ofKey(p.pd_bias);
    if (pk === 'null') {
      parts.push('pd –');
      why.push('pd_bias chưa có (chưa FVG khung lớn nào được respect / disrespect)');
    } else {
      var sp = sinceOf(M, h, ['pd_bias', 'pd_bias_tf']);
      parts.push('pd ' + ARROW[pk] + (p.pd_bias_tf ? ' ' + p.pd_bias_tf : ''));
      why.push('pd_bias ' + (pk === '0' ? 'mâu thuẫn trong cùng nến' : DIR_WORD[pk]) + (p.pd_bias_tf ? ' (FVG ' + p.pd_bias_tf + ')' : '') +
        (M.tl[sp] ? ' từ ' + fmtShort(M.tl[sp].time) : ''));
    }
    if (p.dol_side === 1 || p.dol_side === -1) {
      var tg = poolByLevel(M, h, p.dol_target, p.dol_tier);
      var tname = tg ? poolName(tg) : (p.dol_tier || '');
      var dist = finite(p.dol_dist_atr) ? ' (' + p.dol_dist_atr.toFixed(1) + ' ATR)' : '';
      parts.push('DOL ' + ARROW[String(p.dol_side)] + ' ' + tname + ' ' + fp(p.dol_target, d) + dist);
      why.push('DOL ' + (p.dol_side === 1 ? 'lên' : 'xuống') + ': đích ' + tname + ' ' + fp(p.dol_target, d) +
        (finite(p.dol_dist_atr) ? ', cách ' + p.dol_dist_atr.toFixed(1) + ' ATR' : ''));
    } else {
      parts.push('DOL –');
      why.push('chưa có DOL (chưa có shift, hoặc shift gần nhất không có vùng tầng ≥ H1 phía đó, hoặc đích đã bị lấy)');
    }
    return { text: parts.join(' · '), title: 'Khung lớn (chỉ nến đã chốt): ' + why.join('; ') + '.' };
  }

  function sourceText(M, p, c) {
    var src = p.sources.filter(function (s) { return s.known <= c; });
    var pre = runTier(p.tier) ? '' : (TIER_VI[p.tier] || 'tầng ' + p.tier) + ' — ';
    if (!src.length) return pre + 'biết lúc #' + p.known;
    function one(s) {
      var tp = M.tl[s.bar], x = (s.ev && s.ev.details) || {}, extra = '';
      if (/^HTF_SWING_/.test(s.type) && x.mo_nen_htf) extra = '; nến ' + (x.khung || '') + ' mở ' + fmtIsoShort(x.mo_nen_htf);
      else if (/^HTF_PERIOD_/.test(s.type) && x.mo_ky) extra = '; kỳ ' + fmtIsoShort(x.mo_ky) + ' → ' + fmtIsoShort(x.period_end);
      return s.kind + ' ' + (tp ? fmtShort(tp.time) + ' ' : '') + '(#' + s.bar + extra + ')';
    }
    function known(s) {
      var x = (s.ev && s.ev.details) || {}, k = '#' + s.known;
      if (x.known_at && /^HTF_/.test(s.type || '')) {
        k += ' (' + (/^HTF_PERIOD_/.test(s.type) ? 'kỳ chốt ' : 'nến ' + (x.khung || '') + ' chốt ') + fmtIsoShort(x.known_at) +
          (x.chot_muon ? ', chốt muộn' : '') + ')';
      }
      return k;
    }
    if (src.length === 1) return pre + 'từ ' + one(src[0]) + ', biết lúc ' + known(src[0]);
    return pre + 'gộp ' + src.length + ' ' + (p.side === 'BSL' ? 'đỉnh' : 'đáy') + ': ' + src.map(function (s) {
      return one(s) + (finite(s.price) ? ' ' + fp(s.price, M.digits) : '');
    }).join(', ') + ' — biết lúc ' + src.map(known).join(', ');
  }

  /** Dòng tooltip của một vùng ở con trỏ: {head, body, more}. */
  function poolLine(M, s) {
    var p = s.pool, d = M.digits, name = poolName(s), price = fp(s.level, d), c = M.cursor;
    var src = sourceText(M, p, c);
    var atrC = atrAt(M, c);
    if (s.state === 'intact') {
      return { head: name + ' ' + price, body: src + ' · còn nguyên', more: 'Chưa bị lấy (giá chưa xuyên mức ≥ ngưỡng lấy).' +
        (finite(atrC) ? ' ATR hiện tại ' + fp(atrC, d) + '.' : '') +
        (runTier(p.tier) ? '' : ' Vùng khung lớn: dựng từ nến ' + (PERIOD_NAME[p.tier] ? 'ngày / tuần' : p.tier) +
          ' đã chốt, hiệu lực từ nến sau lúc biết; vòng đời (lấy → sweep / run) đo bằng nến khung chạy.') };
    }
    var tk = '#' + p.taken;
    if (s.state === 'sweep') {
      var depth = finite(p.extreme) && finite(p.atrLocked) && p.atrLocked > 0
        ? Math.abs(p.extreme - s.level) / p.atrLocked : p.pen;
      return {
        head: 'Sweep ' + name + ' ' + price,
        body: 'lấy ở ' + tk + ', close quay lại ' + (p.sweepBars === 0 ? 'ngay nến lấy' : 'ở #' + p.resolved +
          (finite(p.sweepBars) ? ' (sau ' + p.sweepBars + ' nến)' : '')) +
          (finite(depth) ? ', quét sâu ' + depth.toFixed(2) + ' ATR' : ''),
        more: 'Vùng ' + src + '.'
      };
    }
    if (s.state === 'run') {
      return {
        head: 'Run ' + name + ' ' + price,
        body: 'lấy ở ' + tk + ', close không quay lại trong ' + (M.W !== null ? M.W : '?') + ' nến → biết lúc #' + p.resolved +
          (finite(p.pen) ? ', xuyên ' + p.pen.toFixed(2) + ' ATR' : ''),
        more: 'Vùng ' + src + '.'
      };
    }
    if (s.state === 'unresolved') {
      return {
        head: 'Chưa rõ ' + name + ' ' + price,
        body: 'lấy ở ' + tk + ', gặp khoảng trống ' + (GAP_VI[p.gapKind] || p.gapKind || '') + ' trước khi rõ sweep hay run (#' + p.resolved + ')',
        more: 'Vùng ' + src + '.'
      };
    }
    var tp = M.tl[p.taken], left = M.W !== null ? p.taken + M.W - c : p.pendingLeft;
    return {
      head: name + ' ' + price + ' bị lấy · chờ',
      body: 'lấy ở ' + tk + (tp ? ' (' + fmtHM(tp.time) + ')' : '') + ', cần close ' + (s.side === 'BSL' ? '<' : '>') + ' ' + price +
        (finite(left) ? ' trong ≤ ' + left + ' nến nữa' : '') + ' để thành sweep; hết cửa sổ → run',
      more: 'Vùng ' + src + '.'
    };
  }

  function mssLines(M, e) {
    var x = e.details || {}, d = M.digits, up = e.structure_type === 'MSS_UP', ch = x.chan || {};
    var main = (x.swept || []).filter(function (w) { return w.muc === x.muc_bi_quet; })[0] || (x.swept || [])[0] || {};
    var out = [{
      head: 'MSS ' + (up ? 'tăng ↑' : 'giảm ↓') + ' — market structure shift',
      body: 'quét ' + (up ? 'SSL ' : 'BSL ') + fp(x.muc_bi_quet, d) + ' (lấy #' + main.nen_lay + ', sweep #' + x.nen_sweep + ') → close ' +
        (up ? 'vượt ' : 'phá ') + (x.moc_pha_ten || '') + ' ' + fp(x.moc_pha, d) + ' (đỉnh/đáy ngắn hạn #' + x.nen_moc_pha +
        ' trước cú chạy) ở #' + e.event_bar_index + (finite(x.so_nen_tu_sweep) ? ' (sau ' + x.so_nen_tu_sweep + ' nến)' : '') +
        (x.significant ? ' — phá luôn ' + (up ? 'ITH ' : 'ITL ') + fp(x.moc_significant, d) + ' (significant)' : ''),
      more: 'Đoạn displacement ' + (finite(ch.so_nen) ? ch.so_nen : '—') + ' nến từ ' + fp(ch.cuc_tri, d) + ': ' +
        (finite(ch.bien_do_atr) ? ch.bien_do_atr.toFixed(2) : '—') + ' ATR (cần ≥ ' + ch.nguong_atr + ') · ' + (x.swept || []).length +
        ' vùng bị quét' + (x.fvg_trong_chan ? ' · có FVG trong đoạn' : '') + '. Chưa biết sẽ tiếp diễn hay thất bại.'
    }];
    var fv = M.shiftFvg[e.event_id];
    if (fv) out.push(fvgLine(M, fv));
    return out;
  }

  function shiftLines(M, e) {
    if (isMss(e)) return mssLines(M, e);
    var x = e.details || {}, d = M.digits, up = e.structure_type === 'SHIFT_UP';
    var main = (x.swept || []).filter(function (w) { return w.muc === x.muc_bi_quet; })[0] || (x.swept || [])[0] || {};
    var dp = x.displacement || {};
    var out = [{
      head: 'Shift ' + (up ? 'tăng ↑' : 'giảm ↓'),
      body: 'quét ' + (up ? 'SSL ' : 'BSL ') + fp(x.muc_bi_quet, d) + ' (lấy #' + main.nen_lay + ', sweep #' + x.nen_sweep + ') → displacement ' +
        (up ? 'tăng' : 'giảm') + ' ở #' + e.event_bar_index + (finite(x.so_nen_tu_sweep) ? ' (sau ' + x.so_nen_tu_sweep + ' nến)' : '') +
        ', close ' + fp(e.price, d) + (up ? ' > ' : ' < ') + fp(x.muc_bi_quet, d),
      more: 'Biên độ ' + (finite(dp.bien_do_atr) ? dp.bien_do_atr.toFixed(2) : '—') + ' ATR · thân ' +
        (finite(dp.than_ty_le) ? Math.round(dp.than_ty_le * 100) : '—') + '% · ' + (x.swept || []).length + ' vùng bị quét. ' +
        'Chưa biết sẽ tiếp diễn hay thất bại.'
    }];
    var fv = M.shiftFvg[e.event_id];
    if (fv) out.push(fvgLine(M, fv));
    return out;
  }

  function fvgLine(M, fv) {
    var x = fv.details || {}, d = M.digits, up = /_UP$/.test(fv.structure_type), mss = /^MSS_/.test(fv.structure_type);
    var filled = M.fvgFilled[x.fvg];
    return {
      head: 'FVG ' + (up ? 'tăng' : 'giảm') + ' ' + fp(x.lo, d) + '–' + fp(x.hi, d),
      body: (mss ? 'do chính nến phá #' + x.nen_pha + ' của MSS' : 'do chính nến displacement #' + x.nen_displacement + ' của shift') +
        ' tạo ra (biết lúc #' + fv.confirmed_bar_index + ') · ' +
        (filled ? 'đã lấp ở #' + filled.event_bar_index : 'còn mở'),
      more: ''
    };
  }

  function ofLines(M, since, key) {
    var s = since === 'none' ? null : Number(since), k = key;
    var start = s !== null ? M.tl[s] : null, end = null, n = 0;
    M.tlList.forEach(function (p) {
      var ps = finite(p.order_flow_since) ? p.order_flow_since : null;
      if (ps === s && ofKey(p.order_flow) === k && hasOwn(p, 'order_flow')) { end = p.bar_index; n++; }
    });
    var why = start ? ofWhy(M, start) : '';
    return [{
      head: 'Order flow ' + OF_WORD[k],
      body: (s !== null ? 'từ #' + s + (start ? ' (' + fmtShort(start.time) + ')' : '') : 'từ đầu lần chạy') +
        (end !== null ? ' tới #' + end + ' (' + n + ' nến)' : '') + (why ? ' · ' + why : ''),
      more: k === 'null' ? 'Chưa có run hay ' + M.flip + ' nào kể từ đầu lần chạy.'
        : 'Run hoặc ' + M.flip + ' đặt chiều; run phía ngược → chưa rõ; ' + M.flip + ' lật thẳng' +
          (M.flip === 'MSS' ? '; OB của MSS gần nhất hỏng → chưa rõ' : '') + '. Mô tả, không phải dự báo.'
    }];
  }

  var ORDER_VI = { '1': 'tăng (HH + HL)', '-1': 'giảm (LH + LL)', '0': 'lẫn lộn', 'null': 'chưa đủ swing' };
  var DIR_VI = { up: 'tăng', down: 'giảm' };

  function rawFvgLine(M, e) {
    var x = e.details || {}, d = M.digits, up = e.structure_type === 'FVG_UP';
    var filled = M.fvgFilled[e.event_id], touched = M.fvgTouched[e.event_id];
    return {
      head: 'FVG ' + (up ? 'tăng' : 'giảm') + ' ' + fp(x.lo, d) + '–' + fp(x.hi, d),
      body: 'ba nến #' + x.nen_1 + '–#' + x.nen_3 + ', biết lúc #' + e.confirmed_bar_index +
        (finite(x.kich_thuoc_atr) ? ' · ' + x.kich_thuoc_atr.toFixed(2) + ' ATR' : '') + ' · ' +
        (filled ? 'đã lấp ở #' + filled.event_bar_index : (touched ? 'đã chạm ở #' + touched.event_bar_index + ', chưa lấp' : 'còn mở')),
      more: (x.from_displacement ? 'Nến giữa là displacement cùng chiều. ' : '') + 'Đường nét đứt = CE (giữa FVG).'
    };
  }

  function protLines(M) {
    var pr = structureAt(M).prot, d = M.digits;
    if (!pr) return null;
    var low = pr.side === 'low';
    return [{
      head: (low ? 'Protected Low ' : 'Protected High ') + fp(pr.price, d),
      body: 'mức được bảo vệ — ' + (low ? 'đáy' : 'đỉnh') + ' cấu trúc ở #' + pr.swingBar + ', là mức được bảo vệ từ #' + pr.since +
        ' (thứ tự ' + ORDER_VI[String(pr.order === undefined ? null : pr.order)] + ')' +
        (pr.brokenAt !== null ? ' · close đã vượt ở #' + pr.brokenAt : ' · chưa bị close vượt'),
      more: 'Thứ tự tăng → đáy gần nhất; giảm → đỉnh gần nhất. Close vượt chỉ là cờ, không phải BOS, không đổi thứ tự.'
    }];
  }

  function rangeLines(M, part) {
    var r = structureAt(M).range, d = M.digits;
    if (!r) return null;
    var name = { premium: 'Premium', eq: 'EQ', discount: 'Discount' }[part] || part;
    var what = { premium: '5% trên cùng', eq: '47.5–52.5% (giữa)', discount: '5% dưới cùng' }[part] || '';
    var zone = { premium: 'premium (trên EQ)', discount: 'discount (dưới EQ)', eq: 'đúng EQ' }[r.zone] || '—';
    return [{
      head: name + ' — dealing range ' + fp(r.lo, d) + '–' + fp(r.hi, d),
      body: what + ' của range từ đỉnh #' + r.hiBar + ' và đáy #' + r.loBar + ' (mở rộng theo giá), EQ ' + fp(r.eq, d) +
        ' · giá đang ở ' + zone + (r.pos !== null ? ', vị trí ' + Math.round(r.pos * 100) + '%' : ''),
      more: 'Chỉ là vị trí trong range, không phải tín hiệu.'
    }];
  }

  function swingLine(M, e) {
    var x = e.details || {}, d = M.digits, kind = SWING_KIND[e.structure_type] || e.structure_type;
    var cmp = x.nhan ? x.nhan + ' so với ' + fp(x.gia_truoc, d) + ' (chênh ' + (x.chenh_lech >= 0 ? '+' : '') + fp(x.chenh_lech, d) +
      ', dung sai ±' + fp(x.dung_sai, d) + ')' : (x.cap_cau_truc ? 'chưa so — ' + (x.ly_do_chua_so || '') : '');
    return {
      head: kind + ' ' + fp(e.price, d),
      body: 'nến #' + e.event_bar_index + ', biết lúc #' + e.confirmed_bar_index + (cmp ? ' · ' + cmp : ''),
      more: x.cap_cau_truc ? 'Thứ tự sau swing: ' + (x.order_sau_vi || ORDER_VI[String(x.order_sau)]) : (x.quy_tac || '')
    };
  }

  function dispLine(M, e) {
    var x = e.details || {};
    return {
      head: 'Displacement ' + (e.structure_type === 'DISPLACEMENT_UP' ? 'tăng' : 'giảm'),
      body: 'nến #' + e.event_bar_index + ' · biên độ ' + (finite(x.bien_do_atr) ? x.bien_do_atr.toFixed(2) : '—') + ' ATR · thân ' +
        (finite(x.than_ty_le) ? Math.round(x.than_ty_le * 100) : '—') + '% biên độ',
      more: x.nguong_vi || ''
    };
  }

  // ------------------------------------------------------------------ khung lớn: tooltip, giải thích

  function pdWord(t) { return /^PD_RESPECT/.test(t) ? 'respect' : 'disrespect'; }
  function fvgDirWord(t) { return /_UP$/.test(t) ? 'tăng' : 'giảm'; }
  function levelState(M, e) {
    var x = e.details || {}, v = x.vung_thanh_khoan || {};
    if (v.trang_thai === 'khong_tao') return 'không thành vùng — ' + (v.ly_do_vi || 'đã bị lấy trước khi biết');
    var s = v.vung && M.pools[v.vung] ? poolAt(M.pools[v.vung], M.cursor) : null;
    if (!s) return '—';
    if (s.state === 'intact') return 'còn nguyên';
    return 'đã bị lấy ở #' + s.pool.taken + (OUTCOME[s.state] ? ' (' + (s.state === 'unresolved' ? 'chưa rõ' : s.state) + ')' : ' (chờ sweep / run)');
  }

  function htfSwingLine(M, e) {
    var x = e.details || {}, d = M.digits, f = frameOf(e), high = e.structure_type === 'HTF_SWING_HIGH', tp = M.tl[e.event_bar_index];
    return {
      head: (x.ten || (high ? 'ITH' : 'ITL')) + ' ' + f + ' ' + fp(e.price, d) + (x.nhan ? ' (' + x.nhan + ')' : ''),
      body: (high ? 'đỉnh' : 'đáy') + ' của nến ' + f + ' mở ' + fmtIsoShort(x.mo_nen_htf) + ', chạm ở #' + e.event_bar_index +
        (tp ? ' (' + fmtShort(tp.time) + ')' : '') + ', biết lúc #' + e.confirmed_bar_index +
        (x.known_at ? ' (nến ' + f + ' chốt ' + fmtIsoShort(x.known_at) + (x.chot_muon ? ', chốt muộn' : '') + ')' : '') +
        (x.nhan && finite(x.gia_truoc) ? ' · ' + x.nhan + ' so với ' + fp(x.gia_truoc, d) : ''),
      more: 'Cấu trúc khung lớn chỉ tính trên nến ' + f + ' đã chốt (ITH/ITL = đỉnh/đáy cấp 2 của nến ' + f + '). Thứ tự ' + f +
        ' sau swing: ' + (x.order_sau_vi || DIR_WORD[ofKey(x.order_sau)]) + '.'
    };
  }

  function htfFvgLine(M, e, isSrc) {
    var x = e.details || {}, d = M.digits, f = frameOf(e), end = M.htfFvgEnd[e.event_id], st;
    if (end) {
      var y = end.details || {};
      st = pdWord(end.structure_type) + ' ở #' + end.event_bar_index + ' (close ' + fp(y.close, d) + (y.quy_tac_vi ? '; ' + y.quy_tac_vi : '') +
        ') → hàm ý ' + (y.chieu_ham_y > 0 ? 'tăng' : 'giảm');
    } else {
      st = 'còn mở — chưa respect / disrespect';
    }
    return {
      head: 'FVG ' + f + ' ' + fvgDirWord(e.structure_type) + ' ' + fp(x.lo, d) + '–' + fp(x.hi, d),
      body: 'ba nến ' + f + ' (nến giữa mở ' + fmtIsoShort(x.mo_nen_giua) + '), biết lúc #' + e.confirmed_bar_index +
        (x.known_at ? ' (nến ' + f + ' thứ 3 chốt ' + fmtIsoShort(x.known_at) + ')' : '') + ' · ' + st,
      more: 'Vùng PD array khung lớn, hiệu lực từ nến sau lúc biết; kết quả đầu tiên (respect / disrespect) đặt pd_bias.' +
        (x.from_displacement ? ' Nến giữa là displacement.' : '') + (isSrc ? ' Đây là FVG đặt pd_bias hiện tại.' : '') +
        ' Mô tả, không phải tín hiệu.'
    };
  }

  function htfRangeLines(M) {
    var r = htfRangeAt(M), d = M.digits;
    if (!r) return null;
    var a = r.hiAnchor, b = r.loAnchor;
    return [{
      head: 'Dealing range H4 ' + fp(r.lo, d) + '–' + fp(r.hi, d) + ' · EQ ' + fp(r.eq, d),
      body: (a && b ? 'từ ITH H4 #' + a.event_bar_index + ' và ITL H4 #' + b.event_bar_index + ', ' : '') +
        'mở rộng theo high/low nến H4 đã chốt' + (r.zone ? ' · giá (close) ở ' + r.zone + (r.pos !== null ? ' ' + Math.round(r.pos * 100) + '%' : '') : '') +
        ' · thứ tự H4 ' + DIR_WORD[ofKey(r.order)],
      more: 'Chỉ đổi khi nến H4 chốt (nến H4 đang hình thành không dùng). Vị trí trong range, không phải tín hiệu.'
    }];
  }

  function levelLines(M, e) {
    var x = e.details || {}, d = M.digits, tp = M.tl[e.event_bar_index], name = x.ten || srcKind(e.structure_type, x);
    return [{
      head: name + ' ' + fp(e.price, d),
      body: (x.khung === 'W' ? 'mức tuần' : 'mức ngày') + ' — ' + (/HIGH$/.test(e.structure_type) ? 'high' : 'low') + ' kỳ ' +
        fmtIsoShort(x.mo_ky) + ' → ' + fmtIsoShort(x.period_end) + ', đạt ở #' + e.event_bar_index + (tp ? ' (' + fmtShort(tp.time) + ')' : '') +
        ', biết lúc #' + e.confirmed_bar_index + (x.known_at ? ' (kỳ chốt ' + fmtIsoShort(x.known_at) + (x.chot_muon ? ', chốt muộn' : '') + ')' : '') +
        ' · ' + levelState(M, e),
      more: 'Ngày giao dịch bắt đầu 17:00 New York (mốc ny_1700); giờ hiển thị UTC. Mức là vùng thanh khoản tầng ' + (x.khung || 'D') +
        ' (lấy → sweep / run như mọi vùng).'
    }];
  }

  function formingLines(M, barOf) {
    var fm = formingAt(M, M.cursor, barOf), d = M.digits;
    if (!fm) return null;
    var t0 = M.tl[fm.start];
    return [{
      head: 'Nến H4 đang hình thành — chưa dùng',
      body: 'mở ' + (t0 ? fmtShort(t0.time) : '#' + fm.start) + ' → đóng ' + fmtShort(fm.periodEnd) + ' (UTC) · ' + fm.n + '/' + fm.expected +
        ' nến · O ' + fp(fm.open, d) + ' H ' + fp(fm.high, d) + ' L ' + fp(fm.low, d) + ' C ' + fp(fm.close, d),
      more: 'Chỉ để vẽ: thuật toán chỉ dùng nến H4 ĐÃ CHỐT; giá trị còn đổi tới khi nến chốt. ' +
        (fm.from === 'lõi' ? 'Số liệu khớp pending_state của lõi.' : 'Gộp từ nến khung chạy tới nến này (mốc 17:00 New York).')
    }];
  }

  /** Khung «Thuật toán đang làm gì»: một dòng mỗi thành phần khung lớn, đọc pending_state tại con trỏ (khung_lon, pd, dol).
   * extra.dolReached = DOL_REACHED gần nhất ≤ con trỏ (để nói «đích đã bị lấy»). → [{kind, text}] chữ thuần. */
  function htfExplain(ps, digits, extra) {
    var fl = flipOf(ps), flipName = fl.name;              // lõi 0.10.0: DOL đặt sau MSS
    var kl = (ps || {}).khung_lon, out = [], d = digits === undefined ? 2 : digits;
    if (!kl) return out;
    if (!kl.bat) {
      out.push({ kind: 'muted', text: 'Khung lớn: tắt (dataset lớn hơn H1 hoặc htf_list rỗng) — không có H1/H4, PDH/PDL, pd_bias, DOL.' });
      return out;
    }
    var ctx = kl.ngu_canh || {};
    ['H4', 'H1'].forEach(function (f) {
      var c = ctx[f], st = kl[f];
      if (!c || !st) return;   // khung không chạy (vd dataset H1 → không có H1)
      var dr = st.dealing_range || {};
      var t = 'Thứ tự ' + f + ': ';
      if (!c.ready || c.order === null || c.order === undefined) t += 'chưa có (khởi động — chưa đủ ITH/ITL ' + f + ' trên nến đã chốt)';
      else t += DIR_WORD[ofKey(c.order)] + (finite(c.order_age_bars) ? ' (' + c.order_age_bars + ' nến ' + f + ')' : '');
      if (c.zone && finite(c.range_pos)) {
        t += ', giá ở ' + c.zone + ' ' + Math.round(c.range_pos * 100) + '%' +
          (finite(dr.lo) && finite(dr.hi) ? ' (dealing range ' + f + ' ' + fp(dr.lo, d) + '–' + fp(dr.hi, d) + ')' : '');
      }
      if (finite(c.protected)) t += ', mức được bảo vệ ' + fp(c.protected, d) + (c.protected_broken ? ' (close ' + f + ' đã vượt — cờ)' : '');
      t += '. Nến ' + f + ' chốt gần nhất: ' + (finite(c.age_ltf_bars) ? (c.age_ltf_bars === 0 ? 'ở nến này' : c.age_ltf_bars + ' nến trước') : '—') + '.';
      out.push({ kind: 'state', text: t });
    });
    var pd = ps.pd || null;
    if (pd) {
      if (pd.pd_bias === null || pd.pd_bias === undefined) {
        out.push({ kind: 'state', text: 'pd_bias: chưa có (chưa FVG H1/H4 nào được respect / disrespect).' });
      } else {
        var src = (pd.su_kien || []).map(parseId).filter(Boolean).map(function (q) {
          return 'FVG ' + (q.sfx ? q.sfx.split('.')[0] + ' ' : '') + fvgDirWord(q.type) + ' bị ' + pdWord(q.type);
        }).join(' và ');
        var ago = finite(pd.so_nen) ? (pd.so_nen === 0 ? 'ở nến này' : pd.so_nen + ' nến trước') : '';
        out.push({ kind: 'state', text: 'pd_bias: ' + (pd.pd_bias_vi || DIR_WORD[ofKey(pd.pd_bias)]) +
          (src || ago ? ' (' + [src, ago].filter(Boolean).join(', ') + ')' : '') + '.' });
      }
    }
    var dl = ps.dol || null;
    if (dl) {
      var rc = extra && extra.dolReached;
      if (dl.side === 1 || dl.side === -1) {
        var v = dl.vung || {}, q0 = parseId((v.nguon || [])[0]);
        var nm = PERIOD_NAME[v.tang] ? PERIOD_NAME[v.tang][v.phia] : (v.phia || '') + (runTier(v.tang) ? '' : ' ' + v.tang);
        var from = q0 ? srcKind(q0.type, null, q0.sfx) : '';
        out.push({ kind: 'state', text: 'DOL: ' + (dl.side > 0 ? 'lên' : 'xuống') + ', đích ' + nm + ' ' + fp(dl.target, d) +
          (from && from !== nm ? ' — ' + from : '') + (finite(dl.dist_atr) ? ' (cách ' + dl.dist_atr.toFixed(1) + ' ATR)' : '') +
          '; đặt sau ' + flipName + ' ' + (dl.side > 0 ? 'tăng' : 'giảm') + ' ở nến #' + dl.tu_nen + (finite(dl.so_nen) ? ' (' + dl.so_nen + ' nến trước)' : '') + '.' });
      } else if (dl[fl.key]) {
        out.push({ kind: 'state', text: 'DOL: không có — ' + flipName + ' ở nến #' + dl.tu_nen + ' không còn vùng tầng ≥ ' +
          (dl.tang_toi_thieu || 'H1') +
          ' nguyên phía đó.' });
      } else if (rc) {
        var rx = rc.details || {};
        out.push({ kind: 'state', text: 'DOL: không có — đích ' + fp(rx.muc, d) + ' (' + (rx.tang || '') + ') đã bị lấy ở nến #' + rc.event_bar_index +
          '; chờ ' + flipName + ' kế tiếp đặt DOL mới.' });
      } else {
        out.push({ kind: 'state', text: 'DOL: chưa có (chưa có ' + flipName + ' nào đặt DOL).' });
      }
    }
    var lv = ctx.levels;
    if (lv) {
      var tk = function (v2) { return v2 === true ? 'đã lấy' : (v2 === false ? 'còn nguyên' : '—'); };
      var items = [['PDH', lv.pdh, lv.pdh_taken], ['PDL', lv.pdl, lv.pdl_taken], ['PWH', lv.pwh, lv.pwh_taken], ['PWL', lv.pwl, lv.pwl_taken]]
        .filter(function (r) { return finite(r[1]); }).map(function (r) { return r[0] + ' ' + fp(r[1], d) + ' (' + tk(r[2]) + ')'; });
      out.push({ kind: 'state', text: 'Mức theo kỳ: ' + (items.length ? items.join(' · ') : 'chưa có (kỳ đầu chưa chốt hoặc thiếu dữ liệu)') +
        '; giá mở ngày ' + fp(lv.day_open, d) + ', midnight open ' + fp(lv.midnight_open, d) + '.' });
    }
    var fm = kl.H4 && kl.H4.dang_hinh_thanh;
    if (fm) {
      out.push({ kind: 'muted', text: 'Nến H4 đang hình thành: ' + fm.n_bars + '/' + fm.expected_bars + ' nến (mở ' + fmtIsoShort(fm.mo) +
        ' → đóng ' + fmtIsoShort(fm.period_end) + ' UTC), O ' + fp(fm.open, d) + ' H ' + fp(fm.high, d) + ' L ' + fp(fm.low, d) + ' C ' +
        fp(fm.close, d) + ' — chỉ để vẽ, chưa dùng.' });
    } else if (kl.H4 && ctx.H4 && ctx.H4.age_ltf_bars === 0) {
      out.push({ kind: 'muted', text: 'Nến H4 vừa chốt ở nến này — ngữ cảnh H4 mới có hiệu lực từ nến sau.' });
    }
    return out;
  }

  /** Câu giải thích một sự kiện khung lớn / PD / DOL ở nến xác nhận (chữ thuần): {kind, text} | null. */
  function htfEventText(e, digits) {
    var t = e && e.structure_type, x = (e && e.details) || {}, d = digits === undefined ? 2 : digits, f = frameOf(e);
    if (t === 'HTF_SWING_HIGH' || t === 'HTF_SWING_LOW') {
      var v = x.vung_thanh_khoan || {}, hi = t === 'HTF_SWING_HIGH';
      var vtxt = v.trang_thai === 'khong_tao' ? 'không tạo vùng (' + (v.ly_do_vi || 'đã bị lấy trước khi biết') + ')'
        : (v.trang_thai === 'gop_eq' ? 'gộp EQ vào vùng ' : 'vùng ') + (hi ? 'BSL ' : 'SSL ') + f + ' ' + (v.vung || '') + ' ' + fp(v.muc_vung, d) +
          ', hiệu lực từ nến sau';
      return { kind: 'info', text: (x.ten || (hi ? 'ITH' : 'ITL')) + ' ' + f + ' ' + fp(e.price, d) + (x.nhan ? ' (' + x.nhan + ')' : '') +
        ' xác nhận: ' + (hi ? 'đỉnh' : 'đáy') + ' nến ' + f + ' mở ' + fmtIsoShort(x.mo_nen_htf) + ' (chạm ở nến #' + e.event_bar_index + ') → ' + vtxt +
        '. Thứ tự ' + f + ': ' + (x.order_sau_vi || DIR_WORD[ofKey(x.order_sau)]) + '.' };
    }
    if (t === 'HTF_FVG_UP' || t === 'HTF_FVG_DOWN') {
      return { kind: 'info', text: 'FVG ' + f + ' ' + fvgDirWord(t) + ' [' + fp(x.lo, d) + ', ' + fp(x.hi, d) + '] biết ở nến này (nến ' + f +
        ' giữa mở ' + fmtIsoShort(x.mo_nen_giua) + (x.from_displacement ? ', là displacement' : '') + ') — vùng PD array, hiệu lực từ nến sau.' };
    }
    if (t === 'HTF_PERIOD_HIGH' || t === 'HTF_PERIOD_LOW') {
      var vp = x.vung_thanh_khoan || {};
      return { kind: 'info', text: (x.ten || srcKind(t, x)) + ' ' + fp(x.muc, d) + ' (kỳ ' + fmtIsoShort(x.mo_ky) + ' → ' + fmtIsoShort(x.period_end) +
        (x.chot_muon ? ', chốt muộn' : '') + ') → ' + (vp.trang_thai === 'khong_tao' ? 'không thành vùng (' + (vp.ly_do_vi || 'đã bị lấy') + ')'
          : 'vùng thanh khoản tầng ' + (x.khung || 'D') + ', hiệu lực từ nến sau') + '.' };
    }
    if (t === 'HTF_BAR_DEGRADED') {
      return { kind: 'warn', text: 'Nến ' + (x.khung || f || '') + ' mở ' + fmtIsoShort(x.mo) + ' không dùng được (' + (x.ly_do_degraded || '') +
        (finite(x.coverage) ? ', coverage ' + x.coverage.toFixed(2) + ' < ' + x.nguong_coverage : '') + '): ' + (x.he_qua_vi || '') + '.' };
    }
    if (PD_TYPES[t]) {
      return { kind: 'ok', text: 'FVG ' + (x.khung || '') + ' ' + fvgDirWord(t) + ' [' + fp(x.lo, d) + ', ' + fp(x.hi, d) + '] bị ' + pdWord(t) +
        ': close ' + fp(x.close, d) + (x.quy_tac_vi ? ' (' + x.quy_tac_vi + ')' : '') + ' → pd_bias ' +
        (x.pd_bias_sau === 0 ? 'mâu thuẫn trong cùng nến (0)' : DIR_WORD[ofKey(x.pd_bias_sau)]) + (x.pd_bias_khung ? ' (' + x.pd_bias_khung + ')' : '') + '.' };
    }
    if (t === 'DOL_REACHED') {
      var vg = x.vung || {};
      var nmd = PERIOD_NAME[vg.tang] ? PERIOD_NAME[vg.tang][vg.phia] : (vg.phia || '') + (runTier(vg.tang) ? '' : ' ' + vg.tang);
      var fx = flipOf(x);
      return { kind: 'ok', text: 'Đích DOL ' + nmd + ' ' + fp(x.muc, d) + ' bị lấy (đặt sau ' + fx.name +
        ' ở nến #' + x.nen_dat_dol + ', ' + x['so_nen_tu_' + fx.key] +
        ' nến trước' + (finite(x.xuyen_atr) ? '; xuyên ' + x.xuyen_atr.toFixed(2) + ' ATR' : '') + ') — DOL hết hiệu lực. Mô tả, không phải tín hiệu.' };
    }
    return null;
  }

  /** Tooltip của đối tượng `id` (pool / shift / fvg / of / prot / range / swing / disp / htfsw / htffvg / htfrange / lvl / forming)
   * tại con trỏ: [{head, body, more}]. opts.barOf: nến (cho nến H4 đang hình thành). */
  function objectInfo(M, id, opts) {
    if (!M || typeof id !== 'string') return null;
    var c = M.cursor, i = id.indexOf(':'), kind = id.slice(0, i), rest = id.slice(i + 1);
    var pr = structureAt(M).prot;
    if (kind === 'pool') {
      var out = [], byLevel = [], protDone = false;
      rest.split('+').forEach(function (pid) {
        var s = poolAt(M.pools[pid], c);
        if (!s) return;
        var b = byLevel.filter(function (q) { return q.level === s.level; })[0];
        if (!b) { b = { level: s.level, list: [] }; byLevel.push(b); }
        b.list.push(s);
      });
      byLevel.forEach(function (b) {
        // Cùng một đỉnh/đáy ở nhiều tầng (M15, H1, H4, PDH…): một dòng theo tầng cao nhất, nguồn từng tầng ở dòng phụ.
        var top = b.list[0];
        b.list.forEach(function (s) { if (tierRank(s.pool.tier) > tierRank(top.pool.tier)) top = s; });
        var line = poolLine(M, top);
        if (b.list.length > 1) {
          line.head += ' — cùng mức ' + b.list.length + ' tầng: ' + b.list.map(poolName).join(', ');
          line.more = b.list.map(function (s) { return poolName(s) + ': ' + sourceText(M, s.pool, c); }).join(' | ');
        }
        out.push(line);
        // Mức được bảo vệ thường trùng đúng vùng của đáy/đỉnh cấu trúc gần nhất → hai đường chồng nhau: ghi cả hai.
        if (!protDone && opts && opts.prot && pr && b.list.some(function (s) {
          return pr.price === s.level && s.pool.sources.some(function (x) { return x.bar === pr.swingBar; });
        })) {
          out = out.concat(protLines(M));
          protDone = true;
        }
      });
      return out.length ? out : null;
    }
    if (kind === 'shift') return M.ev[rest] ? shiftLines(M, M.ev[rest]) : null;
    if (kind === 'fvg') {
      var fe = M.ev[rest];
      if (!fe) return null;
      return [/^(SHIFT|MSS)_FVG_/.test(fe.structure_type) ? fvgLine(M, fe) : rawFvgLine(M, fe)];
    }
    if (kind === 'prot') {
      var lines = protLines(M);
      if (lines && pr) {
        M.poolList.forEach(function (p) {
          var s = poolAt(p, c);
          if (s && s.state === 'intact' && s.level === pr.price && p.sources.some(function (x) { return x.bar === pr.swingBar; })) {
            lines.push(poolLine(M, s));
          }
        });
      }
      return lines;
    }
    if (kind === 'range') return rangeLines(M, rest.slice(rest.lastIndexOf(':') + 1));
    if (kind === 'swing') return M.ev[rest] ? [swingLine(M, M.ev[rest])] : null;
    if (kind === 'disp') return M.ev[rest] ? [dispLine(M, M.ev[rest])] : null;
    if (kind === 'of') {
      var parts = rest.split(':');
      return ofLines(M, parts[0], parts[1]);
    }
    if (kind === 'htfsw') return M.ev[rest] ? [htfSwingLine(M, M.ev[rest])] : null;
    if (kind === 'htffvg') {
      var he = M.ev[rest];
      if (!he) return null;
      var lastPd = M.pds.length ? M.pds[M.pds.length - 1].confirmed_bar_index : null;
      var isSrc = M.pds.some(function (e) { return e.confirmed_bar_index === lastPd && ((e.details || {}).fvg || e.reference_event_id) === rest; });
      return [htfFvgLine(M, he, isSrc)];
    }
    if (kind === 'htfrange') return htfRangeLines(M);
    if (kind === 'lvl') return M.ev[rest] ? levelLines(M, M.ev[rest]) : null;
    if (kind === 'forming') return formingLines(M, opts && opts.barOf);
    return null;
  }

  MSL.ictView = {
    COL: COL, OF_COLORS: OF_COLORS, OF_TEXT: OF_TEXT, OF_WORD: OF_WORD, GAP_VI: GAP_VI, DEFAULTS: DEF, PRIORITY: PRI,
    HCOL: HCOL, TIER: TIER,
    hasOwn: hasOwn, flipOf: flipOf, finite: finite, withDefaults: withDefaults, fvgDist: fvgDist, fpRange: fpRange, pct: pct, pct1: pct1, ofKey: ofKey, fp: fp, fmtShort: fmtShort, rgba: rgba, parseId: parseId, displayDigits: displayDigits,
    buildModel: buildModel, poolAt: poolAt, statesAt: statesAt, nearestIntact: nearestIntact, atrAt: atrAt,
    selectCurrent: selectCurrent, groupPools: groupPools, poolName: poolName, buildDrawing: buildDrawing, structureAt: structureAt,
    bandBars: bandBars, statusAt: statusAt, objectInfo: objectInfo,
    selectHtf: selectHtf, htfRangeAt: htfRangeAt, formingAt: formingAt, h4Bucket: h4Bucket, htfStatusAt: htfStatusAt, poolByLevel: poolByLevel,
    htfExplain: htfExplain, htfEventText: htfEventText, frameOf: frameOf
  };
})(window.MSL);
