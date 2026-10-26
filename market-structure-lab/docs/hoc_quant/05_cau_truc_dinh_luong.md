# Module 5 — Cấu trúc thị trường định lượng

> **Sau module này bạn làm được:**
> - Viết một khái niệm chart (đỉnh, sweep, shift) thành luật có ngưỡng, có thời điểm biết và có cách xử lý chỗ mơ hồ.
> - Tự cài pivot strict 1/1 và khớp từng nến với sự kiện `SWING_HIGH` của lab.
> - Đo độ trễ xác nhận của STH, ITH/ITL và directional change.
> - Đếm sweep / run trên dữ liệu thật và trên bước ngẫu nhiên, nói được chênh lệch đáng tin tới đâu.
> - Bắt lỗi nhìn tương lai bằng phép thử tiền tố và phép thử «sửa tương lai».
>
> **Cần trước:** module 1 (ATR, khoảng trống), module 3 (bước ngẫu nhiên, `nen_tu_gia`, `chay_tren_df`)  ·  **Thời lượng:** ~6 giờ

> **Ba điều cần nhớ** (đọc lại khi ôn)
>
> 1. Định nghĩa vận hành biến khái niệm chart thành luật kiểm được: pivot 1/1 tự cài khớp 3 479/3 479 đỉnh của lab; ITH/ITL được biết trễ trung vị 5 nến.
> 2. Zigzag và pivot hai phía nhìn tương lai: gắn ở nến cực trị thì «đúng» 94,6%, gắn ở nến thật sự biết thì còn 45,6%, ngang đối chứng 46,7%.
> 3. «70% sweep» chủ yếu do định nghĩa (cửa sổ 0 nến → 41%, 6 nến → 77%). Luôn so với null khớp hình nến, và dùng phép thử tiền tố để bắt lỗi nhìn tương lai.

## Vì sao cần

Trên chart bạn thấy ngay «đỉnh» hay «giá quét BSL rồi sập». Máy thì chưa thấy gì cho tới khi bạn viết ra luật. Có hai câu
hỏi phải trả lời. Một: luật nào, đủ chặt để người khác (và chính bạn tuần sau) áp vào cùng dữ liệu thì ra cùng kết quả? Hai:
**biết lúc nào**? Một đỉnh chỉ «là đỉnh» khi các nến sau nó đã đóng thấp hơn. `ict_structure` của lab đã trả lời hai câu đó.
Trên XAUUSD M15 01–08/2024 có 1 575 vùng thanh khoản M15 bị lấy rồi kết thúc bằng sweep hoặc run; 70,7% là sweep. Con số này nghe
như «thị trường thích quét rồi quay đầu». Nhưng chạy đúng luật đó trên bước ngẫu nhiên thì được 67–70% (mục 6). Module này
dạy bốn việc phải làm trước khi tin một con số cấu trúc: viết luật, đo độ trễ, so với null và bắt lỗi nhìn tương lai.

## 1. Định nghĩa vận hành

**Trực giác.** Hỏi ba trader «nến này có phải swing high không», có thể nhận ba câu trả lời. «Rõ ràng», «đáng kể», «mạnh»
không đo được.

**Định nghĩa.** **Định nghĩa vận hành (operational definition)** là luật biến một khái niệm thành phép kiểm có / không trên
dữ liệu. Một định nghĩa đủ dùng có bốn phần:

1. **Đầu vào:** giá nào (high/low hay close), chỉ nến đã đóng.
2. **Điều kiện bằng số:** phép so sánh, ngưỡng. Lab tính ngưỡng theo ATR để không phụ thuộc mức giá.
3. **Thời điểm biết:** nến nào đóng thì được phép kết luận. Lab ghi hai mốc. **Nến sự kiện (event bar)** là chỗ cấu trúc
   nằm trên chart. **Nến xác nhận (confirmation bar)** là lúc máy được biết. **Độ trễ xác nhận (confirmation lag)** là
   khoảng cách giữa hai mốc này.
4. **Chỗ mơ hồ:** hai đỉnh bằng giá, khoảng trống phiên, một nến lấy nhiều vùng. Mỗi chỗ chọn một cách xử lý và ghi lại
   (đặc tả §6).

| Bạn nói trên chart | Luật của lab ([đặc tả](../algorithms/thuat_toan_ict_structure.md)) | Biết lúc |
|---|---|---|
| đỉnh nhỏ (STH) | high\[c\] lớn hơn nghiêm ngặt high nến trước và nến sau, cửa sổ không vắt qua khoảng trống (§4.3) | close nến c+1 |
| đỉnh trung hạn (ITH) | STH ở giữa cao hơn nghiêm ngặt STH liền trước và liền sau (§4.4) | close nến xác nhận STH bên phải |
| BSL | vùng ở mức ITH, hiệu lực từ nến sau nến xác nhận (§4.9) | — |
| «lấy» BSL | high − mức ≥ 0,1 × ATR của nến trước | close nến lấy b |
| sweep / run | close quay lại dưới mức trong \[b, b+3\] / không quay lại | close nến quay lại / close b+3 |
| shift giảm | sau sweep BSL, trong 3 nến có displacement giảm đóng dưới mức, cực trị cú quét chưa bị vượt (§4.10) | close nến displacement |

Mỗi sự kiện của lab mang sẵn cả hai mốc và câu luật:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

ev = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-02-01")["su_kien"]
pd.set_option("display.max_colwidth", 95)
for loai in ["SWING_HIGH", "SWING_HIGH_L2", "LIQ_SWEEP_BSL", "LIQ_RUN_UP", "SHIFT_DOWN"]:
    e = ev[ev.structure_type == loai].iloc[0]
    print("%-14s nến sự kiện %4d → biết ở nến %4d (trễ %d)" % (loai, e.event_bar_index, e.confirmed_bar_index,
                                                               e.confirmation_lag_bars))
    print("   luật:", e.reason_text_vi)
```

```text
Kết quả khi mình chạy:
SWING_HIGH     nến sự kiện    4 → biết ở nến    5 (trễ 1)
   luật: High của nến pivot LỚN HƠN TUYỆT ĐỐI mọi high trong cửa sổ trái/phải. Trường hợp bằng nhau không được nhận là pivot ở phiên bản này.
SWING_HIGH_L2  nến sự kiện    9 → biết ở nến   12 (trễ 3)
   luật: Đỉnh cấp 2: pivot cấp 1 giữa cao hơn tuyệt đối hai đỉnh cấp 1 liền kề trên chuỗi pivot (không phải ba nến liên tiếp). Chỉ xác nhận khi đỉnh cấp 1 bên phải đã xác nhận — không gắn về lúc đỉnh giữa hình thành.
LIQ_SWEEP_BSL  nến sự kiện   19 → biết ở nến   19 (trễ 0)
   luật: Giá xuyên mức ≥ ngưỡng × ATR (đã lấy) rồi close quay lại phía trong mức trong cửa sổ W nến (tính cả nến lấy), không gặp khoảng trống.
LIQ_RUN_UP     nến sự kiện  184 → biết ở nến  187 (trễ 3)
   luật: Đã lấy thanh khoản, hết cửa sổ W nến mà close không quay lại.
SHIFT_DOWN     nến sự kiện   44 → biết ở nến   44 (trễ 0)
   luật: Sau một sweep: nến displacement ngược chiều trong cửa sổ, close vượt lại mức bị quét, cực trị của cú quét chưa bị vượt, không có khoảng trống. Là «shift có displacement» lúc phát hiện — chưa biết sẽ tiếp diễn hay thất bại.
