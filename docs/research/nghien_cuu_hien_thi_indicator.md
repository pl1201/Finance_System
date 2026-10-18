<!-- Nghiên cứu cho docs/plans/plan_hien_thi_ict.md — tổng hợp từ mã Pine mở và docs Lightweight Charts, 06/10/2026. -->

# Cách hiển thị của các indicator ICT/SMC/thanh khoản: tham khảo để thiết kế lại phần vẽ của `ict_structure`

Ngày: 2026-10-06. Không sửa file nào trong `D:\Finance_System`.

**Cách làm.** Trang script trên TradingView nạp mã nguồn bằng JS nên không đọc trực tiếp được. Vì vậy mình đọc **bản sao mã Pine mở trên GitHub** (cột "Mã đã đọc"), đối chiếu với **mô tả chính thức** trên TradingView / docs LuxAlgo, và đọc docs + mã ví dụ của **Lightweight Charts (LWC) v4.2**. Có một điểm cần lưu ý: bản sao GitHub có thể cũ hơn bản đang chạy trên TradingView. Với TFO thì chắc chắn bản GitHub cũ hơn, vì mô tả trên TradingView có những tính năng mà mã không có.

---

## 0. Nguồn (mã nguồn tham chiếu dùng trong các bảng)

Độ phổ biến lấy từ danh sách tổng hợp của bên thứ ba [S27] (cột `agreeCount`, chụp lúc 04/2026). Đây không phải số liệu chính thức của TradingView.

| Mã | Indicator | Phổ biến [S27] | Trang chính thức | Mã đã đọc |
|---|---|---|---|---|
| S1 | Smart Money Concepts (SMC) [LuxAlgo] | 132 591 | https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/ | https://github.com/idoall/stockindicator/blob/main/trend/SmartMoneyConcepts.pine |
| S2 | Buyside & Sellside Liquidity [LuxAlgo] | 24 647 | https://www.tradingview.com/script/Qk4vBbfL-Buyside-Sellside-Liquidity-LuxAlgo/ | https://github.com/samkomo/nashipai/blob/main/tradingview/indicators/buside_sellside_liquidity.ps |
| S3 | Liquidity Sweeps [LuxAlgo] | 15 683 | https://www.tradingview.com/script/JRqryeJ5-Liquidity-Sweeps-LuxAlgo/ | https://github.com/gestas666/Backtest-Lab/blob/master/indicators/liquidity-sweeps.pine |
| S4 | ICT Concepts [LuxAlgo] | 25 104 | https://fr.tradingview.com/script/ib4uqBJx-ICT-Concepts-LuxAlgo/ | https://github.com/moPPingg/TechPulse/blob/main/ICT.txt |
| S5 | ICT Killzones + Pivots [TFO] | 44 515 | https://www.tradingview.com/script/nW5oGfdO-ICT-Killzones-Pivots-TFO | https://github.com/AubakirovArman/SaltanatbotV2/blob/main/pine/5-ict-killzones-pivots.pine (bản cũ) |
| S6 | Liquidity Swings [LuxAlgo] | 31 201 | https://www.tradingview.com/script/1S2VOnJP-Liquidity-Swings-LuxAlgo/ | https://github.com/heyphat/piner/blob/main/test/pinescripts/lux-algo/liq-swing.pine |
| S7 | Liquidity Pools [LuxAlgo] | 15 734 | https://kr.tradingview.com/script/yXJBwibN-Liquidity-Pools-LuxAlgo | https://github.com/dandandd001-crypto/TaskMaster/blob/main/attached_assets/liquidity%20pools_1760779440778 |
| S8 | Market Structure with Inducements & Sweeps [LuxAlgo] | (không có trong danh sách) | https://www.tradingview.com/script/kMDlPZuz-Market-Structure-with-Inducements-Sweeps-LuxAlgo | repo alvinng214/S1_Silver_Bullet (*) |
| S9 | Pure Price Action Liquidity Sweeps [LuxAlgo] | (không có) | https://jp.tradingview.com/script/WYB2cYmM-Pure-Price-Action-Liquidity-Sweeps-LuxAlgo | repo alvinng214/S1_Silver_Bullet (*) |
| S10 | Price Action Smart Money Concepts [BigBeluga] | 20 464 | https://www.tradingview.com/script/jvNJYfbL/ | https://github.com/IAMATOMIC001/TradingView-MT4-MT5-Indicators-Strategies-Collection/blob/main/Indicators/PA_WITH_SMC_TV_INDICATOR.PINE |
| S11 | ICT HTF MSS & Liquidity (fadi) | (không có) | https://www.tradingview.com/script/vzT0XcBD-ICT-HTF-MSS-Liquidity-fadi | repo alvinng214/S1_Silver_Bullet (*) |
| S12 | Market Structure MTF Trend [Pt] | (không có) | https://www.tradingview.com/script/hn7xYdd7-Market-Structure-MTF-Trend-Pt | repo alvinng214/S1_Silver_Bullet (*) |
| S13 | Market Structure CHoCH/BOS (Fractal) [LuxAlgo] | 12 963 | https://www.tradingview.com/script/ZpHqSrBK-Market-Structure-CHoCH-BOS-Fractal-LuxAlgo | https://github.com/sappbr/pine-code/blob/main/indicators/lux-ms-fractals.pine |
| S14 | Market Structure Break & Order Block (EmreKb) | 50 552 | https://es.tradingview.com/script/DkE7UniD | https://github.com/winter000boy/Trading-Indicators/blob/main/Market_Stratergy.pine |
| S15 | Fair Value Gap [LuxAlgo] | 21 207 | (chưa mở trang chính thức) | https://github.com/rohitbhure65/pine-scripts/blob/master/FVG.PINE |
| S16 | Inversion Fair Value Gaps (IFVG) [LuxAlgo] | 12 713 | (chưa mở trang chính thức) | https://github.com/sappbr/pine-code/blob/main/indicators/lux-ifvg.pine |
| S17 | Order Blocks & Breaker Blocks [LuxAlgo] | 25 230 | (chưa mở trang chính thức) | repo alvinng214/S1_Silver_Bullet (*) |
| S18 | Quantura – Liquidity Sweep & Run Levels | (không có) | (chưa mở trang chính thức) | repo alvinng214/S1_Silver_Bullet (*) |
| S19 | cd_sweep&cisd_Cx | (không có) | (chưa mở trang chính thức) | repo alvinng214/S1_Silver_Bullet (*) |
| S20 | Change in State of Delivery CISD [AlgoAlpha] | (không có) | https://www.tradingview.com/script/DNxCFCO1-Change-in-State-of-Delivery-CISD-AlgoAlpha/ | chỉ đọc mô tả |
| S21 | Docs LuxAlgo Price Action Concepts: Market Structures | (trả phí) | https://docs.luxalgo.com/docs/algos/price-action-concepts/market-structures | chỉ đọc docs |
| S22 | Smart Money Concepts [Modern Neon V2] (bản sửa phần hiển thị của S1) | – | https://www.tradingview.com/script/Cjk9hF0I-Smart-Money-Concepts-Modern-Neon-V2/ | chỉ đọc mô tả |
| S23 | ICT LIQUIDITY indicator [Focused Trader] | – | https://vn.tradingview.com/script/ONYztvvZ-ICT-LIQUIDITY-indicator-Focused-Trader | chỉ đọc mô tả |
| S24 | Trang tag «bsl» (có script «Swing Liquidity Targets») | – | https://www.tradingview.com/scripts/bsl/ (nội dung trang tag thay đổi theo thời gian) | – |
| S25 | Pine docs: Tables | – | https://www.tradingview.com/pine-script-docs/visuals/tables/ | – |
| S26 | Pine docs: Text and shapes | – | https://www.tradingview.com/pine-script-docs/visuals/text-and-shapes/ | – |
| S27 | Danh sách indicator dùng nhiều (CSV, commit 2026-04-18) | – | https://github.com/danywayGit/TradingView/blob/main/MostUseTradingViewIndicatorsList.csv | – |

