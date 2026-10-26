/* Trang Gán nhãn — lưu bộ mới, tải, ghi đè, xuất / nhập CSV. */
(function (MSL) {
  'use strict';

  var G = MSL.label;
  var $ = MSL.dom.$;
  var S = G.S;

  async function saveSet() {
    G.showError('');
    G.showOk('');
    if (!S.dataset) { G.showError('Chọn dataset.'); return; }
    var annotator = $('#label-annotator').value;
    if (!annotator.trim()) { G.showError('Phải ghi tên người gán nhãn.'); return; }
    if (!S.draft.length) { G.showError('Chưa có nhãn để lưu.'); return; }
    $('#btn-save').disabled = true;
    try {
      var ls = await API.saveLabelSet({
        dataset_id: S.dataset.id,
        annotator: annotator,
        version: $('#label-version').value,
        rubric_vi: $('#label-rubric').value,
        labels: S.draft
      });
      S.savedId = ls.id;
      S.dirty = false;
      window.LabelDraft.setLastAnnotator(ls.annotator || '');
      G.persistDraft();
      G.updateEvalLink();
      await G.loadSavedSets();
      G.renderMeta();
      G.showOk('Đã lưu ' + ls.id + ' · ' + ls.annotator + ' · ' + (ls.labels ? ls.labels.length : S.draft.length) +
        ' nhãn trên ' + S.dataset.symbol + ' ' + S.dataset.timeframe +
        '. Lưu tạo bộ mới, không ghi đè. Mở Đánh giá để chấm F1.');
    } catch (e) {
      G.showError(e.message);
    } finally {
      $('#btn-save').disabled = false;
    }
  }

  async function loadSet(id) {
    if (S.dirty && !window.confirm('Tải bộ đã lưu sẽ thay nháp hiện tại. Tiếp tục?')) return;
    try {
      var ls = await API.getLabelSet(id);
      G.pushUndo();
      S.draft = (ls.labels || []).map(function (l) {
        return {
          structure_type: l.structure_type,
          bar_index: l.bar_index,
          price: l.price,
          notes: l.notes || '',
          source: l.source || 'human',
          source_algorithm: l.source_algorithm || '',
          source_detail: l.source_detail || ''
        };
      });
      S.savedId = ls.id;
      S.dirty = false;
      $('#label-annotator').value = ls.annotator || '';
      $('#label-version').value = ls.version || '1';
      $('#label-rubric').value = ls.rubric_vi || '';
      S.selected = S.draft[0] ? { bar_index: S.draft[0].bar_index, structure_type: S.draft[0].structure_type } : null;
      G.updateEvalLink();
      G.renderDraft();
      if (S.selected) S.chart.scrollToIndex(S.selected.bar_index);
      G.showOk('Đã tải ' + ls.id + ' của ' + ls.annotator + '. Sửa rồi lưu sẽ tạo bộ mới.');
    } catch (e) { G.showError(e.message); }
  }

  async function updateSet() {
    G.showError(''); G.showOk('');
    if (!S.savedId) { G.showError('Chưa mở bộ nhãn nào để cập nhật. Dùng "Lưu thành bộ mới".'); return; }
    if (!S.draft.length) { G.showError('Bộ nháp rỗng — không ghi đè bằng bộ rỗng.'); return; }
    var annotator = $('#label-annotator').value;
    if (!annotator.trim()) { G.showError('Phải ghi tên người gán nhãn.'); return; }
    var payload = {
      annotator: annotator,
      version: $('#label-version').value,
      rubric_vi: $('#label-rubric').value,
      labels: S.draft
    };
    $('#btn-update').disabled = true;
    try {
      var ls;
      try {
        ls = await API.updateLabelSet(S.savedId, payload);
      } catch (e) {
        if (e.message.indexOf('đánh giá đã lưu') === -1) throw e;
        if (!window.confirm(e.message + '\n\nVẫn ghi đè?')) {
          G.showError('Đã huỷ ghi đè. Bộ nhãn giữ nguyên.');
          return;
        }
        payload.confirm_overwrite = true;
        ls = await API.updateLabelSet(S.savedId, payload);
      }
      S.dirty = false;
      window.LabelDraft.setLastAnnotator(ls.annotator || '');
      G.persistDraft();
      await G.loadSavedSets();
      G.renderMeta();
      G.showOk('Đã ghi đè ' + ls.id + ' thành bản ' + (ls.revision || 1) + ' · ' +
        (ls.labels ? ls.labels.length : S.draft.length) + ' nhãn. ' + (ls.ghi_chu_vi || ''));
    } catch (e) {
      G.showError(e.message);
    } finally {
      G.renderMeta();
    }
  }

  function exportLabels() {
    if (!S.savedId) { G.showError('Lưu hoặc tải một bộ nhãn trước khi xuất.'); return; }
    if (S.dirty) {
      G.showOk('Lưu ý: file xuất ra là nội dung ĐÃ LƯU của ' + S.savedId + ', không phải nháp hiện tại.');
    }
    window.location.href = API.labelSetExportUrl(S.savedId);
  }

  async function importLabels(file) {
    G.showError(''); G.showOk('');
    if (!S.dataset) { G.showError('Chọn dataset trước khi nhập nhãn.'); return; }
    if (S.draft.length && !window.confirm('Nhập CSV sẽ thay bộ nháp hiện tại (' +
        S.draft.length + ' nhãn). Tiếp tục?')) return;
    try {
      var text = await file.text();
      var out = await API.parseLabelCsv({ dataset_id: S.dataset.id, csv_text: text });
      G.pushUndo();
      S.draft = out.labels || [];
      S.savedId = '';
      S.dirty = true;
      S.selected = S.draft[0]
        ? { bar_index: S.draft[0].bar_index, structure_type: S.draft[0].structure_type }
        : null;
      G.updateEvalLink();
      G.renderDraft();
      if (S.selected) S.chart.scrollToIndex(S.selected.bar_index);
      if ((out.warnings || []).length) G.showError('Cảnh báo: ' + out.warnings.join(' '));
      else G.showOk(out.ghi_chu_vi);
    } catch (e) {
      G.showError('Không nhập được CSV: ' + e.message);
    }
  }

  G.exportLabels = exportLabels;
  G.importLabels = importLabels;
  G.loadSet = loadSet;
  G.saveSet = saveSet;
  G.updateSet = updateSet;
})(window.MSL);