```

**Bẫy hay gặp.**
- Định nghĩa vận hành không phải chân lý. Ngưỡng 0,1 ATR và cửa sổ 3 nến là lab chọn (đặc tả §3 ghi «do lab chọn»). Đổi
  cửa sổ thì tỷ lệ sweep đổi theo (bài tập 3).
- Lấy một sự kiện rồi dùng nó ở nến sự kiện, như thể lúc đó đã biết, là nhìn tương lai (mục 4 và 7).

## 2. Pivot strict 1/1 (STH / STL)

**Trực giác.** Đỉnh nhỏ nhất bạn chỉ được trên chart là một nến cao hơn cả hai nến kề bên.

**Định nghĩa.** **STH (short-term high)** tại nến c khi

$$\text{high}_c > \text{high}_{c-1} \quad\text{và}\quad \text{high}_c > \text{high}_{c+1}$$

Nghĩa là high của nến c cao hơn hẳn high nến ngay trước và nến ngay sau. Chữ **strict** (nghiêm ngặt) nghĩa là bằng giá thì
không tính. Ba nến phải liền nhau: cửa sổ vắt qua nghỉ phiên hay cuối tuần thì không xét. Kết luận được khi nến c+1 đóng.
STL làm đối xứng với low. Tổng quát hơn: `pivot_left` = L nến bên trái, `pivot_right` = R nến bên phải, trễ đúng R nến.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

tu, den = "2024-01-01", "2024-09-01"
df = nap_nen(XAU_M15, tu, den)
h, t = df["high"].to_numpy(), df.index
# lien[i]: nến i nối liền nến i-1 (không có khoảng trống giữa hai nến)
lien = np.r_[False, (t[1:] - t[:-1]) == pd.Timedelta(minutes=15)]
c = np.arange(1, len(df) - 1)
# Luật STH strict 1/1: high[c] > high[c-1] và high[c] > high[c+1], cửa sổ 3 nến liền nhau. Biết khi nến c+1 đóng.
cao_hon = (h[c] > h[c - 1]) & (h[c] > h[c + 1])
cua_so_lien = lien[c] & lien[c + 1]
dinh_minh = set(c[cao_hon & cua_so_lien])

sth = chay_thuat_toan("ict_structure", XAU_M15, tu, den)["su_kien"].query("structure_type == 'SWING_HIGH'")
dinh_lab = set(sth.event_bar_index)
print("STH của mình: %d | của lab: %d | trùng: %d | chỉ mình có: %d | chỉ lab có: %d" % (
    len(dinh_minh), len(dinh_lab), len(dinh_minh & dinh_lab), len(dinh_minh - dinh_lab), len(dinh_lab - dinh_minh)))
print("độ trễ xác nhận của STH (nến → số đỉnh):", sth.confirmation_lag_bars.value_counts().to_dict())
bang_gia = ((h[c] == h[c - 1]) & (h[c] > h[c + 1])) | ((h[c] == h[c + 1]) & (h[c] > h[c - 1]))
print("bị loại vì bằng giá với nến kề bên:", int((bang_gia & cua_so_lien).sum()),
      "| bị chặn vì cửa sổ vắt qua khoảng trống:", int((cao_hon & ~cua_so_lien).sum()))

xem = df.iloc[112:124][["high"]].assign(vi_tri=range(112, 124))
xem["STH_minh"] = ["x" if i in dinh_minh else "" for i in xem.vi_tri]
xem["STH_lab"] = ["x" if i in dinh_lab else "" for i in xem.vi_tri]
print(xem.to_string())
```

```text
Kết quả khi mình chạy:
STH của mình: 3479 | của lab: 3479 | trùng: 3479 | chỉ mình có: 0 | chỉ lab có: 0
độ trễ xác nhận của STH (nến → số đỉnh): {1: 3479}
bị loại vì bằng giá với nến kề bên: 82 | bị chặn vì cửa sổ vắt qua khoảng trống: 108
                               high  vi_tri STH_minh STH_lab
bar_time                                                    
2024-01-03 04:00:00+00:00  2065.025     112                 
2024-01-03 04:15:00+00:00  2065.075     113                 
2024-01-03 04:30:00+00:00  2065.485     114        x       x
2024-01-03 04:45:00+00:00  2065.045     115                 
2024-01-03 05:00:00+00:00  2064.755     116                 
2024-01-03 05:15:00+00:00  2064.225     117                 
2024-01-03 05:30:00+00:00  2065.835     118        x       x
2024-01-03 05:45:00+00:00  2064.915     119                 
2024-01-03 06:00:00+00:00  2065.325     120        x       x
2024-01-03 06:15:00+00:00  2065.265     121                 
2024-01-03 06:30:00+00:00  2064.825     122                 
2024-01-03 06:45:00+00:00  2065.008     123        x       x
```

Khớp cả 3 479 đỉnh. 82 nến bị loại vì high bằng đúng nến kề bên: mắt bạn thấy đỉnh (đỉnh đôi), luật strict thì không. Lab
xử lý «bằng giá» ở tầng khác: gộp hai ITH gần nhau thành EQH theo `eq_tol_atr` (§4.9). 108 cửa sổ bị chặn vì khoảng trống.

**Bẫy hay gặp.**
- `event_bar_index` là vị trí nến **trong lần chạy** (đếm từ 0 ở ngày `tu`), không phải cột `idx` của dataset. So với
  `nap_nen` thì phải dùng đúng cùng `tu`.

## 3. Độ trễ xác nhận và ITH / ITL

**Trực giác.** Nhìn lại bảng ở mục 2. Các nến 114 (2065,485), 118 (2065,835) và 120 (2065,325) đều là STH. Nến 118 cao hơn
hai STH hai bên nên là đỉnh trung hạn. Nhưng phải tới khi nến 121 đóng, máy mới biết 120 là STH. Vì vậy lab ghi sự kiện
`ict:SWING_HIGH_L2@118>121`: nằm ở nến 118, biết ở nến 121.

**Định nghĩa.** **ITH (intermediate-term high)**: trong ba STH liên tiếp (trái, giữa, phải), STH giữa cao hơn nghiêm ngặt
cả hai. ITH được xác nhận khi STH bên phải xác nhận. Trễ ngắn nhất là 3 nến. Nến c+1 thấp hơn c nên không thể là STH; STH
phải sớm nhất ở c+2 và được biết ở c+3. Trễ dài nhất thì không có giới hạn, vì nó tuỳ giá mất bao lâu mới tạo được STH
thấp hơn. ITL đối xứng.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

ev = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
ith = ev[ev.structure_type.isin(["SWING_HIGH_L2", "SWING_LOW_L2"])]
tre_nen = ith.confirmed_bar_index - ith.event_bar_index          # nến xác nhận − nến sự kiện (nến cực trị)
tre_gio = (pd.to_datetime(ith.confirmed_at) - pd.to_datetime(ith.event_close_time)).dt.total_seconds() / 3600

print("số ITH + ITL: %d" % len(ith))
print("trễ (nến): TV %.0f | P25 %.0f | P75 %.0f | P90 %.0f | max %d" % (
    tre_nen.median(), tre_nen.quantile(.25), tre_nen.quantile(.75), tre_nen.quantile(.9), tre_nen.max()))
