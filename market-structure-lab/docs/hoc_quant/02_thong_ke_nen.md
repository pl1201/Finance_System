# Module 2 — Thống kê nền

> **Sau module này bạn làm được:**
> - mô tả phân phối lợi suất bằng trung bình, độ lệch chuẩn, độ lệch, kurtosis, và đếm được «đuôi dày» so với phân phối chuẩn;
> - tính sai số chuẩn và khoảng tin cậy 95% cho một tỷ lệ (vd tỷ lệ nến tăng), và nói đúng khoảng đó nghĩa là gì;
> - làm một kiểm định giả thuyết, đọc p-value **đúng nghĩa**, và biết những gì p-value không nói;
> - nhận ra bẫy thử nhiều lần, sửa bằng Benjamini–Hochberg;
> - tự cài bootstrap iid và bootstrap khối, giải thích vì sao dữ liệu giá cần khối;
> - tính lực thống kê và hiệu ứng nhỏ nhất phát hiện được (MDE), rồi đọc lại kết quả «±2 điểm %» của nghiên cứu order flow.
>
> **Cần trước:** module 1  ·  **Thời lượng:** ~6 giờ

> **Ba điều cần nhớ** (đọc lại khi ôn)
>
> 1. Lợi suất M15 của vàng có đuôi rất dày: 123 lần vượt 4σ, trong khi phân phối chuẩn chỉ cho khoảng 1.
> 2. p-value không phải xác suất giả thuyết đúng. Thử 23 giờ trong ngày thì vài giờ «có ý nghĩa» chỉ do may; sau Benjamini–Hochberg không còn giờ nào.
> 3. Trước khi kết luận «không có hiệu ứng», tính hiệu ứng nhỏ nhất phát hiện được (MDE): kết quả «±2 điểm %» của order flow nằm sát MDE.

## Vì sao cần

Nghiên cứu order flow của lab kết luận: 7 cách đọc order flow kiểu ICT không đoán phía thanh khoản bị lấy kế tiếp tốt hơn mốc ngẫu
nhiên — «lợi thế nằm trong ±2 điểm %, khoảng tin cậy chứa 0». Trang Đánh giá sẽ báo F1 của thuật toán cạnh «F1 ngẫu nhiên TB
[P5–P95] · x/N lượt ≥ thực tế». Để đọc những dòng đó bạn cần biết: một tỷ lệ 52% khác 50% thật hay do may? «Khoảng tin cậy chứa
0» có nghĩa là «không có hiệu ứng» không? Thử từng giờ trong ngày thì mấy giờ «có ý nghĩa» chỉ do may? Mẫu 176 lần shift đủ để thấy
lợi thế 5 điểm % không? Module này trả lời bằng chính dữ liệu vàng của lab.

## 1. Phân phối, trung bình, độ lệch chuẩn, độ lệch

**Trực giác.** Mỗi nến M15 cho một lợi suất. Xếp 15 677 lợi suất thành biểu đồ cột, bạn thấy hình dạng của «một nến bình thường»:
đa số quanh 0, ít dần về hai phía. **Phân phối (distribution)** là hình dạng đó. Ba con số tóm tắt nó: tâm ở đâu, rộng bao nhiêu,
lệch về phía nào.

**Định nghĩa.** Với $n$ lợi suất $r_1, \dots, r_n$:
- **Trung bình (mean)** $\bar r = \frac{1}{n}\sum_i r_i$ — tâm.
- **Độ lệch chuẩn (standard deviation)** $s = \sqrt{\frac{1}{n-1}\sum_i (r_i - \bar r)^2}$ — độ rộng điển hình quanh tâm (chia
  $n-1$ thay vì $n$ để không đánh giá thấp độ rộng thật). Với lợi suất, $s$ chính là **biến động (volatility)** của khung đó.
- **Độ lệch (skewness)** $\frac{1}{n}\sum_i z_i^3$ với $z_i = (r_i - \bar r)/s$ — âm khi cú giảm lớn nhiều hơn cú tăng lớn.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()
lien = df.index.to_series().diff() == pd.Timedelta(minutes=15)    # chỉ lấy cặp nến liền nhau (bỏ qua khoảng trống)
r = r[lien].values * 1e4                                          # đơn vị: bp (1 bp = 0.01%)

n = len(r)
tb = r.sum() / n
sd = np.sqrt(((r - tb) ** 2).sum() / (n - 1))
z = (r - tb) / sd
print("n = %d · trung bình %.3f bp · độ lệch chuẩn %.2f bp" % (n, tb, sd))
print("độ lệch (skewness) %.2f · kurtosis dư %.1f" % ((z ** 3).mean(), (z ** 4).mean() - 3))
print("scipy kiểm lại   : skew %.2f · kurtosis dư %.1f" % (stats.skew(r), stats.kurtosis(r)))
print("phân vị 1/25/50/75/99%:", np.percentile(r, [1, 25, 50, 75, 99]).round(1))

# Biểu đồ chữ: số nến thật trong từng ô 5 bp, cạnh số nến nếu phân phối là chuẩn (cùng TB, cùng sd)
canh = np.arange(-30, 31, 5)
that, _ = np.histogram(r, bins=canh)
chuan = n * np.diff(stats.norm.cdf(canh, tb, sd))
for a, b, x, y in zip(canh[:-1], canh[1:], that, chuan):
    print("%4d..%3d bp  thật %5d  chuẩn %7.0f  %s" % (a, b, x, y, "#" * int(x / 100)))
```

```text
Kết quả khi mình chạy:
n = 15677 · trung bình 0.091 bp · độ lệch chuẩn 9.40 bp
độ lệch (skewness) -0.26 · kurtosis dư 13.4
scipy kiểm lại   : skew -0.26 · kurtosis dư 13.4
phân vị 1/25/50/75/99%: [-27.8  -3.9   0.1   4.2  25.6]
 -30..-25 bp  thật    66  chuẩn      49
 -25..-20 bp  thật   118  chuẩn     196  #
 -20..-15 bp  thật   296  chuẩn     595  ##
 -15..-10 bp  thật   718  chuẩn    1369  #######
 -10.. -5 bp  thật  1897  chuẩn    2391  ##################
  -5..  0 bp  thật  4447  chuẩn    3168  ############################################
   0..  5 bp  thật  4574  chuẩn    3184  #############################################
   5.. 10 bp  thật  2041  chuẩn    2427  ####################
  10.. 15 bp  thật   772  chuẩn    1404  #######
  15.. 20 bp  thật   303  chuẩn     616  ###
  20.. 25 bp  thật   150  chuẩn     205  #
  25.. 30 bp  thật    64  chuẩn      52
```

Một nến M15 vàng 2024 điển hình dao động 9.4 bp (khoảng 2 USD ở giá 2300). Trung bình 0.091 bp mỗi nến — nhỏ hơn độ lệch chuẩn
100 lần, dù vàng tăng 21% trong 8 tháng: hướng gần như chìm hẳn trong nhiễu ở khung M15. So với phân phối chuẩn cùng trung bình và
độ lệch chuẩn, dữ liệu thật **nhọn hơn** ở giữa (−5..5 bp: 9021 nến so với 6352), **hụt** ở vai (10–20 bp), và **dày hơn** ở đuôi
(ngoài ±25 bp). Đó là hình dạng điển hình của lợi suất tài chính.

**Bẫy hay gặp.**
- **Trung bình bị vài nến kéo.** Với đuôi dày, một tin CPI có thể đổi trung bình cả tháng. Trung vị (median) bền hơn.
- **Độ lệch chuẩn ≠ «biên độ tối đa».** Ở phân phối chuẩn, ±2 sd chứa 95% dữ liệu; ở lợi suất thật, ±2 sd chứa nhiều hơn 95% (vì
  nhọn) nhưng phần còn lại có những cú lớn hơn nhiều (mục 2).
- **Gộp lợi suất vắt qua khoảng trống** (nến mở tuần) làm sd và đuôi lớn giả tạo — vì vậy code trên lọc `lien`.

## 2. Đuôi dày và kurtosis

**Trực giác.** Nếu lợi suất là phân phối chuẩn, một cú 4 độ lệch chuẩn (vd 38 bp trong một nến M15) hiếm tới mức cả 8 tháng chỉ
gặp khoảng 1 lần. Người xem chart vàng biết ngày công bố CPI có những nến như vậy mỗi tháng.

**Định nghĩa.**
- **Kurtosis** $\frac{1}{n}\sum_i z_i^4$ đo độ «nặng» của đuôi; phân phối chuẩn có kurtosis 3. **Kurtosis dư (excess kurtosis)**
  = kurtosis − 3 (scipy trả con số này): 0 với phân phối chuẩn, dương là **đuôi dày (fat tails)**.
- Cách đo trực tiếp hơn: đếm số lần $|z| > k$ và so với kỳ vọng dưới phân phối chuẩn $n \cdot 2\,P(Z > k)$.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()
r = r[df.index.to_series().diff() == pd.Timedelta(minutes=15)] * 1e4
z = (r - r.mean()) / r.std()
n = len(z)
print(" k   số nến |z| > k   nếu phân phối chuẩn")
for k in [2, 3, 4, 5, 6]:
    print("%2d   %12d   %16.2f" % (k, (z.abs() > k).sum(), n * 2 * stats.norm.sf(k)))

lon = z.abs().sort_values(ascending=False).head(5).index
print(pd.DataFrame({"gio_NY": lon.tz_convert("America/New_York").strftime("%a %d/%m %H:%M"),
                    "r_bp": r[lon].round(1).values, "z": z[lon].round(1).values}).to_string(index=False))
```

