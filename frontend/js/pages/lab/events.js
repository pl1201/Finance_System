/* Trang Thử nghiệm — bảng sự kiện và panel chi tiết sự kiện được chọn. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var S = L.S;

  /** Panel giải thích một sự kiện DC: công thức với số thực tế, tham chiếu, lúc biết. */
  function renderEventDetail(e) {
    var box = $('#event-detail');
    if (!box) return;
    if (!e || e.algorithm !== 'dc_atr_structure') { box.hidden = true; box.innerHTML = ''; return; }
    var x = e.details || {};
    var d = S.digits;
    var f = function (v) { return v === null || v === undefined ? '—' : Number(v).toFixed(d); };
    var TXT = window.chartUtils.REGIME_TEXT_VI;
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
    box.innerHTML = '<h4>Chi tiết sự kiện được chọn</h4><dl>' + rows.join('') + '</dl>';
    box.hidden = false;
  }

  function renderEvents(events) {
    var tbody = $('#events-table tbody');
    var filter = ($('#event-filter').value || '').trim().toUpperCase();
    var list = (events || []).filter(function (e) {
      var sid = ((e.details && (e.details.setup_id || e.details.candidate_id)) || '').toUpperCase();
      return !filter || e.structure_type.indexOf(filter) >= 0 || (e.reason_code || '').indexOf(filter) >= 0 ||
        sid.indexOf(filter) >= 0;
    });
    $('#event-count').textContent = list.length + ' / ' + (events || []).length + ' sự kiện';
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="empty-cell">' +
        ((events && events.length) ? 'Không có sự kiện khớp bộ lọc.' : 'Chưa có sự kiện.') + '</td></tr>';
      return;
    }
    var d = S.digits;
    tbody.innerHTML = list.slice(0, 3000).map(function (e, i) {
      return '<tr data-ev="' + i + '" tabindex="' + (i === 0 ? 0 : -1) + '" aria-selected="false">' +
        '<td class="num">' + (i + 1) + '</td>' +
        '<td><span class="badge b-' + esc(e.structure_type) + '">' + esc(e.structure_type) + '</span></td>' +
        '<td class="num">' + Number(e.price).toFixed(d) + '</td>' +
        '<td class="num">' + e.event_bar_index + '</td>' +
        '<td class="mono">' + fmtIso(e.event_time) + '</td>' +
        '<td class="num">' + e.confirmed_bar_index + '</td>' +
        '<td class="mono">' + fmtIso(e.confirmed_at) + '</td>' +
        '<td class="num">' + e.confirmation_lag_bars + '</td>' +
        '<td class="mono">' + esc(e.reason_code) + '</td>' +
        '<td class="mono">' + esc(e.reference_event_id || '—') +
          ((e.details && (e.details.setup_id || e.details.candidate_id))
            ? '<br><span class="muted">' + esc(e.details.setup_id ? 'setup ' + e.details.setup_id : 'ứng viên ' + e.details.candidate_id) + '</span>'
            : '') + '</td>' +
        '</tr>';
    }).join('');
    if (list.length > 3000) {
      tbody.innerHTML += '<tr><td colspan="10" class="empty-cell">Hiển thị 3000 dòng đầu; xuất CSV để xem đầy đủ.</td></tr>';
    }
    Array.prototype.forEach.call(tbody.querySelectorAll('tr[data-ev]'), function (tr) {
      tr.addEventListener('click', function () {
        Array.prototype.forEach.call(tbody.querySelectorAll('tr'), function (r) {
          r.classList.remove('selected');
          if (r.hasAttribute('data-ev')) { r.setAttribute('tabindex', '-1'); r.setAttribute('aria-selected', 'false'); }
        });
        tr.classList.add('selected');
        tr.setAttribute('tabindex', '0');
        tr.setAttribute('aria-selected', 'true');
        var ev = list[parseInt(tr.getAttribute('data-ev'), 10)];
        renderEventDetail(ev);
        if (ev.algorithm === 'dc_atr_structure') {
          S.selectedEventId = ev.event_id;   // hiện điểm xác nhận của pivot đang chọn
          L.applyChartEvents();
        }
        S.chart.focusEvent(ev);
      });
    });
  }

  L.renderEventDetail = renderEventDetail;
  L.renderEvents = renderEvents;
})(window.MSL);