(*) Các file nằm trong thư mục https://github.com/alvinng214/S1_Silver_Bullet/tree/main/S1_Silver_Bullet, tên file trùng tên indicator.

---

## (a) Các quy ước hiển thị phổ biến, theo từng loại đối tượng

### a1. Mức/vùng thanh khoản (BSL/SSL, EQH/EQL, pool)

| Indicator | Bắt đầu từ | Kéo tới | Nhãn | Khi bị lấy | Giới hạn | Nguồn |
|---|---|---|---|---|---|---|
| BSL/SSL [LuxAlgo] | Pivot **gốc** của cụm đỉnh/đáy ngang nhau (cần >2 pivot nằm trong biên ATR) | Đoạn liền từ pivot tới nến phát hiện, sau đó **nét chấm** kéo tới nến hiện tại | Chữ «Buyside liquidity» / «Sellside liquidity», cỡ tiny, căn trái, đặt ở đầu trái sát đường (hộp chữ cao 0: BSL căn đáy, SSL căn đỉnh), chữ mờ 25% | Đoạn nét chấm **ngừng kéo**. Một **hộp mờ (73%)** xuất hiện từ nến phá, cao từ mức tới đỉnh râu (giới hạn ở mức + k·ATR), kéo tiếp khi giá còn lảng vảng quanh mức | «# Visible Levels» = **3** mỗi phía; Mode **Present** (500 nến cuối) là mặc định | S2 (mã) |
| ICT Concepts [LuxAlgo] | Pivot gốc của cụm | Hộp vùng (mức ± ATR/margin) và đường kéo tới **hiện tại + 3 nến** | «Buyside liquidity» / «Sellside liquidity» (tiny) | Khi close lọt vào vùng: hộp được **tô mờ 90%** và **xoá đường**. Khi close vượt hẳn vùng: hộp dừng tại nến đó | «# Visible Liq. boxes» = **2**; Mode Present | S4 (mã + mô tả) |
| Liquidity Swings [LuxAlgo] | Nến pivot (đường) + **hộp vùng râu** (từ đỉnh tới thân, hoặc cả cây nến) | Hiện tại + 3 nến | Số **khối lượng tích luỹ** đặt tại pivot | Đường **dừng ở nến có close vượt** và **chuyển sang nét đứt** | Lọc theo số lần chạm/khối lượng | S6 (mã) |
| ICT HTF MSS & Liquidity (fadi), dùng khái niệm ICT STH/ITH/LTH | Nến pivot (ST/IT/LT) | Hiện tại + **10 nến** («Extend» = 10) | – | «Open» = **liền**, tím mờ 50%. «Claimed» = **chấm**, đen mờ 50%, **dừng tại nến lấy**. «Reclaimed» = đổi **đỏ** | «Number of lines» = 50 | S11 (mã + mô tả) |
| SMC [LuxAlgo] EQH/EQL | Pivot thứ nhất | Pivot thứ hai (đoạn nối 2 đỉnh/đáy) | «EQH» (màu giảm, phía trên) / «EQL» (màu tăng, phía dưới), đặt **giữa đoạn** | – | Mode Present thì chỉ giữ cặp mới nhất | S1 (mã) |
| TFO Killzones + Pivots | Nến tạo đỉnh/đáy của phiên | Nến hiện tại | Bản cũ: «AS.H», «LO.L»… đặt tại pivot. Bản mới: nhãn **ở bên phải**, có tuỳ chọn hiện giá, nhãn cùng giá thì **gộp lại** | Dừng ở nến «traded through». Bản mới có tuỳ chọn **vẫn kéo dài sau khi bị mitigate** | **Cutoff time** (mặc định 12:00) để ngừng kéo; **Timeframe Limit** (mặc định 30m) để không vẽ trên khung lớn; «drawing limit» | S5 (mã bản cũ + mô tả bản mới) |
| Liquidity Pools [LuxAlgo] | Nến chạm đầu tiên | Hiện tại (hộp lớn dần theo số lần chạm) | Số khối lượng ở bên phải | – | Tuỳ chọn tô nến trong vùng (mặc định tắt) | S7 (mã + mô tả) |
| Quantura Sweep & Run | Pivot | Nến cuối | – | Dừng đúng ở nến lấy | – | S18 (mã) |
| Swing Liquidity Targets | – | – | – | «The line freezes there and turns gray» (đóng băng và chuyển xám) | – | S24 (mô tả) |
| ICT LIQUIDITY [Focused Trader] | Pivot | Tuỳ chỉnh | Dấu **x** trên nến lấy | Tuỳ chọn **xoá thanh khoản đã bị lấy** | Mặc định 50 đường (trước là 500, gây chậm) | S23 (mô tả) |