print("trễ (giờ đồng hồ): TV %.2f | P90 %.2f | max %.1f" % (tre_gio.median(), tre_gio.quantile(.9), tre_gio.max()))
phan_bo = (100 * tre_nen.clip(upper=12).value_counts(normalize=True).sort_index()).round(1)
phan_bo.index = [str(i) if i < 12 else "≥12" for i in phan_bo.index]
print("% theo số nến trễ:"); print(phan_bo.to_frame().T.to_string(index=False))
print("trễ ≥ 8 nến (≥ 2 giờ): %.1f%%" % (100 * (tre_nen >= 8).mean()))
```

```text
Kết quả khi mình chạy:
số ITH + ITL: 1768
trễ (nến): TV 5 | P25 4 | P75 7 | P90 9 | max 18
trễ (giờ đồng hồ): TV 1.25 | P90 2.32 | max 52.8
% theo số nến trễ:
   3    4    5    6   7   8   9  10  11  ≥12
17.8 20.1 20.1 13.9 9.8 6.5 4.0 2.5 1.9  3.3
trễ ≥ 8 nến (≥ 2 giờ): 18.2%
```

Trễ trung vị (TV) là 5 nến (1 giờ 15 phút); 18% phải chờ từ 2 giờ trở lên. Dài nhất là 18 nến theo nến, 52,8 giờ theo
đồng hồ (vắt qua cuối tuần). Cái giá của độ trễ: lúc ITH được biết, close trung vị đã rời đỉnh khoảng 1,5 ATR (bài tập 2).

**Bẫy hay gặp.**
- Trễ theo nến khác trễ theo giờ khi có khoảng trống. Báo cả hai.
- Độ trễ là cái giá của nhân quả. Không có cách nào «sửa» nó; chỉ có cách đổi định nghĩa, vd pivot nhỏ hơn thì ít trễ hơn
  nhưng nhiều nhiễu hơn. Plan regime ghi «pivot ~5 nến» chính là con số này.

## 4. Zigzag và pivot hai phía: đẹp vì nhìn tương lai

**Trực giác.** Chỉ báo zigzag trên chart vẽ trúng mọi đỉnh đáy, vì nó được vẽ **sau khi** mọi chuyện đã xảy ra.

**Định nghĩa.** **Zigzag** với ngưỡng θ: điểm đảo chiều là cực trị của close giữa hai lần giá quay đầu ít nhất θ (tính theo
tỷ lệ). Điểm được vẽ ở **nến cực trị** e nhưng chỉ biết được ở **nến biết** k, lúc giá đã quay đầu đủ θ. Chân cuối đang chạy
được vẽ tới cực trị hiện tại và **vẽ lại (repaint)** mỗi khi giá đi tiếp. **Pivot hai phía** n/n (vd 5/5) là nến có high cao
nhất trong 5 nến trước và 5 nến sau, nên chỉ biết được ở c+5. Viết bằng `rolling(11, center=True)` nghĩa là dùng 5 nến tương
lai. **Nhìn tương lai (look-ahead bias)** là dùng một thông tin mà ở thời điểm quyết định chưa có.

Phép thử: đặt mốc ở từng đỉnh, rồi hỏi «8 nến sau giá có thấp hơn không?».

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
c, h, n = df["close"].to_numpy(), df["high"].to_numpy(), len(df)

def zigzag(c, theta):
    """Zigzag theo close, đảo chiều ≥ theta (tỷ lệ). Trả [(nến cực trị, 'H'/'L', nến biết)] và chân cuối chưa xác nhận."""
    out, huong, cuc = [], 0, 0
    for i in range(1, len(c)):
        if huong == 0 and abs(c[i] / c[0] - 1) >= theta:
            huong, cuc = (1 if c[i] > c[0] else -1), i            # hướng đầu tiên
        elif huong == 1 and c[i] > c[cuc] or huong == -1 and c[i] < c[cuc]:
            cuc = i                                                # cực trị mới, chân đang chạy kéo dài
        elif huong != 0 and huong * (c[cuc] - c[i]) >= theta * c[cuc]:
            out.append((cuc, "H" if huong == 1 else "L", i))       # quay đầu đủ θ → BIẾT ở nến i
            huong, cuc = -huong, i
    return out, cuc

H = 8   # nhìn 8 nến (2 giờ) sau mốc
def do(moc):
    """Số mốc, % «close H nến sau thấp hơn close ở mốc», thay đổi trung bình (%)."""
    moc = np.array([m for m in moc if m + H < n])
    thay_doi = (c[moc + H] / c[moc] - 1) * 100
    return len(moc), (thay_doi < 0).mean() * 100, thay_doi.mean()

piv, chan_cuoi = zigzag(c, 0.0025)                                 # θ = 0,25%
dinh = [(e, k) for e, loai, k in piv if loai == "H"]
# Pivot «hai phía» 5/5: high[i] cao nhất nghiêm ngặt trong 5 nến trước và 5 nến sau
p5 = [i for i in range(5, n - 5) if h[i] > max(h[i - 5:i].max(), h[i + 1:i + 6].max())]
bang = pd.DataFrame([("zigzag 0,25% — gắn ở nến cực trị", *do([e for e, k in dinh])),
                     ("zigzag 0,25% — gắn ở nến biết", *do([k for e, k in dinh])),
                     ("pivot 5/5 — gắn ở nến giữa", *do(p5)),
                     ("pivot 5/5 — gắn ở nến c+5 (biết)", *do([i + 5 for i in p5])),
                     ("mọi nến (đối chứng)", *do(range(n)))],
                    columns=["mốc", "số mốc", "% giá 8 nến sau thấp hơn", "thay đổi TB (%)"])
print(bang.round(3).to_string(index=False))
tre = [k - e for e, _, k in piv]
print("zigzag: %d điểm, trễ (nến biết − nến cực trị) TV %.0f, P90 %.0f; chân cuối chưa xác nhận ở nến %d / %d" % (
    len(piv), np.median(tre), np.percentile(tre, 90), chan_cuoi, n - 1))
```

```text
Kết quả khi mình chạy:
                             mốc  số mốc  % giá 8 nến sau thấp hơn  thay đổi TB (%)
zigzag 0,25% — gắn ở nến cực trị     388                    94.588           -0.302
   zigzag 0,25% — gắn ở nến biết     388                    45.619            0.002
      pivot 5/5 — gắn ở nến giữa     955                    74.555           -0.133
pivot 5/5 — gắn ở nến c+5 (biết)     954                    46.017            0.013
             mọi nến (đối chứng)   15842                    46.686            0.010
zigzag: 776 điểm, trễ (nến biết − nến cực trị) TV 5, P90 16; chân cuối chưa xác nhận ở nến 15839 / 15849
```

Gắn ở nến cực trị, zigzag «đoán đúng» 94,6% rằng giá 2 giờ sau thấp hơn: tuyệt vời trên giấy, vô nghĩa ngoài đời. Gắn ở
nến biết thì còn 45,6%, ngang mức đối chứng 46,7% của mọi nến (dưới 50% vì vàng tăng mạnh năm 2024). Pivot 5/5 cũng vậy:
74,6% ở nến giữa, 46,0% ở nến biết.

Vì vậy zigzag và pivot hai phía chỉ được dùng làm **nhãn hậu kiểm (hindsight label)**: đáp án để chấm thuật toán (module 7),
không bao giờ là đầu vào hay tín hiệu ([AGENTS.md](../../AGENTS.md) §2.1).

