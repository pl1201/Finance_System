/* Market Structure Lab — điều khiển giao diện. */
(function () {
  'use strict';

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };

  var S = {
    datasets: [],
    dataset: null,
    algorithms: [],
    algo: null,
    mode: 'full',
    digits: 2,
    run: null,            // kết quả chạy hiện tại {events, timeline, stats, ...}
    allBars: [],          // nến của khoảng đang chọn
    replay: null,         // {sid, cursor, total, events, timeline, playing, timer, renderedCursor}
    runs: [],
    selectedRuns: [],
    layers: {
      swing: true, swing_l2: true, hhll: true, eq: true, levels: true, bos: true, choch: true,
      c2: true, cisd: true, lifecycle: true, dataq: true,
      // dc_atr_structure: mặc định bật khung chính; nhãn chữ, xác nhận, ứng viên, baseline tắt.
      dc: true, regime: true, range: true, dc_labels: false, dc_confirm: false,
      dc_candidate: false, baseline: false
    },
    baseline: null,       // run swing_pivot 3/3 phủ lên để so sánh {run_id, events, dataset_id, range}
    selectedEventId: null,
    chart: null,
    draftLabels: [],
    labelSetId: null,
    labelSets: [],
    labelDirty: false,
    labelDraftSaved: null
  };

  // ----------------------------------------------------------------- tiện ích

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmtIso(s) { return window.chartUtils.fmtIso(s); }

  function detectDigits(bars) {
    var maxD = 0;
    for (var i = 0; i < Math.min(bars.length, 200); i++) {
      var v = String(bars[i].close);
      var dot = v.indexOf('.');
      if (dot >= 0) maxD = Math.max(maxD, v.length - dot - 1);
    }
    return Math.max(2, Math.min(maxD, 6));
  }

  function banner(kind, html) {
    var el = $('#status-banner');
    if (!kind) { el.hidden = true; el.innerHTML = ''; return; }
    el.className = 'note note-' + kind;
    el.innerHTML = html;
    el.hidden = false;
  }

  function loading(on) { $('#chart-loading').hidden = !on; }

  function toLocalInput(iso) {
    if (!iso) return '';
    return String(iso).replace('+00:00', '').replace('Z', '').slice(0, 16);
  }

  function fromLocalInput(v) { return v ? v + ':00+00:00' : null; }

  // ----------------------------------------------------------------- khởi tạo

  async function init() {
    S.chart = new window.MarketChart($('#chart'), $('#chart-tooltip'));
    S.chart.onCompactChange(function (c) { $('#dc-compact-note').hidden = !c; });

    try {
      var h = await API.health();
      $('#health-pill').textContent = 'Backend OK · v' + h.version;
      $('#health-pill').className = 'pill pill-ok';
    } catch (e) {
      $('#health-pill').textContent = 'Backend lỗi';
      $('#health-pill').className = 'pill pill-bad';
      banner('error', 'Không kết nối được backend: ' + esc(e.message));
    }

    await loadAlgorithms();
    await loadDatasets();
    bindEvents();
    await loadRuns();
  }

  async function loadAlgorithms() {
    S.algorithms = await API.algorithms();
    var opts = S.algorithms
      .map(function (a) { return '<option value="' + esc(a.name) + '">' + esc(a.display_name_vi) + ' (v' + esc(a.version) + ')</option>'; })
      .join('');
    $('#algo-select').innerHTML = opts;
    $('#rp-algo').innerHTML = opts;
    var last = null;
    try { last = window.localStorage.getItem('msl.lastAlgorithm'); } catch (e) { last = null; }
    var known = S.algorithms.some(function (a) { return a.name === last; });
    selectAlgorithm(known ? last : (S.algorithms[0] ? S.algorithms[0].name : null));
  }

  function selectAlgorithm(name) {
    S.algo = S.algorithms.filter(function (a) { return a.name === name; })[0] || null;
    if (!S.algo) return;
    $('#algo-select').value = S.algo.name;
    $('#rp-algo').value = S.algo.name;
    try { window.localStorage.setItem('msl.lastAlgorithm', S.algo.name); } catch (e) { /* chế độ riêng tư */ }
    $('#algo-desc').textContent = S.algo.description_vi;
    $('#algo-desc').title = S.algo.description_vi || '';
    var hint = $('#layer-hint');
    if (S.algo.name === 'swing_hierarchy') {
      hint.textContent = 'Cấp 2 = ô vuông. HH/LH chỉ so hai đỉnh/đáy cấp 2 liên tiếp. Không gồm BOS. Đường mức = cấp 2 gần nhất.';
    } else if (S.algo.name === 'swing_pivot') {
      hint.textContent = 'HH/LH so từng đỉnh cấp 1. BOS/CHoCH là sự kiện phá vỡ riêng — không trộn với nhãn HH.';
    } else if (S.algo.name === 'dc_atr_structure') {
      hint.textContent = 'DC: marker nằm ĐÚNG giá close (không snap lên wick). Đường nối chỉ giữa hai pivot đã xác nhận; ứng viên là nét đứt. Dải đáy = trạng thái theo swing đã xác nhận, bắt đầu từ lúc biết. Chữ nhãn tự ẩn khi zoom xa (nhãn DC dày hơn ~1 nhãn / 26 px).';
    } else {
      hint.textContent = 'Bật/tắt lớp marker cho lần chạy hiện tại. Replay vẫn chỉ hiện sự kiện đã xác nhận tại con trỏ.';
    }
    var isDc = S.algo.name === 'dc_atr_structure';
    $('#dc-layers').hidden = !isDc;
    $('#btn-baseline').hidden = !isDc;
    renderParamForm();
    syncTimeframeParam();
  }

  /** Tham số `timeframe` (nếu thuật toán có) luôn theo khung của dataset đang chọn. */
  function syncTimeframeParam() {
    var el = $('#param-timeframe');
    if (el && S.dataset && S.dataset.timeframe) {
      el.value = S.dataset.timeframe;
      el.title = 'Tự điền theo dataset đang chọn (' + S.dataset.timeframe + ').';
    }
  }

  /** Ẩn tham số không có hiệu lực (ParamSpec.show_if), vd reversal_pct khi mode = atr. */
  function applyParamVisibility() {
    if (!S.algo) return;
    S.algo.params.forEach(function (p) {
      if (!p.show_if) return;
      var wrap = $('#param-form [data-param-wrap="' + p.name + '"]');
      var ctl = $('#param-' + p.show_if.param);
      if (wrap && ctl) wrap.hidden = ctl.value !== p.show_if.value;
    });
  }

  function renderParamForm() {
    var box = $('#param-form');
    if (!S.algo) { box.innerHTML = ''; return; }
    box.innerHTML = S.algo.params.map(function (p) {
      return '<div data-param-wrap="' + esc(p.name) + '">' + fieldHtml(p) + '</div>';
    }).join('');
    S.algo.params.forEach(function (p) {
      if (!p.show_if) return;
      var ctl = $('#param-' + p.show_if.param);
      if (ctl && !ctl.dataset.visBound) {
        ctl.dataset.visBound = '1';
        ctl.addEventListener('change', applyParamVisibility);
      }
    });
    applyParamVisibility();

    function fieldHtml(p) {
      var id = 'param-' + p.name;
      if (p.type === 'bool') {
        return '<label class="check" title="' + esc(p.help_vi) + '">' +
          '<input type="checkbox" id="' + id + '" data-param="' + esc(p.name) + '"' + (p.default ? ' checked' : '') + '>' +
          '<span>' + esc(p.label_vi) + '</span></label>';
      }
      if (p.type === 'choice') {
        return '<label class="field" title="' + esc(p.help_vi) + '"><span>' + esc(p.label_vi) + '</span>' +
          '<select id="' + id + '" data-param="' + esc(p.name) + '">' +
          (p.choices || []).map(function (c) { return '<option' + (c === p.default ? ' selected' : '') + '>' + esc(c) + '</option>'; }).join('') +
          '</select></label>';
      }
      if (p.type === 'str' || p.type === 'string') {
        return '<label class="field" title="' + esc(p.help_vi) + '"><span>' + esc(p.label_vi) + '</span>' +
          '<input id="' + id + '" data-param="' + esc(p.name) + '" type="text" value="' + esc(p.default) + '"></label>' +
          (p.help_vi ? '<p class="hint">' + esc(p.help_vi) + '</p>' : '');
      }
      var attrs = ' type="number" value="' + esc(p.default) + '"';
      if (p.min !== null && p.min !== undefined) attrs += ' min="' + p.min + '"';
      if (p.max !== null && p.max !== undefined) attrs += ' max="' + p.max + '"';
      attrs += ' step="' + (p.step || (p.type === 'int' ? 1 : 'any')) + '"';
      return '<label class="field" title="' + esc(p.help_vi) + '"><span>' + esc(p.label_vi) + '</span>' +
        '<input id="' + id + '" data-param="' + esc(p.name) + '"' + attrs + '></label>' +
        (p.help_vi ? '<p class="hint">' + esc(p.help_vi) + '</p>' : '');
    }
  }

  function collectParams() {
    var out = {};
    $$('#param-form [data-param]').forEach(function (el) {
      var name = el.getAttribute('data-param');
      var spec = S.algo.params.filter(function (p) { return p.name === name; })[0];
      if (!spec) return;
      if (spec.type === 'bool') out[name] = el.checked;
      else if (spec.type === 'int') out[name] = parseInt(el.value, 10);
      else if (spec.type === 'float') out[name] = parseFloat(el.value);
      else out[name] = el.value;
    });
    return out;
  }

  // ----------------------------------------------------------------- dataset

  async function loadDatasets(keepId) {
    S.datasets = await API.datasets();
    var sel = $('#dataset-select');
    if (!S.datasets.length) {
      sel.innerHTML = '<option value="">— chưa có dataset —</option>';
      S.dataset = null;
      renderDatasetInfo();
      $('#btn-run').disabled = true;
      banner('info', 'Chưa có dataset nào. Bấm <strong>Tạo dữ liệu mẫu</strong> để sinh bộ dữ liệu MÔ PHỎNG, hoặc <strong>Nhập CSV…</strong> để nạp dữ liệu của bạn.');
      return;
    }
    sel.innerHTML = S.datasets.map(function (d) {
      var prefix = d.is_synthetic ? 'MP · ' : '';
      var label = prefix + d.symbol + ' ' + d.timeframe + ' · ' + d.row_count + ' nến';
      var from = (d.name || '').match(/\(từ [^)]+\)/);
      if (from) label += ' ' + from[0];
      return '<option value="' + esc(d.id) + '">' + esc(label) + '</option>';
    }).join('');
    // Mở lại trang thì quay về dataset đang làm dở, nếu nó còn tồn tại —
    // nếu không, bộ nháp nhãn đã khôi phục sẽ nằm ở dataset người dùng không
    // nhìn thấy và trông như bị mất.
    function exists(id) {
      return !!id && S.datasets.some(function (d) { return d.id === id; });
    }
    var remembered = window.LabelDraft.lastDataset();
    var target = exists(keepId) ? keepId
      : (exists(remembered) ? remembered : S.datasets[0].id);
    sel.value = target;
    await selectDataset(target);
  }

  async function selectDataset(id, opts) {
    opts = opts || {};
    var keepStart = opts.keepRange ? $('#range-start').value : '';
    var keepEnd = opts.keepRange ? $('#range-end').value : '';
    S.dataset = S.datasets.filter(function (d) { return d.id === id; })[0] || null;
    S.baseline = null;
    syncTimeframeParam();
    renderDatasetInfo();
    resetRangeInputs();
    if (opts.keepRange && keepStart && keepEnd && S.dataset) {
      var lo = toLocalInput(S.dataset.start_time);
      var hi = toLocalInput(S.dataset.end_time);
      $('#range-start').value = keepStart > lo ? keepStart : lo;
      $('#range-end').value = keepEnd < hi ? keepEnd : hi;
    }
    $('#btn-run').disabled = !S.dataset;
    S.run = null;
    $('#btn-replay-here').hidden = true;
    S.allBars = [];
    await stopReplay();
    if (S.mode !== 'full') switchMode('full');
    $('#btn-export-csv').disabled = true;
    $('#btn-export-png').disabled = true;
    renderEvents([]);
    $('#stats-body').innerHTML = '<p class="hint">F1, P90 và so sánh nhiều cấu hình: <a href="/danh-gia">Đánh giá thuật toán</a>.</p><p class="muted">Chưa chạy lần nào trên dataset này.</p>';
    $('#synthetic-watermark').hidden = !(S.dataset && S.dataset.is_synthetic);
    if (S.dataset) {
      await previewDatasetBars();
    } else {
      S.chart.setBars([]);
      $('#chart-empty').hidden = false;
    }
    // Nháp nhãn gắn với ĐÚNG dataset: bar_index của dataset này không dùng lại
    // được cho dataset khác. Nạp nháp riêng của dataset vừa chọn.
    if (S.dataset) window.LabelDraft.setLastDataset(S.dataset.id);
    loadDraftForDataset();
    await refreshLabelSetPicker();
    if ($('#chk-history-current-ds').checked) await loadRuns();
  }

  async function previewDatasetBars() {
    try {
      var barsRes = await API.bars(
        S.dataset.id,
        fromLocalInput($('#range-start').value),
        fromLocalInput($('#range-end').value)
      );
      S.allBars = barsRes.bars || [];
      S.digits = detectDigits(S.allBars);
      S.chart.setDigits(S.digits);
      S.chart.setBars(S.allBars);
      S.chart.setEvents([], [], { layers: S.layers });
      S.chart.showLast(350);
      $('#chart-empty').hidden = true;
      var legend = $('#chart-legend');
      if (legend) legend.hidden = true;
      $('#btn-export-png').disabled = false;
    } catch (e) {
      S.allBars = [];
      S.chart.setBars([]);
      $('#chart-empty').hidden = false;
    }
  }

  function renderDatasetInfo() {
    var box = $('#dataset-info');
    var d = S.dataset;
    if (!d) { box.className = 'info-card empty'; box.textContent = 'Chưa chọn dataset.'; $('#quality-details').hidden = true; renderTfSwitch(); return; }
    box.className = 'info-card';
    var synth = d.is_synthetic
      ? '<span class="pill pill-synth">DỮ LIỆU MÔ PHỎNG</span>'
      : '';
    box.innerHTML = '<div class="ds-summary">' + synth +
      '<strong>' + esc(d.symbol) + ' ' + esc(d.timeframe) + '</strong>' +
      '<span class="muted">' + d.row_count + ' nến</span></div>' +
      '<details class="ds-extra"><summary>Chi tiết nguồn</summary><dl>' +
      '<dt>Từ</dt><dd class="mono">' + fmtIso(d.start_time) + '</dd>' +
      '<dt>Đến</dt><dd class="mono">' + fmtIso(d.end_time) + '</dd>' +
      '<dt>Múi giờ nguồn</dt><dd>' + esc(d.source_timezone) + '</dd>' +
      '<dt>Timestamp</dt><dd>' + (d.timestamp_convention === 'open' ? 'mốc MỞ nến' : 'mốc ĐÓNG nến') + '</dd>' +
      '<dt>Loại giá</dt><dd>' + esc(d.price_type) + '</dd>' +
      '<dt>Nguồn</dt><dd>' + esc(d.source) + '</dd>' +
      '<dt>Checksum</dt><dd class="mono">' + esc(String(d.checksum_sha256).slice(0, 16)) + '…</dd>' +
      '</dl>' + (d.notes ? '<p class="hint">' + esc(d.notes) + '</p>' : '') + '</details>';
    renderQuality(d);
    renderTfSwitch();
  }

  function renderQuality(d) {
    var det = $('#quality-details');
    var q = d.quality || {};
    var issues = q.issues || [];
    det.hidden = false;
    var sev = issues.some(function (i) { return i.severity === 'error'; }) ? 'error'
            : issues.some(function (i) { return i.severity === 'warning'; }) ? 'cảnh báo' : 'sạch';
    det.querySelector('summary').textContent = 'Báo cáo kiểm tra dữ liệu (' + sev + ', ' + issues.length + ' mục)';
    var html = '<p class="hint">Đã nạp ' + (q.rows_out || 0) + '/' + (q.rows_in || 0) + ' dòng.' +
      (q.expected_bars ? ' Số vị trí nến lý thuyết trong khoảng: ' + q.expected_bars + '.' : '') + '</p>';
    if (!issues.length) html += '<p class="muted">Không phát hiện vấn đề.</p>';
    html += issues.map(function (i) {
      return '<div class="note note-' + (i.severity === 'error' ? 'error' : i.severity === 'warning' ? 'warn' : 'info') + '" style="margin-bottom:6px">' +
        '<code>' + esc(i.code) + '</code> — ' + esc(i.message_vi) + '</div>';
    }).join('');
    if (q.gap_note_vi) html += '<p class="hint">' + esc(q.gap_note_vi) + '</p>';
    $('#quality-body').innerHTML = html;
  }

  var TF_ORDER = ['M5', 'M15', 'M30', 'H1', 'H4'];
  var TF_SEC = { M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400 };

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

  function findFinerSource(symbol, targetTf, current) {
    var need = TF_SEC[targetTf];
    if (!need) return null;
    var cands = S.datasets.filter(function (d) {
      return d.symbol === symbol && TF_SEC[d.timeframe] && TF_SEC[d.timeframe] < need;
    });
    if (!cands.length) return null;
    cands.sort(function (a, b) {
      var aSyn = current && !!a.is_synthetic === !!current.is_synthetic ? 0 : 1;
      var bSyn = current && !!b.is_synthetic === !!current.is_synthetic ? 0 : 1;
      if (aSyn !== bSyn) return aSyn - bSyn;
      return TF_SEC[a.timeframe] - TF_SEC[b.timeframe];
    });
    return cands[0];
  }

  function renderTfSwitch() {
    var box = $('#tf-switch');
    var hint = $('#tf-hint');
    if (!box) return;
    if (!S.dataset) {
      box.innerHTML = '';
      if (hint) hint.hidden = true;
      return;
    }
    var cur = S.dataset;
    var srcSec = TF_SEC[cur.timeframe] || 0;
    box.innerHTML = TF_ORDER.map(function (tf) {
      var sib = findSiblingDataset(cur.symbol, tf, cur);
      var dstSec = TF_SEC[tf];
      var cls = 'tf-btn';
      var title = '';
      if (tf === cur.timeframe) {
        cls += ' active';
        title = 'Khung đang chọn';
      } else if (sib) {
        cls += ' available';
        title = 'Chuyển sang dataset ' + tf + ' cùng ' + cur.symbol;
      } else if (dstSec > srcSec) {
        cls += ' up';
        title = 'Tổng hợp từ ' + cur.timeframe + ' lên ' + tf;
      } else {
        cls += ' down';
        title = 'Không tách được ' + cur.timeframe + ' thành ' + tf + ' trừ khi đã có dataset ' + tf + ' cùng symbol.';
      }
      return '<button type="button" class="' + cls + '" data-tf="' + tf + '" title="' + esc(title) + '">' + tf + '</button>';
    }).join('');
    $$('#tf-switch [data-tf]').forEach(function (b) {
      b.addEventListener('click', function () { switchTimeframe(b.getAttribute('data-tf')); });
    });
    if (hint) {
      hint.hidden = false;
      hint.textContent = 'Xuống khung nhỏ hơn (H4→M5) chỉ được khi đã có dataset M5 cùng symbol — không tách nến lớn.';
    }
  }

  async function switchTimeframe(tf) {
    if (!S.dataset) return;
    tf = String(tf || '').toUpperCase();
    if (tf === S.dataset.timeframe) return;
    var sib = findSiblingDataset(S.dataset.symbol, tf, S.dataset);
    if (sib) {
      var fromTf = S.dataset.timeframe;
      $('#dataset-select').value = sib.id;
      await selectDataset(sib.id, { keepRange: true });
      banner('ok', 'Đã chuyển từ <strong>' + esc(fromTf) + '</strong> sang dataset <strong>' +
        esc(sib.symbol) + ' ' + esc(tf) + '</strong> (' + sib.row_count +
        ' nến). Đây là dữ liệu có sẵn — không tách nến ' + esc(fromTf) + ' thành ' + esc(tf) + '.');
      return;
    }
    var srcSec = TF_SEC[S.dataset.timeframe] || 0;
    var dstSec = TF_SEC[tf] || 0;
    if (dstSec > srcSec) {
      openResampleModal(tf);
      return;
    }
    var finer = findFinerSource(S.dataset.symbol, tf, S.dataset);
    if (finer) {
      try {
        loading(true);
        var out = await API.resample({
          dataset_id: finer.id,
          target_timeframe: tf,
          gap_policy: 'drop_incomplete'
        });
        await loadDatasets(out.dataset.id);
        banner('ok', 'Đã tạo khung <strong>' + esc(tf) + '</strong> bằng cách tổng hợp từ <strong>' +
          esc(finer.symbol) + ' ' + esc(finer.timeframe) + '</strong> (' + out.dataset.row_count + ' nến).');
      } catch (e) {
        banner('error', esc(e.message));
      } finally {
        loading(false);
      }
      return;
    }
    banner('error', 'Không tách được nến <strong>' + esc(S.dataset.timeframe) + '</strong> thành <strong>' +
      esc(tf) + '</strong>. Hãy chọn dataset ' + esc(tf) + ' cùng symbol (ví dụ dữ liệu mẫu XAUUSD M5) hoặc nhập CSV/MT5 khung nhỏ.');
  }

  // Dataset dài (vd M1 cả năm, M15 8 năm): chạy/vẽ toàn bộ tạo kết quả hàng trăm MB và hàng
  // trăm nghìn marker — trình duyệt có thể treo. Mặc định chỉ lấy ~DEFAULT_MAX_BARS nến gần nhất.
  var DEFAULT_MAX_BARS = 50000;
  var HEAVY_RUN_BARS = 100000;

  /** Ước lượng số nến trong khoảng đang chọn — theo tỷ lệ thời gian trên số nến của dataset. */
  function estimateRangeBars() {
    var d = S.dataset;
    if (!d || !d.row_count) return 0;
    var t0 = Date.parse(d.start_time), t1 = Date.parse(d.end_time);
    if (!(t1 > t0)) return d.row_count;
    var a = Date.parse(fromLocalInput($('#range-start').value) || d.start_time);
    var b = Date.parse(fromLocalInput($('#range-end').value) || d.end_time);
    var span = Math.max(0, Math.min(b, t1) - Math.max(a, t0));
    return Math.round(d.row_count * span / (t1 - t0));
  }

  function renderRangeHint() {
    var hint = $('#range-hint');
    if (!S.dataset || !S.dataset.row_count || S.dataset.row_count <= DEFAULT_MAX_BARS) { hint.hidden = true; return; }
    var est = estimateRangeBars();
    hint.hidden = false;
    hint.innerHTML = 'Dataset có <strong>' + S.dataset.row_count.toLocaleString('vi-VN') + '</strong> nến; khoảng đang chọn ~<strong>' +
      est.toLocaleString('vi-VN') + '</strong> nến.' + (est > HEAVY_RUN_BARS
        ? ' <strong>Rất nặng</strong> — kết quả có thể hàng trăm MB, trình duyệt có thể treo; nên thu hẹp khoảng.'
        : ' Mặc định chỉ lấy khoảng ' + DEFAULT_MAX_BARS.toLocaleString('vi-VN') + ' nến gần nhất cho nhẹ; sửa «Từ ngày» để chạy dài hơn.');
  }

  /** Khoảng mặc định: toàn bộ dataset, hoặc ~DEFAULT_MAX_BARS nến cuối nếu dataset dài. */
  function resetRangeInputs() {
    if (!S.dataset) { $('#range-start').value = ''; $('#range-end').value = ''; renderRangeHint(); return; }
    var start = S.dataset.start_time, n = S.dataset.row_count || 0;
    if (n > DEFAULT_MAX_BARS) {
      var t0 = Date.parse(S.dataset.start_time), t1 = Date.parse(S.dataset.end_time);
      start = new Date(t1 - (t1 - t0) * DEFAULT_MAX_BARS / n).toISOString();
      $('#range-details').open = true;
    }
    $('#range-start').value = toLocalInput(start);
    $('#range-end').value = toLocalInput(S.dataset.end_time);
    renderRangeHint();
  }

  /** Nút «Dùng toàn bộ khoảng dữ liệu»: đúng toàn bộ, kể cả dataset dài (gợi ý sẽ cảnh báo). */
  function useFullRange() {
    if (!S.dataset) return;
    $('#range-start').value = toLocalInput(S.dataset.start_time);
    $('#range-end').value = toLocalInput(S.dataset.end_time);
    renderRangeHint();
  }

  function confirmHeavyRange(action) {
    var est = estimateRangeBars();
    if (est <= HEAVY_RUN_BARS) return true;
    return window.confirm('Khoảng đang chọn có khoảng ' + est.toLocaleString('vi-VN') + ' nến. ' + action +
      ' trên khoảng này có thể tạo kết quả hàng trăm MB và làm trình duyệt chậm hoặc treo.\n\nVẫn tiếp tục?');
  }

  // ----------------------------------------------------------------- chạy thử

  async function doRun() {
    if (!S.dataset) return;
    if (!confirmHeavyRange('Chạy thuật toán')) return;
    await stopReplay();
    loading(true);
    banner(null);
    try {
      var payload = {
        dataset_id: S.dataset.id,
        algorithm: S.algo.name,
        params: collectParams(),
        range_start: fromLocalInput($('#range-start').value),
        range_end: fromLocalInput($('#range-end').value),
        label: $('#run-label').value,
        save: $('#run-save').checked
      };
      var res = await API.run(payload);
      var barsRes = await API.bars(S.dataset.id, payload.range_start, payload.range_end);
      S.allBars = barsRes.bars;
      S.digits = detectDigits(S.allBars);
      S.run = res;
      S.selectedEventId = null;
      if (S.baseline && (S.baseline.range_start !== res.range_start || S.baseline.range_end !== res.range_end ||
          S.baseline.dataset_id !== res.dataset_id)) S.baseline = null;
      renderEventDetail(null);

      S.chart.setDigits(S.digits);
      S.chart.setBars(S.allBars);
      applyChartEvents();
      S.chart.showLast(350);

      $('#chart-empty').hidden = true;
      $('#btn-export-csv').disabled = !res.saved;
      $('#btn-export-png').disabled = false;
      renderEvents(res.events);
      renderStats(res);
      renderAlgoNotes(res.algorithm, res.stats, res.data_status, res.pending_state);

      var nDcPivots = res.algorithm === 'dc_atr_structure'
        ? res.events.filter(function (e) { return e.structure_type === 'DC_HIGH' || e.structure_type === 'DC_LOW'; }).length
        : null;
      if (res.data_status !== 'OK') {
        banner('warn', esc(res.data_status_message_vi));
      } else if (nDcPivots === 0) {
        banner('warn', 'Chạy xong nhưng <strong>chưa có pivot DC nào được xác nhận</strong>. Dữ liệu vẫn hợp lệ — có thể ngưỡng quá lớn so với biên độ, hoặc mỗi segment (giữa hai gap) quá ngắn sau warm-up. Xem ghi chú phía trên.');
      } else if (!res.events.length) {
        banner('warn', 'Chạy xong nhưng <strong>không có sự kiện nào</strong>. Dữ liệu vẫn hợp lệ — hãy thử giảm số nến trái/phải hoặc mở rộng khoảng thời gian.');
      } else {
        banner('ok', 'Đã chạy <strong>' + res.bars_processed + '</strong> nến trong <strong>' +
          res.duration_ms.toFixed(1) + ' ms</strong>, phát hiện <strong>' + res.events.length + '</strong> sự kiện.' +
          (res.saved ? ' Lần chạy đã lưu: <code>' + esc(res.run_id) + '</code>.' : ' (không lưu).') +
          ' Chart đang hiển thị 350 nến cuối — cuộn hoặc zoom để xem phần còn lại.');
      }
      if (res.saved) await loadRuns();
    } catch (e) {
      banner('error', 'Chạy thất bại: ' + esc(e.message));
    } finally {
      loading(false);
    }
  }

  /**
   * Chạy swing_pivot 3/3 (tham số mặc định, không đổi) trên CÙNG dataset và khoảng
   * của run DC hiện tại rồi phủ pivot wick lên chart. Lưu run nếu đang bật «Lưu».
   */
  /** Nguồn để so baseline: phiên replay đang mở (nếu có) hoặc lần chạy đang hiển thị. */
  function baselineSource() {
    var r = S.replay;
    if (S.mode === 'replay' && r && r.snapshot && r.bars.length) {
      return {
        algorithm: r.snapshot.algorithm, dataset_id: r.snapshot.dataset.id,
        checksum: r.snapshot.dataset.checksum_sha256,
        range_start: r.bars[0].bar_time, range_end: r.bars[r.bars.length - 1].bar_time,
        events: r.events, label: 'replay', replay: true
      };
    }
    if (!S.run) return null;
    return {
      algorithm: S.run.algorithm, dataset_id: S.run.dataset_id, checksum: S.run.dataset_checksum,
      range_start: S.run.range_start, range_end: S.run.range_end, events: S.run.events,
      label: S.run.run_id || 'DC chưa lưu', replay: false
    };
  }

  async function runBaseline() {
    var src = baselineSource();
    if (!src || src.algorithm !== 'dc_atr_structure') {
      banner('warn', 'So sánh baseline cần một lần chạy hoặc phiên replay của <strong>dc_atr_structure</strong>. ' +
        'Chọn thuật toán «DC theo close + ATR» rồi bấm <strong>Chạy thử</strong> hoặc mở replay.');
      return;
    }
    loading(true);
    try {
      var base = await API.run({
        dataset_id: src.dataset_id, algorithm: 'swing_pivot', params: { left: 3, right: 3 },
        range_start: src.range_start, range_end: src.range_end,
        label: 'baseline pivot 3/3 — so với ' + src.label, save: $('#run-save').checked
      });
      if (base.dataset_checksum !== src.checksum) throw new Error('Checksum dataset khác nhau — không so sánh.');
      S.baseline = {
        run_id: base.saved ? base.run_id : null, events: base.events, dataset_id: base.dataset_id,
        range_start: base.range_start, range_end: base.range_end
      };
      S.layers.baseline = true;
      var cb = $('#dc-layers input[data-layer="baseline"]');
      if (cb) cb.checked = true;
      applyChartEvents();
      if (src.replay) renderAlgoNotes(src.algorithm, null, S.replay.snapshot.data_status, S.replay.snapshot.pending_state);
      else renderAlgoNotes(S.run.algorithm, S.run.stats, S.run.data_status, S.run.pending_state);
      var cnt = function (evs, a, b) { return evs.filter(function (e) { return e.structure_type === a || e.structure_type === b; }).length; };
      var lagMed = function (evs, a, b) {
        var xs = evs.filter(function (e) { return e.structure_type === a || e.structure_type === b; })
          .map(function (e) { return e.confirmation_lag_bars; }).sort(function (x, y) { return x - y; });
        return xs.length ? xs[Math.floor((xs.length - 1) / 2)] : '—';
      };
      banner('ok', 'Baseline swing_pivot v' + esc(base.algorithm_version) + ' (3/3, wick): <strong>' + cnt(base.events, 'SWING_HIGH', 'SWING_LOW') +
        '</strong> pivot trên cả khoảng, trễ trung vị ' + lagMed(base.events, 'SWING_HIGH', 'SWING_LOW') + ' nến · DC (close): <strong>' +
        cnt(src.events, 'DC_HIGH', 'DC_LOW') + '</strong> pivot' + (src.replay ? ' (tới con trỏ replay)' : '') +
        ', trễ trung vị ' + lagMed(src.events, 'DC_HIGH', 'DC_LOW') +
        (src.replay ? ' nến. Trong replay, baseline cũng chỉ hiện pivot đã xác nhận tới con trỏ.' : '') +
        ' nến. Cùng checksum <code>' + esc(String(base.dataset_checksum).slice(0, 12)) + '…</code> và khoảng thời gian.' +
        (base.saved ? ' Đã lưu <code>' + esc(base.run_id) + '</code> — chọn hai run ở tab Lịch sử để so sánh chi tiết.' : ''));
      if (base.saved) await loadRuns();
    } catch (e) {
      banner('error', 'Không chạy được baseline: ' + esc(e.message));
    } finally {
      loading(false);
    }
  }

  /**
   * Cảnh báo riêng c2_cisd_research, tách bạch: alignment, warm-up, thiếu dữ liệu,
   * không có setup. Thuật toán khác: ẩn.
   */
  function renderAlgoNotes(algorithm, stats, dataStatus, pending) {
    var box = $('#algo-notes');
    if (!box) return;
    if (algorithm === 'dc_atr_structure') { renderDcNotes(box, stats, dataStatus, pending); return; }
    if (algorithm !== 'c2_cisd_research') { box.hidden = true; box.innerHTML = ''; return; }
    var m = (stats && stats.chi_so_thuat_toan) || null;
    var notes = [];
    notes.push(['info', 'C2 + CISD (bản nghiên cứu closed-bar, <strong>chưa xác minh parity với Pine</strong>). ' +
      'Kỳ H4 theo <strong>mốc UTC epoch</strong> (00/04/08/12/16/20 UTC) — chưa đối chiếu với H4 của broker/TradingView. ' +
      'Marker C2 neo tại nến cực trị nhưng chỉ xuất hiện sau khi C2 đóng; đường mức chỉ bắt đầu từ nến sau lúc mức được biết.']);
    if (dataStatus === 'WARMUP_INSUFFICIENT') {
      notes.push(['warn', '<strong>Warm-up:</strong> cần ít nhất 2 kỳ H4 đủ nến (32 nến M15) trước khi có C1/C2 hợp lệ.']);
    }
    var gaps = m ? m.so_gap_ltf : (pending ? pending.so_gap_ltf : 0);
    var inc = m ? m.so_ky_htf_thieu_nen : (pending ? pending.so_ky_htf_thieu : 0);
    if (inc || gaps) {
      var killed = m && m.ket_thuc_theo_ly_do ? (m.ket_thuc_theo_ly_do.SETUP_LTF_GAP || 0) : null;
      notes.push(['warn', '<strong>Dữ liệu thiếu:</strong> ' + gaps + ' chỗ gap M15, ' + inc + ' kỳ H4 thiếu nến — không dùng làm C1/C2/C3/C4, không tự bù.' +
        (killed !== null ? ' <strong>' + killed + '</strong> setup dừng vì gap (không phải bị giá phá).' : '') +
        ' XAUUSD nghỉ phiên hằng ngày nên kỳ 20:00 UTC thường thiếu.']);
    }
    if (m && dataStatus === 'OK' && !m.tong_setup) {
      notes.push(['info', '<strong>Không có setup C2 nào</strong> trong khoảng này (dữ liệu vẫn hợp lệ). Đây không phải lỗi.']);
    }
    box.innerHTML = notes.map(function (n) {
      return '<div class="note note-compact note-' + n[0] + '">' + n[1] + '</div>';
    }).join('');
    box.hidden = false;
  }

  /** Ghi chú riêng dc_atr_structure: close vs wick, gap/segment, warm-up, UNKNOWN, nhãn, baseline. */
  function renderDcNotes(box, stats, dataStatus, pending) {
    var m = (stats && stats.chi_so_thuat_toan) || null;
    var ps = pending || {};
    var notes = [];
    notes.push(['info', '<strong>DC theo CLOSE</strong>: đỉnh/đáy là close của nến cực trị, xác nhận khi close đảo chiều ≥ Δ (k×ATR hoặc % khoá tại cực trị). ' +
      'Trend/Range là <strong>định nghĩa vận hành của lab</strong> (HH+HL, LH+LL, cụm đỉnh/đáy) — không phải dự báo hay tín hiệu giao dịch.']);
    if (S.dataset && S.dataset.is_synthetic) {
      notes.push(['warn', 'Dataset <strong>MÔ PHỎNG</strong> — số liệu chỉ để thử công cụ, không mô tả thị trường thật.']);
    }
    if (dataStatus === 'WARMUP_INSUFFICIENT') {
      notes.push(['warn', '<strong>Warm-up:</strong> cần ATR period + 1 nến liên tục trong MỖI segment trước khi detector khởi tạo.']);
    }
    var gaps = m ? m.so_gap : ps.so_gap;
    var segs = m ? m.so_segment : ps.so_segment;
    var bridged = m ? m.so_gap_noi : ps.so_gap_noi;
    var policy = (m && m.gap_policy) || ps.gap_policy || 'reset';
    if (policy === 'bridge_short') {
      var hrs = S.run && S.run.params ? S.run.params.bridge_max_gap_hours : '?';
      notes.push(['warn', '<strong>Gap dữ liệu (gap_policy=bridge_short, ≤ ' + esc(hrs) + ' giờ):</strong> ' + (bridged || 0) +
        ' gap ngắn được NỐI (giữ ứng viên, ATR, lịch sử; TR tính cả bước nhảy qua gap; marker «nối»), ' + (gaps || 0) +
        ' gap dài bị reset → ' + segs + ' segment. Nối là lựa chọn phương pháp, không phải dữ liệu liền mạch. Chưa dùng lịch phiên broker.']);
    } else if (gaps) {
      notes.push(['warn', '<strong>Gap dữ liệu:</strong> ' + gaps + ' gap → ' + segs + ' segment (gap_policy=reset). ' +
        'Mỗi gap — kể cả nghỉ phiên hằng ngày và cuối tuần — bỏ ứng viên, ATR, lịch sử trend/range và warm-up lại; không nối swing qua gap. ' +
        'Chưa suy đoán lịch phiên broker, nên mỗi phiên bắt đầu ở «Chưa rõ». Có thể thử gap_policy=bridge_short.']);
    }
    if (m && m.regime_ty_le_thoi_gian && m.regime_ty_le_thoi_gian.UNKNOWN !== null && m.regime_ty_le_thoi_gian.UNKNOWN > 0.5) {
      notes.push(['info', '«Chưa rõ» chiếm <strong>' + (m.regime_ty_le_thoi_gian.UNKNOWN * 100).toFixed(1) + '%</strong> thời gian sau warm-up: thiếu hoặc mâu thuẫn bằng chứng swing — không bị ép thành Range.']);
    }
    if (m && m.so_pivot_xac_nhan === 0) {
      notes.push(['warn', 'Không có pivot DC xác nhận. Không phải lỗi dữ liệu — thử giảm k hoặc dùng khoảng dài hơn.']);
    }
    if (S.baseline && S.layers.baseline) {
      notes.push(['warn', '<strong>So sánh baseline:</strong> pivot baseline (swing_pivot 3/3, run <code>' + esc(S.baseline.run_id || '(không lưu)') + '</code>) theo <strong>WICK</strong>, DC theo <strong>CLOSE</strong> — ' +
        'chênh giá marker là khác định nghĩa, không phải lỗi. Đây là so sánh trải nghiệm tổng thể (khác cả ngưỡng lẫn nguồn giá).']);
    }
    notes.push(['info', 'Chưa có nhãn tham chiếu cho swing close / đoạn regime — không hiển thị F1 hay confusion matrix.']);
    box.innerHTML = notes.map(function (n) {
      return '<div class="note note-compact note-' + n[0] + '">' + n[1] + '</div>';
    }).join('');
    box.hidden = false;
  }

  /** Baseline chỉ dùng được khi cùng chuỗi nến (bar_index tính từ đầu khoảng chạy). */
  function baselineMatches(bars) {
    if (!S.baseline || !bars || !bars.length) return false;
    return bars[0].bar_time === S.baseline.range_start && bars[bars.length - 1].bar_time === S.baseline.range_end;
  }

  /**
   * Panel thứ hai cho run baseline: cùng nến, cùng con trỏ replay; cuộn/zoom và
   * crosshair liên kết với chart chính (MarketChart.linkWith).
   */
  function renderSplit() {
    var want = $('#chk-split-baseline').checked && S.algo && S.algo.name === 'dc_atr_structure';
    var replay = S.mode === 'replay' && S.replay;
    var src = replay ? S.replay.bars : S.allBars;
    var ok = want && baselineMatches(src);
    $('#chart2-wrap').hidden = !ok;
    $('.main').classList.toggle('split', !!ok);
    if (!ok) {
      S.c2 = null;
      return;
    }
    if (!S.chart2) {
      S.chart2 = new window.MarketChart($('#chart2'), $('#chart2-tooltip'));
      S.chart2.setCompactPane();
      S.chart.linkWith(S.chart2);
    }
    var n = replay ? S.replay.cursor + 1 : src.length;
    var c2 = S.c2 || { src: null, n: -1 };
    S.chart2.setDigits(S.digits);
    if (c2.src === src && n === c2.n + 1 && n > 0) S.chart2.appendBar(src[n - 1]);
    else if (!(c2.src === src && n === c2.n)) S.chart2.setBars(src.slice(0, n));
    S.c2 = { src: src, n: n };
    S.chart2.setEvents(S.baseline.events, [], {
      layers: { swing: true, swing_l2: true, hhll: S.layers.dc_labels, eq: S.layers.dc_labels },
      markerAtConfirm: false, replayCursor: replay ? S.replay.cursor : null
    });
    S.chart.copyRangeTo(S.chart2);
  }

  function applyChartEvents() {
    var curBars = (S.mode === 'replay' && S.replay) ? S.replay.bars : S.allBars;
    var baseEvs = baselineMatches(curBars) ? S.baseline.events : [];
    if (S.mode === 'replay' && S.replay) {
      S.chart.setEvents(S.replay.events, S.replay.timeline, {
        layers: S.layers, markerAtConfirm: false, replayCursor: S.replay.cursor,
        baselineEvents: baseEvs, selectedEventId: S.selectedEventId
      });
    } else if (S.run) {
      S.chart.setEvents(S.run.events, S.run.timeline, {
        layers: S.layers, markerAtConfirm: $('#chk-confirm-position').checked, replayCursor: null,
        baselineEvents: baseEvs, selectedEventId: S.selectedEventId
      });
    }
    var tl = (S.mode === 'replay' && S.replay) ? S.replay.timeline : (S.run ? S.run.timeline : []);
    var isDc = !!(tl && tl.length && tl[0].dc_phase !== undefined);
    $('#btn-replay-here').hidden = !(S.mode === 'full' && S.run);
    $('#dc-legend').hidden = !isDc;
    $('#dc-compact-note').hidden = !(isDc && S.chart.isCompact());
    renderSplit();
    var legend = $('#chart-legend');
    if (!legend) return;
    var evs = (S.mode === 'replay' && S.replay) ? S.replay.events : (S.run ? S.run.events : []);
    var hasL2 = (evs || []).some(function (e) {
      return e.structure_type === 'SWING_HIGH_L2' || e.structure_type === 'SWING_LOW_L2';
    });
    legend.hidden = !hasL2;
  }

  /** Panel giải thích một sự kiện DC: công thức với số thực tế, tham chiếu, lúc biết. */
  function renderEventDetail(e) {
    var box = $('#event-detail');
    if (!box) return;
    if (!e || e.algorithm !== 'dc_atr_structure') { box.hidden = true; box.innerHTML = ''; return; }
    var x = e.details || {};
    var d = S.digits;
    var f = function (v) { return v === null || v === undefined ? '—' : Number(v).toFixed(d); };
    var TXT = window.chartUtils.REGIME_TEXT_VI;
    var rows = [];
    function row(k, v) { rows.push('<dt>' + esc(k) + '</dt><dd>' + v + '</dd>'); }
    row('Loại', esc(e.structure_type) + ' — ' + esc(e.structure_text_vi || ''));
    row('Nến sự kiện', '#' + e.event_bar_index + ' · ' + esc(fmtIso(e.event_time)));
    row('Biết lúc (confirmed_at)', '#' + e.confirmed_bar_index + ' · ' + esc(fmtIso(e.confirmed_at)) + ' · trễ ' + e.confirmation_lag_bars + ' nến');
    row('Segment', esc(x.segment));
    if (e.structure_type === 'DC_HIGH' || e.structure_type === 'DC_LOW') {
      row('Giá (theo close)', f(e.price) + ' — không phải ' + (e.structure_type === 'DC_HIGH' ? 'high' : 'low') + ' của nến');
      row('Ngưỡng khoá', esc(x.cong_thuc_nguong) + ' · đặt lúc ' + esc(fmtIso(x.threshold_set_at)));
      row('Điều kiện xác nhận', esc(x.dieu_kien_xac_nhan));
      row('Khoảng đảo chiều', f(x.reversal_distance) + ' = ' + Number(x.reversal_distance_atr).toFixed(2) + ' × ATR tại cực trị');
      row('Nhãn so sánh', x.nhan
        ? esc(x.nhan) + ': ' + f(x.nhan_gia_nay) + ' so với ' + f(x.nhan_gia_truoc) + ' (chênh ' + f(x.nhan_chenh_lech) + ', dung sai ±' + f(x.nhan_dung_sai) + ' = ' + esc(S.run && S.run.params ? S.run.params.label_tolerance_atr : '') + ' × ATR tại cực trị)'
        : 'Pivot đầu cùng loại trong segment — chưa so sánh');
      row('Tham chiếu', esc(e.reference_event_id || '—'));
      if (x.nhip) row('Nhịp từ pivot trước', f(x.nhip.bien_do) + ' = ' + Number(x.nhip.bien_do_atr).toFixed(2) + ' × ATR pivot đầu nhịp');
    } else if (e.structure_type === 'DC_GAP_BRIDGED') {
      row('Gap được nối', (x.khoang_cach_giay / 60) + ' phút (≤ ' + esc(x.bridge_max_gap_hours) + ' giờ) · không reset segment');
      row('Bước nhảy', 'open − close trước gap = ' + f(x.buoc_nhay_open) + ' (tính vào TR/ATR)');
      row('Ứng viên giữ nguyên', x.ung_vien_giu_nguyen ? f(x.ung_vien_giu_nguyen.candidate_price) + ' (nến #' + x.ung_vien_giu_nguyen.candidate_index + ')' : '—');
    } else if (e.structure_type === 'DC_SEGMENT_GAP') {
      row('Gap', (x.khoang_cach_giay / 60) + ' phút (' + Number(x.so_buoc_khung).toFixed(2) + ' bước khung)');
      row('Trước gap', 'nến #' + x.nen_truoc_gap + ' · trạng thái ' + esc(TXT[x.regime_truoc_gap] || x.regime_truoc_gap));
      row('Ứng viên bị bỏ', x.ung_vien_bi_bo ? f(x.ung_vien_bi_bo.candidate_price) + ' (nến #' + x.ung_vien_bi_bo.candidate_index + ')' : '—');
    } else {
      row('Chuyển trạng thái', esc(TXT[x.tu_trang_thai] || x.tu_trang_thai) + ' → <b>' + esc(TXT[x.sang_trang_thai] || x.sang_trang_thai) + '</b>');
      row('Giải thích', esc(x.giai_thich_vi || ''));
      if (x.bang_chung && x.bang_chung.length) row('Bằng chứng', esc(x.bang_chung.join(', ')));
      var rg = x.range || x.range_dong;
      if (rg) row(x.range ? 'Range' : 'Range vừa đóng', '[' + f(rg.lower) + ', ' + f(rg.upper) + '] · buffer ' + f(rg.buffer) + ' · ATR khoá ' + f(rg.atr_luc_vao) + ' · từ nến #' + rg.start_index);
      if (x.kiem_tra_range && !x.kiem_tra_range.dat) row('Range không đạt', esc(x.kiem_tra_range.ly_do_vi || ''));
      if (x.close_pha !== undefined) row('Close phá', f(x.close_pha) + ' vs ngưỡng ' + f(x.nguong_pha) + ' · xét lại từ nến #' + x.chi_xet_lai_tu_nen);
    }
    box.innerHTML = '<h4>Chi tiết sự kiện được chọn</h4><dl>' + rows.join('') + '</dl>';
    box.hidden = false;
  }

  // ----------------------------------------------------------------- bảng sự kiện

  function renderEvents(events) {
    var tbody = $('#events-table tbody');
    var filter = ($('#event-filter').value || '').trim().toUpperCase();
    var list = (events || []).filter(function (e) {
      var sid = ((e.details && (e.details.setup_id || e.details.candidate_id)) || '').toUpperCase();
      return !filter || e.structure_type.indexOf(filter) >= 0 || (e.reason_code || '').indexOf(filter) >= 0 ||
        sid.indexOf(filter) >= 0;
    });
    $('#event-count').textContent = list.length + ' / ' + (events || []).length + ' sự kiện';
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="empty-cell">' +
        ((events && events.length) ? 'Không có sự kiện khớp bộ lọc.' : 'Chưa có sự kiện.') + '</td></tr>';
      return;
    }
    var d = S.digits;
    tbody.innerHTML = list.slice(0, 3000).map(function (e, i) {
      return '<tr data-ev="' + i + '" tabindex="' + (i === 0 ? 0 : -1) + '" aria-selected="false">' +
        '<td class="num">' + (i + 1) + '</td>' +
        '<td><span class="badge b-' + esc(e.structure_type) + '">' + esc(e.structure_type) + '</span></td>' +
        '<td class="num">' + Number(e.price).toFixed(d) + '</td>' +
        '<td class="num">' + e.event_bar_index + '</td>' +
        '<td class="mono">' + fmtIso(e.event_time) + '</td>' +
        '<td class="num">' + e.confirmed_bar_index + '</td>' +
        '<td class="mono">' + fmtIso(e.confirmed_at) + '</td>' +
        '<td class="num">' + e.confirmation_lag_bars + '</td>' +
        '<td class="mono">' + esc(e.reason_code) + '</td>' +
        '<td class="mono">' + esc(e.reference_event_id || '—') +
          ((e.details && (e.details.setup_id || e.details.candidate_id))
            ? '<br><span class="muted">' + esc(e.details.setup_id ? 'setup ' + e.details.setup_id : 'ứng viên ' + e.details.candidate_id) + '</span>'
            : '') + '</td>' +
        '</tr>';
    }).join('');
    if (list.length > 3000) {
      tbody.innerHTML += '<tr><td colspan="10" class="empty-cell">Hiển thị 3000 dòng đầu; xuất CSV để xem đầy đủ.</td></tr>';
    }
    Array.prototype.forEach.call(tbody.querySelectorAll('tr[data-ev]'), function (tr) {
      tr.addEventListener('click', function () {
        Array.prototype.forEach.call(tbody.querySelectorAll('tr'), function (r) {
          r.classList.remove('selected');
          if (r.hasAttribute('data-ev')) { r.setAttribute('tabindex', '-1'); r.setAttribute('aria-selected', 'false'); }
        });
        tr.classList.add('selected');
        tr.setAttribute('tabindex', '0');
        tr.setAttribute('aria-selected', 'true');
        var ev = list[parseInt(tr.getAttribute('data-ev'), 10)];
        renderEventDetail(ev);
        if (ev.algorithm === 'dc_atr_structure') {
          S.selectedEventId = ev.event_id;   // hiện điểm xác nhận của pivot đang chọn
          applyChartEvents();
        }
        S.chart.focusEvent(ev);
      });
    });
  }

  function renderStats(res) {
    var st = res.stats || {};
    var byType = st.so_su_kien_theo_loai || {};
    var lag = st.do_tre_xac_nhan_theo_loai_nen || {};
    var html = '<div class="stat-grid">' +
      box('Tổng sự kiện', st.tong_su_kien || 0) +
      box('Nến đã xử lý', st.so_nen_xu_ly || 0) +
      box('Warm-up (nến)', res.warmup_bars) +
      box('Thời gian tính (ms)', (st.thoi_gian_tinh_toan_ms || 0).toFixed(2)) +
      box('Tốc độ (nến/giây)', st.toc_do_nen_tren_giay || '—') +
      box('Trễ xác nhận TB (nến)', st.do_tre_xac_nhan_chung_nen ? st.do_tre_xac_nhan_chung_nen.trung_binh : '—') +
      '</div>';

    html += '<div class="section-title">Số sự kiện và độ trễ xác nhận theo loại</div>';
    html += '<table class="data-table"><thead><tr><th>Loại</th><th>Số sự kiện</th>' +
            '<th>Trễ min</th><th>Trễ TB</th><th>Trễ trung vị</th><th>Trễ max</th></tr></thead><tbody>';
    var keys = Object.keys(byType).sort();
    if (!keys.length) html += '<tr><td colspan="6" class="empty-cell">Không có sự kiện.</td></tr>';
    keys.forEach(function (k) {
      var l = lag[k] || {};
      html += '<tr><td><span class="badge b-' + esc(k) + '">' + esc(k) + '</span></td>' +
        '<td class="num">' + byType[k] + '</td>' +
        '<td class="num">' + (l.min !== undefined ? l.min : '—') + '</td>' +
        '<td class="num">' + (l.trung_binh !== undefined ? l.trung_binh : '—') + '</td>' +
        '<td class="num">' + (l.trung_vi !== undefined ? l.trung_vi : '—') + '</td>' +
        '<td class="num">' + (l.max !== undefined ? l.max : '—') + '</td></tr>';
    });
    html += '</tbody></table>';

    html += '<div class="section-title">Hồ sơ lần chạy</div>';
    html += '<div class="info-card"><dl>' +
      '<dt>run_id</dt><dd class="mono">' + esc(res.run_id) + '</dd>' +
      '<dt>Thuật toán</dt><dd>' + esc(res.algorithm) + ' v' + esc(res.algorithm_version) + '</dd>' +
      '<dt>Tham số</dt><dd class="mono">' + esc(JSON.stringify(res.params)) + '</dd>' +
      '<dt>Dataset</dt><dd>' + esc(res.dataset_name || res.dataset_id) + (res.is_synthetic ? ' <span class="pill pill-synth">MÔ PHỎNG</span>' : '') + '</dd>' +
      '<dt>Dataset checksum</dt><dd class="mono">' + esc(res.dataset_checksum) + '</dd>' +
      '<dt>Khoảng chạy</dt><dd class="mono">' + fmtIso(res.range_start) + ' → ' + fmtIso(res.range_end) + '</dd>' +
      '<dt>Chạy lúc</dt><dd class="mono">' + fmtIso(res.created_at) + '</dd>' +
      '</dl></div>';
    html += '<p class="hint">' + esc(st.ghi_chu_vi || '') + '</p>';
    if (st.chi_so_thuat_toan && res.algorithm === 'c2_cisd_research') html = c2StatsHtml(st.chi_so_thuat_toan, res) + html;
    if (st.chi_so_thuat_toan && res.algorithm === 'dc_atr_structure') html = dcStatsHtml(st.chi_so_thuat_toan, res) + html;
    $('#stats-body').innerHTML = '<p class="hint">F1, P90 và so sánh nhiều cấu hình: <a href="/danh-gia">Đánh giá thuật toán</a>.</p>' + html;
    var mb = $('#c2-mfe-btn');
    if (mb) mb.addEventListener('click', function () { loadC2Excursion(res.run_id); });

    function box(k, v) {
      return '<div class="stat-box"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }
  }

  /** Metric không cần nhãn của dc_atr_structure — mô tả hành vi, không phải accuracy. */
  function dcStatsHtml(m, res) {
    function box(k, v, title) {
      return '<div class="stat-box"' + (title ? ' title="' + esc(title) + '"' : '') + '><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }
    function num(x, dg) { return x === null || x === undefined ? '—' : Number(x).toFixed(dg === undefined ? 2 : dg); }
    function sm(s, dg) { return s && s.n ? num(s.trung_vi, dg) + ' / ' + num(s.p90, dg) + ' (n=' + s.n + ')' : '—'; }
    var TXT = window.chartUtils.REGIME_TEXT_VI, COL = window.chartUtils.REGIME_COLORS;
    var share = m.regime_ty_le_thoi_gian || {};
    var html = '<div class="section-title">DC + regime (không cần nhãn — mô tả hành vi, không phải accuracy)</div>';
    html += '<div class="stat-grid">' +
      box('Pivot xác nhận', m.so_pivot_xac_nhan + ' (' + m.so_dinh + ' đỉnh / ' + m.so_day + ' đáy)') +
      box('Mật độ / 1.000 nến', num(m.mat_do_tren_1000_nen, 1), m.mat_do_ghi_chu_vi) +
      box('Trễ xác nhận (nến) TV / P90', sm(m.do_tre_nen, 1)) +
      box('Trễ (phút) TV / P90', sm(m.do_tre_phut, 0)) +
      box('Đảo chiều / ATR cực trị TV / P90', sm(m.reversal_distance_atr), m.reversal_ghi_chu_vi) +
      box('Biên độ nhịp / ATR TV / P90', sm(m.bien_do_nhip_atr), m.bien_do_ghi_chu_vi) +
      box('Lần chuyển trạng thái', m.so_lan_chuyen_trang_thai) +
      box('Độ dài đoạn TV (nến)', num(m.do_dai_doan_trung_vi_tat_ca, 0)) +
      box('Gap reset / nối / segment', m.so_gap + ' / ' + (m.so_gap_noi || 0) + ' / ' + m.so_segment, 'gap_policy=' + (m.gap_policy || 'reset')) +
      box('Nến đủ điều kiện / tổng', m.so_nen_du_dieu_kien + ' / ' + m.so_nen) +
      '</div>';
    html += '<div class="section-title">Tỷ lệ thời gian theo trạng thái (sau warm-up, không tính gap)</div>';
    html += '<div class="regime-share" role="img" aria-label="Tỷ lệ thời gian theo trạng thái">';
    ['UPTREND', 'DOWNTREND', 'RANGE', 'UNKNOWN'].forEach(function (k) {
      var v = share[k] || 0;
      if (v > 0) html += '<span style="width:' + (v * 100).toFixed(2) + '%;background:' + COL[k] + '" title="' + esc(TXT[k]) + ' ' + (v * 100).toFixed(1) + '%"></span>';
    });
    html += '</div><table class="data-table"><thead><tr><th>Trạng thái</th><th>Số nến</th><th>Tỷ lệ</th><th>Độ dài đoạn TV (nến)</th></tr></thead><tbody>';
    ['UPTREND', 'DOWNTREND', 'RANGE', 'UNKNOWN'].forEach(function (k) {
      html += '<tr><td>' + esc(TXT[k]) + '</td><td class="num">' + ((m.regime_so_nen || {})[k] || 0) + '</td>' +
        '<td class="num">' + (share[k] === null || share[k] === undefined ? '—' : (share[k] * 100).toFixed(1) + '%') + '</td>' +
        '<td class="num">' + num((m.do_dai_doan_trung_vi_nen || {})[k], 0) + '</td></tr>';
    });
    html += '</tbody></table>';
    var labs = m.nhan_so_sanh || {};
    html += '<p class="hint">Nhãn swing: ' + Object.keys(labs).sort().map(function (k) { return esc(k) + ' ' + labs[k]; }).join(' · ') + '</p>';
    html += '<p class="hint">' + esc((m.nhan_tham_chieu || {}).ghi_chu_vi || '') + ' ' + esc(m.ghi_chu_vi || '') + '</p>';
    return html;
  }

  function c2StatsHtml(m, res) {
    function box(k, v) {
      return '<div class="stat-box"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }
    function pct(x) { return x === null || x === undefined ? '—' : (x * 100).toFixed(1) + '%'; }
    function sm(x) { return x ? x.trung_vi + ' / ' + x.trung_binh + ' (n=' + x.n + ')' : '—'; }
    var r = m.ty_le_co_cisd || {};
    var ea = m.early_cisd || {};
    var html = '<div class="section-title">C2 + CISD — vòng đời setup</div>';
    html += '<div class="stat-grid">' +
      box('Setup C2 (↑ / ↓)', m.tong_setup + ' (' + m.so_c2_theo_huong.up + ' / ' + m.so_c2_theo_huong.down + ')') +
      box('C2 outside bar (cả hai hướng)', m.so_c2_outside_bar) +
      box('Có CISD / mọi setup', pct(r.tren_moi_setup) + ' (mẫu ' + r.mau_so_moi_setup + ')') +
      box('Có CISD / setup đã kết thúc', pct(r.tren_setup_da_ket_thuc) + ' (mẫu ' + r.mau_so_da_ket_thuc + ')') +
      box('CISD theo pha C2(early)/C3/C4', m.so_cisd_theo_pha.C2 + ' / ' + m.so_cisd_theo_pha.C3 + ' / ' + m.so_cisd_theo_pha.C4) +
      box('Trễ CISD sau C2 (trung vị / TB, nến)', sm(m.do_tre_cisd_sau_c2_nen)) +
      box('Early: nến bằng chứng trước cuối C2', sm(ea.so_nen_bang_chung_truoc_cuoi_c2)) +
      box('Early ứng viên không thành C2', ea.so_ung_vien_khong_thanh_c2 + ' / ' + ea.so_su_kien_early_ung_vien) +
      box('Censored (còn mở khi hết dữ liệu)', m.censored_dang_mo) +
      box('C4 không hợp lệ (chưa kết thúc)', m.so_c4_khong_hop_le_chua_ket_thuc) +
      box('Gap M15 / kỳ H4 thiếu', m.so_gap_ltf + ' / ' + m.so_ky_htf_thieu_nen) +
      '</div>';
    html += '<table class="data-table"><thead><tr><th>Kết thúc theo lý do</th><th>Số setup</th></tr></thead><tbody>';
    var ks = Object.keys(m.ket_thuc_theo_ly_do_vi || {});
    if (!ks.length) html += '<tr><td colspan="2" class="empty-cell">Chưa setup nào kết thúc.</td></tr>';
    ks.forEach(function (k) { html += '<tr><td>' + esc(k) + '</td><td class="num">' + m.ket_thuc_theo_ly_do_vi[k] + '</td></tr>'; });
    html += '<tr><td><em>Censored — chưa kết thúc (không tính thất bại)</em></td><td class="num">' + m.censored_dang_mo + '</td></tr>';
    html += '</tbody></table>';
    html += '<p class="hint">' + esc(r.ghi_chu_vi || '') + ' ' + esc(ea.ghi_chu_vi || '') + ' ' + esc(m.ghi_chu_vi || '') + '</p>';
    html += '<div class="section-title">Đối chứng C2-only vs C2+CISD (MFE/MAE, chỉ để đánh giá)</div>';
    if (res.run_id && res.saved) {
      html += '<div class="c2-metric-ctl"><label>Horizon (nến M15) <input type="number" id="c2-horizon" min="1" max="500" value="16"></label>' +
        '<button id="c2-mfe-btn" class="btn btn-secondary btn-sm" type="button">Tính MFE/MAE</button></div>' +
        '<div id="c2-mfe-body" class="hint">Dùng nến SAU lúc biết trong horizon cố định; mẫu thiếu horizon bị bỏ và được đếm. Không phải win rate hay P&amp;L.</div>';
    } else {
      html += '<p class="hint">Lưu lần chạy để tính MFE/MAE trên đúng snapshot dữ liệu.</p>';
    }
    return html;
  }

  async function loadC2Excursion(runId) {
    var body = $('#c2-mfe-body');
    var h = parseInt(($('#c2-horizon') || {}).value, 10) || 16;
    body.textContent = 'Đang tính…';
    try {
      var r = await API.c2CisdMetrics(runId, h);
      var x = r.mfe_mae;
      var rows = '';
      [['c2_only', 'C2-only (neo lúc C2 đóng)'], ['c2_cisd', 'C2+CISD (neo lúc CISD được biết)']].forEach(function (g) {
        ['up', 'down', 'tat_ca'].forEach(function (d) {
          var c = x[g[0]][d];
          var f = function (s) { return s ? s.trung_vi + ' / ' + s.trung_binh : '—'; };
          rows += '<tr><td>' + esc(g[1]) + '</td><td>' + (d === 'tat_ca' ? 'tất cả' : d) + '</td>' +
            '<td class="num">' + c.so_mau + '</td><td class="num">' + c.so_mau_bo_thieu_horizon + '</td>' +
            '<td class="num">' + f(c.mfe) + '</td><td class="num">' + f(c.mae) + '</td>' +
            '<td class="num">' + c.so_mau_mfe_lon_hon_mae + '</td></tr>';
        });
      });
      body.innerHTML = '<table class="data-table"><thead><tr><th>Nhóm</th><th>Hướng</th><th>Mẫu</th><th>Bỏ (thiếu horizon)</th>' +
        '<th>MFE trung vị / TB</th><th>MAE trung vị / TB</th><th>Số mẫu MFE &gt; MAE</th></tr></thead><tbody>' + rows +
        '</tbody></table><p class="hint">Horizon ' + x.horizon_nen + ' nến. ' + esc(x.ghi_chu_vi) + '</p>';
    } catch (e) {
      body.innerHTML = '<span class="note note-error">' + esc(e.message) + '</span>';
    }
  }

  // ----------------------------------------------------------------- lịch sử chạy

  async function loadRuns() {
    var onlyCurrent = $('#chk-history-current-ds').checked && S.dataset;
    S.runs = await API.runs(onlyCurrent ? S.dataset.id : null);
    renderRuns();
  }

  function renderRuns() {
    var tbody = $('#runs-table tbody');
    if (!S.runs.length) {
      tbody.innerHTML = '<tr><td colspan="12" class="empty-cell">Chưa có lần chạy nào được lưu.</td></tr>';
      $('#btn-compare').disabled = true;
      return;
    }
    tbody.innerHTML = S.runs.map(function (r) {
      var n = (r.stats && r.stats.tong_su_kien) || 0;
      return '<tr data-run="' + esc(r.run_id) + '">' +
        '<td><input type="checkbox" class="run-pick" data-run="' + esc(r.run_id) + '"></td>' +
        '<td class="mono">' + esc(r.run_id) + '</td>' +
        '<td>' + esc(r.label || '—') + '</td>' +
        '<td>' + esc(r.dataset_name || r.dataset_id) + (r.is_synthetic ? ' <span class="pill pill-synth">MP</span>' : '') + '</td>' +
        '<td>' + esc(r.symbol) + '</td><td>' + esc(r.timeframe) + '</td>' +
        '<td>' + esc(r.algorithm) + ' v' + esc(r.algorithm_version) + '</td>' +
        '<td class="mono">' + esc(JSON.stringify(r.params)) + '</td>' +
        '<td class="num">' + n + '</td>' +
        '<td class="num">' + r.duration_ms.toFixed(1) + ' ms</td>' +
        '<td class="mono">' + fmtIso(r.created_at) + '</td>' +
        '<td><button class="btn btn-sm" data-open="' + esc(r.run_id) + '">Mở lại</button> ' +
        '<button class="btn btn-sm" data-del="' + esc(r.run_id) + '">Xoá</button></td>' +
        '</tr>';
    }).join('');

    $$('#runs-table .run-pick').forEach(function (cb) {
      cb.addEventListener('change', function () {
        S.selectedRuns = $$('#runs-table .run-pick:checked').map(function (c) { return c.getAttribute('data-run'); });
        $('#btn-compare').disabled = S.selectedRuns.length !== 2;
      });
    });
    $$('#runs-table [data-open]').forEach(function (b) {
      b.addEventListener('click', function (ev) { ev.stopPropagation(); openRun(b.getAttribute('data-open')); });
    });
    $$('#runs-table [data-del]').forEach(function (b) {
      b.addEventListener('click', async function (ev) {
        ev.stopPropagation();
        if (!confirm('Xoá lần chạy ' + b.getAttribute('data-del') + '?')) return;
        await API.deleteRun(b.getAttribute('data-del'));
        await loadRuns();
      });
    });
  }

  /** Mở lại một lần chạy đã lưu và đồng thời kiểm tra tính tái lập. */
  async function openRun(runId) {
    loading(true);
    try {
      await stopReplay();
      var saved = await API.getRun(runId);
      if (S.dataset && S.dataset.id !== saved.dataset_id) {
        var ds = S.datasets.filter(function (d) { return d.id === saved.dataset_id; })[0];
        if (!ds) throw new Error('Dataset của lần chạy này đã bị xoá, không mở lại được chart.');
        $('#dataset-select').value = ds.id;
        S.dataset = ds;
        renderDatasetInfo();
      }
      $('#range-start').value = toLocalInput(saved.range_start);
      $('#range-end').value = toLocalInput(saved.range_end);
      selectAlgorithm(saved.algorithm);
      Object.keys(saved.params || {}).forEach(function (k) {
        var el = $('#param-' + k);
        if (!el) return;
        if (el.type === 'checkbox') el.checked = !!saved.params[k];
        else el.value = saved.params[k];
      });
      applyParamVisibility();
      S.baseline = null;
      S.selectedEventId = null;
      renderEventDetail(null);
      $('#run-label').value = saved.label || '';

      // Chạy lại đúng cấu hình để lấy chuỗi mức swing cho chart, đồng thời
      // đối chiếu với kết quả đã lưu -> kiểm tra tái lập.
      var fresh = await API.run({
        dataset_id: saved.dataset_id, algorithm: saved.algorithm, params: saved.params,
        range_start: saved.range_start, range_end: saved.range_end, save: false
      });
      var barsRes = await API.bars(saved.dataset_id, saved.range_start, saved.range_end);
      S.allBars = barsRes.bars;
      S.digits = detectDigits(S.allBars);
      S.run = fresh;
      S.run.run_id = saved.run_id;
      S.chart.setDigits(S.digits);
      S.chart.setBars(S.allBars);
      applyChartEvents();
      S.chart.showLast(350);
      $('#chart-empty').hidden = true;
      $('#btn-export-csv').disabled = false;
      $('#btn-export-png').disabled = false;
      renderEvents(fresh.events);
      renderStats(Object.assign({}, fresh, { run_id: saved.run_id, created_at: saved.created_at, saved: true }));
      renderAlgoNotes(fresh.algorithm, fresh.stats, fresh.data_status, fresh.pending_state);
      $('#synthetic-watermark').hidden = !saved.is_synthetic;

      var same = (saved.events || []).length === fresh.events.length &&
        (saved.events || []).every(function (e, i) {
          var f = fresh.events[i];
          return f && e.event_id === f.event_id && Math.abs(e.price - f.price) < 1e-9 &&
                 e.confirmed_bar_index === f.confirmed_bar_index;
        });
      banner(same ? 'ok' : 'warn',
        same
          ? 'Đã mở lại <code>' + esc(runId) + '</code>. <strong>Kiểm tra tái lập: khớp hoàn toàn</strong> — chạy lại cùng dataset và tham số cho đúng ' + fresh.events.length + ' sự kiện như bản đã lưu.'
          : 'Đã mở lại <code>' + esc(runId) + '</code> nhưng <strong>kết quả chạy lại KHÁC bản đã lưu</strong> (' + (saved.events || []).length + ' so với ' + fresh.events.length + ' sự kiện). Kiểm tra xem dataset hoặc phiên bản thuật toán có thay đổi không.');
    } catch (e) {
      banner('error', 'Không mở lại được lần chạy: ' + esc(e.message));
    } finally {
      loading(false);
    }
  }

  // ----------------------------------------------------------------- so sánh

  async function doCompare() {
    if (S.selectedRuns.length !== 2) return;
    try {
      var c = await API.compare(S.selectedRuns[0], S.selectedRuns[1]);
      $$('.tab').forEach(function (t) { t.classList.toggle('active', t.getAttribute('data-tab') === 'compare'); });
      $$('.tab-panel').forEach(function (p) { p.classList.toggle('active', p.getAttribute('data-panel') === 'compare'); });

      var html = '';
      if (c.canh_bao.length) {
        html += c.canh_bao.map(function (w) { return '<div class="note note-warn" style="margin-bottom:6px">' + esc(w) + '</div>'; }).join('');
      } else {
        html += '<div class="note note-ok" style="margin-bottom:8px">Hai lần chạy dùng cùng dataset, cùng khoảng thời gian và cùng phiên bản thuật toán — khác biệt đến từ tham số.</div>';
      }

      html += '<table class="data-table"><thead><tr><th></th><th>A</th><th>B</th></tr></thead><tbody>' +
        row('run_id', c.run_a.run_id, c.run_b.run_id) +
        row('Nhãn', c.run_a.label || '—', c.run_b.label || '—') +
        row('Thuật toán', c.run_a.algorithm + ' v' + c.run_a.algorithm_version, c.run_b.algorithm + ' v' + c.run_b.algorithm_version) +
        row('Tham số', JSON.stringify(c.run_a.params), JSON.stringify(c.run_b.params)) +
        row('Dataset', c.run_a.dataset_name || c.run_a.dataset_id, c.run_b.dataset_name || c.run_b.dataset_id) +
        row('Khoảng', fmtIso(c.run_a.range_start) + ' → ' + fmtIso(c.run_a.range_end), fmtIso(c.run_b.range_start) + ' → ' + fmtIso(c.run_b.range_end)) +
        row('Nến xử lý', c.run_a.bars_processed, c.run_b.bars_processed) +
        row('Warm-up (nến)', c.run_a.warmup_bars, c.run_b.warmup_bars) +
        row('Thời gian tính (ms)', c.thoi_gian_tinh_toan_ms.a.toFixed(2), c.thoi_gian_tinh_toan_ms.b.toFixed(2)) +
        row('Trễ xác nhận TB (nến)', c.do_tre_a ? c.do_tre_a.trung_binh : '—', c.do_tre_b ? c.do_tre_b.trung_binh : '—') +
        row('Trễ xác nhận max (nến)', c.do_tre_a ? c.do_tre_a.max : '—', c.do_tre_b ? c.do_tre_b.max : '—') +
        '</tbody></table>';

      html += '<div class="section-title">Số sự kiện theo loại</div>';
      html += '<table class="data-table"><thead><tr><th>Loại</th><th>A</th><th>B</th><th>Chênh lệch</th></tr></thead><tbody>';
      c.so_sanh_theo_loai.forEach(function (r) {
        var diff = r.b - r.a;
        html += '<tr><td><span class="badge b-' + esc(r.structure_type) + '">' + esc(r.structure_type) + '</span></td>' +
          '<td class="num">' + r.a + '</td><td class="num">' + r.b + '</td>' +
          '<td class="num">' + (diff > 0 ? '+' : '') + diff + '</td></tr>';
      });
      html += '</tbody></table>';

      html += '<div class="section-title">Trùng khớp sự kiện (khoá: loại + nến sự kiện + nến xác nhận)</div>';
      html += '<div class="stat-grid">' +
        '<div class="stat-box"><div class="k">Chung cả hai</div><div class="v">' + c.so_su_kien_chung + '</div></div>' +
        '<div class="stat-box"><div class="k">Chỉ có ở A</div><div class="v">' + c.chi_co_o_a + '</div></div>' +
        '<div class="stat-box"><div class="k">Chỉ có ở B</div><div class="v">' + c.chi_co_o_b + '</div></div>' +
        '</div>';
      html += '<p class="hint">' + esc(c.ghi_chu_vi) + '</p>';
      $('#compare-body').innerHTML = html;

      function row(k, a, b) {
        return '<tr><td>' + esc(k) + '</td><td class="mono">' + esc(a) + '</td><td class="mono">' + esc(b) + '</td></tr>';
      }
    } catch (e) {
      $('#compare-body').innerHTML = '<div class="note note-error">' + esc(e.message) + '</div>';
    }
  }

  // ----------------------------------------------------------------- replay

  /**
   * cfg (tuỳ chọn): { dataset_id, algorithm, params, range_start, range_end, seekTo }.
   * Không truyền = dùng form (hành vi cũ). «Replay từ vùng đang xem» truyền cấu
   * hình của run đang hiển thị và seekTo = nến đầu vùng nhìn.
   */
  async function enterReplay(cfg) {
    if (!S.dataset) { banner('warn', 'Chọn dataset trước khi replay.'); switchMode('full'); return; }
    if (!cfg && !confirmHeavyRange('Replay')) { switchMode('full'); return; }
    cfg = cfg || {};
    loading(true);
    try {
      var snap = await API.replayCreate({
        dataset_id: cfg.dataset_id || S.dataset.id,
        algorithm: cfg.algorithm || S.algo.name,
        params: cfg.params || collectParams(),
        range_start: cfg.range_start !== undefined ? cfg.range_start : fromLocalInput($('#range-start').value),
        range_end: cfg.range_end !== undefined ? cfg.range_end : fromLocalInput($('#range-end').value)
      });
      var barsRes = await API.replayBars(snap.session_id);
      S.replay = {
        sid: snap.session_id,
        bars: barsRes.bars,
        cursor: snap.cursor,
        events: snap.events,
        timeline: snap.timeline,
        snapshot: snap,
        playing: false,
        timer: null,
        renderedCursor: -2,
        prev: null,
        renderedEvents: -1
      };
      S.digits = detectDigits(barsRes.bars);
      S.chart.setDigits(S.digits);
      $('#rp-slider').min = -1;
      $('#rp-slider').max = String(barsRes.bars.length - 1);
      $('#rp-slider').value = String(snap.cursor);
      $('#chart-empty').hidden = true;
      $('#btn-export-png').disabled = false;
      $('#btn-export-csv').disabled = true;
      if (cfg.seekTo !== undefined && cfg.seekTo >= 0) {
        await replayAction(function (sid, since) { return API.replaySeek(sid, cfg.seekTo, since); });
      } else {
        renderReplay();
      }
      banner(null);
    } catch (e) {
      banner('error', 'Không tạo được phiên replay: ' + esc(e.message));
      switchMode('full');
    } finally {
      loading(false);
    }
  }

  function renderReplay() {
    var r = S.replay;
    if (!r) return;
    var visible = r.bars.slice(0, r.cursor + 1);
    if (r.renderedCursor === r.cursor - 1 && r.cursor >= 0) {
      S.chart.appendBar(r.bars[r.cursor]);
    } else {
      S.chart.setBars(visible);
    }
    if (visible.length) S.chart.followReplay();
    r.renderedCursor = r.cursor;
    applyChartEvents();

    $('#rp-slider').value = String(r.cursor);
    var bar = r.cursor >= 0 ? r.bars[r.cursor] : null;
    $('#rp-position').textContent = (r.cursor + 1) + ' / ' + r.bars.length;
    $('#rp-position').title = bar ? fmtIso(bar.close_time) : 'Chưa nạp nến';

    var lastId = r.events.length ? r.events[r.events.length - 1].event_id : '';
    if (r.renderedEvents !== r.events.length || r.renderedLastId !== lastId) {
      renderEvents(r.events);
      r.renderedEvents = r.events.length;
      r.renderedLastId = lastId;
    }
    renderExplain();
    var s = r.snapshot || {};
    var warmupEl = $('#rp-warmup');
    var warmupNeed = s.warmup_bars || 0;
    var skipBtn = $('#rp-skip-warmup');
    if (s.data_status === 'WARMUP_INSUFFICIENT') {
      warmupEl.hidden = false;
      warmupEl.textContent = 'Warm-up ' + Math.max(0, r.cursor + 1) + '/' + warmupNeed;
      warmupEl.title = s.data_status_message_vi || '';
      if (S.mode === 'replay') banner(null);
    } else {
      warmupEl.hidden = true;
    }
    if (skipBtn) skipBtn.disabled = !warmupNeed || r.cursor >= warmupNeed - 1;
    if (s.data_status && s.data_status !== 'OK' && s.data_status !== 'WARMUP_INSUFFICIENT') {
      banner('warn', esc(s.data_status_message_vi));
    }
    renderReplayStats();
    renderAlgoNotes(s.algorithm, null, s.data_status, s.pending_state);
  }

  function renderReplayStats() {
    var r = S.replay;
    if (!r) return;
    var byType = {};
    r.events.forEach(function (e) { byType[e.structure_type] = (byType[e.structure_type] || 0) + 1; });
    var ps = (r.snapshot && r.snapshot.pending_state) || {};
    var html = '<div class="note note-info" style="margin-bottom:10px">Thống kê trong chế độ replay được tính trên phần dữ liệu ĐÃ NẠP, không phải toàn bộ dataset.</div>';
    html += '<div class="stat-grid">' +
      '<div class="stat-box"><div class="k">Nến đã nạp</div><div class="v">' + (r.cursor + 1) + '</div></div>' +
      '<div class="stat-box"><div class="k">Tổng nến</div><div class="v">' + r.bars.length + '</div></div>' +
      '<div class="stat-box"><div class="k">Sự kiện đã xác nhận</div><div class="v">' + r.events.length + '</div></div>' +
      '<div class="stat-box"><div class="k">Warm-up (nến)</div><div class="v">' + ((r.snapshot && r.snapshot.warmup_bars) || '—') + '</div></div>' +
      '</div>';
    html += '<div class="section-title">Trạng thái nội bộ thuật toán tại nến hiện tại</div>';
    if (ps.setup_dang_mo) {
      html += c2PendingHtml(ps);
    } else if (ps.dc) {
      html += dcPendingHtml(ps);
    } else html += '<div class="info-card"><dl>' +
      '<dt>Mức swing high đang hoạt động</dt><dd class="mono">' + (ps.muc_swing_high_dang_hoat_dong ? Number(ps.muc_swing_high_dang_hoat_dong.gia).toFixed(S.digits) + ' (nến #' + ps.muc_swing_high_dang_hoat_dong.nen + ')' : '— chưa có —') + '</dd>' +
      '<dt>Mức swing low đang hoạt động</dt><dd class="mono">' + (ps.muc_swing_low_dang_hoat_dong ? Number(ps.muc_swing_low_dang_hoat_dong.gia).toFixed(S.digits) + ' (nến #' + ps.muc_swing_low_dang_hoat_dong.nen + ')' : '— chưa có —') + '</dd>' +
      '<dt>Số mức high đã bị phá</dt><dd>' + (ps.so_muc_high_da_pha !== undefined ? ps.so_muc_high_da_pha : '—') + '</dd>' +
      '<dt>Số mức low đã bị phá</dt><dd>' + (ps.so_muc_low_da_pha !== undefined ? ps.so_muc_low_da_pha : '—') + '</dd>' +
      '<dt>Nến chưa đủ cửa sổ phải</dt><dd class="mono">' + ((ps.nen_dang_cho_xac_nhan || []).join(', ') || '—') + '</dd>' +
      '</dl></div>';
    html += '<div class="section-title">Số sự kiện theo loại (tính tới nến hiện tại)</div>';
    var keys = Object.keys(byType).sort();
    html += '<table class="data-table"><thead><tr><th>Loại</th><th>Số sự kiện</th></tr></thead><tbody>';
    if (!keys.length) html += '<tr><td colspan="2" class="empty-cell">Chưa có sự kiện nào được xác nhận.</td></tr>';
    keys.forEach(function (k) {
      html += '<tr><td><span class="badge b-' + esc(k) + '">' + esc(k) + '</span></td><td class="num">' + byType[k] + '</td></tr>';
    });
    html += '</tbody></table>';
    $('#stats-body').innerHTML = '<p class="hint">F1, P90 và so sánh nhiều cấu hình: <a href="/danh-gia">Đánh giá thuật toán</a>.</p>' + html;
  }

  /** Trạng thái nội bộ DC tại con trỏ replay: dựng lại từ đầu khi lùi, không đọc trạng thái cuối run. */
  function dcPendingHtml(ps) {
    var d = S.digits;
    function f(x) { return x === null || x === undefined ? '—' : Number(x).toFixed(d); }
    var dc = ps.dc || {}, c = dc.ung_vien, cl = ps.classifier || {}, rg = cl.range;
    return '<div class="info-card"><dl>' +
      '<dt>Trạng thái (theo swing đã xác nhận)</dt><dd><strong>' + esc(ps.regime_vi) + '</strong> — ' + esc(cl.ly_do_vi || '') + '</dd>' +
      '<dt>Pha detector</dt><dd>' + esc(dc.phase_vi || dc.phase) + (dc.ly_do_cho ? ' · ' + esc(dc.ly_do_cho) : '') + '</dd>' +
      '<dt>ATR hiện tại</dt><dd class="mono">' + f(ps.atr_hien_tai) + '</dd>' +
      (dc.anchor ? '<dt>Anchor</dt><dd class="mono">' + f(dc.anchor.price) + ' ± ' + f(dc.anchor.delta) + ' (nến #' + dc.anchor.index + ')</dd>' : '') +
      '<dt>Ứng viên (chưa xác nhận)</dt><dd class="mono">' + (c
        ? (c.side === 'high' ? 'đỉnh ' : 'đáy ') + f(c.candidate_price) + ' @ #' + c.candidate_index + ' · Δ khoá ' + f(c.delta_e) +
          ' (ATR ' + f(c.candidate_atr) + ') · xác nhận khi close ' + (c.side === 'high' ? '≤ ' : '≥ ') + f(c.muc_xac_nhan)
        : '— không có —') + '</dd>' +
      '<dt>Range đang khoá</dt><dd class="mono">' + (rg ? '[' + f(rg.lower) + ', ' + f(rg.upper) + '] · buffer ' + f(rg.buffer) + ' · từ #' + rg.start_index : '—') + '</dd>' +
      '<dt>Pivot trong segment</dt><dd>' + (cl.so_dinh_xac_nhan || 0) + ' đỉnh (' + esc(cl.nhan_dinh_gan_nhat || '—') + ') · ' + (cl.so_day_xac_nhan || 0) + ' đáy (' + esc(cl.nhan_day_gan_nhat || '—') + ')</dd>' +
      '<dt>Segment / gap</dt><dd>#' + ps.segment + ' (từ nến #' + ps.segment_bat_dau_tu_nen + ') · ' + ps.so_gap + ' gap reset · ' + (ps.so_gap_noi || 0) + ' gap nối (' + esc(ps.gap_policy) + ')</dd>' +
      '</dl><p class="hint">' + esc(ps.ghi_chu_vi || '') + '</p></div>';
  }

  function c2PendingHtml(ps) {
    var d = S.digits;
    function f(x) { return x === null || x === undefined ? '—' : Number(x).toFixed(d); }
    function setup(s) {
      if (!s) return '— không có —';
      return esc(s.setup_id) + ' · pha ' + esc(s.phase) + ' · cực trị ' + f(s.extreme) + ' · mức CISD ' + f(s.cisd_level) +
        (s.cisd_confirmed ? ' · CISD đã xác nhận' : ' · chưa có CISD') + (s.c4_invalid ? ' · C4 không hợp lệ' : '');
    }
    function lv(x) {
      if (!x) return '— chưa có —';
      return f(x.price) + ' (nguồn #' + x.source_bar_index + ', biết lúc #' + x.set_bar_index + ', ' + esc(x.branch) +
        ', rev ' + x.revision + (x.reclaimed ? ', đã reclaim' : '') + ')';
    }
    var k = ps.ky_htf_hien_tai;
    return '<div class="info-card"><dl>' +
      '<dt>Setup tăng đang mở</dt><dd class="mono">' + setup(ps.setup_dang_mo.up) + '</dd>' +
      '<dt>Setup giảm đang mở</dt><dd class="mono">' + setup(ps.setup_dang_mo.down) + '</dd>' +
      '<dt>Mức CISD tăng đang theo dõi</dt><dd class="mono">' + lv(ps.muc_cisd_dang_theo_doi.up) + '</dd>' +
      '<dt>Mức CISD giảm đang theo dõi</dt><dd class="mono">' + lv(ps.muc_cisd_dang_theo_doi.down) + '</dd>' +
      '<dt>Kỳ H4 hiện tại</dt><dd class="mono">' + (k ? fmtIso(k.start) + ' — ' + k.n_bars + '/' + k.expected_bars + ' nến' + (k.complete ? '' : ' (chưa đủ)') : '—') + '</dd>' +
      '<dt>Gap M15 / kỳ H4 thiếu / kỳ H4 đủ</dt><dd>' + ps.so_gap_ltf + ' / ' + ps.so_ky_htf_thieu + ' / ' + ps.so_ky_htf_du + '</dd>' +
      '</dl></div>';
  }

  async function replayAction(fn) {
    if (!S.replay) return;
    try {
      var snap = await fn(S.replay.sid, S.replay.cursor);
      var r = S.replay;
      r.prev = { cursor: r.cursor, pending: r.snapshot ? r.snapshot.pending_state : null };
      r.snapshot = snap;
      r.cursor = snap.cursor;
      mergeReplayDelta(r, snap);
      renderReplay();
      return snap;
    } catch (e) {
      pausePlay();
      banner('error', esc(e.message));
    }
  }

  function playPause() {
    if (!S.replay) return;
    if (S.replay.playing) { pausePlay(); return; }
    S.replay.playing = true;
    $('#rp-play').textContent = '⏸';
    var tick = async function () {
      if (!S.replay || !S.replay.playing) return;
      if (S.replay.cursor >= S.replay.bars.length - 1) { pausePlay(); return; }
      await replayAction(function (sid, since) { return API.replayStep(sid, 1, since); });
      if (S.replay && S.replay.playing) {
        S.replay.timer = setTimeout(tick, parseInt($('#rp-speed').value, 10));
      }
    };
    tick();
  }

  function pausePlay() {
    if (!S.replay) return;
    S.replay.playing = false;
    if (S.replay.timer) { clearTimeout(S.replay.timer); S.replay.timer = null; }
    $('#rp-play').textContent = '▶';
  }

  async function stopReplay() {
    if (!S.replay) return;
    pausePlay();
    try { await API.replayClose(S.replay.sid); } catch (e) { /* bỏ qua */ }
    S.replay = null;
  }

  /**
   * Ghép phản hồi replay. `delta_since = s`: phần tới nến s không đổi (nhân quả) nên
   * chỉ cắt phần sau s rồi nối phần mới; `null` = bản đầy đủ.
   */
  function mergeReplayDelta(r, snap) {
    var s = snap.delta_since;
    if (s === null || s === undefined) {
      r.events = snap.events;
      r.timeline = snap.timeline;
      r.renderedEvents = -1;
      return;
    }
    var ev = r.events.slice(), tl = r.timeline.slice();
    while (ev.length && ev[ev.length - 1].confirmed_bar_index > s) ev.pop();
    while (tl.length && tl[tl.length - 1].bar_index > s) tl.pop();
    Array.prototype.push.apply(ev, snap.events);
    Array.prototype.push.apply(tl, snap.timeline);
    r.events = ev;
    r.timeline = tl;
  }

  /**
   * Đổi thuật toán/tham số khi đang replay: mở phiên mới theo form và nhảy tới
   * đúng nến đang xem. Thuật toán mới vẫn chạy nhân quả từ nến #0 tới đó.
   */
  async function restartReplayKeepCursor(what) {
    var cur = S.replay ? S.replay.cursor : -1;
    await stopReplay();
    await enterReplay({ seekTo: cur });
    if (S.replay) {
      banner('info', 'Đã đổi ' + esc(what) + ': replay chạy lại với <strong>' + esc(S.algo.display_name_vi) +
        '</strong> (v' + esc(S.algo.version) + ') tới nến #' + Math.max(0, cur) +
        ' — tính lại nhân quả từ nến #0, không dùng kết quả của thuật toán cũ.');
    }
  }

  /** Bắt đầu replay đúng cấu hình của run đang hiển thị, tại nến đầu vùng đang xem. */
  async function replayFromView() {
    if (!S.run) return;
    var vr = S.chart.visibleIndexRange();
    var start = vr ? vr.start : 0;
    await stopReplay();
    if (S.run.algorithm === 'dc_atr_structure' && !S.layers.dc_candidate) {
      S.layers.dc_candidate = true;
      var cb = $('#dc-layers input[data-layer="dc_candidate"]');
      if (cb) cb.checked = true;
    }
    $('#chk-explain').checked = true;
    if (!S.algo || S.algo.name !== S.run.algorithm) selectAlgorithm(S.run.algorithm);
    switchMode('replay');
    await enterReplay({
      dataset_id: S.run.dataset_id, algorithm: S.run.algorithm, params: S.run.params,
      range_start: S.run.range_start, range_end: S.run.range_end, seekTo: start
    });
    if (S.replay) {
      banner('info', 'Replay bắt đầu ở nến #' + start + ' (đầu vùng đang xem) với đúng tham số của lần chạy. ' +
        'Thuật toán đã chạy nhân quả từ nến #0 tới đây; từ giờ bấm <strong>▶</strong>, <strong>→</strong> hoặc ' +
        '<strong>Tới xác nhận kế tiếp</strong> để xem từng bước. Khung bên trái giải thích mỗi nến.');
    }
  }

  function f2(x) { return x === null || x === undefined || !isFinite(x) ? '—' : Number(x).toFixed(S.digits); }

  /** Khung «Thuật toán đang làm gì» — chỉ đọc snapshot/sự kiện đã có tại con trỏ. */
  function renderExplain() {
    var box = $('#rp-explain');
    var r = S.replay;
    var isDc = r && r.snapshot && r.snapshot.algorithm === 'dc_atr_structure';
    var chk = $('#chk-explain');
    chk.disabled = !!(r && r.snapshot) && !isDc;
    chk.parentNode.title = chk.disabled
      ? 'Giải thích từng bước hiện có cho «DC theo close + ATR». Thuật toán này xem ở tab Thống kê (trạng thái nội bộ).'
      : 'Khung giải thích từng bước trên chart (dc_atr_structure)';
    if (!r || S.mode !== 'replay' || !isDc || !$('#chk-explain').checked) { box.hidden = true; return; }
    box.hidden = false;
    var i = r.cursor, bar = i >= 0 ? r.bars[i] : null;
    $('#rp-explain-bar').textContent = bar ? 'nến #' + i + ' · ' + fmtIso(bar.close_time) : '';
    if (!bar) {
      $('#rp-explain-body').innerHTML = '<div class="xp xp-muted">Chưa nạp nến nào. Bấm ▶ hoặc → để nạp nến đầu tiên.</div>';
      return;
    }
    var snap = r.snapshot, ps = snap.pending_state || {}, dc = ps.dc || {}, cl = ps.classifier || {};
    var params = snap.params || {};
    var out = [];
    function add(kind, html) { out.push('<div class="xp xp-' + kind + '">' + html + '</div>'); }

    // 1. Điều gì vừa xảy ra ở nến này
    out.push('<div class="xp-sec">Nến này: close = ' + f2(bar.close) + ' (chỉ dùng CLOSE; high/low chỉ để tính ATR)</div>');
    var here = [];
    for (var k = r.events.length - 1; k >= 0 && r.events[k].confirmed_bar_index >= i; k--) {
      if (r.events[k].confirmed_bar_index === i) here.unshift(r.events[k]);
    }
    var pivotHere = false;
    here.forEach(function (e) {
      var x = e.details || {};
      if (e.structure_type === 'DC_HIGH' || e.structure_type === 'DC_LOW') {
        pivotHere = true;
        var hi = e.structure_type === 'DC_HIGH';
        add('ok', '<b>Xác nhận ' + (hi ? 'ĐỈNH' : 'ĐÁY') + ' DC</b> tại nến #' + e.event_bar_index + ' (close ' + f2(e.price) + '): ' +
          esc(x.dieu_kien_xac_nhan) + '. Biết sau ' + e.confirmation_lag_bars + ' nến. ' +
          (x.nhan
            ? 'Nhãn <b>' + esc(x.nhan) + '</b>: so với ' + (hi ? 'đỉnh' : 'đáy') + ' trước ' + f2(x.nhan_gia_truoc) + ', chênh ' + f2(x.nhan_chenh_lech) + ' (dung sai ±' + f2(x.nhan_dung_sai) + ').'
            : 'Là ' + (hi ? 'đỉnh' : 'đáy') + ' đầu tiên trong segment nên chưa có nhãn so sánh.') +
          ' Từ nến này chuyển sang theo dõi ' + (hi ? 'ĐÁY' : 'ĐỈNH') + ', ứng viên mới = close hiện tại.');
      } else if (e.structure_type === 'DC_SEGMENT_GAP') {
        add('warn', '<b>Gap ' + Math.round(x.khoang_cach_giay / 60) + ' phút</b> → reset segment: bỏ ứng viên, ATR, lịch sử pivot/trạng thái; warm-up lại từ nến này.');
      } else if (e.structure_type === 'DC_GAP_BRIDGED') {
        add('info', '<b>Gap ' + Math.round(x.khoang_cach_giay / 60) + ' phút được NỐI</b> (≤ ' + esc(x.bridge_max_gap_hours) + ' giờ): giữ ứng viên, ATR, lịch sử; bước nhảy ' + f2(x.buoc_nhay_open) + ' được tính vào ATR.');
      } else {
        var TXT = window.chartUtils.REGIME_TEXT_VI;
        add('info', '<b>Trạng thái: ' + esc(TXT[x.tu_trang_thai] || x.tu_trang_thai) + ' → ' + esc(TXT[x.sang_trang_thai] || x.sang_trang_thai) + '</b>. ' + esc(x.giai_thich_vi || ''));
      }
    });
    var prev = r.prev && r.prev.cursor === i - 1 && r.prev.pending ? r.prev.pending : null;
    var pdc = prev ? (prev.dc || {}) : null, c = dc.ung_vien, pc = pdc ? pdc.ung_vien : null;
    if (prev && !pivotHere) {
      if (pdc.phase === 'WARMUP' && dc.phase === 'SEEK_DIRECTION' && dc.anchor) {
        add('info', 'ATR vừa đủ → đặt <b>anchor</b> = close ' + f2(dc.anchor.price) + ', Δ = ' + f2(dc.anchor.delta) + '. Không phát pivot ở anchor; chờ giá đi đủ Δ để chọn hướng.');
      } else if (pdc.phase === 'SEEK_DIRECTION' && c) {
        add('info', 'Close ' + f2(bar.close) + (c.side === 'high' ? ' ≥ anchor + Δ' : ' ≤ anchor − Δ') + ' → chọn hướng <b>' + (c.side === 'high' ? 'LÊN' : 'XUỐNG') +
          '</b>: bắt đầu theo dõi ' + (c.side === 'high' ? 'đỉnh' : 'đáy') + ' với ứng viên = close nến này.');
      } else if (c && pc && c.side === pc.side && c.candidate_index !== pc.candidate_index) {
        add('info', 'Close ' + f2(bar.close) + (c.side === 'high' ? ' > ' : ' < ') + 'ứng viên cũ ' + f2(pc.candidate_price) +
          ' → <b>ứng viên dời</b> sang nến này; Δ khoá lại = ' + f2(c.delta_e) + ' (ATR ' + f2(c.candidate_atr) + ').');
      } else if (c && pc && c.candidate_index === pc.candidate_index) {
        add('muted', 'Không đổi: close chưa ' + (c.side === 'high' ? 'cao hơn' : 'thấp hơn') + ' ứng viên và chưa chạm mức xác nhận. Δ vẫn giữ giá trị đã khoá dù ATR đổi.');
      } else if (pdc.phase === 'SEEK_DIRECTION' && dc.phase === 'SEEK_DIRECTION') {
        add('muted', 'Không đổi: close ' + f2(bar.close) + ' vẫn nằm trong anchor ± Δ nên chưa chọn hướng.');
      } else if (dc.phase === 'WARMUP') {
        add('muted', 'Đang warm-up: chưa đủ nến để có ATR, detector chưa làm gì.');
      }
    } else if (!prev && !here.length) {
      add('muted', 'Vừa nhảy tới nến này (không phải bước 1 nến) — chỉ mô tả trạng thái hiện tại.');
    }

    // 2. Trạng thái hiện tại của detector
    out.push('<div class="xp-sec">Detector DC (' + esc(dc.phase_vi || dc.phase || '') + ')</div>');
    if (dc.phase === 'WARMUP') {
      add('state', 'Warm-up ATR: cần ' + ((params.atr_period || 14) + 1) + ' nến liên tục trong segment (segment bắt đầu ở nến #' + ps.segment_bat_dau_tu_nen + '). Chưa tìm cực trị.');
    } else if (dc.phase === 'WAIT_ATR') {
      add('state', esc(dc.ly_do_cho || 'Chờ ATR > 0.'));
    } else if (dc.phase === 'SEEK_DIRECTION' && dc.anchor) {
      var a = dc.anchor;
      add('state', 'Chờ chọn hướng: anchor ' + f2(a.price) + ' ± Δ ' + f2(a.delta) + ' → cần close ≥ <b>' + f2(a.price + a.delta) + '</b> (lên) hoặc ≤ <b>' + f2(a.price - a.delta) + '</b> (xuống).');
    } else if (c) {
      var hi2 = c.side === 'high';
      var gap = hi2 ? bar.close - c.muc_xac_nhan : c.muc_xac_nhan - bar.close;
      var moved = hi2 ? c.candidate_price - bar.close : bar.close - c.candidate_price;
      var pct = Math.max(0, Math.min(1, c.delta_e > 0 ? moved / c.delta_e : 0));
      add('state', 'Đang theo dõi <b>' + (hi2 ? 'ĐỈNH' : 'ĐÁY') + '</b>: ứng viên close ' + f2(c.candidate_price) + ' @ nến #' + c.candidate_index +
        ' (chưa phải pivot — có thể còn dời).<br>Δ khoá = ' + f2(c.delta_e) +
        (params.threshold_mode === 'percent' ? ' (' + esc(params.reversal_pct) + '% close ứng viên)' : ' = ' + esc(params.atr_multiplier) + ' × ATR ' + f2(c.candidate_atr)) +
        '.<br>Xác nhận khi close ' + (hi2 ? '≤ ' : '≥ ') + '<b>' + f2(c.muc_xac_nhan) + '</b> (đường chấm vàng) — ' +
        (gap > 0 ? 'close hiện tại còn cách ' + f2(gap) + '.' : 'đã chạm.') +
        '<div class="rp-progress" title="Đã đảo chiều ' + Math.round(pct * 100) + '% ngưỡng Δ"><span style="width:' + (pct * 100).toFixed(0) + '%"></span></div>' +
        '<span class="muted">Đã đảo chiều ' + Math.round(pct * 100) + '% Δ. Nếu close ' + (hi2 ? 'vượt lên trên ' : 'xuống dưới ') + f2(c.candidate_price) + ' thì ứng viên dời theo.</span>');
    }
    // 3. Trạng thái Trend/Range
    out.push('<div class="xp-sec">Trạng thái (theo swing đã xác nhận)</div>');
    var rg = cl.range;
    add('state', '<b>' + esc(ps.regime_vi || '') + '</b> — ' + esc(cl.ly_do_vi || '') +
      (cl.so_dinh_xac_nhan !== undefined ? '<br><span class="muted">Segment có ' + cl.so_dinh_xac_nhan + ' đỉnh (gần nhất ' + esc(cl.nhan_dinh_gan_nhat || '—') + '), ' +
        cl.so_day_xac_nhan + ' đáy (gần nhất ' + esc(cl.nhan_day_gan_nhat || '—') + '). Tăng cần HH + HL, Giảm cần LH + LL.</span>' : '') +
      (rg ? '<br>Range khoá [' + f2(rg.lower) + ', ' + f2(rg.upper) + '], thoát khi close vượt ' + f2(rg.bien_tren_pha) + ' hoặc thủng ' + f2(rg.bien_duoi_pha) + '.' : ''));
    $('#rp-explain-body').innerHTML = out.join('');
  }

  function switchMode(mode) {
    S.mode = mode;
    $$('.mode-btn').forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-mode') === mode); });
    $('#replay-bar').hidden = mode !== 'replay';
    $('#btn-replay-here').hidden = !(mode === 'full' && S.run);
    if (mode !== 'replay') $('#rp-explain').hidden = true;
    $('#mode-note').innerHTML = mode === 'full'
      ? 'Marker tại nến sự kiện, không phải lúc hệ thống biết. Cột «Xác nhận lúc» mới là thời điểm tín hiệu khả dụng.'
      : 'Replay chỉ nạp prefix tới nến hiện tại. Phím → ← từng nến, Space phát. Bấm <strong>Tới hết warm-up</strong> để bỏ qua nến đầu.';
  }

  // ----------------------------------------------------------------- nhập CSV

  var importState = { file: null, preview: null };

  function openImport() {
    importState = { file: null, preview: null };
    $('#import-file').value = '';
    $('#import-preview').hidden = true;
    $('#import-error').hidden = true;
    $('#btn-do-import').disabled = true;
    $('#import-modal').hidden = false;
  }

  function closeImport() { $('#import-modal').hidden = true; }

  async function onPickFile() {
    var f = $('#import-file').files[0];
    if (!f) return;
    importState.file = f;
    $('#import-error').hidden = true;
    try {
      var pv = await API.previewCsv(f);
      importState.preview = pv;
      renderPreview(pv);
      $('#btn-do-import').disabled = false;
      if (pv.suggested_timeframe) $('#import-timeframe').value = pv.suggested_timeframe;
    } catch (e) {
      showImportError(e.message);
      $('#btn-do-import').disabled = true;
    }
  }

  function renderPreview(pv) {
    $('#import-preview').hidden = false;
    $('#import-preview-note').textContent =
      'Delimiter: ' + JSON.stringify(pv.delimiter) + ' · ' + (pv.has_header ? 'có dòng tiêu đề' : 'không có dòng tiêu đề') +
      (pv.note_vi ? ' · ' + pv.note_vi : '');

    var fields = [
      ['time', 'Thời gian'], ['date_part', 'Cột ngày (nếu tách)'], ['time_part', 'Cột giờ (nếu tách)'],
      ['open', 'Open'], ['high', 'High'], ['low', 'Low'], ['close', 'Close'], ['volume', 'Volume']
    ];
    $('#mapping-grid').innerHTML = fields.map(function (f) {
      var cur = pv.suggested_mapping[f[0]] || '';
      return '<label class="field"><span>' + esc(f[1]) + '</span><select data-map="' + f[0] + '">' +
        '<option value="">— không dùng —</option>' +
        pv.headers.map(function (h) {
          return '<option value="' + esc(h) + '"' + (h === cur ? ' selected' : '') + '>' + esc(h) + '</option>';
        }).join('') + '</select></label>';
    }).join('');

    var t = '<thead><tr>' + pv.headers.map(function (h) { return '<th>' + esc(h) + '</th>'; }).join('') + '</tr></thead><tbody>';
    t += pv.sample_rows.map(function (r) {
      return '<tr>' + r.map(function (c) { return '<td class="mono">' + esc(c) + '</td>'; }).join('') + '</tr>';
    }).join('');
    $('#preview-table').innerHTML = t + '</tbody>';
  }

  function showImportError(msg) {
    var el = $('#import-error');
    el.textContent = msg;
    el.hidden = false;
  }

  async function doImport() {
    if (!importState.file) return;
    var symbol = $('#import-symbol').value.trim();
    if (!symbol) { showImportError('Phải nhập symbol.'); return; }
    var tz = $('#import-tz').value.trim();
    if (!tz) { showImportError('Phải khai báo múi giờ nguồn.'); return; }

    var mapping = {};
    $$('#mapping-grid [data-map]').forEach(function (s) {
      if (s.value) mapping[s.getAttribute('data-map')] = s.value;
    });

    var fd = new FormData();
    fd.append('file', importState.file);
    fd.append('name', $('#import-name').value);
    fd.append('symbol', symbol);
    fd.append('timeframe', $('#import-timeframe').value);
    fd.append('source', $('#import-source').value);
    fd.append('source_timezone', tz);
    fd.append('timestamp_convention', $('#import-convention').value);
    fd.append('price_type', $('#import-pricetype').value);
    fd.append('notes', $('#import-notes').value);
    fd.append('mapping_json', JSON.stringify(mapping));

    $('#btn-do-import').disabled = true;
    try {
      var ds = await API.importCsv(fd);
      closeImport();
      await loadDatasets(ds.id);
      banner('ok', 'Đã nhập dataset <strong>' + esc(ds.name) + '</strong> — ' + ds.row_count + ' nến.');
    } catch (e) {
      showImportError(e.message);
    } finally {
      $('#btn-do-import').disabled = false;
    }
  }

  // ----------------------------------------------------------------- xuất

  function exportPng() {
    var canvas = S.chart.screenshot();
    var name = 'chart_' + (S.dataset ? S.dataset.symbol + '_' + S.dataset.timeframe : 'msl') + '_' +
      new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '.png';
    canvas.toBlob(function (blob) {
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = name;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
    });
  }

  async function doResample() {
    openResampleModal(null);
  }

  function fillResampleTargets(preselect) {
    var sel = $('#resample-target');
    if (!S.dataset) { sel.innerHTML = ''; return; }
    var srcSec = TF_SEC[S.dataset.timeframe] || 0;
    var opts = TF_ORDER.filter(function (tf) { return TF_SEC[tf] > srcSec; });
    sel.innerHTML = opts.map(function (tf) {
      return '<option value="' + tf + '"' + (tf === preselect ? ' selected' : '') + '>' + tf + '</option>';
    }).join('');
    $('#btn-do-resample').disabled = !opts.length;
  }

  function openResampleModal(preselect) {
    if (!S.dataset) { banner('error', 'Chọn dataset nguồn.'); return; }
    $('#resample-error').hidden = true;
    $('#resample-source-note').textContent = 'Nguồn: ' + S.dataset.symbol + ' ' + S.dataset.timeframe +
      ' · ' + S.dataset.row_count + ' nến. Mốc utc_epoch, không lấp gap bằng tương lai.';
    fillResampleTargets(preselect);
    if (!$('#resample-target').options.length) {
      banner('error', 'Dataset ' + S.dataset.timeframe + ' đã ở khung lớn nhất lab hỗ trợ (H4), không tổng hợp lên được. Xuống M5: bấm nút M5 trên thanh Khung.');
      return;
    }
    $('#resample-modal').hidden = false;
  }

  function closeResampleModal() { $('#resample-modal').hidden = true; }

  async function submitResample() {
    if (!S.dataset) return;
    var tf = ($('#resample-target').value || '').toUpperCase();
    var policy = $('#resample-gap').value || 'drop_incomplete';
    $('#resample-error').hidden = true;
    $('#btn-do-resample').disabled = true;
    try {
      var out = await API.resample({
        dataset_id: S.dataset.id,
        target_timeframe: tf,
        gap_policy: policy
      });
      closeResampleModal();
      await loadDatasets(out.dataset.id);
      banner('ok', 'Đã tổng hợp ' + out.dataset.row_count + ' nến ' + esc(out.dataset.timeframe) +
        '. ' + esc(out.resample.note_vi));
    } catch (e) {
      $('#resample-error').hidden = false;
      $('#resample-error').textContent = e.message;
    } finally {
      $('#btn-do-resample').disabled = false;
    }
  }

  function openMt5() {
    $('#mt5-modal').hidden = false;
    API.mt5Status().then(function (s) {
      $('#mt5-status-note').textContent = (s.available ? 'Gói MetaTrader5: có. ' : 'Gói MetaTrader5: CHƯA cài. ') + s.note_vi;
    }).catch(function (e) { $('#mt5-status-note').textContent = e.message; });
  }
  function closeMt5() { $('#mt5-modal').hidden = true; $('#mt5-error').hidden = true; }

  async function doMt5Import() {
    $('#mt5-error').hidden = true;
    try {
      var ds = await API.importMt5({
        symbol: $('#mt5-symbol').value.trim(),
        timeframe: $('#mt5-timeframe').value,
        source_timezone: $('#mt5-tz').value.trim(),
        timestamp_convention: $('#mt5-convention').value,
        count: parseInt($('#mt5-count').value, 10),
        terminal_path: $('#mt5-path').value.trim()
      });
      closeMt5();
      await loadDatasets(ds.id);
      banner('ok', 'Đã nhập ' + ds.row_count + ' nến đóng từ MT5.');
    } catch (e) {
      $('#mt5-error').hidden = false;
      $('#mt5-error').textContent = e.message;
    }
  }

  // ---------------------------------------------------------------- nhãn
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
    banner('ok', what + ' <code>' + esc(ls.id) + '</code> (bản ' + (ls.revision || 1) + ') — ' +
      (ls.labels ? ls.labels.length : S.draftLabels.length) + ' nhãn, người gán: ' +
      esc(ls.annotator) + '.' + warn +
      (ls.ghi_chu_vi ? ' ' + esc(ls.ghi_chu_vi) : ''));
  }

  async function saveLabels() {
    if (!S.dataset) { banner('error', 'Chọn dataset.'); return; }
    if (!S.draftLabels.length) { banner('error', 'Chưa có nhãn nào để lưu.'); return; }
    $('#btn-save-labels').disabled = true;
    try {
      var ls = await API.saveLabelSet(Object.assign(
        { dataset_id: S.dataset.id }, labelPayload()));
      afterLabelWrite(ls, 'Đã lưu bộ nhãn mới');
      await refreshLabelSetPicker(ls.id);
    } catch (e) {
      banner('error', esc(e.message));
    } finally {
      $('#btn-save-labels').disabled = false;
    }
  }

  async function updateLabels() {
    if (!S.labelSetId) { banner('error', 'Chưa mở bộ nhãn nào để cập nhật. Dùng "Lưu thành bộ mới".'); return; }
    if (!S.draftLabels.length) { banner('error', 'Bộ nháp rỗng — không ghi đè bằng bộ rỗng.'); return; }
    $('#btn-update-labels').disabled = true;
    try {
      var ls;
      try {
        ls = await API.updateLabelSet(S.labelSetId, labelPayload());
      } catch (e) {
        // Backend chặn khi bộ nhãn đã được dùng trong đánh giá đã lưu.
        if (e.message.indexOf('đánh giá đã lưu') === -1) throw e;
        if (!window.confirm(e.message + '\n\nVẫn ghi đè?')) {
          banner('warn', 'Đã huỷ ghi đè. Bộ nhãn giữ nguyên.');
          return;
        }
        ls = await API.updateLabelSet(S.labelSetId,
          Object.assign(labelPayload(), { confirm_overwrite: true }));
      }
      afterLabelWrite(ls, 'Đã ghi đè bộ nhãn');
      await refreshLabelSetPicker(ls.id);
    } catch (e) {
      banner('error', esc(e.message));
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
    if (!S.dataset) { banner('error', 'Chọn dataset.'); return; }
    var id = $('#label-set-pick').value;
    if (!id) { banner('warn', 'Dataset này chưa có bộ nhãn nào để tải.'); return; }
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
      banner('ok', 'Đã tải bộ <code>' + esc(ls.id) + '</code> (bản ' + (ls.revision || 1) + ') của ' +
        esc(ls.annotator) + ' — ' + S.draftLabels.length + ' nhãn.' +
        (used ? ' Bộ này đã được dùng trong ' + used + ' đánh giá đã lưu; ghi đè sẽ phải xác nhận.' : ''));
    } catch (e) { banner('error', esc(e.message)); }
  }

  function exportLabels() {
    if (!S.labelSetId) { banner('error', 'Lưu hoặc tải một bộ nhãn trước khi xuất.'); return; }
    if (draftIsDirty()) {
      banner('warn', 'Nháp đang có thay đổi chưa lưu — file xuất ra là nội dung ĐÃ LƯU của bộ ' +
        esc(S.labelSetId) + ', không phải nháp hiện tại.');
    }
    window.location.href = API.labelSetExportUrl(S.labelSetId);
  }

  async function importLabelsCsv(file) {
    if (!S.dataset) { banner('error', 'Chọn dataset trước khi nhập nhãn.'); return; }
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
      banner(out.warnings && out.warnings.length ? 'warn' : 'ok',
        esc(out.ghi_chu_vi) + w);
    } catch (e) {
      banner('error', 'Không nhập được CSV: ' + esc(e.message));
    }
  }

  async function evalLabels() {
    if (!S.run || !S.run.run_id) { banner('error', 'Chạy thử trước.'); return; }
    if (!S.labelSetId) { banner('error', 'Lưu hoặc tải bộ nhãn trước.'); return; }
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
    } catch (e) { banner('error', esc(e.message)); }
  }

  async function doMql5Compare() {
    if (!S.run || !S.run.run_id) { banner('error', 'Chạy thử Python trước.'); return; }
    var f = $('#mql5-file').files[0];
    if (!f) { banner('error', 'Chọn file CSV MQL5.'); return; }
    var text = await f.text();
    try {
      var out = await API.compareMql5({
        run_id: S.run.run_id,
        csv_text: text,
        csv_checksum: $('#mql5-checksum').value.trim() || null
      });
      var w = (out.warnings || []).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('');
      $('#mql5-body').innerHTML = '<p>' + esc(out.note_vi) + '</p>' +
        (w ? '<ul>' + w + '</ul>' : '') +
        '<p>Checksum khớp: ' + (out.checksum_khop ? 'có' : 'không') +
        ' · TP=' + out.true_positives + ' FP=' + out.false_positives + ' FN=' + out.false_negatives + '</p>';
    } catch (e) { banner('error', esc(e.message)); }
  }

  // ----------------------------------------------------------------- sự kiện DOM

  function bindEvents() {
    $('#dataset-select').addEventListener('change', function (e) { selectDataset(e.target.value); });
    $('#algo-select').addEventListener('change', function (e) {
      selectAlgorithm(e.target.value);
      if (S.mode === 'replay' && S.replay) restartReplayKeepCursor('thuật toán');
    });
    $('#rp-algo').addEventListener('change', function (e) {
      selectAlgorithm(e.target.value);
      if (S.mode === 'replay' && S.replay) restartReplayKeepCursor('thuật toán');
    });
    $('#param-form').addEventListener('change', function () {
      if (S.mode !== 'replay' || !S.replay) return;
      clearTimeout(S.paramRestartTimer);
      S.paramRestartTimer = setTimeout(function () { restartReplayKeepCursor('tham số'); }, 350);
    });
    $('#btn-run').addEventListener('click', doRun);
    $('#btn-range-reset').addEventListener('click', useFullRange);
    $('#range-start').addEventListener('change', renderRangeHint);
    $('#range-end').addEventListener('change', renderRangeHint);

    $('#btn-seed').addEventListener('click', async function () {
      var b = $('#btn-seed');
      b.disabled = true; b.textContent = 'Đang tạo…';
      try {
        await API.seedSamples();
        await loadDatasets();
        banner('ok', 'Đã tạo các dataset <strong>MÔ PHỎNG</strong>. Đây không phải dữ liệu thị trường thật — dùng để thử công cụ.');
      } catch (e) {
        banner('error', esc(e.message));
      } finally {
        b.disabled = false; b.textContent = 'Tạo dữ liệu mẫu';
      }
    });

    $('#btn-open-import').addEventListener('click', openImport);
    $('#btn-close-import').addEventListener('click', closeImport);
    $('#btn-cancel-import').addEventListener('click', closeImport);
    $('#import-file').addEventListener('change', onPickFile);
    $('#btn-do-import').addEventListener('click', doImport);

    $$('.mode-btn').forEach(function (b) {
      b.addEventListener('click', async function () {
        var m = b.getAttribute('data-mode');
        if (m === S.mode) return;
        if (m === 'replay') {
          switchMode('replay');
          await enterReplay();
        } else {
          await stopReplay();
          switchMode('full');
          if (S.run) {
            S.chart.setBars(S.allBars);
            applyChartEvents();
            S.chart.showLast(350);
            renderEvents(S.run.events);
            renderStats(S.run);
          } else {
            $('#chart-empty').hidden = false;
          }
        }
      });
    });

    $$('.tab[data-tab]').forEach(function (t) {
      t.addEventListener('click', function () {
        var panel = $('#bottom-panel');
        if (panel.classList.contains('collapsed')) {
          panel.classList.remove('collapsed');
          $('#btn-toggle-bottom').textContent = 'Thu gọn';
        }
        $$('.tab[data-tab]').forEach(function (x) { x.classList.remove('active'); });
        $$('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
        t.classList.add('active');
        $('.tab-panel[data-panel="' + t.getAttribute('data-tab') + '"]').classList.add('active');
      });
    });

    $$('#layer-toggles input[data-layer], #dc-layers input[data-layer]').forEach(function (cb) {
      cb.addEventListener('change', function () {
        S.layers[cb.getAttribute('data-layer')] = cb.checked;
        applyChartEvents();
        var cur = S.mode === 'replay' && S.replay ? S.replay : S.run;
        if (cur) renderAlgoNotes(S.algo && S.algo.name, S.mode === 'replay' ? null : cur.stats,
          S.mode === 'replay' ? (cur.snapshot || {}).data_status : cur.data_status,
          S.mode === 'replay' ? (cur.snapshot || {}).pending_state : cur.pending_state);
      });
    });
    $('#btn-baseline').addEventListener('click', runBaseline);
    $('#chk-split-baseline').addEventListener('change', function () {
      if (this.checked && !S.baseline) {
        banner('warn', 'Chưa có run baseline cho dataset/khoảng này — bấm <strong>So sánh baseline (pivot 3/3)</strong> trước.');
      }
      renderSplit();
    });
    // Bàn phím trên bảng sự kiện: ↑/↓/Home/End/PageUp/PageDown di chuyển, Enter/Space chọn.
    $('#events-table tbody').addEventListener('keydown', function (e) {
      var tr = e.target.closest && e.target.closest('tr[data-ev]');
      if (!tr) return;
      var rows = Array.prototype.slice.call(this.querySelectorAll('tr[data-ev]'));
      var i = rows.indexOf(tr), j = null;
      if (e.key === 'ArrowDown') j = i + 1;
      else if (e.key === 'ArrowUp') j = i - 1;
      else if (e.key === 'Home') j = 0;
      else if (e.key === 'End') j = rows.length - 1;
      else if (e.key === 'PageDown') j = i + 10;
      else if (e.key === 'PageUp') j = i - 10;
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); tr.click(); tr.focus({ preventScroll: true }); return; }
      else return;
      e.preventDefault();
      e.stopPropagation();
      j = Math.max(0, Math.min(rows.length - 1, j));
      tr.setAttribute('tabindex', '-1');
      rows[j].setAttribute('tabindex', '0');
      rows[j].focus({ preventScroll: true });
      rows[j].scrollIntoView({ block: 'nearest' });
    });
    $('#rp-next-event').addEventListener('click', function () {
      pausePlay();
      replayAction(function (sid, since) { return API.replayNextEvent(sid, since); });
    });
    $('#chk-confirm-position').addEventListener('change', applyChartEvents);

    $('#event-filter').addEventListener('input', function () {
      renderEvents(S.mode === 'replay' && S.replay ? S.replay.events : (S.run ? S.run.events : []));
    });

    $('#rp-fwd').addEventListener('click', function () { pausePlay(); replayAction(function (sid, since) { return API.replayStep(sid, 1, since); }); });
    $('#rp-back').addEventListener('click', function () { pausePlay(); replayAction(function (sid, since) { return API.replayBack(sid, 1, since); }); });
    $('#btn-replay-here').addEventListener('click', replayFromView);
    $('#chk-explain').addEventListener('change', renderExplain);
    $('#rp-explain-hide').addEventListener('click', function () { $('#chk-explain').checked = false; renderExplain(); });
    $('#rp-reset').addEventListener('click', function () { pausePlay(); replayAction(function (sid) { return API.replayReset(sid); }); });
    $('#rp-play').addEventListener('click', playPause);
    $('#rp-skip-warmup').addEventListener('click', function () {
      if (!S.replay) return;
      pausePlay();
      var need = (S.replay.snapshot && S.replay.snapshot.warmup_bars) || 0;
      var idx = Math.max(0, need - 1);
      replayAction(function (sid, since) { return API.replaySeek(sid, idx, since); });
    });
    $('#rp-slider').addEventListener('change', function (e) {
      pausePlay();
      replayAction(function (sid, since) { return API.replaySeek(sid, parseInt(e.target.value, 10), since); });
    });

    $('#btn-reload-runs').addEventListener('click', loadRuns);
    $('#chk-history-current-ds').addEventListener('change', loadRuns);
    $('#btn-compare').addEventListener('click', doCompare);

    $('#btn-export-csv').addEventListener('click', function () {
      if (!S.run || !S.run.run_id) return;
      window.location.href = API.exportUrl(S.run.run_id);
    });
    $('#btn-export-png').addEventListener('click', exportPng);

    document.addEventListener('keydown', function (e) {
      if (S.mode !== 'replay' || !S.replay) return;
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
      if (e.key === 'ArrowRight') { e.preventDefault(); pausePlay(); replayAction(function (sid, since) { return API.replayStep(sid, 1, since); }); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); pausePlay(); replayAction(function (sid, since) { return API.replayBack(sid, 1, since); }); }
      if (e.key === ' ') { e.preventDefault(); playPause(); }
    });

    window.addEventListener('beforeunload', function () {
      if (S.replay && navigator.sendBeacon) {
        navigator.sendBeacon('/api/replay/' + S.replay.sid + '/close');
      }
    });

    $('#btn-resample').addEventListener('click', doResample);
    $('#btn-close-resample').addEventListener('click', closeResampleModal);
    $('#btn-cancel-resample').addEventListener('click', closeResampleModal);
    $('#btn-do-resample').addEventListener('click', submitResample);
    $('#btn-open-mt5').addEventListener('click', openMt5);
    $('#btn-close-mt5').addEventListener('click', closeMt5);
    $('#btn-cancel-mt5').addEventListener('click', closeMt5);
    $('#btn-do-mt5').addEventListener('click', doMt5Import);
    $('#btn-save-labels').addEventListener('click', saveLabels);
    $('#btn-update-labels').addEventListener('click', updateLabels);
    $('#btn-load-labels').addEventListener('click', loadLabelSets);
    $('#btn-eval-labels').addEventListener('click', evalLabels);
    $('#btn-export-labels').addEventListener('click', exportLabels);
    $('#btn-import-labels').addEventListener('click', function () {
      $('#label-import-file').click();
    });
    $('#label-import-file').addEventListener('change', function (e) {
      var f = e.target.files[0];
      if (f) importLabelsCsv(f);
      e.target.value = '';
    });
    $('#btn-clear-draft-labels').addEventListener('click', function () {
      if (draftIsDirty() &&
          !window.confirm('Xoá ' + S.draftLabels.length + ' nhãn chưa lưu trong bộ nháp?')) return;
      S.draftLabels = [];
      S.labelSetId = null;
      S.labelDirty = false;
      if (S.dataset) window.LabelDraft.clear(S.dataset.id);
      renderDraftLabels();
      renderDraftStatus();
    });
    ['#label-annotator', '#label-version', '#label-rubric'].forEach(function (sel) {
      $(sel).addEventListener('change', persistDraft);
    });
    // Nhắc lại khi đóng tab mà nháp chưa lưu.
    window.LabelDraft.guardUnload(draftIsDirty);
    $('#btn-mql5-compare').addEventListener('click', doMql5Compare);

    $('#btn-toggle-bottom').addEventListener('click', function () {
      var p = $('#bottom-panel');
      var on = p.classList.toggle('collapsed');
      this.textContent = on ? 'Mở bảng' : 'Thu gọn';
    });
    (function bindBottomResize() {
      var panel = $('#bottom-panel');
      var handle = $('#bottom-resizer');
      var drag = null;
      handle.addEventListener('mousedown', function (e) {
        if (panel.classList.contains('collapsed')) return;
        drag = { y: e.clientY, h: panel.getBoundingClientRect().height };
        e.preventDefault();
      });
      window.addEventListener('mousemove', function (e) {
        if (!drag) return;
        var next = Math.round(drag.h + (drag.y - e.clientY));
        next = Math.max(120, Math.min(Math.round(window.innerHeight * 0.7), next));
        panel.style.height = next + 'px';
      });
      window.addEventListener('mouseup', function () { drag = null; });
    })();

    S.chart.setBarClickHandler(function (bar) {
      if (!$('#chk-label-mode').checked) return;
      var t = $('#label-type').value;
      S.draftLabels.push({
        structure_type: t,
        bar_index: bar.index,
        price: t.indexOf('LOW') !== -1 || t.indexOf('DOWN') !== -1 ? bar.low : bar.high,
        notes: ''
      });
      S.labelDirty = true;
      renderDraftLabels();
      persistDraft();
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
