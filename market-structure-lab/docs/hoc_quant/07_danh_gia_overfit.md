# Module 7 — Đánh giá và overfit

> **Sau module này bạn làm được:**
> - tự viết bộ ghép một-một có dung sai thời gian, tính precision / recall / F1 và đọc đúng con số trang Đánh giá báo;
> - đặt một con số cạnh chuẩn ngẫu nhiên và baseline ngây thơ trước khi nói «tốt»;
> - mô phỏng để thấy data snooping, tính cực đại kỳ vọng của N lần thử và PBO;
> - chia dữ liệu theo thời gian (đoạn phát triển / kiểm tra, walk-forward, purge + embargo) và giải thích vì sao lab khoá
>   đoạn kiểm tra;
> - kiểm định chuỗi trạng thái bằng shift test, giữ sổ đăng ký mọi lần thử và kiểm soát FDR.
>
> **Cần trước:** module 2, 3 (module 5 cho ITH/ITL, module 6 cho chuỗi trạng thái)  ·  **Thời lượng:** ~7 giờ

> **Ba điều cần nhớ** (đọc lại khi ôn)
>
> 1. Nhãn chép từ chính thuật toán cho F1 = 1 và không nói gì. Luôn so với chuẩn ngẫu nhiên và baseline «không làm gì».
> 2. Chọn cái tốt nhất trong 200 bộ lọc ngẫu nhiên: 52,49% trong mẫu, 49,90% ngoài mẫu. PBO đo xác suất chuyện này xảy ra.
> 3. Chuỗi trạng thái phải kiểm bằng shift test (null hoán vị báo sai 83% số lần), kèm sổ đăng ký mọi lần thử và kiểm soát FDR.

## Vì sao cần

Lab chưa có thuật toán nào có F1, vì chưa có nhãn tham chiếu. Nghiên cứu order flow đã đo 7 cách đọc và không cách nào hơn
đoán ngẫu nhiên quá ±2 điểm %. Repo giao dịch cũ thì ngược lại: README ghi win rate 93–95%, profit factor 8–37, nhưng các
con số đó «gần như chắc do rò rỉ»; artifact M15 thật duy nhất cho PF ≈ 1,0 *trước phí*
([`nghien_cuu_regime_copilot_va_repo_cu.md`](../research/nghien_cuu_regime_copilot_va_repo_cu.md) §2.2). Module này trả
lời câu hỏi: **làm sao biết một thuật toán tốt thật, hay chỉ khớp với quá khứ?** Mỗi luật trong
[`AGENTS.md`](../../AGENTS.md) §6 là câu trả lời viết gọn; cuối module có bảng nối từng luật với bài học tương ứng.

## 1. Nhãn tham chiếu và vì sao phải độc lập

**Trực giác.** Chấm bài bằng đáp án do chính thí sinh viết thì ai cũng được 10 điểm. Muốn biết `ict_structure` vẽ đỉnh
có đúng không, bạn cần một bộ đỉnh/đáy *người phân tích* đánh dấu, theo quy tắc viết sẵn, không nhìn output thuật toán.

**Định nghĩa.** **Nhãn tham chiếu (reference label)** là bộ sự kiện người gán theo một quy tắc viết trước (cấp swing nào,
wick hay close, xử lý gap, hai đỉnh bằng nhau), kèm tên người gán và **khoảng gán đầy đủ (coverage)**: đoạn chart mà mọi
cấu trúc đúng quy tắc đều đã được đánh dấu. Ngoài khoảng đó, sự kiện của thuật toán không bị tính là sai. Khi so hai
định nghĩa với nhau (vd ITH của `ict_structure` với đỉnh pivot 3/3), đó là **so chéo định nghĩa (cross-definition
comparison)**: đo hai định nghĩa giống nhau đến đâu, không đo cái nào đúng.

Khối dưới tự cài phép chấm (mục 2 giải thích chi tiết) và dùng đỉnh pivot 3/3 làm «nhãn» để thấy chuyện gì xảy ra.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def so_tp(nhan, su_kien, dung_sai):
    """Ghép một-một theo vị trí nến: cặp lệch ít nhất được ghép trước; mỗi nhãn / sự kiện dùng tối đa một lần."""
    o_nen = {}
    for j, b in enumerate(su_kien):
        o_nen.setdefault(int(b), []).append(j)
    cap = sorted((abs(d), i, j) for i, l in enumerate(nhan) for d in range(-dung_sai, dung_sai + 1)
                 for j in o_nen.get(int(l) + d, []))
    da_nhan, da_sk = set(), set()
    for _, i, j in cap:
        if i not in da_nhan and j not in da_sk:
            da_nhan.add(i); da_sk.add(j)
    return len(da_nhan)

def cham(nhan, su_kien, dung_sai=1):
    tp = so_tp(nhan, su_kien, dung_sai)
    p, r = tp / len(su_kien), tp / len(nhan)
    return "TP %4d  FP %4d  FN %4d  P %.3f  R %.3f  F1 %.3f" % (
        tp, len(su_kien) - tp, len(nhan) - tp, p, r, 2 * p * r / (p + r))

