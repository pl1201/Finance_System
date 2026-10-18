# Module 1 — Dữ liệu giá

> **Sau module này bạn làm được:**
> - nói đúng một nến của lab chứa gì, biết đủ lúc nào, theo giá nào (Bid, không có volume);
> - đổi giờ UTC ↔ New York ↔ London, xác định ngày giao dịch (mốc 17:00 New York) và thấy đổi giờ mùa hè dời phiên ra sao;
> - phân loại khoảng trống giữa hai nến bằng lịch phiên khai báo, và nhận ra một bộ dữ liệu lệch giờ;
> - tính lợi suất đơn giản và lợi suất log, biết khi nào dùng cái nào;
> - tự gộp M15 → H1 / H4 khớp từng nến với dataset của lab, tự cài True Range và ATR Wilder khớp với ATR của lab.
>
> **Cần trước:** Python cơ bản, đọc được bảng pandas  ·  **Thời lượng:** ~5 giờ

> **Ba điều cần nhớ** (đọc lại khi ôn)
>
> 1. Nến của lab là giá **Bid**, volume luôn bằng 0; «một ngày giao dịch» bắt đầu 17:00 New York, và giờ UTC của các phiên dịch 1 tiếng khi đổi giờ mùa hè.
> 2. Khoảng trống phải phân loại theo lịch phiên: 172 khoảng trống trong 8 tháng 2024 chỉ có 1 là thiếu dữ liệu thật. Không bao giờ tự lấp nến.
> 3. Lợi suất log cộng được qua thời gian; ATR lệch mạnh theo giờ (giờ sôi động gấp 3,7 lần giờ vắng).

## Vì sao cần

Mọi con số lab đưa ra — 172 khoảng trống trong 8 tháng XAUUSD M15, ngưỡng «lấy» thanh khoản 0.1·ATR, order flow đổi chiều
0.72–0.82 lần mỗi ngày giao dịch — đều dựa trên ba quyết định về dữ liệu: một nến là gì, giờ nào là «một ngày», khoảng trống nào
là bình thường. Lab đã trả giá thật ở chỗ này: bộ XAUUSD 2024 đầu tiên lệch 1 giờ trong ba tuần tháng 3, và 30 run cũ chạy trên
bộ đó. Module này cho bạn tự kiểm từng điều bằng chính dữ liệu của lab, trước khi tin bất kỳ thống kê nào ở các module sau.

## 1. Một nến chứa gì: OHLC, nến đã đóng, giá Bid, volume = 0

**Trực giác.** Một nến M15 tóm tắt 15 phút giao dịch bằng 4 con số. Bốn con số giữ được biên độ và hướng, nhưng bỏ mất nhiều thứ:
high đến trước hay low đến trước, giá đi qua mỗi mức bao nhiêu lần, bao nhiêu người giao dịch.

**Định nghĩa.**
- **OHLC (open, high, low, close)**: giá đầu, cao nhất, thấp nhất, cuối của khoảng thời gian. Luôn phải có
  $L \le \min(O, C)$ và $\max(O, C) \le H$.
- `bar_time` của lab là **giờ mở nến**, theo UTC. Nến M15 mở 23:00 thì đóng lúc 23:15 (`close_time` trong
  [`core/types.py`](../../core/types.py)). **Nến đã đóng (closed bar)**: chỉ dùng OHLC của nến khi đồng hồ đã qua `close_time`.
  Mọi thuật toán của lab gắn `confirmed_at` = `close_time` của nến đang xử lý.
- **Giá Bid**: giá người mua sẵn sàng trả, tức giá bạn **bán** được. Giá bạn **mua** được là **giá Ask** = Bid + **spread
  (chênh lệch mua–bán)**. Dữ liệu lab chỉ có Bid, nên không có spread.
- **Volume**: HistData (nguồn của lab) không cung cấp, cột `volume` luôn bằng 0. MT5 có **tick volume** = số lần giá thay đổi
  trong nến, không phải số hợp đồng; vàng giao ngay không có sàn tập trung nên không có volume «thật».

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
print(df.head(4))
print("Số nến:", len(df))
print("volume: nhỏ nhất", df.volume.min(), "· lớn nhất", df.volume.max())

# OHLC hợp lệ: low ≤ min(open, close) và max(open, close) ≤ high
hop_le = (df.low <= df[["open", "close"]].min(axis=1)) & (df[["open", "close"]].max(axis=1) <= df.high)
print("Nến vi phạm quan hệ OHLC:", (~hop_le).sum())

ds = danh_sach_dataset()
print(ds[ds.id.isin([XAU_M15, XAU_H1, EUR_M15_DAI])][["id", "ma", "khung", "loai_gia", "so_nen"]].to_string(index=False))

# Nến đã đóng: nến mở lúc t chỉ biết đủ OHLC lúc t + 15 phút
t_mo = df.index[0]
print("Nến đầu mở", t_mo, "→ biết close lúc", t_mo + pd.Timedelta(minutes=15))
```

```text
Kết quả khi mình chạy:
                           idx      open      high       low     close  volume
bar_time
2024-01-01 23:00:00+00:00    0  2062.598  2066.595  2062.405  2065.734     0.0
2024-01-01 23:15:00+00:00    1  2065.715  2066.075  2065.045  2065.075     0.0
2024-01-01 23:30:00+00:00    2  2065.155  2065.405  2064.155  2064.465     0.0
2024-01-01 23:45:00+00:00    3  2064.425  2064.435  2063.105  2063.615     0.0
Số nến: 15850
volume: nhỏ nhất 0.0 · lớn nhất 0.0
Nến vi phạm quan hệ OHLC: 0
             id     ma khung loai_gia  so_nen
