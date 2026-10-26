/* Khung phụ ngay dưới chart chính — hook `pane` của plugin (hợp đồng ở đầu algos/registry.js), dùng chung cho trang Thử
 * nghiệm (pages/lab/run.js) và trang Live MT5 (pages/live/view.js). Một SubPane (chart/sub-pane.js) tạo lần đầu cần (LWC cần
 * kích thước thật lúc tạo chart), cùng chuỗi nến, cuộn / zoom / crosshair theo chart chính. Plugin khác vẽ khung → gỡ series,
 * init lại. Chỉ lấy điểm (hook.points) khi nến / timeline đổi; tiến một nến (MarketChart.appendBar: cùng mảng nến, dài thêm 1
 * — setBars luôn nhận mảng mới) → ctx.from = nến mới, khung chỉ thêm nến đó. Không có hook / lớp tắt / has() = false → ẩn.
 *
 *   var host = new PaneHost({ wrap, pane, legend, chart, anchorRight });
 *   host.render(own, timeline, cursor, layers);   // own = plugin của kết quả đang xem (null = ẩn); nến = chart.bars
 */
(function (global) {
  'use strict';

  var esc = global.MSL.dom.esc;

  function PaneHost(els) {
    this.els = els;           // { wrap, pane, legend, chart, anchorRight }
    this.sp = null;           // SubPane, tạo lần đầu cần
    this.own = null;          // plugin đang vẽ khung
    this.last = null;         // { ctx, n } của lần vẽ trước
    this.hover = null;        // nến dưới chuột (null = nến con trỏ)
    this.html = null;         // dòng chú giải đang hiện
    this.anchorRight = !!els.anchorRight;
  }

  /** Nến cuối bám mép phải (replay / live), như chart chính. */
  PaneHost.prototype.setAnchorRight = function (on) {
    this.anchorRight = !!on;
    if (this.sp) this.sp.setAnchorRight(this.anchorRight);
  };

  /** `timeline` / `cursor` của kết quả đang xem (cursor = Infinity khi xem toàn lịch sử); nến lấy ở chart chính — appendBar
   * giữ mảng, setBars thay mảng mới, nhờ vậy biết lần này chỉ thêm một nến. */
  PaneHost.prototype.render = function (own, timeline, cursor, layers) {
    var hook = own && own.pane, self = this;
    var ctx = hook ? { timeline: timeline || [], bars: this.els.chart.bars, cursor: cursor, from: 0 } : null;
    if (!ctx || !layers[hook.layer] || (hook.has && !hook.has(ctx))) {
      if (this.own) { this.sp.setVisible(false); this.sp.reset(); this.own = null; this.last = null; this.hover = null; }
      return;
    }
    if (!this.sp) {
      this.els.wrap.hidden = false;
      this.sp = new global.SubPane(this.els.pane, { wrap: this.els.wrap });
      this.sp.linkWith(this.els.chart);
      this.sp.setAnchorRight(this.anchorRight);
      this.sp.onCrosshair(function (bar) { self.hover = bar; self.renderLegend(bar); });
    }
    if (this.own !== own) { this.sp.reset(); hook.init(this.sp); this.own = own; this.last = null; }
    var last = this.last, n = ctx.bars.length, same = last && last.ctx.bars === ctx.bars;
    if (!(same && last.n === n && last.ctx.timeline === ctx.timeline)) {
      if (same && last.n === n - 1) ctx.from = n - 1;
      this.sp.draw(hook.points(ctx), ctx.from > 0);
    }
    this.sp.setVisible(true);           // sau khi có dữ liệu: khoảng nhìn chép từ chart chính áp lên đúng chuỗi nến
    this.last = { ctx: ctx, n: n };
    this.renderLegend(this.hover);      // đang rê chuột thì giữ nến dưới chuột (nến mới, chọn sự kiện…)
  };

  /** Dòng chú giải (els.legend): tiêu đề hook + html plugin trả cho nến dưới chuột (null = nến con trỏ). */
  PaneHost.prototype.renderLegend = function (bar) {
    var hook = this.last ? this.own.pane : null;
    if (!hook) return;
    var html = '<b class="pane-title">' + esc(hook.title || '') + '</b>' + (hook.legend ? hook.legend(bar, this.last.ctx) || '' : '');
    if (html === this.html) return;
    this.html = html;
    this.els.legend.innerHTML = html;
  };

  global.PaneHost = PaneHost;
})(window);
