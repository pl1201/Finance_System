/* Khung giao diện dùng chung mọi trang (giao diện v3, 26/10/2026) — không biết thuật toán nào:
 *
 *   MSL.ui.bindMenus()             menu thả: <div class="menu"><button data-menu-btn …>…</button><div class="menu-list" role="menu"
 *                                  hidden>…nút…</div></div> — bấm nút mở / đóng; bấm một mục, bấm ra ngoài hoặc Esc thì đóng
 *   MSL.ui.bindSections()          mục gập <details data-remember="khoá">: nhớ mở / đóng theo trình duyệt
 *   MSL.ui.bindSidebar(key)        nút [data-sidebar-toggle aria-controls=id]: ẩn / hiện cột (body.sb-hidden), nhớ theo trình duyệt
 *   MSL.ui.bindDialogs()           <dialog>: nút [data-dialog-close] và bấm ra nền thì đóng (Esc: trình duyệt tự đóng)
 *
 * Mỗi hàm gọi một lần khi trang khởi động. */
(function (MSL) {
  'use strict';

  var $$ = MSL.dom.$$;
  var load = MSL.dom.load;
  var save = MSL.dom.save;

  function bindMenus() {
    $$('.menu').forEach(function (m) {
      var btn = m.querySelector('[data-menu-btn]'), list = m.querySelector('.menu-list');
      function set(open) {
        list.hidden = !open;
        btn.setAttribute('aria-expanded', String(open));
      }
      btn.addEventListener('click', function () {
        set(list.hidden);
        var first = !list.hidden && list.querySelector('button:not(:disabled)');
        if (first) first.focus();
      });
      list.addEventListener('click', function (e) { if (e.target.closest('button')) set(false); });
      document.addEventListener('click', function (e) { if (!list.hidden && !m.contains(e.target)) set(false); });
      m.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape' || list.hidden) return;
        e.stopPropagation();
        set(false);
        btn.focus();
      });
    });
  }

  function bindSections() {
    $$('details[data-remember]').forEach(function (d) {
      var key = d.getAttribute('data-remember'), v = load(key);
      if (v !== null) d.open = v === '1';
      d.addEventListener('toggle', function () { save(key, d.open ? '1' : '0'); });
    });
  }

  function bindSidebar(key) {
    $$('[data-sidebar-toggle]').forEach(function (btn) {
      function set(hidden) {
        document.body.classList.toggle('sb-hidden', hidden);
        btn.setAttribute('aria-expanded', String(!hidden));
        btn.title = hidden ? 'Hiện cột cấu hình' : 'Ẩn cột cấu hình (chart rộng hơn)';
      }
      set(load(key) === '1');
      btn.addEventListener('click', function () {
        var hidden = !document.body.classList.contains('sb-hidden');
        set(hidden);
        save(key, hidden ? '1' : '0');
      });
    });
  }

  function bindDialogs() {
    $$('dialog').forEach(function (d) {
      d.addEventListener('click', function (e) {
        if (e.target === d || e.target.closest('[data-dialog-close]')) d.close();
      });
    });
  }

  MSL.ui = { bindMenus: bindMenus, bindSections: bindSections, bindSidebar: bindSidebar, bindDialogs: bindDialogs };
})(window.MSL);
