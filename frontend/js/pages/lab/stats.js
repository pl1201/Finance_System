/* Trang Thử nghiệm — tab Thống kê lần chạy (chung + khối chỉ số riêng do plugin algos/ sinh). */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;

  function renderStats(res) {
    var st = res.stats || {};
    var byType = st.so_su_kien_theo_loai || {};
    var lag = st.do_tre_xac_nhan_theo_loai_nen || {};
    var html = '<div class="stat-grid">' +
      box('Tổng sự kiện', st.tong_su_kien || 0) +
      box('Nến đã xử lý', st.so_nen_xu_ly || 0) +
      box('Warm-up (nến)', res.warmup_bars) +
      box('Thời gian tính (ms)', (st.thoi_gian_tinh_toan_ms || 0).toFixed(2)) +
      box('Tốc độ (nến/giây)', st.toc_do_nen_tren_giay || '—') +
      box('Trễ xác nhận TB (nến)', st.do_tre_xac_nhan_chung_nen ? st.do_tre_xac_nhan_chung_nen.trung_binh : '—') +
      '</div>';

    html += '<div class="section-title">Số sự kiện và độ trễ xác nhận theo loại</div>';
    html += '<table class="data-table"><thead><tr><th>Loại</th><th>Số sự kiện</th>' +
            '<th>Trễ min</th><th>Trễ TB</th><th>Trễ trung vị</th><th>Trễ max</th></tr></thead><tbody>';
    var keys = Object.keys(byType).sort();
    if (!keys.length) html += '<tr><td colspan="6" class="empty-cell">Không có sự kiện.</td></tr>';
    keys.forEach(function (k) {
      var l = lag[k] || {};
      html += '<tr><td><span class="badge b-' + esc(k) + '">' + esc(k) + '</span></td>' +
        '<td class="num">' + byType[k] + '</td>' +
        '<td class="num">' + (l.min !== undefined ? l.min : '—') + '</td>' +
        '<td class="num">' + (l.trung_binh !== undefined ? l.trung_binh : '—') + '</td>' +
        '<td class="num">' + (l.trung_vi !== undefined ? l.trung_vi : '—') + '</td>' +
        '<td class="num">' + (l.max !== undefined ? l.max : '—') + '</td></tr>';
    });
    html += '</tbody></table>';

    html += '<div class="section-title">Hồ sơ lần chạy</div>';
    html += '<div class="info-card"><dl>' +
      '<dt>run_id</dt><dd class="mono">' + esc(res.run_id) + '</dd>' +
      '<dt>Thuật toán</dt><dd>' + esc(res.algorithm) + ' v' + esc(res.algorithm_version) + '</dd>' +
      '<dt>Tham số</dt><dd class="mono">' + esc(JSON.stringify(res.params)) + '</dd>' +
      '<dt>Dataset</dt><dd>' + esc(res.dataset_name || res.dataset_id) + (res.is_synthetic ? ' <span class="pill pill-synth">MÔ PHỎNG</span>' : '') + '</dd>' +
      '<dt>Dataset checksum</dt><dd class="mono">' + esc(res.dataset_checksum) + '</dd>' +
      '<dt>Khoảng chạy</dt><dd class="mono">' + fmtIso(res.range_start) + ' → ' + fmtIso(res.range_end) + '</dd>' +
      '<dt>Chạy lúc</dt><dd class="mono">' + fmtIso(res.created_at) + '</dd>' +
      '</dl></div>';
    html += '<p class="hint">' + esc(st.ghi_chu_vi || '') + '</p>';
    if (st.chi_so_thuat_toan) html = (MSL.algos.callFor(res.algorithm, 'statsHtml', st.chi_so_thuat_toan, res) || '') + html;
    $('#stats-body').innerHTML = '<p class="hint">F1, P90 và so sánh nhiều cấu hình: <a href="/danh-gia">Đánh giá thuật toán</a>.</p>' + html;
    MSL.algos.callFor(res.algorithm, 'afterStats', res);

    function box(k, v) {
      return '<div class="stat-box"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }
  }

  L.renderStats = renderStats;
})(window.MSL);
