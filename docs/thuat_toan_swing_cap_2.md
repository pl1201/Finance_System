# Đặc tả thuật toán Swing phân cấp (cấp 1 + cấp 2)

**Mã thuật toán:** `swing_hierarchy`
**Phiên bản:** `1.0.0`
**File:** [`core/algorithms/swing_hierarchy.py`](../core/algorithms/swing_hierarchy.py)

Đây là **đặc tả phân cấp swing để thử nghiệm**, chưa phải toàn bộ phương pháp ICT.
Thuật toán `swing_pivot` **v1.1.0 không đổi**: HH/LH ở đó vẫn so từng đỉnh cấp 1.
Phương pháp này chỉ đổi **đỉnh nào được đưa vào phép so**. Phép so HH/LH (kèm `tol`) giữ nguyên.

**Không** gồm sự kiện phá vỡ. `Close_t > ReferenceHigh + ε` là BOS, triển khai riêng
nếu cần — không trộn với xác nhận đỉnh HH cấp 2.

Tài liệu này là đặc tả chuẩn. Nếu code và tài liệu khác nhau thì đó là lỗi cần sửa.
Mọi thay đổi quy tắc phải tăng `version`.

---

## 1. Đầu vào

Thuật toán nhận **từng nến đã đóng**, theo thứ tự thời gian tăng dần, qua
`on_bar(bar)`. Không đọc nến phía sau.

## 2. Tham số

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `left` | 3 | Số nến bên trái nến pivot cấp 1 |
| `right` | 3 | Số nến bên phải nến pivot cấp 1 — độ trễ xác nhận cấp 1 |
| `label_eq_tolerance` | 0.0 | Dung sai phân loại HH/LH/EQH giữa **hai đỉnh cấp 2**. Chỉ dùng khi gắn nhãn, không dùng khi lọc cấp 2. |
| `emit_level1` | true | Phát thêm sự kiện `SWING_HIGH` / `SWING_LOW` cấp 1 để đối chiếu trên chart. **Không** gắn HH/LH cấp 1. |

**Warm-up:** `left + right + 1` nến (đủ để xác nhận pivot cấp 1 đầu tiên).
Cấp 2 cần thêm ít nhất ba pivot cấp 1 cùng phía đã xác nhận.

## 3. Pivot cấp 1

Giữ nguyên fractal `swing_pivot` v1.1.0. Với `left = right = 3`, nến \(c\) là
đỉnh cấp 1 khi:

\[
H_c > \max(H_{c-3}, H_{c-2}, H_{c-1}, H_{c+1}, H_{c+2}, H_{c+3})
\]

So sánh **lớn hơn tuyệt đối**. Bằng nhau trong cửa sổ → không nhận pivot.
Đáy cấp 1 đối xứng bằng `low`.

Chỉ xác nhận sau khi nến \(c + \texttt{right}\) **đóng**.

```
event_bar_index     = c
confirmed_bar_index = c + right
confirmation_lag_bars = right
```

## 4. Đỉnh / đáy cấp 2 trên chuỗi pivot

Gọi \(P_{k-1}, P_k, P_{k+1}\) là **ba đỉnh cấp 1 liên tiếp đã xác nhận**,
không phải ba nến liên tiếp.

\(P_k\) là đỉnh cấp 2 khi:

\[
P_k > P_{k-1} \quad\text{và}\quad P_k > P_{k+1}
\]

Tương tự, với ba đáy cấp 1 liên tiếp \(Q\):

\[
Q_k < Q_{k-1} \quad\text{và}\quad Q_k < Q_{k+1}
\]

So sánh **nghiêm ngặt**. Đỉnh giữa bằng một trong hai đỉnh cạnh → không phải cấp 2.

**Thời điểm xác nhận cấp 2** là lúc pivot cấp 1 phía phải (\(P_{k+1}\) hoặc
\(Q_{k+1}\)) được xác nhận — tức tại nến đang xử lý trong `on_bar`.
Không được gắn tín hiệu khả dụng ngược về lúc đỉnh/đáy giữa hình thành,
cũng không về lúc đỉnh giữa được xác nhận cấp 1.

```
event_bar_index     = chỉ số nến của P_k (đỉnh giữa)
confirmed_bar_index = confirmed_bar_index của P_{k+1}
                    = event_bar_index(P_{k+1}) + right
confirmation_lag_bars = confirmed_bar_index − event_bar_index   (thường > right)
```

Mỗi bộ ba mới (khi thêm một pivot cấp 1) chỉ xét **một** ứng viên giữa.
Không xét lại bộ ba cũ.

## 5. Nhãn HH / LH / EQH trên cấp 2

