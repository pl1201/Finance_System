/* Trang Thử nghiệm — dataset: danh sách, chọn, xem trước nến, thông tin/chất lượng, đổi khung, khoảng thời gian. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var TF_ORDER = MSL.tf.ORDER;
  var TF_SEC = MSL.tf.SEC;
  var detectDigits = MSL.format.detectDigits;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var DEFAULT_MAX_BARS = L.DEFAULT_MAX_BARS;
  var HEAVY_RUN_BARS = L.HEAVY_RUN_BARS;
  var S = L.S;

  async function loadDatasets(keepId) {
    S.datasets = await API.datasets();
    var sel = $('#dataset-select');
    if (!S.datasets.length) {
      sel.innerHTML = '<option value="">— chưa có dataset —</option>';
      S.dataset = null;
      renderDatasetInfo();
      $('#btn-run').disabled = true;
      L.banner('info', 'Chưa có dataset nào. Bấm <strong>Tạo dữ liệu mẫu</strong> để sinh bộ dữ liệu MÔ PHỎNG, hoặc <strong>Nhập CSV…</strong> để nạp dữ liệu của bạn.');
      return;
    }
    // Gom theo mã → khung → tên, ẩn sẵn dataset phụ (lib/dataset_picker.js). Mở lại trang thì quay về dataset đang làm
    // dở, nếu nó còn tồn tại — nếu không, bộ nháp nhãn đã khôi phục sẽ nằm ở dataset người dùng không nhìn thấy và trông
    // như bị mất. Mặc định: dataset mới nhất không bị ẩn.
    function exists(id) {
      return !!id && S.datasets.some(function (d) { return d.id === id; });
    }
    var remembered = window.LabelDraft.lastDataset();
    MSL.datasetPicker.render(sel, S.datasets, { keep: [keepId, remembered].filter(exists) });
    var firstShown = S.datasets.filter(function (d) { return !MSL.datasetPicker.hiddenReason(d); })[0] || S.datasets[0];
    var target = exists(keepId) ? keepId : (exists(remembered) ? remembered : firstShown.id);
    MSL.datasetPicker.select(sel, target);
    await selectDataset(target);
  }

  /** «XAUUSD M1 · HistData 2024 · giờ đã sửa … · 355652 nến» (lib/dataset_picker.js). */
  function datasetLabel(d) {
    return MSL.datasetPicker.label(d);
  }

  async function selectDataset(id, opts) {
    opts = opts || {};
    var keepStart = opts.keepRange ? $('#range-start').value : '';
    var keepEnd = opts.keepRange ? $('#range-end').value : '';
    S.dataset = S.datasets.filter(function (d) { return d.id === id; })[0] || null;
    S.baseline = null;
    L.syncTimeframeParam();
    renderDatasetInfo();
    resetRangeInputs();
    if (opts.keepRange && keepStart && keepEnd && S.dataset) {
      var lo = L.toLocalInput(S.dataset.start_time);
      var hi = L.toLocalInput(S.dataset.end_time);
      var ks = keepStart > lo ? keepStart : lo;
      var ke = keepEnd < hi ? keepEnd : hi;
      if (ks < ke) {                     // không trùng khoảng → giữ khoảng mặc định của dataset mới
        $('#range-start').value = ks;
        $('#range-end').value = ke;
      }
    }
    $('#btn-run').disabled = !S.dataset;
    S.run = null;
    $('#btn-replay-here').hidden = true;
    S.allBars = [];
    await L.stopReplay();
    if (S.mode !== 'full') L.switchMode('full');
    L.applyChartEvents();                 // chưa có kết quả → ẩn + xoá khung riêng (khung phụ, panel baseline) trước khi nạp nến mới
    $('#btn-export-csv').disabled = true;
    $('#btn-export-png').disabled = true;
    L.renderEvents([]);
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
    L.loadDraftForDataset();
    await L.refreshLabelSetPicker();
    if ($('#chk-history-current-ds').checked) await L.loadRuns();
  }

  async function previewDatasetBars() {
    try {
      var barsRes = await API.bars(
        S.dataset.id,
        L.fromLocalInput($('#range-start').value),
        L.fromLocalInput($('#range-end').value)
      );
      S.allBars = barsRes.bars || [];
      S.digits = detectDigits(S.allBars);
      S.chart.setDigits(S.digits);
      S.chart.setBars(S.allBars);
      S.chart.setEvents([], [], { layers: S.layers });
      S.chart.showLast(350);
      $('#chart-empty').hidden = true;
      MSL.algos.each('syncLegend', [], [], S);   // chưa có kết quả → mọi chú giải riêng dưới chart ẩn
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

  /** Khoảng đang chọn ở ô Từ/Đến (ISO) — để đổi khung nhảy đúng dataset chứa khoảng đó. */
  function rangeFocus() {
    var a = L.fromLocalInput($('#range-start').value);
    var b = L.fromLocalInput($('#range-end').value);
    return a && b ? { start: a, end: b } : null;
  }

  function findSiblingDataset(symbol, tf, current) {
    return MSL.tf.findSibling(S.datasets, symbol, tf, current, rangeFocus());
  }

  function findFinerSource(symbol, targetTf, current) {
    var need = TF_SEC[targetTf];
    if (!need) return null;
    // M1 không làm nguồn tổng hợp tự động (mỗi dataset ~350 nghìn nến) — giữ như trước khi thanh
    // khung có M1; muốn tổng hợp từ M1 thì mở dataset M1 rồi dùng «Tổng hợp nến…».
    var cands = S.datasets.filter(function (d) {
      return d.symbol === symbol && d.timeframe !== 'M1' && TF_SEC[d.timeframe] && TF_SEC[d.timeframe] < need;
    });
    if (!cands.length) return null;
    cands.sort(function (a, b) {
      var aSyn = current && !!a.is_synthetic === !!current.is_synthetic ? 0 : 1;
      var bSyn = current && !!b.is_synthetic === !!current.is_synthetic ? 0 : 1;
      if (aSyn !== bSyn) return aSyn - bSyn;
      return TF_SEC[a.timeframe] - TF_SEC[b.timeframe];
    });
    // Cùng loại + cùng khung với ứng viên đầu: chọn dataset chứa khoảng đang xem (dữ liệu chia đoạn).
    var top = cands.filter(function (d) {
      return d.timeframe === cands[0].timeframe && !!d.is_synthetic === !!cands[0].is_synthetic;
    });
    return MSL.tf.pickByTime(top, current, rangeFocus());
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
      } else if (dstSec > srcSec && MSL.tf.RESAMPLE.indexOf(tf) !== -1) {
        cls += ' up';
        title = 'Tổng hợp từ ' + cur.timeframe + ' lên ' + tf;
      } else if (dstSec > srcSec) {
        cls += ' down';
        title = 'Chưa có dataset ' + tf + ' cùng ' + cur.symbol + '. Lab không tự tổng hợp ' + tf +
          ' (nến ngày mở lúc 17:00 New York) — nhập từ market-data-pipeline.';
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
      var f = rangeFocus();
      var covers = !f || (Date.parse(sib.start_time) <= Date.parse(f.end) && Date.parse(sib.end_time) >= Date.parse(f.start));
      MSL.datasetPicker.select($('#dataset-select'), sib.id);
      await selectDataset(sib.id, { keepRange: true });
      L.banner(covers ? 'ok' : 'warn', 'Đã chuyển từ <strong>' + esc(fromTf) + '</strong> sang dataset <strong>' +
        esc(datasetLabel(sib)) + '</strong>. Đây là dữ liệu có sẵn — không tách nến ' + esc(fromTf) + ' thành ' + esc(tf) + '.' +
        (covers ? '' : ' Dataset này <strong>không chứa khoảng đang xem</strong> — đã dùng khoảng mặc định của nó; chọn dataset ' +
          esc(tf) + ' khác trong danh sách nếu cần.'));
      return;
    }
    var srcSec = TF_SEC[S.dataset.timeframe] || 0;
    var dstSec = TF_SEC[tf] || 0;
    if (dstSec > srcSec && MSL.tf.RESAMPLE.indexOf(tf) !== -1) {
      L.openResampleModal(tf);
      return;
    }
    if (dstSec > srcSec) {
      L.banner('error', 'Chưa có dataset <strong>' + esc(S.dataset.symbol) + ' ' + esc(tf) + '</strong>. Lab không tự tổng hợp ' +
        esc(tf) + ' (nến ngày của dữ liệu thật mở lúc 17:00 New York) — nhập dataset ' + esc(tf) + ' từ market-data-pipeline.');
      return;
    }
    var finer = findFinerSource(S.dataset.symbol, tf, S.dataset);
    if (finer) {
      try {
        L.loading(true);
        var out = await API.resample({
          dataset_id: finer.id,
          target_timeframe: tf,
          gap_policy: 'drop_incomplete'
        });
        await loadDatasets(out.dataset.id);
        L.banner('ok', 'Đã tạo khung <strong>' + esc(tf) + '</strong> bằng cách tổng hợp từ <strong>' +
          esc(finer.symbol) + ' ' + esc(finer.timeframe) + '</strong> (' + out.dataset.row_count + ' nến).');
      } catch (e) {
        L.banner('error', esc(e.message));
      } finally {
        L.loading(false);
      }
      return;
    }
    L.banner('error', 'Không tách được nến <strong>' + esc(S.dataset.timeframe) + '</strong> thành <strong>' +
      esc(tf) + '</strong>. Hãy chọn dataset ' + esc(tf) + ' cùng symbol (ví dụ dữ liệu mẫu XAUUSD M5) hoặc nhập CSV/MT5 khung nhỏ.');
  }

  /** Ước lượng số nến trong khoảng đang chọn — theo tỷ lệ thời gian trên số nến của dataset. */
  function estimateRangeBars() {
    var d = S.dataset;
    if (!d || !d.row_count) return 0;
    var t0 = Date.parse(d.start_time), t1 = Date.parse(d.end_time);
    if (!(t1 > t0)) return d.row_count;
    var a = Date.parse(L.fromLocalInput($('#range-start').value) || d.start_time);
    var b = Date.parse(L.fromLocalInput($('#range-end').value) || d.end_time);
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
    $('#range-start').value = L.toLocalInput(start);
    $('#range-end').value = L.toLocalInput(S.dataset.end_time);
    renderRangeHint();
  }

  /** Nút «Dùng toàn bộ khoảng dữ liệu»: đúng toàn bộ, kể cả dataset dài (gợi ý sẽ cảnh báo). */
  function useFullRange() {
    if (!S.dataset) return;
    $('#range-start').value = L.toLocalInput(S.dataset.start_time);
    $('#range-end').value = L.toLocalInput(S.dataset.end_time);
    renderRangeHint();
  }

  function confirmHeavyRange(action) {
    var est = estimateRangeBars();
    if (est <= HEAVY_RUN_BARS) return true;
    return window.confirm('Khoảng đang chọn có khoảng ' + est.toLocaleString('vi-VN') + ' nến. ' + action +
      ' trên khoảng này có thể tạo kết quả hàng trăm MB và làm trình duyệt chậm hoặc treo.\n\nVẫn tiếp tục?');
  }

  L.confirmHeavyRange = confirmHeavyRange;
  L.loadDatasets = loadDatasets;
  L.renderDatasetInfo = renderDatasetInfo;
  L.renderRangeHint = renderRangeHint;
  L.selectDataset = selectDataset;
  L.useFullRange = useFullRange;
})(window.MSL);
