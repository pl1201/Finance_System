/* Plugin hiển thị indicator_baseline / hmm_online: marker BASELINE_UP/DOWN/… và HMM_STATE_CHANGE.
 * Đường SMA dùng chung đường mức của plugin swing (timeline có `sma`, không có muc_high/low).
 */
(function (MSL) {
  'use strict';

  var COLORS = { up: '#66bb6a', down: '#ef5350', other: '#b0bec5' };

  MSL.algos.register({
    id: 'baseline',
    algorithms: ['indicator_baseline', 'hmm_online'],
    chart: {
      ownsEvent: function (t) { return t.indexOf('BASELINE_') === 0 || t === 'HMM_STATE_CHANGE'; },

      /** Cùng lớp «Sự kiện BOS» với swing — bật/tắt chung một ô. */
      marker: function (e, ctx) {
        if (!ctx.layers.bos) return;
        var t = e.structure_type;
        var upB = t === 'BASELINE_UP';
        var downB = t === 'BASELINE_DOWN';
        ctx.markers.push({
          time: ctx.timeByIndex[e.confirmed_bar_index],
          position: downB ? 'aboveBar' : 'belowBar',
          color: upB ? COLORS.up : (downB ? COLORS.down : COLORS.other),
          shape: upB ? 'arrowUp' : (downB ? 'arrowDown' : 'circle'),
          text: t.replace('BASELINE_', 'BL ').replace('HMM_STATE_CHANGE', 'HMM'),
          size: 1
        });
      }
    }
  });
})(window.MSL);
