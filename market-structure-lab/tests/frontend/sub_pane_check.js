/* Kiểm khung phụ dưới chart chính bằng node (gọi từ test_sub_pane.py) — nạp script thật trong vm với LightweightCharts /
 * ResizeObserver / DOM giả, không cần trình duyệt:
 *   - chart/sub-pane.js (window.SubPane): parse được; giao diện chung MarketChart.baseOptions + tuỳ chọn riêng (trục thời
 *     gian ẩn, trục giá không số, kéo trục giá bị tắt); addHistogram / draw (cả chuỗi / thêm cuối) / reset; linkWith —
 *     khoảng nhìn hai chiều (chart chính dẫn, trừ khi người dùng đang bấm / lăn trên khung; mất pointerup vẫn trả lại),
 *     crosshair hai chiều chỉ theo chuột thật (MarketChart.byMouse — lần LWC phát lại không đẩy, kể cả chỗ không có nến)
 *     qua MarketChart.setBars / barAtTime / crosshairAt / canSync thật, trục giá rộng đúng bằng chart chính mà không đổi
 *     tuỳ chọn chart chính; ẩn / hiện; setAnchorRight;
 *   - hook `pane` mà algos/ict_structure.js đăng ký: lớp, has, init (series + đường 0 + thang cố định), points cả chuỗi /
 *     chỉ nến mới (ctx.from) đổ qua SubPane.draw, legend.
 * In ra JSON {checks: n, failures: [...]}.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const REPO = path.resolve(__dirname, '..', '..');

let checks = 0;
const failures = [];
function ok(cond, msg, extra) {
  checks++;
  if (!cond) failures.push(msg + (extra !== undefined ? ' — ' + JSON.stringify(extra) : ''));
}
function eq(a, b, msg) { ok(JSON.stringify(a) === JSON.stringify(b), msg, { got: a, want: b }); }
const last = (xs) => xs[xs.length - 1];
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ------------------------------------------------------------------ đồ giả

function listeners(o) {
  const m = {};
  o.addEventListener = (type, fn) => { (m[type] = m[type] || []).push(fn); };
  o.dispatch = (type) => { (m[type] || []).forEach((fn) => fn({ type })); };
  return o;
}

function makeSeries(kind, opts) {
  return {
    kind, opts, data: [], priceLines: [],
    setData(d) { this.data = d.slice(); },
    update(item) {
      if (this.data.length && last(this.data).time === item.time) this.data[this.data.length - 1] = item;
      else this.data.push(item);
    },
    createPriceLine(o) { this.priceLines.push(o); return o; }
  };
}

function merge(dst, src) {
  for (const k of Object.keys(src)) {
    const v = src[k];
    if (v && typeof v === 'object' && !Array.isArray(v) && dst[k] && typeof dst[k] === 'object') merge(dst[k], v);
    else dst[k] = v;
  }
  return dst;
}

/** Chart giả: setVisibleLogicalRange chỉ ghi lại (LWC 4.2.3 áp ở khung hình sau); setCrosshairPosition không phát sự kiện
 *  (như LWC 4.2.3). fireRange / fireCross / fireSize = thư viện phát sự kiện. effective() = tuỳ chọn sau mọi applyOptions. */
function makeChart(createOpts) {
  const subs = { cross: [], range: [], size: [] };
  const ts = {
    range: null, applied: [],
    subscribeVisibleLogicalRangeChange(fn) { subs.range.push(fn); },
    subscribeSizeChange(fn) { subs.size.push(fn); },
    setVisibleLogicalRange(r) { this.applied.push(r); },
    getVisibleLogicalRange() { return this.range; }
  };
  const chart = {
    createOpts, opts: [], series: [], crossSet: [], crossCleared: 0, axisWidth: 0,
    applyOptions(o) { this.opts.push(o); },
    effective() { return this.opts.reduce((acc, o) => merge(acc, JSON.parse(JSON.stringify(o))), JSON.parse(JSON.stringify(createOpts || {}))); },
    timeScale() { return ts; },
    priceScale() { return { width: () => chart.axisWidth }; },
    addHistogramSeries(o) { const s = makeSeries('histogram', o); this.series.push(s); return s; },
    removeSeries(s) { this.series = this.series.filter((x) => x !== s); },
    subscribeCrosshairMove(fn) { subs.cross.push(fn); },
    setCrosshairPosition(price, time, series) { this.crossSet.push([price, time, series && series.kind]); },
    clearCrosshairPosition() { this.crossCleared++; },
    fireRange(r) { ts.range = r; subs.range.forEach((fn) => fn(r)); },
    fireCross(p) { subs.cross.forEach((fn) => fn(p)); },
    fireSize() { subs.size.forEach((fn) => fn()); },
    ts
  };
  return chart;
}

