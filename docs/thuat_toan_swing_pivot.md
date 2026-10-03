# Đặc tả thuật toán Swing Pivot + HH/HL/LH/LL + BOS / CHoCH

**Mã thuật toán:** `swing_pivot`
**Phiên bản:** `1.1.0` (1.0.0 chỉ có BOS theo mức mới nhất, không phân loại CHoCH / BOS nội bộ)
**File:** [`core/algorithms/swing_pivot.py`](../core/algorithms/swing_pivot.py)

Tài liệu này là đặc tả chuẩn. Nếu code và tài liệu khác nhau thì đó là lỗi cần sửa.
Mọi thay đổi quy tắc phải tăng `version` để kết quả cũ vẫn truy vết được.

---

## 1. Đầu vào

Thuật toán nhận **từng nến đã đóng**, theo thứ tự thời gian tăng dần, qua
`on_bar(bar)`. Không có API nào cho phép nó đọc nến phía sau — tính nhân quả
là thuộc tính cấu trúc của code, không phải quy ước phải ghi nhớ.

Mỗi nến mang ba mốc thời gian:

| Trường | Ý nghĩa |
|---|---|
| `bar_time` | Timestamp của nến theo quy ước dataset (UTC) |
| `close_time` | Thời điểm nến ĐÓNG. Quy ước `open`: `bar_time + timeframe`. Quy ước `close`: `= bar_time` |
| — | Thuật toán chỉ dùng `close_time` làm mốc "thông tin khả dụng" |

## 2. Tham số

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `left` | 3 | Số nến bên trái nến pivot |
| `right` | 3 | Số nến bên phải nến pivot — cũng chính là độ trễ xác nhận |
| `label_eq_tolerance` | 0.0 | Dung sai coi hai swing cùng phía là "bằng giá" |
| `bos_buffer` | 0.0 | Biên giá phải vượt thêm mới tính là phá vỡ |
| `enable_bos` | true | Bật/tắt phát hiện phá vỡ (BOS và CHoCH) |
| `enable_choch` | true | Bật phân loại CHoCH và BOS nội bộ. Tắt → mọi phá vỡ đều là `BOS_UP`/`BOS_DOWN` như v1.0.0 |

**Warm-up:** `left + right + 1` nến. Trước mốc này không thể xác nhận pivot nào,
và trạng thái dữ liệu được báo là `WARMUP_INSUFFICIENT`.

## 3. Quy tắc pivot

Nến tại chỉ số `c` là **swing high** khi và chỉ khi:

```
high[c] > high[j]   với mọi j ∈ [c-left, c-1] ∪ [c+1, c+right]
```

Swing low đối xứng: `low[c] < low[j]` với cùng cửa sổ.

* So sánh là **lớn hơn / nhỏ hơn tuyệt đối**.
* **Bằng nhau không được nhận là pivot** ở phiên bản này. Nếu có bất kỳ nến nào
  trong cửa sổ có `high` bằng đúng `high[c]` thì `c` không phải swing high.
  Quy ước này được chọn để đơn giản và tất định; một phiên bản sau có thể thêm
  luật xử lý đỉnh bằng nhau, khi đó phải tăng `version`.
* Một nến có thể vừa là swing high vừa là swing low (hiếm, nhưng hợp lệ).

**Thời điểm xác nhận.** Pivot tại `c` chỉ được xác nhận khi nến bên phải **cuối
cùng** đã đóng, tức tại nến `i = c + right`:

```
event_bar_index       = c
event_time            = bar_time[c]
event_close_time      = close_time[c]
confirmed_bar_index   = c + right
confirmed_at          = close_time[c + right]
confirmation_lag_bars = right
```

Ví dụ theo tài liệu nhóm: đỉnh nằm ở nến 100, `right = 3` ⟹ `event_time` thuộc
nến 100 còn `confirmed_at` thuộc nến 103. Chart có thể vẽ đỉnh ở nến 100, nhưng
**không được giả định hệ thống đã biết đỉnh đó tại nến 100**.

## 4. Nhãn HH / LH / EQH và HL / LL / EQL

Khi một swing high được xác nhận, so sánh với swing high **đã xác nhận liền
trước** (`prev`), với dung sai `tol = label_eq_tolerance`:

