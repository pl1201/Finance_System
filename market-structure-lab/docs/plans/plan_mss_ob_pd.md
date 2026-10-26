# Plan MSS thay shift + order block là PD array (`ict_structure` 0.10.0)

Ngày 26/10/2026. Người dùng yêu cầu: «Ở đây dùng Market structure shift thay thế BOS/CHoCH», và «Order block / OTE: tích hợp thêm
vào ict_structure». Quyết định B1 (02/10/2026: không BOS/CHoCH/MSS) đổi thành: **không BOS/CHoCH; đổi hướng = MSS**.

## 1. Lựa chọn của người dùng (26/10/2026)

| Câu hỏi | Chọn |
|---|---|
| MSS phá mức nào | **STL / STH hình thành trước cú chạy** vào vùng bị quét (ICT 2022 Ep 6). Cờ `significant` khi phá luôn ITL / ITH cấp 2 |
| Điều kiện phá | **Close** vượt mức + **đoạn displacement** 1–5 nến có tổng biên độ ≥ k·ATR. Chờ tới khi cực trị cú quét bị vượt thì huỷ. FVG là cờ chất lượng, không bắt buộc |
| Quan hệ với shift | **MSS thay shift**: order flow lật ở MSS, OB / OTE / DOL neo vào MSS. Shift giữ thành tham số đối chiếu (`doi_huong = shift`). Đo phần giao / lệch trên đoạn dev trước khi chốt mặc định |
| OB / OTE | Neo vào MSS; **OB thành PD array trong lõi** (chạm → giữ / hỏng → breaker; vào `pd_bias`; OB hỏng làm order flow «bị vô hiệu»); bật sẵn trên chart. Không đưa OB vào xác suất chạm |

Nguồn: [`reports/Định nghĩa cấu trúc thị trường.md`](../../../reports/Định%20nghĩa%20cấu%20trúc%20thị%20trường.md) (Mentorship 2022 Ep 6
≈0:18:11: «trades above an old high … and then it breaks down once that low is broken»; ≈0:18:58: displacement «energetic … preferably
close below»; ≈0:20:50: displacement là một đoạn giá; ≈0:21:30: FVG là điều kiện vào lệnh), [`reports/Thuật toán ICT của LuxAlgo.md`](../../../reports/Thuật%20toán%20ICT%20của%20LuxAlgo.md)
hạng 1 (MSS ICT-2022: mức = swing chưa lấy gần nhất, displacement nhiều nến; Displacement LuxAlgo chân 1–5 nến), hạng 3 (breaker từ
`OB_FAIL`), §«Những gì lab còn thiếu» (order flow intact / invalidated theo OB).

## 2. MSS — định nghĩa vận hành

Mô tả cho **MSS giảm** (sau quét BSL); MSS tăng đối xứng.

**Ứng viên** (bước 3 của nến r, khi phát `LIQ_SWEEP_BSL`): mỗi vùng bị quét q cho một ứng viên với

* mức bị quét L = q.level, nến lấy b = q.taken_index, cực trị cú quét X = max(high[b..r]);
* **mốc phá** = STL (pivot cấp 1) **gần nhất có nến cực trị < b**, trong số STL đã xác nhận trước nến r. Không có → không ứng viên
  (đếm `khong_co_moc`). Không kiểm STL đó đã bị close phá trước b hay chưa (giá đã đi từ STL lên trên L nên gần như không xảy ra);
* **mốc «significant»** = ITL (cấp 2) gần nhất có nến cực trị < b, cùng điều kiện (có thể không có).

**Xét ở bước 6 của mỗi nến t ≥ r** (chỗ của shift):

1. t > r và có khoảng trống trước t → huỷ (`huy_khoang_trong`); t > r và high[t] > X → huỷ (`huy_vuot_cuc_tri`). Bằng X không huỷ.
2. close[t] < STL (nghiêm ngặt; bằng không tính) → **quyết định một lần**:
   * đoạn displacement = n nến cuối tới t, n = `mss_chan_nen` (mặc định 5), không vắt qua khoảng trống; đỉnh đoạn H = max high của
     đoạn, nến đầu đoạn s = nến có H (nến muộn nhất nếu bằng nhau);
   * H − close[t] ≥ `mss_chan_atr` × ATR[t−1] → **MSS giảm tại t**; không đủ (hoặc chưa có ATR) → ứng viên kết thúc «phá yếu»
     (`pha_yeu`, không phát sự kiện — ICT «lethargic … not all that convincing»).
3. Còn lại: chờ tiếp, **không giới hạn thời gian** (ICT không đặt; điều 1 hoặc 2 sẽ đến).

