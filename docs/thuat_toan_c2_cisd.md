# Thuật toán `c2_cisd_research` v0.1.0 — C2 Sweep + CISD (M15–H4, closed-bar)

Trạng thái: **bản nghiên cứu**. Chạy được end-to-end trong app (core → API/lưu →
chart/replay → metric). **Chưa xác minh parity với Pine/TradingView** — chưa có
trace TradingView nào được chạy. Dữ liệu synthetic trong test chỉ chứng minh hành
vi trên fixture, không chứng minh giá trị thị trường. Không phải tín hiệu giao dịch.

- Code: [`core/algorithms/c2_cisd_research.py`](../core/algorithms/c2_cisd_research.py),
  aggregator [`core/data/htf_stream.py`](../core/data/htf_stream.py),
  metric [`core/eval/c2_cisd_metrics.py`](../core/eval/c2_cisd_metrics.py).
- Test: [`tests/test_c2_cisd.py`](../tests/test_c2_cisd.py) (fixture tính tay + nhân quả),
  [`tests/test_c2_cisd_api.py`](../tests/test_c2_cisd_api.py) (API/lưu/export/replay/đánh giá).
- Plan: [`plan_tich_hop_c2_cisd.md`](plan_tich_hop_c2_cisd.md). Bản đồ nguồn:
  [`nghien_cuu_cantolab_fractal.md`](nghien_cuu_cantolab_fractal.md).

## 1. Nguồn và giấy phép

Chuyển thể từ indicator Pine **Open Source Fractal** của CantoLab —
<https://github.com/cantolab/open-source-fractal>, commit pin
`1bb53262deba9456f2b1a85d15c6ac5a5e880cf7` (clone đã kiểm tra `git rev-parse HEAD`
tại `D:\Finance_System\research-references\open-source-fractal`).

MIT License, Copyright (c) 2026 cantolab. Toàn văn giấy phép được giữ nguyên văn
trong header module và bản sao tại
[`third_party/open-source-fractal/LICENSE`](../third_party/open-source-fractal/LICENSE).
Manifest mỗi run (`GET /api/runs/{id}/manifest` → `algorithm_info.nguon`) ghi repo,
commit, license và `parity_pine = "CHƯA XÁC MINH"`.

Chỉ chuyển thể phần logic: C2, chọn mức CISD, reclaim/early CISD, vòng đời C3/C4.
**Không** chuyển: vẽ nến HTF, T-Spot box/đường EQ, projections độ lệch chuẩn,
cảnh báo, bảng dashboard. CISD ở đây **không** đồng nghĩa MSS/BOS; T-Spot
**không** phải FVG.

## 2. Dữ liệu, khung và thời điểm biết

| Mục | Quyết định |
|---|---|
| Cặp khung | Chỉ M15 (LTF) + H4 (HTF). Tham số khác → lỗi rõ ràng. Dataset không phải M15 → `ServiceError` (API trả 400), không tự tổng hợp/tách nến. |
| Mốc H4 | `utc_epoch`: kỳ mở tại bội số 4 giờ tính từ Unix epoch theo UTC (00/04/08/12/16/20 UTC), cùng quy ước `core/data/resample.py`. **Chưa đối chiếu** với H4 của broker hay TradingView (TradingView thường theo giờ sàn/phiên). Ghi trong event (`details.htf_alignment`) và manifest. |
| Kỳ hợp lệ | Đủ **16** nến M15 liên tiếp, đúng timestamp. Nến bị thiếu không được bù. |
| Nến | Mỗi nến phải có `close_time − bar_time ∈ {0, 15 phút}` và `close_time` nằm trên lưới 15 phút UTC; nếu không → `ValueError`. |
| Thời điểm biết | Mọi sự kiện có `confirmed_at = close_time` của nến đang xử lý (hợp đồng lab). `details.observed_at`/`observed_bar_index` là cùng giá trị, ghi rõ để không nhầm với thời gian nến sự kiện. |
| Warm-up | `warmup_bars = 32` (hai kỳ H4 đủ nến cho C1 và C2). |

