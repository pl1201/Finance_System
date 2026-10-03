/* Trang Đánh giá — dataset, đổi khung, bộ nhãn, chọn run và baseline. */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var TF_ORDER = MSL.tf.ORDER;
  var esc = MSL.dom.esc;
  var S = E.S;

  function findSiblingDataset(symbol, tf, current) {
    return MSL.tf.findSibling(S.datasets, symbol, tf, current);
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
      E.showError('Chưa có dataset ' + S.dataset.symbol + ' ' + tf +
        '. Hãy tạo hoặc nhập ở trang Thử nghiệm. Trang đánh giá không tổng hợp hay tách nến.');
      return;
    }
    E.showError('');
    $('#dataset-select').value = sib.id;
    await onDatasetChange();
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
    await E.loadSaved();
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
        '<td class="mono">' + esc(E.paramsStr(r.params)) + '</td>' +
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

  E.checkedRunIds = checkedRunIds;
  E.fillBaselineSelect = fillBaselineSelect;
  E.onDatasetChange = onDatasetChange;
  E.renderDatasets = renderDatasets;
  E.renderRunPicker = renderRunPicker;
})(window.MSL);
