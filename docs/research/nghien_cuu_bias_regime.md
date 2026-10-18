# Nghiên cứu tài liệu: lớp kịch bản bias → regime (Trend / Range / Breakout / Uncertain) và router

Tài liệu nền cho [`plan_bias_regime.md`](../plans/plan_bias_regime.md) (giai đoạn 4 của `ict_structure`). Tra cứu web 07/10/2026; chưa chạy thí nghiệm nào trên dữ liệu của lab cho tài liệu này.

Ngày tra cứu: 07/10/2026. Đối tượng: XAUUSD, EURUSD; M15 với ngữ cảnh H1/H4/D; dữ liệu 2018–2025.
Mục đích: làm căn cứ cho plan của tầng regime. Lab không tối ưu P&L; ưu tiên định nghĩa vận hành, nhân quả, kiểm được, có null.

## Quy ước đọc

- **Mức tin cậy**
  - **A**: bài peer-review hoặc sách học thuật; đã đọc trực tiếp abstract hoặc toàn văn.
  - **B**: working paper, preprint, tài liệu kỹ thuật hoặc mã nguồn đã đọc trực tiếp; hoặc bài peer-review nhưng chỉ đọc qua bản tóm tắt thứ cấp.
  - **C**: blog, mô tả indicator TradingView, marketing; hoặc thông tin thứ cấp chưa xác minh được tận gốc.
- **Loại khẳng định**
  - **[TN]**: kết quả thực nghiệm có kiểm định.
  - **[PP]**: phương pháp hoặc định nghĩa.
  - **[YK]**: ý kiến, quy ước thực hành hoặc marketing; không có kiểm định.
