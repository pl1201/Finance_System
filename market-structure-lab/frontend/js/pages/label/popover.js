/* Trang Gán nhãn — bảng thao tác cạnh nến khi bấm nến có nhãn / đề xuất. */
(function (MSL) {
  'use strict';

  var G = MSL.label;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = G.S;
  var TYPES = G.TYPES;

  //
  // Bấm vào nến đã có nhãn nháp hoặc đề xuất đang hiện (chấm xám) -> mở bảng nhỏ
  // cạnh nến: chấp nhận / bỏ / chấp nhận thành loại khác cho đề xuất; đổi loại /
  // dời nến / sửa giá / xoá cho nhãn; thêm nhãn khác vào cùng nến. Nến trống vẫn
  // gán nhanh như cũ; Shift+click luôn là gán/gỡ nhanh loại đang chọn.

  var SHORT = {};   // tên ngắn trên nút đổi loại, từ `short` của loại nhãn plugin khai báo
  TYPES.forEach(function (t) { SHORT[t.id] = t.short; });

  /** Nhãn nháp và đề xuất ĐANG HIỆN trên chart tại nến `idx`. */
  function itemsAtBar(idx) {
    var out = { labels: [], sugs: [] };
    S.draft.forEach(function (lb, i) { if (lb.bar_index === idx) out.labels.push(i); });
    if (S.auto) {
      S.auto.items.forEach(function (it, i) {
        if (it.bar_index !== idx) return;
        var st = G.itemState(it);
        if (st === 'pending' || st === 'removed') out.sugs.push(i);
      });
    }
    return out;
  }

  function typeChips(action, attrs, skip, current) {
    return '<div class="pop-types">' + TYPES.map(function (t) {
      if (skip && skip[t.id]) return '';
      var on = t.id === current;
      return '<button type="button" class="pop-chip' + (on ? ' on' : '') + '" data-pa="' + action + '"' +
        attrs + ' data-t="' + t.id + '"' + (on ? ' disabled' : '') +
        ' title="' + esc(t.label + ' (' + t.id + ')') + '">' +
        '<span class="sw" style="background:' + t.sw + '"></span>' + SHORT[t.id] + '</button>';
    }).join('') + '</div>';
  }

  function openPop(idx) {
    var at = itemsAtBar(idx);
    S.pop = { bar: idx };
    S.chart.setTooltipSuppressed(true);
    if (at.sugs.length) S.auto.cursor = at.sugs[0];   // A / X trong bảng duyệt trỏ đúng đề xuất này
    if (at.labels.length) {
      var lb = S.draft[at.labels[0]];
      S.selected = { bar_index: lb.bar_index, structure_type: lb.structure_type };
    }
    G.renderDraft();   // vẽ lại chart + bảng nháp + bảng thao tác
  }

  function closePop() {
    if (!S.pop) return;
    S.pop = null;
    S.chart.setTooltipSuppressed(false);
    renderPop();
  }

  function renderPop() {
    var el = $('#bar-pop');
    if (!el) return;
    if (!S.pop || !G.barByIndex(S.pop.bar)) {
      el.hidden = true;
      el.innerHTML = '';
      if (S.pop) { S.pop = null; S.chart.setTooltipSuppressed(false); }
      return;
    }
    var idx = S.pop.bar;
    var bar = G.barByIndex(idx);
    var at = itemsAtBar(idx);
    var html = '<div class="pop-head"><span>Nến <span class="mono">#' + idx + '</span> · ' +
      esc(G.barTimeText(idx)) + '</span>' +
      '<button type="button" class="pop-x" data-pa="close" title="Đóng (Esc)">×</button></div>';

    at.sugs.forEach(function (ai) {
      var it = S.auto.items[ai];
      html += '<div class="pop-item pop-sug">' +
        '<div class="pop-title"><span class="badge b-' + esc(it.structure_type) + '">' +
          esc(it.structure_type) + '</span> <span class="st-pending">đề xuất</span> · ' +
          esc(it.source_algorithm || S.auto.algorithm) + '</div>' +
        '<div class="pop-meta">giá <span class="mono">' + G.fmtNum(it.price) + '</span> · xác nhận ở nến #' +
          it.confirmed_bar_index + ' (trễ ' + it.confirmation_lag_bars + ')</div>' +
        '<div class="pop-row">' +
          '<button type="button" class="btn btn-primary btn-sm" data-pa="acc" data-ai="' + ai + '">Chấp nhận</button>' +
          '<button type="button" class="btn btn-secondary btn-sm" data-pa="rej" data-ai="' + ai + '">Bỏ</button>' +
        '</div>' +
        '<div class="pop-sub">Chấp nhận nhưng đổi thành:</div>' +
        typeChips('accas', ' data-ai="' + ai + '"', null, it.structure_type) +
        '</div>';
    });

    at.labels.forEach(function (di) {
      var lb = S.draft[di];
      html += '<div class="pop-item pop-lab">' +
        '<div class="pop-title"><span class="badge b-' + esc(lb.structure_type) + '">' +
          esc(lb.structure_type) + '</span> ' + G.sourceCell(lb) + '</div>' +
        '<div class="pop-sub">Đổi loại:</div>' +
        typeChips('retype', ' data-di="' + di + '"', null, lb.structure_type) +
        '<div class="pop-row">' +
          '<button type="button" class="btn btn-secondary btn-sm" data-pa="mv" data-di="' + di +
            '" data-d="-1" title="Dời sang nến trước ([)">◀</button>' +
          '<button type="button" class="btn btn-secondary btn-sm" data-pa="mv" data-di="' + di +
            '" data-d="1" title="Dời sang nến sau (])">▶</button>' +
          '<label class="pop-price">Giá <input type="number" step="any" data-pp="' + di + '" value="' +
            esc(lb.price) + '"></label>' +
          '<button type="button" class="btn btn-secondary btn-sm pop-del" data-pa="del" data-di="' + di +
            '" title="Xoá nhãn (Delete)">Xoá</button>' +
        '</div></div>';
    });

    if (!at.sugs.length && !at.labels.length) {
      html += '<div class="pop-meta">Nến này chưa có nhãn.</div>';
    }
    var have = {};
    at.labels.forEach(function (di) { have[S.draft[di].structure_type] = 1; });
    html += '<div class="pop-sub">Thêm nhãn vào nến này:</div>' + typeChips('add', '', have, null) +
      '<div class="pop-foot">Esc đóng · Shift+click nến = gán nhanh loại đang chọn · Ctrl+Z hoàn tác</div>';

    el.innerHTML = html;
    el.hidden = false;
    el.setAttribute('data-bar', String(bar.index));
    positionPop();
  }

  function positionPop() {
    var el = $('#bar-pop');
    if (!el || !S.pop) return;
    var c = S.chart.barCoords(S.pop.bar);
    if (!c) { el.style.visibility = 'hidden'; return; }   // nến đã cuộn ra khỏi khung nhìn
    el.style.visibility = '';
    var wrap = el.parentNode;
    var cw = wrap.clientWidth, ch = wrap.clientHeight;
    var w = el.offsetWidth, h = el.offsetHeight;
    var x = c.x + 16;
    if (x + w > cw - 4) x = c.x - w - 16;
    x = Math.max(4, Math.min(x, cw - w - 4));
    var y = (c.yHigh + c.yLow) / 2 - h / 2;
    y = Math.max(4, Math.min(y, ch - h - 4));
    el.style.left = x + 'px';
    el.style.top = y + 'px';
  }

  function onChartClick(bar, info) {
    if (info.shift) { closePop(); G.addOrToggle(bar); return; }
    var at = itemsAtBar(bar.index);
    if (at.labels.length || at.sugs.length) { openPop(bar.index); return; }
    if (S.pop) { closePop(); return; }   // click ra ngoài chỉ để đóng bảng, không gán nhầm
    G.addOrToggle(bar);
  }

  function onPopAction(ev) {
    var b = ev.target.closest('[data-pa]');
    if (!b || b.disabled) return;
    var act = b.getAttribute('data-pa');
    var ai = parseInt(b.getAttribute('data-ai'), 10);
    var di = parseInt(b.getAttribute('data-di'), 10);
    var t = b.getAttribute('data-t');
    G.showError('');
    if (act === 'close') { closePop(); return; }
    if (act === 'acc' || act === 'accas') {
      var it = S.auto && S.auto.items[ai];
      if (!it) return;
      if (!G.acceptAuto(ai, act === 'accas' ? { structure_type: t } : {})) return;
      var nt = act === 'accas' ? t : it.structure_type;
      S.selected = { bar_index: it.bar_index, structure_type: nt };
      G.renderDraft();
      G.showOk(nt === it.structure_type
        ? 'Đã chấp nhận ' + nt + ' tại nến #' + it.bar_index + '. Nhớ bấm Lưu.'
        : 'Đã chấp nhận đề xuất ' + it.structure_type + ' thành ' + nt + ' (nguồn: auto, người đã sửa).');
      return;
    }
    if (act === 'rej') {
      if (G.rejectAuto(ai)) { G.renderDraft(); G.showOk('Đã bỏ đề xuất. Ctrl+Z để hoàn tác.'); }
      return;
    }
    if (act === 'retype') {
      if (G.editLabel(di, { structure_type: t })) { G.renderDraft(); G.showOk('Đã đổi loại nhãn thành ' + t + '.'); }
      return;
    }
    if (act === 'mv') {
      var lb = S.draft[di];
      if (lb && G.editLabel(di, { bar_index: lb.bar_index + parseInt(b.getAttribute('data-d'), 10) })) G.renderDraft();
      return;
    }
    if (act === 'del') {
      if (!S.draft[di]) return;
      G.pushUndo();
      var gone = S.draft.splice(di, 1)[0];
      S.dirty = true;
      S.selected = null;
      G.renderDraft();
      G.showOk('Đã xoá nhãn ' + gone.structure_type + ' tại nến #' + gone.bar_index + '. Ctrl+Z để hoàn tác.');
      return;
    }
    if (act === 'add') {
      var bar = G.barByIndex(S.pop.bar);
      if (bar) G.addOrToggle(bar, t);
    }
  }

  function bindPop() {
    var el = $('#bar-pop');
    el.addEventListener('click', onPopAction);
    el.addEventListener('change', function (ev) {
      var inp = ev.target.closest('[data-pp]');
      if (!inp) return;
      var ok = G.editLabel(parseInt(inp.getAttribute('data-pp'), 10), { price: parseFloat(inp.value) });
      G.renderDraft();
      if (ok) G.showOk('Đã sửa giá. Ctrl+Z để hoàn tác.');
    });
    // Enter trong ô giá = xác nhận; không để phím lọt xuống phím tắt của trang.
    el.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter' && ev.target.matches('[data-pp]')) ev.target.blur();
    });
    S.chart.onViewChange(positionPop);
  }

  G.bindPop = bindPop;
  G.closePop = closePop;
  G.onChartClick = onChartClick;
  G.renderPop = renderPop;
})(window.MSL);
