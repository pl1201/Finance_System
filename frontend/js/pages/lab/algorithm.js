/* Trang Thử nghiệm — chọn thuật toán, form tham số dựng từ registry (ParamSpec, show_if). */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;
  var S = L.S;

  async function loadAlgorithms() {
    S.algorithms = await API.algorithms();
    var opts = S.algorithms
      .map(function (a) { return '<option value="' + esc(a.name) + '">' + esc(a.display_name_vi) + ' (v' + esc(a.version) + ')</option>'; })
      .join('');
    $('#algo-select').innerHTML = opts;
    $('#rp-algo').innerHTML = opts;
    var last = null;
    try { last = window.localStorage.getItem('msl.lastAlgorithm'); } catch (e) { last = null; }
    var known = S.algorithms.some(function (a) { return a.name === last; });
    selectAlgorithm(known ? last : (S.algorithms[0] ? S.algorithms[0].name : null));
  }

  function selectAlgorithm(name) {
    S.algo = S.algorithms.filter(function (a) { return a.name === name; })[0] || null;
    if (!S.algo) return;
    $('#algo-select').value = S.algo.name;
    $('#rp-algo').value = S.algo.name;
    try { window.localStorage.setItem('msl.lastAlgorithm', S.algo.name); } catch (e) { /* chế độ riêng tư */ }
    $('#algo-desc').textContent = S.algo.description_vi;
    $('#algo-desc').title = S.algo.description_vi || '';
    var hint = $('#layer-hint');
    if (S.algo.name === 'swing_hierarchy') {
      hint.textContent = 'Cấp 2 = ô vuông. HH/LH chỉ so hai đỉnh/đáy cấp 2 liên tiếp. Không gồm BOS. Đường mức = cấp 2 gần nhất.';
    } else if (S.algo.name === 'swing_pivot') {
      hint.textContent = 'HH/LH so từng đỉnh cấp 1. BOS/CHoCH là sự kiện phá vỡ riêng — không trộn với nhãn HH.';
    } else if (S.algo.name === 'dc_atr_structure') {
      hint.textContent = 'DC: marker nằm ĐÚNG giá close (không snap lên wick). Đường nối chỉ giữa hai pivot đã xác nhận; ứng viên là nét đứt. Dải đáy = trạng thái theo swing đã xác nhận, bắt đầu từ lúc biết. Chữ nhãn tự ẩn khi zoom xa (nhãn DC dày hơn ~1 nhãn / 26 px).';
    } else {
      hint.textContent = 'Bật/tắt lớp marker cho lần chạy hiện tại. Replay vẫn chỉ hiện sự kiện đã xác nhận tại con trỏ.';
    }
    var isDc = S.algo.name === 'dc_atr_structure';
    $('#dc-layers').hidden = !isDc;
    $('#btn-baseline').hidden = !isDc;
    renderParamForm();
    syncTimeframeParam();
  }

  /** Tham số `timeframe` (nếu thuật toán có) luôn theo khung của dataset đang chọn. */
  function syncTimeframeParam() {
    var el = $('#param-timeframe');
    if (el && S.dataset && S.dataset.timeframe) {
      el.value = S.dataset.timeframe;
      el.title = 'Tự điền theo dataset đang chọn (' + S.dataset.timeframe + ').';
    }
  }

  /** Ẩn tham số không có hiệu lực (ParamSpec.show_if), vd reversal_pct khi mode = atr. */
  function applyParamVisibility() {
    if (!S.algo) return;
    S.algo.params.forEach(function (p) {
      if (!p.show_if) return;
      var wrap = $('#param-form [data-param-wrap="' + p.name + '"]');
      var ctl = $('#param-' + p.show_if.param);
      if (wrap && ctl) wrap.hidden = ctl.value !== p.show_if.value;
    });
  }

  function renderParamForm() {
    var box = $('#param-form');
    if (!S.algo) { box.innerHTML = ''; return; }
    box.innerHTML = S.algo.params.map(function (p) {
      return '<div data-param-wrap="' + esc(p.name) + '">' + fieldHtml(p) + '</div>';
    }).join('');
    S.algo.params.forEach(function (p) {
      if (!p.show_if) return;
      var ctl = $('#param-' + p.show_if.param);
      if (ctl && !ctl.dataset.visBound) {
        ctl.dataset.visBound = '1';
        ctl.addEventListener('change', applyParamVisibility);
      }
    });
    applyParamVisibility();

    function fieldHtml(p) {
      var id = 'param-' + p.name;
      if (p.type === 'bool') {
        return '<label class="check" title="' + esc(p.help_vi) + '">' +
          '<input type="checkbox" id="' + id + '" data-param="' + esc(p.name) + '"' + (p.default ? ' checked' : '') + '>' +
          '<span>' + esc(p.label_vi) + '</span></label>';
      }
      if (p.type === 'choice') {
        return '<label class="field" title="' + esc(p.help_vi) + '"><span>' + esc(p.label_vi) + '</span>' +
          '<select id="' + id + '" data-param="' + esc(p.name) + '">' +
          (p.choices || []).map(function (c) { return '<option' + (c === p.default ? ' selected' : '') + '>' + esc(c) + '</option>'; }).join('') +
          '</select></label>';
      }
      if (p.type === 'str' || p.type === 'string') {
        return '<label class="field" title="' + esc(p.help_vi) + '"><span>' + esc(p.label_vi) + '</span>' +
          '<input id="' + id + '" data-param="' + esc(p.name) + '" type="text" value="' + esc(p.default) + '"></label>' +
          (p.help_vi ? '<p class="hint">' + esc(p.help_vi) + '</p>' : '');
      }
      var attrs = ' type="number" value="' + esc(p.default) + '"';
      if (p.min !== null && p.min !== undefined) attrs += ' min="' + p.min + '"';
      if (p.max !== null && p.max !== undefined) attrs += ' max="' + p.max + '"';
      attrs += ' step="' + (p.step || (p.type === 'int' ? 1 : 'any')) + '"';
      return '<label class="field" title="' + esc(p.help_vi) + '"><span>' + esc(p.label_vi) + '</span>' +
        '<input id="' + id + '" data-param="' + esc(p.name) + '"' + attrs + '></label>' +
        (p.help_vi ? '<p class="hint">' + esc(p.help_vi) + '</p>' : '');
    }
  }

  function collectParams() {
    var out = {};
    $$('#param-form [data-param]').forEach(function (el) {
      var name = el.getAttribute('data-param');
      var spec = S.algo.params.filter(function (p) { return p.name === name; })[0];
      if (!spec) return;
      if (spec.type === 'bool') out[name] = el.checked;
      else if (spec.type === 'int') out[name] = parseInt(el.value, 10);
      else if (spec.type === 'float') out[name] = parseFloat(el.value);
      else out[name] = el.value;
    });
    return out;
  }

  L.applyParamVisibility = applyParamVisibility;
  L.collectParams = collectParams;
  L.loadAlgorithms = loadAlgorithms;
  L.selectAlgorithm = selectAlgorithm;
  L.syncTimeframeParam = syncTimeframeParam;
})(window.MSL);
