# Module 3 — Bước ngẫu nhiên và null

> **Sau module này bạn làm được:**
> - Mô phỏng một bước ngẫu nhiên có độ biến động cỡ XAUUSD M15, dựng nến từ nó và chạy `ict_structure` lên đó.
> - Đọc bảng «thật vs ngẫu nhiên» và chỉ ra con số nào của lab là tính chất của nhiễu, con số nào khác nhiễu và khác bao nhiêu.
> - Tính xác suất giá chạm vùng trên trước vùng dưới khi không có thông tin gì (gambler's ruin), và dùng nó làm mốc cho mọi tỷ lệ «đúng».
> - Chọn null hợp với câu hỏi: xáo từng nến, xáo theo ngày, đổi dấu, cùng giờ × tầng ATR; giải thích vì sao null yếu làm thuật toán trông giỏi.
>
> **Cần trước:** module 1, 2  ·  **Thời lượng:** ~6 giờ

> **Ba điều cần nhớ** (đọc lại khi ôn)
>
> 1. Chạy `ict_structure` trên bước ngẫu nhiên vẫn ra gần bằng số đỉnh/đáy, sweep, shift, displacement như vàng thật: đếm được cấu trúc không chứng minh gì.
> 2. Câu hỏi đúng là khác nhiễu bao nhiêu: vàng ít FVG hơn khoảng 40% và tỷ lệ sweep 72,8% so với 66–67%, vì nến vàng nhiều râu hơn.
> 3. Mốc ngẫu nhiên: P(chạm mức trên trước) = d_dưới / (d_trên + d_dưới). Null phải giữ biến động (xáo theo ngày); null xáo từng nến quá dễ thắng.

## Vì sao cần

Bạn nhìn chart và thấy sweep, shift, FVG ở khắp nơi. Câu hỏi của module này: **nếu giá chỉ là tung đồng xu, thuật toán của lab
có còn thấy những thứ đó không?** Câu trả lời ở mục 2 là có, và nhiều gần bằng trên giá thật. Vì vậy đếm được bao nhiêu sweep
chưa nói lên gì. Câu hỏi đúng là sweep **khác nhiễu bao nhiêu**. Lab đã trả lời câu hỏi đó cho order flow: 7 cách đọc, hơn 100 nghìn
lần lật, và không cách nào đoán phía thanh khoản bị lấy kế tiếp tốt hơn mốc ngẫu nhiên quá ±2 điểm %
([`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) §1). Mốc ngẫu nhiên đó là một công thức bạn sẽ tự kiểm ở
mục 3. Danh mục phương pháp quant cũng kết luận: «nhiều quy luật cấu trúc là tính chất của bước ngẫu nhiên», nên mọi thống kê swing
/ sweep / shift phải đặt cạnh cùng thống kê đó trên dữ liệu mô phỏng ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md) §3).

## 1. Bước ngẫu nhiên và «không có nhớ»

**Trực giác.** Mỗi 15 phút bạn tung một đồng xu: ngửa thì giá lên một chút, sấp thì xuống một chút, độ lớn mỗi lần cũng ngẫu
nhiên. Đồng xu không nhớ lần trước ra gì. Đó là bước ngẫu nhiên.

**Định nghĩa.** Gọi $p_t = \ln(\text{giá}_t)$ là log giá sau nến $t$. **Bước ngẫu nhiên (random walk)**:

$$p_t = p_{t-1} + \varepsilon_t, \qquad \varepsilon_t \text{ độc lập, trung bình } 0, \text{ độ lệch chuẩn } \sigma$$

Bằng lời: log giá nến này bằng log giá nến trước cộng một cú xóc ngẫu nhiên; cú xóc không phụ thuộc vào mọi cú xóc trước. Hệ quả
quan trọng nhất là **không có nhớ (martingale)**: dự báo tốt nhất cho giá nến sau là giá hiện tại,
$\mathbb{E}[p_{t+1} \mid \text{mọi giá đã biết}] = p_t$. Quá khứ không cho biết hướng tiếp theo. Giả thuyết **thị trường hiệu quả
dạng yếu (weak-form efficiency)** nói gần như vậy về thị trường thật: chỉ dùng giá quá khứ thì không kiếm được lợi nhuận vượt trội
sau chi phí. Đó là giả thuyết để kiểm, không phải định luật.

Lấy $\sigma$ từ vàng thật rồi so một chuỗi mô phỏng với vàng:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# 1) Lợi suất log M15 thật, chỉ giữa hai nến liền nhau (bỏ bước nhảy qua giờ nghỉ / cuối tuần)
df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r_that = np.log(df.close).diff()[df.index.to_series().diff() == pd.Timedelta("15min")].to_numpy()
sigma = r_that.std()
print("Số lợi suất M15: %d · độ lệch chuẩn mỗi nến: %.5f (%.3f%%) · ≈ %.2f USD ở giá 2300"
      % (len(r_that), sigma, 100 * sigma, 2300 * sigma))

# 2) Bước ngẫu nhiên cùng số bước, cùng sigma: r = sigma * nhiễu chuẩn, không phụ thuộc gì vào quá khứ
rng = np.random.default_rng(7)
r_mp = rng.normal(0, sigma, len(r_that))

def mo_ta(r):
    len_truoc = r[:-1] > 0
    return {
        "TB (×1e-5)": round(r.mean() * 1e5, 2),
        "độ lệch chuẩn (%)": round(r.std() * 100, 4),
        "kurtosis thừa": round(pd.Series(r).kurt(), 1),
        "|r| > 4σ (‰)": round(1000 * np.mean(np.abs(r) > 4 * sigma), 2),
        "P(lên | nến trước lên)": round(np.mean(r[1:][len_truoc] > 0), 3),
        "P(lên | nến trước xuống)": round(np.mean(r[1:][~len_truoc] > 0), 3),
    }

print(pd.DataFrame({"XAUUSD M15 thật": mo_ta(r_that), "bước ngẫu nhiên": mo_ta(r_mp)}).to_string())
```

```text
Kết quả khi mình chạy:
Số lợi suất M15: 15677 · độ lệch chuẩn mỗi nến: 0.00094 (0.094%) · ≈ 2.16 USD ở giá 2300
                          XAUUSD M15 thật  bước ngẫu nhiên
TB (×1e-5)                          0.910          -0.4900
độ lệch chuẩn (%)                   0.094           0.0936
kurtosis thừa                      13.400           0.0000
|r| > 4σ (‰)                        7.780           0.0600
P(lên | nến trước lên)              0.489           0.4980
P(lên | nến trước xuống)            0.528           0.4980
```

Đọc kết quả:

- Cùng độ lệch chuẩn, nhưng vàng có **đuôi dày** (module 2): cú xóc > 4σ xảy ra 7.8 lần trên nghìn nến, bước ngẫu nhiên chuẩn chỉ
  0.06. Bước ngẫu nhiên Gauss thiếu những cú nến tin tức.
- Sau một nến tăng, nến kế tiếp tăng 48.9%; sau một nến giảm thì 52.8%. Vàng M15 hơi «quay đầu» sau mỗi nến. Đây là một lệch nhỏ
  khỏi bước ngẫu nhiên (tự tương quan bậc 1 ≈ −0.02, đo kỹ ở module 4). Tính ra tiền thì kỳ vọng chỉ cỡ 2 cent mỗi nến
  (−0.016 × ~1.4 USD, mức đi trung bình của một nến), nhỏ hơn chi phí giao dịch. Nó không phải lợi thế (module 8).

**Bẫy hay gặp.**
- Mô phỏng trên **giá** thay vì **log giá**: chuỗi dài có thể ra giá âm, và cú xóc không tỷ lệ với mức giá.
- Hiểu «ngẫu nhiên» là «không có xu hướng nhìn thấy được». Sai, xem mục 2.
- Coi bước ngẫu nhiên là mô hình đúng của thị trường. Không phải: giá thật có đuôi dày, biến động co cụm, mùa vụ trong ngày
  (module 4). Bước ngẫu nhiên là **null** (giả thuyết không): điểm so «nếu không có gì đặc biệt thì trông thế nào».

## 2. Mẫu hình trong nhiễu

### 2.1. Xu hướng mọc ra từ nhiễu

**Trực giác.** Tung đồng xu 15 850 lần (bằng số nến M15 của 8 tháng 2024) và vẽ đường tích luỹ. Bạn nghĩ đường đó sẽ lượn quanh
mức xuất phát. Thực tế phần lớn đường đi hẳn về một phía và ở đó rất lâu. Một trader nhìn vào sẽ gọi là «trend».

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# 2000 «năm 2024» giả: mỗi đường 15 850 nến M15, sigma 0.094% mỗi nến, KHÔNG có xu hướng
rng = np.random.default_rng(11)
n_duong, n_nen, sigma = 2000, 15850, 0.00094
ty_le_tren, bien_dong, max_tang, max_giam = [], [], [], []
for _ in range(n_duong):
    logp = np.cumsum(rng.normal(0, sigma, n_nen))        # log giá so với giá đầu
    ty_le_tren.append(np.mean(logp > 0))                 # phần thời gian nằm TRÊN giá mở đầu
    bien_dong.append(logp[-1])
    max_tang.append(np.max(logp - np.minimum.accumulate(logp)))   # cú tăng lớn nhất từ một đáy
    max_giam.append(np.max(np.maximum.accumulate(logp) - logp))   # cú giảm lớn nhất từ một đỉnh
ty_le_tren = np.array(ty_le_tren); bien_dong = np.array(bien_dong) * 100

print("Thay đổi cả kỳ (%%): trung vị |thay đổi| = %.1f, 10%% số đường đi xa hơn ±%.1f"
      % (np.median(np.abs(bien_dong)), np.quantile(np.abs(bien_dong), 0.9)))
print("Cú tăng lớn nhất từ đáy (%%): trung vị %.1f · cú giảm lớn nhất từ đỉnh: trung vị %.1f"
      % (100 * np.median(max_tang), 100 * np.median(max_giam)))
print("Phần thời gian nằm trên giá mở đầu:")
for a, b in [(0, .1), (.1, .3), (.3, .7), (.7, .9), (.9, 1.01)]:
    print("  %3.0f%%–%3.0f%%: %5.1f%% số đường" % (100 * a, min(100, 100 * b), 100 * np.mean((ty_le_tren >= a) & (ty_le_tren < b))))
print("Luật arcsin dự đoán cho hai đuôi (<10%% hoặc >90%%): %.1f%%" % (100 * 4 / np.pi * np.arcsin(np.sqrt(0.1))))

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
thay_doi = 100 * np.log(df.close.iloc[-1] / df.open.iloc[0])
print("XAUUSD thật 01–08/2024: %.1f%% (log) · số đường ngẫu nhiên đi xa hơn thế: %.1f%%"
      % (thay_doi, 100 * np.mean(np.abs(bien_dong) >= abs(thay_doi))))
```

```text
Kết quả khi mình chạy:
Thay đổi cả kỳ (%): trung vị |thay đổi| = 7.7, 10% số đường đi xa hơn ±19.1
Cú tăng lớn nhất từ đáy (%): trung vị 13.4 · cú giảm lớn nhất từ đỉnh: trung vị 13.5
Phần thời gian nằm trên giá mở đầu:
    0%– 10%:  21.3% số đường
   10%– 30%:  15.8% số đường
   30%– 70%:  28.1% số đường
   70%– 90%:  16.1% số đường
   90%–100%:  18.7% số đường
Luật arcsin dự đoán cho hai đuôi (<10% hoặc >90%): 41.0%
XAUUSD thật 01–08/2024: 19.3% (log) · số đường ngẫu nhiên đi xa hơn thế: 9.6%
```

40% số đường nhiễu nằm về một phía của giá mở đầu hơn 90% thời gian (luật **arcsin** dự đoán 41%). Chỉ 28% đường «lượn quanh»
mức xuất phát. Mỗi đường còn có một cú tăng và một cú giảm cỡ 13%. Vàng tăng 19.3% trong 8 tháng là mạnh, nhưng cứ 10 đường nhiễu
thì 1 đường đi xa như thế. Một kỳ tăng như vậy không đủ để nói thị trường «có xu hướng» theo nghĩa thống kê.

### 2.2. Chạy thuật toán của lab trên nhiễu

Đây là phép thử trung tâm của cả bộ tài liệu. Hai hàm trợ giúp:

- `nen_tu_gia(gia, so_tick_moi_nen=15)` gom mỗi 15 giá liên tiếp thành một nến: open là giá đầu, high / low là cực trị, close là
  giá cuối. 15 «tick» một nến ≈ một tick mỗi phút.
- `chay_tren_df("ict_structure", df)` chạy đúng mã của lab trên nến bạn tạo. Lịch phiên đặt `none` vì chuỗi mô phỏng chạy liên
  tục, không có giờ nghỉ.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def dem(kq):
    """Tóm tắt một lần chạy ict_structure thành vài con số dễ so."""
    loai = kq["su_kien"]["structure_type"].value_counts()
    n = lambda *ten: int(sum(loai.get(t, 0) for t in ten))
    cs = kq["ket_qua"].stats["chi_so_thuat_toan"]
    sweep, run = n("LIQ_SWEEP_BSL", "LIQ_SWEEP_SSL"), n("LIQ_RUN_UP", "LIQ_RUN_DOWN")
    fvg, shift = n("FVG_UP", "FVG_DOWN"), n("SHIFT_UP", "SHIFT_DOWN")
    return {
        "STH + STL": n("SWING_HIGH", "SWING_LOW"),
        "ITH + ITL": n("SWING_HIGH_L2", "SWING_LOW_L2"),
        "displacement (% nến)": round(100 * n("DISPLACEMENT_UP", "DISPLACEMENT_DOWN") / len(kq["nen"]), 2),
        "FVG": fvg,
        "FVG bị lấp (%)": round(100 * n("FVG_FILLED") / fvg, 1),
        "sweep": sweep,
        "run": run,
        "sweep / (sweep + run) %": round(100 * sweep / (sweep + run), 1),
        "shift": shift,
        "shift có FVG (%)": round(100 * n("SHIFT_FVG_UP", "SHIFT_FVG_DOWN") / shift, 1),
        "order flow đổi trạng thái": n("ORDER_FLOW_UP", "ORDER_FLOW_DOWN", "ORDER_FLOW_UNCLEAR"),
        "order flow chưa rõ (% tg)": round(100 * cs["order_flow"]["ty_le_thoi_gian"]["chua_ro"], 1),
        "thứ tự lẫn lộn (% tg)": round(100 * cs["ty_le_thoi_gian_order"]["0"], 1),
        "thân / biên độ nến (trung vị)": round(float(np.median(
            [abs(b.close - b.open) / (b.high - b.low) for b in kq["nen"] if b.high > b.low])), 2),
    }

# Dữ liệu thật: XAUUSD M15 01–08/2024
that = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")
df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()[df.index.to_series().diff() == pd.Timedelta("15min")]
sigma, n_nen, k = r.std(), len(df), 15
bang = {"thật": dem(that)}

# Ba bước ngẫu nhiên: cùng số nến, cùng sigma mỗi nến; mỗi nến gom 15 «tick» (≈ 1 phút một tick)
for seed in (1, 2, 3):
    rng = np.random.default_rng(seed)
    gia = 2300 * np.exp(np.cumsum(rng.normal(0, sigma / np.sqrt(k), n_nen * k)))
    bang["ngẫu nhiên %d" % seed] = dem(chay_tren_df("ict_structure", nen_tu_gia(gia, so_tick_moi_nen=k)))

pd.set_option("display.width", 160)
print("Số nến mỗi chuỗi:", n_nen)
print(pd.DataFrame(bang).round(2).to_string())
```

```text
Kết quả khi mình chạy (~20 giây):
Số nến mỗi chuỗi: 15850
                                  thật  ngẫu nhiên 1  ngẫu nhiên 2  ngẫu nhiên 3
STH + STL                      6991.00       7002.00       6867.00       7006.00
ITH + ITL                      1768.00       1742.00       1725.00       1719.00
displacement (% nến)              7.36          7.40          7.81          7.43
FVG                            3139.00       5197.00       5312.00       5220.00
FVG bị lấp (%)                   97.40         97.90         97.90         98.90
sweep                           970.00        962.00        929.00        975.00
run                             363.00        479.00        486.00        478.00
sweep / (sweep + run) %          72.80         66.80         65.70         67.10
shift                           152.00        134.00        160.00        145.00
shift có FVG (%)                 55.30         77.60         76.20         73.80
order flow đổi trạng thái       292.00        334.00        306.00        351.00
order flow chưa rõ (% tg)        23.90         20.50         17.80         19.60
thứ tự lẫn lộn (% tg)            47.70         43.20         41.90         41.50
thân / biên độ nến (trung vị)     0.46          0.58          0.58          0.57
```

Đọc bảng thành hai nhóm.

**Giống nhiễu (nằm trong dải ba chuỗi ngẫu nhiên hoặc sát nó):** số đỉnh/đáy 3 nến (~22% số nến mỗi phía), số ITH/ITL, tỷ lệ
displacement (~7.4%), số sweep, số shift (~150 trong 8 tháng), tỷ lệ FVG bị lấp (~98%). Một đường tung đồng xu cũng sinh ra
chừng ấy «cấu trúc». Ví dụ: «FVG gần như luôn được lấp» đúng cả trên nhiễu, nên nó không phải bằng chứng FVG «hút giá» (một mô phỏng
tương tự ở [`nghien_cuu_bias_regime.md`](../research/nghien_cuu_bias_regime.md) §3.3 cho 83.4% so với 83.5% của mức ngẫu nhiên).
Vì sao giống: mọi ngưỡng của `ict_structure` tính theo ATR. Thuật toán đo giá **so với chính biến động của nó**, nên mức biến động
không quan trọng (bài tập 1). Pivot, sweep, displacement chỉ cần giá dao động. Nhiễu nào cũng dao động.

**Khác nhiễu:** vàng có ít FVG hơn ~40% (3 139 so với ~5 200), ít run hơn, tỷ lệ sweep cao hơn ~6 điểm % (72.8 so với 66–67),
shift ít kèm FVG hơn (55% so với 74–78%), «chưa rõ» nhiều hơn vài điểm %. Dòng cuối gợi ý vì sao: nến vàng **nhiều râu hơn**.
Thân chỉ chiếm 46% biên độ, nến ngẫu nhiên chiếm 58%. Râu dài làm nến chồng lên nhau, nên khó có khoảng trống 3 nến (ít FVG). Râu
cũng hay xuyên mức rồi close quay lại, tức là sweep thay vì run. Mục 5 tách xem phần khác biệt nào đến từ hình dạng nến và phần nào
đến từ thứ tự các nến.

Bài học: câu hỏi «thuật toán có thấy sweep không?» vô nghĩa. Câu hỏi đúng là «thấy nhiều hơn hay ít hơn nhiễu bao nhiêu, khác biệt đó
lớn hơn dao động giữa các chuỗi nhiễu không, và do tính chất gì gây ra». Ở đây khác biệt có thật (vượt dải ba chuỗi). Mục 5 sẽ cho
thấy nó đến từ hình dạng nến và từ quan hệ giữa các nến liền nhau trong ngày. Chưa có gì cho thấy nó giúp biết giá sẽ đi đâu.

**Bẫy hay gặp.**
- So với **một** chuỗi ngẫu nhiên. Phải chạy vài hạt giống để thấy dải dao động: shift dao động 134–160 chỉ vì đổi hạt giống.
- So số tuyệt đối khi số nến khác nhau. Giữ cùng số nến, hoặc quy về mỗi 100 nến / mỗi ngày.
- Dữ liệu thật có 172 khoảng trống (giờ nghỉ, cuối tuần) chặn cửa sổ pivot / FVG / sweep. Chuỗi mô phỏng chạy liền. Mục 5 có cột
  «thật nối liền» để kiểm phần chênh này: nó nhỏ.
- Dataset `[MÔ PHỎNG]` trong database (sinh bởi [`core/data/synthetic.py`](../../core/data/synthetic.py)) có các giai đoạn trend /
  tích luỹ **cài sẵn** để thử giao diện. Nó không phải null.

## 3. Xác suất chạm biên (gambler's ruin) — mốc ngẫu nhiên của order flow

**Trực giác.** Vàng ở 2400. BSL gần nhất ở 2402, SSL gần nhất ở 2394. Không biết gì thêm thì phía nào bị lấy trước? Phía gần
hơn, vì giá chỉ cần đi 2 USD thay vì 6. Bao nhiêu phần trăm?

**Định nghĩa.** Với bước ngẫu nhiên không xu hướng, khoảng cách tới mức trên là $d_{\text{trên}}$ và tới mức dưới là
$d_{\text{dưới}}$:

$$P(\text{chạm trên trước}) = \frac{d_{\text{dưới}}}{d_{\text{trên}} + d_{\text{dưới}}}$$

Bằng lời: xác suất chạm phía trên bằng khoảng cách tới phía **dưới** chia cho tổng khoảng cách. Ví dụ trên: $6 / (2 + 6) = 75\%$.
Lý do: trò chơi công bằng thì kỳ vọng vị trí lúc dừng bằng vị trí xuất phát. Gọi $P$ là xác suất chạm trên trước thì
$P \cdot d_{\text{trên}} - (1-P) \cdot d_{\text{dưới}} = 0$, giải ra công thức. Đây là bài toán **gambler's ruin** (con bạc
cháy túi): một con bạc có $d_{\text{dưới}}$ đồng chơi tới khi thắng thêm $d_{\text{trên}}$ đồng hoặc mất sạch.

Kiểm bằng mô phỏng:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# Bước ngẫu nhiên xuất phát ở 0, dừng khi chạm +d_tren hoặc -d_duoi. Đếm tỷ lệ chạm TRÊN trước.
rng = np.random.default_rng(42)

def mo_phong(d_tren, d_duoi, n_duong=20000, buoc=0.1):
    x = np.zeros(n_duong)
    con = np.ones(n_duong, bool)            # đường còn chưa chạm biên nào
    tren = np.zeros(n_duong, bool)
    while con.any():
        x[con] += rng.normal(0, buoc, con.sum())
        cham_tren = con & (x >= d_tren)
        cham_duoi = con & (x <= -d_duoi)
        tren |= cham_tren
        con &= ~(cham_tren | cham_duoi)
    return tren.mean()

print("d_trên  d_dưới   công thức d_dưới/(d_trên+d_dưới)   mô phỏng")
for d_tren, d_duoi in [(1, 3), (1, 1), (2, 1), (3, 1), (1, 9)]:
    print("%5.0f %7.0f %20.3f %22.3f" % (d_tren, d_duoi, d_duoi / (d_tren + d_duoi), mo_phong(d_tren, d_duoi)))
```

```text
Kết quả khi mình chạy:
d_trên  d_dưới   công thức d_dưới/(d_trên+d_dưới)   mô phỏng
    1       3                0.750                  0.748
    1       1                0.500                  0.495
    2       1                0.333                  0.338
    3       1                0.250                  0.253
    1       9                0.900                  0.898
```

Trên giá thật thì sao? Lấy vùng BSL / SSL còn nguyên gần nhất mà lab theo dõi sau mỗi nến (cột `liq_above`, `liq_below` của
timeline). Cứ 8 nến lấy một mẫu, tính mốc theo công thức, rồi nhìn tương lai xem vùng nào bị **lấy** trước (xuyên ≥ 0.1 ATR, đúng
định nghĩa của lab). Cách làm này giống phần «kiểm thước đo» của nghiên cứu order flow (§4). Vùng ở đây gồm cả tầng H1 / H4 / D / W
của `ict_structure` 0.4.0, còn nghiên cứu dùng vùng M15 của 0.2.0, nên số không trùng từng ô.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def kiem_moc(dataset, tu, den):
    """Tại mỗi 8 nến: mốc = d_dưới/(d_trên+d_dưới) tới vùng BSL/SSL còn nguyên gần nhất; thực tế = vùng trên bị lấy trước?"""
    kq = chay_thuat_toan("ict_structure", dataset, tu, den)
    tl, nen = kq["timeline"], kq["nen"]
    hi = np.array([b.high for b in nen]); lo = np.array([b.low for b in nen]); cl = np.array([b.close for b in nen])
    dong = []
    for t in range(200, len(nen) - 1, 8):                    # bỏ 200 nến khởi động
        tren, duoi, atr = tl.at[t, "liq_above"], tl.at[t, "liq_below"], tl.at[t, "atr"]
        if pd.isna(tren) or pd.isna(duoi) or pd.isna(atr):
            continue
        muc_tren, muc_duoi = tren + 0.1 * atr, duoi - 0.1 * atr   # «lấy» = xuyên ≥ 0.1 ATR như lab
        i_tren = np.flatnonzero(hi[t + 1:] >= muc_tren)
        i_duoi = np.flatnonzero(lo[t + 1:] <= muc_duoi)
        a = i_tren[0] if len(i_tren) else 10**9
        b = i_duoi[0] if len(i_duoi) else 10**9
        if a == b:                                            # cùng một nến, hoặc tới cuối vẫn chưa rõ → bỏ
            continue
        d_tren, d_duoi = muc_tren - cl[t], cl[t] - muc_duoi
        dong.append((d_duoi / (d_tren + d_duoi), a < b))
    m = pd.DataFrame(dong, columns=["moc", "tren_truoc"])
    m["nhom"] = pd.cut(m.moc, [0, .2, .4, .6, .8, 1])
    return m

for ten, ds, tu, den in [("XAUUSD M15 2021–2023", XAU_M15_DAI, "2021-01-01", "2024-01-01"),
                         ("XAUUSD M15 01–08/2024", XAU_M15, "2024-01-01", "2024-09-01")]:
    m = kiem_moc(ds, tu, den)
    bang = m.groupby("nhom", observed=True).agg(so_mau=("moc", "size"), moc_TB=("moc", "mean"),
                                                 thuc_te=("tren_truoc", "mean"))
    print("==", ten, "· %d mẫu · mốc TB %.3f · thực tế %.3f" % (len(m), m.moc.mean(), m.tren_truoc.mean()))
    print(bang.round(3).to_string())
```

```text
Kết quả khi mình chạy (~25 giây):
== XAUUSD M15 2021–2023 · 8740 mẫu · mốc TB 0.506 · thực tế 0.503
            so_mau  moc_TB  thuc_te
nhom
(0.0, 0.2]     940   0.132    0.131
(0.2, 0.4]    2167   0.304    0.315
(0.4, 0.6]    2388   0.502    0.486
(0.6, 0.8]    2207   0.697    0.681
(0.8, 1.0]    1038   0.871    0.898
== XAUUSD M15 01–08/2024 · 1885 mẫu · mốc TB 0.518 · thực tế 0.560
            so_mau  moc_TB  thuc_te
nhom
(0.0, 0.2]     197   0.134    0.203
(0.2, 0.4]     436   0.303    0.337
(0.4, 0.6]     512   0.503    0.576
(0.6, 0.8]     479   0.696    0.716
(0.8, 1.0]     261   0.868    0.885
```

Năm 2021–2023, công thức một dòng đoán đúng tỷ lệ thực tế trong từng nhóm, lệch không quá 3 điểm %. Giá vàng thật, ở thang vùng thanh
khoản M15, chạm biên gần như một bước ngẫu nhiên. Năm 2024 phía trên bị lấy trước nhiều hơn mốc ~4 điểm %: vàng tăng 19% trong 8
tháng, tức có **xu hướng (drift)**. Vì vậy nghiên cứu order flow báo thêm **lợi thế cân bằng chiều**: trung bình lợi thế của lật
tăng và lật giảm. Drift cộng cho chiều này bao nhiêu thì trừ chiều kia bấy nhiêu, nên trung bình hai chiều triệt tiêu drift.

**Nối với order flow của lab.** Nghiên cứu đo: tại lúc order flow lật sang tăng, vùng phía trên có bị lấy trước không.
**Lợi thế = tỷ lệ trúng − mốc.** Giả sử một cách đọc «đúng 70%». Nghe hay, nhưng nếu lúc lật BSL thường cách 1 ATR còn SSL cách
3 ATR thì mốc là 75%, và «70%» **kém** tung đồng xu 5 điểm. Mọi cách đọc lab đã thử đều cho lợi thế trong ±2 điểm % ở mẫu lớn. Cùng
bẫy này có trong tài liệu: bài nowcast directional change của Tsang (2024) báo 66.6% «đúng», còn xác suất gambler's ruin dưới bước
ngẫu nhiên cho đúng tình huống đó là ≈ 68% (danh mục tự tính, mục R5-03).

**Bẫy hay gặp.**
- Báo tỷ lệ «đúng» mà không có mốc. Mọi tỷ lệ chạm mức đều phải trừ $d_{\text{dưới}}/(d_{\text{trên}}+d_{\text{dưới}})$.
- Quên drift. Vùng càng xa thì giá càng mất lâu mới chạm, và drift càng có thời gian cộng dồn (bài tập 2). Đó là lý do với vùng
  D1, lợi thế tách theo chiều lệch ±15 điểm % theo xu hướng dài hạn (nghiên cứu order flow §5.4).
- Mẫu chồng nhau. Mẫu cách 8 nến vẫn có thể cùng chờ một cặp vùng, nên không độc lập. Khoảng tin cậy phải bootstrap theo khối
  (tuần), như nghiên cứu đã làm.

## 4. Directional change trên bước ngẫu nhiên: overshoot ≈ θ

**Trực giác.** Thuật toán `dc_atr_structure` của lab xác nhận đảo chiều khi giá đi ngược một ngưỡng θ từ cực trị gần nhất. Sau
lúc xác nhận, giá thường đi tiếp thêm một đoạn rồi mới đảo chiều lần nữa. Đoạn đi tiếp đó dài bao nhiêu nếu giá là nhiễu?

**Định nghĩa.** **Directional change (DC)**: sự kiện giá rời cực trị gần nhất ít nhất θ. Điểm xác nhận gọi là **DCC**.
**Overshoot (OS)** là quãng giá đi tiếp từ DCC tới cực trị kế tiếp, trước lần DC sau. Với bước ngẫu nhiên liên tục,
$\mathbb{E}|OS| = \theta$. Một sóng trung bình vì thế dài $2\theta$ (θ để xác nhận + θ đi tiếp). Glattfelder và cộng sự (2011) thấy
tỷ số ≈ 1.04–1.06 trên tick 13 cặp FX, và nhấn mạnh rằng kết quả này cũng đúng với bước ngẫu nhiên Gauss (danh mục, mục R5-02).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def overshoot(x, theta):
    """Directional change trên log giá x, ngưỡng theta. Trả |overshoot| / theta của các sóng đã đóng."""
    huong, cuc_tri, dcc, os_ = 1, x[0], None, []
    for p in x[1:]:
        if huong * (p - cuc_tri) > 0:                  # đi tiếp theo hướng cũ → cực trị mới
            cuc_tri = p
        elif huong * (cuc_tri - p) >= theta:           # ngược lại ≥ theta từ cực trị → xác nhận đảo chiều (DCC)
            if dcc is not None:
                os_.append(abs(cuc_tri - dcc))         # sóng vừa đóng đã đi tiếp bao xa sau DCC của nó
            huong, cuc_tri, dcc = -huong, p, p
    return np.array(os_) / theta

def in_dong(ten, a):
    print("%-40s sóng %5d · TB %.2f · trung vị %.2f" % (ten, len(a), a.mean(), np.median(a)))

rng = np.random.default_rng(0)
in_dong("bước ngẫu nhiên mịn (θ = 20 bước)", overshoot(np.cumsum(rng.normal(0, 1, 2_000_000)), 20))

df = nap_nen(XAU_M15_DAI, "2018-01-01", "2024-01-01")
x = np.log(df.close.to_numpy())
sigma = np.diff(x).std()
for theta in (0.005, 0.01, 0.02):
    in_dong("XAUUSD M15 2018–2023, θ = %.1f%%" % (100 * theta), overshoot(x, theta))
    x_mp = np.cumsum(rng.normal(0, sigma, len(x)))      # bước ngẫu nhiên cùng sigma, cùng số nến
    in_dong("  ngẫu nhiên cùng số nến, θ = %.1f%%" % (100 * theta), overshoot(x_mp, theta))
```

```text
Kết quả khi mình chạy:
bước ngẫu nhiên mịn (θ = 20 bước)        sóng  4458 · TB 1.03 · trung vị 0.70
XAUUSD M15 2018–2023, θ = 0.5%           sóng  2414 · TB 1.18 · trung vị 0.67
  ngẫu nhiên cùng số nến, θ = 0.5%       sóng  3362 · TB 1.13 · trung vị 0.74
XAUUSD M15 2018–2023, θ = 1.0%           sóng   760 · TB 1.18 · trung vị 0.76
  ngẫu nhiên cùng số nến, θ = 1.0%       sóng  1006 · TB 1.04 · trung vị 0.67
XAUUSD M15 2018–2023, θ = 2.0%           sóng   229 · TB 1.12 · trung vị 0.75
  ngẫu nhiên cùng số nến, θ = 2.0%       sóng   282 · TB 1.01 · trung vị 0.66
```

Đọc kết quả:

- Bước ngẫu nhiên mịn: OS/θ trung bình 1.03, đúng lý thuyết. Trung vị chỉ 0.70 (gần $\ln 2 \approx 0.69$, vì OS có phân phối gần
  hàm mũ): nửa số sóng đi tiếp chưa tới 0.7θ, vài sóng rất dài kéo trung bình lên 1.
- Khi chỉ xét close M15, chuỗi ngẫu nhiên cho OS/θ 1.01–1.13. Lấy mẫu thô theo nến làm tỷ số nhích lên, nhất là khi θ nhỏ (0.5% chỉ
  khoảng 5 lần σ của một nến).
- Vàng thật: 1.12–1.18, nhỉnh hơn nhiễu một chút. Vàng cũng có ít sóng hơn dù cùng σ (2 414 so với 3 362 ở θ 0.5%). Một lý do có
  thể: phương sai của vàng dồn vào ít cú nhảy lớn (đuôi dày), mà một cú nhảy lớn chỉ tạo tối đa một sóng. Khác biệt 1.18 so với
  1.04 có ý nghĩa không? Câu trả lời đổi theo null bạn chọn. Bài tập 4 cho thấy chuyện đó.

**Bẫy hay gặp.** «Sau khi xác nhận đảo chiều, giá đi thêm khoảng θ» nghe như một quy luật. Thật ra đó là kỳ vọng của nhiễu. OS/θ
chỉ có thông tin khi **khác 1 một cách có ý nghĩa so với null**, và null phải có cùng cách lấy mẫu (close M15, không phải tick).

## 5. Null iid và null giữ biến động

**Trực giác.** Muốn biết «thứ tự các nến có quan trọng không», hãy xáo thứ tự rồi xem kết quả có đổi không. Xáo kiểu nào thì quyết
định bạn đang kiểm cái gì.

**Định nghĩa.** **Null** (giả thuyết không) ở đây là một cách tạo dữ liệu giả. Nó **giữ** những tính chất bạn không muốn kiểm và
**phá** đúng tính chất bạn đang kiểm. Bốn loại hay dùng:

| Null | Giữ | Phá |
|---|---|---|
| bước ngẫu nhiên Gauss (R7-22) | độ biến động trung bình | đuôi dày, co cụm, mùa vụ, hình dạng nến, mọi thứ tự |
| **xáo iid** (xáo từng lợi suất / từng nến) | phân phối lợi suất, hình dạng từng nến | mọi thứ tự: co cụm biến động, mùa vụ, tương quan giữa các nến |
| **xáo theo khối ngày** (R7-17) | mọi thứ **trong** một ngày: co cụm, mùa vụ, thứ tự nến | thứ tự **giữa** các ngày |
| **đổi dấu ngẫu nhiên** | toàn bộ chuỗi \|r\|: co cụm, mùa vụ, đuôi dày | hướng: mọi quan hệ giữa chiều nến này và chiều nến sau |

**Biến động co cụm (volatility clustering)**: nến lớn hay đi cạnh nến lớn (module 4). Đếm số cặp nến liền nhau cùng có |r| > 3σ:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()
r = r[df.index.to_series().diff() == pd.Timedelta("15min")]       # chỉ lợi suất giữa hai nến liền nhau
ngay = (r.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).date   # ngày giao dịch (mốc 17:00 NY)
r = r.to_numpy()
sigma = r.std()

def thong_ke(x):
    lon = np.abs(x) > 3 * sigma
    a = np.abs(x)
    return (np.sum(lon[1:] & lon[:-1]),                        # số cặp nến liền nhau cùng |r| > 3σ
            np.corrcoef(a[1:], a[:-1])[0, 1])                  # tương quan của |r| với |r| nến trước

rng = np.random.default_rng(2024)
cac_ngay = pd.unique(ngay)
vi_tri = {d: np.flatnonzero(ngay == d) for d in cac_ngay}
iid, khoi = [], []
for _ in range(500):
    iid.append(thong_ke(rng.permutation(r)))                                            # xáo từng lợi suất
    khoi.append(thong_ke(r[np.concatenate([vi_tri[d] for d in rng.permutation(cac_ngay)])]))  # xáo thứ tự NGÀY
iid, khoi = np.array(iid), np.array(khoi)

that = thong_ke(r)
print("Số nến có |r| > 3σ: %d / %d" % (np.sum(np.abs(r) > 3 * sigma), len(r)))
for j, ten in enumerate(["cặp liền nhau |r|>3σ", "tương quan |r| bậc 1"]):
    print("%-22s thật %7.3f | xáo từng nến TB %7.3f [P5 %6.3f, P95 %6.3f] | xáo theo ngày TB %7.3f [P5 %6.3f, P95 %6.3f]"
          % (ten, that[j], iid[:, j].mean(), *np.quantile(iid[:, j], [.05, .95]),
             khoi[:, j].mean(), *np.quantile(khoi[:, j], [.05, .95])))
```

```text
Kết quả khi mình chạy:
Số nến có |r| > 3σ: 278 / 15677
cặp liền nhau |r|>3σ   thật  37.000 | xáo từng nến TB   5.042 [P5  2.000, P95  9.000] | xáo theo ngày TB  37.036 [P5 37.000, P95 37.000]
tương quan |r| bậc 1   thật   0.267 | xáo từng nến TB   0.000 [P5 -0.013, P95  0.015] | xáo theo ngày TB   0.267 [P5  0.266, P95  0.268]
```

Thật có 37 cặp nến lớn liền nhau. Xáo iid chỉ còn ~5, vì nó rải 278 nến lớn đều khắp 8 tháng. Xáo theo ngày giữ nguyên 37, vì các cặp
nến lớn gần như luôn nằm trong cùng một ngày. Null iid vì thế **yếu**: thế giới nó tạo ra yên ả hơn thật nhiều. Một thống kê nào
dính tới biến động (biên độ sau sự kiện, số nến lớn…) sẽ trông «có ý nghĩa» khi so với null iid, chỉ vì biến động co cụm.

Áp dụng cho câu hỏi ở mục 2: khác biệt giữa vàng và nhiễu đến từ đâu? Xáo **nến** (giữ hình dạng high / low / close so với open
của từng nến, rồi nối lại: open nến sau = close nến trước):

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def dem(kq):
    loai = kq["su_kien"]["structure_type"].value_counts()
    n = lambda *ten: int(sum(loai.get(t, 0) for t in ten))
    sweep, run = n("LIQ_SWEEP_BSL", "LIQ_SWEEP_SSL"), n("LIQ_RUN_UP", "LIQ_RUN_DOWN")
    shift = n("SHIFT_UP", "SHIFT_DOWN")
    return {"ITH + ITL": n("SWING_HIGH_L2", "SWING_LOW_L2"),
            "FVG": n("FVG_UP", "FVG_DOWN"),
            "sweep / (sweep + run) %": round(100 * sweep / (sweep + run), 1),
            "shift": shift,
            "shift có FVG (%)": round(100 * n("SHIFT_FVG_UP", "SHIFT_FVG_DOWN") / shift, 1),
            "order flow chưa rõ (% tg)": round(100 * kq["ket_qua"].stats["chi_so_thuat_toan"]["order_flow"]
                                              ["ty_le_thoi_gian"]["chua_ro"], 1)}

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
# Mỗi nến = (high, low, close) tính theo log so với open của chính nó → «hình dạng nến»
o = np.log(df.open.to_numpy())
dh, dl, dc = np.log(df.high.to_numpy()) - o, np.log(df.low.to_numpy()) - o, np.log(df.close.to_numpy()) - o
ngay = (df.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).date   # ngày giao dịch, mốc 17:00 NY

def xep_lai(thu_tu):
    """Nối các nến theo thứ tự cho trước: open nến sau = close nến trước; thời gian liên tục, không giờ nghỉ."""
    c = np.cumsum(dc[thu_tu]); mo = np.concatenate([[0.0], c[:-1]])
    idx = pd.date_range("2024-01-01", periods=len(thu_tu), freq="15min", tz="UTC")
    return 2300 * np.exp(pd.DataFrame({"open": mo, "high": mo + dh[thu_tu], "low": mo + dl[thu_tu], "close": c},
                                      index=idx))

rng = np.random.default_rng(5)
r = np.log(df.close).diff()[df.index.to_series().diff() == pd.Timedelta("15min")]
gia_mp = 2300 * np.exp(np.cumsum(rng.normal(0, r.std() / np.sqrt(15), len(df) * 15)))
cac_ngay = pd.unique(ngay)
theo_ngay = np.concatenate([np.flatnonzero(ngay == d) for d in rng.permutation(cac_ngay)])

bang = {
    "ngẫu nhiên": dem(chay_tren_df("ict_structure", nen_tu_gia(gia_mp))),
    "xáo từng nến": dem(chay_tren_df("ict_structure", xep_lai(rng.permutation(len(df))))),
    "xáo theo ngày": dem(chay_tren_df("ict_structure", xep_lai(theo_ngay))),
    "thật nối liền": dem(chay_tren_df("ict_structure", xep_lai(np.arange(len(df))))),
    "thật": dem(chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")),
}
pd.set_option("display.width", 160)
print(pd.DataFrame(bang).to_string())
```

```text
Kết quả khi mình chạy (~20 giây):
                           ngẫu nhiên  xáo từng nến  xáo theo ngày  thật nối liền    thật
ITH + ITL                      1730.0        2033.0         1822.0         1833.0  1768.0
FVG                            5329.0        3777.0         3239.0         3241.0  3139.0
sweep / (sweep + run) %          66.3          69.5           72.6           72.7    72.8
shift                           149.0         139.0          169.0          161.0   152.0
shift có FVG (%)                 81.2          70.5           54.4           54.7    55.3
order flow chưa rõ (% tg)        20.2          19.0           24.9           24.7    23.9
```

Đọc từ trái sang phải:

- «Thật nối liền» ≈ «thật»: bỏ giờ nghỉ / cuối tuần không đổi bức tranh.
- **Hình dạng nến** (ngẫu nhiên → xáo từng nến): FVG giảm từ ~5 300 xuống ~3 800, tỷ lệ sweep tăng 66 → 70%. Râu dài làm việc này,
  không cần thứ tự nào.
- **Thứ tự trong ngày** (xáo từng nến → xáo theo ngày): FVG xuống ~3 240, shift kèm FVG từ 70 xuống 54%, «chưa rõ» lên 25%. Đây là
  phần do nến liền nhau phụ thuộc nhau (hơi quay đầu, biến động co cụm, mùa vụ trong ngày: module 4).
- **Thứ tự giữa các ngày** (xáo theo ngày → thật): gần như không đổi gì. Mọi con số cấu trúc ở đây được giải thích bởi tính chất của
  từng ngày. Không cần «ngày hôm trước dẫn tới ngày hôm sau».

Không phải con số nào cũng dễ giải thích: xáo từng nến lại cho **nhiều** ITH/ITL hơn cả thật lẫn nhiễu. Điều quan trọng là phương
pháp: mỗi bước xáo tắt đúng một tính chất, nên bạn biết khác biệt đến từ đâu. Osler (2000) làm đúng kiểu này với mức hỗ trợ /
kháng cự do các công ty công bố. Null của bà là 10 000 bộ mức nhân tạo, và giá bật tại mức thật nhiều hơn mức nhân tạo chỉ ~4 điểm %
([`nghien_cuu_bias_regime.md`](../research/nghien_cuu_bias_regime.md) §2.2).

**Nguyên tắc chọn null:** giữ mọi thứ bạn **không** kiểm, phá đúng thứ bạn **đang** kiểm.

**Bẫy hay gặp.**
- Dùng xáo iid cho một thống kê liên quan tới biến động. Null quá yên, nên mọi thứ đều «có ý nghĩa».
- Dùng xáo theo ngày để kiểm một hiệu ứng **trong ngày**, ví dụ «sau sweep SSL, 8 nến sau giá đi lên». Xáo theo ngày giữ nguyên
  hiệu ứng đó nên không bao giờ bác bỏ được. Kiểm hướng mà vẫn giữ biến động thì dùng **đổi dấu** (bài tập 3), mốc phân tích (mục 3)
  hoặc ghép cặp (mục 6).

## 6. Chuẩn ngẫu nhiên «cùng giờ × tầng ATR» của lab

**Trực giác.** Bạn thấy sau shift giá thường chạy mạnh. So với cái gì? Nếu so với một nến bất kỳ thì gần như chắc chắn shift
«thắng», vì shift cần một nến displacement. Displacement dồn vào giờ mở phiên London / New York và những ngày biến động cao. Nến bất
kỳ thì phần lớn rơi vào giờ vắng.

**Định nghĩa.** **Chuẩn ngẫu nhiên ghép cặp (matched null)** của trang Đánh giá, chế độ `matched_hour_atr_v1`
([`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.3): mỗi sự kiện thật kéo một nến ngẫu nhiên **cùng giờ New York**
và **cùng tầng ATR** (tam phân vị ATR Wilder trong cửa sổ). Lặp N lần để có phân phối. So với kiểu `uniform_v1` (rải đều), trang
Đánh giá ghi rõ: rải đều đưa sự kiện ngẫu nhiên vào giờ vắng nên «làm thuật toán trông giỏi hơn thực tế». Tự kiểm điều đó với thước
đo «biên độ 8 nến sau shift»:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

kq = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")
ev, tl = kq["su_kien"], kq["timeline"]
df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")      # cùng nến, cùng thứ tự với kq["nen"]
n, H = len(df), 8
# Biên độ (USD) của 8 nến NGAY SAU nến t — thước đo sau sự kiện, chỉ để chấm, không bao giờ là đầu vào
bien_do_sau = (df.high.rolling(H).max().shift(-H) - df.low.rolling(H).min().shift(-H)).to_numpy()
gio_ny = df.index.tz_convert("America/New_York").hour.to_numpy()
atr = tl["atr"].to_numpy(float)

hop_le = np.flatnonzero((np.arange(n) >= 200) & ~np.isnan(bien_do_sau) & ~np.isnan(atr))
tang_atr = np.full(n, -1)
tang_atr[hop_le] = pd.qcut(atr[hop_le], 3, labels=False)          # 3 tầng ATR (tam phân vị trên cửa sổ)

shift = ev.loc[ev.structure_type.isin(["SHIFT_UP", "SHIFT_DOWN"]), "confirmed_bar_index"].to_numpy()
shift = shift[np.isin(shift, hop_le)]
that = bien_do_sau[shift].mean()

nhom = {}                                                  # (giờ NY, tầng ATR) → các nến hợp lệ trong nhóm
for t in hop_le:
    nhom.setdefault((gio_ny[t], tang_atr[t]), []).append(t)
rng = np.random.default_rng(1)
deu, khop = [], []
for _ in range(2000):
    deu.append(bien_do_sau[rng.choice(hop_le, len(shift))].mean())                          # rải đều
    khop.append(bien_do_sau[[rng.choice(nhom[(gio_ny[t], tang_atr[t])]) for t in shift]].mean())  # cùng giờ × tầng ATR

print("Shift: %d sự kiện · biên độ 8 nến sau shift: TB %.2f USD" % (len(shift), that))
for ten, a in (("rải đều (uniform)", np.array(deu)), ("cùng giờ NY × tầng ATR", np.array(khop))):
    p = (1 + np.sum(a >= that)) / (len(a) + 1)
    print("%-24s TB %.2f USD [P5 %.2f, P95 %.2f] · p (≥ thật) = %.4f" % (ten, a.mean(), *np.quantile(a, [.05, .95]), p))
```

```text
Kết quả khi mình chạy (~10 giây):
Shift: 150 sự kiện · biên độ 8 nến sau shift: TB 11.68 USD
rải đều (uniform)        TB 8.42 USD [P5 7.61, P95 9.29] · p (≥ thật) = 0.0005
cùng giờ NY × tầng ATR   TB 11.15 USD [P5 10.36, P95 11.96] · p (≥ thật) = 0.1344
```

So với nến rải đều, 2 giờ sau shift giá đi rộng hơn 3.3 USD, p = 0.0005: một «phát hiện» rất đẹp. So với nến **cùng giờ và cùng
tầng ATR**, chênh chỉ còn 0.5 USD, p = 0.13: không phân biệt được với may rủi. Shift không báo trước biến động. Nó chỉ hay xảy ra
đúng những giờ và những giai đoạn vốn đã sôi động. Đó là lý do trang Đánh giá khuyên đọc chế độ ghép cặp.

**Bẫy hay gặp.**
- Thước đo nhìn về sau (biên độ 8 nến tới) và tầng ATR tính trên cả cửa sổ đều dùng thông tin tương lai. Được, vì đây là phép
  **chấm** sau sự kiện, không bao giờ là đầu vào của thuật toán (AGENTS.md §2.1). Đưa chúng vào detector là nhìn tương lai.
- Ghép cặp theo giờ chỉ khử phần giải thích được bởi giờ và ATR. Tin vĩ mô theo lịch (NFP, CPI) vẫn còn trong đó. p = 0.13 nghĩa là
  «chưa thấy khác», không phải «chứng minh không khác».
- p = 0.0005 trên **một** phép thử chọn trong nhiều phép thử vẫn cần điều chỉnh kiểm định nhiều lần (module 2).

## Lab đang dùng những điều này ở đâu

| Khái niệm | File / tài liệu của lab | Ghi chú |
|---|---|---|
| Mốc gambler's ruin cho order flow | [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) §4–§5, [`research/orderflow_survey.py`](../../research/orderflow_survey.py) | lợi thế = trúng − mốc; kiểm thước đo theo nhóm mốc; lợi thế cân bằng chiều |
| Vùng BSL / SSL còn nguyên, «lấy» = xuyên ≥ 0.1 ATR | [`core/components/liquidity.py`](../../core/components/liquidity.py), [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §4.9 | cột timeline `liq_above`, `liq_below` dùng ở mục 3 |
| Chuẩn ngẫu nhiên cùng giờ × tầng ATR | [`core/eval/null_baseline.py`](../../core/eval/null_baseline.py), [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.3 | `matched_hour_atr_v1` (nên đọc) và `uniform_v1` (chỉ để so) |
| Directional change, ngưỡng θ·ATR | [`thuat_toan_dc_atr_structure.md`](../algorithms/thuat_toan_dc_atr_structure.md) §4 | OS/θ ≈ 1 là kỳ vọng của nhiễu (R5-02) |
| Chạy thuật toán trên nến tự tạo | [`research/hoc_quant/hoc.py`](../../research/hoc_quant/hoc.py) `chay_tren_df`, `nen_tu_gia` | lịch phiên `none` cho chuỗi liên tục |
| Dữ liệu `[MÔ PHỎNG]` trong DB | [`core/data/synthetic.py`](../../core/data/synthetic.py) | có giai đoạn cài sẵn, để thử giao diện, **không** phải null |
| Null mô phỏng, bootstrap theo ngày | [`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md) R7-22, R7-17 | bước 2 của đề xuất «vòng so tài» |

## Bài tập

**Bài 1 (dễ).** Chạy `ict_structure` trên hai bước ngẫu nhiên **cùng hạt giống**, một chuỗi có σ như vàng, một chuỗi σ gấp 10. Số
ITH/ITL, FVG, displacement, sweep, run, shift có đổi không? Vì sao điều này giải thích phần «giống nhiễu» ở mục 2?

*Gợi ý:* cùng `default_rng(1)` cho cả hai, chỉ nhân σ.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def dem(kq):
    loai = kq["su_kien"]["structure_type"].value_counts()
    n = lambda *ten: int(sum(loai.get(t, 0) for t in ten))
    return {"ITH + ITL": n("SWING_HIGH_L2", "SWING_LOW_L2"), "FVG": n("FVG_UP", "FVG_DOWN"),
            "displacement": n("DISPLACEMENT_UP", "DISPLACEMENT_DOWN"),
            "sweep": n("LIQ_SWEEP_BSL", "LIQ_SWEEP_SSL"), "run": n("LIQ_RUN_UP", "LIQ_RUN_DOWN"),
            "shift": n("SHIFT_UP", "SHIFT_DOWN")}

bang = {}
for he_so in (1, 10):
    rng = np.random.default_rng(1)                      # CÙNG hạt giống → cùng hình dạng đường, chỉ khác tỷ lệ
    gia = 2300 * np.exp(np.cumsum(rng.normal(0, he_so * 0.00094 / np.sqrt(15), 15850 * 15)))
    bang["sigma × %d" % he_so] = dem(chay_tren_df("ict_structure", nen_tu_gia(gia)))
print(pd.DataFrame(bang).to_string())
```

```text
Kết quả khi mình chạy:
              sigma × 1  sigma × 10
ITH + ITL          1742        1742
FVG                5197        5197
displacement       1173        1173
sweep               962         959
run                 479         481
shift               134         132
```

Gần như trùng tuyệt đối. Pivot và FVG chỉ so giá với giá; displacement, «lấy» thanh khoản, dung sai EQ đều tính theo ATR. Phóng to
biến động 10 lần thì ATR cũng to 10 lần. Vài sweep/run lệch nhau vì giá = exp(log giá): phóng log giá 10 lần không phóng mọi hiệu
giá đúng 10 lần, nên vài phép so với ATR đổi kết quả. Hệ quả: so lab với nhiễu thì **mức** biến động không quan trọng. Thứ quan
trọng là **hình dạng** (đuôi, râu, co cụm).

</details>

**Bài 2 (vừa).** Thêm drift: mỗi nến cộng trung bình lợi suất của vàng 01–08/2024. Hai vùng cách đều hai phía 2, 10 và 40 ATR. Xác
suất chạm trên trước bằng bao nhiêu? Nối kết quả với việc nghiên cứu order flow thấy vùng D1 lệch ±15 điểm % theo xu hướng.

*Gợi ý:* mô phỏng như mục 3 với `rng.normal(mu, sigma)`; ATR xấp xỉ bằng biên độ log trung bình của một nến.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()[df.index.to_series().diff() == pd.Timedelta("15min")]
mu, sigma = r.mean(), r.std()
atr = np.log(df.high / df.low).mean()                 # biên độ TB một nến, xấp xỉ ATR theo log
print("drift mỗi nến %.2e · sigma %.2e · «ATR» %.2e (log)" % (mu, sigma, atr))

rng = np.random.default_rng(3)
def mo_phong(d, mu, n_duong=4000):
    """Hai vùng cách đều d (log) hai phía; bước ngẫu nhiên có drift mu. Tỷ lệ chạm TRÊN trước + số nến TB."""
    x = np.zeros(n_duong); con = np.ones(n_duong, bool); tren = np.zeros(n_duong, bool); so_nen = 0
    while con.any():
        x[con] += rng.normal(mu, sigma, con.sum()); so_nen += 1
        tren |= con & (x >= d); con &= (x < d) & (x > -d)
    return tren.mean(), (d / sigma) ** 2

for k in (2, 10, 40):
    p, t = mo_phong(k * atr, mu)
    print("vùng cách %2d ATR mỗi phía: P(trên trước) = %.3f (không drift: 0.500) · ~%d nến tới khi chạm" % (k, p, t))
```

```text
Kết quả khi mình chạy:
drift mỗi nến 9.08e-06 · sigma 9.40e-04 · «ATR» 1.24e-03 (log)
vùng cách  2 ATR mỗi phía: P(trên trước) = 0.525 (không drift: 0.500) · ~6 nến tới khi chạm
vùng cách 10 ATR mỗi phía: P(trên trước) = 0.568 (không drift: 0.500) · ~173 nến tới khi chạm
vùng cách 40 ATR mỗi phía: P(trên trước) = 0.735 (không drift: 0.500) · ~2777 nến tới khi chạm
```

Thời gian chờ tăng theo **bình phương** khoảng cách (khoảng $(d/\sigma)^2$ nến), còn drift cộng dồn **tuyến tính** theo thời gian.
Vùng M15 gần (2 ATR) bị chạm sau vài nến, drift gần như vô hình. Biên độ trung bình một nến D1 năm 2024 là ~32 USD, gấp ~11 lần nến
M15. Vậy 10 ATR M15 cỡ khoảng cách tới PDH / PDL, và đã lệch gần 7 điểm %. 40 ATR cỡ mức tuần, chờ ~30 ngày giao dịch, và bị drift
chi phối: 73.5% thay vì 50%. Với hai vùng cách đều, lời giải chính xác cho chuyển động Brown có drift là
$P = 1/(1 + e^{-2\mu d/\sigma^2})$, cho 0.513 / 0.563 / 0.735. Mô phỏng khớp; chênh 0.012 ở 2 ATR cỡ 1.5 lần sai số mô phỏng của
4000 đường. Vì vậy với vùng D1 phải dùng lợi thế cân bằng chiều.

</details>

**Bài 3 (vừa).** Kiểm «sau một nến lớn (|r| > 3σ), 4 nến kế tiếp đi tiếp cùng chiều». Thống kê S = trung bình của
dấu(nến lớn) × tổng 4 lợi suất sau, chia σ. So S thật với hai null: xáo từng nến và đổi dấu ngẫu nhiên. Null nào rộng hơn, vì sao?

*Gợi ý:* đổi dấu = `r * rng.choice([-1, 1], len(r))`.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()
r = r[df.index.to_series().diff() == pd.Timedelta("15min")].to_numpy()
sigma = r.std()

def S(x, k=4):
    """Sau nến |r| > 3σ, 4 nến kế tiếp đi tiếp cùng chiều bao nhiêu (đơn vị σ)? > 0: tiếp diễn, < 0: quay đầu."""
    lon = np.flatnonzero(np.abs(x[:-k]) > 3 * sigma)
    tiep = np.array([x[i + 1:i + 1 + k].sum() for i in lon])
    return np.mean(np.sign(x[lon]) * tiep) / sigma

rng = np.random.default_rng(1)
s_that = S(r)
xao = np.array([S(rng.permutation(r)) for _ in range(1000)])                  # null iid
doi_dau = np.array([S(r * rng.choice([-1, 1], len(r))) for _ in range(1000)])  # giữ |r| (biến động), phá hướng
print("S thật = %.3f" % s_that)
for ten, a in (("xáo từng nến", xao), ("đổi dấu ngẫu nhiên", doi_dau)):
    p = (1 + np.sum(np.abs(a) >= abs(s_that))) / (len(a) + 1)
    print("%-20s độ lệch chuẩn %.3f · khoảng 95%% [%.3f, %.3f] · p hai phía %.2f" % (ten, a.std(), *np.quantile(a, [.025, .975]), p))
```

```text
Kết quả khi mình chạy:
S thật = 0.087
xáo từng nến         độ lệch chuẩn 0.118 · khoảng 95% [-0.225, 0.235] · p hai phía 0.47
đổi dấu ngẫu nhiên   độ lệch chuẩn 0.237 · khoảng 95% [-0.467, 0.459] · p hai phía 0.71
```

Không có tiếp diễn hay quay đầu đáng kể sau nến lớn (p 0.47 / 0.71). Null đổi dấu rộng **gấp đôi** null iid: sau nến lớn thật thì 4
nến kế tiếp cũng lớn (co cụm), nên tổng của chúng dao động mạnh. Null iid đặt 4 nến bình thường sau nến lớn, nên dải quá hẹp. Nếu
S thật là 0.3 thì null iid báo «có ý nghĩa» (ngoài 0.235), còn null đổi dấu thì không (trong 0.459). Null iid làm hiệu ứng trông chắc
hơn thực tế.

</details>

**Bài 4 (khó).** Mục 4 thấy vàng M15 2018–2023 có OS/θ = 1.18 ở θ = 1%. Lập ba null, mỗi null 100 chuỗi: bước ngẫu nhiên chuẩn cùng
σ, xáo từng lợi suất, xáo theo ngày. Tính p cho mỗi null. Kết luận «sóng vàng kéo dài hơn ngẫu nhiên» đứng được không?

*Gợi ý:* hàm `overshoot` ở mục 4; xáo theo ngày như mục 5 (ngày giao dịch mốc 17:00 NY).

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def overshoot(x, theta):                               # như ở mục 4
    huong, cuc_tri, dcc, os_ = 1, x[0], None, []
    for p in x[1:]:
        if huong * (p - cuc_tri) > 0:
            cuc_tri = p
        elif huong * (cuc_tri - p) >= theta:
            if dcc is not None:
                os_.append(abs(cuc_tri - dcc))
            huong, cuc_tri, dcc = -huong, p, p
    return np.array(os_) / theta

theta = 0.01
df = nap_nen(XAU_M15_DAI, "2018-01-01", "2024-01-01")
x = np.log(df.close.to_numpy())
r = np.diff(x)
that = overshoot(x, theta).mean()
ngay = (df.index[1:].tz_convert("America/New_York") + pd.Timedelta(hours=7)).date   # ngày giao dịch của mỗi r
vi_tri = list(pd.Series(np.arange(len(r))).groupby(ngay).apply(np.array))          # chỉ số của từng ngày

rng = np.random.default_rng(8)
null = {"ngẫu nhiên chuẩn": [], "xáo từng lợi suất": [], "xáo theo ngày": []}
for _ in range(100):
    null["ngẫu nhiên chuẩn"].append(overshoot(np.cumsum(rng.normal(0, r.std(), len(r))), theta).mean())
    null["xáo từng lợi suất"].append(overshoot(np.cumsum(rng.permutation(r)), theta).mean())
    thu_tu = np.concatenate([vi_tri[i] for i in rng.permutation(len(vi_tri))])
    null["xáo theo ngày"].append(overshoot(np.cumsum(r[thu_tu]), theta).mean())
print("Thật: OS/θ TB = %.3f (θ = 1%%)" % that)
for ten, a in null.items():
    a = np.array(a)
    print("%-18s TB %.3f [P5 %.3f, P95 %.3f] · p (≥ thật) = %.3f"
          % (ten, a.mean(), *np.quantile(a, [.05, .95]), (1 + np.sum(a >= that)) / (len(a) + 1)))
```

```text
Kết quả khi mình chạy:
Thật: OS/θ TB = 1.182 (θ = 1%)
ngẫu nhiên chuẩn   TB 1.051 [P5 0.994, P95 1.103] · p (≥ thật) = 0.010
xáo từng lợi suất  TB 1.102 [P5 1.032, P95 1.168] · p (≥ thật) = 0.040
xáo theo ngày      TB 1.138 [P5 1.094, P95 1.192] · p (≥ thật) = 0.109
```

Ba null cho ba kết luận. Với bước ngẫu nhiên chuẩn, 1.18 nằm ngoài mọi chuỗi (p = 0.01, mức nhỏ nhất có thể với 100 chuỗi). Xáo
lợi suất giữ đuôi dày nên null nhích lên 1.10 và p = 0.04. Xáo theo ngày giữ thêm mọi thứ trong ngày (co cụm biến động, mùa vụ):
null lên 1.14, p = 0.11, không còn ý nghĩa. Một sóng θ = 1% kéo dài trung bình ~2 ngày (760 sóng trong ~1 550 ngày), nên câu hỏi
thật là «thứ tự giữa các ngày có làm sóng dài hơn không». Khi null đã giữ tính chất của từng ngày, câu trả lời là chưa thấy. Kết
luận «sóng vàng có quán tính» chưa đứng được.

</details>

## Tự kiểm

1. Một đường bước ngẫu nhiên không xu hướng có thể nằm trên giá mở đầu 95% thời gian của 8 tháng không? Hiếm hay thường?
<details><summary>Đáp án</summary>

Thường. Theo luật arcsin, ~20% số đường nằm trên mức đầu hơn 90% thời gian và ~20% nằm dưới (mục 2.1). «Một phía rất lâu» không phải dấu hiệu xu hướng.

</details>

2. Vàng ở 2400, BSL ở 2403, SSL ở 2391. Mốc ngẫu nhiên cho «BSL bị lấy trước» là bao nhiêu? Một cách đọc order flow tăng «đúng 72%»
   trong những tình huống như vậy thì lợi thế là bao nhiêu?
<details><summary>Đáp án</summary>

d_trên = 3, d_dưới = 9 → mốc 9/12 = 75%. Lợi thế = 72 − 75 = −3 điểm %: kém tung đồng xu.

</details>

3. Vì sao số ITH/ITL, displacement, shift trên bước ngẫu nhiên gần bằng trên vàng thật?
<details><summary>Đáp án</summary>

Các định nghĩa so giá với giá (pivot, FVG) hoặc so với ATR của chính chuỗi (displacement, lấy thanh khoản). Chuỗi nào dao động cũng có chúng, và mức biến động không quan trọng (bài tập 1).

</details>

4. Xáo từng nến giữ gì và phá gì? Xáo theo ngày giữ gì và phá gì?
<details><summary>Đáp án</summary>

Xáo từng nến giữ phân phối và hình dạng từng nến; phá mọi thứ tự (co cụm, mùa vụ, phụ thuộc giữa nến liền nhau). Xáo theo ngày giữ mọi thứ trong ngày; chỉ phá thứ tự giữa các ngày.

</details>

5. Bạn muốn kiểm «sau sweep SSL, 8 nến sau giá đi lên». Null xáo theo ngày có hợp không?
<details><summary>Đáp án</summary>

Không. Hiệu ứng nằm trong ngày nên xáo theo ngày giữ nguyên nó, null trùng với thật. Dùng mốc gambler's ruin (nếu kết cục là chạm mức), đổi dấu ngẫu nhiên, hoặc ghép cặp cùng giờ × tầng ATR.

</details>

6. Vì sao chuẩn ngẫu nhiên rải đều (`uniform_v1`) làm thuật toán trông giỏi hơn thực tế?
<details><summary>Đáp án</summary>

Sự kiện thật dồn vào giờ sôi động và giai đoạn biến động cao. Rải đều đặt sự kiện ngẫu nhiên vào cả giờ vắng, nên mọi thước đo gắn với biến động của null thấp hơn. Ở mục 6, p = 0.0005 với rải đều nhưng 0.13 với ghép cặp.

</details>

7. Một bài báo viết: «sau khi xác nhận đảo chiều θ, giá đi tiếp trung bình 1.02θ». Bạn kết luận gì?
<details><summary>Đáp án</summary>

Không gì cả. OS ≈ θ là kỳ vọng của bước ngẫu nhiên (R5-02). Chỉ khi khác 1 có ý nghĩa so với một null cùng cách lấy mẫu mới có thông tin.

</details>

8. «97% FVG bị lấp» có phải bằng chứng FVG hút giá?
<details><summary>Đáp án</summary>

Không. Trên bước ngẫu nhiên tỷ lệ là 98–99% (mục 2.2). Giá dao động thì sớm muộn sẽ quay lại hầu hết mọi vùng gần.

</details>

## Đọc thêm

- William Feller, *An Introduction to Probability Theory and Its Applications*, tập 1: chương III (dao động khi tung đồng xu, luật
  arcsin) và chương XIV (bước ngẫu nhiên và bài toán cháy túi).
- David Aronson, *Evidence-Based Technical Analysis*: kiểm định luật kỹ thuật bằng chuẩn ngẫu nhiên và xáo trộn; vì sao đào nhiều
  luật thì luật tốt nhất trông giỏi nhờ may.
- Eugene Fama (1970), «Efficient Capital Markets: A Review of Theory and Empirical Work»: ba dạng hiệu quả thị trường.
- Carol Osler (2000), FRBNY Economic Policy Review: kiểm mức hỗ trợ / kháng cự bằng 10 000 bộ mức nhân tạo. Đây là mẫu cách so «khác
  nhiễu bao nhiêu».
- Tài liệu lab: [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) §4–§5 (mốc, lợi thế cân bằng chiều),
  [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.3 (chuẩn ngẫu nhiên).
- Danh mục quant ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md)): R5-02 (overshoot ≈ θ), R5-03 (DC
  nowcast so với gambler's ruin), R7-17 (bootstrap khối theo ngày / tuần), R7-22 (null mô phỏng + đối chứng dương).