**Bẫy hay gặp.**
- Nhiều indicator zigzag và fractal trên MT5 / TradingView vẽ lại. Backtest bằng giá trị đã vẽ chính là nhìn tương lai.
- Bản thân zigzag tính tuần tự được. Lỗi nằm ở chỗ gắn điểm vào nến cực trị thay vì nến biết. Chỉ giữ điểm đã biết thì
  zigzag qua được phép thử tiền tố (bài tập 4). Đó chính là directional change ở mục sau.

## 5. Directional change theo ATR

**Trực giác.** Thay câu hỏi «nến này có cao hơn hàng xóm không» bằng câu «giá đã quay đầu đủ xa chưa».

**Định nghĩa.** **Đổi hướng theo ngưỡng (directional change, DC)** trong `dc_atr_structure` chạy theo close. Ngưỡng
$\Delta = k \times \text{ATR14}_e$ được khoá tại nến cực trị e. Khi đang tìm đỉnh, close nào cao hơn ứng viên thì ứng viên
dời lên đó. Close nào ≤ ứng viên − Δ thì phát `DC_HIGH` tại e; nến hiện tại là nến biết. Tìm đáy làm đối xứng. Ứng viên cuối
không bao giờ bị ép thành pivot. Như vậy DC chính là zigzag viết theo kiểu nhân quả, ngưỡng tính bằng ATR.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

dong = []
for k in (1.0, 1.5, 2.0):
    kq = chay_thuat_toan("dc_atr_structure", XAU_M15, "2024-01-01", "2024-09-01", tham_so={"atr_multiplier": k})
    piv = kq["su_kien"].query("structure_type in ['DC_HIGH', 'DC_LOW']")
    tre = piv.details.map(lambda d: d["lag_bars"])                     # nến xác nhận − nến cực trị
    dao = piv.details.map(lambda d: d["reversal_distance_atr"])        # giá đã quay đầu bao xa lúc biết
    dong.append((k, len(piv), 1000 * len(piv) / len(kq["nen"]), tre.median(), tre.quantile(.9), dao.median()))
print(pd.DataFrame(dong, columns=["k (× ATR)", "số pivot", "pivot /1000 nến", "trễ TV (nến)", "trễ P90 (nến)",
                                  "quay đầu lúc biết (ATR) TV"]).round(2).to_string(index=False))

# Mỗi pivot mang công thức ngưỡng và điều kiện xác nhận bằng số thật
r = kq["su_kien"].query("structure_type == 'DC_HIGH'").iloc[3]
print(r.event_id, "| nến cực trị", r.event_bar_index, "→ biết ở nến", r.confirmed_bar_index)
print(" ", r.details["cong_thuc_nguong"], "|", r.details["dieu_kien_xac_nhan"])
```

```text
Kết quả khi mình chạy:
 k (× ATR)  số pivot  pivot /1000 nến  trễ TV (nến)  trễ P90 (nến)  quay đầu lúc biết (ATR) TV
       1.0      1533            96.72           2.0            5.0                        1.28
       1.5       856            54.01           3.0            8.0                        1.84
       2.0       553            34.89           4.0           11.0                        2.34
dc:s3:DC_HIGH:308>318 | nến cực trị 308 → biết ở nến 318
  Δ = k × ATR14[e] = 2 × 1.51811 = 3.03623 | close[t] = 2041.14 ≤ 2045.03 − 3.03623 = 2041.99
```

k càng lớn thì càng ít pivot, nhịp càng dài và trễ càng lâu (TV 2 → 3 → 4 nến, P90 5 → 8 → 11). Đây là một đánh đổi. Chừng
nào chưa có nhãn thì không có k nào «đúng» ([đặc tả DC](../algorithms/thuat_toan_dc_atr_structure.md) §8). Với k = 1,5, DC
cho 54 pivot / 1000 nến, trễ TV 3 nến; ITH/ITL cho khoảng 111 / 1000 nến, trễ TV 5 nến.

**Bẫy hay gặp.**
- DC đo theo close, ITH đo theo wick. So DC với nhãn swing là **so chéo định nghĩa**, phải ghi rõ (đặc tả DC §5).

## 6. Vùng thanh khoản: chạm → lấy → sweep / run, so với bước ngẫu nhiên

**Trực giác.** Phía trên một đỉnh có lệnh dừng của người bán, gọi là BSL. ICT nói giá «đi lấy thanh khoản». Lab biến câu đó
thành một vòng đời đo được.

**Định nghĩa** (đặc tả §4.9). Mỗi ITH sinh một vùng **BSL (buy-side liquidity)** ở mức đỉnh; mỗi ITL sinh một vùng **SSL**.
Vùng có hiệu lực từ nến ngay sau nến xác nhận. Với vùng BSL ở mức M:

- **chạm (touch):** $0 < \text{high}_t - M < 0{,}1 \times \text{ATR}_{t-1}$. Vùng vẫn còn nguyên.
- **lấy (take)** tại nến b đầu tiên có $\text{high}_b - M \ge 0{,}1 \times \text{ATR}_{b-1}$. Nghĩa là giá xuyên qua mức
  ít nhất một phần mười ATR của nến trước.
- **sweep:** nến r đầu tiên trong \[b, b+3\] có close dưới M (quay lại). `sweep_bars` = r − b, bằng 0 khi quay lại ngay trong
  nến lấy.
- **run:** tới hết nến b+3 vẫn không có close nào quay lại.
- **chưa rõ (unresolved):** gặp khoảng trống trước khi rõ kết cục.

Đếm trên dữ liệu thật, rồi chạy **đúng luật đó** trên bước ngẫu nhiên không xu hướng (module 3) với hai kiểu nến:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

KET_CUC = {"LIQ_SWEEP_BSL": "sweep", "LIQ_SWEEP_SSL": "sweep", "LIQ_RUN_UP": "run", "LIQ_RUN_DOWN": "run",
           "LIQ_UNRESOLVED": "chưa rõ"}

def dem_vung(kq):
    """Kết cục theo TỪNG VÙNG tầng M15 (một sự kiện có thể gom nhiều vùng — details['pools'])."""
    ev = kq["su_kien"]
    vung = [(KET_CUC[l], p) for l, d in zip(ev.structure_type, ev.details) if l in KET_CUC
            for p in d["pools"] if p["tang"] == "M15"]
    kc = pd.Series([k for k, _ in vung]).value_counts()
    sw, ru = kc.get("sweep", 0), kc.get("run", 0)
    h, l, c = (np.array([getattr(b, k) for b in kq["nen"]]) for k in ("high", "low", "close"))
    return {"biên độ nến / |Δclose| (hình nến)": (h - l).mean() / np.abs(np.diff(c)).mean(),
            "ITH+ITL /1000 nến": 1000 * ev.structure_type.isin(["SWING_HIGH_L2", "SWING_LOW_L2"]).sum() / len(c),
            "vùng bị lấy": len(vung), "sweep": sw, "run": ru, "chưa rõ": kc.get("chưa rõ", 0),
            "% sweep = sweep/(sweep+run)": 100 * sw / (sw + ru),
            "% sweep quay lại ngay nến lấy": 100 * np.mean([p["sweep_bars"] == 0 for k, p in vung if k == "sweep"]),
            "xuyên lúc lấy (ATR) TV": np.median([p["xuyen_atr"] for _, p in vung])}

cot = {"XAU M15 thật": dem_vung(chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01"))}
# Null: bước ngẫu nhiên không xu hướng, cùng số nến (15 850), không có phiên (module 3).
# so_tick_moi_nen quyết định HÌNH nến: ít tick → râu ngắn hơn nến thật.
for tick in (15, 240):
    for seed in (1, 2):
        gia = 2000 + np.cumsum(np.random.default_rng(seed).normal(0, 0.5, 15850 * tick))
        cot["NN %d tick #%d" % (tick, seed)] = dem_vung(chay_tren_df("ict_structure", nen_tu_gia(gia, so_tick_moi_nen=tick)))
print(pd.DataFrame(cot).round(2).to_string())
```

