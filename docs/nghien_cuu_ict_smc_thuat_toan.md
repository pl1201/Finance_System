# Nghiên cứu: các thuật toán ICT/SMC đã được code hoá — cái nào phổ biến, cái nào có bằng chứng, chỗ nào mơ hồ

Ngày: 27/09/2026. Phạm vi: đọc mã nguồn thật của 10 cài đặt công khai (Python, Pine, MQL5,
TypeScript), 1 nghiên cứu kiểm định 44 khái niệm ICT/SMC, 1 thư viện kiến thức ICT có dẫn
video, và các nghiên cứu học thuật về nhận diện đỉnh/đáy, điểm đổi trạng thái và thanh khoản.

**Cách đọc tài liệu này.** «Phổ biến» = số cài đặt đã đọc dùng cùng một định nghĩa. Phổ biến
**không** có nghĩa là đúng với ICT hay có lợi thế giao dịch. Mục 5 tách riêng bằng chứng.
Những gì chưa tự kiểm tra được ghi rõ ở mục 8.

**Khái niệm nào cần khái niệm nào, và nối vào lab ra sao** (tài liệu này xếp theo từng khái
niệm riêng nên không thể hiện được): xem [`kien_truc_luong_ict.md`](kien_truc_luong_ict.md).

---

## 1. Kết luận ngắn

1. **Không có benchmark chuẩn nào xếp hạng «thuật toán ICT tốt nhất».** Không tìm thấy nghiên
   cứu bình duyệt nào. Nghiên cứu công khai kỹ nhất (44 khái niệm, S&P 500, 2010–2026) thấy
   **không khái niệm nào thắng vào lệnh ngẫu nhiên có cấu trúc tương đương** (mục 5.1).
2. **Định nghĩa đồng thuận cao** (nên code theo): FVG 3 nến; BOS xác nhận bằng **close**; BOS
   vs CHoCH/MSS phân biệt bằng **xu hướng trước đó**; mỗi mức chỉ phá một lần.
3. **Định nghĩa chia hai trường phái** (phải chọn và ghi phiên bản): cách tìm swing (pivot đối
   xứng vs «leg» một phía của LuxAlgo); order block là nến nào; độ dài swing.
4. **Không có định nghĩa định lượng gốc từ ICT**: displacement, ngưỡng «bằng giá» (EQH/EQL),
   sweep cần bao nhiêu wick / trong bao nhiêu nến. Mọi con số đang lưu hành đều do cộng đồng
   tự đặt.
5. **Swing gốc của ICT** là khối 3 nến của Larry Williams (1 nến mỗi bên) + phân cấp
   ngắn/trung/dài hạn — lab đã có đúng cấu trúc này trong `swing_hierarchy` (mục 6.1).
6. Nhiều cài đặt phổ biến **nhìn tương lai** khi dùng cho backtest (gắn nhãn tại nến sự kiện,
   dùng min/max toàn dataset). Lab phải giữ nguyên tắc `confirmed_at`.

---

## 2. Các cài đặt đã đọc

Số sao lấy qua GitHub API ngày 27/09/2026.