| Điều kiện | Nhãn | `reason_code` |
|---|---|---|
| `price > prev + tol` | `HH` | `SEQ_HIGHER_HIGH` |
| `price < prev - tol` | `LH` | `SEQ_LOWER_HIGH` |
| còn lại | `EQH` | `SEQ_EQUAL_HIGH` |

Swing low đối xứng: `HL` / `LL` / `EQL`.

`EQH`/`EQL` là **nhãn riêng**, không bị ép thành HH/HL/LH/LL. Swing đầu tiên của
mỗi phía không có mốc so sánh nên không sinh nhãn. Nhãn dùng cùng
`event_time`/`confirmed_at` với pivot sinh ra nó, và trỏ tới pivot trước qua
`reference_event_id`.

Phiên bản này so **từng đỉnh cấp 1**. Muốn lọc đỉnh cấp 2 rồi mới so HH/LH
(thí nghiệm cấu trúc, không gồm BOS) dùng thuật toán riêng
[`swing_hierarchy`](thuat_toan_swing_cap_2.md) — không đổi quy tắc `swing_pivot`.

## 5. Quy tắc BOS

**Mức đang hoạt động** (`active level`) của một phía là swing đã xác nhận, **chưa
bị phá**, có chỉ số xác nhận lớn nhất.

* **BOS lên** tại nến `i`: `close[i] > active_high.price + bos_buffer`
* **BOS xuống** tại nến `i`: `close[i] < active_low.price - bos_buffer`

Phá vỡ tính theo **giá đóng cửa**, không theo bóng nến (wick).

**Chống phát lặp.** Khi một BOS lên xảy ra tại giá `p = close[i]`:

1. Phát **đúng một** sự kiện `BOS_UP`, `reference_event_id` trỏ tới mức mới nhất
   bị phá; `price` của sự kiện là **giá của mức bị phá**, không phải giá đóng cửa
   (giá đóng cửa nằm trong `details.gia_dong_cua`).
2. Đánh dấu **đã phá** cho mọi mức swing high chưa bị phá thoả `p > level + buffer`.

Nhờ đó: một mức không bao giờ phát tín hiệu lần thứ hai, và một cú phá mạnh
vượt nhiều mức cũ không tạo ra chuỗi BOS lặp ở các nến sau.

BOS dùng `close` của chính nến đang xét nên:

```
event_bar_index = confirmed_bar_index = i
confirmation_lag_bars = 0
```

Phát hiện *có phá vỡ hay không* giữ nguyên v1.0.0 (chỉ so với mức **mới nhất
chưa bị phá**). Phiên bản 1.1.0 **phân loại** phá vỡ đó thành BOS chính, BOS
nội bộ hoặc CHoCH — xem mục 5.1–5.3.

## 5.1. Bias cấu trúc (hướng đang được công nhận)

`bias ∈ {none, bullish, bearish}`, bắt đầu bằng `none`.

Cập nhật **sau khi gắn nhãn** HH/LH/EQH hoặc HL/LL/EQL, khi **cả hai phía**
đã có nhãn mới nhất:

| Nhãn đỉnh mới nhất | Nhãn đáy mới nhất | Bias |
|---|---|---|
| `HH` | `HL` | `bullish` |
| `LH` | `LL` | `bearish` |
| `HH` | `LL` | `none` (cặp lẫn: mở rộng hai phía) |
| `LH` | `HL` | **không đổi** — đỉnh hồi / đáy hồi, không xoá bias |
| có `EQH` hoặc `EQL` | — | **không đổi** bias |

Khi chỉ mới có nhãn một phía, bias giữ nguyên (kể cả bias do CHoCH vừa gán).

CHoCH **gán bias ngay** và **xoá cặp nhãn** để cấu trúc mới được dựng lại từ
đầu: `CHOCH_UP` → `bullish`, `CHOCH_DOWN` → `bearish`. EQH/EQL không tham gia
bảng trên.

Khi `bias = none`, mọi phá vỡ được gắn `BOS_UP` / `BOS_DOWN` như v1.0.0 — nhờ
đó các chuỗi chưa hoàn thành HH+HL (ví dụ chỉ phá đỉnh trước khi có đáy được
gắn HL) không đổi loại sự kiện so với bản cũ.

