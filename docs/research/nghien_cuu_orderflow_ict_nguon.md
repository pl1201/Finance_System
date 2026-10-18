<!-- Phụ lục nguồn của docs/research/nghien_cuu_orderflow_ict.md — tổng hợp tài liệu web ngày 06/10/2026; số liệu đo trên dữ liệu lab nằm ở tài liệu chính. -->

# Order flow kiểu ICT/SMC, đọc thuần từ giá: tổng hợp nguồn cho lab

Ngày tổng hợp: 2026-10-06. Phạm vi: «institutional order flow» theo nghĩa ICT (đọc từ nến/giá + thanh khoản), **không** phải orderflow vi cấu trúc (footprint/delta/DOM).

## Cách làm và cách đọc độ tin cậy

- **Nguồn gốc ICT (mức A):** Tôi tải phụ đề của các video trên kênh YouTube chính thức **«The Inner Circle Trader»** (đã kiểm tra `ownerChannelName` của từng video). Có khoảng 50 video: Core Content 2016 (ghi hình 2016, ICT tải lại lên YouTube năm 2022), toàn bộ 41 tập 2022 Mentorship, các bài 2023 và một bài 2024. Sau đó tôi tìm từ khoá trong toàn bộ văn bản. Mốc thời gian `&t=` trong link là vị trí đoạn trích.
  - **Cảnh báo:** đây là **phụ đề tự động**. Câu chữ có thể sai, ví dụ «overflow» = *order flow*, «bull shoulder block» = *bullish order block*, «city/civ» = *SIBI*. Câu trích dưới đây giữ nguyên phụ đề; chữ trong [ngoặc vuông] là phần tôi sửa hoặc chú thích. Muốn trích nguyên văn chính thức thì nên nghe lại tại mốc thời gian.
- **Mức A-:** clip do kênh khác («ICT Gems») cắt ra. Mô tả clip ghi rõ video gốc, và tôi đã đối chiếu lại với video gốc khi có thể.
- **Mức B:** mã nguồn công khai mà tôi đã đọc được trực tiếp, gồm thư viện Python `smart-money-concepts` và bản Pine LuxAlgo SMC.
- **Mức C:** blog, wiki, mô tả indicator, khoá học thứ cấp. Đây là diễn giải của người khác, **không phải lời ICT**.
- **Mức D:** preprint hoặc bài nghiên cứu chưa bình duyệt. **Mức E:** tạp chí có bình duyệt.
- Câu nào **không tìm thấy nguyên văn** của ICT thì tôi ghi rõ là «không tìm thấy».

---

## 0. Tóm tắt điều hành

1. Với ICT, «institutional order flow» (IOF) **không phải** dữ liệu DOM hay footprint. Ông bác bỏ thẳng cách hiểu đó: *«I'm seeing institutional order flow in price action»* (A).
2. Định nghĩa gốc năm 2016: IOF là *«the seeking of large institutional liquidity»*, tức là giá đi tìm thanh khoản lớn nằm trên khung tháng/tuần, rồi nhìn thấy nó được giao dịch vào trên khung ngày (A).
3. Dấu hiệu vận hành rõ nhất mà ICT nói: **khi tăng, các nến đóng giảm (down-close) đỡ giá; một đáy ngắn hạn bị lấy chỉ là stop run và giá phải quay lên ngay. Khi giảm thì ngược lại** (A, 2023). Năm 2022 ông nói: *«when you're bearish all of your up closed candles should keep price from going higher than them»* (A).
4. **Thân nến kể câu chuyện, râu nến gây thiệt hại** (body vs wick). Với PD array (order block, FVG), ICT xét **thân nến**: thân không vượt mean threshold hoặc CE (50%) thì là tôn trọng (A).
5. Giá chỉ làm một trong hai việc: **đi lấy thanh khoản (stop) hoặc đi tái cân bằng chỗ kém hiệu quả (FVG)**. Không có việc nào trong hai thì giá đi ngang (A). Đây chính là ý «thanh khoản → thanh khoản» mà người dùng đã chốt.
6. Có định nghĩa gốc cho **ERL/IRL** (12/2016 và 2022). ERL là stop phía trên/dưới biên range. IRL là FVG, liquidity void, OB và đỉnh/đáy ngắn hạn bên trong range. ERL/IRL **mang tính tương đối**, phụ thuộc range được chọn (A).
   - Câu «ERL → IRL → ERL» **không tìm thấy nguyên văn** của ICT. Đó là cách diễn đạt của nguồn thứ cấp, nhưng khớp với cách ICT quản lý lệnh: chốt một phần ở IRL, phần còn lại nhắm ERL.
7. «Protected high/low» là **thuật ngữ SMC** (LuxAlgo gọi là strong/weak high-low), không phải từ ICT. Ý tương đương ở ICT: đỉnh/đáy trung hạn (ITH/ITL) hoặc đáy đã được tin tưởng thì *«should not be violated»*. Nếu bị phá thì ý tưởng sai: đứng ngoài và chờ thêm thông tin. **Đó chính là trạng thái «chưa rõ»** (A).
8. Đổi chiều theo ICT:
   - **MSS (2022):** sau khi lấy thanh khoản, giá *giao dịch qua* đỉnh/đáy ngắn hạn, **không cần đóng cửa qua**, kèm displacement tạo FVG (A).
   - **CISD (2023+):** giá vượt **giá mở của nến đầu tiên trong chuỗi nến cùng màu** ngay sau một «sự kiện chuyển tiếp» (vừa lấy thanh khoản hoặc vừa chạm FVG). ICT diễn đạt mơ hồ giữa «chạm qua» và «đóng qua». Nguồn thứ cấp và các indicator đều chuẩn hoá thành **đóng cửa qua** (C).
9. Định lượng từ ICT gần như không có, chỉ có:
   - swing = 3 nến;
   - FVG = 3 nến;
   - mean threshold / CE = 50%;
   - FVG «hết hạn» sau khoảng 1–1,5 tháng, opening range gap khoảng 60 ngày.
   - Không có ngưỡng ATR, không có số nến xác nhận cho CISD hay sweep.
10. Nhiều khung: theo ICT, tuần cho bias, **ngày là nơi chứa draw on liquidity**, H1 hoặc M15 để dựng setup, M1–M5 để vào lệnh. Swing khung nhỏ «phụ thuộc» swing khung lớn, và đánh ngược khung ngày là *«asking for failure»* (A). Công thức «order flow trên H1/H4, vào lệnh M15/M5» chỉ là quy ước thứ cấp (C).
11. Code công khai (`smart-money-concepts`, LuxAlgo SMC/ICT Concepts, «ICT Institutional Order Flow [fadi]», các indicator CISD) **không có biến "order flow state" tường minh**, trừ một indicator đóng mã (IOF Matrix V6) có trạng thái **neutral**. `smart-money-concepts` **nhìn trước dữ liệu tương lai (look-ahead)**, nên không dùng được cho kiểm định nhân quả (B).
12. Kiểm định:
    - Hai preprint SSRN 2026 (D) và một blog backtest (C) **không thấy lợi thế có ý nghĩa thống kê** của các quy tắc ICT/SMC «như được dạy».
    - Đáng chú ý cho lab: một preprint trên G10 FX báo rằng **sau sweep giá thường *tiếp diễn*, không đảo chiều**.
    - Hướng này khớp với nghiên cứu có bình duyệt của Osler (2003, 2005) về «price cascade» khi stop-loss bị kích hoạt (E).
    - Chưa thấy nghiên cứu nào kiểm định **trạng thái order flow** của ICT như một biến.