**OHLC cuối của một kỳ H4 chỉ được đọc sau khi nến M15 cuối cùng của kỳ đóng.**
Aggregator tuần tự chỉ trả OHLC đang chạy (running) cho nến trước đó.

### 2.1. Gap và chất lượng dữ liệu (chính sách nghiêm)

- Nến M15 không liền nến trước → **gap**. Tại nến đầu tiên sau gap:
  1. mọi setup đang mở kết thúc `SETUP_DATA_GAP` (lý do `SETUP_LTF_GAP`) — không
     tính là bị giá phá, không tính là hết hạn;
  2. xoá mức CISD đang theo dõi cả hai hướng và lịch sử LTF dùng để tìm ngược
     (không quét qua gap);
  3. kỳ trước dùng làm `l1/h1` và C1 bị huỷ tới khi có một kỳ đủ nến mới.
- Mỗi kỳ H4 thiếu nến phát đúng một `HTF_BUCKET_INCOMPLETE` lúc phát hiện
  (thiếu nến đầu kỳ → phát ở nến đầu tiên thấy được; thiếu nến cuối → phát ở
  nến đầu kỳ sau). Kỳ cuối đang chạy khi hết dữ liệu **không** bị báo thiếu.
- Kỳ thiếu nến không được làm C1/C2/C3/C4; không cập nhật mức CISD và không
  phát early CISD trong kỳ đã thiếu nến.

**Ảnh hưởng thực tế (XAUUSD M15 HistData 2024, run demo mục 9):** XAUUSD nghỉ phiên
hằng ngày ~1 giờ nên kỳ 20:00 UTC thiếu 4 nến gần như mỗi ngày (305/315 kỳ thiếu
là kỳ 20:00; 10 kỳ 16:00 do nghỉ cuối tuần). Hệ quả: không có C2 ở kỳ 20:00 và
00:00 (C1 thiếu), và **223/523 setup (43%) dừng vì gap** — chủ yếu setup có C3/C4
chạm kỳ 20:00. Đây là giới hạn lớn nhất của chính sách hiện tại; một chính sách
"nghỉ phiên" (bỏ qua gap phiên đã biết) sẽ đổi output nên phải là version mới.

## 3. C2 sweep

C1 là kỳ H4 hợp lệ ngay trước C2 (liền kề). Tại nến M15 cuối cùng của C2 (khi C2
đủ nến):

```text
C2 tăng  = low(C2)  < low(C1)  and close(C2) > low(C1)
C2 giảm  = high(C2) > high(C1) and close(C2) < high(C1)
```

- So sánh strict, không dung sai. Không yêu cầu màu nến hay close nằm trong C1.
- Outside bar đạt cả hai → hai setup độc lập (`up-…`, `down-…`), cờ
  `details.outside_bar_ambiguous = true`. Không chọn hướng bằng dữ liệu sau.
- `bias` (Neutral/Bullish/Bearish, mặc định Neutral) là **bộ lọc người chọn**,
  lưu trong params/manifest và `details.bias`; không phải bias suy luận. Bias chỉ
  chặn tạo setup; mức CISD và early CISD vẫn theo dõi cả hai hướng như Pine.
- Cực trị setup (`extreme`) = low C2 (tăng) / high C2 (giảm); nến cực trị = nến M15
  **đầu tiên** đạt giá đó (so strict như `HtfCandle.update` của Pine).
- `setup_id = <up|down>-<giờ mở C2 dạng YYYYMMDDTHHMM>` — tất định.
- C3 = kỳ H4 ngay sau C2, C4 = kỳ sau C3 (theo khoảng thời gian thực tế).

**Khác Pine về thời điểm:** Pine phát trigger ở nến **đầu** kỳ sau
(`state.prevC2Buy := c2Buy[1]` khi `periodChanged`). Bản closed-bar biết C2 ngay
khi nến M15 cuối cùng của C2 đóng — **sớm hơn Pine đúng 1 nến M15**. Mọi thứ khác
của setup (mức CISD chụp tại lúc tạo, trạng thái reclaim) lấy đúng trạng thái
"cuối nến đó" như các giá trị `[1]` Pine dùng ở nến kế tiếp, nên log chỉ lệch
đúng 1 nến ở sự kiện C2.

