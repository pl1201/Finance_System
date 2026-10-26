/* Chart — tiện ích dựng dữ liệu series cho Lightweight Charts 4.2 (MSL.series).
 *
 * Dùng chung cho lõi chart và các plugin algos/. Không biết thuật toán nào.
 */
(function (MSL) {
  'use strict';

  var LWC = window.LightweightCharts;
  var isFiniteNum = MSL.format.isFiniteNum;

  var TRANSPARENT = 'rgba(0,0,0,0)';

  function setLineData(series, points, extraOpts) {
    var clean = [];
    for (var i = 0; i < (points || []).length; i++) {
      var p = points[i];
      if (p && p.time != null && isFiniteNum(p.value)) {
        clean.push({ time: p.time, value: p.value });
      }
    }
    var opts = { visible: clean.length > 0 };
    if (extraOpts) {
      var k;
      for (k in extraOpts) {
        if (Object.prototype.hasOwnProperty.call(extraOpts, k)) opts[k] = extraOpts[k];
      }
    }
    series.applyOptions(opts);
    series.setData(clean);
  }

  /**
   * Chuỗi mức có ngắt cho đường bậc thang. LWC 4.2 vẽ nối qua điểm khoảng trắng,
   * nên ngắt bằng điểm màu trong suốt: đoạn ngang lấy màu điểm đầu, đoạn dọc lấy
   * màu điểm cuối. Điểm tại nến xác lập mức (hoặc đổi ``idKey``) trong suốt →
   * đường chỉ hiện từ nến SAU lúc mức được biết, không nối sang mức/setup khác.
   */
  function levelSeriesData(timeline, key, cursor, idKey) {
    var out = [];
    var prevVal = null, prevId = null, lastVal = null;
    for (var j = 0; j < timeline.length; j++) {
      var p = timeline[j];
      if (p.bar_index > cursor) break;
      var v = p[key];
      var id = idKey ? p[idKey] : null;
      if (!isFiniteNum(v)) {
        if (lastVal !== null) out.push({ time: p.time, value: lastVal, color: TRANSPARENT });
        prevVal = null; prevId = null;
        continue;
      }
      if (prevVal === null || v !== prevVal || id !== prevId) {
        out.push({ time: p.time, value: v, color: TRANSPARENT });
      } else {
        out.push({ time: p.time, value: v });
      }
      prevVal = v; prevId = id; lastVal = v;
    }
    return out;
  }

  /**
   * Biên Range: chỉ có điểm khi Range đang hoạt động (không kéo mức cũ qua các nến
   * sau exit — tránh làm giãn autoscale). Điểm đầu mỗi Range trong suốt (đường
   * bắt đầu từ nến SAU lúc biết); điểm cuối mỗi Range trong suốt để không nối
   * sang Range kế tiếp.
   */
  function rangeSeriesData(timeline, key, idKey, cursor) {
    var out = [], prevId = null;
    for (var j = 0; j < timeline.length; j++) {
      var p = timeline[j];
      if (p.bar_index > cursor) break;
      var v = p[key], id = p[idKey];
      if (!isFiniteNum(v)) {
        if (prevId !== null && out.length) out[out.length - 1].color = TRANSPARENT;
        prevId = null;
        continue;
      }
      if (id !== prevId) {
        if (out.length) out[out.length - 1].color = TRANSPARENT;
        out.push({ time: p.time, value: v, color: TRANSPARENT });
      } else {
        out.push({ time: p.time, value: v });
      }
      prevId = id;
    }
    return out;
  }

  function setGapLineData(series, points) {
    var any = false;
    for (var i = 0; i < points.length; i++) if (!points[i].color) { any = true; break; }
    series.applyOptions({ visible: any });
    series.setData(any ? points : []);
  }

  /** Tuỳ chọn đường bậc thang (mức giá đang hoạt động) — không nhãn giá, không chấm crosshair. */
  function stepLineOpts(color, width, style) {
    return {
      color: color, lineWidth: width, lineStyle: style, lineType: LWC.LineType.WithSteps,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: ''
    };
  }

  /** Như stepLineOpts nhưng nối thẳng giữa các điểm. */
  function simpleLineOpts(color, width, style) {
    return {
      color: color, lineWidth: width, lineStyle: style, lineType: LWC.LineType.Simple,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: ''
    };
  }

  MSL.series = {
    TRANSPARENT: TRANSPARENT,
    setLineData: setLineData,
    levelSeriesData: levelSeriesData,
    rangeSeriesData: rangeSeriesData,
    setGapLineData: setGapLineData,
    stepLineOpts: stepLineOpts,
    simpleLineOpts: simpleLineOpts
  };
})(window.MSL);
