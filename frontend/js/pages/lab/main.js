/* Trang Thử nghiệm — khởi động và gắn sự kiện DOM. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;
  var S = L.S;

  /**
   * Lớp phụ thuộc lớp khác: phần tử có `data-requires="<lớp>"` bị vô hiệu khi lớp đó tắt — input → `disabled`;
   * phần tử khác (label) → làm mờ (class `is-disabled`) và vô hiệu mọi input bên trong. Chung cho mọi khung lớp,
   * không biết thuật toán nào; giá trị riêng của lớp con giữ nguyên (plugin tự quyết có vẽ hay không).
   */
  function syncLayerRequires() {
    $$('[data-requires]').forEach(function (el) {
      var on = !!S.layers[el.getAttribute('data-requires')];
      if (el.tagName === 'INPUT') { el.disabled = !on; return; }
      el.classList.toggle('is-disabled', !on);
      Array.prototype.forEach.call(el.querySelectorAll('input'), function (i) { i.disabled = !on; });
    });
  }

  /** Áp trạng thái lớp (mặc định plugin khai báo) lên checkbox — trình duyệt có thể khôi phục ô đã tick từ lần
   * trước khi tải lại trang. Lớp không plugin nào khai báo thì lấy theo checkbox. */
  function syncLayerInputs() {
    $$('input[data-layer]').forEach(function (cb) {
      var k = cb.getAttribute('data-layer');
      if (Object.prototype.hasOwnProperty.call(S.layers, k)) cb.checked = !!S.layers[k];
      else S.layers[k] = cb.checked;
    });
    syncLayerRequires();
  }

  /** Bật/tắt một lớp từ code (vd lớp bật sẵn khi replay, baseline): S.layers + checkbox + lớp phụ thuộc. */
  function setLayer(name, on) {
    S.layers[name] = !!on;
    $$('input[data-layer="' + name + '"]').forEach(function (cb) { cb.checked = !!on; });
    syncLayerRequires();
  }

  async function init() {
    S.chart = new window.MarketChart($('#chart'), $('#chart-tooltip'));
    MSL.algos.each('bindChart', S.chart);   // vd DC: ghi chú «chữ nhãn đang ẩn vì zoom xa»
    syncLayerInputs();

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
        await L.stopReplay();                    // rời replay / live hiện tại
        L.switchMode(m);
        if (m === 'replay') {
          await L.enterReplay();
        } else if (m === 'live') {
          await L.enterLive();
        } else {
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
        if (t.getAttribute('data-tab') === 'stats' && L.replaying() && S.replay.live) L.renderLiveStats(S.replay);
      });
    });

    $$('#layer-toggles input[data-layer], #dc-layers input[data-layer], #ict-layers input[data-layer]').forEach(function (cb) {
      cb.addEventListener('change', function () {
        S.layers[cb.getAttribute('data-layer')] = cb.checked;
        syncLayerRequires();
        L.applyChartEvents();
        var rp = L.replaying(), cur = rp || S.run;
        if (cur) L.renderAlgoNotes(S.algo && S.algo.name, rp ? null : cur.stats,
          rp ? (cur.snapshot || {}).data_status : cur.data_status,
          rp ? (cur.snapshot || {}).pending_state : cur.pending_state);
      });
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
      L.renderEvents(L.replaying() ? S.replay.events : (S.run ? S.run.events : []));
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
      if (S.replay && !S.replay.live && navigator.sendBeacon) {
        navigator.sendBeacon('/api/replay/' + S.replay.sid + '/close');
      }
    });

    L.bindLive();
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
  L.syncLayerRequires = syncLayerRequires;

  document.addEventListener('DOMContentLoaded', init);
})(window.MSL);
