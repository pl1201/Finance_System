/* Bảng dưới chart (các tab): nút «Thu gọn» / «Mở bảng», bấm một tab thì mở lại, kéo thanh trên cùng để đổi chiều cao — dùng
 * chung cho trang Thử nghiệm và trang Live MT5.
 *
 *   var bottom = MSL.bottomPanel.bind({ panel, toggle, handle, key, onOpen });
 *   bottom.open();          // vd khi bấm một tab
 *   bottom.collapsed();     // đang thu gọn?
 *
 * `key` (tuỳ chọn): nhớ thu gọn / mở theo trình duyệt (localStorage lỗi thì bỏ qua); `collapsedByDefault` (tuỳ chọn): thu gọn khi
 * chưa có lựa chọn đã nhớ. `onOpen` (tuỳ chọn): gọi khi mở lại. */
(function (MSL) {
  'use strict';

  function bind(o) {
    var panel = o.panel;

    function collapsed() { return panel.classList.contains('collapsed'); }

    function set(on, remember) {
      panel.classList.toggle('collapsed', on);
      o.toggle.textContent = on ? 'Mở bảng' : 'Thu gọn';
      o.toggle.setAttribute('aria-expanded', String(!on));
      if (o.key && remember !== false) MSL.dom.save(o.key, on ? '1' : '0');
      if (!on && o.onOpen) o.onOpen();
    }

    var saved = o.key ? MSL.dom.load(o.key) : null;
    if (saved === '1' || (saved === null && o.collapsedByDefault)) set(true, false);   // mặc định: không ghi thành lựa chọn
    o.toggle.addEventListener('click', function () { set(!collapsed()); });

    if (o.handle) {                      // kéo thanh trên cùng: cao 120 px … 70% cửa sổ
      var drag = null;
      o.handle.addEventListener('mousedown', function (e) {
        if (collapsed()) return;
        drag = { y: e.clientY, h: panel.getBoundingClientRect().height };
        e.preventDefault();
      });
      window.addEventListener('mousemove', function (e) {
        if (!drag) return;
        var next = Math.round(drag.h + (drag.y - e.clientY));
        panel.style.height = Math.max(120, Math.min(Math.round(window.innerHeight * 0.7), next)) + 'px';
      });
      window.addEventListener('mouseup', function () { drag = null; });
    }

    return { open: function () { if (collapsed()) set(false); }, collapsed: collapsed };
  }

  MSL.bottomPanel = { bind: bind };
})(window.MSL);