---

## 1. ICT định nghĩa «order flow» / «institutional order flow» thế nào?

### 1.1 Trích nguồn gốc ICT (mức A, kênh chính thức; phụ đề tự động)

| # | Trích (phụ đề) | Video gốc (ngày đăng YouTube) | Ý chính |
|---|---|---|---|
| 1 | «what institutional order [flow] is it's the seeking of large institutional liquidity and it's going to be found on the monthly and the weekly and you see that being traded into on the daily» | [Core Content 2016 – Month 03 – Institutional Order Flow @27:49](https://www.youtube.com/watch?v=PQkcFbr61FI&t=1669s) (ghi hình 11/2016; đăng 2022-09-01) | IOF = **giá đi tìm thanh khoản lớn** (khung tháng/tuần) |
| 2 | «the bodies of the candle is where all the volume is the institutional volume … the wick is always going to be directly related to retail» | [cùng video @6:18](https://www.youtube.com/watch?v=PQkcFbr61FI&t=378s) | Phân tích theo **thân nến**; râu là «giá cực đoan» |
| 3 | «we only need it to reach below the bodies of the candle» | [@11:39](https://www.youtube.com/watch?v=PQkcFbr61FI&t=699s) | Lấy thanh khoản: chỉ cần vượt **thân**, không cần vượt râu |
| 4 | «institutional order [flow] is bearish until we get down to here then … it's going to look for the liquidity on the upside … institutional order [flow] is bullish here then once it gets to this point … we would see institutional order flow swing to the downside» | [@10:36](https://www.youtube.com/watch?v=PQkcFbr61FI&t=636s) | Order flow **đảo chiều khi chạm mục tiêu thanh khoản hoặc PD array khung lớn** |
| 5 | «how do we know it's gonna be bearish because it breaks the last up candle at an area where we would expect to see bearishness» | [@20:42](https://www.youtube.com/watch?v=PQkcFbr61FI&t=1242s) | Xác nhận giảm: phá **nến tăng cuối cùng** tại vùng kỳ vọng giảm |
| 6 | «we have to wait for price to want to show a break above a short-term high … so now we know buyers are in the market again» | [@22:50](https://www.youtube.com/watch?v=PQkcFbr61FI&t=1370s) | Ở khung ngày, phải chờ **phá đỉnh ngắn hạn** rồi mới xác nhận phe mua |
| 7 | «when you're bearish all of your up closed candles should keep price from going higher than them» | [2022 Mentorship Ep.12 @48:40](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=2920s) (2022-02-24) | Định nghĩa vận hành: nến **đóng tăng** là kháng cự khi giảm |
| 8 | «down closed candles should support price if it trades back down to them» | [Ep.12 @52:19](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=3139s) | Đối xứng: nến **đóng giảm** đỡ giá khi tăng |
| 9 | «easiest thing is if we're bullish we want to see down closed candles support price if we see a short-term low taken out we expect to see that as a stop run and then price should revert right back into going higher right away and everything I just said reverse it for when the markets are bearish» | [ICT Mentorship 2023 – Deep Dive Into Institutional Order Flow @1:21:58](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=4918s) (2023-07-16) | **Quy tắc đơn giản nhất** của ICT về IOF |
| 10 | «when I say … trading with institutional order flow I'm seeing institutional order flow in price action» (và gọi DOM/footprint là «numbers that can be spoofed») | [Deep Dive @20:08](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=1208s) | IOF **chỉ đọc từ giá**, bác bỏ DOM/footprint |
| 11 | «you do need to know where price is drawing to … it's going there for stops or it's going there because it needs to reprice and re-deliver where inefficiency exists … if it's not going to do either one of those things … it's going to go sideways» | [ICT Mentorship 2023 – Immediate Rebalance & IOF @1:24:37](https://www.youtube.com/watch?v=ZtLMTXv-Dr0&t=5077s) (2023-05-25) | Giá có **hai động cơ: stop hoặc FVG**; không có cái nào thì đi ngang |
| 12 | «the Market's going to seek liquidity and fair value constantly it's always this ebb and flow between the two» | [Feb 15, 2023 ES Session Review @55:43](https://www.youtube.com/watch?v=SSWN6YSVyFY&t=3343s) (clip: [ICT Gems](https://www.youtube.com/watch?v=4hLj_mmPfxw)) | Luân phiên giữa thanh khoản và FVG |
| 13 | «institutional order [flow] is rooted on higher time frame bias» | [2022 Ep.19 @17:05](https://www.youtube.com/watch?v=IEa1N0rTtbc&t=1025s) (2022-04-20) | IOF gắn với **bias khung lớn** |
| 14 | «bearish ict fair value gap this is institutional order flow» | [2022 Ep.6 @10:20](https://www.youtube.com/watch?v=Bkt8B3kLATQ&t=620s) (2022-02-03; chủ đề tập: «market efficiency paradigm and institutional order flow») | FVG là «dấu vết» của IOF |
| 15 | «If order flow is bullish, I look for longs. If order flow is bearish, I look for shorts.» và «If it is Time for Price to displace or redeliver, the Liquidity or inefficiency is where it will be delivered.» | [Thread X của @I_Am_The_ICT, 2023-03-02 (Thread Reader)](https://threadreaderapp.com/thread/1631424751099944961.html) | Tweet gốc (A). Câu chữ trích qua Thread Reader, không phải trực tiếp từ X |

**Nhận xét về độ tin cậy:**
- Các câu trên là lời ICT (A), nhưng là phụ đề tự động.
- ICT **không đưa ra một định nghĩa hình thức duy nhất**. Khái niệm thay đổi theo thời gian:
  - 2016: thiên về «đi tìm thanh khoản khung tháng/tuần» và order block là «nến ngược chiều cuối cùng»;
  - 2022–2023: thiên về «nến đóng giảm đỡ giá / nến đóng tăng chặn giá» và *«order block = change in the state of delivery»* ([Ep.18 @46:43](https://www.youtube.com/watch?v=eai0nHhAC8w&t=2803s); [Ep.3 @24:28](https://www.youtube.com/watch?v=nQfHZ2DEJ8c&t=1468s)).
- ICT cũng tự nói rằng không phải mọi PD array đều có mặt ở mọi lúc, và người học được «mang cá tính» vào cách dùng ([2023 IRIOF](https://www.youtube.com/watch?v=ZtLMTXv-Dr0)). Điều này **làm tăng mức tự do diễn giải**.

### 1.2 Nguồn thứ cấp (mức C): để đối chiếu, không phải lời ICT

| Nguồn | Định nghĩa | Ghi chú |
|---|---|---|
| [LuxAlgo Library – Institutional Order Flow](https://www.luxalgo.com/library/concept/institutional-order-flow/) | «the market's prevailing direction of delivery … inferred entirely from price behavior». Khi tăng: giá liên tục với tới đỉnh cũ, pullback vào nến đóng giảm hoặc PD array tăng thì giữ được. Khi các vùng này «start failing on retests, the flow is in question» | Diễn giải sát ICT 2022–2023; có khái niệm «flow in question» (≈ neutral) |
| [TradingFinder – ICT Market Order Flow](https://tradingfinder.com/education/forex/ict-market-order-flow/) | Order flow là **các nến hồi ngược xu hướng**, hình thành trước BOS | Nghĩa **hẹp và khác**; dễ gây nhầm |
| [writofinance – ICT Institutional Order Flow](https://www.writofinance.com/ict-order-flow-trading/), [pineify](https://pineify.app/trading-strategy/ict-trading-strategy) | Diễn giải chung chung (dòng lệnh tổ chức để lại «dấu chân») | Thấp, mang tính marketing |
| [Scribd – «IOF and Standard Deviation»](https://www.scribd.com/document/748527063/INSTITUTIONAL-ORDERFLOW-STANDARD-DEVIATION) (qua snippet tìm kiếm) | «When IOF is bearish, price should disrespect all Bullish PD Arrays» | Tài liệu cộng đồng, tác giả không rõ |

---

## 2. Nhận ra order flow tăng/giảm bằng dấu hiệu nào?

| Dấu hiệu | ICT gốc nói gì (A) | Nguồn | Hệ quả cho code |
|---|---|---|---|
| **Nến đóng giảm / đóng tăng** (đơn vị cơ bản của OB) | Tăng: down-close đỡ giá. Giảm: up-close chặn giá («does it overtake this up close candle no … so it acts as real resistance that's institutional orderflow») | [Ep.12 @48:40](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=2920s), [Deep Dive @1:21:58](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=4918s) | Dùng được trực tiếp: đánh dấu «vùng nến ngược chiều gần nhất» và kiểm tra **thân nến** có đóng vượt hay không |
| **«Không muốn» vượt** (unwillingness) | «retraced had an unwillingness to go above this up candle here so institutional order flow … moves back to bearish and expands to the downside» | [Core 2016 Month 1 – Liquidity Runs @18:06](https://www.youtube.com/watch?v=22XkhpJR5eA&t=1086s) | Phiên bản ICT của «price fails to trade above …» |
| «Price fails to trade below …» | **Không tìm thấy nguyên văn** trong khoảng 50 transcript đã quét. ICT dùng «unwilling», «should not be violated», «fails to get above this swing high» | (quét transcript) | Câu này là diễn đạt phổ biến của nguồn thứ cấp ([tradezella](https://www.tradezella.com/learning-items/key-ict-concepts), [ictkillzone](https://www.ictkillzone.com/ict-order-block)) (C) |
| **Mean threshold của OB** | «ideally the best order blocks will not see price trade down below the midway point of the entire body» (đo từ open tới close, «do not use the wicks») | [Core 2016 Month 04 – Orderblocks @9:59](https://www.youtube.com/watch?v=PIYh0CxoY9c&t=599s) | Quy tắc định lượng hiếm hoi: 50% **thân** OB |
| **FVG được tôn trọng** | Bearish FVG: «you want to see that upper half … stay open … that means you have a very strong probability that you're right». Thân nến không vượt CE (50%) thì vẫn bearish | [2024 «How To Trade ICT FVGs Correctly» @27:11](https://www.youtube.com/watch?v=HhgWGduQZQY&t=1631s); [2023-09-12 NQ Algorithmic Price Delivery @1:51:27](https://www.youtube.com/watch?v=9MLRE-n6St8&t=6687s) («the bodies which is what tells you the story … did it pierce and breach the halfway point here no») | «Respect FVG» ≈ **close không vượt CE**; râu được phép xuyên |
| **FVG bị «disrespect»** | Thủng FVG thì «I'm probably looking at an inversion fair value gap» | [2024 FVG @33:05](https://www.youtube.com/watch?v=HhgWGduQZQY&t=1985s) | FVG đảo vai (IFVG). ICT không nói rõ thủng bằng close hay wick |
| **Đáy ngắn hạn bị lấy rồi quay lại** (khi tăng) | «short-term low taken out … stop run … price should revert right back into going higher right away»; «any swing low is a potential stop run» | [Deep Dive @1:21:58](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=4918s), [@1:25:18](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=5118s) | Trong order flow tăng, **sweep SSL nhỏ là tín hiệu tiếp diễn**, không phải đảo chiều |
| **Đỉnh ngắn hạn liên tục bị lấy** | «does it take out short-term highs yes yes» (trong chuỗi xác nhận tăng) | [Deep Dive](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=4918s) | Order flow tăng ≈ **BSL liên tục bị lấy**, SSL thì không bị phá thật |
| **Đỉnh/đáy trung hạn (ITH/ITL) không bị vi phạm** | «every rebalance of an old imbalance that swing … I immediately label … as an intermediate term high/low»; «intermediate term high or low should not be violated» | [Ep.12 @13:59](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=839s), [@52:51](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=3171s) | ICT **khác Larry Williams** ở chỗ này: swing tạo ra lúc lấp FVG được coi là ITH/ITL ngay. Lab đang dùng ITH/ITL kiểu Williams |
| **Displacement** | «obvious displacement … not … a little lethargic run»; displacement «qualifies that order block because it creates a fair value [gap]» | [2022 Ep.5 @18:46](https://www.youtube.com/watch?v=N29ZJ-o31xs&t=1126s), [Ep.19](https://www.youtube.com/watch?v=IEa1N0rTtbc) | ICT chỉ định nghĩa định tính, tiêu chí thực tế là **tạo FVG**. Ngưỡng 1,5 ATR / thân ≥60% là quy ước riêng của lab |
| **Chuỗi HH/HL** | «we're not looking for just the simple higher high higher low therefore it's a bullish market … I'm looking at does the market have a reason to go up for buy side liquidity … or … to rebalance» | [Ep.12 @6:06](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=366s) | ICT **không coi HH/HL là tiêu chí chính**; tiêu chí chính là **draw** (thanh khoản hay FVG) |
| **Respect/disrespect PD array** (bullish OF = PD tăng được tôn trọng, PD giảm bị xuyên) | ICT dùng «respect» cho thân nến với mức giá. **Không tìm thấy** «disrespect» theo nghĩa PD array trong các transcript đã quét (chỉ thấy theo nghĩa bình luận bất lịch sự) | — | Công thức «respect/disrespect» là **chuẩn hoá thứ cấp** ([LuxAlgo IOF](https://www.luxalgo.com/library/concept/institutional-order-flow/), [IOF Matrix V6](https://www.tradingview.com/script/rpPuN4cO-ICT-MTF-Institutional-Order-Flow-Matrix-V6/)) (C) |
| **Premium/discount** | «we have to do all of our buying below equilibrium … while we're on a discount» | [Deep Dive](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=4918s) | Có thể dùng làm bộ lọc vị trí trong dealing range |

---

## 3. Order flow ↔ thanh khoản

### 3.1 ERL / IRL: có định nghĩa gốc (A)

- **Core 2016 Month 04 – Reinforcing Liquidity Concepts & Price Delivery** ([@0:50](https://www.youtube.com/watch?v=npL3ZXJ5zOU&t=50s)):
  - ERL: «the current trading range will have buy side liquidity above the Range High … sell side liquidity below the range low; runs on liquidity seek to pair orders with pending order liquidity … external range liquidity runs can be low resistance or high resistance».
  - IRL: «when the current trading range is likely to remain liquidity voids will fill in … fair value [gaps] will also fill in … order blocks inside the trading range will be populated with new buys and/or sells».
- **Tính tương đối** ([@5:59](https://www.youtube.com/watch?v=npL3ZXJ5zOU&t=359s)): «in the context from this high to this low its internal range liquidity but from this low to this high its external range liquidity». Cùng một đáy có thể là IRL hoặc ERL, **tuỳ dealing range được chọn**.
- **2022 Ep.3** ([@35:04](https://www.youtube.com/watch?v=nQfHZ2DEJ8c&t=2104s)): «internal range liquidity is looking for short-term lows or short-term highs inside a price leg that we're retracing back into … a short term high or low with stops above or below it or an imbalance in that same range».
- **2022 Ep.6** ([@45:33](https://www.youtube.com/watch?v=Bkt8B3kLATQ&t=2733s)): FVG nằm giữa range là IRL; «the stops below these lows … external range liquidity … so partials internal range external range». Chốt **một phần ở IRL, phần còn lại ở ERL**.

### 3.2 «Liquidity → liquidity», draw on liquidity

- Giá đi tới **stop** hoặc **FVG** (bảng mục 1, dòng 11, 12, 15). Ý «đi từ thanh khoản tới thanh khoản» của người dùng khớp với ICT nếu hiểu «thanh khoản» gồm cả **FVG/inefficiency (IRL)**.
- **Draw on liquidity** ([2022 Ep.2 @16:42](https://www.youtube.com/watch?v=tmeCWULSTHc&t=1002s)): «on the daily chart you're looking for swing highs and swing lows to get your liquidity … the draw on liquidity what makes the market go higher or lower it's predominantly found on this time frame [daily]».
- **Chu kỳ ERL → IRL → ERL:** **không tìm thấy nguyên văn** của ICT. Đây là cách diễn đạt của nguồn thứ cấp:
  - [LuxAlgo – Internal vs External Range Liquidity](https://www.luxalgo.com/library/concept/internal-vs-external-range-liquidity/): «After external liquidity is taken, the next draw … is commonly internal … and once internal liquidity is filled, expectation rotates outward toward the opposite extreme»;
  - [tradingedges](https://tradingedges.org/en/articles/ict-internal-external-range-liquidity-explained-2026) (C).
  - Chu kỳ này **phù hợp** với ví dụ của ICT ở Month 04: quét đỉnh cũ (ERL) → hồi về nến tăng hoặc FVG (IRL) → quét đáy bằng nhau.

### 3.3 Sweep vs run

ICT có một vài khái niệm liên quan:
- «stop run», «turtle soup» (phá giả);
- «low resistance liquidity run» và «high resistance liquidity run» ([Month 1 – Liquidity Runs](https://www.youtube.com/watch?v=22XkhpJR5eA&t=1086s); [Month 04](https://www.youtube.com/watch?v=npL3ZXJ5zOU&t=50s)).

ICT **không định nghĩa** sweep bằng «close quay lại trong N nến». Quy tắc 3 nến là của lab. Điều kiện duy nhất ICT nhấn mạnh: một MSS chỉ có nghĩa nếu trước đó **đã lấy thanh khoản** («significant only if this run down here has traded into sell stops», [Ep.3 @7:05](https://www.youtube.com/watch?v=nQfHZ2DEJ8c&t=425s)).

Bằng chứng ngoài ICT:
- **Osler (2003)**, *Journal of Finance* ([Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/1540-6261.00588); [bản NY Fed SR125](https://www.newyorkfed.org/research/staff_reports/sr125.html)) (E): take-profit tụ ở số tròn (giải thích bật lại tại hỗ trợ/kháng cự); stop-loss tụ **ngay sau** số tròn (giải thích giá chạy nhanh khi vượt mức).
- **Osler (2005)**, *JIMF* ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0261560604001147); [NY Fed SR150](https://www.newyorkfed.org/research/staff_reports/sr150.html)) (E): stop-loss tạo «price cascades» tự củng cố.
- **Mahadzva (2026, SSRN preprint)** (D, xem mục 7): sweep dự báo **tiếp diễn**, không phải đảo chiều.

→ Cần đo cả hai nhánh **sweep** và **run**; không nên mặc định sweep = đảo chiều.

### 3.4 «Protected low/high»

- **Là thuật ngữ SMC.**
  - [LuxAlgo – Strong vs Weak Swings](https://www.luxalgo.com/library/concept/strong-vs-weak-swings/) (C): strong low = «the low that launched a break of structure upward»; «protected» dùng đồng nghĩa với «strong»; «a decisive close through it is treated as a change of character».
  - Trong mã LuxAlgo SMC (B): nhãn `'Strong High'` khi `trend < 0`, ngược lại `'Weak High'`; `trail_up/trail_dn` là cực trị trượt của chân hiện tại. Xu hướng đổi khi **close cắt qua** swing gần nhất (`ta.crossover(close, top_y)`) ([gist mirror](https://gist.github.com/niquedegraaff/8c2f45dc73519458afeae14b0096d719); bản gốc trên TradingView).
- **Ý tương đương ở ICT (A):**
  - «we trusted that low will not be violated why because this Candlestick was crossed right there [CISD]» ([Deep Dive @1:20:11](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=4811s));
  - ITH «should not trade higher than a high. That's the reason why … you can put your stop loss there» ([Ep.18 @46:43](https://www.youtube.com/watch?v=eai0nHhAC8w&t=2803s));
  - «this now is a long-term High I do not expect this High to be broken … if it goes above that then I'm probably wrong … I demand more information … sitting on my hands» ([Ep.12 @11:13](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=673s)).
- **Lưu ý:**
  - Với ICT, mức «được bảo vệ» là **ITH/ITL (thường là swing được tạo khi lấp FVG)** hoặc **đáy mà CISD xuất phát**, không nhất thiết là «đáy cấu trúc gần nhất».
  - Ngưỡng phá là «violated / trade higher than», **nghiêng về wick** (giá giao dịch qua), khác với SMC/LuxAlgo dùng **close**.

---

## 4. Cái gì làm order flow đổi chiều hoặc «chưa rõ»?

| Sự kiện | Định nghĩa gốc (A) / thứ cấp (C) | Định lượng có sẵn? | Nguồn |
|---|---|---|---|
| **Chạm mục tiêu thanh khoản / PD array khung lớn** | Order flow «swing» khi giá tới vùng thanh khoản hoặc OB khung tháng/tuần đã nhắm (A) | Không | [Month 03 IOF @10:36](https://www.youtube.com/watch?v=PQkcFbr61FI&t=636s) |
| **MSS (2022)** | Sau khi lấy BSL/SSL, đỉnh/đáy ngắn hạn đã tạo ra cực trị bị **giao dịch qua**: «we traded above it it does not need to close above that okay real important». Sau đó chờ nến đóng xem có tạo FVG không (A) | **Wick là đủ**; cần có sweep trước; cần FVG (tức displacement) | [Ep.3 @13:47](https://www.youtube.com/watch?v=nQfHZ2DEJ8c&t=827s), [@7:05](https://www.youtube.com/watch?v=nQfHZ2DEJ8c&t=425s). ICT phân biệt «intraday shift» với «market structure break» kéo dài nhiều ngày |
| **CISD** | ICT: «series of down closed candles you use that entire block … as one … this change in the state of delivery that is the order block … three down closed candles that opening price» ([Feb-15-2023 @52:14](https://www.youtube.com/watch?v=SSWN6YSVyFY&t=3134s)); «nothing to do with engulfing … size of the candle … it's the fact that we opened or closed higher or lower after a transitional event like either liquidity has been traded to or an inefficiency has been revisited» ([2023-09-12 @2:02:31](https://www.youtube.com/watch?v=9MLRE-n6St8&t=7351s)); «when that candle starts moving above that opening price … shift in market structure» ([Deep Dive @1:21:25](https://www.youtube.com/watch?v=vN2BkfyRWE4&t=4885s)) (A) | ICT **mơ hồ** giữa giao dịch qua và đóng qua. Không có số nến | Thứ cấp chuẩn hoá thành **body close qua giá mở nến đầu chuỗi**: [LuxAlgo Library CISD](https://www.luxalgo.com/library/concept/change-in-state-of-delivery/) («a wick through the level does not count»); [indicator CISD LuxAlgo](https://www.tradingview.com/script/gHHRpuHC-Change-in-State-of-Delivery-CISD-LuxAlgo/) (chế độ Classic: «closes above the opening price of the first candle in a sequence of bearish candles»); [Fadi trên X](https://x.com/FadiZeidan/status/1951655408243761207) (C) |
| **Phá «nến ngược chiều cuối cùng»** (breaker) | «it breaks the last up candle at an area where we would expect to see bearishness» (A) | Không | [Month 03 @20:42](https://www.youtube.com/watch?v=PQkcFbr61FI&t=1242s) |
| **Disrespect PD array** | Thủng FVG → «inversion fair value gap» (A); OB tăng bị đóng qua đáy → breaker giảm (C) | ICT không nói rõ close hay wick; thứ cấp dùng close | [2024 FVG @33:05](https://www.youtube.com/watch?v=HhgWGduQZQY&t=1985s); [innercircletrader.net – breaker](https://innercircletrader.net/tutorials/ict-breaker-block-trading/) (C, không liên kết ICT) |
| **Phá ITH/ITL / LTH/LTL đang «tin tưởng»** | «if that intermediate term high is broken and you're bearish then you got to move [to] the sidelines» (A) | Không | [Ep.12 @52:51](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=3171s) → **trạng thái «chưa rõ»**, không phải đảo chiều ngay |
| **Không có draw** | «if it's not going to do either one of those things … it's going to go sideways» (A) | Không | [2023 IRIOF @1:24:37](https://www.youtube.com/watch?v=ZtLMTXv-Dr0&t=5077s) |
| **Neutral do PD array không còn đúng vai** | IOF Matrix V6: bullish hợp lệ khi close được phép vào nửa trên thân discount array, «if it closes below the dMean … the state immediately neutralizes» (C, đóng mã) | Có: close so với 50% thân | [TradingView – IOF Matrix V6](https://www.tradingview.com/script/rpPuN4cO-ICT-MTF-Institutional-Order-Flow-Matrix-V6/) |

**Các con số ICT thực sự đưa ra:**
- swing = 3 nến; ICT nói thẳng «you do not need a Williams fractal that's way too many candles» ([Ep.10 @18:31](https://www.youtube.com/watch?v=S9ORTYmXwdE&t=1111s));
- FVG = 3 nến;
- mean threshold và CE = 50%;
- FVG «expire after about a month maybe sometimes a month and a half»; opening range gap «expiration date of about 60 days» ([2023-09-12 @1:58:53](https://www.youtube.com/watch?v=9MLRE-n6St8&t=7133s)).

**Không có:** ngưỡng ATR, số nến cho sweep, số nến cho CISD, độ lớn displacement.

---

## 5. Order flow trên nhiều khung

| Khẳng định | Mức | Nguồn |
|---|---|---|
| Tháng = position, tuần = swing, **ngày = short-term (chart «tốt nhất»; cho bias)**, ≤4H = day trading; «start [in] the daily chart … really good bellwether … it'll also give you the directional bias» | A | [Core 2016 Month 03 – Timeframe Selection @19:50](https://www.youtube.com/watch?v=UF5J0nEBc0E&t=1190s) |
| Quy trình 2022: **tuần** đặt bias («weekly candle expand higher or lower») → **ngày** tìm draw on liquidity → **H1 / M15** khung setup → **M1–M3** tìm MSS/FVG sau khi lấy thanh khoản «in an opposing direction of your weekly expected range» | A | [Ep.2 @16:42](https://www.youtube.com/watch?v=tmeCWULSTHc&t=1002s), [@47:22](https://www.youtube.com/watch?v=tmeCWULSTHc&t=2842s) |
| «the subordination that the smaller time frame price swings adhere to from the higher time frame is directly linked to the order flow on those higher time frame charts»; dựng setup trên H1 với khung ngày là «parent»; đánh ngược khung ngày là «asking for failure» | A | [Ep.12 @20:46](https://www.youtube.com/watch?v=8GkQfdAXZP0&t=1246s) |
| Giao dịch ngược IOF khung lớn có thể làm, nhưng ICT khuyên người mới không làm | A | [Ep.19](https://www.youtube.com/watch?v=IEa1N0rTtbc&t=1025s) |
| Mức tháng/tuần được «chuyển» xuống khung ngày để nhìn phản ứng | A | [Month 03 IOF](https://www.youtube.com/watch?v=PQkcFbr61FI&t=1669s) |
| Cặp khung «4H → 15m/5m», «1H → 5m/1m»; «4H for bias, 15m for entry» | C | [r2ftrading](https://www.r2ftrading.com/learn/best-timeframes-for-ict-trading), [tradingstrategyguides](https://tradingstrategyguides.com/day-10-multi-timeframe-analysis-ict-smc-the-top-down-approach-explained/) |
| Khi mơ hồ: «defer to the flow one or two timeframes higher» | C | [LuxAlgo IOF](https://www.luxalgo.com/library/concept/institutional-order-flow/) |

→ Cách bố trí «order flow trên H1/H4 (có D1 làm parent), sự kiện trên M15/M5» **phù hợp tinh thần ICT**. Tuy nhiên ICT gốc nhấn mạnh **D1 (và W1)** là nơi chứa draw. Cặp «H1/H4 → M15/M5» cụ thể là quy ước thứ cấp.

---

## 6. Các cài đặt code công khai xấp xỉ order flow thế nào?

| Công cụ | Mã mở? | Swing | Cấu trúc / xu hướng | Close hay wick | Nhân quả? | Có «order flow state»? |
|---|---|---|---|---|---|---|
| [`smart-money-concepts` (Python, joshyattridge)](https://github.com/joshyattridge/smart-money-concepts) ([mã `smc.py`](https://raw.githubusercontent.com/joshyattridge/smart-money-concepts/master/smartmoneyconcepts/smc.py)) | Có (B) | Cửa sổ đối xứng `swing_length=50` (dùng `shift(-n)` nên **nhìn tương lai**). Ép xen kẽ đỉnh/đáy; **gán nhãn giả cho nến đầu và nến cuối** | BOS/CHoCH từ mẫu 4 swing liên tiếp; `close_break=True` mặc định | Tuỳ chọn | **Không**: swing cần nến tương lai; BOS cũ bị xoá khi BOS mới phá sau; `liquidity` dùng `range_percent` × biên độ **toàn bộ dataset** | Không |
| [LuxAlgo Smart Money Concepts (Pine)](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/) ([mirror mã](https://gist.github.com/niquedegraaff/8c2f45dc73519458afeae14b0096d719)) | Có, CC BY-NC-SA (B) | `swings(len)`: xác nhận trễ `len` nến (swing 50, internal 5), nhân quả | `trend` đổi khi **close cắt** swing gần nhất; Strong/Weak High/Low theo `trend`; premium/discount theo cực trị trượt | Close | Có (trễ `len`) | Gián tiếp: biến `trend` + strong/weak |
| [LuxAlgo ICT Concepts](https://www.tradingview.com/script/ib4uqBJx-ICT-Concepts-LuxAlgo/) | Mô tả (C) | Theo tham số Length | MSS = phá swing ngược xu hướng; BOS = phá cùng xu hướng; displacement = chuỗi nến cùng màu thân lớn, râu ngắn; liquidity margin theo ATR | — | — | Không tường minh |
| [ICT Institutional Order Flow (fadi)](https://www.tradingview.com/script/RoK9cao8-ICT-Institutional-Order-Flow-fadi/) | Có (C, chỉ đọc mô tả) | STH/STL 3 nến → ITH/ITL = STH có STH thấp hơn hai bên → LTH | Thanh khoản dưới/trên pivot; FVG/VI/gap | — | — | Không. Tác giả ghi rõ chưa xử lý quy tắc «STH lấp FVG ⇒ ITH» của ICT |
| [CISD (LuxAlgo)](https://www.tradingview.com/script/gHHRpuHC-Change-in-State-of-Delivery-CISD-LuxAlgo/) | Mở (C) | Swing Length (chế độ sweep) | Classic: close qua open nến đầu chuỗi ngược màu; chế độ Liquidity Sweep; «Minimum CISD Duration», «Maximum Swing Validity» | Close | Có | CISD là tín hiệu đổi chiều |
| [CISD (AlgoAlpha)](https://www.tradingview.com/script/DNxCFCO1-Change-in-State-of-Delivery-CISD-AlgoAlpha/) | Mở (C) | Pivot | Wick xuyên swing → đo tỉ lệ «counter-move / failed push» vượt ngưỡng tolerance; Expiry Bars | Wick (cho sweep) | — | — |
| [ICT MTF IOF Matrix V6](https://www.tradingview.com/script/rpPuN4cO-ICT-MTF-Institutional-Order-Flow-Matrix-V6/) | **Đóng** (C) | — | Bull: hỗ trợ ở down-close, xuyên qua up-close; **neutral** khi close dưới 50% thân discount array; M/W/D với lookback 20/40/60 ngày | Close so với 50% thân | Không kiểm chứng được | **Có (bull/bear/neutral)** |
| [ICT HTF Candles Pro (fadi)](https://www.tradingview.com/script/CFob1nQO-ICT-HTF-Candles-Pro-fadi/) | Invite-only (C) | — | «Trend Bias … tracks order blocks and change in state of delivery» theo từng khung | — | — | Có (mô tả) |

---

## 7. Nghiên cứu và kiểm định định lượng

| Nghiên cứu | Loại | Dữ liệu | Kết quả | Ghi chú độ tin cậy |
|---|---|---|---|---|
| Mahadzva, *Smart Money or Costly Folklore? …ICT/SMC Trading Rules in G10 FX* ([SSRN 7430998](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7430998), đăng 2026-09-14) | D, preprint | EURUSD, GBPUSD, AUDUSD, USDJPY; intraday; 6 quy tắc; walk-forward, bootstrap, permutation, holdout | «no evidence that ICT/SMC concepts work as literally taught». Ba cơ chế liquidity-sweep độc lập (equal highs/lows, OB, Asian range) đồng thuận ở **65/66** fold-selection rằng **mức bị sweep dự báo tiếp diễn, không phải đảo chiều**. Một kết quả nổi bật: EURUSD H1, CHoCH + FVG retrace, p = 0,0192 | SSRN trả 403 nên tôi chỉ đọc được tóm tắt qua kết quả tìm kiếm. Chưa đọc toàn văn |
| Tangirala, *Do Smart Money Concepts Predict Returns? …44 Formalised Detectors on S&P 500 Daily Bars, 2010–2026* ([SSRN 7483658](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7483658), 2026-09-19) | D, preprint | 496 cổ phiếu S&P 500, nến ngày; 44 detector dịch từ 2 script Pine mã mở; 2,20 triệu sự kiện | Kiểm soát Benjamini-Hochberg trên 352 giả thuyết: **không concept nào hơn vào lệnh ngẫu nhiên**, cũng không cái nào tệ hơn có ý nghĩa. Ước lượng lớn nhất (liquidity sweep) là 11–12 bp/10 ngày, p ≥ 0,23. Bản trước từng báo sai (28/42 «thắng» trong khi thực tế 27 thua) và đã đính chính | Chỉ đọc qua tóm tắt. Cổ phiếu/khung ngày khác XAU/EUR M5–M15 |
| StatOasis, *I Backtested ICT / SMC — What Survives* ([link](https://statoasis.com/overfit/research/ict-backtest-what-survives), 2026-09-03) | C, blog | SPY, QQQ, DIA, IWM (ngày); OB, FVG, sweep, OTE; 648 backtest; baseline ngẫu nhiên 50 seed | Chỉ **1/32** điểm số có t > 2 (OTE trên DIA 10 ngày, t = 2,07). SPY 5 ngày: OB t = +1,22, FVG −0,08, sweep +0,94, OTE −0,17. 0/648 thắng buy-and-hold | Phương pháp mô tả khá rõ, nhưng không bình duyệt |
| Quant Trading Discoveries, FVG EURUSD ([substack](https://quanttradingdiscoveries.substack.com/p/fair-value-gap-backtest-results-eurusd), 2026-03-29) | C | EURUSD 2022–2025; 1.247 FVG | 63,7% FVG «never fill». Bộ lọc 5 điểm giữ 341 setup: win 66,5%, +1,14R. Không nêu out-of-sample, không nêu khung | Thấp: nguy cơ chọn bộ lọc sau khi nhìn kết quả |
| [Edgeful](https://www.edgeful.com/blog/posts/fair-value-gap-best-practices-guide) (vendor) | C | YM futures | FVG không lấp trong cùng phiên: khoảng 60,7% (tăng), khoảng 63,2% (giảm) | Nhà bán công cụ |
| Osler 2003 (JF), 2005 (JIMF) (link ở mục 3.3) | **E** | Lệnh thật của ngân hàng FX | Stop-loss tụ sau số tròn → giá chạy nhanh khi vượt; take-profit tụ ở số tròn → bật lại | Không kiểm định ICT, nhưng là cơ sở vi cấu trúc cho «thanh khoản bị lấy → chạy tiếp» |

**Kết luận mục 7:**
- **Không tìm thấy** nghiên cứu nào kiểm định *trạng thái order flow kiểu ICT* (bull/bear/neutral theo PD array và thanh khoản) như một biến dự báo.
- Các kiểm định sẵn có nhắm vào từng mẫu riêng lẻ (OB, FVG, sweep, CHoCH) và đa số không thấy lợi thế.
- Không có kiểm định công khai, đáng tin nào trên **XAUUSD M5/M15**.
- Tôi không đánh giá khả năng sinh lời ngoài các số liệu trên.

---

## 8. Những chỗ mơ hồ lab phải tự chọn

| # | Điểm mơ hồ | Phương án | Ưu / nhược |
|---|---|---|---|
| 1 | **Trạng thái order flow dựa trên gì** | (a) Chuỗi swing HH/HL + mức bảo vệ (lab đã có) | + Đơn giản, đã code. − ICT nói rõ đây **không** phải tiêu chí chính (Ep.12) |
| | | (b) Hành vi PD array: down-close/FVG tăng được giữ và up-close/FVG giảm bị xuyên | + Sát ICT 2022–23. − Phải định nghĩa «vùng» và «giữ/xuyên»; nhiều tham số |
| | | (c) Hướng thanh khoản đang bị lấy: BSL liên tục bị lấy còn SSL chỉ bị sweep thì tăng; ngược lại thì giảm | + Khớp «thanh khoản → thanh khoản», tận dụng vòng đời BSL/SSL của lab. − Trễ; cần quy tắc khi cả hai phía cùng bị lấy |
| 2 | **Wick hay close** | (a) Close cho mọi thứ | + Ít nhiễu, nhất quán với lab (close vượt mới bật cờ). − Lệch ICT ở MSS/vi phạm ITH (ICT dùng «trade through») |
| | | (b) Wick + đệm (ví dụ 0,1 ATR, như ngưỡng «lấy» của lab) | + Sát ICT ở khái niệm «lấy thanh khoản». − Nhạy với spread/râu XAU |
| | | (c) **Lai**: wick cho «lấy thanh khoản»; close (thân) cho «tôn trọng/xuyên PD array», «phá mức bảo vệ» và CISD | + Khớp phân vai của ICT: «bodies tell the story, wicks do the damage». − Hai ngưỡng, phải ghi rõ trong spec |
| 3 | **Mức vô hiệu của order flow tăng** | (a) ITL gần nhất (Williams) | + Có sẵn. − Không trùng ITH/ITL kiểu ICT |
| | | (b) Đáy xuất phát của chân đã lấy BSL gần nhất (strong low kiểu SMC) | + Chuẩn SMC, ổn định. − Có thể rất xa, nên phản ứng chậm |
| | | (c) Đáy swing được tạo khi lấp FVG (ITL kiểu ICT) hoặc open của CISD | + Đúng tinh thần ICT. − Phải thêm detector «swing tạo lúc rebalance» |
| 4 | **Sweep đơn có đổi trạng thái không** | (a) Không; chỉ «shift» của lab (sweep + displacement ngược chiều ≤3 nến) mới đổi | + Bảo thủ, ít lật. − Trễ |
| | | (b) Sweep + CISD (close qua open chuỗi) mới đổi | + Sớm hơn shift, có cơ sở ICT 2023. − CISD rất thường xuất hiện trên M5, nhiễu |
| | | (c) Sweep đơn ngược chiều → **neutral**; cần shift/CISD mới sang chiều mới | + Có trạng thái «chưa rõ», khớp ICT «sitting on my hands». − Thêm một trạng thái phải đánh giá |
| | | Lưu ý | Bằng chứng D/E cho thấy sweep thường **tiếp diễn**. Nên đo xác suất tiếp diễn vs đảo chiều trước khi chọn |
| 5 | **Vùng nào được tính** | (a) Mọi vùng trên khung thực thi | + Nhiều sự kiện. − Nhiễu, nhiều lần lật |
| | | (b) Chỉ ITH/ITL + vùng khung lớn (H1/H4/D1) | + Sát «draw nằm ở khung ngày» (ICT). − Ít mẫu |
| | | (c) Trọng số theo cấp (STH < ITH < LTH; M5 < M15 < H1 < H4 < D1) | + Linh hoạt. − Khó diễn giải, dễ overfit |
| 6 | **Dealing range cho ERL/IRL** | (a) ITH–ITL gần nhất trên khung đang xét | + Nhất quán với lab. − ERL/IRL đổi vai liên tục (ICT thừa nhận tính tương đối) |
| | | (b) Chân swing gần nhất trên H1/H4 (parent) | + Ổn định, đúng tinh thần «parent». − Cần ánh xạ đa khung nhân quả |
| | | (c) Range theo phiên (Asia/London) hoặc range ngày trước | + Rõ ràng, ICT dùng nhiều khi intraday. − Không phản ánh cấu trúc |
| 7 | **CISD định lượng** | (a) Chuỗi ≥1 nến cùng màu; close qua open nến đầu | + Đúng chế độ Classic của LuxAlgo. − Quá nhiều tín hiệu |
| | | (b) Chuỗi ≥2 nến và chỉ tính trong N nến sau «sự kiện chuyển tiếp» (lấy thanh khoản hoặc chạm FVG khung lớn) | + Sát ICT 2023 («after a transitional event»). − Thêm tham số N |
| | | (c) Không dùng CISD; giữ «shift» của lab | + Đơn giản. − Bỏ một công cụ ICT nhấn mạnh |
| 8 | **Displacement** | (a) Ngưỡng lab: biên độ ≥1,5 ATR, thân ≥60% | + Định lượng sẵn. − Không phải định nghĩa ICT |
| | | (b) Phải tạo FVG | + Đúng ICT («qualifies … because it creates a fair value gap»). − Nến lớn đơn lẻ không tạo FVG sẽ bị loại |
| | | (c) Cả hai (AND) hoặc một trong hai (OR) | AND ít nhiễu; OR nhiều mẫu |
| 9 | **Trạng thái «chưa rõ»** | (a) Neutral khi mức bảo vệ bị phá mà chưa có shift ngược | + Khớp ICT Ep.12. − Có thể kéo dài |
| | | (b) Neutral khi không có draw rõ (giá giữa range, không có BSL/SSL hay FVG gần) | + Khớp «sideways» (2023). − Cần định nghĩa «gần» (ATR?) |
| | | (c) Neutral khi khung lớn và khung nhỏ mâu thuẫn | + Đơn giản. − Trộn hai khái niệm khác nhau |
| 10 | **Thời hạn hiệu lực vùng** | (a) Không hết hạn cho tới khi bị lấy/lấp | + Đơn giản. − Vùng cũ làm nhiễu |
| | | (b) Theo số nến | + Dễ code. − Phụ thuộc khung |
| | | (c) Theo thời gian lịch (ICT: FVG khoảng 1–1,5 tháng, ORG khoảng 60 ngày) | + Có cơ sở ICT. − Con số chỉ là ước lượng miệng |
| 11 | **Ưu tiên khung** | (a) Trạng thái khung lớn ghi đè | + Đúng «subordination» (Ep.12). − Bỏ lỡ chuyển chiều sớm ở khung nhỏ |
| | | (b) Trạng thái khung nhỏ chỉ hợp lệ khi cùng chiều khung lớn | + Ít tín hiệu ngược. − Ít mẫu |
| | | (c) Trạng thái độc lập + điểm đồng thuận | + Đo được giá trị thêm vào của khung lớn. − Phức tạp hơn |
| 12 | **«Respect» một FVG** | (a) Close không vượt CE (50%) | + Đúng ICT 2023–24. − Nhạy với FVG nhỏ |
| | | (b) Close không vượt mép xa | + Ít lật. − Lỏng hơn ICT |
| | | (c) Wick không chạm CE | + Rất chặt. − Hiếm |
| 13 | **Độ trễ xác nhận (nhân quả)** | Pivot 1/1 cần 1 nến sau; ITH cần STH kế tiếp nên có độ trễ biến thiên | Mọi sự kiện phải gắn **thời điểm xác nhận** (nến đóng), không phải thời điểm pivot. Không dùng `smart-money-concepts` nguyên trạng vì nó nhìn tương lai |
| 14 | **Premium/discount làm bộ lọc** | (a) Không dùng; (b) chỉ tính PD array tăng ở dưới 50% dealing range (ICT Deep Dive) | (b) sát ICT nhưng phụ thuộc lựa chọn ở mục 6 |

### Phác thảo để thảo luận (đề xuất của tôi, không phải trích nguồn)

Đây là một máy trạng thái nhân quả cho mỗi khung, chỉ dùng nến đã đóng, với `state ∈ {BULL, BEAR, NEUTRAL}`:

- **Vào BULL:**
  - Từ NEUTRAL/BEAR: SSL (ITL hoặc vùng khung lớn) bị lấy, rồi trong ≤3 nến có shift tăng của lab (hoặc tuỳ chọn CISD tăng).
  - Hoặc: BSL bị **run** (close vượt và không quay lại), dùng làm bằng chứng tiếp diễn.
- **Duy trì BULL:**
  - mức bảo vệ chưa bị phá (theo lựa chọn ở mục 2/3);
  - PD array tăng gần nhất không bị đóng xuyên (mục 12);
  - draw = BSL chưa bị lấy gần nhất phía trên (ERL), mục tiêu trung gian = FVG chưa lấp (IRL).
- **BULL → NEUTRAL:**
  - close dưới mức bảo vệ mà chưa có shift giảm; hoặc
  - FVG/OB tăng then chốt bị đóng xuyên; hoặc
  - đã chạm draw khung lớn (ICT: order flow «swing» tại mục tiêu).
- **BULL → BEAR:** BSL bị sweep rồi có shift giảm (đối xứng với vào BULL).
- **Cách kiểm định đề xuất:**
  - Đo xác suất lấy ERL cùng chiều trạng thái trước ERL ngược chiều, so với null (trạng thái xáo trộn hoặc chỉ dùng HH/HL).
  - Tách riêng: sweep → tiếp diễn hay đảo chiều; giá trị thêm vào của khung lớn.

---

## Phụ lục: danh sách video ICT gốc đã quét (kênh «The Inner Circle Trader»)

- Core Content 2016 (đăng 2022):
  - [Month 1 – Liquidity Runs](https://www.youtube.com/watch?v=22XkhpJR5eA)
  - [Month 03 – Institutional Order Flow](https://www.youtube.com/watch?v=PQkcFbr61FI)
  - [Month 03 – Institutional Market Structure](https://www.youtube.com/watch?v=GuycI8XubgE)
  - [Month 03 – Timeframe Selection](https://www.youtube.com/watch?v=UF5J0nEBc0E)
  - [Month 04 – Orderblocks](https://www.youtube.com/watch?v=PIYh0CxoY9c)
  - [Month 04 – Reinforcing Liquidity Concepts & Price Delivery](https://www.youtube.com/watch?v=npL3ZXJ5zOU)
- [Essentials To ICT Market Structure (2020)](https://www.youtube.com/watch?v=xGFCIUFxsbw)
- 2022 ICT Mentorship: 40/41 tập có phụ đề, lấy từ [playlist](https://www.youtube.com/playlist?list=PLVgHx4Z63paYiFGQ56PjTF1PGePL3r69s); một tập tắt phụ đề.
- 2023:
  - [Deep Dive Into IOF](https://www.youtube.com/watch?v=vN2BkfyRWE4)
  - [Immediate Rebalance & IOF](https://www.youtube.com/watch?v=ZtLMTXv-Dr0)
  - [Feb 15, 2023 ES Session Review](https://www.youtube.com/watch?v=SSWN6YSVyFY)
  - [Sep 12, 2023 NQ Algorithmic Price Delivery](https://www.youtube.com/watch?v=9MLRE-n6St8)
- 2024: [How To Trade ICT FVGs Correctly](https://www.youtube.com/watch?v=HhgWGduQZQY)
- Giới hạn:
  - Chưa quét 2023 Mentorship đầy đủ, 2024 Mentorship đầy đủ và các «Twitter Spaces». Có thể còn định nghĩa khác ở đó.
  - Không truy cập trực tiếp được X/Twitter (chỉ đọc qua Thread Reader).
  - SSRN bị chặn (403), nên chỉ có tóm tắt hai preprint.
