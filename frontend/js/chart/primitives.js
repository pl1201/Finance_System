/* Chart — ba lớp vẽ dùng chung bằng series primitive của Lightweight Charts 4.2 (MSL.primitives).
 *
 * Không biết thuật toán nào: plugin đưa vào MẢNG ĐỐI TƯỢNG THUẦN, primitive tự vẽ lại mỗi khung hình (cuộn / zoom
 * không cần dựng lại). Gắn bằng `mc.attachPrimitive(p)` (MarketChart: gắn lên series nến + đăng ký để tooltip hitTest
 * đúng vị trí chuột) hoặc thẳng `series.attachPrimitive(p)`.
 *
 * Toạ độ ngang `l` là CHỈ SỐ LOGIC của LWC: vị trí nến trong dữ liệu đã nạp (0 = nến đầu), số lẻ = giữa hai nến,
 * lớn hơn nến cuối = vùng tương lai bên phải (vẽ được «con trỏ + N nến»). Đổi chỉ số nến (`bar.index`) sang chỉ số
 * logic: MarketChart.logicalOf(index). LWC 4.2.3 trả 0 cho chỉ số lẻ → ở đây tự nội suy tuyến tính.
 *
 *   new Segments(opts)  (i) đoạn neo (l, giá) hai đầu — zOrder 'normal'
 *     opts: { reserved: [rect] | function() → [rect]   vùng (toạ độ pane, px) không đặt nhãn, vd dòng trạng thái HTML
 *             bottomGuard: px                          chừa đáy pane (vd dải iii) — nhãn không xuống đó
 *             priceExtent: function(lFrom, lTo) → {lo, hi} | null   khoảng giá nến đang hiện (cho autoscale 'near')
 *             hitTolerance: px (4) }
 *     item: { id,                                       trả qua hitTest → param.hoveredObjectId của crosshair
 *             l1, p1, l2, p2,                           hai đầu (chỉ số logic, giá)
 *             color, width (1.5), style 'solid'|'dashed'|'dotted', alpha (1),
 *             noLine: true                              chỉ nhãn / chấm (vd chữ cho một hộp, chấm đỉnh/đáy)
 *             dot: { r (2.5), color, alpha,             chấm tròn tại (l1, p1) — trúng chuột trong r + 3 px (thắng đường
 *                    ring: true, width (1.5) }          đi qua cùng điểm); ring = vòng tròn rỗng nét `width` thay chấm đặc
 *             autoscale: true | false | 'near', near: khoảng giá   'near' = chỉ giãn trục giá khi mức cách khoảng giá
 *                                                       nến đang hiện ≤ near (đối tượng xa không ép nến)
 *             label: { text, pos 'right'|'end'|'mid'|'left'|'start', side 'above'|'below' (end/mid),
 *                      at: l (mid: tâm nhãn; start: chỗ bắt đầu nhãn), gap: số nến chừa trước đầu cuối (end, mặc định 0.5),
 *                      — 'start' = trong đoạn, từ đầu trái phần đang hiện (hoặc `at`), ngang hàng đường, trượt dần sang
 *                        phải dọc đường khi bị chiếm (nhãn của dải / hộp, không tranh chỗ với nhãn ở mép phải)
 *                      size (11), weight (600), color (= màu đường), alpha (1), bg (nền mờ) | false,
 *                      priority (5 — nhỏ đặt trước, thắng chỗ), strict: true (không lệch xa khỏi chỗ neo — mid: chỉ
 *                      phía `side`, vd HH/LL; right/left: chỉ ngang hàng đường; không còn chỗ thì bỏ),
 *                      fallback: ký hiệu gọn (vd '✕', '▾') vẽ sát điểm neo khi không còn chỗ cho chữ — để đường không
 *                      bị trơn không tên (ghi ở `stats.symbols`; bỏ hẳn ghi ở `stats.dropped`),
 *                      edgeText: chữ khi đường nằm ngoài pane theo chiều dọc → nhãn kẹp mép trên/dưới, tự thêm ↑ / ↓ } }
 *     Nhãn không đè nhau: đặt theo `priority` (nhỏ trước — nhãn quan trọng chiếm chỗ trước, nhãn sau phải tránh), thử
 *     lần lượt các chỗ (đầu phải / sát đầu cuối / giữa, trên/dưới, mỗi chỗ nhích ±3 px rồi lệch dần); không còn chỗ thì
 *     thử ký hiệu `fallback`, rồi mới bỏ. `stats.placed` = khung nhãn / ký hiệu đã vẽ (kiểm thử).
 *   new Boxes(opts)     (ii) hộp giá × thời gian — zOrder 'bottom' (dưới nến)
 *     item: { id, l1, l2, p1, p2, fill, border, borderStyle 'solid'|'dashed'|'dotted', borderWidth (1), alpha (1),
 *             minH (2 px): hộp mỏng hơn thì nới ra — grow 'up'|'down'|(giữa); autoscale / near như (i);
 *             label: { text, pos 'right'|'inside', color, size } — chữ đơn giản, không tránh nhãn khác
 *             (cần tránh thì dùng một item noLine của Segments) }
 *   new Band(opts)      (iii) dải theo từng nến ở đáy pane — zOrder 'normal'
 *     opts: { height (14), bottom (3), caption: chữ sau nến cuối, minTextX (44 — chừa logo TradingView) }
 *     setBars([{ l, key, color, text, textColor, id }]): nến liên tiếp cùng `key` gộp thành một đoạn; `text` / `id`
 *     lấy ở nến đầu đoạn; chữ chỉ vẽ khi đoạn đủ rộng.
 *   reservedRects(container)  khung các phần tử phủ có `data-chart-reserve` (cùng khối cha với `container`), theo
 *                             toạ độ pane — dùng làm `reserved` của Segments.
 *
 * Cả ba: setItems / setBars → vẽ lại; hitTest(x, y) → { externalId: id, zOrder } khi chuột trúng đối tượng có `id`
 * (crosshair của chart nhận `hoveredObjectId` = id; MarketChart chuyển cho hook `tooltipObject` của plugin).
 * Mặc định đối tượng góp vào trục giá (autoscale khác false). Chỉ phần nằm trong khung nhìn (± 160 px cho nhãn) được
 * tính toạ độ và vẽ → mảng hàng chục nghìn đối tượng (chế độ lịch sử nhiều năm) vẫn nhẹ; `stats.ms` = thời gian vẽ
 * khung hình gần nhất.
 */
