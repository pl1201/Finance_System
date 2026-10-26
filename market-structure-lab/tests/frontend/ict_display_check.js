/* Kiểm các hàm thuần của frontend/js/algos/ict_structure_view.js bằng node (gọi từ test_ict_display.py).
 *
 *   node ict_display_check.js hand            kịch bản dựng tay: vòng đời vùng, lọc «Hiện tại», gộp, nhân quả, chữ;
 *                                             Chi tiết (FVG + vòng đời, Protected, dealing range, ITH/ITL, displacement),
 *                                             Lịch sử (mọi thứ tới con trỏ, mờ dần), nhân quả của Chi tiết + Lịch sử
 *   node ict_display_check.js real <file>     dữ liệu lõi thật (JSON do pytest xuất): vùng gần nhất = timeline,
 *                                             replay prefix = lọc theo con trỏ, không đối tượng nào trước nến xác nhận
 * In ra JSON {checks: n, failures: [...], info: {...}}.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const REPO = path.resolve(__dirname, '..', '..');
const SRC = fs.readFileSync(path.join(REPO, 'frontend', 'js', 'algos', 'ict_structure_view.js'), 'utf8');
const sandbox = { window: { MSL: {} } };
vm.createContext(sandbox);
vm.runInContext(SRC, sandbox, { filename: 'ict_structure_view.js' });
const V = sandbox.window.MSL.ictView;

let checks = 0;
const failures = [];
const info = {};
function ok(cond, msg, extra) {
  checks++;
  if (!cond) failures.push(msg + (extra !== undefined ? ' — ' + JSON.stringify(extra) : ''));
}
function eq(a, b, msg) { ok(JSON.stringify(a) === JSON.stringify(b), msg, { got: a, want: b }); }
const J = (x) => JSON.parse(JSON.stringify(x));   // bỏ prototype của vm
const near = (a, b) => typeof a === 'number' && Math.abs(a - b) < 1e-9;
const ident = (i) => i;

// ------------------------------------------------------------------ kịch bản dựng tay

function handScenario() {
  const T0 = 1704067200;   // 01/01/2024 00:00 UTC, nến 5 phút
  const N = 35;            // nến 0..34, con trỏ cuối = 34
  const evs = [];
  function ev(type, bar, conf, price, details, ref, suffix) {
    const id = 'ict:' + type + '@' + bar + '>' + conf + (suffix ? ':' + suffix : '');
    const e = { event_id: id, structure_type: type, event_bar_index: bar, confirmed_bar_index: conf, price: price,
      algorithm: 'ict_structure', reference_event_id: ref || null, details: Object.assign({ killzone: null }, details || {}) };
    evs.push(e);
    return e;
  }
  function swing(high, bar, conf, price, vung, status, muc, nhan) {
    return ev(high ? 'SWING_HIGH_L2' : 'SWING_LOW_L2', bar, conf, price, {
      cap_cau_truc: true, nhan: nhan || null, gia_truoc: nhan ? price - 1 : null, chenh_lech: nhan ? 1 : null, dung_sai: 0.4,
      vung_thanh_khoan: { trang_thai: status || 'tao_moi', phia: high ? 'BSL' : 'SSL', tang: 'M15', vung: vung,
        muc_vung: muc === undefined ? price : muc, hieu_luc_tu_nen: conf + 1 }
    });
  }
  function fvg(up, mid, lo, hi, touch, fill) {
    const id = 'ict:' + (up ? 'FVG_UP' : 'FVG_DOWN') + '@' + mid + '>' + (mid + 1);
    ev(up ? 'FVG_UP' : 'FVG_DOWN', mid, mid + 1, (lo + hi) / 2, { lo: lo, hi: hi, kich_thuoc_atr: hi - lo, nen_1: mid - 1,
      nen_giua: mid, nen_3: mid + 1, from_displacement: false });
    const sfx = String(mid) + (up ? 'U' : 'D');
    if (touch !== null) ev('FVG_TOUCHED', touch, touch, up ? hi : lo, { fvg: id, lo: lo, hi: hi }, id, sfx);
    if (fill !== null) ev('FVG_FILLED', fill, fill, up ? lo : hi, { fvg: id, lo: lo, hi: hi }, id, sfx);
    return id;
  }
  function brief(id, side, muc, taken, extreme, extra) {
    return Object.assign({ id: id, phia: side, muc: muc, tang: 'M15', nguon: [], biet_tai_nen: null, so_lan_cham: 0,
      nen_lay: taken, atr_khoa: 1.0, xuyen: 0.5, xuyen_atr: 0.5, cuc_tri_cu_quet: extreme }, extra || {});
  }
  swing(true, 2, 4, 130, 'B6');
  swing(true, 3, 4, 140, 'B7');
  swing(false, 1, 4, 85, 'S8');
  swing(false, 2, 4, 80, 'S9');
  const ithA = swing(true, 5, 8, 110, 'B1');
  swing(false, 6, 9, 90, 'S2');
  swing(true, 12, 15, 110.2, 'B1', 'gop_eq', 110.2);      // EQH: mức đổi 110 → 110.2 khi biết ở #15
  swing(false, 14, 17, 95, 'S3');
  swing(true, 18, 20, 120, 'B4', null, undefined, 'HH');
  swing(false, 19, 21, 93, 'S5', null, undefined, 'LL');
  const swp = ev('LIQ_SWEEP_BSL', 22, 23, 110.2, { phia: 'BSL', muc: 110.2, vung: 'B1', nen_lay: 22, cua_so: 3, so_vung: 1,
    sweep_bars: 1, pools: [brief('B1', 'BSL', 110.2, 22, 110.8, { sweep_bars: 1, nguon: [ithA.event_id], biet_tai_nen: 8, xuyen_atr: 0.6 })] },
    ithA.event_id);
  swp.details.group_id = swp.event_id;
  const sh = ev('SHIFT_DOWN', 24, 24, 108.5, { chieu: 'down', muc_bi_quet: 110.2, cuc_tri_cu_quet: 110.8, nen_sweep: 23,
    so_nen_tu_sweep: 1, swept: [{ sweep: swp.event_id, vung: 'B1', muc: 110.2, tang: 'M15', nen_lay: 22, nen_sweep: 23, cuc_tri_cu_quet: 110.8 }],
    displacement: { bien_do_atr: 2.1, than_ty_le: 0.8, atr: 1 } }, swp.event_id);
  ev('ORDER_FLOW_DOWN', 24, 24, 108.5, { tu: null, sang: -1, tu_vi: 'chưa có', sang_vi: 'giảm', ly_do: 'shift_giam',
    basis: [sh.event_id] }, sh.event_id);
  ev('SHIFT_FVG_DOWN', 24, 25, 108.5, { shift: sh.event_id, fvg: 'ict:FVG_DOWN@24>25', lo: 108, hi: 109, nen_displacement: 24 }, sh.event_id);
  ev('LIQ_UNRESOLVED', 26, 27, 93, { phia: 'SSL', muc: 93, vung: 'S5', nen_lay: 26, cua_so: 3, so_vung: 1,
    loai_khoang_trong: 'cuoi_tuan', pools: [brief('S5', 'SSL', 93, 26, 92.5)] }, null, 'SSL');
  ev('LIQ_RUN_DOWN', 25, 28, 95, { phia: 'SSL', muc: 95, vung: 'S3', nen_lay: 25, cua_so: 3, so_vung: 1, so_nen_sau_lay: 3,
    pools: [brief('S3', 'SSL', 95, 25, 93.9, { xuyen_atr: 1.1 })] });
  ev('FVG_FILLED', 29, 29, 109, { fvg: 'ict:FVG_DOWN@24>25', chieu_fvg: 'down', lo: 108, hi: 109 }, 'ict:FVG_DOWN@24>25', '24D');
  // FVG thô (Chi tiết): A lấp ở #16 (chạm #13), B đã chạm #26, C/D/E còn mở, F = FVG của shift (lấp #29), G mở phía trên.
  const fv = {
    A: fvg(true, 10, 100, 101, 13, 16), B: fvg(true, 20, 102, 103, 26, null), C: fvg(true, 22, 104, 104.5, null, null),
    D: fvg(true, 27, 98, 99, null, null), E: fvg(true, 31, 90, 91, null, null), G: fvg(false, 30, 112, 113, null, null)
  };
  ev('FVG_DOWN', 24, 25, 108.5, { lo: 108, hi: 109, nen_1: 23, nen_giua: 24, nen_3: 25, from_displacement: true });
  fv.F = 'ict:FVG_DOWN@24>25';
  ev('DISPLACEMENT_DOWN', 24, 24, 108.5, { bien_do_atr: 2.1, than_ty_le: 0.8, atr: 1 });
  swing(false, 27, 30, 87.0, 'S12');
  swing(false, 29, 31, 88.0, 'S10');
  swing(false, 30, 32, 88.3, 'S11');
  ev('LIQ_SWEEP_SSL', 33, 34, 87.0, { phia: 'SSL', muc: 87.0, vung: 'S12', nen_lay: 33, cua_so: 3, so_vung: 3, sweep_bars: 1,
    pools: [brief('S10', 'SSL', 88.0, 33, 86.4, { sweep_bars: 1 }), brief('S11', 'SSL', 88.3, 33, 86.4, { sweep_bars: 1 }),
      brief('S12', 'SSL', 87.0, 33, 86.4, { sweep_bars: 1 })] });
  evs.sort((a, b) => a.confirmed_bar_index - b.confirmed_bar_index);

  // Kết cục theo vùng (để dựng pending_state đúng cho mọi con trỏ — như lõi phát ở nến đó).
  const takes = { B1: [22, 23, 110.8], S3: [25, 28, 93.9], S5: [26, 27, 92.5], B4: [33, null, 120.6],
    S10: [33, 34, 86.4], S11: [33, 34, 86.4], S12: [33, 34, 86.4] };
  const levels = { B1: 110.2, S3: 95, S5: 93, B4: 120, S10: 88.0, S11: 88.3, S12: 87.0 };
  function pendingAt(c) {
    const out = [];
    Object.keys(takes).forEach(function (id) {
      const t = takes[id];
      if (t[0] <= c && (t[1] === null || t[1] > c)) {
        out.push({ id: id, phia: id[0] === 'B' ? 'BSL' : 'SSL', muc: levels[id], nen_lay: t[0], cuc_tri_cu_quet: t[2],
          con_lai_nen: t[0] + 3 - c, can_close: 'x', nguon: [], atr_khoa: 1, xuyen_atr: 0.4 });
      }
    });
    return { thanh_khoan: { dang_cho_sweep_run: out } };
  }
  const tl = [];
  for (let i = 0; i < N; i++) {
    const p = { bar_index: i, time: T0 + 300 * i, dealing_hi: 1, atr: 1.0, liq_above: null, liq_above_id: null,
      liq_below: null, liq_below_id: null, order_flow: i >= 24 ? -1 : null, order_flow_since: i >= 24 ? 24 : null,
      order_flow_reason: i >= 24 ? 'shift_giam' : null };
    if (i >= 30) { p.liq_above = i >= 33 ? 130 : 120; p.liq_above_id = i >= 33 ? 'B6' : 'B4'; p.liq_below = 90; p.liq_below_id = 'S2'; }
    // Chi tiết (đọc thẳng timeline): mức được bảo vệ đáy l14 (95) từ #20, bị close vượt từ #25; đỉnh h18 (120) từ #30.
    Object.assign(p, { protected: null, protected_side: null, protected_id: null, protected_broken: null, order: null,
      dealing_hi: null, dealing_lo: null, dealing_eq: null, dealing_id: null, zone: null, range_pos: null });
    if (i >= 20 && i < 30) Object.assign(p, { protected: 95, protected_side: 'low', protected_id: 'l14', protected_broken: i >= 25, order: 1 });
    if (i >= 30) Object.assign(p, { protected: 120, protected_side: 'high', protected_id: 'h18', protected_broken: false, order: -1 });
    // dealing range 12-14 từ #18 (mở rộng lên 110.8 từ #22), 18-25 từ #29
    if (i >= 18 && i < 29) { const hi = i >= 22 ? 110.8 : 110.2; Object.assign(p, { dealing_hi: hi, dealing_lo: 95, dealing_eq: (hi + 95) / 2, dealing_id: '12-14', zone: 'premium', range_pos: 0.7 }); }
    if (i >= 29) Object.assign(p, { dealing_hi: 120, dealing_lo: 93.9, dealing_eq: 106.95, dealing_id: '18-25', zone: 'discount', range_pos: 0.2 });
    tl.push(p);
  }
  return { evs: evs, tl: tl, pendingAt: pendingAt, N: N, shiftId: sh.event_id, fv: fv };
}

function runHand() {
  const H = handScenario();
  const last = H.N - 1;
  const M = V.buildModel(H.evs, H.tl, H.pendingAt(last), Infinity, 2);
  ok(M && M.cursor === last, 'con trỏ Infinity = nến cuối timeline');
  const st = (id, h) => { const s = V.poolAt(M.pools[id], h); return s ? s.state + '@' + V.fp(s.level, 2) + (s.eq ? ':EQ' : '') : null; };
  // vòng đời: tạo, gộp EQ, sweep, run, chưa rõ, đang chờ
  eq(st('B1', 7), null, 'B1 chưa biết trước nến xác nhận #8');
  eq(st('B1', 8), 'intact@110.00', 'B1 tạo ở nến xác nhận ITH (#8), mức 110');
  eq(st('B1', 14), 'intact@110.00', 'B1 trước khi gộp');
  eq(st('B1', 15), 'intact@110.20:EQ', 'gộp EQH ở #15: mức 110.2, EQ');
  eq(st('B1', 22), 'pending@110.20:EQ', 'B1 bị lấy ở #22 → đang chờ');
  eq(st('B1', 23), 'sweep@110.20:EQ', 'B1 sweep biết ở #23');
  eq(M.pools.B1.origin, 5, 'nến gốc vùng = nến ITH đầu (#5)');
  eq([st('S3', 24), st('S3', 25), st('S3', 27), st('S3', 28)], ['intact@95.00', 'pending@95.00', 'pending@95.00', 'run@95.00'], 'S3: run biết ở #28');
  eq([st('S5', 26), st('S5', 27)], ['pending@93.00', 'unresolved@93.00'], 'S5: chưa rõ (khoảng trống) ở #27');
  eq(st('B4', 34), 'pending@120.00', 'B4 đang chờ (chỉ từ pending_state)');
  eq(M.W, 3, 'cửa sổ W đọc từ cua_so');

  // «Hiện tại» tại con trỏ cuối
  const sel = V.selectCurrent(M);
  const ids = sel.pools.map((s) => s.id + ':' + s.state).sort();
  eq(ids, ['B1:sweep', 'B4:pending', 'B6:intact', 'B7:intact', 'S10:sweep', 'S11:sweep', 'S12:sweep', 'S2:intact', 'S3:run', 'S8:intact'],
    '«Hiện tại»: 2 vùng nguyên mỗi phía (S9 xa nhất bị bỏ) + ≤ 3 nhóm kết cục gần con trỏ nhất mỗi phía (S5 cũ nhất bị bỏ) + đang chờ');
  const sel9 = V.selectCurrent(M, { outcomePerSide: 9 });
  ok(sel9.pools.some((x) => x.id === 'S5' && x.state === 'unresolved'), 'nới outcomePerSide → có lại S5 (chưa rõ)');
  eq(sel.shifts.map((e) => e.event_id), [H.shiftId], 'shift gần nhất được giữ');
  const sel5 = V.selectCurrent(M, { recent: 5 });
  eq(sel5.pools.map((s) => s.id).sort(), ['B1', 'B4', 'B6', 'B7', 'S10', 'S11', 'S12', 'S2', 'S8'],
    'recent = 5: bỏ kết cục cũ (S3, S5) nhưng giữ B1 vì là vùng bị quét của shift đang hiện');
  // gộp vùng trùng
  const groups = V.groupPools(sel.pools, V.atrAt(M, last));
  const sweepSsl = groups.filter((g) => g.side === 'SSL' && g.state === 'sweep').map((g) => g.id).sort();
  eq(sweepSsl, ['pool:S10+S11', 'pool:S12'], 'gộp S10+S11 (cách 0.3 ≤ 0.5 ATR), S12 riêng (cách 1 ATR)');

  // đối tượng vẽ
  const dr = V.buildDrawing(M, sel, ident, { flow: true, shift: true });
  const seg = (id) => dr.segments.filter((x) => x.id === id && !x.noLine)[0];
  const b6 = seg('pool:B6');
  ok(b6 && b6.l1 === 2 && b6.l2 === last + 5 && b6.style === 'solid' && b6.label.text === 'BSL' && b6.label.pos === 'right',
    'vùng còn nguyên: từ nến gốc tới con trỏ + 5, nét liền, «BSL» ở đầu phải', b6 && J(b6));
  ok(b6 && b6.label.edgeText === 'BSL 130.00' && b6.autoscale === 'near' && b6.near === 3, 'vùng xa: nhãn mép + chỉ giãn trục khi ≤ 3 ATR', b6 && J(b6));
  const b1 = seg('pool:B1');
  ok(b1 && b1.l1 === 5 && b1.l2 === 22 && b1.style === 'dotted' && b1.label.text === 'sweep EQH' && b1.label.pos === 'end',
    'sweep: dừng ở nến lấy, nét chấm, «sweep EQH» sát nến lấy', b1 && J(b1));
  const box1 = dr.boxes.filter((x) => x.id === 'pool:B1')[0];
  ok(box1 && near(box1.l1, 21.55) && near(box1.l2, 23.45) && box1.p1 === 110.2 && box1.p2 === 110.8, 'hộp sweep: mức → đầu râu, nến lấy → nến quay lại', box1 && J(box1));
  const s3 = seg('pool:S3');
  ok(s3 && s3.l2 === 25 && s3.alpha > 0.4 && s3.alpha < 1 && s3.label.text === 'run', 'run: dừng ở nến lấy, mờ vừa phải, «run»', s3 && J(s3));
  const dr9 = V.buildDrawing(M, sel9, ident, { flow: true, shift: true });
  const s5 = dr9.segments.filter((x) => x.id === 'pool:S5')[0];
  ok(s5 && s5.style === 'dotted' && s5.label.text === 'chưa rõ' && s5.label.fallback === '?', 'chưa rõ: nét chấm xám', s5 && J(s5));
  ok(!seg('pool:S5'), '«Hiện tại»: vùng kết cục thứ 4 phía SSL không vẽ');
  const b4 = seg('pool:B4');
  ok(b4 && b4.style === 'dashed' && b4.l2 === last + 1 && b4.label.text === 'BSL bị lấy · chờ', 'đang chờ: nét đứt tới con trỏ, «BSL bị lấy · chờ»', b4 && J(b4));
  const g2 = seg('pool:S10+S11');
  ok(g2 && g2.label.text === 'sweep ×2', 'vùng gộp: «sweep ×2»', g2 && J(g2));
  const shs = seg('shift:' + H.shiftId);
  ok(shs && near(shs.l1, 21.55) && near(shs.l2, 24.45) && shs.p1 === 110.2 && shs.label.text === 'Shift ↓' && shs.label.pos === 'mid',
    'Shift: đoạn tại mức bị quét từ nến lấy tới nến displacement, «Shift ↓» giữa đoạn', shs && J(shs));
  const fvg = dr.boxes.filter((x) => x.id.indexOf('fvg:') === 0)[0];
  ok(fvg && near(fvg.l1, 23.55) && near(fvg.l2, 29.45) && fvg.borderStyle === 'dotted', 'FVG của shift: tới nến bị lấp (#29), viền chấm', fvg && J(fvg));
  eq(dr.counts.lines, 9, 'số đường vùng (10 vùng, 2 gộp thành 1)');
  // vùng đang chờ trùng nhau (cùng phía, cùng nến lấy, cách ≤ 0.5 ATR) gộp như sweep: «SSL bị lấy · chờ ×2»
  const M33 = V.buildModel(H.evs, H.tl, H.pendingAt(33), 33, 2);
  const d33 = V.buildDrawing(M33, V.selectCurrent(M33), ident, { flow: true, shift: true });
  const p33 = d33.segments.filter((x) => x.id === 'pool:S10+S11')[0];
  ok(p33 && p33.style === 'dashed' && p33.label.text === 'SSL bị lấy · chờ ×2' && d33.boxes.some((b) => b.id === 'pool:S10+S11' && b.p1 === 88.3 && b.p2 === 86.4),
    'đang chờ trùng nhau: một đường «SSL bị lấy · chờ ×2» + hộp phủ cả hai mức', p33 && J(p33));
  // ưu tiên nhãn cứng: shift gần nhất (1) > bị lấy · chờ (2) > còn nguyên gần nhất (3) > sweep/run gần con trỏ trước
  const pri = (id) => (seg(id) && seg(id).label ? seg(id).label.priority : null);
  ok(pri('shift:' + H.shiftId) === 1 && pri('pool:B4') === 2 && pri('pool:B6') === 3 && pri('pool:S10+S11') < pri('pool:S3') &&
    pri('pool:S3') < pri('pool:B1') && pri('pool:B1') < 5, 'thứ tự ưu tiên nhãn', [pri('shift:' + H.shiftId), pri('pool:B4'), pri('pool:B6'), pri('pool:S10+S11'), pri('pool:S3'), pri('pool:B1')]);
  ok(seg('pool:B1').label.fallback === '✕' && seg('pool:S3').label.fallback === '»' && seg('shift:' + H.shiftId).label.fallback === '▾',
    'ký hiệu thay chữ khi hết chỗ: sweep ✕, run », shift ▾');

  // nhân quả: replay từng con trỏ với pending_state của chính con trỏ đó
  const confirmedOf = {};
  H.evs.forEach((e) => { confirmedOf[e.event_id] = e.confirmed_bar_index; });
  for (let c = 0; c <= last; c++) {
    const Mc = V.buildModel(H.evs, H.tl, H.pendingAt(c), c, 2);
    const sc = V.selectCurrent(Mc);
    const dc = V.buildDrawing(Mc, sc, ident, {});
    dc.segments.concat(dc.boxes).forEach(function (it) {
      if (it.id.indexOf('pool:') === 0) {
        it.id.slice(5).split('+').forEach(function (pid) {
          const p = Mc.pools[pid];
          ok(p && p.known <= c, 'vùng ' + pid + ' hiện ở con trỏ ' + c + ' trước nến xác nhận', p && p.known);
          if (p && p.outcome) ok(p.resolved <= c, 'kết cục ' + pid + ' hiện trước nến xác nhận (con trỏ ' + c + ')');
        });
        ok(it.l1 <= c + 0.5 || it.noLine, 'đường vùng bắt đầu sau con trỏ ' + c, J(it));
      } else if (it.id.indexOf('shift:') === 0) {
        ok(confirmedOf[it.id.slice(6)] <= c, 'shift hiện trước nến xác nhận (con trỏ ' + c + ')');
      } else if (it.id.indexOf('fvg:') === 0) {
        ok(confirmedOf[it.id.slice(4)] <= c, 'FVG hiện trước nến xác nhận (con trỏ ' + c + ')');
      }
    });
    const has = (id) => dc.segments.concat(dc.boxes).some((x) => x.id === id);
    ok(has('shift:' + H.shiftId) === (c >= 24), 'shift chỉ từ #24 (con trỏ ' + c + ')');
    ok(dc.boxes.some((x) => x.id.indexOf('fvg:') === 0) === (c >= 25), 'hộp FVG chỉ từ #25 (con trỏ ' + c + ')');
    const sB1 = dc.segments.filter((x) => x.id === 'pool:B1')[0];
    if (c < 8) ok(!sB1, 'B1 chưa hiện trước #8 (con trỏ ' + c + ')');
    if (c === 8) ok(sB1 && sB1.label.text === 'BSL', 'B1 hiện ở #8 với nhãn BSL');
    if (c === 15) ok(sB1 && sB1.label.text === 'EQH' && sB1.p1 === 110.2, 'B1 thành EQH ở #15');
    if (c === 22) ok(sB1 && sB1.style === 'dashed' && /chờ/.test(sB1.label.text), 'B1 đang chờ ở #22');
    if (c === 23) ok(sB1 && sB1.style === 'dotted', 'B1 thành sweep ở #23');
  }

  // dải order flow + dòng trạng thái + tooltip
  const band = V.bandBars(M, ident);
  const segs = [];
  band.forEach((b) => { if (!segs.length || segs[segs.length - 1].key !== b.key) segs.push({ key: b.key, text: b.text }); });
  eq(segs, [{ key: 'null|null', text: 'chưa có' }, { key: '-1|24', text: '↓ shift' }], 'dải order flow: «chưa có» rồi «↓ shift»');
  const s30 = J(V.statusAt(M, 30, 100));
  eq([s30.word, s30.since, s30.why], ['GIẢM', '01/01 02:00', 'shift giảm: quét BSL 110.20'], 'trạng thái hàng 1 ở #30');
  eq(s30.near, 'Vùng dưới gần nhất: SSL 90.00 (cách 10.0 ATR)', 'trạng thái: vùng dưới gần nhất + khoảng cách ATR');
  eq(s30.change, 'Đổi khi: run BSL 120.00 → chưa rõ · shift tăng → tăng', 'trạng thái: đổi khi');
  const s33 = J(V.statusAt(M, 33, 100));
  eq(s33.pending, 'Đang chờ: BSL 120.00, SSL 88.00, SSL 88.30, SSL 87.00 bị lấy lúc 02:45, ≤ 3 nến nữa biết sweep hay run',
    'trạng thái: đang chờ ở #33 (gom theo nến lấy)');
  eq(V.statusAt(M, 26, 100).pending, 'Đang chờ: SSL 95.00 bị lấy lúc 02:05, ≤ 2 nến nữa biết sweep hay run; SSL 93.00 bị lấy lúc 02:10, ≤ 3 nến nữa biết sweep hay run',
    'trạng thái: hai nến lấy khác nhau ở #26');
  const t1 = J(V.objectInfo(M, 'pool:B1'));
  ok(t1 && t1[0].head === 'Sweep EQH 110.20' && t1[0].body === 'lấy ở #22, close quay lại ở #23 (sau 1 nến), quét sâu 0.60 ATR',
    'tooltip sweep', t1);
  const t6 = J(V.objectInfo(M, 'pool:B6'));
  ok(t6 && t6[0].head === 'BSL 130.00' && t6[0].body === 'từ ITH 01/01 00:10 (#2), biết lúc #4 · còn nguyên', 'tooltip vùng còn nguyên', t6);
  const tsh = J(V.objectInfo(M, 'shift:' + H.shiftId));
  ok(tsh && tsh.length === 2 && /^quét BSL 110\.20 \(lấy #22, sweep #23\) → displacement giảm ở #24/.test(tsh[0].body) && /đã lấp ở #29/.test(tsh[1].body),
    'tooltip shift + FVG', tsh);

  // kết quả cũ: timeline không có order_flow, run thiếu khoá pools → không lỗi
  const oldTl = H.tl.map((p) => { const q = Object.assign({}, p); delete q.order_flow; delete q.order_flow_since; delete q.order_flow_reason; return q; });
  const oldEv = H.evs.map((e) => {
    if (e.structure_type !== 'LIQ_RUN_DOWN') return e;
    const x = Object.assign({}, e.details); delete x.pools; return Object.assign({}, e, { details: x });
  }).filter((e) => e.structure_type.indexOf('ORDER_FLOW') !== 0);
  let threw = null, Mo = null;
  try {
    Mo = V.buildModel(oldEv, oldTl, null, Infinity, 2);
    V.buildDrawing(Mo, V.selectCurrent(Mo), ident, {});
    ok(V.bandBars(Mo, ident).length === 0, 'kết quả cũ: dải rỗng');
    ok(V.statusAt(Mo, 30, 100).hasOF === false, 'kết quả cũ: trạng thái không có order flow');
    ok(V.poolAt(Mo.pools.S3, last).state === 'run', 'run thiếu khoá pools vẫn đọc được từ vùng chính');
  } catch (e) { threw = String(e && e.stack || e); }
  ok(threw === null, 'kết quả cũ không lỗi', threw);
  ok(V.buildModel([], [{ bar_index: 0, time: 1704067200 }], null, 0, 2) === null, 'timeline không phải ICT → null');
  ok(V.statusAt(Mo, 30, 100).htf === null && V.htfStatusAt(M, 30) === null, 'kết quả trước 0.4.0 (không có cột htf_*): không có ngữ cảnh khung lớn');
  runHandDetail(H);
  runHandHtf();
  runHandMss(H);
}

/** Lõi 0.10.0: cùng kịch bản, sự kiện đổi hướng là MSS (thay SHIFT_DOWN) — đoạn ngang tại STL bị phá từ nến STL tới nến phá,
 *  «MSS ↓», FVG của nến phá, chữ order flow / dòng trạng thái theo MSS. */
