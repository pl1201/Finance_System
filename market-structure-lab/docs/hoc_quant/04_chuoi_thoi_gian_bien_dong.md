# Module 4 — Chuỗi thời gian và biến động

> **Sau module này bạn làm được:**
> - Tính tự tương quan của lợi suất và của |lợi suất|, và đọc được vì sao một cái gần 0 còn cái kia dương kéo dài.
> - Tự cài variance ratio Lo–MacKinlay với z-score chịu dị phương sai, và giải thích vì sao z thường báo sai.
> - Dựng bảng biến động theo giờ New York, khử mùa vụ, và giải thích vì sao displacement của lab dồn vào giờ mở phiên.
> - Ước lượng biến động từ OHLC (Parkinson, Garman–Klass, Rogers–Satchell), so với realized variance từ nến M1.
> - Dự báo biến động ngày bằng HAR-RV (OLS numpy) ngoài mẫu, và đo «nén → bung» một cách trung thực.
>
> **Cần trước:** module 1, 2, 3  ·  **Thời lượng:** ~7 giờ

> **Ba điều cần nhớ** (đọc lại khi ôn)
>
> 1. Lợi suất gần như không tự tương quan, còn |lợi suất| thì tự tương quan mạnh và lâu: biến động đoán được, hướng thì không.
> 2. Biến động đổi rất mạnh theo giờ phiên. Phải khử mùa vụ trước khi đo (tự tương quan |r| ở bậc 92 giảm từ 0,151 còn 0,061).
> 3. HAR-RV dự báo biến động ngày tốt hơn «bằng hôm qua» (MSE bằng 0,64 lần); «nén rồi bung» chủ yếu là hồi quy về trung bình.

## Vì sao cần

