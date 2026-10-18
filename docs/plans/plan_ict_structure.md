# Plan: `ict_structure` — bộ nhận diện cấu trúc ICT phân tầng, cung cấp bằng chứng cho regime

Bản 2.3 — 06/10/2026 (bản 2.2: 04/10/2026; bản 2.1: 02/10/2026; bản 1: 01/10/2026).
**Trạng thái: đặc tả đã duyệt (D1–D15, 04/10/2026); giai đoạn 1–2 đã cài (`ict_structure` v0.1.0 rồi v0.2.0, 05/10/2026 —
[`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md), đối chiếu survey ở §8 của đặc tả);
order flow theo thanh khoản đã chốt (OF1–OF2, 06/10/2026 — §8.3) và cài ở v0.3.0 (đặc tả §4.12);
giai đoạn 3 — phần lõi ([T0]–[T3], vùng H1/H4/D/W, [S5] `pd_bias`, [S6] DOL) đã cài ở v0.4.0 (08/10/2026 — đặc tả
§4.13–§4.19, đối chiếu §8.2, chỗ cài khác plan §12), giao diện giai đoạn 3 cùng ngày (đặc tả §11), v0.4.1 (18/10/2026)
bỏ `details.htf` ở sự kiện nguyên liệu; công cụ hồ sơ khung (§11.6) chưa làm. Giai đoạn 4 (§10) có plan riêng:
[`plan_bias_regime.md`](plan_bias_regime.md).**
Bản 2.3 chỉ thêm §8.3 (order flow). Bản 2.2 chỉ đổi §8: cả 15 câu D1–D15 được duyệt đúng theo đề xuất,
không sửa định nghĩa nào.
Bản 2.1: số liệu §2 và §11 chạy lại trên dataset **đã sửa giờ** (`ds_db1583cd4dde`) với lịch phiên
khai báo `data/calendars/cme_globex_metals.json`. So với lần chạy trên dataset lệch giờ, các tỷ lệ chỉ
đổi ≤ 2 điểm %, trừ phần lịch và dữ liệu (§2.1, §11.3).
Theo vòng thiết kế trong [`AGENTS.md`](../../AGENTS.md) §3, đây là bước ② (định nghĩa vận hành).
Mọi quyết định đã chốt ở §8 (không còn câu hỏi mở). Mọi con số ở §2 và §11 lấy từ dữ liệu thật, đoạn phát
triển, và **tái lập được** bằng `research/ict_survey.py` (§2).

Liên kết: [`kien_truc_luong_ict.md`](../guides/kien_truc_luong_ict.md) (tầng và luồng),
[`nghien_cuu_ict_smc_thuat_toan.md`](../research/nghien_cuu_ict_smc_thuat_toan.md) (định nghĩa so sánh,
chỗ mơ hồ), [`khao_sat/ict_survey_dev.json`](../research/khao_sat/ict_survey_dev.json) (số liệu gốc),
[`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) (order flow — §8.3).

---

## 0. Thay đổi so với bản 1

**Quyết định của người dùng (02/10/2026):** cách đánh này **không dùng BOS/CHoCH/MSS**.
- Đổi hướng = **quét thanh khoản rồi displacement ngược chiều** (gọi là *shift*).
- Bias = **ba thành phần riêng**: thứ tự đỉnh/đáy HH-HL, phản ứng ở PD array khung lớn, DOL.

BOS/CHoCH chỉ còn trong baseline `swing_pivot` (giữ nguyên để so sánh).

| # | Vấn đề từ review 02/10 | Cách xử lý ở bản 2 | Ở đâu |
|---|---|---|---|
| R1 | «Mức được bảo vệ» khác mức dùng để báo CHoCH | Không còn CHoCH. Mức được bảo vệ có **một** định nghĩa (thứ tự tăng → ITL gần nhất); close vượt mức chỉ bật cờ `protected_broken`, không phát sự kiện, không đổi trạng thái | §4.5 |
| R2 | «Đã lấy thanh khoản» có hai định nghĩa | **Một** định nghĩa: lấy = xuyên ≥ 0.1·ATR (ATR khoá tại nến lấy); nông hơn = *chạm*, vùng còn nguyên. Ghi rõ cửa sổ tính những nến nào và xử lý gap | §4.6 |
| R3 | Nến khung lớn thiếu dữ liệu vẫn tạo cấu trúc | Lịch phiên **khai báo** (gồm ngày lễ); `coverage`; nến < 90% không được nằm trong cửa sổ swing/FVG nên cấu trúc phụ thuộc tự không có; bucket mất trọn; kỳ đầu dataset | §4.0, §11.4 |
| R4 | Displacement và FVG có thể không cùng một nhịp | Shift tham chiếu **đúng một** displacement sau cú quét, cực trị cú quét không bị vượt; FVG phải có nến giữa **chính là** displacement đó; `SHIFT_FVG` là sự kiện bổ sung, không sửa shift; một chuỗi = một cơ hội khi đánh giá | §4.7 |
| R5 | Mức ngày/tuần và mốc thời gian khung lớn chưa rõ | Tách `period_end` và `known_at`; «giá mở ngày» = open nến giao dịch đầu ngày (18:00 NY); midnight open thiếu → `null`; kỳ đầu thiếu → không tạo mức; neo sự kiện khung lớn theo loại | §11.4 |
| R6 | Số liệu khảo sát không tái lập được | Script trong repo + JSON có checksum dataset, checksum đoạn, sha256 script, phiên bản, cấu hình, lịch phiên; quy tắc đối chiếu DC–ITH ghi rõ; bỏ kết luận «DC là tập con»; nghiệm thu không còn «đếm khớp khảo sát» | §2, §10 |
| R7 | Lộ trình gộp nhiều thứ, refactor thuật toán cũ quá sớm | 4 giai đoạn; **không** refactor `swing_pivot`/`swing_hierarchy` — thành phần mới chỉ dùng cho `ict_structure`, kiểm bằng test tương đương | §10 |

---

## 1. Bài toán: bộ nhận diện này phục vụ cái gì

Trong AI Trading Copilot, chuỗi quyết định là:

```text
Cấu trúc & đặc trưng giá  ──►  Regime: Trend / Range / Breakout / Uncertain  ──►  Router:
(lab này)                       (tầng phân loại)                                 Trend Pullback ·
                                                                                Range Mean Reversion ·
                                                                                No Trade
```

`ict_structure` **không phát tín hiệu vào lệnh**. Tại mỗi nến, chỉ dùng thông tin đã biết, nó
cung cấp **bằng chứng có giải thích** cho tầng regime:

| Router cần biết | Bằng chứng | Thành phần (§3) |
|---|---|---|
| Có hướng không, hướng nào? | Ba thành phần **riêng**: thứ tự đỉnh/đáy ITH/ITL; phản ứng ở FVG khung lớn; DOL | S2, S5, S6 |
| Vừa đổi hướng chưa? | **Shift**: quét thanh khoản rồi displacement ngược chiều (+ FVG do chính displacement) | E2, E3 |
| Pullback đang ở đâu? | Dealing range, premium/discount, mức được bảo vệ | S4, S2 |
| Đang đi ngang? | Thứ tự lẫn lộn; quét hai biên mà không có displacement | S2, E2 |
| Phá biên có lực hay không? | Lấy thanh khoản mà **không** quay lại (*run*) và có displacement cùng chiều; lấy rồi quay lại = *sweep* | E2, P3 |
| Có nên đứng ngoài? | Thành phần mâu thuẫn, đang khởi động, dữ liệu thiếu | G, timeline |

Ngoài phạm vi v0.1:
- Điểm vào/thoát lệnh, quản lý vốn.
- Order block, IFVG (§7).
- BOS/CHoCH/MSS (không dùng — B1).
- **Lớp kịch bản bias** — cách ghép ba thành phần thành nhận định (§10 giai đoạn 4).

---

## 2. Khảo sát dữ liệu làm căn cứ thiết kế (survey-v2)

**Chạy lại:**

```powershell
.\.venv\Scripts\python.exe research\ict_survey.py --json docs\research\khao_sat\ict_survey_dev.json
```

- Dữ liệu: XAUUSD M15 HistData 2024 **đã sửa giờ** `ds_db1583cd4dde` (checksum `39428eac…`),
  **đoạn phát triển** 01/01–31/08/2024 (checksum đoạn `313514f8…`): 15 850 nến, **173 ngày giao
  dịch** (ngày kết thúc 17:00 New York). M5 `ds_933fa5ec67e2` chỉ dùng cho hồ sơ khung.
  - Dataset cũ `ds_564bff443e42` bị lệch 1 giờ trong các tuần Mỹ–Âu lệch lịch đổi giờ
    (`market-data-pipeline/docs/du_lieu_thi_truong.md` §3), vẫn giữ để mở run cũ.
  - Đoạn kiểm tra 09–12/2024 **chưa đụng** (script từ chối nếu không có `--allow-test`).
- Script đọc DB **chỉ đọc**, không ghi gì. JSON ghi:
  - sha256 script;
  - phiên bản thuật toán lab dùng lại (`swing_pivot` 1.1.0, `swing_hierarchy` 1.0.0,
    `dc_atr_structure` 0.2.0);
  - cấu hình và nguồn lịch phiên.

  Hai lần chạy cho JSON giống hệt nhau (trừ `tao_luc`).
- Pivot/ITH tự viết trong script được kiểm **khớp 100%** với `swing_pivot(1,1)` và
  `swing_hierarchy(1,1)` khi tắt chặn gap.
- «Mỗi ngày» = mỗi **ngày giao dịch**. Bản 1 chia cho 208 ngày lịch UTC (gồm 35 Chủ nhật cụt) nên
  thấp hơn ~17%.

### 2.1. Lịch phiên và chất lượng dữ liệu

Phân loại bằng lịch phiên khai báo `cme_globex_metals` (`core/data/session_calendar.py`; nguồn và
cách kiểm ở `market-data-pipeline/docs/du_lieu_thi_truong.md` §5):

| Khoảng trống giữa hai nến M15 | Số lần | Ghi chú |
|---|---:|---|
| Nghỉ hằng ngày 17:00–18:00 NY | 133 | |
| Cuối tuần (Thứ Sáu 17:00 → Chủ nhật 18:00 NY) | 32 | |
| Lễ theo lịch (đóng sớm ngày lễ Mỹ, Good Friday) | 6 | |
| **Thiếu dữ liệu trong phiên** | 1 | 12/01/2024: mất 13:00–17:00 NY (16 nến M15), nguồn cũng thiếu |

- Bản trên dataset cũ có thêm 16 khoảng «bất thường» (nghỉ 16:00 NY trong 11–28/03, đóng tuần
  16:00 NY…). Toàn bộ là **lỗi quy đổi giờ khi nhập**, không phải lịch nguồn; hết sau khi sửa giờ.
- → Lịch phiên là **dữ liệu khai báo** theo nguồn (AGENTS §2.2), không phải hằng số trong code.
  Những gì không khớp lịch thì gắn cờ, không tự giải thích (§4.0).

### 2.2. Swing — chọn cấp nào làm «cấu trúc»

| Nguồn swing | Số / ngày | Trễ xác nhận TV / P90 (nến) | Biên độ nhịp TV / P90 (× ATR) |
|---|---:|---|---|
| Pivot 1/1 — STH/STL (`swing_pivot`) | 41.7 | 1 / 1 | 1.58 / 3.25 |
| Pivot 3/3 — baseline lab | 17.2 | 3 / 3 | — |
| **ITH/ITL** — cấp 2 trên 1/1 (`swing_hierarchy`) | **10.6** | **5 / 9** | **3.33 / 6.42** |
| ITH/ITL, cửa sổ pivot không vắt qua gap (survey-v2) | 10.2 | — | — |
| DC k = 1.5 (close, `bridge_short`) | 6.0 | 4 / 10 | 3.44 / 7.67 |
| LTH/LTL — cấp 3 (chặn gap) | 2.7 | 23 / 40 | — |

- STH/STL quá dày để gọi là cấu trúc; là **nguyên liệu**.
- LTH/LTL trễ trung vị 23 nến (~6 giờ) — chỉ hợp làm ngữ cảnh, hoặc lấy ITH/ITL của khung H1/H4.
- **ITH/ITL** cân bằng mật độ (~10/ngày) và trễ (trung vị 5 nến).
- **DC và ITH/ITL** — quy tắc đối chiếu:
  - Cùng phía (đỉnh với đỉnh), `event_bar_index` chênh ≤ 2 nến, không xét giá.
  - Một phần tử bên A được đếm nếu có ít nhất một phần tử bên B ở gần.
  - ITH theo wick, DC theo close; hai bên khác cả cách xác nhận lẫn chính sách gap.

  Kết quả: **77,5%** pivot DC có ITH/ITL ở gần; **43,7%** ITH/ITL có DC ở gần. Như vậy phần lớn
  pivot DC **trùng vị trí** với ITH/ITL, nhưng điều này **chưa chứng minh** DC là tập con hay chỉ là
  bộ lọc biên độ của ITH (bản 1 kết luận quá tay). Nguồn swing vẫn thay được; DC là biến thể để so
  trên nhãn.

### 2.3. Displacement và FVG (M15)

| Đo | Giá trị |
|---|---|
| Biên độ nến / ATR — TV, P90, P95 | 0.87, 1.68, 2.06 |
| Thân / biên độ — TV, P90 | 0.46, 0.82 |
| Nến đạt «biên độ ≥ 1.5 ATR **và** thân ≥ 60%» | **7.4%** số nến, 6.7 nến/ngày |
| FVG (3 nến, gắn ở nến 3) | **18.1/ngày**; kích thước TV 0.26 ATR, P90 0.88 ATR |
| FVG có nến giữa là displacement | 26% |
| Ứng viên FVG vắt qua giờ nghỉ (bị loại — đó là opening gap) | 88 |

Ngưỡng displacement ≈ 7% nến — mặc định có cơ sở số liệu, **do lab chọn**, không phải số ICT. FVG
thô quá phổ biến để mỗi FVG là một bằng chứng → cần cờ «FVG do displacement tạo ra».

### 2.4. Vùng thanh khoản — vòng đời theo tầng (định nghĩa §4.6)

| Tầng | Vùng / ngày | Bị lấy | Vùng bị *chạm nông* trước khi lấy | Độ xuyên khi lấy — TV (P90), × ATR | W = 0: sweep / run | W = 3: sweep / run / chưa rõ do gap |
|---|---:|---:|---:|---|---|---|
| M15 ITH/ITL | 10.1 | 1661 | 243 (14%) | 0.56 (1.93) | 684 / 977 | 1168 / 485 / 8 |
| H1 ITH/ITL | 2.7 | 417 | 45 | 0.70 (2.40) | 180 / 237 | 287 / 130 / 0 |
| H4 ITH/ITL | 0.68 | 93 | 12 | 0.78 (3.49) | 30 / 63 | 57 / 36 / 0 |
| PDH/PDL | 1.98 | 292 | 34 | 0.73 (2.41) | 118 / 174 | 193 / 99 / 0 |
| PWH/PWL | 0.39 | 49 | 6 | 0.80 (3.49) | 10 / 39 | 26 / 23 / 0 |

- Vùng bị vượt ngay trong khoảng từ cực trị tới lúc được biết → không tạo: 13 (M15), 1 (W).
- 14% vùng M15 từng bị chạm nông (< 0.1 ATR) rồi mới bị lấy — đây là chỗ bản 1 có hai định nghĩa.
- Với W = 0 phần lớn là *run*; W = 3 đảo lại. Mọi sweep W = 0 cũng là sweep W = 3 (cùng nến
  quay lại) → chỉ cần phát W = 3 kèm `sweep_bars` để lọc (D3).

### 2.5. Shift = sweep → displacement ngược chiều (định nghĩa §4.7)

| Đo | Sweep W = 0 | Sweep W = 3 |
|---|---|---|
| Số shift | 55 (**0.32/ngày**) | 153 (**0.88/ngày**) |
| Theo tầng vùng bị quét | M15 32 · H1 13 · D 9 · W 1 | M15 96 · D 26 · H1 26 · W 5 |
| Có FVG do chính displacement (biết ở d+1) | 56% | 55% |
| Displacement ngay trên nến quét | 15% | 5% |

| Killzone (giờ NY, theo giờ mở nến) | Ngoài | Asia 20–24 | London 02–05 | NY AM 07–10 |
|---|---:|---:|---:|---:|
| Tất cả nến (để so) | 56% | 18% | 13% | 13% |
| Shift (W = 0) | 29% | 18% | 13% | **40%** |
| Shift (W = 3) | 23% | 22% | 18% | **37%** |

Shift dồn mạnh vào NY AM (gấp ~3 lần tỷ lệ nến). Nhiều khả năng do biến động phiên Mỹ làm
displacement dễ xảy ra — **chưa phải bằng chứng lợi thế**. Killzone vẫn chỉ là cờ.

### 2.6. Ba thành phần bias (định nghĩa §4.5, §4.9, §4.10)

**Thứ tự đỉnh/đáy** (trạng thái sau mỗi nến M15):

| Khung | +1 (HH-HL) | −1 (LH-LL) | Lẫn lộn | Số lần đổi | Thời lượng ±1 — TV / P90 | ±1 nhưng mức được bảo vệ đã bị close vượt |
|---|---:|---:|---:|---:|---|---:|
| M15 | 30% | 22% | **48%** | 886 | 3.5 / 11.5 giờ | 12% thời gian |
| H1 | 31% | 25% | 43% | 241 | 16 / 65 giờ | 12% |
| H4 | 35% | 19% | 42% | 60 | 81 / 236 giờ | 13% |

**Phản ứng ở FVG khung lớn** (đo bằng close M15; §4.9):

| | FVG H1 | FVG H4 |
|---|---|---|
| Số vùng | 729 (4.2/ngày) | 218 (1.3/ngày) |
| Giá chạm sau khi biết — TV / P90 | 1 / 49 giờ | 4.5 / 80 giờ |
| Respect **lỏng** (close quay ra ngoài mép gần) / disrespect | **502 / 204** (71% respect) | **156 / 48** (76%) |
| Disrespect tính theo CE 50% | 454 / 252 | 138 / 66 |
| Respect **chặt** (rời mép gần ≥ 1 ATR M15) / disrespect | 325 / 381 | 114 / 90 |

- Respect lỏng gần như luôn xảy ra: một cái wick chạm vùng rồi đóng ra ngoài là đủ. Định nghĩa
  này không mang thông tin → mặc định đề xuất là bản chặt (D6).
- `pd_bias` (sự kiện gần nhất của H1+H4, bản chặt) đổi 410 lần, trung vị 7.5 giờ — **nhiễu**.

**DOL** (sau mỗi shift W = 0; §4.10):
- 54/55 shift có vùng đích.
- Khoảng cách tới đích: TV **6.1 ATR M15** (P25 4.0, P90 12.3).
- Đích thuộc tầng H1 41 lần, PDH/PDL 13 lần.
- DOL có giá trị 53% thời gian.

**Đồng thuận giữa các thành phần** (chỉ tính nến mà cả hai đều có chiều ±1):

| Cặp | Cùng chiều | Cặp | Cùng chiều |
|---|---:|---|---:|
| thứ tự H1 ~ thứ tự H4 | 56% | thứ tự H1 ~ pd | 52% |
| thứ tự M15 ~ thứ tự H1 | 55% | thứ tự H4 ~ pd | 52% |
| thứ tự H1 ~ DOL | **32%** | pd ~ DOL | 42% |
| thứ tự H4 ~ DOL | **41%** | thứ tự M15 ~ DOL | 37% |

Ba thành phần (thứ tự H1, pd, DOL) **cùng chiều chỉ 4.1%** thời gian, **mâu thuẫn 26%**, còn 70%
thiếu ít nhất một thành phần.

Rút ra cho thiết kế:
1. Ba thành phần đo **những thang thời gian khác nhau**:
   - DOL đặt ngay sau shift (một cú đảo) nên tự nhiên **ngược** thứ tự đỉnh/đáy cũ.
   - `pd_bias` phản ánh nhịp gần nhất.
   - Thứ tự H4 kéo dài nhiều ngày.

   Ghép chúng bằng một quy tắc tự đặt trong bộ nhận diện sẽ che mất thông tin. → v0.1 phát **ba
   thành phần riêng**; cách ghép thuộc **lớp kịch bản** của bạn (B3, §10 giai đoạn 4).
2. Thứ tự «lẫn lộn» chiếm 42–48% thời gian — đó là một trạng thái hợp lệ (thường là range hoặc
   chuyển tiếp), không phải lỗi.
3. `protected_broken` xảy ra ~12% thời gian ở mọi khung → đáng là một trường riêng cho regime.

### 2.7. Ví dụ thật để bạn tự kiểm (shift W = 0 đầu tháng 3/2024; mở XAUUSD M15)

| Cú quét (giờ UTC / NY) | Vùng bị quét | Nến quét H / L / C | Displacement (UTC) O → C | FVG |
|---|---|---|---|---|
| 11/03 13:00 / 09:00 — quét đáy | M15 ITL 2175.78 | 2178.17 / 2174.70 / 2176.73 | 13:30 tăng 2178.08 → 2183.61 | có |
| 15/03 01:15 / 21:15 (14/03) — quét đỉnh | M15 ITH 2164.91 | 2165.88 / 2163.95 / 2164.57 | 01:30 giảm 2164.61 → 2162.76 | có |
| 20/03 00:30 / 20:30 (19/03) — quét đáy | M15 ITL 2155.39 | 2155.68 / 2155.13 / 2155.49 | 00:45 tăng 2155.45 → 2157.08 | có |
| 20/03 04:00 / 00:00 — quét đỉnh | M15 ITH 2159.93 | 2160.14 / 2159.10 / 2159.31 | 04:45 giảm 2158.52 → 2156.79 | có |
| 28/03 10:45 / 06:45 — quét đỉnh | M15 ITH 2212.28 | 2213.64 / 2210.28 / 2212.09 | 11:30 giảm 2212.61 → 2208.85 | không |

Cả năm ví dụ đều nằm trong tuần Mỹ–Âu lệch lịch đổi giờ, nên giờ ở đây muộn hơn bản 2 đúng 1 giờ
(bản 2 đọc dataset lệch giờ). Ví dụ cuối trước đây gắn với một ITH H1; trên dữ liệu đúng giờ, mức đó
chỉ còn là ITH M15.

### 2.8. Giới hạn

- Script là **bản mẫu định nghĩa**, chưa phải thuật toán sẽ cài. Chưa có:
  - gộp EQH/EQL;
  - theo dõi FVG M15 chạm/lấp;
  - sự kiện `LIQ_UNRESOLVED` theo thời gian thực.
- Một năm, một mã, 55–153 shift — mẫu nhỏ.
- Lịch lễ khai báo 2018–2025 dựa trên thư viện lịch CME. Vài giờ đóng sớm ngày lễ chưa xác minh
  được bằng nguồn ngoài (`market-data-pipeline/docs/du_lieu_thi_truong.md` §5).
- Số liệu dùng để **chọn hướng và mặc định**, không dùng để kết luận chất lượng hay làm chuẩn
  nghiệm thu (§10).

---

## 3. Kiến trúc thuật toán

Một `StructureAlgorithm` tên `ict_structure` v0.1.0, ghép các thành phần mới trong
`core/components/` — chỉ `ict_structure` dùng ở v0.1 (R7). Engine, lưu trữ, đánh giá, giao diện
giữ nguyên.

```text
nến M15 t ─► [G] lịch phiên · gap · chất lượng ─► [A] ATR (giá trị t−1 cho nến t)
                 │
   ┌─────────────┼───────────────────┬──────────────────────┐
   ▼             ▼                   ▼                      ▼
[P1] STH/STL  [P3] displacement  [P2] FVG M15        [T] khung lớn H1/H4 (§11): nến ĐÃ CHỐT
   │             │                   │                → ITH/ITL · FVG H1/H4 · PDH/PDL · PWH/PWL
[S1] ITH/ITL     │                   │                      │
   │             │                   │                      │
[S2] thứ tự HH-HL + mức được bảo vệ  │                      │
[S4] dealing range · premium/discount│                      │
   │             │                   │                      │
[S3] vùng thanh khoản (mọi tầng) ◄──────────────────────────┤
   │             │                   │                      │
[E2] vòng đời: chạm → lấy → sweep / run / chưa rõ           │
   │             │                   │                      │
   └──► [E3] SHIFT = sweep → displacement ngược chiều ──► SHIFT_FVG (FVG do chính displacement)
                 │                                          │
           [S6] DOL: vùng đích sau shift            [S5] phản ứng ở FVG H1/H4 → pd_bias
                 │                                          │
                 ▼                                          ▼
     ba thành phần bias: thứ tự (S2) · pd_bias (S5) · DOL (S6) — KHÔNG ghép ở v0.1
                 │
          [C] killzone (giờ NY) ─► sự kiện + timeline + pending + giải thích
```

### 3.1. Thứ tự trong một nến t (cố định)

1. **[G]** Validate nến; phân loại khoảng trống trước nến t theo lịch phiên → `ICT_GAP`.
2. **[A]** ATR\[t−1\] dùng cho **mọi** ngưỡng của nến t; sau bước 10 mới cập nhật ATR\[t\].
3. **[E2]** Với vùng **đã biết trước t**:
   - các vùng đang chờ (đã lấy ở nến trước) → quay lại / hết cửa sổ / gặp gap;
   - các vùng còn nguyên → chạm / lấy ở nến t (rồi xét quay lại ngay trong nến t).
4. **[P3]** cờ displacement của nến t.
5. **[P2]** FVG với nến 3 = t; chạm/lấp của FVG M15 đang mở.
6. **[E3]** Ứng viên shift đang chờ (và ứng viên mới từ sweep ở bước 3): kiểm nến t (vượt cực
   trị → huỷ; displacement đúng điều kiện → `SHIFT`). Shift ở t−1 + FVG ở t có nến giữa t−1 →
   `SHIFT_FVG`.
7. **[S5]** Phản ứng của nến t ở các FVG khung lớn đã biết trước t.
8. **[S2]** Kiểm `protected_broken` bằng close\[t\] với mức đang có. Sau đó **[P1] → [S1]**:
   pivot/ITH/ITL xác nhận tại t → cập nhật thứ tự, mức được bảo vệ, **[S4]**, vùng mới **[S3]**.
   Tất cả có hiệu lực **từ t+1**.
9. **[S6]** DOL: đặt theo shift ở bước 6; kết thúc nếu đích bị lấy ở bước 3 (`DOL_REACHED`).
10. **[T]** Nến H1/H4/ngày/tuần chốt tại t → cập nhật ngăn xếp khung lớn, vùng/FVG/mức mới
    (hiệu lực từ t+1). Sau đó **[C]**, ghi timeline/pending.

Lý do thứ tự: mọi so sánh ở nến t chỉ dùng mức/vùng đã biết **trước** t. Như vậy một nến không thể
vừa tạo đỉnh vừa «quét» chính đỉnh đó. Cũng không có chuyện nến t vừa lật ngữ cảnh khung lớn vừa
được đếm là «cùng chiều» với sự kiện của chính nó.

---

## 4. Định nghĩa vận hành từng thành phần (v0.1.0)

### 4.0. [G] Lịch phiên, gap, chất lượng dữ liệu
- **Lịch phiên khai báo** — đã có: `data/calendars/cme_globex_metals.json` (XAUUSD),
  `data/calendars/fx_spot.json` (EURUSD), đọc bằng `core/data/session_calendar.py`. Mỗi lịch liệt kê
  từng phiên (giờ mở/đóng New York, `regular`/`early_close`) và các ngày đóng cửa. Lịch kim loại có:
  - nghỉ hằng ngày 17:00–18:00 NY;
  - cuối tuần từ Thứ Sáu 17:00 tới Chủ nhật 18:00 NY;
  - ngày lễ đóng cả ngày, hoặc đóng sớm kèm giờ đóng.

  Không suy lịch từ dữ liệu; nguồn và cách kiểm ở `market-data-pipeline/docs/du_lieu_thi_truong.md` §5.
- Mỗi khoảng trống giữa hai nến được phân loại (`SessionCalendar.classify_gap`):
  - `nghi_phien`, `cuoi_tuan`, `nghi_le` nếu mọi ô thiếu nằm ngoài phiên;
  - `thieu_trong_phien` (bất thường, kèm số ô thiếu) nếu ngược lại.

  Loại gap ghi vào `ICT_GAP`. Gap bất thường **không** được gộp thành Range/Uncertain (AGENTS §2.2).
- Chính sách gap (D1): **giữ** mức swing/vùng thanh khoản qua mọi gap. **Chặn**:
  - cửa sổ pivot (nến c−1..c+1) và bộ ba nến FVG vắt qua gap;
  - displacement ở nến đầu sau gap;
  - cửa sổ sweep/shift có gap (§4.6, §4.7).
- Nến khung lớn: chất lượng theo lịch (`coverage`, `degraded`, bucket mất trọn) — §11.4.

### 4.1. [P1] Swing ngắn hạn — STH/STL
- STH tại nến c: `high[c] > high[c−1]` **và** `high[c] > high[c+1]` (strict). Biết khi nến c+1 đóng.
  STL đối xứng. Outside bar có thể vừa là STH vừa là STL.
- Bằng nhau → không phải swing (giữ quy ước lab; ảnh hưởng EQH — D15).
- Nguồn thay thế (`swing_source`): `pivot`, `dc`.

### 4.2. [S1] Swing trung hạn — ITH/ITL (Larry Williams)
- ITH = STH có STH liền trước và liền sau **thấp hơn** (strict); biết khi STH bên phải xác nhận.
- `structure_level` ∈ {1, 2, 3}, mặc định **2**. Biến thể `min_leg_atr` (mặc định 0 = tắt).

### 4.3. [P3] Displacement
- Nến t là displacement tăng nếu `close > open`, `high−low ≥ k_disp·ATR[t−1]`,
  `|close−open| ≥ body_min·(high−low)`. Giảm đối xứng. Mặc định 1.5 và 0.6 (≈ 7% nến, §2.3).
- Không xét nến đầu sau gap.

### 4.4. [P2] FVG (M15)
- Tăng: `low[t] > high[t−2]`, vùng `[high[t−2], low[t]]`; giảm đối xứng. Gắn tại t
  (`event_bar` = t−1 để vẽ, `confirmed_at` = close t).
- Loại nếu có gap trong t−2..t. Ngưỡng `fvg_min_atr` (mặc định 0).
- `details.from_displacement` = nến giữa là displacement cùng chiều.
- Vòng đời: `FVG_TOUCHED` khi giá chạm lần đầu, `FVG_FILLED` khi đi hết vùng. «Đã lấp» chỉ là nhãn
  đánh giá có cửa sổ.

### 4.5. [S2] Thứ tự đỉnh/đáy và mức được bảo vệ
- Khi một ITH (ITL) mới có hiệu lực, so với ITH (ITL) liền trước, dung sai
  `eq_tol_atr·ATR` (ATR của khung, lúc xác nhận):
  - `hh` ∈ {+1, 0, −1} giữa hai ITH;
  - `hl` ∈ {+1, 0, −1} giữa hai ITL.
- `order` =
  - **+1** nếu `hh = +1` và `hl = +1`;
  - **−1** nếu cả hai bằng −1;
  - **0 (lẫn lộn)** trong mọi trường hợp còn lại (mở rộng, thu hẹp, bằng nhau);
  - `none` khi chưa đủ 2 ITH và 2 ITL.
- `order` **chỉ đổi khi có swing mới**, không đổi vì close vượt một mức nào.
- **Mức được bảo vệ — một định nghĩa duy nhất:**
  - `order = +1` → ITL gần nhất (HL);
  - `order = −1` → ITH gần nhất (LH);
  - `order = 0` → không có.
- `protected_broken` = đã có close vượt mức được bảo vệ kể từ khi nó trở thành mức được bảo vệ;
  xoá khi mức đổi. **Không** phát sự kiện, **không** đổi `order`.
- Ví dụ của review:
  - `order = +1`, mức được bảo vệ ITL 100.
  - ITL mới 105 xác nhận (HL so với 100) → mức được bảo vệ chuyển thành **105**.
  - Close 104 → `protected_broken = true`, `order` vẫn +1 cho tới swing mới.

  Không có sự kiện nào báo «đổi hướng» ở đây; đổi hướng chỉ đến từ shift (§4.7).
- Nhãn HH/LH/EQH, HL/LL/EQL nằm trong `details` của ITH/ITL.

### 4.6. [S3] Vùng thanh khoản và [E2] vòng đời: chạm → lấy → sweep / run
- **Nguồn vùng (tầng):**
  - M15 ITH/ITL;
  - H1/H4 ITH/ITL (§11);
  - PDH/PDL, PWH/PWL (§11, D13).

  EQH/EQL: hai ITH (ITL) liên tiếp cùng tầng chênh ≤ `eq_tol_atr·ATR` → một vùng gộp.
- **Hiệu lực** từ nến sau nến làm vùng được biết. Nếu trong khoảng từ cực trị tới lúc biết đã có
  nến xuyên ≥ ngưỡng thì vùng **không được tạo** (đã bị lấy trước khi biết).
- **Trạng thái** (BSL; SSL đối xứng):
  - `intact` → **chạm** khi `0 < high[t] − mức < min_pen·ATR[t−1]`. Vùng vẫn `intact`; tăng
    `touch_count`; không phát sự kiện.
  - **Lấy** tại nến b đầu tiên có `high[b] − mức ≥ min_pen·ATR[b−1]` (mặc định 0.1).
    **ATR khoá** = ATR\[b−1\]; `pen_atr` tính theo ATR khoá. Đây là **định nghĩa duy nhất** của «đã
    lấy»; vùng không bao giờ quay lại `intact`.
- **Giải quyết** sau khi lấy, cửa sổ `sweep_window` = W (mặc định 3, D3):
  - `LIQ_SWEEP_BSL` tại r = nến **đầu tiên** trong `[b, b+W]` (tính cả b) có `close[r] < mức`,
    với điều kiện **không** có gap trong (b, r]. Ghi `sweep_bars = r − b` (0 = quay lại cùng nến).
  - `LIQ_RUN_UP` tại b+W nếu hết cửa sổ mà không quay lại.
  - `LIQ_UNRESOLVED` nếu gặp gap (mọi loại) trước khi rõ. Phát tại nến đầu tiên sau gap, ghi
    loại gap; không thành sweep hay run.
  - Hết dữ liệu khi đang chờ → vẫn là pending (không phát gì).
- Một nến lấy nhiều vùng cùng phía: mỗi vùng có vòng đời riêng. Sự kiện được gom theo
  (nến, phía), `details.pools` liệt kê các vùng, `tier` = tầng cao nhất.

### 4.7. [E3] Shift = sweep → displacement ngược chiều (thay BOS/CHoCH/MSS)
- **Đầu vào:** một `LIQ_SWEEP` tại r, nến lấy b. Cực trị cú quét
  `X = max(high[b..r])` (BSL) hoặc `min(low[b..r])` (SSL).
- **Shift giảm** (sau khi quét BSL) tại d = nến **đầu tiên** trong `[r, r + shift_window]` (mặc định
  3) thoả cả bốn điều kiện:
  1. d là displacement giảm (§4.3);
  2. `close[d] <` mức bị quét;
  3. không có gap trong (r, d];
  4. không nến nào trong (r, d] có `high > X`. Nếu có, cú quét đã bị vượt → **huỷ**, không tìm
     tiếp.

  Shift tăng đối xứng.
- **Cùng một nhịp (R4):**
  - Shift tham chiếu **đúng một** nến displacement (d) và các sweep dẫn tới nó.
  - Nhiều sweep cùng dẫn tới một d → **một** `SHIFT`, `details.swept` liệt kê tất cả, `tier` = cao
    nhất.
- **FVG xác nhận:** nếu FVG cùng chiều tại d+1 có **nến giữa = d** (FVG do chính displacement tạo
  ra) → phát `SHIFT_FVG` tại d+1 với `reference_event_id` = shift. Shift **không bị sửa**. Không
  tìm FVG ở xa hơn.
- **Khi đánh giá:** sweep → shift → shift_fvg mang cùng `group_id` và tính là **một cơ hội**.
  `event_type_map` chọn một tầng (`SHIFT` hoặc `SHIFT_FVG`), không đếm cả hai.
- **Ngôn ngữ:** đây là «shift có displacement» tại lúc phát hiện. Không gọi «đảo chiều thật» —
  chưa biết nó sẽ tiếp diễn hay thất bại.

### 4.8. [S4] Dealing range, premium/discount
- `range_hi` = max(ITH gần nhất, high cao nhất từ nến cực trị của ITH đó tới nến hiện tại).
  `range_lo` đối xứng với ITL. Cập nhật dần, nhân quả.
- Dealing range **luôn chứa giá** nên `zone` (premium > EQ > discount) luôn xác định.
  `range_pos` ∈ [0, 1].
- Khác bản 1 (neo vào BOS — không còn). Bản 1 đo vùng «ITL..ITH gần nhất» không mở rộng: giá nằm
  **ngoài** vùng đó 35% thời gian, vì vậy bỏ định nghĩa này.
- Mức được bảo vệ (§4.5) hiển thị cùng dealing range.

### 4.9. [S5] Phản ứng ở PD array khung lớn → `pd_bias`
- v0.1 chỉ dùng **FVG H1/H4** (order block để v0.2). Một vùng FVG khung lớn hợp lệ khi:
  - là ba nến khung lớn **đã chốt**, liền kề nhau theo lịch (không vắt qua nghỉ phiên/cuối tuần,
    không có bucket mất);
  - không nến nào `degraded`.

  Vùng có hiệu lực từ nến M15 sau lúc chốt nến thứ ba. Cờ `from_displacement` theo ATR của khung
  lớn.
- **Tương tác đo bằng close M15 đã đóng.** `tap` = lần đầu giá chạm vùng. Từ nến tap trở đi, kết
  quả **đầu tiên** xảy ra được ghi:
  - `PD_DISRESPECT`: close vượt **mép xa** (FVG tăng: close < mép dưới).
  - `PD_RESPECT` (mặc định **chặt**): close rời **mép gần** ≥ `respect_away_atr`·ATR M15 (mặc
    định 1.0) trước khi disrespect.
  - Biến thể để so: **lỏng** (close ra ngoài mép gần, bất kỳ khoảng nào — §2.6 cho thấy gần như
    luôn đúng) và **CE** (disrespect khi close vượt 50% vùng).
- Mỗi vùng chỉ có **một** kết quả; sau đó vùng là `used`. Vùng bị disrespect đổi vai (IFVG) —
  để v0.2.
- `pd_bias` = chiều hàm ý của sự kiện PD gần nhất (H1 và H4 gộp; `details` ghi khung nguồn):
  - respect FVG tăng → +1; disrespect FVG tăng → −1;
  - FVG giảm thì ngược lại.

### 4.10. [S6] DOL (draw on liquidity)
- Sau mỗi `SHIFT`:
  - `dol_side` = chiều shift;
  - `dol_target` = vùng **chưa bị lấy** gần nhất phía đó, ở tầng ≥ `dol_min_tier` (mặc định H1:
    ITH/ITL H1/H4, PDH/PDL, PWH/PWL), nằm ngoài close nến shift. Ghi khoảng cách theo ATR M15.
- Hết hiệu lực khi đích bị lấy (phát `DOL_REACHED` tại nến lấy) hoặc khi có shift mới (thay thế).
  Không có vùng nào phía đó → `none`.
- «Tỷ lệ đạt DOL» là **nhãn đánh giá nhìn về sau**, không bao giờ là đặc trưng hay đầu vào.
- Định nghĩa khác (DOL theo premium/discount khung lớn, theo vùng D/W lớn nhất) để so ở v0.2 (D7).

### 4.11. [C] Phiên / killzone
- Giờ New York có đổi giờ mùa hè (`zoneinfo`), theo giờ mở nến:
  - Asia 20–24;
  - London 02–05;
  - NY AM 07–10;
  - London close 10–12.

  Khung giờ là tham số.
- Chỉ là cờ trong `details`/timeline, không lọc sự kiện ở v0.1.

---

## 5. Đầu ra

### 5.1. Sự kiện

| Loại | Dùng lại / mới | Ghi chú |
|---|---|---|
| `SWING_HIGH` / `SWING_LOW` | có sẵn | STH/STL — ẩn mặc định |
| `SWING_HIGH_L2` / `SWING_LOW_L2` | có sẵn | ITH/ITL; `details.hh/hl`, `order` sau swing |
| `SWING_HIGH_L3` / `SWING_LOW_L3` | mới | chỉ khi bật cấp 3 |
| `DISPLACEMENT_UP/DOWN` | mới | ẩn mặc định; làm `basis` |
| `FVG_UP/DOWN`, `FVG_TOUCHED`, `FVG_FILLED` | mới | FVG M15 |
| `LIQ_SWEEP_BSL/SSL` | mới | `pools`, `tier`, nến lấy b, `sweep_bars`, `pen_atr`, ATR khoá |
| `LIQ_RUN_UP/DOWN` | mới | hết cửa sổ, không quay lại |
| `LIQ_UNRESOLVED` | mới | gặp gap trong cửa sổ |
| `SHIFT_UP/DOWN` | mới | §4.7; `swept`, nến displacement, X, `group_id` |
| `SHIFT_FVG_UP/DOWN` | mới | tại d+1, `reference_event_id` = shift |
| `PD_RESPECT_UP/DOWN`, `PD_DISRESPECT_UP/DOWN` | mới | FVG H1/H4, `details.tf`, biến thể |
| `DOL_REACHED` | mới | đích DOL bị lấy |
| `HTF_SWING_HIGH/LOW`, `HTF_FVG_UP/DOWN`, `HTF_BAR_DEGRADED` | mới | ẩn mặc định, ngoài đánh giá M15 (§11.5, D12) |
| `ICT_GAP` | mới | loại gap theo lịch |
| ~~`BOS_*`, `CHOCH_*`, `MSS_*`~~ | — | **không phát** (B1) |

Mọi sự kiện M15 mang `details.htf` (ảnh chụp ngữ cảnh khung lớn, §11.5) và `details.killzone`.

### 5.2. Trạng thái mỗi nến (timeline) — bằng chứng cho regime
`order_M15`, `protected`, `protected_broken`, `range_lo/hi`, `eq`, `zone`, `range_pos`,
`pending_sweeps`, `last_sweep` (+ phía, tầng, số nến), `last_shift` (+ chiều, số nến, có
`SHIFT_FVG`), `dol_side`, `dol_target` (+ tầng, khoảng cách ATR), `pd_bias` (+ khung nguồn, số
nến), `open_fvg_up/down`, `killzone`, `atr`, `gap_state`; các cột khung lớn ở §11.5.

### 5.3. Bằng chứng → regime (bản nháp cho bước sau, **chưa** nằm trong v0.1)

| Regime | Bằng chứng nháp |
|---|---|
| Trend tăng | `order` +1 (M15 và/hoặc khung lớn), không `protected_broken`; pd_bias +1; DOL lên |
| Range | `order` lẫn lộn; sweep ở hai biên không kèm displacement; dealing range không mở rộng |
| Breakout | `LIQ_RUN` có displacement cùng chiều sau giai đoạn range |
| Uncertain | thành phần mâu thuẫn (§2.6: 26% thời gian); `protected_broken`; khởi động; gap bất thường; nến khung lớn `degraded` |

Cách ghép là việc của **lớp kịch bản bias** (B3), làm sau khi v0.1 có số liệu trên nhãn.

---

## 6. Tham số v0.1.0

| Tham số | Mặc định | Ghi chú |
|---|---:|---|
| `timeframe` | M15 | tự điền theo dataset |
| `session_calendar` | theo mã | `cme_globex_metals` (XAUUSD), `fx_spot` (EURUSD) — `data/calendars/` (D14) |
| `swing_source` | `pivot` | `pivot` \| `dc` |
| `pivot_left`, `pivot_right` | 1, 1 | |
| `structure_level` | 2 | ITH/ITL |
| `min_leg_atr` | 0 | |
| `atr_period` | 14 | Wilder, seed theo close trước |
| `k_disp`, `body_min` | 1.5, 0.6 | ≈ 7% nến |
| `fvg_min_atr` | 0 | |
| `eq_tol_atr` | 0.1 | HH/HL, EQH/EQL |
| `min_pen_atr` | 0.1 | ngưỡng «lấy» (D4) |
| `sweep_window` | 3 | `sweep_bars` để lọc bản cùng nến (D3) |
| `shift_window` | 3 | (D5) |
| `respect_away_atr` | 1.0 | `pd_respect_mode` = `strict` \| `loose` \| `ce` (D6) |
| `dol_min_tier` | H1 | (D7) |
| `htf_list` | `H1,H4` | rỗng = tắt [T] |
| `htf_alignment` | `ny_1700` | (D10) |
| `htf_min_coverage` | 0.9 | (D14) |
| `period_levels` | bật | PDH/PDL, PWH/PWL làm vùng thanh khoản (D13) |
| `htf_events` | ẩn | (D12) |
| `gap_policy` | giữ mức, chặn cửa sổ | (D1) |

---

## 7. Để sau (v0.2+)

- **Order block / breaker**, **IFVG** (FVG bị disrespect đổi vai), PD array khung lớn ngoài FVG.
- Sweep đo trên nến khung lớn (hiện chỉ đo bằng nến M15 với vùng mọi tầng).
- DOL theo premium/discount khung lớn hoặc vùng D/W lớn nhất; NDOG/NWOG; SMT; OTE.
- Cấu trúc D1; M5 để tinh chỉnh.
- **Lớp kịch bản bias** và bộ phân loại regime (§5.3); so với `dc_regime`, `indicator_baseline`.

---

## 8. Quyết định

### 8.1. Đã chốt (người dùng, 02/10/2026)

| # | Quyết định |
|---|---|
| B1 | `ict_structure` **không** có BOS/CHoCH/MSS. BOS/CHoCH chỉ còn ở baseline `swing_pivot` để so |
| B2 | Đổi hướng = **sweep rồi displacement ngược chiều** (shift, §4.7) |
| B3 | Bias = ba thành phần **riêng**: thứ tự đỉnh/đáy (§4.5), phản ứng ở PD array khung lớn (§4.9), DOL (§4.10). v0.1 không ghép |

### 8.2. Đã duyệt (người dùng, 04/10/2026) — đúng theo đề xuất

Đây là **mặc định v0.1** (cấu hình thí nghiệm, AGENTS §5.2), không phải giá trị «tối ưu». Khi đã có
nhãn (D8), đổi mặc định nào cũng đi qua vòng ⑦–⑧ và tăng phiên bản.

| # | Câu hỏi | Quyết định | Căn cứ |
|---|---|---|---|
| D1 | Gap | **Giữ** mức qua mọi gap; **chặn** cửa sổ pivot/FVG/displacement/sweep/shift vắt qua gap | §4.0 |
| D2 | Cấp cấu trúc | ITH/ITL (cấp 2 trên 1/1); DC là biến thể | §2.2 |
| D3 | Cửa sổ sweep | Phát **W = 3**; `sweep_bars = 0` là bản cùng nến (tập con, lọc được) | §2.4: sweep W = 0 ⊂ W = 3; tránh hai run |
| D4 | Ngưỡng «lấy» | 0.1·ATR khoá tại nến lấy; nông hơn = chạm | §2.4: 14% vùng M15 bị chạm nông trước |
| D5 | Shift | `shift_window` = 3; quy tắc cùng nhịp §4.7; FVG phải do chính displacement | §2.5: 0.32–0.88/ngày, ~55% có FVG |
| D6 | Respect PD array | **Chặt** (rời mép gần ≥ 1 ATR M15) mặc định; lỏng và CE là biến thể | §2.6: lỏng → 71–78% respect, không mang thông tin |
| D7 | DOL | Vùng chưa bị lấy gần nhất, tầng ≥ H1, phía shift | §2.6: 54/55 shift có đích, TV 6.1 ATR |
| D8 | Nhãn tham chiếu | Gán **ITH/ITL** và **shift** trên 2 tuần dev + 2 tuần test | Không có nhãn thì D3–D7 không quyết được bằng số liệu |
| D9 | Phạm vi khung | Cấu trúc M15; ngữ cảnh H1 + H4 gộp nội bộ; D/W chỉ là mức theo kỳ | §11.1 |
| D10 | Mốc nến khung lớn | `ny_1700` cho `ict_structure`; `utc_epoch` giữ cho `c2_cisd_research` | §11.3 |
| D11 | Khung lớn: bộ lọc hay đặc trưng? | **Đặc trưng**; không lọc sự kiện M15 | §11.2 |
| D12 | Sự kiện khung lớn | `HTF_*` ẩn mặc định, ngoài `event_type_map` | Không đếm trùng khi đánh giá M15 |
| D13 | PDH/PDL, PWH/PWL | **Đổi so với bản 1:** làm vùng thanh khoản ngay ở v0.1 | B2/B3 dựa trên quét thanh khoản và DOL; §2.4: PDH/PDL 1.96 vùng/ngày |
| D14 | Lịch phiên và dữ liệu thiếu | Lịch khai báo theo nguồn (**đã có** 2018–2025, `data/calendars/`); gap trong phiên = bất thường; nến khung lớn `coverage` < 0.9 = `degraded` | §2.1, §11.3; `market-data-pipeline/docs/du_lieu_thi_truong.md` §5 |
| D15 | Hai đỉnh bằng nhau | Giữ strict ở v0.1; biến thể ở v0.2 | Nhất quán với lab |

### 8.3. Đã chốt (06/10/2026) — order flow

Cơ sở: [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) — ICT nói gì về order flow
(§2), đo trên dữ liệu lab (§5), quyết định (§7), số mô tả các quy tắc «chưa rõ» (§8). Cài ở `ict_structure`
0.3.0 ([`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §4.12). Không thêm tham
số, mục tiêu chấm hay loại nhãn.

| # | Quyết định | Lý do |
|---|---|---|
| OF1 | Dải order flow đọc theo **run + shift** («thanh khoản → thanh khoản»): `LIQ_RUN_UP` / `SHIFT_UP` đã xác nhận → tăng, `LIQ_RUN_DOWN` / `SHIFT_DOWN` → giảm. Sweep, FVG, displacement, HH/HL **không** là đầu vào. Order flow là **mô tả**, không phải dự báo | Khớp ICT: order flow đọc thuần từ giá, giá đi từ thanh khoản tới thanh khoản; khi tăng, đáy ngắn hạn bị quét chỉ là stop run (nghiên cứu §2). Dùng đúng sự kiện lab đã có (run; shift — B2). Trên dữ liệu lab không cách đọc nào dự báo phía thanh khoản bị lấy kế tiếp tốt hơn mốc ngẫu nhiên (nghiên cứu §5), nên chọn cách đọc sát ICT, ít lật, dễ giải thích |
| OF2 | «Chưa rõ» = run phía **ngược** order flow đang có (không lật ngay); shift vẫn lật thẳng; hai chiều cùng nến → chưa rõ; từ chưa rõ, run hoặc shift kế tiếp đặt chiều. **Bỏ** quy tắc «hai phía đều bị run trong N nến» | ICT: mức đang tin bị phá → «sitting on my hands», chờ thêm thông tin (nghiên cứu §2). Quy tắc hai phía gần như không xảy ra: ở N = 4/8/16 nến M15 chỉ thêm < 0.1 đoạn chưa rõ mỗi ngày giao dịch và ≤ 0.5 điểm % thời gian; ghép vào quy tắc trên thì gần như trùng (nghiên cứu §8.2) |

---

## 9. Kiểm thử bắt buộc (theo AGENTS.md §7.1)

- **Tính tay:**
  - STH/STL với outside bar và nến bằng nhau; ITH cần STH bên phải xác nhận;
  - FVG đúng ngưỡng, FVG vắt qua gap bị loại; displacement đúng/thiếu ngưỡng.
- **Thứ tự đỉnh/đáy (§4.5):**
  - ví dụ 100 → 105 → close 104: `protected` = 105, `protected_broken` = true, `order` vẫn +1,
    không có sự kiện;
  - `order` 0 khi HH + LL; dung sai EQ.
- **Vòng đời thanh khoản (§4.6):**
  - xuyên 0.05 ATR rồi 0.15 ATR → lần đầu chỉ là chạm, lần sau là lấy;
  - ATR khoá đúng nến;
  - W tính cả nến lấy; quay lại ở b+3 là sweep, ở b+4 là run;
  - gap trong cửa sổ → `LIQ_UNRESOLVED` tại nến sau gap;
  - vùng đã bị vượt trước khi biết → không tạo;
  - một nến lấy nhiều vùng.
- **Shift (§4.7):**
  - displacement ngay nến quét; displacement ở r+3;
  - nến vượt X trước displacement → huỷ; gap → huỷ;
  - FVG ở d+1 có nến giữa d → `SHIFT_FVG`; FVG khác → không;
  - hai sweep cùng dẫn tới một d → một shift;
  - `group_id` chung.
- **PD (§4.9):**
  - tap rồi respect chặt / disrespect;
  - một kết quả mỗi vùng;
  - vùng vắt qua cuối tuần hoặc có nến `degraded` → không tạo.
- **DOL (§4.10):** chọn vùng gần nhất đúng tầng; hết hiệu lực khi lấy hoặc khi có shift mới;
  `none`.
- **Thứ tự trong nến:** nến vừa xác nhận ITH không được quét chính ITH đó ở cùng nến; vùng/FVG
  khung lớn mới chốt ở t chỉ có hiệu lực từ t+1.
- **Nhân quả:**
  - prefix = full ở nhiều điểm cắt, có gap và cắt giữa nến H4;
  - sửa đuôi không đổi quá khứ; deep-copy;
  - replay lùi = prefix mới;
  - `basis`/`reference` không trỏ tới sự kiện xác nhận sau nó.
- **Tương đương (không refactor):** pivot/ITH của `core/components` khi tắt chặn gap khớp
  `swing_pivot(1,1)` và `swing_hierarchy(1,1)` trên cùng dữ liệu.
- **Hồi quy:** mọi thuật toán cũ không đổi output — chúng không bị đụng tới.
- **Khung lớn:** §11.7.

---

## 10. Lộ trình triển khai (sau khi duyệt)

Mỗi giai đoạn xong và được duyệt mới sang giai đoạn sau. **Không refactor thuật toán cũ.**

| Giai đoạn | Nội dung | Nghiệm thu |
|---|---|---|
| **1** | [G] lịch phiên khai báo + phân loại gap; [P1] [S1] swing; [S2] thứ tự + mức được bảo vệ; [S4] dealing range; timeline; giao diện tối thiểu | Test §9 phần tương ứng + nhân quả; smoke trình duyệt trên bản sao DB |
| **2** | [P3] displacement, [P2] FVG + vòng đời; [S3]/[E2] vòng đời thanh khoản M15; [E3] shift + `SHIFT_FVG` + `group_id`; killzone; khung «Thuật toán đang làm gì» vẽ chuỗi quét → displacement → FVG | Test §9; đếm so với survey-v2 — **sai lệch có giải thích** (survey là bản mẫu, không phải chuẩn đúng) |
| **3** | [T] khung lớn (§11): bộ gộp `ny_1700` + lịch + coverage + `known_at`; ngăn xếp H1/H4; vùng H1/H4 và PDH/PDL/PWH/PWL; [S5] phản ứng FVG khung lớn; [S6] DOL; lớp phủ H4 | Test §11.7; hồi quy `c2_cisd_research` khớp 100% |
| **4** | Lớp kịch bản bias của bạn (cách ghép ba thành phần) → regime; so với `dc_regime` | Theo spec riêng, sau khi có nhãn (D8) |

Song song: bạn gán nhãn ITH/ITL và shift (D8). Viết `docs/algorithms/thuat_toan_ict_structure.md` cùng
giai đoạn 1 và cập nhật theo từng giai đoạn.

---

## 11. Bộ phân tích khung thời gian

Hai câu hỏi khác nhau, hai bộ phận khác nhau:

| | (A) Hồ sơ khung — *chạy cấu trúc ở khung nào?* | (B) Ngữ cảnh khung lớn — *M15 đang ở bối cảnh H1/H4 nào?* |
|---|---|---|
| Loại | Công cụ đo, chạy ngoài thuật toán | Thành phần **[T]** trong `ict_structure`, nhân quả từng nến |
| Đầu ra | Bảng so sánh các khung + JSON tái lập | Vùng/FVG khung lớn cho S3/S5, `details.htf`, timeline, lớp phủ |
| Phục vụ | Chọn khung (D9), chọn tham số theo khung | Bằng chứng cho regime/router |

### 11.1. Hồ sơ khung (survey-v2)

M5 là dataset thật. H1, H4, D gộp tuần tự từ M15 thật theo mốc `ny_1700`. Trễ tính theo
**đồng hồ thật** (gồm cả nghỉ phiên và cuối tuần).

| Khung | ITH/ITL mỗi ngày | STH/STL mỗi ngày | Trễ xác nhận — nến (TV / P90) | Trễ — giờ thật (TV / P90) | Biên độ nhịp TV | Biên độ TV theo ATR của khung |
|---|---:|---:|---|---|---:|---:|
| M5 | 30.3 | 120 | 5 / 9 | 0.42 / 0.75 | 4.7 USD | 3.33 |
| **M15** | **10.2** | 40.4 | 5 / 9 | **1.25 / 2.5** | 8.5 USD | 3.33 |
| H1 | 2.7 | 10.4 | 5 / 9 | 5 / 10 | 19.9 USD | 3.59 |
| H4 | 0.68 | 2.7 | 5 / 8 | 24 / 72 | 43.6 USD | 3.69 |
| D | 0.11 | 0.45 | 5 / 8 | 168 / 288 | 104.7 USD | 3.49 |

Thứ tự đỉnh/đáy theo khung: xem bảng §2.6. Thêm khung D: chỉ đổi **8 lần** trong 8 tháng, chưa có
trạng thái trong 24% thời gian đầu đoạn.

Rút ra:
1. **Cấu trúc gần như tự đồng dạng theo khung.** Đo bằng ATR của chính khung, biên độ nhịp ITH/ITL
   chỉ dao động 3.3–3.7 từ M5 tới D.
   - Tham số tính **theo ATR** (`k_disp`, `min_pen_atr`, `eq_tol_atr`, `respect_away_atr`) dùng
     chung được.
   - Tham số tính **theo nến/giờ** (`sweep_window`, `shift_window`, killzone) thì không.
2. **Trễ theo nến cố định (~5 nến) nên trễ theo giờ tăng theo khung.** ITH H4 được biết trung vị
   24 giờ (P90 72 giờ, vì vắt qua cuối tuần). Ngữ cảnh khung lớn luôn là thông tin cũ — phải mang
   theo **tuổi**.
3. **D không đủ mẫu làm nguồn cấu trúc** → D/W chỉ đóng vai **mức theo kỳ** (PDH/PDL, PWH/PWL).

### 11.2. Ngữ cảnh khung lớn có mang thông tin cho shift không?

55 shift (W = 0). Trạng thái lấy ở nến **trước** shift (d−1; với dealing range lấy ở b−1).
«Ngẫu nhiên» = tỷ lệ kỳ vọng nếu shift độc lập với ngữ cảnh, tính từ tỷ lệ thời gian của mỗi trạng
thái.

| Đo | Thực tế | Ngẫu nhiên |
|---|---:|---:|
| Shift cùng chiều thứ tự H1 | 38% | 28% |
| Shift cùng chiều thứ tự H4 | 36% | 28% |
| Shift cùng chiều pd_bias | **33%** | 50% |
| Shift cùng chiều DOL đang có (từ shift trước) | 20% | 26% |
| Cực trị cú quét nằm đúng phía dealing range H1 (tăng ở discount / giảm ở premium) | **82%** | 55% |
| Như trên, dealing range H4 (n = 54) | 69% | 52% |

Rút ra:
1. Với n = 55, sai số chuẩn ~±6 điểm %. Thứ tự H1 cao hơn ngẫu nhiên ~1,7 sai số chuẩn, H4 ~1,5 —
   **chưa đủ** để thành bộ lọc. → Khung lớn là **đặc trưng**, không lọc (D11).
2. Shift thường **ngược** pd_bias. Hợp lý về cơ học: trước khi quét đáy, giá vừa đi xuống xuyên qua
   FVG tăng (disrespect → pd −1). pd_bias đo nhịp gần, không đo bối cảnh.
3. Vị trí cú quét trong dealing range khung lớn khớp sách ICT (quét đáy ở discount) với chênh lệch
   lớn. Một phần là cơ học: quét đáy nghĩa là giá đang ở vùng thấp. Cần null ghép cặp (§11.6) trước
   khi coi đây là thông tin.

### 11.3. Cơ chế dữ liệu: mốc nến, lịch phiên, rò rỉ tương lai

| Đo | `ny_1700` | `utc_epoch` |
|---|---|---|
| H4: số nến · nến cụt (< nửa trung vị) | 1037 · **5** | 1071 · **36** (Chủ nhật) |
| H4: thiếu > 10% so với lịch | 0 | 1 |
| D: số nến · nến cụt | 173 · **0** | 207 · **35** |
| D: thiếu > 10% so với lịch | 1 (12/01) | 1 |
| Thứ tự H4 khác nhau giữa hai mốc | **30%** số nến M15 | |
| Nến H1/H4 nhiều nến con hơn lịch | 0 / 0 | |
| Chốt muộn (thiếu nến cuối, chốt khi kỳ sau mở) — D | 6 lần, lâu nhất 49 giờ (ngày nguồn dừng sớm) | |

Bản trên dataset lệch giờ có 15 nến H4 «thiếu > 10%» và 14 nến «nhiều hơn lịch» — đều do lỗi quy đổi
giờ, không còn sau khi sửa.

Thêm: dùng nến khung lớn **đang hình thành** thay vì nến đã chốt làm thứ tự sai ở **6.1% (H1)** và
**5.9% (H4)** số nến M15. Các nến sai dồn đúng quanh lúc khung lớn đổi trạng thái.

Rút ra:
1. **Mốc nến là tham số làm đổi kết quả.**
   - Mốc UTC sinh nến Chủ nhật cụt và cắt giờ nghỉ vào giữa nến.
   - Mốc 17:00 NY đặt giờ nghỉ ở đầu ngày giao dịch.

   → `ny_1700` (D10). Đã đối chiếu D1 với broker FXCM (EURUSD): theo mốc 17:00 NY, close lệch
   trung vị 0.5 pip; theo mốc UTC lệch 3 pip (`market-data-pipeline/docs/du_lieu_thi_truong.md` §8). Nến H4/D1 của TradingView
   chưa so tự động — có danh sách để so bằng mắt ở §8.
2. **Chỉ dùng nến khung lớn đã chốt.** Nến đang hình thành chỉ được vẽ, có nhãn.
3. Với lịch khai báo và ngưỡng `coverage` 0.9, chỉ còn 1 nến D bị coi là thiếu (12/01/2024, nguồn
   dừng từ 13:00 NY). Ngày lễ không bị coi là mất dữ liệu.

### 11.4. Thiết kế (B): thành phần [T]

```text
nến M15 t ─► bước 1–9 của §3.1 (dùng ngữ cảnh khung lớn đã chốt ≤ t−1)
                │
                ▼ bước 10
     [T0] bộ gộp (ny_1700, lịch khai báo) ── nến H1/H4/ngày/tuần nào vừa CHỐT tại t?
                │                                 (kèm coverage, degraded, known_at)
       ┌────────┴──────────┐
       ▼                   ▼
 [T1] ngăn xếp H1     [T1] ngăn xếp H4       cùng thành phần với M15, ATR riêng từng khung:
 P1→S1→S2, S4         P1→S1→S2, S4           ITH/ITL → thứ tự → dealing range;
 FVG H1 (cho S5)      FVG H4 (cho S5)        ITH/ITL thành vùng thanh khoản cho S3
       └────────┬──────────┘
                ▼
     [T2] mức theo kỳ: PDH/PDL, PWH/PWL (vùng cho S3); giá mở ngày, midnight open (ngữ cảnh)
                ▼
     [T3] ảnh chụp ngữ cảnh ─► timeline nến t; sự kiện M15 dùng từ nến t+1
```

- **Một luồng dữ liệu.** Chỉ nạp dataset khung nhỏ; khung lớn gộp **bên trong**, tuần tự.
- **[T0] Bộ gộp** — mở rộng `core/data/htf_stream.py`:
  - `alignment` ∈ {`utc_epoch` (giữ nguyên cho `c2_cisd_research`), `ny_1700`}. Với `ny_1700`:
    ngày giao dịch bắt đầu 17:00 NY, H4 = 6 nến từ 17:00 NY, tuần từ Chủ nhật 17:00 tới Thứ Sáu
    17:00 NY.
  - **Chốt nến:** khi nến LTF có `close_time` = `period_end`. Nếu thiếu nến cuối thì chốt khi nến
    đầu của kỳ sau tới.
  - **Mỗi nến chốt mang:**
    - `period_end` (mốc đóng theo lịch);
    - `known_at` (close của nến LTF làm hệ thống biết đã chốt) — **hai trường riêng** (R5);
    - `n_bars`, `expected_bars` (theo lịch khai báo), `coverage`.
  - **Chất lượng (R3):**
    - `degraded` = `coverage` < `htf_min_coverage` (0.9) hoặc kỳ đầu dataset thiếu nến;
    - `over` = nhiều nến hơn lịch → lịch dữ liệu khác lịch khai báo; gắn cờ, không coi là thiếu;
    - `after_hole` = trước nó mất trọn một bucket giao dịch. Bucket không có nến nào không tồn tại
      — nó là một hole.
  - Phải giữ output `c2_cisd_research` không đổi (hồi quy AGENTS §7.3). `resample.py` cũng hỗ trợ
    `ny_1700` để có dataset H4 cùng mốc cho phép thử tương đương.
- **[T1] Quy tắc chất lượng lan truyền (R3):**
  - Nến `degraded` không được nằm trong cửa sổ pivot (c−1..c+1) hay bộ ba FVG. Cửa sổ vắt qua hole
    cũng bị chặn.
  - Vì ITH/ITL chỉ dựng từ STH hợp lệ, mọi thứ phụ thuộc (ITH/ITL, thứ tự, dealing range, vùng,
    FVG) **tự không có** trên dữ liệu thiếu. Không cần cờ riêng cho từng sự kiện.
  - Mỗi nến `degraded` phát `HTF_BAR_DEGRADED` (ẩn).
  - Ngữ cảnh mang `blocked_windows_recent` để regime biết cấu trúc khung lớn đang thưa vì dữ liệu.
  - Survey: 2 (H1) / 2 (H4) cửa sổ pivot bị chặn trong 8 tháng (trên dataset lệch giờ là 31 / 45).
- **[T2] Mức theo kỳ — mốc thời gian chính xác (R5):**
  - **PDH/PDL, PWH/PWL:** biết tại `known_at` của kỳ; hiệu lực từ nến sau. Kỳ `degraded` (kể cả
    kỳ đầu dataset thiếu) **không** tạo mức.
  - **Giá mở ngày** = open của nến giao dịch **đầu tiên** của ngày giao dịch (thường 18:00 NY — lúc
    17:00 không có nến vì nghỉ). Biết tại close nến đó.
  - **Midnight open** = open của nến bắt đầu đúng 00:00 NY. Không có nến đó → `null`, **không**
    lấy giá thay thế.
- **Neo sự kiện khung lớn:**
  - `HTF_SWING_*`: `event_bar_index` = nến M15 chạm cực trị (`high_bar_index`/`low_bar_index` của
    bộ gộp).
  - `HTF_FVG_*`: `event_bar_index` = nến M15 đầu tiên của nến khung lớn ở giữa.
  - Mọi sự kiện khung lớn: `confirmed_at` = close của nến M15 tại `known_at`; `details` ghi
    `period_end`, `known_at`, `coverage`.
- **Thứ tự nhân quả:** [T] chạy **cuối** nến t. Sự kiện M15 tại t dùng ngữ cảnh chốt **≤ t−1**.
- **Khởi động:** mỗi khung `ready = false` tới khi đủ ATR và có trạng thái thứ tự. Survey: chưa có
  thứ tự 1.1% thời gian (H1), 4% (H4), 24% (D).

### 11.5. Đầu ra của ngữ cảnh khung lớn

`details.htf` trên mọi sự kiện M15 — ảnh chụp **gọn** tại lúc xác nhận, bất biến:

```json
"htf": {
  "alignment": "ny_1700",
  "H1": {"ready": true, "order": 1, "order_age_bars": 7, "protected": 2318.4,
         "protected_broken": false, "zone": "discount", "range_pos": 0.31,
         "liq_above": 2341.0, "liq_below": 2309.2, "age_ltf_bars": 2,
         "coverage_last": 1.0, "blocked_windows_recent": 0},
  "H4": {"...": "cùng các trường như H1"},
  "pd_bias": {"dir": -1, "tf": "H1", "age_ltf_bars": 5},
  "dol": {"side": 1, "target": 2341.0, "tier": "H1", "dist_atr": 4.2},
  "levels": {"pdh": 2339.1, "pdl": 2301.7, "pdh_taken": false, "pdl_taken": true,
             "day_open": 2312.0, "midnight_open": null}
}
```

- Khoảng cách tính bằng **ATR M15**.
- `age_ltf_bars` = số nến M15 kể từ lần chốt nến khung lớn gần nhất.
- Số trong ví dụ chỉ minh hoạ định dạng.
- **Không** có trường «bias tổng hợp» (B3).

Timeline thêm cột phẳng: `htf_H1_order`, `htf_H4_order`, `htf_H4_zone`, `htf_H4_range_pos`,
`pd_bias`, `dol_side`, `pdh_taken`, `pdl_taken`, `htf_H4_age`.

**Giao diện:**
- Lớp phủ H4 trên chart M15: ITH/ITL H4, dealing range, EQ, FVG H4 đang mở, PDH/PDL — nét khác M15.
- Nến H4 đang hình thành vẽ mờ, nhãn «đang hình thành — chưa dùng».
- Khung «Thuật toán đang làm gì» thêm một dòng mỗi thành phần, ví dụ: «Thứ tự H4: tăng (7 nến), giá
  ở discount 31%. pd_bias: giảm (FVG H1 bị disrespect 5 nến trước). DOL: lên, đích ITH H1 2341.0
  (cách 4.2 ATR).»

### 11.6. Thiết kế (A): công cụ hồ sơ khung

- Hiện tại: `research/ict_survey.py` (bản mẫu, §2).
- Sau giai đoạn 3: thay bằng công cụ chạy **chính** các thành phần của `ict_structure`, không viết
  lại định nghĩa.
- Bổ sung so với survey-v2:
  - **null ghép cặp** (thời điểm ngẫu nhiên cùng killzone và cùng nhóm ATR, AGENTS §6) cho §11.2.
    Cho **chất lượng nhận diện so với nhãn** đã có ở trang Đánh giá (`matched_hour_atr_v1`: cùng giờ
    New York × nhóm ATR, `danh_gia_thuat_toan.md` §1.3); null cho câu hỏi §11.2 (shift có đi cùng
    ngữ cảnh khung lớn không) vẫn làm trong công cụ này;
  - sai số chuẩn ghi cạnh mọi tỷ lệ.
- Không có win rate/P&L (AGENTS §2.4).

### 11.7. Kiểm thử bổ sung

- **Bộ gộp `ny_1700`:**
  - biên 17:00 NY trước và sau đổi giờ (10/03/2024, 03/11/2024);
  - giờ nghỉ nằm trong nến đầu ngày;
  - nến mở tuần Chủ nhật; tuần kết thúc Thứ Sáu 17:00;
  - ngày lễ đóng sớm theo lịch khai báo → **không** `degraded`; chốt muộn → `period_end` ≠
    `known_at`;
  - `utc_epoch` không đổi output (`c2_cisd_research` hồi quy khớp 100%).
- **Chất lượng:**
  - nến `degraded` trong cửa sổ pivot/FVG → không có ITH/FVG;
  - hole chặn cửa sổ;
  - kỳ đầu dataset thiếu → không có PDH/PWH;
  - midnight open thiếu → `null`.
- **Không nhìn trước:** sửa OHLC các nến M15 **sau** t trong cùng nến H4 đang hình thành →
  `details.htf` và timeline tại ≤ t không đổi.
- **Tương đương:** ngăn xếp H4 trong run M15 cho ITH/ITL/FVG H4 trùng (giá, nến H4) với cùng thành
  phần chạy trực tiếp trên dataset H4 gộp `ny_1700`; chỉ `confirmed_at` khác.
- **Thứ tự:** sự kiện M15 ở đúng nến chốt nến H4 dùng ngữ cảnh **trước** lần chốt đó.
