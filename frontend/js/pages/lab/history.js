/* Trang Thử nghiệm — tab Lịch sử chạy: danh sách, mở lại (kiểm tái lập), xoá, so sánh hai run. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var detectDigits = MSL.format.detectDigits;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var S = L.S;

  async function loadRuns() {
    var onlyCurrent = $('#chk-history-current-ds').checked && S.dataset;
    S.runs = await API.runs(onlyCurrent ? S.dataset.id : null);
    renderRuns();
  }

  /** Thuật toán của lần chạy còn trong registry không (thuật toán đã gỡ: run cũ vẫn trong kho). */
  function algorithmKnown(name) {
    return (S.algorithms || []).some(function (a) { return a.name === name; });
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
        '<td>' + esc(r.algorithm) + ' v' + esc(r.algorithm_version) +
          (algorithmKnown(r.algorithm) ? '' : ' <span class="pill" title="Thuật toán đã gỡ khỏi lab: chỉ còn dữ liệu, không mở lại được trên chart">đã gỡ</span>') + '</td>' +
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
    L.loading(true);
    try {
      await L.stopReplay();
      var saved = await API.getRun(runId);
      if (!algorithmKnown(saved.algorithm)) {
        L.banner('warn', 'Lần chạy <code>' + esc(runId) + '</code> dùng thuật toán <code>' + esc(saved.algorithm) +
          '</code> đã gỡ khỏi lab, nên không mở lại được trên chart. Dữ liệu lần chạy vẫn còn trong kho.');
        return;
      }
      if (S.dataset && S.dataset.id !== saved.dataset_id) {
        var ds = S.datasets.filter(function (d) { return d.id === saved.dataset_id; })[0];
        if (!ds) throw new Error('Dataset của lần chạy này đã bị xoá, không mở lại được chart.');
        MSL.datasetPicker.select($('#dataset-select'), ds.id);
        S.dataset = ds;
        L.renderDatasetInfo();
      }
      $('#range-start').value = L.toLocalInput(saved.range_start);
      $('#range-end').value = L.toLocalInput(saved.range_end);
      L.selectAlgorithm(saved.algorithm);
      Object.keys(saved.params || {}).forEach(function (k) {
        var el = $('#param-' + k);
        if (!el) return;
        if (el.type === 'checkbox') el.checked = !!saved.params[k];
        else el.value = saved.params[k];
      });
      L.applyParamVisibility();
      S.baseline = null;
      S.selectedEventId = null;
      L.renderEventDetail(null);
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
      L.applyChartEvents();
      S.chart.showLast(350);
      $('#chart-empty').hidden = true;
      $('#btn-export-csv').disabled = false;
      $('#btn-export-png').disabled = false;
      L.renderEvents(fresh.events);
      L.renderStats(Object.assign({}, fresh, { run_id: saved.run_id, created_at: saved.created_at, saved: true }));
      L.renderAlgoNotes(fresh.algorithm, fresh.stats, fresh.data_status, fresh.pending_state);
      $('#synthetic-watermark').hidden = !saved.is_synthetic;

      var same = (saved.events || []).length === fresh.events.length &&
        (saved.events || []).every(function (e, i) {
          var f = fresh.events[i];
          return f && e.event_id === f.event_id && Math.abs(e.price - f.price) < 1e-9 &&
                 e.confirmed_bar_index === f.confirmed_bar_index;
        });
      L.banner(same ? 'ok' : 'warn',
        same
          ? 'Đã mở lại <code>' + esc(runId) + '</code>. <strong>Kiểm tra tái lập: khớp hoàn toàn</strong> — chạy lại cùng dataset và tham số cho đúng ' + fresh.events.length + ' sự kiện như bản đã lưu.'
          : 'Đã mở lại <code>' + esc(runId) + '</code> nhưng <strong>kết quả chạy lại KHÁC bản đã lưu</strong> (' + (saved.events || []).length + ' so với ' + fresh.events.length + ' sự kiện). Kiểm tra xem dataset hoặc phiên bản thuật toán có thay đổi không.');
    } catch (e) {
      L.banner('error', 'Không mở lại được lần chạy: ' + esc(e.message));
    } finally {
      L.loading(false);
    }
  }

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

  L.doCompare = doCompare;
  L.loadRuns = loadRuns;
})(window.MSL);