## 4. Mức CISD

Chuyển nguyên các nhánh Pine (dòng 680–749). Mỗi hướng có **một** mức đang theo dõi
(tương ứng `bullLevelFixed/bullIndexFixed`), tồn tại qua các kỳ H4 như Pine.

Điều kiện kích hoạt tại nến t (hướng tăng; giảm đối xứng):
`low[t] == l0 and low[t] < l1`, với `l0` = low đang chạy của kỳ hiện tại (gồm t),
`l1` = low của kỳ trước **hợp lệ và liền kề**.

```text
dw = close < open, up = close > open, eq = close == open
nhánh trực tiếp: (dw[0] or eq[0]) and (up[1] or eq[1]) and not (eq[0] and eq[1])
                 → mức = open[t], nguồn = t
nếu không:  for i = 2..10:
                if low[i] < low[t]: break
                if (up[i] or eq[i]) and dw[i-1]:
                    b = i-1; mức = open[b]
                    for j = b..0: if open[j] > mức and dw[j]: mức = open[j]   (nâng)
                    if mức < open[t]: mức = close[t] > open[t] ? high[t] : open[t]  (dự phòng)
                    break
            không khớp → giữ mức cũ
```

- Doji: nhánh trực tiếp chấp nhận doji ở t hoặc t-1 nhưng không cả hai.
- Lịch sử để tìm ngược chỉ gồm nến liên tục từ lần gap/reset gần nhất; nến không có
  (Pine: `na`) → mọi điều kiện sai → kết thúc vòng lặp, không đổi mức.
- `break` do `low[i] < low[t]` **không đạt được** với M15–H4 đủ nến: t là đáy của
  kỳ hiện tại và thấp hơn đáy kỳ trước, còn i ≤ 10 không vượt quá kỳ trước.
- **Mức mới** ⇔ nến nguồn đổi (như `newBullLevel` của Pine). Khi đó phát
  `CISD_LEVEL_SET_UP/DOWN` (bất biến; không sửa mức trong sự kiện cũ), tăng
  `revision`, reset trạng thái reclaim, `reference_event_id` trỏ mức trước.
  Chi tiết: `branch` (`truc_tiep`/`tim_nguoc`/`du_phong_high|low|open`), `scan_i`,
  nến nguồn (`event_bar_index`), nến kích hoạt (`trigger_bar_index`),
  `doji_trigger`, `previous_level`.
- Không có TTL, không chặn quét tại biên H4 (giữ như nguồn). Chỉ gap mới xoá mức.

## 5. Reclaim, early CISD, xác nhận CISD

- **Khoá mức trước khi kiểm tra (khác Pine có chủ đích).** Tại nến t, close[t-1] được
  so với mức **có hiệu lực cuối nến t-1**; sau đó mới cập nhật mức bằng nến t. Pine
  cập nhật mức bằng nến t trước rồi so close[1], nên một nến gap xuống lập mức mới ở t
  có thể được "reclaim" bằng close[t-1] — bằng chứng cũ hơn chính mức. Fixture
  `test_muc_moi_khong_duoc_reclaim_bang_close_truoc_khi_muc_ton_tai` khoá hành vi này;
  bất biến `evidence_bar_index >= nến biết mức` được kiểm trên chuỗi ngẫu nhiên.
- Reclaim tăng: `close[t-1] > mức` (strict). Chỉ tính một lần cho mỗi mức.
- **Early CISD** (`EARLY_CISD_UP/DOWN`): reclaim xảy ra khi kỳ hiện tại đã quét đáy
  (đỉnh) kỳ trước (`l0 < l1`). Đây là **ứng viên** (`candidate_id` = hướng + giờ mở kỳ
  hiện tại), chưa phải setup; ứng viên không thành C2 vẫn nằm trong log và được đếm
  riêng (`so_ung_vien_khong_thanh_c2`).