function runHandMss(H) {
  const last = H.N - 1, mid = 'ict:MSS_DOWN@24>24';
  const evs = J(H.evs).map(function (e) {
    if (e.event_id === H.shiftId) {
      const x = e.details;
      return Object.assign(e, { event_id: mid, structure_type: 'MSS_DOWN', price: 105, details: { chieu: 'down', killzone: null,
        moc_pha: 105, moc_pha_ten: 'STL', nen_moc_pha: 20, moc_pha_id: 'ict:SWING_LOW@20>21', significant: false, moc_significant: 93,
        muc_bi_quet: x.muc_bi_quet, cuc_tri_cu_quet: x.cuc_tri_cu_quet, nen_sweep: x.nen_sweep, so_nen_tu_sweep: x.so_nen_tu_sweep,
        swept: x.swept, chan: { nen_dau: 22, cuc_tri: 110.8, so_nen: 3, bien_do: 2.3, bien_do_atr: 2.3, atr: 1, nguong_atr: 2, toi_da_nen: 5 },
        fvg_trong_chan: null, group_id: x.group_id } });
    }
    if (e.structure_type === 'SHIFT_FVG_DOWN') {
      return Object.assign(e, { event_id: 'ict:MSS_FVG_DOWN@24>25', structure_type: 'MSS_FVG_DOWN', reference_event_id: mid,
        details: { mss: mid, fvg: e.details.fvg,
        lo: e.details.lo, hi: e.details.hi, nen_pha: 24, killzone: null } });
    }
    if (e.reference_event_id === H.shiftId) {
      e.reference_event_id = mid;
      if (e.details.ly_do === 'shift_giam') e.details.ly_do = 'mss_giam';
      e.details.basis = [mid];
    }
    return e;
  });
  const tl = J(H.tl).map(function (p) { p.pending_mss = 0; return p; });
  const M = V.buildModel(evs, tl, H.pendingAt(last), last, 2);
  eq([M.flip, M.shifts.length, !!M.shiftFvg[mid]], ['MSS', 1, true], 'MSS: M.flip = MSS (có cột pending_mss), MSS vào danh sách đổi hướng + FVG của nó');
  const dr = V.buildDrawing(M, V.selectCurrent(M), ident, { flow: true, shift: true });
  const ms = dr.segments.filter((x) => x.id === 'shift:' + mid && x.label)[0];
  ok(ms && near(ms.l1, 19.55) && near(ms.l2, 24.45) && ms.p1 === 105 && ms.label.text === 'MSS ↓',
    'MSS: đoạn tại STL bị phá (105) từ nến STL #20 tới nến phá #24, «MSS ↓»', ms && J(ms));
  const fb = dr.boxes.filter((x) => x.id === 'fvg:ict:MSS_FVG_DOWN@24>25')[0];
  ok(fb && near(fb.l1, 23.55), 'FVG của MSS bắt đầu ở nến phá', fb && J(fb));
  const head = V.objectInfo(M, 'shift:' + mid, {})[0];
  ok(head.head.indexOf('MSS giảm') === 0 && head.body.indexOf('phá STL 105') > 0, 'tooltip MSS', J(head));
  const st = V.statusAt(M, 24, 108.5);
  ok(st.why.indexOf('MSS giảm: quét BSL 110.20, phá STL 105.00') === 0 && st.change.indexOf('MSS tăng → tăng') > 0,
    'dòng trạng thái: vì sao = MSS, «Đổi khi: … MSS tăng → tăng»', J(st));
}