ict = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
piv = chay_thuat_toan("swing_pivot", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
ith = ict.loc[ict.structure_type == "SWING_HIGH_L2", "event_bar_index"].to_numpy()   # ITH (cấp 2 trên pivot 1/1)
p33 = piv.loc[piv.structure_type == "SWING_HIGH", "event_bar_index"].to_numpy()      # đỉnh pivot 3/3
print("Số ITH: %d   số đỉnh pivot 3/3: %d" % (len(ith), len(p33)))
print("«Nhãn» chép từ chính pivot 3/3, chấm pivot 3/3 :", cham(p33, p33))
for tol in (0, 1, 3):
    print("Nhãn = pivot 3/3, sự kiện = ITH, ±%d nến   :" % tol, cham(p33, ith, tol))
print("Đổi vai: nhãn = ITH, sự kiện = pivot 3/3, ±1  :", cham(ith, p33, 1))
```

```text
Kết quả khi mình chạy:
Số ITH: 888   số đỉnh pivot 3/3: 1499
«Nhãn» chép từ chính pivot 3/3, chấm pivot 3/3 : TP 1499  FP    0  FN    0  P 1.000  R 1.000  F1 1.000
Nhãn = pivot 3/3, sự kiện = ITH, ±0 nến   : TP  874  FP   14  FN  625  P 0.984  R 0.583  F1 0.732
Nhãn = pivot 3/3, sự kiện = ITH, ±1 nến   : TP  874  FP   14  FN  625  P 0.984  R 0.583  F1 0.732
Nhãn = pivot 3/3, sự kiện = ITH, ±3 nến   : TP  881  FP    7  FN  618  P 0.992  R 0.588  F1 0.738
Đổi vai: nhãn = ITH, sự kiện = pivot 3/3, ±1  : TP  874  FP  625  FN   14  P 0.583  R 0.984  F1 0.732
```

Đọc kết quả:

- Nhãn chép từ thuật toán cho F1 = 1 tuyệt đối. Đó là lý do [`AGENTS.md`](../../AGENTS.md) §6.2 cấm «chấp nhận hàng loạt
  gợi ý auto-label rồi coi là chân lý».
- 98,4% ITH nằm *đúng* trên một đỉnh pivot 3/3: ITH (STH cao hơn nghiêm ngặt hai STH liền kề) trên dữ liệu này hầu như luôn
  cũng cao hơn 3 nến mỗi bên. Ngược lại, 42% đỉnh pivot 3/3 không phải ITH. F1 0,73 nói «hai định nghĩa trùng nhau khá nhiều»,
  không nói ITH đúng hay sai.
- Đổi vai nhãn / sự kiện thì P và R đổi chỗ, F1 giữ nguyên. Cái nào là «chuẩn» quyết định bạn đọc P hay R.

**Bẫy hay gặp.**

- Chọn định nghĩa nhãn *sau khi* xem điểm. Bài tập 1: đổi nhãn sang pivot 5/5 thì F1 của ITH lên 0,84. Chọn nhãn cho khớp
  thuật toán cũng là một cách overfit.
- Quên khai khoảng gán: mọi sự kiện ở đoạn chưa gán thành FP, precision bị kéo xuống oan.
- Gán nhãn trên chart đang bật lớp vẽ của thuật toán: mắt bạn bị dẫn, nhãn không còn độc lập.

## 2. Precision, recall, F1 có dung sai thời gian

**Trực giác.** Bạn đánh dấu đỉnh ở nến 100, thuật toán báo ở nến 101. Tính là trúng hay trượt? Cần một luật viết sẵn: lệch
tối đa bao nhiêu nến, và mỗi nhãn chỉ được «trả lời» một lần.

**Định nghĩa.** Ghép nhãn với sự kiện thành cặp. Một cặp hợp lệ khi cùng loại và lệch $|\Delta\text{nến}| \le \tau$
(**dung sai thời gian (time tolerance)**). **Ghép một-một (one-to-one matching)**: mỗi nhãn và mỗi sự kiện thuộc tối đa
một cặp, nếu không một sự kiện có thể «trúng» hai nhãn. Sau khi ghép:

- TP (true positive) = số cặp; FP = sự kiện không ghép được; FN = nhãn không ghép được.
- **Precision** $P = \frac{TP}{TP+FP}$: trong những gì thuật toán báo, bao nhiêu phần đúng.
- **Recall** $R = \frac{TP}{TP+FN}$: trong những gì có thật, thuật toán bắt được bao nhiêu phần.
- **F1** $= \frac{2PR}{P+R} = \frac{2\,TP}{2\,TP+FP+FN}$: trung bình điều hoà, thấp khi một trong hai thấp.

Hàm `so_tp` ở mục 1 ghép tham: sắp mọi cặp hợp lệ theo độ lệch rồi lấy dần. Lab có hai bộ ghép được khoá phiên bản
([`core/eval/matcher.py`](../../core/eval/matcher.py)): `greedy_label_order_v1` (duyệt nhãn theo thứ tự nến, mỗi nhãn lấy
sự kiện gần nhất còn trống) và `min_cost_v1` (luồng chi phí tối thiểu: tối đa số cặp, rồi tối thiểu tổng độ lệch). Khối
dưới chạy ví dụ tính tay của trang Đánh giá, rồi chấm lại ITH/ITL bằng chính matcher của lab.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from core.labels import ReferenceLabel
from core.eval.matcher import match_labels

# 1) Ví dụ tính tay trong trang Đánh giá: nhãn A (nến 2, giá 10), B (nến 5, giá 10); sự kiện P (nến 0, giá 12), Q (nến 4, giá 10)
nhan = [ReferenceLabel("SWING_HIGH_L2", 2, 10.0, seq=0), ReferenceLabel("SWING_HIGH_L2", 5, 10.0, seq=1)]
sk = [dict(event_id="P", structure_type="SWING_HIGH_L2", event_bar_index=0, price=12.0),
      dict(event_id="Q", structure_type="SWING_HIGH_L2", event_bar_index=4, price=10.0)]
for m in ("greedy_label_order_v1", "min_cost_v1"):
    kq = match_labels(nhan, sk, time_tolerance_bars=2, price_tolerance=5.0, matcher_version=m)
    print("%-22s" % m, [("AB"[h.label_index], h.event_id) for h in kq.matches])

# 2) Matcher của lab trên ITH/ITL so với đỉnh/đáy pivot 3/3 (protocol mặc định: ±1 nến, dung sai giá 0)
ict = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
piv = chay_thuat_toan("swing_pivot", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
doi = {"SWING_HIGH": "SWING_HIGH_L2", "SWING_LOW": "SWING_LOW_L2"}     # ánh xạ khai báo, như event_type_map
nhan = [ReferenceLabel(doi[r.structure_type], int(r.event_bar_index), float(r.price), seq=k)
        for k, r in enumerate(piv[piv.structure_type.isin(list(doi))].itertuples())]
sk = ict[ict.structure_type.isin(list(doi.values()))][["event_id", "structure_type", "event_bar_index", "price"]]
kq = match_labels(nhan, sk.to_dict("records"), time_tolerance_bars=1, price_tolerance=0.0, matcher_version="min_cost_v1")
tp = len(kq.matches); p, r = tp / len(sk), tp / len(nhan)
print("min_cost_v1, đỉnh + đáy: TP %d  FP %d  FN %d  P %.3f  R %.3f  F1 %.3f"
      % (tp, len(kq.unmatched_event_indices), len(kq.unmatched_label_indices), p, r, 2 * p * r / (p + r)))
```

```text
Kết quả khi mình chạy:
greedy_label_order_v1  [('A', 'Q')]
min_cost_v1            [('A', 'P'), ('B', 'Q')]
min_cost_v1, đỉnh + đáy: TP 1742  FP 26  FN 1230  P 0.985  R 0.586  F1 0.735
```

Bộ ghép tham theo thứ tự nhãn để A lấy Q (cùng giá, nên «gần» hơn), B mất ứng viên: 1 TP. Min-cost thấy cách ghép có 2 TP.
Khi sự kiện dày, thứ tự ghép đổi được con số.

**Lab chấm thế nào** (protocol `1.0.0`, [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1): matcher
`min_cost_v1`; dung sai ±1 nến và **dung sai giá 0** (cặp lệch 1 nến chỉ hợp lệ khi hai giá bằng nhau, nên thực tế gần như
chỉ trùng nến mới tính); chỉ đếm loại có trong `event_type_map` (HH/LH/BOS không thành swing thứ hai của cùng pivot); bỏ sự
kiện xác nhận sau nến cuối khoảng chấm; chấm theo chỉ số nến **của dataset**. Chưa có nhãn thì F1 để trống, không hiện 0.
Độ trễ (trung vị, P90 theo nearest-rank) và mật độ báo riêng, không trộn vào F1. Đổi bất kỳ quy tắc nào phải tăng phiên
bản để kết quả cũ/mới không trộn (`protocol_hash`, [`core/eval/protocol.py`](../../core/eval/protocol.py)).

**Bẫy hay gặp.**

- Nới dung sai làm F1 tăng, nhưng F1 ngẫu nhiên tăng nhanh hơn (bài tập 2: ±8 nến, F1 ngẫu nhiên 0,58).
- Một F1 gộp che chỗ lệch: báo tách đỉnh / đáy, kèm TP/FP/FN, số mẫu, độ trễ.
- Thuật toán xác nhận trễ 3 nến nhưng nhãn đặt ở nến cực trị: so `event_bar_index` (nến chứa cấu trúc), không so
  `confirmed_bar_index`. Độ trễ là thước đo thứ hai.

## 3. Chuẩn ngẫu nhiên và baseline «không làm gì»

**Trực giác.** «58% đúng» chỉ có nghĩa khi biết tung đồng xu được bao nhiêu. Với sự kiện trên chart cũng vậy: đỉnh pivot 3/3
dày (1 499 đỉnh / 15 850 nến), nên đặt bừa 888 điểm cũng trúng kha khá.

**Định nghĩa.** **Chuẩn ngẫu nhiên (random baseline, null)**: giữ nguyên nhãn, thay sự kiện bằng sự kiện đặt ngẫu nhiên
*cùng số lượng*, chấm bằng đúng matcher; lặp N lần để có phân phối. Vị trí của số thật trong phân phối cho
$p_{\ge} = \frac{1 + \#\{\text{lượt} \ge \text{thật}\}}{N+1}$. **Baseline ngây thơ (naive baseline)**: luật rẻ nhất có thể
nghĩ ra — «không làm gì», «giữ trạng thái hôm trước» (persistence), «theo giờ». **Skill** $= 1 - S/S_{\text{ref}}$ đo phần
hơn baseline (S là sai số).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def so_tp(nhan, su_kien, dung_sai=1):
    """Số cặp ghép một-một trong ± dung_sai nến (cặp lệch ít nhất được ghép trước)."""
    o_nen = {}
    for j, b in enumerate(su_kien):
        o_nen.setdefault(int(b), []).append(j)
    cap = sorted((abs(d), i, j) for i, l in enumerate(nhan) for d in range(-dung_sai, dung_sai + 1)
                 for j in o_nen.get(int(l) + d, []))
    dn, ds = set(), set()
    for _, i, j in cap:
        if i not in dn and j not in ds:
            dn.add(i); ds.add(j)
    return len(dn)

def f1(nhan, su_kien, dung_sai=1):
    return 2 * so_tp(nhan, su_kien, dung_sai) / (len(nhan) + len(su_kien))   # = 2PR/(P+R)

ict = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
piv = chay_thuat_toan("swing_pivot", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
n_nen = int(ict.confirmed_bar_index.max()) + 1
rng = np.random.default_rng(7)
q = lambda x: "TB %.3f  [P5 %.3f – P95 %.3f]" % (np.mean(x), np.percentile(x, 5), np.percentile(x, 95))
for phia, loai_ict, loai_piv in (("đỉnh", "SWING_HIGH_L2", "SWING_HIGH"), ("đáy", "SWING_LOW_L2", "SWING_LOW")):
    nhan = piv.loc[piv.structure_type == loai_piv, "event_bar_index"].to_numpy()
    that = ict.loc[ict.structure_type == loai_ict, "event_bar_index"].to_numpy()
    cap1 = ict.loc[ict.structure_type == loai_piv, "event_bar_index"].to_numpy()   # STH/STL = pivot 1/1 của ict
    null1 = [f1(nhan, rng.choice(np.arange(20, n_nen), len(that), replace=False)) for _ in range(200)]
    null2 = [f1(nhan, rng.choice(cap1, len(that), replace=False)) for _ in range(200)]
    thuc = f1(nhan, that)
    print("%s: F1 thật %.3f" % (phia, thuc))
    print("   null 1 — nến bất kỳ, cùng số lượng       :", q(null1), " lượt ≥ thật:", sum(np.array(null1) >= thuc))
    print("   null 2 — rút ngẫu nhiên trong STH/STL     :", q(null2), " lượt ≥ thật:", sum(np.array(null2) >= thuc))
```

```text
Kết quả khi mình chạy:
đỉnh: F1 thật 0.732
   null 1 — nến bất kỳ, cùng số lượng       : TB 0.199  [P5 0.184 – P95 0.215]  lượt ≥ thật: 0
   null 2 — rút ngẫu nhiên trong STH/STL     : TB 0.307  [P5 0.292 – P95 0.327]  lượt ≥ thật: 0
đáy: F1 thật 0.738
   null 1 — nến bất kỳ, cùng số lượng       : TB 0.198  [P5 0.184 – P95 0.213]  lượt ≥ thật: 0
   null 2 — rút ngẫu nhiên trong STH/STL     : TB 0.302  [P5 0.283 – P95 0.320]  lượt ≥ thật: 0
```

Mỗi null trả lời một câu hỏi khác. Null 1: «ITH có hơn đặt điểm bừa không?» (0,73 so với 0,20). Null 2: «luật chọn cấp 2
có thêm gì so với rút bừa trong các đỉnh pivot 1/1?» (0,73 so với 0,31). Lab dùng null thứ ba, `matched_hour_atr_v1`: mỗi
sự kiện thật kéo một sự kiện ngẫu nhiên **cùng giờ New York và cùng tầng ATR** (module 3), vì swing dồn vào giờ sôi động;
rải đồng đều (`uniform_v1`) làm thuật toán trông giỏi hơn thực tế
([`core/eval/null_baseline.py`](../../core/eval/null_baseline.py)).

Baseline ngây thơ quan trọng không kém. Khối dưới hỏi: «16 nến M15 tới có bung mạnh không (top 30% biên độ)?» và so ba cách
đoán, mọi ngưỡng chốt trên tháng 1–4, chấm trên tháng 5–8.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

d = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
h = 16
bien_do_toi = (d["high"].rolling(h).max().shift(-h) - d["low"].rolling(h).min().shift(-h)) / d["close"]
atr = (d["high"] - d["low"]).ewm(span=14).mean() / d["close"]          # biến động gần đây (đã biết)
gio = d.index.tz_convert("America/New_York").hour
dau = d.index < "2024-05-01"                                           # nửa đầu: chốt mọi ngưỡng ở đây
y = (bien_do_toi > bien_do_toi[dau].quantile(0.7)).astype(float).where(bien_do_toi.notna())   # «sắp bung»: top 30%
sau = (~dau) & y.notna()

ty_le_gio = y[dau].groupby(gio[dau]).mean()                            # tần suất «sắp bung» theo giờ NY, nửa đầu
du_doan = {
    "không làm gì (luôn 0)": pd.Series(0.0, index=d.index),
    "theo giờ NY":           pd.Series((ty_le_gio.reindex(gio).to_numpy() > 0.5).astype(float), index=d.index),
    "ATR cao":               (atr > atr[dau].quantile(0.7)).astype(float),
}
for ten, p in du_doan.items():
    tp = ((p == 1) & (y == 1))[sau].sum(); fp = ((p == 1) & (y == 0))[sau].sum(); fn = ((p == 0) & (y == 1))[sau].sum()
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    print("%-22s chính xác %.1f%%   F1 lớp «sắp bung» %.2f" % (ten, 100 * (p == y)[sau].mean(), f1))
```

```text
Kết quả khi mình chạy:
không làm gì (luôn 0)  chính xác 68.4%   F1 lớp «sắp bung» 0.00
theo giờ NY            chính xác 78.2%   F1 lớp «sắp bung» 0.59
ATR cao                chính xác 61.8%   F1 lớp «sắp bung» 0.42
```

«ATR cao» nghe hợp lý nhưng có độ chính xác *thấp hơn* «không làm gì» (61,8% so với 68,4%) và thua hẳn đồng hồ: chỉ cần
biết giờ New York là đoán được 78%. Phần lớn «khả năng đoán biến động» ở M15 nằm trong lịch phiên. Một bộ phân loại regime
không thắng baseline «theo giờ» thì chưa thêm gì.

**Bẫy hay gặp.**

- So với 0, hoặc với 50%, thay vì với baseline (AGENTS.md §6.3: «không so với 0»).
- Độ chính xác (accuracy) khi lớp lệch: «luôn 0» được 68% mà không làm gì. Đọc F1 của lớp cần bắt, hoặc skill.
- Ở bài toán điểm đổi, baseline «không báo điểm đổi nào» thắng nhiều thuật toán đã công bố (TCPD: F1 0,645, trên prophet,
  wbs, kcpa; mục R7-30, R7-46). Ở thang chấm của lab, detector im lặng có F1 = 0, nên lab dùng chuẩn ngẫu nhiên thay thế.

## 4. Data snooping: chọn cái tốt nhất trên nhiễu

**Trực giác.** 200 người tung đồng xu 3 000 lần. Người «giỏi nhất» được 52,5% mặt ngửa. Anh ta không giỏi; bạn chỉ chọn
người may nhất. Thử 200 cấu hình rồi báo cấu hình tốt nhất là đúng phép đó.

**Định nghĩa.** **Data snooping (thiên lệch do đào dữ liệu)**: dùng cùng một dữ liệu để vừa chọn vừa đánh giá. Khi thử N
cấu hình không có lợi thế nào, giá trị *lớn nhất* vẫn dương và tăng theo N. Với thống kê xấp xỉ chuẩn, độ lệch chuẩn
$\sigma$:

$$\mathbb{E}[\max] \approx \sigma\left[(1-\gamma)\,\Phi^{-1}\!\left(1-\tfrac{1}{N}\right) + \gamma\,\Phi^{-1}\!\left(1-\tfrac{1}{N e}\right)\right],\quad \gamma \approx 0{,}5772$$

Nói bằng lời: mức «tốt nhất do may» xấp xỉ $\sigma$ nhân một hệ số tăng chậm theo N (khoảng 2,3 khi N = 50, 2,8 khi
N = 200). $\Phi^{-1}$ là hàm ngược của phân phối chuẩn, $\gamma$ là hằng số Euler. Đây là ý của **Deflated Sharpe Ratio**
(R7-07): ngưỡng phải vượt là cực đại kỳ vọng, không phải 0.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

rng = np.random.default_rng(11)
T, N = 6000, 200                                   # 6000 nến, 200 «bộ lọc»
r = rng.standard_normal(T)                         # lợi suất nhiễu: không có gì để đoán

def bo_loc_ngau_nhien(T, do_dai_tb, rng):
    """Chuỗi +1/−1 đổi chiều ngẫu nhiên, mỗi đoạn dài trung bình do_dai_tb nến — không nhìn giá."""
    doi = rng.random(T) < 1.0 / do_dai_tb
    return np.where(np.cumsum(doi) % 2 == 0, 1, -1)

loc = np.array([bo_loc_ngau_nhien(T, rng.integers(5, 100), rng) for _ in range(N)])   # N × T
dung = (loc[:, :-1] * r[1:] > 0)                    # bộ lọc nói đúng chiều nến kế tiếp?
nua = T // 2
trong = dung[:, :nua].mean(axis=1)                  # tỷ lệ đúng nửa đầu (trong mẫu)
ngoai = dung[:, nua:].mean(axis=1)                  # nửa sau (ngoài mẫu)
k = trong.argmax()
print("Bộ lọc tốt nhất nửa đầu: #%d  đúng %.1f%%  →  nửa sau %.1f%%" % (k, 100 * trong[k], 100 * ngoai[k]))
print("Top 5 nửa đầu:", np.round(100 * np.sort(trong)[-5:], 1), " → nửa sau:", np.round(100 * ngoai[np.argsort(trong)[-5:]], 1))
print("Tương quan hạng trong/ngoài mẫu của 200 bộ lọc: %.3f" % pd.Series(trong).corr(pd.Series(ngoai), method="spearman"))

# Lặp lại cả thí nghiệm 300 lần (chuỗi nhiễu mới, 200 bộ lọc mới)
tot, sau = [], []
for _ in range(300):
    r = rng.standard_normal(T)
    loc = np.array([bo_loc_ngau_nhien(T, rng.integers(5, 100), rng) for _ in range(N)])
    dung = (loc[:, :-1] * r[1:] > 0)
    tr = dung[:, :nua].mean(axis=1); k = tr.argmax()
    tot.append(tr[k]); sau.append(dung[k, nua:].mean())
print("300 lần: tốt nhất trong mẫu TB %.2f%%  |  cùng bộ lọc ngoài mẫu TB %.2f%%  (sd %.2f%%)"
      % (100 * np.mean(tot), 100 * np.mean(sau), 100 * np.std(sau)))
from scipy.stats import norm
sd = 0.5 / np.sqrt(nua)
g = 0.5772156649
emax = 0.5 + sd * ((1 - g) * norm.ppf(1 - 1 / N) + g * norm.ppf(1 - 1 / (N * np.e)))
print("Lý thuyết: cực đại kỳ vọng của %d lần thử ≈ %.2f%%" % (N, 100 * emax))
```

```text
Kết quả khi mình chạy:
Bộ lọc tốt nhất nửa đầu: #179  đúng 52.9%  →  nửa sau 50.4%
Top 5 nửa đầu: [52.1 52.3 52.4 52.6 52.9]  → nửa sau: [50.2 51.1 51.2 49.3 50.4]
Tương quan hạng trong/ngoài mẫu của 200 bộ lọc: 0.066
300 lần: tốt nhất trong mẫu TB 52.49%  |  cùng bộ lọc ngoài mẫu TB 49.90%  (sd 0.92%)
Lý thuyết: cực đại kỳ vọng của 200 lần thử ≈ 52.52%
```

Cái tốt nhất trong mẫu đạt 52,5% (khớp công thức: 52,52%), ra ngoài mẫu rơi về 49,9%. Thứ hạng trong mẫu gần như không
nói gì về thứ hạng ngoài mẫu (tương quan 0,07). Trên XAU M15 thật, bài tập 3 cho kết quả cùng dạng.

**Bẫy hay gặp.**

- Các cấu hình tương quan (lookback 20 và 21 gần như một) nên «số lần thử hiệu dụng» nhỏ hơn N, nhưng không bao giờ là 1.
- Lần thử ẩn: cấu hình bạn đọc trên mạng, thử trong đầu khi nhìn chart, thử năm ngoái rồi bỏ. Tất cả cộng vào N.
- «Chỉnh tới khi chạy được» trên cùng dữ liệu là snooping kể cả khi mỗi lần chỉnh đều có lý do nghe hợp lý.

## 5. Ý tưởng PBO: xác suất backtest bị overfit

**Trực giác.** Nếu nhà vô địch vòng tập luyện thường chỉ xếp giữa bảng ở vòng thi thật, quy trình chọn vô địch là ăn may.

**Định nghĩa** (Bailey, Borwein, López de Prado, Zhu; mục R7-06). Có ma trận $T \times N$: điểm theo từng nến của N cấu
hình. Chia T thành S khối liền. Với mỗi cách lấy S/2 khối làm **trong mẫu (in-sample, IS)** và phần còn lại làm **ngoài
mẫu (out-of-sample, OOS)** — có $\binom{S}{S/2}$ cách — tìm cấu hình tốt nhất IS, ghi hạng tương đối OOS của nó
$\omega \in (0,1)$, đặt $\lambda = \ln\frac{\omega}{1-\omega}$. **PBO** $= P(\lambda \le 0)$: tỷ lệ lần cấu hình thắng IS
rơi xuống nửa dưới OOS. Không có lợi thế thật: PBO quanh 0,5 hoặc hơn. Quy trình chọn tốt: PBO gần 0.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from itertools import combinations

def pbo(diem, S=10):
    """diem: ma trận T × N (điểm theo nến của N cấu hình). Chia T thành S khối; xét mọi cách lấy S/2 khối làm
    trong mẫu (IS), phần còn lại ngoài mẫu (OOS). PBO = tỷ lệ lần cấu hình tốt nhất IS rơi xuống nửa dưới OOS."""
    T, N = diem.shape
    khoi = np.array_split(np.arange(T), S)
    tb_khoi = np.array([diem[k].mean(axis=0) for k in khoi])           # S × N
    lambdas = []
    for is_ in combinations(range(S), S // 2):
        oos = [s for s in range(S) if s not in is_]
        is_tb, oos_tb = tb_khoi[list(is_)].mean(axis=0), tb_khoi[oos].mean(axis=0)
        best = is_tb.argmax()
        w = (oos_tb < oos_tb[best]).sum() + 1                             # hạng OOS của nó (1 = tệ nhất)
        w = w / (N + 1)
        lambdas.append(np.log(w / (1 - w)))
    lambdas = np.array(lambdas)
    return (lambdas <= 0).mean(), len(lambdas)

def bo_loc_ngau_nhien(T, do_dai_tb, rng):
    doi = rng.random(T) < 1.0 / do_dai_tb
    return np.where(np.cumsum(doi) % 2 == 0, 1, -1)

rng = np.random.default_rng(5)
T, N = 6000, 200
loc = np.array([bo_loc_ngau_nhien(T, rng.integers(5, 100), rng) for _ in range(N)])
for ten, canh in (("nhiễu thuần", 0.0), ("#0 có lợi thế rất nhỏ", 0.03), ("#0 có lợi thế nhỏ", 0.08)):
    r = rng.standard_normal(T)
    r[1:] += canh * loc[0, :-1]                     # chỉ bộ lọc #0 thật sự biết chút ít về nến sau
    diem = (loc[:, :-1] * r[1:] > 0).T.astype(float)   # T-1 × N
    p, n = pbo(diem)
    print("%-26s PBO = %.2f  (%d cách chia)   bộ lọc #0 đúng %.1f%%" % (ten, p, n, 100 * diem[:, 0].mean()))
```

```text
Kết quả khi mình chạy:
nhiễu thuần                PBO = 0.68  (252 cách chia)   bộ lọc #0 đúng 50.2%
#0 có lợi thế rất nhỏ      PBO = 0.63  (252 cách chia)   bộ lọc #0 đúng 51.3%
#0 có lợi thế nhỏ          PBO = 0.01  (252 cách chia)   bộ lọc #0 đúng 53.6%
```

Lợi thế 51,3% có thật nhưng chìm giữa 199 bộ lọc may mắn: PBO không phân biệt được. Lợi thế 53,6% thì nổi rõ. Với N lớn,
lợi thế phải lớn so với nhiễu thì mới «sống sót» qua phép chọn — một lý do nữa để thử ít cấu hình, có lý do từ trước.

**Bẫy hay gặp.**

- N phải là *mọi* cấu hình đã thử; giấu bớt làm PBO thấp giả (vì vậy cần sổ đăng ký, mục 9).
- Thước đo phải tính được trên từng khối: F1 cần đủ nhãn trong mỗi khối, nên với bộ nhãn 4 tuần của lab, PBO trên F1 chưa
  làm được.
- PBO đo *quy trình chọn*, không nói cấu hình thắng có lời hay không.

## 6. Đoạn phát triển / kiểm tra và walk-forward

**Trực giác.** Đề thi thử để luyện, đề thi thật để biết trình độ. Đã xem đề thi thật mà còn luyện tiếp theo nó thì điểm thi
thật hết nghĩa.

**Định nghĩa.** **Đoạn phát triển (development segment)**: phần dữ liệu để nhìn, chọn tham số, sửa định nghĩa.
**Đoạn kiểm tra (test segment)**: phần để dành, chỉ mở một lần cho cấu hình đã chốt. Chia **theo thời gian**, đoạn kiểm tra
nằm sau, khai *trước khi* xem kết quả. Ở lab, đoạn kiểm tra bắt đầu 01/09/2024: `hoc.py` từ chối mọi khoảng chạm vào nó;
trang Đánh giá khoá chấm đoạn `test` cho tới khi bật `test_unlocked`, và ghi `[ĐÃ MỞ ĐOẠN KIỂM TRA]` vào ghi chú
([`core/eval/segments.py`](../../core/eval/segments.py)). **Walk-forward (kiểm tra cuốn chiếu)**: lặp «chọn trên quá khứ,
đo trên đoạn kế tiếp» theo thời gian; **cửa sổ mở rộng (anchored)** giữ gốc cố định, **cửa sổ trượt (rolling)** dời cả gốc.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

try:
    nap_nen(XAU_D1, "2018-01-01", "2024-12-31")
except ValueError as loi:
    print("Bị chặn:", loi)

CAC_K = [5, 10, 20, 40, 60, 120, 250]          # lookback (số nến D1) cần chọn
for ten, ds in (("XAU", XAU_D1), ("EUR", EUR_D1)):
    d = nap_nen(ds, "2018-01-01", "2024-09-01")
    c = d["close"]
    sau = np.sign(c.shift(-1) - c)               # chiều của nến KẾ TIẾP (chỉ dùng để chấm)
    dung = pd.DataFrame({k: (np.sign(c - c.shift(k)) == sau).where(c.shift(k).notna() & sau.notna())
                         for k in CAC_K})           # 1 = đoán đúng chiều, NaN = chưa đủ dữ liệu
    luon_tang = (sau == 1).where(sau.notna())    # baseline: lúc nào cũng đoán «tăng»
    nam = d.index.year
    print("\n%s — walk-forward cửa sổ mở rộng: chọn k trên mọi năm trước, chấm trên năm sau" % ten)
    print(" năm KT | k chọn | đúng trong mẫu | đúng năm KT | «luôn tăng» năm KT | số nến")
    for y in range(2020, 2025):
        tr = dung[nam < y].mean()
        k = tr.idxmax()
        te = dung.loc[nam == y, k]
        print("  %d  |  %3d   |     %.1f%%      |    %.1f%%    |       %.1f%%        | %d"
              % (y, k, 100 * tr[k], 100 * te.mean(), 100 * luon_tang[nam == y].mean(), te.notna().sum()))
```

```text
Kết quả khi mình chạy:
Bị chặn: Khoảng 2018-01-01 → 2024-12-31 chạm đoạn kiểm tra (từ 2024-09-01). Bài tập chỉ dùng đoạn phát triển; đổi «den» thành «2024-09-01» hoặc sớm hơn.

XAU — walk-forward cửa sổ mở rộng: chọn k trên mọi năm trước, chấm trên năm sau
 năm KT | k chọn | đúng trong mẫu | đúng năm KT | «luôn tăng» năm KT | số nến
  2020  |  120   |     55.1%      |    58.7%    |       59.5%        | 259
  2021  |  120   |     56.5%      |    46.5%    |       50.8%        | 258
  2022  |  120   |     53.7%      |    52.7%    |       51.2%        | 258
  2023  |  120   |     53.5%      |    51.0%    |       49.4%        | 257
  2024  |  120   |     53.0%      |    55.2%    |       55.2%        | 172

EUR — walk-forward cửa sổ mở rộng: chọn k trên mọi năm trước, chấm trên năm sau
 năm KT | k chọn | đúng trong mẫu | đúng năm KT | «luôn tăng» năm KT | số nến
  2020  |  250   |     51.9%      |    51.0%    |       52.1%        | 261
  2021  |  250   |     51.4%      |    48.8%    |       47.7%        | 260
  2022  |  120   |     50.9%      |    50.8%    |       49.2%        | 260
  2023  |  120   |     50.9%      |    50.8%    |       50.0%        | 260
  2024  |  120   |     50.9%      |    45.7%    |       52.0%        | 173
```

Ba điều: (1) số «đúng trong mẫu» luôn cao hơn số năm kiểm tra — đó là thiên lệch chọn của mục 4, lặp mỗi năm; (2) với XAU,
k = 120 gần như chỉ là «vàng đang tăng»: baseline «luôn tăng» cho số gần bằng; (3) một năm D1 chỉ có ~258 nến, sai số chuẩn
của một tỷ lệ quanh 50% là $\sqrt{0{,}25/258} \approx 3{,}1$ điểm %, nên 46,5% hay 58,7% đều nằm trong nhiễu.

**Bẫy hay gặp.**

- Chia ngẫu nhiên (random split) cho chuỗi thời gian — lỗi của repo cũ: nến hôm nay ở train, nến hôm qua ở test (mục 7).
- Mỗi lần chọn lại tham số trong walk-forward là một lần thử; báo kết quả của *quy trình*, không chỉ năm đẹp nhất.
- Mở đoạn kiểm tra, thấy kém, chỉnh rồi chấm lại: đoạn đó hết là kiểm tra độc lập (AGENTS.md §6.3). Ghi nhận kết quả kém,
  sửa trên đoạn phát triển, chờ dữ liệu mới (forward) để kiểm tra phiên bản sau.
- Chuẩn hoá hay lấy phân vị trên *cả* dữ liệu (kể cả đoạn kiểm tra) là rò rỉ: ngưỡng phải tính trên đoạn phát triển.

## 7. Rò rỉ do nhãn chồng nhau: purge và embargo

**Trực giác.** Nhãn «16 nến tới tăng hay giảm» của nến 100 và nến 101 dùng chung 15 nến tương lai. Nếu nến 100 ở tập kiểm
tra còn nến 101 ở tập huấn luyện, mô hình «chép bài» từ hàng xóm.

**Định nghĩa.** Mỗi mẫu t có **cửa sổ nhãn** $[t, t+h]$. **Rò rỉ (leakage)**: thông tin của tập kiểm tra lọt vào tập huấn
luyện. **Purge (tẩy)**: bỏ khỏi tập huấn luyện mọi mẫu có cửa sổ nhãn chạm cửa sổ nhãn của tập kiểm tra. **Embargo (cấm
vận)**: bỏ thêm e mẫu ngay sau tập kiểm tra, vì đặc trưng có tự tương quan (López de Prado; mục R7-01).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from sklearn.neighbors import KNeighborsClassifier

h, K, T = 32, 50, 6000                     # tầm nhãn 32 nến, chia 50 phần
kq = {"xáo ngẫu nhiên rồi chia (sai)": [], "khối thời gian liền": [], "khối liền + purge 32 + embargo 64": []}
for seed in range(10):                     # 10 chuỗi bước ngẫu nhiên: tương lai KHÔNG đoán được
    rng = np.random.default_rng(seed)
    gia = np.cumsum(rng.standard_normal(T + h))
    X = np.column_stack([gia[64:T], gia[64:T] - gia[:T - 64]])   # đặc trưng: mức giá, lợi suất 64 nến qua
    y = (gia[64 + h:T + h] > gia[64:T]).astype(int)              # nhãn: 32 nến tới tăng? — cửa sổ nhãn chồng nhau
    i = np.arange(len(y))
    def cv(chia):
        return np.mean([(KNeighborsClassifier(5).fit(X[tr], y[tr]).predict(X[te]) == y[te]).mean() for te, tr in chia])
    xao = rng.permutation(i)
    kq["xáo ngẫu nhiên rồi chia (sai)"].append(cv([(te, np.setdiff1d(xao, te)) for te in np.array_split(xao, K)]))
    khoi = np.array_split(i, K)
    kq["khối thời gian liền"].append(cv([(te, np.setdiff1d(i, te)) for te in khoi]))
    # purge: bỏ mẫu train có cửa sổ nhãn [t, t+h] chạm khoảng test; embargo: bỏ thêm 64 mẫu sau khoảng test
    kq["khối liền + purge 32 + embargo 64"].append(cv([(te, i[~((i >= te[0] - h) & (i <= te[-1] + 64))]) for te in khoi]))
for ten, v in kq.items():
    print("%-36s độ chính xác TB %.1f%%  (10 chuỗi: %.0f–%.0f%%)" % (ten, 100 * np.mean(v), 100 * min(v), 100 * max(v)))
```

```text
Kết quả khi mình chạy:
xáo ngẫu nhiên rồi chia (sai)        độ chính xác TB 69.9%  (10 chuỗi: 67–75%)
khối thời gian liền                  độ chính xác TB 52.6%  (10 chuỗi: 46–57%)
khối liền + purge 32 + embargo 64    độ chính xác TB 50.8%  (10 chuỗi: 46–56%)
```

Trên bước ngẫu nhiên, không gì đoán được tương lai, vậy mà chia xáo trộn cho 70%: mô hình tìm hàng xóm cùng mức giá — chính
là nến liền trước, có nhãn gần như trùng. Chia theo khối liền còn 52,6% (rò ở biên 50 khối); purge + embargo đưa về
50,8%. Cũng để ý khoảng 46–56% giữa 10 chuỗi: nhãn chồng nhau làm **cỡ mẫu hiệu dụng** nhỏ hơn số nến nhiều (gần 6 000 mẫu,
tầm 32 → chỉ khoảng 185 cửa sổ không chồng).

**Bẫy hay gặp.**

- Embargo ngắn hơn tầm nhãn, hoặc ngắn hơn thời gian khởi động của đặc trưng khung lớn (H4, D1), vẫn rò.
- Ở lab: một sự kiện của đoạn phát triển xác nhận trong đoạn kiểm tra *không* được tính cho đoạn phát triển (quy tắc bỏ đuôi
  chưa xác nhận tính theo từng đoạn) — cùng tinh thần purge.
- Kết cục tương lai (MFE/MAE, «đạt DOL», biên độ tới) chỉ được làm nhãn đánh giá, không bao giờ là đầu vào (AGENTS.md §2.1).

## 8. Shift test cho chuỗi trạng thái

**Trực giác.** Hai chuỗi «dai» (trạng thái kéo dài hàng trăm nến, biến động đi theo cụm) rất dễ trùng nhau do tình cờ. Xáo
trộn từng nến phá vỡ độ dai đó, nên null hoán vị quá dễ thắng: thứ gì dai cũng «có ý nghĩa».

**Định nghĩa** (Harris 2020; mục R7-20). Thống kê T đo liên hệ giữa chuỗi trạng thái $s_t$ và kết cục tương lai $y_t$ (vd
chênh kết cục trung bình giữa hai trạng thái). **Shift test (kiểm định dịch vòng)**: dịch vòng $s$ đi k nến (nối đuôi vào
đầu), với $|k|$ đủ lớn để bỏ phần trùng do tự tương quan, tính lại T. Dịch giữ nguyên độ dài đoạn của $s$ và cấu trúc của
$y$, chỉ cắt đứt *thời điểm* trùng nhau. $p = \frac{1 + \#\{|T_k| \ge |T|\}}{B+1}$ với B lần dịch.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

d = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
lr = np.log(d["close"]).diff()
h = 16
ket_cuc = lr.abs().rolling(h).sum().shift(-h).to_numpy()      # |biến động| 16 nến TỚI (kết cục tương lai)
ok = ~np.isnan(ket_cuc); y = ket_cuc[ok]; n = len(y)

def thong_ke(s):                                              # chênh kết cục TB giữa trạng thái 1 và 0
    return y[s == 1].mean() - y[s == 0].mean()

def p_hoan_vi(s, rng, B=199):                                 # null iid: xáo trạng thái
    t = abs(thong_ke(s)); return (1 + sum(abs(thong_ke(rng.permutation(s))) >= t for _ in range(B))) / (B + 1)

def p_dich_vong(s, rng, B=199, min_dich=500):                 # null dịch vòng: giữ nguyên độ dài đoạn
    t = abs(thong_ke(s)); dich = rng.integers(min_dich, n - min_dich, B)
    return (1 + sum(abs(thong_ke(np.roll(s, k))) >= t for k in dich)) / (B + 1)

def trang_thai_gia(n, do_dai_tb, rng):                        # chuỗi 0/1 bền, KHÔNG liên quan gì tới giá
    return (np.cumsum(rng.random(n) < 1 / do_dai_tb) % 2).astype(int)

rng = np.random.default_rng(2)
p_hv, p_dv = [], []
for _ in range(100):
    s = trang_thai_gia(n, 200, rng)
    p_hv.append(p_hoan_vi(s, rng)); p_dv.append(p_dich_vong(s, rng))
print("100 chuỗi trạng thái GIẢ (độc lập với giá), tỷ lệ p < 0.05:")
print("   null hoán vị iid : %.0f%%" % (100 * np.mean(np.array(p_hv) < 0.05)))
print("   null dịch vòng   : %.0f%%   (đúng ra phải ≈ 5%%)" % (100 * np.mean(np.array(p_dv) < 0.05)))

# Hai trạng thái THẬT, tính nhân quả (chỉ dùng nến đã đóng)
bd = lr.abs().ewm(span=4).mean()
s_bd = (bd > bd.rolling(500).median()).astype(int).to_numpy()[ok]       # «biến động cao»
s_mom = (np.log(d["close"]).diff(64) > 0).astype(int).to_numpy()[ok]                        # «trend tăng 64 nến»
print("Biến động cao → |biến động| tới: chênh %.5f, p dịch vòng %.3f" % (thong_ke(s_bd), p_dich_vong(s_bd, rng)))
y = lr.rolling(h).sum().shift(-h).to_numpy()[ok]               # đổi kết cục: lợi suất CÓ DẤU 16 nến tới
print("Trend tăng 64 nến → lợi suất tới: chênh %.5f, p dịch vòng %.3f" % (thong_ke(s_mom), p_dich_vong(s_mom, rng)))
```

```text
Kết quả khi mình chạy:
100 chuỗi trạng thái GIẢ (độc lập với giá), tỷ lệ p < 0.05:
   null hoán vị iid : 83%
   null dịch vòng   : 8%   (đúng ra phải ≈ 5%)
Biến động cao → |biến động| tới: chênh 0.00209, p dịch vòng 0.005
Trend tăng 64 nến → lợi suất tới: chênh 0.00003, p dịch vòng 0.865
```

Với chuỗi trạng thái *bịa* hoàn toàn, null hoán vị báo «có ý nghĩa» 83 lần trên 100. Null dịch vòng báo 8 lần — gần mức 5%
danh nghĩa (100 lần thử thì sai số khoảng ±2 điểm %, và biến động XAU không dừng hẳn). Trên trạng thái thật: «biến động
cao» báo trước biến động tới (p = 0,005, đúng điều module 4 dạy: biến động đoán được); «trend tăng 64 nến» không nói gì về
chiều 16 nến tới (p = 0,865).

**Bẫy hay gặp.**

- Dịch nhỏ hơn độ dai của chuỗi thì bản dịch vẫn gần trùng bản gốc; phải bỏ các độ dịch nhỏ (`min_dich`).
- Mùa vụ trong ngày và các đợt biến động kéo dài cả tháng làm null rộng ra, lực kiểm định giảm. Thử đổi `span=4` thành
  `span=32` ở khối trên: trạng thái mượt hơn, đoạn dài hơn, p của «biến động cao» lên 0,29 (lúc mình chạy). Khử mùa vụ
  trước (module 4) rồi mới kiểm.
- Đây là null lab đang thiếu cho chuỗi trạng thái; plan regime dùng nó cho thước đo «độ tách kết cục tương lai»
  ([`plan_bias_regime.md`](../plans/plan_bias_regime.md), M5–M6).

## 9. Sổ đăng ký mọi lần thử và kiểm soát FDR

**Trực giác.** Nhà khoa học giữ nhật ký thí nghiệm, kể cả lần hỏng. Không có nhật ký, không ai biết «phát hiện» là 1 trên 1
hay 1 trên 200 lần thử.

**Định nghĩa.** **Sổ đăng ký lần thử (trial registry)**: mỗi cấu hình / kiểm định đã chạy một dòng (ngày, dữ liệu, tham số,
thước đo, kết quả), *kể cả thất bại*. **Đăng ký trước (pre-registration)**: viết sẵn thước đo, null, ngưỡng, họ kiểm định
trước khi mở đoạn kiểm tra (R7-05). Khi chạy m kiểm định cùng lúc, **kiểm soát FDR (false discovery rate)** bằng
Benjamini–Hochberg (module 2; R7-14): sắp p tăng dần, giữ k kiểm định đầu với k lớn nhất thoả $p_{(k)} \le q\,k/m$.
Bằng lời: ngưỡng nới dần theo thứ hạng, và **m là số lần thử thật trong sổ**.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy import stats

so_dang_ky = []                                     # sổ đăng ký: MỌI lần thử, kể cả lần «thất bại»
for ten, ds in (("XAU", XAU_M15_DAI), ("EUR", EUR_M15_DAI)):
    d = nap_nen(ds, "2018-01-01", "2024-09-01")
    lr = np.log(d["close"]).diff().dropna()
    gio = lr.index.tz_convert("America/New_York").hour
    for g in range(24):
        x = lr[gio == g]
        t, p = stats.ttest_1samp(x, 0.0)
        so_dang_ky.append(dict(ma=ten, gio_ny=g, n=len(x), tb_bp=1e4 * x.mean(), t=t, p=p))
reg = pd.DataFrame(so_dang_ky)

def bh(p, q=0.10):
    """Benjamini–Hochberg: trả mảng True/False «phát hiện» với tỷ lệ phát hiện sai kỳ vọng ≤ q."""
    p = np.asarray(p); m = len(p); thu_tu = np.argsort(p)
    dat = p[thu_tu] <= q * np.arange(1, m + 1) / m
    k = dat.nonzero()[0].max() + 1 if dat.any() else 0
    kq = np.zeros(m, bool); kq[thu_tu[:k]] = True
    return kq

reg["bh_48"] = bh(reg.p)
print("Số lần thử: %d. p < 0.05: %d (kỳ vọng do may ≈ %.1f). Qua BH q=0.10: %d"
      % (len(reg), (reg.p < 0.05).sum(), 0.05 * len(reg), reg.bh_48.sum()))
print(reg[reg.bh_48].sort_values("p").round({"tb_bp": 2, "t": 1, "p": 4}).to_string(index=False))
chon = (reg.ma == "EUR") & reg.gio_ny.isin([2, 4, 6])           # ba giờ cùng dấu âm, buổi sáng giờ London
print("Chỉ khai 3 giờ EUR 2, 4, 6 NY (m = 3): BH giữ %d/3.  Trong sổ đủ 48 lần thử: giữ %d/3."
      % (bh(reg.p[chon]).sum(), reg.bh_48[chon].sum()))
```

```text
Kết quả khi mình chạy:
Số lần thử: 48. p < 0.05: 12 (kỳ vọng do may ≈ 2.4). Qua BH q=0.10: 10
 ma  gio_ny    n  tb_bp     t      p  bh_48
EUR      16 6872  -0.33 -10.7 0.0000   True
EUR      18 6931   0.30   9.1 0.0000   True
XAU      17  127  -0.80  -6.6 0.0000   True
XAU      18 6818   0.80   5.8 0.0000   True
EUR      17 6882   0.19   4.9 0.0000   True
EUR       7 6920  -0.27  -4.3 0.0000   True
XAU      19 6868   0.23   3.2 0.0016   True
XAU      16 6634  -0.18  -2.8 0.0052   True
EUR       3 6920   0.22   2.8 0.0052   True
EUR       2 6936  -0.14  -2.4 0.0157   True
Chỉ khai 3 giờ EUR 2, 4, 6 NY (m = 3): BH giữ 3/3.  Trong sổ đủ 48 lần thử: giữ 1/3.
```

Đọc kỹ:

- Ba giờ «đẹp» cùng dấu, nếu chỉ khai ba giờ đó thì cả ba qua BH; đặt vào sổ đủ 48 lần thử thì còn một. Giấu lần thử làm
  «phát hiện» nhiều lên mà không ai thấy.
- 7 trong 8 phát hiện mạnh nhất nằm ở 16–19 giờ New York: giờ rollover, spread giãn. Dữ liệu là giá **Bid** (module 1): spread
  giãn kéo Bid xuống rồi hồi lên. Hiệu ứng có thật *trong dữ liệu*, nhưng là dấu vết của cách báo giá, không giao dịch được.
  XAU giờ 17 chỉ có 127 nến (giờ nghỉ phiên): mẫu nhỏ, dữ liệu bất thường.
- Cỡ hiệu ứng 0,1–0,8 bp mỗi nến M15, nhỏ hơn chi phí một vòng giao dịch (module 8). «Có ý nghĩa thống kê» khác «đáng
  giao dịch».

**Bẫy hay gặp.**

- Sổ chỉ ghi lần thành công. Sổ thiếu thì PBO, FDR, cực đại kỳ vọng đều đánh giá thấp mức overfit.
- Họ kiểm định khai sau khi xem p. Phải khai trước (giờ nào, mã nào, thước đo nào).
- p-value đầu vào sai vì bỏ qua phụ thuộc chuỗi: dùng bootstrap khối, shift test (mục 8) cho dữ liệu có tự tương quan.

## Nối luật AGENTS.md §6 với bài học

| Luật trong [`AGENTS.md`](../../AGENTS.md) | Vì sao (bài học) |
|---|---|
| §6.1 Không trộn «kiểm tra bản cài đặt» với «chất lượng nhận diện» | Mục 1: so chéo hai định nghĩa đo độ giống, không đo độ đúng |
| §6.2 Nhãn theo quy tắc viết sẵn, độc lập với output; không nhận hàng loạt auto-label | Mục 1: nhãn chép từ thuật toán cho F1 = 1 |
| §6.2 Khai khoảng gán đầy đủ; ngoài khoảng không tính FP | Mục 1–2: thiếu coverage thì precision bị kéo xuống oan |
| §6.2 So khác định nghĩa phải khai `event_type_map`, ghi «so chéo định nghĩa» | Mục 2: matcher chỉ ghép cùng loại sau ánh xạ khai báo |
| §6.3 Cố định dữ liệu, đoạn phát triển / kiểm tra theo thời gian **trước khi** xem kết quả | Mục 6: đoạn kiểm tra khoá; mục 9: đăng ký trước |
| §6.3 Chọn tham số trên đoạn phát triển; mở rộng lưới sau khi xem đoạn kiểm tra thì hết độc lập | Mục 4–6: cái tốt nhất do chọn sụp ngoài mẫu |
| §6.3 Luôn có baseline và chuẩn ngẫu nhiên có cấu trúc tương đương, không so với 0 | Mục 3: null 1 / null 2 / theo giờ cho ba câu trả lời khác nhau |
| §6.3 Báo số mẫu, độ trễ (trung vị, P90), mật độ; nói rõ khi chưa có nhãn | Mục 2, 7: một F1 gộp che chỗ lệch; cỡ mẫu hiệu dụng nhỏ hơn số nến |
| §6.3 Đọc F1 cạnh F1 ngẫu nhiên | Mục 3 và bài tập 2: F1 ngẫu nhiên đổi theo mật độ và dung sai |
| §6.3 Thí nghiệm tái lập bằng script, run gắn nhãn | Mục 9: sổ đăng ký là điều kiện để FDR, PBO có nghĩa |
| §2.1 Kết cục tương lai chỉ là nhãn đánh giá | Mục 7–8: kết cục tới dùng để chấm; lọt vào đặc trưng là rò rỉ |
| §2.4 Không kết luận «tốt hơn» khi chưa có nhãn và chuẩn so sánh | Mục 3–5 |

## Lab đang dùng những điều này ở đâu

| Khái niệm | File / tài liệu | Ghi chú |
|---|---|---|
| Nhãn tham chiếu, coverage, auto-label có người duyệt | [`../guides/nhan_tham_chieu.md`](../guides/nhan_tham_chieu.md) | Trang Gán nhãn; bộ nhãn D8: 2 tuần dev + 2 tuần test |
| Protocol chấm, `protocol_hash` | [`../../core/eval/protocol.py`](../../core/eval/protocol.py), [`../guides/danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1 | ±1 nến, dung sai giá 0, `event_type_map` |
| Ghép một-một | [`../../core/eval/matcher.py`](../../core/eval/matcher.py) | `greedy_label_order_v1`, `min_cost_v1` |
| Chấm, theo đoạn, bỏ đuôi chưa xác nhận | [`../../core/eval/evaluate.py`](../../core/eval/evaluate.py), [`../../core/eval/metrics.py`](../../core/eval/metrics.py) | F1 trống khi chưa có nhãn; P90 nearest-rank |
| Chuẩn ngẫu nhiên | [`../../core/eval/null_baseline.py`](../../core/eval/null_baseline.py) | `matched_hour_atr_v1` (nên đọc), `uniform_v1` |
| Đoạn phát triển / kiểm tra | [`../../core/eval/segments.py`](../../core/eval/segments.py), [`../../research/hoc_quant/hoc.py`](../../research/hoc_quant/hoc.py) | Kiểm tra từ 01/09/2024, khoá tới khi mở |
| Shift test, PBO, Reality Check, purge cho regime | [`../research/nghien_cuu_bias_regime.md`](../research/nghien_cuu_bias_regime.md), [`../plans/plan_bias_regime.md`](../plans/plan_bias_regime.md) | Kế hoạch thước đo M5, M6, M13 |
| Lỗi đánh giá của repo cũ | [`../research/nghien_cuu_regime_copilot_va_repo_cu.md`](../research/nghien_cuu_regime_copilot_va_repo_cu.md) §2.2 | Random split, chọn cấu hình trên test, chuẩn hoá toàn dữ liệu |
| Danh mục phương pháp đánh giá | [`../research/danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md) nhóm R7 | 46 mục, «thử sớm» 23 |

## Bài tập

**Bài 1 — Nhãn khác, F1 khác.** Dùng đỉnh pivot 3/3, 5/5, 8/8 làm «nhãn» (tham số `{"left": n, "right": n}` của
`swing_pivot`), chấm ITH với dung sai ±1. Định nghĩa nhãn nào cho F1 cao nhất? Điều đó nói gì về việc chọn nhãn sau khi xem
điểm? *Gợi ý:* dùng lại `so_tp` ở mục 1.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def so_tp(nhan, su_kien, dung_sai):
    o_nen = {}
    for j, b in enumerate(su_kien):
        o_nen.setdefault(int(b), []).append(j)
    cap = sorted((abs(d), i, j) for i, l in enumerate(nhan) for d in range(-dung_sai, dung_sai + 1)
                 for j in o_nen.get(int(l) + d, []))
    dn, ds = set(), set()
    for _, i, j in cap:
        if i not in dn and j not in ds:
            dn.add(i); ds.add(j)
    return len(dn)

ict = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
ith = ict.loc[ict.structure_type == "SWING_HIGH_L2", "event_bar_index"].to_numpy()
for lr in (3, 5, 8):
    piv = chay_thuat_toan("swing_pivot", XAU_M15, "2024-01-01", "2024-09-01", tham_so={"left": lr, "right": lr})["su_kien"]
    nhan = piv.loc[piv.structure_type == "SWING_HIGH", "event_bar_index"].to_numpy()
    tp = so_tp(nhan, ith, 1); p, r = tp / len(ith), tp / len(nhan)
    print("nhãn = pivot %d/%d (%4d đỉnh): P %.3f  R %.3f  F1 %.3f" % (lr, lr, len(nhan), p, r, 2 * p * r / (p + r)))
```

```text
Kết quả khi mình chạy:
nhãn = pivot 3/3 (1499 đỉnh): P 0.984  R 0.583  F1 0.732
nhãn = pivot 5/5 ( 955 đỉnh): P 0.873  R 0.812  F1 0.841
nhãn = pivot 8/8 ( 622 đỉnh): P 0.645  R 0.921  F1 0.759
```

Pivot 5/5 có mật độ gần ITH nhất nên F1 cao nhất. Nếu bạn chọn «nhãn» sau khi thấy bảng này, 0,84 là con số của phép chọn,
không phải chất lượng của ITH. Nhãn người gán phải viết quy tắc trước.
</details>

**Bài 2 — Dung sai và chuẩn ngẫu nhiên.** Lấy nhãn pivot 5/5, chấm ITH với dung sai 0, 1, 2, 4, 8 nến; mỗi mức tính thêm F1
trung bình của 100 lượt sự kiện ngẫu nhiên cùng số lượng. Khi dung sai tăng, F1 thật và khoảng cách «thật − ngẫu nhiên»
thay đổi thế nào?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def f1(nhan, su_kien, dung_sai):
    o_nen = {}
    for j, b in enumerate(su_kien):
        o_nen.setdefault(int(b), []).append(j)
    cap = sorted((abs(d), i, j) for i, l in enumerate(nhan) for d in range(-dung_sai, dung_sai + 1)
                 for j in o_nen.get(int(l) + d, []))
    dn, ds = set(), set()
    for _, i, j in cap:
        if i not in dn and j not in ds:
            dn.add(i); ds.add(j)
    return 2 * len(dn) / (len(nhan) + len(su_kien))

ict = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
piv = chay_thuat_toan("swing_pivot", XAU_M15, "2024-01-01", "2024-09-01", tham_so={"left": 5, "right": 5})["su_kien"]
nhan = piv.loc[piv.structure_type == "SWING_HIGH", "event_bar_index"].to_numpy()
ith = ict.loc[ict.structure_type == "SWING_HIGH_L2", "event_bar_index"].to_numpy()
n_nen = int(ict.confirmed_bar_index.max()) + 1
rng = np.random.default_rng(1)
print("dung sai | F1 thật | F1 ngẫu nhiên TB | chênh")
for tol in (0, 1, 2, 4, 8):
    null = [f1(nhan, rng.choice(np.arange(20, n_nen), len(ith), replace=False), tol) for _ in range(100)]
    thuc = f1(nhan, ith, tol)
    print("   ±%d    |  %.3f  |      %.3f       | %+.3f" % (tol, thuc, np.mean(null), thuc - np.mean(null)))
```

```text
Kết quả khi mình chạy:
dung sai | F1 thật | F1 ngẫu nhiên TB | chênh
   ±0    |  0.841  |      0.056       | +0.785
   ±1    |  0.841  |      0.165       | +0.676
   ±2    |  0.842  |      0.260       | +0.582
   ±4    |  0.856  |      0.412       | +0.444
   ±8    |  0.865  |      0.581       | +0.284
```

F1 thật nhích từ 0,84 lên 0,87, nhưng F1 ngẫu nhiên tăng từ 0,06 lên 0,58: phần hơn ngẫu nhiên giảm gần ba lần. Dung sai
rộng làm con số đẹp lên mà thông tin ít đi. Đó là lý do trang Đánh giá in F1 ngẫu nhiên cạnh F1 thật.
</details>

**Bài 3 — Snooping trên dữ liệu thật.** Trên XAU M15 01–08/2024, thử 400 luật «đoán chiều nến kế tiếp»: theo đà hoặc ngược
đà của k nến qua, k = 1…200. Chọn luật tốt nhất trên tháng 1–4, xem nó ở tháng 5–8. Tương quan hạng giữa hai giai đoạn là
bao nhiêu?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

d = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
c = d["close"]
sau = np.sign(c.shift(-1) - c)                                 # chiều nến kế tiếp
dau = d.index < "2024-05-01"
kq = {}
for k in range(1, 201):
    for chieu in (1, -1):                                      # theo đà (+1) hoặc ngược đà (−1): 400 «luật»
        du = chieu * np.sign(c - c.shift(k))
        ok = du.ne(0) & sau.ne(0) & sau.notna() & du.notna()
        dung = (du == sau)[ok]
        kq[(k, chieu)] = (dung[dau[ok.to_numpy()]].mean(), dung[~dau[ok.to_numpy()]].mean())
kq = pd.DataFrame(kq, index=["T1-4", "T5-8"]).T
best = kq["T1-4"].idxmax()
print("400 luật. Tốt nhất T1–4: k=%d, chiều %+d: %.2f%%  →  T5–8: %.2f%%" % (best[0], best[1], 100 * kq.loc[best, "T1-4"], 100 * kq.loc[best, "T5-8"]))
print("Top 5 T1–4 → T5–8:"); print((100 * kq.nlargest(5, "T1-4")).round(2).to_string())
print("Tương quan hạng T1–4 / T5–8: %.2f" % kq["T1-4"].corr(kq["T5-8"], method="spearman"))
```

```text
Kết quả khi mình chạy:
400 luật. Tốt nhất T1–4: k=1, chiều -1: 52.36%  →  T5–8: 51.43%
Top 5 T1–4 → T5–8:
        T1-4   T5-8
1  -1  52.36  51.43
13 -1  51.45  50.53
3  -1  51.43  51.41
19 -1  51.39  50.27
42 -1  51.35  49.37
Tương quan hạng T1–4 / T5–8: 0.02
```

Tương quan hạng 0,02: xếp hạng 400 luật ở tháng 1–4 không nói gì về tháng 5–8. Luật đứng đầu («ngược đà 1 nến») giữ được
51,4% vì có cơ sở: nhiễu báo giá tạo tự tương quan âm ở trễ 1 (module 4). Nhưng 1,4 điểm % ở M15 nhỏ hơn nhiều so với chi phí
(chi phí một vòng XAU ≈ 19% biên độ một nến M15, module 8).
</details>

**Bài 4 — Shift test cho order flow của lab.** Lấy cột `order_flow` trong timeline của `ict_structure` (+1 tăng, −1 giảm,
0 chưa rõ) trên XAU M15 01–08/2024. Thống kê: lợi suất log 16 nến tới trung bình khi order flow tăng trừ khi giảm. Kiểm bằng
999 lần dịch vòng. Kết luận có khớp với nghiên cứu order flow của lab không?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

kq = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")
tl = kq["timeline"]
c = pd.Series([b.close for b in kq["nen"]])
of = tl["order_flow"].fillna(0).to_numpy()                     # +1 tăng, −1 giảm, 0 chưa rõ / chưa có
h = 16
y_all = (np.log(c).shift(-h) - np.log(c)).to_numpy()          # lợi suất log 16 nến tới
ok = ~np.isnan(y_all)
s, y = of[ok], y_all[ok]
n = len(y)
print("Tỷ lệ thời gian: tăng %.0f%%, giảm %.0f%%, chưa rõ %.0f%%" % tuple(100 * np.mean(s == v) for v in (1, -1, 0)))

def thong_ke(s):
    return y[s == 1].mean() - y[s == -1].mean()               # chênh lợi suất tới: order flow tăng − giảm

rng = np.random.default_rng(4)
thuc = thong_ke(s)
dich = rng.integers(500, n - 500, 999)
null = np.array([thong_ke(np.roll(s, k)) for k in dich])
print("Chênh thật: %+.2f bp; null dịch vòng: P5 %+.2f, P95 %+.2f bp; p hai phía = %.3f"
      % (1e4 * thuc, 1e4 * np.percentile(null, 5), 1e4 * np.percentile(null, 95),
         (1 + np.sum(np.abs(null) >= abs(thuc))) / (len(null) + 1)))
```

```text
Kết quả khi mình chạy:
Tỷ lệ thời gian: tăng 46%, giảm 30%, chưa rõ 24%
Chênh thật: -1.08 bp; null dịch vòng: P5 -4.91, P95 +4.72 bp; p hai phía = 0.709
```

Chênh −1,1 bp (ngược chiều mong đợi) nằm giữa null [−4,9; +4,7] bp, p = 0,71: order flow không báo trước chiều 16 nến tới,
khớp với kết luận của [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md). Lab đã chốt order flow là
**mô tả, không phải dự báo**. Để ý null rộng ±5 bp: chênh lệch nhỏ hơn vậy không phân biệt được với may rủi.
</details>

## Tự kiểm

1. ITH so với đỉnh pivot 3/3 cho F1 0,73. Có kết luận được «ITH nhận diện đỉnh tốt» không?
<details><summary>Đáp án</summary>

Không. Pivot 3/3 là một định nghĩa khác, không phải nhãn người gán: đây là so chéo định
nghĩa, đo hai định nghĩa trùng nhau bao nhiêu. Muốn nói «tốt» cần nhãn tham chiếu độc lập và chuẩn ngẫu nhiên.

</details>

2. Vì sao phải ghép một-một?
<details><summary>Đáp án</summary>

Nếu không, một sự kiện nằm giữa hai nhãn gần nhau được tính trúng cả hai, TP và recall bị
thổi lên. Một-một bắt mỗi nhãn và mỗi sự kiện chỉ thuộc một cặp.

</details>

3. Thử 50 cấu hình trên 3 000 nến, tốt nhất đoán đúng 53%. Cực đại kỳ vọng do may khoảng bao nhiêu, và 53% có thuyết phục?
<details><summary>Đáp án</summary>

σ = 0,5/√3000 ≈ 0,91 điểm %, hệ số ≈ 2,28 với N = 50, nên cực đại do may ≈ 52,1%. 53% chỉ
hơn mức đó khoảng một σ: chưa thuyết phục. Cần đoạn kiểm tra độc lập.

</details>

4. PBO = 0,68 nghĩa là gì?
<details><summary>Đáp án</summary>

Trong 68% cách chia trong / ngoài mẫu, cấu hình thắng trong mẫu rơi xuống nửa dưới ngoài
mẫu. Quy trình chọn không hơn bốc thăm; cấu hình «tốt nhất» chủ yếu là may.

</details>

5. Trên chuỗi bước ngẫu nhiên, chia xáo trộn cho độ chính xác 70%. Lỗi ở đâu, sửa thế nào?
<details><summary>Đáp án</summary>

Nhãn 32 nến tới chồng nhau và đặc trưng (mức giá) đổi chậm, nên mẫu kiểm tra có hàng xóm
liền kề trong tập huấn luyện với nhãn gần như trùng. Sửa: chia theo khối thời gian liền, purge các mẫu có cửa sổ nhãn chạm
tập kiểm tra, embargo thêm một đoạn sau đó.

</details>

6. Vì sao null hoán vị báo «có ý nghĩa» cho 83% chuỗi trạng thái bịa?
<details><summary>Đáp án</summary>

Hoán vị phá độ dai của chuỗi trạng thái, nên null chỉ tạo chênh lệch rất nhỏ. Chuỗi trạng
thái dai trùng với các đợt biến động dài của kết cục cho chênh lệch lớn hơn thế dù không có liên hệ. Dịch vòng giữ độ dai nên
null đúng cỡ.

</details>

7. Bạn mở đoạn kiểm tra, F1 kém, sửa tham số rồi chấm lại đoạn kiểm tra và thấy tốt. Báo kết quả nào?
<details><summary>Đáp án</summary>

Báo kết quả lần mở đầu tiên (kém). Lần chấm sau không còn là kiểm tra độc lập (AGENTS.md
§6.3). Phiên bản mới phải chờ dữ liệu mới (forward) hoặc một đoạn kiểm tra khác khai trước.

</details>

8. BH giữ 10/48 kiểm định «giờ có lợi suất khác 0», nhiều cái ở 16–19 giờ New York. Có nên dựng chiến lược quanh giờ đó?
<details><summary>Đáp án</summary>

Chưa. Kiểm cơ chế trước: đó là giờ rollover, spread giãn, dữ liệu là giá Bid nên Bid tụt
rồi hồi — dấu vết báo giá, không giao dịch được. Cỡ hiệu ứng 0,1–0,8 bp mỗi nến cũng nhỏ hơn chi phí.

</details>

## Đọc thêm

- Marcos López de Prado, *Advances in Financial Machine Learning*: phần cross-validation trong tài chính (purging, embargo —
  danh mục lab ghi chương 7) và phần về overfit khi backtest.
- David Aronson, *Evidence-Based Technical Analysis*: thiên lệch do đào dữ liệu, kiểm định luật kỹ thuật bằng chuẩn ngẫu
  nhiên.
- James, Witten, Hastie, Tibshirani, Taylor, *An Introduction to Statistical Learning*: chương về resampling
  (cross-validation, bootstrap).
- Bài gốc: Bailey, Borwein, López de Prado, Zhu (PBO, 2017); Bailey & López de Prado (Deflated Sharpe, 2014); Harris
  (shift test, 2020, arXiv 2012.06862); White (Reality Check, 2000); van den Burg & Williams (đánh giá điểm đổi, 2020).
- Tài liệu lab: [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md),
  [`nghien_cuu_bias_regime.md`](../research/nghien_cuu_bias_regime.md) (null, shift test, PBO cho regime).
- Danh mục quant ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md)): R7-01 purge/embargo, R7-03
  walk-forward, R7-05 đăng ký trước, R7-06 PBO, R7-07 Deflated Sharpe, R7-14 BH, R7-20 shift test, R7-22 null mô phỏng,
  R7-30 F1 có dung sai và baseline «zero», R7-46 baseline ngây thơ.
