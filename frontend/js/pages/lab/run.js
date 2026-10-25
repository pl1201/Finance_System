/* Trang Thử nghiệm — chạy thuật toán, baseline so sánh (pivot 3/3), panel baseline đồng bộ, khung phụ dưới chart (hook
 * `pane` của plugin), vẽ sự kiện lên chart. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var detectDigits = MSL.format.detectDigits;
  var esc = MSL.dom.esc;
  var S = L.S;

  async function doRun() {
    if (!S.dataset) return;
    if (!L.confirmHeavyRange('Chạy thuật toán')) return;
    await L.stopReplay();
    if (S.mode !== 'full') L.switchMode('full');     // kết quả chạy xem ở «Toàn lịch sử»
    L.loading(true);
    L.banner(null);
    try {
      var payload = {
        dataset_id: S.dataset.id,
        algorithm: S.algo.name,
        params: L.collectParams(),
        range_start: L.fromLocalInput($('#range-start').value),
        range_end: L.fromLocalInput($('#range-end').value),
        label: $('#run-label').value,
        save: $('#run-save').checked
      };
      var res = await API.run(payload);
      var barsRes = await API.bars(S.dataset.id, payload.range_start, payload.range_end);
      S.allBars = barsRes.bars;
      S.digits = detectDigits(S.allBars);
      S.run = res;
      S.selectedEventId = null;
      if (S.baseline && (S.baseline.range_start !== res.range_start || S.baseline.range_end !== res.range_end ||
          S.baseline.dataset_id !== res.dataset_id)) S.baseline = null;
      L.renderEventDetail(null);

      S.chart.setDigits(S.digits);
      S.chart.setBars(S.allBars);
      applyChartEvents();
      S.chart.showLast(350);

      $('#chart-empty').hidden = true;
      $('#btn-export-csv').disabled = !res.saved;
      $('#btn-export-png').disabled = false;
      L.renderEvents(res.events);
      L.renderStats(res);
      L.renderAlgoNotes(res.algorithm, res.stats, res.data_status, res.pending_state);

      var algoWarn = MSL.algos.callFor(res.algorithm, 'runWarning', res);   // vd DC: chưa có pivot nào
      if (res.data_status !== 'OK') {
        L.banner('warn', esc(res.data_status_message_vi));
      } else if (algoWarn) {
        L.banner('warn', algoWarn);
      } else if (!res.events.length) {
        L.banner('warn', 'Chạy xong nhưng <strong>không có sự kiện nào</strong>. Dữ liệu vẫn hợp lệ — hãy thử giảm số nến trái/phải hoặc mở rộng khoảng thời gian.');
      } else {
        L.banner('ok', 'Đã chạy <strong>' + res.bars_processed + '</strong> nến trong <strong>' +
          res.duration_ms.toFixed(1) + ' ms</strong>, phát hiện <strong>' + res.events.length + '</strong> sự kiện.' +
          (res.saved ? ' Lần chạy đã lưu: <code>' + esc(res.run_id) + '</code>.' : ' (không lưu).') +
          ' Chart đang hiển thị 350 nến cuối — cuộn hoặc zoom để xem phần còn lại.');
      }
      if (res.saved) await L.loadRuns();
    } catch (e) {
      L.banner('error', 'Chạy thất bại: ' + esc(e.message));
    } finally {
      L.loading(false);
    }
  }

  /** Cấu hình so baseline của thuật toán `name` (plugin khai báo `baselineCompare`), hoặc null. */
  function compareSpec(name) {
    var own = name ? MSL.algos.forAlgorithm(name) : null;
    return (own && own.baselineCompare) || null;
  }

  /** Nguồn để so baseline: phiên replay đang mở (nếu có) hoặc lần chạy đang hiển thị. */
  function baselineSource() {
    var r = L.replaying();
    if (r && r.live) return null;           // luồng live không phải dataset nghiên cứu: không so baseline
    if (r && r.snapshot && r.bars.length) {
      return {
        algorithm: r.snapshot.algorithm, dataset_id: r.snapshot.dataset.id,
        checksum: r.snapshot.dataset.checksum_sha256,
        range_start: r.bars[0].bar_time, range_end: r.bars[r.bars.length - 1].bar_time,
        events: r.events, label: 'replay', replay: true
      };
    }
    if (!S.run) return null;
    return {
      algorithm: S.run.algorithm, dataset_id: S.run.dataset_id, checksum: S.run.dataset_checksum,
      range_start: S.run.range_start, range_end: S.run.range_end, events: S.run.events,
      label: S.run.run_id || null, replay: false
    };
  }

  /**
   * Chạy swing_pivot 3/3 (tham số mặc định, không đổi) trên CÙNG dataset và khoảng
   * của run hiện tại (thuật toán có `baselineCompare`, vd DC) rồi phủ pivot wick lên chart.
   * Lưu run nếu đang bật «Lưu».
   */
  async function runBaseline() {
    var src = baselineSource();
    var cmp = src ? compareSpec(src.algorithm) : null;
    if (!cmp) {
      var able = MSL.algos.list().filter(function (p) { return p.baselineCompare; });
      L.banner('warn', 'So sánh baseline cần một lần chạy hoặc phiên replay của <strong>' +
        able.map(function (p) { return p.algorithms.join(', '); }).join(', ') + '</strong>. ' +
        'Chọn thuật toán ' + able.map(function (p) { return '«' + p.title + '»'; }).join(' hoặc ') +
        ' rồi bấm <strong>Chạy thử</strong> hoặc mở replay.');
      return;
    }
    L.loading(true);
    try {
      var base = await API.run({
        dataset_id: src.dataset_id, algorithm: 'swing_pivot', params: { left: 3, right: 3 },
        range_start: src.range_start, range_end: src.range_end,
        label: 'baseline pivot 3/3 — so với ' + (src.label || cmp.unsavedLabel), save: $('#run-save').checked
      });
      if (base.dataset_checksum !== src.checksum) throw new Error('Checksum dataset khác nhau — không so sánh.');
      S.baseline = {
        run_id: base.saved ? base.run_id : null, events: base.events, dataset_id: base.dataset_id,
        range_start: base.range_start, range_end: base.range_end
      };
      L.setLayer('baseline', true);   // S.layers + checkbox + lớp phụ thuộc (data-requires)
      applyChartEvents();
      if (src.replay) L.renderAlgoNotes(src.algorithm, null, S.replay.snapshot.data_status, S.replay.snapshot.pending_state);
      else L.renderAlgoNotes(S.run.algorithm, S.run.stats, S.run.data_status, S.run.pending_state);
      var cnt = function (evs, a, b) { return evs.filter(function (e) { return e.structure_type === a || e.structure_type === b; }).length; };
      var lagMed = function (evs, a, b) {
        var xs = evs.filter(function (e) { return e.structure_type === a || e.structure_type === b; })
          .map(function (e) { return e.confirmation_lag_bars; }).sort(function (x, y) { return x - y; });
        return xs.length ? xs[Math.floor((xs.length - 1) / 2)] : '—';
      };
      L.banner('ok', 'Baseline swing_pivot v' + esc(base.algorithm_version) + ' (3/3, wick): <strong>' + cnt(base.events, 'SWING_HIGH', 'SWING_LOW') +
        '</strong> pivot trên cả khoảng, trễ trung vị ' + lagMed(base.events, 'SWING_HIGH', 'SWING_LOW') + ' nến · ' + cmp.label + ': <strong>' +
        cnt(src.events, cmp.pivotTypes[0], cmp.pivotTypes[1]) + '</strong> pivot' + (src.replay ? ' (tới con trỏ replay)' : '') +
        ', trễ trung vị ' + lagMed(src.events, cmp.pivotTypes[0], cmp.pivotTypes[1]) +
        (src.replay ? ' nến. Trong replay, baseline cũng chỉ hiện pivot đã xác nhận tới con trỏ.' : '') +
        ' nến. Cùng checksum <code>' + esc(String(base.dataset_checksum).slice(0, 12)) + '…</code> và khoảng thời gian.' +
        (base.saved ? ' Đã lưu <code>' + esc(base.run_id) + '</code> — chọn hai run ở tab Lịch sử để so sánh chi tiết.' : ''));
      if (base.saved) await L.loadRuns();
    } catch (e) {
      L.banner('error', 'Không chạy được baseline: ' + esc(e.message));
    } finally {
      L.loading(false);
    }
  }

  /** Baseline chỉ dùng được khi cùng chuỗi nến (bar_index tính từ đầu khoảng chạy). */
  function baselineMatches(bars) {
    if (!S.baseline || !bars || !bars.length) return false;
    return bars[0].bar_time === S.baseline.range_start && bars[bars.length - 1].bar_time === S.baseline.range_end;
  }

  /**
   * Panel thứ hai cho run baseline: cùng nến, cùng con trỏ replay; cuộn/zoom và
   * crosshair liên kết với chart chính (MarketChart.linkWith).
   */
  function renderSplit() {
    var cmp = S.algo ? compareSpec(S.algo.name) : null;
    var want = $('#chk-split-baseline').checked && !!cmp;
    var replay = L.replaying();
    var src = replay ? S.replay.bars : S.allBars;
    var ok = want && baselineMatches(src);
    $('#chart2-wrap').hidden = !ok;
    $('.main').classList.toggle('split', !!ok);
    if (!ok) {
      S.c2 = null;
      return;
    }
    if (!S.chart2) {
      S.chart2 = new window.MarketChart($('#chart2'), $('#chart2-tooltip'));
      S.chart2.setCompactPane();
      S.chart.linkWith(S.chart2);
      S.chart2.setAnchorRight(S.mode !== 'full');
    }
    var n = replay ? S.replay.cursor + 1 : src.length;
    var c2 = S.c2 || { src: null, n: -1 };
    S.chart2.setDigits(S.digits);
    if (c2.src === src && n === c2.n + 1 && n > 0) S.chart2.appendBar(src[n - 1]);
    else if (!(c2.src === src && n === c2.n)) S.chart2.setBars(src.slice(0, n));
    S.c2 = { src: src, n: n };
    S.chart2.setEvents(S.baseline.events, [], {
      layers: { swing: true, swing_l2: true, hhll: S.layers[cmp.labelsLayer], eq: S.layers[cmp.labelsLayer] },
      markerAtConfirm: false, replayCursor: replay ? S.replay.cursor : null
    });
    S.chart.copyRangeTo(S.chart2);
  }

  /**
   * Khung phụ ngay dưới chart chính — hook `pane` của plugin vẽ kết quả đang xem (hợp đồng ở đầu algos/registry.js), không
   * so tên thuật toán. Một SubPane (chart/sub-pane.js) dùng chung, tạo lần đầu cần; plugin khác vẽ khung → gỡ series, init
   * lại. Chỉ lấy điểm (hook.points) khi nến / timeline đổi; replay tiến một nến (MarketChart.appendBar: cùng mảng nến, dài
   * thêm 1 — setBars luôn nhận mảng mới) → ctx.from = nến mới, khung chỉ thêm nến đó. Không có hook / lớp tắt / has() =
   * false → ẩn, gỡ series.
   */
  function renderPane(res, replay) {
    var own = res ? MSL.algos.forAlgorithm(replay ? (res.snapshot || {}).algorithm : res.algorithm) : null;
    var hook = own && own.pane, P = S.pane;
    var ctx = hook ? { timeline: res.timeline || [], bars: S.chart.bars, cursor: replay ? res.cursor : Infinity, from: 0 } : null;
    if (!ctx || !S.layers[hook.layer] || (hook.has && !hook.has(ctx))) {
      if (P && P.own) { P.sp.setVisible(false); P.sp.reset(); P.own = null; P.last = null; P.hover = null; }
      return;
    }
    if (!P) {
      $('#pane-wrap').hidden = false;   // LWC cần kích thước thật lúc tạo chart
      P = S.pane = { sp: new window.SubPane($('#pane'), { wrap: $('#pane-wrap') }), own: null, last: null, hover: null, html: null };
      P.sp.linkWith(S.chart);
      P.sp.setAnchorRight(S.mode !== 'full');
      P.sp.onCrosshair(function (bar) { S.pane.hover = bar; renderPaneLegend(bar); });
    }
    if (P.own !== own) { P.sp.reset(); hook.init(P.sp); P.own = own; P.last = null; }
    var last = P.last, n = ctx.bars.length, same = last && last.ctx.bars === ctx.bars;
    if (!(same && last.n === n && last.ctx.timeline === ctx.timeline)) {
      if (same && last.n === n - 1) ctx.from = n - 1;
      P.sp.draw(hook.points(ctx), ctx.from > 0);
    }
    P.sp.setVisible(true);              // sau khi có dữ liệu: khoảng nhìn chép từ chart chính áp lên đúng chuỗi nến
    P.last = { ctx: ctx, n: n };
    renderPaneLegend(P.hover);          // đang rê chuột thì giữ nến dưới chuột (replay chạy, chọn sự kiện…)
  }

  /** Dòng chú giải của khung phụ (#pane-legend): tiêu đề hook + html plugin trả cho nến dưới chuột (null = nến con trỏ). */
  function renderPaneLegend(bar) {
    var P = S.pane, hook = P && P.last ? P.own.pane : null;
    if (!hook) return;
    var html = '<b class="pane-title">' + esc(hook.title || '') + '</b>' + (hook.legend ? hook.legend(bar, P.last.ctx) || '' : '');
    if (html === P.html) return;
    P.html = html;
    $('#pane-legend').innerHTML = html;
  }

  /** Vẽ lại mọi thứ theo kết quả đang xem (lần chạy / phiên replay; không có → các khung riêng ẩn). */
  function applyChartEvents() {
    var replay = !!L.replaying();
    var res = replay ? S.replay : (S.mode === 'live' ? null : S.run);   // Live chưa mở luồng: không vẽ lần chạy cũ
    var baseEvs = baselineMatches(replay ? S.replay.bars : S.allBars) ? S.baseline.events : [];
    // pendingState: trạng thái nội bộ lõi tại con trỏ (nến cuối của lần chạy / con trỏ replay) — plugin đọc phần
    // chưa thành sự kiện (vd vùng đã lấy, chờ sweep/run).
    if (replay) {
      S.chart.setEvents(S.replay.events, S.replay.timeline, {
        layers: S.layers, markerAtConfirm: false, replayCursor: S.replay.cursor,
        baselineEvents: baseEvs, selectedEventId: S.selectedEventId,
        pendingState: S.replay.snapshot ? S.replay.snapshot.pending_state : null
      });
    } else if (res) {
      S.chart.setEvents(S.run.events, S.run.timeline, {
        layers: S.layers, markerAtConfirm: $('#chk-confirm-position').checked, replayCursor: null,
        baselineEvents: baseEvs, selectedEventId: S.selectedEventId, pendingState: S.run.pending_state || null
      });
    }
    $('#btn-replay-here').hidden = !(S.mode === 'full' && S.run);
    MSL.algos.each('syncLegend', res ? res.timeline : [], res ? res.events : [], S);   // chú giải riêng (cấp 2, DC…)
    renderPane(res, replay);                    // khung phụ ngay dưới chart (hook `pane`, vd trạng thái ict_structure)
    renderSplit();
  }

  L.applyChartEvents = applyChartEvents;
  L.doRun = doRun;
  L.renderSplit = renderSplit;
  L.runBaseline = runBaseline;
})(window.MSL);