ds_a9a2a5e4cef5 EURUSD   M15      bid  199296
ds_83abaa3c6eab XAUUSD    H1      bid   47386
ds_db1583cd4dde XAUUSD   M15      bid   23717
Nến đầu mở 2024-01-01 23:00:00+00:00 → biết close lúc 2024-01-01 23:15:00+00:00
```

Bạn tự thấy: volume bằng 0 ở **mọi** nến; mọi dataset là giá Bid; nến đầu của năm 2024 mở lúc 23:00 UTC ngày 01/01 (mục 2 giải
thích vì sao không phải 00:00). `so_nen` 23 717 là cả năm 2024; hàm trợ giúp chỉ trả 15 850 nến vì bị chặn ở 01/09/2024.

**Bẫy hay gặp.**
- **Dùng nến đang hình thành.** Trên MT5, `copy_rates_from_pos(..., start_pos=0, ...)` trả nến số 0 là nến **chưa đóng**; lab bỏ
  nến đó mặc định ([`mt5_va_tong_hop_nen.md`](../guides/mt5_va_tong_hop_nen.md) §1). Thống kê dùng close chưa đóng là nhìn tương lai.
- **Thứ tự trong nến.** Một nến M15 vừa quét đỉnh vừa đóng ngược: OHLC không cho biết đỉnh bị quét trước hay đáy tạo trước.
  Muốn biết phải xuống M1 (lab có `XAU_M1` cho 2024).
- **Bid và thanh khoản phía trên.** Stop bán (SSL) khớp theo Bid — đúng giá trên chart. Stop mua (BSL) khớp theo **Ask** = Bid +
  spread, nên trên chart Bid một đỉnh «chưa bị lấy» có thể đã bị lấy trên Ask. Ngưỡng «lấy» của lab là xuyên ≥ 0.1·ATR, khoảng
  0.26 USD ở ATR trung vị (mục 7) — cùng cỡ spread vàng ở nhiều broker bán lẻ (xem cột spread trên MT5 của bạn). Sweep BSL vì thế
  nhạy với spread hơn sweep SSL; dữ liệu lab không đo được điều này.
- **Volume.** Chỉ báo cần volume (VWAP, volume profile) không chạy được trên dữ liệu này. Tick volume là đại lượng khác, đừng gọi
  là volume.

## 2. Giờ: UTC, New York, «một ngày» và đổi giờ mùa hè

**Trực giác.** Cùng một nến có ba nhãn giờ tuỳ bạn đứng ở đâu. Nến đầu của 2024 mở 23:00 UTC ngày 01/01, tức 18:00 New York ngày
01/01 — nhưng nó thuộc **ngày giao dịch 02/01**. Hỏi «hôm nay giá tăng bao nhiêu» thì phải chọn một cách cắt ngày.

**Định nghĩa.**
- **UTC** là giờ lưu trong lab. **Giờ New York (America/New_York)** = UTC−5 mùa đông (EST), UTC−4 mùa hè (EDT). **Giờ London** =
  UTC+0 (GMT) mùa đông, UTC+1 (BST) mùa hè.
- **Ngày giao dịch (trading day)** của dữ liệu lab bắt đầu **17:00 New York**, kết thúc 17:00 New York hôm sau. XAUUSD theo lịch
  CME Globex kim loại: phiên mở 18:00 New York, nghỉ hằng ngày 17:00–18:00 New York. Cách tính: lấy giờ New York, cộng 7 giờ (để
  17:00 thành 00:00), rồi lấy phần ngày.
- **Đổi giờ mùa hè (daylight saving time, DST).** Mỹ: từ Chủ nhật thứ hai tháng 3 (10/03/2024) tới Chủ nhật đầu tháng 11. Anh và
  châu Âu: từ Chủ nhật cuối tháng 3 (31/03/2024) tới Chủ nhật cuối tháng 10. Mấy tuần ở giữa là **tuần lệch lịch** (năm 2024:
  10–30/03 và 27/10–02/11).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
t = df.index[0]
print("Nến đầu: UTC", t, "· New York", t.tz_convert("America/New_York"), "· London", t.tz_convert("Europe/London"))
# Ngày giao dịch bắt đầu 17:00 New York: cộng 7 giờ vào giờ NY rồi lấy phần ngày
ngay_gd = (df.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)).date
print("Ngày giao dịch của nến đầu:", ngay_gd[0], "· số ngày lịch UTC có nến:", len(set(df.index.date)),
      "· số ngày giao dịch:", len(set(ngay_gd)))
d1 = nap_nen(XAU_D1, "2024-01-01", "2024-01-02")
print("Nến D1 đầu: mốc", d1.index[0].tz_convert("America/New_York"), "giờ New York · open", d1.open.iloc[0])

# Đổi giờ mùa hè: nến mở tuần (nến đầu sau khoảng trống > 40 giờ) theo ba múi giờ
s = df.loc["2024-02-25":"2024-04-15"].index.to_series()
mo_tuan = s[s.diff() > pd.Timedelta(hours=40)]
print(pd.DataFrame({"mở tuần (UTC)": mo_tuan.dt.strftime("%a %d/%m %H:%M"),
                    "New York": mo_tuan.dt.tz_convert("America/New_York").dt.strftime("%H:%M"),
                    "London": mo_tuan.dt.tz_convert("Europe/London").dt.strftime("%H:%M")}).to_string(index=False))
# 08:00 London và 09:30 New York là mấy giờ UTC?
for ngay in ["2024-03-04", "2024-03-11", "2024-04-01"]:
    lon = pd.Timestamp(ngay + " 08:00", tz="Europe/London").tz_convert("UTC")
    ny = pd.Timestamp(ngay + " 09:30", tz="America/New_York").tz_convert("UTC")
    print(ngay, "· London 08:00 =", lon.strftime("%H:%M"), "UTC · NY 09:30 =", ny.strftime("%H:%M"), "UTC · cách", ny - lon)
```

```text
Kết quả khi mình chạy:
Nến đầu: UTC 2024-01-01 23:00:00+00:00 · New York 2024-01-01 18:00:00-05:00 · London 2024-01-01 23:00:00+00:00
Ngày giao dịch của nến đầu: 2024-01-02 · số ngày lịch UTC có nến: 208 · số ngày giao dịch: 173
Nến D1 đầu: mốc 2024-01-01 17:00:00-05:00 giờ New York · open 2062.598
  mở tuần (UTC) New York London
Sun 03/03 23:00    18:00  23:00
Sun 10/03 22:00    18:00  22:00
Sun 17/03 22:00    18:00  22:00
Sun 24/03 22:00    18:00  22:00
Sun 31/03 22:00    18:00  23:00
Sun 07/04 22:00    18:00  23:00
Sun 14/04 22:00    18:00  23:00
2024-03-04 · London 08:00 = 08:00 UTC · NY 09:30 = 14:30 UTC · cách 0 days 06:30:00
2024-03-11 · London 08:00 = 08:00 UTC · NY 09:30 = 13:30 UTC · cách 0 days 05:30:00
2024-04-01 · London 08:00 = 07:00 UTC · NY 09:30 = 13:30 UTC · cách 0 days 06:30:00
```

01/01/2024 là ngày lễ, CME đóng cả ngày; phiên đầu năm mở 18:00 New York tối 01/01 và thuộc ngày giao dịch 02/01. Nến D1 của lab
ghi mốc 17:00 New York (đầu ngày giao dịch theo danh nghĩa) nhưng open 2062.598 chính là open của nến M15 23:00 UTC — giao dịch
thật bắt đầu một giờ sau mốc. 173 ngày giao dịch trải trên 208 ngày lịch UTC, vì phiên tối Chủ nhật và phần sau 00:00 UTC của
mỗi phiên rơi vào ngày UTC khác.

Đổi giờ mùa hè (bảng thứ hai): theo giờ New York tuần nào cũng mở 18:00. Theo UTC, giờ mở tuần nhảy từ 23:00 sang 22:00 đúng
ngày 10/03. Theo giờ London, ba tuần 10–30/03 mở lúc 22:00 thay vì 23:00, và trong ba tuần đó London với New York chỉ cách nhau 5
giờ 30 thay vì 6 giờ 30.
Killzone của lab ([`core/components/killzone.py`](../../core/components/killzone.py), mặc định
`asia=20-24, london=2-5, ny_am=7-10, london_close=10-12`) tính theo **giờ New York**: «london = 2–5 giờ NY» là 07:00–10:00 London
quanh năm, trừ ba tuần lệch lịch là 06:00–09:00 London.

**Bẫy hay gặp.**
- **Mốc UTC cố định cho phiên** («London mở 08:00 UTC», «New York mở 13:30 UTC») chỉ đúng một phần năm. Lab tính phiên và
  killzone theo giờ New York có đổi giờ (AGENTS.md §9).
