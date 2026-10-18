# Module 8 — Chiến lược và chi phí

> **Sau module này bạn làm được:**
> - biến một tín hiệu thành vị thế không nhìn tương lai (chốt ở close, vào ở open nến sau) và bắt được lỗi nhìn tương
>   lai trong backtest;
> - tính lãi/lỗ theo điểm giá, pip, %, bp và USD/lot cho XAUUSD và EURUSD;
> - ước lượng chi phí một vòng (spread, hoa hồng, trượt giá) và tỷ lệ chi phí / biên độ nến theo khung;
> - viết backtest có chi phí, tính Sharpe năm hoá đúng, drawdown tối đa, turnover; so với «đứng ngoài» và «mua giữ»;
> - giải thích vì sao «tốt nhất trong backtest» không đáng tin, và router E0 / E1 của Copilot cần gì từ lab.
>
> **Cần trước:** module 2, 7 (module 4, 6 có ích)  ·  **Thời lượng:** ~6 giờ

> **Đọc trước khi bắt đầu.** Lab **không đo P&L** ([`AGENTS.md`](../../AGENTS.md) §2.4: không đưa win rate / P&L vào
> thống kê lần chạy). Module này là bài học cho **repo giao dịch** sau này. Mọi con số lãi/lỗ, Sharpe trong bài chỉ để
> học cách đo, dựa trên **chi phí giả định**, **không phải kết quả của lab** và không phải khuyến nghị giao dịch.

> **Ba điều cần nhớ** (đọc lại khi ôn)
>
> 1. Luôn vào lệnh ở open nến sau tín hiệu: cùng một luật, nhìn tương lai biến 0%/năm thành +40%/năm.
> 2. Chi phí so với biên độ một nến của XAUUSD: M5 33%, M15 19%, H1 9%, D1 1,4%. Khung càng nhỏ càng khó thắng chi phí.
> 3. Trong ví dụ, time-series momentum D1 không thắng mua giữ vàng; London breakout M15 âm sau phí. «Đứng ngoài» là baseline phải thắng.

## Vì sao cần

Nhận diện đúng cấu trúc chưa phải là kiếm được tiền. Ở giữa còn bốn bước: biến tín hiệu thành vị thế mà không nhìn tương lai,
trừ chi phí, so với cách đơn giản nhất (đứng ngoài, mua giữ), và loại phần «may» do thử nhiều cấu hình. Repo giao dịch cũ là
ví dụ: artifact M15 thật duy nhất có lợi thế 0,07–1 bp mỗi tín hiệu *trước phí*, trong khi chính repo giả định chi phí 10–16
bp mỗi vòng; README của nó ghi «cost/move ratio M15 40% vs H1 12%»
([`nghien_cuu_regime_copilot_va_repo_cu.md`](../research/nghien_cuu_regime_copilot_va_repo_cu.md) §2.2–2.3). Sản phẩm
Copilot muốn «nhận diện điều kiện thị trường, chọn giữa hai chiến lược hoặc No Trade»; chuỗi thí nghiệm E0 → E1 sẽ đo việc
đó *sau chi phí*. Module này cho bạn đủ công cụ để đọc và tự làm các phép đo ấy.

## 1. Từ tín hiệu tới vị thế

**Trực giác.** Nến D1 đóng lúc 17:00 New York. Bạn chỉ biết «giá đóng cửa hôm nay cao hơn 20 nến trước» *sau khi* nến
đóng. Sớm nhất bạn vào lệnh được ở open nến kế tiếp (sau giờ nghỉ 17:00–18:00 NY). Backtest nào cho bạn vào lệnh trước lúc
đó là đang nhìn tương lai.

**Định nghĩa.** **Tín hiệu (signal)** $s_t$ tính từ nến đã đóng tới hết nến t. **Vị thế (position)** $q_{t+1} = s_t$ giữ
trong nến t+1, từ open nến t+1 tới open nến t+2. Lợi suất chiến lược của nến t+1:

$$r^{\text{cl}}_{t+1} = q_{t+1}\left(\frac{O_{t+2}}{O_{t+1}} - 1\right)$$

Bằng lời: vị thế chốt lúc close hôm nay, ăn lợi suất open-tới-open của ngày mai. **Nhìn tương lai (look-ahead bias)**: dùng
bất cứ giá nào chưa có ở thời điểm ra quyết định.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

d = nap_nen(XAU_D1, "2018-01-01", "2024-09-01")
o, c = d["open"], d["close"]
tin_hieu = np.sign(c - c.shift(20))                 # biết lúc nến t ĐÓNG: giá đóng cửa hôm nay so với 20 nến trước

# Đúng: tín hiệu chốt ở close t → vào ở open t+1, giữ tới open t+2 (lợi suất open→open của nến t+1)
r_dung = tin_hieu * (o.shift(-2) / o.shift(-1) - 1)
# Sai: dùng tín hiệu của nến t cho lợi suất close t-1 → close t — tức là «biết» close t trước khi vào lệnh
r_sai = tin_hieu * (c / c.shift(1) - 1)
# Gần đúng: vào đúng giá close t (giả định khớp được ở chính giá tạo tín hiệu)
r_close = tin_hieu * (c.shift(-1) / c - 1)

N = len(d) / ((d.index[-1] - d.index[0]).days / 365.25)      # số nến D1 mỗi năm trong dữ liệu
for ten, r in (("đúng: vào open nến sau", r_dung), ("sai: nhìn tương lai", r_sai), ("vào ngay close t", r_close)):
    r = r.dropna()
    print("%-24s lợi suất TB/năm %+6.1f%%   ngày đúng chiều %.1f%%" % (ten, 100 * r.mean() * N, 100 * (r > 0).mean()))
print("Số nến D1 mỗi năm: %.1f" % N)
```

```text
Kết quả khi mình chạy:
đúng: vào open nến sau   lợi suất TB/năm   -0.0%   ngày đúng chiều 49.3%
sai: nhìn tương lai      lợi suất TB/năm  +40.0%   ngày đúng chiều 56.7%
vào ngay close t         lợi suất TB/năm   -0.8%   ngày đúng chiều 49.6%
Số nến D1 mỗi năm: 258.6
```

Cùng một luật, cùng dữ liệu: dời mốc lợi suất *một nến* biến 0%/năm thành 40%/năm. Lỗi này không hiện ra khi đọc code
lướt, chỉ hiện ra khi bạn hỏi «giá này có trước lúc quyết định không?». Đây cũng là luật nhân quả của lab
([`AGENTS.md`](../../AGENTS.md) §2.1) áp vào giao dịch: quyết định ở nến t chỉ dùng nến đã đóng tới t.

**Bẫy hay gặp.**

- Dùng nến H4/D1 đang hình thành, hoặc gắn nhãn đầu kỳ rồi điền ngược — lỗi rò tới 23 giờ của repo cũ.
- Vào lệnh ở mức phá vỡ trong khi điều kiện lại xét bằng close (bài tập 2: +1,9 bp thành +59,5 bp mỗi lệnh).
- Một nến chạm cả stop và target: không biết cái nào trước. Dùng dữ liệu khung nhỏ hơn hoặc giả định bất lợi, không chọn kết
  quả có lợi (tài liệu Copilot, «hợp đồng mô phỏng»).

## 2. Lãi/lỗ theo điểm giá và theo %

**Trực giác.** «Vàng chạy 10 giá» và «EUR chạy 10 pip» không so được với nhau: một cái là 0,4%, một cái là 0,09%.

**Định nghĩa.** **Điểm giá (price points)**: chênh lệch giá thô (XAUUSD tính bằng USD/oz). **Pip**: với EURUSD là 0,0001.
**Basis point (bp)** = 0,01% = $10^{-4}$. Lãi/lỗ của một vị thế: $\text{P\&L (USD)} = \Delta\text{giá} \times \text{khối lượng}$,
khối lượng tính bằng oz hoặc EUR; theo %: $\Delta\text{giá}/\text{giá vào}$. Quy ước phổ biến của broker: 1 lot vàng = 100
oz, 1 lot EURUSD = 100 000 EUR (kiểm lại spec của broker bạn dùng). [`AGENTS.md`](../../AGENTS.md) §9: không dùng thông số
pip/lot của EURUSD cho vàng; so biên độ giữa các mã bằng ATR hoặc bp.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# Hợp đồng chuẩn (quy ước phổ biến của broker — kiểm lại spec của broker bạn dùng)
LOT = {"XAU": 100, "EUR": 100_000}           # 1 lot = 100 oz vàng; 100 000 EUR
DIEM = {"XAU": (1.0, "USD/oz"), "EUR": (0.0001, "pip")}
for ma, ds in (("XAU", XAU_D1), ("EUR", EUR_D1)):
    d = nap_nen(ds, "2024-01-01", "2024-09-01")
    diem = d["open"].shift(-1) - d["open"]                      # P&L của 1 đơn vị giữ từ open tới open nến sau
    pct = d["open"].shift(-1) / d["open"] - 1
    usd = diem * LOT[ma]                                        # P&L của 1 lot, bằng USD (đồng định giá)
    dv, ten = DIEM[ma]
    print("%s: |thay đổi 1 nến D1| trung vị = %.1f %s = %.2f%% = %.0f bp = %.0f USD/lot"
          % (ma, diem.abs().median() / dv, ten, 100 * pct.abs().median(), 1e4 * pct.abs().median(), usd.abs().median()))
    i = 10
    print("   vd: long 1 lot từ open nến %s → open nến sau: %+.1f %s, %+.3f%%, %+.0f USD"
          % (d.index[i].strftime("%Y-%m-%d %H:%M UTC"), diem.iloc[i] / dv, ten, 100 * pct.iloc[i], usd.iloc[i]))
```

