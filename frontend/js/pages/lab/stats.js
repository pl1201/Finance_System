/* Trang Thử nghiệm — tab Thống kê lần chạy (chung + chỉ số riêng thuật toán, MFE/MAE C2). */
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
    if (st.chi_so_thuat_toan && res.algorithm === 'c2_cisd_research') html = c2StatsHtml(st.chi_so_thuat_toan, res) + html;
    if (st.chi_so_thuat_toan && res.algorithm === 'dc_atr_structure') html = dcStatsHtml(st.chi_so_thuat_toan, res) + html;
    $('#stats-body').innerHTML = '<p class="hint">F1, P90 và so sánh nhiều cấu hình: <a href="/danh-gia">Đánh giá thuật toán</a>.</p>' + html;
    var mb = $('#c2-mfe-btn');
    if (mb) mb.addEventListener('click', function () { loadC2Excursion(res.run_id); });

    function box(k, v) {
      return '<div class="stat-box"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }
  }

  /** Metric không cần nhãn của dc_atr_structure — mô tả hành vi, không phải accuracy. */
  function dcStatsHtml(m, res) {
    function box(k, v, title) {
      return '<div class="stat-box"' + (title ? ' title="' + esc(title) + '"' : '') + '><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }
    function num(x, dg) { return x === null || x === undefined ? '—' : Number(x).toFixed(dg === undefined ? 2 : dg); }
    function sm(s, dg) { return s && s.n ? num(s.trung_vi, dg) + ' / ' + num(s.p90, dg) + ' (n=' + s.n + ')' : '—'; }
    var TXT = window.chartUtils.REGIME_TEXT_VI, COL = window.chartUtils.REGIME_COLORS;
    var share = m.regime_ty_le_thoi_gian || {};
    var html = '<div class="section-title">DC + regime (không cần nhãn — mô tả hành vi, không phải accuracy)</div>';
    html += '<div class="stat-grid">' +
      box('Pivot xác nhận', m.so_pivot_xac_nhan + ' (' + m.so_dinh + ' đỉnh / ' + m.so_day + ' đáy)') +
      box('Mật độ / 1.000 nến', num(m.mat_do_tren_1000_nen, 1), m.mat_do_ghi_chu_vi) +
      box('Trễ xác nhận (nến) TV / P90', sm(m.do_tre_nen, 1)) +
      box('Trễ (phút) TV / P90', sm(m.do_tre_phut, 0)) +
      box('Đảo chiều / ATR cực trị TV / P90', sm(m.reversal_distance_atr), m.reversal_ghi_chu_vi) +
      box('Biên độ nhịp / ATR TV / P90', sm(m.bien_do_nhip_atr), m.bien_do_ghi_chu_vi) +
      box('Lần chuyển trạng thái', m.so_lan_chuyen_trang_thai) +
      box('Độ dài đoạn TV (nến)', num(m.do_dai_doan_trung_vi_tat_ca, 0)) +
      box('Gap reset / nối / segment', m.so_gap + ' / ' + (m.so_gap_noi || 0) + ' / ' + m.so_segment, 'gap_policy=' + (m.gap_policy || 'reset')) +
      box('Nến đủ điều kiện / tổng', m.so_nen_du_dieu_kien + ' / ' + m.so_nen) +
      '</div>';
    html += '<div class="section-title">Tỷ lệ thời gian theo trạng thái (sau warm-up, không tính gap)</div>';
    html += '<div class="regime-share" role="img" aria-label="Tỷ lệ thời gian theo trạng thái">';
    ['UPTREND', 'DOWNTREND', 'RANGE', 'UNKNOWN'].forEach(function (k) {
      var v = share[k] || 0;
      if (v > 0) html += '<span style="width:' + (v * 100).toFixed(2) + '%;background:' + COL[k] + '" title="' + esc(TXT[k]) + ' ' + (v * 100).toFixed(1) + '%"></span>';
    });
    html += '</div><table class="data-table"><thead><tr><th>Trạng thái</th><th>Số nến</th><th>Tỷ lệ</th><th>Độ dài đoạn TV (nến)</th></tr></thead><tbody>';
    ['UPTREND', 'DOWNTREND', 'RANGE', 'UNKNOWN'].forEach(function (k) {
      html += '<tr><td>' + esc(TXT[k]) + '</td><td class="num">' + ((m.regime_so_nen || {})[k] || 0) + '</td>' +
        '<td class="num">' + (share[k] === null || share[k] === undefined ? '—' : (share[k] * 100).toFixed(1) + '%') + '</td>' +
        '<td class="num">' + num((m.do_dai_doan_trung_vi_nen || {})[k], 0) + '</td></tr>';
    });
    html += '</tbody></table>';
    var labs = m.nhan_so_sanh || {};
    html += '<p class="hint">Nhãn swing: ' + Object.keys(labs).sort().map(function (k) { return esc(k) + ' ' + labs[k]; }).join(' · ') + '</p>';
    html += '<p class="hint">' + esc((m.nhan_tham_chieu || {}).ghi_chu_vi || '') + ' ' + esc(m.ghi_chu_vi || '') + '</p>';
    return html;
  }

  function c2StatsHtml(m, res) {
    function box(k, v) {
      return '<div class="stat-box"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }
    function pct(x) { return x === null || x === undefined ? '—' : (x * 100).toFixed(1) + '%'; }
    function sm(x) { return x ? x.trung_vi + ' / ' + x.trung_binh + ' (n=' + x.n + ')' : '—'; }
    var r = m.ty_le_co_cisd || {};
    var ea = m.early_cisd || {};
    var html = '<div class="section-title">C2 + CISD — vòng đời setup</div>';
    html += '<div class="stat-grid">' +
      box('Setup C2 (↑ / ↓)', m.tong_setup + ' (' + m.so_c2_theo_huong.up + ' / ' + m.so_c2_theo_huong.down + ')') +
      box('C2 outside bar (cả hai hướng)', m.so_c2_outside_bar) +
      box('Có CISD / mọi setup', pct(r.tren_moi_setup) + ' (mẫu ' + r.mau_so_moi_setup + ')') +
      box('Có CISD / setup đã kết thúc', pct(r.tren_setup_da_ket_thuc) + ' (mẫu ' + r.mau_so_da_ket_thuc + ')') +
      box('CISD theo pha C2(early)/C3/C4', m.so_cisd_theo_pha.C2 + ' / ' + m.so_cisd_theo_pha.C3 + ' / ' + m.so_cisd_theo_pha.C4) +
      box('Trễ CISD sau C2 (trung vị / TB, nến)', sm(m.do_tre_cisd_sau_c2_nen)) +
      box('Early: nến bằng chứng trước cuối C2', sm(ea.so_nen_bang_chung_truoc_cuoi_c2)) +
      box('Early ứng viên không thành C2', ea.so_ung_vien_khong_thanh_c2 + ' / ' + ea.so_su_kien_early_ung_vien) +
      box('Censored (còn mở khi hết dữ liệu)', m.censored_dang_mo) +
      box('C4 không hợp lệ (chưa kết thúc)', m.so_c4_khong_hop_le_chua_ket_thuc) +
      box('Gap M15 / kỳ H4 thiếu', m.so_gap_ltf + ' / ' + m.so_ky_htf_thieu_nen) +
      '</div>';
    html += '<table class="data-table"><thead><tr><th>Kết thúc theo lý do</th><th>Số setup</th></tr></thead><tbody>';
    var ks = Object.keys(m.ket_thuc_theo_ly_do_vi || {});
    if (!ks.length) html += '<tr><td colspan="2" class="empty-cell">Chưa setup nào kết thúc.</td></tr>';
    ks.forEach(function (k) { html += '<tr><td>' + esc(k) + '</td><td class="num">' + m.ket_thuc_theo_ly_do_vi[k] + '</td></tr>'; });
    html += '<tr><td><em>Censored — chưa kết thúc (không tính thất bại)</em></td><td class="num">' + m.censored_dang_mo + '</td></tr>';
    html += '</tbody></table>';
    html += '<p class="hint">' + esc(r.ghi_chu_vi || '') + ' ' + esc(ea.ghi_chu_vi || '') + ' ' + esc(m.ghi_chu_vi || '') + '</p>';
    html += '<div class="section-title">Đối chứng C2-only vs C2+CISD (MFE/MAE, chỉ để đánh giá)</div>';
    if (res.run_id && res.saved) {
      html += '<div class="c2-metric-ctl"><label>Horizon (nến M15) <input type="number" id="c2-horizon" min="1" max="500" value="16"></label>' +
        '<button id="c2-mfe-btn" class="btn btn-secondary btn-sm" type="button">Tính MFE/MAE</button></div>' +
        '<div id="c2-mfe-body" class="hint">Dùng nến SAU lúc biết trong horizon cố định; mẫu thiếu horizon bị bỏ và được đếm. Không phải win rate hay P&amp;L.</div>';
    } else {
      html += '<p class="hint">Lưu lần chạy để tính MFE/MAE trên đúng snapshot dữ liệu.</p>';
    }
    return html;
  }

  async function loadC2Excursion(runId) {
    var body = $('#c2-mfe-body');
    var h = parseInt(($('#c2-horizon') || {}).value, 10) || 16;
    body.textContent = 'Đang tính…';
    try {
      var r = await API.c2CisdMetrics(runId, h);
      var x = r.mfe_mae;
      var rows = '';
      [['c2_only', 'C2-only (neo lúc C2 đóng)'], ['c2_cisd', 'C2+CISD (neo lúc CISD được biết)']].forEach(function (g) {
        ['up', 'down', 'tat_ca'].forEach(function (d) {
          var c = x[g[0]][d];
          var f = function (s) { return s ? s.trung_vi + ' / ' + s.trung_binh : '—'; };
          rows += '<tr><td>' + esc(g[1]) + '</td><td>' + (d === 'tat_ca' ? 'tất cả' : d) + '</td>' +
            '<td class="num">' + c.so_mau + '</td><td class="num">' + c.so_mau_bo_thieu_horizon + '</td>' +
            '<td class="num">' + f(c.mfe) + '</td><td class="num">' + f(c.mae) + '</td>' +
            '<td class="num">' + c.so_mau_mfe_lon_hon_mae + '</td></tr>';
        });
      });
      body.innerHTML = '<table class="data-table"><thead><tr><th>Nhóm</th><th>Hướng</th><th>Mẫu</th><th>Bỏ (thiếu horizon)</th>' +
        '<th>MFE trung vị / TB</th><th>MAE trung vị / TB</th><th>Số mẫu MFE &gt; MAE</th></tr></thead><tbody>' + rows +
        '</tbody></table><p class="hint">Horizon ' + x.horizon_nen + ' nến. ' + esc(x.ghi_chu_vi) + '</p>';
    } catch (e) {
      body.innerHTML = '<span class="note note-error">' + esc(e.message) + '</span>';
    }
  }

  L.renderStats = renderStats;
})(window.MSL);