- **C2 tạo khi mức đã reclaim** (Pine `cisdAlreadyConfirmed = bullReclaimed[1]`):
  phát `CISD_CONFIRMED_*` ngay tại nến tạo setup với `details.early = true`,
  `confirm_phase = "C2"`, `evidence_bar_index` = nến có close vượt,
  `reclaim_before_c2` (bằng chứng trước cả kỳ C2), `reference_event_id` = sự kiện
  early nếu có. Như Pine, mức reclaim có thể từ trước kỳ C2 nếu mức không đổi.
- **CISD sau C2**: setup chưa xác nhận, có mức (chụp lúc tạo, **không** đổi theo mức
  mới về sau — như `s.cisdLevel` Pine), `close[t-1]` vượt mức khi setup ở C3/C4 →
  `CISD_CONFIRMED_*` phát tại t, `event_bar_index = t-1` (nến bằng chứng),
  `delay_bars_from_c2` = t − nến tạo setup. Không dịch nhãn về quá khứ: marker có thể
  neo ở nến bằng chứng nhưng chỉ hiện sau `confirmed_at`.

## 6. Vòng đời setup và thứ tự xử lý

```text
                 C2 đóng (đủ nến, C1 hợp lệ)
   [ứng viên] ───────────────────────────────▶ C3 ──(nến đầu kỳ C4)──▶ C4 ──(C4 đóng đủ)──▶ SETUP_EXPIRED
       │ early CISD (không phải setup)          │                       │
       ▼                                        ├─ phá cực trị ────────▶ SETUP_INVALIDATED (SETUP_EXTREME_BREACHED)
   (log EARLY_CISD, có thể không thành C2)      ├─ gap M15 ────────────▶ SETUP_DATA_GAP
                                                ├─ C2 mới cùng hướng ──▶ SETUP_SUPERSEDED   (xem 6.2)
                                                └─ ở C4: close[t-1] vượt cạnh T-Spot C4:
                                                     CISD xác nhận TRONG C4 → SETUP_INVALIDATED (C4_FAIL_AFTER_CISD_IN_C4)
                                                     ngược lại → SETUP_C4_INVALIDATED (không kết thúc)
```

Trạng thái hiển thị (pha, có CISD chưa, C4 invalid) được suy ra từ log; `pending_state`
chỉ là bản tiện xem.

### 6.1. Thứ tự tại mỗi nến M15 t

1. Kiểm tra nến; nếu gap → `SETUP_DATA_GAP` cho setup mở, xoá mức/lịch sử LTF.
2. Nạp vào aggregator; phát `HTF_BUCKET_INCOMPLETE`. Nếu t là nến đầu kỳ mới:
   setup ở C3 (C3 = kỳ vừa xong) chuyển **C4**, cạnh T-Spot C4:
   `mid = (high C3 + low C3)/2`, `top = max(open[t], mid)`, `bottom = min(open[t], mid)`
   (Pine `computeTopBot` tại nến đầu C4).
3. Với từng setup đang mở (tăng rồi giảm, như Pine `buySetup` rồi `sellSetup`):
   a. **phá cực trị**: tăng `low[t] < extreme`, giảm `high[t] > extreme` → terminal;
   b. **C4 invalid** (chỉ pha C4, một lần): tăng `close[t-1] < bottom`, giảm
      `close[t-1] > top`;
   c. **xác nhận CISD** bằng `close[t-1]`.
   Nến vừa phá cực trị vừa có close đủ xác nhận → **phá trước** (đúng thứ tự
   `extendAndCheck` → `checkC4Invalid` → `checkCisdConfirm` của Pine); không đoán
   đường đi tick trong nến.
4. Theo dõi reclaim mức (mục 5), có thể phát early CISD.
5. Cập nhật mức CISD bằng nến t (mục 4).
6. Nếu t là nến cuối của kỳ đủ nến: (a) setup có C4 = kỳ này → `SETUP_EXPIRED`;
   (b) xét C2 cho kỳ này và tạo setup (thay setup cũ cùng hướng nếu còn).