// ------------------------------------------------------------------ khung lớn (lõi 0.4.0) — kịch bản dựng tay

/** Nến M15 từ 02/01/2024 06:00 UTC (01:00 New York, EST) → ô H4 mốc ny_1700: #0–15 (06–10 UTC), #16–31, #32–47, #48–63. */
function htfScenario() {
  const T0 = Date.UTC(2024, 0, 2, 6, 0) / 1000, STEP = 900, N = 60;
  const bars = [];
  for (let i = 0; i < N; i++) {
    const o = 100 + 0.1 * i + (i % 3 === 0 ? 0.4 : 0);
    bars.push({ index: i, open: o, high: o + 1 + (i % 5) * 0.1, low: o - 1 - (i % 4) * 0.1, close: o + (i % 2 ? 0.3 : -0.2) });
  }
  const iso = (i) => new Date((T0 + STEP * i) * 1000).toISOString().replace('.000Z', '+00:00');
  const evs = [];
  function ev(type, bar, conf, price, details, ref, sfx) {
    const id = 'ict:' + type + '@' + bar + '>' + conf + (sfx ? ':' + sfx : '');
    const e = { event_id: id, structure_type: type, event_bar_index: bar, confirmed_bar_index: conf, price: price, direction: null,
      algorithm: 'ict_structure', reference_event_id: ref || null, details: Object.assign({ killzone: null }, details || {}) };
    evs.push(e);
    return e;
  }
  const pool = (tang, phia, vung, muc, conf, status) => ({ trang_thai: status || 'tao_moi', phia: phia, tang: tang, vung: vung, muc_vung: muc,
    hieu_luc_tu_nen: conf + 1 });
  // khung chạy + H1 cùng đỉnh #5 (110) → hai vùng cùng mức; H4: ITH #20 (120, HH), ITL #10 (90)
  ev('SWING_HIGH_L2', 5, 8, 110, { cap_cau_truc: true, vung_thanh_khoan: pool('M15', 'BSL', 'B1', 110, 8) });
  ev('HTF_SWING_HIGH', 5, 12, 110, { khung: 'H1', ten: 'ITH', mo_nen_htf: iso(4), known_at: iso(12), period_end: iso(12), chot_muon: false,
    order_sau: null, vung_thanh_khoan: pool('H1', 'BSL', 'B2', 110, 12) }, null, 'H1');
  const sw4 = ev('HTF_SWING_HIGH', 20, 33, 120, { khung: 'H4', ten: 'ITH', nhan: 'HH', gia_truoc: 118, mo_nen_htf: iso(16), known_at: iso(32),
    period_end: iso(32), chot_muon: false, order_sau: 1, order_sau_vi: 'tăng (HH + HL)', vung_thanh_khoan: pool('H4', 'BSL', 'B3', 120, 33) }, null, 'H4');
  ev('HTF_SWING_LOW', 10, 31, 90, { khung: 'H4', ten: 'ITL', mo_nen_htf: iso(0), known_at: iso(31), period_end: iso(31), chot_muon: false,
    vung_thanh_khoan: pool('H4', 'SSL', 'S4', 90, 31) }, null, 'H4');
  ev('HTF_PERIOD_HIGH', 2, 40, 125, { khung: 'D', ten: 'PDH', muc: 125, mo_ky: '2024-01-01T22:00:00+00:00', period_end: iso(40),
    known_at: iso(40), chot_muon: false, vung_thanh_khoan: pool('D', 'BSL', 'B5', 125, 40) }, null, 'D');
  ev('HTF_PERIOD_LOW', 3, 41, 80, { khung: 'W', ten: 'PWL', muc: 80, mo_ky: '2023-12-31T22:00:00+00:00', period_end: iso(41),
    known_at: iso(41), chot_muon: false, vung_thanh_khoan: pool('W', 'SSL', 'S6', 80, 41) }, null, 'W');
  const f4 = ev('HTF_FVG_UP', 16, 47, 101, { khung: 'H4', lo: 100, hi: 102, ce: 101, nen_giua_tu: 16, nen_giua_den: 31, mo_nen_giua: iso(16),
    known_at: iso(47), from_displacement: true, hieu_luc_tu_nen: 48 }, null, 'H4');
  const f1 = ev('HTF_FVG_DOWN', 36, 43, 104.5, { khung: 'H1', lo: 104, hi: 105, ce: 104.5, nen_giua_tu: 36, nen_giua_den: 39, mo_nen_giua: iso(36),
    known_at: iso(43), from_displacement: false, hieu_luc_tu_nen: 44 }, null, 'H1');
  const f4b = ev('HTF_FVG_UP', 40, 55, 95.5, { khung: 'H4', lo: 95, hi: 96, ce: 95.5, nen_giua_tu: 40, nen_giua_den: 47, mo_nen_giua: iso(40),
    known_at: iso(55), from_displacement: false, hieu_luc_tu_nen: 56 }, null, 'H4');
  const pd = ev('PD_DISRESPECT_UP', 52, 52, 99, { khung: 'H4', fvg: f4.event_id, chieu_fvg: 'up', lo: 100, hi: 102, ce: 101, ket_qua: 'disrespect',
    quy_tac_vi: 'close < mép xa (lo)', close: 99, nen_cham: 50, so_nen_tu_cham: 2, chieu_ham_y: -1, pd_bias_sau: -1, pd_bias_khung: 'H4' },
  f4.event_id, 'H4.16');
  pd.direction = 'down';
  const brief = (id, phia, muc, tang, taken, extreme) => ({ id: id, phia: phia, muc: muc, tang: tang, nguon: [], nen_lay: taken, atr_khoa: 1,
    xuyen_atr: 0.5, cuc_tri_cu_quet: extreme });
  ev('LIQ_RUN_UP', 45, 48, 110, { phia: 'BSL', muc: 110, vung: 'B2', tang: 'H1', nen_lay: 45, cua_so: 3, so_vung: 2, so_nen_sau_lay: 3,
    pools: [brief('B1', 'BSL', 110, 'M15', 45, 111), brief('B2', 'BSL', 110, 'H1', 45, 111)] });
  ev('LIQ_SWEEP_BSL', 50, 51, 125, { phia: 'BSL', muc: 125, vung: 'B5', tang: 'D', nen_lay: 50, cua_so: 3, so_vung: 1, sweep_bars: 1,
    pools: [Object.assign(brief('B5', 'BSL', 125, 'D', 50, 125.6), { sweep_bars: 1 })] });
  const sh = ev('SHIFT_UP', 54, 54, 104, { chieu: 'up', muc_bi_quet: 90, nen_sweep: 53, swept: [] });
  ev('DOL_REACHED', 58, 58, 120, { chieu_dol: 1, vung: brief('B3', 'BSL', 120, 'H4', 58, 120.4), muc: 120, tang: 'H4', phia: 'BSL',
    shift: sh.event_id, nen_dat_dol: 54, so_nen_tu_shift: 4, xuyen_atr: 0.4 }, sh.event_id);
  evs.sort((a, b) => a.confirmed_bar_index - b.confirmed_bar_index);
  // timeline: thứ tự H4 tăng từ #33; range H4 [90, 120] từ #33; pd_bias giảm (H4) từ #52; DOL lên đích B3 (H4, 120) #54–#57
  const lastClose = (i) => (i >= 15 ? (i >= 31 ? (i >= 47 ? 47 : 31) : 15) : null);
  const tl = [];
  for (let i = 0; i < N; i++) {
    const c = bars[i].close, hasR = i >= 33;
    tl.push({ bar_index: i, time: T0 + STEP * i, atr: 1, dealing_hi: null, liq_above: null, liq_above_id: null, liq_below: null, liq_below_id: null,
      order_flow: null, order_flow_since: null, order_flow_reason: null,
      htf_H1_order: i >= 12 ? 0 : null, htf_H4_order: i >= 33 ? 1 : null, htf_H4_zone: hasR ? (c > 105 ? 'premium' : 'discount') : null,
      htf_H4_range_pos: hasR ? (c - 90) / 30 : null, htf_H4_age: lastClose(i) === null ? null : i - lastClose(i),
      htf_H4_dealing_hi: hasR ? 120 : null, htf_H4_dealing_lo: hasR ? 90 : null,
      pd_bias: i >= 52 ? -1 : null, pd_bias_tf: i >= 52 ? 'H4' : null,
      dol_side: i >= 54 && i < 58 ? 1 : null, dol_target: i >= 54 && i < 58 ? 120 : null, dol_tier: i >= 54 && i < 58 ? 'H4' : null,
      dol_dist_atr: i >= 54 && i < 58 ? 120 - c : null, pdh_taken: i >= 40 ? i >= 50 : null, pdl_taken: null });
  }
  return { bars: bars, evs: evs, tl: tl, N: N, T0: T0, f4: f4, f1: f1, f4b: f4b, pd: pd, sw4: sw4, sh: sh };
}

