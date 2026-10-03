/* Trang Đánh giá — chi tiết run đang chọn: tổng quan, bằng chứng, bảng TP/FP/FN, chart overlay. */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = E.S;

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