Hệ quả khớp Pine: close của nến M15 **cuối cùng** của C4 không bao giờ được xét
(Pine `finish()` ở nến đầu kỳ sau trước khi kiểm tra). Có test riêng.

Mỗi setup có **tối đa một** sự kiện terminal (`details.terminal = true`); sau terminal
không có sự kiện nào của setup đó (kiểm trên chuỗi ngẫu nhiên). Setup chưa kết thúc
khi hết dữ liệu là **censored** — không có sự kiện, được đếm riêng trong metric.

### 6.2. Nhánh không đạt được với so sánh strict

`SETUP_SUPERSEDED`: C2 mới cùng hướng trong lúc setup cũ ở C3 buộc low C3 < low C2 cũ
= cực trị cũ → setup cũ đã bị phá ở chính nến tạo đáy đó (bước 3a) trước khi C3 đóng.
Setup ở C4 thì hết hạn (6a) trước khi xét C2 (6b). Vì vậy supersede **không xảy ra**
với logic hiện tại (năm 2024 thật: 0 lần). Nhánh được giữ làm phòng vệ; test
`test_setup_moi_cung_huong_luon_pha_cuc_tri_truoc_nen_khong_co_superseded` ghi lại lập
luận này.

## 7. Sự kiện và trường dữ liệu

| Loại | `event_bar_index` / giá | Phát tại | Ghi chú |
|---|---|---|---|
| `C2_CONFIRMED_UP/DOWN` | nến cực trị C2 / extreme | nến cuối C2 | `setup_id`, C1/C2 OHLC, `sweep_from(_bar_index)`, mức CISD chụp lúc tạo, `outside_bar_ambiguous`, `bias`, `c3_start`, `c4_start`. Ref → mức CISD. |
| `CISD_LEVEL_SET_UP/DOWN` | nến nguồn mức / mức | nến kích hoạt | `branch`, `scan_i`, `revision`, `cisd_level_id`, `previous_level`. Ref → mức trước. |
| `EARLY_CISD_UP/DOWN` | nến có close vượt / mức | nến sau đó | `candidate_id`, mức + nguồn + revision. Ref → mức. |
| `CISD_CONFIRMED_UP/DOWN` | nến có close vượt / mức | nến sau đó, hoặc nến tạo setup (early) | `early`, `confirm_phase` (C2/C3/C4), `evidence_*`, `delay_bars_from_c2`. Ref → early hoặc C2. |
| `SETUP_C4_INVALIDATED` | nến có close vượt cạnh / cạnh C4 | nến sau đó | không terminal. |
| `SETUP_INVALIDATED` | nến phá (hoặc nến close vượt C4) / extreme (hoặc cạnh C4) | nến phát hiện | `reason_code` phân biệt phá cực trị và C4 fail sau CISD trong C4. **CISD đã phát không bị xoá** (Pine xoá hình; lab chỉ append). |
| `SETUP_EXPIRED` | nến cuối C4 / extreme | nến cuối C4 | |
| `SETUP_SUPERSEDED` | nến tạo setup mới / extreme cũ | — | không đạt được (6.2). |
| `SETUP_DATA_GAP` | nến sau gap / extreme | nến sau gap | `missing_ltf_bars`, `gap_*`. |
| `HTF_BUCKET_INCOMPLETE` | nến cuối thấy được / close đang chạy | lúc phát hiện | `bucket_start/end`, `n_bars_seen`, `expected_bars`. Không có hướng. |

Mọi sự kiện có: `event_id` tất định (`c2cisd:<TYPE>:<nến phát>:<khoá>`), `direction`,
`reason_code` (giải thích tiếng Việt trong `core/types.py`), `details.observed_*`,
`details.htf/ltf/htf_alignment`. Setup events mang `setup_id`, `phase`, `extreme`,
mức CISD, `c4_top/bottom`, `cisd_confirmed(_in_c4)`. Run lưu `algorithm_version`,
`params`, `dataset_checksum`; lưu/xuất CSV giữ nguyên `details_json` (có test).

## 8. Timeline tính tay (fixture `BASIC`)

