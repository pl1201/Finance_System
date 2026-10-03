/* Trang Gán nhãn — khởi động, gắn sự kiện DOM và phím tắt. */
(function (MSL) {
  'use strict';

  var G = MSL.label;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var S = G.S;

  function bind() {
    G.bindAuto();
    $('#dataset-select').addEventListener('change', function () {
      if (!G.confirmLeaveDraft()) {
        $('#dataset-select').value = S.dataset ? S.dataset.id : '';
        return;
      }
      G.onDatasetChange().catch(function (e) { G.showError(e.message); });
    });
    $('#btn-save').addEventListener('click', function () { G.saveSet(); });
    $('#real-data-hint').addEventListener('click', function (ev) {
      var b = ev.target.closest('#btn-go-real');
      if (!b) return;
      $('#dataset-select').value = b.getAttribute('data-id');
      G.onDatasetChange().catch(function (e) { G.showError(e.message); });
    });
    $('#btn-update').addEventListener('click', function () { G.updateSet(); });
    $('#btn-undo').addEventListener('click', G.undo);
    $('#btn-export-labels').addEventListener('click', G.exportLabels);
    $('#btn-import-labels').addEventListener('click', function () {
      $('#label-import-file').click();
    });
    $('#label-import-file').addEventListener('change', function (ev) {
      var f = ev.target.files[0];
      if (f) G.importLabels(f);
      ev.target.value = '';
    });
    ['#label-annotator', '#label-version', '#label-rubric'].forEach(function (sel) {
      $(sel).addEventListener('change', G.persistDraft);
    });
    window.LabelDraft.guardUnload(function () { return S.dirty && S.draft.length > 0; });
    $('#draft-table').addEventListener('click', function (ev) {
      var del = ev.target.closest('[data-del]');
      if (del) {
        var i = parseInt(del.getAttribute('data-del'), 10);
        G.pushUndo();
        S.draft.splice(i, 1);
        S.dirty = true;
        S.selected = null;
        G.renderDraft();
        return;
      }
      var mv = ev.target.closest('[data-mv]');
      if (mv) {
        var mi = parseInt(mv.getAttribute('data-i'), 10);
        var lbm = S.draft[mi];
        if (lbm && G.editLabel(mi, { bar_index: lbm.bar_index + parseInt(mv.getAttribute('data-mv'), 10) })) {
          G.renderDraft();
          S.chart.centerOnIndex(S.selected.bar_index);
        }
        return;
      }
      var tr = ev.target.closest('tr[data-i]');
      if (!tr) return;
      if (ev.target.closest('input, select')) {
        // Không vẽ lại bảng khi bấm vào ô nhập — vẽ lại sẽ làm mất con trỏ / đóng menu.
        var r0 = S.draft[parseInt(tr.getAttribute('data-i'), 10)];
        if (r0) {
          S.selected = { bar_index: r0.bar_index, structure_type: r0.structure_type };
          $$('#draft-table tbody tr').forEach(function (x) { x.classList.toggle('selected', x === tr); });
          G.paint();
        }
        return;
      }
      var row = S.draft[parseInt(tr.getAttribute('data-i'), 10)];
      if (!row) return;
      S.selected = { bar_index: row.bar_index, structure_type: row.structure_type };
      G.renderDraft();
      S.chart.scrollToIndex(row.bar_index);
    });
    $('#draft-table').addEventListener('change', function (ev) {
      var inp = ev.target.closest('.note-in');
      if (!inp) return;
      var i = parseInt(inp.getAttribute('data-i'), 10);
      if (!S.draft[i]) return;
      G.pushUndo();
      S.draft[i].notes = inp.value;
      S.dirty = true;
      G.persistDraft();
    });
    $('#draft-table').addEventListener('change', function (ev) {
      var ty = ev.target.closest('.type-in');
      var pr = ev.target.closest('.price-in');
      if (!ty && !pr) return;
      var el = ty || pr;
      var i = parseInt(el.getAttribute('data-i'), 10);
      var ok = ty ? G.editLabel(i, { structure_type: ty.value })
                  : G.editLabel(i, { price: parseFloat(pr.value) });
      G.renderDraft();   // vẽ lại cả khi thất bại để trả ô về giá trị cũ
      if (ok) G.showOk('Đã sửa nhãn. Hoàn tác được bằng Ctrl+Z.');
    });
    $('#saved-sets').addEventListener('click', function (ev) {
      var btn = ev.target.closest('.btn-load-set');
      if (btn) G.loadSet(btn.getAttribute('data-id'));
    });
    document.addEventListener('keydown', function (ev) {
      var k = ev.key;
      if (k === 'Escape' && S.pop) { ev.preventDefault(); G.closePop(); return; }
      if (G.isTypingTarget(ev.target)) return;
      // A/X/N/P chuyển sang đề xuất khác và cuộn chart -> đóng bảng thao tác trước.
      if (S.pop && S.auto && !ev.ctrlKey && !ev.metaKey && !ev.altKey && /^[axnpAXNP]$/.test(k)) G.closePop();
      if (k === 'Backspace' || (k === 'z' && (ev.ctrlKey || ev.metaKey))) {
        ev.preventDefault();
        G.undo();
        return;
      }
      // Duyệt đề xuất auto label.
      if (S.auto && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        if (k === 'a' || k === 'A') { ev.preventDefault(); G.acceptCurrent(); return; }
        if (k === 'x' || k === 'X') { ev.preventDefault(); G.rejectCurrent(); return; }
        if (k === 'n' || k === 'N') {
          ev.preventDefault();
          var nx = G.nextPending(S.auto.cursor, 1);
          if (nx >= 0) G.focusAuto(nx);
          return;
        }
        if (k === 'p' || k === 'P') {
          ev.preventDefault();
          G.focusAuto(S.auto.cursor > 0 ? S.auto.cursor - 1 : S.auto.items.length - 1);
          return;
        }
      }
      // Nhãn đang chọn: [ ] dời 1 nến, Delete xoá.
      var si = G.selectedDraftIndex();
      if (si >= 0 && (k === '[' || k === ']')) {
        ev.preventDefault();
        if (G.editLabel(si, { bar_index: S.draft[si].bar_index + (k === ']' ? 1 : -1) })) {
          G.renderDraft();
          S.chart.centerOnIndex(S.selected.bar_index);
        }
        return;
      }
      if (si >= 0 && k === 'Delete') {
        ev.preventDefault();
        G.pushUndo();
        S.draft.splice(si, 1);
        S.dirty = true;
        S.selected = null;
        G.renderDraft();
        return;
      }
      if (k === '1') { S.currentType = 'SWING_HIGH'; $('input[name="label-type"][value="SWING_HIGH"]').checked = true; }
      if (k === '2') { S.currentType = 'SWING_HIGH_L2'; $('input[name="label-type"][value="SWING_HIGH_L2"]').checked = true; }
      if (k === 'h' || k === 'H') {
        S.currentType = S.currentType.indexOf('L2') >= 0 ? 'SWING_HIGH_L2' : 'SWING_HIGH';
        $('input[name="label-type"][value="' + S.currentType + '"]').checked = true;
      }
      if (k === 'l' || k === 'L') {
        S.currentType = S.currentType.indexOf('L2') >= 0 ? 'SWING_LOW_L2' : 'SWING_LOW';
        $('input[name="label-type"][value="' + S.currentType + '"]').checked = true;
      }
    });
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
    S.chart = new MarketChart($('#label-chart'), $('#label-tooltip'));
    S.chart.setBarClickHandler(function (bar, info) { G.onChartClick(bar, info || {}); });
    G.renderTypes();
    bind();
    G.bindPop();
    try {
      S.autoAlgos = await API.autoLabelAlgorithms();
    } catch (e) {
      S.autoAlgos = [];
    }
    G.renderAutoAlgos();
    S.datasets = await API.datasets();
    G.renderDatasets();
    var q = new URLSearchParams(location.search);
    // Ưu tiên dataset trên URL; nếu không có thì quay về dataset đang làm dở,
    // để bộ nháp đã lưu trong trình duyệt hiện ra đúng chỗ.
    var ds = q.get('dataset_id') || window.LabelDraft.lastDataset();
    var known = ds && S.datasets.some(function (d) { return d.id === ds; });
    if (known) {
      $('#dataset-select').value = ds;
      await G.onDatasetChange();
    } else {
      G.renderTfSwitch();
    }
  }

  boot().catch(function (e) { G.showError(e.message || String(e)); });
})(window.MSL);
