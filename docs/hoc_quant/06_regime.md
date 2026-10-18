# Module 6 — Regime

> **Sau module này bạn làm được:**
> - Giải thích vì sao regime là biến ẩn và vì sao mọi bộ phát hiện đều phải chọn giữa trễ và nhấp nháy.
> - Fit HMM bằng hmmlearn, tự viết bộ lọc forward, đo nó lệch Viterbi / làm trơn bao nhiêu nến.
> - Tự cài Kalman local linear trend và đọc «độ dốc / sai số chuẩn» như một chỉ số trend có độ bất định.
> - Tự cài CUSUM, đo trễ và báo động giả trên chuỗi mô phỏng có điểm đổi biết trước.
> - Đo độ bền một chuỗi trạng thái và kiểm một trục regime bằng shift test trước khi dùng.
>
> **Cần trước:** module 2 (p-value, kiểm định nhiều lần), 3 (null mô phỏng), 4 (biến động co cụm, mùa vụ trong ngày); module 5
> giúp hiểu độ trễ  ·  **Thời lượng:** ~7 giờ

> **Ba điều cần nhớ** (đọc lại khi ôn)
>
> 1. HMM chạy trên lợi suất tách trạng thái theo biến động, và học luôn cả giờ phiên, chứ không theo hướng.
> 2. Chỉ lọc forward dùng được ở từng nến; Viterbi và làm trơn nhìn cả chuỗi. Mọi bộ phát hiện đều đánh đổi giữa độ trễ và độ nhấp nháy.
> 3. Hai trục: trục biến động qua cổng thống kê (p = 0,002); trục hướng theo độ dốc Kalman không qua, ở M15 (p = 0,31) lẫn H1 (p = 0,54), với cấu hình đã thử.

## Vì sao cần

Giai đoạn 4 của lab ([plan_bias_regime.md](../plans/plan_bias_regime.md)) muốn gán ở mỗi nến M15 một trong các trạng thái
Trend ↑ / Trend ↓ / Range / Breakout / Uncertain, chỉ dùng thông tin đã biết, để repo giao dịch chọn chiến lược. Có hai sự
thật khó chịu. Thứ nhất, không ai quan sát được regime: nó chỉ tồn tại trong một mô hình hay một định nghĩa. Thứ hai, mọi bộ
phát hiện đều trễ, và bộ nào bớt trễ thì nhấp nháy nhiều hơn. Số liệu của lab đã cho thấy điều này. Bộ Trend/Range hiện có
gần như không bao giờ báo Range. Đoạn order flow một chiều kéo dài trung vị khoảng 13 giờ. Danh mục quant kết luận «biến động
đoán được, hướng thì gần như không» và đề xuất regime hai trục. Module này cho bạn các công cụ để tự đo những điều đó.

## 1. Regime là gì và vì sao khó

**Trực giác.** «Mùa mưa» không nhìn thấy được; bạn chỉ thấy từng ngày mưa hay nắng, rồi đoán mùa từ chuỗi ngày đó. Gặp vài
ngày nắng giữa mùa mưa, bạn có đổi ý ngay không?

**Định nghĩa.** **Regime** (chế độ thị trường) là một **trạng thái ẩn (hidden state)** điều khiển cách giá chạy. **Trend**:
giá đi một hướng, hồi nông. **Range**: giá bị giữ giữa hai biên. **Chuyển tiếp**: vừa phá biên hoặc vừa đổi chiều, chưa rõ.
Vì không quan sát được, mỗi regime là đầu ra của một luật hay một mô hình $s_t = f(x_1, \dots, x_t)$, tức trạng thái ở nến t
chỉ được tính từ dữ liệu tới t. Ba thước đo **độ bền (persistence)** của một chuỗi trạng thái:

- **tỷ lệ thời gian** của từng trạng thái;
- **số lần đổi mỗi ngày**;
- **độ dài đoạn**: một đoạn là dãy nến liên tiếp cùng trạng thái. Xem trung vị, P90 và % đoạn ngắn.

Regime có sẵn của lab là `dc_regime` trong `dc_atr_structure`: Trend khi hai đỉnh và hai đáy DC gần nhất cùng tăng hoặc cùng
giảm, Range khi các pivot gom thành hai cụm biên.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def do_ben(chuoi, thoi_gian, phut=15):
    """Độ bền của một chuỗi trạng thái: số lần đổi / ngày giao dịch, độ dài đoạn (nến)."""
    s = pd.Series(chuoi).reset_index(drop=True)
    ma_doan = (s != s.shift()).cumsum()
    dai = s.groupby(ma_doan).size()
    # ngày giao dịch kết thúc 17:00 New York (như lab)
    ngay = (pd.DatetimeIndex(thoi_gian).tz_convert("America/New_York") + pd.Timedelta(hours=7)).normalize().nunique()
    return {"đổi / ngày": (len(dai) - 1) / ngay, "đoạn TV (nến)": dai.median(), "đoạn TV (giờ)": dai.median() * phut / 60,
            "đoạn P90 (nến)": dai.quantile(.9), "% đoạn < 4 nến": 100 * (dai < 4).mean()}

ket_qua = {}
for ten, p in (("reset", {}), ("bridge_short 2h", {"gap_policy": "bridge_short"})):
    tl = chay_thuat_toan("dc_atr_structure", XAU_M15, "2024-01-01", "2024-09-01", tham_so=p)["timeline"]
    tl = tl[tl.regime != "WARMUP"]                     # khởi động không phải regime
    ty_le = (100 * tl.regime.value_counts(normalize=True)).round(1).to_dict()
    ket_qua[ten] = {**{"% " + k: v for k, v in ty_le.items()},
                    **do_ben(tl.regime.to_numpy(), pd.to_datetime(tl.time, unit="s", utc=True))}
print(pd.DataFrame(ket_qua).round(2).to_string())
```

```text
Kết quả khi mình chạy:
                 reset  bridge_short 2h
% UNKNOWN        80.20            49.80
% UPTREND        11.40            27.10
% DOWNTREND       8.40            23.10
đổi / ngày        1.62             2.83
đoạn TV (nến)    30.00            21.00
đoạn TV (giờ)     7.50             5.25
đoạn P90 (nến)  126.90            73.00
% đoạn < 4 nến    4.96             7.55
```

Với cấu hình mặc định (`reset`), 80% thời gian là «chưa rõ» và **không có một nến Range nào**. Nối khoảng trống ngắn
(`bridge_short`) đưa «chưa rõ» xuống 50%, nhưng số lần đổi tăng từ 1,6 lên 2,8 mỗi ngày và đoạn trung vị ngắn lại từ 7,5 xuống
5,25 giờ.

**Bẫy hay gặp.**
- «Range 0%» không có nghĩa là vàng không bao giờ đi ngang. Nó có nghĩa là điều kiện Range của định nghĩa này quá chặt (đặc tả
  DC §8b). Tỷ lệ thời gian là tính chất của **định nghĩa cộng thị trường**, không phải của riêng thị trường.
- Trạng thái khởi động (`WARMUP`) và dữ liệu thiếu không phải regime. Bỏ chúng ra khỏi mẫu số
  ([AGENTS.md](../../AGENTS.md) §2.2, plan §4.2).

## 2. HMM: trạng thái ẩn, và vì sao nó tách theo biến động

**Trực giác.** Có hai cái hộp sinh lợi suất: hộp «êm» (dao động nhỏ) và hộp «động» (dao động lớn). Mỗi nến, một đồng xu thiên
lệch quyết định có đổi hộp hay không. Bạn chỉ thấy lợi suất, không thấy hộp.

**Định nghĩa.** **Mô hình Markov ẩn (hidden Markov model, HMM)** với K trạng thái:

$$P(s_t = j \mid s_{t-1} = i) = A_{ij}, \qquad x_t \mid (s_t = k) \sim \mathcal{N}(\mu_k, \Sigma_k)$$

$A_{ij}$ là xác suất chuyển từ trạng thái i sang j. $\mu_k, \Sigma_k$ là trung bình và hiệp phương sai của đặc trưng $x_t$ khi
đang ở trạng thái k. $A_{ii}$ đo độ «dính»: số nến kéo dài kỳ vọng là $1/(1 - A_{ii})$. hmmlearn ước lượng mọi tham số bằng
thuật toán EM (`fit`). Thử với đặc trưng giống `hmm_online`: lợi suất r và |r| trên H1, một lần với lợi suất thô và một lần
sau khi khử mùa vụ trong ngày (module 4).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from hmmlearn.hmm import GaussianHMM

df = nap_nen(XAU_H1, "2021-01-01", "2024-01-01")          # 3 năm để fit
r = 100 * np.log(df["close"]).diff().dropna()              # lợi suất log, đơn vị %
gio = r.index.hour
mua = r.abs().groupby(gio).mean()                          # |r| trung bình theo giờ UTC (mùa vụ — module 4)
r_khu = r / mua.reindex(gio).to_numpy()                    # lợi suất đã khử mùa vụ (đơn vị: «lần mức thường của giờ đó»)

for ten, s in (("THÔ", r), ("ĐÃ KHỬ MÙA VỤ", r_khu)):
    X = np.column_stack([s, s.abs()])                      # đặc trưng như hmm_online: r và |r|
    m = GaussianHMM(n_components=3, covariance_type="diag", n_iter=200, random_state=0).fit(X)
    tt = m.predict(X)
    sd = np.sqrt(np.diagonal(m.covars_, axis1=1, axis2=2))[:, 0]
    thu_tu = np.argsort(sd)                                # xếp trạng thái từ êm tới động
    a = np.diag(m.transmat_)
    bang = pd.DataFrame({
        "TB r": m.means_[thu_tu, 0], "σ r": sd[thu_tu], "TB |r|": m.means_[thu_tu, 1],
        "A_ii": a[thu_tu], "kéo dài kỳ vọng (giờ)": 1 / (1 - a[thu_tu]),
        "% thời gian": [100 * (tt == k).mean() for k in thu_tu],
        "% lúc 03h UTC": [100 * (tt[gio == 3] == k).mean() for k in thu_tu],
        "% lúc 13h UTC": [100 * (tt[gio == 13] == k).mean() for k in thu_tu],
    }, index=["êm", "vừa", "động"])
    print("== HMM 3 trạng thái trên lợi suất H1", ten)
    print(bang.round(3).to_string())
```

