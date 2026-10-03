/* Trang Gán nhãn — click nến, lưu bộ theo dataset, không chấm F1 tại đây. */
(function () {
  'use strict';

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };

  var TF_ORDER = ['M5', 'M15', 'M30', 'H1', 'H4'];
  var TYPES = [
    { id: 'SWING_HIGH', label: 'Đỉnh cấp 1', sw: '#ffb74d' },
    { id: 'SWING_LOW', label: 'Đáy cấp 1', sw: '#4dd0e1' },
    { id: 'SWING_HIGH_L2', label: 'Đỉnh cấp 2', sw: '#ffe082' },
    { id: 'SWING_LOW_L2', label: 'Đáy cấp 2', sw: '#80deea' },
    { id: 'BOS_UP', label: 'BOS lên', sw: '#66bb6a' },
    { id: 'BOS_DOWN', label: 'BOS xuống', sw: '#ef5350' },
    { id: 'CHOCH_UP', label: 'CHoCH lên', sw: '#26c6da' },
    { id: 'CHOCH_DOWN', label: 'CHoCH xuống', sw: '#ff7043' },
    { id: 'BOS_INTERNAL_UP', label: 'BOS nội bộ lên', sw: '#9ccc65' },
    { id: 'BOS_INTERNAL_DOWN', label: 'BOS nội bộ xuống', sw: '#ef9a9a' },
    { id: 'C2_CONFIRMED_UP', label: 'C2 tăng (nến cực trị)', sw: '#00e676' },
    { id: 'C2_CONFIRMED_DOWN', label: 'C2 giảm (nến cực trị)', sw: '#ff5252' },
    { id: 'CISD_CONFIRMED_UP', label: 'CISD tăng (nến close vượt)', sw: '#69f0ae' },
    { id: 'CISD_CONFIRMED_DOWN', label: 'CISD giảm (nến close vượt)', sw: '#ff8a80' }
  ];

  var S = {
    datasets: [],
    dataset: null,
    bars: [],
    draft: [],
    undo: [],
    selected: null,
    dirty: false,
    savedId: '',
    savedSets: [],
    draftSaved: null,
    digits: 2,
    chart: null,
    currentType: 'SWING_HIGH',
    autoAlgos: [],
    // Phiên auto label: { algorithm, algorithm_version, source_detail, start, end,
    //   types, items: [đề xuất + status], cursor }. status: pending | accepted | rejected
    auto: null,
    // Bảng thao tác trên chart, mở khi bấm nến đã có nhãn / đề xuất: { bar }
    pop: null
  };

  var TYPE_LABEL = {};
  TYPES.forEach(function (t) { TYPE_LABEL[t.id] = t.label; });

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmtNum(x, d) {
    if (x === null || x === undefined || x === '') return '—';
    var n = Number(x);
    if (!isFinite(n)) return '—';
    return n.toFixed(d == null ? S.digits : d);
  }

  function showError(msg) {
    var el = $('#label-error');
    var ok = $('#label-ok');
    ok.hidden = true;
    if (!msg) { el.hidden = true; el.textContent = ''; return; }
    el.hidden = false;
    el.textContent = msg;
  }

  function showOk(msg) {
    var el = $('#label-ok');
    $('#label-error').hidden = true;
    if (!msg) { el.hidden = true; el.textContent = ''; return; }
    el.hidden = false;
    el.textContent = msg;
  }

  function isTypingTarget(el) {
    if (!el) return false;
    var tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable;
  }

  function priceFor(type, bar) {
    // CISD: nhãn ở nến có close vượt mức — mặc định close, sửa thành mức CISD nếu chấm theo giá.
    if (String(type).indexOf('CISD_') === 0) return bar.close;
    // C2 tăng quét low (giá = low), C2 giảm quét high.
    if (type === 'C2_CONFIRMED_UP') return bar.low;
    if (type === 'C2_CONFIRMED_DOWN') return bar.high;
    if (String(type).indexOf('LOW') !== -1 || String(type).indexOf('DOWN') !== -1) return bar.low;
    return bar.high;
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
      showError('Chưa có dataset ' + S.dataset.symbol + ' ' + tf +
        '. Hãy tạo ở trang Thử nghiệm. Trang gán nhãn không tổng hợp hay tách nến.');
      return;
    }
    if (!confirmLeaveDraft()) return;
    showError('');
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

  function paint() {
    if (!S.chart) return;
    S.chart.setLabelOverlay({
      labels: S.draft,
      selected: S.selected,
      suggestions: autoOverlayItems()
    });
    renderPop();
  }

  function renderDraft() {
    var tb = $('#draft-table tbody');
    $('#draft-count').textContent = S.draft.length ? S.draft.length + ' nhãn' : '';
    if (!S.draft.length) {
      tb.innerHTML = '<tr><td colspan="7" class="empty-cell">Chưa có nhãn.</td></tr>';
      paint();
      renderMeta();
      renderAuto();
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
    renderMeta();
    renderAuto();
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
    if (!S.undo.length) { showError('Không còn bước để hoàn tác.'); return; }
    showError('');
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
    showOk('Đã hoàn tác. Còn ' + S.undo.length + ' bước có thể hoàn tác.');
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
    var bar = barByIndex(nb);
    if (!bar) { showError('Nến #' + nb + ' nằm ngoài dataset.'); return false; }
    var moved = nt !== lb.structure_type || nb !== lb.bar_index;
    if (moved && draftIndexOf(nt, nb) >= 0) {
      showError('Đã có nhãn ' + nt + ' tại nến #' + nb + '.');
      return false;
    }
    if (change.price != null && !isFinite(change.price)) { showError('Giá không hợp lệ.'); return false; }
    pushUndo();
    if (change.price != null) {
      lb.price = change.price;
    } else if (moved && (isSwingType(nt) || dirOf(nt) !== dirOf(lb.structure_type))) {
      lb.price = priceFor(nt, bar);
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
    showError('');
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
        price: priceFor(type, bar),
        notes: '',
        source: 'human'
      });
      S.selected = { bar_index: bar.index, structure_type: type };
    }
    showError('');
    showOk('');
    renderDraft();
  }

  async function loadBars() {
    if (!S.dataset) {
      S.bars = [];
      $('#label-chart-empty').hidden = false;
      return;
    }
    var payload = await API.bars(S.dataset.id);
    S.bars = payload.bars || [];
    S.digits = detectDigits(S.bars);
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
    closePop();
    S.draft = [];
    S.undo = [];
    S.selected = null;
    S.dirty = false;
    S.savedId = '';
    S.auto = null;
    if (S.dataset) window.LabelDraft.setLastDataset(S.dataset.id);
    var restored = loadDraftForDataset();
    renderTfSwitch();
    updateEvalLink();
    await loadBars();
    resetAutoRange();
    await loadSavedSets();
    renderDraft();
    if (restored && (S.draft.length || S.auto)) {
      var pend = S.auto ? autoCounts().pending : 0;
      showOk('Đã khôi phục ' + S.draft.length + ' nhãn từ bộ nháp trong trình duyệt' +
        (S.dirty ? ' — CHƯA lưu vào kho nhãn' : '') +
        (pend ? '; còn ' + pend + ' đề xuất chưa duyệt.' : '.'));
    }
  }

  async function saveSet() {
    showError('');
    showOk('');
    if (!S.dataset) { showError('Chọn dataset.'); return; }
    var annotator = $('#label-annotator').value;
    if (!annotator.trim()) { showError('Phải ghi tên người gán nhãn.'); return; }
    if (!S.draft.length) { showError('Chưa có nhãn để lưu.'); return; }
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
      persistDraft();
      updateEvalLink();
      await loadSavedSets();
      renderMeta();
      showOk('Đã lưu ' + ls.id + ' · ' + ls.annotator + ' · ' + (ls.labels ? ls.labels.length : S.draft.length) +
        ' nhãn trên ' + S.dataset.symbol + ' ' + S.dataset.timeframe +
        '. Lưu tạo bộ mới, không ghi đè. Mở Đánh giá để chấm F1.');
    } catch (e) {
      showError(e.message);
    } finally {
      $('#btn-save').disabled = false;
    }
  }

  async function loadSet(id) {
    if (S.dirty && !window.confirm('Tải bộ đã lưu sẽ thay nháp hiện tại. Tiếp tục?')) return;
    try {
      var ls = await API.getLabelSet(id);
      pushUndo();
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
      updateEvalLink();
      renderDraft();
      if (S.selected) S.chart.scrollToIndex(S.selected.bar_index);
      showOk('Đã tải ' + ls.id + ' của ' + ls.annotator + '. Sửa rồi lưu sẽ tạo bộ mới.');
    } catch (e) { showError(e.message); }
  }

  async function updateSet() {
    showError(''); showOk('');
    if (!S.savedId) { showError('Chưa mở bộ nhãn nào để cập nhật. Dùng "Lưu thành bộ mới".'); return; }
    if (!S.draft.length) { showError('Bộ nháp rỗng — không ghi đè bằng bộ rỗng.'); return; }
    var annotator = $('#label-annotator').value;
    if (!annotator.trim()) { showError('Phải ghi tên người gán nhãn.'); return; }
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
          showError('Đã huỷ ghi đè. Bộ nhãn giữ nguyên.');
          return;
        }
        payload.confirm_overwrite = true;
        ls = await API.updateLabelSet(S.savedId, payload);
      }
      S.dirty = false;
      window.LabelDraft.setLastAnnotator(ls.annotator || '');
      persistDraft();
      await loadSavedSets();
      renderMeta();
      showOk('Đã ghi đè ' + ls.id + ' thành bản ' + (ls.revision || 1) + ' · ' +
        (ls.labels ? ls.labels.length : S.draft.length) + ' nhãn. ' + (ls.ghi_chu_vi || ''));
    } catch (e) {
      showError(e.message);
    } finally {
      renderMeta();
    }
  }

  function exportLabels() {
    if (!S.savedId) { showError('Lưu hoặc tải một bộ nhãn trước khi xuất.'); return; }
    if (S.dirty) {
      showOk('Lưu ý: file xuất ra là nội dung ĐÃ LƯU của ' + S.savedId + ', không phải nháp hiện tại.');
    }
    window.location.href = API.labelSetExportUrl(S.savedId);
  }

  async function importLabels(file) {
    showError(''); showOk('');
    if (!S.dataset) { showError('Chọn dataset trước khi nhập nhãn.'); return; }
    if (S.draft.length && !window.confirm('Nhập CSV sẽ thay bộ nháp hiện tại (' +
        S.draft.length + ' nhãn). Tiếp tục?')) return;
    try {
      var text = await file.text();
      var out = await API.parseLabelCsv({ dataset_id: S.dataset.id, csv_text: text });
      pushUndo();
      S.draft = out.labels || [];
      S.savedId = '';
      S.dirty = true;
      S.selected = S.draft[0]
        ? { bar_index: S.draft[0].bar_index, structure_type: S.draft[0].structure_type }
        : null;
      updateEvalLink();
      renderDraft();
      if (S.selected) S.chart.scrollToIndex(S.selected.bar_index);
      if ((out.warnings || []).length) showError('Cảnh báo: ' + out.warnings.join(' '));
      else showOk(out.ghi_chu_vi);
    } catch (e) {
      showError('Không nhập được CSV: ' + e.message);
    }
  }

  // ================================================================ auto label
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
    var di = draftIndexOf(it.structure_type, it.bar_index);
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

  function barTimeText(idx) {
    for (var i = 0; i < S.bars.length; i++) {
      if (S.bars[i].index === idx) {
        return window.chartUtils ? window.chartUtils.fmtIso(S.bars[i].bar_time) : S.bars[i].bar_time;
      }
    }
    return '';
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
      ' · ' + rangeText(S.auto.start, S.auto.end);

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
        ' · nến <span class="mono">#' + cur.bar_index + '</span> (' + esc(barTimeText(cur.bar_index)) + ')' +
        ' · giá <span class="mono">' + fmtNum(cur.price) + '</span>' +
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
        '<td class="num">' + fmtNum(it.price) + '</td>' +
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
    paint();
    renderAuto();
    persistDraft();
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
    if (draftIndexOf(nt, it.bar_index) >= 0) {
      showError('Đã có nhãn ' + nt + ' tại nến #' + it.bar_index + '.');
      return false;
    }
    var price = it.price;
    if (nt !== it.structure_type && (isSwingType(nt) || dirOf(nt) !== dirOf(it.structure_type))) {
      var bar = barByIndex(it.bar_index);
      if (bar) price = priceFor(nt, bar);
    }
    if (!opts.noUndo) pushUndo();
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
    if (!opts.noUndo) pushUndo();
    it.status = 'rejected';
    return true;
  }

  function acceptCurrent() {
    if (!S.auto) return;
    var i = S.auto.cursor;
    if (!acceptAuto(i)) return;
    S.selected = { bar_index: S.auto.items[i].bar_index, structure_type: S.auto.items[i].structure_type };
    var nx = nextPending(i, 1);
    renderDraft();
    if (nx >= 0) focusAuto(nx); else { S.auto.cursor = -1; paint(); renderAuto(); persistDraft(); }
  }

  function rejectCurrent() {
    if (!S.auto) return;
    var i = S.auto.cursor;
    if (!rejectAuto(i)) return;
    var nx = nextPending(i, 1);
    if (nx >= 0) focusAuto(nx); else { S.auto.cursor = -1; paint(); renderAuto(); persistDraft(); }
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
    pushUndo();
    if (accept) {
      pend.forEach(function (i) { acceptAuto(i, { noUndo: true }); });
    } else {
      pend.forEach(function (i) { rejectAuto(i, { noUndo: true }); });
    }
    S.auto.cursor = -1;
    renderDraft();
    paint();
    renderAuto();
    persistDraft();
    showOk(accept
      ? 'Đã chấp nhận ' + pend.length + ' đề xuất vào bộ nháp. Nhớ bấm Lưu.'
      : 'Đã bỏ ' + pend.length + ' đề xuất.');
  }

  function closeAuto() {
    if (!S.auto) return;
    var c = autoCounts();
    if (c.pending && !window.confirm('Còn ' + c.pending + ' đề xuất chưa duyệt. Đóng phiên sẽ bỏ các đề xuất này ' +
        '(nhãn đã chấp nhận vẫn ở trong nháp). Tiếp tục?')) return;
    S.auto = null;
    paint();
    renderAuto();
    persistDraft();
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

  // ---- Khoảng đề xuất theo NGÀY GIỜ (UTC). Backend vẫn nhận chỉ số nến; việc
  // ánh xạ ngày giờ -> nến làm ở đây, trên chính các nến của dataset đang mở.

  function pad2(n) { return String(n).padStart(2, '0'); }

  /** Unix giây -> giá trị ô datetime-local, hiểu là giờ UTC. */
  function tsToInput(ts) {
    var d = new Date(ts * 1000);
    return d.getUTCFullYear() + '-' + pad2(d.getUTCMonth() + 1) + '-' + pad2(d.getUTCDate()) +
      'T' + pad2(d.getUTCHours()) + ':' + pad2(d.getUTCMinutes());
  }

  function inputToTs(v) {
    if (!v) return NaN;
    return Date.parse(v.length === 16 ? v + ':00Z' : v + 'Z') / 1000;
  }

  function tsText(ts) { return tsToInput(ts).replace('T', ' ') + ' UTC'; }

  function barByIndex(idx) {
    for (var i = 0; i < S.bars.length; i++) if (S.bars[i].index === idx) return S.bars[i];
    return null;
  }

  function setRangeByIndex(a, b) {
    var ba = barByIndex(a);
    var bb = barByIndex(b);
    if (ba) $('#auto-start').value = tsToInput(ba.time);
    if (bb) $('#auto-end').value = tsToInput(bb.time);
    updateRangeHint();
  }

  /**
   * Ngày giờ đang nhập -> khoảng nến: nến đầu = nến đầu tiên có thời gian >= "Từ",
   * nến cuối = nến cuối cùng có thời gian <= "Đến".
   */
  function rangeFromInputs() {
    var t1 = inputToTs($('#auto-start').value);
    var t2 = inputToTs($('#auto-end').value);
    if (isNaN(t1) || isNaN(t2)) return { error: 'Chọn đủ ngày giờ bắt đầu và kết thúc.' };
    if (t1 > t2) return { error: 'Ngày bắt đầu đang sau ngày kết thúc.' };
    var a = null;
    var b = null;
    for (var i = 0; i < S.bars.length; i++) {
      var t = S.bars[i].time;
      if (a === null && t >= t1) a = S.bars[i];
      if (t <= t2) b = S.bars[i];
    }
    if (!a || !b || a.index > b.index) return { error: 'Không có nến nào trong khoảng ngày này.' };
    return { start: a.index, end: b.index, n: b.index - a.index + 1, startTs: a.time, endTs: b.time };
  }

  function updateRangeHint() {
    var el = $('#auto-range-hint');
    if (!S.dataset || !S.bars.length) { el.textContent = 'Chọn dataset để đặt khoảng.'; return; }
    var r = rangeFromInputs();
    if (r.error) { el.innerHTML = '<span class="st-removed">' + esc(r.error) + '</span>'; return; }
    el.textContent = r.n + ' nến ' + S.dataset.timeframe + ': ' + tsText(r.startTs) + ' → ' +
      tsText(r.endTs) + ' (nến #' + r.start + ' → #' + r.end + ').';
  }

  function resetAutoRange() {
    var has = !!(S.dataset && S.bars.length);
    var first = has ? S.bars[0] : null;
    var last = has ? S.bars[S.bars.length - 1] : null;
    $('#auto-start').min = $('#auto-end').min = first ? tsToInput(first.time) : '';
    $('#auto-start').max = $('#auto-end').max = last ? tsToInput(last.time) : '';
    if (!has) {
      $('#auto-start').value = '';
      $('#auto-end').value = '';
    } else if (S.auto && barByIndex(S.auto.start) && barByIndex(S.auto.end)) {
      setRangeByIndex(S.auto.start, S.auto.end);
    } else {
      setRangeByIndex(first.index, last.index);
    }
    updateRangeHint();
    $('#auto-run').disabled = !has || !S.autoAlgos.length;
  }

  function rangeText(a, b) {
    var ba = barByIndex(a);
    var bb = barByIndex(b);
    if (!ba || !bb) return 'nến ' + a + ' → ' + b;
    return tsText(ba.time) + ' → ' + tsText(bb.time);
  }

  async function runAutoSuggest() {
    showError(''); showOk('');
    if (!S.dataset) { showError('Chọn dataset trước.'); return; }
    var a = selectedAutoAlgo();
    if (!a) { showError('Chọn thuật toán đề xuất.'); return; }
    var rg = rangeFromInputs();
    if (rg.error) { showError(rg.error); return; }
    var start = rg.start;
    var end = rg.end;
    var types = $$('#auto-types [data-atype]').filter(function (c) { return c.checked; })
      .map(function (c) { return c.getAttribute('data-atype'); });
    if (!types.length) { showError('Chọn ít nhất một loại nhãn cần đề xuất.'); return; }
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
      if (first >= 0) focusAuto(first); else { paint(); renderAuto(); persistDraft(); }
      var c = autoCounts();
      var msg = out.suggestions.length + ' đề xuất trong ' + rangeText(out.start_index, out.end_index) +
        (c.dup ? ' (' + c.dup + ' trùng nhãn bạn đã gán)' : '') +
        '. Duyệt bằng A (chấp nhận) / X (bỏ) / N (kế tiếp). Đề xuất chưa phải nhãn — vẫn phải bấm Lưu.';
      if (!out.suggestions.length) msg = 'Không có đề xuất nào trong ' +
        rangeText(out.start_index, out.end_index) + ' với các loại đã chọn.';
      if ((out.warnings || []).length) showError(msg + ' Lưu ý: ' + out.warnings.join(' '));
      else showOk(msg);
    } catch (e) {
      showError('Không đề xuất được: ' + e.message);
    } finally {
      $('#auto-run').disabled = false;
      $('#auto-run').textContent = 'Đề xuất nhãn';
    }
  }

  // ======================================================= bảng thao tác trên chart
  //
  // Bấm vào nến đã có nhãn nháp hoặc đề xuất đang hiện (chấm xám) -> mở bảng nhỏ
  // cạnh nến: chấp nhận / bỏ / chấp nhận thành loại khác cho đề xuất; đổi loại /
  // dời nến / sửa giá / xoá cho nhãn; thêm nhãn khác vào cùng nến. Nến trống vẫn
  // gán nhanh như cũ; Shift+click luôn là gán/gỡ nhanh loại đang chọn.

  var SHORT = {
    SWING_HIGH: 'H', SWING_LOW: 'L', SWING_HIGH_L2: 'H2', SWING_LOW_L2: 'L2',
    BOS_UP: 'BU', BOS_DOWN: 'BD', CHOCH_UP: 'CU', CHOCH_DOWN: 'CD',
    BOS_INTERNAL_UP: 'IU', BOS_INTERNAL_DOWN: 'ID',
    C2_CONFIRMED_UP: 'C2↑', C2_CONFIRMED_DOWN: 'C2↓', CISD_CONFIRMED_UP: 'CI↑', CISD_CONFIRMED_DOWN: 'CI↓'
  };

  /** Nhãn nháp và đề xuất ĐANG HIỆN trên chart tại nến `idx`. */
  function itemsAtBar(idx) {
    var out = { labels: [], sugs: [] };
    S.draft.forEach(function (lb, i) { if (lb.bar_index === idx) out.labels.push(i); });
    if (S.auto) {
      S.auto.items.forEach(function (it, i) {
        if (it.bar_index !== idx) return;
        var st = itemState(it);
        if (st === 'pending' || st === 'removed') out.sugs.push(i);
      });
    }
    return out;
  }

  function typeChips(action, attrs, skip, current) {
    return '<div class="pop-types">' + TYPES.map(function (t) {
      if (skip && skip[t.id]) return '';
      var on = t.id === current;
      return '<button type="button" class="pop-chip' + (on ? ' on' : '') + '" data-pa="' + action + '"' +
        attrs + ' data-t="' + t.id + '"' + (on ? ' disabled' : '') +
        ' title="' + esc(t.label + ' (' + t.id + ')') + '">' +
        '<span class="sw" style="background:' + t.sw + '"></span>' + SHORT[t.id] + '</button>';
    }).join('') + '</div>';
  }

  function openPop(idx) {
    var at = itemsAtBar(idx);
    S.pop = { bar: idx };
    S.chart.setTooltipSuppressed(true);
    if (at.sugs.length) S.auto.cursor = at.sugs[0];   // A / X trong bảng duyệt trỏ đúng đề xuất này
    if (at.labels.length) {
      var lb = S.draft[at.labels[0]];
      S.selected = { bar_index: lb.bar_index, structure_type: lb.structure_type };
    }
    renderDraft();   // vẽ lại chart + bảng nháp + bảng thao tác
  }

  function closePop() {
    if (!S.pop) return;
    S.pop = null;
    S.chart.setTooltipSuppressed(false);
    renderPop();
  }

  function renderPop() {
    var el = $('#bar-pop');
    if (!el) return;
    if (!S.pop || !barByIndex(S.pop.bar)) {
      el.hidden = true;
      el.innerHTML = '';
      if (S.pop) { S.pop = null; S.chart.setTooltipSuppressed(false); }
      return;
    }
    var idx = S.pop.bar;
    var bar = barByIndex(idx);
    var at = itemsAtBar(idx);
    var html = '<div class="pop-head"><span>Nến <span class="mono">#' + idx + '</span> · ' +
      esc(barTimeText(idx)) + '</span>' +
      '<button type="button" class="pop-x" data-pa="close" title="Đóng (Esc)">×</button></div>';

    at.sugs.forEach(function (ai) {
      var it = S.auto.items[ai];
      html += '<div class="pop-item pop-sug">' +
        '<div class="pop-title"><span class="badge b-' + esc(it.structure_type) + '">' +
          esc(it.structure_type) + '</span> <span class="st-pending">đề xuất</span> · ' +
          esc(it.source_algorithm || S.auto.algorithm) + '</div>' +
        '<div class="pop-meta">giá <span class="mono">' + fmtNum(it.price) + '</span> · xác nhận ở nến #' +
          it.confirmed_bar_index + ' (trễ ' + it.confirmation_lag_bars + ')</div>' +
        '<div class="pop-row">' +
          '<button type="button" class="btn btn-primary btn-sm" data-pa="acc" data-ai="' + ai + '">Chấp nhận</button>' +
          '<button type="button" class="btn btn-secondary btn-sm" data-pa="rej" data-ai="' + ai + '">Bỏ</button>' +
        '</div>' +
        '<div class="pop-sub">Chấp nhận nhưng đổi thành:</div>' +
        typeChips('accas', ' data-ai="' + ai + '"', null, it.structure_type) +
        '</div>';
    });

    at.labels.forEach(function (di) {
      var lb = S.draft[di];
      html += '<div class="pop-item pop-lab">' +
        '<div class="pop-title"><span class="badge b-' + esc(lb.structure_type) + '">' +
          esc(lb.structure_type) + '</span> ' + sourceCell(lb) + '</div>' +
        '<div class="pop-sub">Đổi loại:</div>' +
        typeChips('retype', ' data-di="' + di + '"', null, lb.structure_type) +
        '<div class="pop-row">' +
          '<button type="button" class="btn btn-secondary btn-sm" data-pa="mv" data-di="' + di +
            '" data-d="-1" title="Dời sang nến trước ([)">◀</button>' +
          '<button type="button" class="btn btn-secondary btn-sm" data-pa="mv" data-di="' + di +
            '" data-d="1" title="Dời sang nến sau (])">▶</button>' +
          '<label class="pop-price">Giá <input type="number" step="any" data-pp="' + di + '" value="' +
            esc(lb.price) + '"></label>' +
          '<button type="button" class="btn btn-secondary btn-sm pop-del" data-pa="del" data-di="' + di +
            '" title="Xoá nhãn (Delete)">Xoá</button>' +
        '</div></div>';
    });

    if (!at.sugs.length && !at.labels.length) {
      html += '<div class="pop-meta">Nến này chưa có nhãn.</div>';
    }
    var have = {};
    at.labels.forEach(function (di) { have[S.draft[di].structure_type] = 1; });
    html += '<div class="pop-sub">Thêm nhãn vào nến này:</div>' + typeChips('add', '', have, null) +
      '<div class="pop-foot">Esc đóng · Shift+click nến = gán nhanh loại đang chọn · Ctrl+Z hoàn tác</div>';

    el.innerHTML = html;
    el.hidden = false;
    el.setAttribute('data-bar', String(bar.index));
    positionPop();
  }

  function positionPop() {
    var el = $('#bar-pop');
    if (!el || !S.pop) return;
    var c = S.chart.barCoords(S.pop.bar);
    if (!c) { el.style.visibility = 'hidden'; return; }   // nến đã cuộn ra khỏi khung nhìn
    el.style.visibility = '';
    var wrap = el.parentNode;
    var cw = wrap.clientWidth, ch = wrap.clientHeight;
    var w = el.offsetWidth, h = el.offsetHeight;
    var x = c.x + 16;
    if (x + w > cw - 4) x = c.x - w - 16;
    x = Math.max(4, Math.min(x, cw - w - 4));
    var y = (c.yHigh + c.yLow) / 2 - h / 2;
    y = Math.max(4, Math.min(y, ch - h - 4));
    el.style.left = x + 'px';
    el.style.top = y + 'px';
  }

  function onChartClick(bar, info) {
    if (info.shift) { closePop(); addOrToggle(bar); return; }
    var at = itemsAtBar(bar.index);
    if (at.labels.length || at.sugs.length) { openPop(bar.index); return; }
    if (S.pop) { closePop(); return; }   // click ra ngoài chỉ để đóng bảng, không gán nhầm
    addOrToggle(bar);
  }

  function onPopAction(ev) {
    var b = ev.target.closest('[data-pa]');
    if (!b || b.disabled) return;
    var act = b.getAttribute('data-pa');
    var ai = parseInt(b.getAttribute('data-ai'), 10);
    var di = parseInt(b.getAttribute('data-di'), 10);
    var t = b.getAttribute('data-t');
    showError('');
    if (act === 'close') { closePop(); return; }
    if (act === 'acc' || act === 'accas') {
      var it = S.auto && S.auto.items[ai];
      if (!it) return;
      if (!acceptAuto(ai, act === 'accas' ? { structure_type: t } : {})) return;
      var nt = act === 'accas' ? t : it.structure_type;
      S.selected = { bar_index: it.bar_index, structure_type: nt };
      renderDraft();
      showOk(nt === it.structure_type
        ? 'Đã chấp nhận ' + nt + ' tại nến #' + it.bar_index + '. Nhớ bấm Lưu.'
        : 'Đã chấp nhận đề xuất ' + it.structure_type + ' thành ' + nt + ' (nguồn: auto, người đã sửa).');
      return;
    }
    if (act === 'rej') {
      if (rejectAuto(ai)) { renderDraft(); showOk('Đã bỏ đề xuất. Ctrl+Z để hoàn tác.'); }
      return;
    }
    if (act === 'retype') {
      if (editLabel(di, { structure_type: t })) { renderDraft(); showOk('Đã đổi loại nhãn thành ' + t + '.'); }
      return;
    }
    if (act === 'mv') {
      var lb = S.draft[di];
      if (lb && editLabel(di, { bar_index: lb.bar_index + parseInt(b.getAttribute('data-d'), 10) })) renderDraft();
      return;
    }
    if (act === 'del') {
      if (!S.draft[di]) return;
      pushUndo();
      var gone = S.draft.splice(di, 1)[0];
      S.dirty = true;
      S.selected = null;
      renderDraft();
      showOk('Đã xoá nhãn ' + gone.structure_type + ' tại nến #' + gone.bar_index + '. Ctrl+Z để hoàn tác.');
      return;
    }
    if (act === 'add') {
      var bar = barByIndex(S.pop.bar);
      if (bar) addOrToggle(bar, t);
    }
  }

  function bindPop() {
    var el = $('#bar-pop');
    el.addEventListener('click', onPopAction);
    el.addEventListener('change', function (ev) {
      var inp = ev.target.closest('[data-pp]');
      if (!inp) return;
      var ok = editLabel(parseInt(inp.getAttribute('data-pp'), 10), { price: parseFloat(inp.value) });
      renderDraft();
      if (ok) showOk('Đã sửa giá. Ctrl+Z để hoàn tác.');
    });
    // Enter trong ô giá = xác nhận; không để phím lọt xuống phím tắt của trang.
    el.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter' && ev.target.matches('[data-pp]')) ev.target.blur();
    });
    S.chart.onViewChange(positionPop);
  }

  function bindAuto() {
    $('#auto-algo').addEventListener('change', renderAutoAlgoForm);
    $('#auto-run').addEventListener('click', function () { runAutoSuggest(); });
    $('#auto-range-all').addEventListener('click', function () {
      if (!S.dataset || !S.bars.length) return;
      setRangeByIndex(S.bars[0].index, S.bars[S.bars.length - 1].index);
    });
    ['#auto-start', '#auto-end'].forEach(function (sel) {
      $(sel).addEventListener('change', updateRangeHint);
      $(sel).addEventListener('input', updateRangeHint);
    });
    $('#auto-range-view').addEventListener('click', function () {
      var r = S.chart.visibleIndexRange();
      if (!r) { showError('Chưa có nến trên chart.'); return; }
      setRangeByIndex(r.start, r.end);
      showOk('Khoảng = vùng đang xem trên chart: ' + rangeText(r.start, r.end) + '.');
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
    $('#auto-undo').addEventListener('click', undo);
    $('#auto-table').addEventListener('click', function (ev) {
      var acc = ev.target.closest('[data-aacc]');
      if (acc) {
        var ia = parseInt(acc.getAttribute('data-aacc'), 10);
        S.auto.cursor = ia;
        if (acceptAuto(ia)) { renderDraft(); focusAuto(ia); }
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

  function bind() {
    bindAuto();
    $('#dataset-select').addEventListener('change', function () {
      if (!confirmLeaveDraft()) {
        $('#dataset-select').value = S.dataset ? S.dataset.id : '';
        return;
      }
      onDatasetChange().catch(function (e) { showError(e.message); });
    });
    $('#btn-save').addEventListener('click', function () { saveSet(); });
    $('#real-data-hint').addEventListener('click', function (ev) {
      var b = ev.target.closest('#btn-go-real');
      if (!b) return;
      $('#dataset-select').value = b.getAttribute('data-id');
      onDatasetChange().catch(function (e) { showError(e.message); });
    });
    $('#btn-update').addEventListener('click', function () { updateSet(); });
    $('#btn-undo').addEventListener('click', undo);
    $('#btn-export-labels').addEventListener('click', exportLabels);
    $('#btn-import-labels').addEventListener('click', function () {
      $('#label-import-file').click();
    });
    $('#label-import-file').addEventListener('change', function (ev) {
      var f = ev.target.files[0];
      if (f) importLabels(f);
      ev.target.value = '';
    });
    ['#label-annotator', '#label-version', '#label-rubric'].forEach(function (sel) {
      $(sel).addEventListener('change', persistDraft);
    });
    window.LabelDraft.guardUnload(function () { return S.dirty && S.draft.length > 0; });
    $('#draft-table').addEventListener('click', function (ev) {
      var del = ev.target.closest('[data-del]');
      if (del) {
        var i = parseInt(del.getAttribute('data-del'), 10);
        pushUndo();
        S.draft.splice(i, 1);
        S.dirty = true;
        S.selected = null;
        renderDraft();
        return;
      }
      var mv = ev.target.closest('[data-mv]');
      if (mv) {
        var mi = parseInt(mv.getAttribute('data-i'), 10);
        var lbm = S.draft[mi];
        if (lbm && editLabel(mi, { bar_index: lbm.bar_index + parseInt(mv.getAttribute('data-mv'), 10) })) {
          renderDraft();
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
          paint();
        }
        return;
      }
      var row = S.draft[parseInt(tr.getAttribute('data-i'), 10)];
      if (!row) return;
      S.selected = { bar_index: row.bar_index, structure_type: row.structure_type };
      renderDraft();
      S.chart.scrollToIndex(row.bar_index);
    });
    $('#draft-table').addEventListener('change', function (ev) {
      var inp = ev.target.closest('.note-in');
      if (!inp) return;
      var i = parseInt(inp.getAttribute('data-i'), 10);
      if (!S.draft[i]) return;
      pushUndo();
      S.draft[i].notes = inp.value;
      S.dirty = true;
      persistDraft();
    });
    $('#draft-table').addEventListener('change', function (ev) {
      var ty = ev.target.closest('.type-in');
      var pr = ev.target.closest('.price-in');
      if (!ty && !pr) return;
      var el = ty || pr;
      var i = parseInt(el.getAttribute('data-i'), 10);
      var ok = ty ? editLabel(i, { structure_type: ty.value })
                  : editLabel(i, { price: parseFloat(pr.value) });
      renderDraft();   // vẽ lại cả khi thất bại để trả ô về giá trị cũ
      if (ok) showOk('Đã sửa nhãn. Hoàn tác được bằng Ctrl+Z.');
    });
    $('#saved-sets').addEventListener('click', function (ev) {
      var btn = ev.target.closest('.btn-load-set');
      if (btn) loadSet(btn.getAttribute('data-id'));
    });
    document.addEventListener('keydown', function (ev) {
      var k = ev.key;
      if (k === 'Escape' && S.pop) { ev.preventDefault(); closePop(); return; }
      if (isTypingTarget(ev.target)) return;
      // A/X/N/P chuyển sang đề xuất khác và cuộn chart -> đóng bảng thao tác trước.
      if (S.pop && S.auto && !ev.ctrlKey && !ev.metaKey && !ev.altKey && /^[axnpAXNP]$/.test(k)) closePop();
      if (k === 'Backspace' || (k === 'z' && (ev.ctrlKey || ev.metaKey))) {
        ev.preventDefault();
        undo();
        return;
      }
      // Duyệt đề xuất auto label.
      if (S.auto && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        if (k === 'a' || k === 'A') { ev.preventDefault(); acceptCurrent(); return; }
        if (k === 'x' || k === 'X') { ev.preventDefault(); rejectCurrent(); return; }
        if (k === 'n' || k === 'N') {
          ev.preventDefault();
          var nx = nextPending(S.auto.cursor, 1);
          if (nx >= 0) focusAuto(nx);
          return;
        }
        if (k === 'p' || k === 'P') {
          ev.preventDefault();
          focusAuto(S.auto.cursor > 0 ? S.auto.cursor - 1 : S.auto.items.length - 1);
          return;
        }
      }
      // Nhãn đang chọn: [ ] dời 1 nến, Delete xoá.
      var si = selectedDraftIndex();
      if (si >= 0 && (k === '[' || k === ']')) {
        ev.preventDefault();
        if (editLabel(si, { bar_index: S.draft[si].bar_index + (k === ']' ? 1 : -1) })) {
          renderDraft();
          S.chart.centerOnIndex(S.selected.bar_index);
        }
        return;
      }
      if (si >= 0 && k === 'Delete') {
        ev.preventDefault();
        pushUndo();
        S.draft.splice(si, 1);
        S.dirty = true;
        S.selected = null;
        renderDraft();
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
    S.chart.setBarClickHandler(function (bar, info) { onChartClick(bar, info || {}); });
    renderTypes();
    bind();
    bindPop();
    try {
      S.autoAlgos = await API.autoLabelAlgorithms();
    } catch (e) {
      S.autoAlgos = [];
    }
    renderAutoAlgos();
    S.datasets = await API.datasets();
    renderDatasets();
    var q = new URLSearchParams(location.search);
    // Ưu tiên dataset trên URL; nếu không có thì quay về dataset đang làm dở,
    // để bộ nháp đã lưu trong trình duyệt hiện ra đúng chỗ.
    var ds = q.get('dataset_id') || window.LabelDraft.lastDataset();
    var known = ds && S.datasets.some(function (d) { return d.id === ds; });
    if (known) {
      $('#dataset-select').value = ds;
      await onDatasetChange();
    } else {
      renderTfSwitch();
    }
  }

  boot().catch(function (e) { showError(e.message || String(e)); });
})();