## 5.2. Mức chính và mức nội bộ

* **Mức chính khi `bias = bullish`:** swing của nhãn `HH` mới nhất (phía high)
  và swing của nhãn `HL` mới nhất (phía low), nếu mức đó **chưa bị phá**.
* **Mức chính khi `bias = bearish`:** swing `LH` mới nhất và swing `LL` mới
  nhất, nếu chưa bị phá.
* **Mức đang hoạt động (active)** — giữ v1.0.0: mức chưa bị phá có
  `confirmed_index` lớn nhất.
* **Mức nội bộ:** mức active **khác** mức chính của cùng phía (đỉnh/đáy hồi
  bên trong cấu trúc đang có). `EQH`/`EQL` không cập nhật mức chính.

Không dùng "giá cao nhất/thấp nhất từ đầu chuỗi" làm mức chính: đáy đầu tiên
thấp hơn HL sau đó không phải mốc CHoCH. CHoCH tăng/giảm phá **HL hoặc LH
đang định nghĩa bias**.

Phá vỡ vẫn chỉ được **phát hiện** khi `close` vượt **mức active**. Nếu cùng
nến cũng vượt mức chính, sự kiện được phân loại theo mức chính (mục 5.3).

## 5.3. CHoCH, BOS chính, BOS nội bộ

Gọi `broke_extreme` khi `close` cũng vượt mức chính cùng phía (cùng điều kiện
buffer). `enable_choch = false` thì luôn phát `BOS_UP` / `BOS_DOWN`.

**Phá lên** (`close > active_high + buffer`), `enable_choch = true`:

| Bias | Điều kiện | Sự kiện | Ý nghĩa |
|---|---|---|---|
| `none` | luôn | `BOS_UP` | như v1.0.0 |
| `bullish` | `broke_extreme` hoặc active ≡ chính | `BOS_UP` | BOS **chính** — tiếp diễn tăng |
| `bullish` | active khác chính, chưa vượt chính | `BOS_INTERNAL_UP` | BOS **nội bộ** |
| `bearish` | `broke_extreme` hoặc active ≡ chính | `CHOCH_UP` | đổi hướng tăng |
| `bearish` | active khác chính, chưa vượt chính | `BOS_INTERNAL_UP` | phá đỉnh hồi, chưa đổi cấu trúc chính |

**Phá xuống** đối xứng: `BOS_DOWN` / `BOS_INTERNAL_DOWN` / `CHOCH_DOWN`.

Một nến chỉ phát **đúng một** sự kiện phá vỡ mỗi phía. `reason_code` tương ứng:
`BOS_CLOSE_ABOVE_SWING_HIGH`, `BOS_INTERNAL_CLOSE_ABOVE`,
`CHOCH_CLOSE_ABOVE_SWING_HIGH` (và bộ ba phía xuống). `details` ghi
`phan_loai` (`chinh` | `noi_bo` | `choch`), `bias_truoc`, `bias_sau`,
`muc_chinh`, `muc_active`.

## 5.4. CHoCH và BOS trên cùng một nến

Với phá vỡ theo **close**, một giá đóng cửa không thể vừa lớn hơn đỉnh vừa nhỏ
hơn đáy khi đỉnh > đáy. Do đó cặp CHoCH ngược chiều với BOS ngược chiều
**không xảy ra** trên cấu trúc hợp lệ.

Trường hợp thực sự cần quy tắc ưu tiên: **cùng một phía**, close xuyên cả mức
nội bộ lẫn mức chính. Khi đó:

1. Chỉ phát **một** sự kiện, phân loại theo mức chính (CHoCH nếu ngược bias,
   BOS chính nếu cùng bias).
2. **Không** phát thêm BOS nội bộ trên cùng nến.
3. Vẫn đánh dấu đã phá mọi mức bị `close` vượt qua (chống phát lặp như v1.0.0).
4. CHoCH gán bias mới **sau** khi phân loại xong nến đó — nến đang xét dùng
   bias **trước** nến, không dùng bias vừa lật để phát sự kiện thứ hai.