```text
Kết quả khi mình chạy:
== HMM 3 trạng thái trên lợi suất H1 THÔ
       TB r    σ r  TB |r|   A_ii  kéo dài kỳ vọng (giờ)  % thời gian  % lúc 03h UTC  % lúc 13h UTC
êm   -0.001  0.034   0.029  0.473                  1.899       40.146         52.781         16.300
vừa   0.001  0.129   0.120  0.507                  2.030       47.353         45.019         43.338
động  0.001  0.435   0.370  0.351                  1.541       12.501          2.199         40.362
== HMM 3 trạng thái trên lợi suất H1 ĐÃ KHỬ MÙA VỤ
       TB r    σ r  TB |r|   A_ii  kéo dài kỳ vọng (giờ)  % thời gian  % lúc 03h UTC  % lúc 13h UTC
êm   -0.005  0.319   0.271  0.433                  1.762       39.592         36.740         38.163
vừa   0.003  1.201   1.109  0.541                  2.180       51.674         54.981         52.523
động  0.073  3.930   3.193  0.262                  1.355        8.734          8.279          9.314
```

Đọc bảng:

- **Trung bình r gần 0 ở mọi trạng thái**, còn σ khác nhau tới 13 lần. HMM tách theo **biến động**, không theo **hướng**, đúng
  như Persson (2021) thấy trên EURUSD (danh mục R1-06).
- Bản thô **học cái đồng hồ**: trạng thái «động» chiếm 40% lúc 13h UTC (New York mở cửa) nhưng chỉ 2% lúc 03h. Sau khi khử mùa
  vụ, tỷ lệ theo giờ đều nhau (8–9%).
- $A_{ii}$ = 0,26–0,54, tức mỗi trạng thái kéo dài kỳ vọng chưa tới 2,2 giờ: nhấp nháy. Khi |r| là một đặc trưng Gauss riêng,
  mỗi nến gần như tự quyết định trạng thái của mình.

**Bẫy hay gặp.**
- Đặt tên «trend», «range» cho trạng thái sau khi đã xem kết quả là một quyết định nghiên cứu. `hmm_online` mặc định không gắn
  nghĩa ([thuat_toan_hmm_online.md](../algorithms/thuat_toan_hmm_online.md)).
- `hmm_online` dùng r, |r| và biên độ / close **thô**, nên dễ học giờ phiên như bản thô ở trên.
- EM có thể dừng ở cực trị cục bộ. Cố định `random_state`, thử vài hạt giống, và ghi lại.

## 3. Lọc forward so với làm trơn và Viterbi

**Trực giác.** Đọc nhật ký từng ngày một rồi đoán «hôm nay là mùa gì» là **lọc**. Đọc hết cả cuốn rồi quay lại gán mùa cho
từng ngày là **làm trơn**. Cách thứ hai đẹp hơn, nhưng lúc giao dịch bạn chưa có phần sau của cuốn nhật ký.

**Định nghĩa.**
- **Lọc (filtering):** $P(s_t \mid x_1, \dots, x_t)$, chỉ dùng dữ liệu tới t.
- **Làm trơn (smoothing):** $P(s_t \mid x_1, \dots, x_T)$ với T > t, dùng cả tương lai.
- **Viterbi:** chuỗi trạng thái có xác suất cao nhất cho **cả** dãy $x_1..x_T$.

Thuật toán **forward** tính xác suất lọc từng bước:

$$\alpha_t(j) \;\propto\; b_j(x_t) \sum_i \alpha_{t-1}(i)\, A_{ij}$$

$\alpha_t(j)$ là xác suất đang ở j sau khi thấy dữ liệu tới t. Tổng bên phải là «dự báo» từ nến trước qua ma trận chuyển.
$b_j(x_t)$ là mật độ của $x_t$ nếu đang ở j; chuẩn hoá để tổng các $\alpha_t$ bằng 1. Trong hmmlearn, `predict` là Viterbi và
`predict_proba` là làm trơn, cả hai nhìn cả chuỗi. hmmlearn không có hàm lọc nên phải tự viết (R1-06). Lần này chỉ dùng một
đặc trưng r (đã khử mùa vụ), K = 2: không có |r|, HMM phải gom bằng chứng qua nhiều nến nhờ ma trận chuyển.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from hmmlearn.hmm import GaussianHMM

df = nap_nen(XAU_H1, "2021-01-01", "2024-09-01")
r = 100 * np.log(df["close"]).diff().dropna()
gio, fit = r.index.hour, r.index < "2024-01-01"            # fit trên 2021–2023, dùng trên 01–08/2024
mua = r[fit].abs().groupby(gio[fit]).mean()                # mùa vụ chỉ tính trên đoạn fit
z = (r / mua.reindex(gio).to_numpy()).to_numpy()[:, None]  # MỘT đặc trưng: r đã khử mùa vụ
m = GaussianHMM(n_components=2, covariance_type="diag", n_iter=200, random_state=0).fit(z[fit])
dong = int(np.argmax(m.covars_.ravel()))                   # trạng thái «động» = σ lớn hơn
print("σ hai trạng thái:", np.sqrt(m.covars_.ravel()).round(2), "| A_ii:", np.diag(m.transmat_).round(3))

def loc_forward(m, X):
    """Xác suất LỌC P(trạng thái t | x_1..x_t): mỗi bước chỉ dùng dữ liệu tới t."""
    var, mu = m.covars_.ravel(), m.means_.ravel()
    alpha, p = np.empty((len(X), len(mu))), m.startprob_
    for t, x in enumerate(X.ravel()):
        lb = -0.5 * (x - mu) ** 2 / var - 0.5 * np.log(var)       # log mật độ Gauss của x ở từng trạng thái
        p = (p if t == 0 else alpha[t - 1] @ m.transmat_) * np.exp(lb - lb.max())
        alpha[t] = p / p.sum()
    return alpha

X = z[~fit]
loc = loc_forward(m, X)
f = (loc.argmax(1) == dong).astype(int)                    # lọc: nhân quả
v = (m.predict(X) == dong).astype(int)                     # Viterbi: nhìn cả chuỗi
s = (m.predict_proba(X).argmax(1) == dong).astype(int)     # làm trơn forward–backward: nhìn cả chuỗi
print("kiểm: |lọc của mình − predict_proba trên TIỀN TỐ, nến cuối| lớn nhất = %.1e" % max(
    abs(m.predict_proba(X[:k + 1])[-1] - loc[k]).max() for k in (5, 700, 3000)))
ngay = len(X) / 23                                         # ~23 nến H1 mỗi ngày giao dịch
print("nến khác Viterbi: lọc %d / %d (%.1f%%), làm trơn %.1f%%" % (
    (f != v).sum(), len(X), 100 * (f != v).mean(), 100 * (s != v).mean()))
print("đổi / ngày: lọc %.2f | làm trơn %.2f | Viterbi %.2f" % tuple((np.diff(c) != 0).sum() / ngay for c in (f, s, v)))
doi_v = np.flatnonzero(np.diff(v)) + 1                     # Viterbi đổi sang j ở nến a: bao lâu sau lọc mới ở j?
tre = [np.argmax(f[a:] == v[a]) for a in doi_v]
print("trễ của lọc so với Viterbi: TV %.0f nến, P90 %.0f nến (%d lần đổi)" % (np.median(tre), np.percentile(tre, 90), len(tre)))
cat = np.random.default_rng(0).choice(np.arange(100, len(X) - 50), 200, replace=False)
print("Viterbi chạy trên tiền tố: nhãn nến cuối bị đổi khi có thêm tương lai ở %.1f%% điểm cắt" % (
    100 * np.mean([(m.predict(X[:k + 1])[-1] == dong) != v[k] for k in cat])))
