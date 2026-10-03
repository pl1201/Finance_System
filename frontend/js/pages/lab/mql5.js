/* Trang Thử nghiệm — tab Đối chiếu MQL5. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = L.S;

  async function doMql5Compare() {
    if (!S.run || !S.run.run_id) { L.banner('error', 'Chạy thử Python trước.'); return; }
    var f = $('#mql5-file').files[0];
    if (!f) { L.banner('error', 'Chọn file CSV MQL5.'); return; }
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
    } catch (e) { L.banner('error', esc(e.message)); }
  }

  L.doMql5Compare = doMql5Compare;
})(window.MSL);
