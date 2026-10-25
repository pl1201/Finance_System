/* Trang Live MT5 (docs/plans/plan_mt5_live.md §7) — chọn / tạo luồng, mở luồng (một lời gọi since = −1: sự kiện, timeline và
   mọi nến đọc cùng lúc), hỏi phần mới sau nến cuối (10 giây; 60 giây khi luồng không chạy / lỗi; ngừng khi tab trình duyệt ẩn),
   dừng / chạy tiếp, ô lớp hiển thị, tab, khởi động. Chỉ đọc nến MT5 — không gửi lệnh. Thuật toán của luồng do backend báo. */
(function (MSL) {
  'use strict';

  var V = MSL.live;
  var S = V.S;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var POLL_MS = 10000;          // bằng nhịp backend hỏi MT5 — hỏi dày hơn không thấy thêm gì
  var IDLE_MS = 60000;          // luồng không chạy / lỗi: hỏi thưa
  var openSeq = 0;              // lần mở luồng mới nhất — phản hồi của lần mở cũ bị bỏ

  async function loadFeeds(selectId) {
    var sel = $('#lv-feed');
    var res = await API.liveList();
    S.info = { algorithm: res.algorithm, hasPkg: res.goi_mt5 };
    var cur = selectId || sel.value;
    sel.innerHTML = res.luong.length ? res.luong.map(function (f) {
      return '<option value="' + esc(f.id) + '">' + esc(f.symbol + ' ' + f.timeframe + ' · ' + f.mt5_symbol + ' · ' +
        f.status_vi + ' · ' + fmtIso(f.created_at)) + '</option>';
    }).join('') : '<option value="">— chưa có luồng —</option>';
    if (cur && res.luong.some(function (f) { return f.id === cur; })) sel.value = cur;
    return res;
  }

  /** Mở luồng ``fid``; true khi xong. Thôi xem luồng cũ ngay (luồng ở backend vẫn chạy): xoá màn hình, lần hỏi đang dở của
   * nó bị bỏ, không hẹn lại. Lần mở mới hơn thì phản hồi này bị bỏ. */
  async function openFeed(fid) {
    var seq = ++openSeq;
    if (S.session) clearTimeout(S.session.timer);
    V.clear();
    if (!fid) return false;
    V.loading(true);
    try {
      var snap = await API.liveSnapshot(fid, -1);   // since = −1: mọi sự kiện, timeline VÀ mọi nến, đọc trong một lần
      if (seq !== openSeq) return false;
      MSL.layerToggles.showPanelsFor(MSL.algos.forAlgorithm(snap.algorithm));   // khung lớp của plugin phụ trách luồng
      S.dataset = snap.dataset;
      S.digits = MSL.format.detectDigits(snap.bars_moi);
      S.chart.setDigits(S.digits);
      S.selectedEventId = null;
      var r = S.session = {
        sid: fid, bars: snap.bars_moi, cursor: snap.cursor, events: snap.events, timeline: snap.timeline, snapshot: snap,
        prev: null, renderedCursor: -2, timer: null, busy: false, fwdKey: null, eventsShown: -1,
        gen: 0                                     // tăng khi Dừng / Chạy tiếp: lần hỏi bắt đầu trước đó không ghi đè trạng thái
      };
      V.render();
      V.renderStatus(snap.live);
      V.banner(null);
      schedule(r, snap.live);
      return true;
    } catch (e) {
      if (seq !== openSeq) return false;
      V.clear();
      V.banner('error', 'Không mở được luồng live: ' + esc(e.message));
      return false;
    } finally {
      if (seq === openSeq) V.loading(false);
    }
  }

  /** Hẹn lần hỏi sau: thưa khi luồng không chạy / lỗi; tab trình duyệt ẩn thì thôi (hiện lại → hỏi ngay, since gom đủ). */
  function schedule(r, st, err) {
    clearTimeout(r.timer);
    r.timer = null;
    if (document.hidden || S.session !== r) return;
    r.timer = setTimeout(function () { tick(r); }, st && st.status === 'running' && !st.loi && !err ? POLL_MS : IDLE_MS);
  }

  /** Một lần hỏi phần mới sau nến cuối (mỗi lúc chỉ một — hẹn giờ và lúc tab hiện lại không chồng nhau). Nến mới → nối
   * nến, sự kiện, timeline (backend chỉ trả phần sau con trỏ — nhân quả, phần trước không đổi), vẽ lại. */
  async function tick(r) {
    if (S.session !== r || r.busy) return;
    r.busy = true;
    var err = null, gen = r.gen;
    try {
      var snap = await API.liveSnapshot(r.sid, r.cursor);
      if (S.session !== r) return;                 // đã đổi luồng trong lúc chờ
      if (r.gen !== gen) snap.live = r.snapshot.live;   // Dừng / Chạy tiếp trong lúc hỏi: giữ trạng thái mới hơn
      if (snap.cursor > r.cursor && snap.delta_since === r.cursor) {
        Array.prototype.push.apply(r.bars, snap.bars_moi);
        Array.prototype.push.apply(r.events, snap.events);
        Array.prototype.push.apply(r.timeline, snap.timeline);
        r.prev = { cursor: r.cursor, pending: r.snapshot.pending_state };
        r.snapshot = snap;
        r.cursor = snap.cursor;
        V.render();
      } else if (snap.cursor > r.cursor) {         // delta không nối tiếp con trỏ (không nên xảy ra): mở lại cho chắc
        r.busy = false;
        openFeed(r.sid);
        return;
      } else {
        r.snapshot.live = snap.live;               // không có nến mới: backend chỉ trả trạng thái luồng
        V.renderForward();                         // broker sửa lịch sử không kèm nến mới vẫn đổi điểm
      }
      V.renderStatus(snap.live);
    } catch (e) {
      if (S.session !== r) return;
      err = e.message;
      V.renderStatus(r.snapshot.live, err);
    } finally {
      r.busy = false;
    }
    schedule(r, r.snapshot.live, err);
  }

  async function toggleFeed() {
    var r = S.session;
    if (!r) return;
    r.gen++;
    try {
      var st = r.snapshot.live.status === 'running' ? await API.liveStop(r.sid) : await API.liveResume(r.sid);
      if (S.session !== r) return;                 // đã đổi luồng trong lúc chờ
      r.gen++;
      r.snapshot.live = st;
      V.renderStatus(st);
      schedule(r, st);
      loadFeeds().catch(function () { /* nhãn trong danh sách cập nhật lần sau; giữ luồng đang chọn */ });
    } catch (e) {
      if (S.session === r) V.banner('error', esc(e.message));
    }
  }

  // ------------------------------------------------------------------ tạo luồng
  function openCreate() {
    $('#live-modal').hidden = false;
    $('#lv-error').hidden = true;
    $('#lv-hint').textContent = '';
    $('#lv-algo').textContent = S.info.algorithm || '—';
    $('#lv-pkg-note').textContent = S.info.hasPkg ? '' :
      'Gói MetaTrader5 CHƯA cài trong .venv: pip install MetaTrader5 (Windows), mở terminal và đăng nhập sẵn.';
  }

  function closeCreate() { $('#live-modal').hidden = true; }

  function createPayload() {
    return {
      symbol: $('#lv-symbol').value.trim(), mt5_symbol: $('#lv-mt5-symbol').value.trim(),
      timeframe: $('#lv-tf').value, server_tz: $('#lv-tz').value.trim(),
      history_bars: parseInt($('#lv-hist').value, 10), terminal_path: $('#lv-path').value.trim()
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
    var st, seq = openSeq;
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
    var other = seq !== openSeq;                   // người dùng đã chọn luồng khác trong lúc tạo → không mở đè
    try {
      await loadFeeds(other ? null : st.id);
    } catch (e) {
      V.banner('error', 'Đã tạo luồng ' + esc(st.id) + ' nhưng không đọc lại được danh sách: ' + esc(e.message));
      return;
    }
    var msg = 'Đã tạo luồng live <strong>' + esc(st.symbol + ' ' + st.timeframe) + '</strong>: ' + st.history_bars +
      ' nến lịch sử, bản ghi dự báo bắt đầu từ nến đóng sau ' + esc(fmtIso(st.forward_from)) + '. Lab chỉ đọc nến MT5.';
    if (other) V.banner('ok', msg + ' Chưa mở vì bạn đang xem luồng khác — chọn trong danh sách.');
    else if (await openFeed(st.id)) V.banner('ok', msg);
  }

  // ------------------------------------------------------------------ gắn sự kiện, khởi động
  function bind() {
    $('#lv-feed').addEventListener('change', function (e) { openFeed(e.target.value); });
    $('#lv-toggle').addEventListener('click', toggleFeed);
    $('#lv-new').addEventListener('click', openCreate);
    $('#btn-close-live').addEventListener('click', closeCreate);
    $('#lv-cancel').addEventListener('click', closeCreate);
    $('#lv-check-tz').addEventListener('click', checkTz);
    $('#lv-do-create').addEventListener('click', doCreate);
    document.addEventListener('visibilitychange', function () {
      var r = S.session;
      if (r && !document.hidden && !r.timer) tick(r);
    });
    MSL.layerToggles.bind('input[data-layer]', S.layers, V.draw);
    $('#chk-explain').addEventListener('change', V.renderExplain);
    $('#rp-explain-hide').addEventListener('click', function () { $('#chk-explain').checked = false; V.renderExplain(); });
    var bottom = MSL.bottomPanel.bind({ panel: $('#bottom-panel'), toggle: $('#btn-toggle-bottom'), handle: $('#bottom-resizer'),
      key: 'msl.live.bottomCollapsed', onOpen: V.renderForward });
    $$('.tab[data-tab]').forEach(function (t) {
      t.addEventListener('click', function () {
        bottom.open();
        $$('.tab[data-tab]').forEach(function (x) { x.classList.toggle('active', x === t); });
        $$('.tab-panel').forEach(function (p) { p.classList.toggle('active', p.getAttribute('data-panel') === t.getAttribute('data-tab')); });
        if (t.getAttribute('data-tab') === 'forward') V.renderForward();
      });
    });
    $('#events-table tbody').addEventListener('click', function (e) {
      var tr = e.target.closest && e.target.closest('tr[data-ev]');
      if (tr) V.selectEvent(parseInt(tr.getAttribute('data-ev'), 10));
    });
  }

  async function init() {
    S.chart = new window.MarketChart($('#chart'), $('#chart-tooltip'));
    S.chart.setAnchorRight(true);                  // nến cuối bám mép phải, như replay
    S.pane = new window.PaneHost({ wrap: $('#pane-wrap'), pane: $('#pane'), legend: $('#pane-legend'), chart: S.chart,
      anchorRight: true });
    MSL.layerToggles.syncInputs(S.layers);
    bind();
    try {
      var h = await API.health();
      $('#health-pill').textContent = 'Backend OK · v' + h.version;
      $('#health-pill').className = 'pill pill-ok';
    } catch (e) {
      $('#health-pill').textContent = 'Backend lỗi';
      $('#health-pill').className = 'pill pill-bad';
      V.banner('error', 'Không kết nối được backend: ' + esc(e.message));
      return;
    }
    try {
      var res = await loadFeeds();
      MSL.layerToggles.showPanelsFor(MSL.algos.forAlgorithm(res.algorithm));   // trước khi mở luồng nào
      MSL.algos.callFor(res.algorithm, 'bindChart', S.chart);   // chỉ plugin phụ trách (plugin khác cần phần tử trang lab)
      if (!res.luong.length) {
        V.clear();
        V.banner('warn', 'Chưa có luồng live. Bấm <strong>Tạo luồng…</strong> (cần terminal MT5 đang mở, đã đăng nhập' +
          (res.goi_mt5 ? '' : '; gói <code>MetaTrader5</code> chưa cài trong .venv') + '). Lab chỉ đọc nến, không gửi lệnh.');
        return;
      }
      await openFeed($('#lv-feed').value);
    } catch (e) {
      V.clear();
      V.banner('error', 'Không đọc được danh sách luồng live: ' + esc(e.message));
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})(window.MSL);