```

```text
Kết quả khi mình chạy:
σ hai trạng thái: [1.06 3.76] | A_ii: [0.962 0.628]
kiểm: |lọc của mình − predict_proba trên TIỀN TỐ, nến cuối| lớn nhất = 1.2e-13
nến khác Viterbi: lọc 137 / 3965 (3.5%), làm trơn 1.4%
đổi / ngày: lọc 1.80 | làm trơn 1.35 | Viterbi 0.97
trễ của lọc so với Viterbi: TV 0 nến, P90 1 nến (168 lần đổi)
Viterbi chạy trên tiền tố: nhãn nến cuối bị đổi khi có thêm tương lai ở 4.0% điểm cắt
```

Đọc kết quả:

- Bộ lọc tự viết khớp `predict_proba` chạy trên **tiền tố**, ở nến cuối (lệch cỡ 1e-13, chỉ là sai số làm tròn). Làm trơn ở
  nến cuối của tiền tố chính là lọc. Đó là cách kiểm bộ lọc của bạn.
- Lọc khác Viterbi ở 137 / 3 965 nến (3,5%). Nhưng lọc đổi 1,80 lần / ngày, Viterbi chỉ 0,97. Bộ lọc không chậm hơn nhiều
  (trễ trung vị 0, P90 1 nến) mà **ồn hơn**: một nến lớn là nó nhảy sang «động», rồi lại nhảy về.
- Nếu hiển thị Viterbi «sống» (chạy lại mỗi nến), nhãn của nến mới nhất bị sửa về sau ở 4% số lần. Đó là chart vẽ lại.

**Bẫy hay gặp.**
- Backtest bằng `predict` hay `predict_proba` là nhìn tương lai. Chuỗi trạng thái trông bền hơn (0,97 so với 1,80 lần đổi / ngày)
  so với mọi thứ bạn có được lúc chạy thật.
- Fit trên cả đoạn rồi lọc lại chính đoạn đó thì tham số đã «thấy» tương lai. Fit trên đoạn trước, đóng băng, rồi mới lọc đoạn
  sau, như khối code trên và như `hmm_online`.

## 4. Kalman local linear trend: độ dốc có sai số

**Trực giác.** GPS ước lượng vị trí và vận tốc của xe từ những lần đo bị nhiễu. Ở đây «vận tốc» là độ dốc của giá. Kalman cho
bạn cả ước lượng lẫn độ bất định của nó.

**Định nghĩa.** Với $y_t$ = 100 × log close (đơn vị %):

$$y_t = \mu_t + \varepsilon_t, \qquad \mu_{t+1} = \mu_t + \nu_t + \xi_t, \qquad \nu_{t+1} = \nu_t + \zeta_t$$

$\mu_t$ là **mức** (giá «thật» không nhiễu), $\nu_t$ là **độ dốc** (% mỗi nến). $\varepsilon$, $\xi$, $\zeta$ là nhiễu quan sát,
nhiễu mức và nhiễu độ dốc, độ lệch chuẩn lần lượt $\sigma_\varepsilon, \sigma_\xi, \sigma_\zeta$. Mỗi nến, **bộ lọc Kalman**
dự báo (mức + dốc), xem sai số dự báo, rồi sửa ước lượng theo **độ lợi Kalman (Kalman gain)**. Kết quả là độ dốc lọc $\hat\nu_t$ và sai số
chuẩn $SE_t$, cả hai chỉ dùng dữ liệu tới t. **Chỉ số trend** là $z_t = \hat\nu_t / SE_t$: |z| lớn nghĩa là độ dốc khác 0 «chắc
chắn» theo mô hình. Ước lượng nhiễu đơn giản: thử một lưới giá trị, chọn bộ cho **log-likelihood** của sai số dự báo một bước
lớn nhất (MLE trên lưới).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def kalman_llt(y, s_eps, s_xi, s_zeta):
    """Local linear trend: y = mức + ε;  mức(t+1) = mức + dốc + ξ;  dốc(t+1) = dốc + ζ.
    Trả mức lọc, độ dốc lọc, sai số chuẩn của độ dốc (chỉ dùng y tới t) và log-likelihood dự báo một bước."""
    n = len(y)
    muc, doc, se = np.empty(n), np.empty(n), np.empty(n)
    m, d = y[0], 0.0
    P00, P01, P11 = 1e2, 0.0, 1e2                         # rất bất định lúc đầu
    ll = 0.0
    for t in range(n):
        if t > 0:                                         # bước DỰ BÁO
            m = m + d
            P00, P01, P11 = P00 + 2 * P01 + P11 + s_xi ** 2, P01 + P11, P11 + s_zeta ** 2
        F = P00 + s_eps ** 2                              # phương sai sai số dự báo
        e = y[t] - m                                      # sai số dự báo (innovation)
        if t > 1:
            ll += -0.5 * (np.log(2 * np.pi * F) + e * e / F)
        K0, K1 = P00 / F, P01 / F                         # độ lợi Kalman
        m, d = m + K0 * e, d + K1 * e                     # bước CẬP NHẬT
        P00, P01, P11 = (1 - K0) * P00, (1 - K0) * P01, P11 - K1 * P01
        muc[t], doc[t], se[t] = m, d, np.sqrt(P11)
    return muc, doc, se, ll

df = nap_nen(XAU_H1, "2023-01-01", "2024-09-01")
y = 100 * np.log(df["close"].to_numpy())                  # log giá × 100 → độ dốc đơn vị «% mỗi giờ»
fit = df.index < "2024-01-01"
s = np.diff(y[fit]).std()                                 # độ lệch chuẩn lợi suất H1 của 2023

# Ước lượng nhiễu đơn giản: lưới (σ_ε, σ_ζ) theo bội của s; σ_ξ chọn để phương sai Δy khớp s².
bang = {}
for fe in (0.0, 0.2):
    for fz in (1e-4, 1e-3, 1e-2, 3e-2, 1e-1):
        s_eps = fe * s
        bang[(fe, fz)] = kalman_llt(y[fit], s_eps, np.sqrt(s * s - 2 * s_eps ** 2), fz * s)[3]
print("log-likelihood trên 2023 (hàng σ_ε/s, cột σ_ζ/s):")
print(pd.Series(bang).unstack().round(1).to_string())

# Chọn theo THANG THỜI GIAN (không theo MLE): σ_ζ = 0,03 s ≈ độ dốc «nhớ» cỡ 1–2 ngày
s_eps, s_zeta = 0.2 * s, 0.03 * s
s_xi = np.sqrt(s * s - 2 * s_eps ** 2)

def mo_ta(y):
    _, doc, se, _ = kalman_llt(y, s_eps, s_xi, s_zeta)
    zz = (doc / se)[~fit]                                 # z = độ dốc / sai số chuẩn, trên 01–08/2024
    h = pd.Series(np.where(zz > 2, 1, np.where(zz < -2, -1, 0)))
    dai = h.groupby((h != h.shift()).cumsum()).size()
    return {"% z > 2": 100 * (zz > 2).mean(), "% z < −2": 100 * (zz < -2).mean(), "% |z| > 1": 100 * (abs(zz) > 1).mean(),
            "độ lệch chuẩn z": zz.std(), "đổi / ngày (ngưỡng 2)": (len(dai) - 1) / (len(zz) / 23),
            "sai số chuẩn dốc (%/giờ)": se[~fit].mean()}

rng = np.random.default_rng(3)
y_nn = y[0] + np.cumsum(np.r_[0, rng.normal(0, s, len(y) - 1)])   # bước ngẫu nhiên, cùng σ, KHÔNG có trend
print(pd.DataFrame({"XAU H1 thật": mo_ta(y), "bước ngẫu nhiên": mo_ta(y_nn)}).round(3).to_string())

# Với nhiễu cố định, độ dốc lọc chỉ là trung bình trượt mũ (EMA) của lợi suất:
_, doc, _, _ = kalman_llt(y, 0.0, s, s_zeta)
dy = pd.Series(np.diff(y, prepend=y[0]))
print("tương quan(độ dốc Kalman σ_ε=0, EMA lợi suất α=0,03): %.4f" % np.corrcoef(doc[100:], dy.ewm(alpha=0.03).mean()[100:])[0, 1])
```

```text
Kết quả khi mình chạy:
log-likelihood trên 2023 (hàng σ_ε/s, cột σ_ζ/s):
     0.0001  0.0010  0.0100  0.0300  0.1000
0.0  2041.9  2041.1  2030.5  2000.4  1900.9
0.2  2036.7  2036.0  2026.0  1997.1  1901.8
                          XAU H1 thật  bước ngẫu nhiên
% z > 2                         0.984            0.151
% z < −2                        0.807            0.025
% |z| > 1                      20.101           21.513
độ lệch chuẩn z                 0.781            0.782
đổi / ngày (ngưỡng 2)           0.232            0.035
sai số chuẩn dốc (%/giờ)        0.029            0.029
tương quan(độ dốc Kalman σ_ε=0, EMA lợi suất α=0,03): 1.0000
```

