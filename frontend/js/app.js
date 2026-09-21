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
    layers: { swing: true, swing_l2: true, hhll: true, eq: true, levels: true, bos: true, choch: true },
    chart: null,
    draftLabels: [],
    labelSetId: null
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
    var sel = $('#algo-select');
    sel.innerHTML = S.algorithms
      .map(function (a) { return '<option value="' + esc(a.name) + '">' + esc(a.display_name_vi) + ' (v' + esc(a.version) + ')</option>'; })
      .join('');
    selectAlgorithm(S.algorithms[0] ? S.algorithms[0].name : null);
  }

  function selectAlgorithm(name) {
    S.algo = S.algorithms.filter(function (a) { return a.name === name; })[0] || null;
    if (!S.algo) return;
    $('#algo-select').value = S.algo.name;
    $('#algo-desc').textContent = S.algo.description_vi;
    $('#algo-desc').title = S.algo.description_vi || '';
    var hint = $('#layer-hint');
    if (S.algo.name === 'swing_hierarchy') {
      hint.textContent = 'Cấp 2 = ô vuông. HH/LH chỉ so hai đỉnh/đáy cấp 2 liên tiếp. Không gồm BOS. Đường mức = cấp 2 gần nhất.';
    } else if (S.algo.name === 'swing_pivot') {
      hint.textContent = 'HH/LH so từng đỉnh cấp 1. BOS/CHoCH là sự kiện phá vỡ riêng — không trộn với nhãn HH.';
    } else {
      hint.textContent = 'Bật/tắt lớp marker cho lần chạy hiện tại. Replay vẫn chỉ hiện sự kiện đã xác nhận tại con trỏ.';
    }
    renderParamForm();
  }

  function renderParamForm() {
    var box = $('#param-form');
    if (!S.algo) { box.innerHTML = ''; return; }
    box.innerHTML = S.algo.params.map(function (p) {
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
    }).join('');
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
    var target = (keepId && S.datasets.some(function (d) { return d.id === keepId; })) ? keepId : S.datasets[0].id;
    sel.value = target;
    await selectDataset(target);
  }

  async function selectDataset(id, opts) {
    opts = opts || {};
    var keepStart = opts.keepRange ? $('#range-start').value : '';
    var keepEnd = opts.keepRange ? $('#range-end').value : '';
    S.dataset = S.datasets.filter(function (d) { return d.id === id; })[0] || null;
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
    S.allBars = [];
    await stopReplay();
    if (S.mode !== 'full') switchMode('full');
    $('#btn-export-csv').disabled = true;
    $('#btn-export-png').disabled = true;
    renderEvents([]);
    $('#stats-body').innerHTML = '<p class="muted">Chưa chạy lần nào trên dataset này.</p>';
    $('#synthetic-watermark').hidden = !(S.dataset && S.dataset.is_synthetic);
    if (S.dataset) {
      await previewDatasetBars();
    } else {
      S.chart.setBars([]);
      $('#chart-empty').hidden = false;
    }
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

  function resetRangeInputs() {
    if (!S.dataset) { $('#range-start').value = ''; $('#range-end').value = ''; return; }
    $('#range-start').value = toLocalInput(S.dataset.start_time);
    $('#range-end').value = toLocalInput(S.dataset.end_time);
  }

  // ----------------------------------------------------------------- chạy thử

  async function doRun() {
    if (!S.dataset) return;
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

      S.chart.setDigits(S.digits);
      S.chart.setBars(S.allBars);
      applyChartEvents();
      S.chart.showLast(350);

      $('#chart-empty').hidden = true;
      $('#btn-export-csv').disabled = !res.saved;
      $('#btn-export-png').disabled = false;
      renderEvents(res.events);
      renderStats(res);

      if (res.data_status !== 'OK') {
        banner('warn', esc(res.data_status_message_vi));
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

  function applyChartEvents() {
    if (S.mode === 'replay' && S.replay) {
      S.chart.setEvents(S.replay.events, S.replay.timeline, {
        layers: S.layers, markerAtConfirm: false, replayCursor: S.replay.cursor
      });
    } else if (S.run) {
      S.chart.setEvents(S.run.events, S.run.timeline, {
        layers: S.layers, markerAtConfirm: $('#chk-confirm-position').checked, replayCursor: null
      });
    }
    var legend = $('#chart-legend');
    if (!legend) return;
    var evs = (S.mode === 'replay' && S.replay) ? S.replay.events : (S.run ? S.run.events : []);
    var hasL2 = (evs || []).some(function (e) {
      return e.structure_type === 'SWING_HIGH_L2' || e.structure_type === 'SWING_LOW_L2';
    });
    legend.hidden = !hasL2;
  }

  // ----------------------------------------------------------------- bảng sự kiện

  function renderEvents(events) {
    var tbody = $('#events-table tbody');
    var filter = ($('#event-filter').value || '').trim().toUpperCase();
    var list = (events || []).filter(function (e) {
      return !filter || e.structure_type.indexOf(filter) >= 0 || (e.reason_code || '').indexOf(filter) >= 0;
    });
    $('#event-count').textContent = list.length + ' / ' + (events || []).length + ' sự kiện';
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="empty-cell">' +
        ((events && events.length) ? 'Không có sự kiện khớp bộ lọc.' : 'Chưa có sự kiện.') + '</td></tr>';
      return;
    }
    var d = S.digits;
    tbody.innerHTML = list.slice(0, 3000).map(function (e, i) {
      return '<tr data-ev="' + i + '">' +
        '<td class="num">' + (i + 1) + '</td>' +
        '<td><span class="badge b-' + esc(e.structure_type) + '">' + esc(e.structure_type) + '</span></td>' +
        '<td class="num">' + Number(e.price).toFixed(d) + '</td>' +
        '<td class="num">' + e.event_bar_index + '</td>' +
        '<td class="mono">' + fmtIso(e.event_time) + '</td>' +
        '<td class="num">' + e.confirmed_bar_index + '</td>' +
        '<td class="mono">' + fmtIso(e.confirmed_at) + '</td>' +
        '<td class="num">' + e.confirmation_lag_bars + '</td>' +
        '<td class="mono">' + esc(e.reason_code) + '</td>' +
        '<td class="mono">' + esc(e.reference_event_id || '—') + '</td>' +
        '</tr>';
    }).join('');
    if (list.length > 3000) {
      tbody.innerHTML += '<tr><td colspan="10" class="empty-cell">Hiển thị 3000 dòng đầu; xuất CSV để xem đầy đủ.</td></tr>';
    }
    Array.prototype.forEach.call(tbody.querySelectorAll('tr[data-ev]'), function (tr) {
      tr.addEventListener('click', function () {
        Array.prototype.forEach.call(tbody.querySelectorAll('tr'), function (r) { r.classList.remove('selected'); });
        tr.classList.add('selected');
        S.chart.focusEvent(list[parseInt(tr.getAttribute('data-ev'), 10)]);
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
    $('#stats-body').innerHTML = html;

    function box(k, v) {
      return '<div class="stat-box"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
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
      renderStats(Object.assign({}, fresh, { run_id: saved.run_id, created_at: saved.created_at }));
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

  async function enterReplay() {
    if (!S.dataset) { banner('warn', 'Chọn dataset trước khi replay.'); switchMode('full'); return; }
    loading(true);
    try {
      var snap = await API.replayCreate({
        dataset_id: S.dataset.id,
        algorithm: S.algo.name,
        params: collectParams(),
        range_start: fromLocalInput($('#range-start').value),
        range_end: fromLocalInput($('#range-end').value)
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
        renderedCursor: -2
      };
      S.digits = detectDigits(barsRes.bars);
      S.chart.setDigits(S.digits);
      $('#rp-slider').min = -1;
      $('#rp-slider').max = String(barsRes.bars.length - 1);
      $('#rp-slider').value = String(snap.cursor);
      $('#chart-empty').hidden = true;
      $('#btn-export-png').disabled = false;
      $('#btn-export-csv').disabled = true;
      renderReplay();
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

    renderEvents(r.events);
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
    html += '<div class="info-card"><dl>' +
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
    $('#stats-body').innerHTML = html;
  }

  async function replayAction(fn) {
    if (!S.replay) return;
    try {
      var snap = await fn(S.replay.sid);
      S.replay.snapshot = snap;
      S.replay.cursor = snap.cursor;
      S.replay.events = snap.events;
      S.replay.timeline = snap.timeline;
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
      await replayAction(function (sid) { return API.replayStep(sid, 1); });
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

  function switchMode(mode) {
    S.mode = mode;
    $$('.mode-btn').forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-mode') === mode); });
    $('#replay-bar').hidden = mode !== 'replay';
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

  function renderDraftLabels() {
    var tb = $('#labels-table tbody');
    if (!S.draftLabels.length) {
      tb.innerHTML = '<tr><td colspan="6" class="empty-cell">Chưa có nhãn.</td></tr>';
      return;
    }
    tb.innerHTML = S.draftLabels.map(function (lb, i) {
      return '<tr><td>' + i + '</td><td><span class="badge b-' + esc(lb.structure_type) + '">' +
        esc(lb.structure_type) + '</span></td><td class="num">' + lb.bar_index +
        '</td><td class="num">' + lb.price + '</td><td>' + esc(lb.notes || '') +
        '</td><td><button type="button" class="btn btn-link btn-sm" data-del-label="' + i + '">xoá</button></td></tr>';
    }).join('');
    $$('#labels-table [data-del-label]').forEach(function (b) {
      b.addEventListener('click', function () {
        S.draftLabels.splice(parseInt(b.getAttribute('data-del-label'), 10), 1);
        renderDraftLabels();
      });
    });
  }

  async function saveLabels() {
    if (!S.dataset) { banner('error', 'Chọn dataset.'); return; }
    try {
      var ls = await API.saveLabelSet({
        dataset_id: S.dataset.id,
        annotator: $('#label-annotator').value,
        version: $('#label-version').value,
        rubric_vi: $('#label-rubric').value,
        labels: S.draftLabels
      });
      S.labelSetId = ls.id;
      banner('ok', 'Đã lưu bộ nhãn ' + esc(ls.id) + ' — người gán: ' + esc(ls.annotator));
    } catch (e) { banner('error', esc(e.message)); }
  }

  async function loadLabelSets() {
    if (!S.dataset) { banner('error', 'Chọn dataset.'); return; }
    try {
      var list = await API.labelSets(S.dataset.id);
      if (!list.length) { banner('warn', 'Dataset này chưa có bộ nhãn.'); return; }
      var id = list[0].id;
      var ls = await API.getLabelSet(id);
      S.draftLabels = ls.labels || [];
      S.labelSetId = ls.id;
      $('#label-annotator').value = ls.annotator;
      $('#label-version').value = ls.version;
      $('#label-rubric').value = ls.rubric_vi;
      renderDraftLabels();
      banner('ok', 'Đã tải bộ ' + esc(ls.id) + ' của ' + esc(ls.annotator));
    } catch (e) { banner('error', esc(e.message)); }
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
    $('#algo-select').addEventListener('change', function (e) { selectAlgorithm(e.target.value); });
    $('#btn-run').addEventListener('click', doRun);
    $('#btn-range-reset').addEventListener('click', resetRangeInputs);

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

    $$('#layer-toggles input[data-layer]').forEach(function (cb) {
      cb.addEventListener('change', function () {
        S.layers[cb.getAttribute('data-layer')] = cb.checked;
        applyChartEvents();
      });
    });
    $('#chk-confirm-position').addEventListener('change', applyChartEvents);

    $('#event-filter').addEventListener('input', function () {
      renderEvents(S.mode === 'replay' && S.replay ? S.replay.events : (S.run ? S.run.events : []));
    });

    $('#rp-fwd').addEventListener('click', function () { pausePlay(); replayAction(function (sid) { return API.replayStep(sid, 1); }); });
    $('#rp-back').addEventListener('click', function () { pausePlay(); replayAction(function (sid) { return API.replayBack(sid, 1); }); });
    $('#rp-reset').addEventListener('click', function () { pausePlay(); replayAction(function (sid) { return API.replayReset(sid); }); });
    $('#rp-play').addEventListener('click', playPause);
    $('#rp-skip-warmup').addEventListener('click', function () {
      if (!S.replay) return;
      pausePlay();
      var need = (S.replay.snapshot && S.replay.snapshot.warmup_bars) || 0;
      var idx = Math.max(0, need - 1);
      replayAction(function (sid) { return API.replaySeek(sid, idx); });
    });
    $('#rp-slider').addEventListener('change', function (e) {
      pausePlay();
      replayAction(function (sid) { return API.replaySeek(sid, parseInt(e.target.value, 10)); });
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
      if (e.key === 'ArrowRight') { e.preventDefault(); pausePlay(); replayAction(function (sid) { return API.replayStep(sid, 1); }); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); pausePlay(); replayAction(function (sid) { return API.replayBack(sid, 1); }); }
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
    $('#btn-load-labels').addEventListener('click', loadLabelSets);
    $('#btn-eval-labels').addEventListener('click', evalLabels);
    $('#btn-clear-draft-labels').addEventListener('click', function () {
      S.draftLabels = []; S.labelSetId = null; renderDraftLabels();
    });
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
      renderDraftLabels();
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