```text
Kết quả khi mình chạy:
                                   XAU M15 thật  NN 15 tick #1  NN 15 tick #2  NN 240 tick #1  NN 240 tick #2
biên độ nến / |Δclose| (hình nến)          2.02           1.60           1.59            1.90            1.91
ITH+ITL /1000 nến                        111.55         109.91         108.83          105.80          105.55
vùng bị lấy                             1583.00        1615.00        1576.00         1492.00         1497.00
sweep                                   1113.00        1067.00        1018.00         1028.00         1003.00
run                                      462.00         548.00         558.00          464.00          494.00
chưa rõ                                    8.00           0.00           0.00            0.00            0.00
% sweep = sweep/(sweep+run)               70.67          66.07          64.59           68.90           67.00
% sweep quay lại ngay nến lấy             58.76          48.83          45.78           53.31           54.34
xuyên lúc lấy (ATR) TV                     0.56           0.39           0.44            0.36            0.38
```

Cách đọc bảng:

- Thật: 70,7% sweep. Bước ngẫu nhiên, không có «smart money» nào: 64,6–66,1% (15 tick / nến), 67,0–68,9% (240 tick / nến).
- Số tick đổi **hình nến**. Biên độ nến / |Δclose| của dữ liệu thật là 2,02, sát giá trị 2 của chuyển động Brown liên tục;
  nến 15 tick chỉ được 1,60, râu quá ngắn nên ít sweep ngay trong nến lấy. Null phải giống dữ liệu thật ở mọi chỗ **không**
  thuộc giả thuyết đang kiểm.
- 6 hạt giống null 240 tick cho 69,2% ± 1,5 điểm % (bài tập 5): 70,7% chỉ cách khoảng một độ lệch chuẩn. Cả mật độ đỉnh
  đáy cũng gần nhau: 111,6 ITH+ITL / 1000 nến so với 105,6–109,9.
- Còn hai chênh lệch: thật «quay lại ngay nến lấy» nhiều hơn (58,8% so với 53–54%) và xuyên sâu hơn (0,56 so với 0,36–0,38
  ATR). Hợp với đuôi dày và biến động co cụm (module 4) mà null iid không có; muốn quy cho «cấu trúc» phải dùng null giữ biến
  động (module 3).

Điều này khớp với kết quả lớn của lab: không cách đọc order flow nào dự báo phía thanh khoản bị lấy kế tiếp tốt hơn mốc ngẫu
nhiên (lệch trong ±2 điểm %, [nghiên cứu order flow](../research/nghien_cuu_orderflow_ict.md)).

**Bẫy hay gặp.**
- Đếm theo sự kiện khác đếm theo vùng. Một sự kiện có thể gom nhiều vùng (`details["pools"]`) thuộc nhiều tầng (M15, H1, H4,
  D, W từ bản 0.4.0). Muốn so với đặc tả §8 thì đếm theo vùng tầng M15. Module 3 đếm theo sự kiện, mọi tầng, nên ra 72,8% cho
  dữ liệu thật; kết luận vẫn như nhau, và mục 5 của module 3 tách phần chênh thành hình nến và thứ tự biến động trong ngày.
- Tỷ lệ sweep phụ thuộc trước hết vào W: 41% khi W = 0 và 77% khi W = 6 (bài tập 3). «70% sweep» trước hết là tính chất của
  định nghĩa.

## 7. Phép thử tiền tố và phép thử «sửa tương lai»

**Trực giác.** Thuật toán nhân quả giống bạn đang xem replay: ở nến t chỉ thấy tới t. Nếu kết luận ở t đổi khi có thêm nến
sau t thì nó đã nhìn tương lai.

**Định nghĩa.**
- **Phép thử tiền tố (prefix test):** chạy trên các nến \[0, t\] được tập sự kiện $A_t$. Chạy trên toàn bộ dữ liệu rồi chỉ giữ
  sự kiện có `confirmed_bar_index` ≤ t được $B_t$. Thuật toán nhân quả phải có $A_t = B_t$ ở mọi t, và timeline tới t cũng
  phải giống hệt.
- **Phép thử sửa tương lai:** thay mọi nến sau t bằng dữ liệu khác. Sự kiện đã biết tới t và timeline tới t không được đổi.

Lab bắt buộc cả hai phép thử cho mọi thuật toán ([AGENTS.md](../../AGENTS.md) §7.1;
[test](../../tests/algorithms/test_ict_structure.py) `test_nhan_qua_prefix_bang_full_va_sua_duoi_khong_doi_qua_khu`).
Bạn tự làm lại:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

TU = "2024-01-01"
tron = chay_thuat_toan("ict_structure", XAU_M15, TU, "2024-03-01")["ket_qua"]
ev_tron = [e.to_dict() for e in tron.events]

thua = []
for cat in ["2024-01-10", "2024-01-26 14:00", "2024-02-14 08:45", "2024-02-29 20:30"]:
    phan = chay_thuat_toan("ict_structure", XAU_M15, TU, cat)["ket_qua"]
    t = len(phan.timeline) - 1                                   # nến cuối của tiền tố
    ev_phan = [e.to_dict() for e in phan.events]
    ky_vong = [e for e in ev_tron if e["confirmed_bar_index"] <= t]   # chạy trọn rồi cắt theo LÚC BIẾT
    sai_cat = [e for e in ev_tron if e["event_bar_index"] <= t]       # cắt SAI: theo nến sự kiện
    print("cắt ở nến %5d (%s): sự kiện %s, timeline %s | cắt theo nến sự kiện thừa %d sự kiện chưa biết" % (
        t, cat, "khớp" if ev_phan == ky_vong else "KHÁC",
        "khớp" if phan.timeline == tron.timeline[: t + 1] else "KHÁC", len(sai_cat) - len(ky_vong)))
    thua += [e["structure_type"] for e in sai_cat if e["confirmed_bar_index"] > t]
