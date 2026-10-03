/* Trang Đánh giá — đánh giá đã lưu: danh sách, mở lại đúng protocol. */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = E.S;

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
    await E.onDatasetChange();
    (row.run_ids || []).forEach(function (rid) { S.selectedIds[rid] = true; });
    E.renderRunPicker();
    $('#label-set-select').value = row.label_set_id || '';
    $('#baseline-select').value = row.baseline_run_id || '';
    E.applyProtocol(row.protocol || result.protocol);
    result.evaluation_id = row.id;
    await E.showResult(result);
    location.hash = row.id;
  }

  E.loadSaved = loadSaved;
  E.openSaved = openSaved;
})(window.MSL);
