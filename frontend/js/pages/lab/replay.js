/* Trang Thử nghiệm — replay từng nến: phiên, tiến/lùi/tua, phát, ghép delta, trạng thái nội bộ tại con trỏ. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var $$ = MSL.dom.$$;
  var detectDigits = MSL.format.detectDigits;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var S = L.S;

  /**
   * cfg (tuỳ chọn): { dataset_id, algorithm, params, range_start, range_end, seekTo }.
   * Không truyền = dùng form (hành vi cũ). «Replay từ vùng đang xem» truyền cấu
   * hình của run đang hiển thị và seekTo = nến đầu vùng nhìn.
   */
  async function enterReplay(cfg) {
    if (!S.dataset) { L.banner('warn', 'Chọn dataset trước khi replay.'); switchMode('full'); return; }
    if (!cfg && !L.confirmHeavyRange('Replay')) { switchMode('full'); return; }
    cfg = cfg || {};
    L.loading(true);
    try {
      var snap = await API.replayCreate({
        dataset_id: cfg.dataset_id || S.dataset.id,
        algorithm: cfg.algorithm || S.algo.name,
        params: cfg.params || L.collectParams(),
        range_start: cfg.range_start !== undefined ? cfg.range_start : L.fromLocalInput($('#range-start').value),
        range_end: cfg.range_end !== undefined ? cfg.range_end : L.fromLocalInput($('#range-end').value)
      });
      var barsRes = await API.replayBars(snap.session_id);
      S.replay = {
        sid: snap.session_id,
        bars: barsRes.bars,
        cursor: snap.cursor,
        events: snap.events,
        timeline: snap.timeline,
        snapshot: snap,
        playing: false,
        timer: null,
        renderedCursor: -2,
        prev: null,
        renderedEvents: -1
      };
      S.digits = detectDigits(barsRes.bars);
      S.chart.setDigits(S.digits);
      $('#rp-slider').min = -1;
      $('#rp-slider').max = String(barsRes.bars.length - 1);
      $('#rp-slider').value = String(snap.cursor);
      $('#chart-empty').hidden = true;
      $('#btn-export-png').disabled = false;
      $('#btn-export-csv').disabled = true;
      if (cfg.seekTo !== undefined && cfg.seekTo >= 0) {
        await replayAction(function (sid, since) { return API.replaySeek(sid, cfg.seekTo, since); });
      } else {
        renderReplay();
      }
      L.banner(null);
    } catch (e) {
      L.banner('error', 'Không tạo được phiên replay: ' + esc(e.message));
      switchMode('full');
    } finally {
      L.loading(false);
    }
  }

  function renderReplay() {
    var r = S.replay;
    if (!r) return;
    var visible = r.bars.slice(0, r.cursor + 1);
    // Không tự zoom: giữ độ rộng nến người dùng đang chọn (như Bar Replay của TradingView) — nến cuối đang trong khung
    // nhìn thì chart tự cuộn theo nến mới. Phiên mới (renderedCursor = −2) bật lại tự co giãn trục giá; lùi / tua trong
    // phiên giữ khung giá người dùng đang chỉnh.
    if (r.renderedCursor === r.cursor - 1 && r.cursor >= 0) {
      S.chart.appendBar(r.bars[r.cursor]);
    } else {
      S.chart.setBars(visible, { keepPriceScale: r.renderedCursor !== -2 });
      // Phiên mới / tua / tới xác nhận kế tiếp: đưa nến con trỏ vào khung nếu đang khuất. Lùi một nến thì để yên.
      if (r.cursor !== r.renderedCursor - 1) S.chart.revealLastBar();
    }
    r.renderedCursor = r.cursor;
    L.applyChartEvents();

    $('#rp-slider').value = String(r.cursor);
    var bar = r.cursor >= 0 ? r.bars[r.cursor] : null;
    $('#rp-position').textContent = (r.cursor + 1) + ' / ' + r.bars.length;
    $('#rp-position').title = bar ? fmtIso(bar.close_time) : 'Chưa nạp nến';

    var lastId = r.events.length ? r.events[r.events.length - 1].event_id : '';
    if (r.renderedEvents !== r.events.length || r.renderedLastId !== lastId) {
      L.renderEvents(r.events);
      r.renderedEvents = r.events.length;
      r.renderedLastId = lastId;
    }
    L.renderExplain();
    var s = r.snapshot || {};
    var warmupEl = $('#rp-warmup');
    var warmupNeed = s.warmup_bars || 0;
    var skipBtn = $('#rp-skip-warmup');
    if (s.data_status === 'WARMUP_INSUFFICIENT') {
      warmupEl.hidden = false;
      warmupEl.textContent = 'Warm-up ' + Math.max(0, r.cursor + 1) + '/' + warmupNeed;
      warmupEl.title = s.data_status_message_vi || '';
      if (S.mode === 'replay') L.banner(null);
    } else {
      warmupEl.hidden = true;
    }
    if (skipBtn) skipBtn.disabled = !warmupNeed || r.cursor >= warmupNeed - 1;
    if (s.data_status && s.data_status !== 'OK' && s.data_status !== 'WARMUP_INSUFFICIENT') {
      L.banner('warn', esc(s.data_status_message_vi));
    }
    renderReplayStats();
    L.renderAlgoNotes(s.algorithm, null, s.data_status, s.pending_state);
  }

  function renderReplayStats() {
    var r = S.replay;
    if (!r) return;
    var byType = {};
    r.events.forEach(function (e) { byType[e.structure_type] = (byType[e.structure_type] || 0) + 1; });
    var ps = (r.snapshot && r.snapshot.pending_state) || {};
    var html = '<div class="note note-info" style="margin-bottom:10px">Thống kê trong chế độ replay được tính trên phần dữ liệu ĐÃ NẠP, không phải toàn bộ dataset.</div>';
    html += '<div class="stat-grid">' +
      '<div class="stat-box"><div class="k">Nến đã nạp</div><div class="v">' + (r.cursor + 1) + '</div></div>' +
      '<div class="stat-box"><div class="k">Tổng nến</div><div class="v">' + r.bars.length + '</div></div>' +
      '<div class="stat-box"><div class="k">Sự kiện đã xác nhận</div><div class="v">' + r.events.length + '</div></div>' +
      '<div class="stat-box"><div class="k">Warm-up (nến)</div><div class="v">' + ((r.snapshot && r.snapshot.warmup_bars) || '—') + '</div></div>' +
      '</div>';
    html += '<div class="section-title">Trạng thái nội bộ thuật toán tại nến hiện tại</div>';
    // Plugin nhận dạng pending_state của mình (C2: setup_dang_mo, DC: dc); không ai nhận → mức swing (fallback).
    html += MSL.algos.pick('pendingHtml', ps, S.digits);
    html += '<div class="section-title">Số sự kiện theo loại (tính tới nến hiện tại)</div>';
    var keys = Object.keys(byType).sort();
    html += '<table class="data-table"><thead><tr><th>Loại</th><th>Số sự kiện</th></tr></thead><tbody>';
    if (!keys.length) html += '<tr><td colspan="2" class="empty-cell">Chưa có sự kiện nào được xác nhận.</td></tr>';
    keys.forEach(function (k) {
      html += '<tr><td><span class="badge b-' + esc(k) + '">' + esc(k) + '</span></td><td class="num">' + byType[k] + '</td></tr>';
    });
    html += '</tbody></table>';
    $('#stats-body').innerHTML = '<p class="hint">F1, P90 và so sánh nhiều cấu hình: <a href="/danh-gia">Đánh giá thuật toán</a>.</p>' + html;
  }

  async function replayAction(fn) {
    if (!S.replay) return;
    try {
      var snap = await fn(S.replay.sid, S.replay.cursor);
      var r = S.replay;
      r.prev = { cursor: r.cursor, pending: r.snapshot ? r.snapshot.pending_state : null };
      r.snapshot = snap;
      r.cursor = snap.cursor;
      mergeReplayDelta(r, snap);
      renderReplay();
      return snap;
    } catch (e) {
      pausePlay();
      L.banner('error', esc(e.message));
    }
  }

  function playPause() {
    if (!S.replay) return;
    if (S.replay.playing) { pausePlay(); return; }
    S.replay.playing = true;
    $('#rp-play').textContent = '⏸';
    var tick = async function () {
      if (!S.replay || !S.replay.playing) return;
      if (S.replay.cursor >= S.replay.bars.length - 1) { pausePlay(); return; }
      await replayAction(function (sid, since) { return API.replayStep(sid, 1, since); });
      if (S.replay && S.replay.playing) {
        S.replay.timer = setTimeout(tick, parseInt($('#rp-speed').value, 10));
      }
    };
    tick();
  }

  function pausePlay() {
    if (!S.replay) return;
    S.replay.playing = false;
    if (S.replay.timer) { clearTimeout(S.replay.timer); S.replay.timer = null; }
    $('#rp-play').textContent = '▶';
  }

  async function stopReplay() {
    if (!S.replay) return;
    pausePlay();
    try { await API.replayClose(S.replay.sid); } catch (e) { /* bỏ qua */ }
    S.replay = null;
  }

  /**
   * Ghép phản hồi replay. `delta_since = s`: phần tới nến s không đổi (nhân quả) nên
   * chỉ cắt phần sau s rồi nối phần mới; `null` = bản đầy đủ.
   */
  function mergeReplayDelta(r, snap) {
    var s = snap.delta_since;
    if (s === null || s === undefined) {
      r.events = snap.events;
      r.timeline = snap.timeline;
      r.renderedEvents = -1;
      return;
    }
    var ev = r.events.slice(), tl = r.timeline.slice();
    while (ev.length && ev[ev.length - 1].confirmed_bar_index > s) ev.pop();
    while (tl.length && tl[tl.length - 1].bar_index > s) tl.pop();
    Array.prototype.push.apply(ev, snap.events);
    Array.prototype.push.apply(tl, snap.timeline);
    r.events = ev;
    r.timeline = tl;
  }

  /**
   * Đổi thuật toán/tham số khi đang replay: mở phiên mới theo form và nhảy tới
   * đúng nến đang xem. Thuật toán mới vẫn chạy nhân quả từ nến #0 tới đó.
   */
  async function restartReplayKeepCursor(what) {
    var cur = S.replay ? S.replay.cursor : -1;
    await stopReplay();
    await enterReplay({ seekTo: cur });
    if (S.replay) {
      L.banner('info', 'Đã đổi ' + esc(what) + ': replay chạy lại với <strong>' + esc(S.algo.display_name_vi) +
        '</strong> (v' + esc(S.algo.version) + ') tới nến #' + Math.max(0, cur) +
        ' — tính lại nhân quả từ nến #0, không dùng kết quả của thuật toán cũ.');
    }
  }

  /** Bắt đầu replay đúng cấu hình của run đang hiển thị, tại nến đầu vùng đang xem. */
  async function replayFromView() {
    if (!S.run) return;
    var vr = S.chart.visibleIndexRange();
    var start = vr ? vr.start : 0;
    await stopReplay();
    var own = MSL.algos.forAlgorithm(S.run.algorithm);
    ((own && own.replayLayers) || []).forEach(function (layer) {   // vd DC: bật «Ứng viên» để thấy từng bước
      if (!S.layers[layer]) L.setLayer(layer, true);   // S.layers + checkbox + lớp phụ thuộc (data-requires)
    });
    $('#chk-explain').checked = true;
    if (!S.algo || S.algo.name !== S.run.algorithm) L.selectAlgorithm(S.run.algorithm);
    switchMode('replay');
    await enterReplay({
      dataset_id: S.run.dataset_id, algorithm: S.run.algorithm, params: S.run.params,
      range_start: S.run.range_start, range_end: S.run.range_end, seekTo: start
    });
    if (S.replay) {
      L.banner('info', 'Replay bắt đầu ở nến #' + start + ' (đầu vùng đang xem) với đúng tham số của lần chạy. ' +
        'Thuật toán đã chạy nhân quả từ nến #0 tới đây; từ giờ bấm <strong>▶</strong>, <strong>→</strong> hoặc ' +
        '<strong>Tới xác nhận kế tiếp</strong> để xem từng bước. Khung bên trái giải thích mỗi nến.');
    }
  }

  function switchMode(mode) {
    S.mode = mode;
    $$('.mode-btn').forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-mode') === mode); });
    $('#replay-bar').hidden = mode !== 'replay';
    if (S.chart) S.chart.setAnchorRight(mode === 'replay');
    if (S.chart2) S.chart2.setAnchorRight(mode === 'replay');
    $('#btn-replay-here').hidden = !(mode === 'full' && S.run);
    if (mode !== 'replay') $('#rp-explain').hidden = true;
    $('#mode-note').innerHTML = mode === 'full'
      ? 'Marker tại nến sự kiện, không phải lúc hệ thống biết. Cột «Xác nhận lúc» mới là thời điểm tín hiệu khả dụng.'
      : 'Replay chỉ nạp prefix tới nến hiện tại. Phím → ← từng nến, Space phát. Bấm <strong>Tới hết warm-up</strong> để bỏ qua nến đầu.';
  }

  L.enterReplay = enterReplay;
  L.pausePlay = pausePlay;
  L.playPause = playPause;
  L.replayAction = replayAction;
  L.replayFromView = replayFromView;
  L.restartReplayKeepCursor = restartReplayKeepCursor;
  L.stopReplay = stopReplay;
  L.switchMode = switchMode;
})(window.MSL);
