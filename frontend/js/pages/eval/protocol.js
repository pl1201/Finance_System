/* Trang Đánh giá — form protocol chấm (mục tiêu, matcher, dung sai, khoảng chấm, ánh xạ). */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
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

  function protocolFromForm() {
    var emptyInt = function (id) {
      var v = $(id).value;
      return v === '' ? null : Number(v);
    };
    var cross = activeCrossMap();
    var extra = cross ? { event_type_map: cross.map } : {};
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
  E.applyProtocol = applyProtocol;
  E.protocolFromForm = protocolFromForm;
  E.updateTargetHelp = updateTargetHelp;
})(window.MSL);