**Điểm chung.**
1. Mọi script đã đọc đều đặt **x1 = nến pivot gốc**, kể cả khi pivot chỉ được xác nhận sau vài nến.
2. Mức còn nguyên được kéo tới nến hiện tại, thường **thêm 3–20 nến khoảng trống** bên phải.
3. Khi bị lấy thì **dừng ở nến lấy** và đổi kiểu: chấm, đứt, mờ/xám, hoặc tô hộp.
4. Số mức hiển thị thường là **2–3 mỗi phía**.
5. Màu cho mức thanh khoản **không thống nhất**:
   - S2 dùng BSL xanh lá, SSL đỏ.
   - S1/S6 dùng đỉnh màu đỏ, đáy màu xanh.
   - S4 dùng **cam/cyan** và S11 dùng **tím**. Đây là các màu không mang nghĩa tăng/giảm.

### a2. Sweep / stop hunt / run

| Indicator | Đánh dấu ở đâu | Dạng | Nối về mức bị quét? | Nguồn |
|---|---|---|---|---|
| Liquidity Sweeps [LuxAlgo] | Nến quét | Đường từ pivot tới nến quét, màu mờ 50%: **nét chấm** = quét bằng râu, **nét đứt** = phá rồi retest. **Vạch dọc dày (width 3)** từ mức tới đầu râu. **Hộp nhỏ** (n-1..n+1) giữa mức và đầu râu, mờ khoảng 75%, kéo sang phải tới khi close vượt hộp hoặc tối đa **300 nến**. Thêm một **đoạn chấm 3 nến** từ râu đối diện làm mốc vào lệnh. Ảnh minh hoạ trong mô tả có nhãn «Trigger» | Có: đường đi từ pivot gốc tới nến quét | S3 (mã + mô tả) |
| Pure PA Liquidity Sweeps [LuxAlgo], swing theo kiểu ICT Short/Intermediate/Long term | Nến quét | Đường liền từ pivot tới nến quét và hộp nhỏ giữa mức và đầu râu. Mức bị close vượt thì bị **xoá** | Có | S9 (mã) |
| MS with Inducements & Sweeps [LuxAlgo] | Nến quét | **Đường chấm xám** từ đỉnh/đáy tới nến quét, chữ **«x»** đặt **giữa đoạn** | Có | S8 (mã) |
| PA SMC [BigBeluga], «Build Sweep (x)» bật mặc định | Nến quét | Đường cấu trúc đang chờ kết thúc tại nến quét, **chuyển nét chấm**, chữ đổi thành **«x»**. Một đường chờ mới bắt đầu từ đầu râu | Có | S10 (mã) |
| ICT LIQUIDITY [Focused Trader] | Nến lấy | **Dấu x** trên nến | Không rõ | S23 |
| Quantura | Nến sweep (close quay lại) hoặc run (close vượt) | ▲/▼ (plotshape labelup/labeldown) dưới/trên nến | Không, mức chỉ dừng | S18 |
| BSL/SSL [LuxAlgo] | Nến phá | Hộp mờ trên/dưới mức (xem a1) | Có, hộp đặt sát mức | S2 |
| CISD [AlgoAlpha] | Nến CISD sau sweep | ▲/▼, chấm swing, «origin lines» | Có | S20 |

**Điểm chung.**
- Sweep được vẽ **ngay trên mức bị quét**: đoạn kết thúc tại nến quét, kèm «x» giữa đoạn hoặc hộp giữa mức và đầu râu.
- Dấu tách rời (▲▼, x trên nến) thường chỉ dùng cho **tín hiệu**.
- Không thấy script nào dùng chấm tròn có chữ cho sweep.
- Tách **sweep với run** bằng **kiểu nét** (chấm với đứt) có ở S3. S18 thì tách bằng chế độ Sweep/Run.