```text
Kết quả khi mình chạy:
XAU: |thay đổi 1 nến D1| trung vị = 12.8 USD/oz = 0.56% = 56 bp = 1279 USD/lot
   vd: long 1 lot từ open nến 2024-01-15 22:00 UTC → open nến sau: -27.0 USD/oz, -1.315%, -2702 USD
EUR: |thay đổi 1 nến D1| trung vị = 19.2 pip = 0.18% = 18 bp = 192 USD/lot
   vd: long 1 lot từ open nến 2024-01-15 22:00 UTC → open nến sau: -75.0 pip, -0.685%, -750 USD
```

Một ngày bình thường vàng đi 56 bp, EUR đi 18 bp: vàng «động» gấp ba. Vì vậy từ đây mọi so sánh giữa hai mã dùng % hoặc bp.

**Bẫy hay gặp.**

- «Pip» của vàng mỗi broker một kiểu (0,01 hay 0,1): đừng dùng pip cho vàng.
- Cộng lãi/lỗ theo điểm qua nhiều năm khi giá đổi mạnh (vàng 1 300 → 2 500): một điểm năm 2018 «nặng» gần gấp đôi năm 2024.
  Dùng %.
- Nến D1 ghi giờ mở 22:00 UTC là ngày giao dịch *hôm sau* (mốc 17:00 New York, module 1).

## 3. Chi phí: spread, hoa hồng, trượt giá

**Trực giác.** Mua ở giá hỏi (ask), bán ở giá chào (bid). Mỗi vòng mua rồi bán, bạn mất ít nhất một spread, cộng phí broker,
cộng phần khớp tệ hơn giá bạn thấy.

**Định nghĩa.**

- **Spread** = ask − bid. Dữ liệu của lab là giá **Bid** HistData, **không có cột spread** (danh mục quant §5 đề xuất đọc
  cột spread MT5 sau). Nên mọi spread dưới đây là **giả định**.
- **Hoa hồng (commission)**: phí theo lot, thường tính cả vào và ra.
- **Trượt giá (slippage)**: giá khớp tệ hơn giá dự kiến, lớn hơn khi tin ra, đầu phiên, thanh khoản mỏng.
- **Chi phí một vòng (round-trip cost)** = spread + hoa hồng hai chiều + trượt giá hai chiều.
- **Swap / phí qua đêm**: giữ lệnh qua 17:00 NY phải trả hoặc nhận; bài này **chưa tính**, với lệnh giữ nhiều ngày nó có thể
  lớn hơn spread.

Giả định dùng trong cả module (giờ thanh khoản tốt, tài khoản kiểu ECN; giờ Á, rollover, tin lớn đều tệ hơn):

| Mã | Spread | Hoa hồng (vào + ra) | Trượt giá (vào + ra) | Một vòng |
|---|---|---|---|---|
| XAUUSD | 0,25 USD/oz | 0,07 USD/oz (7 USD/lot) | 0,10 USD/oz | **0,42 USD/oz** |
| EURUSD | 0,6 pip | 0,7 pip (7 USD/lot) | 0,2 pip | **1,5 pip** |

Mức XAU này gần với chi phí 0,5 điểm/vòng mà Mesfin (2026) dùng cho vàng micro MGC (mục R8-31). **Tỷ lệ chi phí / biên
độ** = chi phí một vòng chia trung vị biên độ nến (high − low): phần biên độ một nến bị chi phí ăn mất.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# GIẢ ĐỊNH chi phí một vòng (vào + ra), giờ thanh khoản tốt — KHÔNG phải số đo của lab (lab chỉ có giá Bid)
CHI_PHI = {"XAU": dict(spread=0.25, hoa_hong=0.07, truot=0.10),         # USD/oz
           "EUR": dict(spread=0.00006, hoa_hong=0.00007, truot=0.00002)}  # đơn vị giá (1 pip = 0.0001)
DON_VI = {"XAU": (1.0, "USD"), "EUR": (0.0001, "pip")}
DS = {"XAU": {"M5": XAU_M5, "M15": XAU_M15, "H1": XAU_H1, "H4": XAU_H4, "D1": XAU_D1},
      "EUR": {"M5": "ds_17ffe8e4b74d", "M15": EUR_M15_DAI, "H1": EUR_H1, "H4": "ds_8e87b4f82dfe", "D1": EUR_D1}}
for ma, bang in DS.items():
    cp = sum(CHI_PHI[ma].values()); dv, ten_dv = DON_VI[ma]
    gia = nap_nen(bang["D1"], "2024-01-01", "2024-09-01")["close"].median()
    print("%s: chi phí một vòng = %.2f %s = %.1f bp (giá trung vị %.4g)" % (ma, cp / dv, ten_dv, 1e4 * cp / gia, gia))
    for khung, ds in bang.items():
        d = nap_nen(ds, "2024-01-01", "2024-09-01")
        bien_do = (d["high"] - d["low"]).median()
        print("   %-3s  trung vị biên độ nến %6.2f %s   chi phí / biên độ = %5.1f%%"
              % (khung, bien_do / dv, ten_dv, 100 * cp / bien_do))
```

```text
Kết quả khi mình chạy:
XAU: chi phí một vòng = 0.42 USD = 1.8 bp (giá trung vị 2326)
   M5   trung vị biên độ nến   1.26 USD   chi phí / biên độ =  33.3%
   M15  trung vị biên độ nến   2.25 USD   chi phí / biên độ =  18.7%
   H1   trung vị biên độ nến   4.58 USD   chi phí / biên độ =   9.2%
   H4   trung vị biên độ nến   9.87 USD   chi phí / biên độ =   4.3%
   D1   trung vị biên độ nến  30.27 USD   chi phí / biên độ =   1.4%
EUR: chi phí một vòng = 1.50 pip = 1.4 bp (giá trung vị 1.084)
   M5   trung vị biên độ nến   2.10 pip   chi phí / biên độ =  71.4%
   M15  trung vị biên độ nến   3.80 pip   chi phí / biên độ =  39.5%
   H1   trung vị biên độ nến   8.00 pip   chi phí / biên độ =  18.8%
   H4   trung vị biên độ nến  17.00 pip   chi phí / biên độ =   8.8%
   D1   trung vị biên độ nến  52.35 pip   chi phí / biên độ =   2.9%
```

Biên độ tăng gần theo $\sqrt{\text{thời gian}}$ (module 3, 4), còn chi phí mỗi vòng thì cố định. Nên khung càng nhỏ, chi phí
càng chiếm phần lớn: ở EUR M15, một vòng giao dịch ăn 40% biên độ một nến trung vị (README repo cũ, với tài sản và cách tính khác, cũng ghi
M15 40%, H1 12% — cùng một bức tranh). Một
chiến lược M15 phải đoán đúng *rất* thường xuyên mới bù được, trong khi module 3 và 7 cho thấy chiều giá ngắn hạn gần như
không đoán được.

**Bẫy hay gặp.**

- Spread không cố định: rộng hơn ở giờ Á, quanh rollover 17:00 NY, khi tin ra (bài tập 1 tính tỷ lệ theo giờ).
- Chi phí cố định theo USD nên tính theo bp sẽ cao hơn khi giá vàng thấp (1,8 bp năm 2024, khoảng 3 bp năm 2018).
- Backtest trên giá Bid: lệnh mua thật khớp ở ask. Bỏ qua spread là cộng lãi giả cho mọi lệnh mua.

## 4. Sharpe, drawdown, turnover — năm hoá cho đúng

**Trực giác.** Lãi 10%/năm với biến động 5% khác hẳn lãi 10%/năm với biến động 40%. Cần thước đo lãi trên rủi ro, thước đo
nỗi đau tệ nhất, và thước đo giao dịch nhiều hay ít.

**Định nghĩa.**

- **Sharpe ratio** năm hoá: $SR = \frac{\bar r}{s_r}\sqrt{N}$, với $\bar r$, $s_r$ là trung bình và độ lệch chuẩn lợi suất
  mỗi nến, **N là số nến mỗi năm của chính dữ liệu**. Bằng lời: lợi suất trung bình trên một đơn vị biến động, quy về năm.
  D1 vàng / FX có khoảng 258–261 nến mỗi năm (nghỉ cuối tuần), không phải 365, và 252 là quy ước của cổ phiếu Mỹ. (Bài
  này bỏ qua lãi suất phi rủi ro.)
- **Sai số chuẩn của Sharpe** (Lo 2002, lợi suất iid): $\text{SE}(SR) \approx \sqrt{(1 + SR^2/2)/Y}$ với Y số năm.
- **Drawdown tối đa (max drawdown)**: $\min_t \left(V_t / \max_{s \le t} V_s - 1\right)$, V là giá trị tài khoản — mức sụt
  sâu nhất từ đỉnh.
- **Turnover**: tổng $|q_{t+1} - q_t|$ mỗi năm. Đảo từ +1 sang −1 là turnover 2 (đóng một, mở một). Chi phí tỷ lệ với nó.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

d = nap_nen(XAU_D1, "2019-01-01", "2024-09-01")
r = (d["open"].shift(-1) / d["open"] - 1).dropna()          # mua giữ vàng, lợi suất open → open từng nến D1
nam = (d.index[-1] - d.index[0]).days / 365.25
N = len(r) / nam
s_ngay = r.mean() / r.std()                                 # Sharpe một nến (chưa năm hoá)
for ten, n in (("đếm từ dữ liệu", N), ("252 (quy ước cổ phiếu)", 252), ("365 (sai: có ngày không giao dịch)", 365)):
    print("Năm hoá × √%-6.1f %-36s Sharpe = %.2f" % (n, ten, s_ngay * np.sqrt(n)))
SR = s_ngay * np.sqrt(N)
print("Sai số chuẩn xấp xỉ của Sharpe năm (Lo 2002, lợi suất iid): √((1 + SR²/2)/số năm) = %.2f  (%.1f năm)"
      % (np.sqrt((1 + SR ** 2 / 2) / nam), nam))
theo_nam = r.groupby(r.index.year).apply(lambda x: x.mean() / x.std() * np.sqrt(N))
print("Sharpe từng năm:", theo_nam.round(2).to_dict())
```

