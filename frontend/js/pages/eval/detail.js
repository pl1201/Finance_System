/* Trang Đánh giá — chi tiết run đang chọn: tổng quan, bằng chứng, bảng TP/FP/FN, chart overlay. */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = E.S;

  function nullStatsRow(label, real, dist) {
    dist = dist || {};
    return '<dt>' + esc(label) + '</dt><dd class="mono">thực tế ' + E.fmtNum(real, 3) + ' · ngẫu nhiên TB ' +
      E.fmtNum(dist.mean, 3) + ' (sd ' + E.fmtNum(dist.sd, 3) + ') [P5 ' + E.fmtNum(dist.p5, 3) + ' – P95 ' +
      E.fmtNum(dist.p95, 3) + ']</dd>';
  }

  /** Khối chuẩn ngẫu nhiên trong tab Tổng quan. */
  function nullHtml(nb) {
    var head = '<div class="section-title">Chuẩn ngẫu nhiên — ' + esc(nb.mode_vi || nb.mode) + ' · ' + nb.n +
      ' lượt · seed ' + esc(nb.seed) + '</div>';
    if (nb.status !== 'ok') return head + '<p class="hint">' + esc(nb.note_vi || nb.status) + '</p>';
    var real = nb.real || {};
    var rules = Object.keys(nb.price_rule || {}).map(function (k) { return k + '=' + nb.price_rule[k]; }).join(', ');
    return head + '<div class="info-card"><dl>' +
      nullStatsRow('F1', real.f1, nb.f1) +
      nullStatsRow('Precision', real.precision, nb.precision) +
      nullStatsRow('Recall', real.recall, nb.recall) +
      '<dt>Thực tế so với ngẫu nhiên</dt><dd>' + nb.n_ge_real + '/' + nb.n + ' lượt có F1 ≥ thực tế (p ≈ ' +
        E.fmtNum(nb.p_ge, 4) + ') · thực tế ở phân vị ' + E.fmtNum(nb.percentile, 1) + ' · chênh TB ' +
        E.fmtNum(nb.f1_minus_mean, 3) + '</dd>' +
      '<dt>Sai số chuẩn thực tế</dt><dd class="mono">P ± ' + E.fmtNum(real.precision_se, 3) + ' · R ± ' +
        E.fmtNum(real.recall_se, 3) + ' (xấp xỉ lạc quan)</dd>' +
      '<dt>Phạm vi đặt</dt><dd>' + nb.eligible_bars + ' nến đủ điều kiện · ' + nb.n_windows + ' cửa sổ · ' +
        nb.n_events + ' sự kiện · ' + nb.n_labels + ' nhãn · giá theo ' + esc(rules || '—') +
        (nb.strata ? ' · ' + nb.strata.n_strata + ' nhóm, bù ' + nb.strata.fallback_events + ' sự kiện' : '') + '</dd>' +
      '</dl></div><p class="hint">' + esc(nb.note_vi || '') + '</p>';
  }

  var SEG_STATUS_VI = {
    khoa: 'Đang khoá — chưa chấm',
    ngoai_khoang: 'Ngoài khoảng run đã chạy / khoảng chấm'
  };

  /** Bảng số theo đoạn phát triển / kiểm tra. */
  function segmentsHtml(run) {
    var rows = (run.by_segment || []).map(function (sg) {
      var span = esc(String(sg.start).slice(0, 16).replace('T', ' ')) + ' → ' + esc(String(sg.end).slice(0, 16).replace('T', ' '));
      var head = '<td>' + esc(sg.name) + '</td><td>' + (sg.role === 'test' ? 'kiểm tra' : 'phát triển') + '</td><td class="mono">' + span + '</td>';
      if (sg.status !== 'ok') return '<tr>' + head + '<td colspan="7" class="seg-locked">' + esc(SEG_STATUS_VI[sg.status] || sg.status) + '</td></tr>';
      var q = sg.quality || {};
      var nb = sg.null_baseline;
      return '<tr>' + head +
        '<td class="num">' + esc(sg.n_bars) + '</td>' +
        '<td class="num">' + (q.has_labels ? E.fmtNum(q.f1, 3) : 'chưa có nhãn') + '</td>' +
        '<td class="num">' + E.fmtNum(q.precision, 3) + '</td>' +
        '<td class="num">' + E.fmtNum(q.recall, 3) + '</td>' +
        '<td class="num">' + (q.has_labels ? q.true_positives + '/' + q.false_positives + '/' + q.false_negatives : '—') + '</td>' +
        '<td class="num">' + E.fmtNum((sg.lag || {}).p90, 1) + '</td>' +
        '<td class="num">' + (nb && nb.status === 'ok' ? E.fmtNum((nb.f1 || {}).mean, 3) + ' (' + nb.n_ge_real + '/' + nb.n + ' ≥)' : '—') + '</td>' +
        '</tr>';
    }).join('');
    return '<div class="section-title">Theo đoạn</div>' +
      '<p class="hint">' + esc(run.segments_note_vi || '') + '</p>' +
      '<div class="table-scroll small"><table class="data-table"><thead><tr>' +
      '<th>Đoạn</th><th>Vai</th><th>Từ → đến (UTC)</th><th class="num">Nến</th><th class="num">F1</th><th class="num">P</th>' +
      '<th class="num">R</th><th class="num">TP/FP/FN</th><th class="num">Trễ P90</th><th class="num">F1 ngẫu nhiên</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }

  async function renderDetail() {
    var run = E.selectedRun();
    $('#detail-section').hidden = !run;
    if (!run) return;
    $('#detail-run-id').textContent = run.run_id + (run.is_baseline ? ' · baseline' : '');
    var q = run.quality || {};
    var lag = run.lag || {};
    var atr = run.price_atr || {};
    var den = run.density || {};
    var perf = run.performance || {};
    var ign = run.counts_ignored || {};
    var side = q.by_side || {};
    $('#panel-overview').innerHTML =
      '<div class="pad">' +
      '<div class="info-card"><dl>' +
      '<dt>Thuật toán</dt><dd>' + esc(run.algorithm) + ' v' + esc(run.algorithm_version) + '</dd>' +
      '<dt>Tham số</dt><dd class="mono">' + esc(E.paramsStr(run.params)) + '</dd>' +
      '<dt>Ánh xạ loại</dt><dd class="mono">' + esc(E.paramsStr(run.event_type_map)) + '</dd>' +
      '<dt>High F1</dt><dd class="mono">' + (side.high && q.has_labels ? E.fmtNum(side.high.f1, 3) + ' (TP ' + side.high.true_positives + ')' : '—') + '</dd>' +
      '<dt>Low F1</dt><dd class="mono">' + (side.low && q.has_labels ? E.fmtNum(side.low.f1, 3) + ' (TP ' + side.low.true_positives + ')' : '—') + '</dd>' +
      '<dt>Khoảng giá lúc xác nhận</dt><dd>median ' + E.fmtNum(atr.median_distance, 4) + ' · P90 ' + E.fmtNum(atr.p90_distance, 4) +
        ' · /ATR median ' + E.fmtNum(atr.median_atr_ratio, 3) + ' (n=' + (atr.n || 0) + ', loại ATR ' + (atr.n_atr_invalid || 0) + ')</dd>' +
      '<dt>Mật độ</dt><dd>' + E.fmtNum(den.per_100, 2) + ' swing / 100 nến · khoảng cách median ' + E.fmtNum(den.median_gap_bars, 1) + ' nến</dd>' +
      '<dt>Bỏ qua</dt><dd>ngoài map ' + ign.unmapped_type + ' · ngoài khoảng chấm ' + ign.outside_coverage +
        ' · đuôi chưa xác nhận ' + ign.unconfirmed_tail + ' · quá max trễ ' + ign.over_max_lag + '</dd>' +
      '<dt>Thời gian</dt><dd>thuật toán ' + E.fmtNum(perf.algorithm_ms, 1) + ' ms · đánh giá ' + E.fmtNum(perf.evaluation_ms, 1) + ' ms</dd>' +
      '</dl></div>' +
      '<p class="hint">' + esc(atr.formula_vi || '') + '</p>' +
      '<p class="hint">' + esc(den.note_vi || '') + '</p>' +
      (run.null_baseline ? nullHtml(run.null_baseline) : '') +
      (run.by_segment ? segmentsHtml(run) : '') +
      '</div>';

    var val = run.validity || {};
    var checks = (val.checks || []).map(function (c) {
      return '<li>' + (c.ok ? 'Đạt' : 'Không đạt') + ' — ' + esc(c.label_vi) + '</li>';
    }).join('');
    var viol = (val.violations || []).slice(0, 20).map(function (v) {
      return '<li class="mono">' + esc(v) + '</li>';
    }).join('');
    $('#panel-evidence').innerHTML =
      '<div class="pad">' +
      '<p><span class="status-text ' + esc(val.status || '') + '">' + esc(val.status_label_vi || '') + '</span></p>' +
      '<p class="hint">' + esc(val.note_vi || '') + '</p>' +
      '<p class="hint">' + esc(val.pham_vi_vi || '') + '</p>' +
      '<ul>' + checks + '</ul>' +
      (viol ? '<div class="section-title">Vi phạm</div><ul>' + viol + '</ul>' : '') +
      '<p class="hint">Pytest xanh của bộ test không suy ra trạng thái này cho mọi run.</p>' +
      '</div>';

    renderEventTable();
    await loadChart(run);
  }

  function eventRows(run) {
    var rows = [];
    (run.matches || []).forEach(function (e) {
      rows.push({
        role: 'tp', bar: e.event_bar_index, type: e.structure_type, price: e.price,
        lag: e.lag, extra: 'nhãn #' + e.label_seq + ' Δ' + e.delta_bars,
        event_id: e.event_id, label_seq: e.label_seq
      });
    });
    (run.false_positives || []).forEach(function (e) {
      rows.push({
        role: 'fp', bar: e.event_bar_index, type: e.structure_type, price: e.price,
        lag: e.lag, extra: e.event_id || '', event_id: e.event_id
      });
    });
    (run.false_negatives || []).forEach(function (e) {
      rows.push({
        role: 'fn', bar: e.bar_index, type: e.structure_type, price: e.price,
        lag: '—', extra: 'seq ' + e.label_seq, label_seq: e.label_seq
      });
    });
    return rows;
  }

  function renderEventTable() {
    var run = E.selectedRun();
    var tb = $('#evt-table tbody');
    if (!run) { tb.innerHTML = ''; return; }
    if (!run.quality || !run.quality.has_labels) {
      tb.innerHTML = '<tr><td colspan="6" class="empty-cell">Chưa có nhãn tham chiếu — không có TP/FP/FN. Chart vẫn hiện nến của run.</td></tr>';
      return;
    }
    var q = ($('#evt-search').value || '').toLowerCase();
    var show = { tp: $('#flt-tp').checked, fp: $('#flt-fp').checked, fn: $('#flt-fn').checked };
    var rows = eventRows(run).filter(function (r) {
      if (!show[r.role]) return false;
      if (!q) return true;
      return (r.type + ' ' + r.role + ' ' + (r.extra || '') + ' ' + (r.event_id || '')).toLowerCase().indexOf(q) >= 0;
    });
    if (!rows.length) {
      tb.innerHTML = '<tr><td colspan="6" class="empty-cell">Không có sự kiện khớp bộ lọc.</td></tr>';
      return;
    }
    tb.innerHTML = rows.map(function (r, i) {
      var sel = S.selectedEvent && S.selectedEvent.role === r.role && S.selectedEvent.bar_index === r.bar
        ? ' selected' : '';
      return '<tr class="' + sel + '" data-i="' + i + '" data-role="' + r.role +
        '" data-bar="' + r.bar + '" data-eid="' + esc(r.event_id || '') +
        '" data-seq="' + (r.label_seq != null ? r.label_seq : '') + '">' +
        '<td class="role-' + r.role + '">' + r.role.toUpperCase() + '</td>' +
        '<td><span class="badge b-' + esc(r.type) + '">' + esc(r.type) + '</span></td>' +
        '<td class="num">' + r.bar + '</td>' +
        '<td class="num">' + E.fmtNum(r.price, S.digits) + '</td>' +
        '<td class="num">' + esc(r.lag) + '</td>' +
        '<td class="mono">' + esc(r.extra) + '</td></tr>';
    }).join('');
  }

  async function loadChart(run) {
    $('#eval-chart-empty').hidden = true;
    var key = run.dataset_id + '|' + (run.range_start || '') + '|' + (run.range_end || '');
    var payload;
    if (S.barsCache[key]) payload = S.barsCache[key];
    else {
      payload = await API.bars(run.dataset_id, run.range_start, run.range_end);
      // Kết quả chấm và nhãn dùng chỉ số nến của dataset → đánh số nến chart theo dataset.
      (payload.bars || []).forEach(function (b) {
        if (b.dataset_index !== undefined && b.dataset_index !== null) b.index = b.dataset_index;
      });
      S.barsCache[key] = payload;
    }
    S.digits = E.detectDigits(payload.bars);
    S.chart.setDigits(S.digits);
    S.chart.setBars(payload.bars);
    S.labels = [];
    var lsId = (S.result.label_set && S.result.label_set.id) || $('#label-set-select').value;
    if (lsId) {
      try {
        var ls = await API.getLabelSet(lsId);
        S.labels = ls.labels || [];
      } catch (e) { S.labels = []; }
    }
    paintOverlay();
    S.chart.fit();
  }

  function paintOverlay() {
    var run = E.selectedRun();
    if (!run || !S.chart) return;
    S.chart.setEvalOverlay({
      matches: run.matches || [],
      false_positives: run.false_positives || [],
      false_negatives: run.false_negatives || [],
      labels: S.labels,
      selected: S.selectedEvent
    });
  }

  function jumpToEvent(row) {
    S.selectedEvent = {
      role: row.role,
      bar_index: Number(row.bar),
      event_id: row.event_id || undefined,
      label_seq: row.label_seq === '' || row.label_seq == null ? undefined : Number(row.label_seq)
    };
    paintOverlay();
    renderEventTable();
    S.chart.scrollToIndex(Number(row.bar));
  }

  E.jumpToEvent = jumpToEvent;
  E.renderDetail = renderDetail;
  E.renderEventTable = renderEventTable;
})(window.MSL);