### a3. Cấu trúc / đổi chiều (BOS / CHoCH / MSS / CISD)

| Indicator | Đường | Nhãn | Màu / nét | Nguồn |
|---|---|---|---|---|
| SMC [LuxAlgo] | Đường ngang từ **pivot bị phá** tới **nến close phá**, tại giá pivot | «BOS» / «CHoCH» đặt **giữa đoạn**, chữ không nền. Phá lên thì nhãn nằm trên đường, phá xuống thì nằm dưới | Internal: **nét đứt**, nhãn **tiny**. Swing: **nét liền**, nhãn **small**. Xanh #089981 / đỏ #F23645. Có chế độ Monochrome | S1 (mã + mô tả) |
| Docs LuxAlgo PAC | Như trên | «CHoCH» (leading) với «CHoCH+» (supported) | «internal structure with dashed lines and labels with a smaller text size» | S21 |
| ICT Concepts [LuxAlgo] | Từ swing tới nến phá | «MSS» / «BOS» tiny, đặt giữa đoạn | MSS **liền**, BOS **chấm**. Ở Mode Present, mỗi MSS mới **xoá toàn bộ** MSS/BOS cũ, nên chỉ còn nhịp hiện tại | S4 (mã) |
| MS IDM & Sweeps [LuxAlgo] | Như trên | «CHoCH» (nét đứt), «BOS» (liền), «IDM» (chấm xám) | Ở nến cuối, script vẽ thêm **«Extensions»**: các mức CHoCH/BOS/IDM **đang chờ** được kéo tới hiện tại, nhãn đặt ở đầu phải. Swing vẽ bằng **chấm tròn** mờ 50% đặt lùi đúng vào nến pivot (offset âm) | S8 (mã) |
| EmreKb MSB-OB | Đường dày (width 2) | «MSB» small, giữa đoạn | Kèm hộp «Bu-OB/Be-OB/BB/MB», chữ căn phải | S14 (mã) |
| Fractal MS [LuxAlgo] | Như trên | «ChoCH» / «BOS» tiny, giữa đoạn | S/R nét đứt (tắt mặc định). Điểm phá được vẽ bằng **chấm tròn** | S13 (mã) |
| MTF Trend [Pt] | Đường **chấm** từ pivot tới nến phá | «CHoCH\n15m» (kèm tên khung) | Khi nhiều khung đổi cùng lúc thì các nhãn được đẩy xuống dòng để không đè nhau | S12 (mã) |
| cd_sweep&cisd_Cx | Đường CISD (hộp cao 0) từ nến gốc tới nến trước | «cisd+» / «cisd-» tiny, giữa đoạn. CISD cũ mờ 50% | Kèm mũi tên plotshape | S19 (mã) |
| fadi (setup) | Sau khi thanh khoản bị «claimed», vẽ **BOS line và FVG box** của setup | – | – | S11 (mã) |

**Nhãn swing HH/HL/LH/LL** (S1): chữ không nền, đặt **tại nến pivot**. «HH/LH» nằm trên đỉnh với màu giảm, «HL/LL» nằm dưới đáy với màu tăng. Tuỳ chọn «Show Swings Points» **mặc định tắt**.

**Strong/Weak High/Low** (S1): chỉ có **một** đỉnh và **một** đáy gần nhất. Đường kéo từ pivot tới **nến cuối + 20 nến**, nhãn tiny «Strong High» / «Weak High» / «Strong Low» / «Weak Low» đặt ở **đầu phải**. Mạnh hay yếu tuỳ theo xu hướng swing. Tuỳ chọn này **bật mặc định**.

### a4. Trạng thái xu hướng / order flow / bias

| Kiểu | Ví dụ | Chi tiết | Nguồn |
|---|---|---|---|
| **Tô màu nến** | SMC «Color Candles» (mặc định **tắt**); BigBeluga «Color Candles» (mặc định tắt); AlgoAlpha CISD («Candle colors follow the latest CISD trend»); LuxAlgo PAC | PAC phân biệt **2 sắc độ**: «Darker bullish color: Bullish CHoCH active / Regular bullish color: Bullish BOS active», tương tự cho phía giảm. Docs nói: «Candle coloring is useful if users want to … determine a detected internal market structure **without having labels and lines on their chart**» | S1, S10, S20, S21 |
| **Dải (ribbon) nhiều hàng** | MTF Trend [Pt] | Pane riêng, mỗi khung một hàng (plot dày 10). Màu **tối sau CHoCH**, **tươi sau BoS**. **Tên khung ghi ở đầu phải** mỗi hàng (label trên nến cuối) | S12 (mã) |
| **Bảng (dashboard) ở góc** | Fractal MS («Structure To Fractal %», mặc định tắt); cd_sweep&cisd (bảng khung lớn / thời gian còn lại); LuxAlgo PAC có «MTF dashboard»; trang tag bias có «MTF Bias Table» | Pine docs: bảng **không neo vào nến**, đặt ở 9 vị trí cố định, nên cập nhật ở nến cuối | S13, S19, S25 |
| **Tô nền theo phiên/khoảng** | ICT Concepts tô Killzones bằng `bgcolor` mờ 93% (mặc định tắt) | Dùng cho **thời gian**, không dùng cho xu hướng | S4 (mã) |
| **Nhãn trạng thái** | Strong/Weak High/Low (S1); Extensions CHoCH/BOS (S8) | Trạng thái được ngầm thể hiện qua **mức sẽ làm đổi chiều** | S1, S8 |

