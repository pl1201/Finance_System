/* Lớp gọi API backend. Mọi lỗi được ném ra dưới dạng Error có thông điệp tiếng Việt. */
(function (global) {
  'use strict';

  async function request(method, url, body, isForm) {
    const opts = { method, headers: {} };
    if (body !== undefined && body !== null) {
      if (isForm) {
        opts.body = body;
      } else {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
      }
    }
    let res;
    try {
      res = await fetch(url, opts);
    } catch (e) {
      throw new Error('Không kết nối được backend (' + url + '). Kiểm tra tiến trình uvicorn còn chạy không.');
    }
    const ct = res.headers.get('content-type') || '';
    if (!res.ok) {
      let msg = 'Lỗi ' + res.status;
      if (ct.includes('application/json')) {
        try {
          const j = await res.json();
          if (typeof j.detail === 'string') msg = j.detail;
          else if (Array.isArray(j.detail)) msg = j.detail.map(d => (d.loc || []).join('.') + ': ' + d.msg).join('; ');
          else msg = JSON.stringify(j);
        } catch (e) { /* giữ msg mặc định */ }
      } else {
        try { msg = (await res.text()).slice(0, 400) || msg; } catch (e) { /* bỏ qua */ }
      }
      throw new Error(msg);
    }
    if (ct.includes('application/json')) return res.json();
    return res.text();
  }

  global.API = {
    health: () => request('GET', '/api/health'),
    algorithms: () => request('GET', '/api/algorithms'),

    datasets: () => request('GET', '/api/datasets'),
    dataset: (id) => request('GET', '/api/datasets/' + encodeURIComponent(id)),
    deleteDataset: (id) => request('DELETE', '/api/datasets/' + encodeURIComponent(id)),
    bars: (id, start, end) => {
      const q = new URLSearchParams();
      if (start) q.set('start', start);
      if (end) q.set('end', end);
      const qs = q.toString();
      return request('GET', '/api/datasets/' + encodeURIComponent(id) + '/bars' + (qs ? '?' + qs : ''));
    },
    seedSamples: () => request('POST', '/api/datasets/seed-samples'),
    previewCsv: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return request('POST', '/api/datasets/preview', fd, true);
    },
    importCsv: (formData) => request('POST', '/api/datasets/import', formData, true),

    run: (payload) => request('POST', '/api/runs', payload),
    runs: (datasetId, limit) => request('GET', '/api/runs?' + (datasetId ? 'dataset_id=' + encodeURIComponent(datasetId) + '&' : '') +
      (limit ? 'limit=' + limit : '')),
    getRun: (id) => request('GET', '/api/runs/' + encodeURIComponent(id)),
    deleteRun: (id) => request('DELETE', '/api/runs/' + encodeURIComponent(id)),
    exportUrl: (id) => '/api/runs/' + encodeURIComponent(id) + '/export.csv',
    compare: (a, b) => request('POST', '/api/compare', { run_id_a: a, run_id_b: b }),
    resample: (payload) => request('POST', '/api/datasets/resample', payload),
    mt5Status: () => request('GET', '/api/mt5/status'),
    importMt5: (payload) => request('POST', '/api/datasets/import-mt5', payload),
    saveLabelSet: (payload) => request('POST', '/api/label-sets', payload),
    labelSets: (datasetId) => request('GET', '/api/label-sets' + (datasetId ? '?dataset_id=' + encodeURIComponent(datasetId) : '')),
    getLabelSet: (id) => request('GET', '/api/label-sets/' + encodeURIComponent(id)),
    updateLabelSet: (id, payload) => request('PUT', '/api/label-sets/' + encodeURIComponent(id), payload),
    labelSetExportUrl: (id) => '/api/label-sets/' + encodeURIComponent(id) + '/export.csv',
    parseLabelCsv: (payload) => request('POST', '/api/label-sets/parse-csv', payload),
    autoLabelAlgorithms: () => request('GET', '/api/auto-label/algorithms'),
    autoLabelSuggest: (payload) => request('POST', '/api/auto-label/suggest', payload),
    evaluate: (payload) => request('POST', '/api/evaluate', payload),
    evalMeta: () => request('GET', '/api/eval/meta'),
    createEvaluation: (payload) => request('POST', '/api/evaluations', payload),
    evaluations: (datasetId) => request('GET', '/api/evaluations' + (datasetId ? '?dataset_id=' + encodeURIComponent(datasetId) : '')),
    getEvaluation: (id) => request('GET', '/api/evaluations/' + encodeURIComponent(id)),
    deleteEvaluation: (id) => request('DELETE', '/api/evaluations/' + encodeURIComponent(id)),
    evaluationReportUrl: (id) => '/api/evaluations/' + encodeURIComponent(id) + '/report.md',
    compareMql5: (payload) => request('POST', '/api/compare-mql5', payload),

    replayCreate: (payload) => request('POST', '/api/replay', payload),
    replayBars: (sid) => request('GET', '/api/replay/' + encodeURIComponent(sid) + '/bars'),
    // `since` (tuỳ chọn): con trỏ client đang có → server chỉ trả phần mới (delta_since).
    replayStep: (sid, n, since) => request('POST', '/api/replay/' + encodeURIComponent(sid) + '/step', { n: n || 1, since: since === undefined ? null : since }),
    replayNextEvent: (sid, since) => request('POST', '/api/replay/' + encodeURIComponent(sid) + '/next-event', { since: since === undefined ? null : since }),
    replayBack: (sid, n, since) => request('POST', '/api/replay/' + encodeURIComponent(sid) + '/back', { n: n || 1, since: since === undefined ? null : since }),
    replaySeek: (sid, index, since) => request('POST', '/api/replay/' + encodeURIComponent(sid) + '/seek', { index, since: since === undefined ? null : since }),
    replayReset: (sid) => request('POST', '/api/replay/' + encodeURIComponent(sid) + '/reset'),
    replayClose: (sid) => request('DELETE', '/api/replay/' + encodeURIComponent(sid)),

    // Live chỉ đọc nến MT5 (plan_mt5_live.md): `since` như replay → kèm nến mới (bars_moi).
    liveList: () => request('GET', '/api/live'),
    liveCreate: (payload) => request('POST', '/api/live', payload),
    liveHint: (payload) => request('POST', '/api/live/hint', payload),
    liveSnapshot: (id, since) => request('GET', '/api/live/' + encodeURIComponent(id) +
      (since === undefined || since === null ? '' : '?since=' + encodeURIComponent(since))),
    liveForward: (id) => request('GET', '/api/live/' + encodeURIComponent(id) + '/forward'),
    liveStop: (id) => request('POST', '/api/live/' + encodeURIComponent(id) + '/stop'),
    liveResume: (id) => request('POST', '/api/live/' + encodeURIComponent(id) + '/resume')
  };
})(window);
