/* Trang Gán nhãn — loại nhãn, trạng thái dùng chung (S), tiện ích: thông báo, giá theo loại, tra nến. */
(function (MSL) {
  'use strict';

  var G = MSL.label = MSL.label || {};
  var $ = MSL.dom.$;

  var TYPES = [
    { id: 'SWING_HIGH', label: 'Đỉnh cấp 1', sw: '#ffb74d' },
    { id: 'SWING_LOW', label: 'Đáy cấp 1', sw: '#4dd0e1' },
    { id: 'SWING_HIGH_L2', label: 'Đỉnh cấp 2', sw: '#ffe082' },
    { id: 'SWING_LOW_L2', label: 'Đáy cấp 2', sw: '#80deea' },
    { id: 'BOS_UP', label: 'BOS lên', sw: '#66bb6a' },
    { id: 'BOS_DOWN', label: 'BOS xuống', sw: '#ef5350' },
    { id: 'CHOCH_UP', label: 'CHoCH lên', sw: '#26c6da' },
    { id: 'CHOCH_DOWN', label: 'CHoCH xuống', sw: '#ff7043' },
    { id: 'BOS_INTERNAL_UP', label: 'BOS nội bộ lên', sw: '#9ccc65' },
    { id: 'BOS_INTERNAL_DOWN', label: 'BOS nội bộ xuống', sw: '#ef9a9a' },
    { id: 'C2_CONFIRMED_UP', label: 'C2 tăng (nến cực trị)', sw: '#00e676' },
    { id: 'C2_CONFIRMED_DOWN', label: 'C2 giảm (nến cực trị)', sw: '#ff5252' },
    { id: 'CISD_CONFIRMED_UP', label: 'CISD tăng (nến close vượt)', sw: '#69f0ae' },
    { id: 'CISD_CONFIRMED_DOWN', label: 'CISD giảm (nến close vượt)', sw: '#ff8a80' }
  ];

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

  function priceFor(type, bar) {
    // CISD: nhãn ở nến có close vượt mức — mặc định close, sửa thành mức CISD nếu chấm theo giá.
    if (String(type).indexOf('CISD_') === 0) return bar.close;
    // C2 tăng quét low (giá = low), C2 giảm quét high.
    if (type === 'C2_CONFIRMED_UP') return bar.low;
    if (type === 'C2_CONFIRMED_DOWN') return bar.high;
    if (String(type).indexOf('LOW') !== -1 || String(type).indexOf('DOWN') !== -1) return bar.low;
    return bar.high;
  }

  /** Trang này kẹp số chữ số thập phân tối đa 5 (trang Thử nghiệm: 6). */
  function detectDigits(bars) {
    return MSL.format.detectDigits(bars, 5);
  }

  function barTimeText(idx) {
    for (var i = 0; i < S.bars.length; i++) {
      if (S.bars[i].index === idx) {
        return window.chartUtils ? window.chartUtils.fmtIso(S.bars[i].bar_time) : S.bars[i].bar_time;
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