**Khen/chê.** Mình không tìm được nguồn đánh giá độc lập, đáng tin, kiểu «cái nào dễ đọc hơn». Chỉ có tín hiệu gián tiếp:
- Các script lớn để **tô nến tắt mặc định**.
- S22 (bản sửa giao diện của S1) **tăng nhãn từ tiny lên normal**, **bỏ các phần tử nhỏ và nét chấm** để «market structure is readable at a glance». Có thể hiểu là tác giả này thấy nhãn tiny và nét chấm của bản gốc khó đọc.

### a5. FVG / Order Block / Premium–Discount

| Đối tượng | Indicator | Cách vẽ | Nguồn |
|---|---|---|---|
| FVG | SMC [LuxAlgo] | **Hai hộp chồng nhau, chia đôi ở mức 50%**, nên CE hiện ra như một đường ngăn. Mờ 70%. Kéo thêm 1 nến. **Xoá khi lấp hẳn**. Mặc định **tắt** | S1 (mã) |
| FVG | ICT Concepts [LuxAlgo] | Hộp mờ 90%, viền mờ 65%, chữ «FVG». Kéo tới **hiện tại + 8 nến** khi còn mở. Giá **chạm vào** thì viền **nét đứt**. **Lấp hẳn** thì đổi màu «Break» mờ 95%, viền **chấm** và **dừng** tại nến đó. Giữ 2 cái gần nhất | S4 (mã) |
| FVG | Fair Value Gap [LuxAlgo] | Hộp kéo thêm 20 nến, chữ «FVG» căn phải. **Xoá hộp khi mitigate**. Có tuỳ chọn vẽ **đường đứt tại mức mitigate**. «Unmitigated Levels» = N đường còn mở. Bảng thống kê (tắt) | S15 (mã) |
| IFVG | IFVG [LuxAlgo] | Hộp màu gốc tới nến đảo chiều, sau đó hộp **màu ngược**. **Đường giữa (CE) nét đứt xám**. «Show Last» = 5 | S16 (mã) |
| OB | SMC [LuxAlgo] | Hộp từ nến OB kéo sang phải (extend.right), mờ 80%. Internal OB không viền. **Mất đi khi bị mitigate**. Internal OB hiện 5 cái, Swing OB **tắt** | S1 (mã) |
| OB/Breaker | OB & BB [LuxAlgo] | OB: hộp + 2 đường biên liền kéo phải. Sau khi bị phá: phần OB dừng ở nến phá, phần **breaker** có **biên nét đứt** và màu khác, kéo phải. Hiện 3 cái gần nhất mỗi chiều | S17 (mã) |
| Premium/Discount | SMC [LuxAlgo] | **Không tô cả vùng**. Chỉ có 3 dải mỏng, từ swing gốc tới nến cuối, mờ 80%, không viền: **Premium** (5% trên cùng, nhãn trên), **Equilibrium** (47,5–52,5%, nhãn ở bên phải), **Discount** (5% dưới cùng, nhãn dưới). Mặc định **tắt** | S1 (mã) |
| Displacement | ICT Concepts | `plotshape` labelup/labeldown dưới/trên nến, mặc định **tắt** | S4 (mã) |

### a6. Chống rối: tuỳ chọn và mặc định

| Kỹ thuật | Ví dụ (mặc định) | Nguồn |
|---|---|---|
| Mode **Present / Historical** | BSL/SSL và ICT Concepts: **Present** (chỉ 500 nến cuối). SMC: Historical, ở Present thì xoá đối tượng cũ cùng loại. ICT Concepts: mỗi MSS mới xoá MSS/BOS cũ | S2, S4, S1 |
| **N gần nhất** | BSL/SSL 3; ICT liq 2, FVG 2, VI 2, OB 1/1; SMC internal OB 5; OB&BB 3/3; IFVG 5; fadi 50 đường; Focused Trader 50 (giảm từ 500 vì chậm) | S2, S4, S1, S17, S16, S11, S23 |
| **Xoá/khóa khi đã dùng** | Liquidity Sweeps xoá pivot đã bị mitigate, pivot quá 2000 nến, hộp sweep tối đa 300 nến; SMC xoá OB/FVG đã mitigate; FVG Lux xoá hộp; EmreKb «Delete Old/Broken Boxes» = bật | S3, S1, S15, S14 |
| **Tắt sẵn lớp phụ** | SMC: FVG, PD, swing points, MTF levels, color candles đều tắt. ICT Concepts: displacement, killzones, NDOG tắt | S1, S4 |
| **Theo khung / thời gian** | TFO: Timeframe Limit 30m, Cutoff 12:00 | S5 |
| **Cỡ nhãn** | SMC: internal tiny, swing small, EQH tiny (chọn được tiny/small/normal). TFO: Label Size | S1, S5 |
| **Pine tự xoá cái cũ** | Mặc định khoảng 50 nhãn/đường, tối đa 500. Khi vượt thì bản cũ nhất bị xoá (garbage collection) | S26 |

### a7. Chú giải