const ALL_HTF = { swing: true, range: true, fvg: true, levels: true, forming: true, h1: false };

function runHandHtf() {
  const H = htfScenario();
  const last = H.N - 1;
  const barOf = (i) => H.bars[i] || null;
  // mốc ô H4 ny_1700 (EST): 06:00 UTC = 01:00 New York → ô 01–05 NY đóng 10:00 UTC; mùa hè (EDT) 05:00 UTC
  const bk = V.h4Bucket(H.T0);
  eq(bk && bk.end, H.T0 + 4 * 3600, 'ô H4 mốc 17:00 New York (mùa đông): 06:00 → 10:00 UTC');
  const summer = Date.UTC(2024, 3, 2, 17, 0) / 1000;   // 02/04/2024 17:00 UTC = 13:00 EDT → ô 13–17 NY đóng 21:00 UTC
  eq(V.h4Bucket(summer).end, summer + 4 * 3600, 'ô H4 mùa hè: 17:00 → 21:00 UTC');
  eq(V.h4Bucket(summer + 3 * 3600 + 2700).end, summer + 4 * 3600, 'nến 20:45 UTC cùng ô 17–21 UTC');
  const winterDay = Date.UTC(2024, 0, 2, 22, 0) / 1000;   // 17:00 EST: ô đầu ngày giao dịch (17–21 NY, gồm giờ nghỉ)
  eq(V.h4Bucket(winterDay).end, winterDay + 4 * 3600, 'ô H4 đầu ngày giao dịch bắt đầu 17:00 New York');

  // ---- vùng theo tầng (Gọn) tại #44: B1 (M15) + B2 (H1) cùng mức 110 → một đường «BSL H1»; B3 «BSL H4»; S4 «SSL H4», S6 «PWL»
  const M44 = V.buildModel(H.evs, H.tl, null, 44, 2);
  const s44 = V.selectCurrent(M44);
  eq(s44.pools.map((s) => s.id).sort(), ['B1', 'B2', 'B3', 'S4', 'S6'], '2 MỨC còn nguyên gần nhất mỗi phía (vùng cùng mức tính một): PDH 125 ngoài 2 mức gần nhất');
  const d44 = V.buildDrawing(M44, s44, ident, { flow: true, shift: true });
  const seg44 = (id) => d44.segments.filter((x) => x.id === id && !x.noLine)[0];
  const b12 = seg44('pool:B1+B2');
  ok(b12 && b12.label.text === 'BSL H1' && near(b12.width, 1.9) && b12.l1 === 5, 'hai vùng cùng mức (M15 + H1) → một đường, tên tầng cao nhất «BSL H1»', b12 && J(b12));
  const b3 = seg44('pool:B3'), s4 = seg44('pool:S4'), s6 = seg44('pool:S6');
  ok(b3 && b3.label.text === 'BSL H4' && near(b3.width, 2.3) && b3.label.edgeText === 'BSL H4 120.00', 'vùng H4: «BSL H4», nét 2.3', b3 && J(b3));
  ok(s4 && s4.label.text === 'SSL H4' && s6 && s6.label.text === 'PWL' && near(s6.width, 2.7), 'vùng W: «PWL», nét đậm nhất', [s4 && J(s4), s6 && J(s6)]);
  ok(d44.counts.lines === 4 && d44.counts.intact === 5 && d44.counts.htfTier === 4, 'đếm: 4 đường cho 5 vùng', J(d44.counts));
  const M41 = V.buildModel(H.evs, H.tl, null, 41, 2);
  const d41 = V.buildDrawing(M41, V.selectCurrent(M41, { allIntact: true }), ident, { flow: true, shift: true });
  const pdh = d41.segments.filter((x) => x.id === 'pool:B5')[0];
  ok(pdh && pdh.label.text === 'PDH' && pdh.l1 === 2, 'PDH (tầng D) vẽ từ nến đạt mức', pdh && J(pdh));
  ok(!V.buildDrawing(V.buildModel(H.evs, H.tl, null, 39, 2), V.selectCurrent(V.buildModel(H.evs, H.tl, null, 39, 2), { allIntact: true }), ident, {})
    .segments.some((x) => x.id.indexOf('B5') >= 0), 'PDH chưa hiện trước nến biết (#40)');
  // tooltip theo tầng
  const tB3 = J(V.objectInfo(M44, 'pool:B3'));
  ok(tB3 && tB3[0].head === 'BSL H4 120.00' && /^tầng H4 \(ITH\/ITL H4\) — từ ITH H4 02\/01 11:00 \(#20; nến H4 mở 02\/01 10:00\), biết lúc #33 \(nến H4 chốt 02\/01 14:00\) · còn nguyên$/.test(tB3[0].body),
    'tooltip vùng H4: tầng, nến H4 nguồn, lúc biết (known_at)', tB3);
  const tB12 = J(V.objectInfo(M44, 'pool:B1+B2'));
  ok(tB12 && tB12.length === 1 && /^BSL H1 110\.00 — cùng mức 2 tầng: BSL, BSL H1$/.test(tB12[0].head) && /BSL: từ ITH .* \| BSL H1: tầng H1/.test(tB12[0].more),
    'tooltip hai vùng cùng mức: một dòng, nguồn từng tầng', tB12);
  const tB5 = J(V.objectInfo(M41, 'pool:B5'));
  ok(tB5 && /^mức ngày \(D\) — từ PDH 02\/01 06:30 \(#2; kỳ 01\/01 22:00 → 02\/01 16:00\), biết lúc #40 \(kỳ chốt 02\/01 16:00\)/.test(tB5[0].body), 'tooltip PDH: kỳ ngày + lúc biết', tB5);
  // kết cục theo tầng ở con trỏ cuối: run của B1+B2 → «run H1»; sweep PDH → «sweep PDH» + hộp
  const ML = V.buildModel(H.evs, H.tl, null, last, 2);
  const dL = V.buildDrawing(ML, V.selectCurrent(ML), ident, { flow: true, shift: true });
  const segL = (id) => dL.segments.filter((x) => x.id === id && !x.noLine)[0];
  ok(segL('pool:B1+B2') && segL('pool:B1+B2').label.text === 'run H1', 'run hai tầng cùng mức → «run H1»', segL('pool:B1+B2') && J(segL('pool:B1+B2')));
  ok(segL('pool:B5') && segL('pool:B5').label.text === 'sweep PDH' && dL.boxes.some((b) => b.id === 'pool:B5'), 'sweep PDH: «sweep PDH» + hộp quét',
    segL('pool:B5') && J(segL('pool:B5')));
  eq(V.groupPools([V.poolAt(ML.pools.B5, last), V.poolAt(ML.pools.B1, last)], 1).length, 2, 'không gộp kết cục khác nhau');

  // ---- lớp khung lớn: nhân quả ở MỌI con trỏ, FVG H4 đóng đúng lúc PD_*, mức theo kỳ, range, nến đang hình thành
  const conf = {};
  H.evs.forEach((e) => { conf[e.event_id] = e.confirmed_bar_index; });
  for (let c = 0; c <= last; c++) {
    const Mc = V.buildModel(H.evs, H.tl, null, c, 2);
    const close = H.bars[c].close;
    [false, true].forEach(function (hist) {
      const sc = V.selectCurrent(Mc, { close: close, history: hist, htf: Object.assign({}, ALL_HTF, { h1: hist }) });
      const dc = J(V.buildDrawing(Mc, sc, ident, { flow: false, shift: false, history: hist, htf: Object.assign({}, ALL_HTF, { h1: hist }), barOf: barOf }));
      dc.segments.concat(dc.boxes).forEach(function (it) {
        const k = it.id.slice(0, it.id.indexOf(':')), rest = it.id.slice(it.id.indexOf(':') + 1);
        if (k === 'htfsw' || k === 'htffvg' || k === 'lvl') ok(conf[rest] <= c, 'khung lớn: ' + it.id + ' hiện trước nến xác nhận (con trỏ ' + c + ')', conf[rest]);
        if (k === 'htfrange') ok(c >= 33, 'range H4 hiện trước khi có (con trỏ ' + c + ')');
        if (k === 'forming') ok(it.l1 >= 47.5 || c < 48, 'nến H4 đang hình thành sai ô (con trỏ ' + c + ')', it);
      });
      const fb = dc.boxes.filter((b) => b.id === 'htffvg:' + H.f4.event_id)[0];
      if (c < 47) ok(!fb, 'FVG H4 chưa hiện trước #47 (con trỏ ' + c + ')');
      else if (c < 52) ok(fb && fb.l2 === c + 5 && fb.borderStyle === 'solid' && near(fb.l1, 15.55) && fb.borderWidth === 2,
        'FVG H4 còn mở: từ nến giữa H4 tới con trỏ + 5, viền liền dày (con trỏ ' + c + ')', fb);
      else ok(fb && near(fb.l2, 52.45) && fb.borderStyle === 'dotted', 'FVG H4 dừng đúng ở nến PD_* #52, viền chấm (con trỏ ' + c + ')', fb);
      const fl = dc.segments.filter((s) => s.id === 'htffvg:' + H.f4.event_id)[0];
      if (c >= 47) ok(fl && fl.label.text === (c >= 52 ? 'FVG H4 · disrespect' : 'FVG H4'), 'chữ FVG H4 (con trỏ ' + c + ')', fl && fl.label);
      const h1b = dc.boxes.some((b) => b.id === 'htffvg:' + H.f1.event_id);
      ok(h1b === (hist && c >= 43), 'FVG H1 chỉ khi bật «Thêm H1» và đã biết (con trỏ ' + c + ', H1 ' + hist + ')');
      const rg = dc.segments.filter((s) => s.id === 'htfrange:H4:eq')[0];
      if (c >= 33) ok(rg && rg.p1 === 105 && near(rg.l1, 9.55) && rg.label.text === 'EQ H4', 'EQ H4 = 105, vẽ từ mốc ITL H4 #10 (con trỏ ' + c + ')', rg);
      const lv = dc.segments.filter((s) => s.id === 'lvl:' + 'ict:HTF_PERIOD_HIGH@2>40:D');
      if (c < 40) ok(lv.length === 0, 'PDH chưa hiện trước #40 (con trỏ ' + c + ')');
      else if (c < 51) ok(lv.length === 1 && lv[0].l2 === c + 5 && lv[0].label.text === 'PDH', 'PDH còn nguyên: liền tới con trỏ + 5 (con trỏ ' + c + ')', lv);
      else ok(lv.length === 2 && lv[0].l2 === 50 && lv[1].style === 'dotted' && lv[1].label.text === 'PDH · đã lấy', 'PDH bị lấy ở #50: liền tới #50 rồi chấm «· đã lấy» (con trỏ ' + c + ')', lv);
      const sw = dc.segments.filter((s) => s.id === 'htfsw:' + H.sw4.event_id)[0];
      if (c >= 33) ok(sw && sw.dot.ring && sw.label.text === 'HH H4' && sw.l1 === 20, 'ITH H4: vòng tròn rỗng «HH H4» tại nến chạm đỉnh (con trỏ ' + c + ')', sw);
    });
    // nến H4 đang hình thành: chỉ đọc nến ≤ con trỏ; khớp gộp tay theo ô H4
    let maxAsk = -1;
    const fm = J(V.formingAt(Mc, c, (i) => { maxAsk = Math.max(maxAsk, i); return H.bars[i]; }));
    ok(maxAsk <= c, 'nến đang hình thành không đọc nến sau con trỏ (con trỏ ' + c + ')', maxAsk);
    const start = Math.floor(c / 16) * 16, closed = c % 16 === 15;
    if (c === 0) ok(fm === null, 'con trỏ #0: chưa biết bước nến → không vẽ nến đang hình thành', fm);
    else if (closed) ok(fm === null, 'nến cuối ô H4 → nến H4 vừa chốt, không có nến đang hình thành (con trỏ ' + c + ')', fm);
    else {
      const seg = H.bars.slice(start, c + 1);
      const want = { start: start, end: start + 15, open: seg[0].open, high: Math.max.apply(null, seg.map((b) => b.high)),
        low: Math.min.apply(null, seg.map((b) => b.low)), close: seg[seg.length - 1].close, n: seg.length, expected: 16 };
      ok(fm && Object.keys(want).every((k) => fm[k] === want[k]) && fm.from === 'gộp', 'nến H4 đang hình thành = gộp nến ' + start + '…' + c, { fm: fm, want: want });
    }
    // dữ liệu sau con trỏ đổi → không đổi gì
    const bars2 = H.bars.map((b) => (b.index > c ? { index: b.index, open: 1, high: 999, low: -999, close: 5 } : b));
    eq(J(V.formingAt(Mc, c, (i) => bars2[i])), fm, 'sửa nến sau con trỏ không đổi nến đang hình thành (con trỏ ' + c + ')');
  }
  // tại đúng con trỏ có pending_state: lấy period_end / số nến kỳ vọng của lõi
  const pend = { khung_lon: { bat: true, H4: { dang_hinh_thanh: { nen_dau: 48, nen_cuoi: 57, n_bars: 10, expected_bars: 14, period_end: '2024-01-02T22:00:00+00:00' } } } };
  const fmP = V.formingAt(V.buildModel(H.evs, H.tl, pend, 57, 2), 57, barOf);
  ok(fmP && fmP.from === 'lõi' && fmP.expected === 14 && fmP.end === 61, 'con trỏ có pending_state: số nến kỳ vọng của lõi', fmP && J(fmP));
  const fmQ = V.formingAt(V.buildModel(H.evs, H.tl, pend, 56, 2), 56, barOf);
  ok(fmQ && fmQ.from === 'gộp', 'pending_state của nến khác → không dùng', fmQ && J(fmQ));
  // ngày đóng sớm: lõi chốt nến H4 giữa ô danh nghĩa (htf_H4_age = 0 ở #40, #39 cùng ô) → không còn nến đang hình thành
  const tlE = H.tl.map((p) => Object.assign({}, p));
  tlE[40].htf_H4_age = 0;
  ok(V.formingAt(V.buildModel(H.evs, tlE, null, 40, 2), 40, barOf) === null, 'lõi chốt H4 sớm ở #40 (đóng sớm theo lịch) → không vẽ nến đang hình thành');
  ok(V.formingAt(V.buildModel(H.evs, H.tl, null, 40, 2), 40, barOf) !== null, 'không chốt ở #40 → vẫn có nến đang hình thành');
  const tlL = H.tl.map((p) => Object.assign({}, p));
  tlL[48].htf_H4_age = 0;   // #48 là nến đầu ô mới: chốt muộn ô trước → nến h mở ô mới, vẫn vẽ
  ok(V.formingAt(V.buildModel(H.evs, tlL, null, 48, 2), 48, barOf) !== null, 'chốt muộn ô trước ở nến đầu ô mới → vẫn vẽ nến đang hình thành của ô mới');
  // Hiện tại vs Lịch sử: FVG H4 thứ hai (#55) mở; FVG đã disrespect vẫn hiện vì là nguồn pd_bias
  const MH = V.buildModel(H.evs, H.tl, null, last, 2);
  const sH = V.selectCurrent(MH, { close: 100, htf: ALL_HTF });
  eq(sH.htf.fvgs.map((e) => e.event_id), [H.f4.event_id, H.f4b.event_id], 'FVG «Hiện tại»: FVG H4 mở + FVG đặt pd_bias (đã disrespect)');
  eq(Object.keys(sH.htf.pdSrc), [H.f4.event_id], 'nguồn pd_bias = FVG của PD_* gần nhất');
  const far = V.selectCurrent(MH, { close: 200, htf: ALL_HTF }).htf.fvgs.map((e) => e.event_id);
  eq(far, [H.f4.event_id], 'FVG H4 mở nhưng xa > 10 ATR → không ở «Hiện tại» (FVG nguồn pd_bias vẫn hiện)');

  // ---- dòng trạng thái: ngữ cảnh khung lớn gọn + câu đầy đủ
  const st56 = J(V.htfStatusAt(MH, 56));
  eq(st56.text, 'H4 ↑ · ' + (H.bars[56].close > 105 ? 'premium ' : 'discount ') + Math.round((H.bars[56].close - 90) / 30 * 100) + '% · pd ↓ H4 · DOL ↑ BSL H4 120.00 (' + (120 - H.bars[56].close).toFixed(1) + ' ATR)',
    'trạng thái khung lớn ở #56');
  ok(/^Khung lớn \(chỉ nến đã chốt\): thứ tự H4 tăng \(từ 02\/01 14:15\), H1 lẫn lộn; giá ở (premium|discount) \d+% của dealing range H4 90\.00–120\.00; pd_bias giảm \(FVG H4\) từ 02\/01 19:00; DOL lên: đích BSL H4 120\.00, cách [\d.]+ ATR\.$/.test(st56.title),
    'câu đầy đủ (title) của trạng thái khung lớn', st56.title);
  eq(J(V.htfStatusAt(MH, 20)).text, 'H4 – · pd – · DOL –', 'trạng thái khung lớn khi chưa có gì (khởi động)');
  eq(J(V.statusAt(MH, 58, 100)).htf.text.slice(-5), 'DOL –', 'đích DOL bị lấy (#58) → DOL –');

  // ---- khung «Thuật toán đang làm gì»: một dòng mỗi thành phần, từ pending_state
  const ps = {
    khung_lon: {
      bat: true,
      ngu_canh: {
        H1: { ready: true, order: 0, order_age_bars: 3, zone: 'premium', range_pos: 0.64, age_ltf_bars: 1, protected: null },
        H4: { ready: true, order: 1, order_age_bars: 7, zone: 'discount', range_pos: 0.31, age_ltf_bars: 5, protected: 2318.4, protected_broken: false },
        levels: { pdh: 2339.1, pdl: 2301.7, pdh_taken: false, pdl_taken: true, pwh: null, pwl: 2290, pwh_taken: null, pwl_taken: false,
          day_open: 2312, midnight_open: null }
      },
      H1: { dealing_range: { hi: 2341, lo: 2300 } },
      H4: { dealing_range: { hi: 2341, lo: 2301.7 }, dang_hinh_thanh: { mo: '2024-03-28T17:00:00+00:00', period_end: '2024-03-28T21:00:00+00:00',
        open: 2310, high: 2315, low: 2305, close: 2312, n_bars: 7, expected_bars: 16 } }
    },
    pd: { pd_bias: -1, pd_bias_vi: 'giảm', khung: 'H1', tu_nen: 95, so_nen: 5, su_kien: ['ict:PD_DISRESPECT_UP@95>95:H1.80'] },
    dol: { side: 1, target: 2341.0, tier: 'H1', dist_atr: 4.2, vung: { id: 'B9', phia: 'BSL', muc: 2341, tang: 'H1', nguon: ['ict:HTF_SWING_HIGH@60>70:H1'] },
      shift: 'ict:SHIFT_UP@88>88', tu_nen: 88, so_nen: 12, tang_toi_thieu: 'H1' }
  };
  const xl = J(V.htfExplain(ps, 2)).map((l) => l.text);
  eq(xl, [
    'Thứ tự H4: tăng (7 nến H4), giá ở discount 31% (dealing range H4 2301.70–2341.00), mức được bảo vệ 2318.40. Nến H4 chốt gần nhất: 5 nến trước.',
    'Thứ tự H1: lẫn lộn (3 nến H1), giá ở premium 64% (dealing range H1 2300.00–2341.00). Nến H1 chốt gần nhất: 1 nến trước.',
    'pd_bias: giảm (FVG H1 tăng bị disrespect, 5 nến trước).',
    'DOL: lên, đích BSL H1 2341.00 — ITH H1 (cách 4.2 ATR); đặt sau shift tăng ở nến #88 (12 nến trước).',
    'Mức theo kỳ: PDH 2339.10 (còn nguyên) · PDL 2301.70 (đã lấy) · PWL 2290.00 (còn nguyên); giá mở ngày 2312.00, midnight open —.',
    'Nến H4 đang hình thành: 7/16 nến (mở 28/03 17:00 → đóng 28/03 21:00 UTC), O 2310.00 H 2315.00 L 2305.00 C 2312.00 — chỉ để vẽ, chưa dùng.'
  ], 'giải thích khung lớn: thứ tự H4/H1 + vị trí, pd_bias + FVG nguồn, DOL + đích, mức theo kỳ, nến H4 đang hình thành');
  const ps2 = { khung_lon: { bat: true, ngu_canh: {} }, pd: { pd_bias: null }, dol: { side: null, shift: null } };
  eq(J(V.htfExplain(ps2, 2, { dolReached: H.evs.filter((e) => e.structure_type === 'DOL_REACHED')[0] })).map((l) => l.text),
    ['pd_bias: chưa có (chưa FVG H1/H4 nào được respect / disrespect).', 'DOL: không có — đích 120.00 (H4) đã bị lấy ở nến #58; chờ shift kế tiếp đặt DOL mới.'],
    'giải thích khi chưa có pd_bias / đích DOL vừa bị lấy');
  eq(J(V.htfExplain({ ict: true }, 2)), [], 'kết quả trước 0.4.0: không có dòng khung lớn');
  eq(J(V.htfEventText(H.pd, 2)).text, 'FVG H4 tăng [100.00, 102.00] bị disrespect: close 99.00 (close < mép xa (lo)) → pd_bias giảm (H4).', 'câu PD_DISRESPECT');
  ok(/^ITH H4 120\.00 \(HH\) xác nhận: đỉnh nến H4 mở 02\/01 10:00 \(chạm ở nến #20\) → vùng BSL H4 B3 120\.00, hiệu lực từ nến sau\. Thứ tự H4: tăng/.test(V.htfEventText(H.sw4, 2).text),
    'câu HTF_SWING', V.htfEventText(H.sw4, 2).text);
  // tooltip đối tượng khung lớn
  const tf = J(V.objectInfo(MH, 'htffvg:' + H.f4.event_id));
  ok(tf && tf[0].head === 'FVG H4 tăng 100.00–102.00' && /disrespect ở #52 \(close 99\.00; close < mép xa \(lo\)\) → hàm ý giảm/.test(tf[0].body) && /đặt pd_bias hiện tại/.test(tf[0].more),
    'tooltip FVG H4: vòng đời + nguồn pd_bias', tf);
  const tr = J(V.objectInfo(MH, 'htfrange:H4:hi'));
  ok(tr && tr[0].head === 'Dealing range H4 90.00–120.00 · EQ 105.00' && /từ ITH H4 #20 và ITL H4 #10/.test(tr[0].body), 'tooltip range H4', tr);
  const tfm = J(V.objectInfo(MH, 'forming:H4', { barOf: barOf }));
  ok(tfm && tfm[0].head === 'Nến H4 đang hình thành — chưa dùng' && /12\/16 nến/.test(tfm[0].body), 'tooltip nến H4 đang hình thành', tfm);
  const tsw = J(V.objectInfo(MH, 'htfsw:' + H.sw4.event_id));
  ok(tsw && tsw[0].head === 'ITH H4 120.00 (HH)' && /biết lúc #33 \(nến H4 chốt 02\/01 14:00\)/.test(tsw[0].body), 'tooltip ITH H4', tsw);
  const tlv = J(V.objectInfo(MH, 'lvl:ict:HTF_PERIOD_HIGH@2>40:D'));
  ok(tlv && /đã bị lấy ở #50 \(sweep\)$/.test(tlv[0].body), 'tooltip PDH: trạng thái vùng', tlv);
  // không bật lớp khung lớn → không có đối tượng khung lớn; Gọn không đổi
  const g0 = J(V.buildDrawing(MH, V.selectCurrent(MH, { close: 100 }), ident, { flow: true, shift: true }));
  ok(!g0.segments.concat(g0.boxes).some((x) => /^(htf|lvl|forming)/.test(x.id)), 'tắt lớp khung lớn → không vẽ gì của khung lớn');
  const g1 = J(V.buildDrawing(MH, V.selectCurrent(MH, { close: 100, htf: ALL_HTF }), ident, { flow: true, shift: true, htf: ALL_HTF, barOf: barOf }));
  eq(g1.segments.filter((x) => !/^(htf|lvl|forming)/.test(x.id)), g0.segments, 'bật lớp khung lớn không đổi đối tượng Gọn');
  ok(!g1.segments.some((x) => x.id === 'lvl:ict:HTF_PERIOD_HIGH@2>40:D'), 'PDH đã vẽ ở Gọn (vùng B5) → lớp khung lớn không vẽ lại');
}

const ALL_DETAIL = { protected: true, range: true, fvg: true, ith: true, sth: true, labels: true, disp: true };
const barOf = (i) => ({ high: 110, low: 107, open: 109, close: 108 });

function runHandDetail(H) {
  const last = H.N - 1;
  const M = V.buildModel(H.evs, H.tl, H.pendingAt(last), Infinity, 2);
  // mức được bảo vệ + dealing range: đọc timeline tại con trỏ
  const s34 = J(V.structureAt(M));
  eq(s34.prot, { id: 'h18', price: 120, side: 'high', swingBar: 18, since: 30, brokenAt: null, broken: false, order: -1 }, 'Protected tại #34 = timeline');
  eq([s34.range.id, s34.range.hi, s34.range.lo, s34.range.start, s34.range.since], ['18-25', 120, 93.9, 18, 29], 'dealing range tại #34 = timeline');
  const M27 = V.buildModel(H.evs, H.tl, H.pendingAt(27), 27, 2);
  const s27 = J(V.structureAt(M27));
  eq([s27.prot.id, s27.prot.since, s27.prot.brokenAt, s27.prot.side], ['l14', 20, 25, 'low'], 'Protected tại #27: đáy l14, bị close vượt từ #25');
  eq([s27.range.id, s27.range.hi, s27.range.start, s27.range.since], ['12-14', 110.8, 12, 18], 'dealing range tại #27: đã mở rộng 110.8');
  // FVG «Hiện tại» (close 100, ATR 1): còn mở, ≤ 200 nến, cách ≤ 5 ATR, ≤ 3 mỗi chiều — D (1), B (2), C (4);
  // E (cách 9) và G (cách 12) xa bị bỏ; A, F đã lấp
  const sel = V.selectCurrent(M, { close: 100 });
  eq(sel.fvgs.map((e) => e.event_id), [H.fv.B, H.fv.C, H.fv.D], 'FVG Hiện tại: còn mở, gần (≤ 5 ATR), ≤ 3 mỗi chiều');
  eq(V.selectCurrent(M, { close: 100, fvgRecent: 10 }).fvgs.map((e) => e.event_id), [H.fv.D], 'FVG Hiện tại: chỉ FVG biết trong fvgRecent nến gần con trỏ');
  eq(V.selectCurrent(M, { close: 100, fvgFarAtr: 20 }).fvgs.map((e) => e.event_id), [H.fv.B, H.fv.C, H.fv.D, H.fv.G], 'nới fvgFarAtr → có G; E vẫn ngoài 3 gần nhất');
  const dr = J(V.buildDrawing(M, sel, ident, { flow: true, shift: true, detail: ALL_DETAIL, barOf: barOf }));
  const box = (id) => dr.boxes.filter((b) => b.id === 'fvg:' + id)[0];
  ok(box(H.fv.B) && box(H.fv.B).borderStyle === 'dashed' && near(box(H.fv.B).l1, 19.55) && box(H.fv.B).l2 === last + 5,
    'FVG đã chạm: viền đứt, từ nến giữa tới con trỏ + 5', box(H.fv.B));
  ok(box(H.fv.C) && box(H.fv.C).borderStyle === 'solid', 'FVG còn mở: viền liền', box(H.fv.C));
  ok(!box(H.fv.E) && !box(H.fv.A), 'FVG xa / đã lấp không ở «Hiện tại»');
  ok(dr.boxes.filter((b) => b.id === 'fvg:' + H.fv.F).length === 0, 'FVG của shift không vẽ lại ở lớp FVG (đã có hộp của shift)');
  const ce = dr.segments.filter((x) => x.id === 'fvg:' + H.fv.C)[0];
  ok(ce && ce.style === 'dashed' && near(ce.p1, 104.25) && ce.label && ce.label.text === 'FVG' && ce.label.pos === 'start' && near(ce.label.at, 23.6),
    'CE 50% nét đứt + chữ «FVG» trong hộp ngay sau nến 3', ce);
  const prot = dr.segments.filter((x) => x.id === 'prot:h18');
  ok(prot.length === 1 && prot[0].l1 === 18 && prot[0].l2 === last + 20 && prot[0].label.text === 'Protected High' && prot[0].style === 'solid',
    'Protected High: từ swing #18 tới con trỏ + 20, chưa vượt → nét liền', prot);
  const rng = dr.boxes.filter((b) => b.id.indexOf('range:18-25:') === 0);
  ok(rng.length === 3 && near(rng[0].p1, 120 - 0.05 * 26.1) && near(rng[1].p1, 93.9 + 0.475 * 26.1) && near(rng[2].p2, 93.9 + 0.05 * 26.1) &&
    near(rng[0].l1, 17.55) && near(rng[0].l2, last + 0.45), '3 dải Premium / EQ / Discount từ nến mốc #18 tới con trỏ', rng);
  ok(dr.segments.filter((x) => x.id.indexOf('range:') === 0).map((x) => x.label.text + '@' + x.label.pos + ':' + x.label.at).join(',') ===
    'Premium@start:18.6,EQ@start:18.6,Discount@start:18.6', 'chữ 3 dải ở đầu trái (sau nến mốc #18)');
  const sw = dr.segments.filter((x) => x.id.indexOf('swing:') === 0);
  eq(sw.length, 13, 'chấm ITH/ITL tại mọi pivot cấp 2 đã xác nhận');
  eq(sw.filter((x) => x.label).map((x) => x.label.text + (x.label.side === 'above' ? '↑' : '↓')).sort(), ['HH↑', 'LL↓'], 'nhãn HH trên đỉnh, LL dưới đáy');
  ok(sw.every((x) => x.noLine && x.dot && x.dot.r > 0), 'ITH/ITL là chấm nhỏ');
  const dsp = dr.boxes.filter((b) => b.id.indexOf('disp:') === 0);
  ok(dsp.length === 1 && near(dsp[0].p1, 106.85) && near(dsp[0].p2, 110.15) && near(dsp[0].l2 - dsp[0].l1, 1.1), 'displacement: quầng nhạt sau cả cây nến (± 0.15 ATR)', dsp);
  const d27 = J(V.buildDrawing(M27, V.selectCurrent(M27, { close: 100 }), ident, { flow: true, shift: true, detail: ALL_DETAIL }));
  const p27 = d27.segments.filter((x) => x.id === 'prot:l14');
  ok(p27.length === 2 && p27[0].style === 'solid' && p27[0].l2 === 25 && p27[1].style === 'dashed' && p27[1].l1 === 25 &&
    p27[1].label.text === 'Protected Low · broken', 'Protected Low bị close vượt ở #25: liền tới #25 rồi nét đứt đỏ «· broken»', p27);
  // không bật lớp nào của Chi tiết → không có đối tượng Chi tiết; Gọn giữ nguyên
  const g0 = J(V.buildDrawing(M, V.selectCurrent(M), ident, { flow: true, shift: true }));
  const g1 = J(V.buildDrawing(M, V.selectCurrent(M, { close: 100 }), ident, { flow: true, shift: true, detail: null, history: false }));
  eq(g1, g0, 'Gọn không đổi khi tắt Chi tiết / Lịch sử');
  // tooltip Chi tiết
  const tp = J(V.objectInfo(M, 'prot:h18'));
  ok(tp && /^Protected High 120\.00$/.test(tp[0].head) && /đỉnh cấu trúc ở #18, là mức được bảo vệ từ #30 \(thứ tự giảm/.test(tp[0].body), 'tooltip Protected', tp);
  const tr = J(V.objectInfo(M, 'range:18-25:premium'));
  ok(tr && /^Premium — dealing range 93\.90–120\.00$/.test(tr[0].head) && /từ đỉnh #18 và đáy #25/.test(tr[0].body), 'tooltip dải Premium', tr);
  const tf = J(V.objectInfo(M, 'fvg:' + H.fv.B));
  ok(tf && /^FVG tăng 102\.00–103\.00$/.test(tf[0].head) && /đã chạm ở #26, chưa lấp/.test(tf[0].body), 'tooltip FVG đã chạm', tf);
  const tA = J(V.objectInfo(M, 'fvg:' + H.fv.A));
  ok(tA && /đã lấp ở #16/.test(tA[0].body), 'tooltip FVG đã lấp', tA);
  const tsw = J(V.objectInfo(M, 'swing:' + H.evs.filter((e) => e.details.nhan === 'HH')[0].event_id));
  ok(tsw && tsw[0].head === 'ITH 120.00' && /HH so với 119\.00/.test(tsw[0].body), 'tooltip ITH + HH', tsw);
  ok(J(V.objectInfo(M, 'disp:ict:DISPLACEMENT_DOWN@24>24'))[0].head === 'Displacement giảm', 'tooltip displacement');
  // mức được bảo vệ trùng đúng vùng của cùng đỉnh (B4 từ ITH #18, 120): tooltip ghi cả hai
  eq(J(V.objectInfo(M, 'pool:B4', { prot: true })).map((r) => r.head), ['BSL 120.00 bị lấy · chờ', 'Protected High 120.00'], 'tooltip vùng trùng Protected (lớp bật)');
  eq(J(V.objectInfo(M, 'pool:B4')).length, 1, 'tooltip vùng: lớp Protected tắt → chỉ vùng');
  const M31 = V.buildModel(H.evs, H.tl, H.pendingAt(31), 31, 2);
  eq(J(V.objectInfo(M31, 'prot:h18')).map((r) => r.head), ['Protected High 120.00', 'BSL 120.00'], 'tooltip Protected kèm vùng còn nguyên trùng mức');

  // Lịch sử: mọi vùng / shift / FVG tới con trỏ, mờ dần theo tuổi; vùng xa không có nhãn mép
  const sh = V.selectCurrent(M, { history: true, close: 100 });
  eq(sh.pools.length, M.poolList.length, 'Lịch sử: mọi vùng đã biết');
  eq(sh.fvgs.length, 7, 'Lịch sử: mọi FVG đã biết (kể cả đã lấp)');
  const dh = J(V.buildDrawing(M, sh, ident, { flow: true, shift: true, detail: ALL_DETAIL, history: true }));
  const s9 = dh.segments.filter((x) => x.id === 'pool:S9')[0];
  ok(s9 && s9.alpha === 0.5 && !s9.label.edgeText, 'Lịch sử: vùng còn nguyên không thuộc 2 gần nhất — mờ, không nhãn mép', s9);
  const b1h = dh.segments.filter((x) => x.id === 'pool:B1')[0];
  ok(b1h && near(b1h.alpha, 0.85 * (1 - 11 / 300)), 'Lịch sử: sweep mờ theo tuổi (34 − 23 = 11 nến)', b1h && b1h.alpha);
  const aBox = dh.boxes.filter((b) => b.id === 'fvg:' + H.fv.A)[0];
  ok(aBox && aBox.borderStyle === 'dotted' && near(aBox.l2, 16.45) && near(aBox.alpha, 1 - 18 / 300), 'Lịch sử: FVG đã lấp dừng ở nến lấp, viền chấm, mờ theo tuổi', aBox);
  // «Mọi vùng còn nguyên» (ict_liq): thêm S9 nhưng không đổi kết cục
  const sa = V.selectCurrent(M, { allIntact: true });
  ok(sa.pools.some((s) => s.id === 'S9') && sa.pools.length === 11, 'mọi vùng còn nguyên: thêm S9', sa.pools.map((s) => s.id));

  // nhân quả Chi tiết + Lịch sử ở mọi con trỏ (pending_state đúng con trỏ)
  const conf = {};
  H.evs.forEach((e) => { conf[e.event_id] = e.confirmed_bar_index; });
  for (let c = 0; c <= last; c++) {
    const Mc = V.buildModel(H.evs, H.tl, H.pendingAt(c), c, 2);
    const scs = [V.selectCurrent(Mc, { close: 100 }), V.selectCurrent(Mc, { history: true, close: 100 })];
    scs.forEach(function (sc, k) {
      const dc = J(V.buildDrawing(Mc, sc, ident, { flow: true, shift: true, detail: ALL_DETAIL, history: k === 1, barOf: barOf }));
      dc.segments.concat(dc.boxes).forEach(function (it) {
        const kind = it.id.slice(0, it.id.indexOf(':')), rest = it.id.slice(it.id.indexOf(':') + 1);
        if (kind === 'swing' || kind === 'fvg' || kind === 'disp' || kind === 'shift') {
          ok(conf[rest] <= c, (k ? 'Lịch sử' : 'Chi tiết') + ': ' + it.id + ' hiện trước nến xác nhận (con trỏ ' + c + ')', conf[rest]);
        } else if (kind === 'pool') {
          rest.split('+').forEach(function (pid) { ok(Mc.pools[pid].known <= c, 'vùng ' + pid + ' trước khi biết (con trỏ ' + c + ')'); });
        } else if (kind === 'prot') {
          ok(H.tl[c].protected_id === rest, 'Protected khác timeline tại con trỏ ' + c, [rest, H.tl[c].protected_id]);
        } else if (kind === 'range') {
          ok(rest.indexOf(H.tl[c].dealing_id + ':') === 0, 'dealing range khác timeline tại con trỏ ' + c, [rest, H.tl[c].dealing_id]);
        }
        if (kind === 'fvg' && it.borderStyle) {
          const fe = Mc.ev[rest], tch = Mc.fvgTouched[rest], fil = Mc.fvgFilled[rest];
          const want = fil ? 'dotted' : (tch ? 'dashed' : 'solid');
          if (fe && /^FVG_/.test(fe.structure_type)) {
            ok(it.borderStyle === want, 'vòng đời FVG ' + rest + ' ở con trỏ ' + c + ': ' + it.borderStyle + ' ≠ ' + want);
            ok(!tch || tch.confirmed_bar_index <= c, 'FVG đã chạm trước khi biết');
          }
        }
      });
      if (c < 13) ok(!dc.boxes.some((b) => b.id === 'fvg:' + H.fv.A && b.borderStyle !== 'solid'), 'FVG A chưa chạm trước #13');
      if (k === 1 && c >= 16) ok(dc.boxes.some((b) => b.id === 'fvg:' + H.fv.A && b.borderStyle === 'dotted'), 'Lịch sử: FVG A đã lấp từ #16 (con trỏ ' + c + ')');
      if (c < 11) ok(!dc.boxes.some((b) => b.id === 'fvg:' + H.fv.A), 'FVG A chưa hiện trước #11');
      if (c < 18) ok(!dc.boxes.some((b) => b.id.indexOf('range:') === 0), 'chưa có dealing range trước #18');
    });
  }
}

// ------------------------------------------------------------------ dữ liệu lõi thật

function runReal(file) {
  const D = JSON.parse(fs.readFileSync(file, 'utf8'));
  const full = D.full;
  const M = V.buildModel(full.events, full.timeline, full.pending, Infinity, D.digits);
  let bars = 0, nBad = 0;
  const bad = [];
  full.timeline.forEach(function (p) {
    const n = V.nearestIntact(M, p.bar_index);
    const a = n.BSL[0] || null, b = n.SSL[0] || null;
    bars++;
    const got = [a ? a.id : null, a ? a.level : null, b ? b.id : null, b ? b.level : null];
    const want = [p.liq_above_id, p.liq_above, p.liq_below_id, p.liq_below];
    if (JSON.stringify(got) === JSON.stringify(want)) return;
    nBad++;
    if (bad.length < 5) bad.push({ bar: p.bar_index, got: got, want: want });
  });
  ok(nBad === 0, 'vùng còn nguyên gần nhất suy từ sự kiện khớp liq_above/liq_below của timeline ở mọi nến', { n: nBad, first: bad });
  info.nen_so_khop = bars;
  info.vung = M.poolList.length;
  const sel = V.selectCurrent(M);
  const dr = V.buildDrawing(M, sel, ident, {});
  info.hien_tai_cuoi = { vung: sel.pools.length, duong: dr.counts.lines, shift: dr.counts.shift, hop: dr.boxes.length };
  // mỗi kết cục vùng khớp sự kiện LIQ_* (nhân quả từ sự kiện) — đếm
  const outcomes = {};
  M.poolList.forEach((p) => {
    const k = p.outcome || (p.taken !== null ? 'pending' : 'intact');
    outcomes[k] = (outcomes[k] || 0) + 1;
  });
  info.ket_cuc = outcomes;
  ok((outcomes.sweep || 0) > 5 && (outcomes.run || 0) > 5, 'dữ liệu có đủ sweep và run', outcomes);

  // replay prefix: dựng từ prefix (sự kiện + pending_state tại con trỏ) = dựng từ toàn bộ sự kiện lọc theo con trỏ
  let pendSeen = 0;
  D.prefixes.forEach(function (px) {
    const c = px.cursor;
    const Mp = V.buildModel(px.events, px.timeline, px.pending, c, D.digits);
    const Mf = V.buildModel(full.events, full.timeline, px.pending, c, D.digits);
    const dp = V.buildDrawing(Mp, V.selectCurrent(Mp), ident, {});
    const df = V.buildDrawing(Mf, V.selectCurrent(Mf), ident, {});
    eq(J(dp), J(df), 'con trỏ ' + c + ': đối tượng vẽ từ prefix replay = từ toàn bộ sự kiện lọc theo con trỏ');
    eq(J(V.bandBars(Mp, ident)), J(V.bandBars(Mf, ident)), 'con trỏ ' + c + ': dải order flow giống nhau');
    const last = px.timeline[px.timeline.length - 1];
    const n = V.nearestIntact(Mp, c);
    eq([n.BSL[0] ? n.BSL[0].id : null, n.SSL[0] ? n.SSL[0].id : null], [last.liq_above_id, last.liq_below_id],
      'con trỏ ' + c + ': vùng gần nhất = timeline của prefix');
    // không đối tượng nào trước nến xác nhận
    dp.segments.concat(dp.boxes).forEach(function (it) {
      if (it.id.indexOf('pool:') !== 0) return;
      it.id.slice(5).split('+').forEach(function (pid) {
        const p = Mp.pools[pid];
        ok(p.known <= c && (!p.outcome || p.resolved <= c), 'con trỏ ' + c + ': vùng ' + pid + ' trước nến xác nhận');
      });
    });
    const pend = ((px.pending || {}).thanh_khoan || {}).dang_cho_sweep_run || [];
    pend.forEach(function (d) {
      pendSeen++;
      const s = V.poolAt(Mp.pools[d.id], c);
      ok(s && s.state === 'pending', 'con trỏ ' + c + ': vùng ' + d.id + ' của pending_state ở trạng thái chờ', s && s.state);
      ok(dp.segments.some((x) => x.id.indexOf('pool:') === 0 && x.id.slice(5).split('+').indexOf(d.id) >= 0 && x.style === 'dashed'),
        'con trỏ ' + c + ': vùng chờ ' + d.id + ' vẽ nét đứt (có thể gộp với vùng chờ trùng)');
      const fp = V.poolAt(M.pools[d.id], c);
      ok(fp && fp.state === 'pending', 'con trỏ ' + c + ': dựng lại từ sự kiện toàn bộ cũng thấy ' + d.id + ' đang chờ ở ' + c, fp && fp.state);
    });
  });
  ok(pendSeen > 0, 'có ít nhất một con trỏ đang chờ sweep/run trong các prefix');
  // Chi tiết + Lịch sử: dựng từ prefix = dựng từ toàn bộ sự kiện lọc theo con trỏ; Protected / range = timeline prefix
  D.prefixes.forEach(function (px) {
    const c = px.cursor;
    const Mp = V.buildModel(px.events, px.timeline, px.pending, c, D.digits);
    const Mf = V.buildModel(full.events, full.timeline, px.pending, c, D.digits);
    [false, true].forEach(function (hist) {
      const o = { flow: true, shift: true, detail: ALL_DETAIL, history: hist };
      const a = J(V.buildDrawing(Mp, V.selectCurrent(Mp, { history: hist, close: 2000 }), ident, o));
      const b = J(V.buildDrawing(Mf, V.selectCurrent(Mf, { history: hist, close: 2000 }), ident, o));
      eq(a, b, 'con trỏ ' + c + (hist ? ' Lịch sử' : ' Chi tiết') + ': prefix = toàn bộ lọc theo con trỏ');
    });
    const last = px.timeline[px.timeline.length - 1], sp = V.structureAt(Mp);
    eq([sp.prot ? sp.prot.id : null, sp.prot ? sp.prot.price : null, sp.range ? sp.range.id : null, sp.range ? sp.range.hi : null],
      [last.protected_id, last.protected, last.dealing_id, last.dealing_hi], 'con trỏ ' + c + ': Protected / range = timeline');
    const hs = V.selectCurrent(Mp, { history: true });
    ok(hs.pools.length === Mp.poolList.filter((p) => p.known <= c).length && hs.shifts.length === Mp.shifts.length &&
      hs.fvgs.every((e) => e.confirmed_bar_index <= c), 'con trỏ ' + c + ': Lịch sử = mọi vùng / shift / FVG tới con trỏ');
  });
  // vòng đời FVG trên dữ liệu thật: lấp → hộp dừng ở nến lấp, viền chấm (Lịch sử ở nến cuối)
  const dH = V.buildDrawing(M, V.selectCurrent(M, { history: true }), ident, { flow: false, shift: false, detail: { fvg: true }, history: true });
  let nf = 0, badF = 0;
  dH.boxes.forEach(function (b) {
    const id = b.id.slice(4), fil = M.fvgFilled[id];
    nf++;
    if (fil ? !(b.borderStyle === 'dotted' && near(b.l2, fil.event_bar_index + 0.45)) : b.borderStyle === 'dotted') badF++;
  });
  ok(nf > 50 && badF === 0, 'vòng đời FVG (dữ liệu thật): hộp dừng ở nến lấp, viền chấm', { nf: nf, bad: badF });
  info.fvg_lich_su = nf;
  info.prefix = D.prefixes.map((p) => p.cursor);
  info.cho = pendSeen;
  if (D.bars) runRealHtf(D, M);
}

/** Khung lớn trên dữ liệu lõi thật (0.4.0): prefix = toàn bộ lọc theo con trỏ (cả lớp khung lớn), không đối tượng khung lớn nào
 * trước nến xác nhận, nến H4 đang hình thành tự gộp KHỚP pending_state của lõi, đích DOL luôn là vùng còn nguyên đúng tầng,
 * FVG khung lớn lõi còn mở = giao diện còn mở, dòng trạng thái khung lớn ở mọi nến. */
function runRealHtf(D, M) {
  const full = D.full, B = {};
  D.bars.forEach((b) => { B[b.index] = b; });
  const limited = (c) => (i) => { if (i > c) throw new Error('đọc nến #' + i + ' sau con trỏ #' + c); return B[i] || null; };
  const HALL = { swing: true, range: true, fvg: true, levels: true, forming: true, h1: true };
  const kinds = {};
  full.events.forEach((e) => { if (/^(HTF_|PD_|DOL_)/.test(e.structure_type)) kinds[e.structure_type] = (kinds[e.structure_type] || 0) + 1; });
  info.htf_su_kien = kinds;
  ok((kinds.HTF_SWING_HIGH || 0) > 3 && (kinds.HTF_FVG_UP || 0) + (kinds.HTF_FVG_DOWN || 0) > 3 && (kinds.HTF_PERIOD_HIGH || 0) > 3 &&
    Object.keys(kinds).some((k) => /^PD_/.test(k)), 'dữ liệu có đủ sự kiện khung lớn (ITH/ITL, FVG, PDH, PD_*)', kinds);
  let nHtfObj = 0;
  D.prefixes.forEach(function (px) {
    const c = px.cursor;
    const Mp = V.buildModel(px.events, px.timeline, px.pending, c, D.digits);
    const Mf = V.buildModel(full.events, full.timeline, px.pending, c, D.digits);
    [false, true].forEach(function (hist) {
      const o = { flow: true, shift: true, history: hist, htf: HALL, barOf: limited(c) };
      let a = null, b = null, threw = null;
      try {
        a = J(V.buildDrawing(Mp, V.selectCurrent(Mp, { history: hist, close: B[c].close, htf: HALL }), ident, o));
        b = J(V.buildDrawing(Mf, V.selectCurrent(Mf, { history: hist, close: B[c].close, htf: HALL }), ident, o));
      } catch (err) { threw = String(err && err.stack || err); }
      ok(threw === null, 'con trỏ ' + c + ': dựng lớp khung lớn không đọc nến sau con trỏ', threw);
      if (threw) return;
      eq(a, b, 'con trỏ ' + c + (hist ? ' Lịch sử' : '') + ' + khung lớn: prefix = toàn bộ lọc theo con trỏ');
      a.segments.concat(a.boxes).forEach(function (it) {
        const k = it.id.slice(0, it.id.indexOf(':')), rest = it.id.slice(it.id.indexOf(':') + 1);
        if (k === 'htfsw' || k === 'htffvg' || k === 'lvl') {
          nHtfObj++;
          ok(Mp.ev[rest] && Mp.ev[rest].confirmed_bar_index <= c, 'con trỏ ' + c + ': ' + it.id + ' trước nến xác nhận');
        }
        if (k === 'htffvg' && it.borderStyle) {
          const end = Mp.htfFvgEnd[rest];
          ok(end ? (end.confirmed_bar_index <= c && near(it.l2, end.event_bar_index + 0.45)) : it.l2 === c + 5,
            'con trỏ ' + c + ': FVG khung lớn ' + rest + ' dừng đúng ở PD_* (hoặc mở tới con trỏ + 5)', it);
        }
      });
    });
    // FVG khung lớn lõi còn mở (pending_state) = giao diện còn mở
    const kl = (px.pending || {}).khung_lon || {};
    ['H1', 'H4'].forEach(function (f) {
      ((kl[f] || {}).fvg_dang_mo_gan_nhat || []).forEach(function (z) {
        ok(Mp.ev[z.fvg] && !Mp.htfFvgEnd[z.fvg], 'con trỏ ' + c + ': FVG ' + f + ' lõi còn mở cũng còn mở ở giao diện', z.fvg);
      });
    });
  });
  info.htf_doi_tuong_prefix = nHtfObj;
  // nến H4 đang hình thành: giao diện tự gộp (không pending) = pending_state của lõi
  const formChecks = (D.forming || []).concat(D.prefixes.map((p) => ({ cursor: p.cursor,
    forming: (((p.pending || {}).khung_lon || {}).H4 || {}).dang_hinh_thanh || null })));
  let nForm = 0, nNull = 0;
  formChecks.forEach(function (fx) {
    const c = fx.cursor, want = fx.forming;
    const Mn = V.buildModel(full.events, full.timeline, null, c, D.digits);
    let fm = null, threw = null;
    try { fm = J(V.formingAt(Mn, c, limited(c))); } catch (err) { threw = String(err); }
    ok(threw === null, 'con trỏ ' + c + ': nến đang hình thành không đọc nến sau con trỏ', threw);
    if (!want) { nNull++; ok(fm === null, 'con trỏ ' + c + ': lõi không có nến H4 đang hình thành → giao diện cũng không', fm); return; }
    nForm++;
    ok(fm && fm.start === want.nen_dau && fm.open === want.open && fm.high === want.high && fm.low === want.low && fm.close === want.close &&
      fm.n === want.n_bars, 'con trỏ ' + c + ': nến H4 đang hình thành tự gộp = pending_state của lõi', { fm: fm, want: want });
  });
  ok(nForm >= 5, 'có đủ con trỏ có nến H4 đang hình thành để so', nForm);
  info.forming_so = { co: nForm, khong: nNull };
  // đích DOL (timeline) luôn là vùng còn nguyên đúng mức + tầng; trạng thái khung lớn ở mọi nến
  let nDol = 0, badDol = [], badSt = 0;
  full.timeline.forEach(function (p) {
    const h = p.bar_index;
    const st = V.htfStatusAt(M, h);
    if (!st || !/^H4 [↑↓↕–]/.test(st.text) || !/DOL [↑↓–]/.test(st.text)) badSt++;
    if (p.dol_side === 1 || p.dol_side === -1) {
      nDol++;
      const s = V.poolByLevel(M, h, p.dol_target, p.dol_tier);
      if (!s && badDol.length < 5) badDol.push({ h: h, target: p.dol_target, tier: p.dol_tier });
    }
  });
  ok(nDol > 20 && badDol.length === 0, 'đích DOL của timeline = vùng còn nguyên đúng mức + tầng ở mọi nến có DOL', { nDol: nDol, bad: badDol });
  ok(badSt === 0, 'dòng trạng thái khung lớn có ở mọi nến', badSt);
  info.dol_nen = nDol;
}

const mode = process.argv[2];
try {
  if (mode === 'hand') runHand();
  else if (mode === 'real') runReal(process.argv[3]);
  else throw new Error('chế độ? hand | real <file>');
} catch (e) {
  failures.push('LỖI: ' + (e && e.stack || e));
}
process.stdout.write(JSON.stringify({ checks: checks, failures: failures, info: info }));
