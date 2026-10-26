/* Khung thời gian: thứ tự, độ dài, tìm dataset cùng symbol ở khung khác. */
(function (MSL) {
  'use strict';

  // Cùng danh sách với core.types.TIMEFRAME_SECONDS — khung nào lõi đọc được thì thanh đổi khung có nút.
  var ORDER = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];
  var SEC = { M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400, D1: 86400 };
  // Khung lab được tự tổng hợp tới (mốc utc_epoch). D1 không có: nến ngày của dữ liệu thật mở lúc
  // 17:00 New York (plan_ict_structure D10) — chỉ chuyển sang dataset D1 đã nhập.
  var RESAMPLE = ['M5', 'M15', 'M30', 'H1', 'H4'];

  /** Số ms hai khoảng [a, b] và [start_time, end_time] của dataset trùng nhau (0 nếu không trùng/không rõ). */
  function overlapMs(d, a, b) {
    var s = Date.parse(d.start_time), e = Date.parse(d.end_time);
    if (!isFinite(s) || !isFinite(e)) return 0;
    return Math.max(0, Math.min(e, b) - Math.max(s, a));
  }

  /**
   * Trong `cands`, dataset trùng nhiều nhất với khoảng `focus` ({start, end} ISO). Không có
   * `focus` thì dùng khoảng của `current`. Hoà (vd bản lệch giờ và bản đã sửa cùng năm) → giữ
   * thứ tự sẵn có: API trả dataset tạo gần nhất trước.
   */
  function pickByTime(cands, current, focus) {
    if (cands.length < 2) return cands[0] || null;
    var a = NaN, b = NaN;
    if (focus && focus.start && focus.end) {
      a = Date.parse(focus.start);
      b = Date.parse(focus.end);
    } else if (current) {
      a = Date.parse(current.start_time);
      b = Date.parse(current.end_time);
    }
    if (!isFinite(a) || !isFinite(b) || b < a) return cands[0];
    b = Math.max(b, a + 1);                          // khoảng một điểm vẫn chọn được dataset chứa nó
    var best = cands[0], bestOv = overlapMs(best, a, b);
    for (var i = 1; i < cands.length; i++) {
      var ov = overlapMs(cands[i], a, b);
      if (ov > bestOv) { best = cands[i]; bestOv = ov; }
    }
    return best;
  }

  /**
   * Dataset cùng symbol ở khung `tf`. Ưu tiên cùng loại (mô phỏng / thật) với dataset đang mở,
   * rồi dataset trùng nhiều nhất với khoảng đang xem (`focus`, hoặc khoảng của `current`) — dữ
   * liệu chia theo năm / theo đoạn thì nhảy đúng năm. Không tách hay tổng hợp nến.
   */
  function findSibling(datasets, symbol, tf, current, focus) {
    var cands = datasets.filter(function (d) {
      return d.symbol === symbol && d.timeframe === tf;
    });
    if (!cands.length) return null;
    if (current) {
      var sameFlag = cands.filter(function (d) { return !!d.is_synthetic === !!current.is_synthetic; });
      if (sameFlag.length) cands = sameFlag;
    }
    return pickByTime(cands, current, focus);
  }

  MSL.tf = { ORDER: ORDER, SEC: SEC, RESAMPLE: RESAMPLE, findSibling: findSibling, pickByTime: pickByTime };
})(window.MSL);