```text
Kết quả khi mình chạy:
 k   số nến |z| > k   nếu phân phối chuẩn
 2            752             713.31
 3            278              42.32
 4            123               0.99
 5             58               0.01
 6             38               0.00
         gio_NY   r_bp     z
Thu 11/07 08:30  122.5  13.0
Fri 02/08 10:30 -113.9 -12.1
Mon 22/04 21:30 -103.8 -11.1
Fri 07/06 04:00  -94.7 -10.1
Tue 13/02 08:30  -87.3  -9.3
```

Ở mức 2σ, số thật gần với phân phối chuẩn. Từ 3σ trở đi, khoảng cách bùng nổ: 123 nến vượt 4σ thay vì ~1; 38 nến vượt 6σ thay
vì 0.00. Cú lớn nhất là 13σ. Hai trong năm cú lớn nhất rơi đúng 08:30 New York ngày 11/07 và 13/02/2024 — ngày Mỹ công bố CPI.

Một phần đuôi dày đến từ chỗ biến động **đổi theo giờ và theo ngày** (module 1 mục 7: giờ sôi động gấp 3.7 lần giờ vắng): trộn nến
yên ắng với nến tin tức thì phân phối chung nhọn và đuôi dày. Module 4 chia lợi suất cho biến động theo giờ rồi đo lại.

**Bẫy hay gặp.**
- **Dùng công thức «chuẩn» cho rủi ro đuôi.** Với phân phối chuẩn, cú vượt 5σ chỉ khoảng một lần trong 1.7 triệu nến; vàng M15 có 58
  cú trong 8 tháng.
- **Kurtosis rất nhạy với vài điểm.** Bỏ một ngày CPI là kurtosis đổi hẳn. Đếm $|z| > k$ dễ hiểu và bền hơn.
- **Ngưỡng theo σ toàn kỳ** (vd «nến > 3σ là bất thường») gắn cờ gần hết nến tin tức và hầu như không nến giờ châu Á. Ngưỡng theo
  ATR của lab đỡ hơn vì ATR là biến động gần đây, nhưng vẫn trễ theo mùa vụ (module 1 mục 7).

## 3. Sai số chuẩn và khoảng tin cậy

**Trực giác.** Tỷ lệ nến tăng của 8 tháng là 51.0%. Nếu thị trường «chạy lại» 8 tháng đó với cùng tính chất, con số sẽ khác đi một
chút — 50.6%, 51.4%… **Sai số chuẩn** đo con số ước lượng dao động bao nhiêu giữa những lần «chạy lại» tưởng tượng đó.

**Định nghĩa.**
- **Ước lượng (estimate)** $\hat p$: con số tính từ mẫu, vd $\hat p = k/n$ ($k$ nến tăng trên $n$ nến).
- **Sai số chuẩn (standard error, SE)**: độ lệch chuẩn của ước lượng qua các mẫu tưởng tượng. Với một tỷ lệ, nếu các nến độc lập:
  $$SE(\hat p) = \sqrt{\hat p(1-\hat p)/n}$$
  Sai số giảm theo $\sqrt n$: muốn hẹp gấp đôi phải có gấp bốn số nến.
- **Khoảng tin cậy 95% (confidence interval, KTC)** $\hat p \pm 1.96 \cdot SE$. Nghĩa đúng: **quy trình** dựng khoảng này, lặp lại
  trên nhiều mẫu, sẽ chứa giá trị thật khoảng 95% số lần. Nó không nói «giá trị thật có 95% xác suất nằm trong khoảng cụ thể này».

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
tang = (df.close > df.open).values           # nến tăng = close > open (nến close == open tính là không tăng)
n, k = len(tang), tang.sum()
p_mu = k / n
se = np.sqrt(p_mu * (1 - p_mu) / n)
print("n = %d · nến tăng %d · nến bằng (close = open) %d" % (n, k, (df.close == df.open).sum()))
print("tỷ lệ nến tăng %.4f · sai số chuẩn %.4f · KTC 95%% [%.4f, %.4f]" % (p_mu, se, p_mu - 1.96 * se, p_mu + 1.96 * se))