const created = [];
const sandbox = listeners({ console, MSL: {} });
sandbox.window = sandbox;                               // như trình duyệt: window === đối tượng toàn cục
sandbox.ResizeObserver = function () { this.observe = function () {}; };
sandbox.LightweightCharts = {
  CrosshairMode: { Normal: 0 }, LineStyle: { Solid: 0 }, LineType: { Simple: 0, WithSteps: 1 },
  createChart(container, opts) { const c = makeChart(opts); created.push(c); return c; }
};
vm.createContext(sandbox);
vm.runInContext('var __now = 1e6; Date.now = function () { return __now; };', sandbox);
const setNow = (t) => vm.runInContext('__now = ' + t + ';', sandbox);
for (const f of ['lib/dom.js', 'lib/format.js', 'algos/registry.js', 'algos/ict_structure_view.js', 'algos/ict_ob_ote_view.js',
  'algos/ict_nhan_dien_view.js', 'algos/ict_structure.js', 'chart/market-chart.js', 'chart/sub-pane.js']) {
  vm.runInContext(fs.readFileSync(path.join(REPO, 'frontend', 'js', f), 'utf8'), sandbox, { filename: f });
}
const MSL = sandbox.MSL;

function newPane(wrap) {
  const sp = new sandbox.SubPane(listeners({ clientWidth: 800, clientHeight: 140 }), { wrap: wrap || { hidden: false } });
  return { sp, pc: last(created) };
}

// ------------------------------------------------------------------ SubPane

