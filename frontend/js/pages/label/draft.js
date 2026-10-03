/* Trang Gán nhãn — bộ nháp: vẽ, bảng, giữ trong trình duyệt, hoàn tác, sửa / dời / gán nhanh. */
(function (MSL) {
  'use strict';

  var G = MSL.label;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = G.S;
  var TYPES = G.TYPES;

  function paint() {
    if (!S.chart) return;
    S.chart.setLabelOverlay({
      labels: S.draft,
      selected: S.selected,
      suggestions: G.autoOverlayItems()
    });
    G.renderPop();
  }

  function renderDraft() {
    var tb = $('#draft-table tbody');
    $('#draft-count').textContent = S.draft.length ? S.draft.length + ' nhãn' : '';
    if (!S.draft.length) {
      tb.innerHTML = '<tr><td colspan="7" class="empty-cell">Chưa có nhãn.</td></tr>';
      paint();
      G.renderMeta();
      G.renderAuto();
      persistDraft();
      return;
    }
    tb.innerHTML = S.draft.map(function (lb, i) {
      var sel = S.selected && S.selected.bar_index === lb.bar_index &&
        S.selected.structure_type === lb.structure_type ? ' selected' : '';
      return '<tr class="' + sel + '" data-i="' + i + '">' +
        '<td class="num">' + i + '</td>' +
        '<td><select class="type-in" data-i="' + i + '">' + TYPES.map(function (t) {
          return '<option value="' + t.id + '"' + (t.id === lb.structure_type ? ' selected' : '') + '>' +
            esc(t.id) + '</option>';
        }).join('') + '</select></td>' +
        '<td class="num bar-cell"><button type="button" class="btn btn-sm mv-btn" data-mv="-1" data-i="' + i +
          '" title="Dời sang nến trước">◀</button> #' + lb.bar_index +
          ' <button type="button" class="btn btn-sm mv-btn" data-mv="1" data-i="' + i +
          '" title="Dời sang nến sau">▶</button></td>' +
        '<td><input type="number" step="any" class="price-in" data-i="' + i + '" value="' +
          esc(lb.price) + '"></td>' +
        '<td>' + sourceCell(lb) + '</td>' +
        '<td><input type="text" class="note-in" data-i="' + i + '" value="' + esc(lb.notes || '') + '" placeholder="tuỳ chọn"></td>' +
        '<td><button type="button" class="btn btn-link btn-sm" data-del="' + i + '">xoá</button></td></tr>';
    }).join('');
    paint();
    G.renderMeta();
    G.renderAuto();
    persistDraft();
  }

  function sourceCell(lb) {
    if (!lb.source || lb.source === 'human') return '<span class="src-human">người gán</span>';
    if (lb.source === 'auto_edited') {
      return '<span class="src-edit" title="' + esc(lb.source_detail || '') + '">auto · ' +
        esc(lb.source_algorithm || '?') + ' (người đã sửa)</span>';
    }
    return '<span class="src-auto" title="' + esc(lb.source_detail || '') + '">auto · ' +
      esc(lb.source_algorithm || '?') + ' (đã duyệt)</span>';
  }

  // Nháp được giữ trong bộ nhớ trình duyệt theo TỪNG dataset. Không phải nơi
  // lưu chính thức — chỉ nút Lưu / Cập nhật mới ghi vào kho nhãn.
  function persistDraft() {
    if (!S.dataset) return;
    S.draftSaved = window.LabelDraft.write(S.dataset.id, {
      labels: S.draft,
      annotator: $('#label-annotator').value,
      version: $('#label-version').value,
      rubric_vi: $('#label-rubric').value,
      label_set_id: S.savedId || null,
      dirty: S.dirty,
      auto: S.auto,
      undo: S.undo
    });
  }

  function loadDraftForDataset() {
    var d = S.dataset ? window.LabelDraft.read(S.dataset.id) : null;
    if (!d) {
      if (!$('#label-annotator').value) {
        $('#label-annotator').value = window.LabelDraft.lastAnnotator();
      }
      return false;
    }
    S.draft = d.labels || [];
    S.savedId = d.label_set_id || '';
    S.dirty = !!d.dirty;
    S.auto = d.auto || null;
    S.undo = Array.isArray(d.undo) ? d.undo : [];
    if (d.annotator) $('#label-annotator').value = d.annotator;
    if (d.version) $('#label-version').value = d.version;
    $('#label-rubric').value = d.rubric_vi || '';
    return true;
  }

  // Mỗi bước hoàn tác chụp CẢ bộ nháp lẫn trạng thái duyệt đề xuất (chấp nhận /
  // bỏ), nên hoàn tác được mọi thao tác: click tay, xoá, sửa, chấp nhận, bỏ,
  // chấp nhận/bỏ hàng loạt. Lịch sử được giữ cùng nháp qua tải lại trang.
  var ST_CODE = { pending: 'p', accepted: 'a', rejected: 'r' };
  var ST_DECODE = { p: 'pending', a: 'accepted', r: 'rejected' };

  function pushUndo() {
    S.undo.push({
      d: JSON.parse(JSON.stringify(S.draft)),
      a: S.auto ? S.auto.items.map(function (it) { return ST_CODE[it.status] || 'p'; }).join('') : null,
      c: S.auto ? S.auto.cursor : -1
    });
    if (S.undo.length > 60) S.undo.shift();
  }

  function undo() {
    if (!S.undo.length) { G.showError('Không còn bước để hoàn tác.'); return; }
    G.showError('');
    var snap = S.undo.pop();
    if (typeof snap === 'string') snap = { d: JSON.parse(snap) };   // định dạng cũ
    S.draft = snap.d || [];
    // Chỉ khôi phục trạng thái duyệt nếu vẫn là cùng phiên đề xuất.
    if (S.auto && snap.a && snap.a.length === S.auto.items.length) {
      for (var i = 0; i < S.auto.items.length; i++) {
        S.auto.items[i].status = ST_DECODE[snap.a.charAt(i)] || 'pending';
      }
      S.auto.cursor = snap.c;
    }
    S.dirty = true;
    S.selected = null;
    renderDraft();
    if (S.auto && S.auto.cursor >= 0 && S.auto.items[S.auto.cursor]) {
      S.chart.centerOnIndex(S.auto.items[S.auto.cursor].bar_index);
    }
    G.showOk('Đã hoàn tác. Còn ' + S.undo.length + ' bước có thể hoàn tác.');
  }

  function isSwingType(t) { return String(t).indexOf('SWING_') === 0; }

  function dirOf(t) {
    return (String(t).indexOf('LOW') !== -1 || String(t).indexOf('DOWN') !== -1) ? 'down' : 'up';
  }

  /**
   * Sửa một nhãn trong nháp: đổi loại, dời nến, sửa giá.
   *
   * Giá khi dời/đổi loại: đỉnh/đáy lấy high/low của nến mới; BOS/CHoCH giữ mức
   * giá cũ (mức bị phá không đổi theo nến) trừ khi đổi chiều lên/xuống. Muốn giá
   * khác thì gõ trực tiếp. Nhãn auto bị người sửa chuyển nguồn `auto_edited`.
   */
  function editLabel(i, change) {
    var lb = S.draft[i];
    if (!lb) return false;
    var nt = change.structure_type || lb.structure_type;
    var nb = change.bar_index != null ? change.bar_index : lb.bar_index;
    var bar = G.barByIndex(nb);
    if (!bar) { G.showError('Nến #' + nb + ' nằm ngoài dataset.'); return false; }
    var moved = nt !== lb.structure_type || nb !== lb.bar_index;
    if (moved && draftIndexOf(nt, nb) >= 0) {
      G.showError('Đã có nhãn ' + nt + ' tại nến #' + nb + '.');
      return false;
    }
    if (change.price != null && !isFinite(change.price)) { G.showError('Giá không hợp lệ.'); return false; }
    pushUndo();
    if (change.price != null) {
      lb.price = change.price;
    } else if (moved && (isSwingType(nt) || dirOf(nt) !== dirOf(lb.structure_type))) {
      lb.price = G.priceFor(nt, bar);
    }
    if (S.pop && S.pop.bar === lb.bar_index) S.pop.bar = nb;   // bảng thao tác đi theo nhãn
    lb.structure_type = nt;
    lb.bar_index = nb;
    if (lb.source === 'auto_accepted') lb.source = 'auto_edited';
    S.dirty = true;
    S.selected = { bar_index: nb, structure_type: nt };
    S.draft.sort(function (a, b) {
      return a.bar_index - b.bar_index || String(a.structure_type).localeCompare(String(b.structure_type));
    });
    G.showError('');
    return true;
  }

  function selectedDraftIndex() {
    return S.selected ? draftIndexOf(S.selected.structure_type, S.selected.bar_index) : -1;
  }

  function addOrToggle(bar, typeOverride) {
    var type = typeOverride || S.currentType;
    var exist = -1;
    for (var i = 0; i < S.draft.length; i++) {
      if (S.draft[i].bar_index === bar.index && S.draft[i].structure_type === type) {
        exist = i; break;
      }
    }
    pushUndo();
    S.dirty = true;
    if (exist >= 0) {
      S.draft.splice(exist, 1);
      S.selected = null;
    } else {
      S.draft.push({
        structure_type: type,
        bar_index: bar.index,
        price: G.priceFor(type, bar),
        notes: '',
        source: 'human'
      });
      S.selected = { bar_index: bar.index, structure_type: type };
    }
    G.showError('');
    G.showOk('');
    renderDraft();
  }

  //
  // Hybrid: thuật toán có sẵn ĐỀ XUẤT, người DUYỆT. Chỉ đề xuất được chấp nhận
  // mới vào bộ nháp (kèm nguồn gốc `auto_accepted` + thuật toán + tham số), và
  // vẫn phải bấm Lưu mới vào kho nhãn.

  function draftIndexOf(type, bar) {
    for (var i = 0; i < S.draft.length; i++) {
      if (S.draft[i].structure_type === type && S.draft[i].bar_index === bar) return i;
    }
    return -1;
  }

  G.addOrToggle = addOrToggle;
  G.dirOf = dirOf;
  G.draftIndexOf = draftIndexOf;
  G.editLabel = editLabel;
  G.isSwingType = isSwingType;
  G.loadDraftForDataset = loadDraftForDataset;
  G.paint = paint;
  G.persistDraft = persistDraft;
  G.pushUndo = pushUndo;
  G.renderDraft = renderDraft;
  G.selectedDraftIndex = selectedDraftIndex;
  G.sourceCell = sourceCell;
  G.undo = undo;
})(window.MSL);