# KTC 95% "bắt" được giá trị thật bao nhiêu lần? Mô phỏng 10 000 "năm 2024" với tỷ lệ thật p = 0.51
rng = np.random.default_rng(42)
p_that = 0.51
k_gia = rng.binomial(n, p_that, size=10_000)
p_gia = k_gia / n
se_gia = np.sqrt(p_gia * (1 - p_gia) / n)
trung = (p_gia - 1.96 * se_gia <= p_that) & (p_that <= p_gia + 1.96 * se_gia)
print("KTC chứa p thật: %.1f%% số lần" % (100 * trung.mean()))
# Với 1/4 số nến (vd chỉ 2 tháng), KTC rộng gấp đôi
print("Độ rộng KTC: n = %d → ±%.4f · n = %d → ±%.4f" % (n, 1.96 * se, n // 4, 1.96 * np.sqrt(p_mu * (1 - p_mu) / (n // 4))))
```

```text
Kết quả khi mình chạy:
n = 15850 · nến tăng 8085 · nến bằng (close = open) 29
tỷ lệ nến tăng 0.5101 · sai số chuẩn 0.0040 · KTC 95% [0.5023, 0.5179]
KTC chứa p thật: 94.8% số lần
Độ rộng KTC: n = 15850 → ±0.0078 · n = 3962 → ±0.0156
```

Tỷ lệ nến tăng 51.0%, KTC 95% từ 50.2% đến 51.8%. Mô phỏng xác nhận nghĩa của «95%»: trong 10 000 năm giả, 94.8% số khoảng chứa tỷ
lệ thật. Với chỉ 2 tháng dữ liệu (1/4 số nến), khoảng rộng gấp đôi: ±1.6 điểm %.

**Bẫy hay gặp.**
- **Công thức giả định các nến độc lập.** Với dấu của nến (tăng / giảm) giả định này gần đúng (mục 6). Với thứ gì phụ thuộc biến
  động — «nến biên độ lớn», «swing», «sweep» — các quan sát dính chùm theo phiên, theo ngày, và công thức cho khoảng **quá hẹp**.
  Trang Đánh giá ghi rõ: sai số chuẩn $\sqrt{p(1-p)/n}$ của P/R là «xấp xỉ lạc quan vì swing không độc lập».
- **Định nghĩa thay đổi con số.** «Nến tăng» là close > open; 29 nến bằng (close = open) bị tính là «không tăng». Ở giờ có nhiều nến
  phẳng, quy ước này làm tỷ lệ tăng thấp giả tạo (bài tập 2 có ví dụ thật).

## 4. Kiểm định giả thuyết và p-value

**Trực giác.** Bạn tung đồng xu 15 850 lần, được 8085 mặt ngửa (51.0%). Đồng xu có lệch không? Cách nghĩ của kiểm định: **giả sử**
đồng xu công bằng, rồi hỏi «trong thế giới đó, kết quả lệch nhiều như thế này hiếm đến mức nào?». Rất hiếm thì ta nghi ngờ giả sử
ban đầu.

**Định nghĩa.**
- **Giả thuyết không (null hypothesis, $H_0$)**: phát biểu «không có gì đặc biệt» cụ thể đến mức tính toán được, vd $p = 0.5$.
- **Thống kê kiểm định**: khoảng cách giữa dữ liệu và $H_0$ tính bằng đơn vị sai số chuẩn **dưới $H_0$**:
  $$z = \frac{\hat p - 0.5}{\sqrt{0.5 \cdot 0.5 / n}}$$
- **p-value**: **nếu $H_0$ đúng**, xác suất thu được một kết quả lệch khỏi $H_0$ **ít nhất bằng** kết quả ta thấy (hai phía: lệch về
  phía nào cũng tính). Với $z$ lớn, xấp xỉ $p = 2\,P(Z > |z|)$.
- **Mức ý nghĩa $\alpha$** (thường 0.05): ngưỡng quy ước để nói «bác bỏ $H_0$». Bác bỏ khi $H_0$ đúng là **sai lầm loại I (dương
  tính giả, false positive)** — xảy ra với xác suất $\alpha$. Không bác bỏ khi $H_0$ sai là **sai lầm loại II (âm tính giả)**.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
tang = (df.close > df.open).values
n, k = len(tang), int(tang.sum())
p_mu = k / n

# H0: p = 0.5 (mỗi nến là một lần tung đồng xu công bằng)
se0 = np.sqrt(0.5 * 0.5 / n)                 # sai số chuẩn NẾU H0 đúng
z = (p_mu - 0.5) / se0
p_value = 2 * stats.norm.sf(abs(z))          # hai phía: lệch về phía nào cũng tính
print("tỷ lệ %.4f · z = %.2f · p-value (xấp xỉ chuẩn) = %.4f" % (p_mu, z, p_value))
print("p-value (nhị thức chính xác, scipy)        = %.4f" % stats.binomtest(k, n, 0.5).pvalue)

# p-value bằng mô phỏng: tung 200 000 "năm 2024" bằng đồng xu công bằng
rng = np.random.default_rng(3)
k_gia = rng.binomial(n, 0.5, size=200_000)
cuc_doan = np.abs(k_gia / n - 0.5) >= abs(p_mu - 0.5)
print("Mô phỏng: %.4f số năm giả lệch khỏi 50%% ít nhất bằng năm thật" % cuc_doan.mean())
```

```text
Kết quả khi mình chạy:
tỷ lệ 0.5101 · z = 2.54 · p-value (xấp xỉ chuẩn) = 0.0110
p-value (nhị thức chính xác, scipy)        = 0.0113
Mô phỏng: 0.0111 số năm giả lệch khỏi 50% ít nhất bằng năm thật
```

Ba cách tính cho cùng một đáp án: **trong một thế giới mà mỗi nến M15 là đồng xu công bằng, chỉ khoảng 1.1% số «năm 2024» cho tỷ lệ
lệch khỏi 50% nhiều như năm thật.** Đó là toàn bộ ý nghĩa của p = 0.011. Ở đây có lời giải thích đơn giản: vàng tăng 21% trong kỳ,
nên nến tăng nhỉnh hơn nến giảm một chút.

**p-value KHÔNG phải những điều sau** — đọc chậm từng dòng:
1. **Không phải xác suất $H_0$ đúng.** p = 0.011 không có nghĩa «1.1% khả năng thị trường là đồng xu». p-value là
   $P(\text{dữ liệu cực đoan như vậy} \mid H_0)$; câu bạn muốn hỏi là $P(H_0 \mid \text{dữ liệu})$ — hai thứ khác hẳn nhau. Giống
   như: «nếu là sweep thật thì giá quay lại ngay» không cho phép suy ra «giá quay lại ngay thì là sweep thật».
2. **Không phải xác suất «kết quả do may».** Nó được tính *với giả định* mọi thứ là may.
3. **Không đo độ lớn.** Với 15 850 nến, chênh 1 điểm % đã cho p = 0.011. Với 1 triệu nến, chênh 0.2 điểm % cũng cho p nhỏ — vô dụng
   cho thực tế. Luôn báo **cỡ hiệu ứng** và khoảng tin cậy cạnh p (mục 7).
4. **p > 0.05 không chứng minh «không có hiệu ứng».** Có thể hiệu ứng có thật nhưng mẫu quá nhỏ để thấy (bài tập 1: vàng D1 tăng 57%
   trong 6 năm mà tỷ lệ ngày tăng vẫn có p = 0.075).
5. **Chỉ đúng khi mô hình $H_0$ đúng giả định.** Ở đây $H_0$ giả định các nến độc lập. Nếu quan sát dính chùm (mục 6), p-value tính
   như trên **quá nhỏ**.

Vì sao điều 1 quan trọng đến vậy — một phép tính tay. Giả sử trong 1000 ý tưởng bạn thử, 100 ý tưởng có hiệu ứng thật, và mỗi phép
thử chỉ có lực 36% (mục 7: lực điển hình khi kiểm một giờ với lệch 3 điểm %). Ý tưởng thật lọt «p < 0.05»: 100 × 0.36 = 36. Ý tưởng
rỗng lọt do may: 900 × 0.05 = 45. Trong 81 kết quả «có ý nghĩa», chỉ 36 (44%) là thật. p < 0.05 mà phần lớn vẫn là sai.

**Bẫy hay gặp.**
- **Chọn $H_0$ dễ bác bỏ.** «Tỷ lệ = 50%» cho một giờ cụ thể trong năm vàng tăng mạnh: bác bỏ được, nhưng chỉ vì cả kỳ đã lệch,
  không phải vì giờ đó đặc biệt (mục 5).
- **Nhìn dữ liệu rồi mới đặt giả thuyết** («giờ 23 có vẻ cao, kiểm thử xem»): p-value mất nghĩa vì bạn đã chọn trong nhiều khả năng.
  Lab giải quyết bằng đoạn kiểm tra khoá: giả thuyết sinh ra trên đoạn phát triển phải kiểm trên dữ liệu chưa xem (module 7).

## 5. Kiểm định nhiều lần và FDR

**Trực giác.** Thử một giả thuyết rỗng ở mức 5%: 5% khả năng «có ý nghĩa» do may. Thử 23 giả thuyết rỗng: trung bình ~1 cái «có ý
nghĩa», và khả năng có ít nhất một cái là $1 - 0.95^{23} \approx 69\%$. Đây chính là chuyện của mọi bảng «theo giờ», «theo
killzone», «theo ngày trong tuần».

**Định nghĩa.**
- **Kiểm định nhiều lần (multiple testing)**: chạy $m$ kiểm định rồi báo những cái có p nhỏ.
- **FWER (family-wise error rate)**: xác suất có ít nhất một dương tính giả. Hiệu chỉnh **Bonferroni**: chỉ nhận $p \le \alpha/m$ —
  chặt, an toàn, mất nhiều lực.
- **FDR (false discovery rate, tỷ lệ phát hiện sai)**: trong những gì bạn tuyên bố «có ý nghĩa», tỷ lệ kỳ vọng là sai.
  **Benjamini–Hochberg (BH)** giữ FDR ≤ $q$: xếp p tăng dần $p_{(1)} \le \dots \le p_{(m)}$, tìm $i$ lớn nhất có
  $p_{(i)} \le q \cdot i / m$, nhận $i$ giả thuyết đầu. Nghĩa là p nhỏ nhất phải qua ngưỡng $q/m$, p nhỏ thứ hai qua $2q/m$…

Câu hỏi thật: «có giờ nào trong ngày (giờ New York) mà nến M15 vàng tăng nhiều hơn không?». Giờ 17 New York là giờ nghỉ, nên chỉ
có 23 giờ để thử.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
t = pd.DataFrame({"tang": (df.close > df.open).values, "gio": df.index.tz_convert("America/New_York").hour})
g = t.groupby("gio").tang.agg(["sum", "size"])
k, n = g["sum"].values, g["size"].values

def p_ty_le(k, n, p0):
    z = (k / n - p0) / np.sqrt(p0 * (1 - p0) / n)
    return 2 * stats.norm.sf(np.abs(z))

g["ty_le"] = (k / n).round(3)
g["p_vs_50"] = p_ty_le(k, n, 0.5).round(4)
print("Số giờ được thử:", len(g), "· giờ có p < 0.05:", g.index[g.p_vs_50 < 0.05].tolist())
print(g[g.p_vs_50 < 0.05].to_string())

# Nếu MỌI giờ là đồng xu công bằng thì sao? Mô phỏng 10 000 "năm giả", cùng số nến mỗi giờ
rng = np.random.default_rng(7)
k_gia = rng.binomial(n, 0.5, size=(10_000, len(n)))
so_gio = (p_ty_le(k_gia, n, 0.5) < 0.05).sum(axis=1)
print("Năm giả (50%%): TB %.2f giờ «có ý nghĩa» · ≥ 1 giờ: %.0f%% · ≥ 5 giờ: %.2f%%"
      % (so_gio.mean(), 100 * (so_gio >= 1).mean(), 100 * (so_gio >= 5).mean()))

# Câu hỏi đúng hơn: giờ X có khác MỨC CHUNG của cả kỳ không?
p_chung = k.sum() / n.sum()
g["p_vs_chung"] = p_ty_le(k, n, p_chung).round(4)
print("So với mức chung %.4f: giờ có p < 0.05: %s" % (p_chung, g.index[g.p_vs_chung < 0.05].tolist()))
k_gia = rng.binomial(n, p_chung, size=(10_000, len(n)))          # mọi giờ cùng một tỷ lệ
p_chung_gia = k_gia.sum(axis=1, keepdims=True) / n.sum()          # mức chung ước lượng lại trong từng năm giả
so_gio = (p_ty_le(k_gia, n, p_chung_gia) < 0.05).sum(axis=1)
print("Năm giả (mọi giờ như nhau): TB %.2f giờ · ≥ 3 giờ: %.0f%%" % (so_gio.mean(), 100 * (so_gio >= 3).mean()))

def benjamini_hochberg(p, q=0.05):
    m = len(p)
    thu_tu = np.argsort(p)
    nguong = q * np.arange(1, m + 1) / m          # p nhỏ thứ i phải ≤ q · i / m
    dat = p[thu_tu] <= nguong
    so_giu = (np.max(np.nonzero(dat)[0]) + 1) if dat.any() else 0
    giu = np.zeros(m, bool)
    giu[thu_tu[:so_giu]] = True
    return giu

for cot in ["p_vs_50", "p_vs_chung"]:
    p = g[cot].values
    print("%-10s p nhỏ nhất %.4f · ngưỡng BH cho nó %.4f · số giờ giữ lại sau BH: %d"
          % (cot, p.min(), 0.05 / len(p), benjamini_hochberg(p).sum()))
```

```text
Kết quả khi mình chạy:
Số giờ được thử: 23 · giờ có p < 0.05: [3, 6, 7, 18, 23]
     sum  size  ty_le  p_vs_50
gio
3    318   692  0.460   0.0333
6    375   692  0.542   0.0275
7    320   692  0.462   0.0481
18   374   692  0.540   0.0333
23   382   692  0.552   0.0062
Năm giả (50%): TB 1.19 giờ «có ý nghĩa» · ≥ 1 giờ: 71% · ≥ 5 giờ: 0.42%
So với mức chung 0.5101: giờ có p < 0.05: [3, 7, 23]
Năm giả (mọi giờ như nhau): TB 1.01 giờ · ≥ 3 giờ: 8%
p_vs_50    p nhỏ nhất 0.0062 · ngưỡng BH cho nó 0.0022 · số giờ giữ lại sau BH: 0
p_vs_chung p nhỏ nhất 0.0078 · ngưỡng BH cho nó 0.0022 · số giờ giữ lại sau BH: 0
```

Đọc theo ba bước:
1. **So với 50%**: 5 giờ «có ý nghĩa». Nếu mọi giờ là đồng xu công bằng, trung bình 1.19 giờ lọt lưới do may, 71% số năm có ít nhất
   một giờ — nhưng 5 giờ thì chỉ 0.42% số năm. Vậy giả thuyết «mọi giờ 50%» sai thật. Nhưng sai ở chỗ nào? Mục 4 đã trả lời: **cả
   kỳ** lệch lên 51.0% (vàng tăng), kéo cả loạt giờ lên theo.
2. **So với mức chung 51.0%** — câu hỏi đúng cho «giờ X có đặc biệt không»: còn 3 giờ, trong khi năm giả «mọi giờ như nhau» cho trung
   bình 1.01 giờ và 8% số năm có ≥ 3 giờ. Không có gì lạ.
3. **BH**: p nhỏ nhất (0.0062) phải qua ngưỡng 0.05/23 = 0.0022. Không giờ nào giữ lại được, ở cả hai cách hỏi.

Kết luận trung thực: dữ liệu 2024 không cho bằng chứng giờ nào trong ngày có nhiều nến tăng hơn các giờ khác. Một bảng «giờ 23 New
York tăng 55%» trông rất thuyết phục — và đó chính là bảng mà cách đọc thông thường sẽ in ra. Nghiên cứu order flow của lab cũng nói
đúng điều này về bảng killzone: «Đây là 10 lát cắt; với ngần ấy phép thử, một hai ô "có ý nghĩa" là chuyện bình thường»
([`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) §5.5).