- **Không có legend màu.** Không script nào trong S1–S19 dựng bảng chú giải màu. Tất cả **ghi chữ ngay trên đối tượng**: «BOS», «CHoCH», «MSS», «IDM», «x», «EQH», «Buyside liquidity», «Strong High», «Premium», «FVG», «Bu-OB», «cisd+»… (đã kiểm trong mã).
- **Bảng chỉ dùng cho thống kê/dashboard**, ví dụ S13, S15, S19, TFO bản mới. Pine docs mô tả bảng là đối tượng cố định ở 9 vị trí, không gắn với nến (S25).
- **Tooltip**:
  - Pine `label.new(..., tooltip=)` hiện thông tin khi rê chuột (S26).
  - TFO bản mới có tooltip trên nhãn mức: «the level's name, price, date, and historical hit rate» (S5).
  - MTF Trend [Pt] có tham số tooltip trên nhãn (S12).
- **Giải thích ý nghĩa nằm trong Settings**: mỗi input có `tooltip`. Ví dụ ở SMC: «Highlight most recent strong and weak high/low points on the chart» (S1).
- **Hàng màu tự ghi tên**: dải trạng thái ghi tên ngay ở đầu phải (S12), không cần legend.

---

## (b) Lightweight Charts 4.1+/4.2 làm được gì tương đương

| Nhu cầu | Cách làm trong LWC 4.2 | Ví dụ / docs chính thức | Giới hạn |
|---|---|---|---|
| Plugin nói chung | **Series primitives** và custom series, **có từ 4.1**. Gắn bằng `series.attachPrimitive()` | Release 4.1: https://github.com/tradingview/lightweight-charts/releases/tag/v4.1.0 · Docs: https://tradingview.github.io/lightweight-charts/docs/4.2/plugins/series-primitives | Tự vẽ bằng Canvas 2D |
| Đoạn ngang/xiên có điểm đầu–cuối + nhãn | Mẫu **Trend Line**: 2 điểm (time, price), nhãn chữ ở hai đầu | https://github.com/tradingview/lightweight-charts/tree/v4.2.0/plugin-examples/src/plugins/trend-line | Nét đứt/chấm tự vẽ (Canvas `setLineDash`, mẫu không có sẵn) |
| Hộp giá × thời gian (vùng, FVG, hộp sweep, PD) | Mẫu **Rectangle Drawing Tool**: primitive hình chữ nhật từ 2 điểm, `zOrder` = `'bottom'`, kèm nhãn trên trục giá/thời gian | https://github.com/tradingview/lightweight-charts/tree/v4.2.0/plugin-examples/src/plugins/rectangle-drawing-tool | Mẫu là công cụ vẽ bằng chuột, cần tách lớp primitive ra để dùng theo dữ liệu |
| Tô nền theo từng nến (trạng thái order flow, killzone) | Mẫu **Session Highlighting**: hàm `time → màu`, tô cột rộng bằng 1 nến, `zOrder 'bottom'` | https://github.com/tradingview/lightweight-charts/tree/v4.2.0/plugin-examples/src/plugins/session-highlighting | Mẫu tô **hết chiều cao**. Muốn làm dải mỏng thì sửa `yTop/height` trong renderer |
| Vùng tô giữa 2 đường | Mẫu **Bands Indicator** (có `autoscaleInfo`) | https://github.com/tradingview/lightweight-charts/tree/v4.2.0/plugin-examples/src/plugins/bands-indicator | – |
| Chữ cố định trong pane | Mẫu **Anchored Text**: neo theo **vị trí pane** (top/middle/bottom × left/middle/right), **không** neo theo time/price | https://github.com/tradingview/lightweight-charts/tree/v4.2.0/plugin-examples/src/plugins/anchored-text | Không dùng được làm nhãn gắn nến. Nhãn gắn nến phải tự vẽ trong primitive |
| Đường giá chỉ vẽ phần bên phải | Mẫu **Partial Price Line** | https://github.com/tradingview/lightweight-charts/tree/v4.2.0/plugin-examples/src/plugins/partial-price-line | – |
| Danh sách mọi mẫu | Gồm cả Tooltip, Vertical Line, Delta Tooltip, Shaded Background Series… | https://tradingview.github.io/lightweight-charts/plugin-examples/ | – |
| Thứ tự lớp | `zOrder`: `'bottom'` (dưới mọi thứ trừ nền), `'normal'`, `'top'` (trên cả crosshair) | https://tradingview.github.io/lightweight-charts/docs/4.2/api/type-aliases/SeriesPrimitivePaneViewZOrder | – |
| Hover / tooltip trên đối tượng | `hitTest()` có trong `ISeriesPrimitiveBase` 4.2. Hoặc dùng `subscribeCrosshairMove` cộng một div HTML | https://tradingview.github.io/lightweight-charts/docs/4.2/api/interfaces/ISeriesPrimitiveBase · https://tradingview.github.io/lightweight-charts/tutorials/how_to/tooltips | – |
| Legend / dòng trạng thái | LWC **không có legend sẵn**. Docs hướng dẫn dùng div HTML cập nhật theo crosshair | https://tradingview.github.io/lightweight-charts/tutorials/how_to/legends | – |
| Marker | `series.setMarkers`: `position` chỉ có `aboveBar` / `belowBar` / `inBar`; `shape` gồm circle/square/arrowUp/arrowDown; có `text`, `size`, **không có tooltip** | https://tradingview.github.io/lightweight-charts/docs/4.2/api/type-aliases/SeriesMarkerPosition · https://tradingview.github.io/lightweight-charts/docs/4.2/api/interfaces/SeriesMarker | **Không neo vào một mức giá**, nên «x» trên mức BSL phải vẽ bằng primitive. Ở **v5** marker có `atPriceTop` / `atPriceBottom` / `atPriceMiddle` (https://tradingview.github.io/lightweight-charts/docs/api/type-aliases/SeriesMarkerPricePosition) |
| Price line | `createPriceLine`: không có tham số thời gian đầu/cuối | https://tradingview.github.io/lightweight-charts/docs/4.2/api/interfaces/PriceLineOptions | Chỉ có giá, **không giới hạn được đoạn** theo thời gian, nên **không hợp cho vùng có vòng đời** |
| Vẽ sang vùng tương lai (+N nến) | `timeToCoordinate` trả `null` nếu thời điểm không có trên thang thời gian. Dùng `logicalToCoordinate` (chỉ số logic) | https://tradingview.github.io/lightweight-charts/docs/4.2/api/interfaces/ITimeScaleApi | Cần quy đổi «+N nến» sang chỉ số logic |
| Pane riêng cho dải trạng thái | v4: chưa có pane, chỉ mô phỏng bằng price scale riêng. **v5 có panes**, marker thành plugin `createSeriesMarkers` | https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5 | Nâng lên v5 sẽ làm đổi API |

