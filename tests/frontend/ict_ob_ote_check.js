/* Kiểm hàm thuần frontend/js/algos/ict_ob_ote_view.js (lõi 0.5.0) bằng node (gọi từ test_ict_ob_ote_display.py).
 *
 *   node ict_ob_ote_check.js hand          kịch bản dựng tay: nét / chữ theo kết cục OB, OTE đang chờ (có / chưa có vùng),
 *                                          OTE vừa vào, chữ giải thích, «Đang theo dõi»
 *   node ict_ob_ote_check.js real <file>   dữ liệu lõi thật (JSON do pytest xuất): vùng OTE = timeline tại con trỏ, OB mở gần
 *                                          nhất = cột ob_*, replay prefix = lọc theo con trỏ, mọi đối tượng có tooltip
 * In ra JSON {checks: n, failures: [...]}.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const REPO = path.resolve(__dirname, '..', '..');
const sandbox = { window: { MSL: {} } };
vm.createContext(sandbox);
for (const f of ['ict_structure_view.js', 'ict_ob_ote_view.js']) {
  vm.runInContext(fs.readFileSync(path.join(REPO, 'frontend', 'js', 'algos', f), 'utf8'), sandbox, { filename: f });
}
const V = sandbox.window.MSL.ictView;
const OB = sandbox.window.MSL.ictObOteView;

let checks = 0;
const failures = [];
function ok(cond, msg, extra) {
  checks++;
  if (!cond) failures.push(msg + (extra !== undefined ? ' — ' + JSON.stringify(extra) : ''));
}
function eq(a, b, msg) { ok(JSON.stringify(a) === JSON.stringify(b), msg, { got: a, want: b }); }
const J = (x) => JSON.parse(JSON.stringify(x));
const ident = (i) => i;
const ALL = { ob: true, ote: true };

function draw(M, close) { return J(OB.drawing(M, OB.select(M, { close: close }), ident, ALL)); }
function labelOf(dr, id) {
  const s = dr.segments.find((x) => x.id === id && x.label);
  return s ? s.label.text : null;
}

// ------------------------------------------------------------------ kịch bản dựng tay

function runHand() {
  const evs = [];
  function ev(type, bar, conf, price, details, ref, dir, suffix) {
    const id = 'ict:' + type + '@' + bar + '>' + conf + (suffix ? ':' + suffix : '');
    evs.push({ event_id: id, structure_type: type, event_bar_index: bar, confirmed_bar_index: conf, price: price,
      direction: dir, reference_event_id: ref || null, reason_code: null, details: details || {} });
    return id;
  }
  const obd = (lo, hi, d, k) => ({ chieu: 'up', lo: lo, hi: hi, mean_threshold: (lo + hi) / 2, nen_dau: d - 2, nen_cuoi: d - 1,
    so_nen: 2, bien_the: 'than_chuoi', neo: 'shift', nen_neo: d, nen_xac_nhan: k, han_nen: d + 96, basis: [] });
  const sh = ev('SHIFT_UP', 4, 4, 101, { chieu: 'up', muc_bi_quet: 100, swept: [] }, null, 'up');
  const a = ev('ORDER_BLOCK_UP', 3, 4, 100.5, obd(100, 101, 4, 4), sh, 'up', '4');                 // còn mở
  const b = ev('ORDER_BLOCK_UP', 6, 8, 102.5, obd(102, 103, 8, 8), sh, 'up', '8');                 // chạm ở 10
  ev('OB_TAP_UP', 10, 10, 103, { chieu_ob: 'up', lo: 102, hi: 103, so_nen_tu_tao: 2 }, b, 'up', '6.8');
  const c = ev('ORDER_BLOCK_UP', 11, 13, 104.5, obd(104, 105, 13, 13), sh, 'up', '13');            // hỏng ở 15
  ev('OB_FAIL_UP', 15, 15, 103.8, { chieu_ob: 'up', lo: 104, hi: 105 }, c, 'up', '11.13');
  ev('OTE_ENTRY_UP', 18, 18, 101.2, { chieu: 'up', x: 99, h: 105, vung_lo: 100.26, vung_hi: 101.28, nen_neo: 4, do_sau: 0.66,
    nhip_atr: 3.0, ket_cuc: 'entry' }, sh, 'up', '4');
  const sh2 = ev('SHIFT_DOWN', 20, 20, 104, { chieu: 'down', muc_bi_quet: 106, swept: [] }, null, 'down');
  const tl = [];
  for (let i = 0; i <= 22; i++) {
    tl.push({ bar_index: i, dealing_hi: 110, atr: 1, ob_up_hi: null, ob_up_lo: null, ob_down_hi: null, ob_down_lo: null,
      ote_dir: i >= 20 ? 'down' : null, ote_neo: i >= 20 ? 20 : null, ote_x: i >= 20 ? 107 : null, ote_h: i >= 20 ? (i === 22 ? 101 : 103) : null,
      ote_lo: i === 22 ? 104.72 : null, ote_hi: i === 22 ? 105.74 : null });
  }
  const ps = { ote: { tu: 0.62, den: 0.79, dang_cho: null }, order_block: { dang_mo: [] } };
  // con trỏ 21: nhịp chờ chưa đủ lớn → chỉ gốc nhịp; OB a mở, b chạm, c hỏng; OTE vừa vào (18)
  let M = V.buildModel(evs, tl, ps, 21, 2);
  const C = OB.collect(M);
  eq([C.obs.length, Object.keys(C.ends).length, C.otes.length], [3, 2, 1], 'collect gom đủ OB / kết cục / OTE, không gom SHIFT');
  ok(OB.collect(M) === C, 'collect tính một lần cho mỗi mô hình');
  let dr = draw(M, 104);
  eq(labelOf(dr, 'ob:' + a), 'OB ↑', 'OB còn mở: chữ không có kết cục');
  eq(labelOf(dr, 'ob:' + b), 'OB ↑ · chạm', 'OB đã chạm');
  eq(labelOf(dr, 'ob:' + c), 'OB ↑ · hỏng', 'OB hỏng');
  const bx = (id) => dr.boxes.find((x) => x.id === id);
  eq([bx('ob:' + a).borderStyle, bx('ob:' + b).borderStyle, bx('ob:' + c).borderStyle], ['solid', 'dashed', 'dotted'],
    'nét viền theo kết cục');
  eq([bx('ob:' + b).l1, bx('ob:' + b).l2], [5.55, 10.45], 'hộp OB từ nến đầu tới nến chạm');
  eq(bx('ob:' + a).l2, 26, 'OB còn mở kéo tới con trỏ + ext');
  ok(!dr.boxes.some((x) => x.id === 'ote:pending'), 'nhịp chưa đủ lớn → không có hộp OTE');
  eq(labelOf(dr, 'ote:pending'), 'gốc nhịp · chờ nhịp đủ lớn', 'chỉ có gốc nhịp');
  ok(dr.boxes.some((x) => x.id.indexOf('ote:ict:OTE_ENTRY_UP') === 0), 'OTE vừa vào có hộp');
  ok(dr.segments.some((x) => x.label && x.label.text === 'OTE ↑ · vào 66%'), 'chữ OTE vừa vào ghi độ sâu');
  // con trỏ 22: vùng OTE giảm có hiệu lực, gốc = SHIFT_DOWN #20
  M = V.buildModel(evs, tl, ps, 22, 2);
  dr = draw(M, 103);
  const ote = dr.boxes.find((x) => x.id === 'ote:pending');
  eq(ote && [ote.l1, ote.p1, ote.p2], [19.55, 104.72, 105.74], 'hộp OTE đang chờ: từ nến shift, vùng = timeline');
  eq(labelOf(dr, 'ote:pending'), 'OTE ↓ 62–79%', 'chữ OTE đang chờ');
  ok(OB.info(M, 'ote:pending')[0].head.indexOf('OTE giảm đang chờ') === 0, 'tooltip OTE đang chờ');
  ok(OB.info(M, 'ob:' + b)[0].body.indexOf('Chạm lần đầu ở nến #10') >= 0, 'tooltip OB ghi kết cục');
  // nhân quả: con trỏ 9 chưa thấy OB c, OB b chưa chạm
  M = V.buildModel(evs, tl, ps, 9, 2);
  dr = draw(M, 104);
  ok(!dr.boxes.some((x) => x.id === 'ob:' + c), 'chưa thấy OB xác nhận sau con trỏ');
  eq(labelOf(dr, 'ob:' + b), 'OB ↑', 'kết cục sau con trỏ chưa hiện');
  // kết cục cũ hơn `recent`: vẫn giữ kết cục gần nhất (OB mỗi chiều, OTE) như shift gần nhất — chart không bao giờ trống
  M = V.buildModel(evs, tl, ps, 22, 2);
  const old = J(OB.drawing(M, OB.select(M, { close: 103, recent: 1 }), ident, ALL));
  ok(old.boxes.some((x) => x.id === 'ob:' + c) && !old.boxes.some((x) => x.id === 'ob:' + b),
    'recent = 1: giữ OB kết thúc gần nhất (hỏng ở #15), bỏ OB cũ hơn (chạm ở #10)');
  ok(old.boxes.some((x) => x.id.indexOf('ote:ict:OTE_ENTRY_UP') === 0), 'recent = 1: giữ OTE vào gần nhất (#18)');
  // tắt lớp
  eq(J(OB.drawing(M, OB.select(M, {}), ident, { ob: false, ote: false })).boxes.length, 0, 'tắt cả hai lớp → không vẽ');
  // chữ
  for (const e of evs) {
    if (OB.isType(e.structure_type)) ok(typeof OB.eventText(e, 2) === 'string', 'có câu giải thích ' + e.structure_type);
  }
  eq(OB.eventText(evs[0], 2), null, 'SHIFT không phải loại OB / OTE');
  const lines = OB.pendingLines({ order_block: { dang_mo: [{ chieu: 'up', lo: 1, hi: 2, nen_neo: 5, con_lai_nen: 3, can: 'x' }] },
    ote: { dang_cho: { chieu: 'down', x: 3, h: 1, vung_hieu_luc: false, con_lai_nen: 9, can: 'y' } } }, 2);
  eq(lines.length, 2, 'Đang theo dõi: một dòng OB + một dòng OTE');
  ok(lines[0].text.indexOf('(SHIFT #5,') > 0, 'OB neo shift ghi SHIFT #', lines[0].text);
  const ld = OB.pendingLines({ order_block: { neo: 'displacement', dang_mo: [{ chieu: 'up', lo: 1, hi: 2, nen_neo: 5, con_lai_nen: 3, can: 'x' }] } }, 2);
  ok(ld[0].text.indexOf('(nến #5,') > 0, 'OB neo displacement ghi nến #', ld[0].text);
  eq([OB.meta('OB_EXPIRED').end, OB.meta('ORDER_BLOCK_UP').end, OB.meta('OTE_ENTRY_DOWN').group, OB.meta('SHIFT_UP')],
    ['expired', null, 'ote', null], 'meta: nhóm / kết cục theo loại');
  eq(OB.pendingLines({}, 2), [], 'kết quả cũ → không có dòng');
}

// ------------------------------------------------------------------ dữ liệu lõi thật

function runReal(file) {
  const D = JSON.parse(fs.readFileSync(file, 'utf8'));
  let oteBoxes = 0, obOpen = 0;
  for (const P of D.prefixes) {
    const c = P.cursor, tlc = P.timeline[P.timeline.length - 1];
    const Mf = V.buildModel(D.full.events, D.full.timeline, P.pending, c, D.digits);
    const Mp = V.buildModel(P.events, P.timeline, P.pending, c, D.digits);
    const close = P.close;
    const df = draw(Mf, close), dp = draw(Mp, close);
    eq(dp, df, 'replay prefix = toàn bộ sự kiện lọc theo con trỏ #' + c);
    const ote = df.boxes.find((x) => x.id === 'ote:pending');
    if (tlc.ote_lo !== null) {
      oteBoxes++;
      eq(ote && [ote.p1, ote.p2], [tlc.ote_lo, tlc.ote_hi], 'hộp OTE = vùng timeline tại #' + c);
    } else {
      ok(!ote, 'không có vùng OTE ở timeline → không có hộp #' + c);
    }
    const sel = J(OB.select(Mf, { close: close }));
    const openHi = sel.obs.filter((o) => !o.end && o.dir === 'up').map((o) => o.ev.details.hi);
    const openLo = sel.obs.filter((o) => !o.end && o.dir === 'down').map((o) => o.ev.details.lo);
    if (tlc.ob_up_hi !== null) { obOpen++; ok(openHi.indexOf(tlc.ob_up_hi) >= 0, 'OB tăng mở gần nhất = timeline #' + c, openHi); }
    else ok(!openHi.length, 'không có OB tăng mở ở timeline → không vẽ #' + c);
    if (tlc.ob_down_lo !== null) ok(openLo.indexOf(tlc.ob_down_lo) >= 0, 'OB giảm mở gần nhất = timeline #' + c, openLo);
    else ok(!openLo.length, 'không có OB giảm mở ở timeline → không vẽ #' + c);
    for (const o of sel.obs) ok(o.ev.confirmed_bar_index <= c && (!o.end || o.end.confirmed_bar_index <= c), 'nhân quả OB #' + c);
    const ids = new Set(df.boxes.map((x) => x.id));
    for (const id of ids) {
      const info = OB.info(Mf, id);
      ok(info && info.length && info[0].head, 'tooltip cho ' + id);
    }
  }
  ok(oteBoxes > 0 && obOpen > 0, 'dữ liệu có cả vùng OTE và OB mở ở các con trỏ', { oteBoxes: oteBoxes, obOpen: obOpen });
  for (const e of D.full.events) {
    if (OB.isType(e.structure_type)) ok(typeof OB.eventText(e, D.digits) === 'string', 'câu giải thích ' + e.event_id);
  }
}

const mode = process.argv[2];
try {
  if (mode === 'hand') runHand();
  else if (mode === 'real') runReal(process.argv[3]);
  else failures.push('chế độ lạ: ' + mode);
} catch (err) {
  failures.push('lỗi: ' + (err && err.stack ? err.stack : err));
}
process.stdout.write(JSON.stringify({ checks: checks, failures: failures }));