**Bẫy hay gặp.**
- **Chỉ báo những ô thắng.** Số phép thử thật gồm mọi thứ bạn đã thử, kể cả những thứ không in ra (7 cách đọc × 4 khung × 2 mã × …).
  Lab giữ «sổ đăng ký mọi lần thử» vì lý do này (module 7).
- **BH giả định các phép thử độc lập hoặc phụ thuộc dương.** Với phép thử phụ thuộc phức tạp có bản Benjamini–Yekutieli chặt hơn.
- **BH bảo vệ khỏi may mắn, không bảo vệ khỏi lỗi dữ liệu hay đổi chế độ thị trường.** Bài tập 2: một giờ qua BH trên 6 năm dữ liệu
  hoá ra là hiện tượng của nến phẳng; một giờ khác đổi chiều ở năm sau.

## 6. Bootstrap: từ iid tới bootstrap khối

**Trực giác.** Công thức sai số chuẩn chỉ có cho vài thống kê đơn giản. Với trung vị, F1, «lợi thế so với mốc» thì sao? Ý tưởng
**bootstrap**: coi mẫu bạn có là «cả thế giới», rút lại từ nó nhiều mẫu mới cùng cỡ (có hoàn lại), tính thống kê trên mỗi mẫu; độ
phân tán của các kết quả đó xấp xỉ sai số chuẩn.

**Định nghĩa.**
- **Bootstrap iid**: rút $n$ quan sát **có hoàn lại** từ $n$ quan sát gốc, tính thống kê, lặp $B$ lần (vd 2000). Độ lệch chuẩn của
  $B$ giá trị ≈ SE; phân vị 2.5% và 97.5% cho **KTC phân vị (percentile CI)**. «iid» = các quan sát **độc lập, cùng phân phối**.
- **Tự tương quan (autocorrelation)** ở trễ $k$: tương quan giữa chuỗi và chính nó dời $k$ bước. Lợi suất có tự tương quan gần 0;
  **|lợi suất|** (độ lớn biến động) thì không — nến sôi động đi thành chùm (module 4).
- **Bootstrap khối (block bootstrap)**: rút **đoạn liền** $L$ quan sát (khối) thay vì từng quan sát lẻ, ghép đủ $n$. Bên trong khối,
  quan hệ giữa các nến liền nhau được giữ nguyên. Bản «moving block» chọn điểm đầu khối ngẫu nhiên; bản «theo cụm» rút nguyên ngày /
  tuần có hoàn lại.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()
r = (r[df.index.to_series().diff() == pd.Timedelta(minutes=15)] * 1e4).values    # bp
a = np.abs(r)                                                                     # |r|: một thước đo biến động
n = len(r)
rng = np.random.default_rng(11)
B = 2000

# Bootstrap iid: rút n nến CÓ HOÀN LẠI, tính lại trung bình, lặp B lần
chi_so = rng.integers(0, n, size=(B, n))
tb_r = r[chi_so].mean(axis=1)
print("Trung bình r  = %.3f bp · SE công thức %.3f · SE bootstrap %.3f · KTC 95%% bootstrap [%.3f, %.3f]"
      % (r.mean(), r.std(ddof=1) / np.sqrt(n), tb_r.std(ddof=1), *np.percentile(tb_r, [2.5, 97.5])))

def se_khoi(x, L, B, rng):
    """Bootstrap khối chồng (moving block): ghép các đoạn liền L nến, bắt đầu ngẫu nhiên, tới đủ n."""
    n = len(x)
    so_khoi = int(np.ceil(n / L))
    dau = rng.integers(0, n - L + 1, size=(B, so_khoi))
    idx = (dau[:, :, None] + np.arange(L)).reshape(B, -1)[:, :n]
    return x[idx].mean(axis=1).std(ddof=1)

print(" L (nến)   SE của TB r   SE của TB |r|")
for L in [1, 4, 24, 96, 480]:
    print("%7d   %11.3f   %13.3f" % (L, se_khoi(r, L, B, rng), se_khoi(a, L, B, rng)))

def tu_tuong_quan(x, tre):
    x = x - x.mean()
    return (x[:-tre] * x[tre:]).sum() / (x * x).sum()
print("Tự tương quan trễ 1 / 4 / 96 nến:  r %s · |r| %s"
      % ([round(float(tu_tuong_quan(r, k)), 3) for k in (1, 4, 96)], [round(float(tu_tuong_quan(a, k)), 3) for k in (1, 4, 96)]))
```

```text
Kết quả khi mình chạy:
Trung bình r  = 0.091 bp · SE công thức 0.075 · SE bootstrap 0.074 · KTC 95% bootstrap [-0.057, 0.233]
 L (nến)   SE của TB r   SE của TB |r|
      1         0.076           0.057
      4         0.075           0.075
     24         0.074           0.117
     96         0.076           0.149
    480         0.072           0.253
