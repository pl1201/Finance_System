/* Kiểm hàm thuần frontend/js/algos/ict_nhan_dien_view.js (lõi 0.6.0) bằng node (gọi từ test_ict_nhan_dien_display.py).
 *
 *   node ict_nhan_dien_check.js hand          kịch bản dựng tay: dải trạng thái, đoạn, dòng trạng thái, hộp range (đang có /
 *                                             đã qua), tooltip, câu giải thích, «Đang theo dõi», kết quả cũ
 *   node ict_nhan_dien_check.js real <file>   dữ liệu lõi thật (JSON do pytest xuất): dải = cột nd_trang_thai, replay prefix =
 *                                             lọc theo con trỏ, hộp range = biên timeline, mọi đối tượng có tooltip
 * In ra JSON {checks: n, failures: [...]}.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const REPO = path.resolve(__dirname, '..', '..');
const sandbox = { window: { MSL: {} } };
vm.createContext(sandbox);
for (const f of ['ict_structure_view.js', 'ict_nhan_dien_view.js']) {
  vm.runInContext(fs.readFileSync(path.join(REPO, 'frontend', 'js', 'algos', f), 'utf8'), sandbox, { filename: f });
}
const V = sandbox.window.MSL.ictView;
const ND = sandbox.window.MSL.ictNdView;

let checks = 0;
const failures = [];
function ok(cond, msg, extra) {
  checks++;
  if (!cond) failures.push(msg + (extra !== undefined ? ' — ' + JSON.stringify(extra) : ''));
}
function eq(a, b, msg) { ok(JSON.stringify(a) === JSON.stringify(b), msg, { got: a, want: b }); }
const J = (x) => JSON.parse(JSON.stringify(x));
const ident = (i) => i;

// ------------------------------------------------------------------ kịch bản dựng tay

function runHand() {
  // #0–#4 chưa đủ nến · #5–#9 trend ↑ (từ #5) · #10–#19 range [100, 102] (từ #10) · #20–#24 nhiễu (từ #20)
  const tl = [];
  for (let i = 0; i <= 24; i++) {
    const st = i < 5 ? null : i < 10 ? 'trend_len' : i < 20 ? 'range' : 'nhieu';
    tl.push({ bar_index: i, dealing_hi: 110, atr: 1, nd_trang_thai: st, nd_tu: st === null ? null : i < 10 ? 5 : i < 20 ? 10 : 20,
      nd_range_tu: st === 'range' ? i - 7 : null,   // cửa sổ 8 nến kết thúc ở nến đó (lúc nhận ra ở #10: từ #3)
      nd_range_hi: st === 'range' ? 102 : null, nd_range_lo: st === 'range' ? (i < 15 ? 100 : 100.5) : null });
  }
  const evs = [
    { event_id: 'ict:STATE_TREND_UP@5>6', structure_type: 'STATE_TREND_UP', event_bar_index: 5, confirmed_bar_index: 6, price: 1,
      direction: 'up', details: { trang_thai: 'trend_len', cua_so_nen: 32, er: 0.41, giu_nen: 2, thu_tu_cung_chieu: true } },
    { event_id: 'ict:STATE_RANGE@10>11', structure_type: 'STATE_RANGE', event_bar_index: 10, confirmed_bar_index: 11, price: 1,
      direction: null, details: { trang_thai: 'range', cua_so_nen: 8, bien_tren: 102, bien_duoi: 100, rong_atr: 2, er: 0.1,
        cham_tren: [3, 9], cham_duoi: [4, 10], dung_sai: 0.3, giu_nen: 2 } },
    { event_id: 'ict:STATE_CHOP@20>21', structure_type: 'STATE_CHOP', event_bar_index: 20, confirmed_bar_index: 21, price: 1,
      direction: null, details: { trang_thai: 'nhieu', cua_so_nen: 32, er: 0.12, giu_nen: 2 } }
  ];
  // con trỏ 15: đang range — hộp từ nến đầu cửa sổ lúc nhận ra (nd_range_tu ở #10 = #3) tới con trỏ + 5, biên tại con trỏ
  let M = V.buildModel(evs, tl, null, 15, 2);
  ok(ND.has(M), 'có cột nd_* → có lớp trạng thái');
  const bars = J(ND.bandBars(M, ident));
  eq(bars.length, 16, 'dải: một ô mỗi nến ≤ con trỏ');
  eq([bars[0].text, bars[5].text, bars[10].text], ['', 'trend ↑', 'range'], 'chữ của dải theo trạng thái');
  eq(J(ND.episodes(M)).map((e) => [e.key, e.from, e.to]), [['trend_len', 5, 9], ['range', 10, 15]], 'đoạn trạng thái ≤ con trỏ');
  let dr = J(ND.drawing(M, ident));
  eq(dr.boxes.map((b) => [b.id, b.l1, b.l2, b.p1, b.p2, b.borderStyle]), [['nd:range:10', 2.55, 20, 100.5, 102, 'dashed']],
    'hộp range đang có: từ đầu cửa sổ tới con trỏ + 5, biên tại con trỏ');
  ok(ND.statusAt(M, 15).text.indexOf('range biên rõ [100.50 – 102.00] · 6 nến (từ #10)') > 0, 'dòng trạng thái', ND.statusAt(M, 15).text);
  ok(ND.statusAt(M, 7).text.indexOf('trend lên') > 0 && ND.statusAt(M, 2).key === null, 'dòng trạng thái theo nến rê / chưa đủ nến');
  const tip = ND.info(M, 'nd:range:10')[0];
  ok(tip.head.indexOf('range biên rõ · #10 → #15 (đang có)') > 0 && tip.body.indexOf('chạm biên trên 2 lần') > 0, 'tooltip hộp range', tip);
  ok(ND.info(M, 'nd:state:6')[0].body.indexOf('thứ tự cấu trúc cùng chiều') > 0, 'tooltip dải: trend ghi thứ tự cấu trúc');
  // con trỏ 24: range đã qua (chấm, dừng ở #19), đang nhiễu
  M = V.buildModel(evs, tl, null, 24, 2);
  dr = J(ND.drawing(M, ident));
  eq(dr.boxes.map((b) => [b.l2, b.borderStyle]), [[19.45, 'dotted']], 'range gần nhất đã qua vẫn hiện (chấm, dừng ở nến cuối đoạn)');
  ok(dr.segments.some((s) => s.label && s.label.text === 'Range (đã qua)'), 'nhãn range đã qua');
  // hai range đã qua, con trỏ không ở range → chỉ vẽ range gần nhất
  const tl2 = tl.map((p) => Object.assign({}, p, p.bar_index >= 20 && p.bar_index < 23
    ? { nd_trang_thai: 'range', nd_tu: 20, nd_range_tu: 14, nd_range_hi: 103, nd_range_lo: 101 } : {}));
  M = V.buildModel(evs, tl2, null, 24, 2);
  eq(J(ND.drawing(M, ident)).boxes.map((b) => b.id), ['nd:range:20'], 'không ở range: chỉ một range đã qua (gần nhất)');
  // nhân quả: con trỏ 8 chưa thấy range
  M = V.buildModel(evs, tl, null, 8, 2);
  eq(J(ND.drawing(M, ident)).boxes.length, 0, 'con trỏ trước range: không có hộp');
  // chữ
  for (const e of evs) ok(typeof ND.eventText(e, 2) === 'string', 'câu giải thích ' + e.structure_type);
  eq(ND.eventText({ structure_type: 'SHIFT_UP' }, 2), null, 'không phải STATE_*');
  eq(ND.meta('STATE_SQUEEZE').state, 'nen', 'meta theo loại');
  const lines = ND.pendingLines({ nhan_dien: { trang_thai: 'range', tu_nen: 10, chi_tiet: evs[1].details,
    ung_vien: { trang_thai: 'nhieu', tu_nen: 15, so_nen: 1, can: 2 } } }, 2);
  eq(lines.map((l) => l.kind), ['state', 'pending'], '«Đang theo dõi»: trạng thái + ứng viên chờ đủ nến');
  ok(lines[1].text.indexOf('1/2 nến') > 0, 'ứng viên ghi số nến đã giữ', lines[1].text);
  // kết quả cũ (0.5.0, chưa có cột nd_*)
  const old = V.buildModel([], tl.map((p) => ({ bar_index: p.bar_index, dealing_hi: 1 })), null, 10, 2);
  ok(!ND.has(old) && ND.statusAt(old, 10) === null && ND.pendingLines({}, 2).length === 0, 'kết quả cũ → không có lớp');
}

// ------------------------------------------------------------------ dữ liệu lõi thật

function runReal(file) {
  const D = JSON.parse(fs.readFileSync(file, 'utf8'));
  let ranges = 0;
  for (const P of D.prefixes) {
    const c = P.cursor, tlc = P.timeline[P.timeline.length - 1];
    const Mf = V.buildModel(D.full.events, D.full.timeline, P.pending, c, D.digits);
    const Mp = V.buildModel(P.events, P.timeline, P.pending, c, D.digits);
    const bars = J(ND.bandBars(Mf, ident)), dr = J(ND.drawing(Mf, ident));
    eq(J(ND.bandBars(Mp, ident)), bars, 'replay prefix = toàn bộ lọc theo con trỏ (dải) #' + c);
    eq(J(ND.drawing(Mp, ident)), dr, 'replay prefix = toàn bộ lọc theo con trỏ (hộp) #' + c);
    const s = ND.statusAt(Mf, c);
    eq(s.key, tlc.nd_trang_thai, 'dòng trạng thái = cột timeline #' + c);
    const live = dr.boxes.filter((b) => b.borderStyle === 'dashed');
    if (tlc.nd_trang_thai === 'range') {
      ranges++;
      eq(live.map((b) => [b.p1, b.p2]), [[tlc.nd_range_lo, tlc.nd_range_hi]], 'hộp range đang có = biên timeline #' + c);
      const first = P.timeline.find((p) => p.nd_trang_thai === 'range' && p.nd_tu === tlc.nd_tu);
      eq(live[0].l1, first.nd_range_tu - 0.45, 'mép trái hộp = nến đầu cửa sổ lõi lúc nhận ra #' + c);
    } else {
      eq(live.length, 0, 'không range ở con trỏ → không hộp nét đứt #' + c);
    }
    for (const b of bars) {
      if (b.l % 97 === 0) ok(ND.info(Mf, b.id)[0].head, 'tooltip dải ' + b.id);
    }
    eq(ND.pendingLines(P.pending, D.digits)[0].kind, 'state', '«Đang theo dõi» có dòng trạng thái #' + c);
  }
  ok(ranges > 0, 'dữ liệu có con trỏ đang range', { ranges: ranges });
  for (const e of D.full.events) {
    if (ND.isType(e.structure_type)) ok(typeof ND.eventText(e, D.digits) === 'string', 'câu giải thích ' + e.event_id);
  }
}

const mode = process.argv[2];
try {
  if (mode === 'hand') runHand();
  else if (mode === 'real') runReal(process.argv[3]);
  else throw new Error('mode?');
} catch (err) {
  failures.push('LỖI: ' + (err && err.stack || err));
}
process.stdout.write(JSON.stringify({ checks: checks, failures: failures }));