- Nội dung đánh dấu «đề xuất» là suy luận của người viết cho lab, không phải kết luận của tài liệu.
- Bối cảnh lab (thuật toán, khung đánh giá, số liệu survey đã có) chỉ dùng để điều chỉnh mục 7; nguồn: `AGENTS.md`, [`plan_ict_structure.md`](../plans/plan_ict_structure.md), [`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md).

---

## 0. Tóm tắt điều hành

1. **Không có định nghĩa chuẩn cho «Trend/Range/Breakout».** Có ba họ cách làm:
   - Luật trên chỉ báo: ADX, CHOP, Kaufman ER, Donchian, variance ratio, Hurst. Ngưỡng phổ biến (ADX 20/25/40; CHOP 38.2/61.8) là quy ước của người thực hành, không có căn cứ thống kê.
   - Mô hình trạng thái ẩn: Markov-switching/HMM, HSMM, statistical jump model.
   - Phân đoạn dựa trên sự kiện: directional change, Lunde–Timmermann, Pagan–Sossounov, trend-scanning. Phần lớn họ này **nhìn về sau** nên chỉ dùng làm nhãn tham chiếu.
2. **Đánh đổi chung là độ trễ ↔ nhấp nháy (whipsaw).** HMM bị đặc tả sai thường lật trạng thái quá nhanh. Statistical jump model có hình phạt mỗi lần nhảy, giảm số lần đổi trạng thái từ khoảng 9.7 lần/năm xuống dưới 1 lần/năm trên dữ liệu ngày, nhưng độ trễ phát hiện khoảng nửa tháng. Một nghiên cứu khác báo trung vị trễ 25 ngày lịch.
3. **DC (Tsang) và thuật toán bull/bear của Lunde–Timmermann có cùng cấu trúc:** ngưỡng % (hoặc ATR) tính từ cực trị gần nhất.
   - Trạng thái tại **điểm xác nhận** (DCC) là nhân quả.
   - Trạng thái **gán ngược từ cực trị** là nhìn về sau.
   - Hệ quả: baseline DC của lab dùng được cả làm bộ phân loại nhân quả lẫn làm nhãn tham chiếu hậu kiểm, miễn là tách bạch hai cách dùng.
4. **Breakout:** bằng chứng mạnh nhất nằm ở vi cấu trúc FX.
   - Osler cho thấy lệnh take-profit tụ ở số tròn (giá dễ bật lại), còn stop-loss tụ ngay sau số tròn (khi bị phá thì giá chạy nhanh: price cascade).
   - Hiệu ứng có thật nhưng **nhỏ**: tần suất bật tại mức S/R được công bố cao hơn mức ngẫu nhiên khoảng 4–6 điểm %.
   - Với FX intraday, quy tắc phá biên **không** sinh lời trung bình (Curcio et al. 1997).
   - Không tìm thấy nghiên cứu học thuật nào phân biệt breakout thật/giả bằng cấu trúc kiểu ICT.
5. **ICT/SMC «daily bias»:** có nhiều bản mã hoá (thư viện Python `smartmoneyconcepts`, script TradingView), nhưng **không có kiểm định peer-review**.
   - Bản kiểm định hệ thống duy nhất tìm được là một preprint SSRN 2026, chỉ đọc qua tóm tắt thứ cấp. Preprint này kết luận «no evidence that ICT/SMC concepts work as literally taught»: quét thanh khoản dự báo **tiếp diễn**, không phải đảo chiều.
   - Điều này khớp với phát hiện của lab (order flow/shift ≈ ngẫu nhiên).
6. **Ghép bằng chứng khi ít nhãn:** nên chọn
   - điểm số trọng số đơn vị trên các nhóm bằng chứng **đã khử trùng lặp** (Dawes 1979);
   - máy trạng thái có hysteresis và thời gian giữ tối thiểu (hoặc hình phạt nhảy online);
   - lớp Uncertain hiểu theo nghĩa selective classification, báo cáo bằng đường **risk–coverage**.

   Naive Bayes/log-odds đẩy xác suất về 0/1 khi bằng chứng tương quan, mà các bằng chứng cấu trúc của lab tương quan mạnh. Dempster–Shafer phức tạp và có nghịch lý khi xung đột cao.
7. **Đánh giá không dùng P&L có sẵn công cụ:**
   - F1 theo điểm đổi với dung sai, covering metric, κ (lưu ý nghịch lý prevalence), concordance Harding–Pagan;
   - thời lượng đoạn, số lần lật;
   - so phân phối kết cục tương lai có điều kiện với không điều kiện (Lo–Mamaysky–Wang);
   - null dịch vòng (shift test) cho chuỗi trạng thái, null mức ngẫu nhiên (Osler), baseline «không có điểm đổi».

   Đây là baseline đánh bại nhiều thuật toán phát hiện điểm đổi trong benchmark của van den Burg & Williams.
8. **Router:** bằng chứng về chọn chiến lược theo regime chủ yếu ở mức phân bổ tài sản, dữ liệu ngày/tháng (momentum crashes, momentum turning points, regime-switching allocation).
   - **Không tìm được** bằng chứng chặt chẽ cho việc định tuyến pullback/mean-reversion ở M15 FX/vàng.
   - Một nghiên cứu «falsification» 2026 trên MNQ 5 phút: 0/14 họ tín hiệu OHLCV intraday vượt qua bộ tiêu chí.
   - Giá trị của router phụ thuộc vào tỉ lệ «thời lượng regime còn lại sau khi phát hiện».

---

## 1. Định nghĩa regime Trend / Range / Breakout trong tài liệu

### 1.1 Bảng so sánh

| Họ | Đầu vào | Độ trễ cố hữu | Nhân quả? | Điểm yếu chính | Có lớp «uncertain» không |
|---|---|---|---|---|---|
| ADX/DMI (Wilder 1978) | H, L, C; làm trơn kiểu Wilder 14 kỳ (hai lần) | Lớn; Wikipedia ghi rõ là chỉ báo trễ | Có | Ngưỡng 20/25/40 không có trích dẫn; không phân biệt range với chuyển tiếp | Ngầm: vùng ADX 20–25 |
| Choppiness Index (Dreiss) | ΣTR(1) / (MaxHi−MinLo) trên n nến, thang log, chuẩn 0–100 | Khoảng n nến | Có | 61.8/38.2 là «Fibonacci borrowings, not statistical guarantees»; không cho chiều | Vùng giữa 38.2–61.8 |
| Kaufman Efficiency Ratio | \|C_t − C_{t−n}\| / Σ\|ΔC\| | Khoảng n nến | Có | Nhạy với nhiễu bid-ask ở khung nhỏ; không có ngưỡng chuẩn | Không (phải tự đặt vùng chết) |
| Donchian / trading-range break | Max/min của n nến trước | Phá biên: tức thời; range: cần n nến | Có, nếu chỉ dùng nến đã đóng | Phá giả; n tuỳ ý | Không |
| Variance ratio (Lo–MacKinlay 1988) | Return nhiều kỳ so với 1 kỳ | Cửa sổ ước lượng dài | Có (cuốn chiếu) | Bid-ask bounce gây VR<1 giả ở tần số cao (Roll 1984); phương sai ước lượng lớn | Có: vùng không bác bỏ VR=1 |
| Hurst / R/S | Cửa sổ dài | Rất lớn | Có (cuốn chiếu) | R/S cổ điển lệch lên trong mẫu nhỏ (H>0.5 với Brownian hữu hạn); Lo 1991: hết bằng chứng nhớ dài khi kiểm soát phụ thuộc ngắn hạn | Có: khoảng tin cậy chứa 0.5 |
| Markov-switching / HMM (Hamilton 1989) | Return, vol hoặc đặc trưng | Xác suất lọc (filtered): trễ; xác suất làm trơn (smoothed): dùng tương lai | Filtered: có. Smoothed: **không** | Đặc tả sai thì lật quá nhanh; label switching khi fit lại; thời gian lưu trú buộc là phân phối hình học | Có: posterior max < ngưỡng |
| HSMM (Bulla & Bulla 2006) | Như HMM, thêm phân phối thời gian lưu trú | Như HMM | Filtered: có | Phức tạp hơn | Như HMM |
| Statistical jump model (Bemporad et al. 2018; Nystrup, Kolm, Lindström) | Đặc trưng thời gian đã chuẩn hoá | Trễ phát hiện khoảng nửa tháng (dữ liệu ngày) | Có bản online/greedy | λ phải chọn; bài ứng dụng chọn λ theo Sharpe | CJM cho vector xác suất |
| Directional change (Tsang et al.) | Giá; ngưỡng θ (%, hoặc ATR trong lab) | Xác nhận khi giá đi θ từ cực trị, nên trễ đúng bằng θ | Tại DCC: có. Gán từ cực trị: **không** | θ chi phối mọi thứ; regime theo Tsang là normal/abnormal, không phải trend/range | Không trực tiếp |
| Lunde–Timmermann / Pagan–Sossounov | Giá; ngưỡng λ1/λ2 hoặc luật kiểm duyệt | Hậu kiểm | **Không** (dùng làm nhãn tham chiếu) | Tham số định nghĩa luôn «sự thật» | Không |
| Trend-scanning (López de Prado) | Hồi quy giá theo thời gian trên [t, t+L], chọn t-stat lớn nhất | Nhìn tới L nến tương lai | **Không** | Chỉ là nhãn | Có: \|t\| < ngưỡng thì nhãn 0 |
| BOCPD (Adams & MacKay 2007) | Chuỗi bất kỳ, mô hình hậu nghiệm liên hợp | Online, có posterior của run-length | Có | Cần prior hazard; nhạy với mô hình quan sát | Có: posterior run-length phân tán |
| Đồng thuận momentum chậm/nhanh (Garg et al.) | Hai tín hiệu momentum | Trễ của tín hiệu chậm | Có | Chỉ cho chiều | **Có**: Correction/Rebound (hai tín hiệu bất đồng) chiếm hơn 1/3 thời gian |

### 1.2 Chi tiết theo họ

**(a) Luật trên chỉ báo** [PP/YK]

- **ADX.** Wilder (1978).
  - Wikipedia: «a trend must have established itself before the ADX will generate a signal».
  - Ngưỡng «below 20 … weak trend, above 40 … strong trend» không có nguồn trích.
  - Nguồn: https://en.wikipedia.org/wiki/Average_directional_movement_index. Tin cậy **B** (tài liệu kỹ thuật).
- **CHOP.**
  - Công thức: `100·log10(ΣATR(1),n / (MaxHi(n) − MinLo(n))) / log10(n)`.
  - Ngưỡng 61.8/38.2 là «Fibonacci borrowings, not statistical guarantees».
  - Nguồn: https://www.luxalgo.com/library/concept/choppiness-index.md ; https://in.tradingview.com/support/solutions/43000501980 . Tin cậy **C/B**.
- **Kaufman ER.** `ER = |C_t − C_{t−P}| / Σ|C_k − C_{k−1}|`, xuất phát từ Kaufman, *Smarter Trading* (1995).
  - Nguồn: https://ta-lib.org/functions/er.html . Tin cậy **B**.
- **Variance ratio.** Lo & MacKinlay (1988), RFS 1:41–66. Bác bỏ random walk với return tuần.
  - Nguồn: https://web.mit.edu/~alo/www/Papers/lo-mackinlay-88.html . Tin cậy **A**.
  - Lưu ý tần số cao: chi phí giao dịch tạo hiệp phương sai âm giữa các thay đổi giá liên tiếp (Roll 1984, JF 39(4)). Ở M15, VR<1 có thể chỉ là bid-ask bounce chứ không phải «range».
  - Nguồn Roll: https://www.bauer.uh.edu/rsusmel/phd/roll1984.pdf . Tin cậy **A**.
- **Hurst.**
  - Lo (1991, Econometrica 59) đưa ra R/S hiệu chỉnh: «no evidence of long-range dependence … once short-range dependence is taken into account». Nguồn: https://web.mit.edu/~alo/www/Papers/lo-91.html (**A**).
  - Couillard & Davison (2005, Physica A 348): Brownian hữu hạn luôn cho H>0.5, dễ diễn giải nhầm thành có nhớ. Nguồn: https://ideas.repec.org/a/eee/phsmap/v348y2005icp404-418.html (**A**, đọc qua tóm tắt).

**(b) Mô hình thống kê** [PP/TN]

- **Markov-switching** (Hamilton 1989, Econometrica 57:357–384): https://ideas.repec.org/a/ecm/emetrp/v57y1989i2p357-84.html (**A**).
  - Xác suất lọc chỉ dùng dữ liệu đến t. Xác suất làm trơn dùng toàn mẫu, nên «nhìn đẹp» hơn mọi thứ đạt được thời gian thực.
  - Tổng quan: Ang & Timmermann (2012), *Regime Changes and Financial Markets*: https://www.nber.org/papers/w17182 (**A**).
- **Nystrup** (seminar NYU 2019): «When a hidden Markov model is misspecified or misestimated, it often leads to unrealistically rapid switching dynamics.»
  - Nguồn: https://math.nyu.edu/dynamic/calendars/seminars/mathematical-finance-seminar/3061/ (**B**).
- **Statistical jump model.**
  - Khung tổng quát: Bemporad, Breschi, Piga, Boyd, «Fitting Jump Models», Automatica 96 (2018): https://arxiv.org/pdf/1711.09220 (**A**).
  - Hàm mục tiêu: `Σ l(x_t, θ_{s_t}) + λ Σ 1{s_{t−1} ≠ s_t}`. Khi λ=0 thì tương đương k-means.
  - **Online:** Nystrup, Kolm, Lindström, «Greedy online classification of persistent market states using realized intraday volatility features», JFDS 2(3), 2020.
    - Bộ phân loại tham lam xác định trạng thái của quan sát mới «without parsing historical observations».
    - Theo tóm tắt: độ chính xác cao hơn MLE đặc tả đúng trong đa số kịch bản; chuỗi trạng thái bền hơn; đặc trưng intraday cải thiện độ chính xác.
    - Nguồn: https://orbit.dtu.dk/en/publications/greedy-online-classification-of-persistent-market-states-using-re/ (**B**, đọc qua tóm tắt).
  - **Ứng dụng có số liệu:** Shu, Yu, Mulvey, arXiv 2402.05272: https://arxiv.org/html/2402.05272v3 (**B**, preprint).
    - Số lần đổi trạng thái mỗi năm: k-means (λ=0) 9.7; λ=5 còn 2.7; λ lớn còn dưới 1. HMM thuần 8.5/năm; HMM có cửa sổ làm trơn k=20 là 2.0/năm.
    - Độ trễ: «a latency of approximately half a month». Bài dẫn Nystrup et al. (2018a, JPM 44(2)): «the median [latency] in detecting regime changes is 25 (calendar) days».
    - Trễ giao dịch 1 ngày.
    - **λ chọn bằng Sharpe tối đa** trên cửa sổ validation. Lab không thể sao chép bước này vì không dùng P&L.
  - **Continuous JM.** Aydınhan, Kolm, Mulvey, Shu (2024, Annals of OR): trạng thái thành vector xác suất, thêm «mode loss» đẩy xác suất về đỉnh simplex. Nguồn: https://papers.ssrn.com/abstract=4556048 (**A**, đọc qua tóm tắt).
  - **Mã nguồn mở:** `jumpmodels` có `.predict_online()` / `.predict_proba_online()` tách khỏi `.predict()`. Nguồn: https://github.com/Yizhan-Oliver-Shu/jump-models (**B**).
- **HSMM.** Bulla & Bulla (2006, CSDA 51): HSMM với thời gian lưu trú nhị thức âm mô tả ACF suy giảm chậm tốt hơn HMM, vốn bị buộc vào phân phối hình học.
  - Nguồn: https://ideas.repec.org/a/eee/csdana/v51y2006i4p2192-2209.html (**A**, đọc qua tóm tắt).
- **Bull/bear 4 trạng thái.** Maheu, McCurdy, Song, «Components of bull and bear markets: bull corrections and bear rallies»: mỗi regime có hai trạng thái con (ví dụ bull correction có mean âm). Đây là tương tự gần nhất với «Trend + pullback».
  - Nguồn: https://www.economics.utoronto.ca/public/workingPapers/tecipa-402.pdf (**B**).
- **BOCPD.** Adams & MacKay (2007) tính phân phối hậu nghiệm của run-length (thời gian kể từ điểm đổi gần nhất) bằng message passing online.
  - Nguồn: https://arxiv.org/abs/0710.3742 (**A/B**).

**(c) Directional change** [PP]

- Định nghĩa theo Wu & Han (arXiv 2309.15383, đã đọc toàn văn):
  - Up-DC xác nhận khi `p(t) ≥ P_EXT·(1+θ)`; down-DC khi `p(t) ≤ P_EXT·(1−θ)`.
  - Điểm xác nhận gọi là DCC. Overshoot (OS) kéo dài đến DC kế tiếp. «a DC event is not always followed by OS events».
  - Bài tối ưu θ bằng Bayesian Optimization trên tick của 8 cặp FX, và dùng HMM trên chỉ báo R_DC để nhận diện regime «abnormal».
  - Nguồn: https://arxiv.org/pdf/2309.15383 (**B**).
- Chỉ báo DC (TMV, T, R): https://blog.quantinsti.com/directional-change-trading/ (**C**).
- Chen & Tsang:
  - «Classification of Normal and Abnormal Regimes in Financial Markets», Algorithms 11(12):202 (2018). Sách *Detecting Regime Change in Computational Finance* (CRC 2021).
  - Regime theo nghĩa **normal/abnormal**, không phải trend/range.
  - Kiểm chứng chủ yếu định tính: thời điểm đổi regime quanh Brexit «consistent with the political developments».
  - Nguồn: https://repository.essex.ac.uk/25877/ ; https://www.taylorfrancis.com/books/9780367536282 (**B**: không mở được toàn văn MDPI, lỗi 403).
- **Hàm ý:** baseline DC theo ATR của lab là phiên bản «trend/range» do lab tự định nghĩa, không phải định nghĩa gốc của Tsang. Khi viết plan cần ghi rõ điều này.

**(d) Phân đoạn hậu kiểm** [PP] (xem thêm mục 5c)

- **Trend-scanning:** hồi quy trên [t, t+L], chọn cửa sổ có \|t-value\| lớn nhất. Nhãn {−1, 0, 1} khi đặt ngưỡng t tối thiểu.
  - Tài liệu ghi rõ là phương pháp nhìn về tương lai (look-forward).
  - Nguồn: https://random-docs.readthedocs.io/en/latest/implementations/labeling_trend_scanning.html ; https://mlfinpy.readthedocs.io/en/latest/_modules/mlfinpy/labeling/trend_scanning.html (**B**). Gốc: López de Prado, *Machine Learning for Asset Managers* (CUP).
- **Garg, Goulding, Harvey, Mazzoleni,** «Momentum Turning Points» (bản 12/2020; toàn văn đã đọc):
  - «Slow signals fail to react quickly to changes in trend while fast signals are often false alarms.»
  - Khi momentum chậm và nhanh bất đồng thì gọi là Correction/Rebound. Hai trạng thái này «combined occur more than one-third of the time».
  - Nguồn: https://benny.aeaweb.org/conference/2021/preliminary/paper/492Ds6fk (**B**: working paper; bản journal chưa kiểm).

### 1.3 Hàm ý cho lab (mục 1)

- Mọi luật chỉ báo đều cần **vùng chết** (dead zone) để có lớp Uncertain. Ngưỡng nên đặt theo **phân vị trên tập dev** (cố định trước) thay vì 20/25/61.8, vì các con số đó không có căn cứ.
- **Hai baseline thống kê đáng thêm:**
  - jump model online: có lớp xác suất (CJM) và tham số λ trực tiếp điều khiển độ bền;
  - BOCPD: cung cấp «xác suất vừa có điểm đổi», dùng làm ứng viên cho Breakout và Uncertain.
- Ở M15 không nên dùng VR/Hurst cửa sổ ngắn làm bằng chứng chính, vì sai lệch mẫu nhỏ và bid-ask bounce.
- Mô hình bull/bear 4 trạng thái (Maheu et al.) và đồng thuận chậm/nhanh (Garg) đều gợi ý một cấu trúc phù hợp: **regime chính (HTF) × pha con (LTF)**. Pullback là pha con của Trend chứ không phải regime riêng; bất đồng giữa hai khung là Uncertain.

---

## 2. Breakout: định nghĩa và kiểm định

### 2.1 Định nghĩa vận hành trong tài liệu [PP]

- **Trading-range break (TRB).** Brock, Lakonishok, LeBaron (1992, JF 47(5)): tín hiệu mua khi giá vượt đỉnh của n kỳ trước, bán khi thủng đáy.
  - Kiểm định bằng bootstrap với các null random walk, AR(1), GARCH-M, EGARCH.
  - Kết quả trên DJIA 1897–1986: lợi nhuận sau tín hiệu mua cao hơn sau tín hiệu bán, «not consistent with four popular null models».
  - Nguồn: https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html (**A**, đọc qua tóm tắt).
  - Sullivan, Timmermann, White (1999, JF) kiểm lại bằng White's Reality Check để điều chỉnh data-snooping trên toàn bộ «vũ trụ» luật. Nguồn: https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf (**A**).
  - Theo hiểu biết của người viết, STW thấy lợi thế không duy trì ở giai đoạn ngoài mẫu sau đó. **Chưa xác minh trực tiếp trong phiên này.**
- **Opening range breakout (ORB):** phá đỉnh/đáy của phiên đầu ngày vượt một ngưỡng định trước.
  - Holmberg, Lönnbark, Lundström (2013, FRL 10(1)): ORB trên dầu thô 1983–2011 cho lợi nhuận dương có ý nghĩa, nhưng «mostly generated in the last decade (2000–2011)». Nguồn: https://ideas.repec.org/a/eee/finlet/v10y2013i1p27-33.html (**A**, đọc qua tóm tắt).
  - Mesfin (arXiv 2605.04004, 2026): 14 họ tín hiệu intraday OHLCV (có ORB) trên MNQ 5 phút, 947 ngày 2021–2025, walk-forward. Năm tiêu chí: t≥2, ≥30 lệnh mỗi fold, dương sau chi phí, cùng chiều qua các năm 2023/24/25, permutation p<0.001. «None passed all five.» Nguồn: https://arxiv.org/abs/2605.04004 (**B**: preprint, một tác giả).
- **Phá vỡ mức S/R do chuyên gia công bố, FX.**
  - Curcio & Goodhart (1992, LSE FMG DP 142), ba tỉ giá: «trading range breaks do generate profitable signals, even after the inclusion of transaction costs». Nguồn: https://www.fmg.ac.uk/publications/discussion-papers/when-supportresistance-levels-are-broken-can-profits-be-made (**B**).
  - Curcio, Goodhart, Guillaume, Payne (1997, IJFE 2(4)), FX **intraday**, luật lọc do nhà phân tích cung cấp: có thể có lời «in periods of trends, this was not the case on average»; kết quả còn yếu hơn khi tính chi phí. Nguồn: https://ideas.repec.org/a/ijf/ijfiec/v2y1997i4p267-80.html (**A**, đọc qua tóm tắt).
  - Như vậy bằng chứng trái chiều: dữ liệu ngày tích cực hơn, dữ liệu intraday tiêu cực.

### 2.2 Cơ chế vi cấu trúc: căn cứ tốt nhất cho «sweep vs run» [TN]

- **Osler (2000), FRBNY EPR** (đã đọc toàn văn):
  - Dữ liệu: mức S/R do 6 công ty công bố, 01/1996–03/1998; giá 1 phút cho DEM, JPY, GBP.
  - Null: **10 000 bộ mức S/R nhân tạo** chọn ngẫu nhiên trong biên độ ngày.
  - Kết quả: tần suất bật tại mức được công bố cao hơn mức nhân tạo khoảng 4.2 điểm % (mark), 5.6 (yen), 4.0 (pound); công ty tốt nhất cao hơn 9.2 điểm %. Hiệu lực kéo dài ít nhất 5 ngày làm việc.
  - «Độ mạnh» (strength) mà các công ty tự công bố **không có ý nghĩa**: chênh lệch đa phần âm.
  - Bài dẫn Curcio et al. (1997) rằng giả thuyết «giá chạy nhanh khi mức bị phá» «is not true on average for currencies, but may hold true during periods of strong trending».
  - Nguồn: https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.html (**A**).
- **Osler (2003, JF 58(5); bản staff report 125 đã đọc):**
  - 9 667 lệnh có điều kiện của một ngân hàng.
  - Take-profit tụ mạnh ở số tròn (9.3% khớp đúng tại «00», so với 4.4% của stop-loss). Stop-loss mua tụ ngay **trên** số tròn, stop-loss bán tụ ngay **dưới**.
  - Mô phỏng: tần suất bật tăng khoảng 3.4 điểm %, tương đương 4.6 điểm % trên dữ liệu thật; khi không bật thì biên độ đi tiếp lớn hơn có ý nghĩa.
  - Nguồn: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf (**A**).
- **Osler (2005, JIMF):** «stop-loss orders propagate trends and are sometimes triggered in waves, contributing to price cascades». Dữ liệu: sổ lệnh RBS 8/1999–4/2000.
  - Nguồn: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.html (**A**, đọc qua tóm tắt).
- **Chung & Bellotti (arXiv 2101.07410, 2021):** dùng thuật toán heuristic tìm mức S/R trên giá intraday.
  - Mức có nhiều lần bật trước đó thì dễ bật lại hơn; xác suất bật **giảm theo thời gian**; hiện tượng «not explained simply by AR(1) processes».
  - Nguồn: https://arxiv.org/abs/2101.07410 (**B**).

### 2.3 Breakout thật/giả bằng cấu trúc

- **Không tìm được** nghiên cứu peer-review nào dùng chuỗi đỉnh/đáy, displacement hay FVG để phân biệt breakout thật/giả với một null rõ ràng.
- Nguồn gần nhất là preprint SSRN Mahadzva (2026), xem mục 3: quét thanh khoản dự báo **tiếp diễn** trong 65/66 lần chọn fold. Chiều này **ngược** với cách diễn giải «sweep = false breakout = đảo chiều». **Chưa xác minh tận gốc.**
- Mô hình Osler cho dự báo hai phía: dừng/bật ở số tròn (take-profit) và chạy nhanh sau khi vượt (stop-loss). Vì vậy khác biệt «sweep vs run» có cơ sở vi cấu trúc, nhưng **độ lớn hiệu ứng chỉ vài điểm %**.
- Lab đo được lợi thế trong ±2 điểm %, cùng bậc độ lớn với Osler. Vì vậy **cần tính lực thống kê** (minimum detectable effect) trước khi kết luận «không có gì».

### 2.4 Hàm ý cho lab (mục 2)

- Breakout nên là **trạng thái chuyển tiếp có hạn thời gian**, gắn với một range đã được xác nhận trước đó. Không nên coi là regime ngang hàng với Trend/Range. Định nghĩa đề xuất ở mục 7.
- **Null bắt buộc:**
  - *Null mức ngẫu nhiên kiểu Osler:* so hành vi sau khi vượt biên range thật với hành vi sau khi vượt các mức ngẫu nhiên cùng khoảng cách (theo ATR), cùng giờ, cùng tam phân vị ATR. Tương thích với `matched_hour_atr_v1` của lab.
  - *Baseline «không bao giờ có breakout»:* xem mục 5.
- Định nghĩa false breakout phải quy định trước: đóng cửa quay lại trong range trong vòng m nến và/hoặc không tạo cực trị mới trong B nến.

---

## 3. ICT/SMC «daily bias» / HTF bias

### 3.1 Cách người thực hành ghép [YK]

Mô tả từ các nguồn practitioner (**C**):

- Xác định hướng mở rộng tuần trên chart tuần.
- Tìm thanh khoản lộ rõ theo hướng đó (DOL: đỉnh/đáy cũ, PDH/PDL, equal highs/lows).
- Tìm imbalance (FVG) trên đường đi.
- Ưu tiên các ngày có tin.

Các thành phần thường gặp:

- chuỗi HH/HL hay LH/LL ở HTF;
- premium/discount trong dealing range;
- giá mở ngày/tuần làm mốc premium/discount;
- IPDA lookback 20/40/60 ngày;
- «Power of 3/AMD»: các bản script chia giờ cố định 19:00–01:00 / 01:00–07:00 / 07:00–13:00 EST;
- weekly templates (ví dụ «Tuesday low»).

Nguồn:
- https://www.luxalgo.com/library/concept/session-and-weekly-profiles.md
- https://in.tradingview.com/script/fee72raV-ICT-IPDA-Lookback
- https://tr.tradingview.com/scripts/power
- https://arjoio.notion.site/Episode-40-Keys-To-Daily-Bias-dbdf128247734f379cb71ffc9fdb4aaf (không đọc được nội dung)

### 3.2 Các bản đã định lượng hoá (mã mở) [PP]

| Bản | Luật chính | Kiểm định |
|---|---|---|
| `smartmoneyconcepts` (Python, joshyattridge) | swing high/low = cao nhất trong `swing_length` nến **trước và sau**; BOS/CHoCH (`close_break`); FVG 3 nến; liquidity (`range_percent`); `previous_high_low`; sessions | Không có kiểm định. Swing dùng **nến tương lai** (nhìn về sau) và không có cảnh báo trong tài liệu |
| Daily Bias Indicator [MTF] (kenkwong0628, TradingView) | Hôm qua đóng cửa trên đỉnh hôm kia, hoặc test đáy hôm kia mà không phá: bullish; đối xứng cho bearish | Không có |
| ICT Daily Bias (LuxAlgo library) | Kiểu «Previous H/L»: râu chạm PDH/PDL thì kỳ vọng đảo chiều; thân đóng ngoài thì kỳ vọng tiếp diễn | Không có |
| Session & Weekly Profiles (LuxAlgo) | Bias tự động: giá trên giá mở tuần là nghiêng tăng | Không có (có disclaimer) |
| LuxAlgo Smart Money Concepts | Internal vs swing structure, BOS/CHoCH, OB, EQH/EQL, vùng premium/discount | Không có |
| Quantitative SMC Framework (FeelsStrategy) | Điểm confluence 0–100: kích thước/ATR 0–30, displacement/ATR 0–30, volume 10–20, chồng FVG 0–20 | Không có |

Nguồn bảng:
- https://github.com/joshyattridge/smart-money-concepts (**B**)
- https://tradingview.com/script/tKNbGEja (**C**)
- https://www.luxalgo.com/library/indicator/R4Jv6gnc-ict-daily-bias/ (**C**)
- https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-LUX/ (**C**)
- https://de.tradingview.com/script/T6BgcudH-Quantitative-Smart-Money-Concepts-Framework/ (**C**)

### 3.3 Có kiểm định không

- **Không tìm được bài peer-review nào.** Theo một blog có tra Crossref, không có bài báo journal nào kiểm định các khái niệm OB/FVG/sweep/BOS/CHoCH.
- **Mahadzva (2026),** «Smart Money or Costly Folklore? A Systematic Evaluation of ICT/Smart-Money-Concepts Trading Rules in G10 FX», SSRN 7430998.
  - Mô tả (thứ cấp): mã hoá 6 luật; walk-forward, bootstrap, permutation, holdout trên EURUSD, GBPUSD, AUDUSD, USDJPY intraday.
  - «We find no evidence that ICT/SMC concepts work as literally taught».
  - Ba luật quét thanh khoản độc lập đồng ý trong 65/66 lần chọn fold rằng mức bị quét dự báo **tiếp diễn**.
  - Kết quả nổi bật (EURUSD H1, đánh ngược) có p=0.0192 nhưng «fails a Deflated Sharpe Ratio check».
  - Nguồn: https://doi.org/10.2139/ssrn.7430998 (SSRN chặn truy cập, 403), dẫn lại qua https://thortradecopier.com/blog/does-ict-smart-money-concepts-work . Tin cậy **C** cho đến khi đọc được bản gốc.
- **Mô phỏng random walk của blog trên** (tự làm, seed 42, 10⁶ nến): 83.4% FVG tăng được lấp lại trong 20 nến, so với 83.5% của mức ngẫu nhiên cùng khoảng cách. Ý nghĩa: «FVG được lấp» không phải bằng chứng nếu không có null. **C**, nhưng phép so sánh tự lặp lại được dễ dàng.
- **Bindra (2026)** báo 78% win rate trên 473 lệnh FVG (vàng và 3 cặp FX, năm 2025), không có out-of-sample, baseline hay chi phí. Theo thứ cấp; thuộc loại [YK].

### 3.4 Hàm ý cho lab (mục 3)

- Các định nghĩa bias kiểu ICT đều là luật đơn giản trên PDH/PDL, giá mở và cấu trúc HTF. Lab đã có đủ thành phần: order, pd_bias, DOL, PDH/PDL.
- Không có nguồn nào đưa ra **trọng số** có căn cứ. Mọi cách ghép đều là lựa chọn của người thiết kế, nên phải đặt tên biến thể và chấm như nhau.
- Kết quả trong tài liệu (khái niệm như được dạy không hơn ngẫu nhiên; sweep dự báo tiếp diễn) **nhất quán** với phát hiện của lab.
  - Vì vậy không nên để bias ICT quyết định Trend/Range một mình.
  - Nên dùng làm **một nhóm bằng chứng**, đánh giá bằng đóng góp cận biên so với baseline thống kê (ER/ADX/DC).
- **Cảnh báo kỹ thuật:** nếu tham khảo `smartmoneyconcepts`, phải thay swing hai phía bằng swing được xác nhận trễ `swing_length` nến và chỉ phát sự kiện ở nến xác nhận.

---

## 4. Ghép nhiều bằng chứng thành một trạng thái

### 4.1 Các phương án và bằng chứng

| Phương án | Căn cứ | Ưu khi ít/không nhãn | Nhược |
|---|---|---|---|
| Điểm số trọng số đơn vị (unit weights) | Dawes (1979): mô hình tuyến tính «improper», tức trọng số đều hoặc theo trực giác, «quite robust» và hơn phán đoán lâm sàng | Không cần nhãn; khó overfit; dễ giải thích | Phải chuẩn hoá đặc trưng; vẫn cần ngưỡng |
| Log-odds / naive Bayes | Domingos & Pazzani (1997): vẫn có thể tối ưu theo lỗi 0-1 dù vi phạm độc lập. Niculescu-Mizil & Caruana (2005): naive Bayes đẩy xác suất về 0 và 1 | Cộng dồn bằng chứng tự nhiên | Cần likelihood (tức là cần nhãn); bằng chứng tương quan bị **đếm trùng**, nên tự tin quá mức và lớp Uncertain bị co lại |
| Dempster–Shafer | Ví dụ của Zadeh: hai nguồn gần như mâu thuẫn hoàn toàn thì luật Dempster cho kết quả phản trực giác. «there is no theoretical way to decide beforehand if one can trust the result» | Biểu diễn được «không biết» | Phức tạp, khó kiểm, nhạy khi xung đột; không cần thiết cho lab |
| Cây quyết định nhỏ viết tay | Thực hành phổ biến | Minh bạch, kiểm được từng nhánh, gán lý do | Ngưỡng cứng; dễ «garden of forking paths» |
| Máy trạng thái có hysteresis / thời gian giữ tối thiểu | Kỹ thuật hai ngưỡng vào/ra và debounce theo số nến (tài liệu kỹ thuật, không có bằng chứng tài chính riêng). Tương đương thống kê: hình phạt nhảy λ (Nystrup) | Chống nhấp nháy; tham số diễn giải được (số nến) | **Thêm độ trễ**; phải đo đánh đổi |
| Hình phạt nhảy online (jump model greedy) | Nystrup et al. (2020): online, bền hơn HMM | Không cần nhãn; λ trực tiếp là «chi phí một lần đổi» | Cần đặc trưng chuẩn hoá; chọn λ không dùng P&L phải có tiêu chí khác |
| HSMM | Bulla & Bulla (2006) | Mô hình hoá được thời lượng | Phức tạp, ước lượng khó |
| Weak supervision (Snorkel; Dawid–Skene) | Snorkel học mô hình sinh trên các labeling function «using no ground-truth data, learning instead from the agreements and disagreements». Dawid–Skene (1979): EM ước lượng sai số từng người gán khi không có nhãn đúng | Biến ADX, CHOP, ER, DC, HMM, cấu trúc thành các «người gán» nhiễu; ước lượng độ chính xác tương đối của từng cái | Giả định độc lập có điều kiện (Snorkel có thể học tương quan); kết quả vẫn cần một bộ nhãn tay nhỏ để kiểm |
| Selective classification / reject option | Chow (1970): luật từ chối tối ưu và quan hệ lỗi–tỉ lệ từ chối. Geifman & El-Yaniv (2017): đường **risk–coverage** | Định nghĩa Uncertain có nguyên tắc: từ chối khi độ tin thấp; báo cáo coverage | Cần một thước đo «risk», tức là nhãn hoặc kết cục tương lai |
| Adaptive conformal (Gibbs & Candès 2021) | Đảm bảo tần suất bao phủ dài hạn dưới dịch chuyển phân phối | Cho tập dự đoán; tập có hơn một lớp thì Uncertain | Cần kết cục quan sát được sau đó; phức tạp hơn mức cần |

Nguồn bảng:
- Dawes: https://www.cmu.edu/dietrich/sds/docs/dawes/the-robust-beauty-of-improper-linear-models-in-decision-making.pdf (**A**)
- Domingos & Pazzani: https://doi.org/10.1023/A:1007413511361 (**A**)
- Niculescu-Mizil & Caruana: https://mlanthology.org/icml/2005/niculescumizil2005icml-predicting (**A**)
- Zadeh/DS: https://arxiv.org/pdf/math/0404371 ; https://www.onera.fr/sites/default/files/297/C111.pdf (**B**)
- Hysteresis/debounce: https://kaira.readthedocs.io/en/dev/generated/kaira.models.binary.soft_bit_thresholding.HysteresisThresholder.html (**C**, tài liệu kỹ thuật)
- Snorkel: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7075849/ (**A**)
- Dawid–Skene: https://ideas.repec.org/a/bla/jorssc/v28y1979i1p20-28.html (**A**)
- Chow: https://researcher.watson.ibm.com/publications/on-optimum-recognition-error-and-reject-tradeoff (**A**)
- Geifman & El-Yaniv: https://arxiv.org/abs/1705.08500 (**A**)
- Gibbs & Candès: https://arxiv.org/abs/2106.00170 (**A**)

### 4.2 Hàm ý cho lab (mục 4)

1. **Khử trùng lặp bằng chứng trước khi ghép.** Order M15/H1/H4, protected level, order flow và shift đều sinh từ cùng chuỗi swing.
   - Đề xuất gom thành 3–4 nhóm, mỗi nhóm một phiếu:
     - (i) hiệu quả xu hướng thống kê: ER/ADX/CHOP;
     - (ii) cấu trúc LTF: order + protected trên M15;
     - (iii) ngữ cảnh HTF: H1/H4 order, pd_bias, DOL;
     - (iv) trạng thái range: dealing range, độ rộng/ATR, số lần chạm.
   - Đo tương quan giữa các nhóm trên dev để chứng minh chúng không trùng.
2. **Hai biến thể đặt tên** (theo §3.2 của lab):
   - (A) cây quyết định viết tay + hysteresis;
   - (B) điểm trọng số đơn vị theo nhóm + vùng chết + thời gian giữ tối thiểu.
   - Bộ so sánh thống kê: jump model online.
3. **Uncertain là một lớp có lý do,** không phải «phần còn lại». Ghi `reason` (xung đột HTF/LTF, điểm trong vùng chết, vừa có shift chưa xác nhận…). Báo **coverage** (tỉ lệ thời gian không Uncertain) song song với mọi thước đo chất lượng.
4. **Hysteresis phải đi kèm phép đo độ trễ:** vẽ đường số lần lật/ngày theo trung vị trễ phát hiện cho một lưới tham số giữ tối thiểu hoặc λ, rồi chọn điểm trên «khuỷu» **trước khi** xem tập test.
5. Weak supervision (Dawid–Skene/Snorkel) là cách hợp lý để **xếp hạng** độ tin của các baseline khi chưa có nhãn regime. Không dùng nó làm «sự thật».

---

## 5. Đánh giá bộ phân loại regime khi không dùng P&L

### 5.a So với nhãn tay

- **Cohen's κ.** Có hai nghịch lý (Feinstein & Cicchetti 1990, J Clin Epidemiol):
  - đồng thuận cao nhưng κ thấp khi một lớp chiếm ưu thế;
  - marginal lệch làm κ thay đổi.
  - Lab có Range ≤0.2% và Uncertain chiếm phần lớn thời gian, nên κ tổng **sẽ gây hiểu lầm**. Phải báo kèm ma trận nhầm lẫn và F1 từng lớp.
  - Nguồn: J Clin Epidemiol 43:543–549, DOI https://doi.org/10.1016/0895-4356(90)90158-L ; mô tả: https://scholarhub.vn/publication/:slug/99d46fd7-7674-4728-9c1a-4edb5f5f85c5 (**A**, đọc qua tóm tắt).
- **Đánh giá theo điểm đổi và theo đoạn.** van den Burg & Williams (2020, arXiv 2003.06222), benchmark TCPD: 37 chuỗi, mỗi chuỗi 5 người gán.
  - F1 với dung sai M=5. Precision chỉ tính false positive khi phát hiện không khớp **bất kỳ** người gán nào; recall lấy trung bình theo từng người gán.
  - **Covering metric:** trung bình có trọng số của Jaccard tốt nhất cho mỗi đoạn thật.
  - Phát hiện quan trọng: phương pháp «zero» (không dự báo điểm đổi nào) «outperforms many of the other methods» trong cấu hình mặc định.
  - Nguồn: https://arxiv.org/abs/2003.06222 ; https://ar5iv.labs.arxiv.org/html/2003.06222 (**A/B**).
- **Precision/recall theo khoảng.** Tatbul et al. (NeurIPS 2018) mở rộng P/R cho sự kiện có độ dài: phần thưởng tồn tại, chồng lấn, vị trí.
  - Nguồn: https://arxiv.org/abs/1803.03639 (**A**).
- **Thoả thuận giữa người gán.** Cần ít nhất hai người gán độc lập trên một tập con để biết **trần** đạt được; mỗi chuỗi TCPD có 5 người gán vì lý do này. Osler (2000) cũng cho thấy các công ty chuyên nghiệp «do not agree extensively with each other».

### 5.b Không cần nhãn

1. **Độ bền:**
   - số lần đổi trạng thái/ngày hoặc /năm (Shu et al. dùng đúng thước đo này để so JM với HMM);
   - phân phối độ dài đoạn (trung vị, IQR, P90);
   - tỉ lệ thời gian mỗi trạng thái;
   - tỉ lệ đoạn ngắn hơn k nến (đoạn «nhấp nháy»).
2. **Độ tách của kết cục tương lai, có kiểm nhân quả.**
   - Đặc trưng tính đến t; kết cục đo trên (t, t+h].
   - Phương pháp mẫu: Lo, Mamaysky, Wang (2000, JF): so phân phối return **có điều kiện** theo mẫu hình với phân phối **không điều kiện** bằng các kiểm định goodness-of-fit (theo tóm tắt; chi tiết KS/χ² cần đọc bản gốc).
   - Nguồn: https://www.nber.org/papers/w7613 ; https://web.mit.edu/~alo/www/Papers/techanal.html (**A**).
3. **Kiểm soát nhiễu do biến động.** Biến động có tự tương quan dương (volatility clustering; Cont 2001, QF 1(2)), nên **bất kỳ** bộ phân loại nào tương quan với ATR cũng sẽ «tách» được biên độ tương lai.
   - Phải đo độ tách **trong từng tầng phân vị ATR**, hoặc trên phần dư sau khi hồi quy theo vol hiện tại.
   - Nguồn: https://ideas.repec.org/a/taf/quantf/v1y2001i2p223-236.html (**A**).
4. **Null cho chuỗi trạng thái:**
   - **Shift test** (Harris 2020, arXiv 2012.06862): dịch chuỗi trạng thái (dừng) đi −N…N bước so với chuỗi kết cục. «If the series are independent, the unshifted value is in the top m shifted values with probability at most m/(N+1).» Giữ nguyên cấu trúc tự tương quan và phân phối độ dài đoạn. Nguồn: https://arxiv.org/abs/2012.06862 (**B**). Lưu ý: dịch nhỏ hơn thời lượng tự tương quan thì vẫn «gần khớp», nên phải loại các độ dịch nhỏ.
   - **Stationary bootstrap** (Politis & Romano 1994, JASA 89) cho khoảng tin cậy khi dữ liệu phụ thuộc. Nguồn: https://arch.readthedocs.io/en/latest/bootstrap/timeseries-bootstraps.html (**B**, tài liệu triển khai).
   - **Null mức ngẫu nhiên** (Osler 2000): xem mục 2.
   - **Baseline «zero» / «giữ nguyên trạng thái cũ»** cho breakout và điểm đổi (van den Burg & Williams).
5. **So với mô hình đơn giản.** Concordance index của Harding & Pagan (2002):
   - `I = (1/T) Σ [S_x S_y + (1−S_x)(1−S_y)]`, so với giá trị kỳ vọng khi độc lập `S̄_x S̄_y + (1−S̄_x)(1−S̄_y)`.
   - Dùng đo mức trùng của bộ phân loại mới với ADX, DC, HMM, tách theo từng lớp nhị phân.
   - Nguồn: https://metricgate.com/calculator/harding-pagan-concordance-statistic (**C**, tài liệu công thức; gốc là J Monetary Econ 2002).
6. **Ổn định ngoài mẫu:**
   - tham số cố định trên dev, đo trên test;
   - tách theo năm 2018–2025 và theo tài sản;
   - **cùng dấu qua các năm** (một tiêu chí của Mesfin 2026);
   - độ nhạy tham số (vùng ổn định thay vì đỉnh nhọn).

### 5.c Nhãn hậu kiểm làm «sự thật tham chiếu» và bẫy rò rỉ

- **Lunde & Timmermann (2004, JBES),** «Duration dependence in stock prices». Thuật toán theo mô tả trong phụ lục của Ntantamis (2010, CREATES RP 2010-51; đã đọc):
  - Từ một đỉnh cục bộ, nếu giá giảm λ2 trước khi lập đỉnh mới thì xác định đáy, và gán bear **từ t0+1**.
  - Từ một đáy, giá tăng λ1 thì gán bull.
  - «A conventional value used in the financial press is 0.2 for both thresholds.»
  - **Đây chính là DC với θ bất đối xứng.** Nhãn được gán **ngược** từ cực trị, nên là nhìn về sau.
  - Nguồn: https://repec.econ.au.dk/repec/creates/rp/10/rp10_51.pdf (**A/B**); CEPR DP4104: https://cepr.org/publications/DP4104 .
- **Pagan & Sossounov (2003, J Applied Econometrics 18(1)):** chuyển thuật toán Bry–Boschan sang chu kỳ thị trường.
  - Dùng cực trị trong cửa sổ hai phía và các luật kiểm duyệt độ dài pha/chu kỳ tối thiểu. Tham số cụ thể **chưa xác minh trong phiên này**.
  - Đặc điểm cần nhớ: cửa sổ hai phía cũng là nhìn về sau.
  - Nguồn: https://ideas.repec.org/a/jae/japmet/v18y2003i1p23-46.html (**A**, đọc qua tóm tắt); cài đặt R: https://ftp.fau.de/cran/web/packages/bbdetection/index.html (**B**).
- **Trend-scanning** và **zigzag** cũng nhìn về sau (mục 1).
- **Các bẫy:**
  1. **Rò rỉ khi chỉnh ngưỡng theo nhãn nhìn về sau.** Nếu ngưỡng bộ phân loại được tối ưu để khớp nhãn trend-scanning hoặc DC hậu kiểm trên cùng dữ liệu thì sẽ overfit. Cửa sổ nhãn chồng nhau làm k-fold thường rò rỉ. López de Prado đề xuất **purging** (bỏ mẫu train nằm trong khoảng hình thành nhãn test) và **embargo** (bỏ thêm một đoạn sau test). Nguồn: https://en.wikipedia.org/wiki/Purged_cross-validation (**B**); gốc: *Advances in Financial Machine Learning* (2018), chương 7.
  2. **«Sự thật» phụ thuộc tham số.** Mỗi θ hoặc λ cho một bộ nhãn khác. Phải báo kết quả trên một **họ** θ (ví dụ 1, 2, 4 ATR) chứ không chọn một θ «đẹp».
  3. **Đặc trưng vô tình nhìn về sau:** swing hai phía, xác suất HMM làm trơn, nến HTF đang hình thành, chuẩn hoá z-score bằng thống kê toàn mẫu, PDH/PDL lấy từ ngày hiện tại.
  4. **Dùng nhãn hậu kiểm để đo «độ trễ» là đúng cách,** vì đó chính là thông tin mà bộ phân loại thời gian thực không có. Còn dùng nó làm «độ chính xác» theo từng nến sẽ phạt mọi bộ phân loại nhân quả một cách có hệ thống ở đầu mỗi đoạn. Nên đo **trễ phát hiện** và **tỉ lệ báo động giả** thay cho accuracy theo nến.

### 5.d Hàm ý cho lab (mục 5)

- Lab hiện chỉ có nhãn điểm và matcher điểm, theo khung đánh giá hiện có ([`danh_gia_thuat_toan.md`](../guides/danh_gia_thuat_toan.md)). Có thể **chuyển ranh giới regime thành sự kiện điểm** (REGIME_CHANGE với loại chuyển) để dùng lại P/R/F1 có dung sai và đo trễ, giống cách TCPD làm với điểm đổi.
- Covering metric và F1 từng lớp theo đoạn cần nhãn đoạn, tức là phải mở rộng schema nhãn. Việc này để sau, khi đã có rubric regime.
- Null cho trạng thái: **shift test** trên chuỗi trạng thái so với kết cục tương lai. Đây là thứ lab đang thiếu (null hiện chỉ dành cho sự kiện điểm).

---

## 6. Router regime → chiến lược

### 6.1 Bằng chứng về chọn chiến lược theo regime [TN, chủ yếu dữ liệu ngày/tháng]

- **Daniel & Moskowitz (2016, JFE 122(2)),** «Momentum Crashes»: momentum «can experience infrequent and persistent strings of negative returns … partly forecastable. They occur in 'panic' states … and are contemporaneous with market rebounds». Chiến lược momentum động «approximately doubles the alpha and Sharpe Ratio».
  - Nguồn: https://www.nber.org/papers/w20439 (**A**).
- **Garg et al.** (mục 1): đánh đổi Type I/II theo tốc độ tín hiệu; chiến lược chọn tốc độ động cho hiệu quả ngoài mẫu trên thị trường cổ phiếu (**B**).
- **Kritzman, Page, Turkington (2012, FAJ 68(3)):** Markov-switching trên chỉ số «turbulence», lạm phát, tăng trưởng. Phân bổ động hơn tĩnh trong backtest, «especially for investors who seek to avoid large losses».
  - Nguồn: https://ideas.repec.org/a/taf/ufajxx/v68y2012i3p22-39.html (**A**, đọc qua tóm tắt).
- **Shu et al. (2024)** và **Nystrup et al.:** phân bổ theo regime của jump model, có trễ 1 ngày và chi phí giao dịch (**B**).
- **Zakamulin & Giner (2024, J Asset Management 25(4)):**
  - Trong mô hình hai trạng thái Markov, luật trend-following tối ưu là EMA.
  - Khi xác suất kết thúc trạng thái tăng theo tuổi (semi-Markov), luật tối ưu giống MACD.
  - Nghĩa là **luật tối ưu phụ thuộc vào phân phối thời lượng regime.**
  - Nguồn: https://ideas.repec.org/a/pal/assmgt/v25y2024i4d10.1057_s41260-024-00357-0.html (**A**, đọc qua tóm tắt).
- **Blanchard & Goffard (2024, HAL):** HMM Bayes trên return ngày; tín hiệu giả dẫn tới nhiều lệnh và tăng chi phí; «a simple smoothing technique» làm giảm tín hiệu giả.
  - Nguồn: https://ideas.repec.org/p/hal/wpaper/hal-04608937.html (**B**).
- **Intraday:**
  - Gao, Han, Li, Zhou (2018, JFE): return nửa giờ đầu dự báo nửa giờ cuối trên ETF S&P 500 1993–2013. Nguồn: https://ideas.repec.org/a/eee/jfinec/v129y2018i2p394-414.html (**A**).
  - Elaut, Frömmel, Lampaert (2018, JFM 37): hiệu ứng tương tự ở RUB-USD. Nguồn: https://ideas.repec.org/a/eee/finmar/v37y2018icp35-51.html (**A**, đọc qua tóm tắt).
  - Hai bài này cho thấy cấu trúc intraday phụ thuộc **khung giờ phiên**, nên regime theo phiên là biến cần kiểm soát.
- **Ngược lại,** Mesfin (2026, MNQ) cho thấy 0/14 họ tín hiệu intraday OHLCV vượt bộ tiêu chí (**B**).

**Không tìm được:** bằng chứng peer-review về việc định tuyến «trend pullback vs range mean reversion vs đứng ngoài» bằng bộ phân loại regime ở M5–H1 cho FX/vàng. Các nguồn tìm thấy là blog/marketing (ví dụ https://www.luxalgo.com/library/concept/strategy-switching-and-rotation.md, **C**).

### 6.2 Chi phí của độ trễ nhận diện

- Dữ liệu ngày: trung vị trễ khoảng 25 ngày lịch (Nystrup et al. 2018a, dẫn trong Shu et al.); Shu et al. báo khoảng nửa tháng.
- Garg et al. diễn đạt dưới dạng đánh đổi: tín hiệu chậm thì lỗi loại II (bỏ lỡ điểm quay), tín hiệu nhanh thì lỗi loại I (báo động giả).
- **Đề xuất chỉ số cho lab:** «tuổi thọ còn lại sau khi phát hiện» = (độ dài đoạn tham chiếu − trễ phát hiện) / độ dài đoạn.
  - Nếu trung vị chỉ số này thấp, router không có gì để khai thác, dù bộ phân loại «đúng».
  - Lab đã đo order flow: đoạn một chiều trung vị khoảng 13 giờ, khoảng 52 nến M15. Đó là thang để so với trễ.

### 6.3 Rủi ro overfitting khi chọn ngưỡng

- **Data-snooping:** STW (1999) và White's Reality Check: phải điều chỉnh theo **toàn bộ** tập luật/ngưỡng đã thử.
- **Probability of backtest overfitting** (Bailey, Borwein, López de Prado, Zhu, J Computational Finance 2015): CSCV ước lượng xác suất cấu hình tốt nhất trong mẫu nằm dưới trung vị ngoài mẫu. Áp dụng được cho **bất kỳ** thước đo nào, không riêng Sharpe.
  - Nguồn: https://papers.ssrn.com/abstract=2326253 ; R: https://cran.hafro.is/web/packages/pbo/readme/README.html (**A**).
- Shu et al. chọn λ theo Sharpe; Wu & Han chọn θ bằng Bayesian Optimization trên lợi nhuận. Cả hai là ví dụ chọn ngưỡng theo mục tiêu kinh tế. Lab cần **tiêu chí thay thế không dùng P&L** (xem mục 7).

---

## 7. Gợi ý cụ thể cho plan của lab

### 7.1 Định nghĩa vận hành (đề xuất; mọi tham số cố định trên dev trước khi xem test)

**Trạng thái riêng, không gộp vào Uncertain** (khớp AGENTS.md:42): `DATA_GAP` và `WARMUP`, dùng cho dữ liệu thiếu, khởi động, nến HTF chưa đóng đủ.

| Trạng thái | Điều kiện vào (ví dụ cấu trúc, ngưỡng theo phân vị dev) | Điều kiện ra | Ghi chú |
|---|---|---|---|
| TREND_UP / DOWN | Cấu trúc LTF và HTF cùng chiều (order M15 + H1); mức được bảo vệ còn nguyên; nhóm hiệu quả thống kê (ER hoặc ADX + DI) ≥ phân vị cao | Mức bảo vệ bị close vượt; hoặc nhóm hiệu quả rơi xuống dưới ngưỡng **ra** (thấp hơn ngưỡng vào); hoặc HTF đổi chiều | Pullback là pha con, không phải regime (Maheu et al.) |
| RANGE | ER/CHOP ở vùng «chop» liên tục ≥ N nến; dealing range có độ rộng/ATR trong khoảng [a, b]; có chạm hai phía | Close ngoài biên ± k·ATR | Baseline dc_regime cho Range ≤0.2% vì điều kiện quá chặt. Nới thành 2+2 chạm, hoặc dùng nhóm thống kê, rồi đo lại |
| BREAKOUT_UP / DOWN (chuyển tiếp, tối đa B nến) | Trạng thái trước là RANGE ≥ N nến; nến **đã đóng** ngoài biên ≥ k·ATR; thân displacement ≥ m·ATR | Sau B nến: thành TREND nếu có follow-through (cực trị mới, không đóng lại vào range); thành sự kiện `FAILED_BREAKOUT` rồi RANGE/UNCERTAIN nếu đóng lại trong range trong m nến | Phát sự kiện riêng để đánh giá như sự kiện điểm |
| UNCERTAIN (có `reason`) | Xung đột HTF/LTF (tương tự Correction/Rebound của Garg); điểm trong vùng chết; vừa có shift/sweep chưa xác nhận; vừa thoát range | Theo hysteresis + thời gian giữ tối thiểu | Báo coverage |

- **Router:** TREND chọn Trend Pullback; RANGE chọn Range Mean Reversion; BREAKOUT và UNCERTAIN chọn No Trade. Riêng BREAKOUT chỉ chuyển sang Trend Pullback khi đã thành TREND.
- **Hai biến thể đặt tên:**
  - `v_tree`: cây viết tay như bảng trên;
  - `v_score`: điểm trọng số đơn vị theo 3–4 nhóm + vùng chết.
- **Bộ so sánh:** dc_regime (đo lại trên dataset đúng giờ), indicator_baseline, hmm_online, và **jump model online** (`jumpmodels.predict_online`) làm baseline thống kê.
- **Gán nghĩa cho trạng thái HMM/JM:** đặt luật xếp hạng theo mean/vol trên dev, cố định trước, rồi áp lên test. Không đặt tên lại sau khi xem kết quả (vấn đề label switching; Stephens 2000, https://ideas.repec.org/a/bla/jorssb/v62y2000i4p795-809.html).

### 7.2 Bộ phép đo nên có (không P&L)

| # | Phép đo | Cách tính | Null / baseline | Ghi chú |
|---|---|---|---|---|
| M1 | Tỉ lệ thời gian, coverage | % nến mỗi trạng thái; coverage = 1 − %UNCERTAIN − %DATA_GAP | So với các baseline | Báo cho từng tài sản và từng năm |
| M2 | Độ bền | Số lần đổi/ngày; trung vị/IQR/P90 độ dài đoạn; % đoạn < k nến | jump model với vài λ; HMM | Theo mẫu run_stats sẵn có |
| M3 | Trễ phát hiện + báo động giả | Ranh giới đoạn tham chiếu hậu kiểm (DC/Lunde–Timmermann với một **họ** θ = 1, 2, 4 ATR; trend-scanning với vài L) so với sự kiện REGIME_CHANGE nhân quả. Trễ (nến), P/R/F1 có dung sai | Baseline «zero»; dc_regime; ADX | Dùng matcher điểm sẵn có |
| M4 | Tuổi thọ còn lại sau phát hiện | (độ dài đoạn tham chiếu − trễ) / độ dài | — | Chỉ số «router có gì để khai thác» |
| M5 | Độ tách kết cục tương lai | Với h ∈ {4, 16, 64} nến: ER tương lai, biên độ/ATR_t, \|return\|/ATR_t, first-passage +k·ATR trước −k·ATR, «về giữa range trước khi phá biên». Hiệu ứng (Cliff's δ hoặc khác biệt trung vị) kèm CI bằng block bootstrap | **Shift test** trên chuỗi trạng thái; trong từng tầng ATR; so baseline | Kiểm soát volatility clustering bắt buộc |
| M6 | Giá trị cận biên của bằng chứng ICT | M5 cho `v_score` có và không có nhóm HTF/ICT | Shift test; phân tích lực (MDE) | Kỳ vọng hiệu ứng nhỏ (Osler: vài điểm %) |
| M7 | Breakout | Tỉ lệ follow-through và FAILED_BREAKOUT; biên độ sau phá | **Mức ngẫu nhiên Osler** (cùng khoảng cách ATR, cùng giờ NY, cùng tam phân vị ATR, tức là `matched_hour_atr_v1` mở rộng) | Định nghĩa false breakout cố định trước |
| M8 | Đồng thuận giữa các bộ phân loại | Concordance Harding–Pagan theo từng lớp nhị phân; ma trận nhầm lẫn giữa các bộ | Giá trị kỳ vọng khi độc lập | Không ai là «sự thật»; chỉ để mô tả |
| M9 | So nhãn tay (khi có) | Ma trận nhầm lẫn, F1 từng lớp, macro-F1, κ (kèm cảnh báo prevalence); F1 điểm đổi có dung sai; covering | Thoả thuận giữa ≥2 người gán làm trần | Cần rubric regime |
| M10 | Selective classification | Đường risk–coverage: risk = lỗi so với nhãn tay, hoặc so với tiêu chí kết cục M5 | — | Chọn vùng chết theo đường này trên dev |
| M11 | Ổn định | Tham số cố định trên dev, đo trên test; tách theo năm 2018–2025 và theo XAU/EUR; cùng dấu qua các năm | — | Bảng độ nhạy tham số: tìm vùng phẳng |
| M12 | Kiểm nhân quả | Chạy lại với dữ liệu bị cắt ở t, so trạng thái tại t (prefix test); kiểm không dùng nến HTF đang hình thành | — | Lab đo được: nến HTF đang hình thành làm thứ tự sai khoảng 6% |
| M13 | Overfitting ngưỡng | Liệt kê **mọi** cấu hình đã thử; PBO/CSCV trên thước đo chính (ví dụ M5) | — | Hoặc chọn ngưỡng theo phân vị cố định, không tối ưu |

### 7.3 Lỗi phương pháp phổ biến cần tránh

1. **Nhìn về sau ẩn:**
   - swing xác nhận bằng nến tương lai nhưng gán vào nến pivot;
   - DC gán ngược từ cực trị;
   - xác suất HMM làm trơn, hoặc fit HMM trên toàn mẫu;
   - z-score bằng thống kê toàn mẫu;
   - nến H1/H4/D đang hình thành;
   - PDH/PDL lấy từ ngày hiện tại;
   - mốc phiên khác nhau (ny_1700 hay utc_epoch: lab đo được thứ tự H4 khác 30%).
2. **Lẫn biến động với regime:** mọi độ tách biên độ tương lai phải được kiểm trong từng tầng ATR (Cont 2001).
3. **Đếm trùng bằng chứng tương quan** khi cộng điểm hoặc log-odds (Niculescu-Mizil & Caruana 2005). Uncertain sẽ bị co lại một cách giả tạo.
4. **κ và accuracy theo nến dưới mất cân bằng lớp** (Feinstein & Cicchetti). Accuracy theo nến còn phạt cấu trúc của mọi bộ phân loại nhân quả ở đầu đoạn.
5. **Cỡ mẫu hiệu dụng là số đoạn/sự kiện, không phải số nến.** Dùng block bootstrap hoặc shift test, không dùng t-test theo nến.
6. **Chọn ngưỡng sau khi xem kết quả** (garden of forking paths). Phải cố định trên dev và khoá test (dev 01–08/2024, test 09–12/2024 theo §6.3 của lab), đồng thời ghi số cấu hình đã thử.
7. **«Sự thật» hậu kiểm với một tham số duy nhất.** Phải báo trên một họ θ/L.
8. **Bỏ qua baseline «zero»/«giữ trạng thái»:** baseline này thắng nhiều thuật toán trong TCPD.
9. **Vi cấu trúc ở M15:**
   - bid-ask bounce tạo đảo chiều giả (Roll 1984);
   - spread giãn lúc rollover và gap cuối tuần tạo «sweep» giả. Phải gắn cờ và cho vào DATA_GAP hoặc loại khỏi thống kê, không cho vào Range/Uncertain.
10. **Gộp lỗi dữ liệu vào Uncertain,** mâu thuẫn với AGENTS.md:42. Cần trạng thái riêng.
11. **Kết luận «không có hiệu ứng» khi thiếu lực thống kê.** Hiệu ứng thật trong tài liệu chỉ vài điểm %. Phải báo MDE cùng kết quả âm tính.
12. **Diễn giải bias ICT theo sách:** bằng chứng (thứ cấp) cho thấy sweep dẫn đến tiếp diễn chứ không phải đảo chiều. Luật «sweep thì đảo chiều» phải được kiểm chứ không mặc định.

### 7.4 Thứ tự công việc gợi ý

1. Đo lại baseline (dc_regime, indicator_baseline, hmm_online) trên dataset đúng giờ: M1, M2.
2. Dựng nhãn tham chiếu hậu kiểm (họ θ, họ L) và đo M3, M4 cho các baseline. Đây cũng là kiểm tra «router có không gian không».
3. Viết spec `v_tree` / `v_score` + DATA_GAP/WARMUP + hysteresis. Chạy prefix test (M12).
4. Thêm baseline jump model online, với λ chọn theo tiêu chí không P&L. Ví dụ: λ nhỏ nhất đạt trung vị độ dài đoạn ≥ X nến trên dev.
5. Đo M5–M8 với shift test và null mức ngẫu nhiên. Báo MDE.
6. Viết rubric regime, lấy hai người gán, rồi M9, M10.
7. Đo M11, M13 trên test đã khoá. Mọi kết luận chỉ ở dạng «khác baseline X với CI», không nói «tốt hơn» khi chưa có nhãn.

---

## Phụ lục A: không tìm được hoặc chưa xác minh

- **Không tìm được:**
  - nghiên cứu peer-review kiểm định ICT/SMC (daily bias, IPDA, AMD, OB, FVG);
  - nghiên cứu phân biệt breakout thật/giả bằng cấu trúc với null rõ ràng;
  - bằng chứng chặt chẽ cho router regime → pullback/mean-reversion ở M15 FX/vàng;
  - thống kê đáng tin về xác suất ngày lấy PDH/PDL.
- **Chưa xác minh tận gốc:**
  - Mahadzva 2026 (SSRN bị chặn; chỉ qua blog);
  - các tham số cụ thể của Pagan–Sossounov;
  - kết quả ngoài mẫu của STW 1999 (theo trí nhớ);
  - toàn văn Chen & Tsang 2018 (MDPI chặn);
  - chi tiết KS/χ² của Lo–Mamaysky–Wang (chỉ đọc tóm tắt).
- Nystrup, Lindström, Madsen, «Learning hidden Markov models with persistent states by penalizing jumps» (thường được dẫn là Expert Systems with Applications, 2020): tìm được abstract seminar, **chưa thấy trang journal**.

## Phụ lục B: tài liệu đã tải để đọc

- Đã đọc toàn văn (bản tải về không lưu trong repo; URL ở các mục trên): Wu & Han 2023 (DC), Osler 2000 EPR, Osler SR125, Ntantamis 2010 (thuật toán Lunde–Timmermann), Garg et al. 2020.
- Chỉ trích văn bản bằng `pdftotext`; không chạy mã nào từ các tệp này.
