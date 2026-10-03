/* Trang Đánh giá — chạy đánh giá, dòng meta, thẻ metric, bảng so sánh cấu hình, chọn run. */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;
  var S = E.S;

  function scoredRuns() {
    var out = [];
    if (!S.result) return out;
    (S.result.groups || []).forEach(function (g) {
      if (!g.comparable) return;
      (g.runs || []).forEach(function (r) { out.push(r); });
    });
    return out;
  }

  function selectedRun() {
    var list = scoredRuns();
    return list.filter(function (r) { return r.run_id === S.selectedRunId; })[0] || list[0] || null;
  }

  function selectedGroupRuns() {
    var id = S.selectedRunId;
    var groups = (S.result && S.result.groups) || [];
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i];
      if (!g.comparable) continue;
      var members = g.runs || [];
      if (!id || members.some(function (r) { return r.run_id === id; })) return members;
    }
    return scoredRuns();
  }

  async function evaluate() {
    E.showError('');
    var ids = E.checkedRunIds();
    if (!ids.length) { E.showError('Chọn ít nhất một lần chạy.'); return; }
    $('#btn-evaluate').disabled = true;
    try {
      var out = await API.createEvaluation({
        run_ids: ids,
        protocol: E.protocolFromForm(),
        label_set_id: $('#label-set-select').value || null,
        baseline_run_id: $('#baseline-select').value || null,
        save: true,
        note_vi: ''
      });
      await showResult(out);
      location.hash = out.evaluation_id || '';
      await E.loadSaved();
    } catch (e) {
      E.showError(e.message);
    } finally {
      $('#btn-evaluate').disabled = false;
    }
  }

  async function showResult(out) {
    S.result = out;
    var list = scoredRuns();
    S.selectedRunId = out.selected_run_id || (list[0] && list[0].run_id) || null;
    S.selectedEvent = null;
    $('#btn-export').disabled = !out.evaluation_id;
    renderMeta();
    renderCards();
    renderTable();
    E.renderScatter();
    E.renderHist();
    await E.renderDetail();
  }

  function renderMeta() {
    var r = S.result;
    var ds = r.dataset || {};
    var cov = r.coverage || {};
    var ls = r.label_set;
    var run = selectedRun();
    var val = run && run.validity ? run.validity : {};
    var st = val.status || 'chua_kiem_tra';
    var stClass = st === 'dat_kiem_tra' ? 'ok' : (st === 'co_vi_pham' ? 'bad' : 'warn');
    var kind = ds.is_synthetic ? 'Dữ liệu mô phỏng' : 'Dữ liệu thực tế';
    $('#eval-meta').innerHTML =
      '<span>' + esc(kind) + ' · ' + esc(ds.name || ds.id || '—') + ' · ' +
        esc(ds.symbol || '') + ' ' + esc(ds.timeframe || '') + '</span>' +
      '<span>Số nến dataset: ' + esc(ds.row_count != null ? ds.row_count : '—') +
        ' · Nhãn trong khoảng chấm: ' + esc(cov.n_labels_in_coverage) + '</span>' +
      '<span>Protocol ' + esc(r.protocol_version) + ' · matcher <code>' + esc(r.matcher_version) +
        '</code> · hash <code>' + esc(r.protocol_hash) + '</code></span>' +
      '<span>Mục tiêu: ' + esc(r.target_label_vi) + '</span>' +
      '<span>Bộ nhãn: ' + (ls ? esc(ls.annotator + ' v' + ls.version) : 'không có') + '</span>' +
      '<span class="' + stClass + '">Kiểm tra nhân quả: ' + esc(val.status_label_vi || 'Chưa kiểm tra') + '</span>' +
      '<span>Đánh giá ' + E.fmtNum(r.duration_ms, 1) + ' ms</span>' +
      provenanceSpan(r.nguon_nhan);

    // Nhãn do chính thuật toán được chấm đề xuất -> F1 bị thổi phồng.
    var warn = $('#eval-provenance-warn');
    var ws = r.canh_bao_nguon_nhan || [];
    warn.hidden = !ws.length;
    warn.innerHTML = ws.length
      ? '<strong>Nhãn không độc lập với thuật toán được chấm.</strong> ' + ws.map(esc).join(' ')
      : '';
  }

  function provenanceSpan(p) {
    if (!p || !p.tong) return '';
    var parts = [p.nguoi_gan + ' người gán'];
    var by = p.auto_theo_thuat_toan || {};
    Object.keys(by).forEach(function (k) { parts.push(by[k] + ' auto từ ' + k); });
    var ed = p.auto_sua_theo_thuat_toan || {};
    Object.keys(ed).forEach(function (k) { parts.push(ed[k] + ' auto từ ' + k + ' (người đã sửa)'); });
    return '<span>Nguồn nhãn: ' + esc(parts.join(' · ')) + '</span>';
  }

  function naQuality(txt) {
    return '<span class="metric-v na">' + esc(txt) + '</span>';
  }

  function renderCards() {
    var el = $('#metric-cards');
    el.hidden = false;
    var run = selectedRun();
    if (!run) {
      ['precision', 'recall', 'f1', 'lag'].forEach(function (k) {
        $('#m-' + (k === 'lag' ? 'lag' : k)).textContent = '—';
      });
      return;
    }
    $$('.metric-card').forEach(function (c) { c.classList.add('selected-run'); });
    var q = run.quality || {};
    var lag = run.lag || {};
    var d = run.delta_vs_baseline || {};
    var noLab = 'Chưa có nhãn tham chiếu';
    if (!q.has_labels) {
      $('#m-precision').className = 'metric-v na';
      $('#m-precision').textContent = noLab;
      $('#m-recall').className = 'metric-v na';
      $('#m-recall').textContent = noLab;
      $('#m-f1').className = 'metric-v na';
      $('#m-f1').textContent = noLab;
      $('#m-precision-sub').textContent = q.note_vi || '';
      $('#m-recall-sub').textContent = '';
      $('#m-f1-sub').textContent = 'Không hiện số 0.';
      $('#m-precision-delta').innerHTML = '';
      $('#m-recall-delta').innerHTML = '';
      $('#m-f1-delta').innerHTML = '';
    } else {
      $('#m-precision').className = 'metric-v';
      $('#m-recall').className = 'metric-v';
      $('#m-f1').className = 'metric-v';
      $('#m-precision').textContent = E.fmtNum(q.precision, 3);
      $('#m-recall').textContent = E.fmtNum(q.recall, 3);
      $('#m-f1').textContent = E.fmtNum(q.f1, 3);
      $('#m-precision-sub').textContent = 'TP ' + q.true_positives + ' / FP ' + q.false_positives;
      $('#m-recall-sub').textContent = 'TP ' + q.true_positives + ' / FN ' + q.false_negatives;
      $('#m-f1-sub').textContent = 'Nhãn ' + q.n_labels + ' · sự kiện ' + q.n_events_scored;
      $('#m-precision-delta').innerHTML = E.fmtDelta(d.precision, 3, false);
      $('#m-recall-delta').innerHTML = E.fmtDelta(d.recall, 3, false);
      $('#m-f1-delta').innerHTML = E.fmtDelta(d.f1, 3, false);
    }
    $('#m-lag').className = 'metric-v';
    $('#m-lag').textContent = lag.p90 == null ? '—' : E.fmtNum(lag.p90, 1);
    var tf = run.timeframe || (S.result.dataset && S.result.dataset.timeframe) || '';
    $('#m-lag-sub').textContent = 'Median ' + E.fmtNum(lag.median, 1) + ' nến' +
      (tf ? ' ' + tf : '') + ' · n=' + (lag.n || 0) +
      (lag.n_tp ? ' · TP median ' + E.fmtNum(lag.median_tp, 1) : '');
    $('#m-lag-delta').innerHTML = E.fmtDelta(d.lag_p90, 1, true);
    $('#card-precision').title = q.note_vi || '';
    $('#card-f1').title = 'F1 = 2PR/(P+R). Mẫu số: sự kiện và nhãn trong khoảng chấm, đúng loại mục tiêu.';
    $('#card-lag').title = lag.note_vi || '';
    $('#card-recall').title = q.note_vi || '';
  }

  function renderTable() {
    $('#compare-section').hidden = false;
    var groups = S.result.groups || [];
    var comparable = groups.filter(function (g) { return g.comparable && (g.runs || []).length; });
    $('#group-note').textContent = comparable.length
      ? comparable.map(function (g) {
          var tf = g.timeframe || (g.runs[0] && g.runs[0].timeframe) || '';
          return (tf ? tf + ' — ' : '') + (g.reason_vi || '');
        }).join(' ')
      : 'Không có nhóm so sánh được.';
    var tb = $('#compare-table tbody');
    if (!comparable.length) {
      tb.innerHTML = '<tr><td colspan="13" class="empty-cell">Không có run so sánh được.</td></tr>';
    } else {
      var html = '';
      comparable.forEach(function (g) {
        if (comparable.length > 1) {
          var tf = g.timeframe || (g.runs[0] && g.runs[0].timeframe) || '';
          html += '<tr class="group-head"><td colspan="13">' + esc((tf ? 'Khung ' + tf + ' · ' : '') + (g.reason_vi || '')) + '</td></tr>';
        }
        (g.runs || []).forEach(function (r) {
          var q = r.quality || {};
          var lag = r.lag || {};
          var atr = r.price_atr || {};
          var den = r.density || {};
          var val = r.validity || {};
          var sel = r.run_id === S.selectedRunId ? ' selected' : '';
          var base = r.is_baseline ? ' is-baseline' : '';
          var f1 = q.has_labels ? E.fmtNum(q.f1, 3) : 'Chưa có nhãn';
          var p = q.has_labels ? E.fmtNum(q.precision, 3) : '—';
          var rec = q.has_labels ? E.fmtNum(q.recall, 3) : '—';
          html += '<tr class="' + sel + base + '" data-id="' + esc(r.run_id) + '" tabindex="0">' +
            '<td>' + (r.is_baseline ? '<span class="baseline-mark" title="Baseline">◆</span>' : '') + '</td>' +
            '<td class="mono">' + esc(r.run_id) + (r.label ? '<div class="muted">' + esc(r.label) + '</div>' : '') + '</td>' +
            '<td>' + esc(r.timeframe || '—') + '</td>' +
            '<td>' + esc(r.algorithm) + ' v' + esc(r.algorithm_version) + '</td>' +
            '<td class="mono">' + esc(E.paramsStr(r.params)) + '</td>' +
            '<td class="num">' + esc(f1) + '</td>' +
            '<td class="num">' + esc(p) + '</td>' +
            '<td class="num">' + esc(rec) + '</td>' +
            '<td class="num">' + esc(E.fmtNum(lag.p90, 1)) + '</td>' +
            '<td class="num">' + esc(E.fmtNum(lag.median, 1)) + '</td>' +
            '<td class="num">' + esc(E.fmtNum(atr.median_atr_ratio, 3)) + '</td>' +
            '<td class="num">' + esc(E.fmtNum(den.per_100, 2)) + '</td>' +
            '<td><span class="status-text ' + esc(val.status || '') + '">' +
              esc(val.status_label_vi || 'Chưa kiểm tra') + '</span></td></tr>';
        });
      });
      tb.innerHTML = html;
    }
    var excl = [];
    groups.forEach(function (g) {
      if (g.comparable) return;
      (g.excluded || []).forEach(function (x) {
        excl.push(x.run_id + ': ' + x.reason_vi);
      });
      if (g.reason_vi && !(g.excluded || []).length) excl.push(g.reason_vi);
    });
    var box = $('#excluded-box');
    if (excl.length) {
      box.hidden = false;
      box.textContent = 'Tách nhóm — không so sánh chéo: ' + excl.join(' · ');
    } else {
      box.hidden = true;
    }
  }

  async function selectRun(id) {
    if (!id) return;
    S.selectedRunId = id;
    S.selectedEvent = null;
    renderMeta();
    renderCards();
    renderTable();
    E.renderScatter();
    E.renderHist();
    await E.renderDetail();
  }

  E.evaluate = evaluate;
  E.scoredRuns = scoredRuns;
  E.selectRun = selectRun;
  E.selectedGroupRuns = selectedGroupRuns;
  E.selectedRun = selectedRun;
  E.showResult = showResult;
})(window.MSL);