Thứ tự bước D trên một nến: (1) phân loại phá lên theo bias hiện tại, (2) phân
loại phá xuống theo **cùng** bias đó (snapshot đầu bước D), (3) đánh dấu mức
đã phá, (4) nếu có CHoCH thì cập nhật bias.

## 6. Thứ tự xử lý trong cùng một nến

```
Với mỗi nến i đã đóng:
  A. Xác nhận pivot tại c = i - right (nếu đủ điều kiện)
  B. Sinh nhãn HH/LH/EQH hoặc HL/LL/EQL cho pivot vừa xác nhận
  C. Đăng ký mức giá của pivot vào danh sách mức đang hoạt động
  D. Kiểm tra BOS bằng close[i] trên các mức đang hoạt động
```

**Thứ tự A→D và D→A cho kết quả giống nhau.** Chứng minh: nếu pivot high tại `c`
vừa được xác nhận tại nến `i = c + right` thì theo định nghĩa `high[c] > high[i]`;
mà `close[i] ≤ high[i]`, nên `close[i] < high[c]`. Một nến vừa xác nhận swing high
không bao giờ đồng thời phá vỡ chính swing high đó. Lập luận đối xứng cho swing
low. Chọn A→D để mức mới sẵn sàng cho các nến tiếp theo.

## 7. Từ điển sự kiện

| `structure_type` | Vị trí `event_bar_index` | Độ trễ | Ghi chú |
|---|---|---|---|
| `SWING_HIGH` | nến pivot | `right` | |
| `SWING_LOW` | nến pivot | `right` | |
| `HH`, `LH`, `EQH` | nến pivot | `right` | trỏ tới `SWING_HIGH` trước |
| `HL`, `LL`, `EQL` | nến pivot | `right` | trỏ tới `SWING_LOW` trước |
| `BOS_UP` | nến phá vỡ | 0 | BOS chính lên, hoặc BOS v1.0 khi `bias=none` |
| `BOS_DOWN` | nến phá vỡ | 0 | BOS chính xuống, hoặc BOS v1.0 khi `bias=none` |
| `BOS_INTERNAL_UP` | nến phá vỡ | 0 | phá đỉnh nội bộ, chưa vượt mức chính |
| `BOS_INTERNAL_DOWN` | nến phá vỡ | 0 | phá đáy nội bộ, chưa thủng mức chính |
| `CHOCH_UP` | nến phá vỡ | 0 | phá mức chính **ngược** bias giảm → bias = bullish |
| `CHOCH_DOWN` | nến phá vỡ | 0 | phá mức chính **ngược** bias tăng → bias = bearish |

Mã lý do: `PIVOT_HIGH_STRICT`, `PIVOT_LOW_STRICT`, `SEQ_HIGHER_HIGH`,
`SEQ_LOWER_HIGH`, `SEQ_EQUAL_HIGH`, `SEQ_HIGHER_LOW`, `SEQ_LOWER_LOW`,
`SEQ_EQUAL_LOW`, `BOS_CLOSE_ABOVE_SWING_HIGH`, `BOS_CLOSE_BELOW_SWING_LOW`,
`BOS_INTERNAL_CLOSE_ABOVE`, `BOS_INTERNAL_CLOSE_BELOW`,
`CHOCH_CLOSE_ABOVE_SWING_HIGH`, `CHOCH_CLOSE_BELOW_SWING_LOW`.
Mỗi mã có một câu giải thích tiếng Việt trong `core/types.py`, dùng cho tooltip.

**`event_id`** có dạng `{structure_type}@{event_bar_index}>{confirmed_bar_index}`.
Định danh này tất định: chạy lại cùng dữ liệu và tham số cho đúng bộ `event_id`.

## 8. Chuỗi trạng thái để vẽ chart

Sau mỗi nến, `timeline_point()` trả về mức swing high/low **đang hoạt động** tại
nến đó. Đường mức trên chart được vẽ từ chuỗi này, nên nó cũng chỉ chứa thông
tin đã khả dụng tại từng thời điểm — overlay không "biết trước" mức sẽ hình thành.

## 9. Giới hạn đã biết của phiên bản 1.1.0

* Nến bằng giá trong cửa sổ làm mất pivot. Trong thị trường có nhiều mức giá lặp
  (ví dụ timeframe rất nhỏ, hoặc dữ liệu làm tròn thô) số pivot sẽ giảm.