---

## (c) Khuyến nghị cho lab (12 điểm)

| # | Làm gì | Vì sao | Học từ |
|---|---|---|---|
| 1 | **Vẽ đường BSL/SSL từ nến ITH/ITL gốc**, không vẽ từ «nến sau lúc biết». Muốn giữ trung thực khi replay thì chỉ **cho đường xuất hiện** khi đã tới thời điểm xác nhận, và (tuỳ chọn) đánh dấu điểm xác nhận bằng một vạch nhỏ/đoạn mờ | Mọi script đã đọc đặt x1 tại pivot, nên trader nhìn là biết «mức này là đỉnh nào». Lúc **hiện** và chỗ **bắt đầu vẽ** là hai chuyện tách được | S1, S2, S6, S11, S18; S8 vẽ chấm swing lùi đúng vào nến pivot |
| 2 | **Thể hiện vòng đời bằng kiểu nét và chỗ dừng**, bỏ marker chấm. Còn nguyên: nét liền, kéo tới hiện tại + 5–10 nến, nhãn chữ ở đầu phải («BSL», «SSL»). Bị lấy: **dừng đúng nến lấy**. Sweep: phần đã kết thúc chuyển **nét chấm**, chữ «sweep» hoặc «x» **giữa đoạn**. Run: **mờ/xám**, chữ «run» rồi ẩn sau K nến. **Màu mức thanh khoản không dùng xanh/đỏ** (ví dụ BSL tím/cam, SSL cyan) để xanh/đỏ chỉ mang nghĩa chiều | Đúng quy ước liền→chấm/đứt→xám của nhiều script, đọc được ngay cả khi không có legend. Màu trung tính tránh nhầm «BSL xanh = tăng» | S11 (open liền / claimed chấm), S6 (dừng + nét đứt), S24 (freeze + gray), S8/S10 («x» + chấm), S3 (chấm = wick, đứt = outbreak); màu: S4 cam/cyan, S11 tím |
| 3 | **Sweep = hộp nhỏ «phần râu vượt mức»** tại nến quét (1–3 nến, mờ khoảng 75%), có thể kéo sang phải tới khi close vượt hộp hoặc tối đa N nến | Cho thấy mức nào bị quét và quét sâu bao nhiêu. Dấu nằm ngay trên mức, không phải chấm tách rời | S3, S9, S2 (hộp sau khi phá) |
| 4 | **Shift vẽ như MSS**: đoạn ngang tại mức bị phá (hoặc tại cạnh FVG của nến displacement) tới nến displacement, chữ «SHIFT ↓/↑» **giữa đoạn**, màu theo chiều mới. **Hộp FVG đi kèm** cùng màu. Ở chế độ Hiện tại chỉ giữ shift gần nhất | Trader ICT đã quen «đường + nhãn giữa đoạn». Gắn shift vào FVG làm rõ «quét → displacement → FVG» | S1 drawStructure, S4 MSS (Present xoá cũ), S11 (BOS line + FVG box của setup sau khi liquidity bị claimed), S19 «cisd±». Riêng cách neo theo FVG là **đề xuất của mình**, không có nguồn trực tiếp |
| 5 | **Order flow theo hai sắc độ**: **đậm/tối = vừa đổi bởi shift**, **tươi = đã có run cùng chiều xác nhận**, **xám = chưa rõ**. Có tuỳ chọn **tô màu nến** (mặc định tắt) thay cho dải | Giống hệt quy ước «darker = CHoCH active, regular = BOS active» của LuxAlgo PAC và «CHoCH tối / BoS tươi» của MTF Trend [Pt]. Tô nến cho đọc trạng thái mà không cần thêm đường | S21, S12, S1/S10 (Color Candles), S20. Màu xám cho «chưa rõ» là đề xuất, không có nguồn |
| 6 | Nếu giữ **dải order flow** thì làm **dày hơn** và **ghi chữ ở đầu phải** («Order flow: TĂNG»). Ở v5 có thể đưa vào pane riêng | Hàng màu tự ghi tên thì không cần legend | S12 (nhãn tên khung ở đầu phải mỗi hàng); LWC v5 panes |
| 7 | **Bỏ legend màu ở góc**, thay bằng: (a) chữ trên đối tượng; (b) **tooltip khi rê chuột** («BSL từ ITH 10:35 · bị sweep 11:20 · close quay lại sau 2 nến»); (c) **dòng trạng thái động** ở góc trên-trái, cập nhật theo nến dưới con trỏ | Không indicator nào đã đọc dùng legend màu. Tooltip và status line là cách TradingView/LWC giải thích | a7; S5 (tooltip), S26 (label tooltip), LWC legends/tooltips tutorial, `hitTest` |
| 8 | **Chế độ «Hiện tại» (mặc định) / «Lịch sử»**. Hiện tại gồm: 2–3 vùng mỗi phía, 1 shift gần nhất, 2–3 FVG còn mở, vùng đã xử lý ẩn sau K nến. Lịch sử: hiện hết, mờ dần theo tuổi | Đây là mặc định chống rối phổ biến nhất | S2 (Present, 3), S4 (Present, 2), S1 (Present), S3 (300 nến), S23 (50 đường) |
| 9 | **Vẽ «mức được bảo vệ» như Strong Low/High**: một đường từ swing tới hiện tại + N nến, chữ «Bảo vệ» hoặc «Strong Low» ở đầu phải. Có thể thêm mức **sẽ làm order flow đổi chiều** và **mục tiêu thanh khoản tiếp theo** dạng «pending» | Trạng thái được thể hiện qua «mức nào phải giữ / mức nào sắp bị nhắm» | S1 (Strong/Weak High/Low), S8 (Extensions CHoCH/BOS/IDM ở nến cuối) |
| 10 | **Nhãn HH/HL/LH/LL**: chữ nhỏ không nền, đặt sát đỉnh (trên) hoặc đáy (dưới) tại nến pivot. **Mặc định tắt**, hoặc chỉ bật cho ITH/ITL | Hữu ích nhưng dễ rối. S1 để tắt mặc định | S1; S22 cho thấy nhãn tiny khó đọc, nên nếu bật thì dùng cỡ vừa |
| 11 | **Dealing range**: không tô cả vùng, chỉ vẽ **3 dải mỏng** (Premium 5% trên, EQ quanh 50%, Discount 5% dưới), mờ 80%, có chữ. **FVG**: hộp kéo tới khi lấp; giá chạm thì **viền đứt**; lấp hẳn thì **mờ + viền chấm + dừng** (hoặc xoá); **CE** là đường đứt 50% hoặc chia đôi hộp. **Displacement**: chỉ nhấn khi gắn với shift | Phân biệt trạng thái bằng kiểu viền, không thêm màu mới | S1 (PD, FVG chia đôi), S4 (đứt→chấm), S16 (CE nét đứt), S15 (xoá khi mitigate) |
| 12 | **Kỹ thuật LWC 4.2**: viết 2–3 series primitive (đoạn có nhãn, hộp, nền theo nến) theo mẫu Trend Line / Rectangle / Session Highlighting, `zOrder 'bottom'` cho hộp và nền. **Không** dùng `createPriceLine` cho vùng (hết chiều ngang). **Không** dùng `setMarkers` cho chữ cần neo vào giá (4.2 chỉ có above/below/inBar). Kéo sang tương lai bằng `logicalToCoordinate`. Hover bằng `hitTest`. Có thể cân nhắc **v5** để có marker `atPrice*` và panes | Đúng khả năng và giới hạn đã kiểm trong docs | (b) |

