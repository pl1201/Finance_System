/* Trang Thử nghiệm — hộp thoại nhập CSV, tổng hợp nến, nhập MT5; xuất ảnh chart. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var TF_ORDER = MSL.tf.ORDER;
  var TF_SEC = MSL.tf.SEC;
  var esc = MSL.dom.esc;
  var S = L.S;

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
      await L.loadDatasets(ds.id);
      L.banner('ok', 'Đã nhập dataset <strong>' + esc(ds.name) + '</strong> — ' + ds.row_count + ' nến.');
    } catch (e) {
      showImportError(e.message);
    } finally {
      $('#btn-do-import').disabled = false;
    }
  }

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
    if (!S.dataset) { L.banner('error', 'Chọn dataset nguồn.'); return; }
    $('#resample-error').hidden = true;
    $('#resample-source-note').textContent = 'Nguồn: ' + S.dataset.symbol + ' ' + S.dataset.timeframe +
      ' · ' + S.dataset.row_count + ' nến. Mốc utc_epoch, không lấp gap bằng tương lai.';
    fillResampleTargets(preselect);
    if (!$('#resample-target').options.length) {
      L.banner('error', 'Dataset ' + S.dataset.timeframe + ' đã ở khung lớn nhất lab hỗ trợ (H4), không tổng hợp lên được. Xuống M5: bấm nút M5 trên thanh Khung.');
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
      await L.loadDatasets(out.dataset.id);
      L.banner('ok', 'Đã tổng hợp ' + out.dataset.row_count + ' nến ' + esc(out.dataset.timeframe) +
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
      await L.loadDatasets(ds.id);
      L.banner('ok', 'Đã nhập ' + ds.row_count + ' nến đóng từ MT5.');
    } catch (e) {
      $('#mt5-error').hidden = false;
      $('#mt5-error').textContent = e.message;
    }
  }

  L.closeImport = closeImport;
  L.closeMt5 = closeMt5;
  L.closeResampleModal = closeResampleModal;
  L.doImport = doImport;
  L.doMt5Import = doMt5Import;
  L.doResample = doResample;
  L.exportPng = exportPng;
  L.onPickFile = onPickFile;
  L.openImport = openImport;
  L.openMt5 = openMt5;
  L.openResampleModal = openResampleModal;
  L.submitResample = submitResample;
})(window.MSL);