Đọc kết quả:

- **MLE chọn σ_ζ nhỏ nhất và σ_ε = 0**: mô hình dự báo một bước tốt nhất là bước ngẫu nhiên với độ dốc gần như cố định. Điều
  này khớp với module 3–4: lợi suất gần như không đoán được. MLE không giúp chọn «trend thay đổi nhanh cỡ nào». σ_ζ là núm
  **thang thời gian**: σ_ζ = 0,03 s cho độ dốc «nhớ» khoảng 1/0,03 ≈ 33 nến.
- Tỷ lệ |z| > 1 gần như bằng bước ngẫu nhiên (20,1% so với 21,5%), độ lệch chuẩn của z cũng vậy (0,781 so với 0,782). Chỉ ở
  đuôi (|z| > 2) dữ liệu thật mới nhiều hơn: 1,8% so với 0,18%.
- Sai số chuẩn của độ dốc **gần như hằng số** (0,029 %/giờ), và độ dốc lọc trùng với EMA của lợi suất (tương quan 1,0000). Với
  nhiễu cố định, «Kalman trend» chính là momentum EMA chia cho một hằng số.

**Bẫy hay gặp.**
- SE hằng số nên z không biết biến động đổi. Một đợt biến động mạnh tự đẩy |z| lên. Phần «|z| > 2 nhiều hơn ngẫu nhiên» rất có
  thể đến từ biến động co cụm chứ không phải trend (mục 7 thấy rõ). Muốn SE có nghĩa, hãy chuẩn hoá lợi suất theo biến động
  trước (module 4).
- Dùng độ dốc **làm trơn** (bộ làm trơn RTS, hay trạng thái smoothed của các thư viện) là nhìn tương lai (danh mục R1-25).

## 5. Phát hiện điểm đổi: CUSUM

**Trực giác.** Cộng dồn «điểm bất thường»: nến lớn hơn bình thường thì cộng, nến nhỏ thì trừ, không cho tổng xuống dưới 0. Tổng
vượt ngưỡng thì báo «biến động đã đổi».

**Định nghĩa.** Gọi $x_t = |r_t| / \text{mức tham chiếu}$ (dữ liệu thật thì khử mùa vụ trước). **CUSUM** (Page, 1954) dò tăng:

$$S_t = \max(0,\; S_{t-1} + x_t - 1 - k), \qquad \text{báo động khi } S_t > h$$

k là **dung sai**: lệch nhỏ hơn k thì không cộng dồn. h là **ngưỡng báo động**. Bản hai trạng thái: đang «thấp» thì dò tăng
như trên; đang «cao» thì dò giảm với $S'_t = \max(0, S'_{t-1} + 1 - k - x_t)$; mỗi lần báo động thì đổi trạng thái và đặt lại
tổng. Ba con số để chấm: **trễ phát hiện (detection delay)**, từ điểm đổi thật tới báo động đúng chiều; **báo động giả (false
alarm)**; và **ARL0 (average run length)**, tức số nến trung bình giữa hai báo động khi không có gì đổi. Không có điểm đổi
biết trước thì không đo được trễ, nên ta dùng mô phỏng.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def mo_phong(T, rng, co_doi=True):
    """Lợi suất có σ luân phiên 1 ↔ 2 theo đoạn dài 150–600 nến (biết trước), nhiễu Student-t 4 bậc tự do (đuôi dày)."""
    sig, diem_doi, t, cao = np.empty(T), [], 0, False
    while t < T:
        L = int(rng.integers(150, 600))
        sig[t:t + L] = (2.0 if cao else 1.0) if co_doi else 1.5
        t += L; cao = not cao
        if t < T and co_doi: diem_doi.append(t)
    return sig * rng.standard_t(4, T) / np.sqrt(2.0), sig, np.array(diem_doi)

def cusum_bien_dong(x, h, k=0.1):
    """CUSUM hai trạng thái trên x = |r| đã chuẩn hoá (mức tham chiếu 1). Đang «thấp» thì dò TĂNG, đang «cao» thì dò GIẢM."""
    trang_thai, bao_dong = np.zeros(len(x), int), []
    s_len = s_xuong = 0.0
    cur = 0
    for t, v in enumerate(x):
        if cur == 0:
            s_len = max(0.0, s_len + v - 1 - k)           # cộng dồn phần |r| vượt mức tham chiếu
            if s_len > h: cur, s_len = 1, 0.0; bao_dong.append((t, 1))
        else:
            s_xuong = max(0.0, s_xuong + 1 - k - v)
            if s_xuong > h: cur, s_xuong = 0, 0.0; bao_dong.append((t, 0))
        trang_thai[t] = cur
    return trang_thai, bao_dong

def cham(bao_dong, diem_doi, sig, T):
    """Điểm đổi τ được phát hiện bởi báo động ĐÚNG CHIỀU đầu tiên trong [τ, điểm đổi kế); báo động còn lại là giả."""
    tre, dung = [], set()
    for tau, het in zip(diem_doi, list(diem_doi[1:]) + [T]):
        k = next((n for n, (a, s) in enumerate(bao_dong)
                  if s == int(sig[tau] == 2.0) and tau <= a < het and n not in dung), None)
        if k is not None:
            dung.add(k); tre.append(bao_dong[k][0] - tau)
    return tre, len(bao_dong) - len(dung)

T = 30000
r, sig, diem_doi = mo_phong(T, np.random.default_rng(42))
x = np.abs(r) / np.abs(r[:2000]).mean()                   # chuẩn hoá bằng 2000 nến đầu («đoạn huấn luyện»)
r0, sig0, _ = mo_phong(T, np.random.default_rng(43), co_doi=False)   # không có điểm đổi nào (σ = 1,5 cố định)
x0 = np.abs(r0) / np.abs(r0[:2000]).mean()

dong = []
for h in (2, 4, 8, 16, 32):
    tt, bd = cusum_bien_dong(x, h)
    tre, gia = cham(bd, diem_doi, sig, T)
    dong.append((h, "%d/%d" % (len(tre), len(diem_doi)), np.median(tre), np.percentile(tre, 90),
                 1000 * gia / T, 1000 * len(cusum_bien_dong(x0, h)[1]) / T, 100 * (tt == (sig == 2)).mean()))
print(pd.DataFrame(dong, columns=["h", "phát hiện", "trễ TV (nến)", "trễ P90", "báo giả /1000 nến",
                                  "báo động /1000 nến khi KHÔNG có đổi", "% nến đúng trạng thái"]).round(2).to_string(index=False))
```

```text
Kết quả khi mình chạy:
 h phát hiện  trễ TV (nến)  trễ P90  báo giả /1000 nến  báo động /1000 nến khi KHÔNG có đổi  % nến đúng trạng thái
 2     77/78           5.0     25.8              33.97                                61.50                  85.31
 4     78/78          12.0     28.6               4.27                                17.97                  92.94
 8     78/78          27.0     45.6               0.20                                 5.03                  92.08