**Ánh xạ nhanh: hiện tại → đề xuất.**

| Lab hiện có | Đề xuất |
|---|---|
| Dải màu nhỏ ở đáy cho order flow | Dải dày hơn, có chữ ở đầu phải, sắc tối/tươi/xám; hoặc tô nến (KN 5–6) |
| Hai đường vùng gần nhất, bắt đầu từ nến sau lúc biết | Bắt đầu từ pivot, chỉ hiện khi đã xác nhận, dừng ở nến lấy, đổi nét theo vòng đời (KN 1–2) |
| Marker chấm «run↑», «?», «SHIFT» | Run: đoạn mờ + chữ giữa đoạn. Sweep: hộp râu. Shift: đường + chữ giữa đoạn + FVG. «?» chuyển vào sắc xám của order flow (KN 2–5) |
| Chú giải ký hiệu màu ở góc | Bỏ. Dùng chữ trên đối tượng, tooltip và dòng trạng thái động (KN 7) |

---

## Điều chưa chắc / chưa tìm được nguồn

- Mã Pine lấy từ bản sao GitHub, **có thể khác bản mới nhất** trên TradingView. TFO thì chắc chắn bản GitHub cũ hơn mô tả hiện tại.
- Nhãn «Trigger» của Liquidity Sweeps chỉ thấy trong **mô tả/ảnh minh hoạ**, không có trong bản mã đã đọc.
- **Không tìm được** đánh giá người dùng đáng tin so sánh tô nến / dải / dashboard. Ý «nhãn tiny và nét chấm khó đọc» chỉ dựa trên S22, một tác giả duy nhất.
- Không tìm được indicator nào dùng chữ «$$$» để có thể dẫn nguồn.
- Không kiểm phần hiển thị trên NinjaTrader/MT5. LuxAlgo nói có bản cho các nền tảng này nhưng mình không xem.
- Màu xám cho trạng thái «chưa rõ» và cách neo nhãn SHIFT vào FVG là **đề xuất của mình**, không lấy từ nguồn nào.
