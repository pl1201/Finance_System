/* Trang Thử nghiệm — khung «Thuật toán đang làm gì» khi replay (dc_atr_structure). */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var S = L.S;

  function f2(x) { return x === null || x === undefined || !isFinite(x) ? '—' : Number(x).toFixed(S.digits); }

  /** Khung «Thuật toán đang làm gì» — chỉ đọc snapshot/sự kiện đã có tại con trỏ. */
  function renderExplain() {
    var box = $('#rp-explain');
    var r = S.replay;
    var isDc = r && r.snapshot && r.snapshot.algorithm === 'dc_atr_structure';
    var chk = $('#chk-explain');
    chk.disabled = !!(r && r.snapshot) && !isDc;
    chk.parentNode.title = chk.disabled
      ? 'Giải thích từng bước hiện có cho «DC theo close + ATR». Thuật toán này xem ở tab Thống kê (trạng thái nội bộ).'
      : 'Khung giải thích từng bước trên chart (dc_atr_structure)';
    if (!r || S.mode !== 'replay' || !isDc || !$('#chk-explain').checked) { box.hidden = true; return; }
    box.hidden = false;
    var i = r.cursor, bar = i >= 0 ? r.bars[i] : null;
    $('#rp-explain-bar').textContent = bar ? 'nến #' + i + ' · ' + fmtIso(bar.close_time) : '';
    if (!bar) {
      $('#rp-explain-body').innerHTML = '<div class="xp xp-muted">Chưa nạp nến nào. Bấm ▶ hoặc → để nạp nến đầu tiên.</div>';
      return;
    }
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
        var TXT = window.chartUtils.REGIME_TEXT_VI;
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
    $('#rp-explain-body').innerHTML = out.join('');
  }

  L.renderExplain = renderExplain;
})(window.MSL);