Gọi \(S_{\text{prev}}\) và \(S_{\text{cur}}\) là hai đỉnh cấp 2 đã xác nhận liên tiếp:

\[
\text{Nhãn}=
\begin{cases}
HH  & S_{\text{cur}} > S_{\text{prev}} + \texttt{tol} \\
LH  & S_{\text{cur}} < S_{\text{prev}} - \texttt{tol} \\
EQH & \text{còn lại}
\end{cases}
\]

Với hai đáy cấp 2: cao hơn là `HL`, thấp hơn là `LL`, còn lại `EQL`.
Đỉnh/đáy cấp 2 **đầu tiên** chưa có nhãn so sánh.

`tol` (`label_eq_tolerance`) chỉ dùng bước này. Mặc định 0.

Nhãn dùng cùng `event_time` / `confirmed_at` với `SWING_HIGH_L2` /
`SWING_LOW_L2` vừa xác nhận, `reference_event_id` trỏ tới sự kiện cấp 2 liền trước.

## 6. Thứ tự trong cùng một nến

1. Xác nhận pivot cấp 1 tại \(c = i - \texttt{right}\) (nếu đủ cửa sổ).
2. Nếu `emit_level1`: phát `SWING_HIGH` / `SWING_LOW`. **Không** gắn HH cấp 1.
3. Thêm pivot vào chuỗi cấp 1 của phía tương ứng.
4. Nếu đủ ba pivot cùng phía: kiểm tra pivot giữa có phải cấp 2 không.
5. Nếu có cấp 2 mới: phát `SWING_HIGH_L2` / `SWING_LOW_L2`, rồi HH/LH/EQH
   (hoặc HL/LL/EQL) nếu đã có cấp 2 cùng phía trước đó.

Không có bước phá vỡ.

## 7. Ví dụ tính tay (left = right = 1)

Chuỗi đỉnh cấp 1:

```
2990 → 3000 → 2980 → 2988 → 2982 → 3010 → 2995
```

Bộ ba và kết quả cấp 2:

| Bộ ba cấp 1 | Giữa là cấp 2? | Nhãn cấp 2 |
|---|---|---|
| 2990, **3000**, 2980 | 3000 > 2990 và 3000 > 2980 → có | (đỉnh cấp 2 đầu, không nhãn) |
| 3000, 2980, 2988 | 2980 không cao hơn hai cạnh | — |
| 2980, **2988**, 2982 | 2988 > 2980 và 2988 > 2982 → có | 2988 < 3000 → **LH** |
| 2988, 2982, 3010 | 2982 không thấp/cao hơn theo quy tắc đỉnh | — |
| 2982, **3010**, 2995 | 3010 > 2982 và 3010 > 2995 → có | 3010 > 2988 → **HH** |

Ở cấp 1, 2988 > 2980 nên *nếu* so từng đỉnh fractal thì 2988 là HH nhỏ.
Ở cấp 2, 2988 < 3000 nên là **LH cấu trúc**. Thuật toán này **chỉ** phát nhãn
cấp 2. Cách này giảm nhãn nhỏ nhưng tăng độ trễ, và không bảo đảm mọi nhiễu biến mất.

## 8. Sự kiện phát ra

| `structure_type` | Nến sự kiện | Nến xác nhận | Ghi chú |
|---|---|---|---|
| `SWING_HIGH` / `SWING_LOW` | nến pivot cấp 1 | `+ right` | chỉ khi `emit_level1` |
| `SWING_HIGH_L2` / `SWING_LOW_L2` | nến của \(P_k\) / \(Q_k\) | lúc \(P_{k+1}\) / \(Q_{k+1}\) xác nhận | |
| `HH`, `LH`, `EQH` | nến của đỉnh cấp 2 hiện tại | giống `SWING_HIGH_L2` | so với đỉnh cấp 2 trước |
| `HL`, `LL`, `EQL` | nến của đáy cấp 2 hiện tại | giống `SWING_LOW_L2` | |

Mã lý do: `PIVOT_HIGH_STRICT` / `PIVOT_LOW_STRICT` (cấp 1),
`PIVOT_HIGH_L2` / `PIVOT_LOW_L2`, `SEQ_HIGHER_HIGH_L2` (và bộ SEQ_*_L2).

`details` của cấp 2 gồm `cap_do=2`, giá/nến ba pivot cấp 1 tạo thành nó,
và với nhãn: `gia_swing_truoc`, `gia_swing_nay`, `dung_sai_bang_gia`.

## 9. Đường mức trên chart

`timeline_point.muc_high` / `muc_low` là **đỉnh/đáy cấp 2 gần nhất đã xác nhận**
(mốc so sánh cho nhãn tiếp theo). Chưa có cấp 2 thì `null`. Đây không phải mức BOS.