Mọi ngưỡng của `ict_structure` tính theo ATR: displacement là nến có biên độ ≥ 1.5 ATR, «lấy» thanh khoản là xuyên ≥ 0.1 ATR
([`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §3). Vậy ATR, tức **biến động**, là thước đo nền của cả
thuật toán. Module này trả lời hai câu hỏi. Thứ nhất, cái gì của giá đoán được? Danh mục quant kết luận: «biến động đoán được, hướng
thì gần như không» ở khung trong ngày ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md) §3). Bạn sẽ tự
thấy điều đó bằng số. Thứ hai, vì sao ATR lệch theo giờ? Vì biến động M15 có hình dạng theo phiên, và một trung bình trượt như ATR
luôn chạy sau hình dạng đó. Hệ quả là displacement dồn vào giờ mở phiên. Đề xuất regime hai trục của danh mục (§4) đặt **trục biến
động** (nén · bình thường · bung · nhảy) lên trước trục hướng, vì đó là trục có bằng chứng vững. Module này là nền cho trục đó.

## 1. Tự tương quan: lợi suất gần như không nhớ, |lợi suất| thì nhớ lâu

**Trực giác.** Nhìn chart M15: sau một nến tăng mạnh, nến sau tăng hay giảm thì khó đoán. Nhưng nến sau **to** hay **nhỏ** thì
đoán được: nến to hay đi cạnh nến to. Giờ tin tức ồn ào cả cụm, giờ trưa Á thì lặng cả cụm.

**Định nghĩa.** **Tự tương quan (autocorrelation)** bậc $k$ của chuỗi $x$ là tương quan giữa $x_t$ và $x_{t-k}$:

$$\rho_k = \frac{\sum_t (x_t - \bar x)(x_{t-k} - \bar x)}{\sum_t (x_t - \bar x)^2}$$

Bằng lời: $\rho_k$ đo mức một giá trị «nhớ» giá trị cách nó $k$ bước. Nó nằm trong [−1, 1]; gần 0 là không nhớ. Nếu chuỗi là nhiễu
độc lập thì $\rho_k$ ước lượng từ $n$ điểm dao động quanh 0 trong khoảng $\pm 1.96/\sqrt{n}$ (dải 95%). Áp vào lợi suất $r$ và vào
$|r|$. $|r|$ là thước đo thô của biến động từng nến. Khi $|r|$ có tự tương quan dương kéo dài, ta gọi là **biến động co cụm
(volatility clustering)**.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()
r = r[df.index.to_series().diff() == pd.Timedelta("15min")].to_numpy()   # bỏ lợi suất vắt qua giờ nghỉ

def tu_tuong_quan(x, k):
    """Hệ số tự tương quan bậc k: tương quan giữa x_t và x_{t-k} (trừ trung bình toàn mẫu)."""
    x = x - x.mean()
    return np.sum(x[k:] * x[:-k]) / np.sum(x * x)

rng = np.random.default_rng(0)
nhieu = rng.normal(0, r.std(), len(r))
print("n = %d · dải ±1.96/√n = ±%.3f (dải 95%% nếu chuỗi là nhiễu độc lập)" % (len(r), 1.96 / np.sqrt(len(r))))
print("bậc k    r thật   |r| thật   r ngẫu nhiên  |r| ngẫu nhiên")
for k in (1, 2, 3, 4, 5, 8, 16, 32, 48, 96, 192):
    print("%5d %9.3f %9.3f %12.3f %13.3f" % (k, tu_tuong_quan(r, k), tu_tuong_quan(np.abs(r), k),
                                             tu_tuong_quan(nhieu, k), tu_tuong_quan(np.abs(nhieu), k)))
```

```text
Kết quả khi mình chạy:
n = 15677 · dải ±1.96/√n = ±0.016 (dải 95% nếu chuỗi là nhiễu độc lập)
bậc k    r thật   |r| thật   r ngẫu nhiên  |r| ngẫu nhiên
    1    -0.016     0.267        0.001        -0.012
    2     0.013     0.230        0.014        -0.002
    3     0.004     0.204       -0.001         0.011
    4    -0.011     0.189       -0.009        -0.001
    5     0.013     0.176       -0.019        -0.010
    8     0.010     0.135        0.011         0.009
   16     0.009     0.055        0.013        -0.006
   32     0.008    -0.001        0.010        -0.007
   48     0.002     0.026       -0.002         0.004
   96    -0.012     0.116        0.004        -0.006
  192     0.007     0.060        0.011         0.003
```

Đọc kết quả:

- Cột **r thật** lẫn trong dải ±0.016, như nhiễu. Bậc 1 hơi âm (−0.016): vàng M15 hơi «quay đầu», khớp với P(lên | xuống) = 52.8% ở
  module 3. Chuỗi ngẫu nhiên cũng có lúc chạm dải (−0.019 ở bậc 5). Một vài con số sát mép dải không nói lên gì.
- Cột **|r| thật** dương rõ: 0.267 ở bậc 1, rồi giảm dần qua vài giờ. Biến động co cụm. Chuỗi nhiễu không có tính chất này.
- |r| lại vọt lên 0.116 ở bậc 96 (một ngày) sau khi về 0 ở bậc 32 (8 giờ). Đó là **đồng hồ**: giờ này hôm nay giống giờ này hôm
  qua. Mục 3 tách phần đồng hồ ra.

Đây là câu «biến động đoán được, hướng thì gần như không» bằng số. Mô hình kinh điển cho |r| co cụm là **GARCH**: phương sai nến này
= hằng số + một phần bình phương lợi suất nến trước + một phần phương sai nến trước. Module này không cài GARCH (cần ước lượng hợp
lý cực đại; lab không có thư viện `arch`). Mục 5 dùng HAR, đơn giản hơn và chỉ cần OLS.

**Bẫy hay gặp.**
- Dải ±1.96/√n giả định nhiễu **độc lập, phương sai không đổi**. Lợi suất vàng co cụm nên dải thật rộng hơn. Vì thế một $\rho_1$ sát
  mép không chắc «có ý nghĩa» (mục 2 sửa chuyện này).
- Nối lợi suất vắt qua cuối tuần vào chuỗi: một cú nhảy mở tuần thành «nến» khổng lồ. Code ở trên bỏ chúng.
- Thấy $\rho_1 < 0$ rồi nghĩ ra chiến lược «đánh ngược nến trước». Ở module 3 bạn đã tính: kỳ vọng cỡ 2 cent mỗi nến, nhỏ hơn chi
  phí. Một phần $\rho_1 < 0$ có thể đến từ nhiễu báo giá (giá Bid nhảy qua lại), không phải từ hành vi thị trường.

## 2. Variance ratio: kiểm bước ngẫu nhiên ở nhiều thang cùng lúc

**Trực giác.** Nếu giá là bước ngẫu nhiên thì phương sai của lợi suất 4 nến bằng đúng 4 lần phương sai 1 nến: các cú xóc độc lập
cộng dồn. Có quán tính (trend) thì lợi suất 4 nến **lớn hơn** 4 lần, vì các nến cùng chiều cộng dồn. Hay quay đầu (range) thì **nhỏ
hơn**, vì các nến triệt tiêu nhau.

**Định nghĩa.** **Variance ratio** (Lo–MacKinlay 1988) ở thang $q$:

$$\mathrm{VR}(q) = \frac{\mathrm{Var}(r_t + r_{t-1} + \dots + r_{t-q+1})}{q \cdot \mathrm{Var}(r_t)} \approx 1 + 2\sum_{k=1}^{q-1}\left(1 - \frac{k}{q}\right)\rho_k$$

Bằng lời: phương sai của lợi suất $q$ nến, chia cho $q$ lần phương sai một nến. Bước ngẫu nhiên cho VR = 1. VR > 1 nghĩa là
có quán tính, VR < 1 nghĩa là hay quay đầu. Vế phải cho thấy VR gom các $\rho_k$ bậc nhỏ hơn $q$, bậc càng gần càng nặng ký.

Muốn biết VR khác 1 có ý nghĩa không, Lo–MacKinlay cho hai z-score:

- **z thường**: $z = (\mathrm{VR}-1)\big/\sqrt{2(2q-1)(q-1)/(3qT)}$, với $T$ là số lợi suất. Nó giả định phương sai không đổi.
- **z\* chịu dị phương sai (heteroskedasticity-robust)**: $z^* = (\mathrm{VR}-1)\big/\sqrt{\hat\theta(q)/T}$, trong đó
  $\hat\theta(q) = \sum_{k=1}^{q-1}\left[\frac{2(q-k)}{q}\right]^2 \hat\delta_k$ và
  $\hat\delta_k = T\sum_t e_t^2 e_{t-k}^2 \big/ \left(\sum_t e_t^2\right)^2$, với $e_t = r_t - \bar r$.
  Bằng lời: $\hat\delta_k$ đo mức nến lớn đi cạnh nến lớn ở khoảng cách $k$. Biến động co cụm thì $\hat\delta_k > 1$, mẫu số to
  ra, z\* nhỏ lại.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def variance_ratio(r, q):
    """Lo–MacKinlay (1988): VR(q), z thường (giả định phương sai không đổi) và z* chịu dị phương sai."""
    r = np.asarray(r, float); T = len(r); mu = r.mean(); e = r - mu
    var1 = np.sum(e ** 2) / (T - 1)                                  # phương sai lợi suất 1 kỳ
    tong_q = np.convolve(r, np.ones(q), "valid")                     # tổng q lợi suất liên tiếp (chồng lấn)
    m = q * (T - q + 1) * (1 - q / T)                                # hệ số hiệu chỉnh lệch
    varq = np.sum((tong_q - q * mu) ** 2) / m
    vr = varq / var1
    z = (vr - 1) / np.sqrt(2 * (2 * q - 1) * (q - 1) / (3 * q * T))
    e2 = e ** 2
    delta = np.array([T * np.sum(e2[k:] * e2[:-k]) / np.sum(e2) ** 2 for k in range(1, q)])
    theta = np.sum((2 * (q - np.arange(1, q)) / q) ** 2 * delta)
    return vr, z, (vr - 1) / np.sqrt(theta / T)

def loi_suat(dataset, tu, den, buoc):
    df = nap_nen(dataset, tu, den)
    r = np.log(df.close).diff()
    return r[df.index.to_series().diff() == pd.Timedelta(buoc)].to_numpy()  # bỏ lợi suất vắt qua giờ nghỉ

rng = np.random.default_rng(1)
chuoi = {
    "XAUUSD M15 01–08/2024": loi_suat(XAU_M15, "2024-01-01", "2024-09-01", "15min"),
    "XAUUSD M15 2018–2023": loi_suat(XAU_M15_DAI, "2018-01-01", "2024-01-01", "15min"),
    "XAUUSD H1 2018–08/2024": loi_suat(XAU_H1, "2018-01-01", "2024-09-01", "1h"),
}
chuoi["ngẫu nhiên (cùng n với M15 2024)"] = rng.normal(0, 1, len(chuoi["XAUUSD M15 01–08/2024"]))
for ten, r in chuoi.items():
    print("== %s (n = %d)" % (ten, len(r)))
    for q in (2, 4, 16):
        vr, z, zs = variance_ratio(r, q)
        print("   q = %2d   VR = %.3f   z thường = %6.2f   z* chịu dị phương sai = %6.2f" % (q, vr, z, zs))
```

```text
Kết quả khi mình chạy:
== XAUUSD M15 01–08/2024 (n = 15677)
   q =  2   VR = 0.984   z thường =  -2.04   z* chịu dị phương sai =  -1.14
   q =  4   VR = 0.991   z thường =  -0.63   z* chịu dị phương sai =  -0.35
   q = 16   VR = 0.971   z thường =  -0.83   z* chịu dị phương sai =  -0.51
== XAUUSD M15 2018–2023 (n = 140188)
   q =  2   VR = 0.977   z thường =  -8.65   z* chịu dị phương sai =  -3.38
   q =  4   VR = 0.964   z thường =  -7.20   z* chịu dị phương sai =  -2.93
   q = 16   VR = 0.965   z thường =  -2.94   z* chịu dị phương sai =  -1.37
== XAUUSD H1 2018–08/2024 (n = 37915)
   q =  2   VR = 0.998   z thường =  -0.46   z* chịu dị phương sai =  -0.22
   q =  4   VR = 1.010   z thường =   1.07   z* chịu dị phương sai =   0.55
   q = 16   VR = 1.010   z thường =   0.43   z* chịu dị phương sai =   0.25
== ngẫu nhiên (cùng n với M15 2024) (n = 15677)
   q =  2   VR = 0.989   z thường =  -1.41   z* chịu dị phương sai =  -1.40
   q =  4   VR = 0.972   z thường =  -1.89   z* chịu dị phương sai =  -1.88
   q = 16   VR = 0.977   z thường =  -0.66   z* chịu dị phương sai =  -0.66
```

Đọc kết quả:

- **M15 2024:** VR(2) = 0.984, z thường = −2.04, tức «bác bỏ bước ngẫu nhiên ở mức 5%». z\* = −1.14 thì không bác bỏ. Chính biến
  động co cụm làm z thường phóng đại.
- **M15 2018–2023:** mẫu lớn gấp 9, VR(2) = 0.977 và z\* = −3.38. Vàng M15 hơi quay đầu ở thang 2–4 nến, và lần này có ý nghĩa
  thống kê. Cỡ hiệu ứng thì nhỏ: phương sai 2 nến chỉ kém 2 × phương sai 1 nến 2.3%.
- **H1:** VR ≈ 1 ở mọi thang. Lên H1 thì hiệu ứng quay đầu ngắn biến mất. Điều này khớp với giải thích «nhiễu báo giá ở thang phút».
- **Chuỗi ngẫu nhiên** cũng cho VR(4) = 0.972, z = −1.89. Với nhiễu thật sự, z thường và z\* gần như trùng nhau. Chênh lớn giữa
  hai z chỉ xuất hiện trên dữ liệu thật, đúng chỗ có dị phương sai.

Danh mục (R3-13) đề xuất dùng z\*(q) ở q = 4, 16 trên M15 làm bằng chứng Range / Trend «có ngưỡng thống kê». Kết quả trên cho biết
trước: trên cả mẫu, vàng không lệch khỏi bước ngẫu nhiên tới mức trend / range rõ. Một bộ chỉ báo VR cuốn chiếu chỉ có giá trị nếu
nó tìm ra những **đoạn** lệch, và phải so với null (module 3) vì chạy cuốn chiếu là kiểm định lặp hàng nghìn lần.

**Bẫy hay gặp.**
- Dùng z thường trên dữ liệu tài chính. Nó bác bỏ bước ngẫu nhiên quá dễ (bài tập 2: 20–27% thay vì 5%).
- Thấy VR < 1 ở M15 rồi kết luận «vàng là thị trường range». Chênh 2–3% chủ yếu ở thang 15–30 phút, H1 không còn. Nhiễu báo giá
  (bid nhảy qua lại) đủ tạo ra nó (danh mục R3-13, mục rủi ro).
- Mùa vụ biến động cũng là dị phương sai. z\* xử lý được về mặt kiểm định, nhưng muốn **so sánh** VR giữa các giờ thì nên khử mùa
  vụ trước (mục 3).

## 3. Mùa vụ biến động trong ngày và vì sao ATR lệch theo giờ

**Trực giác.** Vàng 19:00 New York (châu Á chưa vào hẳn) và vàng 08:30 New York (tin Mỹ) là hai thị trường khác nhau về độ ồn. Một thước đo biến động không biết giờ sẽ lẫn «bây giờ ồn» với «giờ này vốn ồn».

**Định nghĩa.** **Mùa vụ trong ngày (intraday seasonality / periodicity)**: phần biến động lặp lại theo giờ trong ngày. Ước lượng
bằng độ lệch chuẩn của lợi suất trong từng ô giờ $\tau$: $s_\tau$. **Khử mùa vụ**: $\tilde r_t = r_t / s_{\tau(t)}$, tức chia lợi
suất cho độ ồn «bình thường» của đúng giờ đó (danh mục R3-26).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
df["r"] = np.log(df.close).diff().where(df.index.to_series().diff() == pd.Timedelta("15min"))
df["gio_ny"] = df.index.tz_convert("America/New_York").hour

# Displacement theo đúng định nghĩa của lab: biên độ ≥ 1.5 × ATR[t−1], thân ≥ 0.6 × biên độ
kq = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")
ev = kq["su_kien"]
disp = ev.loc[ev.structure_type.str.startswith("DISPLACEMENT"), "event_bar_index"].to_numpy()
df["disp"] = np.isin(np.arange(len(df)), disp)

g = df.groupby("gio_ny")
bang = pd.DataFrame({"số nến": g.size(),
                     "độ lệch chuẩn r (%)": 100 * g.r.std(),
                     "so với TB": g.r.std() / df.r.std(),
                     "displacement (% nến)": 100 * g.disp.mean()})
print(bang.round(3).to_string())
print("Giờ sôi động nhất / yên nhất: độ lệch chuẩn gấp %.1f lần" % (bang["độ lệch chuẩn r (%)"].max() / bang["độ lệch chuẩn r (%)"].min()))
```

```text
Kết quả khi mình chạy:
        số nến  độ lệch chuẩn r (%)  so với TB  displacement (% nến)
gio_ny
0          692                0.050      0.535                 2.601
1          692                0.068      0.727                 8.237
2          692                0.080      0.853                13.006
3          692                0.083      0.878                12.861
4          692                0.083      0.887                 8.815
5          692                0.071      0.755                 7.081
6          692                0.071      0.750                 6.214
7          692                0.074      0.792                 7.225
8          692                0.161      1.716                19.075
9          692                0.156      1.657                20.087
10         692                0.168      1.792                14.595
11         692                0.126      1.339                 5.925
12         692                0.093      0.987                 1.734
13         688                0.086      0.911                 2.180
14         678                0.083      0.884                 2.507
15         668                0.075      0.793                 1.647
16         668                0.051      0.538                 0.749
18         692                0.067      0.715                 1.301
19         692                0.042      0.449                 0.867
20         692                0.066      0.707                 5.925
21         692                0.112      1.189                15.896
22         692                0.079      0.845                 7.659
23         692                0.063      0.674                 2.601
Giờ sôi động nhất / yên nhất: độ lệch chuẩn gấp 4.0 lần
```

Đọc kết quả:

- Không có giờ 17: CME nghỉ 17:00–18:00 New York (module 1). Giờ yên nhất là 19:00 (0.45 × trung bình), sôi động nhất 08:00–10:00
  (tin Mỹ 08:30, mở cửa New York; ~1.7–1.8 ×). Chênh 4 lần.
- Cột **displacement** cho câu trả lời «vì sao ATR lệch theo giờ». ATR Wilder 14 là trung bình làm trơn của True Range với chu kỳ
  14 nến (~3.5 giờ), nên nó luôn **chậm** hơn đồng hồ. Lúc chuyển từ giờ yên sang giờ ồn (02:00–03:00 killzone London, 08:00 New
  York, 21:00 sáng sớm châu Á), nến bình thường của giờ mới đã vượt 1.5 × ATR của giờ cũ. Kết quả: 13–20% nến là displacement.
  Buổi chiều thì ngược lại: ATR còn cao từ buổi sáng nên chỉ 0.7–2.5% nến đạt ngưỡng. Vì vậy nhiều «displacement» của lab đánh
  dấu **sự chuyển giờ** hơn là một cú đẩy bất thường so với giờ đó.

Khử mùa vụ rồi xem tự tương quan của |r| còn lại gì:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
gio = df.index.tz_convert("America/New_York")
df["o"] = gio.hour * 4 + gio.minute // 15                  # ô 15 phút trong ngày New York: 0..95
df["r"] = np.log(df.close).diff().where(df.index.to_series().diff() == pd.Timedelta("15min"))
df = df.dropna(subset=["r"])

# Hệ số mùa vụ = độ lệch chuẩn của r trong từng ô 15 phút (tính trên CẢ mẫu — được cho phân tích mô tả,
# nhưng là nhìn tương lai nếu dùng làm đầu vào thuật toán; bản dùng được phải tính cuốn chiếu từ quá khứ)
s = df.groupby("o").r.std()
df["r_khu"] = df.r / df.o.map(s)

def tu_tuong_quan(x, k):
    x = x - x.mean()
    return np.sum(x[k:] * x[:-k]) / np.sum(x * x)

a, b = np.abs(df.r.to_numpy()), np.abs(df.r_khu.to_numpy())
print("bậc k (nến)   ≈ thời gian    |r| thô   |r| đã khử mùa vụ")
for k, nhan in [(1, "15 phút"), (4, "1 giờ"), (16, "4 giờ"), (32, "8 giờ"), (46, "nửa ngày"),
                (92, "1 ngày"), (184, "2 ngày"), (460, "1 tuần")]:
    print("%8d   %-12s %9.3f %12.3f" % (k, nhan, tu_tuong_quan(a, k), tu_tuong_quan(b, k)))
print("Kurtosis thừa: r thô %.1f · r đã khử %.1f" % (df.r.kurt(), df.r_khu.kurt()))
```

```text
Kết quả khi mình chạy:
bậc k (nến)   ≈ thời gian    |r| thô   |r| đã khử mùa vụ
       1   15 phút          0.267        0.210
       4   1 giờ            0.189        0.134
      16   4 giờ            0.055        0.086
      32   8 giờ           -0.001        0.064
      46   nửa ngày         0.042        0.063
      92   1 ngày           0.151        0.061
     184   2 ngày           0.122        0.049
     460   1 tuần           0.096        0.047
Kurtosis thừa: r thô 13.4 · r đã khử 5.1
```

Một ngày giao dịch vàng có 92 nến M15 (23 giờ), nên bậc 92 ≈ «cùng giờ hôm qua».

- **Thô:** tự tương quan của |r| đi hình sóng: về 0 sau 8 giờ, vọt lên 0.15 ở đúng một ngày. Phần lớn đó là đồng hồ.
- **Đã khử:** giảm đều và chậm, 0.21 → 0.13 → 0.09 → 0.06, và vẫn 0.05 sau một tuần. Đây là biến động co cụm thật. Một tuần ồn kéo
  theo tuần sau ồn. Tính «nhớ lâu» này là thứ HAR khai thác ở mục 5.
- Kurtosis giảm từ 13.4 xuống 5.1: một phần «đuôi dày» chỉ là trộn giờ yên với giờ ồn.

**Bẫy hay gặp.**
- Tính hệ số mùa vụ trên cả mẫu rồi đưa vào thuật toán: nhìn tương lai. Bản dùng được phải tính $s_\tau$ cuốn chiếu trên D ngày
  **trước** (R3-26 gợi ý D = 20–60).
- Lưới giờ theo UTC: đổi giờ mùa hè làm phiên London / New York trượt một giờ hai lần mỗi năm. Dùng giờ New York như lab (module 1).
- Ngày lễ, thứ Sáu NFP có hồ sơ riêng. Chúng vẫn nằm trong trung bình.

## 4. Ước lượng biến động từ OHLC và realized variance

**Trực giác.** Hai nến cùng mở 2400, cùng đóng 2401. Nến A đi thẳng, nến B quét xuống 2390 rồi lên 2405. Nhìn close thì hai nến như
nhau; nhìn high / low thì B ồn hơn hẳn. High và low chứa thêm thông tin về biến động.

**Định nghĩa.** Với log so với open của nến: $h = \ln(H/O)$, $l = \ln(L/O)$, $c = \ln(C/O)$. Ước lượng **phương sai một nến**:

| Ước lượng | Công thức | Ý tưởng |
|---|---|---|
| close − open | $c^2$ | chỉ dùng điểm cuối |
| **Parkinson** | $(h - l)^2 / (4\ln 2)$ | biên độ high − low, chia hằng số để không lệch khi giá là bước ngẫu nhiên |
| **Garman–Klass** | $\tfrac12 (h-l)^2 - (2\ln 2 - 1)\, c^2$ | biên độ, bớt phần do thân nến |
| **Rogers–Satchell** | $h(h-c) + l(l-c)$ | không lệch kể cả khi có drift (trend mạnh) |

Chuẩn để so: **realized variance (RV)**, tổng bình phương lợi suất log của các nến M1 bên trong nến M15:
$\mathrm{RV} = \sum_i r_i^2$. Bằng lời: chia nến thành 15 bước nhỏ và cộng biến động của từng bước. Đây là ước lượng không cần mô
hình của biến động thật trong nến (danh mục R4-10).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

m15 = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
m1 = nap_nen(XAU_M1, "2024-01-01", "2024-09-01")

# Realized variance (RV) của mỗi nến M15 từ các nến M1 bên trong nó: tổng bình phương lợi suất log M1
m1["nen15"] = m1.index.floor("15min")
m1["r"] = np.log(m1.close).diff()
dau = ~m1.nen15.duplicated()                                    # nến M1 đầu tiên của mỗi nến M15
m1.loc[dau, "r"] = np.log(m1.close / m1.open)[dau]             # lợi suất đầu tính từ open của nến M15
g = m1.groupby("nen15")
rv = pd.DataFrame({"RV": g.r.apply(lambda x: np.sum(x ** 2)), "so_m1": g.size()})
df = m15.join(rv, how="inner")
df = df[df.so_m1 == 15]                                         # chỉ nến M15 đủ 15 nến M1

h, l, c = np.log(df.high / df.open), np.log(df.low / df.open), np.log(df.close / df.open)
uoc_luong = {
    "(close−open)²": c ** 2,
    "Parkinson": (h - l) ** 2 / (4 * np.log(2)),
    "Garman–Klass": 0.5 * (h - l) ** 2 - (2 * np.log(2) - 1) * c ** 2,
    "Rogers–Satchell": h * (h - c) + l * (l - c),
}
ngay = (df.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).date   # ngày giao dịch, mốc 17:00 NY
rv_ngay = df.RV.groupby(ngay).sum()
print("%d nến M15 đủ M1 · %d ngày" % (len(df), len(rv_ngay)))
print("%-16s %12s %14s %15s %16s" % ("ước lượng", "TB / TB(RV)", "tương quan nến", "tương quan ngày", "sai số ngày (%)"))
for ten, u in uoc_luong.items():
    u_ngay = u.groupby(ngay).sum()
    sai_so = np.sqrt(np.mean((u_ngay / rv_ngay - 1) ** 2)) * 100      # sai số tương đối so với RV ngày
    print("%-16s %12.2f %14.3f %15.3f %16.1f" % (ten, u.mean() / df.RV.mean(), np.corrcoef(u, df.RV)[0, 1],
                                                 np.corrcoef(u_ngay, rv_ngay)[0, 1], sai_so))
```

```text
Kết quả khi mình chạy:
15818 nến M15 đủ M1 · 173 ngày
ước lượng         TB / TB(RV) tương quan nến tương quan ngày  sai số ngày (%)
(close−open)²            0.96          0.635           0.910             24.4
Parkinson                0.97          0.841           0.979             11.0
Garman–Klass             0.97          0.837           0.980             11.1
Rogers–Satchell          0.99          0.809           0.973             13.2
```

Đọc kết quả:

- Cả bốn đều gần như **không lệch** (trung bình bằng 96–99% RV).
- Khác nhau ở **độ nhiễu**. Từng nến, $c^2$ chỉ tương quan 0.64 với RV, còn Parkinson / Garman–Klass đạt 0.84. Cộng theo ngày, $c^2$
  sai trung bình 24%, Parkinson / GK chỉ 11%. Chỉ cần thêm high và low là sai số giảm một nửa.
- Rogers–Satchell kém Parkinson / GK một chút. Nó được thiết kế để chịu drift, mà trong một nến M15 drift gần như bằng 0. Ở đây
  Parkinson và Garman–Klass sát RV nhất.
- ATR của lab dùng True Range, họ hàng của biên độ $h - l$. Bảng này giải thích vì sao lab dùng biên độ chứ không dùng
  |close − open| để đo biến động.

**Bẫy hay gặp.**
- Dữ liệu là giá **Bid**: spread nằm lẫn trong high − low. Giờ thanh khoản mỏng (rollover 17:00 New York) spread nở, nên biên độ
  phồng lên (R3-25, mục rủi ro).
- RV từ M1 cũng có nhiễu: giá báo nhảy qua lại làm RV nhích lên khi lấy mẫu dày (bài tập 3).
- So ước lượng của một nến với RV của chính nến đó luôn nhiễu (tương quan 0.84). Cộng theo ngày mới thấy bộ ước lượng nào tốt.

## 5. HAR-RV: dự báo biến động ngày mai

**Trực giác.** Muốn đoán biến động ngày mai thì nhìn hôm nay, tuần này và tháng này. Hôm nay có tin lớn thì mai còn dư âm. Tuần này
ồn thì mai nhiều khả năng còn ồn. Tháng là mức nền mà biến động hay quay về.

**Định nghĩa.** **HAR-RV** (Corsi 2009, danh mục R1-29). $\mathrm{RV}_t$ là realized variance của ngày $t$;
$\mathrm{RV}^{(w)}_t$ là trung bình 5 ngày gần nhất, $\mathrm{RV}^{(m)}_t$ là trung bình 22 ngày:

$$\mathrm{RV}_{t+1} = c + \beta_d\, \mathrm{RV}_t + \beta_w\, \mathrm{RV}^{(w)}_t + \beta_m\, \mathrm{RV}^{(m)}_t + \varepsilon_{t+1}$$

Bằng lời: biến động ngày mai là một tổ hợp tuyến tính của biến động hôm nay, tuần này và tháng này. Hệ số tìm bằng hồi quy bình
phương nhỏ nhất (OLS). Ba thang thời gian chồng lên nhau bắt được «nhớ lâu» đã thấy ở mục 3. Đánh giá **ngoài mẫu**: học hệ số
trên 2018–2022, rồi dự báo 2023 → 08/2024 mà không chỉnh gì. So với hai dự báo ngây thơ: «bằng hôm qua» và «trung bình 22 ngày».
Hai thước đo sai số: **RMSE** (căn trung bình bình phương sai số) và **QLIKE** $= \mathbb{E}[\mathrm{RV}/F - \ln(\mathrm{RV}/F) - 1]$,
với $F$ là dự báo. QLIKE phạt dự báo thấp hơn thực tế nặng hơn.

Lab có M1 cho 2018–2025, nhưng `hoc.py` chỉ đặt tên sẵn cho M1 2024, và 8 tháng (173 ngày) quá ít để vừa học vừa kiểm. Vì vậy RV
ngày ở đây tính từ M15 2018 → 08/2024 (`XAU_M15_DAI`). Bài tập 3 cho thấy RV từ M15 và từ M1 tương quan 0.91.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# RV ngày = tổng bình phương lợi suất log M15 trong ngày giao dịch (mốc 17:00 New York)
df = nap_nen(XAU_M15_DAI, "2018-01-01", "2024-09-01")
r = np.log(df.close).diff().where(df.index.to_series().diff() == pd.Timedelta("15min"))
ngay = (df.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).date
g = pd.DataFrame({"r2": r ** 2, "co": r.notna()}).groupby(ngay)
rv = g.r2.sum()[g.co.sum() >= 80] * 1e4                 # bỏ ngày thiếu (lễ, nửa ngày); đơn vị: (%)²

# Đặc trưng HAR tại ngày t (chỉ dùng RV đã biết tới hết ngày t), mục tiêu là RV ngày t+1
X = pd.DataFrame({"ngay": rv, "tuan": rv.rolling(5).mean(), "thang": rv.rolling(22).mean()})
X["muc_tieu"] = rv.shift(-1)
X = X.dropna()
X.index = pd.to_datetime(X.index)
hoc, kiem = X[X.index < "2023-01-01"], X[X.index >= "2023-01-01"]

A = np.column_stack([np.ones(len(hoc)), hoc[["ngay", "tuan", "thang"]]])
beta = np.linalg.lstsq(A, hoc.muc_tieu, rcond=None)[0]      # OLS: c, β_ngày, β_tuần, β_tháng
print("Học %s → %s (%d ngày) · kiểm %s → %s (%d ngày)" % (hoc.index[0].date(), hoc.index[-1].date(), len(hoc),
      kiem.index[0].date(), kiem.index[-1].date(), len(kiem)))
print("Hệ số HAR: c = %.3f · β_ngày = %.3f · β_tuần = %.3f · β_tháng = %.3f" % tuple(beta))

du_bao = {
    "bằng hôm qua": kiem.ngay,
    "TB 22 ngày": kiem.thang,
    "HAR": np.column_stack([np.ones(len(kiem)), kiem[["ngay", "tuan", "thang"]]]) @ beta,
}
y = kiem.muc_tieu.to_numpy()
mse0 = np.mean((y - kiem.ngay) ** 2)
print("%-14s %10s %16s %8s" % ("dự báo", "RMSE", "MSE / bằng hôm qua", "QLIKE"))
for ten, f in du_bao.items():
    f = np.asarray(f)
    qlike = np.mean(y / f - np.log(y / f) - 1)               # phạt dự báo thấp hơn thực tế nặng hơn
    print("%-14s %10.4f %16.2f %8.3f" % (ten, np.sqrt(np.mean((y - f) ** 2)), np.mean((y - f) ** 2) / mse0, qlike))
```

```text
Kết quả khi mình chạy:
Học 2018-02-01 → 2022-12-30 (1238 ngày) · kiểm 2023-01-03 → 2024-08-29 (422 ngày)
Hệ số HAR: c = 0.183 · β_ngày = 0.326 · β_tuần = 0.381 · β_tháng = 0.074
dự báo               RMSE MSE / bằng hôm qua    QLIKE
bằng hôm qua       0.8256             1.00    0.261
TB 22 ngày         0.6685             0.66    0.211
HAR                0.6594             0.64    0.182
```

Đọc kết quả:

- Hệ số: hôm nay nặng 0.33, tuần 0.38, tháng 0.07, cộng một hằng số (mức nền). Biến động ngày mai «nhớ» cả hôm nay lẫn tuần này.
- Ngoài mẫu, HAR giảm bình phương sai số còn 64% so với «bằng hôm qua», và có QLIKE tốt nhất. «Bằng hôm qua» tệ vì RV một ngày rất
  nhiễu: một ngày tin lớn kéo dự báo vọt lên rồi sai ngay hôm sau. Trung bình 22 ngày đã tốt hơn nhiều (66%), HAR nhích thêm chút.
- Corsi (2009) thấy cùng thứ tự trên USD/CHF: HAR có RMSE 2.377, AR(1) có 2.540 (danh mục R1-29). Ở đây «biến động đoán được» có
  một con số ngoài mẫu: sai số giảm khoảng 1/3. Với **hướng** giá trong ngày, lab chưa có kết quả nào như vậy (order flow: ±2 điểm
  %, module 3).

**Bẫy hay gặp.**
- Học hệ số trên cả mẫu rồi báo sai số trên chính mẫu đó: lạc quan. Code ở trên khoá đoạn học trước 2023.
- Ngày thứ Hai có thêm phiên tối Chủ nhật, ngày lễ ngắn: RV ngày không cùng độ dài. Lọc ngày thiếu (≥ 80/92 nến) là cách thô.
- RV có đuôi rất dày. Một vài ngày tin tức chi phối RMSE, nên báo thêm QLIKE hoặc làm trên log RV.

## 6. Tỷ lệ biến động ngắn/dài: «nén → bung» đo cho đúng

**Trực giác.** Trader hay nói «thị trường nén thì sắp bung». Đo được: lấy biến động 2 giờ qua chia cho nền 4 ngày. Tỷ lệ thấp là
«nén». Rồi xem 2 giờ **tiếp theo** ra sao, so với nền và so với lúc nén.

**Định nghĩa.** Với $v_t$ là phương sai Garman–Klass của nến $t$ (đã khử mùa vụ):

$$\text{tỷ lệ}_t = \frac{\text{TB}(v_{t-7..t})}{\text{TB}(v_{t-383..t})}$$

Bằng lời: biến động 8 nến vừa qua so với 384 nến vừa qua (4 ngày). Cả hai đều biết tại $t$ (danh mục R3-27). Thước đo kết quả là
trung bình $v$ của 8 nến **sau** $t$. Thước đo này chỉ để chấm, không phải đầu vào.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15_DAI, "2018-01-01", "2024-01-01")
h, l, c = np.log(df.high / df.open), np.log(df.low / df.open), np.log(df.close / df.open)
gk = 0.5 * (h - l) ** 2 - (2 * np.log(2) - 1) * c ** 2          # phương sai Garman–Klass mỗi nến
gio = df.index.tz_convert("America/New_York")
o = gio.hour * 4 + gio.minute // 15
gk_khu = gk / gk.groupby(o).transform("mean")                    # khử mùa vụ theo ô 15 phút (mô tả, cả mẫu)

NGAN, DAI, SAU = 8, 384, 8                                       # 2 giờ · 4 ngày · 2 giờ tới
def bang_nen(v):
    ngan = v.rolling(NGAN).mean()                                # biến động 8 nến vừa qua (đã biết tại t)
    dai = v.rolling(DAI).mean()                                  # nền 384 nến vừa qua (đã biết tại t)
    toi = v[::-1].rolling(SAU).mean()[::-1].shift(-1)            # 8 nến SAU t — chỉ để chấm
    d = pd.DataFrame({"ngắn/dài": ngan / dai, "tới/dài": toi / dai, "tới/ngắn": toi / ngan}).dropna()
    d["thập phân vị"] = pd.qcut(d["ngắn/dài"], 10, labels=range(1, 11))
    return d.groupby("thập phân vị", observed=True).median()     # trung vị: đỡ bị vài nến tin tức kéo lệch

tho, khu = bang_nen(gk), bang_nen(gk_khu)
print("== Khử mùa vụ")
print(khu.round(2).to_string())
print("== Thô (chưa khử mùa vụ): cột tới/ngắn")
print(tho["tới/ngắn"].round(2).to_frame().T.to_string())
```

```text
Kết quả khi mình chạy:
== Khử mùa vụ
              ngắn/dài  tới/dài  tới/ngắn
thập phân vị
1                 0.28     0.45      1.75
2                 0.43     0.58      1.35
3                 0.54     0.65      1.21
4                 0.64     0.71      1.10
5                 0.75     0.76      1.01
6                 0.87     0.82      0.95
7                 1.00     0.89      0.88
8                 1.18     0.95      0.80
9                 1.48     1.06      0.71
10                2.27     1.31      0.53
== Thô (chưa khử mùa vụ): cột tới/ngắn
thập phân vị     1     2     3     4     5     6     7    8    9    10
tới/ngắn      2.36  1.58  1.24  1.09  0.96  0.85  0.78  0.7  0.6  0.42
```

Đọc kết quả (trung vị, vàng M15 2018–2023, đã khử mùa vụ):

- Nhóm nén nhất (biến động 2 giờ chỉ bằng 0.28 nền): 2 giờ sau biến động **tăng** gấp 1.75 so với lúc nén. Theo nghĩa «so với bây
  giờ» thì có bung.
- Nhưng so với nền thì 2 giờ sau vẫn chỉ bằng 0.45, **thấp nhất** trong 10 nhóm. Nén báo trước biến động thấp, không báo trước bùng
  nổ. Đây là **hồi quy về trung bình** (mean reversion) của biến động: lệch xa thì quay một phần về nền. Nó đối xứng: nhóm bung nhất
  (2.27) sau đó giảm còn 0.53 lần, nhưng vẫn ở mức cao nhất.
- Bản **thô** cho nhóm nén nhất «bung» 2.36 lần thay vì 1.75. Phần chênh là đồng hồ: nén thô thường rơi vào giờ yên, và giờ kế tiếp
  ồn hơn chỉ vì đến phiên. Không khử mùa vụ thì chỉ báo nén → bung «học lại đồng hồ» (R3-27, mục rủi ro).

Danh mục ghi R3-27 là ứng viên chính cho trạng thái Breakout, nhưng «không tìm được kiểm định trực tiếp nén dự báo bung». Bảng trên
cho biết điều nên kỳ vọng: nén giúp dự báo **mức** biến động sắp tới (thấp), còn «bung» theo nghĩa vượt nền thì phải đến từ thứ khác
(tin vĩ mô theo lịch, phá biên). Và nó không cho biết **chiều**.

**Bẫy hay gặp.**
- Đọc «tới/ngắn > 1 sau nén» là «nén dự báo bung». Phải nhìn cả «tới/dài». Nhóm nén vẫn yên nhất.
- Chọn ngưỡng «nén» (vd thập phân vị 1) trên cả mẫu rồi kiểm trên chính mẫu đó. Ngưỡng phải chọn trên đoạn phát triển (module 7).
- Hệ số mùa vụ ở đây tính trên cả mẫu (mô tả). Đưa vào thuật toán thì phải tính cuốn chiếu.

## Lab đang dùng những điều này ở đâu

| Khái niệm | File / tài liệu của lab | Ghi chú |
|---|---|---|
| ATR Wilder (ngưỡng ở nến t dùng ATR[t−1]) | [`core/indicators.py`](../../core/indicators.py) `WilderATRPrevClose`, [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §3, §4.1 | trung bình trượt ~3.5 giờ, chạy sau mùa vụ (mục 3) |
| Displacement ≥ 1.5 ATR, thân ≥ 0.6 biên độ | [`core/components/displacement.py`](../../core/components/displacement.py), [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §4.7 | ~7% nến, dồn vào giờ chuyển phiên (13–20%) |
| Killzone theo giờ New York | [`core/components/killzone.py`](../../core/components/killzone.py), §4.11 cùng tài liệu | cùng lưới giờ với bảng mùa vụ |
| Ngưỡng DC theo θ·ATR | [`thuat_toan_dc_atr_structure.md`](../algorithms/thuat_toan_dc_atr_structure.md) §3 | ATR chưa khử mùa vụ nên θ·ATR đổi theo giờ (R3-26) |
| Chuẩn ngẫu nhiên ghép theo giờ × tầng ATR | [`core/eval/null_baseline.py`](../../core/eval/null_baseline.py), [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.3 | ghép cặp vì biến động theo giờ và co cụm (module 3) |
| Variance ratio, mùa vụ, OHLC, nén / bung | [`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md) R3-13, R3-25, R3-26, R3-27 | đều «thử sớm»; R3-26 là bước 1 «làm sạch thước đo» |
| RV từ M1, HAR-RV | cùng danh mục, R4-10, R1-29 | trục biến động của regime hai trục (§4 danh mục) |
| Regime: trạng thái Breakout | [`plan_bias_regime.md`](../plans/plan_bias_regime.md) §4.5 | Breakout là trạng thái chuyển tiếp ngắn; kết cục phải đo với null |

## Bài tập

**Bài 1 (dễ).** Làm lại mục 1 và mục 3 cho EURUSD M15 01–08/2024 (`EUR_M15_DAI`). So bốn con số với vàng: tự tương quan bậc 1 của
r, của |r|, của |r| ở bậc 92 (thô và đã khử mùa vụ). Giờ New York nào sôi động nhất?

*Gợi ý:* gom cả hai mã vào một vòng lặp; khử mùa vụ bằng `groupby(o).transform("std")`.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def tu_tuong_quan(x, k):
    x = x - x.mean()
    return np.sum(x[k:] * x[:-k]) / np.sum(x * x)

for ten, ds in (("XAUUSD", XAU_M15_DAI), ("EURUSD", EUR_M15_DAI)):
    df = nap_nen(ds, "2024-01-01", "2024-09-01")
    r = np.log(df.close).diff()
    r = r[df.index.to_series().diff() == pd.Timedelta("15min")]
    gio = r.index.tz_convert("America/New_York")
    o = gio.hour * 4 + gio.minute // 15
    r_khu = r / r.groupby(o).transform("std")
    x, a, b = r.to_numpy(), np.abs(r.to_numpy()), np.abs(r_khu.to_numpy())
    print("%s (n = %d): r bậc 1 %.3f · |r| bậc 1 %.3f · |r| bậc 92 %.3f · |r| khử mùa vụ bậc 92 %.3f · giờ NY sôi động nhất %d"
          % (ten, len(x), tu_tuong_quan(x, 1), tu_tuong_quan(a, 1), tu_tuong_quan(a, 92), tu_tuong_quan(b, 92),
             r.groupby(gio.hour).std().idxmax()))
```

```text
Kết quả khi mình chạy:
XAUUSD (n = 15677): r bậc 1 -0.016 · |r| bậc 1 0.267 · |r| bậc 92 0.151 · |r| khử mùa vụ bậc 92 0.061 · giờ NY sôi động nhất 10
EURUSD (n = 16669): r bậc 1 -0.010 · |r| bậc 1 0.223 · |r| bậc 92 0.132 · |r| khử mùa vụ bậc 92 0.025 · giờ NY sôi động nhất 8
```

Cùng một bức tranh: lợi suất gần như không nhớ (−0.01 đến −0.02), |r| co cụm mạnh, bậc một ngày phần lớn là đồng hồ. Với EURUSD,
khử mùa vụ làm bậc 92 giảm mạnh hơn (0.13 → 0.03): phần «cùng giờ hôm qua» của EURUSD gần như toàn là đồng hồ. Vàng sôi động nhất lúc 10:00 New York,
EURUSD lúc 08:00 (tin Mỹ 08:30). `XAU_M15_DAI` cho đúng các số của `XAU_M15` ở mục 1, nên hai dataset khớp nhau trên đoạn này.

</details>

**Bài 2 (vừa).** Giữ nguyên |r| thật của vàng M15 2024 nhưng đổi dấu ngẫu nhiên (null đổi dấu của module 3). Chuỗi này chắc chắn
không có tự tương quan hướng. Chạy `variance_ratio` 300 lần với q = 2, 4, 16, đếm tỷ lệ |z| > 1.96 cho z thường và z\*. Đúng ra
phải ≈ 5%.

*Gợi ý:* `np.abs(r) * rng.choice([-1, 1], len(r))`.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def variance_ratio(r, q):
    r = np.asarray(r, float); T = len(r); mu = r.mean(); e = r - mu
    var1 = np.sum(e ** 2) / (T - 1)
    tong_q = np.convolve(r, np.ones(q), "valid")
    varq = np.sum((tong_q - q * mu) ** 2) / (q * (T - q + 1) * (1 - q / T))
    vr = varq / var1
    z = (vr - 1) / np.sqrt(2 * (2 * q - 1) * (q - 1) / (3 * q * T))
    e2 = e ** 2
    delta = np.array([T * np.sum(e2[k:] * e2[:-k]) / np.sum(e2) ** 2 for k in range(1, q)])
    theta = np.sum((2 * (q - np.arange(1, q)) / q) ** 2 * delta)
    return vr, z, (vr - 1) / np.sqrt(theta / T)

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
r = np.log(df.close).diff()
r = r[df.index.to_series().diff() == pd.Timedelta("15min")].to_numpy()

# Giữ nguyên |r| thật (co cụm, mùa vụ, đuôi dày), chỉ đổi dấu ngẫu nhiên → chắc chắn KHÔNG có tự tương quan hướng
rng = np.random.default_rng(4)
N = 300
for q in (2, 4, 16):
    dem = np.zeros(2)
    for _ in range(N):
        _, z, zs = variance_ratio(np.abs(r) * rng.choice([-1, 1], len(r)), q)
        dem += [abs(z) > 1.96, abs(zs) > 1.96]
    print("q = %2d: tỷ lệ «bác bỏ bước ngẫu nhiên» (đúng ra ≈ 5%%) — z thường %.1f%% · z* %.1f%%" % (q, *(100 * dem / N)))
```

```text
Kết quả khi mình chạy:
q =  2: tỷ lệ «bác bỏ bước ngẫu nhiên» (đúng ra ≈ 5%) — z thường 27.0% · z* 6.3%
q =  4: tỷ lệ «bác bỏ bước ngẫu nhiên» (đúng ra ≈ 5%) — z thường 26.0% · z* 6.3%
q = 16: tỷ lệ «bác bỏ bước ngẫu nhiên» (đúng ra ≈ 5%) — z thường 20.3% · z* 3.0%
```

Trên dữ liệu **không có** quán tính hay quay đầu, z thường «phát hiện» trend / range 20–27% số lần, gấp 4–5 lần mức 5% đã hứa. z\*
giữ gần 5% (300 lần mô phỏng nên sai số ±1.3 điểm). Mọi bộ chỉ báo VR trên dữ liệu trong ngày phải dùng z\* hoặc so với null giữ
biến động.

</details>

**Bài 3 (vừa).** Tính RV ngày của vàng 01–08/2024 từ bốn khung: M1, M5, M15, H1 (`XAU_M1`, `XAU_M5`, `XAU_M15`, `XAU_H1`). So trung
bình và tương quan. Khung nào cho RV lớn nhất, vì sao?

*Gợi ý:* hàm `rv_ngay(dataset, buoc)` như mục 5 nhưng cho 2024; ghép bốn cột bằng `pd.DataFrame`.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def rv_ngay(dataset, buoc):
    df = nap_nen(dataset, "2024-01-01", "2024-09-01")
    r = np.log(df.close).diff().where(df.index.to_series().diff() == pd.Timedelta(buoc))
    ngay = (df.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).date
    return (r ** 2).groupby(ngay).sum() * 1e4                    # đơn vị (%)²

bang = pd.DataFrame({"M1": rv_ngay(XAU_M1, "1min"), "M5": rv_ngay(XAU_M5, "5min"), "M15": rv_ngay(XAU_M15, "15min"),
                     "H1": rv_ngay(XAU_H1, "1h")}).dropna()
bang = bang[bang.M15 > 0]
print("%d ngày giao dịch 01–08/2024" % len(bang))
print("RV TB (%²):", bang.mean().round(3).to_dict())
print("RV TB so với M15:", (bang.mean() / bang.M15.mean()).round(2).to_dict())
print("Tương quan giữa các RV ngày:")
print(bang.corr().round(3).to_string())
```

```text
Kết quả khi mình chạy:
173 ngày giao dịch 01–08/2024
RV TB (%²): {'M1': 0.837, 'M5': 0.803, 'M15': 0.801, 'H1': 0.773}
RV TB so với M15: {'M1': 1.04, 'M5': 1.0, 'M15': 1.0, 'H1': 0.97}
Tương quan giữa các RV ngày:
        M1     M5    M15     H1
M1   1.000  0.980  0.906  0.790
M5   0.980  1.000  0.916  0.776
M15  0.906  0.916  1.000  0.862
H1   0.790  0.776  0.862  1.000
```

RV từ M1 lớn hơn 4%: giá báo nhảy qua lại ở thang phút cộng thêm «biến động» không có thật. Cùng hiện tượng đó (lợi suất ngắn hơi
quay đầu) làm VR < 1 ở M15 mà không có ở H1 (mục 2), và làm RV từ H1 nhỏ hơn 3%. RV từ H1 cũng nhiễu hơn (tương quan với M1 chỉ
0.79) vì mỗi ngày chỉ có 23 lợi suất. M5 / M15 là điểm cân
bằng giữa nhiễu báo giá và số mẫu (danh mục R4-12 bàn về chọn tần số lấy mẫu). RV ngày từ M15 tương quan 0.91 với RV từ M1, đủ tốt
cho HAR ở mục 5.

</details>

**Bài 4 (khó).** Sau khi nén, displacement của lab (≥ 1.5 ATR) có dễ xuất hiện hơn không? Lý lẽ «sau nén ATR thấp nên nến bình
thường cũng vượt 1.5 ATR» nghe hợp lý. Kiểm: chia nến 2024 thành 5 nhóm theo tỷ lệ nén ngắn/dài (8 / 384 nến, GK, thô và khử mùa
vụ). Đo tỷ lệ nến **kế tiếp** là displacement trong mỗi nhóm.

*Gợi ý:* displacement lấy từ `chay_thuat_toan`; `pd.Series(disp).shift(-1)` là «nến kế tiếp».

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
kq = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")
ev = kq["su_kien"]
disp = np.zeros(len(df), bool)
disp[ev.loc[ev.structure_type.str.startswith("DISPLACEMENT"), "event_bar_index"].to_numpy()] = True

h, l, c = np.log(df.high / df.open), np.log(df.low / df.open), np.log(df.close / df.open)
gk = 0.5 * (h - l) ** 2 - (2 * np.log(2) - 1) * c ** 2
gio = df.index.tz_convert("America/New_York")
o = gio.hour * 4 + gio.minute // 15
for ten, v in (("thô", gk), ("khử mùa vụ", gk / gk.groupby(o).transform("mean"))):
    ty_le = v.rolling(8).mean() / v.rolling(384).mean()            # nén/bung đã biết tại t
    d = pd.DataFrame({"ty_le": ty_le, "disp_sau": pd.Series(disp, index=df.index).shift(-1)}).dropna()
    d["nhom"] = pd.qcut(d.ty_le, 5, labels=["1 nén nhất", "2", "3", "4", "5 bung nhất"])
    print("== %s: %% nến KẾ TIẾP là displacement (TB toàn mẫu %.1f%%)" % (ten, 100 * d.disp_sau.astype(float).mean()))
    print((100 * d.groupby("nhom", observed=True).disp_sau.mean().astype(float)).round(1).to_frame("%").T.to_string())
```

```text
Kết quả khi mình chạy:
== thô: % nến KẾ TIẾP là displacement (TB toàn mẫu 7.4%)
nhom  1 nén nhất    2    3    4  5 bung nhất
%            5.4  6.3  7.3  8.1          9.7
== khử mùa vụ: % nến KẾ TIẾP là displacement (TB toàn mẫu 7.4%)
nhom  1 nén nhất    2    3    4  5 bung nhất
%            5.7  7.4  8.1  7.8          7.8
```

Lý lẽ sai. Sau nén, displacement **ít** hơn trung bình (5.4–5.7% so với 7.4%). ATR có thấp thật, nhưng nến kế tiếp cũng nhỏ, vì
biến động co cụm (mục 6: nhóm nén vẫn yên nhất). Bản thô cho thấy displacement nhiều nhất sau giai đoạn đã bung: một phần là đồng
hồ (giờ ồn nối giờ ồn). Khử mùa vụ thì các nhóm 2–5 gần như bằng nhau. Bài học: một lý lẽ «nghe hợp lý» về chỉ báo phải đo, và đo
cạnh một baseline (ở đây là tỷ lệ toàn mẫu).

</details>

## Tự kiểm

1. Tự tương quan bậc 1 của lợi suất vàng M15 là −0.016, của |lợi suất| là 0.267. Điều nào đoán được hơn: chiều nến sau hay độ lớn
   nến sau?
<details><summary>Đáp án</summary>

Độ lớn. Chiều gần như không nhớ (−0.016, cỡ dải nhiễu ±0.016), còn độ lớn nhớ rõ (0.267) và kéo dài nhiều giờ: biến động co cụm.

</details>

2. VR(4) = 0.97 nghĩa là gì? Nếu z thường = −2.5 còn z\* = −1.2 thì kết luận gì?
<details><summary>Đáp án</summary>

Phương sai lợi suất 4 nến nhỏ hơn 4 lần phương sai 1 nến 3%: hơi quay đầu. z\* (chịu dị phương sai) không vượt 1.96 nên chưa bác bỏ được bước ngẫu nhiên. z thường phóng đại vì biến động co cụm.

</details>

3. Vì sao displacement của lab chiếm 19–20% nến lúc 08:00–09:00 New York nhưng chưa tới 1% lúc 16:00?
<details><summary>Đáp án</summary>

ATR là trung bình trượt ~3.5 giờ nên chạy sau mùa vụ. Lúc 08:00 ATR còn mang mức yên của buổi sớm, nến bình thường của giờ tin tức đã vượt 1.5 ATR. Lúc 16:00 ATR còn cao từ buổi sáng nên nến chiều khó đạt ngưỡng.

</details>

4. Tự tương quan của |r| thô vọt lên ở bậc 92 nến. Đó là co cụm biến động hay thứ khác?
<details><summary>Đáp án</summary>

Chủ yếu là mùa vụ: 92 nến = cùng giờ hôm qua. Sau khi khử mùa vụ, bậc 92 chỉ còn 0.06 và nằm trên một đường giảm đều. Phần đó mới là co cụm thật.

</details>

5. Bạn chỉ có OHLC của nến M15. Muốn đo biến động từng ngày sát RV từ M1 nhất, dùng ước lượng nào? Tránh cái nào?
<details><summary>Đáp án</summary>

Parkinson hoặc Garman–Klass (sai số ngày ~11%). Tránh (close − open)² (24%): bỏ phí thông tin high/low.

</details>

6. HAR dự báo RV ngày mai tốt hơn «bằng hôm qua» khoảng bao nhiêu (ngoài mẫu 2023–08/2024)? Vì sao «bằng hôm qua» kém?
<details><summary>Đáp án</summary>

Bình phương sai số còn 64% (giảm ~1/3). RV một ngày rất nhiễu (một tin lớn kéo vọt lên), còn HAR trung bình qua ngày / tuần / tháng và có hằng số kéo về nền.

</details>

7. Sau giai đoạn nén nhất, biến động 2 giờ tới tăng 1.75 lần so với lúc nén. Có nên gọi đó là «nén dự báo bung»?
<details><summary>Đáp án</summary>

Không. So với nền, 2 giờ tới vẫn chỉ 0.45 và thấp nhất trong mọi nhóm. Đó là hồi quy về trung bình của biến động, không phải bùng nổ, và không cho biết chiều.

</details>

## Đọc thêm

- Rob Hyndman, George Athanasopoulos, *Forecasting: Principles and Practice*: tự tương quan, dự báo ngây thơ làm baseline, đánh
  giá ngoài mẫu.
- Ruey Tsay, *Analysis of Financial Time Series*: tính chất lợi suất, biến động co cụm, GARCH, dữ liệu tần suất cao.
- Andrew Lo, Craig MacKinlay (1988), «Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test»,
  *Review of Financial Studies*: variance ratio và z\*.
- Torben Andersen, Tim Bollerslev (1997), «Intraday periodicity and volatility persistence in financial markets», *Journal of
  Empirical Finance*: vì sao phải khử mùa vụ mới thấy được động học biến động.
- Fulvio Corsi (2009), «A Simple Approximate Long-Memory Model of Realized Volatility», *Journal of Financial Econometrics*: HAR-RV.
- Danh mục quant ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md)): R3-13 (variance ratio), R3-25
  (ước lượng OHLC), R3-26 (mùa vụ), R3-27 (nén → bung), R4-10 (RV từ M1), R1-29 (HAR-RV).
