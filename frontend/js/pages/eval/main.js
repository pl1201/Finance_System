/* Trang Đánh giá — khởi động và gắn sự kiện DOM. */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var S = E.S;

  async function boot() {
    try {
      var h = await API.health();
      $('#health-pill').textContent = 'Backend OK · v' + h.version;
      $('#health-pill').className = 'pill pill-ok';
    } catch (e) {
      $('#health-pill').textContent = 'Backend lỗi';
      $('#health-pill').className = 'pill pill-bad';
    }
    try { S.meta = await API.evalMeta(); } catch (e) { S.meta = { targets: [] }; }
    E.syncTargetOptions();
    E.updateTargetHelp();
    S.chart = new MarketChart($('#eval-chart'), $('#eval-tooltip'));
    S.datasets = await API.datasets();
    E.renderDatasets();
    await E.loadSaved();
    bind();
    var params = new URLSearchParams(location.search || '');
    var dsQ = params.get('dataset_id');
    if (dsQ) {
      $('#dataset-select').value = dsQ;
      try { await E.onDatasetChange(); } catch (e) { E.showError(e.message); }
    }
    var lsQ = params.get('label_set_id');
    if (lsQ) $('#label-set-select').value = lsQ;
    var hash = (location.hash || '').replace(/^#/, '');
    if (hash.indexOf('ev_') === 0) {
      try { await E.openSaved(hash); } catch (e) { E.showError(e.message); }
    }
  }

  function bind() {
    $('#dataset-select').addEventListener('change', function () { E.onDatasetChange().catch(function (e) { E.showError(e.message); }); });
    $('#target-select').addEventListener('change', E.updateTargetHelp);
    $('#chk-map-l1').addEventListener('change', E.updateTargetHelp);
    $('#chk-map-dc').addEventListener('change', E.updateTargetHelp);
    $('#btn-evaluate').addEventListener('click', function () { E.evaluate(); });
    $('#btn-export').addEventListener('click', function () {
      if (!S.result || !S.result.evaluation_id) return;
      window.location.href = API.evaluationReportUrl(S.result.evaluation_id);
    });
    $('#run-picker-table').addEventListener('change', function (ev) {
      var t = ev.target;
      if (!t.classList.contains('run-ck')) return;
      S.selectedIds[t.getAttribute('data-id')] = t.checked;
      $('#run-picker-count').textContent = E.checkedRunIds().length + ' / ' + S.runs.length + ' đã chọn';
      E.fillBaselineSelect();
    });
    $('#compare-table').addEventListener('click', function (ev) {
      var tr = ev.target.closest('tr[data-id]');
      if (tr) E.selectRun(tr.getAttribute('data-id'));
    });
    $('#compare-table').addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
      ev.preventDefault();
      var ids = E.scoredRuns().map(function (r) { return r.run_id; });
      var i = ids.indexOf(S.selectedRunId);
      if (ev.key === 'ArrowDown') i = Math.min(ids.length - 1, i + 1);
      else i = Math.max(0, i - 1);
      if (ids[i]) E.selectRun(ids[i]);
    });
    $('#scatter').addEventListener('click', function (ev) {
      var pt = ev.target.closest('[data-id]');
      if (pt) E.selectRun(pt.getAttribute('data-id'));
    });
    $('#scatter').addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
      ev.preventDefault();
      var ids = E.scoredRuns().map(function (r) { return r.run_id; });
      var i = ids.indexOf(S.selectedRunId);
      if (ev.key === 'ArrowRight') i = Math.min(ids.length - 1, i + 1);
      else i = Math.max(0, i - 1);
      if (ids[i]) E.selectRun(ids[i]);
    });
    $$('#detail-tabs .tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('#detail-tabs .tab').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        $$('.dtab-panel').forEach(function (p) {
          p.classList.toggle('active', p.getAttribute('data-dpanel') === btn.getAttribute('data-dtab'));
        });
      });
    });
    $('#evt-table').addEventListener('click', function (ev) {
      var tr = ev.target.closest('tr[data-role]');
      if (!tr) return;
      E.jumpToEvent({
        role: tr.getAttribute('data-role'),
        bar: tr.getAttribute('data-bar'),
        event_id: tr.getAttribute('data-eid'),
        label_seq: tr.getAttribute('data-seq')
      });
    });
    ['flt-tp', 'flt-fp', 'flt-fn', 'evt-search'].forEach(function (id) {
      $('#' + id).addEventListener('input', E.renderEventTable);
      $('#' + id).addEventListener('change', E.renderEventTable);
    });
    $('#saved-table').addEventListener('click', function (ev) {
      var btn = ev.target.closest('.btn-open-ev');
      var tr = ev.target.closest('tr[data-id]');
      var id = (btn && btn.getAttribute('data-id')) || (tr && tr.getAttribute('data-id'));
      if (id) E.openSaved(id).catch(function (e) { E.showError(e.message); });
    });
  }

  boot().catch(function (e) { E.showError(e.message || String(e)); });
})(window.MSL);
