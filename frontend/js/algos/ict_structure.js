/* Plugin hiển thị ict_structure (lõi 0.4.0 — khung lớn H1/H4, PDH/PDL, pd_bias, DOL; order flow theo thanh khoản).
 *
 * Giai đoạn 3 (giao diện, đặc tả §11):
 *   - Gọn: vùng thanh khoản có TẦNG — «BSL» (khung chạy), «BSL H1», «EQH H4», «PDH»/«PDL», «PWH»/«PWL»; nét đậm dần theo tầng;
 *     tooltip ghi tầng, nguồn (nến H4 / kỳ ngày nào), lúc biết. Dòng trạng thái hàng 1 thêm ngữ cảnh khung lớn gọn
 *     «H4 ↑ · discount 31% · pd ↓ H1 · DOL ↑ BSL H1 2341.00 (4.2 ATR)» (đọc cột timeline htf_* / pd_bias / dol_*).
 *   - lớp ict_htf «Khung lớn» (tắt sẵn, nhóm riêng — lớp con data-requires="ict_htf"): ITH/ITL H4 (vòng tròn rỗng tím, «HH H4»),
 *     dealing range H4 + EQ (nét đứt / chấm tím), FVG H4 đang mở (hộp viền dày, «FVG H4», dừng ở PD_* — «· respect» /
 *     «· disrespect»), PDH/PDL/PWH/PWL hiện hành, nến H4 đang hình thành (khung mờ «H4 đang hình thành — chưa dùng»);
 *     lớp con ict_htf_h1 thêm ITH/ITL H1 + FVG H1. Mọi thứ chỉ từ nến xác nhận, «Hiện tại» tính tại con trỏ.
 *   - Khung «Thuật toán đang làm gì»: mục «Khung lớn» — mỗi thành phần một dòng (thứ tự H4/H1 + vị trí trong range, pd_bias +
 *     FVG nguồn, DOL + đích, mức theo kỳ, nến H4 đang hình thành) đọc pending_state; sự kiện HTF_* / PD_* / DOL_REACHED ở
 *     nến con trỏ có câu riêng. Không đọc details.htf (lõi có thể bỏ ở sự kiện phụ vì dung lượng).
 *
 * Chế độ Gọn (mặc định, plan_hien_thi_ict §3) — vẽ bằng 3 lớp chung chart/primitives.js, đối tượng dựng bởi
 * algos/ict_structure_view.js (hàm thuần):
 *   lớp ict_flow  — vùng BSL (cam) / SSL (xanh ngọc) vẽ từ nến đỉnh/đáy gốc, chỉ xuất hiện từ nến xác nhận: còn nguyên
 *                   = nét liền tới con trỏ + 5 nến, nhãn «BSL»/«SSL»/«EQH»/«EQL» ở đầu phải; sweep = dừng ở nến lấy,
 *                   nét chấm, «sweep» + hộp phần râu vượt mức; run = dừng ở nến lấy, mờ, «run»; chưa rõ = chấm xám;
 *                   đang chờ (pending_state) = nét đứt, «BSL bị lấy · chờ»; vùng trùng gộp «sweep ×2»; vùng xa > 3 ATR
 *                   không giãn trục giá, ghi ở mép. «Hiện tại»: 2 vùng còn nguyên mỗi phía + ≤ 3 nhóm kết cục gần con trỏ nhất mỗi phía (≤ 60 nến) + vùng
 *                   của shift đang hiện + vùng đang chờ. Dải order flow ở đáy có chữ; dòng trạng thái 2 hàng #ict-status
 *                   (theo nến dưới chuột, mặc định nến con trỏ).
 *   lớp ict_shift — đoạn «Shift ↓/↑» tại mức bị quét (nến lấy → nến displacement) + hộp FVG của chính nến displacement.
 *   lớp ict_gap   — marker «thiếu» (khoảng trống bất thường).
 *   Rê chuột vào đường / hộp / dải → tooltip giải thích (hook tooltipObject).
 * Chế độ Chi tiết (lớp ict_detail, tắt mặc định, plan §4) — cũng bằng lớp vẽ chung: ITH/ITL = chấm nhỏ tại pivot (+ nhãn
 * HH/HL/LH/LL/EQH/EQL chữ nhỏ không nền, lớp ict_labels tắt sẵn), STH/STL chấm nhỏ hơn (tắt), LTH/LTL marker như cũ;
 * «Protected Low/High» từ swing tới con trỏ + 20 nến (close đã vượt → nét đứt đỏ «· broken» — chỉ là cờ); dealing range
 * = 3 dải mỏng có chữ Premium / EQ / Discount; FVG = hộp + CE nét đứt (mở: viền liền, đã chạm: đứt, đã lấp: chấm, mờ),
 * «Hiện tại» 3 FVG còn mở gần giá nhất mỗi chiều; displacement = tô nhạt cả cây nến (tắt); lớp ict_liq = mọi vùng còn
 * nguyên (không chỉ 2 gần nhất mỗi phía), nét mảnh.
 * Chế độ «Lịch sử» (mọi vùng / shift / FVG tới con trỏ, mờ dần theo tuổi) TẠM BỎ khỏi giao diện (người dùng, 08/10/2026):
 * không còn ô bật; phần dựng hình thuần (opts.history của ict_structure_view.js) vẫn giữ và vẫn được test để bật lại sau.
 * Kèm tooltip, ghi chú, thống kê, trạng thái replay, panel chi tiết sự kiện, khung «Thuật toán đang làm gì».
 * Chỉ đọc details / timeline / pending_state do lõi tính — không tính lại logic ở đây.
 * Kết quả cũ (v0.2.0, chưa có khoá order flow) vẫn hiển thị được — chỉ thiếu phần order flow.
 * Lõi 0.5.0 — lớp ict_ob «Order block» và ict_ote «OTE» (tắt sẵn, nhóm Gọn): dựng hình ở algos/ict_ob_ote_view.js (hàm thuần,
 * MSL.ictObOteView) — hộp OB (nét liền = còn mở, đứt = đã chạm, chấm = hỏng / hết hạn) + mean threshold; vùng OTE đang chờ
 * (hộp vàng nét đứt + điểm ngọt + gốc nhịp) và OTE vừa vào / hỏng. Mô tả, chưa phải tín hiệu.
 * Lõi 0.6.0 — lớp ict_nd_state «Trạng thái» (bật sẵn, nhóm Gọn): dựng hình ở algos/ict_nhan_dien_view.js (MSL.ictNdView) —
 * dải «trạng thái» trên dải order flow (trend ↑ / trend ↓ / range / nén / nhiễu), hộp range đang có + range gần nhất, hàng
 * thứ ba của dòng trạng thái. Mô tả trạng thái, không phải dự báo hướng. Lớp ict_nd_band «Khoảng giá»: khoảng 80% / 50%
 * của 1h, 4h phía trước con trỏ + xác suất chạm vùng gần nhất / PDH / PDL / biên range, tooltip kèm điểm thật (MSL.ictNdView.bandDrawing).
 */
