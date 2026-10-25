/* Trang Live MT5 — khung chat «Trợ lý tổng hợp» (docs/plans/plan_tro_ly_tong_hop.md): gửi lệnh tổng hợp / câu hỏi kèm lịch
   sử; backend dựng bản tóm gọn ở nến cuối của luồng và gọi OpenRouter. Hiện câu trả lời (markdown tối giản, đã thoát HTML),
   nến dữ liệu, token, chi phí, số không có trong dữ liệu. Chỉ gọi khi người dùng bấm. */
(function (MSL) {
  'use strict';

  var S = MSL.live.S;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var OPEN_KEY = 'msl.live.chatOpen';
  var MAX_HISTORY = 20;
  var history = [];             // [{role, content}] gửi lại mỗi lượt (backend cũng chỉ giữ 20 tin cuối)
  var historyFeed = null;       // luồng của cuộc trò chuyện — đổi luồng thì bắt đầu cuộc mới
  var conv = 0;                 // số thứ tự cuộc trò chuyện — câu trả lời về sau khi đã sang cuộc mới thì bỏ
  var statusLoaded = false;

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

  /** Thêm một tin vào khung: kind = user | bot | note | err (lỗi dùng khung báo lỗi chung .note-error). */
  function add(kind, html) {
    var log = $('#chat-log'), el = document.createElement('div');
    el.className = 'chat-msg ' + (kind === 'err' ? 'note note-error' : 'chat-' + kind);
    el.innerHTML = html;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function setBusy(on) {
    $('#chat-send').disabled = on;
    $('#chat-summary').disabled = on;
  }

  function newChat(note) {
    conv++;
    history = [];
    historyFeed = S.session ? S.session.sid : null;
    $('#chat-log').innerHTML = '';
    if (note) add('note', esc(note));
  }

  async function send(mode, text) {
    var r = S.session;
    if ($('#chat-send').disabled) return;
    if (!r) { add('err', 'Chưa mở luồng live — chọn hoặc tạo luồng bên trái.'); return; }
    if (historyFeed !== r.sid) newChat(historyFeed ? 'Đã đổi luồng — bắt đầu cuộc mới.' : null);
    var question = mode === 'tong_hop' ? 'Tổng hợp trạng thái ở nến cuối.' : text;
    add('user', esc(question).replace(/\n/g, '<br>'));
    var wait = add('bot', '<p class="muted">Đang hỏi mô hình…</p>');
    var mine = conv;
    setBusy(true);
    try {
      var res = await API.llmChat({ feed_id: r.sid, mode: mode, cau_hoi: text, lich_su: history, digits: S.digits });
      if (mine !== conv) return;
      // ghi nến vào câu hỏi: lượt sau dữ liệu đã sang nến mới, mô hình phân biệt được số cũ / số hiện tại
      history = history.concat([{ role: 'user', content: '[nến #' + res.nen + '] ' + question },
        { role: 'assistant', content: res.tra_loi }]).slice(-MAX_HISTORY);
      wait.remove();
      add('bot', md(res.tra_loi) + meta(res));
    } catch (e) {
      if (mine !== conv) return;
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
    try { localStorage.setItem(OPEN_KEY, on ? '1' : '0'); } catch (e) { /* chế độ riêng tư */ }
    if (on) { loadStatus(); $('#chat-input').focus(); }
  }

  function bind() {
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
    try { saved = localStorage.getItem(OPEN_KEY); } catch (e) { /* mặc định đóng */ }
    if (saved === '1') setOpen(true);
  }

  document.addEventListener('DOMContentLoaded', bind);
})(window.MSL);