```text
Kết quả khi mình chạy:
Năm hoá × √258.5  đếm từ dữ liệu                       Sharpe = 0.88
Năm hoá × √252.0  252 (quy ước cổ phiếu)               Sharpe = 0.87
Năm hoá × √365.0  365 (sai: có ngày không giao dịch)   Sharpe = 1.04
Sai số chuẩn xấp xỉ của Sharpe năm (Lo 2002, lợi suất iid): √((1 + SR²/2)/số năm) = 0.50  (5.7 năm)
Sharpe từng năm: {2019: 1.52, 2020: 1.25, 2021: -0.24, 2022: 0.07, 2023: 0.99, 2024: 2.12}
```

Năm hoá bằng √365 thổi Sharpe lên 19%. Quan trọng hơn: với 5,7 năm, Sharpe 0,88 có sai số chuẩn 0,50, khoảng tin cậy 95%
xấp xỉ −0,1 → 1,9. Sharpe từng năm đi từ −0,24 tới 2,12. Một Sharpe tính trên vài năm là một con số rất ồn.

**Bẫy hay gặp.**

- Năm hoá M15 bằng $\sqrt{96 \times 365}$: sai vì có giờ nghỉ, cuối tuần. Đếm số nến thật mỗi năm.
- Cắt trần Sharpe để báo cáo, hay báo Sharpe đã «chọn» mà không nói đã thử bao nhiêu cấu hình (mục 7). Kế hoạch Copilot ghi
  rõ: «không cap Sharpe để báo cáo».
- Lợi suất có đuôi dày và tự tương quan làm công thức sai số chuẩn ở trên lạc quan; dùng bootstrap khối (module 2) khi cần.

## 5. Backtest không nhìn tương lai: time-series momentum trên D1

**Trực giác.** «Giá đã lên 3 tháng thì hay lên tiếp» — trend-following. Đây là loại chiến lược có bằng chứng sau chi phí
mạnh nhất trong nhóm R8 của danh mục, nên là ứng viên tốt để học cách backtest.

**Định nghĩa.** **Time-series momentum (TSMOM)**: $q_{t+1} = \text{sign}(C_t - C_{t-k})$, long nếu giá đóng cửa cao hơn k
nến trước, short nếu thấp hơn (Moskowitz, Ooi, Pedersen 2012; R8-01). Bản trung bình ba tốc độ 1/3/12 tháng (21/63/252 nến)
theo Hurst, Ooi, Pedersen 2017 (R8-02): $q = \frac13 \sum_{k} \text{sign}(C_t - C_{t-k})$. Hai mốc so sánh bắt buộc:
**đứng ngoài (stay flat)** — lãi 0, chi phí 0 — và **mua giữ (buy and hold)**.

Bằng chứng trong danh mục (JSON `danh_muc_quant_2026-10-12.json`):

- **R8-02**: 67 thị trường (29 hàng hoá, 11 chỉ số cổ phiếu, 15 trái phiếu, tiền tệ), 1880–2016; lợi nhuận dương trong mọi
  thập kỷ kể cả sau chi phí ước tính và phí 2/20; Sharpe gross trung bình *mỗi thị trường* khoảng 0,4. Rủi ro được ghi:
  lợi thế đa dạng hoá 67 thị trường «không có với 2–3 mã».
- **R8-05**: kênh Donchian / dual MA trên 28 futures hàng hoá, 48 năm dữ liệu tháng: lợi suất vượt trội dương sau chi phí ở
  ít nhất 22/28 thị trường, bền qua điều chỉnh data-mining (Szakmary, Shen, Sharma 2010). Nhưng 3 000 luật channel breakout
  trên FX: thị trường phát triển gần như hết lợi thế sau 1992–1996 (Hsu, Taylor, Wang 2016).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

CHI_PHI_VONG = {"XAU": 0.42, "EUR": 0.00015}        # GIẢ ĐỊNH một vòng (vào + ra), đơn vị giá — xem mục 3

def backtest(d, vi_the, cp_vong, tu="2019-01-01"):
    """vi_the: vị thế mục tiêu chốt ở CLOSE nến t (−1..1), giữ từ open t+1 tới open t+2.
    Trả lợi suất trước phí, sau phí và khối lượng đổi vị thế — từng nến, từ ngày «tu»."""
    giu = vi_the.shift(1).fillna(0.0)                         # vị thế đang giữ trong nến t+1
    r_oo = d["open"].shift(-1) / d["open"] - 1                # lợi suất open → open nến sau
    doi = giu.diff().abs().fillna(giu.abs())                  # khối lượng mua/bán ở open (turnover)
    chi_phi = doi * (cp_vong / 2) / d["open"]                 # mỗi lần mua HOẶC bán trả nửa chi phí một vòng
    m = (d.index >= tu) & r_oo.notna()
    return (giu * r_oo)[m], (giu * r_oo - chi_phi)[m], doi[m]

def sharpe(r, N):
    return "%5.2f" % (r.mean() / r.std() * np.sqrt(N)) if r.std() > 0 else "  —  "   # đứng ngoài: không xác định

def dd_toi_da(r):
    von = (1 + r).cumprod()
    return (von / von.cummax() - 1).min()

for ma, ds in (("XAU", XAU_D1), ("EUR", EUR_D1)):
    d = nap_nen(ds, "2018-01-01", "2024-09-01")
    c = d["close"]
    N = len(d) / ((d.index[-1] - d.index[0]).days / 365.25)   # số nến D1 mỗi năm của chính dữ liệu này
    ct = {"đứng ngoài": c * 0.0, "mua giữ": c * 0 + 1.0}
    for k in (20, 60, 250):
        ct["TSMOM %d" % k] = np.sign(c - c.shift(k))
    ct["TSMOM 21/63/252"] = sum(np.sign(c - c.shift(k)) for k in (21, 63, 252)) / 3
    print("\n%s D1, 01/2019 → 08/2024, %.0f nến/năm" % (ma, N))
    print("  chiến lược       | %/năm trước → sau phí | Sharpe trước → sau | DD tối đa | turnover/năm")
    for ten, vt in ct.items():
        g, n, doi = backtest(d, vt, CHI_PHI_VONG[ma])
        print("  %-16s |   %+5.1f%% → %+5.1f%%      |   %s → %s    |  %6.1f%%  | %5.1f"
              % (ten, 100 * g.mean() * N, 100 * n.mean() * N, sharpe(g, N), sharpe(n, N),
                 100 * dd_toi_da(n), doi.sum() / (len(n) / N)))
```

```text
Kết quả khi mình chạy:

XAU D1, 01/2019 → 08/2024, 259 nến/năm
  chiến lược       | %/năm trước → sau phí | Sharpe trước → sau | DD tối đa | turnover/năm
  đứng ngoài       |    +0.0% →  +0.0%      |     —   →   —      |     0.0%  |   0.0
  mua giữ          |   +13.1% → +13.1%      |    0.88 →  0.88    |   -21.4%  |   0.0
  TSMOM 20         |    +0.9% →  +0.2%      |    0.06 →  0.02    |   -26.9%  |  58.0
  TSMOM 60         |    +5.6% →  +5.3%      |    0.38 →  0.36    |   -26.8%  |  23.3
  TSMOM 250        |    +4.8% →  +4.6%      |    0.32 →  0.31    |   -42.8%  |  14.5
  TSMOM 21/63/252  |    +2.1% →  +1.8%      |    0.18 →  0.16    |   -29.8%  |  27.9