* Phá vỡ theo `close`, không theo wick.
* Mức đang hoạt động (điều kiện *có* phá) chỉ xét mức **mới nhất chưa bị phá**.
  Nếu giá đóng cửa vượt một mức cũ thấp hơn nhưng chưa vượt mức mới nhất thì
  không phát sự kiện — giống v1.0.0.
* "Mức chính" khi đã có bias = swing HH+HL (tăng) hoặc LH+LL (giảm) mới nhất
  chưa bị phá — không phải cực trị giá từ đầu chuỗi.
* Bias `none` khi chưa có cặp HH+HL hoặc LH+LL: không có CHoCH.
* Không dùng volume, không dùng dữ liệu đa khung thời gian.
* Precision/recall chỉ có khi người dùng gán nhãn tham chiếu (công cụ riêng);
  thuật toán này tự nó không báo accuracy.

### 9b. Tối ưu hiệu năng 02/10/2026 — output không đổi, giữ phiên bản 1.1.0

**Vấn đề:** bản cũ quét tuyến tính toàn bộ danh sách mức, gồm cả mức đã bị phá, ở ba chỗ:
- tra mức chính theo id;
- tìm mức đang hoạt động;
- đánh dấu mức bị phá sau mỗi lần phá vỡ.

Danh sách mức lớn dần theo thời gian nên chi phí tăng theo **bình phương** số nến. M15 8 năm (189 000
nến) không chạy xong trong 60 s.

**Cách sửa:** thay bằng chỉ mục.
- Dict theo `event_id` để tra mức chính.
- Dict các mức **chưa phá** theo thứ tự xác nhận; mức đang hoạt động = phần tử cuối.
- Danh sách mức chưa phá xếp theo giá. Điều kiện phá `close > giá + bos_buffer` (đỉnh) /
  `close < giá − bos_buffer` (đáy) đơn điệu theo giá, kể cả khi làm tròn số thực, nên tập mức bị phá
  luôn là một đoạn đầu/cuối của danh sách — đúng tập mà vòng quét cũ đánh dấu.

**Kiểm chứng:**
- So bản cũ/mới trên 13 trường hợp: dữ liệu thật XAUUSD/EURUSD M15/H1/H4/D1, dữ liệu mô phỏng, các
  bộ tham số `left/right`, `bos_buffer`, `enable_choch`, `label_eq_tolerance`. Sự kiện, timeline và
  `pending_state` giống hệt; chỉ khác hai trường đo tốc độ trong `stats`.
- Hồi quy 15/15 run `swing_pivot` đã lưu khớp từng sự kiện (AGENTS §7.3).

**Tốc độ:** M15 8 năm ~5 s, M1 một năm ~10 s, H1 8 năm 1 s (trước: 5,5 s).

## 10. Test bao phủ đặc tả này

[`tests/test_swing_pivot.py`](../tests/test_swing_pivot.py),
[`tests/test_choch_bos.py`](../tests/test_choch_bos.py) và
[`tests/test_replay_causality.py`](../tests/test_replay_causality.py):

* Pivot trên chuỗi nhỏ có kết quả tính tay (mục 3).
* Nến bằng giá không tạo pivot; hai đỉnh bằng nhau nhận `EQH` (mục 3, 4).
* Độ trễ xác nhận đúng bằng `right` với nhiều giá trị tham số (mục 3).
* `confirmed_at` bằng `close_time` của nến xác nhận, khác `event_time` (mục 3).
* BOS phát đúng một lần mỗi mức, dùng close chứ không dùng wick, biên phá vỡ
  hoạt động, BOS xuống đối xứng (mục 5).
* CHoCH, BOS nội bộ, BOS chính trên chuỗi nhỏ tính tay; cùng nến xuyên nội bộ
  lẫn chính chỉ phát CHoCH; `enable_choch=false` trở về nhãn v1.0.0 (mục 5.1–5.4).
* Thêm hoặc **sửa** dữ liệu sau `T` không đổi sự kiện đã xác nhận tại `T` (mục 1).
* Replay tiến/lùi/seek/reset cho kết quả nhất quán và bằng chạy prefix (mục 1).
