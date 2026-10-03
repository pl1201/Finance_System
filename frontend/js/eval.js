/* Trang Đánh giá thuật toán — chọn run, protocol, metric, chart TP/FP/FN. */
(function () {
  'use strict';

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };

  var S = {
    datasets: [],
    dataset: null,
    runs: [],
    selectedIds: {},
    baselineId: '',
    result: null,
    saved: [],
    selectedRunId: null,
    selectedEvent: null,
    labels: [],
    chart: null,
    barsCache: {},
    digits: 2,
    meta: null
  };

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmtNum(x, d) {
    if (x === null || x === undefined || x === '') return '—';
    var n = Number(x);
    if (!isFinite(n)) return '—';
    return n.toFixed(d);
  }

  function fmtDelta(x, d, invert) {
    if (x === null || x === undefined) return '';
    var n = Number(x);
    if (!isFinite(n)) return '';
    var good = invert ? n < 0 : n > 0;
    var cls = n === 0 ? 'flat' : (good ? 'up' : 'dn');
    var sign = n > 0 ? '+' : '';
    return '<span class="' + cls + '">' + sign + n.toFixed(d) + ' vs baseline</span>';
  }

  function paramsStr(p) {
    if (!p) return '—';
    try { return JSON.stringify(p); } catch (e) { return String(p); }
  }

  function detectDigits(bars) {
    var maxD = 0;
    for (var i = 0; i < Math.min(bars.length, 200); i++) {
      var v = String(bars[i].close);
      var dot = v.indexOf('.');
      if (dot >= 0) maxD = Math.max(maxD, v.length - dot - 1);
    }
    return Math.min(5, Math.max(2, maxD));
  }

  function showError(msg) {
    var el = $('#eval-error');
    if (!msg) { el.hidden = true; el.textContent = ''; return; }
    el.hidden = false;
    el.textContent = msg;
  }

  /** Ánh xạ khai báo rõ để chấm pivot DC (close) với nhãn swing cấp 1 (thường theo wick). */
  var DC_CROSS_MAP = {
    SWING_HIGH: 'SWING_HIGH', SWING_LOW: 'SWING_LOW', DC_HIGH: 'SWING_HIGH', DC_LOW: 'SWING_LOW'
  };

  function dcCrossActive() {
    return $('#chk-map-dc').checked && $('#target-select').value === 'swing_nho';
  }

  function protocolFromForm() {
    var emptyInt = function (id) {
      var v = $(id).value;
      return v === '' ? null : Number(v);
    };
    var extra = dcCrossActive() ? { event_type_map: DC_CROSS_MAP } : {};
    return Object.assign({
      target: $('#target-select').value,
      matcher_version: $('#matcher-select').value,
      time_tolerance_bars: Number($('#tol-bars').value || 0),
      price_tolerance: Number($('#tol-price').value || 0),
      coverage_start_index: emptyInt('#cov-start'),
      coverage_end_index: emptyInt('#cov-end'),
      map_level1_to_structure: $('#chk-map-l1').checked,
      atr_period: Number($('#atr-period').value || 14),
      exclude_unconfirmed_tail: $('#chk-exclude-tail').checked,
      max_lag_bars: emptyInt('#max-lag'),
      min_recall: emptyInt('#min-recall')
    }, extra);
  }

  function applyProtocol(p) {
    if (!p) return;
    if (p.target) $('#target-select').value = p.target;
    if (p.matcher_version) $('#matcher-select').value = p.matcher_version;
    if (p.time_tolerance_bars !== undefined) $('#tol-bars').value = p.time_tolerance_bars;
    if (p.price_tolerance !== undefined) $('#tol-price').value = p.price_tolerance;
    $('#cov-start').value = p.coverage_start_index == null ? '' : p.coverage_start_index;
    $('#cov-end').value = p.coverage_end_index == null ? '' : p.coverage_end_index;
    $('#chk-map-l1').checked = !!p.map_level1_to_structure;
    $('#chk-map-dc').checked = !!(p.event_type_map && p.event_type_map.DC_HIGH);
    if (p.atr_period) $('#atr-period').value = p.atr_period;
    $('#chk-exclude-tail').checked = p.exclude_unconfirmed_tail !== false;
    $('#max-lag').value = p.max_lag_bars == null ? '' : p.max_lag_bars;
    $('#min-recall').value = p.min_recall == null ? '' : p.min_recall;
    updateTargetHelp();
  }

  function updateTargetHelp() {
    var t = $('#target-select').value;
    var map = $('#chk-map-l1').checked;
    var help = (S.meta && S.meta.targets || []).filter(function (x) { return x.id === t; })[0];
    var extra = map && t === 'swing_cau_truc'
      ? ' Run cấp 1 được ánh xạ SWING_HIGH→SWING_HIGH_L2, SWING_LOW→SWING_LOW_L2 — không trộn tên loại.'
      : '';
    var dcBox = $('#chk-map-dc');
    dcBox.disabled = t !== 'swing_nho';
    if (dcCrossActive()) {
      extra += ' ⚠ Đang chấm pivot DC theo CLOSE với nhãn swing (thường theo WICK): so sánh CHÉO ĐỊNH NGHĨA — ' +
        'chênh giá do khác nguồn giá là bình thường; nên nới dung sai giá hoặc chỉ chấm theo thời gian, và ghi rõ khi báo cáo.';
    }
    $('#target-help').textContent = (help ? help.help_vi : '') + extra;
  }

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

  var TF_ORDER = ['M5', 'M15', 'M30', 'H1', 'H4'];
  var TF_SEC = { M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400 };

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

  function findSiblingDataset(symbol, tf, current) {
    var cands = S.datasets.filter(function (d) {
      return d.symbol === symbol && d.timeframe === tf;
    });
    if (!cands.length) return null;
    if (current) {
      var sameFlag = cands.filter(function (d) { return !!d.is_synthetic === !!current.is_synthetic; });
      if (sameFlag.length) cands = sameFlag;
    }
    return cands[0];
  }

  function renderTfSwitch() {
    var box = $('#tf-switch');
    var hint = $('#tf-hint');
    if (!box) return;
    if (!S.dataset) {
      box.innerHTML = TF_ORDER.map(function (tf) {
        return '<button type="button" class="tf-btn" data-tf="' + tf + '" disabled>' + tf + '</button>';
      }).join('');
      if (hint) hint.hidden = false;
      return;
    }
    var cur = S.dataset;
    box.innerHTML = TF_ORDER.map(function (tf) {
      var sib = findSiblingDataset(cur.symbol, tf, cur);
      var cls = 'tf-btn';
      var title;
      if (tf === cur.timeframe) {
        cls += ' active';
        title = 'Khung đang chọn';
      } else if (sib) {
        cls += ' available';
        title = 'Chuyển sang ' + cur.symbol + ' ' + tf + ' (' + sib.row_count + ' nến)';
      } else {
        cls += ' down';
        title = 'Chưa có dataset ' + cur.symbol + ' ' + tf + '. Tạo ở trang Thử nghiệm — trang này không tổng hợp/tách nến.';
      }
      return '<button type="button" class="' + cls + '" data-tf="' + tf + '" title="' + esc(title) + '"' +
        (sib || tf === cur.timeframe ? '' : ' disabled') + '>' + tf + '</button>';
    }).join('');
    $$('#tf-switch [data-tf]').forEach(function (b) {
      b.addEventListener('click', function () { switchTimeframe(b.getAttribute('data-tf')); });
    });
    if (hint) {
      hint.hidden = false;
      hint.textContent = 'M5 / M15 / H1 là dataset khác nhau. Độ trễ là số nến khung ' +
        (cur.timeframe || '') + ' — không đổi ra phút, không so chéo khung.';
    }
  }

  async function switchTimeframe(tf) {
    if (!S.dataset) return;
    tf = String(tf || '').toUpperCase();
    if (tf === S.dataset.timeframe) return;
    var sib = findSiblingDataset(S.dataset.symbol, tf, S.dataset);
    if (!sib) {
      showError('Chưa có dataset ' + S.dataset.symbol + ' ' + tf +
        '. Hãy tạo hoặc nhập ở trang Thử nghiệm. Trang đánh giá không tổng hợp hay tách nến.');
      return;
    }
    showError('');
    $('#dataset-select').value = sib.id;
    await onDatasetChange();
  }

  async function boot() {
    try {
      var h = await API.health();
      $('#health-pill').textContent = 'Backend OK · v' + h.version;
      $('#health-pill').className = 'pill pill-ok';
    } catch (e) {
      $('#health-pill').textContent = 'Backend lỗi';
      $('#health-pill').className = 'pill pill-bad';
    }
    try { S.meta = await API.evalMeta(); } catch (e) { S.meta = { targets: [] }; }
    updateTargetHelp();
    S.chart = new MarketChart($('#eval-chart'), $('#eval-tooltip'));
    S.datasets = await API.datasets();
    renderDatasets();
    await loadSaved();
    bind();
    var params = new URLSearchParams(location.search || '');
    var dsQ = params.get('dataset_id');
    if (dsQ) {
      $('#dataset-select').value = dsQ;
      try { await onDatasetChange(); } catch (e) { showError(e.message); }
    }
    var lsQ = params.get('label_set_id');
    if (lsQ) $('#label-set-select').value = lsQ;
    var hash = (location.hash || '').replace(/^#/, '');
    if (hash.indexOf('ev_') === 0) {
      try { await openSaved(hash); } catch (e) { showError(e.message); }
    }
  }

  function renderDatasets() {
    var sel = $('#dataset-select');
    var cur = sel.value;
    var sorted = S.datasets.slice().sort(function (a, b) {
      if (a.symbol !== b.symbol) return String(a.symbol).localeCompare(String(b.symbol));
      var ia = TF_ORDER.indexOf(a.timeframe);
      var ib = TF_ORDER.indexOf(b.timeframe);
      if (ia !== ib) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
      return String(a.name).localeCompare(String(b.name));
    });
    sel.innerHTML = '<option value="">— chọn dataset —</option>' + sorted.map(function (d) {
      return '<option value="' + esc(d.id) + '">' + esc(d.symbol) + ' ' + esc(d.timeframe) +
        ' · ' + esc(d.name) + (d.is_synthetic ? ' (mô phỏng)' : '') +
        ' · ' + (d.row_count != null ? d.row_count + ' nến' : '') + '</option>';
    }).join('');
    if (cur) sel.value = cur;
    renderTfSwitch();
  }

  async function onDatasetChange() {
    var id = $('#dataset-select').value;
    S.dataset = S.datasets.filter(function (d) { return d.id === id; })[0] || null;
    S.selectedIds = {};
    renderTfSwitch();
    if (!id) {
      S.runs = [];
      renderRunPicker();
      renderLabelSets([]);
      return;
    }
    S.runs = await API.runs(id);
    var sets = await API.labelSets(id);
    renderLabelSets(sets);
    renderRunPicker();
    fillBaselineSelect();
    await loadSaved();
  }

  function renderLabelSets(sets) {
    var sel = $('#label-set-select');
    var cur = sel.value;
    sel.innerHTML = '<option value="">— không có nhãn (chỉ độ trễ / mật độ) —</option>' +
      (sets || []).map(function (s) {
        return '<option value="' + esc(s.id) + '">' + esc(s.annotator) + ' · v' + esc(s.version) +
          ' · ' + (s.n_labels || (s.labels ? s.labels.length : '?')) + ' nhãn' +
          (s.n_auto ? ' (' + s.n_auto + ' từ auto label)' : '') + '</option>';
      }).join('');
    if (cur) sel.value = cur;
  }

  function checkedRunIds() {
    return $$('#run-picker-table .run-ck').filter(function (el) {
      return el.checked;
    }).map(function (el) {
      return el.getAttribute('data-id');
    });
  }

  function renderRunPicker() {
    var tb = $('#run-picker-table tbody');
    if (!S.runs.length) {
      tb.innerHTML = '<tr><td colspan="8" class="empty-cell">Dataset này chưa có lần chạy. Hãy tạo ở trang Thử nghiệm.</td></tr>';
      $('#run-picker-count').textContent = '';
      return;
    }
    tb.innerHTML = S.runs.map(function (r) {
      var on = S.selectedIds[r.run_id] ? ' checked' : '';
      return '<tr data-id="' + esc(r.run_id) + '">' +
        '<td><input type="checkbox" class="run-ck" data-id="' + esc(r.run_id) + '"' + on + '></td>' +
        '<td class="mono">' + esc(r.run_id) + '</td>' +
        '<td>' + esc(r.label || '—') + '</td>' +
        '<td>' + esc(r.algorithm) + ' v' + esc(r.algorithm_version) + '</td>' +
        '<td class="mono">' + esc(paramsStr(r.params)) + '</td>' +
        '<td class="num">' + esc((r.stats && r.stats.tong_su_kien) != null ? r.stats.tong_su_kien : '—') + '</td>' +
        '<td class="mono">' + esc((r.range_start || '').slice(0, 16)) + ' → ' + esc((r.range_end || '').slice(0, 16)) + '</td>' +
        '<td class="mono">' + esc((r.created_at || '').replace('T', ' ').slice(0, 19)) + '</td></tr>';
    }).join('');
    $('#run-picker-count').textContent = checkedRunIds().length + ' / ' + S.runs.length + ' đã chọn';
    fillBaselineSelect();
  }

  function fillBaselineSelect() {
    var ids = checkedRunIds();
    var sel = $('#baseline-select');
    var cur = sel.value || S.baselineId;
    sel.innerHTML = '<option value="">— run đầu tiên trong nhóm —</option>' + ids.map(function (id) {
      var r = S.runs.filter(function (x) { return x.run_id === id; })[0];
      var lab = r ? ((r.label || r.algorithm) + ' · ' + id) : id;
      return '<option value="' + esc(id) + '">' + esc(lab) + '</option>';
    }).join('');
    if (cur && ids.indexOf(cur) >= 0) sel.value = cur;
  }

  async function evaluate() {
    showError('');
    var ids = checkedRunIds();
    if (!ids.length) { showError('Chọn ít nhất một lần chạy.'); return; }
    $('#btn-evaluate').disabled = true;
    try {
      var out = await API.createEvaluation({
        run_ids: ids,
        protocol: protocolFromForm(),
        label_set_id: $('#label-set-select').value || null,
        baseline_run_id: $('#baseline-select').value || null,
        save: true,
        note_vi: ''
      });
      await showResult(out);
      location.hash = out.evaluation_id || '';
      await loadSaved();
    } catch (e) {
      showError(e.message);
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
    renderScatter();
    renderHist();
    await renderDetail();
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
      '<span>Đánh giá ' + fmtNum(r.duration_ms, 1) + ' ms</span>' +
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
      $('#m-precision').textContent = fmtNum(q.precision, 3);
      $('#m-recall').textContent = fmtNum(q.recall, 3);
      $('#m-f1').textContent = fmtNum(q.f1, 3);
      $('#m-precision-sub').textContent = 'TP ' + q.true_positives + ' / FP ' + q.false_positives;
      $('#m-recall-sub').textContent = 'TP ' + q.true_positives + ' / FN ' + q.false_negatives;
      $('#m-f1-sub').textContent = 'Nhãn ' + q.n_labels + ' · sự kiện ' + q.n_events_scored;
      $('#m-precision-delta').innerHTML = fmtDelta(d.precision, 3, false);
      $('#m-recall-delta').innerHTML = fmtDelta(d.recall, 3, false);
      $('#m-f1-delta').innerHTML = fmtDelta(d.f1, 3, false);
    }
    $('#m-lag').className = 'metric-v';
    $('#m-lag').textContent = lag.p90 == null ? '—' : fmtNum(lag.p90, 1);
    var tf = run.timeframe || (S.result.dataset && S.result.dataset.timeframe) || '';
    $('#m-lag-sub').textContent = 'Median ' + fmtNum(lag.median, 1) + ' nến' +
      (tf ? ' ' + tf : '') + ' · n=' + (lag.n || 0) +
      (lag.n_tp ? ' · TP median ' + fmtNum(lag.median_tp, 1) : '');
    $('#m-lag-delta').innerHTML = fmtDelta(d.lag_p90, 1, true);
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
          var f1 = q.has_labels ? fmtNum(q.f1, 3) : 'Chưa có nhãn';
          var p = q.has_labels ? fmtNum(q.precision, 3) : '—';
          var rec = q.has_labels ? fmtNum(q.recall, 3) : '—';
          html += '<tr class="' + sel + base + '" data-id="' + esc(r.run_id) + '" tabindex="0">' +
            '<td>' + (r.is_baseline ? '<span class="baseline-mark" title="Baseline">◆</span>' : '') + '</td>' +
            '<td class="mono">' + esc(r.run_id) + (r.label ? '<div class="muted">' + esc(r.label) + '</div>' : '') + '</td>' +
            '<td>' + esc(r.timeframe || '—') + '</td>' +
            '<td>' + esc(r.algorithm) + ' v' + esc(r.algorithm_version) + '</td>' +
            '<td class="mono">' + esc(paramsStr(r.params)) + '</td>' +
            '<td class="num">' + esc(f1) + '</td>' +
            '<td class="num">' + esc(p) + '</td>' +
            '<td class="num">' + esc(rec) + '</td>' +
            '<td class="num">' + esc(fmtNum(lag.p90, 1)) + '</td>' +
            '<td class="num">' + esc(fmtNum(lag.median, 1)) + '</td>' +
            '<td class="num">' + esc(fmtNum(atr.median_atr_ratio, 3)) + '</td>' +
            '<td class="num">' + esc(fmtNum(den.per_100, 2)) + '</td>' +
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

  function axisNice(min, max) {
    if (min === max) { min -= 1; max += 1; }
    var pad = (max - min) * 0.08;
    return { min: min - pad, max: max + pad };
  }

  function renderScatter() {
    $('#chart-pair').hidden = false;
    var host = $('#scatter');
    var runs = selectedGroupRuns().filter(function (r) {
      return r.quality && r.quality.has_labels && r.quality.f1 != null && r.lag && r.lag.p90 != null;
    });
    if (!runs.length) {
      host.innerHTML = '<p class="hint" style="padding:24px">Cần nhãn tham chiếu trong khoảng chấm để vẽ F1. Không gán F1 = 0. Phân phối độ trễ vẫn xem được.</p>';
      return;
    }
    var xs = runs.map(function (r) { return r.lag.p90; });
    var ys = runs.map(function (r) { return r.quality.f1; });
    var xr = axisNice(Math.min.apply(null, xs), Math.max.apply(null, xs));
    var yr = axisNice(0, Math.max(1, Math.max.apply(null, ys)));
    var W = 480, H = 220, L = 42, R = 12, T = 12, B = 28;
    var iw = W - L - R, ih = H - T - B;
    function sx(v) { return L + (v - xr.min) / (xr.max - xr.min) * iw; }
    function sy(v) { return T + (1 - (v - yr.min) / (yr.max - yr.min)) * ih; }
    var pts = runs.map(function (r, i) {
      var sel = r.run_id === S.selectedRunId;
      var cls = 'scatter-pt' + (sel ? ' selected' : '') + (r.is_baseline ? ' baseline' : '');
      var shape;
      if (r.is_baseline) {
        shape = '<rect x="' + (sx(r.lag.p90) - 5) + '" y="' + (sy(r.quality.f1) - 5) +
          '" width="10" height="10" transform="rotate(45 ' + sx(r.lag.p90) + ' ' + sy(r.quality.f1) +
          ')" fill="#ffca6b" class="' + cls + '" data-id="' + esc(r.run_id) + '" tabindex="0" role="option"/>';
      } else {
        shape = '<circle cx="' + sx(r.lag.p90) + '" cy="' + sy(r.quality.f1) + '" r="' + (sel ? 6 : 4.5) +
          '" fill="' + (sel ? '#4c9aff' : '#9aa7b4') + '" class="' + cls + '" data-id="' +
          esc(r.run_id) + '" tabindex="0" role="option"/>';
      }
      return shape;
    }).join('');
    var tf = (runs[0] && runs[0].timeframe) || '';
    host.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img">' +
      '<text x="' + (L + iw / 2) + '" y="' + (H - 4) + '" fill="#6e7d8c" font-size="11" text-anchor="middle">Trễ P90 (nến' +
        (tf ? ' ' + tf : '') + ')</text>' +
      '<text x="12" y="' + (T + ih / 2) + '" fill="#6e7d8c" font-size="11" transform="rotate(-90 12 ' + (T + ih / 2) + ')" text-anchor="middle">F1</text>' +
      '<line x1="' + L + '" y1="' + (T + ih) + '" x2="' + (L + iw) + '" y2="' + (T + ih) + '" stroke="#2a3441"/>' +
      '<line x1="' + L + '" y1="' + T + '" x2="' + L + '" y2="' + (T + ih) + '" stroke="#2a3441"/>' +
      '<text x="' + L + '" y="' + (H - 14) + '" fill="#6e7d8c" font-size="10">' + fmtNum(xr.min, 1) + '</text>' +
      '<text x="' + (L + iw) + '" y="' + (H - 14) + '" fill="#6e7d8c" font-size="10" text-anchor="end">' + fmtNum(xr.max, 1) + '</text>' +
      '<text x="' + (L - 4) + '" y="' + (T + 8) + '" fill="#6e7d8c" font-size="10" text-anchor="end">' + fmtNum(yr.max, 2) + '</text>' +
      '<text x="' + (L - 4) + '" y="' + (T + ih) + '" fill="#6e7d8c" font-size="10" text-anchor="end">' + fmtNum(yr.min, 2) + '</text>' +
      pts + '</svg>';
  }

  function renderHist() {
    var host = $('#lag-hist');
    var runs = selectedGroupRuns();
    if (!runs.length) { host.innerHTML = ''; return; }
    var sel = selectedRun();
    var bins = (sel && sel.lag && sel.lag.histogram) || [];
    if (!bins.length) {
      host.innerHTML = '<p class="hint" style="padding:24px">Chưa có sự kiện để vẽ phân phối độ trễ.</p>';
      return;
    }
    var W = 480, H = 220, L = 36, R = 12, T = 10, B = 36;
    var iw = W - L - R, ih = H - T - B;
    var nBin = bins.length;
    var bw = iw / nBin;
    var others = runs.filter(function (r) { return r.run_id !== (sel && sel.run_id); });
    function countAt(run, i) {
      var h = run.lag && run.lag.histogram;
      return h && h[i] ? h[i].count : 0;
    }
    var maxC = 1;
    bins.forEach(function (b, i) {
      maxC = Math.max(maxC, b.count);
      others.forEach(function (r) { maxC = Math.max(maxC, countAt(r, i)); });
    });
    var bars = '';
    bins.forEach(function (b, i) {
      var x = L + i * bw;
      others.forEach(function (r) {
        var c = countAt(r, i);
        var h = c / maxC * ih;
        var dash = r.is_baseline ? ' stroke-dasharray="3 2"' : '';
        bars += '<rect x="' + (x + 2) + '" y="' + (T + ih - h) + '" width="' + Math.max(1, bw - 6) +
          '" height="' + h + '" fill="rgba(154,167,180,.22)" stroke="' +
          (r.is_baseline ? '#ffca6b' : 'transparent') + '"' + dash + '/>';
      });
      var h2 = b.count / maxC * ih;
      bars += '<rect x="' + (x + 4) + '" y="' + (T + ih - h2) + '" width="' + Math.max(1, bw - 10) +
        '" height="' + h2 + '" fill="#4c9aff"/>';
      var lab = b.to === null ? '≥' + b.from : (b.from === b.to ? String(b.from) : b.from + '–' + b.to);
      bars += '<text x="' + (x + bw / 2) + '" y="' + (H - 8) + '" fill="#6e7d8c" font-size="9" text-anchor="middle">' + lab + '</text>';
    });
    host.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '">' +
      '<line x1="' + L + '" y1="' + (T + ih) + '" x2="' + (L + iw) + '" y2="' + (T + ih) + '" stroke="#2a3441"/>' +
      bars + '</svg>';
  }

  async function renderDetail() {
    var run = selectedRun();
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
      '<dt>Tham số</dt><dd class="mono">' + esc(paramsStr(run.params)) + '</dd>' +
      '<dt>Ánh xạ loại</dt><dd class="mono">' + esc(paramsStr(run.event_type_map)) + '</dd>' +
      '<dt>High F1</dt><dd class="mono">' + (side.high && q.has_labels ? fmtNum(side.high.f1, 3) + ' (TP ' + side.high.true_positives + ')' : '—') + '</dd>' +
      '<dt>Low F1</dt><dd class="mono">' + (side.low && q.has_labels ? fmtNum(side.low.f1, 3) + ' (TP ' + side.low.true_positives + ')' : '—') + '</dd>' +
      '<dt>Khoảng giá lúc xác nhận</dt><dd>median ' + fmtNum(atr.median_distance, 4) + ' · P90 ' + fmtNum(atr.p90_distance, 4) +
        ' · /ATR median ' + fmtNum(atr.median_atr_ratio, 3) + ' (n=' + (atr.n || 0) + ', loại ATR ' + (atr.n_atr_invalid || 0) + ')</dd>' +
      '<dt>Mật độ</dt><dd>' + fmtNum(den.per_100, 2) + ' swing / 100 nến · khoảng cách median ' + fmtNum(den.median_gap_bars, 1) + ' nến</dd>' +
      '<dt>Bỏ qua</dt><dd>ngoài map ' + ign.unmapped_type + ' · ngoài khoảng chấm ' + ign.outside_coverage +
        ' · đuôi chưa xác nhận ' + ign.unconfirmed_tail + ' · quá max trễ ' + ign.over_max_lag + '</dd>' +
      '<dt>Thời gian</dt><dd>thuật toán ' + fmtNum(perf.algorithm_ms, 1) + ' ms · đánh giá ' + fmtNum(perf.evaluation_ms, 1) + ' ms</dd>' +
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
    var run = selectedRun();
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
        '<td class="num">' + fmtNum(r.price, S.digits) + '</td>' +
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
    S.digits = detectDigits(payload.bars);
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
    var run = selectedRun();
    if (!run || !S.chart) return;
    S.chart.setEvalOverlay({
      matches: run.matches || [],
      false_positives: run.false_positives || [],
      false_negatives: run.false_negatives || [],
      labels: S.labels,
      selected: S.selectedEvent
    });
  }

  async function selectRun(id) {
    if (!id) return;
    S.selectedRunId = id;
    S.selectedEvent = null;
    renderMeta();
    renderCards();
    renderTable();
    renderScatter();
    renderHist();
    await renderDetail();
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

  async function loadSaved() {
    var ds = $('#dataset-select').value;
    try {
      S.saved = await API.evaluations(ds || null);
    } catch (e) { S.saved = []; }
    var tb = $('#saved-table tbody');
    if (!S.saved.length) {
      tb.innerHTML = '<tr><td colspan="7" class="empty-cell">Chưa có đánh giá đã lưu.</td></tr>';
      return;
    }
    tb.innerHTML = S.saved.map(function (e) {
      return '<tr data-id="' + esc(e.id) + '">' +
        '<td class="mono">' + esc(e.id) + '</td>' +
        '<td class="mono">' + esc((e.created_at || '').replace('T', ' ').slice(0, 19)) + '</td>' +
        '<td class="mono">' + esc(e.dataset_id) + '</td>' +
        '<td class="mono">' + esc(e.protocol_hash) + '</td>' +
        '<td class="mono">' + esc(e.baseline_run_id || '—') + '</td>' +
        '<td class="num">' + (e.run_ids ? e.run_ids.length : '—') + '</td>' +
        '<td><button class="btn btn-sm btn-secondary btn-open-ev" type="button" data-id="' + esc(e.id) + '">Mở</button></td></tr>';
    }).join('');
  }

  async function openSaved(id) {
    var row = await API.getEvaluation(id);
    var result = row.result || row;
    if (row.dataset_id) $('#dataset-select').value = row.dataset_id;
    await onDatasetChange();
    (row.run_ids || []).forEach(function (rid) { S.selectedIds[rid] = true; });
    renderRunPicker();
    $('#label-set-select').value = row.label_set_id || '';
    $('#baseline-select').value = row.baseline_run_id || '';
    applyProtocol(row.protocol || result.protocol);
    result.evaluation_id = row.id;
    await showResult(result);
    location.hash = row.id;
  }

  function bind() {
    $('#dataset-select').addEventListener('change', function () { onDatasetChange().catch(function (e) { showError(e.message); }); });
    $('#target-select').addEventListener('change', updateTargetHelp);
    $('#chk-map-l1').addEventListener('change', updateTargetHelp);
    $('#chk-map-dc').addEventListener('change', updateTargetHelp);
    $('#btn-evaluate').addEventListener('click', function () { evaluate(); });
    $('#btn-export').addEventListener('click', function () {
      if (!S.result || !S.result.evaluation_id) return;
      window.location.href = API.evaluationReportUrl(S.result.evaluation_id);
    });
    $('#run-picker-table').addEventListener('change', function (ev) {
      var t = ev.target;
      if (!t.classList.contains('run-ck')) return;
      S.selectedIds[t.getAttribute('data-id')] = t.checked;
      $('#run-picker-count').textContent = checkedRunIds().length + ' / ' + S.runs.length + ' đã chọn';
      fillBaselineSelect();
    });
    $('#compare-table').addEventListener('click', function (ev) {
      var tr = ev.target.closest('tr[data-id]');
      if (tr) selectRun(tr.getAttribute('data-id'));
    });
    $('#compare-table').addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
      ev.preventDefault();
      var ids = scoredRuns().map(function (r) { return r.run_id; });
      var i = ids.indexOf(S.selectedRunId);
      if (ev.key === 'ArrowDown') i = Math.min(ids.length - 1, i + 1);
      else i = Math.max(0, i - 1);
      if (ids[i]) selectRun(ids[i]);
    });
    $('#scatter').addEventListener('click', function (ev) {
      var pt = ev.target.closest('[data-id]');
      if (pt) selectRun(pt.getAttribute('data-id'));
    });
    $('#scatter').addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
      ev.preventDefault();
      var ids = scoredRuns().map(function (r) { return r.run_id; });
      var i = ids.indexOf(S.selectedRunId);
      if (ev.key === 'ArrowRight') i = Math.min(ids.length - 1, i + 1);
      else i = Math.max(0, i - 1);
      if (ids[i]) selectRun(ids[i]);
    });
    $$('#detail-tabs .tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('#detail-tabs .tab').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        $$('.dtab-panel').forEach(function (p) {
          p.classList.toggle('active', p.getAttribute('data-dpanel') === btn.getAttribute('data-dtab'));
        });
      });
    });
    $('#evt-table').addEventListener('click', function (ev) {
      var tr = ev.target.closest('tr[data-role]');
      if (!tr) return;
      jumpToEvent({
        role: tr.getAttribute('data-role'),
        bar: tr.getAttribute('data-bar'),
        event_id: tr.getAttribute('data-eid'),
        label_seq: tr.getAttribute('data-seq')
      });
    });
    ['flt-tp', 'flt-fp', 'flt-fn', 'evt-search'].forEach(function (id) {
      $('#' + id).addEventListener('input', renderEventTable);
      $('#' + id).addEventListener('change', renderEventTable);
    });
    $('#saved-table').addEventListener('click', function (ev) {
      var btn = ev.target.closest('.btn-open-ev');
      var tr = ev.target.closest('tr[data-id]');
      var id = (btn && btn.getAttribute('data-id')) || (tr && tr.getAttribute('data-id'));
      if (id) openSaved(id).catch(function (e) { showError(e.message); });
    });
  }

  boot().catch(function (e) { showError(e.message || String(e)); });
})();