EUR D1, 01/2019 → 08/2024, 261 nến/năm
  chiến lược       | %/năm trước → sau phí | Sharpe trước → sau | DD tối đa | turnover/năm
  đứng ngoài       |    +0.0% →  +0.0%      |     —   →   —      |     0.0%  |   0.0
  mua giữ          |    -0.3% →  -0.3%      |   -0.05 → -0.05    |   -22.2%  |   0.0
  TSMOM 20         |    -2.1% →  -2.5%      |   -0.30 → -0.34    |   -21.6%  |  51.6
  TSMOM 60         |    -2.5% →  -2.7%      |   -0.34 → -0.38    |   -22.7%  |  38.6
  TSMOM 250        |    +1.4% →  +1.4%      |    0.20 →  0.19    |   -16.1%  |  11.7
  TSMOM 21/63/252  |    +0.2% →  -0.1%      |    0.03 → -0.01    |    -7.6%  |  32.7
```

(Tính từ 01/2019 để mọi luật, kể cả k = 252, đã đủ nến khởi động; mua giữ vào lệnh trước mốc đó nên turnover trong khoảng
đo là 0.)

Đọc bảng:

- Ở D1, chi phí chỉ ăn 0–0,7%/năm. Vấn đề ở D1 không phải chi phí mà là tín hiệu: không bản TSMOM nào thắng mua giữ vàng
  (Sharpe 0,88), và ở EUR không có gì đáng kể — mọi Sharpe nằm trong ±0,4, không vượt sai số chuẩn ~0,42 (công thức mục 4
  với SR ≈ 0 và 5,7 năm).
- Mua giữ vàng «thắng» vì 2019–2024 vàng tăng mạnh. Đó cũng là *một* lần rút từ lịch sử, không phải quy luật.
- Bằng chứng TSMOM trong tài liệu đến từ danh mục nhiều chục thị trường, khung tháng. Một hai mã, vài năm D1 không tái tạo
  được lợi thế đa dạng hoá đó. Phản biện R8-04 còn cho thấy phần lớn hiệu ứng nằm ở việc **chia vị thế theo biến động**
  (Kim, Tse, Wald: alpha 1,27%/tháng khi có vol scaling, 0,41%/tháng khi không) — bài tập 3.

**Bẫy hay gặp.**

- So TSMOM với 0 thay vì với mua giữ và đứng ngoài.
- Quên giai đoạn khởi động: luật k = 250 chưa có tín hiệu năm 2018, so cả năm đó với mua giữ là không công bằng.
- Chưa tính swap: TSMOM giữ lệnh hàng tuần; swap qua đêm của vàng có thể vài %/năm, lớn hơn cả spread ở bảng trên.

## 6. Chiến lược trong ngày: chi phí ăn mòn

**Trực giác.** Ở M15, chi phí ăn 19% (XAU) đến 40% (EUR) biên độ một nến (mục 3). Một luật trong ngày phải có lợi thế
gross lớn hơn hẳn mức đó. Thử với một luật rất phổ biến trong cộng đồng ICT / retail: phá biên phiên Á ở đầu phiên London.

**Định nghĩa vận hành** (tham số do bài chọn, không tối ưu): biên phiên Á = đỉnh/đáy 00:00–07:00 giờ London; nến M15 đầu
tiên trong 07:00–10:00 *đóng* ngoài biên → vào ở open nến kế tiếp theo chiều phá; thoát ở open nến đầu tiên từ 16:00
London; tối đa một lệnh mỗi ngày. Bằng chứng trong danh mục:

- **R8-14** (mức tin cậy C): không có kiểm định peer-review nào; một backtest thương mại EURUSD H1 10/2016–10/2026: 1 230
  lệnh, thắng 36,3%, profit factor 0,87, −28% sau phí 0,02%/chiều.
- **R8-31** (Mesfin 2026, preprint): 14 họ tín hiệu intraday OHLCV trên MNQ/MGC 5 phút, 947 ngày 2021–2025, walk-forward,
  5 tiêu chí cùng lúc. Không họ nào qua đủ. 11 họ có lợi thế gross tối đa 0,07–1,50 điểm, dưới ngưỡng chi phí 2,0 điểm
  (MNQ). Đối chứng dương duy nhất qua được (GMM regime phiên London) có T = 4,30 ngoài mẫu, nhưng trễ vào lệnh **1 nến** thì
  T đổi dấu thành −2,78.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

CHI_PHI_VONG = {"XAU": 0.42, "EUR": 0.00015}      # GIẢ ĐỊNH một vòng, đơn vị giá

def london_breakout(d):
    """Phiên Á = 00:00–07:00 giờ London. Nến M15 đầu tiên trong 07:00–10:00 ĐÓNG ngoài biên phiên Á → vào ở OPEN nến
    kế tiếp theo chiều phá; thoát ở open nến đầu tiên từ 16:00 London. Mỗi ngày tối đa một lệnh. Tham số do bài chọn."""
    t = d.index.tz_convert("Europe/London")
    x = d.assign(ngay=t.date, phut=t.hour * 60 + t.minute, vt=np.arange(len(d)))
    a = x[x.phut < 7 * 60].groupby("ngay").agg(hi=("high", "max"), lo=("low", "min"), n=("high", "size"))
    a = a[a.n >= 20]                                                     # phiên Á đủ nến (bỏ ngày thiếu dữ liệu)
    w = x[(x.phut >= 7 * 60) & (x.phut < 10 * 60)].join(a, on="ngay", how="inner")
    w["chieu"] = np.where(w.close > w.hi, 1, np.where(w.close < w.lo, -1, 0))
    vao = w[w.chieu != 0].groupby("ngay").first()                        # lần phá đầu tiên trong ngày
    ra = x[x.phut >= 16 * 60].groupby("ngay").first()                    # nến đầu tiên từ 16:00
    lenh = vao.join(ra[["open"]].rename(columns={"open": "gia_ra"}), how="inner")
    lenh = lenh[lenh.vt + 1 < len(d)]
    lenh["gia_vao"] = d["open"].to_numpy()[lenh.vt + 1]
    lenh = lenh[np.asarray(t.date)[lenh.vt + 1] == lenh.index.to_numpy()]   # nến vào lệnh cùng ngày
    lenh["diem"] = lenh.chieu * (lenh.gia_ra - lenh.gia_vao)
    return lenh, len(a)

for ma, ds in (("XAU", XAU_M15_DAI), ("EUR", EUR_M15_DAI)):
    d = nap_nen(ds, "2018-01-01", "2024-09-01")
    L, so_ngay = london_breakout(d)
    cp = CHI_PHI_VONG[ma]
    g = 1e4 * L.diem / L.gia_vao                       # lãi/lỗ mỗi lệnh trước phí, bp
    n = 1e4 * (L.diem - cp) / L.gia_vao                # sau phí
    t_stat = lambda s: s.mean() / s.std() * np.sqrt(len(s))
    print("%s: %d lệnh trên %d ngày đủ dữ liệu phiên Á" % (ma, len(L), so_ngay))
    print("   TB mỗi lệnh: trước phí %+.2f bp (t = %+.2f) | chi phí %.2f bp | sau phí %+.2f bp (t = %+.2f) | thắng sau phí %.0f%%"
          % (g.mean(), t_stat(g), (g - n).mean(), n.mean(), t_stat(n), 100 * (n > 0).mean()))
    nam = np.array([x.year for x in L.index])
    print("   tổng bp sau phí theo năm:", n.groupby(nam).sum().round(0).astype(int).to_dict())
```

```text
Kết quả khi mình chạy:
XAU: 1213 lệnh trên 1720 ngày đủ dữ liệu phiên Á
   TB mỗi lệnh: trước phí +2.28 bp (t = +1.25) | chi phí 2.54 bp | sau phí -0.26 bp (t = -0.14) | thắng sau phí 46%
   tổng bp sau phí theo năm: {2018: -100, 2019: -1768, 2020: 339, 2021: -62, 2022: 383, 2023: -485, 2024: 1381}
EUR: 1473 lệnh trên 1733 ngày đủ dữ liệu phiên Á
   TB mỗi lệnh: trước phí -1.31 bp (t = -1.42) | chi phí 1.34 bp | sau phí -2.65 bp (t = -2.86) | thắng sau phí 47%
   tổng bp sau phí theo năm: {2018: -1657, 2019: -818, 2020: 84, 2021: 353, 2022: -867, 2023: -565, 2024: -436}
```

Đọc kết quả:

- XAU: lợi thế gross +2,3 bp mỗi lệnh (t = 1,25, chưa phân biệt được với may), chi phí 2,5 bp ăn sạch. Đúng mô hình R8-31:
  edge gross nhỏ hơn hoặc bằng chi phí.
- EUR: âm ngay cả trước phí; sau phí t = −2,86 — đều đặn mất tiền.
- Tổng theo năm nhảy từ −1 768 bp tới +1 381 bp. Ai backtest riêng 2024 sẽ thấy một chiến lược «tuyệt vời».
- Chi phí XAU tính theo bp ở đây là 2,54 (không phải 1,8 như mục 3) vì giá vàng 2018–2021 thấp hơn: chi phí cố định theo USD.

