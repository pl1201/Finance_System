/* Trang Gán nhãn — loại nhãn, trạng thái dùng chung (S), tiện ích: thông báo, giá theo loại, tra nến. */
(function (MSL) {
  'use strict';

  var G = MSL.label = MSL.label || {};
  var $ = MSL.dom.$;

  /** Loại nhãn tay [{id, label, sw, short}] — mỗi plugin algos/ khai báo loại của mình (`labelTypes`). */
  var TYPES = MSL.algos.labelTypes();

  var S = {
    datasets: [],
    dataset: null,
    bars: [],
    draft: [],
    undo: [],
    selected: null,
    dirty: false,
    savedId: '',
    savedSets: [],
    draftSaved: null,
    digits: 2,
    chart: null,
    currentType: 'SWING_HIGH',
    autoAlgos: [],
    // Phiên auto label: { algorithm, algorithm_version, source_detail, start, end,
    //   types, items: [đề xuất + status], cursor }. status: pending | accepted | rejected
    auto: null,
    // Bảng thao tác trên chart, mở khi bấm nến đã có nhãn / đề xuất: { bar }
    pop: null
  };

  var TYPE_LABEL = {};
  TYPES.forEach(function (t) { TYPE_LABEL[t.id] = t.label; });

  function fmtNum(x, d) {
    if (x === null || x === undefined || x === '') return '—';
    var n = Number(x);
    if (!isFinite(n)) return '—';
    return n.toFixed(d == null ? S.digits : d);
  }

  function showError(msg) {
    var el = $('#label-error');
    var ok = $('#label-ok');
    ok.hidden = true;
    if (!msg) { el.hidden = true; el.textContent = ''; return; }
    el.hidden = false;
    el.textContent = msg;
  }

  function showOk(msg) {
    var el = $('#label-ok');
    $('#label-error').hidden = true;
    if (!msg) { el.hidden = true; el.textContent = ''; return; }
    el.hidden = false;
    el.textContent = msg;
  }

  function isTypingTarget(el) {
    if (!el) return false;
    var tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable;
  }

  /** Giá mặc định của nhãn: plugin quyết trước, còn lại LOW/DOWN → low, khác → high. */
  function priceFor(type, bar) {
    return MSL.algos.labelPrice(type, bar);
  }

  /** Trang này kẹp số chữ số thập phân tối đa 5 (trang Thử nghiệm: 6). */
  function detectDigits(bars) {
    return MSL.format.detectDigits(bars, 5);
  }

  function barTimeText(idx) {
    for (var i = 0; i < S.bars.length; i++) {
      if (S.bars[i].index === idx) {
        return MSL.format.fmtIso(S.bars[i].bar_time);
      }
    }
    return '';
  }

  function barByIndex(idx) {
    for (var i = 0; i < S.bars.length; i++) if (S.bars[i].index === idx) return S.bars[i];
    return null;
  }

  G.S = S;
  G.TYPES = TYPES;
  G.TYPE_LABEL = TYPE_LABEL;
  G.barByIndex = barByIndex;
  G.barTimeText = barTimeText;
  G.detectDigits = detectDigits;
  G.fmtNum = fmtNum;
  G.isTypingTarget = isTypingTarget;
  G.priceFor = priceFor;
  G.showError = showError;
  G.showOk = showOk;
})(window.MSL);