16     78/78          58.0    112.6               0.00                                 0.47                  83.04
32     72/78         124.0    184.9               0.00                                 0.03                  66.09
```

h nhỏ thì báo nhanh nhưng giả nhiều (h = 2: 34 báo giả / 1000 nến). h lớn thì gần như không báo giả nhưng trễ dài, và h = 32 bỏ
lỡ 6 / 78 điểm đổi. Cột «không có đổi» là baseline «không có điểm đổi» (danh mục R2-35, R7-46): σ cố định 1,5, nằm giữa hai
mức. Bộ hai trạng thái khi đó vẫn lật qua lại (h = 8: 5 lần / 1000 nến), vì không trạng thái nào đúng cả.

**Bẫy hay gặp.**
- CUSUM trên |r| M15 thô sẽ báo động mỗi lần mở phiên London hay New York. Phải khử mùa vụ trước (danh mục R2-25).
- k và h tính theo đơn vị của x. Không chuẩn hoá thì ngưỡng vô nghĩa (danh mục R2-02 ghi rõ chỗ này với Page–Hinkley). Page–
  Hinkley là bài tập 1.

## 6. Đánh đổi trễ ↔ nhấp nháy, và đo độ bền

**Trực giác.** Chuông báo trộm quá nhạy thì kêu khi gió thổi; quá lì thì trộm vào nhà rồi mới kêu.

**Định nghĩa.** **Nhấp nháy (flicker)** là đổi trạng thái rồi đổi lại sau vài nến. Plan §4.6 có hai núm chống nhấp nháy:

- **xác nhận c nến:** chỉ đổi khi tín hiệu thô khác trạng thái hiện tại c nến **liên tiếp**;
- **giữ tối thiểu (minimum hold) H nến:** đã vào trạng thái nào thì giữ ít nhất H nến.

Thử trên chuỗi biến động hai trạng thái có điểm đổi biết trước, tín hiệu thô là bộ lọc forward với **tham số đúng**, tức bộ nhân
quả tốt nhất có thể cho mô hình này:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# Chuỗi có regime BIẾT TRƯỚC: 2 trạng thái biến động σ = 1 ↔ 1,6, xác suất ở lại 0,99 (đoạn TB 100 nến),
# nhiễu Student-t 5 bậc tự do (đuôi dày hơn Gauss mà bộ lọc giả định).
rng = np.random.default_rng(5)
T, p_ii = 40000, 0.99
that = np.zeros(T, int)
for t in range(1, T):
    that[t] = that[t - 1] if rng.random() < p_ii else 1 - that[t - 1]
r = np.where(that == 1, 1.6, 1.0) * rng.standard_t(5, T) / np.sqrt(5 / 3)

# Bộ lọc forward với tham số ĐÚNG — bộ nhân quả tốt nhất có thể cho mô hình này
A = np.array([[p_ii, 1 - p_ii], [1 - p_ii, p_ii]])
b = np.column_stack([np.exp(-r ** 2 / 2) / 1.0, np.exp(-r ** 2 / (2 * 1.6 ** 2)) / 1.6])
p, loc = np.array([0.5, 0.5]), np.empty(T)
for t in range(T):
    p = (p if t == 0 else p @ A) * b[t]; p = p / p.sum(); loc[t] = p[1]
tho = (loc > 0.5).astype(int)

def lam_ben(tho, c=1, H=0):
    """Đổi khi tín hiệu thô khác trạng thái hiện tại c nến LIÊN TIẾP và trạng thái hiện tại đã giữ ≥ H nến."""
    out, cur, dem, giu = np.empty_like(tho), tho[0], 0, 0
    for t, v in enumerate(tho):
        dem = dem + 1 if v != cur else 0
        giu += 1
        if dem >= c and giu >= H:
            cur, dem, giu = v, 0, 0
        out[t] = cur
    return out

doi_that = np.flatnonzero(np.diff(that)) + 1
def danh_gia(ch):
    doi = np.flatnonzero(np.diff(ch)) + 1
    bien = list(doi_that[1:]) + [T]
    tre, dung = [], set()
    for i, tau in enumerate(doi_that):                    # lần đổi ĐÚNG CHIỀU đầu tiên trong đoạn thật
        k = [a for a in doi[(doi >= tau) & (doi < bien[i])] if ch[a] == that[tau] and a not in dung]
        if k: dung.add(k[0]); tre.append(k[0] - tau)
    return {"đổi /1000 nến": 1000 * len(doi) / T, "đổi giả /1000 nến": 1000 * (len(doi) - len(dung)) / T,
            "% điểm đổi bắt được": 100 * len(tre) / len(doi_that), "trễ TV (nến)": np.median(tre),
            "trễ P90 (nến)": np.percentile(tre, 90), "% nến sai trạng thái": 100 * (ch != that).mean()}

print("thật: %.1f lần đổi /1000 nến" % (1000 * len(doi_that) / T))
bang = {"c=%d, H=%d" % (c, H): danh_gia(lam_ben(tho, c, H))
        for c, H in ((1, 0), (2, 0), (3, 0), (5, 0), (8, 0), (1, 10), (1, 20), (1, 40))}
print(pd.DataFrame(bang).T.round(1).to_string())
```

```text
Kết quả khi mình chạy:
thật: 9.6 lần đổi /1000 nến
           đổi /1000 nến  đổi giả /1000 nến  % điểm đổi bắt được  trễ TV (nến)  trễ P90 (nến)  % nến sai trạng thái
c=1, H=0            50.4               42.2                 85.4           7.0           24.4                  19.1
c=2, H=0            34.3               26.3                 83.0           9.0           30.0                  19.6
c=3, H=0            27.4               19.6                 81.2          11.0           35.0                  20.0
c=5, H=0            20.0               12.8                 74.9          13.0           40.0                  20.6
c=8, H=0            14.6                7.9                 70.5          17.0           44.1                  21.2
c=1, H=10           32.0               24.0                 82.8           9.0           28.4                  22.4
c=1, H=20           24.5               17.1                 77.3          11.0           33.0                  27.1
c=1, H=40           16.6               10.0                 68.4          15.0           66.0                  31.6
```

Ngay cả bộ lọc tốt nhất cũng đổi 50 lần / 1000 nến trong khi thật chỉ có 9,6; 42 lần là đổi giả. Tăng c lên 8 thì còn 14,6 lần
đổi và 7,9 đổi giả, đổi lại trễ trung vị tăng từ 7 lên 17 nến và chỉ bắt được 70,5% điểm đổi thay vì 85,4%. H = 40 làm trễ P90
tăng lên 66 nến. % nến sai không giảm. **Bớt nhấp nháy không có nghĩa là đúng hơn.** Không có điểm «tối ưu» chung: router cần
gì thì chọn theo đó. Plan 4a vẽ đường «số lần đổi / ngày» theo «trễ trung vị» và chọn chỗ khuỷu **trước khi** mở đoạn kiểm tra.

**Bẫy hay gặp.**
- Giữ tối thiểu làm lệch tỷ lệ thời gian khi hai trạng thái không cân xứng: một cú nhảy nhất thời sang trạng thái hiếm bị giữ
  đủ H nến. Báo tỷ lệ thời gian thì kèm c và H.
- Trên dữ liệu thật không có điểm đổi «thật». Muốn đo trễ phải có nhãn hậu kiểm (module 7, plan §6 M3) hoặc mô phỏng.

## 7. Regime hai trục và cổng «M15 hay H1»

**Trực giác.** «Thị trường đang động hay êm?» và «đang đi lên hay đi xuống?» là hai câu hỏi khác nhau. Gộp chúng thành một nhãn
«trending» từng làm repo cũ xếp xu hướng giảm vào «ranging/calm» (plan §1).

**Định nghĩa.** **Regime hai trục**: trục **biến động** (CUSUM của mục 5 trên |r| đã khử mùa vụ, so với mức 20 ngày trước) nhân
với trục **hướng** (z Kalman của mục 4, |z| > 1). **Cổng**: một trục chỉ được giữ ở khung đó nếu nó tách được tương lai tốt hơn
null; danh mục quant (§4) đề xuất trục hướng không qua ở M15 thì chuyển lên H1. Thống kê, với chân trời 4 giờ:

- biến động: trung bình |r| khử mùa vụ 4 giờ tới khi «cao» trừ khi «thấp»;
- hướng: trung bình lợi suất 4 giờ tới, nhân với chiều của z.

Null là **phép thử dịch vòng (shift test)** (danh mục R7-20): dịch vòng chuỗi trạng thái một đoạn ngẫu nhiên. Cách này giữ nguyên tự tương quan
và tỷ lệ thời gian của chuỗi trạng thái, chỉ phá liên hệ với tương lai. p = tỷ lệ lần dịch cho thống kê lớn ít nhất bằng số
thật.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def kalman_z(y, s_eps, s_xi, s_zeta):
    """Độ dốc lọc / sai số chuẩn của local linear trend (mục 4, rút gọn)."""
    z = np.empty(len(y)); m, d = y[0], 0.0; P00, P01, P11 = 1e2, 0.0, 1e2
    for t in range(len(y)):
        if t > 0:
            m = m + d; P00, P01, P11 = P00 + 2 * P01 + P11 + s_xi ** 2, P01 + P11, P11 + s_zeta ** 2
        F = P00 + s_eps ** 2; e = y[t] - m; K0, K1 = P00 / F, P01 / F
        m, d = m + K0 * e, d + K1 * e
        P00, P01, P11 = (1 - K0) * P00, (1 - K0) * P01, P11 - K1 * P01
        z[t] = d / np.sqrt(P11)
    return z

def cusum_bien_dong(x, h=8, k=0.1):
    """CUSUM hai trạng thái trên |r| đã chuẩn hoá (mục 5). 1 = biến động cao."""
    out, cur, s1, s0 = np.zeros(len(x), int), 0, 0.0, 0.0
    for t, v in enumerate(x):
        if cur == 0:
            s1 = max(0.0, s1 + v - 1 - k)
            if s1 > h: cur, s1 = 1, 0.0
        else:
            s0 = max(0.0, s0 + 1 - k - v)
            if s0 > h: cur, s0 = 0, 0.0
        out[t] = cur
    return out

