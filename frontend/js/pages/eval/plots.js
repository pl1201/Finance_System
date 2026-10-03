/* Trang Đánh giá — biểu đồ SVG: F1 theo độ trễ P90, phân phối độ trễ. */
(function (MSL) {
  'use strict';

  var E = MSL.evalPage;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var S = E.S;

  function axisNice(min, max) {
    if (min === max) { min -= 1; max += 1; }
    var pad = (max - min) * 0.08;
    return { min: min - pad, max: max + pad };
  }

  function renderScatter() {
    $('#chart-pair').hidden = false;
    var host = $('#scatter');
    var runs = E.selectedGroupRuns().filter(function (r) {
      return r.quality && r.quality.has_labels && r.quality.f1 != null && r.lag && r.lag.p90 != null;
    });
    if (!runs.length) {
      host.innerHTML = '<p class="hint" style="padding:24px">Cần nhãn tham chiếu trong khoảng chấm để vẽ F1. Không gán F1 = 0. Phân phối độ trễ vẫn xem được.</p>';
      return;
    }
    var xs = runs.map(function (r) { return r.lag.p90; });
    var ys = runs.map(function (r) { return r.quality.f1; });
    var xr = axisNice(Math.min.apply(null, xs), Math.max.apply(null, xs));
    var yr = axisNice(0, Math.max(1, Math.max.apply(null, ys)));
    var W = 480, H = 220, L = 42, R = 12, T = 12, B = 28;
    var iw = W - L - R, ih = H - T - B;
    function sx(v) { return L + (v - xr.min) / (xr.max - xr.min) * iw; }
    function sy(v) { return T + (1 - (v - yr.min) / (yr.max - yr.min)) * ih; }
    var pts = runs.map(function (r, i) {
      var sel = r.run_id === S.selectedRunId;
      var cls = 'scatter-pt' + (sel ? ' selected' : '') + (r.is_baseline ? ' baseline' : '');
      var shape;
      if (r.is_baseline) {
        shape = '<rect x="' + (sx(r.lag.p90) - 5) + '" y="' + (sy(r.quality.f1) - 5) +
          '" width="10" height="10" transform="rotate(45 ' + sx(r.lag.p90) + ' ' + sy(r.quality.f1) +
          ')" fill="#ffca6b" class="' + cls + '" data-id="' + esc(r.run_id) + '" tabindex="0" role="option"/>';
      } else {
        shape = '<circle cx="' + sx(r.lag.p90) + '" cy="' + sy(r.quality.f1) + '" r="' + (sel ? 6 : 4.5) +
          '" fill="' + (sel ? '#4c9aff' : '#9aa7b4') + '" class="' + cls + '" data-id="' +
          esc(r.run_id) + '" tabindex="0" role="option"/>';
      }
      return shape;
    }).join('');
    var tf = (runs[0] && runs[0].timeframe) || '';
    host.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img">' +
      '<text x="' + (L + iw / 2) + '" y="' + (H - 4) + '" fill="#6e7d8c" font-size="11" text-anchor="middle">Trễ P90 (nến' +
        (tf ? ' ' + tf : '') + ')</text>' +
      '<text x="12" y="' + (T + ih / 2) + '" fill="#6e7d8c" font-size="11" transform="rotate(-90 12 ' + (T + ih / 2) + ')" text-anchor="middle">F1</text>' +
      '<line x1="' + L + '" y1="' + (T + ih) + '" x2="' + (L + iw) + '" y2="' + (T + ih) + '" stroke="#2a3441"/>' +
      '<line x1="' + L + '" y1="' + T + '" x2="' + L + '" y2="' + (T + ih) + '" stroke="#2a3441"/>' +
      '<text x="' + L + '" y="' + (H - 14) + '" fill="#6e7d8c" font-size="10">' + E.fmtNum(xr.min, 1) + '</text>' +
      '<text x="' + (L + iw) + '" y="' + (H - 14) + '" fill="#6e7d8c" font-size="10" text-anchor="end">' + E.fmtNum(xr.max, 1) + '</text>' +
      '<text x="' + (L - 4) + '" y="' + (T + 8) + '" fill="#6e7d8c" font-size="10" text-anchor="end">' + E.fmtNum(yr.max, 2) + '</text>' +
      '<text x="' + (L - 4) + '" y="' + (T + ih) + '" fill="#6e7d8c" font-size="10" text-anchor="end">' + E.fmtNum(yr.min, 2) + '</text>' +
      pts + '</svg>';
  }

  function renderHist() {
    var host = $('#lag-hist');
    var runs = E.selectedGroupRuns();
    if (!runs.length) { host.innerHTML = ''; return; }
    var sel = E.selectedRun();
    var bins = (sel && sel.lag && sel.lag.histogram) || [];
    if (!bins.length) {
      host.innerHTML = '<p class="hint" style="padding:24px">Chưa có sự kiện để vẽ phân phối độ trễ.</p>';
      return;
    }
    var W = 480, H = 220, L = 36, R = 12, T = 10, B = 36;
    var iw = W - L - R, ih = H - T - B;
    var nBin = bins.length;
    var bw = iw / nBin;
    var others = runs.filter(function (r) { return r.run_id !== (sel && sel.run_id); });
    function countAt(run, i) {
      var h = run.lag && run.lag.histogram;
      return h && h[i] ? h[i].count : 0;
    }
    var maxC = 1;
    bins.forEach(function (b, i) {
      maxC = Math.max(maxC, b.count);
      others.forEach(function (r) { maxC = Math.max(maxC, countAt(r, i)); });
    });
    var bars = '';
    bins.forEach(function (b, i) {
      var x = L + i * bw;
      others.forEach(function (r) {
        var c = countAt(r, i);
        var h = c / maxC * ih;
        var dash = r.is_baseline ? ' stroke-dasharray="3 2"' : '';
        bars += '<rect x="' + (x + 2) + '" y="' + (T + ih - h) + '" width="' + Math.max(1, bw - 6) +
          '" height="' + h + '" fill="rgba(154,167,180,.22)" stroke="' +
          (r.is_baseline ? '#ffca6b' : 'transparent') + '"' + dash + '/>';
      });
      var h2 = b.count / maxC * ih;
      bars += '<rect x="' + (x + 4) + '" y="' + (T + ih - h2) + '" width="' + Math.max(1, bw - 10) +
        '" height="' + h2 + '" fill="#4c9aff"/>';
      var lab = b.to === null ? '≥' + b.from : (b.from === b.to ? String(b.from) : b.from + '–' + b.to);
      bars += '<text x="' + (x + bw / 2) + '" y="' + (H - 8) + '" fill="#6e7d8c" font-size="9" text-anchor="middle">' + lab + '</text>';
    });
    host.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '">' +
      '<line x1="' + L + '" y1="' + (T + ih) + '" x2="' + (L + iw) + '" y2="' + (T + ih) + '" stroke="#2a3441"/>' +
      bars + '</svg>';
  }

  E.renderHist = renderHist;
  E.renderScatter = renderScatter;
})(window.MSL);
