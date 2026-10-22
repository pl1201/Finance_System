/* Kiểm hàm thuần frontend/js/algos/ict_nhan_dien_view.js (lõi 0.6.0) bằng node (gọi từ test_ict_nhan_dien_display.py).
 *
 *   node ict_nhan_dien_check.js hand          kịch bản dựng tay: dải trạng thái, đoạn, dòng trạng thái, hộp range (đang có /
 *                                             đã qua), khoảng giá + xác suất chạm (kèm điểm thật), tooltip, câu giải thích,
 *                                             «Đang theo dõi», ô thống kê, kết quả cũ; khung trạng thái dưới chart (giá trị /
 *                                             màu từng trạng thái, null, dải nén, cắt ở con trỏ, chữ, chú giải, run v1)
 *   node ict_nhan_dien_check.js real <file>   dữ liệu lõi thật (JSON do pytest xuất): dải = cột nd_trang_thai, replay prefix =
 *                                             lọc theo con trỏ, hộp range = biên timeline, mọi đối tượng có tooltip; khung
 *                                             trạng thái = cột timeline, prefix = toàn bộ cắt ở con trỏ
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
  ok(ND.statusAt(M, 15, ST).text.indexOf('range [100.50 – 102.00] · 6 nến (từ #10)') > 0, 'dòng trạng thái', ND.statusAt(M, 15, ST).text);
  ok(ND.statusAt(M, 7, ST).text.indexOf('trend lên') > 0 && ND.statusAt(M, 2, ST).key === null, 'dòng trạng thái theo nến rê / chưa đủ nến');
  ok(ND.statusAt(M, 15, {}) === null, 'tắt cả hai lớp → không có hàng 3');
  const tip = ND.info(M, 'nd:range:10')[0];
  ok(tip.head.indexOf('range · #10 → #15 (đang có)') > 0 && tip.body.indexOf('chạm biên trên 2 lần') > 0, 'tooltip hộp range', tip);
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
  // nón bậc, chỉ số của lõi: 1h từ con trỏ tới +4 nến, 4h nối tiếp tới +16 nến — 80% rồi lõi 50%
  const bd = J(ND.bandDrawing(M, ident));
  eq(bd.boxes.map((b) => [b.id, b.l1, b.l2, b.p1, b.p2]), [['nd:band:1h', 22.5, 26.5, 99, 103], ['nd:band:1h', 22.5, 26.5, 100, 102],
    ['nd:band:4h', 26.5, 38.5, 97, 105], ['nd:band:4h', 26.5, 38.5, 99, 103]], 'nón bậc: tầm ngắn rồi tầm dài, đúng biên của lõi');
  eq(bd.segments.filter((x) => x.label && x.id.indexOf('nd:band') === 0).map((x) => x.label.text), ['1h', '4h'], 'chữ mốc tầm');
  const lv = bd.segments.find((x) => x.id === 'nd:muc:vung_tren');
  ok(lv && lv.p1 === 104 && lv.label.text === 'chạm 1h 12% · 4h 40%' && lv.l2 === 38.5, 'mức trên kèm xác suất chạm (pending của nến con trỏ)', lv);
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
    { loai: 'pdl', phia: 'down', gia: 97.5, kc_atr: 2.5, p_1h: 0.05, p_4h: 0.2 });
  psd.nhan_dien.diem_that['4h'].cham.pdh = { n: 300, brier: 0.1, brier_b0: 0.11, ty_le_cham: 0.12, p_tb: 0.1, chenh: 0.02 };
  psd.nhan_dien.diem_that['4h'].cham.pdl = { n: 300, brier: 0.1, brier_b0: 0.11, ty_le_cham: 0.09, p_tb: 0.095, chenh: -0.005 };
  M = V.buildModel(evs, tlb, psd, 22, 2);
  const lvs = J(ND.bandDrawing(M, ident)).segments.filter((x) => x.id.indexOf('nd:muc:') === 0);
  eq(lvs.map((x) => [x.id, x.p1, x.label.text]), [['nd:muc:vung_tren', 104, 'PDH chạm 1h 12% · 4h 40%'],
    ['nd:muc:pdl', 97.5, 'PDL chạm 1h 5% · 4h 20%']], 'PDH trùng vùng gần nhất: một đường ghi tên PDH; PDL đường riêng');
  const tipd = ND.info(M, 'nd:muc:vung_tren');
  ok(tipd.length === 2 && tipd[0].head.indexOf('vùng trên gần nhất (BSL) = PDH (đỉnh ngày trước) 104.00: 1h 12%') > 0 &&
    tipd[1].body.indexOf('4h Brier 0.100 (B0 0.110, 300 lần), chạm thật 12.0% / kỳ vọng 10.0%') > 0 && !tipd[1].more &&
    tipd[0].more.indexOf('kỳ vọng 10.0%') < 0, 'tooltip mức trùng: mỗi loại điểm thật riêng (BSL không mượn số của PDH)', tipd);
  ok(ND.pendingLines(psd, 2).filter((l) => l.text.indexOf('Xác suất chạm') === 0).map((l) => l.text).join(' | ') ===
    'Xác suất chạm vùng trên gần nhất (BSL) = PDH (đỉnh ngày trước) 104.00 (cách 1.5 ATR): 1h 12% · 4h 40%. | ' +
    'Xác suất chạm PDL (đáy ngày trước) 97.50 (cách 2.5 ATR): 1h 5% · 4h 20%.', '«Đang theo dõi»: mức trùng giá một dòng');
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
  // ---- giao diện v2 (0.9.0): lọc mức (p tầm dài ≥ 10%, ≤ 2 mỗi phía, gần trước), bảng «Nhận diện», dải nén
  const psf = JSON.parse(JSON.stringify(ps));
  psf.nhan_dien.muc = [{ loai: 'vung_tren', phia: 'up', gia: 104, kc_atr: 1.5, p_1h: 0.12, p_4h: 0.4 },
    { loai: 'range_tren', phia: 'up', gia: 105, kc_atr: 2.0, p_1h: 0.08, p_4h: 0.3 },
    { loai: 'pdh', phia: 'up', gia: 105.5, kc_atr: 2.2, p_1h: 0.05, p_4h: 0.2 },
    { loai: 'vung_duoi', phia: 'down', gia: 96, kc_atr: 2.5, p_1h: 0.01, p_4h: 0.06 }];
  M = V.buildModel(evs, tlb, psf, 22, 2);
  eq(J(ND.bandDrawing(M, ident)).segments.filter((x) => x.id.indexOf('nd:muc:') === 0).map((x) => [x.id, x.width, +x.alpha.toFixed(2)]),
    [['nd:muc:vung_tren', 1, 0.65], ['nd:muc:range_tren', 1, 0.6]], 'mức: bỏ p 4h < 10% (SSL 6%), tối đa 2 mỗi phía (PDH thứ 3 bỏ), đậm theo p');
  const tlp = tlt.map((p) => Object.assign({}, p, p.bar_index === 22 ? { nd_nen: true, nd_do_manh: 0.62 } : {}));
  M = V.buildModel(evs, tlp, pst, 22, 2);
  const pn = ND.panel(M);
  eq(pn.rows.map((r) => [r.k, r.v]), [['Trạng thái', 'sideway nhiễu · 3 nến · nén'], ['Còn giữ 4h', '62% · còn ~6 nến'],
    ['Khoảng 4h 80%', '[97.00 – 105.00] · phủ thật 81.0%'], ['Chạm 4h', 'BSL gần 40%']], 'bảng «Nhận diện» ở con trỏ');
  ok(pn.title === 'Nhận diện · #22' && ND.panel(V.buildModel(evs, tl, null, 2, 2)).rows[0].v === 'chưa đủ nến', 'bảng: tiêu đề, chưa đủ nến');
  ok(pn.rows[1].title.indexOf('Điểm thật: 4h Brier 0.240 (B0 0.250, 300 lần).') > 0, 'bảng: còn giữ ghi điểm thật lõi gửi kèm', pn.rows[1]);
  eq(J(ND.squeezeBars(M, ident)).map((b) => [b.l, b.id]), [[22, 'nd:nen:22']], 'dải nén: chỉ nến có cờ nd_nen');
  eq(ND.panel(V.buildModel(evs, tlp, pst, 21, 2)).rows.slice(-1).map((r) => r.v), ['chưa đủ mẫu (khởi động)'], 'bảng: khoảng khởi động');
  ok(ND.info(M, 'nd:nen:22')[0].body.indexOf('cờ đi kèm trạng thái') > 0, 'tooltip dải nén');
  // range đã qua bị phá lên (lõi v2 ghi details.thoat ở trạng thái kế) → biên xanh, nhãn ghi chiều phá; đường giữa chấm
  const evb = evs.map((e) => e.structure_type === 'STATE_CHOP' ? Object.assign({}, e, { details: Object.assign({}, e.details, { thoat: 'pha_bien_len' }) }) : e);
  const drb = J(ND.drawing(V.buildModel(evb, tl, null, 24, 2), ident));
  ok(drb.boxes[0].border === V.rgba(V.COL.up, 0.55) && drb.segments.some((x) => x.id === 'nd:range:10' && x.p1 === 101.25 && x.style === 'dotted') &&
    drb.segments.some((x) => x.label && x.label.text === 'Range (đã qua, phá lên)'), 'range đã qua: biên theo chiều phá, đường giữa', drb);
  eq(J(ND.drawing(V.buildModel(evb, tl, null, 24, 2), ident, { all: true })).boxes.length, 1, 'xem lại: mọi range đã qua (ở đây một)');
  ok(ND.info(V.buildModel(evb, tl, null, 24, 2), 'nd:range:10')[0].head.indexOf('(kết thúc: phá lên)') > 0, 'tooltip range đã qua ghi chiều phá (chữ, không chỉ màu)');
  // «đường trend» (0.9.1): cột nd_duong — nến đầu mỗi đoạn là khoảng trống (không nối hai đoạn), nhiễu không vẽ
  const tll = tl.map((p) => Object.assign({}, p, { time: 1000 + p.bar_index * 900,
    nd_duong: p.nd_trang_thai === 'trend_len' ? 95 + p.bar_index : p.nd_trang_thai === 'range' ? 101 : null }));
  M = V.buildModel(evs, tll, null, 22, 2);
  const tln = J(ND.trendLine(M));
  ok(ND.hasLine(M) && !ND.hasLine(V.buildModel(evs, tl, null, 22, 2)), 'có cột nd_duong → vẽ đường; run v1 không có → dải');
  eq([tln[5], tln[6], tln[10], tln[11], tln[20]], [{ time: 5500 }, { time: 6400, value: 101, color: V.COL.up }, { time: 10000 },
    { time: 10900, value: 101, color: V.rgba('#5c6bc0', 0.9) }, { time: 19000 }], 'đường trend: ngắt ở nến đầu đoạn, màu theo trạng thái, nhiễu trống');
  eq(tln.length, 23, 'đường trend: một điểm mỗi nến ≤ con trỏ');
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
  runPaneHand();
}

// ------------------------------------------------------------------ khung trạng thái dưới chart (hook `pane`, ict_nd_pane)

function runPaneHand() {
  // #430–#434 chưa đủ nến · #435–#455 trend ↑ từ #435 (độ mạnh 0.2; #440 null; #455 0.57 + nén) · #456–#459 range từ #456
  // (#457 nén) · #460 nhiễu · #461 trend ↓ (độ mạnh 1) · nến #462 không có hàng timeline
  const tp = [];
  for (let i = 430; i <= 461; i++) {
    const st = i < 435 ? null : i < 456 ? 'trend_len' : i < 460 ? 'range' : i === 460 ? 'nhieu' : 'trend_xuong';
    tp.push({ bar_index: i, time: 1000 + 900 * i, nd_trang_thai: st,
      nd_tu: st === null ? null : st === 'trend_len' ? 435 : st === 'range' ? 456 : i,
      nd_do_manh: st === null || i === 440 ? null : i === 455 ? 0.57 : i === 461 ? 1 : 0.2,
      nd_nen: st === null ? null : i === 455 || i === 457,
      nd_range_hi: st === 'range' ? 102 : null, nd_range_lo: st === 'range' ? 100 : null });
  }
  const bars = [];
  for (let i = 430; i <= 462; i++) bars.push({ time: 1000 + 900 * i, index: i, close: 100 });
  const UP = V.COL.up, DN = V.COL.down, RG = V.rgba('#5c6bc0', 0.9), CH = V.rgba('#78909c', 0.8), SQ = V.rgba('#ba68c8', 0.85);
  ok(ND.paneHas(tp) && !ND.paneHas([]) && !ND.paneHas([{ bar_index: 0, dealing_hi: 1 }]), 'paneHas: chỉ khi có cột nd_trang_thai');
  ok(ND.has(V.buildModel([], tp.map((p) => Object.assign({ dealing_hi: 1 }, p)), null, 440, 2)), 'has(M) = paneHas của timeline M');
  const S = J(ND.statePaneSeries(tp, bars, Infinity)), KEYS = ['a', 'b', 'nen'];
  eq(Object.keys(S), KEYS, 'khung: ba series a / b / nen');
  ok(KEYS.every((k) => S[k].length === bars.length && S[k].every((x, j) => x.time === bars[j].time)),
    'khung: một phần tử mỗi nến của chart chính, cùng thứ tự / cùng time');
  const at = (i) => { const j = i - 430; return [S.a[j].value, S.a[j].color, S.b[j].value, S.b[j].color, S.nen[j].value]; };
  const U = undefined;
  eq(at(430), [U, U, U, U, U], 'chưa đủ nến: khoảng trống');
  eq(at(435), [0.48, UP, U, U, U], 'trend ↑: +(0.35 + 0.65 × 0.2) xanh, không có cột b');
  eq(at(440), [0.675, UP, U, U, U], 'trend ↑ độ mạnh null → 0.5: +0.675');
  eq(at(455), [0.7205, UP, U, U, 1.2], 'trend ↑ độ mạnh 0.57 + cờ nén: dải tím 1.2');
  eq(at(456), [0.3, RG, -0.3, RG, U], 'range: ±0.3 chàm, đối xứng quanh 0');
  eq(at(457), [0.3, RG, -0.3, RG, 1.2], 'range + nén');
  eq(at(460), [0.1, CH, -0.1, CH, U], 'nhiễu: ±0.1 xám');
  eq(at(461), [-1, DN, U, U, U], 'trend ↓ độ mạnh 1: −1 đỏ');
  eq(at(462), [U, U, U, U, U], 'nến không có hàng timeline: khoảng trống ở mọi series');
  eq(S.nen.filter((x) => x.value !== undefined).map((x) => [x.time, x.color]), [[1000 + 900 * 455, SQ], [1000 + 900 * 457, SQ]],
    'dải nén: đúng các nến có cờ nd_nen = true, màu tím');
  eq(ND.statePaneSeries([{ bar_index: 0, time: 5, nd_trang_thai: 'trend_xuong', nd_tu: 0, nd_do_manh: -0.3 }],
    [{ time: 5, index: 0 }], Infinity).a[0].value, -0.35, 'độ mạnh ngoài [0, 1] bị kẹp (chỉ để hiển thị)');
  // nhân quả: nến sau con trỏ = khoảng trống; replay prefix (timeline + nến ≤ con trỏ) = toàn bộ cắt ở con trỏ
  const C = J(ND.statePaneSeries(tp, bars, 457)), n457 = 457 - 430 + 1;
  ok(KEYS.every((k) => C[k].slice(n457).every((x) => Object.keys(x).join() === 'time')),
    'con trỏ 457: mọi phần tử sau con trỏ chỉ có time');
  const Px = J(ND.statePaneSeries(tp.filter((p) => p.bar_index <= 457), bars.filter((b) => b.index <= 457), 457));
  ok(KEYS.every((k) => JSON.stringify(Px[k]) === JSON.stringify(C[k].slice(0, n457)) &&
    JSON.stringify(Px[k]) === JSON.stringify(S[k].slice(0, n457))), 'replay prefix = toàn bộ lọc theo con trỏ (cả ba series)');
  // một nến lẻ (replay tiến một nến: ctx.from = nến mới) = đúng phần tử đó của cả chuỗi
  ok(bars.every((b, j) => KEYS.every((k) =>
    JSON.stringify(J(ND.statePaneSeries(tp, [b], Infinity))[k][0]) === JSON.stringify(S[k][j]))), 'một nến = phần tử của cả chuỗi');
  // chữ ở nến dưới chuột (mặc định nến con trỏ) — chỉ từ hàng timeline của nến đó
  eq(ND.statePaneText(tp, 455, Infinity), '#455 · trend lên · mạnh 0.57 · 21 nến (từ #435) · nén', 'chữ: trend + độ mạnh + số nến + nén');
  eq(ND.statePaneText(tp, 440, Infinity), '#440 · trend lên · 6 nến (từ #435)', 'chữ: độ mạnh null → không ghi');
  eq(ND.statePaneText(tp, 456, Infinity), '#456 · range · 1 nến (từ #456)', 'chữ: range không ghi độ mạnh');
  eq(ND.statePaneText(tp, 432, Infinity), '#432 · chưa đủ nến (sau khoảng trống / khởi động)', 'chữ: trạng thái null');
  eq(ND.statePaneText(tp, null, Infinity), '#461 · trend xuống · mạnh 1.00 · 1 nến (từ #461)', 'chữ: không rê → nến cuối (toàn lịch sử)');
  eq(ND.statePaneText(tp, null, 457), '#457 · range · 2 nến (từ #456) · nén', 'chữ: không rê → nến con trỏ replay');
  eq(ND.statePaneText(tp, 459, 457), '#457 · range · 2 nến (từ #456) · nén', 'chữ: nến sau con trỏ → con trỏ (không nhìn trước)');
  // cùng cách ghi số nến với hàng trạng thái trên chart (statusAt)
  const Mt = V.buildModel([], tp.map((p) => Object.assign({ dealing_hi: 1 }, p)), null, 455, 2);
  ok(ND.statusAt(Mt, 455, { state: true }).text.indexOf('21 nến (từ #435)') > 0, 'chữ khung và dòng trạng thái cùng cách ghi');
  ok(ND.statePaneText(tp, 425, Infinity) === null && ND.statePaneText([], 1, 1) === null &&
    ND.statePaneText([{ bar_index: 3, dealing_hi: 1 }], 3, 3) === null, 'chữ: không có hàng / kết quả cũ → null');
  // chú giải: chữ cho mọi màu, cùng màu với cột
  const lg = ND.statePaneLegend(tp);
  eq(lg.map((x) => x.sym + ' ' + x.word), ['▲ trend lên', '▼ trend xuống', '▬ range', '· sideway nhiễu', '▔ nén'], 'chú giải v2');
  eq(lg.map((x) => x.color), [UP, DN, RG, CH, SQ], 'chú giải cùng màu với cột');
  // run v1 (nd_kieu = v1, không có cột nd_nen / nd_do_manh): «sideway nén» là trạng thái — ±0.1 tím, không có dải cờ
  const t1 = [{ bar_index: 0, time: 7, nd_trang_thai: 'nen', nd_tu: 0 }, { bar_index: 1, time: 8, nd_trang_thai: 'trend_len', nd_tu: 1 }];
  const S1 = J(ND.statePaneSeries(t1, [{ time: 7, index: 0 }, { time: 8, index: 1 }], Infinity));
  eq([S1.a[0].value, S1.b[0].value, S1.a[0].color, S1.nen[0].value, S1.a[1].value], [0.1, -0.1, V.rgba('#ba68c8', 0.55), U, 0.675],
    'v1: nén là trạng thái ±0.1 tím; trend không có độ mạnh → 0.5');
  eq(ND.statePaneLegend(t1).map((x) => x.word), ['trend lên', 'trend xuống', 'range', 'sideway nén', 'sideway nhiễu'], 'chú giải v1');
  eq(ND.statePaneText(t1, 0, Infinity), '#0 · sideway nén · 1 nến (từ #0)', 'chữ v1');
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
    const bdr = J(ND.bandDrawing(Mf, ident));   // khoảng ở con trỏ = cột timeline; mức = pending của nến con trỏ
    eq(J(ND.bandDrawing(Mp, ident)), bdr, 'replay prefix = toàn bộ lọc theo con trỏ (khoảng) #' + c);
    eq(P.pending.nhan_dien.nen, c, 'lõi đóng dấu pending đúng nến con trỏ #' + c);
    eq(J(ND.panel(Mp)), J(ND.panel(Mf)), 'bảng «Nhận diện»: replay prefix = toàn bộ lọc theo con trỏ #' + c);
    eq(J(ND.drawing(Mp, ident, { all: true })), J(ND.drawing(Mf, ident, { all: true })), 'xem lại range: prefix = toàn bộ #' + c);
    eq(J(ND.squeezeBars(Mp, ident)), J(ND.squeezeBars(Mf, ident)), 'dải nén: prefix = toàn bộ #' + c);
    eq(J(ND.trendLine(Mp)), J(ND.trendLine(Mf)), 'đường trend: prefix = toàn bộ #' + c);
    ok(ND.hasLine(Mf), 'lõi ≥ 0.9.1 có cột nd_duong #' + c);
    if (tlc.nd_4h_lo80 !== null) {
      bands++;
      const b4 = bdr.boxes.filter((b) => b.id === 'nd:band:4h');   // bậc 4h của nón = khoảng 4h của lõi
      eq(b4.map((b) => [b.p1, b.p2]), [[tlc.nd_4h_lo80, tlc.nd_4h_hi80], [tlc.nd_4h_lo50, tlc.nd_4h_hi50]], 'khoảng 4h = timeline #' + c);
      eq(b4[0].l2, c + P.pending.nhan_dien.tam_nen['4h'] + 0.5, 'nón dài đúng tam_nen của lõi #' + c);
      ok(ND.info(Mf, 'nd:band:4h')[0].more.indexOf('Điểm thật') === 0, 'tooltip khoảng có điểm thật #' + c);
    }
    for (const sgm of bdr.segments.filter((x) => x.id.indexOf('nd:muc:') === 0)) {
      ok(ND.info(Mf, sgm.id)[0].head.indexOf('Xác suất chạm') === 0, 'tooltip mức ' + sgm.id + ' #' + c);
    }
    // khung trạng thái dưới chart (hook `pane`): replay prefix (timeline + nến ≤ con trỏ) = toàn bộ cắt ở con trỏ; cột theo
    // đúng cột timeline của lõi ở từng nến
    const fullBars = D.full.timeline.map((p) => ({ time: p.time, index: p.bar_index }));
    const pxBars = P.timeline.map((p) => ({ time: p.time, index: p.bar_index }));
    const sf = J(ND.statePaneSeries(D.full.timeline, fullBars, c)), spx = J(ND.statePaneSeries(P.timeline, pxBars, c));
    for (const k of ['a', 'b', 'nen']) {
      eq(spx[k], sf[k].slice(0, pxBars.length), 'khung trạng thái: prefix = toàn bộ cắt ở con trỏ (' + k + ') #' + c);
      ok(sf[k].slice(pxBars.length).every((x) => !('value' in x)), 'khung trạng thái: sau con trỏ trống (' + k + ') #' + c);
    }
    const bad = P.timeline.filter((p, j) => {
      const s = p.nd_trang_thai, a = spx.a[j].value, b = spx.b[j].value;
      const m = typeof p.nd_do_manh === 'number' ? p.nd_do_manh : 0.5;
      const h = s === 'trend_len' ? 0.35 + 0.65 * m : s === 'trend_xuong' ? -(0.35 + 0.65 * m)
        : s === 'range' ? 0.3 : s === 'nhieu' ? 0.1 : undefined;
      const hb = s === 'range' ? -0.3 : s === 'nhieu' ? -0.1 : undefined;
      return (h === undefined ? a !== undefined : Math.abs(a - h) > 1e-4) || b !== hb ||
        (spx.nen[j].value === 1.2) !== (p.nd_nen === true);
    }).map((p) => p.bar_index);
    eq(bad, [], 'khung trạng thái = cột nd_trang_thai / nd_do_manh / nd_nen của lõi ở mọi nến #' + c);
    ok(ND.paneHas(P.timeline) && ND.statePaneText(P.timeline, null, c).indexOf('#' + c + ' · ') === 0,
      'chữ khung ở nến con trỏ #' + c);
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