Nến M15 từ 2024-01-01 00:00 UTC. Kỳ 0 = nến 0–15 (C1), kỳ 1 = 16–31 (C2),
kỳ 2 = 32–47 (C3), kỳ 3 = 48–63 (C4).

| Nến | OHLC | Điều xảy ra |
|---|---|---|
| 0–15 | 100.0 / 100.5 / 99.5 / 100.2 (tăng) | C1: high 100.5, low 99.5 (nến 0). |
| 16–20 | 100.0 / 100.5 / 99.6 / 100.2 (tăng) | chưa thủng 99.5. |
| 21 | 100.2 / 100.3 / **99.0** / 99.3 (giảm) | đáy kỳ mới < 99.5; nến trước tăng → nhánh trực tiếp: **`CISD_LEVEL_SET_UP` 100.2** (nguồn 21, rev 1). |
| 22–31 | 99.4 / 99.9 / 99.2 / 99.8 | close cuối 99.8 > 99.5 → tại nến 31 (08:00 UTC) **`C2_CONFIRMED_UP`** giá 99.0, nến sự kiện 21, setup `up-20240101T0400`, mức 100.2. High C2 = 100.5 = high C1 → không có C2 giảm. |
| 32 | 99.8 / 100.0 / 99.5 / 99.9 | C3 bắt đầu; close[31]=99.8 < 100.2. |
| 33 | 99.9 / 100.6 / 99.8 / **100.5** | close 100.5 > 100.2 (chưa biết tới khi xử lý nến 34). |
| 34 | 100.5 / 100.7 / 100.3 / 100.6 | close[33] > 100.2 → **`CISD_CONFIRMED_UP`** (bằng chứng 33, trễ 3 nến sau C2, pha C3). |
| 48 | 100.6 / 100.8 / 100.4 / 100.7 | C4: mid C3 = (100.7+99.5)/2 = 100.1, open 100.6 → top 100.6, bottom 100.1. |
| 63 | 〃 | C4 đóng đủ → **`SETUP_EXPIRED`**. |

Biến thể có test riêng: bản lật giá (hướng giảm), early CISD trong C2 (nến 25 đóng
100.3 → `EARLY_CISD_UP` ở nến 26, `CISD_CONFIRMED_UP` early ở nến 31), ứng viên early
không thành C2, phá cực trị cùng nến có close xác nhận, CISD trong C4 rồi C4 fail,
C4 invalid không terminal, xác nhận ở nến cuối C4 cùng nến hết hạn, gap trong C3, kỳ
đầu thiếu nến, kỳ cuối đang chạy, warm-up, từ chối dataset/nến sai khung, mọi nhánh
chọn mức (trực tiếp, doji, hai doji, tìm ngược, nâng mức, dự phòng high/open, biên
i = 10 / 11), mức tồn tại qua kỳ và mức mới thay thế, outside bar, bias.

## 9. Bảng khác biệt với Pine (commit pin)