print("các sự kiện «thừa» khi cắt sai:", pd.Series(thua).value_counts().to_dict())
```

```text
Kết quả khi mình chạy:
cắt ở nến   555 (2024-01-10): sự kiện khớp, timeline khớp | cắt theo nến sự kiện thừa 3 sự kiện chưa biết
cắt ở nến  1633 (2024-01-26 14:00): sự kiện khớp, timeline khớp | cắt theo nến sự kiện thừa 5 sự kiện chưa biết
cắt ở nến  2829 (2024-02-14 08:45): sự kiện khớp, timeline khớp | cắt theo nến sự kiện thừa 5 sự kiện chưa biết
cắt ở nến  3831 (2024-02-29 20:30): sự kiện khớp, timeline khớp | cắt theo nến sự kiện thừa 1 sự kiện chưa biết
các sự kiện «thừa» khi cắt sai: {'HTF_SWING_HIGH': 2, 'HTF_SWING_LOW': 2, 'HTF_PERIOD_HIGH': 2, 'FVG_UP': 1, 'SWING_HIGH_L2': 1, 'SWING_LOW_L2': 1, 'HTF_FVG_UP': 1, 'HTF_PERIOD_LOW': 1, 'FVG_DOWN': 1, 'SWING_HIGH': 1, 'SWING_LOW': 1}
```

Bốn điểm cắt đều khớp. Cắt **sai** (theo `event_bar_index`) thì thừa 1–5 sự kiện: thứ đã nằm trên chart trước t nhưng ở t
chưa biết (STH, STL chờ nến sau; ITH, ITL chờ STH bên phải; FVG chờ nến thứ ba; swing, FVG và mức khung lớn chờ nến H1/H4/D
chốt).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-02-01", "2024-03-01")
chay = lambda d: chay_tren_df("ict_structure", d, "M15", lich_phien="cme_globex_metals")["ket_qua"]
goc = chay(df)
# Bộ «gian lận»: đỉnh = high lớn nhất trong cửa sổ GIỮA 11 nến (5 trước, 5 sau)
pivot_5_5 = lambda d: (d["high"] == d["high"].rolling(11, center=True).max()).to_numpy()

dong = []
for t in sorted(np.random.default_rng(7).choice(np.arange(100, len(df) - 10), size=12, replace=False)):
    moi = df.copy()
    moi.iloc[t + 1:, moi.columns.get_indexer(["open", "high", "low", "close"])] += 30.0   # tương lai khác hẳn
    kq = chay(moi)
    giu = ([e.to_dict() for e in goc.events if e.confirmed_bar_index <= t] ==
           [e.to_dict() for e in kq.events if e.confirmed_bar_index <= t]) and goc.timeline[: t + 1] == kq.timeline[: t + 1]
    doi = np.flatnonzero(pivot_5_5(df)[: t + 1] != pivot_5_5(moi)[: t + 1])
    dong.append((t, giu, len(doi), (t - doi).tolist()))
print(pd.DataFrame(dong, columns=["nến cắt t", "ict_structure giữ nguyên ≤ t", "pivot 5/5: số nhãn ≤ t bị đổi",
                                  "nhãn đổi cách t (nến)"]).to_string(index=False))
```

```text
Kết quả khi mình chạy:
 nến cắt t  ict_structure giữ nguyên ≤ t  pivot 5/5: số nhãn ≤ t bị đổi nhãn đổi cách t (nến)
       200                          True                              0                    []
       507                          True                              0                    []
       616                          True                              0                    []
       643                          True                              1                   [3]
      1143                          True                              0                    []
      1226                          True                              0                    []
      1333                          True                              1                   [2]
      1500                          True                              0                    []
      1606                          True                              0                    []
      1682                          True                              1                   [1]
      1718                          True                              0                    []
      1801                          True                              0                    []
```

`ict_structure` giữ nguyên ở cả 12 điểm cắt. Pivot 5/5 cửa sổ giữa đổi nhãn ở 3/12 điểm cắt, mỗi lần ở một nến cách t 1–3
nến: dấu vân tay của nhìn tương lai.

**Bẫy hay gặp.**
- Phép thử chỉ bắt được lỗi khi điểm cắt rơi đúng chỗ. Hãy dùng nhiều điểm cắt, có cả điểm sát khoảng trống.
- Cắt theo nến sự kiện là rò rỉ, kể cả khi thuật toán đúng.
- Nhìn tương lai không chỉ nằm trong thuật toán. Chuẩn hoá bằng thống kê của cả dataset (min/max, trung bình cả năm) cũng là
  nhìn tương lai. Module 6 vì thế chỉ tính mùa vụ trên đoạn fit.

## Lab đang dùng những điều này ở đâu

| Khái niệm | File / tài liệu | Ghi chú |
|---|---|---|
| Định nghĩa vận hành trước khi code | [AGENTS.md](../../AGENTS.md) §3 (bước ②), §3.2 | Đặc tả viết trước, chỗ mơ hồ ghi thành bảng |
| Pivot strict STH/STL | [swing_source.py](../../core/components/swing_source.py), [đặc tả](../algorithms/thuat_toan_ict_structure.md) §4.3 | `PivotSource`, chặn cửa sổ qua khoảng trống |
| ITH/ITL, LTH/LTL | [hierarchy.py](../../core/components/hierarchy.py), §4.4 | Xác nhận khi STH bên phải xác nhận |
| Thời điểm biết từng loại sự kiện | [đặc tả](../algorithms/thuat_toan_ict_structure.md) §5 | Bảng «Nến sự kiện / Biết lúc» |
| Directional change | [detector.py](../../core/algorithms/dc_atr_structure/detector.py), [thuat_toan_dc_atr_structure.md](../algorithms/thuat_toan_dc_atr_structure.md) | Δ khoá ở nến cực trị, theo close |
| Pivot n/n (baseline) | [swing_pivot](../../core/algorithms/swing_pivot/algorithm.py), [thuat_toan_swing_pivot.md](../algorithms/thuat_toan_swing_pivot.md) | Cũng xác nhận ở c+R |
| Vùng thanh khoản, sweep / run | [liquidity.py](../../core/components/liquidity.py), §4.9 | `LiquidityBook`, đếm theo vùng trong `details.pools` |
| Shift | [shift.py](../../core/components/shift.py), [displacement.py](../../core/components/displacement.py), §4.10 | Sweep → displacement ngược chiều |
| Phép thử tiền tố, sửa tương lai | [test_ict_structure.py](../../tests/algorithms/test_ict_structure.py), [test_dc_atr_structure.py](../../tests/algorithms/test_dc_atr_structure.py) | Bắt buộc theo AGENTS §7.1 |
| Kiểm bất biến nhân quả trên run đã lưu | [causality.py](../../core/eval/causality.py) | Không thay được phép thử tiền tố |
| So với mốc ngẫu nhiên | [nghien_cuu_orderflow_ict.md](../research/nghien_cuu_orderflow_ict.md), [orderflow_rules.py](../../research/orderflow_rules.py) | Order flow không hơn ngẫu nhiên (±2 điểm %) |

## Bài tập

**Bài 1 — Pivot 2/2.** Tự cài STL strict với L = R = 2 (low nhỏ hơn nghiêm ngặt 2 low trước và 2 low sau, cửa sổ 5 nến liền
nhau). So với `SWING_LOW` khi chạy lab với `tham_so={"pivot_left": 2, "pivot_right": 2}`. Độ trễ STL bây giờ là bao nhiêu? Còn
trễ của ITH/ITL?
*Gợi ý:* cửa sổ liền nhau khi mọi bước trong \[c−L, c+R\] đều đúng 15 phút.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

tu, den = "2024-01-01", "2024-09-01"
df = nap_nen(XAU_M15, tu, den)
lo, t = df["low"].to_numpy(), df.index
L = R = 2
lien = np.r_[False, (t[1:] - t[:-1]) == pd.Timedelta(minutes=15)]
day_minh = set()
for c in range(L, len(df) - R):
    cua_so_lien = lien[c - L + 1: c + R + 1].all()          # mọi bước trong [c-L, c+R] liền nhau
    trai, phai = lo[c - L:c], lo[c + 1:c + R + 1]
    if cua_so_lien and lo[c] < trai.min() and lo[c] < phai.min():
        day_minh.add(c)