Kết quả này cũng khớp với điều lab đã đo bằng cách khác: đọc order flow kiểu ICT không đoán được phía thanh khoản kế tiếp
hơn ngẫu nhiên quá ±2 điểm % (module 3, 7). Lab chỉ kiểm được các định nghĩa vận hành của mình, không phải «ICT như được
dạy»; tài liệu học thuật cũng không có kiểm định nào ủng hộ ICT «như được dạy». Luật ở trên cũng chỉ là một định nghĩa vận
hành gần giống, do bài chọn.

**Bẫy hay gặp.**

- Chọn khung giờ (phiên Á kết thúc lúc mấy giờ, ra lúc mấy giờ) *sau khi* xem kết quả: bài tập 4 thử 12 biến thể.
- Đọc «thắng 46%» rồi nghĩ «chỉ cần R:R tốt hơn»: tỷ lệ thắng nói rất ít; nhìn lãi/lỗ trung bình sau phí và t.
- Bỏ qua spread giãn đầu phiên London và lúc tin ra: chi phí thật thường cao hơn giả định.

## 7. Vì sao «tốt nhất trong backtest» không đáng tin

**Trực giác.** Module 7 đã cho thấy: thử 200 bộ lọc trên nhiễu, cái tốt nhất vẫn đẹp, rồi sụp ngoài mẫu. Lưới tham số của
một chiến lược là đúng tình huống đó, thêm một lớp: Sharpe tính trên vài năm vốn đã ồn (mục 4).

**Định nghĩa.** Chọn cấu hình theo Sharpe trong mẫu rồi báo chính Sharpe đó là **thiên lệch chọn (selection bias)**. Mức «tốt
nhất do may» khi thử N cấu hình độc lập không có lợi thế:

$$\mathbb{E}[\max SR] \approx \text{SE}\cdot\left[(1-\gamma)\,\Phi^{-1}(1-1/N) + \gamma\,\Phi^{-1}(1-1/(Ne))\right],\quad \text{SE} \approx 1/\sqrt{Y}$$

Bằng lời: công thức cực đại kỳ vọng của module 7 mục 4, với sai số chuẩn của Sharpe năm khi có Y năm dữ liệu (Sharpe gần
0). Deflated Sharpe Ratio (R7-07) dùng đúng mức đó làm ngưỡng thay cho 0.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from scipy.stats import norm

CHI_PHI_VONG = {"XAU": 0.42, "EUR": 0.00015}
CAC_K = list(range(5, 255, 5))                       # 50 cấu hình lookback
for ma, ds in (("XAU", XAU_D1), ("EUR", EUR_D1)):
    d = nap_nen(ds, "2018-01-01", "2024-09-01")
    c, o = d["close"], d["open"]
    r_oo = o.shift(-1) / o - 1
    N = len(d) / ((d.index[-1] - d.index[0]).days / 365.25)
    sr = {}
    for k in CAC_K:
        giu = np.sign(c - c.shift(k)).shift(1).fillna(0.0)
        net = giu * r_oo - giu.diff().abs().fillna(0.0) * (CHI_PHI_VONG[ma] / 2) / o
        tr, ng = net["2019-01-01":"2021-12-31"].dropna(), net["2022-01-01":].dropna()
        sr[k] = (tr.mean() / tr.std() * np.sqrt(N), ng.mean() / ng.std() * np.sqrt(N))
    sr = pd.DataFrame(sr, index=["trong_mau", "ngoai_mau"]).T
    k = sr.trong_mau.idxmax()
    print("%s: tốt nhất 2019–2021 là k=%d, Sharpe %.2f  →  2022–08/2024: %.2f" % (ma, k, sr.trong_mau[k], sr.ngoai_mau[k]))
    print("     trung vị 50 cấu hình ngoài mẫu: %.2f;  tương quan hạng trong/ngoài mẫu: %.2f"
          % (sr.ngoai_mau.median(), sr.trong_mau.corr(sr.ngoai_mau, method="spearman")))
g = 0.5772156649
se = 1 / np.sqrt(3.0)                                 # sai số chuẩn Sharpe năm khi chỉ có ~3 năm
for n in (5, 10, 50):
    print("Null (không có lợi thế), %2d cấu hình độc lập, 3 năm: Sharpe lớn nhất kỳ vọng ≈ %.2f"
          % (n, se * ((1 - g) * norm.ppf(1 - 1 / n) + g * norm.ppf(1 - 1 / (n * np.e)))))
```

```text
Kết quả khi mình chạy:
XAU: tốt nhất 2019–2021 là k=230, Sharpe 0.87  →  2022–08/2024: 0.32
     trung vị 50 cấu hình ngoài mẫu: 0.35;  tương quan hạng trong/ngoài mẫu: -0.18
EUR: tốt nhất 2019–2021 là k=190, Sharpe 0.66  →  2022–08/2024: 0.34
     trung vị 50 cấu hình ngoài mẫu: 0.00;  tương quan hạng trong/ngoài mẫu: -0.05
Null (không có lợi thế),  5 cấu hình độc lập, 3 năm: Sharpe lớn nhất kỳ vọng ≈ 0.69
Null (không có lợi thế), 10 cấu hình độc lập, 3 năm: Sharpe lớn nhất kỳ vọng ≈ 0.91
Null (không có lợi thế), 50 cấu hình độc lập, 3 năm: Sharpe lớn nhất kỳ vọng ≈ 1.31
```

- Sharpe «tốt nhất» trong mẫu (0,87 và 0,66) *thấp hơn* mức may rủi kỳ vọng ngay cả khi 50 lookback chỉ tương đương 10 cấu
  hình độc lập (0,91). Tức là không có gì để giải thích ngoài may.
- XAU: cấu hình thắng ra ngoài mẫu còn 0,32, ngang trung vị của cả lưới (0,35) — chọn không thêm gì. EUR: cấu hình thắng
  0,34 ngoài mẫu, trên trung vị 0,00; nhưng thứ hạng trong/ngoài mẫu không tương quan (−0,05), nên một lần «trúng» như vậy
  chưa đủ tin.
- Thứ tự đúng theo kế hoạch Copilot §7: chốt dữ liệu, split, mục tiêu, chi phí *trước*; chọn trên validation; holdout cuối
  chỉ dùng một lần; lưu mọi lần thử và thất bại; dùng DSR / PBO khi đủ dữ liệu. Bộ 5 tiêu chí của Mesfin (t ≥ 2 trên net
  ngoài mẫu, ≥ 30 lệnh mỗi fold, net > 0 sau chi phí, cùng chiều qua các năm, p hoán vị) là một mẫu tiêu chí viết trước dùng
  lại được (R8-31).

## 8. Router E0 / E1 và vai trò của regime

**Trực giác.** Thay vì một chiến lược chạy mãi, router hỏi trước: «bây giờ thị trường đang ở trạng thái nào, chiến lược nào
hợp, hay nên đứng ngoài?». Nó chỉ có giá trị nếu thắng được cả từng chiến lược chạy một mình *và* việc đứng ngoài, sau
chi phí.

**Định nghĩa** (tài liệu Copilot, ngoài repo này: `D:\Finance_System\AI_Trading_Copilot_Luong_He_Thong.md` §4 và
`…_Ke_Hoach_Update_Va_Tich_Hop_Research.md` §7):

- **Router** nhận trạng thái Trend, Range, Breakout, Event-risk, Uncertain. Luật: Trend + Trend Pullback đủ bằng chứng →
  đề xuất Trend Pullback; Range + Mean Reversion đủ bằng chứng → Mean Reversion; Breakout khi chưa có bot tương ứng →
  No Trade; Uncertain hoặc tín hiệu xung đột → No Trade; dữ liệu cũ / sai → **chặn lệnh** (lỗi dữ liệu, không phải No Trade
  do thị trường).
- **E0**: từng chiến lược riêng + baseline tiền mặt (đứng ngoài) — biết chất lượng nền trước khi định tuyến. **E1**: router
  luật + No Trade, giữ nguyên sizing và chi phí, so với E0. E2 trở đi thay từng thành phần (HMM lọc online, BOCPD, conformal,
  tin AI…), mỗi bước một thay đổi.
- **No Trade** là một quyết định (R8-33): «luôn đứng ngoài» (lãi 0, chi phí 0) là baseline bắt buộc cho E1; giao dịch chỉ
  khi regime rõ, độ tin ≥ τ và lợi thế gross kỳ vọng ≥ k lần chi phí; báo **coverage** (tỷ lệ thời gian có lệnh). Danh mục
  không tìm được nghiên cứu đo trực tiếp giá trị của lớp No Trade ở FX/vàng trong ngày; bằng chứng gián tiếp: 11/14 họ tín
  hiệu của Mesfin có gross dưới chi phí; lợi nhuận quanh giờ fix FX âm khi trừ đủ spread (Krohn, Mueller, Whelan); dưới 1% day
  trader cá nhân có lợi thế bền sau phí (Barber và cộng sự, R8-32).

Khối dưới dựng một E0 / E1 đồ chơi trên D1: chiến lược Trend = TSMOM 60; «router» chỉ cho giao dịch khi efficiency ratio 20
nến (ER: quãng đi thẳng chia tổng quãng đi, 1 = đi thẳng, 0 = đi ngang) vượt ngưỡng, còn lại No Trade.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

CHI_PHI_VONG = {"XAU": 0.42, "EUR": 0.00015}

def ket_qua(d, vi_the, cp_vong, N, tu="2019-01-01"):
    giu = vi_the.shift(1).fillna(0.0)                              # chốt ở close t, giữ từ open t+1
    r = giu * (d["open"].shift(-1) / d["open"] - 1) - giu.diff().abs().fillna(0.0) * (cp_vong / 2) / d["open"]
    m = (d.index >= tu) & r.notna()
    r, g = r[m], giu[m]
    sr = "%5.2f" % (r.mean() / r.std() * np.sqrt(N)) if r.std() > 0 else "  —  "
    return "%+5.1f%%/năm  Sharpe %s  trong thị trường %3.0f%%" % (100 * r.mean() * N, sr, 100 * (g != 0).mean())

for ma, ds in (("XAU", XAU_D1), ("EUR", EUR_D1)):
    d = nap_nen(ds, "2018-01-01", "2024-09-01")
    c = d["close"]
    N = len(d) / ((d.index[-1] - d.index[0]).days / 365.25)
    huong = np.sign(c - c.shift(60))                               # chiến lược Trend: theo chiều 60 nến
    er = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()  # efficiency ratio 20 nến: 1 = đi thẳng, 0 = đi ngang
    print("%s D1 (sau phí, 01/2019 → 08/2024)" % ma)
    print("   đứng ngoài                     :", ket_qua(d, c * 0.0, CHI_PHI_VONG[ma], N))
    print("   mua giữ                        :", ket_qua(d, c * 0 + 1.0, CHI_PHI_VONG[ma], N))
    print("   E0: TSMOM 60 luôn bật          :", ket_qua(d, huong, CHI_PHI_VONG[ma], N))
    for nguong in (0.2, 0.3, 0.4):
        vt = huong.where(er >= nguong, 0.0)                        # «router»: Trend → giao dịch, còn lại → No Trade
        print("   E1: chỉ khi ER ≥ %.1f (Trend)   :" % nguong, ket_qua(d, vt, CHI_PHI_VONG[ma], N))
```

