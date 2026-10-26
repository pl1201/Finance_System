/* Tiện ích DOM dùng chung cho mọi trang. Mở namespace window.MSL. */
(function (global) {
  'use strict';

  var MSL = global.MSL = global.MSL || {};

  MSL.dom = {
    $: function (sel) { return document.querySelector(sel); },
    $$: function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); },
    /** localStorage an toàn: chế độ riêng tư / bị chặn thì load → null, save bỏ qua (chỉ không nhớ). */
    load: function (key) { try { return global.localStorage.getItem(key); } catch (e) { return null; } },
    save: function (key, v) { try { global.localStorage.setItem(key, v); } catch (e) { /* chỉ không nhớ */ } },
    /** Thoát HTML cho chuỗi chèn vào innerHTML. */
    esc: function (s) {
      return String(s === null || s === undefined ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
  };
})(window);