(function (MSL) {
  'use strict';

  var FONT = '-apple-system, "Segoe UI", Roboto, Arial, sans-serif';
  var LABEL_BG = 'rgba(15,20,25,0.82)';

  function dashOf(style, w) {
    if (style === 'dashed') return [6, 4];
    if (style === 'dotted') return [Math.max(1.6, w), 3.4];
    return [];
  }

  /** Hàm x(l) cho khung hình hiện tại: tuyến tính theo hai chỉ số nguyên (4.2.3 không nhận chỉ số lẻ). */
  function xMapper(chart) {
    var ts = chart.timeScale();
    var a = ts.logicalToCoordinate(0), b = ts.logicalToCoordinate(1);
    if (a === null || b === null) return null;
    var sp = b - a;
    var f = function (l) { return a + l * sp; };
    f.spacing = sp;
    return f;
  }

  function finite(v) { return typeof v === 'number' && isFinite(v); }

  function hit(r, x, y) { return x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h; }
  function now() { var pf = window.performance; return pf && pf.now ? pf.now() : Date.now(); }
  var CULL = 160;   // px ngoài khung nhìn vẫn tính (đủ cho nhãn đầu phải / sát đầu cuối)

  /** Khoảng cách điểm → đoạn thẳng (px). */
  function distSeg(x, y, g) {
    var dx = g.x2 - g.x1, dy = g.y2 - g.y1, L2 = dx * dx + dy * dy;
    var t = L2 ? Math.max(0, Math.min(1, ((x - g.x1) * dx + (y - g.y1) * dy) / L2)) : 0;
    var px = g.x1 + t * dx - x, py = g.y1 + t * dy - y;
    return Math.sqrt(px * px + py * py);
  }

  /** Item có góp vào trục giá trong khoảng logic [a, b] không. */
  function inScale(it, a, b, ext, lo, hi) {
    if (it.autoscale === false) return false;
    if (Math.max(it.l1, it.l2) < a || Math.min(it.l1, it.l2) > b) return false;
    if (it.autoscale === 'near' && ext && finite(it.near)) {
      return Math.max(lo, hi) >= ext.lo - it.near && Math.min(lo, hi) <= ext.hi + it.near;
    }
    return true;
  }

  function autoscale(items, a, b, extentFn) {
    var lo = Infinity, hi = -Infinity, ext = null, asked = false;
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (it.noLine && it.autoscale !== true) continue;
      if (it.autoscale === 'near' && !asked) { ext = extentFn ? extentFn(a, b) : null; asked = true; }
      if (!inScale(it, a, b, ext, it.p1, it.p2)) continue;
      lo = Math.min(lo, it.p1, it.p2); hi = Math.max(hi, it.p1, it.p2);
    }
    return isFinite(lo) ? { priceRange: { minValue: lo, maxValue: hi } } : null;
  }

  /** Bộ khung chung cho cả ba primitive (attached / paneViews / requestUpdate). */
  function base(self, zOrder) {
    self._view = {
      zOrder: function () { return zOrder; },
      renderer: function () { return { draw: function (t) { self._draw(t); } }; }
    };
    self._zOrder = zOrder;
  }
  function attach(proto) {
    proto.attached = function (p) { this._chart = p.chart; this._series = p.series; this._req = p.requestUpdate; };
    proto.detached = function () { this._chart = null; this._series = null; this._req = null; };
    proto.updateAllViews = function () {};
    proto.paneViews = function () { return [this._view]; };
    proto._update = function () { if (this._req) this._req(); };
  }

  // ------------------------------------------------------------------ bố trí nhãn
  function Layout(w, h, reserved) {
    this.w = w; this.h = h; this.rects = (reserved || []).slice();
  }
  Layout.prototype.free = function (r) {
    if (r.x < 1 || r.y < 1 || r.x + r.w > this.w - 1 || r.y + r.h > this.h - 1) return false;
    for (var i = 0; i < this.rects.length; i++) {
      var q = this.rects[i];
      if (r.x < q.x + q.w && q.x < r.x + r.w && r.y < q.y + q.h && q.y < r.y + r.h) return false;
    }
    return true;
  };
  Layout.prototype.place = function (cands) {
    for (var i = 0; i < cands.length; i++) {
      if (this.free(cands[i])) { this.rects.push(cands[i]); return cands[i]; }
    }
    return null;
  };

  // ------------------------------------------------------------------ (i) đoạn thẳng + nhãn
  function Segments(opts) {
    this._opts = opts || {};
    this._items = [];
    this._geo = [];
    this._placed = [];
    this.stats = { lines: 0, labels: 0, dropped: [], placed: [] };
    base(this, 'normal');
  }
  attach(Segments.prototype);
  Segments.prototype.setItems = function (items) { this._items = items || []; this._update(); };
  Segments.prototype.items = function () { return this._items.slice(); };
  Segments.prototype.autoscaleInfo = function (a, b) { return autoscale(this._items, a, b, this._opts.priceExtent); };
  Segments.prototype.hitTest = function (x, y) {
    var i;
    for (i = this._placed.length - 1; i >= 0; i--) {
      if (this._placed[i].id && hit(this._placed[i], x, y)) return { externalId: this._placed[i].id, zOrder: 'normal' };
    }
    var tol = this._opts.hitTolerance || 4, best = null, bd = Infinity;
    for (i = 0; i < this._geo.length; i++) {
      var g = this._geo[i];
      if (!g || !g.id) continue;
      var d;
      if (g.dot) {   // chấm thắng đường đi qua cùng chỗ (vd đường vùng bắt đầu đúng tại chấm ITH)
        d = Math.sqrt((x - g.x1) * (x - g.x1) + (y - g.y1) * (y - g.y1));
        if (d <= g.dot + 3 && d - 3 < bd) { bd = d - 3; best = g.id; }
      }
      if (g.noLine) continue;
      d = distSeg(x, y, g);
      if (d <= tol && d < bd) { bd = d; best = g.id; }
    }
    return best === null ? null : { externalId: best, zOrder: 'normal' };
  };

  Segments.prototype._reserved = function () {
    var r = this._opts.reserved;
    try { return (typeof r === 'function' ? r() : r) || []; } catch (e) { return []; }
  };

  Segments.prototype._draw = function (target) {
    var chart = this._chart, series = this._series, items = this._items, self = this;
    if (!chart || !series) return;
    var X = xMapper(chart);
    if (!X) return;
    var reserved = this._reserved();
    var t0 = now();
    target.useMediaCoordinateSpace(function (scope) {
      var ctx = scope.context, W = scope.mediaSize.width, H = scope.mediaSize.height;
      var Hl = H - (self._opts.bottomGuard || 0);
      var stats = { lines: 0, labels: 0, dots: 0, dropped: [], symbols: [], placed: [], items: items.length };
      var geo = [], placed = [];
      // 1) đường (chỉ phần trong khung nhìn ± CULL px)
      items.forEach(function (it) {
        if (!finite(it.l1) || !finite(it.l2)) { geo.push(null); return; }
        var x1 = X(it.l1), x2 = X(it.l2);
        if (Math.max(x1, x2) < -CULL || Math.min(x1, x2) > W + CULL) { geo.push(null); return; }
        var y1 = series.priceToCoordinate(it.p1), y2 = series.priceToCoordinate(it.p2);
        if (y1 === null || y2 === null) { geo.push(null); return; }
        var g = { id: it.id, noLine: !!it.noLine, x1: x1, x2: x2, y1: y1, y2: y2, dot: it.dot ? (it.dot.r || 2.5) : 0 };
        geo.push(g);
        if (it.dot && x1 >= -5 && x1 <= W + 5) {
          ctx.save();
          ctx.globalAlpha = it.dot.alpha == null ? 1 : it.dot.alpha;
          ctx.beginPath();
          ctx.arc(x1, y1, g.dot, 0, Math.PI * 2);
          if (it.dot.ring) {   // vòng tròn rỗng (vd đỉnh/đáy khung lớn — khác chấm đặc của khung chạy)
            ctx.strokeStyle = it.dot.color || it.color;
            ctx.lineWidth = it.dot.width || 1.5;
            ctx.stroke();
          } else {
            ctx.fillStyle = it.dot.color || it.color;
            ctx.fill();
          }
          ctx.restore();
          stats.dots++;
        }
        if (it.noLine || Math.max(g.x1, g.x2) < 0 || Math.min(g.x1, g.x2) > W) return;
        ctx.save();
        ctx.strokeStyle = it.color;
        ctx.globalAlpha = it.alpha == null ? 1 : it.alpha;
        ctx.lineWidth = it.width || 1.5;
        ctx.setLineDash(dashOf(it.style, ctx.lineWidth));
        ctx.lineCap = it.style === 'dotted' ? 'round' : 'butt';
        ctx.beginPath();
        ctx.moveTo(g.x1, g.y1);
        ctx.lineTo(g.x2, g.y2);
        ctx.stroke();
        ctx.restore();
        stats.lines++;
      });
      // 2) nhãn theo ưu tiên
      var lay = new Layout(W, Hl, reserved);
      var order = [];
      items.forEach(function (it, i) { if (it.label && it.label.text && geo[i]) order.push(i); });
      order.sort(function (a, b) {
        return ((items[a].label.priority || 5) - (items[b].label.priority || 5)) || a - b;
      });
      order.forEach(function (i) {
        var it = items[i], L = it.label, g = geo[i];
        var size = L.size || 11, padX = 4, h = size + 5;
        ctx.font = (L.weight || 600) + ' ' + size + 'px ' + FONT;
        var text = L.text;
        var w = Math.ceil(ctx.measureText(text).width) + padX * 2;
        var xs = Math.min(g.x1, g.x2), xe = Math.max(g.x1, g.x2);
        var yR = g.x2 >= g.x1 ? g.y2 : g.y1, yL = g.x2 >= g.x1 ? g.y1 : g.y2;
        var cands = [], k;
        var pos = L.pos || 'right';
        if (pos === 'right' || pos === 'end' || pos === 'left') {
          // đường nằm ngoài pane theo chiều dọc → nhãn mép (chỉ khi có edgeText)
          var yy = pos === 'left' ? yL : yR;
          if (yy < 0 || yy > Hl) {
            if (!L.edgeText || xe < 0 || xs > W) return;
            var up = yy < 0;
            text = L.edgeText + (up ? ' ↑' : ' ↓');
            w = Math.ceil(ctx.measureText(text).width) + padX * 2;
            var ex = Math.max(2, Math.min(xe + 4, W - 2 - w));
            var ey = up ? 2 : Hl - h - 2;
            for (k = 0; k < 7; k++) cands.push({ x: ex, y: ey + (up ? 1 : -1) * k * (h + 1), w: w, h: h });
            for (k = 0; k < 4; k++) cands.push({ x: ex - (k + 1) * (w + 4), y: ey, w: w, h: h });
          } else if (pos === 'right' || pos === 'left') {
            if (xe < -w || xs > W + w) return;
            var yc = yy - h / 2;
            var xr = pos === 'right' ? Math.min(xe + 4, W - 2 - w) : xs - 4 - w;
            var xin = pos === 'right' ? Math.min(xe, W) - w - 6 : Math.max(xs, 0) + 6;
            cands.push({ x: xr, y: yc, w: w, h: h });
            cands.push({ x: xin, y: yc, w: w, h: h });
            if (!L.strict) [-1, 1, -2, 2].forEach(function (s) { cands.push({ x: xr, y: yc + s * (h + 1), w: w, h: h }); });
          } else {   // end: sát đầu cuối, trên/dưới đường
            var gap = (L.gap == null ? 0.5 : L.gap) * Math.abs(X.spacing);
            var xa = xe - gap - 2 - w;
            if (xa > W || xe + gap + 4 + w < 0) return;
            var above = yR - 3 - h, below = yR + 3;
            var first = L.side === 'below' ? below : above, second = L.side === 'below' ? above : below;
            cands.push({ x: xa, y: first, w: w, h: h });
            cands.push({ x: xa, y: second, w: w, h: h });
            cands.push({ x: xe + gap + 4, y: yR - h / 2, w: w, h: h });
            for (k = 1; k <= 3; k++) {
              cands.push({ x: xa - k * (w * 0.6), y: first, w: w, h: h });
              cands.push({ x: xa - k * (w * 0.6), y: second, w: w, h: h });
            }
            var sg = L.side === 'below' ? 1 : -1;
            cands.push({ x: xa, y: first + sg * (h + 1), w: w, h: h });
            cands.push({ x: xa, y: second - sg * (h + 1), w: w, h: h });
          }
        } else if (pos === 'start') {   // trong đoạn, từ đầu trái phần đang hiện, trượt sang phải dọc đường
          var sx = Math.max(L.at != null ? Math.max(X(L.at), xs) : xs, 2);
          var sEnd = Math.min(xe, W - 2);
          if (sx > sEnd || xe < 0) return;
          var sy = (g.y1 + g.y2) / 2 - h / 2;
          for (k = 0; k < 40; k++) {   // trượt dọc phần đang hiện của đoạn
            var cx = sx + 2 + k * (w * 0.5 + 4);
            if (k > 0 && cx + w > sEnd) break;
            cands.push({ x: cx, y: sy, w: w, h: h });
          }
          cands.push({ x: sEnd + 4, y: sy, w: w, h: h });       // ngay sau đầu phải đoạn
          cands.push({ x: sx - w - 4, y: sy, w: w, h: h });     // ngay trước chỗ bắt đầu
          if (!L.strict) [-1, 1].forEach(function (sg2) { cands.push({ x: sx + 2, y: sy + sg2 * (h + 1), w: w, h: h }); });
        } else {   // mid: giữa phần đoạn đang hiện
          var vis1 = Math.max(xs, 0), vis2 = Math.min(xe, W);
          if (vis2 < vis1 && L.at == null) return;
          var xm = L.at != null ? X(L.at) : (vis1 + vis2) / 2;
          var ym = (g.y1 + g.y2) / 2;
          var ab = ym - 3 - h, bl = ym + 3;
          var f1 = L.side === 'below' ? bl : ab, f2 = L.side === 'below' ? ab : bl;
          var s1 = L.side === 'below' ? 1 : -1;
          var ys = L.strict ? [f1, f1 + s1 * (h + 1)] : [f1, f2, f1 + s1 * (h + 1), f2 - s1 * (h + 1)];
          var xsList = [xm - w / 2, xm - w / 2 - w * 0.6, xm - w / 2 + w * 0.6];
          ys.forEach(function (y0) { xsList.forEach(function (x0) { cands.push({ x: x0, y: y0, w: w, h: h }); }); });
        }
        var all = [];   // mỗi chỗ thử thêm nhích ±3 px (vd chạm mép khung dành riêng) trước khi sang chỗ khác
        cands.forEach(function (q) {
          all.push(q, { x: q.x, y: q.y + 3, w: q.w, h: q.h }, { x: q.x, y: q.y - 3, w: q.w, h: q.h });
        });
        var r = lay.place(all);
        if (!r && L.fallback && !(yR < 0 || yR > Hl) && !(yL < 0 || yL > Hl)) {
          // Không còn chỗ cho chữ → ký hiệu gọn sát điểm neo (giữa / đầu cuối / đầu trái), cùng luật không đè nhau.
          var fs = (L.size || 11) + 1, fw = 0, fh = fs + 3;
          ctx.font = '700 ' + fs + 'px ' + FONT;
          fw = Math.ceil(ctx.measureText(L.fallback).width) + 4;
          var ax, ay;
          if (pos === 'mid') {
            ax = L.at != null ? X(L.at) : (Math.max(xs, 0) + Math.min(xe, W)) / 2;
            ay = (g.y1 + g.y2) / 2;
          } else if (pos === 'left') { ax = Math.max(xs, 6); ay = yL; } else { ax = Math.min(xe, W - 6); ay = yR; }
          if (ax >= 0 && ax <= W) {
            var upF = L.side !== 'below', fc = [];
            var fy1 = upF ? ay - fh - 1 : ay + 1, fy2 = upF ? ay + 1 : ay - fh - 1;
            [0, -fw * 0.6, fw * 0.6, -fw * 1.2, fw * 1.2].forEach(function (dx) {
              fc.push({ x: ax - fw / 2 + dx, y: fy1, w: fw, h: fh }, { x: ax - fw / 2 + dx, y: fy2, w: fw, h: fh });
            });
            r = lay.place(fc);
            if (r) {
              ctx.save();
              ctx.fillStyle = LABEL_BG;
              ctx.fillRect(r.x, r.y, r.w, r.h);
              ctx.globalAlpha = L.alpha == null ? 1 : L.alpha;
              ctx.fillStyle = L.color || it.color;
              ctx.textBaseline = 'middle';
              ctx.fillText(L.fallback, r.x + 2, r.y + r.h / 2 + 0.5);
              ctx.restore();
              stats.symbols.push(L.text + '→' + L.fallback + (it.id ? '@' + it.id : ''));
              stats.placed.push({ id: it.id || null, text: L.fallback, symbol: true, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h) });
              placed.push({ id: it.id || null, x: r.x, y: r.y, w: r.w, h: r.h });
              return;
            }
          }
        }
        if (!r) { stats.dropped.push(text + (it.id ? '@' + it.id : '')); return; }
        ctx.save();
        if (L.bg !== false) {
          ctx.fillStyle = L.bg || LABEL_BG;
          ctx.beginPath();
          if (ctx.roundRect) ctx.roundRect(r.x, r.y, r.w, r.h, 3); else ctx.rect(r.x, r.y, r.w, r.h);
          ctx.fill();
        }
        ctx.globalAlpha = L.alpha == null ? 1 : L.alpha;
        ctx.fillStyle = L.color || it.color;
        ctx.textBaseline = 'middle';
        ctx.fillText(text, r.x + padX, r.y + r.h / 2 + 0.5);
        ctx.restore();
        stats.labels++;
        var rec = { id: it.id || null, text: text, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h) };
        stats.placed.push(rec);
        placed.push({ id: it.id || null, x: r.x, y: r.y, w: r.w, h: r.h });
      });
      self._geo = geo;
      self._placed = placed;
      stats.ms = Math.round((now() - t0) * 100) / 100;
      self.stats = stats;
    });
  };

  // ------------------------------------------------------------------ (ii) hộp giá × thời gian
  function Boxes(opts) {
    this._opts = opts || {};
    this._items = [];
    this._rects = [];
    this.stats = { boxes: 0 };
    base(this, 'bottom');
  }
  attach(Boxes.prototype);
  Boxes.prototype.setItems = function (items) { this._items = items || []; this._update(); };
  Boxes.prototype.items = function () { return this._items.slice(); };
  Boxes.prototype.autoscaleInfo = function (a, b) { return autoscale(this._items, a, b, this._opts.priceExtent); };
  Boxes.prototype.hitTest = function (x, y) {
    for (var i = this._rects.length - 1; i >= 0; i--) {
      var r = this._rects[i];
      if (r.id && hit({ x: r.x - 1, y: r.y - 1, w: r.w + 2, h: r.h + 2 }, x, y)) return { externalId: r.id, zOrder: 'bottom' };
    }
    return null;
  };
  Boxes.prototype._draw = function (target) {
    var chart = this._chart, series = this._series, items = this._items, self = this;
    if (!chart || !series) return;
    var X = xMapper(chart);
    if (!X) return;
    var t0 = now();
    target.useMediaCoordinateSpace(function (scope) {
      var ctx = scope.context, W = scope.mediaSize.width, n = 0, rects = [];
      items.forEach(function (it) {
        if (!finite(it.l1) || !finite(it.l2)) return;
        var x1 = X(it.l1), x2 = X(it.l2);
        if (Math.max(x1, x2) < 0 || Math.min(x1, x2) > W) return;
        var y1 = series.priceToCoordinate(it.p1), y2 = series.priceToCoordinate(it.p2);
        if (y1 === null || y2 === null) return;
        var x = Math.min(x1, x2), y = Math.min(y1, y2), w = Math.max(2, Math.abs(x2 - x1)), h = Math.abs(y2 - y1);
        var mh = it.minH || 2;
        if (h < mh) {   // hộp quá mỏng: nới ra cho thấy được
          if (it.grow === 'up') y = Math.max(y1, y2) - mh;
          else if (it.grow !== 'down') y -= (mh - h) / 2;
          h = mh;
        }
        ctx.save();
        if (it.alpha != null) ctx.globalAlpha = it.alpha;
        if (it.fill) { ctx.fillStyle = it.fill; ctx.fillRect(x, y, w, h); }
        if (it.border) {
          ctx.strokeStyle = it.border;
          ctx.lineWidth = it.borderWidth || 1;
          ctx.setLineDash(dashOf(it.borderStyle, ctx.lineWidth));
          ctx.strokeRect(x + 0.5, y + 0.5, Math.max(1, w - 1), Math.max(1, h - 1));
        }
        if (it.label && it.label.text) {
          var size = it.label.size || 11;
          ctx.setLineDash([]);
          ctx.font = '600 ' + size + 'px ' + FONT;
          ctx.textBaseline = 'middle';
          ctx.fillStyle = it.label.color || it.border || '#cfd8dc';
          var tx = it.label.pos === 'inside' ? x + 3 : x + w + 3;
          ctx.fillText(it.label.text, tx, y + h / 2 + 0.5);
        }
        ctx.restore();
        rects.push({ id: it.id || null, x: x, y: y, w: w, h: h });
        n++;
      });
      self._rects = rects;
      self.stats = { boxes: n, items: items.length, ms: Math.round((now() - t0) * 100) / 100 };
    });
  };

  // ------------------------------------------------------------------ (iii) dải theo nến ở đáy pane
  function Band(opts) {
    var o = opts || {};
    this._opts = {
      height: o.height || 14, bottom: o.bottom == null ? 3 : o.bottom,
      minTextX: o.minTextX == null ? 44 : o.minTextX, caption: o.caption || '', font: o.font || 11
    };
    this._segs = [];
    this._hits = [];
    this.stats = { segments: 0, texts: 0 };
    base(this, 'normal');
  }
  attach(Band.prototype);
  /** bars: [{l, key, color, text, textColor, id}] theo thứ tự l tăng. */
  Band.prototype.setBars = function (bars) {
    var segs = [], cur = null;
    (bars || []).forEach(function (b) {
      if (!finite(b.l)) return;
      if (!cur || cur.key !== b.key || b.l !== cur.lb + 1) {
        cur = { key: b.key, la: b.l, lb: b.l, color: b.color, text: b.text, textColor: b.textColor, id: b.id || null };
        segs.push(cur);
      } else {
        cur.lb = b.l;
      }
    });
    this._segs = segs;
    this._update();
  };
  Band.prototype.segments = function () { return this._segs.slice(); };
  Band.prototype.height = function () { return this._segs.length ? this._opts.height + this._opts.bottom : 0; };
  Band.prototype.hitTest = function (x, y) {
    for (var i = 0; i < this._hits.length; i++) {
      var r = this._hits[i];
      if (r.id && hit(r, x, y)) return { externalId: r.id, zOrder: 'normal' };
    }
    return null;
  };
  Band.prototype._draw = function (target) {
    var chart = this._chart, segs = this._segs, o = this._opts, self = this;
    if (!chart) return;
    if (!segs.length) { this._hits = []; return; }
    var X = xMapper(chart);
    if (!X) return;
    var t0 = now();
    target.useMediaCoordinateSpace(function (scope) {
      var ctx = scope.context, W = scope.mediaSize.width, H = scope.mediaSize.height;
      var y = H - o.bottom - o.height, sp = Math.abs(X.spacing) || 6;
      var nSeg = 0, nText = 0, lastX = null, hits = [];
      ctx.save();
      ctx.font = '600 ' + o.font + 'px ' + FONT;
      ctx.textBaseline = 'middle';
      segs.forEach(function (s) {
        var xa = X(s.la) - sp / 2, xb = X(s.lb) + sp / 2;
        lastX = xb;
        if (xb < 0 || xa > W) return;
        var ca = Math.max(xa, 0), cb = Math.min(xb, W);
        ctx.fillStyle = s.color;
        ctx.fillRect(ca, y, cb - ca, o.height);
        hits.push({ id: s.id, x: ca, y: y, w: cb - ca, h: o.height });
        nSeg++;
        if (xa > 0) {   // vạch ngăn mảnh giữa hai đoạn
          ctx.fillStyle = 'rgba(15,20,25,0.9)';
          ctx.fillRect(xa - 0.5, y, 1, o.height);
        }
        if (s.text) {
          var tx = Math.max(ca, o.minTextX) + 4, tw = ctx.measureText(s.text).width;
          if (cb - tx - 3 >= tw) {
            ctx.fillStyle = s.textColor || '#ffffff';
            ctx.fillText(s.text, tx, y + o.height / 2 + 0.5);
            nText++;
          }
        }
      });
      if (o.caption && lastX !== null) {
        var cw = ctx.measureText(o.caption).width;
        if (lastX + 6 + cw < W - 2 && lastX + 6 > 0) {
          ctx.fillStyle = '#9aa7b4';
          ctx.fillText(o.caption, lastX + 6, y + o.height / 2 + 0.5);
        }
      }
      ctx.restore();
      self._hits = hits;
      self.stats = { segments: nSeg, texts: nText, total: segs.length, ms: Math.round((now() - t0) * 100) / 100 };
    });
  };

  /** Khung (toạ độ pane của `container`) các phần tử phủ đang hiện có `data-chart-reserve`, cùng khối cha. */
  function reservedRects(container, pad) {
    var p = pad == null ? 3 : pad;
    var root = container && container.parentNode;
    if (!root || !root.querySelectorAll) return [];
    var c = container.getBoundingClientRect(), out = [];
    Array.prototype.forEach.call(root.querySelectorAll('[data-chart-reserve]'), function (el) {
      for (var x = el; x && x !== root; x = x.parentElement) if (x.hidden) return;
      var r = el.getBoundingClientRect();
      if (!r.width || !r.height) return;
      out.push({ x: r.left - c.left - p, y: r.top - c.top - p, w: r.width + 2 * p, h: r.height + 2 * p });
    });
    return out;
  }

  MSL.primitives = { Segments: Segments, Boxes: Boxes, Band: Band, reservedRects: reservedRects };
})(window.MSL);
