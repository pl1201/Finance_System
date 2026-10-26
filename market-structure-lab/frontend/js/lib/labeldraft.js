/* Giữ bộ nhãn đang soạn giữa các lần tải trang.
 *
 * Nháp được lưu trong bộ nhớ trình duyệt (localStorage), tách riêng THEO TỪNG
 * DATASET: `bar_index` chỉ có nghĩa trong đúng dataset sinh ra nó, nên nháp của
 * XAUUSD H1 không bao giờ được mang sang EURUSD.
 *
 * Đây KHÔNG phải nơi lưu chính thức. Bộ nhãn chỉ thực sự vào kho khi người dùng
 * bấm Lưu / Cập nhật (ghi xuống SQLite qua API). Nháp chỉ để không mất công sức
 * khi lỡ tải lại trang hay đóng tab.
 *
 * localStorage có thể ném lỗi (cửa sổ riêng tư, chặn site data) hoặc trả về
 * rỗng — mọi truy cập đều bọc try/catch và trang phải chạy được khi không có nó.
 */
(function (global) {
  'use strict';

  var PREFIX = 'msl.labeldraft.v1.';
  var META_KEY = 'msl.labelmeta.v1';

  function store() {
    try {
      var s = global.localStorage;
      // Thử ghi một khoá tạm: một số trình duyệt có localStorage nhưng chặn ghi.
      s.setItem(PREFIX + '__probe', '1');
      s.removeItem(PREFIX + '__probe');
      return s;
    } catch (e) {
      return null;
    }
  }

  var available = !!store();

  function read(datasetId) {
    if (!datasetId) return null;
    var s = store();
    if (!s) return null;
    try {
      var raw = s.getItem(PREFIX + datasetId);
      if (!raw) return null;
      var obj = JSON.parse(raw);
      if (!obj || !Array.isArray(obj.labels)) return null;
      if (obj.auto && !Array.isArray(obj.auto.items)) obj.auto = null;
      return obj;
    } catch (e) {
      return null;
    }
  }

  function write(datasetId, state) {
    if (!datasetId) return false;
    var s = store();
    if (!s) return false;
    try {
      // Không còn nhãn và không còn đề xuất đang duyệt -> xoá hẳn cho sạch.
      var hasAuto = !!(state.auto && state.auto.items && state.auto.items.length);
      var undo = (state.undo || []).slice(-40);   // lịch sử hoàn tác, giữ qua tải lại trang
      if ((!state.labels || !state.labels.length) && !hasAuto && !undo.length) {
        s.removeItem(PREFIX + datasetId);
        return true;
      }
      s.setItem(PREFIX + datasetId, JSON.stringify({
        dataset_id: datasetId,
        labels: state.labels,
        annotator: state.annotator || '',
        version: state.version || '1',
        rubric_vi: state.rubric_vi || '',
        label_set_id: state.label_set_id || null,
        dirty: !!state.dirty,
        // Phiên duyệt auto label đang dở (đề xuất + trạng thái chấp nhận/bỏ).
        auto: hasAuto ? state.auto : null,
        undo: undo,
        saved_at: new Date().toISOString()
      }));
      return true;
    } catch (e) {
      return false;   // hết dung lượng hoặc bị chặn — không làm hỏng luồng gán nhãn
    }
  }

  function clear(datasetId) {
    var s = store();
    if (!s || !datasetId) return;
    try { s.removeItem(PREFIX + datasetId); } catch (e) { /* bỏ qua */ }
  }

  /** Danh sách dataset khác đang còn nháp chưa lưu, để nhắc người dùng. */
  function otherDirty(exceptDatasetId) {
    var s = store();
    if (!s) return [];
    var out = [];
    try {
      for (var i = 0; i < s.length; i++) {
        var k = s.key(i);
        if (!k || k.indexOf(PREFIX) !== 0) continue;
        var id = k.slice(PREFIX.length);
        if (id === exceptDatasetId || id === '__probe') continue;
        var obj = JSON.parse(s.getItem(k) || 'null');
        if (obj && obj.dirty && obj.labels && obj.labels.length) {
          out.push({ dataset_id: id, n: obj.labels.length });
        }
      }
    } catch (e) { /* bỏ qua */ }
    return out;
  }

  /** Dataset đang làm việc, để mở lại trang là thấy đúng nháp cũ. */
  function lastDataset() {
    var s = store();
    if (!s) return '';
    try { return (JSON.parse(s.getItem(META_KEY) || '{}') || {}).dataset_id || ''; }
    catch (e) { return ''; }
  }

  function setLastDataset(datasetId) {
    var s = store();
    if (!s) return;
    try {
      var meta = JSON.parse(s.getItem(META_KEY) || '{}') || {};
      meta.dataset_id = datasetId || '';
      s.setItem(META_KEY, JSON.stringify(meta));
    } catch (e) { /* bỏ qua */ }
  }

  function lastAnnotator() {
    var s = store();
    if (!s) return '';
    try { return (JSON.parse(s.getItem(META_KEY) || '{}') || {}).annotator || ''; }
    catch (e) { return ''; }
  }

  function setLastAnnotator(name) {
    var s = store();
    if (!s) return;
    try {
      var meta = JSON.parse(s.getItem(META_KEY) || '{}') || {};
      meta.annotator = name || '';
      s.setItem(META_KEY, JSON.stringify(meta));
    } catch (e) { /* bỏ qua */ }
  }

  /**
   * Hỏi lại khi đóng tab / tải lại trang mà nháp chưa lưu.
   * `isDirty` là hàm trả về true khi còn nhãn chưa lưu.
   */
  function guardUnload(isDirty) {
    global.addEventListener('beforeunload', function (e) {
      var dirty = false;
      try { dirty = !!isDirty(); } catch (err) { dirty = false; }
      if (!dirty) return undefined;
      // Trình duyệt hiện đại hiện thông điệp chuẩn của chúng, không dùng chuỗi này.
      e.preventDefault();
      e.returnValue = '';
      return '';
    });
  }

  global.LabelDraft = {
    available: available,
    read: read,
    write: write,
    clear: clear,
    otherDirty: otherDirty,
    lastAnnotator: lastAnnotator,
    setLastAnnotator: setLastAnnotator,
    lastDataset: lastDataset,
    setLastDataset: setLastDataset,
    guardUnload: guardUnload
  };
})(window);