```text
Kết quả khi mình chạy:
XAU D1 (sau phí, 01/2019 → 08/2024)
   đứng ngoài                     :  +0.0%/năm  Sharpe   —    trong thị trường   0%
   mua giữ                        : +13.1%/năm  Sharpe  0.88  trong thị trường 100%
   E0: TSMOM 60 luôn bật          :  +5.3%/năm  Sharpe  0.36  trong thị trường 100%
   E1: chỉ khi ER ≥ 0.2 (Trend)   :  +5.1%/năm  Sharpe  0.47  trong thị trường  49%
   E1: chỉ khi ER ≥ 0.3 (Trend)   :  +2.2%/năm  Sharpe  0.25  trong thị trường  32%
   E1: chỉ khi ER ≥ 0.4 (Trend)   :  +0.6%/năm  Sharpe  0.10  trong thị trường  19%
EUR D1 (sau phí, 01/2019 → 08/2024)
   đứng ngoài                     :  +0.0%/năm  Sharpe   —    trong thị trường   0%
   mua giữ                        :  -0.3%/năm  Sharpe -0.05  trong thị trường 100%
   E0: TSMOM 60 luôn bật          :  -2.7%/năm  Sharpe -0.38  trong thị trường 100%
   E1: chỉ khi ER ≥ 0.2 (Trend)   :  -4.0%/năm  Sharpe -0.78  trong thị trường  48%
   E1: chỉ khi ER ≥ 0.3 (Trend)   :  -2.0%/năm  Sharpe -0.53  trong thị trường  28%
   E1: chỉ khi ER ≥ 0.4 (Trend)   :  -0.8%/năm  Sharpe -0.27  trong thị trường  14%
```

- XAU, ngưỡng 0,2: E1 nhỉnh hơn E0 (Sharpe 0,47 so với 0,36) với một nửa thời gian trong thị trường. Nhưng ngưỡng là tham số
  mới, ở đây đã thử 3 giá trị (snooping, module 7); 0,3 và 0,4 tệ hơn E0; và cả ba thua mua giữ.
- EUR: router không cứu được một chiến lược không có lợi thế. «Đứng ngoài» thắng mọi phương án.
- Kế hoạch Copilot yêu cầu so thêm exposure / turnover: E1 ở thị trường một nửa thời gian thì drawdown và biến động tự nhiên
  nhỏ đi; đừng gán hết phần đó cho khả năng nhận diện regime.

**Vai trò của lab trong router.** Lab là tầng *dưới* router: đo cấu trúc và regime, **không** đo P&L. Phần lab đóng góp:

- Một bản «RegimeEstimate» cho repo giao dịch dùng ở E1: phiên bản, trạng thái, lý do, độ bất định, mốc đoạn phát triển đã
  dùng để chốt ngưỡng ([`nghien_cuu_regime_copilot_va_repo_cu.md`](../research/nghien_cuu_regime_copilot_va_repo_cu.md)
  §2.4). Regime đề xuất hai trục: biến động (nén · bình thường · bung · nhảy) và hướng (Trend ↑ / ↓ · Range)
  ([`plan_bias_regime.md`](../plans/plan_bias_regime.md), module 6).
- Regime được đánh giá **không bằng P&L**: độ bền, độ trễ, độ phủ, tỷ lệ Uncertain, và quan hệ với biên độ / biến động tương
  lai so với null (shift test, baseline «theo giờ» — module 7). Ở module 7, «biến động cao» báo trước biến động tới
  (p = 0,005), còn «trend 64 nến» không báo trước chiều (p = 0,87): trục biến động có bằng chứng, trục hướng phải tự chứng
  minh.
- **Uncertain** và **lỗi dữ liệu** là hai trạng thái riêng ([`AGENTS.md`](../../AGENTS.md) §2.2). Router ánh xạ Uncertain
  thành No Trade, còn lỗi dữ liệu thành *chặn lệnh*; không gộp.
- Ngưỡng τ, k chọn theo P&L thì overfit (rủi ro ghi ở R8-33). Chọn ngưỡng regime trên đoạn phát triển của lab bằng thước đo
  không phải P&L, rồi repo giao dịch đo P&L một lần trên holdout — tách hai bước làm giảm số lần thử trên P&L.

**Bẫy hay gặp.**

- Đánh giá router bằng P&L một giai đoạn (một lần rút). Báo theo năm, theo regime, kèm coverage.
- So E1 có ít exposure hơn với E0 rồi kết luận «nhận diện regime tốt».
- Gộp «không có dữ liệu» vào Range hay Uncertain: router sẽ «đứng ngoài» vì lỗi kỹ thuật và bạn tưởng đó là quyết định.

## Lab đang dùng những điều này ở đâu

Lab không tính P&L; bảng dưới chỉ ra chỗ các khái niệm của module chạm vào lab, và chỗ lab trao đầu vào cho repo giao dịch.