function runSubPane() {
  const SubPane = sandbox.SubPane, MC = sandbox.MarketChart;
  ok(typeof SubPane === 'function', 'sub-pane.js parse được và định nghĩa window.SubPane');
  const wrap = { hidden: false };
  const { sp, pc } = newPane(wrap), container = sp.container, eff = pc.effective();
  eq(JSON.parse(JSON.stringify(pc.createOpts)), JSON.parse(JSON.stringify(MC.baseOptions())), 'tạo bằng giao diện chung MarketChart.baseOptions');
  ok(eff.timeScale.visible === false && eff.layout.background.color === '#0f1419', 'trục thời gian ẩn, nền như chart chính', eff);
  ok(eff.handleScale.axisPressedMouseMove.price === false && eff.layout.attributionLogo === false && eff.grid.horzLines.visible === false &&
    eff.crosshair.horzLine.visible === false && eff.kineticScroll.touch === false, 'kéo trục giá tắt; không logo trùng; không đường ngang');
  const fmt = last(pc.opts.filter((o) => o.localization)).localization;
  ok(fmt.priceFormatter(0.7) === '' && /UTC$/.test(pc.createOpts.localization.timeFormatter(0)), 'trục giá không ghi số, giờ UTC');
  ok(pc.opts.some((o) => o.width === 800 && o.height === 140), 'kích thước theo container');

  const a = sp.addHistogram('a', { base: 1.05, color: '#123' });
  const b = sp.addHistogram('b', {});
  ok(a.kind === 'histogram' && pc.series.length === 2 && a.opts.base === 1.05 && a.opts.color === '#123' &&
    a.opts.priceLineVisible === false && a.opts.lastValueVisible === false && a.opts.autoscaleInfoProvider === undefined,
    'addHistogram: series LWC theo tuỳ chọn của plugin, không nhãn giá cuối, thang dọc do series tự khai');

  const d = [{ time: 100, value: 0.5 }, { time: 200 }, { time: 300, value: -0.3 }];
  sp.draw({ a: d, b: d.slice(0, 1), 'khong-co': d }, false);
  sp.draw({ a: [{ time: 400, value: 0.1 }] }, true);
  ok(a.data.length === 4 && last(a.data).value === 0.1 && b.data.length === 1 && pc.series.length === 2,
    'draw: thay cả chuỗi / append thêm nến cuối; key chưa tạo → bỏ qua');

  // chart chính: MarketChart thật (setBars / barAtTime / crosshairAt / canSync / copyRangeTo của prototype) trên chart giả
  const main = Object.create(MC.prototype);
  main.chart = makeChart({});
  main.container = { offsetParent: {} };
  main._plugins = [];
  main._st = {};
  main.candles = { kind: 'candles', setData() {}, setMarkers() {}, priceScale() { return { applyOptions() {} }; } };
  main.chart.ts.range = { from: 0, to: 3 };
  main.chart.axisWidth = 66;
  main.setBars([100, 200, 300, 400].map((t, i) => ({ time: t, index: i, open: 10 + i, high: 11 + i, low: 9 + i, close: 10 + i })));
  sp.linkWith(main);
  ok(main.chart.opts.length === 0, 'linkWith không đổi tuỳ chọn chart chính (trục giá giữ bề rộng tự nhiên)', main.chart.opts);
  ok(pc.effective().rightPriceScale.minimumWidth === 66, 'linkWith: trục giá khung rộng đúng bằng trục giá chart chính');
  eq(last(pc.ts.applied), { from: 0, to: 3 }, 'linkWith: khung lấy khoảng nhìn của chart chính');

  // khoảng nhìn: chart chính dẫn
  main.chart.fireRange({ from: 1, to: 4 });
  eq(last(pc.ts.applied), { from: 1, to: 4 }, 'chart chính cuộn → khung theo');
  const mainApplied = main.chart.ts.applied.length;
  pc.fireRange({ from: 1, to: 4 });
  ok(main.chart.ts.applied.length === mainApplied, 'khung đổi do thư viện / tiếng vọng (không bấm, không lăn) → không đẩy ngược');
  container.dispatch('pointerdown');
  pc.fireRange({ from: 2, to: 5 });
  eq(last(main.chart.ts.applied), { from: 2, to: 5 }, 'kéo trên khung → chart chính theo');
  const paneApplied = pc.ts.applied.length;
  main.chart.fireRange({ from: 2, to: 5 });
  sp.setVisible(true);
  ok(pc.ts.applied.length === paneApplied, 'đang kéo trên khung: tiếng vọng / vẽ lại không giật khung về chart chính');
  setNow(1e6 + 5000);
  main.chart.fireRange({ from: 2, to: 5.2 });
  ok(pc.ts.applied.length === paneApplied, 'bấm giữ lâu vẫn là khung dẫn');
  sandbox.dispatch('pointerup');
  pc.fireRange({ from: 2.5, to: 5.5 });
  eq(last(main.chart.ts.applied), { from: 2.5, to: 5.5 }, 'vừa thả (< 250 ms): khoảng cuối của khung vẫn đẩy sang');
  setNow(1e6 + 6000);
  pc.fireRange({ from: 3, to: 6 });
  eq(last(main.chart.ts.applied), { from: 2.5, to: 5.5 }, 'thả lâu rồi → khung không dẫn nữa');
  main.chart.fireRange({ from: 0, to: 3 });
  eq(last(pc.ts.applied), { from: 0, to: 3 }, 'chart chính dẫn lại');
  container.dispatch('wheel');
  pc.fireRange({ from: 0.5, to: 3 });
  eq(last(main.chart.ts.applied), { from: 0.5, to: 3 }, 'lăn chuột trên khung (zoom) → chart chính theo');
  sp.setVisible(true);
  pc.fireRange({ from: 0.7, to: 3 });
  ok(same(last(main.chart.ts.applied), { from: 0.5, to: 3 }) && same(last(pc.ts.applied), { from: 0, to: 3 }),
    'trang vẽ lại trong 250 ms sau khi lăn → chart chính dẫn ngay (khung theo, khung đổi do dữ liệu không đẩy ngược)');
  setNow(1e6 + 7000);
  container.dispatch('pointerdown');
  sandbox.dispatch('pointermove');   // nút đã thả nhưng mất pointerup (vd thả ngoài cửa sổ): rê chuột với buttons = 0
  setNow(1e6 + 7300);
  main.chart.fireRange({ from: 1, to: 3 });
  eq(last(pc.ts.applied), { from: 1, to: 3 }, 'mất pointerup: lần rê chuột không giữ nút kế tiếp → chart chính dẫn lại');

  // crosshair
  const seen = [];
  sp.onCrosshair((bar) => seen.push(bar ? bar.index : null));
  main.chart.fireCross({ time: 200, point: { x: 1, y: 1 }, sourceEvent: {} });
  eq([last(pc.crossSet), seen], [[0, 200, 'histogram'], [1]], 'chuột trên chart chính → crosshair khung cùng nến; fn(nến chính)');
  main.chart.fireCross({ time: 300, point: { x: 1, y: 1 } });
  eq([last(pc.crossSet), last(seen)], [[0, 300, 'histogram'], 2],
    'LWC phát lại ở chart chính (nến dưới chuột đổi khi replay / cuộn) → khung + chú giải theo');
  pc.fireCross({ time: 200, point: { x: 1, y: 1 } });
  ok(main.chart.crossSet.length === 0 && last(seen) === 1, 'LWC phát lại ở khung → chỉ chú giải, không đẩy sang chart chính');
  pc.fireCross({ time: undefined, point: { x: 1, y: 1 } });
  ok(main.chart.crossCleared === 0 && main._crossByLink === undefined && last(seen) === null,
    'LWC phát lại ở khung chỗ không có nến (có point, không sourceEvent — vd sau reset) → không xoá crosshair chart chính');
  main.chart.fireCross({ time: undefined, point: undefined });
  ok(pc.crossCleared === 1 && last(seen) === null, 'rời chart chính → xoá crosshair khung, fn(null)');
  pc.fireCross({ time: 300, point: { x: 1, y: 1 }, sourceEvent: {} });
  ok(same(last(main.chart.crossSet), [12, 300, 'candles']) && main._crossByLink === true && !main._linked && last(seen) === 2,
    'chuột trên khung → crosshair chart chính tại close (crosshairAt)');
  // tooltip chart chính: ẩn cho lần LWC phát lại vị trí do khung đặt; chuột thật vào chart chính → lại như thường (không tắt mãi)
  main._prims = [];
  main.digits = 2;
  main.container.clientWidth = 800;
  main.container.clientHeight = 400;
  main.tooltipEl = { hidden: false, style: {}, offsetWidth: 10, offsetHeight: 10 };
  main._onCrosshair({ time: 300, point: { x: 5, y: 5 } });
  ok(main.tooltipEl.hidden === true, 'tooltip chart chính ẩn khi LWC phát lại crosshair do khung đặt');
  main._onCrosshair({ time: 300, point: { x: 5, y: 5 }, sourceEvent: {} });
  main._onCrosshair({ time: 300, point: { x: 5, y: 5 } });
  ok(main.tooltipEl.hidden === false && main._crossByLink === false, 'sau khi chuột thật vào chart chính: phát lại vẫn hiện tooltip');
  pc.fireCross({ time: 999, point: { x: 1, y: 1 }, sourceEvent: {} });
  ok(main.chart.crossCleared === 1 && last(seen) === null, 'nến không có ở chart chính → xoá crosshair chart chính');

  // bề rộng trục giá theo chart chính
  main.chart.axisWidth = 96;
  main.chart.fireSize();
  ok(pc.effective().rightPriceScale.minimumWidth === 96, 'trục giá chart chính rộng hơn → khung theo');
  main.chart.axisWidth = 70;
  main.chart.fireRange({ from: 0, to: 2 });
  ok(pc.effective().rightPriceScale.minimumWidth === 70, 'trục giá chart chính hẹp lại → khung theo đúng bề rộng');
  main.chart.axisWidth = 0;
  main.chart.fireSize();
  ok(pc.effective().rightPriceScale.minimumWidth === 70, 'chart chính chưa vẽ trục (0) → giữ bề rộng cũ');

  // ẩn / hiện, giữ mép phải, gỡ series
  sp.setVisible(false);
  ok(wrap.hidden === true, 'setVisible(false) ẩn khung');
  const hiddenApplied = pc.ts.applied.length, crossHidden = pc.crossSet.length;
  main.chart.fireRange({ from: 5, to: 9 });
  main.chart.fireCross({ time: 100, point: { x: 1, y: 1 }, sourceEvent: {} });
  ok(pc.ts.applied.length === hiddenApplied && pc.crossSet.length === crossHidden, 'khung ẩn → không đồng bộ');
  container.clientWidth = 640;
  sp.setVisible(true);
  ok(wrap.hidden === false && pc.opts.some((o) => o.width === 640) && same(last(pc.ts.applied), { from: 5, to: 9 }),
    'hiện lại → đúng kích thước + khoảng nhìn chart chính');
  sp.setAnchorRight(true);
  ok(pc.effective().timeScale.rightBarStaysOnScroll === true, 'setAnchorRight: zoom giữ mép phải (replay)');
  main.setBars([]);
  main.chart.fireRange({ from: 1, to: 2 });
  pc.fireCross({ time: 100, point: { x: 1, y: 1 }, sourceEvent: {} });
  ok(main.chart.crossCleared === 1, 'chart chính chưa có nến → không đẩy crosshair sang');
  sp.reset();
  const crossReset = pc.crossSet.length;
  main.chart.fireCross({ time: 100, point: { x: 1, y: 1 } });
  ok(pc.series.length === 0 && pc.crossSet.length === crossReset, 'reset gỡ mọi series; chưa có series → không đặt crosshair khung');
  sp.addHistogram('c', {});
  main.chart.fireCross({ time: 200, point: { x: 1, y: 1 } });
  eq(last(pc.crossSet), [0, 200, 'histogram'], 'series tạo sau reset làm mốc crosshair của khung');
}