Tự tương quan trễ 1 / 4 / 96 nến:  r [-0.016, -0.011, -0.012] · |r| [0.267, 0.189, 0.116]
```

Ba điều cần thấy:
- Với trung bình lợi suất, bootstrap iid cho đúng SE của công thức (0.074 so với 0.075), và KTC [−0.057, +0.233] bp chứa 0: ở khung M15,
  xu hướng tăng 21% của vàng không phân biệt được với «trung bình 0».
- **Lợi suất** gần như không tự tương quan, nên khối dài hay ngắn SE vẫn ~0.075. **|r|** có tự tương quan 0.27 ở trễ 1 và vẫn 0.12
  sau 96 nến (một ngày): SE thật của trung bình |r| là 0.149 với khối 1 ngày, 0.253 với khối 1 tuần — **gấp 2.6–4.4 lần** con số iid
  0.057. Bootstrap iid ở đây tự tin gấp mấy lần mức đáng có.
- Hầu hết thứ lab đo (swing, sweep, shift, «lợi thế so với mốc») gắn với biến động, nên dính chùm như |r|. Vì vậy nghiên cứu order
  flow tính KTC bằng **bootstrap theo khối tuần**: rút nguyên tuần có hoàn lại
  ([`research/orderflow_survey.py`](../../research/orderflow_survey.py)). Module 3 dùng bootstrap khối để dựng chuỗi giá mô phỏng giữ
  biến động; module 4 đo tự tương quan kỹ hơn.

**Bẫy hay gặp.**
- **Khối quá ngắn** thì vẫn như iid; **quá dài** thì còn ít khối độc lập (8 tháng chỉ có ~35 tuần) và SE ước lượng kém chính xác.
  Cách thực dụng (danh mục quant R7-17): khối = 1 ngày giao dịch hoặc 1 tuần, và thử cả hai.
- **Bootstrap không tạo ra thông tin mới.** Mẫu gốc thiếu một chế độ thị trường (vd không có cú sập 2020) thì bootstrap cũng không có.
- **Bootstrap của một thống kê đã được chọn** (cấu hình tốt nhất trong 50 cấu hình) cho KTC quá đẹp: lỗi chọn lọc xảy ra trước
  bootstrap (module 7).

## 7. Cỡ hiệu ứng, lực thống kê và MDE

**Trực giác.** Kiểm định trả lời «có khác 0 không»; câu hỏi quan trọng hơn là «khác **bao nhiêu**» và «nếu có khác bằng chừng ấy,
mẫu của mình có đủ lớn để thấy không». Một nghiên cứu không thấy gì có thể vì không có gì để thấy, hoặc vì kính lúp quá mờ.

**Định nghĩa.**
- **Cỡ hiệu ứng (effect size)**: độ lớn của khác biệt, theo đơn vị có nghĩa — vd «lợi thế +0.5 điểm %», «F1 thực − F1 ngẫu nhiên TB».
  Không phải $z$ hay p (hai thứ đó lớn lên theo $n$).
- **Lực thống kê (power)**: nếu hiệu ứng thật có cỡ $\delta$, xác suất phép thử của bạn cho «p < α». Lực = 1 − P(sai lầm loại II).
- **Hiệu ứng nhỏ nhất phát hiện được (minimum detectable effect, MDE)**: cỡ hiệu ứng mà phép thử bắt được với lực 80%:
  $$\text{MDE} \approx (z_{1-\alpha/2} + z_{1-\beta})\cdot SE = (1.96 + 0.84)\cdot SE = 2.80 \cdot SE$$
  Hiệu ứng nhỏ hơn MDE vẫn có thể tồn tại — chỉ là phép thử thường bỏ lỡ nó. Với tỷ lệ quanh 50%: $SE = 0.5/\sqrt n$, nên
  $n \approx (1.4/\text{MDE})^2$: muốn thấy 2 điểm % cần ~4900 quan sát độc lập, 5 điểm % cần ~780.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

z_a, z_b = stats.norm.ppf(0.975), stats.norm.ppf(0.80)       # α = 5% hai phía, lực 80%
print("hệ số MDE = %.2f + %.2f = %.2f" % (z_a, z_b, z_a + z_b))

# 1) Tỷ lệ nến tăng quanh 50%: hiệu ứng nhỏ nhất phát hiện được với n nến
for n in [692, 15850]:
    se = np.sqrt(0.25 / n)
    print("n = %5d · SE = %.2f điểm %% · MDE ≈ %.1f điểm %%" % (n, 100 * se, 100 * (z_a + z_b) * se))

# 2) Lực bằng mô phỏng: một giờ (692 nến) có tỷ lệ tăng thật p — bao nhiêu lần ta bắt được?
rng = np.random.default_rng(5)
for p_that in [0.53, 0.553]:
    k = rng.binomial(692, p_that, size=20_000)
    z = (k / 692 - 0.5) / np.sqrt(0.25 / 692)
    print("p thật %.3f: lực = %.0f%% số lần p < 0.05" % (p_that, 100 * (2 * stats.norm.sf(np.abs(z)) < 0.05).mean()))

# 3) Nghiên cứu order flow (docs/research/nghien_cuu_orderflow_ict.md §5): lợi thế, KTC 95% (bootstrap khối tuần), n
for ten, uoc, lo, hi, n in [("XAUUSD M15 run + shift 2018–2023", 0.5, -1.0, 2.2, 1977),
                            ("EURUSD M15 run + shift 2018–2023", -1.9, -3.4, -0.6, 2168),
                            ("XAUUSD M15 run + shift 01–08/2024", -1.4, -6.4, 3.3, 219),
                            ("XAUUSD shift trong London 2018–2023", 4.9, -1.3, 11.4, 176)]:
    se = (hi - lo) / (2 * z_a)                 # SE suy từ độ rộng KTC
    print("%-36s lợi thế %+5.1f · SE ≈ %.2f · MDE ≈ %4.1f điểm %% · n %d" % (ten, uoc, se, (z_a + z_b) * se, n))

# 4) Bộ nhãn 2 tuần: có bao nhiêu swing cấu trúc (ITH/ITL) để chấm recall?
ev = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
so_tuan = (pd.Timestamp("2024-08-31") - pd.Timestamp("2024-01-01")).days / 7
n_nhan = ev.structure_type.isin(["SWING_HIGH_L2", "SWING_LOW_L2"]).sum() / so_tuan * 2
se = np.sqrt(0.6 * 0.4 / n_nhan)
print("≈ %.0f swing cấu trúc / 2 tuần → recall 60%%: SE ≈ %.1f điểm %% · MDE ≈ %.0f điểm %% (lạc quan: coi swing độc lập)"
      % (n_nhan, 100 * se, 100 * (z_a + z_b) * se))
```

```text
Kết quả khi mình chạy:
hệ số MDE = 1.96 + 0.84 = 2.80
n =   692 · SE = 1.90 điểm % · MDE ≈ 5.3 điểm %
n = 15850 · SE = 0.40 điểm % · MDE ≈ 1.1 điểm %
p thật 0.530: lực = 36% số lần p < 0.05
p thật 0.553: lực = 80% số lần p < 0.05
XAUUSD M15 run + shift 2018–2023     lợi thế  +0.5 · SE ≈ 0.82 · MDE ≈  2.3 điểm % · n 1977
EURUSD M15 run + shift 2018–2023     lợi thế  -1.9 · SE ≈ 0.71 · MDE ≈  2.0 điểm % · n 2168
XAUUSD M15 run + shift 01–08/2024    lợi thế  -1.4 · SE ≈ 2.47 · MDE ≈  6.9 điểm % · n 219
XAUUSD shift trong London 2018–2023  lợi thế  +4.9 · SE ≈ 3.24 · MDE ≈  9.1 điểm % · n 176
≈ 102 swing cấu trúc / 2 tuần → recall 60%: SE ≈ 4.9 điểm % · MDE ≈ 14 điểm % (lạc quan: coi swing độc lập)
```

**Đọc lại «±2 điểm %» của nghiên cứu order flow.**
- Với các mẫu lớn (2018–2023, ~2000 lần lật), MDE khoảng 2–2.3 điểm %. Nghĩa là: **nếu** order flow có lợi thế từ ~2.3 điểm % trở
  lên, nghiên cứu này có 80% khả năng thấy nó. Không thấy → lợi thế cỡ đó trở lên khó có. KTC [−1.0, +2.2] của XAUUSD nói cụ thể hơn:
  lợi thế thật (theo định nghĩa đo này) nhiều khả năng nằm trong khoảng đó. Lợi thế 1 điểm % thì **không loại trừ được** — và ở mức
  đó, chi phí giao dịch (module 8) nuốt trọn.
- Ô EURUSD −1.9 [−3.4, −0.6] có KTC không chứa 0 — nhưng là một ô trong hàng chục ô đã thử, và ngược hướng ICT dự đoán. Mục 5 dạy ta
  không đọc ô lẻ.