**Gom:** nhiều ứng viên cùng chiều thành MSS ở cùng nến → **một** `MSS_DOWN` (vùng chính = tầng cao nhất, như shift). Ứng viên cùng chiều
còn chờ bị gom vào MSS vừa phát (`gop_vao_mss`) — một cú đảo, một MSS.

**Sự kiện** `MSS_UP` / `MSS_DOWN`: nến sự kiện = nến xác nhận = t, giá = mốc phá (STL). `details`: mốc phá (giá, nến, id STL),
`significant` (close[t] < ITL) + ITL, đoạn displacement (nến đầu s, H, biên độ / ATR, số nến), vùng bị quét, cực trị cú quét, nến sweep,
số nến từ sweep, `fvg_trong_chan` (FVG cùng chiều đã biết tại t có nến giữa trong [s, t − 1]), `group_id` = sweep.
`MSS_FVG_*` ở t + 1 khi FVG cùng chiều có nến giữa = t (như `SHIFT_FVG`).

**Khác shift:** shift cần một nến displacement đóng cửa vượt lại **mức bị quét** trong 3 nến; MSS cần close phá **STL trước cú chạy**
bằng một **đoạn** mạnh, không hạn cửa sổ. Hai tập giao nhau nhưng không lồng nhau.

## 3. Nối MSS vào phần còn lại (`doi_huong = mss`, mặc định)

* **Order flow:** đầu vào = `LIQ_RUN_*` + `MSS_*` (MSS lật thẳng như shift; mã lý do `mss_tang` / `mss_giam`).
* **OB:** neo vào MSS — tìm chuỗi nến ngược màu cuối trong [s − `ob_lui`, min(s, t − 1)] (nến đầu đoạn displacement trở về trước, không
  gồm nến phá t), không tìm trong đoạn. **OTE:** gốc = X, đầu nhịp từ nến MSS (như shift). **DOL:** đặt lại sau mỗi MSS.
* `doi_huong = shift`: mọi thứ như 0.9.3 (`SHIFT_*`, order flow theo shift…), không phát `MSS_*`.

## 4. Order block là PD array (`ob_pd_array = true`, mặc định)

* **Vòng đời** (thay «chỉ lần chạm đầu»): OB đã xác nhận, chưa chạm → chạm lần đầu (`OB_TAP_*`, hoặc `OB_FAIL_*` nếu close vượt mép
  xa ngay nến đó) → từ nến chạm trở đi, **kết quả đầu tiên**: **giữ** `OB_RESPECT_*` / **hỏng** `OB_FAIL_*`, cùng luật phản ứng với FVG
  khung lớn (`pd_respect_mode`, mặc định chặt: giữ = close rời mép gần ≥ `respect_away_atr` × ATR; hỏng = close vượt mép xa; chế độ
  `ce` = vượt mean threshold). Chưa chạm quá `ob_han` nến → hết hạn; đã chạm mà chưa có kết quả trong `ob_han` nến tính từ nến chạm →
  hết hạn. MSS ngược chiều → OB chiều cũ (chưa chạm hoặc đã chạm chưa kết quả) hết hạn.
* **Breaker:** OB hỏng → `BREAKER_*` ngược chiều trên đúng vùng đó (OB tăng hỏng → breaker giảm), có hiệu lực từ nến sau; cùng vòng đời
  (sự kiện `OB_*` với `details.kieu = breaker`). Breaker hỏng không sinh breaker mới.
* **pd_bias:** kết quả giữ / hỏng của OB và breaker vào `pd_bias` cùng FVG H1 / H4, cùng bảng chiều hàm ý; khung nguồn ghi `OB`
  (hạng thấp nhất). Nhiều kết quả cùng nến: cùng chiều → chiều đó, ngược → 0 (luật sẵn có).
* **Order flow bị vô hiệu:** OB của MSS gần nhất cùng chiều order flow hỏng ở nến t mà t không có run / MSS → order flow = chưa rõ, lý do
  `ob_hong` (ICT 2022 «order flow invalidated»).
* `ob_pd_array = false`: vòng đời 0.5.0 (chỉ lần chạm đầu, không breaker, không vào `pd_bias`).

`doi_huong = shift` + `ob_pd_array = false` phải cho output **khớp tuyệt đối** 0.9.3 (trừ con dấu phiên bản) — so bằng mốc hồi quy trên
5 cấu hình dev.

