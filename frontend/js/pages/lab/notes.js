/* Trang Thử nghiệm — ghi chú riêng thuật toán dưới banner (c2_cisd_research, dc_atr_structure). */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = L.S;

  /**
   * Cảnh báo riêng c2_cisd_research, tách bạch: alignment, warm-up, thiếu dữ liệu,
   * không có setup. Thuật toán khác: ẩn.
   */
  function renderAlgoNotes(algorithm, stats, dataStatus, pending) {
    var box = $('#algo-notes');
    if (!box) return;
    if (algorithm === 'dc_atr_structure') { renderDcNotes(box, stats, dataStatus, pending); return; }
    if (algorithm !== 'c2_cisd_research') { box.hidden = true; box.innerHTML = ''; return; }
    var m = (stats && stats.chi_so_thuat_toan) || null;
    var notes = [];
    notes.push(['info', 'C2 + CISD (bản nghiên cứu closed-bar, <strong>chưa xác minh parity với Pine</strong>). ' +
      'Kỳ H4 theo <strong>mốc UTC epoch</strong> (00/04/08/12/16/20 UTC) — chưa đối chiếu với H4 của broker/TradingView. ' +
      'Marker C2 neo tại nến cực trị nhưng chỉ xuất hiện sau khi C2 đóng; đường mức chỉ bắt đầu từ nến sau lúc mức được biết.']);
    if (dataStatus === 'WARMUP_INSUFFICIENT') {
      notes.push(['warn', '<strong>Warm-up:</strong> cần ít nhất 2 kỳ H4 đủ nến (32 nến M15) trước khi có C1/C2 hợp lệ.']);
    }
    var gaps = m ? m.so_gap_ltf : (pending ? pending.so_gap_ltf : 0);
    var inc = m ? m.so_ky_htf_thieu_nen : (pending ? pending.so_ky_htf_thieu : 0);
    if (inc || gaps) {
      var killed = m && m.ket_thuc_theo_ly_do ? (m.ket_thuc_theo_ly_do.SETUP_LTF_GAP || 0) : null;
      notes.push(['warn', '<strong>Dữ liệu thiếu:</strong> ' + gaps + ' chỗ gap M15, ' + inc + ' kỳ H4 thiếu nến — không dùng làm C1/C2/C3/C4, không tự bù.' +
        (killed !== null ? ' <strong>' + killed + '</strong> setup dừng vì gap (không phải bị giá phá).' : '') +
        ' XAUUSD nghỉ phiên hằng ngày nên kỳ 20:00 UTC thường thiếu.']);
    }
    if (m && dataStatus === 'OK' && !m.tong_setup) {
      notes.push(['info', '<strong>Không có setup C2 nào</strong> trong khoảng này (dữ liệu vẫn hợp lệ). Đây không phải lỗi.']);
    }
    box.innerHTML = notes.map(function (n) {
      return '<div class="note note-compact note-' + n[0] + '">' + n[1] + '</div>';
    }).join('');
    box.hidden = false;
  }

  /** Ghi chú riêng dc_atr_structure: close vs wick, gap/segment, warm-up, UNKNOWN, nhãn, baseline. */
  function renderDcNotes(box, stats, dataStatus, pending) {
    var m = (stats && stats.chi_so_thuat_toan) || null;
    var ps = pending || {};
    var notes = [];
    notes.push(['info', '<strong>DC theo CLOSE</strong>: đỉnh/đáy là close của nến cực trị, xác nhận khi close đảo chiều ≥ Δ (k×ATR hoặc % khoá tại cực trị). ' +
      'Trend/Range là <strong>định nghĩa vận hành của lab</strong> (HH+HL, LH+LL, cụm đỉnh/đáy) — không phải dự báo hay tín hiệu giao dịch.']);
    if (S.dataset && S.dataset.is_synthetic) {
      notes.push(['warn', 'Dataset <strong>MÔ PHỎNG</strong> — số liệu chỉ để thử công cụ, không mô tả thị trường thật.']);
    }
    if (dataStatus === 'WARMUP_INSUFFICIENT') {
      notes.push(['warn', '<strong>Warm-up:</strong> cần ATR period + 1 nến liên tục trong MỖI segment trước khi detector khởi tạo.']);
    }
    var gaps = m ? m.so_gap : ps.so_gap;
    var segs = m ? m.so_segment : ps.so_segment;
    var bridged = m ? m.so_gap_noi : ps.so_gap_noi;
    var policy = (m && m.gap_policy) || ps.gap_policy || 'reset';
    if (policy === 'bridge_short') {
      var hrs = S.run && S.run.params ? S.run.params.bridge_max_gap_hours : '?';
      notes.push(['warn', '<strong>Gap dữ liệu (gap_policy=bridge_short, ≤ ' + esc(hrs) + ' giờ):</strong> ' + (bridged || 0) +
        ' gap ngắn được NỐI (giữ ứng viên, ATR, lịch sử; TR tính cả bước nhảy qua gap; marker «nối»), ' + (gaps || 0) +
        ' gap dài bị reset → ' + segs + ' segment. Nối là lựa chọn phương pháp, không phải dữ liệu liền mạch. Chưa dùng lịch phiên broker.']);
    } else if (gaps) {
      notes.push(['warn', '<strong>Gap dữ liệu:</strong> ' + gaps + ' gap → ' + segs + ' segment (gap_policy=reset). ' +
        'Mỗi gap — kể cả nghỉ phiên hằng ngày và cuối tuần — bỏ ứng viên, ATR, lịch sử trend/range và warm-up lại; không nối swing qua gap. ' +
        'Chưa suy đoán lịch phiên broker, nên mỗi phiên bắt đầu ở «Chưa rõ». Có thể thử gap_policy=bridge_short.']);
    }
    if (m && m.regime_ty_le_thoi_gian && m.regime_ty_le_thoi_gian.UNKNOWN !== null && m.regime_ty_le_thoi_gian.UNKNOWN > 0.5) {
      notes.push(['info', '«Chưa rõ» chiếm <strong>' + (m.regime_ty_le_thoi_gian.UNKNOWN * 100).toFixed(1) + '%</strong> thời gian sau warm-up: thiếu hoặc mâu thuẫn bằng chứng swing — không bị ép thành Range.']);
    }
    if (m && m.so_pivot_xac_nhan === 0) {
      notes.push(['warn', 'Không có pivot DC xác nhận. Không phải lỗi dữ liệu — thử giảm k hoặc dùng khoảng dài hơn.']);
    }
    if (S.baseline && S.layers.baseline) {
      notes.push(['warn', '<strong>So sánh baseline:</strong> pivot baseline (swing_pivot 3/3, run <code>' + esc(S.baseline.run_id || '(không lưu)') + '</code>) theo <strong>WICK</strong>, DC theo <strong>CLOSE</strong> — ' +
        'chênh giá marker là khác định nghĩa, không phải lỗi. Đây là so sánh trải nghiệm tổng thể (khác cả ngưỡng lẫn nguồn giá).']);
    }
    notes.push(['info', 'Chưa có nhãn tham chiếu cho swing close / đoạn regime — không hiển thị F1 hay confusion matrix.']);
    box.innerHTML = notes.map(function (n) {
      return '<div class="note note-compact note-' + n[0] + '">' + n[1] + '</div>';
    }).join('');
    box.hidden = false;
  }

  L.renderAlgoNotes = renderAlgoNotes;
})(window.MSL);
