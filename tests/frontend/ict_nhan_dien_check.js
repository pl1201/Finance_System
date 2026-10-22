/* Kiểm hàm thuần frontend/js/algos/ict_nhan_dien_view.js (lõi 0.6.0) bằng node (gọi từ test_ict_nhan_dien_display.py).
 *
 *   node ict_nhan_dien_check.js hand          kịch bản dựng tay: dải trạng thái, đoạn, dòng trạng thái, hộp range (đang có /
 *                                             đã qua), khoảng giá + xác suất chạm (kèm điểm thật), tooltip, câu giải thích,
 *                                             «Đang theo dõi», ô thống kê, kết quả cũ
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
  const ST = { state: true };
  ok(ND.statusAt(M, 15, ST).text.indexOf('range biên rõ [100.50 – 102.00] · 6 nến (từ #10)') > 0, 'dòng trạng thái', ND.statusAt(M, 15, ST).text);
  ok(ND.statusAt(M, 7, ST).text.indexOf('trend lên') > 0 && ND.statusAt(M, 2, ST).key === null, 'dòng trạng thái theo nến rê / chưa đủ nến');
  ok(ND.statusAt(M, 15, {}) === null, 'tắt cả hai lớp → không có hàng 3');
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
  // ---- khoảng giá + xác suất chạm (lớp ict_nd_band): con trỏ 22, tầm 1h = 4 nến, 4h = 16 nến
  const tlb = tl.map((p) => Object.assign({}, p, p.bar_index === 22 ? {
    nd_1h_lo80: 99, nd_1h_hi80: 103, nd_1h_lo50: 100, nd_1h_hi50: 102, nd_4h_lo80: 97, nd_4h_hi80: 105, nd_4h_lo50: 99,
    nd_4h_hi50: 103, liq_above: 104, nd_p_tren_1h: 0.12, nd_p_tren_4h: 0.4, liq_below: null } : {}));
  const ps = { nhan_dien: { nen: 22, trang_thai: 'nhieu', tu_nen: 20, chi_tiet: { cua_so_nen: 32, er: 0.1 }, tam_nen: { '1h': 4, '4h': 16 },
    khoang: { '1h': { lo80: 99, hi80: 103, lo50: 100, hi50: 102, nguon: 'gio', n_mau: 600, gio_ny: 9 },
      '4h': { lo80: 97, hi80: 105, lo50: 99, hi50: 103, nguon: 'chung', n_mau: 2400, gio_ny: 9 } },
    muc: [{ loai: 'vung_tren', phia: 'up', gia: 104, kc_atr: 1.5, p_1h: 0.12, p_4h: 0.4 }],
    diem_that: { '4h': { n: 500, phu_80: 0.81, phu_50: 0.5, rong_80_atr: 9.9, skill_so_voi_b0: 0.13,
      cham: { vung_tren: { n: 400, brier: 0.15, brier_b0: 0.16 } }, cham_tong: { n: 400, brier: 0.15, brier_b0: 0.16 } } } } };
  M = V.buildModel(evs, tlb, ps, 22, 2);
  const bd = J(ND.bandDrawing(M, ident));
  eq(bd.boxes.map((b) => [b.id, b.l1, b.l2, b.p1, b.p2]), [['nd:band:4h', 22.5, 38.45, 97, 105], ['nd:band:4h', 22.5, 38.45, 99, 103],
    ['nd:band:1h', 22.5, 26.45, 99, 103], ['nd:band:1h', 22.5, 26.45, 100, 102]], 'khoảng 4h rồi 1h: từ con trỏ tới con trỏ + tầm, 80% rồi lõi 50%');
  const lv = bd.segments.find((x) => x.id === 'nd:muc:vung_tren');
  ok(lv && lv.p1 === 104 && lv.label.text === 'chạm 1h 12% · 4h 40%' && lv.l2 === 38.45, 'mức trên kèm xác suất chạm (pending của nến con trỏ)', lv);
  const tb = ND.info(M, 'nd:band:4h')[0];
  ok(tb.head.indexOf('80% [97.00 – 105.00]') > 0 && tb.more.indexOf('phủ 80% thực tế 81.0%') > 0 && tb.more.indexOf('tốt hơn B0') > 0,
    'tooltip khoảng ghi điểm thật', tb);
  ok(ND.info(M, 'nd:muc:vung_tren')[0].more.indexOf('4h Brier 0.150 (B0 0.160, 400 lần)') > 0, 'tooltip mức ghi Brier so với B0');
  ok(ND.statusAt(M, 22, { state: true, band: true }).text.indexOf('│ 4h 80% [97.00 – 105.00]') > 0 &&
    ND.statusAt(M, 22, { state: true }).text.indexOf('4h 80%') < 0 && ND.statusAt(M, 22, { band: true }).text === '4h 80% [97.00 – 105.00]',
    'hàng 3: trạng thái và khoảng 4h theo từng lớp');
  const pl = ND.pendingLines(ps, 2).map((l) => l.text);
  ok(pl.some((t) => t.indexOf('Khoảng 4h: 80% [97.00 – 105.00]') === 0 && t.indexOf('81.0% trên 500') > 0) &&
    pl.some((t) => t.indexOf('Xác suất chạm vùng trên gần nhất (BSL) 104.00 (cách 1.5 ATR): 1h 12% · 4h 40%') === 0),
    '«Đang theo dõi»: khoảng kèm điểm thật + xác suất chạm', pl);
  M = V.buildModel(evs, tlb, ps, 21, 2);
  eq(J(ND.bandDrawing(M, ident)).boxes.length, 0, 'con trỏ chưa có khoảng (khởi động) → không vẽ');
  // pending của nến khác con trỏ (vd cuối lần chạy) → không vẽ mức / không ghi điểm thật ở con trỏ (không tô ngược)
  const tlc2 = tlb.map((p) => Object.assign({}, p, p.bar_index === 21 ? { nd_4h_lo80: 97, nd_4h_hi80: 105, nd_4h_lo50: 99, nd_4h_hi50: 103 } : {}));
  M = V.buildModel(evs, tlc2, ps, 21, 2);
  const bd2 = J(ND.bandDrawing(M, ident));
  ok(bd2.boxes.length === 2 && !bd2.segments.some((x) => x.id.indexOf('nd:muc:') === 0), 'pending khác nến: chỉ khoảng (timeline), không mức');
  ok(ND.info(M, 'nd:band:4h')[0].more === 'Điểm thật: chưa có số liệu ở nến này.', 'pending khác nến: không mượn điểm thật');
  const rows = ND.statsRows({ khoang_va_cham: ps.nhan_dien.diem_that, trang_thai: { ty_le_thoi_gian: { nhieu: 0.7 }, so_lan_doi: 3 } });
  eq(rows.map((r) => r.v), ['81.0% / 50.0%', '0.150 (0.160)', '— / — / — / — / 70%'], 'ô thống kê điểm thật');
  // ---- PDH / PDL (0.8.0): trùng giá với vùng gần nhất → một đường «PDH chạm …»; PDL đường riêng; ô «chạm thật − kỳ vọng»
  const psd = JSON.parse(JSON.stringify(ps));
  psd.nhan_dien.muc.push({ loai: 'pdh', phia: 'up', gia: 104, kc_atr: 1.5, p_1h: 0.12, p_4h: 0.4 },
    { loai: 'pdl', phia: 'down', gia: 96, kc_atr: 2.5, p_1h: 0.05, p_4h: 0.2 });
  psd.nhan_dien.diem_that['4h'].cham.pdh = { n: 300, brier: 0.1, brier_b0: 0.11, ty_le_cham: 0.12, p_tb: 0.1, chenh: 0.02 };
  psd.nhan_dien.diem_that['4h'].cham.pdl = { n: 300, brier: 0.1, brier_b0: 0.11, ty_le_cham: 0.09, p_tb: 0.095, chenh: -0.005 };
  M = V.buildModel(evs, tlb, psd, 22, 2);
  const lvs = J(ND.bandDrawing(M, ident)).segments.filter((x) => x.id.indexOf('nd:muc:') === 0);
  eq(lvs.map((x) => [x.id, x.p1, x.label.text]), [['nd:muc:vung_tren', 104, 'PDH chạm 1h 12% · 4h 40%'],
    ['nd:muc:pdl', 96, 'PDL chạm 1h 5% · 4h 20%']], 'PDH trùng vùng gần nhất: một đường ghi tên PDH; PDL đường riêng');
  const tipd = ND.info(M, 'nd:muc:vung_tren');
  ok(tipd.length === 2 && tipd[0].head.indexOf('vùng trên gần nhất (BSL) = PDH (đỉnh ngày trước) 104.00: 1h 12%') > 0 &&
    tipd[1].body.indexOf('4h Brier 0.100 (B0 0.110, 300 lần), chạm thật 12.0% / kỳ vọng 10.0%') > 0 && !tipd[1].more &&
    tipd[0].more.indexOf('kỳ vọng 10.0%') < 0, 'tooltip mức trùng: mỗi loại điểm thật riêng (BSL không mượn số của PDH)', tipd);
  ok(ND.pendingLines(psd, 2).filter((l) => l.text.indexOf('Xác suất chạm') === 0).map((l) => l.text).join(' | ') ===
    'Xác suất chạm vùng trên gần nhất (BSL) = PDH (đỉnh ngày trước) 104.00 (cách 1.5 ATR): 1h 12% · 4h 40%. | ' +
    'Xác suất chạm PDL (đáy ngày trước) 96.00 (cách 2.5 ATR): 1h 5% · 4h 20%.', '«Đang theo dõi»: mức trùng giá một dòng');
  const pc = ND.statsRows({ khoang_va_cham: psd.nhan_dien.diem_that, trang_thai: {} })
    .find((r) => r.k === 'PDH / PDL 4h — chạm thật − kỳ vọng');
  ok(pc && pc.v === 'PDH +2.0 điểm · PDL −0.5 điểm' && pc.title.indexOf('PDH +2.0 điểm (12.0% / 10.0%, 300 lần) · PDL −0.5 điểm') > 0,
    'ô PDH / PDL: chạm thật − kỳ vọng, ghi tên từng loại', pc);
  const rowsT8 = ND.statsRows({ khoang_va_cham: { '4h': { n: 0, cham: psd.nhan_dien.diem_that['4h'].cham,
    cham_tong: { n: 400, brier: 0.15, brier_b0: 0.16 }, cham_tong_loai: ['vung_tren', 'vung_duoi', 'range_tren', 'range_duoi'] } }, trang_thai: {} });
  ok(rowsT8.find((r) => r.k === 'Xác suất chạm 4h — Brier (B0)').title.indexOf('Gộp BSL gần, SSL gần, biên trên, biên dưới, 400 lần.') === 0,
    'ô Brier gộp ghi đúng các loại lõi gộp (PDH / PDL ở ô riêng)');
  // biên range trùng giá vùng gần nhất: vẫn hai đường như 0.7.0 (chỉ PDH / PDL gộp vào mức không tên)
  const psr = JSON.parse(JSON.stringify(ps));
  psr.nhan_dien.muc.push({ loai: 'range_tren', phia: 'up', gia: 104, kc_atr: 1.5, p_1h: 0.12, p_4h: 0.4 });
  M = V.buildModel(evs, tlb, psr, 22, 2);
  eq(J(ND.bandDrawing(M, ident)).segments.filter((x) => x.id.indexOf('nd:muc:') === 0).map((x) => x.id), ['nd:muc:vung_tren', 'nd:muc:range_tren'],
    'biên range trùng giá vùng gần nhất: hai đường riêng');
  // ---- thời gian (0.7.0): còn giữ + thời gian còn lại (hàng 3, «Đang theo dõi», Thống kê), phá biên (nhãn range)
  const tlt = tlb.map((p) => Object.assign({}, p, p.bar_index === 22 ? { nd_giu_1h: 0.9, nd_giu_4h: 0.62, nd_con_lai: 6 } : {}));
  const pst = JSON.parse(JSON.stringify(ps));
  // giữ 2 nến: trạng thái hiện từ #21 (ứng viên từ #20) → tuổi 2 ở #22
  pst.nhan_dien.thoi_gian = { con_giu: { tuoi_nen: 2, giu: { '1h': 0.9, '4h': 0.62 }, con_lai_nen: 6, nguon: 'trang_thai', n_doan: 80, n_doan_con: 50 },
    pha_bien: { lo: 98, hi: 104, p: { '1h': 0.1, '4h': 0.35 } },
    diem_that: { con_giu: { '4h': { n: 300, ty_le: 0.5, brier: 0.24, brier_b0: 0.25 } }, pha_bien: { '4h': { n: 0 } } } };
  M = V.buildModel(evs, tlt, pst, 22, 2);
  const row3 = ND.statusAt(M, 22, { state: true }).text;
  ok(row3.indexOf('nhiễu · 3 nến (từ #20) · giữ 4h 62% · còn ~6 nến') > 0, 'hàng 3: còn giữ + thời gian còn lại', row3);
  const plT = ND.pendingLines(pst, 2).map((l) => l.text);
  ok(plT.indexOf('Còn giữ sau 1h 90% · 4h 62% (đã hiện 2 nến; còn lại trung vị 6.0 nến; mẫu 50/80 đoạn cùng trạng thái dài ≥ tuổi này) — ' +
    'điểm thật: 4h Brier 0.240 (B0 0.250, 300 lần).') >= 0 &&
    plT.indexOf('Phá biên range [98.00 – 104.00] (close ra ngoài): 1h 10% · 4h 35%.') >= 0,
  '«Đang theo dõi»: còn giữ kèm điểm thật, phá biên (chưa chấm → không ghi điểm)', plT);
  const rowsT = ND.statsRows({ khoang_va_cham: { '4h': { n: 0 } }, trang_thai: {},
    thoi_gian: { con_giu: { '4h': { n: 300, ty_le: 0.5, brier: 0.24, brier_b0: 0.25 } },
      pha_bien: { '4h': { n: 50, ty_le: 0.3, brier: 0.2, brier_b0: 0.21 } }, b0_vi: { pha_bien: 'mẫu chung mọi giờ' } } });
  eq(rowsT.map((r) => [r.k, r.v]).slice(1, 3), [['Còn giữ 4h — Brier (B0)', '0.240 (0.250)'], ['Phá biên range 4h — Brier (B0)', '0.200 (0.210)']],
    'Thống kê: còn giữ, phá biên');
  ok(rowsT[2].title.indexOf('tỷ lệ thật 30.0% (close ra ngoài biên range trong tầm). B0 = mẫu chung mọi giờ.') > 0 &&
    rowsT[1].title.indexOf('B0') < 0, 'Thống kê: B0 theo mô tả của lõi', rowsT.map((r) => r.title));
  const tlr = tl.map((p) => Object.assign({}, p, p.bar_index === 15 ? { nd_pha_4h: 0.35 } : {}));
  M = V.buildModel(evs, tlr, { nhan_dien: { nen: 15, tam_nen: { '1h': 4, '4h': 16 } } }, 15, 2);
  ok(J(ND.drawing(M, ident)).segments.some((x) => x.label && x.label.text === 'Range · phá 4h 35%'), 'nhãn range đang có kèm xác suất phá biên');
  // nhân quả: con trỏ 8 chưa thấy range
  M = V.buildModel(evs, tl, null, 8, 2);
  eq(J(ND.drawing(M, ident)).boxes.length, 0, 'con trỏ trước range: không có hộp');
  // chữ
  for (const e of evs) ok(typeof ND.eventText(e, 2) === 'string', 'câu giải thích ' + e.structure_type);
  eq(ND.eventText({ structure_type: 'SHIFT_UP' }, 2), null, 'không phải STATE_*');
  // v2 (0.9.0): lý do vào, lý do thoát trạng thái trước, số liệu đã dùng; range ghi số lần thăm biên
  const t2 = ND.eventText({ structure_type: 'STATE_TREND_UP', event_bar_index: 50, details: { kieu: 'v2', ly_do: 'cau_truc_va_luc', thoat: 'pha_bien_len',
    er: 0.21, cua_so_nen: 32, adx: 27.4, dong_luong_atr: 3.2, cau_truc: 1, cau_truc_h1: 0, nen: false } }, 2);
  ok(t2.indexOf('cấu trúc cùng chiều + lực: ER 0.21 / 32 nến, ADX 27, động lượng 3.2 ATR, cấu trúc HH-HL · H1 lẫn lộn. ' +
    'Trạng thái trước kết thúc vì range bị phá lên.') > 0, 'câu giải thích trend v2', t2);
  const r2 = ND.eventText({ structure_type: 'STATE_RANGE', event_bar_index: 60, details: { kieu: 'v2', ly_do: 'hop', er: 0.05, cua_so_nen: 32,
    adx: 14, dong_luong_atr: 0.3, cau_truc: 0, cau_truc_h1: null, bien_duoi: 100, bien_tren: 102.5, rong_atr: 2.5,
    tham_tren: [1, 5, 9], tham_duoi: [3, 7], nen: true } }, 2);
  ok(r2.indexOf('Hộp [100.00 – 102.50], rộng 2.5 ATR; thăm biên trên 3 lần, biên dưới 2 lần;') > 0 && r2.indexOf('Đang nén.') > 0,
    'câu giải thích range v2', r2);
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
  let ranges = 0, bands = 0;
  for (const P of D.prefixes) {
    const c = P.cursor, tlc = P.timeline[P.timeline.length - 1];
    const Mf = V.buildModel(D.full.events, D.full.timeline, P.pending, c, D.digits);
    const Mp = V.buildModel(P.events, P.timeline, P.pending, c, D.digits);
    const bars = J(ND.bandBars(Mf, ident)), dr = J(ND.drawing(Mf, ident));
    eq(J(ND.bandBars(Mp, ident)), bars, 'replay prefix = toàn bộ lọc theo con trỏ (dải) #' + c);
    eq(J(ND.drawing(Mp, ident)), dr, 'replay prefix = toàn bộ lọc theo con trỏ (hộp) #' + c);
    const s = ND.statusAt(Mf, c, { state: true });
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
    const bdr = J(ND.bandDrawing(Mf, ident));     // khoảng ở con trỏ = cột timeline; mức = pending của nến con trỏ
    eq(J(ND.bandDrawing(Mp, ident)), bdr, 'replay prefix = toàn bộ lọc theo con trỏ (khoảng) #' + c);
    eq(P.pending.nhan_dien.nen, c, 'lõi đóng dấu pending đúng nến con trỏ #' + c);
    if (tlc.nd_4h_lo80 !== null) {
      bands++;
      const b4 = bdr.boxes.filter((b) => b.id === 'nd:band:4h');
      eq(b4.map((b) => [b.p1, b.p2]), [[tlc.nd_4h_lo80, tlc.nd_4h_hi80], [tlc.nd_4h_lo50, tlc.nd_4h_hi50]], 'khoảng 4h = timeline #' + c);
      eq(b4[0].l2, c + P.pending.nhan_dien.tam_nen['4h'] + 0.45, 'khoảng 4h dài đúng tam_nen của lõi #' + c);
      ok(ND.info(Mf, 'nd:band:4h')[0].more.indexOf('Điểm thật') === 0, 'tooltip khoảng có điểm thật #' + c);
    }
    for (const sgm of bdr.segments.filter((x) => x.id.indexOf('nd:muc:') === 0)) {
      ok(ND.info(Mf, sgm.id)[0].head.indexOf('Xác suất chạm') === 0, 'tooltip mức ' + sgm.id + ' #' + c);
    }

  }
  ok(ranges > 0 && bands > 0, 'dữ liệu có con trỏ đang range và có khoảng', { ranges: ranges, bands: bands });
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