(function (MSL) {
  'use strict';

  var V = MSL.ictView;
  var OB = MSL.ictObOteView;
  var ND = MSL.ictNdView;
  var P = MSL.primitives;
  var isFiniteNum = MSL.format.isFiniteNum;
  var fmtIso = MSL.format.fmtIso;
  var esc = MSL.dom.esc;
  var ALGO = 'ict_structure';

  var COLORS = {
    ith: '#ffd54f',
    itl: '#4fc3f7',
    lth: '#ff8f00',
    ltl: '#0288d1',
    sth: 'rgba(176,190,197,.8)',
    gap: '#ff7043',
    bsl: '#f48fb1',
    ssl: '#80cbc4',
    run: '#b0bec5',
    unresolved: '#ff7043',
    shiftUp: '#00e676',
    shiftDown: '#ff1744',
    fvgUp: 'rgba(102,187,106,.9)',
    fvgDown: 'rgba(239,83,80,.9)',
    disp: '#eceff1',
    ofRunUp: '#66bb6a',
    ofRunDown: '#ef5350',
    ofUnclear: '#ffb300'
  };
  /** Màu dải order flow theo trạng thái (luôn kèm chữ trên dải / dòng trạng thái / tooltip, không chỉ dựa vào màu). */
  var OF_COLORS = V.OF_COLORS;
  /** Màu chữ trạng thái order flow trong dòng trạng thái. */
  var OF_TEXT_COLORS = { '1': '#66bb6a', '-1': '#ef6f6c', '0': '#b0bec5', 'null': '#78909c' };
  var OF_VI = { '1': 'tăng', '-1': 'giảm', '0': 'chưa rõ', 'null': 'chưa có' };
  /** Mã lý do (timeline chỉ có mã) → chữ ngắn; sự kiện / pending_state có sẵn `ly_do_vi` của lõi. */
  var OF_REASON_VI = {
    run_tang: 'run lên (lấy BSL, không quay lại)',
    run_giam: 'run xuống (lấy SSL, không quay lại)',
    shift_tang: 'shift tăng',
    shift_giam: 'shift giảm',
    run_nguoc_chieu: 'run phía ngược chiều',
    hai_chieu_cung_nen: 'run/shift hai chiều cùng nến'
  };
  var OF_TYPES = { ORDER_FLOW_UP: 1, ORDER_FLOW_DOWN: 1, ORDER_FLOW_UNCLEAR: 1 };
  var FLOW_INPUT_TYPES = { LIQ_RUN_UP: 1, LIQ_RUN_DOWN: 1, SHIFT_UP: 1, SHIFT_DOWN: 1 };
  var LEVEL_OF = {
    SWING_HIGH: 1, SWING_LOW: 1, SWING_HIGH_L2: 2, SWING_LOW_L2: 2, SWING_HIGH_L3: 3, SWING_LOW_L3: 3
  };
  var SHORT = { 1: ['STH', 'STL'], 2: ['ITH', 'ITL'], 3: ['LTH', 'LTL'] };
  var ORDER_VI = { '1': 'tăng (HH + HL)', '-1': 'giảm (LH + LL)', '0': 'lẫn lộn', 'null': 'chưa đủ swing' };
  var ZONE_VI = { premium: 'premium (trên EQ)', discount: 'discount (dưới EQ)', eq: 'đúng EQ' };
  var GAP_VI = V.GAP_VI;
  var KZ_VI = { asia: 'Asia', london: 'London', ny_am: 'NY AM', london_close: 'London close', ngoai: 'ngoài killzone' };
  var DIR_VI = { up: 'tăng', down: 'giảm' };
  var POOL_STATUS_VI = { tao_moi: 'tạo vùng mới', gop_eq: 'gộp EQ vào vùng có sẵn', khong_tao: 'không tạo vùng' };
  var LIQ_TYPES = { LIQ_SWEEP_BSL: 1, LIQ_SWEEP_SSL: 1, LIQ_RUN_UP: 1, LIQ_RUN_DOWN: 1, LIQ_UNRESOLVED: 1 };
  /** Sự kiện khung lớn / PD / DOL (lõi 0.4.0): ẩn trên chart (D12) — chỉ marker khi chọn ở bảng; câu giải thích từ V.htfEventText. */
  var HTF_TYPES = {
    HTF_SWING_HIGH: 1, HTF_SWING_LOW: 1, HTF_FVG_UP: 1, HTF_FVG_DOWN: 1, HTF_PERIOD_HIGH: 1, HTF_PERIOD_LOW: 1, HTF_BAR_DEGRADED: 1,
    PD_RESPECT_UP: 1, PD_RESPECT_DOWN: 1, PD_DISRESPECT_UP: 1, PD_DISRESPECT_DOWN: 1, DOL_REACHED: 1
  };
  var PD_RESULT_VI = { respect: 'respect (tôn trọng)', disrespect: 'disrespect (bị xuyên)' };
  /** View phụ của lõi ≥ 0.5.0 (algos/ict_*_view.js): cùng bộ hàm isType / meta / eventText / info / pendingLines — plugin
   *  duyệt danh sách này thay cho nhánh riêng từng view (marker, giải thích, chi tiết, tooltip, «Đang theo dõi»).
   *  Thứ tự = thứ tự khối «Đang theo dõi». Phần vẽ lên chart theo lớp ở draw (mỗi view một kiểu chọn đối tượng). */
  var SUBVIEWS = [
    { view: ND, ids: /^nd:/, title: 'Nhận diện (trạng thái · khoảng · xác suất chạm)',
      note: 'Trạng thái là mô tả, không phải dự báo hướng — định nghĩa: docs/algorithms/thuat_toan_nhan_dien.md §5.',
      marker: function (e, m, push) { push('belowBar', m.color, 'circle', m.short, 0.9); } },
    { view: OB, ids: /^(ob|ote):/, title: 'Order block · OTE',
      note: 'Mô tả theo SHIFT (lab không có MSS), chưa phải tín hiệu — khảo sát K17–K27 ở plan_ket_hop_ict_indicator.md §3.4.',
      marker: function (e, m, push) {
        var up = e.direction !== 'down';
        push(up ? 'belowBar' : 'aboveBar', m.group === 'ote' ? OB.COL.ote : (up ? COLORS.shiftUp : COLORS.shiftDown),
          m.end === null || m.end === 'entry' ? 'square' : 'circle', m.mark, 0.8);
      } }
  ];
  function findSubview(pred) {
    for (var i = 0; i < SUBVIEWS.length; i++) if (pred(SUBVIEWS[i])) return SUBVIEWS[i];
    return null;
  }
  function subviewOf(t) { return findSubview(function (sv) { return sv.view.isType(t); }); }
  function subviewById(id) { return findSubview(function (sv) { return sv.ids.test(id); }); }

  function hasOwn(o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); }
  function orderVi(o) { return ORDER_VI[String(o === undefined ? null : o)] || String(o); }
  function kzVi(k) { return KZ_VI[k || 'ngoai'] || String(k); }

  /** Khoá trạng thái order flow: '1' / '-1' / '0' / 'null' (None, chưa có hoặc thiếu). */
  function ofKey(v) { return v === 1 || v === -1 || v === 0 ? String(v) : 'null'; }
  function ofVi(v) { return OF_VI[ofKey(v)]; }
  function ofColor(v) { return OF_COLORS[ofKey(v)]; }
  function reasonVi(code) { return code ? (OF_REASON_VI[code] || String(code)) : ''; }
  /** Ô màu nhỏ kèm chữ trạng thái (màu không bao giờ đứng một mình). */
  function ofSw(v) { return '<i class="of-sw" style="background:' + ofColor(v) + '" aria-hidden="true"></i>'; }

  function isIctTimeline(tl) {
    return tl.length && hasOwn(tl[tl.length - 1], 'dealing_hi');
  }

  /** Lớp con của «Chi tiết»: chỉ vẽ khi bật cả «Chi tiết» lẫn chính lớp đó. */
  function detailOn(L, k) { return !!(L.ict_detail && L[k]); }

  /** «ict:LIQ_RUN_UP@120>128:B3» → «LIQ_RUN_UP #120→#128» (gọn cho tooltip); khác mẫu → nguyên id. Trả HTML đã thoát. */
  function evShort(id) {
    var m = /^ict:([A-Z0-9_]+)@(\d+)(?:>(\d+))?/.exec(String(id || ''));
    if (!m) return esc(id);
    return esc(m[1]) + ' #' + m[2] + (m[3] && m[3] !== m[2] ? '→#' + m[3] : '');
  }

  /** Run trong id lõi «ict:LIQ_RUN_UP@b>t» (nến sự kiện = nến lấy b, nến xác nhận t = b + W): {side, b, t}; khác → null. */
  function runSpan(id) {
    var m = /^ict:LIQ_RUN_(UP|DOWN)@(\d+)>(\d+)/.exec(String(id || ''));
    return m ? { side: m[1] === 'UP' ? 'BSL' : 'SSL', b: Number(m[2]), t: Number(m[3]) } : null;
  }

  /** «run BSL lấy ở nến #b, biết ở nến #t (sau W nến không quay lại)» — chữ thường, chưa thoát; không phải run → null. */
  function runSpanText(id) {
    var r = runSpan(id);
    if (!r) return null;
    return r.t > r.b
      ? 'run ' + r.side + ' lấy ở nến #' + r.b + ', biết ở nến #' + r.t + ' (sau ' + (r.t - r.b) + ' nến không quay lại)'
      : 'run ' + r.side + ' lấy và biết ở nến #' + r.b;
  }

  /** Một mục run/shift cùng nến cho tooltip: run → «run SSL (lấy #b, biết #t)», khác → evShort. HTML đã thoát. */
  function basisShort(id) {
    var r = runSpan(id);
    return r ? 'run ' + r.side + ' (lấy #' + r.b + ', biết #' + r.t + ')' : evShort(id);
  }


  function poolText(p, d) {
    if (!p) return '—';
    return esc(p.id) + ' ' + esc(p.phia) + ' ' + Number(p.muc).toFixed(d) + ' (' + esc(p.tang) + ', ' +
      (p.nguon || []).length + ' nguồn' + (p.so_lan_cham ? ', chạm ' + p.so_lan_cham + ' lần' : '') + ')';
  }

  /** Nguyên nhân đổi order flow: 'run' | 'shift' | 'unclear' (theo details.ly_do, dự phòng theo reason_code). */
  function ofCause(e) {
    var why = (e.details || {}).ly_do;
    if (why === 'run_tang' || why === 'run_giam') return 'run';
    if (why === 'shift_tang' || why === 'shift_giam') return 'shift';
    if (why === 'run_nguoc_chieu' || why === 'hai_chieu_cung_nen') return 'unclear';
    if (e.reason_code === 'OF_RUN') return 'run';
    if (e.reason_code === 'OF_SHIFT') return 'shift';
    return e.structure_type === 'ORDER_FLOW_UNCLEAR' ? 'unclear' : null;
  }

  /** «Trạng thái cũ (tăng) kéo dài 37 nến (từ nến #120)» cho sự kiện ORDER_FLOW_*. */
  function prevSpanText(x) {
    var vi = x.tu_vi || ofVi(x.tu);
    if (!isFiniteNum(x.trang_thai_cu_so_nen)) {
      return 'Trạng thái cũ: ' + esc(vi) + (x.tu === null || x.tu === undefined ? ' (từ đầu lần chạy)' : '');
    }
    return 'Trạng thái cũ (' + esc(vi) + ') kéo dài ' + x.trang_thai_cu_so_nen + ' nến (từ nến #' + x.trang_thai_cu_tu_nen + ')';
  }

  /** Khoảng giá (low thấp nhất, high cao nhất) của các nến đã nạp nằm trong khoảng logic [a, b]. */
  function visibleExtent(mc, a, b) {
    var n = mc.bars.length;
    var i0 = Math.max(0, Math.ceil(a)), i1 = Math.min(n - 1, Math.floor(b));
    var lo = Infinity, hi = -Infinity;
    for (var i = i0; i <= i1; i++) {
      var x = mc.bars[i];
      if (x.low < lo) lo = x.low;
      if (x.high > hi) hi = x.high;
    }
    return isFinite(lo) ? { lo: lo, hi: hi } : null;
  }

  function clearPrims(st) {
    st.segs.setItems([]);
    st.boxes.setItems([]);
    st.band.setBars([]);
    st.stateBand.setBars([]);
    st.model = null;
    st.sel = null;
    st.drawing = null;
    st.statusBar = null;
  }

  /** Nến có bar.index = h trong dữ liệu đã nạp (null nếu không có). */
  function barAt(mc, h) {
    var pos = mc.logicalOf(h);
    var b = pos === null ? null : mc.bars[pos];
    return b && b.index === h ? b : null;
  }

  /** Hàng bị cắt «…» (hẹp) mới nhận chuột để hiện toàn văn (title); hàng không cắt để chuột xuyên xuống chart. */
  function markCut(el) {
    Array.prototype.forEach.call(el.querySelectorAll('.st-row'), function (r) {
      r.classList.toggle('st-cut', r.scrollWidth > r.clientWidth + 1);
    });
  }

  /** Dòng trạng thái đúng 2 hàng (#ict-status, chỉ có ở trang Thử nghiệm) ở nến h — mặc định nến con trỏ. Hàng dài bị cắt
   * «…»; toàn văn ở title của hàng. */
  function renderStatus(mc, st, h) {
    var el = document.getElementById('ict-status');
    var M = st.model;
    if (!el || !M) return;
    var at = h === null || h === undefined ? M.cursor : Math.min(h, M.cursor);
    var bar = barAt(mc, at);
    var s = V.statusAt(M, at, bar ? bar.close : null);
    if (!s) return;
    st.statusBar = at;
    var row1;
    var t1;
    if (s.hasOF) {
      row1 = '<b>Order flow: <span style="color:' + OF_TEXT_COLORS[s.key] + '">' + esc(s.word) + '</span></b>' +
        (s.since ? ' · từ ' + esc(s.since) + (s.why ? ' (' + esc(s.why) + ')' : '') : '');
      t1 = 'Order flow: ' + s.word + (s.since ? ' · từ ' + s.since + (s.why ? ' (' + s.why + ')' : '') : '');
    } else {
      row1 = '<b>Order flow:</b> <span class="muted">kết quả cũ chưa có — bấm Chạy thử để có dải và trạng thái</span>';
      t1 = 'Order flow: kết quả cũ chưa có — bấm Chạy thử để có dải và trạng thái';
    }
    // Ngữ cảnh khung lớn (0.4.0) ngay sau order flow — gọn, toàn văn tiếng Việt ở title của hàng.
    if (s.htf) {
      row1 += ' <span class="st-htf">│ ' + esc(s.htf.text) + '</span>';
      t1 += ' │ ' + s.htf.text + '\n' + s.htf.title;
    }
    // Nến đang rê (khác con trỏ) ghi ở ĐẦU hàng — hàng dài bị cắt ở cuối.
    if (at !== M.cursor) { row1 = '<span class="st-at">#' + at + ' · </span>' + row1; t1 = 'Nến #' + at + ' · ' + t1; }
    var parts = [esc(s.near)], t2 = [s.near];
    if (s.pending) { parts.push('<span class="st-pend">' + esc(s.pending) + '</span>'); t2.push(s.pending); }
    if (s.change) { parts.push(esc(s.change)); t2.push(s.change); }
    var html = '<div class="st-row st-main" title="' + esc(t1) + '">' + row1 + '</div><div class="st-row" title="' +
      esc(t2.join(' · ')) + '">' + parts.join(' · ') + '</div>';
    var Ls = st.layers || {};   // 0.6.0: hàng 3 = trạng thái (+ khoảng 4h của nến đang xem khi bật lớp khoảng giá)
    var nd = ND.statusAt(M, at, { state: !!Ls.ict_nd_state, band: !!Ls.ict_nd_band });
    if (nd) {
      html += '<div class="st-row st-nd" title="' + esc(nd.title) + '">' +
        (nd.color ? '<i class="sw-nd" style="background:' + nd.color + '"></i>' : '') + esc(nd.text) + '</div>';
    }
    if (st.statusHtml !== html) {
      el.innerHTML = html;
      st.statusHtml = html;
      markCut(el);
    }
  }

  var chart = {
    init: function (mc, st) {
      // Gọn + Chi tiết: 3 lớp vẽ chung — hộp (dưới nến), dải order flow ở đáy, đường + chấm + nhãn (trên cùng).
      var extent = function (a, b) { return visibleExtent(mc, a, b); };
      st.boxes = new P.Boxes({ priceExtent: extent });
      st.band = new P.Band({ caption: 'order flow' });
      // 0.6.0: dải «trạng thái» xếp ngay trên dải order flow (cách 2 px), sát đáy khi không có dải order flow
      st.stateBand = new P.Band({ caption: 'trạng thái', bottom: function () { return st.band.height() ? st.band.height() + 2 : 3; } });
      st.segs = new P.Segments({
        priceExtent: extent, bottomGuard: function () { return Math.max(22, st.stateBand.height() + 5); },
        reserved: function () { return P.reservedRects(mc.container); }
      });
      mc.attachPrimitive(st.boxes);
      mc.attachPrimitive(st.band);
      mc.attachPrimitive(st.stateBand);
      mc.attachPrimitive(st.segs);
      st.timelineByIndex = {};
      st.model = null;
    },

    clear: function (mc, st) {
      clearPrims(st);
    },

    /** Sự kiện của ict_structure (STH/ITH dùng chung loại SWING_* với thuật toán swing). */
    ownsEvent: function (t, e) { return !!e && e.algorithm === ALGO; },

    /** Marker nến chỉ còn: «thiếu» (Gọn) và LTH/LTL (Chi tiết, cấp 3). Mọi thứ khác do primitive vẽ — xem draw. Sự kiện
     * đang chọn ở bảng luôn có marker (kể cả khi lớp của nó tắt) để thấy nó nằm ở đâu. */
    marker: function (e, ctx) {
      var t = e.structure_type, L = ctx.layers, x = e.details || {};
      var at = ctx.opts.markerAtConfirm ? e.confirmed_bar_index : e.event_bar_index;
      var sel = e.event_id === ctx.selectedId;
      var scale = (ctx.chart._markerScale || 1) * (sel ? 1.6 : 1);
      function push(position, color, shape, text, size) {
        ctx.markers.push({ time: ctx.timeByIndex[at], position: position, color: color, shape: shape, text: text, size: size * scale });
      }
      function on(k) { return sel || detailOn(L, k); }
      if (HTF_TYPES[t]) {
        // Khung lớn / PD / DOL: ẩn mặc định (D12) — lớp «Khung lớn» vẽ bằng primitive; marker chỉ khi chọn ở bảng.
        if (!sel) return;
        var hf = V.frameOf(e) || '';
        if (t === 'HTF_SWING_HIGH' || t === 'HTF_SWING_LOW') {
          push(t === 'HTF_SWING_HIGH' ? 'aboveBar' : 'belowBar', V.HCOL[hf] || V.HCOL.H4, 'circle', (x.ten || '') + ' ' + hf, 0.9);
        } else if (t === 'HTF_FVG_UP' || t === 'HTF_FVG_DOWN') {
          push('inBar', t === 'HTF_FVG_UP' ? COLORS.fvgUp : COLORS.fvgDown, 'square', 'FVG ' + hf, 0.7);
        } else if (t === 'HTF_PERIOD_HIGH' || t === 'HTF_PERIOD_LOW') {
          push(t === 'HTF_PERIOD_HIGH' ? 'aboveBar' : 'belowBar', t === 'HTF_PERIOD_HIGH' ? COLORS.bsl : COLORS.ssl, 'circle', x.ten || '', 0.8);
        } else if (t === 'HTF_BAR_DEGRADED') {
          push('belowBar', COLORS.gap, 'square', 'thiếu ' + hf, 0.6);
        } else if (t === 'DOL_REACHED') {
          push(e.direction === 'up' ? 'aboveBar' : 'belowBar', '#fff176', 'circle', 'DOL', 0.8);
        } else {   // PD_*: hướng = chiều hàm ý
          var pu = e.direction === 'up';
          push(pu ? 'belowBar' : 'aboveBar', pu ? COLORS.ofRunUp : COLORS.ofRunDown, pu ? 'arrowUp' : 'arrowDown', 'PD', 0.8);
        }
        return;
      }
      if (OF_TYPES[t]) {
        // Dải order flow ghi chữ ngay trên dải — marker chỉ khi đang chọn sự kiện này ở bảng.
        if (!sel) return;
        var why = ofCause(e), up = t === 'ORDER_FLOW_UP';
        if (why === 'unclear') {
          var both = x.ly_do === 'hai_chieu_cung_nen' || e.reason_code === 'OF_BOTH_SIDES';
          push(!both && x.tu === -1 ? 'belowBar' : 'aboveBar', COLORS.ofUnclear, 'circle', '?', 0.6);
        } else {
          push(up ? 'belowBar' : 'aboveBar', up ? COLORS.ofRunUp : COLORS.ofRunDown, 'circle',
            (why === 'shift' ? 'shift' : 'run') + (up ? '↑' : '↓'), 0.6);
        }
        return;
      }
      if (t === 'ICT_GAP') {
        if (!sel && !(L.ict_gap && x.bat_thuong)) return;
        ctx.markers.push({
          time: ctx.timeByIndex[e.event_bar_index], position: 'belowBar', color: COLORS.gap,
          shape: 'square', text: 'thiếu', size: 0.6 * (sel ? 1.6 : 1)
        });
        return;
      }
      if (LIQ_TYPES[t]) {
        if (!sel) return;            // đường vùng dừng ở nến lấy + «sweep / run / chưa rõ» do primitive vẽ
        var bsl = x.phia === 'BSL';
        if (t === 'LIQ_SWEEP_BSL' || t === 'LIQ_SWEEP_SSL') {
          push(bsl ? 'aboveBar' : 'belowBar', bsl ? COLORS.bsl : COLORS.ssl, 'circle', 'quét', 0.7);
        } else if (t === 'LIQ_UNRESOLVED') {
          push(bsl ? 'aboveBar' : 'belowBar', COLORS.unresolved, 'circle', '?', 0.5);
        } else {
          push(bsl ? 'aboveBar' : 'belowBar', COLORS.run, 'circle', 'run', 0.5);
        }
        return;
      }
      if (t === 'SHIFT_UP' || t === 'SHIFT_DOWN') {
        if (!sel) return;            // đoạn «Shift ↓/↑» tại mức bị quét do primitive vẽ
        var su = t === 'SHIFT_UP';
        push(su ? 'belowBar' : 'aboveBar', su ? COLORS.shiftUp : COLORS.shiftDown, su ? 'arrowUp' : 'arrowDown', 'SHIFT', 1.5);
        return;
      }
      if (t === 'SHIFT_FVG_UP' || t === 'SHIFT_FVG_DOWN') {
        if (!sel) return;            // hộp FVG do primitive vẽ
        var su2 = t === 'SHIFT_FVG_UP';
        push(su2 ? 'belowBar' : 'aboveBar', su2 ? COLORS.shiftUp : COLORS.shiftDown, 'square', '+FVG', 0.5);
        return;
      }
      if (t === 'DISPLACEMENT_UP' || t === 'DISPLACEMENT_DOWN') {
        if (!sel) return;            // tô nhạt nến (lớp ict_disp) do primitive vẽ
        push('inBar', COLORS.disp, 'circle', '', 0.35);
        return;
      }
      if (t === 'FVG_UP' || t === 'FVG_DOWN') {
        if (!sel) return;            // hộp FVG (lớp ict_fvg) do primitive vẽ
        push('inBar', t === 'FVG_UP' ? COLORS.fvgUp : COLORS.fvgDown, 'square', '', 0.45);
        return;
      }
      var sv = subviewOf(t);
      if (sv) {
        if (!sel) return;            // view phụ: đối tượng do primitive vẽ theo lớp (ict_ob / ict_ote / ict_nd_*)
        sv.marker(e, sv.view.meta(t), push);
        return;
      }
      var lvl = LEVEL_OF[t];
      if (!lvl) return;            // FVG_TOUCHED / FVG_FILLED: chỉ trong bảng sự kiện và giải thích
      var high = t.indexOf('HIGH') !== -1;
      if (lvl === 1) {
        if (!sel) return;            // chấm STH/STL tại pivot do primitive vẽ
        push(high ? 'aboveBar' : 'belowBar', COLORS.sth, 'circle', '', 0.4);
        return;
      }
      if (lvl === 2 && !sel) return; // chấm ITH/ITL + nhãn HH… tại pivot do primitive vẽ
      if (!on(lvl === 3 ? 'ict_lth' : 'ict_ith')) return;
      var text = (on('ict_labels') && x.nhan) ? x.nhan : (lvl === 3 ? SHORT[3][high ? 0 : 1] : '');
      push(high ? 'aboveBar' : 'belowBar', lvl === 3 ? (high ? COLORS.lth : COLORS.ltl) : (high ? COLORS.ith : COLORS.itl),
        'square', text, lvl === 3 ? 1.4 : 1);
    },

    draw: function (ctx, st) {
      var tl = ctx.timeline || [], cursor = ctx.cursor, L = ctx.layers, mc = ctx.chart;
      st.timelineByIndex = {};
      st.layers = L;   // tooltip nến: Gọn hay Chi tiết
      if (!isIctTimeline(tl)) {
        clearPrims(st);
        return;
      }
      for (var j = 0; j < tl.length; j++) {
        if (tl[j].bar_index > cursor) break;
        st.timelineByIndex[tl[j].bar_index] = tl[j];
      }
      // Gọn (+ Chi tiết, + Khung lớn): «Hiện tại» tính tại con trỏ (nhân quả). «Lịch sử» tạm bỏ → luôn false.
      var t0 = Date.now();
      var M = V.buildModel(ctx.events || mc.events, tl, ctx.pendingState, cursor, mc.digits);
      if (!M) { clearPrims(st); return; }
      var t1 = Date.now();
      var lof = function (i) { return mc.logicalOf(i); };
      var hist = false, cb = barAt(mc, M.cursor);
      var detail = L.ict_detail ? {
        protected: !!L.ict_protected, range: !!L.ict_range, fvg: !!L.ict_fvg, ith: !!L.ict_ith, sth: !!L.ict_sth,
        labels: !!L.ict_labels, disp: !!L.ict_disp
      } : null;
      // Khung lớn (lớp ict_htf + lớp con) — chỉ khi timeline có cột khung lớn (kết quả 0.4.0+)
      var htf = L.ict_htf && M.hasHtf ? {
        swing: !!L.ict_htf_swing, range: !!L.ict_htf_range, fvg: !!L.ict_htf_fvg, levels: !!L.ict_htf_levels,
        forming: !!L.ict_htf_forming, h1: !!L.ict_htf_h1
      } : null;
      var sel = V.selectCurrent(M, { history: hist, allIntact: !!(L.ict_detail && L.ict_liq), close: cb ? cb.close : null, htf: htf });
      var dr = V.buildDrawing(M, sel, lof, {
        flow: !!L.ict_flow, shift: !!L.ict_shift, detail: detail, history: hist, htf: htf,
        barOf: function (i) { return barAt(mc, i); }
      });
      var merge = function (x, under) {   // under: vẽ trước mọi thứ và nhường rê chuột (hitTest quét từ cuối)
        dr.segments = under ? x.segments.concat(dr.segments) : dr.segments.concat(x.segments);
        dr.boxes = under ? x.boxes.concat(dr.boxes) : dr.boxes.concat(x.boxes);
      };
      if (L.ict_ob || L.ict_ote) {   // 0.5.0: order block / OTE — cùng mô hình M, cùng lớp vẽ chung
        var atrC = V.atrAt(M, M.cursor);
        var od = OB.drawing(M, OB.select(M, { close: cb ? cb.close : null }), lof,
          { ob: !!L.ict_ob, ote: !!L.ict_ote, near: isFiniteNum(atrC) ? V.DEFAULTS.farAtr * atrC : null });
        merge(od);
      }
      var ndHas = ND.has(M), ndOn = !!L.ict_nd_state && ndHas;   // 0.6.0: trạng thái (dải + hộp range), khoảng giá
      if (ndOn) merge(ND.drawing(M, lof));
      if (L.ict_nd_band && ndHas) merge(ND.bandDrawing(M, lof), true);
      st.timing = { model: t1 - t0, build: Date.now() - t1, segments: dr.segments.length, boxes: dr.boxes.length };
      st.model = M;
      st.sel = sel;
      st.drawing = dr;
      st.segs.setItems(dr.segments);
      st.boxes.setItems(dr.boxes);
      st.band.setBars(L.ict_flow ? V.bandBars(M, lof) : []);
      st.stateBand.setBars(ndOn ? ND.bandBars(M, lof) : []);
      st.statusBar = null;
      renderStatus(mc, st, M.cursor);
    },

    /** Khung nhìn / bề rộng đổi → kiểm lại hàng trạng thái nào bị cắt «…». */
    onRangeChange: function (mc, st) {
      var el = st.model && document.getElementById('ict-status');
      if (el && !el.hidden) markCut(el);
    },

    /** Dòng trạng thái theo nến dưới chuột; rời chart → về nến con trỏ. */
    onCrosshair: function (mc, bar, st) {
      if (!st.model || !st.layers || !st.layers.ict_flow) return;
      var h = bar ? Math.min(bar.index, st.model.cursor) : st.model.cursor;
      if (h === st.statusBar) return;
      renderStatus(mc, st, h);
    },

    /** Rê chuột vào đường vùng / hộp sweep / Shift / FVG / dải order flow → giải thích tiếng Việt. */
    tooltipObject: function (mc, id, bar, d, st) {
      if (!st.model || typeof id !== 'string') return '';
      var L = st.layers || {};
      var sv = subviewById(id);
      var info = sv ? sv.view.info(st.model, id)
        : V.objectInfo(st.model, id, { prot: !!(L.ict_detail && L.ict_protected), barOf: function (i) { return barAt(mc, i); } });
      if (!info || !info.length) return '';
      return info.map(function (r) {
        return '<div class="tt-obj-row"><b>' + esc(r.head) + '</b> — ' + esc(r.body) +
          (r.more ? '<div class="tt-rule">' + esc(r.more) + '</div>' : '') + '</div>';
      }).join('');
    },

    /** Gọn: order flow + hai vùng còn nguyên gần nhất + killzone / ATR / khoảng trống. Chi tiết: thêm thứ tự cấu trúc, mức
     * được bảo vệ, dealing range, shift gần nhất, FVG đang mở (ở Gọn dễ gây hiểu nhầm «order flow tăng» ↔ «thứ tự giảm»). */
    tooltipBar: function (mc, bar, d, st) {
      var p = st.timelineByIndex && st.timelineByIndex[bar.index];
      if (!p) return '';
      var detail = !!(st.layers && st.layers.ict_detail);
      var hasOf = hasOwn(p, 'order_flow'), of = p.order_flow;
      var head = '';
      if (hasOf) {
        head = '<div class="tt-of">' + ofSw(of) + 'Order flow sau nến này: <b>' + esc(ofVi(of)) + '</b>' +
          (isFiniteNum(p.order_flow_since)
            ? ' (từ nến #' + p.order_flow_since + (p.order_flow_reason ? ' · ' + esc(reasonVi(p.order_flow_reason)) : '') + ')'
            : '') + '</div>';
      }
      var hx = st.model ? V.htfStatusAt(st.model, bar.index) : null;
      if (hx) head += '<div class="tt-rule">' + esc(hx.title.replace(/^Khung lớn/, 'Khung lớn sau nến này')) + '</div>';
      var s = [];
      if (detail) {
        s.push('Thứ tự (cấu trúc) sau nến này: <b>' + orderVi(p.order) + '</b>');
        if (isFiniteNum(p.protected)) {
          s.push('Mức được bảo vệ (' + (p.protected_side === 'low' ? 'đáy' : 'đỉnh') + ') ' + p.protected.toFixed(d) +
            (p.protected_broken ? ' — <b>close đã vượt</b> (cờ, không phải sự kiện)' : ''));
        }
        if (isFiniteNum(p.dealing_hi) && isFiniteNum(p.dealing_lo)) {
          s.push('Dealing range [' + p.dealing_lo.toFixed(d) + ', ' + p.dealing_hi.toFixed(d) + '] · EQ ' +
            p.dealing_eq.toFixed(d) + ' · ' + (ZONE_VI[p.zone] || '') +
            (isFiniteNum(p.range_pos) ? ' · vị trí ' + (p.range_pos * 100).toFixed(0) + '%' : ''));
        }
      }
      if (p.liq_above !== undefined) {
        var roleHi = of === 1 ? ', cùng chiều' : (of === -1 ? ', ngược chiều' : '');
        var roleLo = of === -1 ? ', cùng chiều' : (of === 1 ? ', ngược chiều' : '');
        s.push('Vùng còn nguyên gần nhất: BSL ' + (isFiniteNum(p.liq_above) ? V.fp(p.liq_above, d) + ' (' + esc(p.liq_above_id) + roleHi + ')' : '—') +
          ' · SSL ' + (isFiniteNum(p.liq_below) ? V.fp(p.liq_below, d) + ' (' + esc(p.liq_below_id) + roleLo + ')' : '—') +
          (detail && p.pending_takes ? ' · ' + p.pending_takes + ' vùng đã lấy chờ sweep/run' : ''));
        if (detail && p.last_shift) {
          s.push('Shift gần nhất: ' + esc(DIR_VI[p.last_shift]) + ', ' + p.last_shift_bars + ' nến trước' +
            (p.last_shift_fvg ? ' (có FVG)' : '') + (p.pending_shifts ? ' · ' + p.pending_shifts + ' ứng viên shift đang chờ' : ''));
        } else if (detail && p.pending_shifts) {
          s.push(p.pending_shifts + ' ứng viên shift đang chờ');
        }
        s.push('Killzone: ' + esc(kzVi(p.killzone)) + (detail
          ? (p.displacement ? ' · nến displacement ' + esc(DIR_VI[p.displacement]) : '') +
            ' · FVG đang mở ' + p.open_fvg_up + ' tăng / ' + p.open_fvg_down + ' giảm'
          : ''));
      }
      var last = isFiniteNum(p.atr) ? 'ATR ' + p.atr.toFixed(d) : 'Chưa có ATR';
      if (p.gap) last += ' · trước nến này: khoảng trống ' + (GAP_VI[p.gap] || p.gap);
      s.push(last);
      return head + '<div class="tt-rule">' + s.join('<br>') + '</div>';
    },

    tooltipEvent: function (e, d) {
      if (e.algorithm !== ALGO) return '';
      var x = e.details || {}, out = [], t = e.structure_type, sv;
      function f(v) { return isFiniteNum(v) ? Number(v).toFixed(d) : '—'; }
      if (HTF_TYPES[t]) {
        var hx = V.htfEventText(e, d);
        if (hx) out.push(esc(hx.text));
      } else if (OF_TYPES[t]) {
        var trig = e.reference_event_id, rs = runSpanText(trig);
        out.push(ofSw(x.sang) + '<b>Order flow ' + esc(x.tu_vi || ofVi(x.tu)) + ' → ' + esc(x.sang_vi || ofVi(x.sang)) + '</b> · ' +
          esc(x.ly_do_vi || reasonVi(x.ly_do)));
        // Run: marker / dải ở nến BIẾT (xác nhận), còn giá lấy vùng từ W nến trước — ghi rõ cả hai.
        out.push('Kích hoạt: ' + (trig ? (rs ? esc(rs) : evShort(trig)) : '— (hai chiều cùng nến)'));
        var others = (x.basis || []).filter(function (b) { return b !== trig; });
        if (others.length) out.push('Cùng nến: ' + others.map(basisShort).join(' · '));
        out.push(prevSpanText(x));
      } else if (t === 'ICT_GAP') {
        out.push('Khoảng trống ' + esc(GAP_VI[x.loai] || x.loai) + ': ' + x.so_o_thieu + ' ô nến' +
          (x.so_o_trong_phien ? ' (' + x.so_o_trong_phien + ' ô trong phiên)' : '') + ' · lịch ' + esc(x.lich_phien));
      } else if (LIQ_TYPES[t]) {
        out.push('Vùng ' + esc(x.vung) + ' ' + esc(x.phia) + ' ' + f(x.muc) + ' (' + esc(x.tang) + ')' +
          (x.so_vung > 1 ? ' + ' + (x.so_vung - 1) + ' vùng khác' : '') + ' · lấy ở nến #' + x.nen_lay +
          ', xuyên ' + num(x.xuyen_atr, 2) + ' ATR');
        if (x.sweep_bars !== undefined) out.push('Close quay lại sau ' + x.sweep_bars + ' nến (W = ' + x.cua_so + ') · cực trị cú quét ' + f(x.cuc_tri_cu_quet));
        else if (x.loai_khoang_trong) out.push('Gặp khoảng trống ' + esc(GAP_VI[x.loai_khoang_trong] || x.loai_khoang_trong) + ' trước khi rõ');
        else out.push('Hết ' + x.cua_so + ' nến không quay lại');
      } else if (t === 'SHIFT_UP' || t === 'SHIFT_DOWN') {
        out.push('<b>Shift ' + esc(DIR_VI[x.chieu]) + '</b>: quét ' + (x.chieu === 'down' ? 'BSL' : 'SSL') + ' ' + f(x.muc_bi_quet) +
          ' (' + esc(x.tang) + ') ở nến #' + x.nen_sweep + ' → displacement ' + x.so_nen_tu_sweep + ' nến sau, close ' + f(e.price));
        out.push('Biên độ ' + num((x.displacement || {}).bien_do_atr, 2) + ' ATR · thân ' + num(((x.displacement || {}).than_ty_le || 0) * 100, 0) +
          '% · ' + (x.swept || []).length + ' vùng bị quét · ' + esc(kzVi(x.killzone)));
      } else if (t === 'SHIFT_FVG_UP' || t === 'SHIFT_FVG_DOWN') {
        out.push('FVG [' + f(x.lo) + ', ' + f(x.hi) + '] do chính nến displacement #' + x.nen_displacement + ' của shift tạo ra');
      } else if (t === 'DISPLACEMENT_UP' || t === 'DISPLACEMENT_DOWN') {
        out.push('Displacement: biên độ ' + num(x.bien_do_atr, 2) + ' ATR, thân ' + num((x.than_ty_le || 0) * 100, 0) + '% biên độ');
      } else if (t === 'FVG_UP' || t === 'FVG_DOWN') {
        out.push('FVG [' + f(x.lo) + ', ' + f(x.hi) + '] · ' + num(x.kich_thuoc_atr, 2) + ' ATR' + (x.from_displacement ? ' · nến giữa là displacement' : ''));
      } else if (t === 'FVG_TOUCHED' || t === 'FVG_FILLED') {
        out.push((t === 'FVG_TOUCHED' ? 'Chạm lần đầu' : 'Lấp') + ' FVG ' + esc(DIR_VI[x.chieu_fvg]) + ' [' + f(x.lo) + ', ' + f(x.hi) + '] (nến giữa #' + x.nen_giua_fvg + ')');
      } else if ((sv = subviewOf(t))) {
        out.push(esc(sv.view.eventText(e, d)));
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
        if (x.vung_thanh_khoan) {
          var v = x.vung_thanh_khoan;
          out.push('Vùng thanh khoản: ' + esc(POOL_STATUS_VI[v.trang_thai] || v.trang_thai) + (v.vung ? ' ' + esc(v.vung) : '') +
            (v.ly_do_vi ? ' — ' + esc(v.ly_do_vi) : ''));
        }
      }
      return '<br>' + out.join('<br>');
    }
  };

  // ------------------------------------------------------------------ trang Thử nghiệm

  /** Ghi chú dưới banner. Gọn: MỘT dòng ngắn về order flow + cảnh báo dữ liệu khi có (khoảng trống bất thường, ngoài
   * phiên, mô phỏng) — để chart đủ cao. Chi tiết: thêm mô tả đầy đủ, lịch phiên, shift / F1. */
  function notes(stats, dataStatus, pending, S) {
    var m = (stats && stats.chi_so_thuat_toan) || null;
    var ps = pending || {};
    var detail = !!(S && S.layers && S.layers.ict_detail);
    var out = [];
    if (!((m && m.order_flow) || ps.order_flow)) {
      out.push(['warn', 'Kết quả này <strong>chưa có order flow</strong> (phiên bản thuật toán cũ) — bấm <strong>Chạy thử</strong> ' +
        'để có dải order flow; vùng thanh khoản và shift vẫn vẽ.']);
    } else if (!detail) {
      out.push(['info', '<strong>Order flow</strong> (dải đáy): run/shift đặt chiều, run phía ngược → chưa rõ · mô tả, không ' +
        'dự báo · rê chuột vào đường BSL/SSL, Shift, FVG, dải để xem giải thích · cấu trúc: bật <strong>Chi tiết</strong>']);
    } else {
      out.push(['info', '<strong>Order flow</strong> (dải đáy chart) đọc theo thanh khoản: run hoặc shift đặt chiều; ' +
        '<strong>run phía ngược → chưa rõ</strong> (không lật ngay); shift lật thẳng; hai chiều cùng nến → chưa rõ. ' +
        'Là <strong>mô tả</strong> giá vừa lấy thanh khoản phía nào — không phải dự báo.']);
    }
    if (detail) {
      out.push(['info', '<strong>Chi tiết</strong>: STH/STL → ITH/ITL → thứ tự đỉnh/đáy, mức được bảo vệ, dealing range; ' +
        'vùng thanh khoản từ ITH/ITL (chạm → lấy → sweep / run); <strong>shift</strong> = sweep rồi displacement ngược chiều; ' +
        'FVG, displacement. <strong>Không có BOS/CHoCH</strong> (B1): đổi hướng chỉ đến từ shift. <strong>Khung lớn</strong> (H1/H4 ' +
        'gộp từ chính luồng nến, chỉ nến đã chốt; PDH/PDL, PWH/PWL; pd_bias; DOL): ngữ cảnh — đặc trưng, không lọc (D9, D11); ' +
        'bật lớp <strong>Khung lớn</strong> để vẽ ITH/ITL H4, range H4, FVG H4, nến H4 đang hình thành.']);
      var cal = (m && m.lich_phien) || ps.lich_phien;
      if (!cal || cal === 'none' || cal === 'auto') {
        out.push(['warn', 'Chưa chọn lịch phiên — mọi khoảng trống là «chưa chọn lịch», không phân biệt nghỉ phiên với thiếu dữ liệu.']);
      } else {
        out.push(['info', 'Khoảng trống phân loại theo lịch khai báo <code>' + esc(cal) + '</code>: giữ mức qua mọi khoảng ' +
          'trống; chặn cửa sổ pivot, bộ ba nến FVG, displacement nến đầu, cửa sổ sweep/shift vắt qua khoảng trống (D1).']);
      }
    }
    // Cảnh báo dữ liệu — mọi chế độ.
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
    if (S && S.dataset && S.dataset.is_synthetic) {
      out.push(['warn', 'Dataset <strong>MÔ PHỎNG</strong> — chỉ để thử công cụ.']);
    }
    if (detail) {
      out.push(['info', 'Shift là «shift có displacement» lúc phát hiện — chưa biết sẽ tiếp diễn hay thất bại. Chưa có nhãn ' +
        'tham chiếu ITH/ITL và shift (D8) — chưa có F1; thống kê ở tab Thống kê là mô tả hành vi.']);
    }
    return out;
  }

  var pct = V.pct1;
  function num(x, dg) { return x === null || x === undefined ? '—' : Number(x).toFixed(dg === undefined ? 2 : dg); }
  function cnt(x) { return x === null || x === undefined ? '—' : String(x); }
  function statBox(k, v, title) {
    return '<div class="stat-box"' + (title ? ' title="' + esc(title) + '"' : '') + '><div class="k">' + esc(k) +
      '</div><div class="v">' + esc(v) + '</div></div>';
  }

  /** Khối «Order flow (run + shift)» ở tab Thống kê — run_stats["order_flow"] của lõi (không có → rỗng). */
  function orderFlowStatsHtml(o) {
    if (!o) return '';
    var share = o.ty_le_thoi_gian || {};
    var parts = [['tang', 1], ['giam', -1], ['chua_ro', 0], ['chua_co', null]];
    var html = '<div class="section-title">Order flow (run + shift) — mô tả theo thanh khoản, không phải dự báo</div>';
    html += '<div class="regime-share" role="img" aria-label="Tỷ lệ thời gian theo order flow: ' + esc(parts.map(function (q) {
      return ofVi(q[1]) + ' ' + pct(share[q[0]]);
    }).join(', ')) + '">';
    parts.forEach(function (q) {
      var v = share[q[0]] || 0;
      if (v > 0) {
        html += '<span style="width:' + (v * 100).toFixed(2) + '%;background:' + ofColor(q[1]) + '" title="' +
          esc(ofVi(q[1]) + ' ' + pct(v)) + '"></span>';
      }
    });
    html += '</div><div class="of-share-legend">' + parts.map(function (q) {
      return '<span>' + ofSw(q[1]) + esc(ofVi(q[1])) + ' <b>' + pct(share[q[0]]) + '</b></span>';
    }).join('') + '<span class="muted">tỷ lệ thời gian, trạng thái sau mỗi nến</span></div>';
    html += '<div class="stat-grid">' +
      statBox('Đổi chiều mỗi ngày', num(o.doi_chieu_moi_ngay, 2) + ' (' + cnt(o.doi_chieu) + ')',
        'Đổi chiều thật: đoạn tăng/giảm có chiều khác đoạn tăng/giảm liền trước (có thể đi qua «chưa rõ»).') +
      statBox('Đoạn chưa rõ mỗi ngày', num(o.doan_chua_ro_moi_ngay, 2) + ' (' + cnt(o.doan_chua_ro) + ')',
        'Số đoạn «chưa rõ» (tính cả đoạn cuối đang mở) chia số ngày giao dịch.') +
      statBox('Chưa rõ kéo dài — trung vị (' + num(o.chua_ro_trung_vi_nen, 1) + ' nến)', num(o.chua_ro_trung_vi_gio, 1) + ' giờ') +
      statBox('Một chiều kéo dài — trung vị (' + num(o.mot_chieu_trung_vi_nen, 1) + ' nến)', num(o.mot_chieu_trung_vi_gio, 1) + ' giờ',
        'Độ dài trung vị của các đoạn tăng hoặc giảm liên tục.') +
      '</div>';
    var why = o.theo_ly_do || {};
    var keys = Object.keys(why).filter(function (k) { return why[k]; });
    html += '<p class="hint">Đổi trạng thái <b>' + cnt(o.doi_trang_thai) + '</b> lần (sự kiện ORDER_FLOW_*)' +
      (keys.length ? ' — theo lý do: ' + keys.map(function (k) { return esc(reasonVi(k)) + ' <b>' + why[k] + '</b>'; }).join(' · ') : '') +
      '</p>';
    if (o.ghi_chu_vi) html += '<p class="hint">' + esc(o.ghi_chu_vi) + '</p>';
    return html;
  }

  /** Khối «Order block, OTE» ở tab Thống kê — run_stats["order_block"] / ["ote"] của lõi 0.5.0 (không có → rỗng). */
  function obOteStatsHtml(ob, ot) {
    if (!ob || !ot) return '';
    return '<div class="section-title">Order block, OTE — mô tả hành vi, không phải tỷ lệ thắng</div><div class="stat-grid">' +
      statBox('OB mỗi ngày', num(ob.moi_ngay, 2) + ' (' + cnt(ob.xac_nhan) + ')',
        'Ứng viên ' + ob.ung_vien + ', xác nhận ' + pct(ob.ty_le_xac_nhan) + ' (giá vượt đầu xa); bỏ trước xác nhận ' +
        ob.bo_truoc_xac_nhan + '; không có nến ngược màu ' + ob.khong_co_nen_nguoc_mau) +
      statBox('OB chạm / hỏng / hết hạn', ob.cham + ' / ' + ob.hong + ' / ' + (ob.het_han + ob.het_han_vi_shift),
        'Hết hạn vì thời gian ' + ob.het_han + ', vì SHIFT ngược chiều ' + ob.het_han_vi_shift + '. Từ xác nhận tới chạm: trung vị ' +
        num(ob.nen_toi_cham_trung_vi, 0) + ' nến') +
      statBox('OB được chạm', pct(ob.ty_le_cham), 'Hỏng ngay lần chạm: ' + pct(ob.ty_le_hong_khi_cham)) +
      statBox('Nhịp OTE vào vùng', pct(ot.ty_le_vao) + ' (' + ot.vao + ' / ' + ot.nhip + ')',
        'Hỏng ' + ot.hong + ', hết hạn ' + ot.het_han + ', SHIFT ngược chiều ' + ot.het_han_vi_shift + ', bị SHIFT cùng chiều thay ' + ot.bi_thay) +
      statBox('Độ sâu khi vào OTE', 'TV ' + pct(ot.do_sau_trung_vi) + ' · P90 ' + pct(ot.do_sau_p90),
        'Vùng ' + pct(ot.tu) + '–' + pct(ot.den) + ' của nhịp; nhịp ≥ ' + ot.nhip_toi_thieu_atr + ' ATR') +
      '</div>';
  }

  /** Khối «Nhận diện» ở tab Thống kê — run_stats["nhan_dien"] của lõi 0.6.0 (không có → rỗng). */
  function ndStatsHtml(nd) {
    var rows = ND.statsRows(nd);
    if (!rows.length) return '';
    return '<div class="section-title">Nhận diện — khoảng giá, xác suất chạm (điểm thật chấm trên kết cục), trạng thái (mô tả)</div>' +
      '<div class="stat-grid">' + rows.map(function (r) { return statBox(r.k, r.v, r.title); }).join('') + '</div>' +
      (nd.ghi_chu_vi ? '<p class="hint">' + esc(nd.ghi_chu_vi) + '</p>' : '');
  }

  function statsHtml(m) {
    var box = statBox;
    var sw = m.swing || {};
    function rate(a, b) {
      return num((sw[a] || {}).moi_ngay, 2) + ' / ' + num((sw[b] || {}).moi_ngay, 2);
    }
    function count(a, b) {
      return (sw[a] || {}).so + ' / ' + (sw[b] || {}).so + ' swing trong khoảng chạy';
    }
    var o = m.ty_le_thoi_gian_order || {};
    var g = m.khoang_trong || {};
    var html = orderFlowStatsHtml(m.order_flow);
    html += '<div class="section-title">Cấu trúc ICT — swing, thứ tự, khoảng trống (mô tả hành vi, không phải accuracy)</div>';
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
    var dp = m.displacement, fv = m.fvg, lq = m.thanh_khoan, sh = m.shift;
    if (dp && fv && lq && sh) {
      var kz = Object.keys(sh.theo_killzone || {}).map(function (k) {
        return kzVi(k) + ' ' + sh.theo_killzone[k];
      }).join(' · ');
      var kzBars = Object.keys(m.killzone_ty_le_nen || {}).map(function (k) {
        return kzVi(k) + ' ' + pct(m.killzone_ty_le_nen[k]);
      }).join(' · ');
      html += '<div class="section-title">Thanh khoản, displacement, FVG, shift (giai đoạn 2)</div><div class="stat-grid">' +
        box('Shift mỗi ngày', num(sh.moi_ngay, 2) + ' (' + sh.so + ')',
          'Tăng ' + sh.tang + ' / giảm ' + sh.giam + '. Ứng viên ' + sh.ung_vien + ': huỷ vì vượt cực trị ' + sh.huy_vuot_cuc_tri +
          ', huỷ vì khoảng trống ' + sh.huy_khoang_trong + ', hết cửa sổ ' + sh.het_cua_so) +
        box('Shift có FVG', pct(sh.ty_le_co_fvg), sh.co_fvg + ' SHIFT_FVG · displacement ngay nến lấy: ' + sh.displacement_tren_nen_lay) +
        box('Shift theo killzone', kz || '—', 'Tỷ lệ nến theo killzone (để so): ' + kzBars) +
        box('Sweep / run / chưa rõ (vùng)', lq.vung_sweep + ' / ' + lq.vung_run + ' / ' + lq.vung_chua_ro,
          'W = ' + lq.cua_so_sweep + '. Sweep cùng nến lấy: ' + lq.vung_sweep_cung_nen + '. Sự kiện (gom theo nến, phía): ' +
          lq.su_kien_sweep + ' / ' + lq.su_kien_run + ' / ' + lq.su_kien_chua_ro) +
        box('Vùng thanh khoản mỗi ngày', num(lq.vung_moi_ngay, 2) + ' (' + esc(lq.tang) + ')',
          lq.vung_tao + ' vùng, gộp EQ ' + lq.gop_eq + ', không tạo vì đã bị lấy ' + lq.khong_tao_da_bi_lay) +
        box('Xuyên khi lấy (× ATR)', 'TV ' + num(lq.xuyen_atr_trung_vi, 2) + ' · P90 ' + num(lq.xuyen_atr_p90, 2),
          lq.bi_lay + ' vùng bị lấy; ' + lq.cham_truoc_khi_lay + ' (' + pct(lq.ty_le_cham_truoc_khi_lay) + ') từng bị chạm nông trước') +
        box('Displacement', pct(dp.ty_le_nen) + ' nến · ' + num(dp.moi_ngay, 1) + '/ngày', 'Tăng ' + dp.tang + ' / giảm ' + dp.giam) +
        box('FVG mỗi ngày', num(fv.moi_ngay, 1) + ' · ' + pct(fv.ty_le_tu_displacement) + ' từ displacement',
          fv.so + ' FVG; bỏ vì vắt khoảng trống ' + fv.bo_vi_khoang_trong + ', bỏ vì nhỏ ' + fv.bo_vi_nho + '; chạm ' + fv.cham + ', lấp ' + fv.lap) +
        '</div>';
    }
    html += obOteStatsHtml(m.order_block, m.ote);
    html += ndStatsHtml(m.nhan_dien);
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

  /** Khối «Order flow» đầu trạng thái replay (pending_state["order_flow"] của lõi; không có → rỗng). */
  function orderFlowPendingHtml(of, d) {
    if (!of) return '';
    var dir = of.trang_thai, directional = dir === 1 || dir === -1;
    var sup = of.ung_ho_gan_nhat;
    var html = '<div class="info-card of-card"><dl>' +
      '<dt>Order flow</dt><dd>' + ofSw(dir) + '<strong>' + esc(of.trang_thai_vi || ofVi(dir)) + '</strong>' +
        (isFiniteNum(of.tu_nen) ? ' · từ nến #' + of.tu_nen + (isFiniteNum(of.so_nen) ? ' (' + of.so_nen + ' nến)' : '') : '') + '</dd>' +
      '<dt>Lý do</dt><dd>' + (of.ly_do ? esc(of.ly_do_vi || reasonVi(of.ly_do)) : '—') +
        (of.su_kien ? ' · <span class="mono">' + evShort(of.su_kien) + '</span>' : '') + '</dd>';
    if (directional) {
      html += '<dt>Vùng cùng chiều</dt><dd class="mono">' + poolText(of.vung_cung_chieu, d) + '</dd>' +
        '<dt>Vùng ngược chiều</dt><dd class="mono">' + poolText(of.vung_nguoc_chieu, d) + ' <span class="muted">— bị run → chưa rõ</span></dd>';
    } else {
      html += '<dt>Vùng cùng / ngược chiều</dt><dd>— (order flow ' + esc(of.trang_thai_vi || ofVi(dir)) + ', chưa có chiều)</dd>';
    }
    if (sup) {
      html += '<dt>Ủng hộ gần nhất</dt><dd>' + esc(sup.loai) + ' cùng chiều ở nến #' + sup.nen +
        (sup.su_kien ? ' · <span class="mono">' + evShort(sup.su_kien) + '</span>' : '') + '</dd>';
    }
    var cond = of.dieu_kien_vi || [];
    html += '<dt>Đổi khi</dt><dd>' + (cond.length ? cond.map(function (c) { return '• ' + esc(c); }).join('<br>') : '—') + '</dd>' +
      '</dl></div>';
    return html;
  }

  function pendingHtml(ps, d) {
    if (!ps.ict) return null;
    function f(x) { return x === null || x === undefined ? '—' : Number(x).toFixed(d); }
    function sw(x) { return x ? f(x.gia) + ' (nến #' + x.nen + ', biết lúc #' + x.xac_nhan_tai + ')' : '— chưa có —'; }
    var c = ps.cau_truc || {}, r = ps.dealing_range || {}, mb = c.muc_bao_ve;
    var cmpVi = function (v, hi) { return v === null || v === undefined ? '—' : (v === 1 ? (hi ? 'HH' : 'HL') : (v === -1 ? (hi ? 'LH' : 'LL') : (hi ? 'EQH' : 'EQL'))); };
    var gaps = Object.keys(ps.khoang_trong || {}).map(function (k) { return (GAP_VI[k] || k) + ' ' + ps.khoang_trong[k]; }).join(' · ');
    var html = orderFlowPendingHtml(ps.order_flow, d) + linesCardHtml('Khung lớn (chỉ nến đã chốt)', V.htfExplain(ps, d)) +
      SUBVIEWS.map(function (sv) { return linesCardHtml(sv.title, sv.view.pendingLines(ps, d)); }).join('') +
      '<div class="info-card"><dl>' +
      '<dt>Thứ tự (cấp ' + esc(ps.cap_cau_truc) + ')</dt><dd><strong>' + esc(c.order_vi || orderVi(c.order)) + '</strong> · so đỉnh ' +
        cmpVi(c.hh, true) + ' · so đáy ' + cmpVi(c.hl, false) + '</dd>' +
      '<dt>Đỉnh / đáy cấu trúc gần nhất</dt><dd class="mono">' + sw(c.dinh_gan_nhat) + ' / ' + sw(c.day_gan_nhat) + '</dd>' +
      '<dt>Mức được bảo vệ</dt><dd class="mono">' + (mb ? (mb.phia === 'low' ? 'đáy ' : 'đỉnh ') + sw(mb) +
        (c.muc_bao_ve_bi_vuot ? ' — close đã vượt ở nến #' + c.bi_vuot_tai_nen : '') : '— không có (thứ tự lẫn lộn / chưa đủ) —') + '</dd>' +
      '<dt>Dealing range</dt><dd class="mono">' + (r && r.hi !== null && r.hi !== undefined
        ? '[' + f(r.lo) + ', ' + f(r.hi) + '] · EQ ' + f(r.eq) + ' · ' + esc(ZONE_VI[r.zone] || '') + ' · ' + (r.range_pos * 100).toFixed(0) + '%'
        : '— chưa đủ đỉnh và đáy —') + '</dd>';
    var lq = ps.thanh_khoan;
    if (lq) {
      var cn = lq.con_nguyen || {};
      html += '<dt>Vùng còn nguyên gần nhất</dt><dd class="mono">trên: ' + poolText(lq.gan_nhat_phia_tren, d) +
        '<br>dưới: ' + poolText(lq.gan_nhat_phia_duoi, d) + '<br>còn nguyên: ' + (cn.BSL || 0) + ' BSL / ' + (cn.SSL || 0) + ' SSL</dd>' +
        '<dt>Đã lấy, chờ sweep / run</dt><dd>' + ((lq.dang_cho_sweep_run || []).map(function (p) {
          return esc(p.id) + ' (lấy ở #' + p.nen_lay + ', còn ' + p.con_lai_nen + ' nến): cần close ' + esc(p.can_close);
        }).join('<br>') || '—') + '</dd>';
      var sh = ps.shift || {};
      html += '<dt>Ứng viên shift</dt><dd>' + ((sh.dang_cho || []).map(function (c2) {
          return esc(DIR_VI[c2.chieu]) + ' sau sweep #' + c2.nen_sweep + ' (hạn nến #' + c2.han_chot + '): ' + esc(c2.can);
        }).join('<br>') || '—') + '</dd>' +
        '<dt>Shift gần nhất</dt><dd>' + (sh.gan_nhat ? esc(DIR_VI[sh.gan_nhat.dir]) + ' ở nến #' + sh.gan_nhat.d +
          (sh.gan_nhat.fvg ? ' · có FVG' : '') + ' · <span class="mono">' + esc(sh.gan_nhat.group_id) + '</span>' : '—') + '</dd>' +
        '<dt>Killzone · FVG đang mở</dt><dd>' + esc(kzVi(ps.killzone)) + ' · ' + ((ps.fvg_dang_mo || {}).up || 0) + ' tăng / ' +
          ((ps.fvg_dang_mo || {}).down || 0) + ' giảm</dd>';
    }
    html += '<dt>ATR</dt><dd class="mono">' + f(ps.atr_hien_tai) + '</dd>' +
      '<dt>Khoảng trống (lịch ' + esc(ps.lich_phien) + ')</dt><dd>' + (gaps || '—') + '</dd>' +
      '</dl><p class="hint">' + esc(ps.ghi_chu_vi || '') + '</p></div>';
    return html;
  }

  /** Dòng panel chi tiết cho sự kiện khung lớn / PD / DOL (0.4.0). `row(k, html)`, `f(giá)`. */
  function htfDetailRows(e, x, d, row, f) {
    var t = e.structure_type, hx = V.htfEventText(e, d);
    if (hx) row('Ý nghĩa', esc(hx.text));
    function when(k) { return x[k] ? esc(fmtIso(x[k])) : '—'; }
    if (t === 'HTF_SWING_HIGH' || t === 'HTF_SWING_LOW') {
      row('Khung', esc(x.khung) + ' · nến ' + esc(x.khung) + ' #' + x.nen_htf + ' mở ' + when('mo_nen_htf') + ' (nến ' + esc(x.khung) + ' trái #' +
        x.nen_htf_trai + ' ' + f(x.gia_trai) + ', phải #' + x.nen_htf_phai + ' ' + f(x.gia_phai) + ')');
      row('Chốt / biết', 'period_end ' + when('period_end') + ' · known_at ' + when('known_at') + (x.chot_muon ? ' · <b>chốt muộn</b>' : '') +
        ' · coverage ' + num(x.coverage, 2));
      row('So với swing cùng phía trước', x.nhan ? esc(x.nhan) + ': ' + f(x.gia_truoc) + ' → ' + f(e.price) + ' (dung sai ±' + f(x.dung_sai) + ')'
        : 'chưa so — ' + esc(x.ly_do_chua_so || ''));
      row('Thứ tự ' + esc(x.khung) + ' sau swing', esc(x.order_sau_vi || orderVi(x.order_sau)) +
        (isFiniteNum(x.muc_bao_ve_sau) ? ' · mức được bảo vệ ' + f(x.muc_bao_ve_sau) : ''));
    } else if (t === 'HTF_FVG_UP' || t === 'HTF_FVG_DOWN') {
      row('Vùng', '[' + f(x.lo) + ', ' + f(x.hi) + '] · CE ' + f(x.ce) + ' · ' + num(x.kich_thuoc_atr, 2) + ' × ATR ' + esc(x.khung) +
        (x.from_displacement ? ' · nến giữa là displacement' : ''));
      row('Ba nến ' + esc(x.khung), '#' + x.nen_htf_1 + ' – #' + x.nen_htf_giua + ' – #' + x.nen_htf_3 + ' · nến giữa = nến khung chạy #' +
        x.nen_giua_tu + '–#' + x.nen_giua_den + ' (mở ' + when('mo_nen_giua') + ')');
      row('Chốt / hiệu lực', 'known_at ' + when('known_at') + ' · hiệu lực từ nến #' + x.hieu_luc_tu_nen);
    } else if (t === 'HTF_PERIOD_HIGH' || t === 'HTF_PERIOD_LOW') {
      row('Kỳ', esc(x.ten) + ' — ' + (x.khung === 'W' ? 'tuần' : 'ngày giao dịch') + ' mở ' + when('mo_ky') + ' → period_end ' + when('period_end') +
        ' · known_at ' + when('known_at') + (x.chot_muon ? ' · <b>chốt muộn</b>' : '') + ' · coverage ' + num(x.coverage, 2));
    } else if (t === 'HTF_BAR_DEGRADED') {
      row('Nến khung lớn', esc(x.khung) + ' mở ' + when('mo') + ' · ' + x.n_bars + '/' + x.expected_bars + ' nến (coverage ' + num(x.coverage, 2) +
        ', ngưỡng ' + esc(x.nguong_coverage) + ') · lý do ' + esc(x.ly_do_degraded || ''));
    } else if (t === 'DOL_REACHED') {
      var v = x.vung || {};
      row('Đích', esc(v.id) + ' ' + esc(v.phia) + ' ' + f(x.muc) + ' · tầng ' + esc(x.tang) + ' · nguồn ' + (v.nguon || []).map(function (s) {
        return '<span class="mono">' + esc(s) + '</span>'; }).join(', '));
      row('Shift đặt DOL', '<span class="mono">' + esc(x.shift) + '</span> (nến #' + x.nen_dat_dol + ', ' + x.so_nen_tu_shift + ' nến trước; lúc đặt cách ' +
        num(x.khoang_cach_atr_luc_dat, 1) + ' ATR)');
      row('Lưu ý', esc(x.ghi_chu_vi || ''));
    } else {   // PD_*
      row('FVG', esc(x.khung) + ' ' + esc(DIR_VI[x.chieu_fvg] || x.chieu_fvg) + ' [' + f(x.lo) + ', ' + f(x.hi) + '] · CE ' + f(x.ce) +
        ' · <span class="mono">' + esc(x.fvg) + '</span>');
      row('Kết quả', esc(PD_RESULT_VI[x.ket_qua] || x.ket_qua) + ' (chế độ ' + esc(x.che_do) + '): ' + esc(x.quy_tac_vi || '') + ' · close ' +
        f(x.close) + ' · chạm ở nến #' + x.nen_cham + ' (' + x.so_nen_tu_cham + ' nến trước)');
      row('pd_bias sau nến này', esc(x.pd_bias_sau === 0 ? 'mâu thuẫn trong cùng nến (0)' : ofVi(x.pd_bias_sau)) +
        (x.pd_bias_khung ? ' (' + esc(x.pd_bias_khung) + ')' : ''));
    }
  }

  /** Một khối «tiêu đề: các dòng» ở trạng thái replay (tab Thống kê) — cùng câu với khung «Thuật toán đang làm gì». */
  function linesCardHtml(title, lines) {
    if (!lines.length) return '';
    return '<div class="info-card"><dl><dt>' + esc(title) + '</dt><dd>' +
      lines.map(function (l) { return esc(l.text); }).join('<br>') + '</dd></dl></div>';
  }

  function eventDetail(e, S) {
    var x = e.details || {}, d = S.digits, rows = [], t = e.structure_type, sv;
    function row(k, v) { rows.push('<dt>' + esc(k) + '</dt><dd>' + v + '</dd>'); }
    function f(v) { return v === null || v === undefined ? '—' : Number(v).toFixed(d); }
    row('Loại', esc(t) + ' — ' + esc(e.structure_text_vi || ''));
    row('Nến sự kiện', '#' + e.event_bar_index + ' · ' + esc(fmtIso(e.event_time)) + ' · ' + esc(kzVi(x.killzone)));
    row('Biết lúc', '#' + e.confirmed_bar_index + ' · ' + esc(fmtIso(e.confirmed_at)) + ' · trễ ' + e.confirmation_lag_bars + ' nến');
    if (HTF_TYPES[t]) {
      htfDetailRows(e, x, d, row, f);
    } else if ((sv = subviewOf(t))) {
      row('Ý nghĩa', esc(sv.view.eventText(e, d)));
      if (x.basis) row('Dựa trên', x.basis.map(function (b) { return '<span class="mono">' + esc(b) + '</span>'; }).join('<br>'));
      row('Lưu ý', esc(sv.note));
    } else if (OF_TYPES[t]) {
      row('Order flow', ofSw(x.tu) + esc(x.tu_vi || ofVi(x.tu)) + ' → ' + ofSw(x.sang) + '<b>' + esc(x.sang_vi || ofVi(x.sang)) + '</b>');
      row('Lý do', esc(x.ly_do_vi || reasonVi(x.ly_do)) + (x.ly_do ? ' <span class="muted">(' + esc(x.ly_do) + ')</span>' : ''));
      var rsd = runSpanText(e.reference_event_id);
      row('Sự kiện kích hoạt', e.reference_event_id
        ? '<span class="mono">' + esc(e.reference_event_id) + '</span>' +
          (rsd ? '<br>' + esc(rsd) + ' — dải order flow đổi ở nến biết' : '')
        : '— không có (run/shift hai chiều trong cùng nến)');
      var basis = x.basis || [];
      row('Run / shift cùng nến (' + basis.length + ')', basis.map(function (b) {
        var rb = runSpanText(b);
        return '<span class="mono">' + esc(b) + '</span>' + (rb ? ' — ' + esc(rb) : '');
      }).join('<br>') || '—');
      row('Trạng thái cũ', prevSpanText(x));
      row('Quy tắc', 'Run hoặc shift đặt chiều; run phía ngược với order flow đang có → chưa rõ (không lật ngay); ' +
        'shift lật thẳng; hai chiều cùng nến → chưa rõ; cùng chiều chỉ «ủng hộ» (không phát sự kiện).');
      row('Lưu ý', 'Mô tả giá vừa lấy thanh khoản phía nào — không phải dự báo, không phải tín hiệu.');
    } else if (t === 'ICT_GAP') {
      row('Khoảng trống', esc(GAP_VI[x.loai] || x.loai) + (x.bat_thuong ? ' — <b>bất thường</b>' : ''));
      row('Từ → đến', esc(fmtIso(x.tu)) + ' → ' + esc(fmtIso(x.den)) + ' (' + x.so_o_thieu + ' ô nến)');
      if (x.so_o_trong_phien !== null && x.so_o_trong_phien !== undefined) row('Ô thiếu trong phiên', String(x.so_o_trong_phien));
      row('Chính sách', esc(x.chinh_sach || ''));
    } else if (LIQ_TYPES[t]) {
      row('Vùng chính', esc(x.vung) + ' ' + esc(x.phia) + ' mức ' + f(x.muc) + ' · tầng ' + esc(x.tang));
      row('Lấy', 'nến #' + x.nen_lay + ' · xuyên ' + num(x.xuyen_atr, 2) + ' × ATR khoá ' + f(x.atr_khoa) + ' · cực trị cú quét ' + f(x.cuc_tri_cu_quet));
      if (x.sweep_bars !== undefined) row('Quay lại', 'close quay lại sau ' + x.sweep_bars + ' nến' + (x.cung_nen_lay ? ' (ngay nến lấy)' : '') + ' · cửa sổ W = ' + x.cua_so);
      if (x.so_nen_sau_lay !== undefined) row('Run', 'hết ' + x.cua_so + ' nến không quay lại');
      if (x.loai_khoang_trong) row('Chưa rõ', 'gặp khoảng trống ' + esc(GAP_VI[x.loai_khoang_trong] || x.loai_khoang_trong));
      if (x.group_id) row('group_id', '<span class="mono">' + esc(x.group_id) + '</span>');
      row('Các vùng (' + x.so_vung + ')', (x.pools || []).map(function (p) {
        return esc(p.id) + ' ' + f(p.muc) + ' (nguồn ' + (p.nguon || []).length + ', lấy #' + p.nen_lay + ', xuyên ' + num(p.xuyen_atr, 2) + ' ATR' +
          (p.so_lan_cham ? ', chạm trước ' + p.so_lan_cham + ' lần' : '') + ')';
      }).join('<br>'));
    } else if (t === 'SHIFT_UP' || t === 'SHIFT_DOWN') {
      row('Chuỗi', 'quét ' + (x.chieu === 'down' ? 'BSL' : 'SSL') + ' ' + f(x.muc_bi_quet) + ' ở nến #' + x.nen_sweep + ' → displacement ' +
        esc(DIR_VI[x.chieu]) + ' ở nến #' + e.event_bar_index + ' (' + x.so_nen_tu_sweep + ' nến sau, cửa sổ ' + x.cua_so + ')');
      row('Điều kiện', 'close ' + f(e.price) + (x.chieu === 'down' ? ' < ' : ' > ') + 'mức bị quét ' + f(x.muc_bi_quet) +
        ' · không nến nào ' + (x.chieu === 'down' ? 'high > ' : 'low < ') + f(x.cuc_tri_cu_quet) + ' · không khoảng trống');
      var dp = x.displacement || {};
      row('Displacement', 'biên độ ' + num(dp.bien_do_atr, 2) + ' × ATR ' + f(dp.atr) + ' · thân ' + num((dp.than_ty_le || 0) * 100, 0) + '%' +
        (x.displacement_tren_nen_lay ? ' · ngay trên nến lấy' : ''));
      row('Vùng bị quét (' + (x.swept || []).length + ')', (x.swept || []).map(function (s) {
        return esc(s.vung) + ' ' + f(s.muc) + ' (' + esc(s.tang) + ', lấy #' + s.nen_lay + ', sweep #' + s.nen_sweep + ')';
      }).join('<br>'));
      row('group_id', '<span class="mono">' + esc(x.group_id) + '</span>');
      row('Lưu ý', esc(x.ghi_chu_vi || ''));
    } else if (t === 'SHIFT_FVG_UP' || t === 'SHIFT_FVG_DOWN') {
      row('FVG', '[' + f(x.lo) + ', ' + f(x.hi) + '] · nến giữa = nến displacement #' + x.nen_displacement);
      row('Shift', '<span class="mono">' + esc(x.shift) + '</span>');
      row('group_id', '<span class="mono">' + esc(x.group_id) + '</span>');
    } else if (t === 'DISPLACEMENT_UP' || t === 'DISPLACEMENT_DOWN') {
      row('Đo', 'biên độ ' + num(x.bien_do_atr, 2) + ' × ATR ' + f(x.atr) + ' · thân ' + num((x.than_ty_le || 0) * 100, 0) + '% biên độ');
      row('Ngưỡng', esc(x.nguong_vi || ''));
    } else if (t === 'FVG_UP' || t === 'FVG_DOWN') {
      row('Vùng', '[' + f(x.lo) + ', ' + f(x.hi) + '] · ' + num(x.kich_thuoc_atr, 2) + ' ATR · nến #' + x.nen_1 + ' – #' + x.nen_3);
      row('Nến giữa', x.from_displacement ? 'là displacement cùng chiều' : 'không phải displacement');
    } else if (t === 'FVG_TOUCHED' || t === 'FVG_FILLED') {
      row('FVG', esc(DIR_VI[x.chieu_fvg]) + ' [' + f(x.lo) + ', ' + f(x.hi) + '] · nến giữa #' + x.nen_giua_fvg + ' · ' + x.so_nen_tu_khi_biet + ' nến sau khi biết');
      if (x.cham_tai_nen !== undefined && x.cham_tai_nen !== null) row('Chạm lần đầu', 'nến #' + x.cham_tai_nen);
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
      if (x.vung_thanh_khoan) {
        var v = x.vung_thanh_khoan;
        row('Vùng thanh khoản', esc(POOL_STATUS_VI[v.trang_thai] || v.trang_thai) + (v.vung ? ' ' + esc(v.vung) + ' mức ' + f(v.muc_vung) +
          ' (hiệu lực từ nến #' + v.hieu_luc_tu_nen + ')' : '') + (v.ly_do_vi ? ' — ' + esc(v.ly_do_vi) : ''));
      }
    }
    if (e.reference_event_id && !OF_TYPES[t]) row('Tham chiếu', '<span class="mono">' + esc(e.reference_event_id) + '</span>');
    return '<h4>Chi tiết sự kiện được chọn</h4><dl>' + rows.join('') + '</dl>';
  }

  /** Lớp viền của dòng giải thích theo trạng thái order flow (màu kèm chữ trong chính dòng đó). */
  function ofXpKind(v) { return v === 1 ? 'of-up' : (v === -1 ? 'of-down' : (v === 0 ? 'of-unk' : 'state')); }

  /** Một dòng «Thuật toán đang làm gì» cho sự kiện ORDER_FLOW_* ở nến con trỏ. */
  function ofExplainHtml(e, params) {
    var x = e.details || {}, why = x.ly_do, from = x.tu, to = x.sang;
    var head = '<b>Order flow: ' + esc(x.tu_vi || ofVi(from)) + ' → ' + esc(String(x.sang_vi || ofVi(to)).toUpperCase()) + '</b> — ';
    var W = params.sweep_window !== undefined && params.sweep_window !== null ? ' trong ' + esc(params.sweep_window) + ' nến' : '';
    var body;
    if (why === 'run_tang' || why === 'run_giam') {
      var up = why === 'run_tang', rr = runSpan(e.reference_event_id), late = !!(rr && rr.t > rr.b);
      body = 'run ' + (up ? 'lên: BSL bị lấy' : 'xuống: SSL bị lấy') + (rr ? ' ở nến #' + rr.b : '') + ' và close không quay lại' +
        (late ? ' trong ' + (rr.t - rr.b) + ' nến → biết ở nến này' : W) +
        (from === 0 ? ' — thoát «chưa rõ»' : (from === null || from === undefined ? ' — lần đặt chiều đầu tiên' : '')) + '.';
    } else if (why === 'shift_tang' || why === 'shift_giam') {
      var up2 = why === 'shift_tang';
      body = 'shift ' + (up2 ? 'tăng (quét SSL rồi displacement tăng)' : 'giảm (quét BSL rồi displacement giảm)') + ' ở nến này' +
        ((from === 1 || from === -1) ? ' — shift lật thẳng, không qua «chưa rõ»' : '') + '.';
    } else if (why === 'run_nguoc_chieu') {
      var ro = runSpan(e.reference_event_id);
      body = 'run phía ngược với order flow đang có (' + esc(x.tu_vi || ofVi(from)) + ')' +
        (ro ? ' — ' + ro.side + ' lấy ở nến #' + ro.b + (ro.t > ro.b ? ', biết ở nến này' : '') : '') +
        ': không lật ngay mà thành «chưa rõ»; run hoặc shift kế tiếp sẽ đặt chiều.';
    } else if (why === 'hai_chieu_cung_nen') {
      body = 'có run/shift cả chiều lên lẫn chiều xuống trong cùng nến → chưa rõ.';
    } else {
      body = esc(x.ly_do_vi || e.reason_text_vi || '');
    }
    var span = isFiniteNum(x.trang_thai_cu_so_nen) ? ' <span class="muted">Trạng thái cũ kéo dài ' + x.trang_thai_cu_so_nen + ' nến.</span>' : '';
    return head + body + span;
  }

  /** Khung «Thuật toán đang làm gì» tại nến `bar` (= con trỏ replay): order flow, chuỗi quét → displacement → FVG.
   * Chỉ đọc sự kiện / timeline / pending_state đã có. */
  function explain(r, bar, S) {
    var d = S.digits;
    function f(x) { return x === null || x === undefined || !isFinite(x) ? '—' : Number(x).toFixed(d); }
    var i = r.cursor;
    var ps = (r.snapshot && r.snapshot.pending_state) || {};
    var params = (r.snapshot && r.snapshot.params) || {};
    var out = [];
    function add(kind, html) { out.push('<div class="xp xp-' + kind + '">' + html + '</div>'); }
    var here = [];
    for (var k = r.events.length - 1; k >= 0 && r.events[k].confirmed_bar_index >= i; k--) {
      if (r.events[k].confirmed_bar_index === i) here.unshift(r.events[k]);
    }
    var tlPrev = null, tlNow = null;
    for (var j = r.timeline.length - 1; j >= 0 && r.timeline[j].bar_index >= i - 1; j--) {
      if (r.timeline[j].bar_index === i) tlNow = r.timeline[j];
      if (r.timeline[j].bar_index === i - 1) tlPrev = r.timeline[j];
    }
    var ofs = ps.order_flow || null;
    var atr = ps.atr_hien_tai;
    function dist(p) { return p && isFiniteNum(atr) && atr > 0 ? ' — cách ' + (Math.abs(p.muc - bar.close) / atr).toFixed(1) + ' ATR' : ''; }

    // 1. Nến này
    out.push('<div class="xp-sec">Nến này: H ' + f(bar.high) + ' · L ' + f(bar.low) + ' · C ' + f(bar.close) + ' · ' +
      esc(kzVi(tlNow ? tlNow.killzone : null)) + ' · ngưỡng dùng ATR nến trước = ' + f(tlPrev ? tlPrev.atr : null) + '</div>');
    var touched = 0, filled = 0, sth = 0, ofHere = 0, flowInputs = 0;
    here.forEach(function (e) {
      var x = e.details || {}, t = e.structure_type;
      if (FLOW_INPUT_TYPES[t]) flowInputs++;
      if (HTF_TYPES[t]) {   // khung lớn / PD / DOL (0.4.0): câu dựng sẵn từ details của chính sự kiện
        var hx = V.htfEventText(e, d);
        if (hx) add(hx.kind, '<b>' + esc(t) + '</b>: ' + esc(hx.text));
        return;
      }
      var sv = subviewOf(t);
      if (sv) {   // view phụ: order block / OTE (0.5.0), trạng thái (0.6.0)
        add(sv.view.meta(t).end === 'expired' ? 'muted' : 'info', '<b>' + esc(t) + '</b>: ' + esc(sv.view.eventText(e, d)));
        return;
      }
      if (OF_TYPES[t]) {
        ofHere++;
        add(ofXpKind(x.sang), ofSw(x.sang) + ofExplainHtml(e, params));
      } else if (t === 'ICT_GAP') {
        add('warn', '<b>Khoảng trống ' + esc(GAP_VI[x.loai] || x.loai) + '</b> trước nến này: vùng đã lấy đang chờ → «chưa rõ»; ' +
          'ứng viên shift bị huỷ; không xét displacement ở nến này; FVG vắt qua bị loại. Mức/vùng vẫn giữ.');
      } else if (t === 'LIQ_SWEEP_BSL' || t === 'LIQ_SWEEP_SSL') {
        var hi = x.phia === 'BSL';
        add('ok', '<b>Sweep ' + esc(x.phia) + '</b> vùng ' + esc(x.vung) + ' ' + f(x.muc) + (x.so_vung > 1 ? ' (+' + (x.so_vung - 1) + ' vùng)' : '') +
          ': lấy ở nến #' + x.nen_lay + ' (xuyên ' + num(x.xuyen_atr, 2) + ' ATR ≥ ' + esc(params.min_pen_atr) + '), close nến này ' +
          (hi ? '< ' : '> ') + 'mức → quay lại sau ' + x.sweep_bars + ' nến. Cực trị cú quét ' + f(x.cuc_tri_cu_quet) +
          '. Mở ứng viên shift <b>' + (hi ? 'giảm' : 'tăng') + '</b> tới nến #' + (i + (params.shift_window || 0)) + '.');
      } else if (t === 'LIQ_RUN_UP' || t === 'LIQ_RUN_DOWN') {
        add('info', '<b>Run ' + esc(x.phia) + '</b> vùng ' + esc(x.vung) + ' ' + f(x.muc) + ': lấy ở nến #' + x.nen_lay + ', hết ' + x.cua_so +
          ' nến mà close không quay lại → giá đi luôn, không phải sweep.');
      } else if (t === 'LIQ_UNRESOLVED') {
        add('warn', '<b>Chưa rõ</b> vùng ' + esc(x.vung) + ' ' + esc(x.phia) + ': đã lấy ở nến #' + x.nen_lay + ' nhưng gặp khoảng trống ' +
          esc(GAP_VI[x.loai_khoang_trong] || x.loai_khoang_trong) + ' trước khi rõ sweep hay run.');
      } else if (t === 'DISPLACEMENT_UP' || t === 'DISPLACEMENT_DOWN') {
        add('info', '<b>Displacement ' + (t === 'DISPLACEMENT_UP' ? 'tăng' : 'giảm') + '</b>: biên độ ' + num(x.bien_do_atr, 2) + ' ATR ≥ ' +
          esc(params.k_disp) + ', thân ' + num((x.than_ty_le || 0) * 100, 0) + '% ≥ ' + num((params.body_min || 0) * 100, 0) + '%.');
      } else if (t === 'FVG_UP' || t === 'FVG_DOWN') {
        add('info', '<b>FVG ' + (t === 'FVG_UP' ? 'tăng' : 'giảm') + '</b> [' + f(x.lo) + ', ' + f(x.hi) + '] từ nến #' + x.nen_1 + '–#' + x.nen_3 +
          (x.from_displacement ? ' — nến giữa là displacement cùng chiều.' : ' — nến giữa không phải displacement (FVG thô).'));
      } else if (t === 'FVG_TOUCHED') {
        touched++;
      } else if (t === 'FVG_FILLED') {
        filled++;
      } else if (t === 'SHIFT_UP' || t === 'SHIFT_DOWN') {
        var dn = x.chieu === 'down';
        add('ok', '<b>SHIFT ' + (dn ? 'GIẢM' : 'TĂNG') + '</b>: quét ' + (dn ? 'BSL' : 'SSL') + ' ' + f(x.muc_bi_quet) + ' ở nến #' + x.nen_sweep +
          ' → nến này là displacement ' + (dn ? 'giảm' : 'tăng') + ' (' + x.so_nen_tu_sweep + ' nến sau sweep), close ' + f(bar.close) +
          (dn ? ' < ' : ' > ') + f(x.muc_bi_quet) + '; chưa nến nào ' + (dn ? 'high > ' : 'low < ') + f(x.cuc_tri_cu_quet) +
          '; không khoảng trống. ' + ((x.swept || []).length > 1 ? (x.swept.length) + ' vùng bị quét gom vào một shift. ' : '') +
          'Chưa biết sẽ tiếp diễn hay thất bại.');
      } else if (t === 'SHIFT_FVG_UP' || t === 'SHIFT_FVG_DOWN') {
        add('ok', '<b>SHIFT_FVG</b>: FVG ' + (t === 'SHIFT_FVG_UP' ? 'tăng' : 'giảm') + ' [' + f(x.lo) + ', ' + f(x.hi) + '] biết ở nến này có nến ' +
          'giữa = nến displacement #' + x.nen_displacement + ' của shift (cùng group). Shift không bị sửa.');
      } else {
        var lvl = LEVEL_OF[t];
        if (lvl === 1) { sth++; return; }
        var v = x.vung_thanh_khoan;
        add('info', '<b>' + esc(x.ten) + '</b> ở nến #' + e.event_bar_index + ' ' + f(e.price) + ' xác nhận' +
          (x.nhan ? ' (' + esc(x.nhan) + ')' : '') +
          (v ? ' → ' + esc(POOL_STATUS_VI[v.trang_thai] || v.trang_thai) + (v.vung ? ' ' + esc(v.vung) + ' ' + f(v.muc_vung) + ', hiệu lực từ nến sau' : '') +
            (v.ly_do_vi ? ' (' + esc(v.ly_do_vi) + ')' : '') : '') + '.');
      }
    });
    if (ofs && flowInputs && !ofHere) {
      add('muted', ofs.trang_thai === 0
        ? 'Run/shift ở nến này không đặt được chiều (vẫn chưa rõ) — order flow giữ nguyên, không phát sự kiện.'
        : 'Run/shift ở nến này cùng chiều order flow (' + esc(ofs.trang_thai_vi || ofVi(ofs.trang_thai)) + ') → chỉ «ủng hộ»: ' +
          'trạng thái giữ nguyên, không phát sự kiện.');
    }
    if (sth) add('muted', sth + ' STH/STL xác nhận ở nến này (nguyên liệu).');
    if (touched || filled) add('muted', (touched ? touched + ' FVG bị chạm lần đầu' : '') + (touched && filled ? ' · ' : '') + (filled ? filled + ' FVG đã lấp' : '') + '.');
    if (!here.length) add('muted', 'Không có sự kiện ở nến này.');

    // 2. Đang theo dõi — dòng đầu là order flow hiện tại + điều kiện đổi
    out.push('<div class="xp-sec">Đang theo dõi</div>');
    var dirNow = ofs ? ofs.trang_thai : null, directional = dirNow === 1 || dirNow === -1;
    if (ofs) {
      var line = ofSw(dirNow) + 'Order flow <b>' + esc(ofs.trang_thai_vi || ofVi(dirNow)) + '</b>' +
        (isFiniteNum(ofs.tu_nen) ? ' từ nến #' + ofs.tu_nen + ' (' + ofs.so_nen + ' nến' +
          (ofs.ly_do ? ' · ' + esc(reasonVi(ofs.ly_do)) : '') + ')' : '') + '.';
      if (directional) {
        line += '<br>Vùng cùng chiều: ' + poolText(ofs.vung_cung_chieu, d) + dist(ofs.vung_cung_chieu) +
          '<br>Vùng ngược chiều (bị run → chưa rõ): ' + poolText(ofs.vung_nguoc_chieu, d) + dist(ofs.vung_nguoc_chieu);
      }
      var cond = ofs.dieu_kien_vi || [];
      if (cond.length) line += '<br>Đổi khi:<br>' + cond.map(function (c) { return '• ' + esc(c); }).join('<br>');
      add(ofXpKind(dirNow), line);
    }
    var lq = ps.thanh_khoan || {}, sh = ps.shift || {};
    (lq.dang_cho_sweep_run || []).forEach(function (p) {
      add('state', 'Vùng ' + esc(p.id) + ' (' + esc(p.phia) + ' ' + f(p.muc) + ') đã lấy ở nến #' + p.nen_lay + ': cần close ' + esc(p.can_close) +
        ' trong ' + p.con_lai_nen + ' nến nữa; hết cửa sổ → run; gặp khoảng trống → chưa rõ.');
    });
    (sh.dang_cho || []).forEach(function (c) {
      add('state', 'Ứng viên shift <b>' + esc(DIR_VI[c.chieu]) + '</b> sau sweep ở nến #' + c.nen_sweep + ' (hạn nến #' + c.han_chot + '): cần ' + esc(c.can) + '.');
    });
    if (!directional) {
      var up = lq.gan_nhat_phia_tren, lo = lq.gan_nhat_phia_duoi;
      add('state', 'Vùng còn nguyên gần nhất: trên ' + poolText(up, d) + dist(up) + ' · dưới ' + poolText(lo, d) + dist(lo) + '.');
    }
    SUBVIEWS.forEach(function (sv) { sv.view.pendingLines(ps, d).forEach(function (l) { add(l.kind, esc(l.text)); }); });
    if (sh.gan_nhat) {
      add('state', 'Shift gần nhất: ' + esc(DIR_VI[sh.gan_nhat.dir]) + ' ở nến #' + sh.gan_nhat.d + ' (' + (i - sh.gan_nhat.d) + ' nến trước)' +
        (sh.gan_nhat.fvg ? ', có FVG' : (i - sh.gan_nhat.d === 0 ? ' — chờ nến sau để biết có FVG không' : ', không có FVG')) + '.');
    }

    // 3. Khung lớn (0.4.0) — mỗi thành phần một dòng, đọc pending_state tại con trỏ (không đọc details.htf)
    var lastDol = null;
    for (var q = r.events.length - 1; q >= 0; q--) {
      var eq = r.events[q];
      if (eq.confirmed_bar_index > i) continue;
      if (eq.structure_type === 'DOL_REACHED') { lastDol = eq; break; }
    }
    var hl = V.htfExplain(ps, d, { dolReached: lastDol });
    if (hl.length) {
      out.push('<div class="xp-sec">Khung lớn (chỉ nến đã chốt)</div>');
      hl.forEach(function (l) { add(l.kind, esc(l.text)); });
    }

    // 4. Cấu trúc
    var c3 = ps.cau_truc || {}, dr = ps.dealing_range || {}, mb = c3.muc_bao_ve;
    out.push('<div class="xp-sec">Cấu trúc (cấp ' + esc(ps.cap_cau_truc) + ')</div>');
    add('state', 'Thứ tự <b>' + esc(c3.order_vi || orderVi(c3.order)) + '</b>' +
      (mb ? ' · mức được bảo vệ ' + f(mb.gia) + (c3.muc_bao_ve_bi_vuot ? ' (close đã vượt — chỉ là cờ)' : '') : '') +
      (dr && isFiniteNum(dr.hi) ? ' · dealing range [' + f(dr.lo) + ', ' + f(dr.hi) + '], ' + esc(ZONE_VI[dr.zone] || '') : '') + '.');
    return out.join('');
  }

  /** Dòng trạng thái #ict-status (chỉ có ở trang Thử nghiệm, nội dung do chart.draw / onCrosshair ghi): hiện khi đang
   * xem kết quả ict_structure và lớp «Order flow + vùng» bật. Không còn chú giải ký hiệu màu — chữ nằm trên đối tượng. */
  function syncLegend(timeline, events, S) {
    var el = document.querySelector('#ict-status');
    if (!el) return;
    var L = (S && S.layers) || {};
    el.hidden = !(isIctTimeline(timeline || []) && L.ict_flow);
  }

  function labelPrice(type, bar) {
    if (type === 'SHIFT_UP' || type === 'SHIFT_DOWN') return bar.close;
    return undefined;
  }

  MSL.algos.register({
    id: 'ict_structure',
    algorithms: [ALGO],
    title: 'Cấu trúc ICT phân tầng + khung lớn + order flow',
    // Gọn (bật sẵn): ict_flow, ict_shift, ict_gap.
    // Chi tiết (ict_detail, tắt): các lớp còn lại giữ mặc định riêng, chỉ vẽ khi «Chi tiết» bật.
    // Khung lớn (ict_htf, tắt — nhóm riêng, không thuộc Chi tiết): lớp con ict_htf_* giữ mặc định riêng, chỉ vẽ khi bật nhóm.
    layers: {
      ict_flow: true, ict_shift: true, ict_gap: true, ict_detail: false,
      ict_ith: true, ict_labels: false, ict_sth: false, ict_lth: true, ict_protected: true, ict_range: true,
      ict_liq: false, ict_fvg: true, ict_disp: false,
      ict_htf: false, ict_htf_swing: true, ict_htf_range: true, ict_htf_fvg: true, ict_htf_levels: true, ict_htf_forming: true,
      ict_htf_h1: false,
      ict_ob: false, ict_ote: false, ict_nd_state: true, ict_nd_band: true
    },
    panels: ['#ict-layers'],
    ownLayersOnly: true,   // khung lớp chung (swing / BOS…) không có tác dụng với thuật toán này → trang ẩn
    layerHints: {
      ict_structure: 'Gọn (mặc định): BSL (cam) / SSL (xanh ngọc) vẽ từ đỉnh/đáy ITH/ITL gốc, chỉ hiện từ lúc xác nhận — ' +
        'nét liền = còn nguyên; «sweep» (nét chấm + hộp phần râu) / «run» (mờ) dừng ở nến lấy; nét đứt «bị lấy · chờ» = chưa ' +
        'biết sweep hay run; EQH/EQL = đỉnh/đáy bằng giá đã gộp. «Shift ↓/↑» = quét rồi displacement ngược chiều, kèm hộp FVG. ' +
        'Dải đáy = order flow sau mỗi nến, chữ ở đầu mỗi đoạn. Chỉ hiện 2 vùng còn nguyên mỗi phía + tối đa 3 vùng đã ' +
        'sweep / run gần con trỏ nhất mỗi phía (trong 60 nến) («Lịch sử»: mọi thứ tới con trỏ, mờ dần theo tuổi). Rê chuột vào đối tượng để xem giải thích. ' +
        'Order flow là mô tả, không phải dự báo. Chi tiết: ITH/ITL = chấm vàng / xanh tại pivot (nhãn HH/HL/LH/LL/EQ tuỳ chọn), ' +
        '«Protected Low/High» = mức được bảo vệ (nét đứt đỏ «broken» khi close đã vượt — chỉ là cờ, không phải BOS), ' +
        'Premium / EQ / Discount = 3 dải của dealing range, FVG = hộp + CE nét đứt (3 FVG còn mở gần giá nhất mỗi chiều). ' +
        'Vùng khung lớn: «BSL H1» / «BSL H4» / «PDH» / «PWL»… — nét đậm hơn theo tầng. Khung lớn (tắt sẵn): ITH/ITL H4 = vòng ' +
        'tròn rỗng tím, Range H4 + EQ H4 = nét đứt / chấm tím, «FVG H4» = hộp viền dày (dừng khi respect / disrespect), ' +
        'nến H4 đang hình thành = khung mờ (chưa dùng). Dòng trạng thái: «H4 ↑ · discount 31% · pd ↓ H1 · DOL ↑ …». ' +
        'Order block (tắt sẵn): hộp xanh / đỏ từ chuỗi nến ngược màu cuối trước displacement của shift, chỉ hiện khi giá đã vượt ' +
        'đầu xa; «· chạm» nét đứt, «· hỏng» / «· hết hạn» nét chấm. OTE (tắt sẵn): hộp vàng = vùng hồi 62–79% của nhịp sau shift, ' +
        'đường chấm = điểm ngọt, nét đứt mờ = gốc nhịp. Mô tả, chưa phải tín hiệu. Trạng thái (bật sẵn, lõi 0.6.0): dải ' +
        '«trạng thái» trên dải order flow — trend ↑ / trend ↓ (ER ≥ ngưỡng, mặc định 0,3), range (mỗi biên bị chạm ≥ 2 lần), ' +
        'nén (đỉnh thấp dần, đáy cao dần), nhiễu (đi ngang không có biên); hộp range màu chàm; hàng thứ ba của dòng trạng thái ghi trạng thái ' +
        'đang có. Mô tả trạng thái, không phải dự báo hướng. Khoảng giá (bật sẵn, lõi 0.6.0): hộp xám nét đứt phía trước ' +
        'con trỏ = khoảng 80% (lõi 50% đậm hơn) của 1h và 4h tới — cả đường giá; đường chấm «chạm 1h x% · 4h y%» = xác suất ' +
        'vùng gần nhất / PDH / PDL / biên range bị chạm. Tooltip ghi điểm thật tới nến đó (độ phủ thực tế, Brier so với B0, ' +
        'chạm thật / kỳ vọng).'
    },
    labelTypes: [
      { id: 'SHIFT_UP', label: 'Shift tăng (nến displacement)', sw: COLORS.shiftUp, short: 'SH↑' },
      { id: 'SHIFT_DOWN', label: 'Shift giảm (nến displacement)', sw: COLORS.shiftDown, short: 'SH↓' }
    ],
    labelPrice: labelPrice,
    replayLayers: [],   // không tự bật lớp nào khi replay (chế độ Gọn đủ để theo dõi từng nến)
    chart: chart,
    notes: notes,
    statsHtml: statsHtml,
    pendingHtml: pendingHtml,
    eventDetail: eventDetail,
    explain: explain,
    syncLegend: syncLegend,
    selectEventOnChart: true
  });
})(window.MSL);