- **London +4.9, n = 176**: MDE ≈ 9 điểm %. Lợi thế 5 điểm % thật thì phép thử này phần lớn sẽ bỏ lỡ; KTC [−1.3, +11.4] rộng tới mức
  chứa cả 0 lẫn một lợi thế lớn. Đó là lý do nghiên cứu gọi nó là «giả thuyết đáng kiểm thêm, chưa phải phát hiện». Bài tập 4 tính
  cần bao nhiêu năm dữ liệu.
- 2024 riêng (n = 219): MDE ~7 điểm % — mẫu một năm không đủ để xác nhận hay bác bỏ gì nhỏ hơn thế.

**Nối với chuẩn ngẫu nhiên `matched_hour_atr_v1` của trang Đánh giá**
([`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.3):
- **$H_0$** ở đây là «thuật toán không hơn sự kiện ngẫu nhiên đặt cùng giờ New York, cùng nhóm ATR». Mỗi lượt ngẫu nhiên cho một F1;
  $N$ lượt (mặc định 200) cho **phân phối của F1 dưới $H_0$**. Cỡ hiệu ứng = F1 thực − F1 ngẫu nhiên TB.
- `p_ge = (1 + số lượt ≥ thực tế) / (N + 1)` là một **p-value mô phỏng** — cùng ý với «số năm giả lệch ít nhất bằng năm thật» ở mục 4.
  Số «+1» giữ p không bao giờ bằng 0: với $N = 200$, p nhỏ nhất là 1/201 ≈ 0.005. So 20 cấu hình với Bonferroni cần
  $p \le 0.05/20 = 0.0025$, tức phải tăng $N$ lên ít nhất 399.
- Vì sao ghép **cùng giờ × cùng nhóm ATR**: swing và nhãn dồn vào giờ sôi động (module 1 mục 7). Đặt sự kiện ngẫu nhiên đều khắp ngày
  sẽ rơi nhiều vào giờ vắng, làm F1 ngẫu nhiên thấp giả tạo — cỡ hiệu ứng phồng lên. $H_0$ phải giữ đúng những gì «không phải kỹ
  năng»; module 3 dựng những $H_0$ như vậy.
- Bộ nhãn 2 tuần (~100 swing cấu trúc): MDE cho recall cỡ 14 điểm % — và đó là con số lạc quan vì swing không độc lập. Hai thuật toán
  chênh nhau vài điểm F1 trên một bộ nhãn như vậy là **không phân biệt được**. Muốn so tinh hơn phải có nhiều nhãn hơn, và KTC
  bootstrap theo ngày cho P/R/F1 (trang Đánh giá §6 ghi là việc chưa làm).

**Bẫy hay gặp.**
- **«Không có ý nghĩa» = «không có hiệu ứng».** Sai khi lực thấp. Luôn kèm KTC hoặc MDE.
- **Tính lực sau khi đã có kết quả** («lực quan sát được») — vòng lặp vô nghĩa. Tính MDE **trước** khi chạy thí nghiệm để biết mẫu
  có đủ không.
- **Dùng SE iid để tính MDE cho dữ liệu dính chùm** — MDE thật lớn hơn (mục 6).

## Lab đang dùng những điều này ở đâu

| Khái niệm | File / tài liệu của lab | Ghi chú |
|---|---|---|
| p-value mô phỏng, cỡ hiệu ứng so với chuẩn ngẫu nhiên | [`core/eval/null_baseline.py`](../../core/eval/null_baseline.py), [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.3 | `p_ge = (1 + số lượt ≥)/(N + 1)`, phân phối F1 qua N lượt (TB, sd, P5–P95) |
| Sai số chuẩn của tỷ lệ (P/R) | [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.3, §6 | $\sqrt{p(1-p)/n}$ «lạc quan»; bootstrap cho P/R/F1 chưa làm |
| Bootstrap theo khối tuần, KTC 95% | [`research/orderflow_survey.py`](../../research/orderflow_survey.py), [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) §4 | 2000 lần, seed 7 |
| Thử nhiều lát cắt, «một hai ô có ý nghĩa là bình thường» | [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) §5.5, §6 | Giả thuyết London phải khai báo trước rồi kiểm trên đoạn chưa dùng |
| Đoạn phát triển / kiểm tra, không đọc F1 một mình | [`AGENTS.md`](../../AGENTS.md) §6.3, [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.2 | Chống «nhìn dữ liệu rồi mới đặt giả thuyết» |
| Báo cáo kèm số mẫu | [`AGENTS.md`](../../AGENTS.md) §6.3 | «Báo cáo kèm số mẫu, độ trễ, mật độ» |

## Bài tập

**Bài 1 — Khung lớn hơn.** Với XAUUSD 2018–2023, tính cho M15, H1, D1: độ lệch chuẩn, kurtosis dư, số lợi suất $|z| > 4$ (so với
phân phối chuẩn), và tỷ lệ nến tăng kèm KTC 95%, p-value so với 50%. Kurtosis đổi thế nào khi gộp khung? Vàng tăng từ 1317 lên 2063
USD trong 6 năm — tỷ lệ ngày tăng có «có ý nghĩa» không, và điều đó nói gì?
*Gợi ý:* M15 và H1 chỉ lấy cặp nến liền nhau; D1 lấy mọi cặp ngày giao dịch liên tiếp.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

for ten, ds, buoc in [("M15", XAU_M15_DAI, "15min"), ("H1", XAU_H1, "1h"), ("D1", XAU_D1, None)]:
    df = nap_nen(ds, "2018-01-01", "2024-01-01")
    r = np.log(df.close).diff()
    if buoc:                                   # M15, H1: chỉ cặp nến liền nhau; D1: mọi cặp ngày giao dịch liên tiếp
        r = r[df.index.to_series().diff() == pd.Timedelta(buoc)]
    r = r.dropna().values * 1e4
    z = (r - r.mean()) / r.std()
    tang = (df.close > df.open).values
    n, p = len(tang), tang.mean()
    se = np.sqrt(p * (1 - p) / n)
    p_value = 2 * stats.norm.sf(abs(p - 0.5) / np.sqrt(0.25 / n))
    print("%-3s sd %5.1f bp · kurtosis dư %5.1f · |z|>4: %4d (chuẩn: %4.1f) · nến tăng %.4f [%.4f, %.4f] · p %.3f"
          % (ten, r.std(), stats.kurtosis(r), (np.abs(z) > 4).sum(), len(r) * 2 * stats.norm.sf(4),
             p, p - 1.96 * se, p + 1.96 * se, p_value))
d1 = nap_nen(XAU_D1, "2018-01-01", "2024-01-01")
print("XAUUSD D1: close đầu %.2f → cuối %.2f" % (d1.close.iloc[0], d1.close.iloc[-1]))
m15 = nap_nen(XAU_M15_DAI, "2018-01-01", "2024-01-01")
r = np.log(m15.close).diff()[m15.index.to_series().diff() == pd.Timedelta("15min")] * 1e4
lon = ((r - r.mean()) / r.std()).abs().nlargest(2).index
print("Hai nến M15 lớn nhất:", [(t.tz_convert("America/New_York").strftime("%a %d/%m/%Y %H:%M NY"), round(float(r[t]), 1)) for t in lon])
```

```text
Kết quả khi mình chạy:
M15 sd   9.3 bp · kurtosis dư  56.1 · |z|>4: 1046 (chuẩn:  8.9) · nến tăng 0.4999 [0.4973, 0.5025] · p 0.920
H1  sd  18.4 bp · kurtosis dư  16.6 · |z|>4:  277 (chuẩn:  2.2) · nến tăng 0.5018 [0.4966, 0.5070] · p 0.487
D1  sd  87.5 bp · kurtosis dư   3.8 · |z|>4:    8 (chuẩn:  0.1) · nến tăng 0.5226 [0.4977, 0.5475] · p 0.075
XAUUSD D1: close đầu 1317.23 → cuối 2062.73
Hai nến M15 lớn nhất: [('Sun 08/08/2021 18:45 NY', -418.9), ('Sun 03/12/2023 18:15 NY', 259.8)]
```

Kurtosis giảm mạnh khi gộp khung (56 → 17 → 3.8): cộng nhiều lợi suất nhỏ làm phân phối «tròn» lại, nhưng D1 vẫn đuôi dày (8 ngày vượt
4σ so với 0.1). Kurtosis M15 2018–2023 (56) cao hơn hẳn 2024 (13.4, mục 1) chủ yếu vì hai nến tối Chủ nhật, ngay sau giờ mở phiên lúc
thanh khoản mỏng: −419 bp (khoảng 45σ) ngày 08/08/2021 và +260 bp ngày 03/12/2023. Hai điểm là đủ đổi kurtosis cả 6 năm — đúng cái bẫy
«kurtosis rất nhạy với vài điểm» ở mục 2.

Tỷ lệ ngày tăng 52.3%, KTC [49.8%, 54.8%], p = 0.075: **không** «có ý nghĩa» ở mức 5%, dù vàng tăng 57%. Điều này không chứng minh vàng
không có xu hướng (điều 4 của mục 4): với 1548 ngày, MDE ≈ 2.8 × 0.5/√1548 ≈ 3.6 điểm %, mà xu hướng dài hạn chỉ dời tỷ lệ ngày tăng
khoảng 2 điểm %. Hơn nữa «tỷ lệ ngày tăng» là thước đo yếu cho xu hướng: nó bỏ qua độ lớn mỗi ngày. Ở M15, tỷ lệ là 49.99% — xu
hướng nhiều năm hoàn toàn vô hình ở từng nến M15.

</details>

**Bài 2 — Khám phá trên 2018–2023, kiểm lại trên 2024.** Lặp lại phép thử «giờ nào có nhiều nến tăng hơn 50%» trên `XAU_M15_DAI`
2018–2023 (mỗi giờ có ~6000 nến nên lực cao hơn nhiều). Áp BH. Những giờ được chọn có giữ được ở 01–08/2024 không? Soi kỹ từng giờ
qua BH: tỷ lệ nến «bằng» (close = open) bao nhiêu, và giờ 18 tách theo từng nến 15 phút ra sao?
*Gợi ý:* dùng lại `benjamini_hochberg` của mục 5; `pivot_table(index="doan", columns="phut", values="tang")` cho giờ 18.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

def benjamini_hochberg(p, q=0.05):
    m = len(p); o = np.argsort(p)
    dat = p[o] <= q * np.arange(1, m + 1) / m
    so = (np.max(np.nonzero(dat)[0]) + 1) if dat.any() else 0
    giu = np.zeros(m, bool); giu[o[:so]] = True
    return giu

df = nap_nen(XAU_M15_DAI, "2018-01-01", "2024-09-01")
ny = df.index.tz_convert("America/New_York")
t = pd.DataFrame({"tang": (df.close > df.open).values, "bang": (df.close == df.open).values, "gio": ny.hour,
                  "phut": ny.minute, "doan": np.where(df.index < "2024-01-01", "2018-23", "2024")})

def theo_gio(x):
    g = x.groupby("gio").tang.agg(["mean", "size"])
    g["p"] = 2 * stats.norm.sf(np.abs((g["mean"] - 0.5) / np.sqrt(0.25 / g["size"])))
    return g

kham_pha, kiem_lai = theo_gio(t[t.doan == "2018-23"]), theo_gio(t[t.doan == "2024"])
kham_pha["qua_BH"] = benjamini_hochberg(kham_pha.p.values)
chon = kham_pha[kham_pha.p < 0.05].copy()
chon["ty_le_2024"], chon["p_2024"] = kiem_lai["mean"].reindex(chon.index), kiem_lai["p"].reindex(chon.index)
print("2018–2023: %d giờ được thử · %d giờ p < 0.05 · %d giờ qua BH" % (len(kham_pha), len(chon), chon.qua_BH.sum()))
print(chon.round(4).to_string())
# Soi kỹ: tỷ lệ nến "bằng" (close = open) theo giờ, và giờ 18 tách theo từng nến 15 phút
print(t[t.gio.isin([16, 17, 18])].groupby(["gio", "doan"])[["tang", "bang"]].mean().round(3).to_string())
print(t[t.gio == 18].pivot_table(index="doan", columns="phut", values="tang", aggfunc="mean").round(3).to_string())
```

```text
Kết quả khi mình chạy:
2018–2023: 24 giờ được thử · 5 giờ p < 0.05 · 4 giờ qua BH
       mean  size       p  qua_BH  ty_le_2024  p_2024
gio
10   0.5184  6192  0.0038    True      0.5173  0.3616
16   0.4626  5966  0.0000    True      0.5299  0.1217
17   0.0315   127  0.0000    True         NaN     NaN
18   0.5319  6127  0.0000    True      0.5405  0.0333
19   0.5138  6176  0.0305   False      0.5130  0.4938
              tang   bang
gio doan
16  2018-23  0.463  0.009
    2024     0.530  0.000
17  2018-23  0.031  0.827
18  2018-23  0.532  0.006
    2024     0.540  0.001
phut        0      15     30     45
doan
2018-23  0.669  0.542  0.454  0.463
2024     0.665  0.532  0.451  0.514
```

Bốn giờ qua BH. Từng giờ một:
- **Giờ 17** (127 nến, 3% tăng): 83% là nến «bằng». Đây là 127 nến lẻ năm 2018 chỉ có một tick lúc đúng 17:00 New York (tài liệu
  pipeline §5 ghi rõ) — **lỗi định nghĩa + dữ liệu**, không phải hành vi thị trường. BH không bắt được loại này.
- **Giờ 16** (46.3% tăng 2018–2023) **đổi chiều** ở 2024 (53.0%). Không lặp lại.
- **Giờ 10** (51.8%) giữ hướng ở 2024 (51.7%) nhưng 2024 không đủ lực để xác nhận (p = 0.36; MDE cho một giờ trong 8 tháng ≈ 5 điểm %).
- **Giờ 18** giữ cả hai đoạn — và hiệu ứng nằm gần hết ở **một nến**: nến 18:00 New York (nến mở phiên) tăng 66.9% rồi 66.5%. Giả
  thuyết hợp lý nhất (chưa kiểm được vì dữ liệu không có Ask): lúc mở phiên spread rất rộng nên giá **Bid** đầu phiên bị đè thấp, rồi
  nhích lên khi spread thu hẹp — một hiện tượng của **dữ liệu Bid** (module 1 mục 1), không phải lực mua. Không giao dịch được: muốn
  mua phải trả Ask.

Bài học: «có ý nghĩa, qua BH, lặp lại ngoài mẫu» vẫn chưa đủ. Phải hỏi **cơ chế** và kiểm dữ liệu trước khi tin.

</details>

**Bài 3 — Khi nào bootstrap khối đổi kết quả?** Với XAUUSD M15 01–08/2024, tính SE của hai tỷ lệ: «nến tăng» và «nến có biên độ
> 2 × biên độ trung vị», theo ba cách: công thức, bootstrap iid, bootstrap **theo ngày giao dịch** (rút nguyên ngày có hoàn lại).
Vì sao hai tỷ lệ cư xử khác nhau?
*Gợi ý:* gom chỉ số nến theo ngày giao dịch (module 1 mục 2); với mỗi lượt, rút ngẫu nhiên các ngày, tỷ lệ = tổng / tổng số nến.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
bien_do = (df.high - df.low).values
nguong = 2 * np.median(bien_do)
cac_chi_bao = {"nến tăng": (df.close > df.open).values.astype(float),
               "nến biên độ > 2 × trung vị": (bien_do > nguong).astype(float)}
ngay = (df.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).date      # ngày giao dịch
nhom = pd.Series(np.arange(len(df))).groupby(ngay).apply(np.array).tolist()         # chỉ số nến của từng ngày
rng = np.random.default_rng(21)
B = 2000
for ten, x in cac_chi_bao.items():
    n = len(x)
    p = x.mean()
    se_cong_thuc = np.sqrt(p * (1 - p) / n)
    tb_iid = x[rng.integers(0, n, size=(B, n))].mean(axis=1)
    # bootstrap theo NGÀY: rút ngày có hoàn lại (giữ nguyên thứ tự nến trong ngày)
    tong_ngay = np.array([x[i].sum() for i in nhom]); so_nen_ngay = np.array([len(i) for i in nhom])
    chon = rng.integers(0, len(nhom), size=(B, len(nhom)))
    tb_ngay = tong_ngay[chon].sum(axis=1) / so_nen_ngay[chon].sum(axis=1)
    print("%-28s tỷ lệ %.4f · SE công thức %.4f · iid %.4f · theo ngày %.4f (gấp %.1f lần)"
          % (ten, p, se_cong_thuc, tb_iid.std(), tb_ngay.std(), tb_ngay.std() / tb_iid.std()))
```

```text
Kết quả khi mình chạy:
nến tăng                     tỷ lệ 0.5101 · SE công thức 0.0040 · iid 0.0040 · theo ngày 0.0037 (gấp 0.9 lần)
nến biên độ > 2 × trung vị   tỷ lệ 0.1415 · SE công thức 0.0028 · iid 0.0028 · theo ngày 0.0082 (gấp 2.9 lần)
```

Dấu của nến gần như không phụ thuộc nến trước, nên rút theo ngày hay rút lẻ cho cùng SE (tỷ số 0.9 nằm trong sai số của chính
bootstrap). «Nến biên độ lớn» dồn vào giờ tin tức và ngày biến động: có ngày 40% nến là nến lớn, có ngày gần như không. Rút theo ngày
giữ cấu trúc đó, và SE thật lớn **gấp 2.9 lần** con số công thức. Một KTC theo công thức cho thứ này hẹp gần ba lần mức đáng có — đúng
loại sai số mà trang Đánh giá gọi là «lạc quan».

</details>

**Bài 4 — Cần bao nhiêu dữ liệu cho giả thuyết London?** Nghiên cứu order flow: shift trong London, XAUUSD +4.9 [−1.3, +11.4] n 176;
EURUSD +4.0 [−0.8, +8.2] n 306 (cả hai 2018–2023). Giả sử lợi thế thật là 5 điểm %. Cần bao nhiêu lần shift London để có lực 80%?
Với tốc độ hiện tại, bao nhiêu năm dữ liệu?
*Gợi ý:* SE từ KTC; độ phân tán của **một** lần shift = SE × √n; rồi $n = (2.80 \cdot \text{sd} / 5)^2$.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

he_so = stats.norm.ppf(0.975) + stats.norm.ppf(0.80)          # 2.80
# Từ nghiên cứu order flow §5.5: London XAUUSD +4.9 [−1.3, +11.4], n 176; EURUSD +4.0 [−0.8, +8.2], n 306
for ten, lo, hi, n in [("XAUUSD", -1.3, 11.4, 176), ("EURUSD", -0.8, 8.2, 306)]:
    se = (hi - lo) / (2 * 1.96)                 # điểm %
    sd_mot_lan = se * np.sqrt(n)                # độ phân tán của MỘT lần shift (điểm %)
    can = (he_so * sd_mot_lan / 5.0) ** 2       # n để MDE = 5 điểm %
    print("%s: SE %.2f · sd một lần %.1f điểm %% · cần n ≈ %.0f shift London để MDE = 5 điểm %% · có %d trong 6 năm → cần ≈ %.0f năm"
          % (ten, se, sd_mot_lan, can, n, can / (n / 6)))
```

```text
Kết quả khi mình chạy:
XAUUSD: SE 3.24 · sd một lần 43.0 điểm % · cần n ≈ 580 shift London để MDE = 5 điểm % · có 176 trong 6 năm → cần ≈ 20 năm
EURUSD: SE 2.30 · sd một lần 40.2 điểm % · cần n ≈ 506 shift London để MDE = 5 điểm % · có 306 trong 6 năm → cần ≈ 10 năm
```

Cần ~500–580 lần shift London: khoảng 20 năm XAUUSD hoặc 10 năm EURUSD với định nghĩa hiện tại. Đoạn kiểm tra của lab (09–12/2024) theo
tốc độ 2018–2023 chỉ có khoảng 10 (XAUUSD) đến 17 (EURUSD) lần — đủ để thấy một lợi thế **rất lớn**, không đủ để xác nhận 5 điểm %. Đây là phép tính nên làm **trước** khi mở khoá
đoạn kiểm tra: nếu mẫu không đủ lực, mở khoá chỉ tiêu tốn đoạn kiểm tra mà không trả lời được câu hỏi. (SE suy từ KTC bootstrap tuần
là xấp xỉ: KTC phân vị không hoàn toàn đối xứng.)

</details>

## Tự kiểm

**1.** Lợi suất M15 vàng 2024 có kurtosis dư 13.4. Điều đó nói gì về số cú lớn hơn 4 độ lệch chuẩn so với phân phối chuẩn?
<details><summary>Đáp án</summary>

Đuôi dày: cú cực đoan nhiều hơn hẳn phân phối chuẩn. Đếm thật: 123 nến vượt 4σ trong 8 tháng, phân
phối chuẩn chỉ cho ~1.

</details>

**2.** Một bạn nói: «p = 0.011 nghĩa là chỉ có 1.1% khả năng tỷ lệ nến tăng thật sự là 50%». Sai ở đâu?
<details><summary>Đáp án</summary>

p-value là xác suất thấy dữ liệu lệch ít nhất như vậy **nếu** tỷ lệ thật là 50% —
$P(\text{dữ liệu} \mid H_0)$, không phải $P(H_0 \mid \text{dữ liệu})$. Muốn có xác suất của giả thuyết phải biết thêm có bao nhiêu
giả thuyết thật trong số được thử (ví dụ 1000 ý tưởng ở mục 4).

</details>

**3.** KTC 95% của tỷ lệ nến tăng là [50.2%, 51.8%]. Câu nào đúng: (a) tỷ lệ thật có 95% xác suất nằm trong khoảng này; (b) quy trình
dựng khoảng này chứa tỷ lệ thật trong khoảng 95% số lần áp dụng?
<details><summary>Đáp án</summary>

(b). Tỷ lệ thật là một số cố định; khoảng mới là thứ ngẫu nhiên. Mô phỏng ở mục 3: 94.8% số khoảng
chứa tỷ lệ thật.

</details>

**4.** Bạn thử 30 killzone × biến thể, 3 cái có p < 0.05. Trước khi vui, bạn cần làm gì?
<details><summary>Đáp án</summary>

So với số «có ý nghĩa» kỳ vọng do may: 30 × 0.05 = 1.5. Áp BH (p nhỏ nhất phải ≤ 0.05/30 ≈ 0.0017).
Kiểm dữ liệu và cơ chế của từng ô (bài tập 2). Rồi khai báo trước đúng một giả thuyết và kiểm trên dữ liệu chưa dùng.

</details>

**5.** Vì sao bootstrap iid cho SE của trung bình lợi suất đúng, nhưng cho SE của trung bình |lợi suất| sai?
<details><summary>Đáp án</summary>

Lợi suất gần như không tự tương quan (−0.016 ở trễ 1), nên các nến gần như độc lập. |Lợi suất| tự
tương quan dương (0.27 ở trễ 1, vẫn 0.12 sau một ngày): nến sôi động đi thành chùm. Rút lẻ phá chùm đó → SE nhỏ giả tạo (0.057 so
với 0.149 khi rút khối một ngày).

</details>

**6.** Nghiên cứu order flow: XAUUSD M15 run + shift +0.5 [−1.0, +2.2], n 1977. Kết luận nào được phép: (a) order flow không có tác
dụng gì; (b) lợi thế, nếu có, nhiều khả năng dưới ~2 điểm %; (c) lợi thế là +0.5 điểm %.
<details><summary>Đáp án</summary>

(b). (a) quá mạnh — một lợi thế 1 điểm % không bị loại trừ (MDE ≈ 2.3). (c) bỏ qua sai số — +0.5 chỉ
là ước lượng điểm, KTC chứa cả 0 lẫn +2.2.

</details>

**7.** Với chuẩn ngẫu nhiên N = 200 lượt, F1 thực tế cao hơn **mọi** lượt. `p_ge` bằng bao nhiêu? Có thể nhỏ hơn không?
<details><summary>Đáp án</summary>

p_ge = (1 + 0)/(200 + 1) ≈ 0.005 — mức nhỏ nhất với N = 200. Muốn nhỏ hơn phải tăng N (tối đa 1000 →
≈ 0.001). Và p_ge nhỏ vẫn chưa nói F1 hơn bao nhiêu: đọc cỡ hiệu ứng F1 thực − F1 ngẫu nhiên TB.

</details>

## Đọc thêm

- James, Witten, Hastie, Tibshirani, Taylor, *An Introduction to Statistical Learning (with Applications in Python)* — chương về
  resampling (bootstrap) và chương về kiểm định nhiều lần (FWER, FDR, Benjamini–Hochberg).
- David Aronson, *Evidence-Based Technical Analysis* — kiểm định luật kỹ thuật bằng chuẩn ngẫu nhiên, thiên lệch do đào dữ liệu (data
  mining bias); gần nhất với bài toán ICT của lab.
- Ruey Tsay, *Analysis of Financial Time Series* — chương 1: phân phối lợi suất, đuôi dày, kiểm định trên lợi suất.
- Tài liệu lab: [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) §4–§6 (cách đo, KTC bootstrap tuần, diễn
  giải); [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.2–§1.3, §6.
- Danh mục quant ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md)): R7-14 (Benjamini–Hochberg), R7-15
  (Benjamini–Yekutieli), R7-17 (bootstrap khối theo ngày / tuần), R7-16 (stationary bootstrap), R7-18 (chọn độ dài khối), R7-19 (kiểm
  định hoán vị, p-value chính xác), R7-29 (cỡ mẫu hiệu dụng và MDE cho chuỗi phụ thuộc), R7-26 (sai số chuẩn HAC).