## 5. Tham số mới (do lab chọn, ghi rõ trong đặc tả)

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `doi_huong` | `mss` | sự kiện đổi hướng: `mss` / `shift` (đối chiếu 0.9.3) |
| `mss_chan_nen` | 5 | đoạn displacement tối đa (nến) — LuxAlgo Displacement chân 1–5 nến |
| `mss_chan_atr` | 2.0 | đoạn displacement ≥ k × ATR[t−1] |
| `ob_pd_array` | true | OB là PD array (giữ / hỏng → breaker, `pd_bias`, order flow vô hiệu) |

## 6. Khảo sát trên đoạn dev (khai trước khi chạy)

Đoạn 2018-01-01 → 2024-08-31, XAUUSD M15 và EURUSD M15; không dùng đoạn kiểm tra. Chỉ số **mô tả**, không có kết quả «đúng / sai».

* Tần suất MSS / ngày và shift / ngày; tỷ lệ sweep → MSS; độ trễ sweep → MSS (trung vị, P90 số nến); tỷ lệ `significant`, có FVG trong
  đoạn, «phá yếu», «vượt cực trị».
* Phần giao: MSS và shift cùng chiều cách nhau ≤ 3 nến (tỷ lệ mỗi bên khớp bên kia).
* Độ nhạy: `mss_chan_atr` ∈ {1.0, 1.5, 2.0, 2.5, 3.0}, `mss_chan_nen` ∈ {3, 5, 8}.
* **Tiêu chí giữ mặc định (khai trước):** giữ k = 2.0, n = 5 nếu MSS / ngày nằm trong [0,5×, 2×] shift / ngày trên cả hai mã; nếu không,
  chọn giá trị k gần 2.0 nhất trong lưới thoả điều kiện đó. Không chỉnh theo bất kỳ kết cục giá nào.
* OB: số OB / ngày theo MSS so với theo shift; tỷ lệ giữ / hỏng / hết hạn; số breaker; tần suất order flow «vô hiệu».

## 7. Đã làm (26/10/2026, lõi 0.10.0)

* Lõi: `core/components/mss.py`; order flow nhận MSS + «OB hỏng → chưa rõ»; `OrderBlockTracker` vòng đời PD array + breaker, cửa
  sổ MSS; `pd_array` nhận kết quả OB; `algorithm.py` nối bước 3 / 3b / 6 / 6b / 6c / 7 / 10; mục tiêu chấm `ict_mss`.
* **Hồi quy:** `doi_huong = shift` + `ob_pd_array = false` khớp tuyệt đối 0.9.3 trên 5 cấu hình dev (sự kiện, timeline, `pending_state`,
  `run_stats`; chỉ chữ giải thích khác).
* **Khảo sát** (đặc tả §8.3, [`khao_sat/mss_dev.json`](../research/khao_sat/mss_dev.json), lịch phiên theo mã): MSS 1,10 / 1,17 mỗi
  ngày (XAUUSD / EURUSD M15) = 1,26 / 1,23 × shift → **giữ k = 2,0, n = 5** theo tiêu chí khai trước. MSS và shift chỉ giao ~38–48%.
  (Lần chạy đầu quên truyền lịch phiên — số / ngày thấp hơn, tỷ lệ như nhau; đã chạy lại.)
* Test: `tests/algorithms/test_ict_mss.py` (tính tay MSS / order flow / OB PD array / breaker / `pd_bias`, bất biến + nhân quả trên dữ
  liệu ngẫu nhiên); node: hình vẽ MSS, OB đã chạm / giữ / hỏng, breaker.
* Giao diện: «MSS ↓/↑» tại mức bị phá + FVG nến phá; OB «· chạm / · giữ / · hỏng», «Breaker»; OB / OTE bật sẵn; chữ order flow / DOL /
  «Đang theo dõi» theo MSS.
* Làm gọn (simplify): một luật phản ứng chung `pd_array.reaction` cho FVG khung lớn và OB; `MssTracker` gọn (mốc từ swing, đoạn
  displacement); thống kê MSS đọc từ chính sự kiện; mỗi lần chạy chỉ ghi cột / khối của một sự kiện đổi hướng; khoá DOL theo chế độ
  (`mss` / `shift`); `ORDER_BLOCK_*` mang `kieu` ở chế độ PD array; hằng `LEGACY_0_9` để script nghiên cứu cũ tái lập 0.9.3.
* Sửa theo code-review: cửa sổ OB không gồm nến phá khi đoạn chỉ 1 nến; «vô hiệu» order flow chỉ khi OB neo sự kiện đổi hướng; ghi chú
  order flow đúng chế độ (shift + PD array); marker + giá nhãn mặc định cho `MSS_*`; JSON khảo sát ghi phiên bản thuật toán.
* Còn để sau: biến thể MSS phá bằng wick (ICT Ep 3), mốc ITL làm biến thể «significant-only», chấm MSS trên nhãn tay (D8).
