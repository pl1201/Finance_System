/* Khung thời gian: thứ tự, độ dài, tìm dataset cùng symbol ở khung khác. */
(function (MSL) {
  'use strict';

  var ORDER = ['M5', 'M15', 'M30', 'H1', 'H4'];
  var SEC = { M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400 };

  /**
   * Dataset cùng symbol ở khung `tf`. Có `current` thì ưu tiên cùng loại (mô phỏng / thật)
   * với dataset đang mở. Không tách hay tổng hợp nến — chỉ tìm dataset có sẵn.
   */
  function findSibling(datasets, symbol, tf, current) {
    var cands = datasets.filter(function (d) {
      return d.symbol === symbol && d.timeframe === tf;
    });
    if (!cands.length) return null;
    if (current) {
      var sameFlag = cands.filter(function (d) { return !!d.is_synthetic === !!current.is_synthetic; });
      if (sameFlag.length) cands = sameFlag;
    }
    return cands[0];
  }

  MSL.tf = { ORDER: ORDER, SEC: SEC, findSibling: findSibling };
})(window.MSL);
