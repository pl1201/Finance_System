/* Trang Thử nghiệm — khởi động và gắn sự kiện DOM. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;
  var S = L.S;

  /** Bật/tắt một lớp từ code (vd lớp bật sẵn khi replay, baseline): S.layers + checkbox + lớp phụ thuộc (lib/layers.js). */
  function setLayer(name, on) { MSL.layerToggles.set(S.layers, name, on); }

  async function init() {
    S.chart = new window.MarketChart($('#chart'), $('#chart-tooltip'));
    S.pane = new window.PaneHost({ wrap: $('#pane-wrap'), pane: $('#pane'), legend: $('#pane-legend'), chart: S.chart });
    MSL.algos.each('bindChart', S.chart);   // vd DC: ghi chú «chữ nhãn đang ẩn vì zoom xa»
    MSL.layerToggles.syncInputs(S.layers);

    try {
      var h = await API.health();
      $('#health-pill').textContent = 'Backend OK · v' + h.version;
      $('#health-pill').className = 'pill pill-ok';
    } catch (e) {
      $('#health-pill').textContent = 'Backend lỗi';
      $('#health-pill').className = 'pill pill-bad';
      L.banner('error', 'Không kết nối được backend: ' + esc(e.message));
    }

    await L.loadAlgorithms();
    await L.loadDatasets();
    bindEvents();
    await L.loadRuns();
  }

  function bindEvents() {
    $('#dataset-select').addEventListener('change', function (e) { L.selectDataset(e.target.value); });
    $('#algo-select').addEventListener('change', function (e) {
      L.selectAlgorithm(e.target.value);
      if (S.mode === 'replay' && S.replay) L.restartReplayKeepCursor('thuật toán');
    });
    $('#rp-algo').addEventListener('change', function (e) {
      L.selectAlgorithm(e.target.value);
      if (S.mode === 'replay' && S.replay) L.restartReplayKeepCursor('thuật toán');
    });
    $('#param-form').addEventListener('change', function () {
      if (S.mode !== 'replay' || !S.replay) return;
      clearTimeout(S.paramRestartTimer);
      S.paramRestartTimer = setTimeout(function () { L.restartReplayKeepCursor('tham số'); }, 350);
    });
    $('#btn-run').addEventListener('click', L.doRun);
    $('#btn-range-reset').addEventListener('click', L.useFullRange);
    $('#range-start').addEventListener('change', L.renderRangeHint);
    $('#range-end').addEventListener('change', L.renderRangeHint);

    $('#btn-seed').addEventListener('click', async function () {
      var b = $('#btn-seed');
      b.disabled = true; b.textContent = 'Đang tạo…';
      try {
        await API.seedSamples();
        await L.loadDatasets();
        L.banner('ok', 'Đã tạo các dataset <strong>MÔ PHỎNG</strong>. Đây không phải dữ liệu thị trường thật — dùng để thử công cụ.');
      } catch (e) {
        L.banner('error', esc(e.message));
      } finally {
        b.disabled = false; b.textContent = 'Tạo dữ liệu mẫu';
      }
    });

    $('#btn-open-import').addEventListener('click', L.openImport);
    $('#btn-close-import').addEventListener('click', L.closeImport);
    $('#btn-cancel-import').addEventListener('click', L.closeImport);
    $('#import-file').addEventListener('change', L.onPickFile);
    $('#btn-do-import').addEventListener('click', L.doImport);

    $$('.mode-btn').forEach(function (b) {
      b.addEventListener('click', async function () {
        var m = b.getAttribute('data-mode');
        if (m === S.mode) return;
        if (m === 'replay') {
          L.switchMode('replay');
          await L.enterReplay();
        } else {
          await L.stopReplay();
          L.switchMode('full');
          if (S.run) {
            S.chart.setBars(S.allBars);
            L.applyChartEvents();
            S.chart.showLast(350);
            L.renderEvents(S.run.events);
            L.renderStats(S.run);
          } else {
            $('#chart-empty').hidden = false;
            L.applyChartEvents();   // không còn kết quả (replay đã đóng) → ẩn các khung riêng
          }
        }
      });
    });

    var bottom = MSL.bottomPanel.bind({ panel: $('#bottom-panel'), toggle: $('#btn-toggle-bottom'), handle: $('#bottom-resizer') });
    MSL.chatPanel.bind({
      nguon: 'replay', where: 'con trỏ Replay', summaryLabel: 'Tổng hợp tại con trỏ',
      source: function () { return S.mode === 'replay' && S.replay ? { id: S.replay.sid, digits: S.digits } : null; },
      noSource: 'Trợ lý đọc trạng thái thuật toán tại con trỏ Replay — chọn «Replay từng nến» (hoặc bấm «Replay từ đây» ' +
        'trên chart) rồi hỏi.',
      beforeSend: L.pausePlay                       // dừng phát (bước đang chạy dở vẫn xong — nến dữ liệu ghi ở dòng meta)
    });
    $$('.tab[data-tab]').forEach(function (t) {
      t.addEventListener('click', function () {
        bottom.open();
        $$('.tab[data-tab]').forEach(function (x) { x.classList.remove('active'); });
        $$('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
        t.classList.add('active');
        $('.tab-panel[data-panel="' + t.getAttribute('data-tab') + '"]').classList.add('active');
      });
    });

    MSL.layerToggles.bind('#layer-toggles input[data-layer], #dc-layers input[data-layer], #ict-layers input[data-layer]',
      S.layers, function () {
        L.applyChartEvents();
        var cur = S.mode === 'replay' && S.replay ? S.replay : S.run;
        if (cur) L.renderAlgoNotes(S.algo && S.algo.name, S.mode === 'replay' ? null : cur.stats,
          S.mode === 'replay' ? (cur.snapshot || {}).data_status : cur.data_status,
          S.mode === 'replay' ? (cur.snapshot || {}).pending_state : cur.pending_state);
      });
    $('#btn-baseline').addEventListener('click', L.runBaseline);
    $('#chk-split-baseline').addEventListener('change', function () {
      if (this.checked && !S.baseline) {
        L.banner('warn', 'Chưa có run baseline cho dataset/khoảng này — bấm <strong>So sánh baseline (pivot 3/3)</strong> trước.');
      }
      L.renderSplit();
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
      L.pausePlay();
      L.replayAction(function (sid, since) { return API.replayNextEvent(sid, since); });
    });
    $('#chk-confirm-position').addEventListener('change', L.applyChartEvents);

    $('#event-filter').addEventListener('input', function () {
      L.renderEvents(S.mode === 'replay' && S.replay ? S.replay.events : (S.run ? S.run.events : []));
    });

    $('#rp-fwd').addEventListener('click', function () { L.pausePlay(); L.replayAction(function (sid, since) { return API.replayStep(sid, 1, since); }); });
    $('#rp-back').addEventListener('click', function () { L.pausePlay(); L.replayAction(function (sid, since) { return API.replayBack(sid, 1, since); }); });
    $('#btn-replay-here').addEventListener('click', L.replayFromView);
    $('#chk-explain').addEventListener('change', L.renderExplain);
    $('#rp-explain-hide').addEventListener('click', function () { $('#chk-explain').checked = false; L.renderExplain(); });
    $('#rp-reset').addEventListener('click', function () { L.pausePlay(); L.replayAction(function (sid) { return API.replayReset(sid); }); });
    $('#rp-play').addEventListener('click', L.playPause);
    $('#rp-skip-warmup').addEventListener('click', function () {
      if (!S.replay) return;
      L.pausePlay();
      var need = (S.replay.snapshot && S.replay.snapshot.warmup_bars) || 0;
      var idx = Math.max(0, need - 1);
      L.replayAction(function (sid, since) { return API.replaySeek(sid, idx, since); });
    });
    $('#rp-slider').addEventListener('change', function (e) {
      L.pausePlay();
      L.replayAction(function (sid, since) { return API.replaySeek(sid, parseInt(e.target.value, 10), since); });
    });

    $('#btn-reload-runs').addEventListener('click', L.loadRuns);
    $('#chk-history-current-ds').addEventListener('change', L.loadRuns);
    $('#btn-compare').addEventListener('click', L.doCompare);

    $('#btn-export-csv').addEventListener('click', function () {
      if (!S.run || !S.run.run_id) return;
      window.location.href = API.exportUrl(S.run.run_id);
    });
    $('#btn-export-png').addEventListener('click', L.exportPng);
    $('#btn-notes').addEventListener('click', L.toggleNotes);
    L.syncNotesToggle();

    document.addEventListener('keydown', function (e) {
      if (S.mode !== 'replay' || !S.replay) return;
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
      if (e.key === 'ArrowRight') { e.preventDefault(); L.pausePlay(); L.replayAction(function (sid, since) { return API.replayStep(sid, 1, since); }); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); L.pausePlay(); L.replayAction(function (sid, since) { return API.replayBack(sid, 1, since); }); }
      if (e.key === ' ') { e.preventDefault(); L.playPause(); }
    });

    window.addEventListener('beforeunload', function () {
      if (S.replay && navigator.sendBeacon) {
        navigator.sendBeacon('/api/replay/' + S.replay.sid + '/close');
      }
    });

    $('#btn-resample').addEventListener('click', L.doResample);
    $('#btn-close-resample').addEventListener('click', L.closeResampleModal);
    $('#btn-cancel-resample').addEventListener('click', L.closeResampleModal);
    $('#btn-do-resample').addEventListener('click', L.submitResample);
    $('#btn-open-mt5').addEventListener('click', L.openMt5);
    $('#btn-close-mt5').addEventListener('click', L.closeMt5);
    $('#btn-cancel-mt5').addEventListener('click', L.closeMt5);
    $('#btn-do-mt5').addEventListener('click', L.doMt5Import);
    $('#btn-save-labels').addEventListener('click', L.saveLabels);
    $('#btn-update-labels').addEventListener('click', L.updateLabels);
    $('#btn-load-labels').addEventListener('click', L.loadLabelSets);
    $('#btn-eval-labels').addEventListener('click', L.evalLabels);
    $('#btn-export-labels').addEventListener('click', L.exportLabels);
    $('#btn-import-labels').addEventListener('click', function () {
      $('#label-import-file').click();
    });
    $('#label-import-file').addEventListener('change', function (e) {
      var f = e.target.files[0];
      if (f) L.importLabelsCsv(f);
      e.target.value = '';
    });
    $('#btn-clear-draft-labels').addEventListener('click', function () {
      if (L.draftIsDirty() &&
          !window.confirm('Xoá ' + S.draftLabels.length + ' nhãn chưa lưu trong bộ nháp?')) return;
      S.draftLabels = [];
      S.labelSetId = null;
      S.labelDirty = false;
      if (S.dataset) window.LabelDraft.clear(S.dataset.id);
      L.renderDraftLabels();
      L.renderDraftStatus();
    });
    ['#label-annotator', '#label-version', '#label-rubric'].forEach(function (sel) {
      $(sel).addEventListener('change', L.persistDraft);
    });
    // Nhắc lại khi đóng tab mà nháp chưa lưu.
    window.LabelDraft.guardUnload(L.draftIsDirty);
    $('#btn-mql5-compare').addEventListener('click', L.doMql5Compare);


    S.chart.setBarClickHandler(function (bar) {
      if (!$('#chk-label-mode').checked) return;
      var t = $('#label-type').value;
      S.draftLabels.push({
        structure_type: t,
        // Nhãn đếm nến từ đầu dataset (chart có thể chỉ đang xem một khoảng con).
        bar_index: bar.dataset_index !== undefined && bar.dataset_index !== null ? bar.dataset_index : bar.index,
        price: t.indexOf('LOW') !== -1 || t.indexOf('DOWN') !== -1 ? bar.low : bar.high,
        notes: ''
      });
      S.labelDirty = true;
      L.renderDraftLabels();
      L.persistDraft();
    });
  }

  L.setLayer = setLayer;

  document.addEventListener('DOMContentLoaded', init);
})(window.MSL);
