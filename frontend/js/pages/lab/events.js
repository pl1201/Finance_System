/* Trang Thử nghiệm — bảng sự kiện và panel chi tiết sự kiện được chọn. */
(function (MSL) {
  'use strict';

  var L = MSL.lab;
  var $ = MSL.dom.$;
  var esc = MSL.dom.esc;
  var fmtIso = MSL.format.fmtIso;
  var S = L.S;

  /** Panel chi tiết sự kiện được chọn — nội dung do plugin của thuật toán sinh (hook `eventDetail`). */
  function renderEventDetail(e) {
    var box = $('#event-detail');
    if (!box) return;
    var html = e ? MSL.algos.callFor(e.algorithm, 'eventDetail', e, S) : null;
    if (!html) { box.hidden = true; box.innerHTML = ''; return; }
    box.innerHTML = html;
    box.hidden = false;
  }

  function renderEvents(events) {
    var tbody = $('#events-table tbody');
    var filter = ($('#event-filter').value || '').trim().toUpperCase();
    var list = (events || []).filter(function (e) {
      var sid = ((e.details && (e.details.setup_id || e.details.candidate_id)) || '').toUpperCase();
      return !filter || e.structure_type.indexOf(filter) >= 0 || (e.reason_code || '').indexOf(filter) >= 0 ||
        sid.indexOf(filter) >= 0;
    });
    $('#event-count').textContent = list.length + ' / ' + (events || []).length + ' sự kiện';
    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="empty-cell">' +
        ((events && events.length) ? 'Không có sự kiện khớp bộ lọc.' : 'Chưa có sự kiện.') + '</td></tr>';
      return;
    }
    var d = S.digits;
    tbody.innerHTML = list.slice(0, 3000).map(function (e, i) {
      return '<tr data-ev="' + i + '" tabindex="' + (i === 0 ? 0 : -1) + '" aria-selected="false">' +
        '<td class="num">' + (i + 1) + '</td>' +
        '<td><span class="badge b-' + esc(e.structure_type) + '">' + esc(e.structure_type) + '</span></td>' +
        '<td class="num">' + Number(e.price).toFixed(d) + '</td>' +
        '<td class="num">' + e.event_bar_index + '</td>' +
        '<td class="mono">' + fmtIso(e.event_time) + '</td>' +
        '<td class="num">' + e.confirmed_bar_index + '</td>' +
        '<td class="mono">' + fmtIso(e.confirmed_at) + '</td>' +
        '<td class="num">' + e.confirmation_lag_bars + '</td>' +
        '<td class="mono">' + esc(e.reason_code) + '</td>' +
        '<td class="mono">' + esc(e.reference_event_id || '—') +
          ((e.details && (e.details.setup_id || e.details.candidate_id))
            ? '<br><span class="muted">' + esc(e.details.setup_id ? 'setup ' + e.details.setup_id : 'ứng viên ' + e.details.candidate_id) + '</span>'
            : '') + '</td>' +
        '</tr>';
    }).join('');
    if (list.length > 3000) {
      tbody.innerHTML += '<tr><td colspan="10" class="empty-cell">Hiển thị 3000 dòng đầu; xuất CSV để xem đầy đủ.</td></tr>';
    }
    Array.prototype.forEach.call(tbody.querySelectorAll('tr[data-ev]'), function (tr) {
      tr.addEventListener('click', function () {
        Array.prototype.forEach.call(tbody.querySelectorAll('tr'), function (r) {
          r.classList.remove('selected');
          if (r.hasAttribute('data-ev')) { r.setAttribute('tabindex', '-1'); r.setAttribute('aria-selected', 'false'); }
        });
        tr.classList.add('selected');
        tr.setAttribute('tabindex', '0');
        tr.setAttribute('aria-selected', 'true');
        var ev = list[parseInt(tr.getAttribute('data-ev'), 10)];
        renderEventDetail(ev);
        var own = MSL.algos.forAlgorithm(ev.algorithm);
        if (own && own.selectEventOnChart) {
          S.selectedEventId = ev.event_id;   // vd DC: hiện điểm xác nhận của pivot đang chọn
          L.applyChartEvents();
        }
        S.chart.focusEvent(ev);
      });
    });
  }

  L.renderEventDetail = renderEventDetail;
  L.renderEvents = renderEvents;
})(window.MSL);
