/* Ô bật/tắt lớp hiển thị (input[data-layer], phần tử data-requires) — dùng chung cho trang Thử nghiệm và trang Live MT5.
 * `layers` = {lớp: bật} của trang (mặc định do plugin khai báo, MSL.algos.defaultLayers()). */
(function (MSL) {
  'use strict';

  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;

  /**
   * Lớp phụ thuộc lớp khác: phần tử có `data-requires="<lớp>"` bị vô hiệu khi lớp đó tắt — input → `disabled`;
   * phần tử khác (label) → làm mờ (class `is-disabled`) và vô hiệu mọi input bên trong. Chung cho mọi khung lớp,
   * không biết thuật toán nào; giá trị riêng của lớp con giữ nguyên (plugin tự quyết có vẽ hay không).
   */
  function syncRequires(layers) {
    $$('[data-requires]').forEach(function (el) {
      var on = !!layers[el.getAttribute('data-requires')];
      if (el.tagName === 'INPUT') { el.disabled = !on; return; }
      el.classList.toggle('is-disabled', !on);
      Array.prototype.forEach.call(el.querySelectorAll('input'), function (i) { i.disabled = !on; });
    });
  }

  /** Áp trạng thái lớp (mặc định plugin khai báo) lên checkbox — trình duyệt có thể khôi phục ô đã tick từ lần
   * trước khi tải lại trang. Lớp không plugin nào khai báo thì lấy theo checkbox. */
  function syncInputs(layers) {
    $$('input[data-layer]').forEach(function (cb) {
      var k = cb.getAttribute('data-layer');
      if (Object.prototype.hasOwnProperty.call(layers, k)) cb.checked = !!layers[k];
      else layers[k] = cb.checked;
    });
    syncRequires(layers);
  }

  /** Bật/tắt một lớp từ code: `layers` + checkbox + lớp phụ thuộc. */
  function set(layers, name, on) {
    layers[name] = !!on;
    $$('input[data-layer="' + name + '"]').forEach(function (cb) { cb.checked = !!on; });
    syncRequires(layers);
  }

  /** Người dùng bật/tắt ô trong `selector` → `layers` + lớp phụ thuộc, rồi `onChange()` (trang vẽ lại). */
  function bind(selector, layers, onChange) {
    $$(selector).forEach(function (cb) {
      cb.addEventListener('change', function () {
        layers[cb.getAttribute('data-layer')] = cb.checked;
        syncRequires(layers);
        onChange();
      });
    });
  }

  /** Khung lớp / nút riêng của plugin (khoá registry `panels`) chỉ hiện với plugin `own` (null = ẩn hết). Trang thiếu khung
   * của plugin khác thì bỏ qua. */
  function showPanelsFor(own) {
    MSL.algos.list().forEach(function (p) {
      (p.panels || []).forEach(function (sel) { var el = $(sel); if (el) el.hidden = p !== own; });
    });
  }

  function shown(el) {
    for (var x = el; x && x !== document.body; x = x.parentElement) if (x.hidden) return false;
    return true;
  }

  /** Bảng «Chú giải» (giao diện v3) dựng từ các khung lớp đang hiện: mỗi ô lớp một dòng — ô màu, tên, bật / tắt, câu giải
   * thích lấy từ title của ô (chữ đi kèm màu, một nguồn với tooltip); tiêu đề nhóm (.layers-head) giữ nguyên. */
  function legendHtml(boxes) {
    var rows = [];
    boxes.filter(shown).forEach(function (box) {
      Array.prototype.forEach.call(box.querySelectorAll('.layers-head, label.check'), function (el) {
        if (el.classList.contains('layers-head')) {
          rows.push('<div class="lgd-head">' + esc(el.textContent) + '</div>');
          return;
        }
        var cb = el.querySelector('input[type=checkbox]'), sw = el.querySelector('.sw'), spans = el.querySelectorAll(':scope > span');
        if (!cb || !shown(el)) return;
        var on = cb.checked && !cb.disabled;
        rows.push('<div class="lgd-row' + (el.closest('.layers-sub') ? ' lgd-sub' : '') + '">' +
          (sw ? sw.outerHTML : '<span class="sw"></span>') +
          '<div><div class="lgd-name">' + (spans.length ? spans[spans.length - 1].innerHTML : '') +
          ' <span class="lgd-state' + (on ? ' on' : '') + '">' + (on ? 'đang bật' : 'đang tắt') + '</span></div>' +
          (el.title ? '<div class="lgd-help">' + esc(el.title) + '</div>' : '') + '</div></div>');
      });
    });
    return rows.join('') || '<p class="muted">Thuật toán này không có lớp riêng.</p>';
  }

  MSL.layerToggles = { bind: bind, set: set, showPanelsFor: showPanelsFor, syncInputs: syncInputs, syncRequires: syncRequires,
    legendHtml: legendHtml };
})(window.MSL);