| Khái niệm | File / tài liệu | Ghi chú |
|---|---|---|
| Ranh giới: lab không đo P&L | [`../../AGENTS.md`](../../AGENTS.md) §2.4 | P&L đo ở repo giao dịch (E0 → E1) |
| Nhân quả, nến khung lớn đã chốt | [`../../AGENTS.md`](../../AGENTS.md) §2.1, §9 | D1/H4 mốc 17:00 New York |
| Giá Bid, không volume, không spread | [`../guides/du_lieu_thi_truong.md`](../guides/du_lieu_thi_truong.md) | Chi phí trong module là giả định |
| Donchian, độ dốc SMA trong lab | [`../algorithms/thuat_toan_indicator_baseline.md`](../algorithms/thuat_toan_indicator_baseline.md) | Baseline nhận diện, không phải chiến lược |
| Regime hai trục, thước đo không dùng P&L | [`../plans/plan_bias_regime.md`](../plans/plan_bias_regime.md) | Liên hệ module 6, 7 |
| Router, E0–E1, bài học repo cũ | [`../research/nghien_cuu_regime_copilot_va_repo_cu.md`](../research/nghien_cuu_regime_copilot_va_repo_cu.md) | Trích tài liệu Copilot ngoài repo |
| Bằng chứng chiến lược (R8) | [`../research/danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md), [`../research/khao_sat/danh_muc_quant_2026-10-12.json`](../research/khao_sat/danh_muc_quant_2026-10-12.json) | R8-02, R8-05, R8-31, R8-33 dùng trong bài |
| Đánh giá, chống overfit | [`07_danh_gia_overfit.md`](07_danh_gia_overfit.md) | Cực đại kỳ vọng, PBO, sổ đăng ký |

## Bài tập

**Bài 1 — Chi phí theo giờ.** Với XAU M15 (01/2023 → 08/2024), tính trung vị biên độ nến theo giờ New York và tỷ lệ chi phí
0,42 USD / biên độ. Giờ nào chi phí «nặng» nhất, giờ nào nhẹ nhất? Nhớ rằng spread thật còn giãn đúng ở các giờ vắng.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

cp = 0.42                                                       # giả định chi phí một vòng XAU, USD/oz
d = nap_nen(XAU_M15_DAI, "2023-01-01", "2024-09-01")
gio = d.index.tz_convert("America/New_York").hour
bd = (d["high"] - d["low"]).groupby(gio).median()
bang = pd.DataFrame({"bien_do_USD": bd.round(2), "chi_phi_tren_bien_do_%": (100 * cp / bd).round(1)})
bang.index.name = "giờ NY"
print(bang.T.iloc[:, :12].to_string()); print(bang.T.iloc[:, 12:].to_string())
```

```text
Kết quả khi mình chạy:
giờ NY                     0      1      2      3      4     5      6      7      8      9      10     11
bien_do_USD              1.24   1.64   2.09   2.23   2.04   1.8   1.76   1.91   3.35   4.13   3.89   2.83
chi_phi_tren_bien_do_%  33.90  25.60  20.10  18.80  20.60  23.3  23.90  22.00  12.50  10.20  10.80  14.90
giờ NY                    12     13    14     15     16     18     19    20     21     22     23
bien_do_USD              2.2   2.03   1.6   1.47   0.95   1.15   1.15   1.6   1.91   1.53   1.28
chi_phi_tren_bien_do_%  19.1  20.70  26.2  28.50  44.20  36.50  36.50  26.3  22.00  27.50  32.80
```

Nhẹ nhất 8–10 giờ NY (mở cửa New York, tin Mỹ): chi phí ~10% biên độ. Nặng nhất 16–19 giờ (quanh giờ nghỉ, 17 giờ không có
nến) và 23–0 giờ: 33–44%, đúng lúc spread thật giãn rộng nhất. Cùng một chiến lược, giờ vào lệnh đổi chi phí tương đối gấp
bốn.
</details>

**Bài 2 — Tìm lỗi nhìn tương lai.** Kênh Donchian 20 nến trên XAU D1 (R8-05): close vượt đỉnh 20 nến trước → long, thủng đáy →
short, giữ 5 nến. Viết hai bản: (A) vào ở open nến sau; (B) «khớp» ngay ở mức biên trong nến phá. Bản nào nhìn tương lai, và
nó thổi kết quả lên bao nhiêu?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

d = nap_nen(XAU_D1, "2018-01-01", "2024-09-01")
o, h, l, c = d["open"], d["high"], d["low"], d["close"]
n = 20
tren = h.rolling(n).max().shift(1)                  # đỉnh 20 nến TRƯỚC (không gồm nến hiện tại)
duoi = l.rolling(n).min().shift(1)
pha_len, pha_xuong = c > tren, c < duoi               # biết lúc nến t ĐÓNG

# Bản A (đúng): close phá biên → vào ở open nến sau, giữ đúng 5 nến D1
ra = o.shift(-6)
A = pd.concat([(ra / o.shift(-1) - 1)[pha_len], (1 - ra / o.shift(-1))[pha_xuong]])
# Bản B (lỗi): cũng điều kiện close phá biên, nhưng «khớp» ngay ở mức biên trong nến t
B = pd.concat([(ra / tren - 1)[pha_len], (1 - ra / duoi)[pha_xuong]])
for ten, r in (("A — vào open nến sau", A), ("B — khớp ở mức biên", B)):
    r = r.dropna()
    print("%-22s %d lệnh, TB mỗi lệnh %+.1f bp, thắng %.0f%%" % (ten, len(r), 1e4 * r.mean(), 100 * (r > 0).mean()))
```

```text
Kết quả khi mình chạy:
A — vào open nến sau   217 lệnh, TB mỗi lệnh +1.9 bp, thắng 52%
B — khớp ở mức biên    217 lệnh, TB mỗi lệnh +59.5 bp, thắng 63%
```

B nhìn tương lai: nó dùng close để *biết* giá đã đóng trên biên, rồi lại khớp ở mức biên thấp hơn — ăn không phần (close − biên).
Kết quả thổi từ +1,9 lên +59,5 bp mỗi lệnh. Nếu muốn vào ở mức biên thật, điều kiện phải là *high* chạm biên (lệnh stop
chờ sẵn), và phải xử lý gap mở cửa vượt qua biên. (Ở đây mỗi ngày phá biên tính một lệnh, các lệnh có thể chồng nhau.)
</details>

**Bài 3 — Chia vị thế theo biến động (R8-04).** Nhân vị thế mua giữ và TSMOM 60 với hệ số $0{,}10/\hat\sigma_t$ ($\hat\sigma_t$:
biến động năm ước lượng bằng EWMA 60 nến tới close t, trần đòn bẩy 3). Sharpe thay đổi thế nào ở XAU và EUR?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

CHI_PHI_VONG = {"XAU": 0.42, "EUR": 0.00015}
for ma, ds in (("XAU", XAU_D1), ("EUR", EUR_D1)):
    d = nap_nen(ds, "2018-01-01", "2024-09-01")
    c, o = d["close"], d["open"]
    N = len(d) / ((d.index[-1] - d.index[0]).days / 365.25)
    r_cc = np.log(c).diff()
    vol = r_cc.ewm(span=60).std() * np.sqrt(N)                    # biến động năm ước lượng tới close t (nhân quả)
    he_so = (0.10 / vol).clip(upper=3.0)                          # nhắm 10%/năm, đòn bẩy tối đa 3
    huong = np.sign(c - c.shift(60))
    for ten, vt in (("mua giữ", c * 0 + 1.0), ("mua giữ × vol", he_so), ("TSMOM 60", huong), ("TSMOM 60 × vol", huong * he_so)):
        giu = vt.shift(1).fillna(0.0)
        r = giu * (o.shift(-1) / o - 1) - giu.diff().abs().fillna(0.0) * (CHI_PHI_VONG[ma] / 2) / o
        r = r["2019-01-01":].dropna()
        print("%s %-16s sau phí %+5.1f%%/năm, biến động %4.1f%%, Sharpe %5.2f"
              % (ma, ten, 100 * r.mean() * N, 100 * r.std() * np.sqrt(N), r.mean() / r.std() * np.sqrt(N)))
```

```text
Kết quả khi mình chạy:
XAU mua giữ          sau phí +13.1%/năm, biến động 14.9%, Sharpe  0.88
XAU mua giữ × vol    sau phí +10.2%/năm, biến động 10.5%, Sharpe  0.97
XAU TSMOM 60         sau phí  +5.3%/năm, biến động 14.9%, Sharpe  0.36
XAU TSMOM 60 × vol   sau phí  +5.4%/năm, biến động 10.5%, Sharpe  0.52
EUR mua giữ          sau phí  -0.3%/năm, biến động  7.2%, Sharpe -0.05
EUR mua giữ × vol    sau phí  -1.3%/năm, biến động 10.1%, Sharpe -0.13
EUR TSMOM 60         sau phí  -2.7%/năm, biến động  7.2%, Sharpe -0.38
EUR TSMOM 60 × vol   sau phí  -4.8%/năm, biến động 10.1%, Sharpe -0.48
```

Ở XAU, chia theo biến động nâng Sharpe cả mua giữ lẫn TSMOM: giảm vị thế khi biến động cao (module 4: biến động đoán được)
cắt bớt các đoạn sụt. Ở EUR, biến động thấp nên hệ số > 1 (đòn bẩy), và một chiến lược không có lợi thế bị khuếch đại thành
lỗ to hơn. Vol scaling thay đổi *rủi ro*, không tạo ra hướng. Lần này cũng là thêm một cấu hình vào sổ đăng ký.
</details>

**Bài 4 — Snooping khung giờ.** Thử 12 biến thể breakout trên XAU M15: phiên Á kết thúc lúc 6, 7 hoặc 8 giờ London; cửa sổ
vào dài 2 hoặc 3 giờ; ra lúc 12 hoặc 16 giờ. Xếp theo 2018–2021, xem 2022–08/2024. Có biến thể nào dương trong mẫu không?
Nếu bạn chỉ nhìn 2022–2024 thì sẽ chọn gì?

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def breakout(d, vao_tu, vao_den, gio_ra, cp):
    """Biên phiên Á = 00:00 → vao_tu (giờ London). Nến đầu tiên trong [vao_tu, vao_den) ĐÓNG ngoài biên → vào open nến
    sau; thoát ở open nến đầu tiên từ gio_ra. Trả lãi/lỗ sau phí từng lệnh (bp), index = ngày London."""
    t = d.index.tz_convert("Europe/London")
    x = d.assign(ngay=t.date, gio=t.hour + t.minute / 60, vt=np.arange(len(d)))
    a = x[x.gio < vao_tu].groupby("ngay").agg(hi=("high", "max"), lo=("low", "min"), n=("high", "size"))
    w = x[(x.gio >= vao_tu) & (x.gio < vao_den)].join(a[a.n >= 0.7 * 4 * vao_tu], on="ngay", how="inner")
    w["chieu"] = np.where(w.close > w.hi, 1, np.where(w.close < w.lo, -1, 0))
    L = w[w.chieu != 0].groupby("ngay").first()
    L = L.join(x[x.gio >= gio_ra].groupby("ngay")["open"].first().rename("ra"), how="inner")
    L = L[L.vt + 1 < len(d)]
    L = L[np.asarray(t.date)[L.vt + 1] == L.index.to_numpy()]          # nến vào lệnh phải cùng ngày
    vao = d["open"].to_numpy()[L.vt + 1]
    return pd.Series(1e4 * (L.chieu * (L.ra - vao) - cp) / vao, index=pd.to_datetime(L.index))

d = nap_nen(XAU_M15_DAI, "2018-01-01", "2024-09-01")
bang, t_stat = {}, lambda s: s.mean() / s.std() * np.sqrt(len(s))
for vao_tu in (6, 7, 8):
    for vao_den in (vao_tu + 2, vao_tu + 3):
        for gio_ra in (12, 16):
            r = breakout(d, vao_tu, vao_den, gio_ra, 0.42)
            a, b = r[:"2021-12-31"], r["2022-01-01":]
            bang["%d–%d → %d" % (vao_tu, vao_den, gio_ra)] = dict(TB_2018_21=a.mean(), t_2018_21=t_stat(a),
                                                                  TB_2022_24=b.mean(), t_2022_24=t_stat(b))
bang = pd.DataFrame(bang).T.sort_values("TB_2018_21", ascending=False)
print("XAU, 12 biến thể (giờ London: vào từ–đến → ra lúc), lãi/lỗ sau phí, bp mỗi lệnh")
print(bang.round(2).to_string())
```

```text
Kết quả khi mình chạy:
XAU, 12 biến thể (giờ London: vào từ–đến → ra lúc), lãi/lỗ sau phí, bp mỗi lệnh
           TB_2018_21  t_2018_21  TB_2022_24  t_2022_24
6–8 → 16        -1.15      -0.44        1.03       0.31
8–11 → 16       -1.21      -0.50       -2.60      -0.84
6–9 → 16        -1.41      -0.61        3.67       1.25
8–10 → 16       -1.84      -0.69       -0.22      -0.07
7–10 → 16       -2.19      -0.92        2.63       0.91
6–9 → 12        -3.04      -2.64       -1.79      -1.24
6–8 → 12        -3.22      -2.43       -2.65      -1.55
8–11 → 12       -3.27      -2.74       -2.70      -2.15
7–9 → 16        -3.29      -1.30        1.88       0.59
7–10 → 12       -3.69      -3.47       -1.93      -1.45
7–9 → 12        -3.91      -3.29       -1.40      -0.93
8–10 → 12       -4.20      -3.64       -2.78      -2.00
```

Cả 12 biến thể đều âm sau phí ở 2018–2021: người làm đúng quy trình dừng ở đây (No Trade). Nếu chỉ nhìn 2022–2024, bạn sẽ
chọn «6–9 → 16» với +3,67 bp (t = 1,25) — đúng biến thể đã lỗ −1,41 bp ở bốn năm trước. Mười hai biến thể là mười hai dòng
trong sổ đăng ký; t lớn nhất 1,25 trong 12 lần thử không phải bằng chứng.
</details>

## Tự kiểm

1. Tín hiệu chốt ở close D1 hôm nay, backtest nhân với lợi suất close hôm qua → close hôm nay. Sai ở đâu?
<details><summary>Đáp án</summary>

Lợi suất đó kết thúc đúng ở giá tạo ra tín hiệu: backtest «biết» close hôm nay trước khi
vào lệnh. Ở mục 1, lỗi này biến 0%/năm thành +40%/năm. Phải dùng lợi suất bắt đầu sau lúc quyết định (open nến sau).

</details>

2. Chi phí một vòng XAU 0,42 USD, biên độ trung vị một nến M15 là 2,25 USD. Tỷ lệ chi phí / biên độ là bao nhiêu, và nghĩa là gì?
<details><summary>Đáp án</summary>

Khoảng 19%: mỗi vòng giao dịch mất gần một phần năm biên độ của một nến trung vị. Một luật
M15 phải có lợi thế gross lớn hơn mức đó một cách đều đặn — trong khi chiều giá ngắn hạn gần như không đoán được.

</details>

3. Vì sao không năm hoá Sharpe của vàng D1 bằng √365?
<details><summary>Đáp án</summary>

Dữ liệu chỉ có ~258 nến D1 mỗi năm (nghỉ cuối tuần). Nhân √365 coi như có 365 lần lấy
mẫu độc lập, thổi Sharpe lên khoảng 19% (0,88 thành 1,04). Luôn đếm số nến mỗi năm của chính dữ liệu.

</details>

4. TSMOM 60 trên XAU D1 có Sharpe 0,36 sau phí, mua giữ có 0,88. Bạn kết luận gì?
<details><summary>Đáp án</summary>

Trên giai đoạn này, luật trend không thêm gì so với mua giữ; cả hai số đều có sai số chuẩn
~0,43–0,5 nên chênh lệch cũng chưa chắc. Bằng chứng TSMOM trong tài liệu đến từ danh mục nhiều thị trường, khung tháng — không
chuyển thẳng sang một mã D1.

</details>

5. London breakout XAU: trước phí +2,28 bp/lệnh (t = 1,25), chi phí 2,54 bp. Có lợi thế không?
<details><summary>Đáp án</summary>

Không. Trước phí t = 1,25 chưa phân biệt được với may; sau phí trung bình âm. Đây đúng là
mẫu «edge gross nhỏ hơn chi phí» mà R8-31 thấy ở 11/14 họ tín hiệu trong ngày.

</details>

6. Lưới 50 lookback, tốt nhất 2019–2021 có Sharpe 0,87. Có nên tin?
<details><summary>Đáp án</summary>

Không. Với ~3 năm, sai số chuẩn Sharpe ≈ 0,58; cực đại kỳ vọng do may của 10 cấu hình độc
lập đã là 0,91, của 50 là 1,31. Ngoài mẫu cấu hình đó còn 0,32, ngang trung vị cả lưới.

</details>

7. E1 (TSMOM 60 chỉ khi ER ≥ 0,2) có Sharpe 0,47, E0 có 0,36. Đủ để nói router có giá trị chưa?
<details><summary>Đáp án</summary>

Chưa. Ngưỡng được chọn trong 3 giá trị đã xem (snooping); 0,3 và 0,4 tệ hơn E0; E1 chỉ ở
thị trường 49% thời gian nên rủi ro tự giảm; mua giữ (0,88) và đứng ngoài vẫn phải là mốc. Cần ngưỡng chốt trước (tốt nhất
bằng thước đo không phải P&L trên đoạn phát triển) và kiểm tra ngoài mẫu một lần.

</details>

8. Lab đóng góp gì cho router, và không làm gì?
<details><summary>Đáp án</summary>

Lab cung cấp trạng thái regime có phiên bản, lý do, độ bất định, được đánh giá bằng độ bền,
độ trễ, độ phủ và quan hệ với kết cục tương lai so với null; tách Uncertain khỏi lỗi dữ liệu. Lab không đo P&L, không chọn
chiến lược; P&L đo ở repo giao dịch qua E0 → E1, cùng chi phí và cách khớp.

</details>

## Đọc thêm

- Larry Harris, *Trading and Exchanges*: spread, thanh khoản, người tham gia thị trường — vì sao chi phí tồn tại và thay đổi
  theo giờ.
- David Aronson, *Evidence-Based Technical Analysis*: kiểm định luật kỹ thuật có chi phí và có điều chỉnh đào dữ liệu.
- Bài gốc: Moskowitz, Ooi, Pedersen (2012), *Time series momentum*; Hurst, Ooi, Pedersen (2017), *A Century of Evidence on
  Trend-Following Investing*; Szakmary, Shen, Sharma (2010); Lo (2002), *The Statistics of Sharpe Ratios*; Bailey & López de
  Prado (2014), *The Deflated Sharpe Ratio*; Mesfin (2026), arXiv 2605.04004.
- Tài liệu Copilot (ngoài repo): `D:\Finance_System\AI_Trading_Copilot_Luong_He_Thong.md` §4 (router),
  `D:\Finance_System\AI_Trading_Copilot_Ke_Hoach_Update_Va_Tich_Hop_Research.md` §7 (chuỗi E0–E6).
- Danh mục quant ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md), nhóm R8): R8-01 TSMOM,
  R8-02 trend-following một thế kỷ, R8-04 phản biện TSMOM / vol scaling, R8-05 Donchian, R8-06 luật MA trên FX suy giảm,
  R8-13 ORB, R8-14 London breakout, R8-19 giờ fix FX, R8-31 Mesfin, R8-32 day trading cá nhân, R8-33 No Trade, R8-34 bộ lọc
  thời gian.