| # | Điểm | Pine | `c2_cisd_research` 0.1.0 | Loại |
|---|---|---|---|---|
| 1 | Dữ liệu HTF | `request.security(..., lookahead_on)` | Aggregator tuần tự từ M15 đã đóng; không đọc OHLC cuối trước khi kỳ đóng | Sửa có chủ đích (chống leak) |
| 2 | Lúc biết C2 | Nến đầu kỳ sau (`c2Buy[1]` khi `periodChanged`) | Nến cuối của C2 | Sớm hơn 1 nến M15, có chủ đích |
| 3 | Mốc H4 | Theo phiên/sàn TradingView | `utc_epoch` | Chưa đối chiếu |
| 4 | Gap / kỳ thiếu | Chuỗi nến liên tục, không kiểm tra | Kỳ thiếu không làm C1–C4; gap kết thúc setup, xoá mức, không quét qua gap | Chính sách chất lượng dữ liệu |
| 5 | Mức ban đầu | `l1` = low nến đầu tiên của chart | Cần kỳ trước đủ nến và liền kề | Warm-up rõ ràng |
| 6 | Reclaim | Cập nhật mức ở t rồi so `close[1]` | So `close[t-1]` với mức cuối t-1, sau đó mới cập nhật | Sửa có chủ đích (chống dùng mức mới như đã biết ở nến cũ) |
| 7 | CISD confirm | `close[1]` | Giữ nguyên `close[t-1]`, ghi riêng nến bằng chứng và nến phát hiện | Giữ nguồn |
| 8 | C4 fail sau CISD trong C4 | Xoá toàn bộ hình, `cisdConfirmed := false` | Append `SETUP_INVALIDATED`; `CISD_CONFIRMED` vẫn trong log | Log bất biến |
| 9 | Early CISD bị "tiêu thụ" | `consumeLastEarlyCisd` xoá hình early | Early giữ trong log; `CISD_CONFIRMED` early tham chiếu nó | Log bất biến |
| 10 | Phá cực trị | Đổi nhãn `XC2`, xoá box | `SETUP_INVALIDATED` terminal | Tương đương logic |
| 11 | Hết hạn | `finish()` ở nến đầu kỳ sau C4 | `SETUP_EXPIRED` ở nến cuối C4; close nến cuối C4 không được xét như Pine | Cùng kết quả, sớm 1 nến |
| 12 | Bias | `allowBuy/allowSell` | Giữ; lưu params/manifest | Giữ nguồn |
| 13 | `requireCisdToShow`, `showHistory`, màu/đường | Hiển thị | Không có trong core; lớp chart chỉ là toggle hiển thị | Ngoài phạm vi |
| 14 | T-Spot C3, projections, alert | Có | Không (chỉ dùng cạnh C4 cho invalid) | Giai đoạn sau |
| 15 | Realtime/intrabar | Có thể repaint trong nến | Chỉ nến đã đóng | Closed-bar |

## 10. Metric (Mốc D)

Tính từ log (lưu trong `stats.chi_so_thuat_toan` mỗi run; `GET /api/runs/{id}/c2-cisd-metrics`):

- Số C2 theo hướng, số outside bar; số CISD theo hướng và pha (C2-early/C3/C4).
- Tỷ lệ có CISD **kèm mẫu số**: trên mọi setup và trên setup đã kết thúc.
  **Không phải win rate.**
- Độ trễ CISD sau C2 (nến) và, **riêng**, số nến bằng chứng early trước cuối C2 —
  không gộp thành một trung bình.
- Kết thúc theo lý do; censored; C4 invalid không terminal; số gap/kỳ thiếu.
- Early: số ứng viên, số không thành C2.
- MFE/MAE (tuỳ chọn, `?horizon=` nến M15): nhóm **C2-only** neo lúc C2 được biết,
  nhóm **C2+CISD** neo lúc CISD được biết; giá tham chiếu = close nến neo; dùng nến
  SAU lúc biết, **chỉ để đánh giá**; bỏ mẫu thiếu horizon (hết dữ liệu hoặc gap) và
  báo số bị bỏ. Không có phí/spread/khớp lệnh.
- Chấm nhãn: mục tiêu `c2` (`C2_CONFIRMED_*`, nhãn ở nến cực trị, giá low/high) và
  `cisd` (`CISD_CONFIRMED_*`, nhãn ở nến có close vượt, giá = mức CISD) trên trang
  Đánh giá; ghép một-một cùng loại/hướng, dung sai thời gian/giá cố định. Chưa có nhãn
  → "Chưa có nhãn tham chiếu", không dựng F1 từ output của chính thuật toán hay nhãn
  HH/MSS. Nhãn do auto label đề xuất bị gắn provenance và cảnh báo như các loại khác.

Không có ngưỡng precision/recall để tuyên bố thuật toán tốt hơn. Kết hợp với swing
là thí nghiệm riêng sau MVP; `swing_pivot` giữ nguyên làm baseline.

## 11. Run minh hoạ (dữ liệu thật)

`run_cb7a8d38e30d` — dataset `ds_564bff443e42` "XAUUSD M15 · HistData 2024 (từ M1)",
checksum `40dd7382…10c4d`, 2024-01-01 23:00 → 2024-12-31 21:45 UTC, 23 713 nến,
params mặc định (Neutral). Nguồn dữ liệu: HistData.com M1 2024, quy đổi
America/New_York (có DST) → UTC (xem ghi chú dataset). 4 416 sự kiện, ~0.2 s.

