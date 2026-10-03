/* Plugin hiển thị c2_cisd_research: marker C2 / CISD / vòng đời setup, đường mức CISD và cực trị
 * setup (timeline lõi), chi tiết tooltip, ghi chú, chỉ số vòng đời + MFE/MAE, trạng thái replay,
 * loại nhãn tay C2 / CISD.
 */
(function (MSL) {
  'use strict';

  var LWC = window.LightweightCharts;
  var series = MSL.series;
  var isFiniteNum = MSL.format.isFiniteNum;
  var fmtIso = MSL.format.fmtIso;
  var esc = MSL.dom.esc;

  var COLORS = {
    c2Up: '#00e676',
    c2Down: '#ff5252',
    cisdUp: '#69f0ae',
    cisdDown: '#ff8a80',
    earlyUp: 'rgba(105,240,174,.7)',
    earlyDown: 'rgba(255,138,128,.7)',
    trackUp: 'rgba(105,240,174,.35)',
    trackDown: 'rgba(255,138,128,.35)',
    extreme: 'rgba(255,213,79,.6)',
    dead: '#e53935',
    c4inv: '#ffa726',
    ended: '#90a4ae',
    dataq: '#607d8b'
  };

  /** Sự kiện của c2_cisd_research: lớp hiển thị, nhãn marker, vị trí neo. */
  var C2CISD = {
    C2_CONFIRMED_UP: { layer: 'c2', up: true, text: 'C2↑', color: 'c2Up', shape: 'arrowUp', at: 'event' },
    C2_CONFIRMED_DOWN: { layer: 'c2', up: false, text: 'C2↓', color: 'c2Down', shape: 'arrowDown', at: 'event' },
    CISD_CONFIRMED_UP: { layer: 'cisd', up: true, text: '+CISD', color: 'cisdUp', shape: 'circle', at: 'event' },
    CISD_CONFIRMED_DOWN: { layer: 'cisd', up: false, text: '-CISD', color: 'cisdDown', shape: 'circle', at: 'event' },
    EARLY_CISD_UP: { layer: 'cisd', up: true, text: 'e+', color: 'earlyUp', shape: 'circle', at: 'event', size: 0.6 },
    EARLY_CISD_DOWN: { layer: 'cisd', up: false, text: 'e−', color: 'earlyDown', shape: 'circle', at: 'event', size: 0.6 },
    CISD_LEVEL_SET_UP: null,
    CISD_LEVEL_SET_DOWN: null,
    SETUP_INVALIDATED: { layer: 'lifecycle', text: 'X', color: 'dead', shape: 'square', at: 'confirm' },
    SETUP_C4_INVALIDATED: { layer: 'lifecycle', text: 'XC4', color: 'c4inv', shape: 'circle', at: 'confirm', size: 0.7 },
    SETUP_EXPIRED: { layer: 'lifecycle', text: 'hết', color: 'ended', shape: 'circle', at: 'confirm', size: 0.7 },
    SETUP_SUPERSEDED: { layer: 'lifecycle', text: 'thay', color: 'ended', shape: 'circle', at: 'confirm', size: 0.7 },
    SETUP_DATA_GAP: { layer: 'lifecycle', text: 'gap', color: 'dataq', shape: 'square', at: 'confirm', size: 0.7 },
    HTF_BUCKET_INCOMPLETE: { layer: 'dataq', up: false, text: 'H4 thiếu', color: 'dataq', shape: 'square', at: 'confirm', size: 0.5 }
  };

  // ------------------------------------------------------------------ chart

  var chart = {
    /** Mức CISD đang theo dõi, mức CISD của setup, cực trị C2. */
    init: function (mc, st) {
      var lineOpts = series.stepLineOpts;
      st.cisdTrackUp = mc.chart.addLineSeries(lineOpts(COLORS.trackUp, 1, LWC.LineStyle.Dotted));
      st.cisdTrackDown = mc.chart.addLineSeries(lineOpts(COLORS.trackDown, 1, LWC.LineStyle.Dotted));
      st.setupLevelUp = mc.chart.addLineSeries(lineOpts(COLORS.cisdUp, 2, LWC.LineStyle.Solid));
      st.setupLevelDown = mc.chart.addLineSeries(lineOpts(COLORS.cisdDown, 2, LWC.LineStyle.Solid));
      st.setupExtremeUp = mc.chart.addLineSeries(lineOpts(COLORS.extreme, 1, LWC.LineStyle.Dashed));
      st.setupExtremeDown = mc.chart.addLineSeries(lineOpts(COLORS.extreme, 1, LWC.LineStyle.Dashed));
    },

    clear: function (mc, st) {
      [st.cisdTrackUp, st.cisdTrackDown, st.setupLevelUp, st.setupLevelDown, st.setupExtremeUp, st.setupExtremeDown]
        .forEach(function (s) { s.setData([]); });
    },

    ownsEvent: function (t) { return Object.prototype.hasOwnProperty.call(C2CISD, t); },

    marker: function (e, ctx) {
      var t = e.structure_type;
      var spec = C2CISD[t];
      if (!spec || !ctx.layers[spec.layer]) return;
      var upDir = spec.up !== undefined ? spec.up : e.direction === 'up';
      var at = (spec.at === 'confirm' || ctx.opts.markerAtConfirm) ? e.confirmed_bar_index : e.event_bar_index;
      var txt = spec.text;
      if ((t === 'C2_CONFIRMED_UP' || t === 'C2_CONFIRMED_DOWN') && e.details && e.details.outside_bar_ambiguous) txt += '?';
      if ((t === 'CISD_CONFIRMED_UP' || t === 'CISD_CONFIRMED_DOWN') && e.details && e.details.early) txt += '(e)';
      ctx.markers.push({
        time: ctx.timeByIndex[at],
        position: upDir ? 'belowBar' : 'aboveBar',
        color: COLORS[spec.color],
        shape: spec.shape,
        text: txt,
        size: spec.size || 1
      });
    },

    /** Đường mức CISD / cực trị setup theo timeline lõi (chỉ khi timeline là của c2_cisd_research). */
    draw: function (ctx, st) {
      var tl = ctx.timeline, layers = ctx.layers, cursor = ctx.cursor;
      var hasC2 = tl.length && Object.prototype.hasOwnProperty.call(tl[tl.length - 1], 'cisd_up');
      var showTrack = hasC2 && layers.cisd;
      var showSetup = hasC2 && layers.c2;
      var lv = series.levelSeriesData, set = series.setGapLineData;
      set(st.cisdTrackUp, showTrack ? lv(tl, 'cisd_up', cursor) : []);
      set(st.cisdTrackDown, showTrack ? lv(tl, 'cisd_down', cursor) : []);
      set(st.setupLevelUp, showSetup && layers.cisd ? lv(tl, 'setup_up_level', cursor, 'setup_up_id') : []);
      set(st.setupLevelDown, showSetup && layers.cisd ? lv(tl, 'setup_down_level', cursor, 'setup_down_id') : []);
      set(st.setupExtremeUp, showSetup ? lv(tl, 'setup_up_extreme', cursor, 'setup_up_id') : []);
      set(st.setupExtremeDown, showSetup ? lv(tl, 'setup_down_extreme', cursor, 'setup_down_id') : []);
    },

    tooltipEvent: function (e, d) {
      var x = e.details || {};
      if (e.algorithm !== 'c2_cisd_research') return '';
      var out = [];
      if (x.setup_id) out.push('Setup: <span class="mono">' + x.setup_id + '</span>' + (x.phase ? ' · pha ' + x.phase : '') +
        (x.terminal === true ? ' · KẾT THÚC' : ''));
      if (x.candidate_id) out.push('Ứng viên: <span class="mono">' + x.candidate_id + '</span> (chưa phải setup)');
      if (isFiniteNum(x.cisd_level) && e.structure_type.indexOf('CISD_LEVEL_SET') !== 0) {
        out.push('Mức CISD: ' + Number(x.cisd_level).toFixed(d) +
          (x.cisd_level_source_bar_index != null ? ' (nến nguồn #' + x.cisd_level_source_bar_index + ')' : ''));
      }
      if (x.branch) out.push('Nhánh chọn mức: ' + x.branch + (x.scan_i ? ' (i=' + x.scan_i + ')' : '') + ' · revision ' + x.revision);
      if (x.evidence_bar_index != null) out.push('Close bằng chứng: nến #' + x.evidence_bar_index + ' = ' + Number(x.evidence_close).toFixed(d));
      if (x.early === true) out.push('Early: reclaim trước khi C2 đóng');
      if (isFiniteNum(x.extreme)) out.push('Cực trị C2: ' + Number(x.extreme).toFixed(d));
      if (x.outside_bar_ambiguous) out.push('⚠ Outside bar: C2 đạt cả hai hướng');
      if (x.bucket_start && e.structure_type === 'HTF_BUCKET_INCOMPLETE') {
        out.push('Kỳ H4 ' + fmtIso(x.bucket_start) + ': thấy ' + x.n_bars_seen + '/' + x.expected_bars + ' nến M15 (tới lúc phát hiện)');
      }
      if (x.missing_ltf_bars != null) out.push('Thiếu ' + x.missing_ltf_bars + ' nến M15');
      return out.length ? '<br>' + out.join('<br>') : '';
    }
  };

  // ------------------------------------------------------------------ trang Thử nghiệm

  /**
   * Cảnh báo tách bạch: alignment, warm-up, thiếu dữ liệu, không có setup.
   */
  function notes(stats, dataStatus, pending) {
    var m = (stats && stats.chi_so_thuat_toan) || null;
    var out = [];
    out.push(['info', 'C2 + CISD (bản nghiên cứu closed-bar, <strong>chưa xác minh parity với Pine</strong>). ' +
      'Kỳ H4 theo <strong>mốc UTC epoch</strong> (00/04/08/12/16/20 UTC) — chưa đối chiếu với H4 của broker/TradingView. ' +
      'Marker C2 neo tại nến cực trị nhưng chỉ xuất hiện sau khi C2 đóng; đường mức chỉ bắt đầu từ nến sau lúc mức được biết.']);
    if (dataStatus === 'WARMUP_INSUFFICIENT') {
      out.push(['warn', '<strong>Warm-up:</strong> cần ít nhất 2 kỳ H4 đủ nến (32 nến M15) trước khi có C1/C2 hợp lệ.']);
    }
    var gaps = m ? m.so_gap_ltf : (pending ? pending.so_gap_ltf : 0);
    var inc = m ? m.so_ky_htf_thieu_nen : (pending ? pending.so_ky_htf_thieu : 0);
    if (inc || gaps) {
      var killed = m && m.ket_thuc_theo_ly_do ? (m.ket_thuc_theo_ly_do.SETUP_LTF_GAP || 0) : null;
      out.push(['warn', '<strong>Dữ liệu thiếu:</strong> ' + gaps + ' chỗ gap M15, ' + inc + ' kỳ H4 thiếu nến — không dùng làm C1/C2/C3/C4, không tự bù.' +
        (killed !== null ? ' <strong>' + killed + '</strong> setup dừng vì gap (không phải bị giá phá).' : '') +
        ' XAUUSD nghỉ phiên hằng ngày nên kỳ 20:00 UTC thường thiếu.']);
    }
    if (m && dataStatus === 'OK' && !m.tong_setup) {
      out.push(['info', '<strong>Không có setup C2 nào</strong> trong khoảng này (dữ liệu vẫn hợp lệ). Đây không phải lỗi.']);
    }
    return out;
  }

  function statsHtml(m, res) {
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

  function afterStats(res) {
    var mb = document.querySelector('#c2-mfe-btn');
    if (mb) mb.addEventListener('click', function () { loadExcursion(res.run_id); });
  }

  async function loadExcursion(runId) {
    var body = document.querySelector('#c2-mfe-body');
    var h = parseInt((document.querySelector('#c2-horizon') || {}).value, 10) || 16;
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

  function pendingHtml(ps, d) {
    if (!ps.setup_dang_mo) return null;
    function f(x) { return x === null || x === undefined ? '—' : Number(x).toFixed(d); }
    function setup(s) {
      if (!s) return '— không có —';
      return esc(s.setup_id) + ' · pha ' + esc(s.phase) + ' · cực trị ' + f(s.extreme) + ' · mức CISD ' + f(s.cisd_level) +
        (s.cisd_confirmed ? ' · CISD đã xác nhận' : ' · chưa có CISD') + (s.c4_invalid ? ' · C4 không hợp lệ' : '');
    }
    function lv(x) {
      if (!x) return '— chưa có —';
      return f(x.price) + ' (nguồn #' + x.source_bar_index + ', biết lúc #' + x.set_bar_index + ', ' + esc(x.branch) +
        ', rev ' + x.revision + (x.reclaimed ? ', đã reclaim' : '') + ')';
    }
    var k = ps.ky_htf_hien_tai;
    return '<div class="info-card"><dl>' +
      '<dt>Setup tăng đang mở</dt><dd class="mono">' + setup(ps.setup_dang_mo.up) + '</dd>' +
      '<dt>Setup giảm đang mở</dt><dd class="mono">' + setup(ps.setup_dang_mo.down) + '</dd>' +
      '<dt>Mức CISD tăng đang theo dõi</dt><dd class="mono">' + lv(ps.muc_cisd_dang_theo_doi.up) + '</dd>' +
      '<dt>Mức CISD giảm đang theo dõi</dt><dd class="mono">' + lv(ps.muc_cisd_dang_theo_doi.down) + '</dd>' +
      '<dt>Kỳ H4 hiện tại</dt><dd class="mono">' + (k ? fmtIso(k.start) + ' — ' + k.n_bars + '/' + k.expected_bars + ' nến' + (k.complete ? '' : ' (chưa đủ)') : '—') + '</dd>' +
      '<dt>Gap M15 / kỳ H4 thiếu / kỳ H4 đủ</dt><dd>' + ps.so_gap_ltf + ' / ' + ps.so_ky_htf_thieu + ' / ' + ps.so_ky_htf_du + '</dd>' +
      '</dl></div>';
  }

  // ------------------------------------------------------------------ trang Gán nhãn

  /** CISD: nhãn ở nến có close vượt mức — mặc định close. C2 tăng quét low (giá = low), C2 giảm quét high. */
  function labelPrice(type, bar) {
    if (String(type).indexOf('CISD_') === 0) return bar.close;
    if (type === 'C2_CONFIRMED_UP') return bar.low;
    if (type === 'C2_CONFIRMED_DOWN') return bar.high;
    return undefined;
  }

  MSL.algos.register({
    id: 'c2_cisd',
    algorithms: ['c2_cisd_research'],
    layers: { c2: true, cisd: true, lifecycle: true, dataq: true },
    labelTypes: [
      { id: 'C2_CONFIRMED_UP', label: 'C2 tăng (nến cực trị)', sw: COLORS.c2Up, short: 'C2↑' },
      { id: 'C2_CONFIRMED_DOWN', label: 'C2 giảm (nến cực trị)', sw: COLORS.c2Down, short: 'C2↓' },
      { id: 'CISD_CONFIRMED_UP', label: 'CISD tăng (nến close vượt)', sw: COLORS.cisdUp, short: 'CI↑' },
      { id: 'CISD_CONFIRMED_DOWN', label: 'CISD giảm (nến close vượt)', sw: COLORS.cisdDown, short: 'CI↓' }
    ],
    labelPrice: labelPrice,
    chart: chart,
    notes: notes,
    statsHtml: statsHtml,
    afterStats: afterStats,
    pendingHtml: pendingHtml
  });
})(window.MSL);
