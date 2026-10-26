/* Trang Thử nghiệm — cột cấu hình (giao diện v3): dòng tóm tắt trên tiêu đề mỗi mục gập (thấy khi mục đóng), dòng ngữ
 * cảnh trên thanh công cụ chart (thấy cả khi ẩn cột), nút «Mặc định» của tham số, bảng «Chú giải» lớp, Ctrl+Enter = Chạy thử.
 * Người dùng sửa ô trong cột → listener chung của cột vẽ lại tóm tắt; code đổi giá trị (chọn dataset / thuật toán, mở lần
 * chạy cũ, bật lớp từ code) → renderRangeHint / applyParamVisibility / setLayer gọi L.renderSidebarSummary. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var S = L.S;

  /** 'YYYY-MM-DDTHH:MM' (ô datetime-local) → 'DD/MM/YYYY'. */
  function day(v) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(v || '');
    return m ? m[3] + '/' + m[2] + '/' + m[1] : '…';
  }

  function changedParams() {
    if (!S.algo) return 0;
    var cur = L.collectParams();
    return S.algo.params.filter(function (p) {
      var wrap = $('#param-form [data-param-wrap="' + p.name + '"]');   // ô đang ẩn (show_if) không có hiệu lực → không đếm
      return p.name in cur && p.name !== 'timeframe' && !(wrap && wrap.hidden) && String(cur[p.name]) !== String(p.default);
    }).length;
  }

  function layerBoxes() { return L.LAYER_BOXES.map(function (sel) { return $(sel); }); }

  function render() {
    var d = S.dataset, a = S.algo, n = changedParams();
    var ds = d ? d.symbol + ' ' + d.timeframe : '', range = d ? day($('#range-start').value) + ' → ' + day($('#range-end').value) : '';
    var est = d && d.row_count ? L.estimateRangeBars() : 0;
    if (est && est < d.row_count) {                // khoảng rút gọn (mặc định ~50 000 nến cuối) — thấy cả khi mục «Dữ liệu» đang gập
      range += ' · ~' + est.toLocaleString('vi-VN') + ' / ' + d.row_count.toLocaleString('vi-VN') + ' nến';
    }
    var changed = n ? n + ' tham số đã đổi' : 'tham số mặc định';
    $('#sum-data').textContent = d ? ds + ' · ' + range : 'chưa chọn dataset';
    $('#sum-algo').textContent = a ? changed : '';
    var on = 0, all = 0;
    layerBoxes().forEach(function (box) {
      if (box.hidden) return;
      Array.prototype.forEach.call(box.querySelectorAll('label.check input[type=checkbox]'), function (cb) {   // cùng tập với «Chú giải»
        all++;
        if (cb.checked && !cb.disabled) on++;
      });
    });
    $('#sum-layers').textContent = all ? on + ' / ' + all + ' lớp đang bật' : '';
    var ctx = $('#run-context');
    ctx.textContent = d ? ds + (a ? ' · ' + a.display_name_vi + (n ? ' · ' + changed : '') : '') : '';
    ctx.title = d ? MSL.datasetPicker.label(d) + ' · ' + range + ' (UTC)' + (a ? '\n' + a.display_name_vi + ' v' + a.version +
      ' · ' + changed : '') : '';
  }

  function openLegend() {
    $('#legend-rows').innerHTML = MSL.layerToggles.legendHtml(layerBoxes());
    $('#legend-algo').textContent = S.algo ? S.algo.display_name_vi : '';
    $('#legend-dialog').showModal();
  }

  function resetParams() {
    if (!S.algo) return;
    L.renderParamForm();                                                  // dựng lại form với giá trị mặc định
    L.syncTimeframeParam();
    $('#param-form').dispatchEvent(new Event('change', { bubbles: true }));   // đang replay → chạy lại như khi sửa tay
  }

  function bind() {
    var sb = $('#lab-sidebar');
    sb.addEventListener('change', render);
    sb.addEventListener('input', function (e) { if (e.target.closest('#param-form')) render(); });
    $('#btn-legend').addEventListener('click', openLegend);
    $('#btn-param-reset').addEventListener('click', resetParams);
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' || !(e.ctrlKey || e.metaKey) || e.defaultPrevented) return;
      if (e.target.closest('textarea, #chat-panel')) return;   // ô nhiều dòng / khung chat dùng Ctrl+Enter cho riêng nó
      var run = $('#btn-run');
      if (run.disabled || $$('dialog[open], .modal:not([hidden])').length) return;
      e.preventDefault();
      run.click();
    });
    render();
  }

  L.bindSidebar = bind;
  L.renderSidebarSummary = render;
})(window.MSL);