- **«Ngày» của bạn không phải ngày của dữ liệu.** Nghiên cứu order flow từng đếm «lần lật mỗi ngày» theo ngày UTC; một ngày giao
  dịch ≈ 1.20 ngày UTC có nến, nên các số «/ngày» phải tính lại
  ([`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) §5.1, §8.4).
- **Gắn múi giờ hai lần.** Index của `nap_nen` đã là UTC có múi giờ: đổi bằng `tz_convert`, đừng `tz_localize` lại.

## 3. Phiên, cuối tuần và khoảng trống theo lịch phiên

**Trực giác.** Chart M15 trông liền mạch, nhưng giữa hai nến cạnh nhau có thể là 15 phút, 1 giờ 15, hai ngày hay ba ngày. Có
khoảng trống bình thường (thị trường đóng cửa), có khoảng trống là lỗi (thiếu dữ liệu). Không có lịch thì không phân biệt được.

**Định nghĩa.**
- **Khoảng trống (gap)** giữa nến $t-1$ và $t$: khi $\text{bar\_time}_t - \text{bar\_time}_{t-1}$ khác đúng một bước khung.
  (Khác «gap giá» — open nến sau cách close nến trước.)
- **Lịch phiên khai báo (session calendar)**: giờ mở / đóng của từng phiên, kể cả ngày lễ và đóng sớm, lấy từ nguồn ngoài (CME),
  **không suy từ dữ liệu** (AGENTS.md §2.2). Lab giữ bản sao ở `data/calendars/`, đọc bằng
  [`core/data/session_calendar.py`](../../core/data/session_calendar.py).
- `classify_gap` xét từng ô 15 phút bị thiếu: mọi ô đều ngoài phiên → `nghi_phien` (nghỉ hằng ngày), `cuoi_tuan` hoặc `nghi_le`;
  có ít nhất một ô **trong** phiên → `thieu_trong_phien` (thiếu dữ liệu, bất thường). Bộ phân loại của `ict_structure` thêm
  `lech_buoc`, `ngoai_lich`, `khong_ro_lich` ([`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §4.2).

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from datetime import timedelta
from core.data.session_calendar import SessionCalendar

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
lich = SessionCalendar.load("cme_globex_metals")          # lịch khai báo của XAUUSD
buoc = timedelta(minutes=15)
t = df.index.to_pydatetime()
dong = []
for a, b in zip(t[:-1], t[1:]):
    if b - a != buoc:                                       # hai nến không liền nhau → có khoảng trống
        loai, o_trong_phien = lich.classify_gap(a + buoc, b, buoc)
        dong.append({"nen_truoc": a.strftime("%a %d/%m %H:%M"), "nen_sau": b.strftime("%a %d/%m %H:%M"),
                     "gio": (b - a).total_seconds() / 3600, "loai": loai, "o_trong_phien": o_trong_phien})
kt = pd.DataFrame(dong)
print(kt.groupby("loai").gio.agg(["size", "min", "max"]))
print(kt[kt.loai.isin(["nghi_le", "thieu_trong_phien"])].to_string(index=False))

# Nghỉ hằng ngày: giờ UTC của nến cuối trước nghỉ → nến đầu sau nghỉ
nghi = kt[kt.loai == "nghi_phien"]
print(nghi.groupby([nghi.nen_truoc.str[-5:], nghi.nen_sau.str[-5:]]).size())

# Lab phân loại y như vậy: sự kiện ICT_GAP của ict_structure
ev = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["su_kien"]
print(pd.Series([d["loai"] for d in ev[ev.structure_type == "ICT_GAP"].details]).value_counts().to_dict())
```

```text
Kết quả khi mình chạy:
                   size    min    max
loai
cuoi_tuan            32  48.25  49.25
nghi_le               6   3.75  73.25
nghi_phien          133   1.25   1.25
thieu_trong_phien     1  53.25  53.25
      nen_truoc         nen_sau   gio              loai  o_trong_phien
Fri 12/01 17:45 Sun 14/01 23:00 53.25 thieu_trong_phien             16
Mon 15/01 19:15 Mon 15/01 23:00  3.75           nghi_le              0
Mon 19/02 19:15 Mon 19/02 23:00  3.75           nghi_le              0
Thu 28/03 20:45 Sun 31/03 22:00 73.25           nghi_le              0
Mon 27/05 18:15 Mon 27/05 22:00  3.75           nghi_le              0
Wed 19/06 18:15 Wed 19/06 22:00  3.75           nghi_le              0
Thu 04/07 18:15 Thu 04/07 22:00  3.75           nghi_le              0
nen_truoc  nen_sau
20:45      22:00      96
21:45      23:00      37
dtype: int64
{'nghi_phien': 133, 'cuoi_tuan': 32, 'nghi_le': 6, 'thieu_trong_phien': 1}
```

Đọc kết quả:
- **133 lần nghỉ hằng ngày**, luôn 1.25 giờ: nến cuối mở 21:45 UTC, nến sau 23:00 UTC vào mùa đông (37 lần); 20:45 → 22:00 UTC
  vào mùa hè (96 lần). Theo giờ New York luôn là 16:45 → 18:00 — đúng con số trong AGENTS.md §9.
- **32 cuối tuần** dài 48.25–49.25 giờ (tuần 10/03 ngắn hơn một giờ vì Mỹ đổi giờ trong lúc nghỉ).
- **6 ngày lễ**: năm lần đóng sớm 14:30 New York (MLK, Presidents' Day, Memorial Day, Juneteenth, 04/07 — nến cuối mở 14:15 New
  York) và Good Friday (73.25 giờ, từ thứ Năm tới Chủ nhật).
- **1 khoảng thiếu dữ liệu thật**: thứ Sáu 12/01, 16 ô trong phiên (13:00–17:00 New York) không có nến. Tài liệu của pipeline
  dữ liệu ghi đúng chỗ này là chỗ nguồn bị mất.
- Bộ đếm `ICT_GAP` của `ict_structure` ra **đúng các con số đó**: bạn vừa cài lại tầng [G] của lab.

Chính sách của lab (D1, §4.2 đặc tả): **giữ** mức swing, dealing range, vùng thanh khoản qua mọi khoảng trống; **chặn** cửa sổ
pivot, bộ ba nến FVG, displacement ở nến đầu sau khoảng trống, và cửa sổ sweep / shift vắt qua khoảng trống. Không tự lấp nến.

**Bẫy hay gặp.**
- **Lấp nến giả** (lặp close cũ, `ffill`) để chuỗi «đều»: tạo nến phẳng, kéo ATR xuống, sinh swing giả. AGENTS.md §2.2 cấm.
- **Đếm «N nến» vắt qua cuối tuần.** «Ba nến sau sweep» có thể là 20:30 thứ Sáu tới 22:15 Chủ nhật — vì vậy các cửa sổ ngắn của
  lab bị chặn khi có khoảng trống.
- **Suy lịch từ dữ liệu.** Nguồn thiếu bốn giờ thì «lịch» suy ra cũng thiếu bốn giờ, và bạn không bao giờ thấy lỗi.

## 4. Dữ liệu xấu: bài học từ bộ «LỆCH GIỜ»

**Trực giác.** Dữ liệu sai giờ một tiếng trông hoàn toàn bình thường: giá đúng, nến đẹp. Chỉ khi so với một thứ **độc lập** —
lịch phiên, một nguồn giá khác — lỗi mới lộ ra.

**Chuyện gì đã xảy ra.** Trang HistData ghi giờ là «EST, không đổi giờ mùa hè». Thực tế: tới hết 2018 giờ gốc bám giờ New York; từ
2019 là giờ server châu Âu − 7 giờ. Bộ XAUUSD 2024 đầu tiên của lab quy đổi theo giờ New York, nên trong các tuần lệch lịch mọi
nến bị **sớm 1 giờ**. Repo `market-data-pipeline` phát hiện và kiểm bằng ba nguồn độc lập (Dukascopy, broker FXCM, vàng COMEX).
Bộ cũ vẫn nằm trong DB với tên bắt đầu bằng `[LỆCH GIỜ — dùng …]`, chỉ để mở 30 run cũ
([`du_lieu_thi_truong.md`](../guides/du_lieu_thi_truong.md) §1, AGENTS.md §9). Ta mở nó ra **chỉ để xem lỗi**:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from datetime import timedelta
from core.data.session_calendar import SessionCalendar

LECH_GIO = "ds_564bff443e42"   # bộ M15 2024 CŨ — chỉ mở ra để xem lỗi, không dùng để phân tích
lich = SessionCalendar.load("cme_globex_metals")
buoc = timedelta(minutes=15)
moi = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
cu = nap_nen(LECH_GIO, "2024-01-01", "2024-09-01")
for ten, df in [("đúng giờ", moi), ("LỆCH GIỜ", cu)]:
    t = df.index.to_pydatetime()
    ngoai = sum(not lich.is_open(x) for x in t)
    thieu = sum(lich.classify_gap(a + buoc, b, buoc)[0] == "thieu_trong_phien"
                for a, b in zip(t[:-1], t[1:]) if b - a != buoc)
    mo = df.loc["2024-03-10"].index[0].tz_convert("America/New_York").strftime("%H:%M")
    print("%-9s %d nến · mở tuần 10/03 lúc %s NY · %2d nến NGOÀI giờ mở cửa · %2d khoảng «thiếu trong phiên»"
          % (ten, len(df), mo, ngoai, thieu))

# So từng mốc giờ chung, rồi dời bộ cũ +1 giờ trong 10–30/03 và so lại
gia = ["open", "high", "low", "close"]
j = moi.join(cu[gia], rsuffix="_cu", how="inner")
khac = (j[gia].values != j[[c + "_cu" for c in gia]].values).any(axis=1)
print("Mốc chung:", len(j), "· khác:", khac.sum(), "· từ", j.index[khac].min(), "đến", j.index[khac].max())
cu2 = cu.copy()
cu2.index = cu.index.where(~((cu.index >= "2024-03-10") & (cu.index < "2024-03-31")), cu.index + pd.Timedelta(hours=1))
j2 = moi.join(cu2[gia], rsuffix="_cu", how="inner")
print("Sau khi dời +1 giờ: mốc chung", len(j2), "· khác:", (j2[gia].values != j2[[c + "_cu" for c in gia]].values).any(axis=1).sum(),
      "· mốc chỉ bộ mới có:", [x.strftime("%d/%m %H:%M") for x in moi.index.difference(cu2.index)])
```

```text
Kết quả khi mình chạy:
đúng giờ  15850 nến · mở tuần 10/03 lúc 18:00 NY ·  0 nến NGOÀI giờ mở cửa ·  1 khoảng «thiếu trong phiên»
LỆCH GIỜ  15846 nến · mở tuần 10/03 lúc 17:00 NY · 56 nến NGOÀI giờ mở cửa · 16 khoảng «thiếu trong phiên»
Mốc chung: 15790 · khác: 1232 · từ 2024-03-10 22:00:00+00:00 đến 2024-03-28 19:45:00+00:00
Sau khi dời +1 giờ: mốc chung 15846 · khác: 0 · mốc chỉ bộ mới có: ['31/03 23:00', '31/03 23:15', '31/03 23:30', '31/03 23:45']
```

Bộ cũ mở tuần 10/03 lúc **17:00 New York**, giờ CME còn đóng cửa. Lịch phiên bắt được ngay: 14 phiên trong ba tuần lệch lịch đều
mở sớm một giờ (4 nến lúc 17:00–17:45 New York: 14 × 4 = 56 nến ngoài giờ mở cửa) và đóng sớm một giờ (4 ô cuối phiên trống: 14
khoảng «thiếu trong phiên»; cộng khoảng 12/01 có thật và 60 phút ngày 31/03 là 16). Giá thì đúng hệt: dời +1 giờ là khớp toàn bộ
15 846 nến. Bốn nến 31/03 23:00–23:45 UTC chỉ bộ mới có — 60 phút M1 mất ở nguồn, được lấp từ Dukascopy cùng luồng giá (ghi
trong `notes` của dataset).

Nếu dùng bộ cũ, trong ba tuần đó mọi thứ **tính theo giờ** sai một giờ: killzone, ngày giao dịch, nến H4 / D1 mốc 17:00 New York,
PDH/PDL, mùa vụ biến động trong ngày. Không một nến nào «trông» sai — mà phần lớn ICT tính theo giờ.

**Danh sách kiểm một bộ dữ liệu mới** (đều chạy được bằng code trong module này):
1. OHLC hợp lệ, không NaN, timestamp tăng dần, không trùng, đúng bước khung (mục 1).
2. Không nến nào ngoài phiên theo lịch; liệt kê mọi khoảng `thieu_trong_phien` (mục 3, 4).
3. Nến mở tuần theo giờ New York luôn 18:00 (XAUUSD) / 17:00 (EURUSD), cả trước lẫn sau ngày đổi giờ (mục 2).
4. Gộp lên khung lớn và so với một bộ độc lập (mục 6; pipeline so D1 với broker FXCM).

## 5. Lợi suất: đơn giản và log

**Trực giác.** Giá tăng 5% rồi giảm 5% không về chỗ cũ. Có hai cách đo «tăng bao nhiêu», và chỉ một cách cộng được qua nhiều nến.

**Định nghĩa.** Với $P_t$ là close của nến $t$:
- **Lợi suất đơn giản (simple return)** $R_t = P_t / P_{t-1} - 1$ — phần trăm thay đổi.
- **Lợi suất log (log return)** $r_t = \ln(P_t / P_{t-1})$.
- Lợi suất log **cộng được**: $\sum_{t=1}^{T} r_t = \ln(P_T / P_0)$ — tổng lợi suất log từng nến bằng đúng lợi suất log cả kỳ.
  Lợi suất đơn giản thì phải **nhân**: $\prod (1 + R_t) = P_T / P_0$. Khi nhỏ, hai loại gần bằng nhau: $r \approx R - R^2/2$.
- **Điểm cơ bản (basis point, bp)**: 1 bp = 0.01% = 0.0001. Lợi suất một nến M15 thường đo bằng bp.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

# Ví dụ tay: 2000 → 2100 → 2000
p = np.array([2000.0, 2100.0, 2000.0])
don = p[1:] / p[:-1] - 1
log = np.diff(np.log(p))
print("đơn giản:", don.round(5), "· tổng", round(don.sum(), 5))
print("log     :", log.round(5), "· tổng", round(log.sum(), 5))

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
c = df.close
r_don = c.pct_change().dropna()
r_log = np.log(c).diff().dropna()
print("Close đầu %.3f · close cuối %.3f" % (c.iloc[0], c.iloc[-1]))
print("Lợi suất cả kỳ   : đơn giản %.5f · log %.5f" % (c.iloc[-1] / c.iloc[0] - 1, np.log(c.iloc[-1] / c.iloc[0])))
print("Cộng từng nến    : đơn giản %.5f · log %.5f" % (r_don.sum(), r_log.sum()))
print("Nhân (1 + r)     : %.5f" % (np.prod(1 + r_don) - 1))
print("|r| trung vị một nến: đơn giản %.3f bp · log %.3f bp" % (r_don.abs().median() * 1e4, r_log.abs().median() * 1e4))
```

```text
Kết quả khi mình chạy:
đơn giản: [ 0.05    -0.04762] · tổng 0.00238
log     : [ 0.04879 -0.04879] · tổng 0.0
Close đầu 2065.734 · close cuối 2502.925
Lợi suất cả kỳ   : đơn giản 0.21164 · log 0.19197
Cộng từng nến    : đơn giản 0.19903 · log 0.19197
Nhân (1 + r)     : 0.21164
|r| trung vị một nến: đơn giản 4.087 bp · log 4.087 bp
```

Đi +5% rồi −4.762% là về đúng 2000, nhưng tổng lợi suất đơn giản là +0.24%; tổng lợi suất log là 0, đúng sự thật. Trên 8 tháng
vàng: cộng 15 849 lợi suất log ra đúng 0.19197 = lợi suất log cả kỳ; cộng lợi suất đơn giản ra 19.9%, trong khi vàng tăng thật
21.2%. Ở một nến lẻ hai cách gần như trùng (4.087 bp), chênh lệch chỉ lộ ra khi gộp nhiều nến. Từ module 2 ta dùng lợi suất log.

**Bẫy hay gặp.**
- **Cộng lợi suất đơn giản** qua nhiều nến — sai số tích luỹ như trên.
- **Lợi suất vắt qua khoảng trống.** Lợi suất của nến mở tuần chứa cả biến động cuối tuần. Khi đo phân phối lợi suất M15, chỉ lấy
  cặp nến liền nhau (module 2 làm vậy).
- **So bằng USD.** 2 USD lúc vàng 2000 và lúc vàng 2500 không như nhau; giữa XAUUSD và EURUSD càng không. So biên độ giữa các mã
  bằng ATR hoặc bp (AGENTS.md §9).

## 6. Gộp khung: M15 → H1, H4, D1

**Trực giác.** Một nến H1 là bốn nến M15 liền nhau: open của nến đầu, high cao nhất, low thấp nhất, close của nến cuối. Phần khó
không phải công thức mà là **mốc**: giờ H1 bắt đầu ở đâu, ngày bắt đầu lúc nào, làm gì với giờ chỉ có hai nến M15.

**Định nghĩa.**
- **Gộp khung (resample)**: nhóm nến nhỏ theo khoảng thời gian của nến lớn rồi lấy (open đầu, max high, min low, close cuối).
- **Mốc nến (alignment)**: `utc_epoch` — nến lớn mở ở bội số độ dài khung tính từ 00:00 UTC (H4 mở 00, 04, 08… UTC); `ny_1700` —
  ngày giao dịch bắt đầu 17:00 New York, H4 mở 17, 21, 01, 05, 09, 13 giờ New York. Với khung ≤ H1 hai mốc trùng nhau. Lab dùng
  `ny_1700` cho H4 / D1 của `ict_structure` ([`core/data/htf_stream.py`](../../core/data/htf_stream.py)); dataset H4 / D1 cũng
  theo mốc này.
- Giờ có ít nến hơn bình thường: [`core/data/resample.py`](../../core/data/resample.py) mặc định `drop_incomplete` (không phát nến
  lớn thiếu), có tuỳ chọn `emit_available`. Không bao giờ đúc nến giả.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

m15 = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
g = m15.groupby(m15.index.floor("h"))            # nhóm theo giờ UTC chứa giờ mở nến
h1 = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(),
                   "close": g.close.last(), "so_nen_m15": g.open.size()})
lab = nap_nen(XAU_H1, "2024-01-01", "2024-09-01")
j = h1.join(lab[["open", "high", "low", "close"]], rsuffix="_lab", how="outer")
print("H1 tự gộp:", len(h1), "· H1 của lab:", len(lab), "· mốc chỉ một bên có:", j.isna().any(axis=1).sum())
lech = np.abs(j[["open", "high", "low", "close"]].values - j[["open_lab", "high_lab", "low_lab", "close_lab"]].values)
print("Nến khớp cả 4 giá:", (lech.max(axis=1) < 1e-9).sum())
print(h1.so_nen_m15.value_counts().to_dict())
thieu = h1[h1.so_nen_m15 < 4]
print(thieu[["open", "close", "so_nen_m15"]].assign(gio_ny=thieu.index.tz_convert("America/New_York").strftime("%H:%M")))

# Bẫy: resample() dựng lưới giờ đều, kể cả giờ thị trường đóng cửa
r = m15.close.resample("1h").last()
print("resample('1h'):", len(r), "dòng, trong đó", r.isna().sum(), "dòng rỗng")
```

```text
Kết quả khi mình chạy:
H1 tự gộp: 3965 · H1 của lab: 3965 · mốc chỉ một bên có: 0
Nến khớp cả 4 giá: 3965
{4: 3960, 2: 5}
                               open     close  so_nen_m15 gio_ny
bar_time
2024-01-15 19:00:00+00:00  2054.278  2054.505           2  14:00
2024-02-19 19:00:00+00:00  2017.615  2017.775           2  14:00
2024-05-27 18:00:00+00:00  2354.885  2350.754           2  14:00
2024-06-19 18:00:00+00:00  2329.995  2327.695           2  14:00
2024-07-04 18:00:00+00:00  2356.185  2356.555           2  14:00
resample('1h'): 5806 dòng, trong đó 1841 dòng rỗng
```

Khớp **3965 / 3965** nến, cả bốn giá (gộp `XAU_M1` → M15 rồi so với `XAU_M15` cũng khớp 15 850 / 15 850 — thử lại bằng
`floor("15min")`). Năm nến H1 chỉ có hai nến M15: đúng năm ngày đóng sớm 14:30 New York ở mục 3. Dataset H1 của lab giữ năm nến
này; gộp bằng `drop_incomplete` thì thiếu đúng năm nến đó — «khớp» hay «lệch» phụ thuộc chính sách, nên chính sách phải ghi lại.
`resample("1h")` của pandas dựng lưới giờ đều, sinh 1841 dòng rỗng cho cuối tuần và giờ nghỉ; phải bỏ, không được lấp. Gộp sang H4
theo mốc 17:00 New York là bài tập 1.

**Bẫy lớn nhất khi dùng khung lớn: nhìn tương lai.** Nến H1 mở 10:00 chỉ biết đủ lúc 11:00. Nếu bạn nối nến H1 vào nến M15 theo
giờ mở (`floor("h")` rồi `merge`), nến M15 10:00, 10:15, 10:30 sẽ «thấy» close H1 trước khi nó tồn tại — 3 trên 4 nến M15. Nối đúng
là theo **giờ đóng**: mỗi nến M15 chỉ lấy nến H1 có `close_time` ≤ `close_time` của nó (`pd.merge_asof(..., direction="backward")`).
Luật của lab: ngữ cảnh khung lớn chỉ lấy từ nến khung lớn **đã chốt** (AGENTS.md §2.1); module 5 có bài thực hành.

## 7. True Range, ATR Wilder và ATR theo giờ trong ngày

**Trực giác.** Biên độ high − low bỏ sót cú nhảy giữa hai nến: nến mở tuần cách close thứ Sáu 5 USD rồi chỉ dao động 2 USD thì
biến động thật lớn hơn 2. **True Range** tính cả khoảng nhảy đó. ATR là «biên độ thật trung bình gần đây» — thước đo lab dùng cho
mọi ngưỡng (lấy thanh khoản, displacement, dung sai bằng giá).

**Định nghĩa.**

$$TR_t = \max\big(H_t - L_t,\ |H_t - C_{t-1}|,\ |L_t - C_{t-1}|\big)$$

Biên độ thật của nến $t$ là khoảng lớn nhất trong ba khoảng: high − low, high tới close trước, low tới close trước.

$$ATR_t = \frac{(N-1)\,ATR_{t-1} + TR_t}{N}, \qquad N = 14$$

Mỗi nến mới, ATR giữ $13/14$ giá trị cũ và thêm $1/14$ TR mới — **làm trơn Wilder (Wilder smoothing)**, trung bình trượt mũ với
hệ số $1/N$ (không phải $2/(N+1)$ như EMA thường). Giá trị đầu (**hạt giống, seed**) = trung bình cộng $N$ TR đầu tiên. Lab có
hai biến thể trong [`core/indicators.py`](../../core/indicators.py): `WilderATRPrevClose` (dùng trong `ict_structure`,
`dc_atr_structure`: nến đầu chỉ cho close trước) và `WilderATR` (trang Đánh giá, chuẩn ngẫu nhiên: nến đầu lấy high − low).
Ngưỡng ở nến $t$ luôn dùng $ATR_{t-1}$.

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
from core.indicators import WilderATR

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
h, l, c = df.high.values, df.low.values, df.close.values
c_truoc = np.r_[np.nan, c[:-1]]
tr = np.maximum.reduce([h - l, np.abs(h - c_truoc), np.abs(l - c_truoc)])   # nến đầu: NaN (chưa có close trước)

N = 14
atr = np.full(len(df), np.nan)
atr[N] = tr[1:N + 1].mean()                        # hạt giống: trung bình 14 TR đầu tiên có close trước
for i in range(N + 1, len(df)):
    atr[i] = (atr[i - 1] * (N - 1) + tr[i]) / N    # làm trơn Wilder

lab = chay_thuat_toan("ict_structure", XAU_M15, "2024-01-01", "2024-09-01")["timeline"]["atr"].astype(float).values
print("Nến đầu có ATR: mình", np.argmax(~np.isnan(atr)), "· lab", np.argmax(~np.isnan(lab)))
print("Lệch lớn nhất so với cột atr của ict_structure:", np.nanmax(np.abs(atr - lab)))

# Biến thể thứ hai của lab (core/indicators.WilderATR, dùng ở trang Đánh giá): nến đầu lấy high − low
w = WilderATR(N)
atr_b = np.array([np.nan if v is None else v for v in (w.update(a, b, x) for a, b, x in zip(h, l, c))])
for i in [14, 100, 200]:
    print("nến %3d: ATR %.4f · biến thể %.4f · lệch %.1e" % (i, atr[i], atr_b[i], abs(atr[i] - atr_b[i])))

print("ATR trung vị %.2f USD → 0.1 × ATR = %.2f USD" % (np.nanmedian(atr), 0.1 * np.nanmedian(atr)))
dau_tuan = (df.index.to_series().diff() > pd.Timedelta(hours=40)).values
print("TR trung vị: mọi nến %.2f · nến mở tuần %.2f · (high − low) nến mở tuần %.2f"
      % (np.nanmedian(tr), np.median(tr[dau_tuan]), np.median((h - l)[dau_tuan])))
```

```text
Kết quả khi mình chạy:
Nến đầu có ATR: mình 14 · lab 14
Lệch lớn nhất so với cột atr của ict_structure: 0.0
nến  14: ATR 2.1338 · biến thể 2.2726 · lệch 1.4e-01
nến 100: ATR 1.6571 · biến thể 1.6574 · lệch 2.4e-04
nến 200: ATR 1.8504 · biến thể 1.8504 · lệch 1.4e-07
ATR trung vị 2.58 USD → 0.1 × ATR = 0.26 USD
TR trung vị: mọi nến 2.25 · nến mở tuần 4.81 · (high − low) nến mở tuần 4.30
```

ATR tự cài khớp tuyệt đối cột `atr` trong timeline của `ict_structure` (lệch 0.0). Hai biến thể của lab chỉ khác hạt giống; phần
khác nhân với $13/14$ mỗi nến nên sau 200 nến (~2 ngày giao dịch) chỉ còn $10^{-7}$. Lab **không** reset ATR qua khoảng trống: TR
của nến mở tuần (trung vị 4.81) chứa cả cú nhảy cuối tuần, gấp đôi nến thường.

**ATR theo giờ trong ngày.** «1 ATR» lúc 09:00 New York và lúc 19:00 New York không cùng nghĩa:

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
c_truoc = df.close.shift(1)
tr = pd.concat([df.high - df.low, (df.high - c_truoc).abs(), (df.low - c_truoc).abs()], axis=1).max(axis=1)
lien = df.index.to_series().diff() == pd.Timedelta(minutes=15)    # bỏ nến ngay sau khoảng trống
tr = tr[lien]
gio_ny = tr.index.tz_convert("America/New_York").hour
bang = tr.groupby(gio_ny).agg(["mean", "size"])
bang["so_voi_tb"] = bang["mean"] / tr.mean()
pd.set_option("display.width", 200)
print(bang[["mean", "so_voi_tb"]].T.round(2).to_string())
print("Số nến mỗi giờ:", bang["size"].min(), "→", bang["size"].max(), "(giờ 18 ít nhất: nến đầu phiên đứng sau khoảng trống nên bị bỏ)")
print("TR trung bình mọi giờ %.2f USD · giờ cao nhất / thấp nhất = %.1f lần"
      % (tr.mean(), bang["mean"].max() / bang["mean"].min()))
```

```text
Kết quả khi mình chạy:
bar_time     0     1     2     3     4     5     6     7     8     9     10    11    12    13    14    15    16   18    19    20    21    22   23
mean       1.73  2.28  2.81  2.78  2.67  2.42  2.39  2.60  4.82  5.47  5.43  4.13  3.12  2.90  2.45  2.25  1.54  1.7  1.48  2.12  3.26  2.48  2.0
so_voi_tb  0.61  0.80  0.99  0.98  0.94  0.85  0.84  0.92  1.70  1.93  1.91  1.46  1.10  1.02  0.86  0.80  0.54  0.6  0.52  0.75  1.15  0.87  0.7
Số nến mỗi giờ: 519 → 692 (giờ 18 ít nhất: nến đầu phiên đứng sau khoảng trống nên bị bỏ)
TR trung bình mọi giờ 2.83 USD · giờ cao nhất / thấp nhất = 3.7 lần
```

TR vọt từ 2.60 (07:00 New York) lên 4.82 (08:00 — 08:30 New York là giờ Mỹ công bố số liệu kinh tế), đỉnh 09:00–10:00 gần gấp đôi
trung bình, rồi còn 1.5 lúc 16:00 và 19:00. Giờ 17 không có (nghỉ hằng ngày). Hệ quả: ATR 14 nến M15 chỉ nhìn lại 3.5 giờ, nên
lúc 08:30 New York nó còn mang mức yên ắng của buổi sáng sớm — «displacement ≥ 1.5 ATR» dễ đạt hơn hẳn đầu phiên New York chỉ vì
mùa vụ biến động. Đó là lý do chuẩn ngẫu nhiên `matched_hour_atr_v1` ghép **cùng giờ New York và cùng nhóm ATR** (module 2, 3), và
module 4 dạy cách khử mùa vụ này.

**Bẫy hay gặp.**
- **EMA thay cho Wilder.** `ewm(span=14)` dùng hệ số $2/15$, không phải $1/14$: ATR nhạy hơn và khác `iATR` của MT5 (dùng Wilder —
  docstring `core/indicators.py`). `ewm(alpha=1/14, adjust=False)` đúng làm trơn nhưng khác hạt giống.
- **Dùng $ATR_t$ làm ngưỡng cho chính nến $t$**: TR của nến $t$ đã nằm trong ATR, ngưỡng tự nới theo chính cú bung cần đo.
- **So ATR giữa hai lần chạy bắt đầu khác ngày**: hạt giống khác, vài trăm nến đầu lệch nhau.
- **ATR tính bằng USD**: không so được XAUUSD với EURUSD, cũng không so được tháng 1 (vàng 2050) với tháng 8 (2500).

## Lab đang dùng những điều này ở đâu

| Khái niệm | File / tài liệu của lab | Ghi chú |
|---|---|---|
| Nến đã đóng, `close_time`, `confirmed_at` | [`core/types.py`](../../core/types.py), [`AGENTS.md`](../../AGENTS.md) §2.1 | Lõi dùng `close_time` làm «thời điểm biết» |
| Nến đang hình thành trên MT5, tick volume | [`core/data/mt5_source.py`](../../core/data/mt5_source.py), [`mt5_va_tong_hop_nen.md`](../guides/mt5_va_tong_hop_nen.md) §1 | `drop_forming=True` mặc định |
| Giá Bid, volume = 0, dataset đã nạp | [`du_lieu_thi_truong.md`](../guides/du_lieu_thi_truong.md) §1 | Mọi dataset thật là Bid |
| Giờ HistData, bộ «LỆCH GIỜ» | [`AGENTS.md`](../../AGENTS.md) §9, [`du_lieu_thi_truong.md`](../guides/du_lieu_thi_truong.md) §1 | Bộ cũ chỉ để mở run cũ |
| Lịch phiên, phân loại khoảng trống | [`core/data/session_calendar.py`](../../core/data/session_calendar.py), [`core/components/session_gap.py`](../../core/components/session_gap.py), [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §4.2 | Sự kiện `ICT_GAP`; chặn cửa sổ vắt qua khoảng trống |
| Killzone theo giờ New York | [`core/components/killzone.py`](../../core/components/killzone.py) | Có đổi giờ mùa hè (`zoneinfo`) |
| Gộp khung, mốc `utc_epoch` / `ny_1700` | [`core/data/resample.py`](../../core/data/resample.py), [`core/data/htf_stream.py`](../../core/data/htf_stream.py), [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §4.13 | H4/D1 của `ict_structure` theo 17:00 New York |
| True Range, ATR Wilder | [`core/indicators.py`](../../core/indicators.py), [`core/algorithms/ict_structure/algorithm.py`](../../core/algorithms/ict_structure/algorithm.py) | Ngưỡng ở nến $t$ dùng $ATR_{t-1}$ |
| ATR theo giờ trong chuẩn ngẫu nhiên | [`core/eval/null_baseline.py`](../../core/eval/null_baseline.py), [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md) §1.3 | `matched_hour_atr_v1`: giờ New York × tam phân vị ATR |

## Bài tập

**Bài 1 — Mốc H4.** Gộp M15 → H4 theo hai mốc (`utc_epoch` và `ny_1700`) rồi so với `XAU_H4`. Mốc nào khớp, và vì sao một mốc
cho nhiều nến hơn?
*Gợi ý:* với `ny_1700`, đổi sang giờ New York (bỏ múi giờ), cộng 7 giờ, `floor("4h")`, trừ 7 giờ, gắn lại múi New York rồi đổi
về UTC.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

def gop(df, khoa):
    g = df.groupby(khoa)
    return pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last()})

m15 = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
lab = nap_nen(XAU_H4, "2024-01-01", "2024-09-01")

# Cách 1 — mốc UTC: 00, 04, 08, 12, 16, 20 giờ UTC
h4_utc = gop(m15, m15.index.floor("4h"))
# Cách 2 — mốc 17:00 New York: dời giờ NY +7 giờ để 17:00 thành 00:00, làm tròn 4 giờ, dời lại
ny = m15.index.tz_convert("America/New_York").tz_localize(None)
khoa = (ny + pd.Timedelta(hours=7)).floor("4h") - pd.Timedelta(hours=7)
h4_ny = gop(m15, khoa)
h4_ny.index = h4_ny.index.tz_localize("America/New_York").tz_convert("UTC")

for ten, x in [("utc_epoch", h4_utc), ("ny_1700", h4_ny)]:
    j = x.join(lab[["open", "high", "low", "close"]], rsuffix="_lab", how="inner")
    lech = np.abs(j[["open", "high", "low", "close"]].values - j[["open_lab", "high_lab", "low_lab", "close_lab"]].values)
    print("%-9s: %d nến · lab %d nến · trùng mốc %d · khớp cả 4 giá %d"
          % (ten, len(x), len(lab), len(j), (lech.max(axis=1) < 1e-9).sum()))
```

```text
Kết quả khi mình chạy:
utc_epoch: 1072 nến · lab 1037 nến · trùng mốc 0 · khớp cả 4 giá 0
ny_1700  : 1037 nến · lab 1037 nến · trùng mốc 1037 · khớp cả 4 giá 1037
```

Mốc 17:00 New York khớp 1037 / 1037; mốc UTC không trùng một mốc nào và cho 1072 nến, vì nến H4 mốc UTC vắt qua giờ nghỉ bị cắt
làm đôi (một mẩu trước nghỉ, một mẩu sau). Cùng dữ liệu, cùng công thức, chỉ khác mốc — mọi swing, FVG, PDH/PDL trên H4 sẽ khác.
Vì vậy mốc là tham số ghi trong run (AGENTS.md §9). Khi so với TradingView, đặt múi giờ chart là New York và kiểm nến H4 mở 17, 21,
01… giờ.

</details>

**Bài 2 — Khoảng trống năm 2023.** Đếm khoảng trống theo loại cho `XAU_M15_DAI` (lịch `cme_globex_metals`) và `EUR_M15_DAI`
(lịch `fx_spot`) trong năm 2023. Vì sao EURUSD không có `nghi_phien`? Khoảng «thiếu trong phiên» rơi vào thứ mấy?
*Gợi ý:* để lab phân loại giúp — chạy `ict_structure` (lịch phiên tự chọn theo mã) và đọc `details` của sự kiện `ICT_GAP`.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

for ten, ds in [("XAUUSD", XAU_M15_DAI), ("EURUSD", EUR_M15_DAI)]:      # lịch phiên tự chọn theo mã
    ev = chay_thuat_toan("ict_structure", ds, "2023-01-01", "2024-01-01")["su_kien"]
    gap = pd.DataFrame(list(ev[ev.structure_type == "ICT_GAP"].details))
    thieu = gap[gap.loai == "thieu_trong_phien"]
    thu = pd.to_datetime(thieu.tu).dt.strftime("%a").value_counts().to_dict()   # "tu" = ô 15 phút thiếu đầu tiên
    print(ten, gap.loai.value_counts().to_dict())
    print("   thiếu trong phiên theo thứ:", thu, "· số ô trong phiên: trung vị", thieu.so_o_trong_phien.median(),
          "lớn nhất", thieu.so_o_trong_phien.max())
```

```text
Kết quả khi mình chạy:
XAUUSD {'nghi_phien': 198, 'cuoi_tuan': 29, 'thieu_trong_phien': 25, 'nghi_le': 4}
   thiếu trong phiên theo thứ: {'Fri': 20, 'Mon': 2, 'Thu': 2, 'Tue': 1} · số ô trong phiên: trung vị 4.0 lớn nhất 12
EURUSD {'cuoi_tuan': 32, 'thieu_trong_phien': 18, 'nghi_le': 3}
   thiếu trong phiên theo thứ: {'Fri': 18} · số ô trong phiên: trung vị 6.0 lớn nhất 84
```

FX giao ngay chạy liền từ tối Chủ nhật tới chiều thứ Sáu, không nghỉ hằng ngày, nên lịch `fx_spot` không có `nghi_phien`. Năm 2023
có 25 (XAUUSD) và 18 (EURUSD) khoảng thiếu, gần hết vào thứ Sáu: HistData 2023 dừng sớm 1–3 giờ trước giờ đóng tuần ở khoảng 20
thứ Sáu (tài liệu pipeline §6 ghi đúng điều này). Khoảng 84 ô của EURUSD là Good Friday 2023 (từ 00:00 UTC thứ Sáu; lịch FX không
đóng ngày này, nguồn thì không có giá). So với 1 khoảng thiếu năm 2024, năm 2023 là năm dữ liệu kém — thống kê «theo giờ» có chiều thứ Sáu sẽ thiếu mẫu
ở 2023.

</details>

**Bài 3 — Mùa vụ biến động và đổi giờ.** Tính TR trung bình theo giờ cho mùa đông (01/01–09/03) và mùa hè (01/04–31/08), theo giờ
UTC và theo giờ New York. Trong khoảng 6–15 giờ, TR vọt mạnh nhất ở giờ nào? Kết luận gì về mốc UTC cố định?
*Gợi ý:* `pivot_table(index=giờ, columns=mùa, values="tr", aggfunc="mean")`, rồi chia mỗi giờ cho giờ liền trước.

<details><summary>Lời giải</summary>

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *

df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
c_truoc = df.close.shift(1)
tr = pd.concat([df.high - df.low, (df.high - c_truoc).abs(), (df.low - c_truoc).abs()], axis=1).max(axis=1)
tr = tr[df.index.to_series().diff() == pd.Timedelta(minutes=15)]
mua = pd.Series("bo", index=tr.index)
mua[tr.index < "2024-03-10"] = "dong"          # cả Mỹ và Anh đang giờ mùa đông
mua[tr.index >= "2024-04-01"] = "he"           # cả hai đã sang giờ mùa hè
t = pd.DataFrame({"tr": tr.values, "mua": mua.values, "utc": tr.index.hour,
                  "ny": tr.index.tz_convert("America/New_York").hour})
t = t[t.mua != "bo"]
for cot in ["utc", "ny"]:
    b = t.pivot_table(index=cot, columns="mua", values="tr", aggfunc="mean").loc[6:15]
    nhay = b / b.shift(1)                       # TR giờ này / TR giờ liền trước
    print("Giờ", cot.upper(), "· TR vọt mạnh nhất (6–15 giờ) ở:", nhay.idxmax().to_dict())
    print(b.T.round(2).to_string())
```

```text
Kết quả khi mình chạy:
Giờ UTC · TR vọt mạnh nhất (6–15 giờ) ở: {'dong': 13, 'he': 12}
utc     6     7     8     9     10    11    12    13    14    15
mua
dong  1.53  1.92  2.05  1.82  1.70  1.74  1.81  4.28  3.90  3.83
he    3.31  3.19  3.08  2.71  2.68  3.01  5.12  6.28  6.29  4.77
Giờ NY · TR vọt mạnh nhất (6–15 giờ) ở: {'dong': 8, 'he': 8}
ny      6     7     8     9     10    11    12    13    14    15
mua
dong  1.74  1.81  4.28  3.90  3.83  2.91  2.27  2.02  1.87  1.45
he    2.68  3.01  5.12  6.28  6.29  4.77  3.59  3.32  2.71  2.65
```

Theo giờ New York cú vọt luôn ở 08:00 (giờ có tin 08:30 của Mỹ). Theo UTC nó nhảy từ 13:00 (mùa đông) sang 12:00 (mùa hè). Bộ lọc
«giờ sôi động = 13:00 UTC» đúng mùa đông, sai một giờ suốt mùa hè. Thêm một quan sát: mùa hè 2024 TR cao hơn mùa đông ở mọi giờ —
mức biến động đổi theo thời gian, không chỉ theo giờ trong ngày (module 4).

</details>

## Tự kiểm

**1.** Nến M15 có `bar_time` 2024-03-12 13:30 UTC. Lúc nào bạn được dùng close của nó? Đó là mấy giờ New York?
<details><summary>Đáp án</summary>

Từ 13:45 UTC (`close_time` = mở + 15 phút). Ngày 12/03 Mỹ đã sang giờ mùa hè (UTC−4): 13:45 UTC =
09:45 New York; nến mở 09:30 New York.

</details>

**2.** Chart lab là giá Bid. Giá Bid vượt một đỉnh 0.15 USD rồi quay xuống. Stop mua đặt ngay trên đỉnh đó đã bị khớp chưa? Stop
bán dưới một đáy bị Bid xuyên 0.15 USD thì sao?
<details><summary>Đáp án</summary>

Stop mua khớp theo Ask = Bid + spread, nên Ask đã vượt đỉnh ít nhất 0.15 + spread: chắc chắn khớp
(thậm chí Ask có thể đã chạm khi Bid còn chưa tới đỉnh). Stop bán khớp theo Bid nên khớp đúng như chart. Chart Bid **đánh giá
thấp** việc BSL bị lấy.

</details>

**3.** Nến mở 2024-07-10 22:30 UTC và nến mở 2024-07-10 20:30 UTC thuộc ngày giao dịch nào?
<details><summary>Đáp án</summary>

Tháng 7 là giờ mùa hè (UTC−4). 22:30 UTC = 18:30 New York 10/07; cộng 7 giờ → 01:30 ngày 11/07:
ngày giao dịch **11/07**. 20:30 UTC = 16:30 New York 10/07; cộng 7 giờ → 23:30 ngày 10/07: ngày giao dịch **10/07**. Cùng ngày UTC,
khác ngày giao dịch.

</details>

**4.** Khoảng trống từ thứ Sáu 20:45 UTC tới Chủ nhật 22:00 UTC, tháng 6. Lịch phân loại là gì? Nếu nến trước khoảng trống là thứ
Sáu 17:45 UTC thì sao?
<details><summary>Đáp án</summary>

Trường hợp đầu: `cuoi_tuan` (thứ Sáu đóng 17:00 New York = 21:00 UTC mùa hè, mọi ô thiếu nằm ngoài
phiên). Trường hợp sau: các ô 18:00–20:45 UTC thứ Sáu nằm trong phiên → `thieu_trong_phien`, bất thường.

</details>

**5.** Bạn gộp M15 → D1 theo ngày UTC (`floor("D")`). Kết quả khác `XAU_D1` của lab ở đâu?
<details><summary>Đáp án</summary>

Ở mọi ngày: D1 của lab là ngày giao dịch 17:00 → 17:00 New York, phần sau 17:00 New York thuộc ngày
hôm sau. Gộp theo ngày UTC tạo thêm «ngày» Chủ nhật ngắn (208 ngày UTC so với 173 ngày giao dịch trong 8 tháng) và cắt phiên Á làm
đôi. PDH/PDL theo hai cách là hai mức khác nhau.

</details>

**6.** ATR Wilder 14 có hệ số làm trơn bao nhiêu? Vì sao lab đặt ngưỡng ở nến $t$ bằng $ATR_{t-1}$ chứ không phải $ATR_t$?
<details><summary>Đáp án</summary>

Hệ số $1/14$ (giữ $13/14$ giá trị cũ). $ATR_t$ đã chứa TR của chính nến $t$: một nến bung mạnh tự
nâng ngưỡng của chính nó. $ATR_{t-1}$ chỉ dựa vào những gì đã biết trước nến $t$.

</details>

## Đọc thêm

- Larry Harris, *Trading and Exchanges* — chủ đề giá Bid / Ask, spread, người tạo lập thị trường, thị trường OTC (vì sao vàng giao
  ngay không có volume tập trung).
- Ruey Tsay, *Analysis of Financial Time Series*, chương 1 — lợi suất đơn giản và log, lợi suất nhiều kỳ.
- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — nguồn gốc True Range và ATR.
- Tài liệu lab: [`du_lieu_thi_truong.md`](../guides/du_lieu_thi_truong.md); tài liệu của repo pipeline
  (`market-data-pipeline/docs/du_lieu_thi_truong.md`) §3 múi giờ HistData, §5 lịch phiên, §6 chất lượng còn lại;
  [`mt5_va_tong_hop_nen.md`](../guides/mt5_va_tong_hop_nen.md); [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md)
  §4.2 (khoảng trống), §4.13 (bộ gộp `ny_1700`).
- Danh mục quant ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md)): R4-09 (cột spread MT5 + kiểm chất
  lượng dữ liệu quanh rollover, cuối tuần, lễ), R3-26 (khử mùa vụ biến động trong ngày), R4-10 (realized variance từ M1), R3-25
  (ước lượng biến động từ OHLC) — ba mục sau thuộc module 4.