kq = chay_thuat_toan("ict_structure", XAU_M15, tu, den, tham_so={"pivot_left": L, "pivot_right": R})
stl = kq["su_kien"].query("structure_type == 'SWING_LOW'")
lab = set(stl.event_bar_index)
print("STL 2/2 của mình:", len(day_minh), "| của lab:", len(lab), "| trùng:", len(day_minh & lab))
print("trễ xác nhận:", stl.confirmation_lag_bars.value_counts().to_dict())
ith = kq["su_kien"].query("structure_type in ['SWING_HIGH_L2', 'SWING_LOW_L2']")
print("ITH+ITL với pivot 2/2: %d, trễ TV %.0f nến, P90 %.0f nến" % (
    len(ith), ith.confirmation_lag_bars.median(), ith.confirmation_lag_bars.quantile(.9)))
```

```text
Kết quả khi mình chạy:
STL 2/2 của mình: 2025 | của lab: 2025 | trùng: 2025
trễ xác nhận: {2: 2025}
ITH+ITL với pivot 2/2: 1038, trễ TV 9 nến, P90 16 nến
```

Khớp 2025/2025, trễ STL đúng bằng R = 2. ITH+ITL giảm từ 1 768 còn 1 038 nhưng trễ trung vị tăng từ 5 lên 9 nến: ít nhiễu
hơn, biết muộn hơn.
</details>

**Bài 2 — Lúc biết thì giá đã đi bao xa?** Với mỗi ITH, tính (mức đỉnh − close ở nến xác nhận) / ATR ở nến đó; với ITL
thì đổi dấu. Trung vị là bao nhiêu ATR? Bao nhiêu phần trăm lớn hơn 1 ATR?
*Gợi ý:* `kq["nen"][k].close`, `kq["timeline"]["atr"]`. ATR là NaN ở vài nến đầu, nhớ bỏ.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

kq = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")
ev, tl = kq["su_kien"], kq["timeline"]
close = np.array([b.close for b in kq["nen"]])
atr = tl["atr"].to_numpy(dtype=float)              # ATR sau nến t (NaN ở vài nến đầu: chưa đủ dữ liệu)

for loai, dau in (("SWING_HIGH_L2", 1), ("SWING_LOW_L2", -1)):
    s = ev[ev.structure_type == loai]
    k = s.confirmed_bar_index.to_numpy()
    roi = dau * (s.price.to_numpy() - close[k]) / atr[k]          # cực trị − close lúc biết, theo ATR
    roi = roi[np.isfinite(roi)]
    print("%s (%d): close lúc biết cách cực trị TV %.2f ATR, P75 %.2f, P90 %.2f; %.0f%% số lần > 1 ATR" % (
        loai, len(roi), np.median(roi), np.percentile(roi, 75), np.percentile(roi, 90), 100 * (roi > 1).mean()))
```

```text
Kết quả khi mình chạy:
SWING_HIGH_L2 (887): close lúc biết cách cực trị TV 1.53 ATR, P75 2.37, P90 3.46; 75% số lần > 1 ATR
SWING_LOW_L2 (879): close lúc biết cách cực trị TV 1.65 ATR, P75 2.46, P90 3.27; 77% số lần > 1 ATR
```

Lúc được phép nói «đó là đỉnh», close trung vị đã dưới đỉnh ~1,5 ATR, 3/4 số lần hơn 1 ATR. «Bán ngay đỉnh» chỉ có trên
chart hậu kiểm.
</details>

**Bài 3 — Tỷ lệ sweep là của thị trường hay của định nghĩa?** Chạy lab với `sweep_window` W = 0, 1, 3, 6 trên dữ liệu thật và
trên một bước ngẫu nhiên 240 tick mỗi nến. Lập bảng % sweep theo vùng M15. W ảnh hưởng nhiều hơn hay khác biệt thật / ngẫu
nhiên ảnh hưởng nhiều hơn?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def ty_le_sweep(kq):
    kc = [l[:9] for l, d in zip(kq["su_kien"].structure_type, kq["su_kien"].details)
          if l[:9] in ("LIQ_SWEEP", "LIQ_RUN_U", "LIQ_RUN_D") for p in d["pools"] if p["tang"] == "M15"]
    return 100 * kc.count("LIQ_SWEEP") / len(kc)