| # | Cài đặt | Ngôn ngữ | Sao | Giấy phép | Dòng dõi | Ghi chú tin cậy |
|---|---|---|---:|---|---|---|
| 1 | [joshyattridge/smart-money-concepts](https://github.com/joshyattridge/smart-money-concepts) | Python | 2028 | MIT | độc lập | Phổ biến nhất trên GitHub |
| 2 | [Smart Money Concepts (SMC) — LuxAlgo](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/) (đọc qua [bản gist mở rộng](https://gist.github.com/niquedegraaff/8c2f45dc73519458afeae14b0096d719)) | Pine | — | CC BY-NC-SA 4.0 | gốc | Phổ biến nhất trên TradingView |
| 3 | [ICT Concepts — LuxAlgo](https://www.tradingview.com/script/ib4uqBJx-ICT-Concepts-LuxAlgo/) | Pine | — | mở theo House Rules TradingView | gốc | Đọc mô tả + các định nghĩa trích trong nghiên cứu mục 5.1; chưa đọc hết source |
| 4 | [Prasad1612/smart-money-concept](https://github.com/Prasad1612/smart-money-concept) | Python | 47 | không ghi | port LuxAlgo (`leg`) | |
| 5 | [gabrielkoerich/smart-money-concepts](https://github.com/gabrielkoerich/smart-money-concepts) | TypeScript | 3 | không ghi | port LuxAlgo (`leg`) | |
| 6 | [harshatangirala/smc-ict-research](https://github.com/harshatangirala/smc-ict-research) | Python | 3 | MIT + CC BY-NC-SA cho phần dịch từ LuxAlgo | port LuxAlgo (2 script) | Nghiên cứu kiểm định, xem mục 5.1 |
| 7 | [KVignesh122/MT5-SMC-trading-bot](https://github.com/KVignesh122/MT5-SMC-trading-bot) | MQL5 | 84 | Apache-2.0 | độc lập | EA giao dịch |
| 8 | [carlosrod723/MQL5-Trading-Bot](https://github.com/carlosrod723/MQL5-Trading-Bot) | MQL5 | 78 | MIT | fractal Bill Williams | |
| 9 | [darkosedam-svg/ict-smc-detector](https://github.com/darkosedam-svg/ict-smc-detector) | Python | 3 | MIT | độc lập | Vector hoá, đơn giản |
| 10 | CantoLab Open Source Fractal (đã chuyển thể trong lab, `c2_cisd_research`) | Pine | — | MIT | gốc | Xem `docs/nghien_cuu_cantolab_fractal.md` |

Nguồn định nghĩa gốc: [SrsBlack/ict-knowledge-library](https://github.com/SrsBlack/ict-knowledge-library)
(45 sao, không ghi giấy phép, **do LLM duy trì** — dùng để tìm video gốc, không dùng như chân lý;
xem mục 4.1).

⚠ Loại khỏi so sánh: một số repo nhiều sao trong kết quả tìm kiếm chỉ chứa HTML, tên kiểu
«2026 Pro-Level … Institutional Signals» (vd *Matrix-Confluence-Scorer*,
*institutional-orderflow-mt5*) — nhiều khả năng là repo quảng cáo/SEO, không có thuật toán để đọc.

---

## 3. So sánh định nghĩa theo từng khái niệm

### 3.1. Swing high/low — **chia hai trường phái**

| Trường phái | Quy tắc | Cài đặt dùng | Tham số mặc định |
|---|---|---|---|
| **Pivot/fractal đối xứng** | high[c] > (hoặc ≥) mọi high trong N nến trái **và** N nến phải | #1 (≥, cửa sổ ±N rồi lọc cho luân phiên), #7 (>, N=5), #8 (fractal Bill Williams, N=2), lab `swing_pivot` (>, 3/3) | 50 (#1), 5 (#7), 2 (#8) |
| **«Leg» một phía (LuxAlgo)** | `high[len] > highest(len)` — chỉ so với **len nến sau**; đỉnh/đáy luân phiên qua biến trạng thái | #2, #3, #4, #5, #6 | nội bộ 5, cấu trúc 50 |
| Không dùng pivot | BOS = close vượt max high của N nến trước (kênh Donchian) | #9 | N tuỳ chọn |
| **Gốc ICT** | Khối 3 nến (1 mỗi bên), ICT ghi công cho **Larry Williams**; phân cấp ngắn/trung/dài hạn | — | 1/1 |

- Đếm: pivot đối xứng 4/10, leg LuxAlgo 5/10 (phần lớn là port của cùng một script), Donchian 1/10.
- Gốc ICT: video «Month 05 — Defining Institutional Swing Points» (bài 1.5, mentorship 01/2017,
  ID YouTube `xRjKtUEKkSE`, [00:56]) theo trích dẫn trong thư viện kiến thức. Larry Williams
  định nghĩa đỉnh trung hạn = đỉnh ngắn hạn có hai đỉnh ngắn hạn thấp hơn hai bên; dài hạn tương
  tự ở cấp trên ([*Long-Term Secrets to Short-Term Trading*](https://www.wiley.com/en-us/Long+Term+Secrets+to+Short+Term+Trading,+2nd+Edition-p-9780470915738)).
- Chênh lệch quan trọng: «leg» một phía **không kiểm tra phía trái**, nên một nến chỉ cao hơn
  `len` nến sau cũng thành đỉnh. Hai trường phái cho ra chuỗi swing khác nhau trên cùng dữ liệu.

### 3.2. BOS, CHoCH, MSS — **đồng thuận cao về cơ chế, khác về điều kiện**

| Điểm | Đồng thuận | Khác biệt |
|---|---|---|
| Xác nhận phá | **Close** vượt mức: #1 (`close_break=True` mặc định), #2–#6 (`crossover(close, level)`), #9, lab | #7 dùng giá tick trực tiếp (không đợi đóng nến) |
| BOS vs CHoCH/MSS | Theo **xu hướng trước đó**: phá ngược xu hướng = CHoCH/MSS, cùng chiều = BOS (#2–#6, lab `swing_pivot`) | #1 dùng mẫu 4 swing liên tiếp |
| Mỗi mức phá mấy lần | **Một lần** (#2 `top_cross := false`, lab) | |
| Displacement | Không bắt buộc ở đa số | #7 yêu cầu displacement cho BOS; thư viện kiến thức định nghĩa **MSS = CHoCH + displacement + để lại FVG** |

- Thuật ngữ: ICT dùng **MSS**; «CHoCH» là thuật ngữ cộng đồng SMC. LuxAlgo ICT Concepts ghi
  rõ MSS là «thuật ngữ của ICT cho cái người khác gọi là CHoCH».
- ⚠ Định nghĩa «MSS phải có displacement + FVG» **chưa tìm được video gốc**: hai nguồn thư viện
  kiến thức dẫn cho nó (`ICT-2017-MSS`, `ICT-2017-DISPLACEMENT`) không có ID video hay mốc thời
  gian (mục 4.1).

### 3.3. Fair Value Gap — **đồng thuận cao nhất**

- Lõi chung ở mọi cài đặt: tăng khi `low[i] > high[i−2]`, giảm khi `high[i] < low[i−2]`.
- Khác biệt:

| Cài đặt | Điều kiện thêm | Gắn nhãn tại nến |
|---|---|---|
| #1 | nến giữa cùng màu (close > open) | **nến giữa** → nhìn trước 1 nến nếu dùng để backtest |
| #2 | close nến giữa vượt high nến 1 + độ lớn > 2× trung bình tích luỹ | nến 3 |
| #7 | khoảng hở ≥ tỷ lệ ATR thích ứng | nến 3 |
| #9 | không | **nến 3** (đúng nhân quả) |

- «FVG đã lấp» là **nhãn kết quả dùng tương lai**, không phải tín hiệu. Nghiên cứu mục 5.1 từng
  mắc lỗi này: 187 719 sự kiện nhìn tương lai tới 60 nến.

### 3.4. Order block — **chia hai trường phái, cần đọc thêm nhiều nhất**

| Trường phái | Nến được chọn | Cài đặt |
|---|---|---|
| Nến cực trị trong nhịp | OB tăng = nến có **low thấp nhất** giữa swing và nến phá (bỏ nến biến động quá lớn); OB giảm đối xứng | #2 (`storeOrdeBlock`), #6 (sau khi sửa lỗi), #1 gần giống |
| Nến ngược màu cuối cùng | OB tăng = **nến giảm cuối** trước cú phá/displacement | #7 (kèm displacement 2/3 tiêu chí), #9 |
| Gốc ICT (có dẫn video) | **Chuỗi nến cùng màu liên tiếp** ngay trước cú bứt là **một** khối; **chỉ thân nến**; «mean threshold» tính trên thân gộp; xác nhận khi giá vượt đầu xa của khối; nến thân nhỏ nằm lọt trong thân nến bên cạnh thì loại | Thư viện kiến thức, dẫn `ICT-2016-PROPULSION-BLOCK` [02:37–03:48], `ICT-2017-SWING-BEAR-SETUPS` [05:53–19:26] |

- Nghiên cứu mục 5.1 ghi nhận chính họ từng lấy **sai nến** (cực trị ngược) và không bỏ OB đã
  bị mitigate. Đây là lỗi dễ mắc nhất khi dịch sang code.

### 3.5. Thanh khoản, bằng giá (EQH/EQL), sweep

| Khái niệm | Cài đặt | Định nghĩa |
|---|---|---|
| EQH/EQL | #2 | hai pivot liên tiếp (độ dài 3) chênh < **0.1 × ATR** |
| | #3 | chênh < ATR(10) / (10 / margin) |
| | #1 | chênh < `range_percent` × (max − min **toàn dataset**) → **nhìn tương lai** |
| Sweep | #3 (nguyên bản) | close **đi vào** vùng thanh khoản — không cần quay lại |
| | #6 (định nghĩa lại) | xuyên qua mức ≥ X·ATR rồi close quay lại trong ≤ Z nến; gắn nhãn ở nến quay lại |
| | thư viện kiến thức | wick vượt + close quay lại, wick ≥ 60% biên độ nến — tự ghi là «định lượng phổ biến, ICT dạy bằng mắt» |
| | lab `c2_cisd_research` | nến H4 quét low/high nến trước rồi close quay lại, so sánh strict |

- Cơ chế nền (không phải ICT) có bằng chứng học thuật: lệnh stop-loss tập trung ở mức tròn/hỗ
  trợ–kháng cự và làm giá tăng tốc khi mức bị phá ([Osler 2003](https://onlinelibrary.wiley.com/doi/abs/10.1111/1540-6261.00588),
  [Osler 2005](https://ideas.repec.org/a/eee/jimfin/v24y2005i2p219-241.html)); mức hỗ trợ/kháng
  cự trùng chỗ sổ lệnh dày ([Kavajecz & Odders-White 2004](https://academic.oup.com/rfs/article-abstract/17/4/1043/1570736)).

### 3.6. Displacement — **không có định nghĩa gốc định lượng**

| Nguồn | Định nghĩa |
|---|---|
| #3 LuxAlgo ICT | chuỗi nến cùng chiều, thân lớn, bóng ngắn (tự mô tả qua tự tương quan và cụm biến động) |
| #7 | đạt 2/3: biên độ ≥ k·ATR (k thích ứng, mặc định 1.5); thân ≥ 60% biên độ; nến sau có thân ≥ 0.4·ATR |
| Thư viện kiến thức | chấm 5 yếu tố (thân/biên độ, bóng ngược, thân so với trung bình, có FVG, nến tiếp diễn) → 5–15 điểm; nguồn **không có video** |

→ Mọi ngưỡng đang lưu hành đều là lựa chọn của người code. Lab phải coi displacement là
**tham số thí nghiệm có phiên bản**, không gọi là «định nghĩa ICT».

### 3.7. Killzone, premium/discount

- Killzone (giờ New York, phải xử lý đổi giờ mùa hè), theo #3: New York 07–09, London Open
  02–05, London Close 10–12, Asia 20:00. Silver Bullet: 03–04, 10–11, 14–15 (thư viện kiến thức).
- ⚠ Mâu thuẫn trong chính ICT: London killzone 01–05 NY (video 2017, `UpyS34voILk` [02:58]) vs
  02–05 NY (video 2021) — thư viện ghi nhận cả hai, chưa thống nhất.
- Premium/discount ở #2 lấy từ cực trị **mở rộng toàn lịch sử**; nghiên cứu mục 5.1 chỉ ra trên
  16 năm, mức từ 2010 vẫn neo vùng năm 2026. Nên dùng dealing range theo swing gần nhất.

---

## 4. Nguồn định nghĩa gốc và độ tin cậy

### 4.1. Thư viện kiến thức ICT (LLM duy trì)

- 226 file khái niệm, mỗi file có định nghĩa, tiêu chí, JSON và mã nguồn trích dẫn
  ([`SOURCES.md`](https://github.com/SrsBlack/ict-knowledge-library/blob/master/SOURCES.md)).
- Chất lượng dẫn nguồn **không đều**. Kiểm tra 9 file cốt lõi (swing, MSS, MSS vs CHoCH,
  institutional swing points, displacement ×2, order block, sweep, FVG): **chỉ 3/12 mã nguồn
  được dẫn có ID video + mốc thời gian** (`ICT-2017-INSTITUTIONAL-SWING-POINTS`,
  `ICT-2016-PROPULSION-BLOCK`, `ICT-2017-SWING-BEAR-SETUPS`). 9/12 còn lại chỉ là nhãn (vd
  `ICT-2017-MSS — Market Structure Shift formalized vs CHoCH.`).
- Cách dùng đúng: lấy ID video + mốc thời gian để **xem lại tận nơi**; bỏ qua các con số
  (60% wick, thang 5–15 điểm) khi file không trỏ tới video.

### 4.2. Nguồn chính thức

- Kênh [The Inner Circle Trader](https://www.youtube.com/@InnerCircleTrader); playlist
  [2022 ICT Mentorship](https://www.youtube.com/playlist?list=PLVgHx4Z63paYiFGQ56PjTF1PGePL3r69s);
  ICT [khuyên thứ tự học](https://x.com/I_Am_The_ICT/status/1665331476060151809): 2022 Mentorship →
  Market Maker Primer → 2023 Mentorship.
- Lưu ý từ thư viện: các video «Core Content» đăng năm 2022 thực chất là **mentorship 2017**
  (Month 05–12) — trích là tài liệu 2017.

---

## 5. Bằng chứng và benchmark

### 5.1. Kiểm định 44 khái niệm ICT/SMC — [harshatangirala/smc-ict-research](https://github.com/harshatangirala/smc-ict-research)

- Dịch toàn bộ khái niệm trong hai script LuxAlgo (SMC + ICT Concepts) sang Python; các mã thuộc
  S&P 500, nến ngày, 01/2010–06/2026; 8 horizon; kiểm soát nhiều giả thuyết Benjamini–Hochberg.
- Kết quả chính: so với **vào lệnh ngẫu nhiên có cấu trúc tương đương**, dùng phương sai
  calendar-time Newey–West, **0/44 khái niệm thắng ở mọi horizon (0/352 giả thuyết)**.
- Bài học phương pháp đáng áp dụng cho lab:
  - So với «lợi nhuận 0» thì 38/44 trông có ý nghĩa — chỉ vì trôi giá tăng của thị trường.
    **Chọn chuẩn so sánh quyết định kết luận.**
  - Tín hiệu SMC/ICT bắn đồng loạt trên nhiều mã cùng ngày; phương sai giả định độc lập bác bỏ
    nhầm 28–41% tín hiệu vô nghĩa.
  - Walk-forward 13 lượt: nhóm khái niệm tốt nhất trong mẫu (+61 bp) mất −39 bp năm sau.
  - Hai detector sweep **có nhịp quay lại** cho ước lượng dương lớn nhất (+11–12 bp / 10 ngày)
    nhưng không có ý nghĩa (p = 0.23, 0.29).
  - Họ công khai 7 lỗi của hai phiên bản trước (nhìn tương lai, OB sai nến, BPR không bao giờ
    thoả, NDOG bắn mọi nến…), và file [`docs/disambiguation.md`](https://github.com/harshatangirala/smc-ict-research/blob/master/docs/disambiguation.md)
    liệt kê **từng chỗ mơ hồ + lựa chọn + mức ảnh hưởng**.
- Giới hạn: chưa bình duyệt; chỉ nến ngày cổ phiếu Mỹ; **loại killzone** (khái niệm trong
  phiên) — trong khi ICT dạy chủ yếu trên khung trong ngày và FX/chỉ số/vàng.
- Một blog độc lập ([StatOasis](https://statoasis.com/overfit/research/ict-backtest-what-survives))
  cũng báo không có lợi thế đáng kể trên SPY/QQQ/DIA/IWM — chưa kiểm tra phương pháp.

### 5.2. Nhận diện đỉnh/đáy và điểm đổi trạng thái (lớp nền)

| Nghiên cứu | Nội dung | Ý nghĩa cho lab |
|---|---|---|
| [van den Burg & Williams 2020](https://arxiv.org/abs/2003.06222), [TCPDBench](https://github.com/alan-turing-institute/TCPDBench) | 14 thuật toán change-point trên 37 chuỗi thật, 5 người gán nhãn mỗi chuỗi. Cài mặc định: binseg/PELT tốt nhất nhưng **không thuật toán nào thắng có ý nghĩa baseline «không có điểm đổi»**. Khi dò tham số (oracle): BOCPD tốt nhất | Detector regime (HMM/BOCPD dự kiến) phải có baseline «không đổi» và kiểm soát báo nhầm; nhãn nhiều người gán |
| [Grillenzoni 2012](https://www.researchgate.net/publication/264519093_Evaluation_of_Recursive_Detection_Methods_for_Turning_Points_in_Financial_Time_Series) | So 3 phương pháp đệ quy phát hiện đỉnh/đáy online; chọn tham số tối đa hoá «gain» giữa các đỉnh/đáy | Gợi ý thước đo không cần nhãn: biên độ thu được vs độ trễ |
| [Lo, Mamaysky & Wang 2000](https://www.nber.org/papers/w7613) | Nhận diện mẫu hình tự động bằng hồi quy kernel + kiểm định thống kê | Khuôn mẫu cho «định nghĩa hoá» thứ vốn nhìn bằng mắt |
| [Fu et al. — PIP](https://www.sciencedirect.com/science/article/abs/pii/S0952197607000577), [Fu 2011 (tổng quan)](https://dl.acm.org/doi/10.1016/j.engappai.2010.09.007) | Điểm quan trọng theo cảm nhận; tổng quan phân đoạn chuỗi thời gian | Phương án swing thay thế (không nhân quả, chỉ hồi cứu) |
| [Glattfelder et al. 2011](https://www.sg.ethz.ch/publications/2011/glattfelder2011patterns-in-high-frequency/Patterns_in_high_frequency_FX_data_discovery_of_12_empirical_scaling_laws.pdf) | Directional change, 12 quy luật tỷ lệ trên FX | Nền tảng của `dc_atr_structure` |

**Không tìm thấy** benchmark có nhãn chuẩn so sánh pivot vs ZigZag vs DC vs PIP cho swing tài
chính. → Cách đánh giá của lab (nhãn người gán + độ trễ xác nhận + kiểm tra nhân quả) là cần
thiết, không có sẵn để mượn.

---

## 6. Đề xuất áp dụng vào lab

Thứ tự xây theo phụ thuộc giữa các khái niệm và cách tách thành thành phần dùng chung:
[`kien_truc_luong_ict.md`](kien_truc_luong_ict.md) §4 và §6.

### 6.1. Nên code ngay (đồng thuận cao)

1. **Preset «ICT gốc» cho swing**: `swing_hierarchy` với left = right = 1 → cấp 1 = đỉnh/đáy
   ngắn hạn (STH/STL, 3 nến Larry Williams), cấp 2 = trung hạn (ITH/ITL). Không cần thuật toán mới.
   Có thể thêm cấp 3 (LTH/LTL) cùng quy tắc.
2. **FVG**: 3 nến, gắn nhãn tại **nến 3** (`confirmed_at` = close nến 3), ngưỡng tối thiểu
   k × ATR tuỳ chọn (mặc định 0 = định nghĩa gốc). «Đã lấp» chỉ là nhãn đánh giá có cửa sổ N.
3. **BOS/MSS**: phá bằng close, mỗi mức một lần, phân biệt theo xu hướng trước đó (lab đã có
   trong `swing_pivot`). Gắn **cờ displacement** như thuộc tính riêng thay vì đổi tên sự kiện —
   để đo được «MSS có displacement» vs «không có».

### 6.2. Phải cài cả hai phương án và so sánh (không chọn im lặng)

4. **Swing**: pivot đối xứng (lab) và «leg» một phía (dòng LuxAlgo) — hai detector riêng, cùng
   bộ nhãn, so độ trễ và mật độ.
5. **Order block**: (a) nến cực trị trong nhịp — LuxAlgo; (b) chuỗi nến ngược màu cuối, chỉ thân
   nến, xác nhận khi vượt đầu xa — ICT gốc. Ghi phiên bản.
6. **Sweep**: (a) wick vượt + close quay lại **cùng nến** (lab C2); (b) quay lại trong ≤ Z nến.

### 6.3. Đánh giá (mượn từ mục 5)

7. So với **vào lệnh ngẫu nhiên có cấu trúc tương đương**, không so với 0.
8. Phương sai theo thời gian lịch (tín hiệu bắn cùng lúc trên nhiều mã / nhiều khung).
9. Walk-forward; khoá tham số trước khi xem đoạn kiểm tra.
10. Test chống nhìn tương lai cho mọi detector mới (lab đã có mẫu prefix/suffix).

---

## 7. Chỗ mơ hồ — nên đọc thêm

Xếp theo mức ảnh hưởng tới kết quả.

| # | Chỗ mơ hồ | Vì sao quan trọng | Nên đọc / xem |
|---|---|---|---|
| 1 | **Order block là nến nào** | Ba cài đặt ra ba đáp án; nghiên cứu 5.1 từng lấy sai nến | Video `ICT-2016-PROPULSION-BLOCK`, `ICT-2017-SWING-BEAR-SETUPS` (mốc thời gian trong `SOURCES.md` thư viện); `storeOrdeBlock` trong source LuxAlgo SMC |
| 2 | **Displacement định lượng thế nào** | Quyết định MSS vs CHoCH, OB hợp lệ | Chưa có nguồn gốc định lượng; cần tìm đoạn ICT định nghĩa displacement trong 2022 Mentorship và ghi mốc thời gian |
| 3 | **Sweep có cần nhịp quay lại? trong bao nhiêu nến?** | Nghiên cứu 5.1: định nghĩa gốc LuxAlgo cho −4.5 bp, định nghĩa có quay lại cho +11–12 bp | `disambiguation.md` mục A7; video ICT về stop run / turtle soup |
| 4 | **Độ dài swing (1/1, 3/3, 5, 50)** | Đổi hoàn toàn mật độ cấu trúc | Video bài 1.5 `xRjKtUEKkSE`; sách Larry Williams (chương về điểm ngắn/trung/dài hạn) |
| 5 | **MSS có bắt buộc FVG không** | Thư viện nói có, nhưng không dẫn video | 2022 Mentorship — tìm đoạn ICT dùng từ «market structure shift» |
| 6 | **Ngưỡng bằng giá EQH/EQL** | 0.1 ATR vs margin ATR(10) vs % toàn dataset | Source LuxAlgo SMC/ICT Concepts; không có số gốc từ ICT |
| 7 | **Khung giờ killzone London** | 01–05 vs 02–05 NY | Hai video trong `SOURCES.md` (2017 `UpyS34voILk`, 2021 OTE scalping) |
| 8 | **Dealing range cho premium/discount** | Cực trị toàn lịch sử vs swing gần nhất | `disambiguation.md` mục A3 |

---

## 8. Giới hạn của nghiên cứu này

- **Chưa tự xem video ICT nào.** Các trích dẫn video lấy từ thư viện kiến thức (bản ghi
  Whisper do LLM tổng hợp); cần xem lại trước khi khoá định nghĩa.
- Chưa đọc hết source Pine của LuxAlgo ICT Concepts; định nghĩa của nó lấy từ mô tả chính thức
  và bản dịch trong nghiên cứu 5.1.
- Tìm kiếm GitHub theo từ khoá + số sao; có thể sót cài đặt tốt nhưng ít sao hoặc không gắn tag.
- Đếm «phổ biến» trên 10 cài đặt, nhiều cái cùng dòng dõi LuxAlgo — không phải mẫu độc lập.
- Không sao chép code nào vào lab. LuxAlgo (CC BY-NC-SA 4.0) chỉ đọc để so sánh định nghĩa.
