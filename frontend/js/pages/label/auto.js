/* Trang Gán nhãn — auto label: thuật toán đề xuất, người duyệt (chấp nhận / bỏ / hàng loạt). */
(function (MSL) {
  'use strict';

  var G = MSL.label;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;
  var S = G.S;
  var TYPES = G.TYPES;
  var TYPE_LABEL = G.TYPE_LABEL;

  /** Trạng thái hiển thị của một đề xuất, suy ra từ bộ nháp hiện tại. */
  function suggestionKey(it) { return it.structure_type + '@' + it.bar_index; }

  function itemState(it) {
    // Nhãn đã chấp nhận rồi được sửa (dời nến / đổi loại) vẫn trỏ về đề xuất gốc.
    var key = suggestionKey(it);
    for (var k = 0; k < S.draft.length; k++) {
      if (S.draft[k].from_suggestion === key) {
        return S.draft[k].source === 'auto_edited' ? 'edited' : 'accepted';
      }
    }
    var di = G.draftIndexOf(it.structure_type, it.bar_index);
    if (di >= 0) {
      var lb = S.draft[di];
      return (lb.source && lb.source !== 'human') ? 'accepted' : 'dup';
    }
    if (it.status === 'rejected') return 'rejected';
    if (it.status === 'accepted') return 'removed';   // đã chấp nhận rồi gỡ / hoàn tác
    return 'pending';
  }

  var STATE_TEXT = {
    pending: 'chưa duyệt',
    accepted: 'đã chấp nhận',
    rejected: 'đã bỏ',
    dup: 'đã có trong nháp (người gán)',
    removed: 'đã gỡ khỏi nháp',
    edited: 'đã chấp nhận rồi sửa'
  };
  var STATE_CLS = {
    pending: 'st-pending', accepted: 'st-accepted', rejected: 'st-rejected',
    dup: 'st-dup', removed: 'st-removed', edited: 'st-edited'
  };

  function autoCounts() {
    var c = { total: 0, pending: 0, accepted: 0, rejected: 0, dup: 0, removed: 0, edited: 0 };
    if (!S.auto) return c;
    S.auto.items.forEach(function (it) { c.total++; c[itemState(it)]++; });
    return c;
  }

  function autoOverlayItems() {
    if (!S.auto) return [];
    var out = [];
    S.auto.items.forEach(function (it, i) {
      var st = itemState(it);
      if (st !== 'pending' && st !== 'removed') return;   // đã chấp nhận thì vẽ như nhãn
      out.push({
        structure_type: it.structure_type,
        bar_index: it.bar_index,
        price: it.price,
        confirmed_bar_index: it.confirmed_bar_index,
        confirmation_lag_bars: it.confirmation_lag_bars,
        reason_text_vi: it.reason_text_vi,
        source_algorithm: it.source_algorithm,
        current: i === S.auto.cursor
      });
    });
    return out;
  }

  function renderAuto() {
    var box = $('#auto-review');
    var sec = $('#auto-table-sec');
    if (!S.auto || !S.auto.items.length) {
      box.hidden = true;
      sec.hidden = true;
      return;
    }
    box.hidden = false;
    sec.hidden = false;
    var c = autoCounts();
    var done = c.total - c.pending;
    $('#auto-progress').textContent = 'Đã duyệt ' + done + '/' + c.total + ' đề xuất · chấp nhận ' +
      c.accepted + (c.edited ? ' · đã sửa ' + c.edited : '') + ' · bỏ ' + c.rejected +
      (c.dup ? ' · trùng nhãn người gán ' + c.dup : '') +
      (c.removed ? ' · đã gỡ ' + c.removed : '');
    $('#auto-source').textContent = S.auto.algorithm + ' v' + S.auto.algorithm_version +
      ' · ' + G.rangeText(S.auto.start, S.auto.end);

    var cur = S.auto.items[S.auto.cursor];
    if (!cur) {
      $('#auto-current').innerHTML = c.pending
        ? 'Chọn một đề xuất trong bảng bên dưới.'
        : '<span class="st-accepted">Đã duyệt hết đề xuất.</span> Kiểm tra lại bộ nháp rồi bấm <strong>Lưu</strong>.';
    } else {
      var st = itemState(cur);
      $('#auto-current').innerHTML =
        '<span class="badge b-' + esc(cur.structure_type) + '">' + esc(cur.structure_type) + '</span> ' +
        esc(TYPE_LABEL[cur.structure_type] || cur.structure_type) +
        ' · nến <span class="mono">#' + cur.bar_index + '</span> (' + esc(G.barTimeText(cur.bar_index)) + ')' +
        ' · giá <span class="mono">' + G.fmtNum(cur.price) + '</span>' +
        ' · thuật toán xác nhận ở nến #' + cur.confirmed_bar_index +
        ' (trễ ' + cur.confirmation_lag_bars + ' nến)' +
        ' · <span class="' + STATE_CLS[st] + '">' + esc(STATE_TEXT[st]) + '</span>' +
        '<br><span class="muted">' + esc(cur.reason_text_vi || cur.reason_code || '') + '</span>';
    }
    var curState = cur ? itemState(cur) : null;
    $('#auto-accept').disabled = !cur || curState === 'accepted' || curState === 'dup' || curState === 'edited';
    $('#auto-reject').disabled = !cur || curState !== 'pending' && curState !== 'removed';
    $('#auto-accept-all').disabled = !c.pending;
    $('#auto-reject-all').disabled = !c.pending;

    $('#auto-count').textContent = c.total + ' đề xuất · còn ' + c.pending + ' chưa duyệt';
    $('#auto-table tbody').innerHTML = S.auto.items.map(function (it, i) {
      var st2 = itemState(it);
      var canAccept = st2 === 'pending' || st2 === 'removed' || st2 === 'rejected';   // không cho khi đã nhận/sửa
      return '<tr data-ai="' + i + '"' + (i === S.auto.cursor ? ' class="current"' : '') + '>' +
        '<td class="num">' + i + '</td>' +
        '<td><span class="badge b-' + esc(it.structure_type) + '">' + esc(it.structure_type) + '</span></td>' +
        '<td class="num">' + it.bar_index + '</td>' +
        '<td class="num">' + G.fmtNum(it.price) + '</td>' +
        '<td class="num">' + it.confirmed_bar_index + ' (+' + it.confirmation_lag_bars + ')</td>' +
        '<td class="mono">' + esc(it.reason_code || '') + '</td>' +
        '<td class="' + STATE_CLS[st2] + '">' + esc(STATE_TEXT[st2]) + '</td>' +
        '<td>' +
          (canAccept ? '<button type="button" class="btn btn-link btn-sm" data-aacc="' + i + '">chấp nhận</button>' : '') +
          (st2 === 'pending' || st2 === 'removed'
            ? '<button type="button" class="btn btn-link btn-sm" data-arej="' + i + '">bỏ</button>' : '') +
        '</td></tr>';
    }).join('');
  }

  function nextPending(from, dir) {
    if (!S.auto) return -1;
    var n = S.auto.items.length;
    for (var k = 1; k <= n; k++) {
      var i = ((from + dir * k) % n + n) % n;
      if (itemState(S.auto.items[i]) === 'pending') return i;
    }
    return -1;
  }

  function focusAuto(i) {
    if (!S.auto || i < 0 || i >= S.auto.items.length) return;
    S.auto.cursor = i;
    S.chart.centerOnIndex(S.auto.items[i].bar_index);
    G.paint();
    renderAuto();
    G.persistDraft();
  }

  /**
   * Chấp nhận đề xuất `i` vào nháp. `opts.structure_type` = chấp nhận nhưng đổi
   * sang loại khác: nguồn ghi `auto_edited` (người đã sửa), không bao giờ `human`.
   */
  function acceptAuto(i, opts) {
    opts = opts || {};
    var it = S.auto && S.auto.items[i];
    if (!it) return false;
    var st0 = itemState(it);
    if (st0 !== 'pending' && st0 !== 'removed' && st0 !== 'rejected') return false;
    var nt = opts.structure_type || it.structure_type;
    if (G.draftIndexOf(nt, it.bar_index) >= 0) {
      G.showError('Đã có nhãn ' + nt + ' tại nến #' + it.bar_index + '.');
      return false;
    }
    var price = it.price;
    if (nt !== it.structure_type && (G.isSwingType(nt) || G.dirOf(nt) !== G.dirOf(it.structure_type))) {
      var bar = G.barByIndex(it.bar_index);
      if (bar) price = G.priceFor(nt, bar);
    }
    if (!opts.noUndo) G.pushUndo();
    S.draft.push({
      structure_type: nt,
      bar_index: it.bar_index,
      price: price,
      notes: '',
      source: nt === it.structure_type ? 'auto_accepted' : 'auto_edited',
      source_algorithm: it.source_algorithm,
      source_detail: it.source_detail,
      from_suggestion: suggestionKey(it)
    });
    S.draft.sort(function (a, b) {
      return a.bar_index - b.bar_index || String(a.structure_type).localeCompare(String(b.structure_type));
    });
    it.status = 'accepted';
    S.dirty = true;
    return true;
  }

  function rejectAuto(i, opts) {
    opts = opts || {};
    var it = S.auto && S.auto.items[i];
    if (!it) return false;
    var st = itemState(it);
    if (st !== 'pending' && st !== 'removed') return false;
    if (!opts.noUndo) G.pushUndo();
    it.status = 'rejected';
    return true;
  }

  function acceptCurrent() {
    if (!S.auto) return;
    var i = S.auto.cursor;
    if (!acceptAuto(i)) return;
    S.selected = { bar_index: S.auto.items[i].bar_index, structure_type: S.auto.items[i].structure_type };
    var nx = nextPending(i, 1);
    G.renderDraft();
    if (nx >= 0) focusAuto(nx); else { S.auto.cursor = -1; G.paint(); renderAuto(); G.persistDraft(); }
  }

  function rejectCurrent() {
    if (!S.auto) return;
    var i = S.auto.cursor;
    if (!rejectAuto(i)) return;
    var nx = nextPending(i, 1);
    if (nx >= 0) focusAuto(nx); else { S.auto.cursor = -1; G.paint(); renderAuto(); G.persistDraft(); }
  }

  function bulkAuto(accept) {
    if (!S.auto) return;
    var pend = [];
    S.auto.items.forEach(function (it, i) { if (itemState(it) === 'pending') pend.push(i); });
    if (!pend.length) return;
    var msg = accept
      ? 'Chấp nhận ' + pend.length + ' đề xuất CHƯA xem từng cái?\n\n' +
        'Các nhãn này được ghi nguồn "auto · ' + S.auto.algorithm + '". Chấm lại ' + S.auto.algorithm +
        ' trên bộ nhãn này sẽ bị cảnh báo thiên lệch, vì nhãn không độc lập với thuật toán.'
      : 'Bỏ ' + pend.length + ' đề xuất chưa duyệt?';
    if (!window.confirm(msg)) return;
    G.pushUndo();
    if (accept) {
      pend.forEach(function (i) { acceptAuto(i, { noUndo: true }); });
    } else {
      pend.forEach(function (i) { rejectAuto(i, { noUndo: true }); });
    }
    S.auto.cursor = -1;
    G.renderDraft();
    G.paint();
    renderAuto();
    G.persistDraft();
    G.showOk(accept
      ? 'Đã chấp nhận ' + pend.length + ' đề xuất vào bộ nháp. Nhớ bấm Lưu.'
      : 'Đã bỏ ' + pend.length + ' đề xuất.');
  }

  function closeAuto() {
    if (!S.auto) return;
    var c = autoCounts();
    if (c.pending && !window.confirm('Còn ' + c.pending + ' đề xuất chưa duyệt. Đóng phiên sẽ bỏ các đề xuất này ' +
        '(nhãn đã chấp nhận vẫn ở trong nháp). Tiếp tục?')) return;
    S.auto = null;
    G.paint();
    renderAuto();
    G.persistDraft();
  }

  function selectedAutoAlgo() {
    var name = $('#auto-algo').value;
    return S.autoAlgos.filter(function (a) { return a.name === name; })[0] || null;
  }

  function renderAutoAlgos() {
    var sel = $('#auto-algo');
    if (!S.autoAlgos.length) {
      sel.innerHTML = '<option value="">— không có thuật toán sinh nhãn cấu trúc —</option>';
      $('#auto-run').disabled = true;
      return;
    }
    sel.innerHTML = S.autoAlgos.map(function (a) {
      return '<option value="' + esc(a.name) + '">' + esc(a.display_name_vi) + ' (v' + esc(a.version) + ')</option>';
    }).join('');
    renderAutoAlgoForm();
  }

  function renderAutoAlgoForm() {
    var a = selectedAutoAlgo();
    if (!a) return;
    $('#auto-params').innerHTML = (a.params || []).map(function (p) {
      var id = 'auto-p-' + p.name;
      if (p.type === 'bool') {
        return '<label class="check" title="' + esc(p.help_vi) + '"><input type="checkbox" id="' + id +
          '" data-ap="' + esc(p.name) + '"' + (p.default ? ' checked' : '') + '><span>' + esc(p.label_vi) + '</span></label>';
      }
      if (p.type === 'choice') {
        return '<label class="field"><span>' + esc(p.label_vi) + '</span><select id="' + id + '" data-ap="' + esc(p.name) + '">' +
          (p.choices || []).map(function (c) {
            return '<option' + (c === p.default ? ' selected' : '') + '>' + esc(c) + '</option>';
          }).join('') + '</select></label>';
      }
      var attrs = ' type="number" value="' + esc(p.default) + '"';
      if (p.min != null) attrs += ' min="' + p.min + '"';
      if (p.max != null) attrs += ' max="' + p.max + '"';
      attrs += ' step="' + (p.step || (p.type === 'int' ? 1 : 'any')) + '"';
      return '<label class="field" title="' + esc(p.help_vi) + '"><span>' + esc(p.label_vi) + '</span>' +
        '<input id="' + id + '" data-ap="' + esc(p.name) + '"' + attrs + '></label>';
    }).join('');
    $('#auto-types').innerHTML = (a.label_types || []).map(function (t) {
      var sw = (TYPES.filter(function (x) { return x.id === t; })[0] || {}).sw || '#78909c';
      return '<label class="type-chip"><input type="checkbox" data-atype="' + esc(t) + '" checked>' +
        '<span class="sw" style="background:' + sw + '"></span>' + esc(TYPE_LABEL[t] || t) + '</label>';
    }).join('');
    $('#auto-run').disabled = !S.dataset;
  }

  function collectAutoParams() {
    var a = selectedAutoAlgo();
    var out = {};
    $$('#auto-params [data-ap]').forEach(function (el) {
      var name = el.getAttribute('data-ap');
      var spec = (a.params || []).filter(function (p) { return p.name === name; })[0];
      if (!spec) return;
      if (spec.type === 'bool') out[name] = el.checked;
      else if (spec.type === 'int') out[name] = parseInt(el.value, 10);
      else if (spec.type === 'float') out[name] = parseFloat(el.value);
      else out[name] = el.value;
    });
    return out;
  }

  async function runAutoSuggest() {
    G.showError(''); G.showOk('');
    if (!S.dataset) { G.showError('Chọn dataset trước.'); return; }
    var a = selectedAutoAlgo();
    if (!a) { G.showError('Chọn thuật toán đề xuất.'); return; }
    var rg = G.rangeFromInputs();
    if (rg.error) { G.showError(rg.error); return; }
    var start = rg.start;
    var end = rg.end;
    var types = $$('#auto-types [data-atype]').filter(function (c) { return c.checked; })
      .map(function (c) { return c.getAttribute('data-atype'); });
    if (!types.length) { G.showError('Chọn ít nhất một loại nhãn cần đề xuất.'); return; }
    if (S.auto && autoCounts().pending &&
        !window.confirm('Phiên đề xuất cũ còn ' + autoCounts().pending + ' đề xuất chưa duyệt. ' +
          'Đề xuất lại sẽ thay phiên cũ (nhãn đã chấp nhận vẫn giữ). Tiếp tục?')) return;

    $('#auto-run').disabled = true;
    $('#auto-run').textContent = 'Đang chạy ' + a.name + '…';
    try {
      var out = await API.autoLabelSuggest({
        dataset_id: S.dataset.id,
        algorithm: a.name,
        params: collectAutoParams(),
        start_index: start,
        end_index: end,
        types: types
      });
      S.auto = {
        algorithm: out.algorithm,
        algorithm_version: out.algorithm_version,
        source_detail: out.source_detail,
        start: out.start_index,
        end: out.end_index,
        types: out.types,
        items: (out.suggestions || []).map(function (sg) {
          var it = {};
          for (var k in sg) if (Object.prototype.hasOwnProperty.call(sg, k)) it[k] = sg[k];
          it.status = 'pending';
          return it;
        }),
        cursor: -1
      };
      var first = nextPending(-1, 1);
      if (first >= 0) focusAuto(first); else { G.paint(); renderAuto(); G.persistDraft(); }
      var c = autoCounts();
      var msg = out.suggestions.length + ' đề xuất trong ' + G.rangeText(out.start_index, out.end_index) +
        (c.dup ? ' (' + c.dup + ' trùng nhãn bạn đã gán)' : '') +
        '. Duyệt bằng A (chấp nhận) / X (bỏ) / N (kế tiếp). Đề xuất chưa phải nhãn — vẫn phải bấm Lưu.';
      if (!out.suggestions.length) msg = 'Không có đề xuất nào trong ' +
        G.rangeText(out.start_index, out.end_index) + ' với các loại đã chọn.';
      if ((out.warnings || []).length) G.showError(msg + ' Lưu ý: ' + out.warnings.join(' '));
      else G.showOk(msg);
    } catch (e) {
      G.showError('Không đề xuất được: ' + e.message);
    } finally {
      $('#auto-run').disabled = false;
      $('#auto-run').textContent = 'Đề xuất nhãn';
    }
  }

  function bindAuto() {
    $('#auto-algo').addEventListener('change', renderAutoAlgoForm);
    $('#auto-run').addEventListener('click', function () { runAutoSuggest(); });
    $('#auto-range-all').addEventListener('click', function () {
      if (!S.dataset || !S.bars.length) return;
      G.setRangeByIndex(S.bars[0].index, S.bars[S.bars.length - 1].index);
    });
    ['#auto-start', '#auto-end'].forEach(function (sel) {
      $(sel).addEventListener('change', G.updateRangeHint);
      $(sel).addEventListener('input', G.updateRangeHint);
    });
    $('#auto-range-view').addEventListener('click', function () {
      var r = S.chart.visibleIndexRange();
      if (!r) { G.showError('Chưa có nến trên chart.'); return; }
      G.setRangeByIndex(r.start, r.end);
      G.showOk('Khoảng = vùng đang xem trên chart: ' + G.rangeText(r.start, r.end) + '.');
    });
    $('#auto-accept').addEventListener('click', acceptCurrent);
    $('#auto-reject').addEventListener('click', rejectCurrent);
    $('#auto-next').addEventListener('click', function () {
      var nx = nextPending(S.auto ? S.auto.cursor : -1, 1);
      if (nx >= 0) focusAuto(nx);
    });
    $('#auto-prev').addEventListener('click', function () {
      if (!S.auto) return;
      var i = S.auto.cursor > 0 ? S.auto.cursor - 1 : S.auto.items.length - 1;
      focusAuto(i);
    });
    $('#auto-accept-all').addEventListener('click', function () { bulkAuto(true); });
    $('#auto-reject-all').addEventListener('click', function () { bulkAuto(false); });
    $('#auto-close').addEventListener('click', closeAuto);
    $('#auto-undo').addEventListener('click', G.undo);
    $('#auto-table').addEventListener('click', function (ev) {
      var acc = ev.target.closest('[data-aacc]');
      if (acc) {
        var ia = parseInt(acc.getAttribute('data-aacc'), 10);
        S.auto.cursor = ia;
        if (acceptAuto(ia)) { G.renderDraft(); focusAuto(ia); }
        return;
      }
      var rej = ev.target.closest('[data-arej]');
      if (rej) {
        var ir = parseInt(rej.getAttribute('data-arej'), 10);
        if (rejectAuto(ir)) focusAuto(ir);
        return;
      }
      var tr = ev.target.closest('tr[data-ai]');
      if (tr) focusAuto(parseInt(tr.getAttribute('data-ai'), 10));
    });
  }

  G.acceptAuto = acceptAuto;
  G.acceptCurrent = acceptCurrent;
  G.autoCounts = autoCounts;
  G.autoOverlayItems = autoOverlayItems;
  G.bindAuto = bindAuto;
  G.focusAuto = focusAuto;
  G.itemState = itemState;
  G.nextPending = nextPending;
  G.rejectAuto = rejectAuto;
  G.rejectCurrent = rejectCurrent;
  G.renderAuto = renderAuto;
  G.renderAutoAlgos = renderAutoAlgos;
})(window.MSL);
