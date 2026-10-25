/* Trang Thử nghiệm — chế độ Live (MT5 chỉ đọc nến, docs/plans/plan_mt5_live.md): chọn / tạo luồng, chart = replay ghim ở nến
   cuối (S.replay.live — dùng lại mọi lớp vẽ của replay: L.beginSession, L.applySnapshot), tự nối nến mới (hỏi backend theo
   since), tab Thống kê = điểm forward. Không có tiến / lùi, không gửi lệnh. Thuật toán của luồng do backend báo. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var S = L.S;
  var POLL_MS = 10000;          // bằng nhịp backend hỏi MT5 — hỏi dày hơn không thấy thêm gì
  var IDLE_MS = 60000;          // luồng không chạy / lỗi: hỏi thưa
  var PILL = { running: 'pill-ok', stopped: 'pill-muted', data_error: 'pill-bad', outdated: 'pill-bad', rebuild_mismatch: 'pill-bad' };
  var info = { algorithm: null, hasPkg: true };   // từ GET /api/live: thuật toán của luồng live, gói MetaTrader5 có cài
  var openSeq = 0;                                // lần mở luồng mới nhất — phản hồi của lần mở cũ bị bỏ

  function liveSession() { return L.replaying() && S.replay.live ? S.replay : null; }

  async function loadFeeds(selectId) {
    var sel = $('#lv-feed');
    var res = await API.liveList();
    info = { algorithm: res.algorithm, hasPkg: res.goi_mt5 };
    var cur = selectId || sel.value;
    sel.innerHTML = res.luong.length ? res.luong.map(function (f) {
      return '<option value="' + esc(f.id) + '">' + esc(f.symbol + ' ' + f.timeframe + ' · ' + f.mt5_symbol + ' · ' +
        f.status_vi + ' · ' + fmtIso(f.created_at)) + '</option>';
    }).join('') : '<option value="">— chưa có luồng —</option>';
    if (cur && res.luong.some(function (f) { return f.id === cur; })) sel.value = cur;
    return res;
  }

  /** Vào chế độ Live: mở luồng đang chọn (hoặc luồng mới nhất). Chưa có luồng → chỉ thanh Live + lời nhắc. */
  async function enterLive() {
    try {
      var res = await loadFeeds();
      if (S.mode !== 'live') return;
      if (!res.luong.length) {
        showEmpty();
        L.banner('warn', 'Chưa có luồng live. Bấm <strong>Tạo luồng…</strong> (cần terminal MT5 đang mở, đã đăng nhập' +
          (res.goi_mt5 ? '' : '; gói <code>MetaTrader5</code> chưa cài trong .venv') + '). Lab chỉ đọc nến, không gửi lệnh.');
        return;
      }
      await openFeed($('#lv-feed').value);
    } catch (e) {
      showEmpty();
      L.banner('error', 'Không đọc được danh sách luồng live: ' + esc(e.message));
    }
  }

  /** Live chưa có phiên (chưa có luồng / mở lỗi): chart trống, không để lại phiên trước. */
  function showEmpty() {
    $('#chart-empty').hidden = false;
    $('#rp-explain').hidden = true;
    $('#stats-body').innerHTML = '';
    L.renderEvents([]);
    L.applyChartEvents();
    renderStatus(null);
  }

  /** Mở luồng ``fid``; true khi xong. Lần mở mới hơn, hay đã rời Live, thì phản hồi này bị bỏ. */
  async function openFeed(fid) {
    if (S.mode !== 'live') return false;
    var seq = ++openSeq;
    await L.stopReplay();
    if (!fid) { showEmpty(); return false; }
    L.loading(true);
    try {
      var snap = await API.liveSnapshot(fid, -1);   // since = −1: mọi sự kiện, timeline VÀ mọi nến, đọc trong một lần
      if (S.mode !== 'live' || seq !== openSeq) return false;
      if (!S.algo || S.algo.name !== snap.algorithm) {      // lớp hiển thị của plugin; rời Live thì trả lại (switchMode)
        if (!S.algoBeforeLive && S.algo) S.algoBeforeLive = S.algo.name;
        L.selectAlgorithm(snap.algorithm);
      }
      var r = L.beginSession(fid, snap, snap.bars_moi, { live: true, statsAt: null, busy: false });
      L.renderReplay();
      renderStatus(snap.live);
      L.banner(null);
      schedule(r, snap.live);
      return true;
    } catch (e) {
      if (S.mode !== 'live' || seq !== openSeq) return false;
      showEmpty();
      L.banner('error', 'Không mở được luồng live: ' + esc(e.message));
      return false;
    } finally {
      if (seq === openSeq) L.loading(false);
    }
  }

  /** Hẹn lần hỏi sau: thưa khi luồng không chạy / lỗi; tab trình duyệt ẩn thì thôi (hiện lại → hỏi ngay, since gom đủ). */
  function schedule(r, st, err) {
    clearTimeout(r.timer);
    r.timer = null;
    if (document.hidden) return;
    r.timer = setTimeout(function () { tick(r); }, st && st.status === 'running' && !st.loi && !err ? POLL_MS : IDLE_MS);
  }

  /** Một lần hỏi phần mới sau con trỏ (mỗi lúc chỉ một — hẹn giờ và lúc tab hiện lại không chồng nhau). */
  async function tick(r) {
    if (S.replay !== r || r.busy) return;
    r.busy = true;
    var err = null;
    try {
      var snap = await API.liveSnapshot(r.sid, r.cursor);
      if (S.replay !== r) return;                  // đã đổi luồng / chế độ trong lúc chờ
      if (snap.cursor > r.cursor && snap.delta_since === r.cursor) {
        Array.prototype.push.apply(r.bars, snap.bars_moi);
        L.applySnapshot(r, snap);
      } else if (snap.cursor > r.cursor) {         // delta không nối tiếp con trỏ (không nên xảy ra): mở lại cho chắc
        r.busy = false;
        openFeed(r.sid);
        return;
      } else {
        r.snapshot.live = snap.live;               // không có nến mới: backend chỉ trả trạng thái luồng
      }
      renderStatus(snap.live);
    } catch (e) {
      if (S.replay !== r) return;
      err = e.message;
      renderStatus(r.snapshot.live, err);
    } finally {
      r.busy = false;
    }
    if (S.replay === r) schedule(r, r.snapshot.live, err);
  }

  function renderStatus(st, err) {
    var pill = $('#lv-pill'), line = $('#lv-status'), btn = $('#lv-toggle');
    if (!st) {
      pill.className = 'pill pill-muted';
      pill.textContent = 'Live · chỉ đọc nến MT5';
      line.textContent = err ? 'Lỗi: ' + err : '';
      btn.hidden = true;
      return;
    }
    pill.className = 'pill ' + (st.loi ? 'pill-bad' : PILL[st.status] || 'pill-muted');
    pill.textContent = 'Live · ' + st.status_vi;
    pill.title = st.status_note || '';
    var bits = [st.symbol + ' ' + st.timeframe + ' (MT5 ' + st.mt5_symbol + ', giờ server ' + st.server_tz + ')',
      'nến cuối đóng ' + fmtIso(st.nen_cuoi_dong_luc), 'hỏi lần cuối ' + fmtIso(st.lan_hoi_cuoi),
      st.so_ban_ghi + ' bản ghi dự báo (' + st.kip_thoi + ' kịp thời)'];
    if (st.sua_lich_su) bits.push(st.sua_lich_su + ' lần broker sửa lịch sử');
    if (st.loi || err) bits.push('lỗi: ' + (err || st.loi));
    line.textContent = bits.join(' · ');
    line.title = (st.nhat_ky || []).map(function (x) { return fmtIso(x.at) + ' ' + x.message; }).join('\n');
    btn.hidden = st.status === 'outdated' || st.status === 'rebuild_mismatch';
    btn.textContent = st.status === 'running' ? 'Dừng' : 'Chạy tiếp';
  }

  async function toggleFeed() {
    var r = liveSession();
    if (!r) return;
    try {
      var st = r.snapshot.live.status === 'running' ? await API.liveStop(r.sid) : await API.liveResume(r.sid);
      if (S.replay !== r) return;                  // đã đổi luồng trong lúc chờ
      r.snapshot.live = st;
      renderStatus(st);
      schedule(r, st);
      loadFeeds(r.sid).catch(function () { /* nhãn trong danh sách cập nhật lần sau */ });
    } catch (e) {
      if (S.replay === r) L.banner('error', esc(e.message));
    }
  }

  // ------------------------------------------------------------------ tab Thống kê = điểm forward
  function pct(x) { return x === null || x === undefined ? '—' : (100 * x).toFixed(1) + '%'; }
  function num(x) { return x === null || x === undefined ? '—' : x.toFixed(3); }
  function verdict(n, min) { return n < min ? ' <span class="muted">· chưa kết luận</span>' : ''; }
  function row(label, n, value) { return '<tr><td>' + label + '</td><td class="num">' + n + '</td><td>' + value + '</td></tr>'; }
  /** Brier như tab Thống kê của lần chạy: «0.114 (B0 0.104)». */
  function brierRow(label, s, min) {
    return s && s.n ? row(label, s.n, num(s.brier) + ' (B0 ' + num(s.brier_b0) + ')' + verdict(s.n, min)) : row(label, 0, '—');
  }
  function box(k, v) { return '<div class="stat-box"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>'; }

  function forwardHtml(fw) {
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
        row('Khoảng 80% — độ phủ (mục tiêu 80%)', s.n, pct(s.phu_80) + verdict(s.n, min)) +
        row('Khoảng 50% — độ phủ (mục tiêu 50%)', s.n, pct(s.phu_50)) +
        row('Khoảng 80% — skill pinball so với B0 (&gt; 0 là hơn B0)', s.n, pct(s.skill_so_voi_b0)) +
        brierRow('Chạm mức gần nhất / biên range — Brier', s.cham_tong, min) +
        brierRow('Còn giữ trạng thái — Brier', s.con_giu, min) +
        brierRow('Phá biên range — Brier', s.pha_bien, min) +
        '</tbody></table>';
    });
    return html;
  }

  /** Điểm forward đổi khi có nến mới (hoặc broker sửa lịch sử); chỉ hỏi khi tab Thống kê đang mở (bấm tab → gọi lại). */
  async function renderLiveStats(r) {
    var key = r.cursor + ':' + ((r.snapshot.live || {}).sua_lich_su || 0);
    if (!$('.tab-panel[data-panel="stats"]').classList.contains('active') || r.statsAt === key) return;
    var at = r.statsAt = key;
    var html;
    try {
      html = forwardHtml(await API.liveForward(r.sid));
    } catch (e) {
      html = '<div class="note note-error">Không lấy được điểm forward: ' + esc(e.message) + '</div>';
      r.statsAt = null;
    }
    if (S.replay === r && r.statsAt === at) $('#stats-body').innerHTML = html;
  }

  // ------------------------------------------------------------------ tạo luồng
  function openCreate() {
    $('#live-modal').hidden = false;
    $('#lv-error').hidden = true;
    $('#lv-hint').textContent = '';
    $('#lv-algo').textContent = info.algorithm || '—';
    $('#lv-pkg-note').textContent = info.hasPkg ? '' :
      'Gói MetaTrader5 CHƯA cài trong .venv: pip install MetaTrader5 (Windows), mở terminal và đăng nhập sẵn.';
  }

  function closeCreate() { $('#live-modal').hidden = true; }

  function createPayload() {
    return {
      symbol: $('#lv-symbol').value.trim(), mt5_symbol: $('#lv-mt5-symbol').value.trim(),
      timeframe: $('#lv-tf').value, server_tz: $('#lv-tz').value.trim(),
      history_bars: parseInt($('#lv-hist').value, 10), terminal_path: $('#lv-path').value.trim(),
      params: S.algo && S.algo.name === info.algorithm ? L.collectParams() : {}
    };
  }

  function hrs(s) {
    var a = Math.abs(s);
    return (s < 0 ? '−' : '+') + Math.floor(a / 3600) + ':' + String(a % 3600 / 60).padStart(2, '0');
  }

  async function checkTz() {
    var p = createPayload(), el = $('#lv-hint');
    el.textContent = 'Đang hỏi terminal…';
    try {
      var h = await API.liveHint({ mt5_symbol: p.mt5_symbol || p.symbol, server_tz: p.server_tz, terminal_path: p.terminal_path });
      el.textContent = !h.co_tick ? 'Chưa có tick nào — không kiểm được. ' + h.ghi_chu_vi :
        'Giờ tick cuối − đồng hồ máy ≈ ' + hrs(h.lech_giay) +
        (h.khai_bao_giay === null ? '' : ' · khai báo ' + hrs(h.khai_bao_giay) + (h.khop ? ' → khớp' : ' → KHÔNG khớp')) +
        (h.tin_duoc ? '' : ' · tick cũ (thị trường đóng?) — chưa tin được') + '. ' + h.ghi_chu_vi;
    } catch (e) {
      el.textContent = 'Lỗi: ' + e.message;
    }
  }

  async function doCreate() {
    var btn = $('#lv-do-create');
    $('#lv-error').hidden = true;
    btn.disabled = true;
    btn.textContent = 'Đang lấy lịch sử, chạy thuật toán…';
    var st;
    try {
      st = await API.liveCreate(createPayload());
    } catch (e) {
      $('#lv-error').hidden = false;
      $('#lv-error').textContent = e.message;
      return;
    } finally {
      btn.disabled = false;
      btn.textContent = 'Tạo luồng';
    }
    closeCreate();
    try {
      await loadFeeds(st.id);
    } catch (e) {
      L.banner('error', 'Đã tạo luồng ' + esc(st.id) + ' nhưng không đọc lại được danh sách: ' + esc(e.message));
      return;
    }
    if (await openFeed(st.id)) {                   // đã rời Live / mở luồng khác trong lúc tạo → không mở đè
      L.banner('ok', 'Đã tạo luồng live <strong>' + esc(st.symbol + ' ' + st.timeframe) + '</strong>: ' + st.history_bars +
        ' nến lịch sử, bản ghi dự báo bắt đầu từ nến đóng sau ' + esc(fmtIso(st.forward_from)) + '. Lab chỉ đọc nến MT5.');
    }
  }

  function bind() {
    $('#lv-feed').addEventListener('change', function (e) { openFeed(e.target.value); });     // openFeed tự kiểm chế độ
    $('#lv-toggle').addEventListener('click', toggleFeed);
    $('#lv-new').addEventListener('click', openCreate);
    $('#btn-close-live').addEventListener('click', closeCreate);
    $('#lv-cancel').addEventListener('click', closeCreate);
    $('#lv-check-tz').addEventListener('click', checkTz);
    $('#lv-do-create').addEventListener('click', doCreate);
    document.addEventListener('visibilitychange', function () {
      var r = liveSession();
      if (r && !document.hidden && !r.timer) tick(r);
    });
  }

  L.bindLive = bind;
  L.enterLive = enterLive;
  L.renderLiveStats = renderLiveStats;
})(window.MSL);
