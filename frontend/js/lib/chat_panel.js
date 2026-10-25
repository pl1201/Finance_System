/* Khung chat «Trợ lý tổng hợp» dùng chung (trang Thử nghiệm — phiên Replay, trang Live MT5 — luồng live;
   docs/plans/plan_tro_ly_tong_hop.md). Mảnh HTML: partials/chat-panel.html. Gửi lệnh tổng hợp / câu hỏi kèm lịch sử; backend
   dựng bản tóm gọn trạng thái thuật toán ở nến đang xét của nguồn và gọi OpenRouter. Hiện câu trả lời (markdown tối giản, đã
   thoát HTML), nến dữ liệu, token, chi phí, số không có trong dữ liệu. Chỉ gọi khi người dùng bấm. */
(function (MSL) {
  'use strict';

  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var MAX_HISTORY = 20;
  var SUMMARY_TURN = 'Tổng hợp trạng thái theo các mục.';   // lượt «tổng hợp» trong lịch sử — không theo chữ nút của trang

  /** Markdown tối giản: «### » tiêu đề, «- » gạch đầu dòng, **đậm**; còn lại là đoạn chữ. Thoát HTML trước. */
  function md(text) {
    var out = [], list = false;
    String(text).split('\n').forEach(function (line) {
      var t = esc(line).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>'), m;
      if ((m = /^\s*[-*•]\s+(.*)$/.exec(t))) {
        if (!list) { out.push('<ul>'); list = true; }
        out.push('<li>' + m[1] + '</li>');
        return;
      }
      if (list) { out.push('</ul>'); list = false; }
      if ((m = /^\s*#{1,4}\s+(.*)$/.exec(t))) out.push('<h4>' + m[1] + '</h4>');
      else if (t.trim()) out.push('<p>' + t + '</p>');
    });
    if (list) out.push('</ul>');
    return out.join('');
  }

  function meta(res) {
    var bits = ['nến #' + res.nen + ' · đóng ' + res.nen_dong_luc + ' UTC', res.mo_hinh];
    if (res.prompt_tokens != null) {
      bits.push(res.prompt_tokens + (res.cached_tokens ? ' (' + res.cached_tokens + ' cache)' : '') + ' → ' +
        res.completion_tokens + ' token');
    }
    if (res.cost != null) bits.push('$' + Number(res.cost).toFixed(4));
    var html = '<div class="chat-meta">' + esc(bits.join(' · ')) + '</div>';
    if (res.so_la && res.so_la.length) {
      html += '<div class="chat-warn">Số không có trong dữ liệu (kiểm lại): ' + esc(res.so_la.join(', ')) + '</div>';
    }
    if (res.cat_ngan) html += '<div class="chat-warn">Câu trả lời bị cắt vì hết giới hạn token.</div>';
    return html;
  }

  /**
   * Gắn khung chat của trang. cfg:
   *   nguon        — 'live' (luồng live) | 'replay' (phiên Replay trang Thử nghiệm); cũng đặt tên khoá nhớ đóng / mở;
   *   where        — chữ «đọc trạng thái ở …» trong ghi chú (vd «nến cuối», «con trỏ Replay»);
   *   summaryLabel — chữ nút tổng hợp (cũng là tin của người dùng);
   *   source()     — nguồn hiện tại {id, digits} hoặc null;
   *   noSource     — lời nhắc khi chưa có nguồn;
   *   beforeSend() — (tuỳ chọn) gọi trước khi gửi, vd dừng phát replay để con trỏ đứng yên.
   */
  function bind(cfg) {
    var key = 'msl.' + cfg.nguon + '.chatOpen';
    var history = [];           // [{role, content}] gửi lại mỗi lượt (backend cũng chỉ giữ 20 tin cuối)
    var historyId = null;       // id nguồn của cuộc trò chuyện — đổi luồng / phiên replay thì bắt đầu cuộc mới
    var statusLoaded = false;

    /** Thêm một tin vào khung: kind = user | bot | note | err (lỗi dùng khung báo lỗi chung .note-error). */
    function add(kind, html) {
      var log = $('#chat-log'), el = document.createElement('div');
      el.className = 'chat-msg ' + (kind === 'err' ? 'note note-error' : 'chat-' + kind);
      el.innerHTML = html;
      log.appendChild(el);
      log.scrollTop = log.scrollHeight;
      return el;
    }

    /** Đang hỏi: khoá gửi, tổng hợp và «Cuộc mới» (câu trả lời về luôn thuộc cuộc trò chuyện đã hỏi). */
    function setBusy(on) {
      ['#chat-send', '#chat-summary', '#chat-new'].forEach(function (s) { $(s).disabled = on; });
    }

    function newChat(note) {
      history = [];
      historyId = null;
      $('#chat-log').innerHTML = '';
      if (note) add('note', esc(note));
    }

    async function send(mode, text) {
      if ($('#chat-send').disabled) return;
      var src = cfg.source();
      if (!src) { add('err', esc(cfg.noSource)); return; }
      if (cfg.beforeSend) cfg.beforeSend();
      if (historyId !== src.id) {
        if (historyId) newChat('Đã đổi nguồn dữ liệu — bắt đầu cuộc mới.');
        historyId = src.id;
      }
      add('user', esc(mode === 'tong_hop' ? cfg.summaryLabel : text).replace(/\n/g, '<br>'));
      var wait = add('bot', '<p class="muted">Đang hỏi mô hình…</p>');
      setBusy(true);
      try {
        var res = await API.llmChat({ nguon: cfg.nguon, nguon_id: src.id, mode: mode, cau_hoi: text, lich_su: history,
          digits: src.digits });
        // ghi nến vào câu hỏi: lượt sau dữ liệu có thể đã sang nến khác, mô hình phân biệt được số cũ / số hiện tại
        var asked = mode === 'tong_hop' ? SUMMARY_TURN : text;
        history = history.concat([{ role: 'user', content: '[nến #' + res.nen + '] ' + asked },
          { role: 'assistant', content: res.tra_loi }]).slice(-MAX_HISTORY);
        wait.remove();
        add('bot', md(res.tra_loi) + meta(res));
      } catch (e) {
        wait.remove();
        add('err', esc(e.message));
      } finally {
        setBusy(false);
      }
    }

    async function loadStatus() {
      if (statusLoaded) return;
      statusLoaded = true;
      try {
        var st = await API.llmStatus();
        $('#chat-model').textContent = st.mo_hinh;
        if (!st.co_khoa) add('err', esc(st.goi_y_khoa));
      } catch (e) {
        statusLoaded = false;
        add('err', 'Không đọc được trạng thái trợ lý: ' + esc(e.message));
      }
    }

    function setOpen(on) {
      $('#chat-panel').hidden = !on;
      $('#chat-toggle').setAttribute('aria-expanded', String(on));
      try { localStorage.setItem(key, on ? '1' : '0'); } catch (e) { /* chế độ riêng tư */ }
      if (on) { loadStatus(); $('#chat-input').focus(); }
    }

    $('#chat-where').textContent = cfg.where;
    $('#chat-summary').textContent = cfg.summaryLabel;
    $('#chat-toggle').addEventListener('click', function () { setOpen($('#chat-panel').hidden); });
    $('#chat-close').addEventListener('click', function () { setOpen(false); });
    $('#chat-summary').addEventListener('click', function () { send('tong_hop', ''); });
    $('#chat-new').addEventListener('click', function () { newChat(null); });
    $('#chat-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var text = $('#chat-input').value.trim();
      if (!text || $('#chat-send').disabled) return;
      $('#chat-input').value = '';
      send('hoi', text);
    });
    $('#chat-input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#chat-form').requestSubmit(); }
    });
    var saved = null;
    try { saved = localStorage.getItem(key); } catch (e) { /* mặc định đóng */ }
    if (saved === '1') setOpen(true);
  }

  MSL.chatPanel = { bind: bind };
})(window.MSL);
