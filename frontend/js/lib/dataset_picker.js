/* Ô chọn dataset dùng chung cho ba trang (Thử nghiệm, Gán nhãn, Đánh giá): gom theo mã (dữ liệu thực) rồi nhóm mô phỏng,
   sắp theo khung; ẩn sẵn dataset phụ — bản «LỆCH GIỜ» đã có bản sửa (AGENTS §9: không dùng cho phân tích mới), M1 từng năm
   (nặng, không nên mở chart) và tuỳ trang thêm điều kiện riêng (trang Đánh giá: chưa có lần chạy đã lưu) — kèm «· ẩn n
   · hiện tất cả» ngay trên dòng chữ của ô (không làm ô cao thêm, lý do ở tooltip). Không xoá gì: chỉ lọc danh sách. Dataset đang chọn hoặc được chọn bằng mã (URL, lần chạy /
   đánh giá đã lưu, nút đổi khung) luôn hiện. Lựa chọn «hiện tất cả» nhớ trong trình duyệt (dùng chung ba trang). */
(function (MSL) {
  'use strict';

  var esc = MSL.dom.esc;
  var ORDER = MSL.tf.ORDER;
  var KEY = 'msl.datasets.showAll';
  var REASON_VI = {
    lech_gio: 'bản lệch giờ đã có bản sửa',
    m1: 'M1 từng năm (nặng)',
    chua_chay: 'chưa có lần chạy đã lưu'
  };

  function showAll() {
    try { return window.localStorage.getItem(KEY) === '1'; } catch (e) { return false; }
  }

  function setShowAll(on) {
    try { window.localStorage.setItem(KEY, on ? '1' : '0'); } catch (e) { /* chế độ riêng tư: chỉ đổi lần này */ }
  }

  /** Mã lý do ẩn sẵn của dataset `d` (null = luôn hiện). `extra(d)` → mã lý do riêng của trang | null. */
  function hiddenReason(d, extra) {
    if (/^\s*\[LỆCH GIỜ/i.test(String(d.name || ''))) return 'lech_gio';
    if (d.timeframe === 'M1' && !d.is_synthetic) return 'm1';
    return extra ? (extra(d) || null) : null;
  }

  /** «XAUUSD M15 · HistData 2024 · giờ đã sửa (từ M1) · 23717 nến» — bỏ phần mã + khung bị lặp trong tên. */
  function label(d) {
    var head = d.symbol + ' ' + d.timeframe;
    var rest = String(d.name || '').replace(head + ' · ', '').replace(head, '').replace(/\s+/g, ' ').trim();
    return head + (rest ? ' · ' + rest : '') + (d.row_count != null ? ' · ' + d.row_count + ' nến' : '');
  }

  function cmp(a, b) {
    if (a.symbol !== b.symbol) return String(a.symbol).localeCompare(String(b.symbol));
    var ia = ORDER.indexOf(a.timeframe), ib = ORDER.indexOf(b.timeframe);
    if (ia !== ib) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    return String(a.name).localeCompare(String(b.name));
  }

  /**
   * Dựng lại `sel` từ `datasets`. opts: { placeholder: '— chọn dataset —' | '' (không có dòng trống),
   * extraHidden(d) → mã lý do ẩn riêng của trang | null, keep: [id…] luôn hiện }. Giữ giá trị đang chọn.
   * Ghi nhớ datasets/opts trên chính `sel` để nút «hiện tất cả» và select() dựng lại được.
   */
  function render(sel, datasets, opts) {
    if (!sel) return null;
    opts = opts || {};
    var st = sel._dsPicker || (sel._dsPicker = { keep: {} });
    st.datasets = datasets || [];
    st.opts = opts;
    (opts.keep || []).forEach(function (id) { if (id) st.keep[id] = true; });
    var cur = sel.value;
    if (cur) st.keep[cur] = true;
    var all = showAll();
    var shown = [], reasons = {}, hidden = 0;
    st.datasets.forEach(function (d) {
      var r = hiddenReason(d, opts.extraHidden);
      if (r && !all && !st.keep[d.id]) {
        hidden++;
        reasons[r] = (reasons[r] || 0) + 1;
        return;
      }
      shown.push(d);
    });
    shown.sort(cmp);
    var groups = [], bySym = {};
    shown.forEach(function (d) {
      var g = d.is_synthetic ? '~sim' : String(d.symbol);
      if (!bySym[g]) { bySym[g] = []; groups.push(g); }
      bySym[g].push(d);
    });
    groups.sort(function (a, b) { return a === '~sim' ? 1 : b === '~sim' ? -1 : a.localeCompare(b); });
    var html = opts.placeholder ? '<option value="">' + esc(opts.placeholder) + '</option>' : '';
    groups.forEach(function (g) {
      html += '<optgroup label="' + esc(g === '~sim' ? 'Mô phỏng (chỉ để thử công cụ)' : g) + '">' +
        bySym[g].map(function (d) {
          return '<option value="' + esc(d.id) + '">' + esc(label(d)) + '</option>';
        }).join('') + '</optgroup>';
    });
    sel.innerHTML = html;
    if (cur) sel.value = cur;
    renderToggle(sel, hidden, reasons, all, st.datasets.length);
    return { shown: shown.length, hidden: hidden };
  }

  /** «· ẩn n · hiện tất cả» / «· đang hiện tất cả n · thu gọn» nối vào chữ «Dataset» của ô (label.field > span) —
   * không làm ô cao hơn các ô cùng hàng; không có chữ ô thì đặt ngay sau ô chọn. */
  function renderToggle(sel, hidden, reasons, all, total) {
    var box = sel._dsToggle;
    if (!box) {
      box = document.createElement('span');
      box.className = 'ds-filter';
      var field = sel.closest('.field'), cap = field && field.querySelector(':scope > span');
      if (cap) cap.appendChild(box); else sel.insertAdjacentElement('afterend', box);
      sel._dsToggle = box;
      box.addEventListener('click', function (ev) {
        var b = ev.target.closest('button[data-ds-all]');
        if (!b) return;
        ev.preventDefault();
        setShowAll(b.getAttribute('data-ds-all') === '1');
        var st = sel._dsPicker;
        render(sel, st.datasets, st.opts);
      });
    }
    var anyHideable = sel._dsPicker.datasets.some(function (d) { return hiddenReason(d, sel._dsPicker.opts.extraHidden); });
    if (all) {
      box.hidden = !anyHideable;
      box.title = 'Đang hiện cả dataset phụ (M1 từng năm, bản lệch giờ…)';
      box.innerHTML = ' · đang hiện tất cả ' + total + ' · <button type="button" class="btn-link" data-ds-all="0">thu gọn</button>';
      return;
    }
    box.hidden = !hidden;
    box.title = 'Đang ẩn: ' + Object.keys(reasons).map(function (r) { return reasons[r] + ' ' + (REASON_VI[r] || r); }).join(', ') +
      '. Không xoá gì — bấm «hiện tất cả» để chọn.';
    box.innerHTML = ' · ẩn ' + hidden + ' · <button type="button" class="btn-link" data-ds-all="1">hiện tất cả</button>';
  }

  /** Chọn dataset `id` bằng mã (URL, lần chạy đã lưu, đổi khung): dataset đang bị ẩn thì cho hiện rồi chọn. */
  function select(sel, id) {
    if (!sel) return;
    var st = sel._dsPicker;
    if (id && st && !Array.prototype.some.call(sel.options, function (o) { return o.value === id; })) {
      st.keep[id] = true;
      render(sel, st.datasets, st.opts);
    }
    sel.value = id || '';
  }

  MSL.datasetPicker = { render: render, select: select, label: label, hiddenReason: hiddenReason };
})(window.MSL);