| Chỉ số | Giá trị |
|---|---|
| Setup C2 (↑/↓) | 523 (246 / 277); outside bar 114 |
| Có CISD | 422/523 (80.7%); pha C2-early/C3/C4 = 346/74/2 |
| Trễ CISD sau C2 | trung vị 3.5 nến, TB 5.07 (n = 76) |
| Early: nến bằng chứng trước cuối C2 | trung vị 6, TB 6.41 (n = 346); ứng viên early không thành C2: 244/590 |
| Kết thúc | phá cực trị 203, hết hạn 95, **gap 223**, censored 2 |
| C4 invalid không terminal | 148 |
| Chất lượng dữ liệu | 260 gap M15, 315 kỳ H4 thiếu, 1 285 kỳ đủ |
| MFE/MAE 16 nến, C2-only | 433 mẫu (bỏ 90); MFE trung vị 5.54, MAE trung vị 5.00; MFE > MAE ở 224 mẫu |
| MFE/MAE 16 nến, C2+CISD | 347 mẫu (bỏ 75); MFE trung vị 5.53, MAE trung vị 4.94; MFE > MAE ở 185 mẫu |

Các số này **mô tả** một năm dữ liệu với một cấu hình; chưa kiểm định thống kê,
không có nhãn người gán, không phải kết quả giao dịch và không nói gì về parity Pine.

## 12. Dùng trên web

1. Trang **Thử nghiệm**: chọn dataset M15 (vd XAUUSD M15 HistData 2024) → thuật toán
   "C2 Sweep + CISD (nghiên cứu, M15–H4)" → Chạy thử. Khung ghi chú dưới banner báo
   alignment, warm-up, dữ liệu thiếu và "không có setup" tách bạch.
2. Chart: `C2↑/C2↓` neo ở nến cực trị (`?` = outside bar), `+CISD/-CISD` ở nến bằng
   chứng (`(e)` = early), `e+/e−` early ứng viên, `X` phá, `XC4`, `hết`, `gap`,
   `H4 thiếu`. Đường: mức CISD đang theo dõi (chấm mờ), mức CISD của setup (liền),
   cực trị setup (gạch vàng). Mỗi đoạn chỉ bắt đầu ở nến **sau** lúc mức/setup được
   biết và dừng khi kết thúc. Tooltip hiện setup/ứng viên, pha, mức + nến nguồn, nến
   bằng chứng, thời gian nến và thời gian biết, lý do.
3. Lớp hiển thị "C2 + cực trị setup", "Mức / xác nhận CISD", "Vòng đời setup",
   "Chất lượng dữ liệu H4" chỉ đổi hiển thị; bảng sự kiện/CSV luôn đầy đủ (lọc được
   theo `setup_id`).
4. Replay từng nến: sự kiện chỉ xuất hiện khi con trỏ ≥ nến xác nhận; tab Thống kê
   hiện setup đang mở, mức đang theo dõi, kỳ H4 hiện tại.
5. Tab Thống kê (toàn lịch sử): bảng vòng đời và nút **Tính MFE/MAE** (run đã lưu).
6. Trang **Gán nhãn** có loại C2/CISD; trang **Đánh giá** có mục tiêu `c2`/`cisd`.

## 13. Giới hạn và việc chưa kiểm chứng

- **Chưa có trace TradingView** → chưa đối chiếu Pine ở bất kỳ nến nào. Khác biệt
  mốc H4 (UTC epoch vs phiên TradingView) có thể làm lệch toàn bộ C2.
- Chính sách gap nghiêm làm mất ~43% setup trên XAUUSD (nghỉ phiên hằng ngày).
- Chỉ M15–H4; không có T-Spot C3/projections; không kết hợp swing.
- Chưa có bộ nhãn C2/CISD do người gán → chưa có precision/recall.
- Metric MFE/MAE không trừ spread, không mô phỏng khớp lệnh.
