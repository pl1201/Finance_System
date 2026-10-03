/* Trang Gán nhãn — dataset, đổi khung, ô loại nhãn, dòng thông tin, nạp nến, bộ đã lưu. */
(function (MSL) {
  'use strict';

  var G = MSL.label;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var TF_ORDER = MSL.tf.ORDER;
  var esc = MSL.dom.esc;
  var S = G.S;
  var TYPES = G.TYPES;

  function findSiblingDataset(symbol, tf, current) {
    return MSL.tf.findSibling(S.datasets, symbol, tf, current);
  }

  function renderTfSwitch() {
    var box = $('#tf-switch');
    var hint = $('#tf-hint');
    if (!S.dataset) {
      box.innerHTML = TF_ORDER.map(function (tf) {
        return '<button type="button" class="tf-btn" data-tf="' + tf + '" disabled>' + tf + '</button>';
      }).join('');
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
        title = 'Chuyển sang ' + cur.symbol + ' ' + tf + ' — nhãn không mang theo';
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
      hint.textContent = 'M5 / M15 / H1 là dataset khác nhau. Nhãn gắn với khung ' +
        cur.timeframe + ' — không đổi ra phút, không so chéo khung.';
    }
  }

  function confirmLeaveDraft() {
    if (!S.dirty) return true;
    // Nháp được giữ riêng cho từng dataset nên đổi dataset không mất gì; chỉ
    // hỏi lại khi trình duyệt không cho lưu nháp.
    if (window.LabelDraft.available && S.draftSaved !== false) return true;
    return window.confirm('Bộ nháp chưa lưu và trình duyệt không giữ được nháp. ' +
      'Đổi dataset/khung sẽ bỏ nháp hiện tại. Tiếp tục?');
  }

  async function switchTimeframe(tf) {
    if (!S.dataset || tf === S.dataset.timeframe) return;
    var sib = findSiblingDataset(S.dataset.symbol, tf, S.dataset);
    if (!sib) {
      G.showError('Chưa có dataset ' + S.dataset.symbol + ' ' + tf +
        '. Hãy tạo ở trang Thử nghiệm. Trang gán nhãn không tổng hợp hay tách nến.');
      return;
    }
    if (!confirmLeaveDraft()) return;
    G.showError('');
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
    function opt(d) {
      return '<option value="' + esc(d.id) + '">' + esc(d.symbol) + ' ' + esc(d.timeframe) +
        ' · ' + esc(d.name) + (d.is_synthetic ? ' (mô phỏng)' : '') +
        ' · ' + (d.row_count != null ? d.row_count + ' nến' : '') + '</option>';
    }
    var real = sorted.filter(function (d) { return !d.is_synthetic; });
    var sim = sorted.filter(function (d) { return d.is_synthetic; });
    sel.innerHTML = '<option value="">— chọn dataset —</option>' +
      (real.length ? '<optgroup label="Dữ liệu thực">' + real.map(opt).join('') + '</optgroup>' : '') +
      (sim.length ? '<optgroup label="Dữ liệu MÔ PHỎNG (chỉ để thử công cụ)">' + sim.map(opt).join('') + '</optgroup>' : '');
    if (cur) sel.value = cur;
    renderTfSwitch();
  }

  function renderTypes() {
    var host = $('#type-grid');
    host.innerHTML = TYPES.map(function (t) {
      var on = t.id === S.currentType ? ' checked' : '';
      return '<label class="type-chip">' +
        '<input type="radio" name="label-type" value="' + esc(t.id) + '"' + on + '>' +
        '<span class="sw" style="background:' + t.sw + '"></span>' +
        esc(t.label) + '</label>';
    }).join('');
    host.addEventListener('change', function (ev) {
      var t = ev.target;
      if (t && t.name === 'label-type') S.currentType = t.value;
    });
  }

  function coverageNote() {
    if (!S.draft.length) return 'Chưa gán nến nào.';
    var idx = S.draft.map(function (l) { return l.bar_index; });
    var a = Math.min.apply(null, idx);
    var b = Math.max.apply(null, idx);
    return 'Khoảng đã gán: nến ' + a + ' → ' + b + ' (' + S.draft.length + ' nhãn). ' +
      'Nếu chưa gán hết chart, khai khoảng này khi chấm trên Đánh giá.';
  }

  function renderMeta() {
    var ds = S.dataset;
    if (!ds) {
      $('#label-meta').textContent = 'Chọn dataset — không cần chạy thuật toán. Nến lấy trực tiếp từ dataset.';
      return;
    }
    var kind = ds.is_synthetic ? 'Dữ liệu mô phỏng' : 'Dữ liệu thực tế';
    var realSib = ds.is_synthetic ? S.datasets.filter(function (d) {
      return !d.is_synthetic && d.symbol === ds.symbol && d.timeframe === ds.timeframe;
    })[0] : null;
    var hint = $('#real-data-hint');
    if (realSib) {
      hint.hidden = false;
      hint.innerHTML = 'Bạn đang xem <strong>dữ liệu MÔ PHỎNG</strong> (' + ds.row_count + ' nến). ' +
        'Đã có dữ liệu thực <strong>' + esc(realSib.name) + '</strong> (' + realSib.row_count + ' nến). ' +
        '<button type="button" class="btn btn-primary btn-sm" id="btn-go-real" data-id="' +
        esc(realSib.id) + '">Chuyển sang dữ liệu thực</button>';
    } else {
      hint.hidden = true;
      hint.innerHTML = '';
    }
    $('#label-meta').innerHTML =
      '<span>' + esc(kind) + ' · ' + esc(ds.symbol) + ' ' + esc(ds.timeframe) +
        ' · ' + (ds.row_count != null ? ds.row_count + ' nến' : '') + '</span>' +
      '<span>' + esc(coverageNote()) + '</span>' +
      '<span>Bộ đã lưu lần này: ' + (S.savedId ? '<code>' + esc(S.savedId) + '</code>' : 'chưa') + '</span>' +
      '<span>' + esc(draftStateText()) + '</span>';
    $('#btn-update').disabled = !S.savedId || !S.draft.length;
    $('#btn-export-labels').disabled = !S.savedId;
  }

  function draftStateText() {
    if (!S.draft.length) return 'Nháp trống.';
    if (!window.LabelDraft.available || S.draftSaved === false) {
      return S.draft.length + ' nhãn — trình duyệt KHÔNG giữ được nháp, đừng tải lại trang trước khi Lưu.';
    }
    return S.dirty
      ? S.draft.length + ' nhãn CHƯA LƯU vào kho (nháp được giữ trong trình duyệt).'
      : S.draft.length + ' nhãn, khớp với bộ đã lưu.';
  }

  function updateEvalLink() {
    var a = $('#link-eval');
    var q = new URLSearchParams();
    if (S.dataset) q.set('dataset_id', S.dataset.id);
    if (S.savedId) q.set('label_set_id', S.savedId);
    a.href = '/danh-gia' + (q.toString() ? '?' + q.toString() : '');
  }

  async function loadBars() {
    if (!S.dataset) {
      S.bars = [];
      $('#label-chart-empty').hidden = false;
      return;
    }
    var payload = await API.bars(S.dataset.id);
    S.bars = payload.bars || [];
    S.digits = G.detectDigits(S.bars);
    S.chart.setDigits(S.digits);
    S.chart.setBars(S.bars);
    S.chart.fit();
    $('#label-chart-empty').hidden = S.bars.length > 0;
  }

  async function loadSavedSets() {
    var tb = $('#saved-sets tbody');
    if (!S.dataset) {
      S.savedSets = [];
      tb.innerHTML = '<tr><td colspan="5" class="empty-cell">Chọn dataset.</td></tr>';
      return;
    }
    try {
      S.savedSets = await API.labelSets(S.dataset.id);
    } catch (e) { S.savedSets = []; }
    if (!S.savedSets.length) {
      tb.innerHTML = '<tr><td colspan="5" class="empty-cell">Chưa có bộ nhãn.</td></tr>';
      return;
    }
    tb.innerHTML = S.savedSets.map(function (s) {
      return '<tr data-id="' + esc(s.id) + '">' +
        '<td class="mono">' + esc(s.id) + '</td>' +
        '<td>' + esc(s.annotator) + '</td>' +
        '<td class="mono">' + esc(s.version) + '</td>' +
        '<td class="num">' + esc(s.n_labels != null ? s.n_labels : '—') +
          (s.n_auto ? ' <span class="src-auto" title="nhãn chấp nhận từ đề xuất auto">(' +
            esc(s.n_auto) + ' auto)</span>' : '') + '</td>' +
        '<td><button type="button" class="btn btn-sm btn-secondary btn-load-set" data-id="' +
          esc(s.id) + '">Tải</button></td></tr>';
    }).join('');
  }

  async function onDatasetChange() {
    var id = $('#dataset-select').value;
    S.dataset = S.datasets.filter(function (d) { return d.id === id; })[0] || null;
    G.closePop();
    S.draft = [];
    S.undo = [];
    S.selected = null;
    S.dirty = false;
    S.savedId = '';
    S.auto = null;
    if (S.dataset) window.LabelDraft.setLastDataset(S.dataset.id);
    var restored = G.loadDraftForDataset();
    renderTfSwitch();
    updateEvalLink();
    await loadBars();
    G.resetAutoRange();
    await loadSavedSets();
    G.renderDraft();
    if (restored && (S.draft.length || S.auto)) {
      var pend = S.auto ? G.autoCounts().pending : 0;
      G.showOk('Đã khôi phục ' + S.draft.length + ' nhãn từ bộ nháp trong trình duyệt' +
        (S.dirty ? ' — CHƯA lưu vào kho nhãn' : '') +
        (pend ? '; còn ' + pend + ' đề xuất chưa duyệt.' : '.'));
    }
  }

  G.confirmLeaveDraft = confirmLeaveDraft;
  G.loadSavedSets = loadSavedSets;
  G.onDatasetChange = onDatasetChange;
  G.renderDatasets = renderDatasets;
  G.renderMeta = renderMeta;
  G.renderTfSwitch = renderTfSwitch;
  G.renderTypes = renderTypes;
  G.updateEvalLink = updateEvalLink;
})(window.MSL);