nen_nn = nen_tu_gia(2000 + np.cumsum(np.random.default_rng(1).normal(0, 0.5, 15850 * 240)), so_tick_moi_nen=240)
dong = []
for W in (0, 1, 3, 6):
    that = ty_le_sweep(chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01", tham_so={"sweep_window": W}))
    nn = ty_le_sweep(chay_tren_df("ict_structure", nen_nn, tham_so={"sweep_window": W}))
    dong.append((W, that, nn, that - nn))
print(pd.DataFrame(dong, columns=["W (nến)", "% sweep thật", "% sweep bước ngẫu nhiên", "chênh (điểm %)"]).round(1).to_string(index=False))
```

```text
Kết quả khi mình chạy:
 W (nến)  % sweep thật  % sweep bước ngẫu nhiên  chênh (điểm %)
       0          41.3                     36.7             4.6
       1          59.4                     56.3             3.1
       3          70.7                     68.9             1.8
       6          77.3                     76.5             0.8
```

W kéo tỷ lệ từ 41% lên 77%; chênh thật / ngẫu nhiên chỉ 1–5 điểm %, lớn nhất ở W = 0 (quay lại ngay trong nến lấy) — hợp
với chuyện nến thật râu dài hơn.
</details>

**Bài 4 — Zigzag vẽ lại.** Với zigzag 0,25% ở mục 4, cắt dữ liệu 01–02/2024 ở mỗi 10 nến. (a) Điểm cuối mà chart vẽ ở t
(chân đang chạy) có phải là một điểm zigzag hậu kiểm không? (b) Nếu chỉ giữ các điểm đã biết ở t, có khớp với «chạy trọn rồi
cắt theo nến biết» không?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def zigzag(c, theta):                                              # như mục 4
    out, huong, cuc = [], 0, 0
    for i in range(1, len(c)):
        if huong == 0 and abs(c[i] / c[0] - 1) >= theta:
            huong, cuc = (1 if c[i] > c[0] else -1), i
        elif huong == 1 and c[i] > c[cuc] or huong == -1 and c[i] < c[cuc]:
            cuc = i
        elif huong != 0 and huong * (c[cuc] - c[i]) >= theta * c[cuc]:
            out.append((cuc, "H" if huong == 1 else "L", i)); huong, cuc = -huong, i
    return out, cuc

c = nap_nen(XAU_M15, "2024-01-01", "2024-03-01")["close"].to_numpy()
tron, _ = zigzag(c, 0.0025)
diem_tron = {e for e, _, k in tron}                                # mọi điểm zigzag hậu kiểm
cat = range(200, len(c), 10)
ve_sai = giu_dung = 0
for t in cat:
    piv, chan_cuoi = zigzag(c[: t + 1], 0.0025)
    ve_sai += chan_cuoi not in diem_tron                           # (a) điểm cuối chart vẽ ở t
    giu_dung += piv == [p for p in tron if p[2] <= t]              # (b) chỉ điểm đã biết ở t
print("(a) điểm cuối zigzag vẽ ở t KHÔNG phải điểm hậu kiểm: %d/%d lần (%.0f%%)" % (ve_sai, len(cat), 100 * ve_sai / len(cat)))
print("(b) chỉ giữ điểm đã biết: khớp «chạy trọn rồi cắt» %d/%d lần" % (giu_dung, len(cat)))
```

```text
Kết quả khi mình chạy:
(a) điểm cuối zigzag vẽ ở t KHÔNG phải điểm hậu kiểm: 239/373 lần (64%)
(b) chỉ giữ điểm đã biết: khớp «chạy trọn rồi cắt» 373/373 lần
```

Ở 64% điểm cắt, điểm cuối zigzag vẽ ra về sau biến mất hoặc dời đi (vẽ lại). Chỉ giữ điểm đã biết thì khớp 100%. Lỗi không
nằm ở zigzag mà ở cách gắn thời gian.
</details>

**Bài 5 — 70,7% có khác bước ngẫu nhiên không?** Chạy null 240 tick với 6 hạt giống, tính trung bình và độ lệch chuẩn của %
sweep. Đặt 70,7% của dữ liệu thật cạnh đó. Vì sao không nên dùng sai số chuẩn nhị thức một mình?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def ty_le_sweep(kq):
    kc = [l[:9] for l, d in zip(kq["su_kien"].structure_type, kq["su_kien"].details)
          if l[:9] in ("LIQ_SWEEP", "LIQ_RUN_U", "LIQ_RUN_D") for p in d["pools"] if p["tang"] == "M15"]
    return kc.count("LIQ_SWEEP") / len(kc), len(kc)

p, n = ty_le_sweep(chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01"))
print("thật: %.1f%% (n = %d vùng, sai số chuẩn nhị thức %.1f điểm %%)" % (100 * p, n, 100 * np.sqrt(p * (1 - p) / n)))
null = np.array([100 * ty_le_sweep(chay_tren_df("ict_structure", nen_tu_gia(
    2000 + np.cumsum(np.random.default_rng(seed).normal(0, 0.5, 15850 * 240)), so_tick_moi_nen=240)))[0]
    for seed in range(10, 16)])
print("bước ngẫu nhiên (6 hạt giống):", np.round(null, 1).tolist())
print("trung bình %.1f%%, độ lệch chuẩn giữa các hạt giống %.1f điểm %% → thật cách %.1f độ lệch chuẩn" % (
    null.mean(), null.std(ddof=1), (100 * p - null.mean()) / null.std(ddof=1)))
```

```text
Kết quả khi mình chạy:
thật: 70.7% (n = 1575 vùng, sai số chuẩn nhị thức 1.1 điểm %)
bước ngẫu nhiên (6 hạt giống): [69.5, 68.0, 70.2, 70.5, 70.3, 66.7]
trung bình 69.2%, độ lệch chuẩn giữa các hạt giống 1.5 điểm % → thật cách 1.0 độ lệch chuẩn
```

Cách khoảng 1 độ lệch chuẩn: không phân biệt được. Sai số chuẩn nhị thức (1,1 điểm %) coi các vùng độc lập (thật ra chung
đỉnh, chung đợt biến động) và bỏ qua dao động giữa các chuỗi null; độ lệch giữa các hạt giống (1,5 điểm %) mới là thước đúng.
</details>

## Tự kiểm

1. STH strict 1/1 ở nến c được biết ở nến nào? Nếu `pivot_right` = 3 thì sao?
   <details><summary>Đáp án</summary>

Ở c+1 (trễ 1 nến). Với R = 3 thì ở c+3: trễ luôn bằng R.

</details>

2. Vì sao trễ của ITH không bao giờ dưới 3 nến?
   <details><summary>Đáp án</summary>

Nến c+1 thấp hơn c nên không là STH. STH bên phải sớm nhất ở c+2 và chỉ được biết khi c+3 đóng.

</details>

3. Một người khoe chiến lược «đoán đúng 94% hướng 2 giờ tới» dựa trên zigzag. Câu đầu tiên bạn hỏi là gì?
   <details><summary>Đáp án</summary>

Điểm zigzag được gắn ở nến nào: nến cực trị hay nến biết (lúc giá đã quay đầu θ)? Gắn ở nến cực trị là nhìn tương lai; gắn ở nến biết thì tỷ lệ về khoảng mức đối chứng (mục 4).

</details>

4. Bạn đếm sự kiện của `ict_structure` «tới nến t» bằng `event_bar_index <= t`. Sai ở đâu?
   <details><summary>Đáp án</summary>

Phải lọc theo `confirmed_bar_index <= t`. Lọc theo nến sự kiện là kéo vào những sự kiện ở t chưa biết (STH chờ nến sau, run chờ hết W nến…).

</details>

5. Vì sao «70,7% vùng bị lấy là sweep» không chứng minh được thị trường hay quét rồi đảo chiều?
   <details><summary>Đáp án</summary>

Cùng luật đó trên bước ngẫu nhiên đã cho 67–70%, và tỷ lệ phụ thuộc chủ yếu vào W. Một tỷ lệ chỉ có nghĩa khi đặt cạnh null.

</details>

6. Null bước ngẫu nhiên 15 tick / nến cho khoảng 65% sweep, 240 tick / nến cho khoảng 68%. Vì sao số tick lại đổi kết quả?
   <details><summary>Đáp án</summary>

Số tick quyết định hình nến: ít tick thì râu ngắn so với thân, ít lần «xuyên rồi đóng lại ngay trong nến». Null phải giống dữ liệu thật ở những thứ không thuộc giả thuyết.

</details>

7. Trắc nghiệm: phép thử nào bắt được bộ pivot viết bằng `rolling(11, center=True)`? (a) chạy hai lần ra cùng kết quả; (b) phép thử tiền tố / sửa tương lai; (c) đếm số pivot mỗi ngày.
   <details><summary>Đáp án</summary>

(b). Chạy lại ra cùng kết quả chỉ chứng tỏ tất định; đếm mật độ không phân biệt được trước / sau.

</details>

## Đọc thêm

- David Aronson, *Evidence-Based Technical Analysis*: phần về luật khách quan (objective rules) so với phân tích chủ quan, và
  về sai lệch do đào dữ liệu. Đây là nền của «định nghĩa vận hành».
- Directional change: Guillaume và cộng sự (1997), «From the bird's eye to the microscope», *Finance and Stochastics*;
  Glattfelder, Dupuis, Olsen (2011), «Patterns in high-frequency FX data», *Quantitative Finance*.
- Marcos López de Prado, *Advances in Financial Machine Learning*: chủ đề gán nhãn và rò rỉ thông tin từ tương lai.
- Tài liệu lab: [thuat_toan_ict_structure.md](../algorithms/thuat_toan_ict_structure.md) §4.3–4.10, §5, §6, §8;
  [thuat_toan_dc_atr_structure.md](../algorithms/thuat_toan_dc_atr_structure.md) §4, §8;
  [kien_truc_luong_ict.md](../guides/kien_truc_luong_ict.md); [AGENTS.md](../../AGENTS.md) §2.1, §7.1.
- Danh mục quant ([danh_muc_phuong_phap_quant.md](../research/danh_muc_phuong_phap_quant.md)): R5-01 (directional change),
  R5-02 (luật tỷ lệ DC), R5-04 (zigzag, chỉ làm nhãn hậu kiểm), R5-06 (pivot n nến / fractal), R5-18 (mẫu nến kiểm bằng null),
  R7-22 (null mô phỏng).
