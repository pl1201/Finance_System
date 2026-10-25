/* Bảng dưới chart (các tab): nút «Thu gọn» / «Mở bảng», bấm một tab thì mở lại, kéo thanh trên cùng để đổi chiều cao — dùng
 * chung cho trang Thử nghiệm và trang Live MT5.
 *
 *   var bottom = MSL.bottomPanel.bind({ panel, toggle, handle, key, onOpen });
 *   bottom.open();          // vd khi bấm một tab
 *   bottom.collapsed();     // đang thu gọn?
 *
 * `key` (tuỳ chọn): nhớ thu gọn / mở theo trình duyệt (localStorage lỗi thì bỏ qua). `onOpen` (tuỳ chọn): gọi khi mở lại. */
(function (MSL) {
  'use strict';

  function bind(o) {
    var panel = o.panel;

    function collapsed() { return panel.classList.contains('collapsed'); }

    function set(on) {
      panel.classList.toggle('collapsed', on);
      o.toggle.textContent = on ? 'Mở bảng' : 'Thu gọn';
      o.toggle.setAttribute('aria-expanded', String(!on));
      if (o.key) { try { localStorage.setItem(o.key, on ? '1' : '0'); } catch (e) { /* chế độ riêng tư */ } }
      if (!on && o.onOpen) o.onOpen();
    }

    if (o.key) {
      var saved = null;
      try { saved = localStorage.getItem(o.key); } catch (e) { /* mặc định mở */ }
      if (saved === '1') set(true);
    }
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
