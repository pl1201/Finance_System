/* Trang Thử nghiệm — tab Nhãn tham chiếu (bản rút gọn): nháp theo dataset, lưu/ghi đè, CSV, đối chiếu. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;
  var S = L.S;

  //
  // Bộ nháp được tự lưu vào bộ nhớ trình duyệt theo TỪNG dataset, nên tải lại
  // trang hay đổi dataset đều không mất công gán. Nháp KHÔNG phải nơi lưu chính
  // thức — chỉ bấm Lưu / Cập nhật mới ghi vào kho nhãn (SQLite).

  function draftIsDirty() {
    return !!(S.labelDirty && S.draftLabels.length);
  }

  function persistDraft() {
    if (!S.dataset) return;
    S.labelDraftSaved = window.LabelDraft.write(S.dataset.id, {
      labels: S.draftLabels,
      annotator: $('#label-annotator').value,
      version: $('#label-version').value,
      rubric_vi: $('#label-rubric').value,
      label_set_id: S.labelSetId,
      dirty: S.labelDirty
    });
    renderDraftStatus();
  }

  function loadDraftForDataset() {
    S.draftLabels = [];
    S.labelSetId = null;
    S.labelDirty = false;
    var d = S.dataset ? window.LabelDraft.read(S.dataset.id) : null;
    if (d) {
      S.draftLabels = d.labels || [];
      S.labelSetId = d.label_set_id || null;
      S.labelDirty = !!d.dirty;
      if (d.annotator) $('#label-annotator').value = d.annotator;
      if (d.version) $('#label-version').value = d.version;
      $('#label-rubric').value = d.rubric_vi || '';
    } else if (!$('#label-annotator').value) {
      $('#label-annotator').value = window.LabelDraft.lastAnnotator();
    }
    renderDraftLabels();
  }

  function renderDraftStatus() {
    var el = $('#label-draft-status');
    if (!el) return;
    $('#btn-update-labels').disabled = !S.labelSetId || !S.draftLabels.length;
    $('#btn-export-labels').disabled = !S.labelSetId;

    if (!S.dataset) { el.className = 'note note-info'; el.textContent = 'Chọn dataset trước khi gán nhãn.'; return; }
    var scope = S.dataset.symbol + ' ' + S.dataset.timeframe;
    if (!S.draftLabels.length) {
      el.className = 'note note-info';
      el.textContent = 'Chưa có nhãn nào trong bộ nháp (' + scope + ').';
      return;
    }
    var where = window.LabelDraft.available
      ? (S.labelDraftSaved === false
          ? ' Không ghi được nháp vào trình duyệt — đừng tải lại trang trước khi Lưu.'
          : ' Nháp được giữ trong trình duyệt, tải lại trang vẫn còn.')
      : ' Trình duyệt không cho lưu nháp — đừng tải lại trang trước khi Lưu.';

    if (S.labelDirty) {
      el.className = 'note note-warn';
      el.innerHTML = '<strong>' + S.draftLabels.length + ' nhãn CHƯA LƯU</strong> trên ' + esc(scope) +
        '.' + esc(where) + ' Bấm <strong>Lưu thành bộ mới</strong> để ghi vào kho nhãn.';
    } else {
      el.className = 'note note-ok';
      el.innerHTML = S.draftLabels.length + ' nhãn trên ' + esc(scope) + ' — đã lưu ở bộ <code>' +
        esc(S.labelSetId || '?') + '</code>.';
    }
  }

  function renderDraftLabels() {
    var tb = $('#labels-table tbody');
    if (!S.draftLabels.length) {
      tb.innerHTML = '<tr><td colspan="6" class="empty-cell">Chưa có nhãn.</td></tr>';
    } else {
      tb.innerHTML = S.draftLabels.map(function (lb, i) {
        return '<tr><td>' + i + '</td><td><span class="badge b-' + esc(lb.structure_type) + '">' +
          esc(lb.structure_type) + '</span></td><td class="num">' + lb.bar_index +
          '</td><td class="num">' + lb.price + '</td><td>' + esc(lb.notes || '') +
          '</td><td><button type="button" class="btn btn-link btn-sm" data-del-label="' + i + '">xoá</button></td></tr>';
      }).join('');
      $$('#labels-table [data-del-label]').forEach(function (b) {
        b.addEventListener('click', function () {
          S.draftLabels.splice(parseInt(b.getAttribute('data-del-label'), 10), 1);
          S.labelDirty = true;
          renderDraftLabels();
          persistDraft();
        });
      });
    }
    renderDraftStatus();
  }

  function labelPayload() {
    return {
      annotator: $('#label-annotator').value,
      version: $('#label-version').value,
      rubric_vi: $('#label-rubric').value,
      labels: S.draftLabels
    };
  }

  function afterLabelWrite(ls, what) {
    S.labelSetId = ls.id;
    S.labelDirty = false;
    window.LabelDraft.setLastAnnotator(ls.annotator || '');
    persistDraft();
    var warn = (ls.warnings || []).length
      ? ' Lưu ý: ' + ls.warnings.map(esc).join(' ')
      : '';
    L.banner('ok', what + ' <code>' + esc(ls.id) + '</code> (bản ' + (ls.revision || 1) + ') — ' +
      (ls.labels ? ls.labels.length : S.draftLabels.length) + ' nhãn, người gán: ' +
      esc(ls.annotator) + '.' + warn +
      (ls.ghi_chu_vi ? ' ' + esc(ls.ghi_chu_vi) : ''));
  }

  async function saveLabels() {
    if (!S.dataset) { L.banner('error', 'Chọn dataset.'); return; }
    if (!S.draftLabels.length) { L.banner('error', 'Chưa có nhãn nào để lưu.'); return; }
    $('#btn-save-labels').disabled = true;
    try {
      var ls = await API.saveLabelSet(Object.assign(
        { dataset_id: S.dataset.id }, labelPayload()));
      afterLabelWrite(ls, 'Đã lưu bộ nhãn mới');
      await refreshLabelSetPicker(ls.id);
    } catch (e) {
      L.banner('error', esc(e.message));
    } finally {
      $('#btn-save-labels').disabled = false;
    }
  }

  async function updateLabels() {
    if (!S.labelSetId) { L.banner('error', 'Chưa mở bộ nhãn nào để cập nhật. Dùng "Lưu thành bộ mới".'); return; }
    if (!S.draftLabels.length) { L.banner('error', 'Bộ nháp rỗng — không ghi đè bằng bộ rỗng.'); return; }
    $('#btn-update-labels').disabled = true;
    try {
      var ls;
      try {
        ls = await API.updateLabelSet(S.labelSetId, labelPayload());
      } catch (e) {
        // Backend chặn khi bộ nhãn đã được dùng trong đánh giá đã lưu.
        if (e.message.indexOf('đánh giá đã lưu') === -1) throw e;
        if (!window.confirm(e.message + '\n\nVẫn ghi đè?')) {
          L.banner('warn', 'Đã huỷ ghi đè. Bộ nhãn giữ nguyên.');
          return;
        }
        ls = await API.updateLabelSet(S.labelSetId,
          Object.assign(labelPayload(), { confirm_overwrite: true }));
      }
      afterLabelWrite(ls, 'Đã ghi đè bộ nhãn');
      await refreshLabelSetPicker(ls.id);
    } catch (e) {
      L.banner('error', esc(e.message));
    } finally {
      renderDraftStatus();
    }
  }

  async function refreshLabelSetPicker(selectId) {
    var sel = $('#label-set-pick');
    if (!sel) return;
    if (!S.dataset) { sel.innerHTML = '<option value="">— chọn dataset —</option>'; return; }
    try {
      S.labelSets = await API.labelSets(S.dataset.id);
    } catch (e) { S.labelSets = []; }
    if (!S.labelSets.length) {
      sel.innerHTML = '<option value="">— dataset này chưa có bộ nhãn —</option>';
    } else {
      sel.innerHTML = S.labelSets.map(function (s) {
        return '<option value="' + esc(s.id) + '">' + esc(s.id) + ' · ' + esc(s.annotator) +
          ' · v' + esc(s.version) + ' · bản ' + (s.revision || 1) + ' · ' +
          (s.n_labels != null ? s.n_labels : '?') + ' nhãn</option>';
      }).join('');
      sel.value = selectId || S.labelSetId || S.labelSets[0].id;
    }
    renderDraftStatus();
  }

  async function loadLabelSets() {
    if (!S.dataset) { L.banner('error', 'Chọn dataset.'); return; }
    var id = $('#label-set-pick').value;
    if (!id) { L.banner('warn', 'Dataset này chưa có bộ nhãn nào để tải.'); return; }
    if (draftIsDirty() &&
        !window.confirm('Bộ nháp có ' + S.draftLabels.length +
                        ' nhãn chưa lưu. Tải bộ đã lưu sẽ thay nháp hiện tại. Tiếp tục?')) {
      return;
    }
    try {
      var ls = await API.getLabelSet(id);
      S.draftLabels = (ls.labels || []).map(function (l) {
        // Giữ nguồn gốc: lưu lại không được biến nhãn auto thành nhãn người gán.
        return {
          structure_type: l.structure_type, bar_index: l.bar_index,
          price: l.price, notes: l.notes || '',
          source: l.source || 'human',
          source_algorithm: l.source_algorithm || '',
          source_detail: l.source_detail || ''
        };
      });
      S.labelSetId = ls.id;
      S.labelDirty = false;
      $('#label-annotator').value = ls.annotator;
      $('#label-version').value = ls.version;
      $('#label-rubric').value = ls.rubric_vi;
      renderDraftLabels();
      persistDraft();
      var used = (ls.used_by_evaluations || []).length;
      L.banner('ok', 'Đã tải bộ <code>' + esc(ls.id) + '</code> (bản ' + (ls.revision || 1) + ') của ' +
        esc(ls.annotator) + ' — ' + S.draftLabels.length + ' nhãn.' +
        (used ? ' Bộ này đã được dùng trong ' + used + ' đánh giá đã lưu; ghi đè sẽ phải xác nhận.' : ''));
    } catch (e) { L.banner('error', esc(e.message)); }
  }

  function exportLabels() {
    if (!S.labelSetId) { L.banner('error', 'Lưu hoặc tải một bộ nhãn trước khi xuất.'); return; }
    if (draftIsDirty()) {
      L.banner('warn', 'Nháp đang có thay đổi chưa lưu — file xuất ra là nội dung ĐÃ LƯU của bộ ' +
        esc(S.labelSetId) + ', không phải nháp hiện tại.');
    }
    window.location.href = API.labelSetExportUrl(S.labelSetId);
  }

  async function importLabelsCsv(file) {
    if (!S.dataset) { L.banner('error', 'Chọn dataset trước khi nhập nhãn.'); return; }
    if (draftIsDirty() &&
        !window.confirm('Bộ nháp có ' + S.draftLabels.length +
                        ' nhãn chưa lưu. Nhập CSV sẽ thay nháp hiện tại. Tiếp tục?')) {
      return;
    }
    try {
      var text = await file.text();
      var out = await API.parseLabelCsv({ dataset_id: S.dataset.id, csv_text: text });
      S.draftLabels = out.labels || [];
      S.labelSetId = null;      // nhãn từ file chưa thuộc bộ đã lưu nào
      S.labelDirty = true;
      renderDraftLabels();
      persistDraft();
      var w = (out.warnings || []).length ? ' Cảnh báo: ' + out.warnings.map(esc).join(' ') : '';
      L.banner(out.warnings && out.warnings.length ? 'warn' : 'ok',
        esc(out.ghi_chu_vi) + w);
    } catch (e) {
      L.banner('error', 'Không nhập được CSV: ' + esc(e.message));
    }
  }

  async function evalLabels() {
    if (!S.run || !S.run.run_id) { L.banner('error', 'Chạy thử trước.'); return; }
    if (!S.labelSetId) { L.banner('error', 'Lưu hoặc tải bộ nhãn trước.'); return; }
    try {
      var ev = await API.evaluate({
        run_id: S.run.run_id,
        label_set_id: S.labelSetId,
        time_tolerance_bars: parseInt($('#label-time-tol').value, 10) || 0,
        price_tolerance: parseFloat($('#label-price-tol').value) || 0
      });
      var html = '<p>' + esc(ev.note_vi) + '</p>';
      if (ev.precision === null) html += '<p>Không có precision (bộ nhãn trống hoặc không ghép được mẫu số).</p>';
      else html += '<p>Người gán: <strong>' + esc(ev.annotator) + '</strong> · precision=' +
        ev.precision.toFixed(3) + ' · recall=' + (ev.recall === null ? '—' : ev.recall.toFixed(3)) +
        ' · TP=' + ev.true_positives + ' FP=' + ev.false_positives + ' FN=' + ev.false_negatives + '</p>';
      $('#label-eval').innerHTML = html;
    } catch (e) { L.banner('error', esc(e.message)); }
  }

  L.draftIsDirty = draftIsDirty;
  L.evalLabels = evalLabels;
  L.exportLabels = exportLabels;
  L.importLabelsCsv = importLabelsCsv;
  L.loadDraftForDataset = loadDraftForDataset;
  L.loadLabelSets = loadLabelSets;
  L.persistDraft = persistDraft;
  L.refreshLabelSetPicker = refreshLabelSetPicker;
  L.renderDraftLabels = renderDraftLabels;
  L.renderDraftStatus = renderDraftStatus;
  L.saveLabels = saveLabels;
  L.updateLabels = updateLabels;
})(window.MSL);