def shift_test(trang_thai, ket_cuc, thong_ke, rng, n_lan=500):
    """Null: dịch vòng chuỗi trạng thái một đoạn ngẫu nhiên (giữ tự tương quan của nó, phá liên hệ với tương lai)."""
    n = len(trang_thai)
    that = thong_ke(trang_thai, ket_cuc)
    null = np.array([thong_ke(np.roll(trang_thai, k), ket_cuc) for k in rng.integers(n // 10, 9 * n // 10, n_lan)])
    return that, np.percentile(null, 2.5), np.percentile(null, 97.5), (1 + (np.abs(null) >= abs(that)).sum()) / (1 + n_lan)

def hai_truc(dataset, phut):
    df = nap_nen(dataset, "2023-01-01", "2024-09-01")
    y = 100 * np.log(df["close"].to_numpy())
    r = np.r_[0.0, np.diff(y)]
    fit = df.index < "2024-01-01"                         # 2023: chỉ để lấy thang đo / mùa vụ
    o = df.index.hour * 60 + df.index.minute              # ô giờ trong ngày (UTC)
    mua = pd.Series(np.abs(r[fit])).groupby(o[fit]).mean()
    x = np.abs(r) / mua.reindex(o).to_numpy()             # |r| đã khử mùa vụ
    muc = pd.Series(x).rolling(20 * 23 * 60 // phut).mean().shift(1).to_numpy()   # mức 20 ngày TRƯỚC t
    x = x / muc                                           # «cao/thấp» so với tháng vừa qua, không so với 2023
    s = r[fit].std()
    z = kalman_z(y, 0.2 * s, np.sqrt(s * s - 2 * (0.2 * s) ** 2), 0.03 * s)
    bd = cusum_bien_dong(x)
    huong = np.where(z > 1, 1, np.where(z < -1, -1, 0))   # ngưỡng |z| > 1: tham số thí nghiệm
    h = 240 // phut                                       # chân trời 4 giờ
    sau = ~fit
    sau[-h:] = False                                      # bỏ h nến cuối (chưa có tương lai)
    tl_sau = np.r_[y[h:] - y[:-h], np.full(h, np.nan)]    # lợi suất h nến tới (%)
    bd_sau = pd.Series(x).rolling(h).mean().shift(-h).to_numpy()   # biến động h nến tới
    return bd[sau], huong[sau], tl_sau[sau], bd_sau[sau]

rng = np.random.default_rng(1)
dong, chia = [], None
for ten, ds, phut in (("M15", XAU_M15_DAI, 15), ("H1", XAU_H1, 60)):
    bd, huong, tl_sau, bd_sau = hai_truc(ds, phut)
    if ten == "M15":
        chia = pd.crosstab(pd.Series(bd, name="biến động").map({0: "thấp", 1: "cao"}),
                           pd.Series(huong, name="hướng").map({1: "lên", -1: "xuống", 0: "không rõ"}), normalize="all")
    dong.append((ten, "biến động: |r| 4h tới, cao − thấp",
                 *shift_test(bd, bd_sau, lambda a, b: b[a == 1].mean() - b[a == 0].mean(), rng)))
    dong.append((ten, "hướng: lợi suất 4h tới theo chiều z (%)",
                 *shift_test(huong, tl_sau, lambda a, b: (a[a != 0] * b[a != 0]).mean(), rng)))
print("Tỷ lệ thời gian M15, 01–08/2024 (%):")
print((100 * chia).round(1).to_string())
print(pd.DataFrame(dong, columns=["khung", "trục: thống kê", "thật", "null 2,5%", "null 97,5%", "p (shift test)"]
                   ).round(4).to_string(index=False))
```

```text
Kết quả khi mình chạy:
Tỷ lệ thời gian M15, 01–08/2024 (%):
hướng      không rõ  lên  xuống
biến động                      
cao            36.3  6.6    5.9
thấp           46.2  3.3    1.7
khung                          trục: thống kê   thật  null 2,5%  null 97,5%  p (shift test)
  M15       biến động: |r| 4h tới, cao − thấp 0.2514    -0.1271      0.1033          0.0020
  M15 hướng: lợi suất 4h tới theo chiều z (%) 0.0230    -0.0409      0.0539          0.3114
   H1       biến động: |r| 4h tới, cao − thấp 0.2580    -0.1653      0.1101          0.0020
   H1 hướng: lợi suất 4h tới theo chiều z (%) 0.0137    -0.0394      0.0551          0.5409
```

Đọc kết quả:

- **Trục biến động qua cổng** ở cả hai khung (p = 0,002, mức nhỏ nhất đo được với 500 lần dịch: 1/501). Đúng như mong đợi:
  biến động co cụm, nên «vừa động» nghĩa là «sắp còn động».
- **Trục hướng không qua cổng** ở M15 (p = 0,31) lẫn H1 (p = 0,54). Theo đề xuất của danh mục, trục hướng kiểu này không dùng
  được ở M15, và lên H1 cũng không cứu được. Kết quả âm tính là kết quả hợp lệ (plan §0). Nó chỉ đúng cho **một** chỉ số
  hướng; chưa nói gì về bằng chứng ICT, thứ mà plan 4a sẽ đo cùng cách.
- Trong bảng tỷ lệ, hướng xuất hiện ở 25,6% số nến biến động cao (12,5 / 48,8) nhưng chỉ 9,8% số nến biến động thấp (5,0 / 51,2).
  Đó là cái bẫy SE hằng số của mục 4: z dính vào biến động.

**Bẫy hay gặp.**
- Mọi bộ phân loại dính biến động đều «tách» được kết cục tương lai, vì biến động tự tương quan. Plan §2.2 vì vậy đo độ tách
  **trong từng tầng ATR**.
- Thử nhiều ngưỡng, nhiều chân trời rồi báo cái p nhỏ nhất là kiểm định nhiều lần (module 2; bài tập 4).
- Không dùng t-test theo nến: các cửa sổ 4 giờ chồng nhau và trạng thái tự tương quan. Cỡ mẫu hiệu dụng gần với số đoạn hơn số
  nến (plan §6).

## Lab đang dùng những điều này ở đâu

| Khái niệm | File / tài liệu | Ghi chú |
|---|---|---|
| Regime theo luật (Trend/Range DC) | [regime.py](../../core/algorithms/dc_atr_structure/regime.py), [thuat_toan_dc_atr_structure.md](../algorithms/thuat_toan_dc_atr_structure.md) §6, §8 | Range ≤ 0,2% thời gian |
| HMM lọc online | [hmm_online/algorithm.py](../../core/algorithms/hmm_online/algorithm.py), [thuat_toan_hmm_online.md](../algorithms/thuat_toan_hmm_online.md) | Fit một lần trên `train_bars`, sau đó chỉ bước forward |
| Kế hoạch regime giai đoạn 4 | [plan_bias_regime.md](../plans/plan_bias_regime.md) §4.6 (giữ tối thiểu, xác nhận c), §6 (M2 độ bền, M3 trễ, shift test), §8 (cổng sau 4a) | Chưa có code |
| Regime hai trục, 6 đối thủ của ICT | [danh_muc_phuong_phap_quant.md](../research/danh_muc_phuong_phap_quant.md) §4 | R1-06, R1-25, R2-01/R2-02, R1-17, R7-20 |
| Tài liệu nền về regime, breakout, đánh giá | [nghien_cuu_bias_regime.md](../research/nghien_cuu_bias_regime.md) | Shift test, baseline «không có điểm đổi» |
| Baseline chỉ báo (ADX, Donchian) | [indicator_baseline](../../core/algorithms/indicator_baseline/algorithm.py), [thuat_toan_indicator_baseline.md](../algorithms/thuat_toan_indicator_baseline.md) | Baseline cho regime |
| Đoạn phát triển / kiểm tra | [segments.py](../../core/eval/segments.py) | Mọi tham số (h, c, H, ngưỡng z) chốt trên đoạn phát triển |
| Order flow (độ bền đoạn) | [thuat_toan_ict_structure.md](../algorithms/thuat_toan_ict_structure.md) §4.12, §7 `run_stats["order_flow"]` | Đổi / ngày, đoạn trung vị: cùng thước với mục 6 |

## Bài tập

**Bài 1 — Page–Hinkley.** Tự cài Page–Hinkley hai trạng thái trên cùng chuỗi mô phỏng của mục 5:
$m_T = \sum_{t \le T} (x_t - \bar x_T - \delta)$ với $\bar x_T$ là trung bình chạy kể từ lần đặt lại; báo động khi
$m_T - \min_{t \le T} m_t > \lambda$ (dò tăng; dò giảm đối xứng). So trễ và báo động giả với CUSUM ở h tương đương.
*Gợi ý:* không báo trong `n_min` = 30 nến đầu sau mỗi lần đặt lại.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# Cùng chuỗi mô phỏng và cách chấm như mục 5
def mo_phong(T, rng):
    sig, diem_doi, t, cao = np.empty(T), [], 0, False
    while t < T:
        L = int(rng.integers(150, 600)); sig[t:t + L] = 2.0 if cao else 1.0; t += L; cao = not cao
        if t < T: diem_doi.append(t)
    return sig * rng.standard_t(4, T) / np.sqrt(2.0), sig, np.array(diem_doi)

def page_hinkley(x, lam, delta=0.1, n_min=30):
    """Page–Hinkley hai trạng thái: đang thấp dò TĂNG trung bình, đang cao dò GIẢM; reset sau mỗi báo động."""
    bao, cur = [], 0
    n = tong = m = m_min = m_max = 0.0
    for t, v in enumerate(x):
        n += 1; tong += v; tb = tong / n                  # trung bình chạy kể từ lần reset
        if cur == 0:
            m += v - tb - delta; m_min = min(m_min, m)
            bao_dong = n > n_min and m - m_min > lam
        else:
            m += v - tb + delta; m_max = max(m_max, m)
            bao_dong = n > n_min and m_max - m > lam
        if bao_dong:
            cur = 1 - cur; bao.append((t, cur)); n = tong = m = m_min = m_max = 0.0
    return bao

def cham(bao_dong, diem_doi, sig, T):
    tre, dung = [], set()
    for tau, het in zip(diem_doi, list(diem_doi[1:]) + [T]):
        k = next((n for n, (a, s) in enumerate(bao_dong)
                  if s == int(sig[tau] == 2.0) and tau <= a < het and n not in dung), None)
        if k is not None:
            dung.add(k); tre.append(bao_dong[k][0] - tau)
    return tre, len(bao_dong) - len(dung)

T = 30000
r, sig, diem_doi = mo_phong(T, np.random.default_rng(42))
x = np.abs(r) / np.abs(r[:2000]).mean()
for lam in (4, 8, 16, 32):
    tre, gia = cham(page_hinkley(x, lam), diem_doi, sig, T)
    print("λ = %2d: phát hiện %d/%d, trễ TV %.0f nến, P90 %.0f, báo giả %.2f /1000 nến" % (
        lam, len(tre), len(diem_doi), np.median(tre), np.percentile(tre, 90), 1000 * gia / T))
```

```text
Kết quả khi mình chạy:
λ =  4: phát hiện 63/78, trễ TV 16 nến, P90 271, báo giả 8.97 /1000 nến
λ =  8: phát hiện 60/78, trễ TV 14 nến, P90 29, báo giả 2.93 /1000 nến
λ = 16: phát hiện 64/78, trễ TV 28 nến, P90 44, báo giả 0.73 /1000 nến
λ = 32: phát hiện 76/78, trễ TV 58 nến, P90 90, báo giả 0.07 /1000 nến
```

Page–Hinkley tự ước lượng mức tham chiếu (trung bình chạy) thay vì dùng mức cố định. Với λ nhỏ nó bỏ lỡ nhiều điểm đổi hơn
CUSUM (60–64 / 78): một báo động giả đặt nó vào sai trạng thái, rồi nó dò sai chiều cho tới lần báo kế tiếp. Với λ = 32 nó
bắt 76 / 78, trễ trung vị 58 nến, gần CUSUM h = 16. Không bộ nào «thắng» chung; mọi bộ đều nằm trên cùng một đường trễ ↔ báo giả.
</details>

**Bài 2 — Jump model online (R1-17).** Đặc trưng nhân quả: log biến động khử mùa vụ trung bình 6 giờ và 24 giờ. Tâm hai cụm lấy
bằng KMeans trên 2021–2023. Trên 2024, gán tham lam
$s_t = \arg\min_k \lVert f_t - \theta_k \rVert^2 + \lambda \cdot \mathbb{1}[k \ne s_{t-1}]$, tức khoảng cách tới tâm cụm cộng
một khoản phạt λ nếu đổi trạng thái. Thử λ = 0; 0,5; 1; 2; 4.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from sklearn.cluster import KMeans

df = nap_nen(XAU_H1, "2021-01-01", "2024-09-01")
r = 100 * np.log(df["close"]).diff().dropna()
gio, fit = r.index.hour, r.index < "2024-01-01"
x = r.abs() / r[fit].abs().groupby(gio[fit]).mean().reindex(gio).to_numpy()   # |r| khử mùa vụ
# Đặc trưng nhân quả: log biến động 6 giờ và 24 giờ gần nhất (chỉ dùng nến ≤ t)
f = np.column_stack([np.log(x.rolling(6).mean()), np.log(x.rolling(24).mean())])
ok = np.isfinite(f).all(axis=1)
mu, sd = f[fit & ok].mean(0), f[fit & ok].std(0)
f = (f - mu) / sd                                         # chuẩn hoá bằng thống kê của đoạn fit
tam = KMeans(2, n_init=10, random_state=0).fit(f[fit & ok]).cluster_centers_   # tâm cụm: chỉ từ 2021–2023
cao = int(np.argmax(tam[:, 0]))

ft = f[~fit]
d2 = ((ft[:, None, :] - tam[None]) ** 2).sum(axis=2)      # khoảng cách tới từng tâm
for lam in (0.0, 0.5, 1.0, 2.0, 4.0):
    s, cur = np.empty(len(ft), int), int(np.argmin(d2[0]))
    for t in range(len(ft)):                              # tham lam: không sửa quá khứ
        chi_phi = d2[t] + lam * (np.arange(2) != cur)
        cur = int(np.argmin(chi_phi)); s[t] = cur
    ch = pd.Series(s)
    dai = ch.groupby((ch != ch.shift()).cumsum()).size()
    print("λ = %.1f: đổi / ngày %.2f | đoạn TV %4.0f giờ | %% đoạn < 4 giờ %4.1f | %% thời gian «cao» %.1f" % (
        lam, (len(dai) - 1) / (len(ch) / 23), dai.median(), 100 * (dai < 4).mean(), 100 * (s == cao).mean()))
```

```text
Kết quả khi mình chạy:
λ = 0.0: đổi / ngày 2.12 | đoạn TV    5 giờ | % đoạn < 4 giờ 43.1 | % thời gian «cao» 50.2
λ = 0.5: đổi / ngày 1.58 | đoạn TV    8 giờ | % đoạn < 4 giờ 26.7 | % thời gian «cao» 50.2
λ = 1.0: đổi / ngày 1.21 | đoạn TV   10 giờ | % đoạn < 4 giờ 11.0 | % thời gian «cao» 50.5
λ = 2.0: đổi / ngày 0.92 | đoạn TV   14 giờ | % đoạn < 4 giờ  6.3 | % thời gian «cao» 49.5
λ = 4.0: đổi / ngày 0.36 | đoạn TV   38 giờ | % đoạn < 4 giờ  1.6 | % thời gian «cao» 45.8
```

λ là núm nhấp nháy rõ ràng nhất: từ 2,1 xuống 0,36 lần đổi / ngày, đoạn trung vị từ 5 lên 38 giờ. Không cần P&L để thấy đánh đổi.
Cũng không cần nhãn để chọn λ theo thang thời gian router cần. Nhưng muốn biết λ nào «đúng» thì vẫn cần nhãn.
</details>

**Bài 3 — HMM trên EURUSD và XAUUSD.** Fit HMM 3 trạng thái trên lợi suất H1 thô 2018–2023 của cả hai mã. Với mỗi trạng thái,
in σ, trung bình, tỷ số trung bình / σ, % thời gian và $A_{ii}$. Trạng thái có tách theo hướng không?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from hmmlearn.hmm import GaussianHMM

for ten, ds in (("XAUUSD", XAU_H1), ("EURUSD", EUR_H1)):
    df = nap_nen(ds, "2018-01-01", "2024-01-01")
    r = 100 * np.log(df["close"]).diff().dropna()
    X = r.to_numpy()[:, None]                             # lợi suất thô (%), một đặc trưng
    m = GaussianHMM(n_components=3, covariance_type="diag", n_iter=300, random_state=0).fit(X)
    tt = m.predict(X)                                     # Viterbi: chỉ để mô tả trạng thái, không dùng làm tín hiệu
    sd = np.sqrt(m.covars_.ravel())
    for k in np.argsort(sd):
        rk = r.to_numpy()[tt == k]
        print("%s  σ %.3f%%  TB %+.4f%%  TB/σ %+.3f  %%thời gian %4.1f  A_ii %.3f" % (
            ten, sd[k], rk.mean(), rk.mean() / sd[k], 100 * len(rk) / len(r), m.transmat_[k, k]))
```

```text
Kết quả khi mình chạy:
XAUUSD  σ 0.076%  TB +0.0003%  TB/σ +0.004  %thời gian 55.4  A_ii 0.860
XAUUSD  σ 0.178%  TB +0.0053%  TB/σ +0.030  %thời gian 41.2  A_ii 0.791
XAUUSD  σ 0.551%  TB -0.0317%  TB/σ -0.058  %thời gian  3.4  A_ii 0.585
EURUSD  σ 0.034%  TB +0.0009%  TB/σ +0.027  %thời gian 43.2  A_ii 0.854
EURUSD  σ 0.088%  TB -0.0009%  TB/σ -0.010  %thời gian 51.3  A_ii 0.824
EURUSD  σ 0.237%  TB -0.0030%  TB/σ -0.013  %thời gian  5.5  A_ii 0.674
```

|trung bình| / σ ≤ 0,06 ở mọi trạng thái của cả hai mã: các trạng thái khác nhau ở σ (gấp 7 lần), không ở hướng. Đây là kết
quả của Persson (2021) lặp lại trên dữ liệu của bạn. Đừng dùng t-statistic theo trạng thái Viterbi để «chứng minh» một trạng
thái có hướng: nhãn được chọn từ chính các lợi suất đó.
</details>

**Bài 4 — Cổng với nhiều cấu hình.** Làm lại phép thử trục hướng của mục 7 với ngưỡng |z| ∈ {1, 2} và chân trời 1, 4, 16 giờ,
ở M15 và H1 (12 cấu hình). p nhỏ nhất là bao nhiêu? So với ngưỡng Bonferroni.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def kalman_z(y, s_eps, s_xi, s_zeta):
    z = np.empty(len(y)); m, d = y[0], 0.0; P00, P01, P11 = 1e2, 0.0, 1e2
    for t in range(len(y)):
        if t > 0:
            m = m + d; P00, P01, P11 = P00 + 2 * P01 + P11 + s_xi ** 2, P01 + P11, P11 + s_zeta ** 2
        F = P00 + s_eps ** 2; e = y[t] - m; K0, K1 = P00 / F, P01 / F
        m, d = m + K0 * e, d + K1 * e
        P00, P01, P11 = (1 - K0) * P00, (1 - K0) * P01, P11 - K1 * P01
        z[t] = d / np.sqrt(P11)
    return z

rng = np.random.default_rng(2)
dong = []
for khung, ds, phut in (("M15", XAU_M15_DAI, 15), ("H1", XAU_H1, 60)):
    df = nap_nen(ds, "2023-01-01", "2024-09-01")
    y = 100 * np.log(df["close"].to_numpy())
    fit = df.index < "2024-01-01"
    s = np.diff(y[fit]).std()
    z = kalman_z(y, 0.2 * s, np.sqrt(s * s - 2 * (0.2 * s) ** 2), 0.03 * s)
    for nguong in (1, 2):
        huong = np.where(z > nguong, 1, np.where(z < -nguong, -1, 0))
        for gio in (1, 4, 16):
            h = gio * 60 // phut
            tl = np.r_[y[h:] - y[:-h], np.full(h, np.nan)]
            chon = ~fit; chon[-h:] = False                    # 01–08/2024, bỏ h nến cuối (chưa có tương lai)
            a, b = huong[chon], tl[chon]
            tk = lambda a, b: (a[a != 0] * b[a != 0]).mean()
            that = tk(a, b)
            null = np.array([tk(np.roll(a, k), b) for k in rng.integers(len(a) // 10, 9 * len(a) // 10, 300)])
            dong.append((khung, nguong, gio, that, (1 + (np.abs(null) >= abs(that)).sum()) / 301))
bang = pd.DataFrame(dong, columns=["khung", "ngưỡng |z|", "chân trời (giờ)", "lợi suất theo chiều z (%)", "p"])
print(bang.round(4).to_string(index=False))
print("số cấu hình: %d | p nhỏ nhất %.3f | ngưỡng Bonferroni 0,05/%d = %.4f" % (
    len(bang), bang.p.min(), len(bang), 0.05 / len(bang)))
```

```text
Kết quả khi mình chạy:
khung  ngưỡng |z|  chân trời (giờ)  lợi suất theo chiều z (%)      p
  M15           1                1                     0.0023 0.6944
  M15           1                4                     0.0230 0.2857
  M15           1               16                     0.0183 0.8472
  M15           2                1                    -0.0114 0.4618
  M15           2                4                     0.0218 0.6611
  M15           2               16                    -0.0331 0.8272
   H1           1                1                     0.0036 0.5880
   H1           1                4                     0.0137 0.5515
   H1           1               16                     0.0115 0.9003
   H1           2                1                    -0.0298 0.1761
   H1           2                4                    -0.1202 0.1229
   H1           2               16                    -0.3735 0.1096
số cấu hình: 12 | p nhỏ nhất 0.110 | ngưỡng Bonferroni 0,05/12 = 0.0042
```

Không cấu hình nào có p < 0,05, chưa nói tới ngưỡng Bonferroni 0,0042. Trục hướng Kalman không qua cổng ở cả hai khung. Nếu một
cấu hình tình cờ ra p = 0,03, nó cũng không phải bằng chứng sau 12 lần thử.
</details>

## Tự kiểm

1. `GaussianHMM.predict` là lọc hay Viterbi? Dùng làm tín hiệu được không?
   <details><summary>Đáp án</summary>

Viterbi trên cả chuỗi đưa vào. Không dùng làm tín hiệu: trạng thái ở t phụ thuộc dữ liệu sau t. Muốn nhân quả thì tự viết forward, hoặc lấy `predict_proba` trên tiền tố rồi chỉ đọc nến cuối (chậm, O(T²)).

</details>

2. Vì sao HMM trên lợi suất vàng / FX thường tách theo biến động chứ không theo hướng?
   <details><summary>Đáp án</summary>

Khác biệt lớn nhất giữa các đoạn dữ liệu là σ (co cụm biến động, mùa vụ trong ngày). Trung bình lợi suất mỗi nến rất nhỏ so với σ (≤ 6% σ ở bài 3), nên mô hình không có gì để tách theo hướng.

</details>

3. $A_{ii}$ = 0,9 trên H1. Trạng thái i kéo dài kỳ vọng bao lâu?
   <details><summary>Đáp án</summary>

1 / (1 − 0,9) = 10 nến = 10 giờ.

</details>

4. MLE của local linear trend chọn σ_ζ gần 0. Nghĩa là gì, và bạn chọn σ_ζ thế nào?
   <details><summary>Đáp án</summary>

Với dự báo một bước, «độ dốc gần như cố định» (gần bước ngẫu nhiên có drift) là tốt nhất: dữ liệu không ủng hộ một độ dốc thay đổi nhanh. σ_ζ khi đó là tham số thang thời gian, chọn theo nhu cầu (vd nhớ ~1–2 ngày) và chốt trên đoạn phát triển.

</details>

5. Tăng ngưỡng h của CUSUM thì trễ và báo động giả thay đổi thế nào?
   <details><summary>Đáp án</summary>

Trễ tăng, báo động giả giảm (ARL0 tăng). Quá cao thì bắt đầu bỏ lỡ điểm đổi (h = 32: 6 / 78).

</details>

6. Bộ A đổi 0,5 lần / ngày, bộ B đổi 2 lần / ngày. A tốt hơn chứ?
   <details><summary>Đáp án</summary>

Chưa biết. Ít đổi có thể chỉ là trễ hơn hoặc bỏ lỡ nhiều hơn (mục 6: % nến sai không giảm). Phải đo trễ và tỷ lệ bắt được so với tham chiếu, và so với baseline «không đổi».

</details>

7. Shift test giữ gì và phá gì?
   <details><summary>Đáp án</summary>

Giữ tự tương quan và tỷ lệ thời gian của chuỗi trạng thái, giữ nguyên chuỗi kết cục. Phá sự thẳng hàng theo thời gian giữa trạng thái và tương lai, đúng thứ cần kiểm.

</details>

8. Trục hướng có p = 0,31 ở M15 và 0,54 ở H1. Theo cổng của danh mục quant, bước tiếp theo là gì?
   <details><summary>Đáp án</summary>

Không dùng trục hướng này ở M15; H1 cũng không qua. Giữ trục biến động. Báo kết quả âm tính kèm lực thống kê. Thử chỉ số hướng khác (vd bằng chứng ICT G1–G2 ở plan 4a) bằng đúng phép thử này, với cấu hình chốt trước.

</details>

## Đọc thêm

- Ruey Tsay, *Analysis of Financial Time Series*: phần mô hình chuyển trạng thái (Markov switching) và mô hình không gian trạng
  thái / Kalman.
- Hyndman & Athanasopoulos, *Forecasting: Principles and Practice*: chương làm trơn mũ (Holt là họ hàng gần của local linear
  trend, mục 4).
- L. Rabiner (1989), «A tutorial on hidden Markov models…», *Proceedings of the IEEE*: thuật toán forward, Viterbi.
- J. Durbin, S. J. Koopman, *Time Series Analysis by State Space Methods*: local linear trend, Kalman, làm trơn.
- E. S. Page (1954), «Continuous inspection schemes», *Biometrika*: CUSUM gốc.
- Danh mục quant ([danh_muc_phuong_phap_quant.md](../research/danh_muc_phuong_phap_quant.md), JSON đầy đủ trong
  `../research/khao_sat/`): R1-06 (HMM lọc forward; Persson 2021), R1-25 (Kalman local linear trend), R2-01 (CUSUM), R2-02
  (Page–Hinkley), R1-17 (jump model online; Nystrup, Kolm, Lindström 2020), R2-25 (CUSUM trên |r| tần suất cao), R7-20 (shift
  test; Harris 2020), R7-46 (baseline ngây thơ).
- Tài liệu lab: [plan_bias_regime.md](../plans/plan_bias_regime.md), [nghien_cuu_bias_regime.md](../research/nghien_cuu_bias_regime.md),
  [thuat_toan_hmm_online.md](../algorithms/thuat_toan_hmm_online.md), [thuat_toan_dc_atr_structure.md](../algorithms/thuat_toan_dc_atr_structure.md).