// ------------------------------------------------------------------ hook `pane` của ict_structure

function runHook() {
  const ND = MSL.ictNdView, plugin = MSL.algos.forAlgorithm('ict_structure'), hook = plugin && plugin.pane;
  ok(!!hook && hook.layer === 'ict_nd_pane' && hook.title === 'Trạng thái' && MSL.algos.defaultLayers().ict_nd_pane === true,
    'ict_structure đăng ký hook pane, lớp ict_nd_pane bật sẵn');
  const { sp, pc } = newPane();
  hook.init(sp);
  const [sa, sb, sn] = pc.series;
  ok(pc.series.length === 3 && pc.series.every((s) => s.kind === 'histogram'), 'init: ba histogram a / b / nen');
  ok(sn.opts.base === ND.PANE.sqzBase && sa.priceLines.length === 1 && sa.priceLines[0].price === 0 &&
    sa.priceLines[0].axisLabelVisible === false, 'dải nén đặt base; đường 0 = price line của a, không nhãn trục');
  ok(pc.series.every((s) => same(s.opts.autoscaleInfoProvider(), { priceRange: { minValue: -1.3, maxValue: 1.3 } })),
    'thang dọc cố định −1,3…+1,3 (ND.PANE.top) cho cả ba series');
  const tl = [0, 1, 2].map((i) => ({ bar_index: i, time: 10 * i, nd_trang_thai: i ? 'trend_len' : null, nd_tu: i ? 1 : null,
    nd_do_manh: 0.2, nd_nen: i === 2 }));
  const bars = tl.map((p) => ({ time: p.time, index: p.bar_index, close: 1 }));
  ok(hook.has({ timeline: tl }) && !hook.has({ timeline: [] }) && !hook.has({ timeline: [{ bar_index: 0, dealing_hi: 1 }] }),
    'has: chỉ khi timeline có cột nd_trang_thai');
  const want = ND.statePaneSeries(tl, bars, Infinity);
  const full = hook.points({ timeline: tl.slice(0, 2), bars: bars.slice(0, 2), cursor: 1, from: 0 });
  eq(Object.keys(full), ['a', 'b', 'nen'], 'points: khoá = tên series của init');
  ok(['a', 'b', 'nen'].every((k) => same(full[k], want[k].slice(0, 2))), 'points ctx.from = 0: cả chuỗi tới con trỏ');
  const step = hook.points({ timeline: tl, bars: bars, cursor: 2, from: 2 });
  ok(['a', 'b', 'nen'].every((k) => same(step[k], want[k].slice(2))), 'points ctx.from = n − 1: chỉ nến mới');
  sp.draw(full, false);
  sp.draw(step, true);
  ok([sa, sb, sn].every((s, j) => same(s.data, want[['a', 'b', 'nen'][j]])),
    'draw cả chuỗi rồi append nến mới = cả chuỗi vẽ một lần');
  const html = hook.legend(null, { timeline: tl, bars: bars, cursor: 2 }), hov = hook.legend(bars[1], { timeline: tl, bars: bars, cursor: 2 });
  ok(['▲', 'trend lên', '▼', 'trend xuống', '▬', 'range', 'sideway nhiễu', '▔', 'nén'].every((w) => html.indexOf(w) >= 0),
    'legend: chữ cho mọi màu', html);
  ok(html.indexOf('<span class="pl-at">#2 · trend lên · mạnh 0.20 · 2 nến (từ #1) · nén</span>') > 0 &&
    hov.indexOf('<span class="pl-at">#1 · trend lên · mạnh 0.20 · 1 nến (từ #1)</span>') > 0, 'legend: trạng thái ở nến con trỏ / nến dưới chuột', hov);
}

try {
  runSubPane();
  runHook();
} catch (err) {
  failures.push('LỖI: ' + (err && err.stack || err));
}
process.stdout.write(JSON.stringify({ checks: checks, failures: failures }));
