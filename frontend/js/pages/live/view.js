/* Trang Live MT5 — vẽ luồng đang xem: chart (nến tới nến cuối, sự kiện, timeline, trạng thái nội bộ), khung phụ, dòng trạng
   thái / bảng «Nhận diện» / khung giải thích (hook của plugin phụ trách thuật toán của luồng — không so tên thuật toán), sự
   kiện gần đây, thông tin luồng, nhật ký, điểm forward. */
(function (MSL) {
  'use strict';

  var V = MSL.live;
  var S = V.S;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var RECENT = 200;             // số sự kiện gần nhất ở tab «Sự kiện gần đây»
  var shown = [];               // các dòng đang hiện ở tab đó (mới nhất trước)
  var PILL = { running: 'pill-ok', stopped: 'pill-muted', data_error: 'pill-bad', outdated: 'pill-bad', rebuild_mismatch: 'pill-bad' };

  function plugin() { return S.session ? MSL.algos.forAlgorithm(S.session.snapshot.algorithm) : null; }

  /** Phiên mới / nến mới: nến lên chart (một nến mới → appendBar; còn lại setBars một bản sao — chart giữ mảng nó nhận),
   * rồi mọi lớp vẽ theo phiên. */
  function render() {
    var r = S.session;
    if (r.renderedCursor === r.cursor - 1) {
      S.chart.appendBar(r.bars[r.cursor]);
    } else {
      S.chart.setBars(r.bars.slice(0, r.cursor + 1), { keepPriceScale: r.renderedCursor !== -2 });
      S.chart.revealLastBar();
    }
    r.renderedCursor = r.cursor;
    $('#chart-empty').hidden = true;
    draw();
    renderEvents(false);
    renderForward();
  }

  /** Sự kiện / timeline / trạng thái nội bộ lên chart, khung phụ, chú giải, khung giải thích — gọi lại khi đổi lớp. */
  function draw() {
    var r = S.session, own = plugin();
    if (r) {
      S.chart.setEvents(r.events, r.timeline, {
        layers: S.layers, markerAtConfirm: false, replayCursor: r.cursor, selectedEventId: S.selectedEventId,
        pendingState: r.snapshot.pending_state
      });
      MSL.algos.callFor(r.snapshot.algorithm, 'syncLegend', r.timeline, r.events, S);
    }
    S.pane.render(own, r && r.timeline, r && r.cursor, S.layers);
    renderExplain();
  }

  /** Khung «Thuật toán đang làm gì» ở nến cuối (hook `explain` của plugin). */
  function renderExplain() {
    var r = S.session, box = $('#rp-explain'), own = plugin();
    if (!r || !own || !own.explain || !$('#chk-explain').checked) { box.hidden = true; return; }
    var bar = r.bars[r.cursor];
    box.hidden = false;
    $('#rp-explain-bar').textContent = 'nến #' + r.cursor + ' · ' + fmtIso(bar.close_time);
    $('#rp-explain-body').innerHTML = own.explain(r, bar, S);
  }

  /** Chưa có phiên (chưa có luồng / đang mở / mở lỗi): gỡ nến và lớp vẽ của luồng trước (plugin tự ẩn khung của mình qua
   * chart.clear và syncLegend), chart trống. */
  function clear() {
    S.session = null;
    S.chart.setBars([]);
    S.chart.setEvents([], [], { layers: S.layers });
    MSL.algos.callFor(S.info.algorithm, 'syncLegend', [], [], S);
    $('#chart-empty').hidden = false;
    draw();
    renderEvents(true);
    renderStatus(null);
    $('#forward-body').innerHTML = '<p class="hint">Chưa mở luồng.</p>';
  }

  // ------------------------------------------------------------------ sự kiện gần đây (mới nhất ở trên)
  /** Dựng lại bảng khi có sự kiện mới / đổi phiên (`force`). */
  function renderEvents(force) {
    var r = S.session, tbody = $('#events-table tbody');
    if (!force && r && r.eventsShown === r.events.length) return;
    if (r) r.eventsShown = r.events.length;
    shown = r ? r.events.slice(-RECENT).reverse() : [];
    if (!shown.length) { tbody.innerHTML = '<tr><td colspan="6" class="empty-cell">Chưa có sự kiện.</td></tr>'; return; }
    tbody.innerHTML = shown.map(function (e, i) {
      return '<tr data-ev="' + i + '"' + (e.event_id === S.selectedEventId ? ' class="selected"' : '') + '>' +
        '<td><span class="badge b-' + esc(e.structure_type) + '"' +
          (e.structure_text_vi ? ' title="' + esc(e.structure_text_vi) + '"' : '') + '>' + esc(e.structure_type) + '</span></td>' +
        '<td class="num">' + Number(e.price).toFixed(S.digits) + '</td>' +
        '<td class="mono">' + fmtIso(e.event_time) + '</td>' +
        '<td class="mono">' + fmtIso(e.confirmed_at) + '</td>' +
        '<td class="num">' + e.confirmation_lag_bars + '</td>' +
        '<td class="mono">' + esc(e.reason_code) + '</td></tr>';
    }).join('');
  }

  /** Chọn một dòng sự kiện: đánh dấu dòng, đánh dấu trên chart (plugin có `selectEventOnChart`), đưa nến vào khung nhìn. */
  function selectEvent(i) {
    var ev = shown[i], own = plugin();
    if (!ev) return;
    S.selectedEventId = ev.event_id;
    Array.prototype.forEach.call($('#events-table tbody').rows, function (tr) {
      tr.classList.toggle('selected', tr.getAttribute('data-ev') === String(i));
    });
    if (own && own.selectEventOnChart) draw();
    S.chart.focusEvent(ev);
  }

  // ------------------------------------------------------------------ thông tin luồng, nhật ký
  function renderStatus(st, err) {
    var pill = $('#lv-pill'), btn = $('#lv-toggle');
    $('#lv-info').hidden = !st && !err;
    if (!st) {
      pill.className = 'pill pill-muted';
      pill.textContent = 'Chưa mở luồng';
      $('#lv-status').innerHTML = err ? '<dt>Lỗi</dt><dd>' + esc(err) + '</dd>' : '';
      $('#log-body').innerHTML = '<p class="hint">Chưa mở luồng.</p>';
      btn.hidden = true;
      return;
    }
    var bad = st.loi || err;
    pill.className = 'pill ' + (bad ? 'pill-bad' : PILL[st.status] || 'pill-muted');
    pill.textContent = st.status_vi + (bad ? ' · lỗi' : '');
    pill.title = st.status_note || '';
    var rows = [['Mã', st.symbol + ' ' + st.timeframe + ' (MT5 ' + st.mt5_symbol + ')'], ['Giờ server', st.server_tz],
      ['Thuật toán', st.algorithm + ' ' + st.algorithm_version], ['Nến', st.so_nen + ' (lịch sử ' + st.history_bars + ')'],
      ['Nến cuối đóng', fmtIso(st.nen_cuoi_dong_luc)], ['Hỏi lần cuối', fmtIso(st.lan_hoi_cuoi)],
      ['Forward từ', fmtIso(st.forward_from)], ['Bản ghi dự báo', st.so_ban_ghi + ' (' + st.kip_thoi + ' kịp thời)']];
    if (st.sua_lich_su) rows.push(['Broker sửa lịch sử', st.sua_lich_su + ' lần']);
    if (st.status_note) rows.push(['Ghi chú', st.status_note]);
    if (bad) rows.push(['Lỗi', err || st.loi]);
    $('#lv-status').innerHTML = rows.map(function (x) { return '<dt>' + esc(x[0]) + '</dt><dd>' + esc(x[1]) + '</dd>'; }).join('');
    var log = st.nhat_ky || [];
    $('#log-body').innerHTML = log.length ? '<table class="data-table"><thead><tr><th>Lúc</th><th>Mức</th><th>Nội dung</th>' +
      '</tr></thead><tbody>' + log.map(function (x) {
        return '<tr><td class="mono">' + esc(fmtIso(x.at)) + '</td><td>' + esc(x.level) + '</td><td>' + esc(x.message) + '</td></tr>';
      }).join('') + '</tbody></table><p class="hint">' + log.length + ' dòng gần nhất (kho live.sqlite giữ đủ).</p>'
      : '<p class="hint">Chưa có dòng nhật ký.</p>';
    btn.hidden = st.status === 'outdated' || st.status === 'rebuild_mismatch';
    btn.textContent = st.status === 'running' ? 'Dừng' : 'Chạy tiếp';
  }

  // ------------------------------------------------------------------ tab «Điểm forward»
  function box(k, v) { return '<div class="stat-box"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>'; }

  /** Phần chung (bản ghi, kịp thời, ghi bù, khoảng thời gian) + mỗi tầm một bảng, hàng do plugin dựng (hook `forwardRows`). */
  function forwardHtml(fw, algorithm) {
    var min = fw.toi_thieu_ket_luan;
    var html = '<div class="note note-info" style="margin-bottom:10px">' + esc(fw.ghi_chu_vi) + '</div><div class="stat-grid">' +
      box('Bản ghi dự báo', fw.so_ban_ghi) + box('Kịp thời (vào điểm)', fw.kip_thoi) + box('Ghi bù (không tính)', fw.ghi_bu) +
      box('Broker sửa lịch sử', fw.sua_lich_su) + '</div><p class="hint">Forward từ ' + esc(fmtIso(fw.forward_tu)) + ' tới ' +
      esc(fmtIso(fw.nen_cuoi_dong_luc)) + ' · bản ghi của thuật toán ' + esc(fw.phien_ban_ban_ghi) + '.</p>';
    Object.keys(fw.tam).forEach(function (k) {
      var s = fw.tam[k];
      html += '<div class="section-title">Tầm ' + esc(k) + ' — ' + s.cho_ket_cuc + ' dự báo đang chờ kết cục, ' +
        s.bo_qua_khoang_trong + ' bỏ vì khoảng trống</div>' +
        '<table class="data-table"><thead><tr><th>Dự báo</th><th>Đã chấm</th><th>Điểm forward</th></tr></thead><tbody>' +
        (MSL.algos.callFor(algorithm, 'forwardRows', s, min) || []).map(function (x) {
          return '<tr><td>' + esc(x.k) + '</td><td class="num">' + x.n + '</td><td>' + esc(x.v) + '</td></tr>';
        }).join('') + '</tbody></table>';
    });
    return html;
  }

  /** Điểm forward đổi khi có nến mới (hoặc broker sửa lịch sử); chỉ hỏi khi tab «Điểm forward» đang mở (bấm tab → gọi lại). */
  async function renderForward() {
    var r = S.session;
    if (!r || !$('.tab-panel[data-panel="forward"]').classList.contains('active')) return;
    var key = r.cursor + ':' + ((r.snapshot.live || {}).sua_lich_su || 0);
    if (r.fwdKey === key) return;
    r.fwdKey = key;
    var html;
    try {
      html = forwardHtml(await API.liveForward(r.sid), r.snapshot.algorithm);
    } catch (e) {
      html = '<div class="note note-error">Không lấy được điểm forward: ' + esc(e.message) + '</div>';
      if (r.fwdKey === key) r.fwdKey = null;      // lần sau hỏi lại — trừ khi đã có lần hỏi mới hơn
    }
    if (S.session === r && r.fwdKey === key) $('#forward-body').innerHTML = html;
  }

  V.clear = clear;
  V.draw = draw;
  V.render = render;
  V.renderExplain = renderExplain;
  V.renderForward = renderForward;
  V.renderStatus = renderStatus;
  V.selectEvent = selectEvent;
})(window.MSL);
