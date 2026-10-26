/* Trang Đánh giá — form protocol chấm (mục tiêu, matcher, dung sai, khoảng chấm, ánh xạ). */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;
  var S = E.S;

  /**
   * Ánh xạ chấm chéo do plugin khai báo (`evalCrossMap`: ô chọn, mục tiêu áp dụng, bảng ánh xạ, cảnh báo),
   * vd chấm pivot DC (close) với nhãn swing cấp 1 (thường theo wick) — xem algos/dc_atr.js.
   */
  var CROSS_MAPS = MSL.algos.list().map(function (p) { return p.evalCrossMap; }).filter(Boolean);

  function activeCrossMap() {
    return CROSS_MAPS.filter(function (c) {
      return $(c.checkbox).checked && $('#target-select').value === c.target;
    })[0] || null;
  }

  /** Mục tiêu chấm có trong /api/eval/meta mà ô chọn chưa có (vd của thuật toán mới) → thêm option. */
  function syncTargetOptions() {
    var sel = $('#target-select');
    ((S.meta && S.meta.targets) || []).forEach(function (t) {
      if (sel.querySelector('option[value="' + t.id + '"]')) return;
      var o = document.createElement('option');
      o.value = t.id;
      o.textContent = t.label_vi;
      sel.appendChild(o);
    });
  }

  /** ISO UTC từ server → giá trị ô datetime-local (giờ UTC, không múi). */
  function isoToInput(iso) {
    return iso ? String(iso).replace('Z', '').replace(/[+-]00:00$/, '').slice(0, 16) : '';
  }

  var EMPTY_SEG = '<tr><td colspan="5" class="empty-cell">Chưa khai đoạn — chấm trên khoảng chấm như thường.</td></tr>';

  /** Bảng đoạn phát triển / kiểm tra. Ô trong bảng không có id — chỉ đọc qua readSegments. */
  function renderSegments(list) {
    var tb = $('#seg-table tbody');
    if (!list.length) {
      tb.innerHTML = EMPTY_SEG;
    } else {
      tb.innerHTML = list.map(function (s, i) {
        var role = s.role === 'test' ? 'test' : 'dev';
        return '<tr class="seg-row">' +
          '<td><input type="text" class="seg-name" maxlength="40" value="' + esc(s.name || '') + '" placeholder="Đoạn ' + (i + 1) + '"></td>' +
          '<td><select class="seg-role"><option value="dev"' + (role === 'dev' ? ' selected' : '') + '>Phát triển</option>' +
          '<option value="test"' + (role === 'test' ? ' selected' : '') + '>Kiểm tra</option></select></td>' +
          '<td><input type="datetime-local" class="seg-start" value="' + esc(isoToInput(s.start)) + '"></td>' +
          '<td><input type="datetime-local" class="seg-end" value="' + esc(isoToInput(s.end)) + '"></td>' +
          '<td><button type="button" class="btn btn-secondary btn-sm seg-del" title="Xoá đoạn" aria-label="Xoá đoạn">✕</button></td>' +
          '</tr>';
      }).join('');
    }
    syncUnlock();
  }

  function readSegments() {
    return $$('#seg-table tbody tr.seg-row').map(function (tr) {
      return {
        name: tr.querySelector('.seg-name').value.trim(),
        role: tr.querySelector('.seg-role').value,
        start: tr.querySelector('.seg-start').value,
        end: tr.querySelector('.seg-end').value
      };
    });
  }

  /** Chỉ mở được khi có đoạn kiểm tra. */
  function syncUnlock() {
    var box = $('#chk-test-unlock');
    var hasTest = readSegments().some(function (s) { return s.role === 'test'; });
    box.disabled = !hasTest;
    if (!hasTest) box.checked = false;
  }

  function bindProtocolExtras() {
    $('#seg-add').addEventListener('click', function () {
      var list = readSegments();
      list.push({ name: '', role: list.length ? 'test' : 'dev', start: '', end: '' });
      renderSegments(list);
    });
    $('#seg-clear').addEventListener('click', function () { renderSegments([]); });
    $('#seg-table').addEventListener('click', function (ev) {
      var btn = ev.target.closest('.seg-del');
      if (!btn) return;
      btn.closest('tr').remove();
      if (!$$('#seg-table tbody tr.seg-row').length) $('#seg-table tbody').innerHTML = EMPTY_SEG;
      syncUnlock();
    });
    $('#seg-table').addEventListener('change', function (ev) {
      if (ev.target.classList.contains('seg-role')) syncUnlock();
    });
    $('#chk-test-unlock').addEventListener('change', function () {
      var box = $('#chk-test-unlock');
      if (box.checked && !window.confirm('Mở đoạn kiểm tra?\n\nChỉ làm khi cấu hình (tham số, dung sai, mục tiêu) đã chốt trên đoạn phát triển. ' +
          'Lần đánh giá này sẽ được đánh dấu [ĐÃ MỞ ĐOẠN KIỂM TRA]; chỉnh tham số theo kết quả đoạn kiểm tra làm mất tính độc lập.')) {
        box.checked = false;
      }
    });
  }

  function protocolFromForm() {
    var emptyInt = function (id) {
      var v = $(id).value;
      return v === '' ? null : Number(v);
    };
    var cross = activeCrossMap();
    var extra = cross ? { event_type_map: cross.map } : {};
    // Tuỳ chọn bổ sung: chỉ gửi khi bật → protocol mặc định giữ nguyên hash.
    if ($('#null-mode').value !== 'off') {
      extra.null_mode = $('#null-mode').value;
      extra.null_n = Number($('#null-n').value || 200);
      extra.null_seed = Number($('#null-seed').value || 0);
    }
    var segs = readSegments();
    if (segs.length) {
      extra.segments = segs;
      extra.test_unlocked = $('#chk-test-unlock').checked;
    }
    return Object.assign({
      target: $('#target-select').value,
      matcher_version: $('#matcher-select').value,
      time_tolerance_bars: Number($('#tol-bars').value || 0),
      price_tolerance: Number($('#tol-price').value || 0),
      coverage_start_index: emptyInt('#cov-start'),
      coverage_end_index: emptyInt('#cov-end'),
      map_level1_to_structure: $('#chk-map-l1').checked,
      atr_period: Number($('#atr-period').value || 14),
      exclude_unconfirmed_tail: $('#chk-exclude-tail').checked,
      max_lag_bars: emptyInt('#max-lag'),
      min_recall: emptyInt('#min-recall')
    }, extra);
  }

  function applyProtocol(p) {
    if (!p) return;
    if (p.target) $('#target-select').value = p.target;
    if (p.matcher_version) $('#matcher-select').value = p.matcher_version;
    if (p.time_tolerance_bars !== undefined) $('#tol-bars').value = p.time_tolerance_bars;
    if (p.price_tolerance !== undefined) $('#tol-price').value = p.price_tolerance;
    $('#cov-start').value = p.coverage_start_index == null ? '' : p.coverage_start_index;
    $('#cov-end').value = p.coverage_end_index == null ? '' : p.coverage_end_index;
    $('#chk-map-l1').checked = !!p.map_level1_to_structure;
    CROSS_MAPS.forEach(function (c) { $(c.checkbox).checked = c.isActive(p.event_type_map); });
    if (p.atr_period) $('#atr-period').value = p.atr_period;
    $('#chk-exclude-tail').checked = p.exclude_unconfirmed_tail !== false;
    $('#max-lag').value = p.max_lag_bars == null ? '' : p.max_lag_bars;
    $('#min-recall').value = p.min_recall == null ? '' : p.min_recall;
    // Protocol cũ không có các khoá này → đặt về mặc định, không giữ lại lựa chọn của lần trước.
    $('#null-mode').value = p.null_mode || 'off';
    $('#null-n').value = p.null_n || 200;
    $('#null-seed').value = p.null_seed == null ? 1 : p.null_seed;
    renderSegments(p.segments || []);
    $('#chk-test-unlock').checked = !!p.test_unlocked && !$('#chk-test-unlock').disabled;
    updateTargetHelp();
  }

  function updateTargetHelp() {
    var t = $('#target-select').value;
    var map = $('#chk-map-l1').checked;
    var help = (S.meta && S.meta.targets || []).filter(function (x) { return x.id === t; })[0];
    var extra = map && t === 'swing_cau_truc'
      ? ' Run cấp 1 được ánh xạ SWING_HIGH→SWING_HIGH_L2, SWING_LOW→SWING_LOW_L2 — không trộn tên loại.'
      : '';
    CROSS_MAPS.forEach(function (c) { $(c.checkbox).disabled = t !== c.target; });
    var cross = activeCrossMap();
    if (cross) extra += cross.warning;
    $('#target-help').textContent = (help ? help.help_vi : '') + extra;
  }

  E.syncTargetOptions = syncTargetOptions;
  E.bindProtocolExtras = bindProtocolExtras;
  E.applyProtocol = applyProtocol;
  E.protocolFromForm = protocolFromForm;
  E.updateTargetHelp = updateTargetHelp;
})(window.MSL);
