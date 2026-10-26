# Nghiên cứu CantoLab Open Source Fractal

Ngày: 25/09/2026. Phạm vi: tải và đọc mã nguồn Pine, đối chiếu code Python hiện tại. Chưa chạy Pine trên TradingView, chưa port thuật toán, chưa đo kết quả trên dữ liệu thật.

## 1. Nguồn và kết luận

- Repo: https://github.com/cantolab/open-source-fractal
- Commit đã đọc: `1bb53262deba9456f2b1a85d15c6ac5a5e880cf7`.
- Bản tải local: `D:\Finance_System\research-references\open-source-fractal`.
- Mã chính: [openSourceFractal.pine tại commit](https://github.com/cantolab/open-source-fractal/blob/1bb53262deba9456f2b1a85d15c6ac5a5e880cf7/openSourceFractal.pine).
- License trong bản tải: MIT, copyright 2026 cantolab. Khi chuyển thể/copy phần đáng kể phải giữ notice và license; clone tham khảo giữ nguyên LICENSE.

**Đây là indicator mô hình C2 sweep + CISD đa khung, không phải bộ tìm đỉnh/đáy fractal left/right.** Giá trị cho lab là bổ sung bối cảnh sweep và một lớp xác nhận chuyển động, không thay thế pivot M15 hiện đã được người dùng đánh giá tốt.

README tự mô tả implementation độc lập theo Fractal Model được ttrades/toodegrees giảng công khai. Các nhận xét lợi nhuận trong README là quan điểm/tuyên bố của tác giả; bản repo khảo sát không cung cấp bộ backtest có thể tái lập để kiểm chứng các khẳng định đó. Không suy ra phương pháp chắc chắn có hoặc không có lợi thế chỉ từ README.

## 2. Trích xuất thuật toán từ code

### 2.1. Khung thời gian

`autoHTF()` (khoảng dòng 266) ghép M1→M15, M3→M30, M5→H1, **M15→H4**, H1→D1, H4→W1, D1→M1 (tháng). Có cấu hình custom và các preset riêng; preset D1–W1 khác auto D1–M1.

Đây là lựa chọn của indicator, chưa chứng minh cặp M15–H4 tối ưu với XAUUSD. `validTf` chủ yếu điều khiển một số phần hiển thị/cảnh báo; khi port phải validate timeframe ở đầu vào engine.

### 2.2. C1/C2 sweep

Gọi C1 là nến HTF trước C2. Quy tắc tại dòng 478–479:

```text
bullish C2: low(C2) < low(C1) AND close(C2) > low(C1)
bearish C2: high(C2) > high(C1) AND close(C2) < high(C1)
```

Các so sánh là strict. Bằng mức không được tính. Close bullish chỉ cần trên low C1, không bắt buộc nằm hoàn toàn trong range C1; bearish đối xứng. Code không bắt buộc C2 phải xanh cho bullish hoặc đỏ cho bearish. Một outside bar có thể thỏa cả hai phía; không tự ép thành một hướng.

Trigger setup dùng `periodChanged` và `c2Buy[1]`/`c2Sell[1]` (dòng 816–829): hình thành setup ở đầu HTF tiếp theo, khi C2 đã kết thúc. Bias là input người dùng `Neutral/Bullish/Bearish`, không phải dự báo regime tự động.

### 2.3. CISD: cách chọn mức và xác nhận

Đây là logic riêng của repo, không đồng nhất với MSS/BOS phá swing:

- Khi LTF tạo cực trị thấp của HTF đang chạy và thấp hơn low HTF trước, tìm mức bullish CISD.
- Nhánh trực tiếp: nến hiện tại giảm/doji sau nến tăng/doji, không đồng thời cả hai doji; mức lấy open hiện tại.
- Nhánh quét ngược: kiểm tra 2–10 nến trước, tìm chuyển tiếp màu nến, rồi lấy open cao hơn trong các nến giảm được xét; có fallback dùng high/open hiện tại.
- Bearish đối xứng: tìm ở cực trị cao, lấy open thấp hơn trong nhóm nến tăng, có fallback low/open.
- `bullLevelFixed`/`bearLevelFixed` là biến lưu trạng thái lâu dài; không mặc định reset ở mỗi HTF. Khi chuyển thể cần kiểm tra mức cũ, tuổi mức và điều kiện reset, không tự thêm TTL rồi gọi là bản port y hệt.
- Xác nhận dùng `close[1] > cisdLevel` cho bullish và `<` cho bearish. Chỉ số xác nhận được ghi ở bar hiện tại. Khi port phải tách nến close đã vượt mức với thời điểm code phát hiện; không tự dịch thời gian để trông sớm hơn.

Các vị trí: chọn mức dòng 704–748; early reclaim dòng 753–781; xác nhận setup trong `checkCisdConfirm` dòng 649 trở đi.

### 2.4. Vòng đời setup

```text
C2 vừa kết thúc → giai đoạn C3 (phase=1)
HTF kế tiếp, nếu không bị thay bằng setup mới → C4 (phase=2)
HTF kế tiếp nữa → finish (phase=0)
```

CISD có thể đã xác nhận sớm trong C2 hoặc xác nhận về sau. `requireCisdToShow=true` khiến setup chỉ được reveal khi đủ CISD. Đây là điều kiện vẽ, không có nghĩa lịch sử không từng tồn tại ứng viên chưa xác nhận.

`extendAndCheck`: bullish bị vô hiệu nếu low xuyên extreme C2; bearish nếu high xuyên extreme C2. Code cập nhật/xóa đối tượng vẽ. Setup mới cùng hướng thay con trỏ setup đang hoạt động; record cũ vẫn có thể còn hình vẽ. Port cần trạng thái `superseded` minh bạch.

### 2.5. T-Spot và projections

`computeTopBot` tạo vùng giữa open LTF tại chuyển kỳ HTF và midpoint `(prevHigh + prevLow)/2`. Đây không phải FVG ba nến.

Phần có tên `StdDev` dùng biên độ giữa mức CISD và extreme, nhân hệ số nhập vào; **không tính độ lệch chuẩn thống kê**. Không dùng projection này làm confidence interval, xác suất hoặc mục tiêu đã kiểm chứng.

Chưa thấy implementation SMT hoặc bộ nhận diện FVG trong file Pine khảo sát. Không coi repo này là toàn bộ ICT.

## 3. Điểm phải xử lý trước khi đưa vào research engine

| Phát hiện | Bằng chứng | Cách xử lý trong lab |
|---|---|---|
| HTF current OHLC dùng lookahead_on | `request.security` dòng 476 lấy `[open[0], high[0], low[0], close[0], high[1], low[1]]` | Aggregate tuần tự từ nến đã đóng; tách HTF đang hình thành khỏi HTF hoàn tất |
| Vẽ hồi tố | `reveal()` dòng 508 vẽ C2 ở cực trị cũ, C3/C4 ở startBar quá khứ | Lưu `event_time`, `observed_at`, `confirmed_at`; replay chỉ hiện từ thời điểm biết |
| Xóa xác nhận về sau | `checkC4Invalid` dòng 619–638 xóa toàn bộ hình và đặt `cisdConfirmed=false` nếu chỉ xác nhận trong C4 rồi invalid | Ghi sự kiện invalidation mới; không xóa lần xác nhận đã xảy ra |
| Logic và số nến preview bị ghép | `state.prevPrev*` lấy từ `htfCandles`; input `htfCandleCount` cho phép 1 | Tách kho HTF tối thiểu của thuật toán khỏi số nến vẽ |
| Chưa thấy gate barstate.isconfirmed | Điều kiện extreme/invalidation dùng high/low đang chạy | Bản nghiên cứu đầu chỉ xử lý nến LTF đã đóng; công bố khác biệt với Pine realtime |
| Tùy chọn showHistory và giới hạn drawing | Prune/delete đối tượng theo lịch sử hiển thị | Không dùng vật thể còn trên chart làm tập đầy đủ để chấm metric |

**Không kết luận mọi C2 trigger bị look-ahead chỉ vì thấy lookahead_on.** Code đợi đổi HTF và đọc giá trị trước đó; phải xét từng đường dữ liệu. Tuy nhiên, chuỗi HTF current được yêu cầu như trên có rủi ro lộ OHLC cuối kỳ trên lịch sử nếu dùng ở thời điểm trong kỳ. Cần kiểm tra riêng historical/realtime và từng đường phát tín hiệu.

Tài liệu chính thức về lookahead/offset: https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/

Đây là audit tĩnh; chưa tái hiện lỗi trên TradingView. Việc xóa/đổi hình được xác nhận từ code, nhưng ảnh hưởng định lượng tới nghiên cứu phải đo bằng replay/log.

## 4. Đối chiếu lab hiện có

| Thành phần local | Hiện có | Đề xuất tận dụng |
|---|---|---|
| `core/algorithms/swing_pivot/` | Pivot strict, HH/HL, BOS/CHoCH theo mức swing | Giữ nguyên làm baseline cấu trúc M15 |
| `core/algorithms/swing_hierarchy/` | Pivot cấp 2 với thời điểm xác nhận | Thêm bằng chứng cấu trúc độc lập, không thay mức CISD bằng pivot |
| `core/data/resample.py` | Gộp nến theo UTC epoch, có chính sách thiếu nến | Dùng làm tham chiếu aggregate; thêm adapter streaming và kiểm tra mốc H4 đúng feed |
| `core/eval/causality.py` | Kiểm tra invariant sự kiện đã lưu; module ghi rõ không phải prefix replay | Bổ sung bài kiểm tra chạy thật theo prefix, sửa suffix và reset |
| Registry | Pivot, hierarchy, indicator baseline, HMM | Đăng ký thuật toán nghiên cứu riêng sau khi port đạt test |

Lab có nhiều thay đổi chưa commit tại thời điểm đọc. Đợt nghiên cứu này không sửa các file đó, không thay default hoặc push lên GitHub.

## 5. Thiết kế bản thử nghiệm đề xuất

Tên dự kiến: `c2_cisd_research`, version độc lập. Không đặt tên như một phiên bản nâng cấp pivot hoặc tuyên bố bản port tương đương Pine khi chưa đối chiếu.

```text
M15 đã đóng ──→ swing hiện tại ──────────────────→ bằng chứng cấu trúc
          └──→ HTF aggregator → C2 sweep → CISD → vòng đời setup
                                 ↓
                    log sự kiện bất biến để đánh giá
```

Contract cần có `setup_id`, `direction`, `c1_id`, `c2_id`, `level_source_id`, LTF/HTF, giá mức và extreme, alignment, nguồn/dataset hash, event/observed/confirmed time, version và reason. Sự kiện đề xuất: `C2_CONFIRMED`, `CISD_LEVEL_SET`, `EARLY_CISD_CONFIRMED`, `CISD_CONFIRMED`, `SETUP_INVALIDATED`, `SETUP_EXPIRED`, `SETUP_SUPERSEDED`.

Các loại sự kiện này là đề xuất mới, chưa thêm vào schema hoặc UI. Nếu chưa đủ dữ liệu HTF hoặc gặp bucket không hoàn chỉnh, trả trạng thái chất lượng và giữ nguyên lịch sử; không tự tạo sweep.

Các quyết định phải khóa trong spec trước port:

1. Alignment H4 theo feed và thời điểm LTF/HTF đóng; không giả định UTC epoch khớp TradingView/broker.
2. Mức CISD quét ngược có được đi qua ranh giới HTF không; mức stale xử lý theo bản faithful hay biến thể sửa đổi.
3. Hai phía cùng C2 được giữ thành hai setup hoặc đánh dấu ambiguity.
4. Nến vừa xuyên extreme vừa close qua CISD: công bố thứ tự xử lý; Pine gọi invalidation trước confirmation. Không suy ra thứ tự tick từ OHLC.
5. Setup kết thúc, bị thay và bị vô hiệu đều được log; có thể tắt lớp hiển thị nhưng không xóa record.
6. Tách `CISD` khỏi `MSS`, `T-Spot` khỏi `FVG`, projection khỏi sigma thống kê.

## 6. Lộ trình hoàn thiện có kiểm chứng

### A. Tái lập logic tối thiểu

Port aggregator + C2 trước, rồi thêm cách chọn mức CISD và state machine. Giữ candidate/early và confirmed riêng. Các phép sửa khác với upstream có tên/version riêng. Nếu chuyển thể code, kèm MIT notice.

### B. Test bắt buộc

- Bull/bear sweep, bằng mức, không reclaim, outside bar thỏa hai phía.
- Thiếu warm-up và partial HTF đầu/cuối, thiếu một nến M15, ranh giới H4 và gap phiên.
- Nhánh CISD trực tiếp, nhánh tìm ngược, doji, không tìm được, mức cũ và cập nhật mức.
- CISD trước/sau đóng C2, xác nhận ở C3/C4, invalidation và superseded.
- Cùng nến breach extreme và close vượt CISD; kiểm tra thứ tự đã công bố.
- Thêm/sửa tương lai không đổi log đã phát; batch và prefix/restart nhất quán.
- Đổi số nến preview/history không đổi kết quả thuật toán.

### C. Đối chiếu TradingView

Chạy cùng OHLC, cùng ranh giới HTF và cấu hình. Ghi trace sự kiện ở thời điểm phát thay vì so ảnh chart cuối kỳ. Tách sai khác do feed, clock, intrabar và các sửa đổi chủ đích. Python chạy được không chứng minh parity Pine; hiện chưa có trace tham chiếu.

### D. Thí nghiệm giá trị bổ sung

Giữ pivot hiện tại cố định. So C2 riêng, C2+CISD, và C2+CISD+kết hợp bối cảnh swing M15. Nếu thử bias, phải sinh từ thông tin có sẵn lúc đó hoặc lưu bias thủ công tại thời điểm ra quyết định; không gán hindsight.

Metric: số C2, tỷ lệ có CISD, độ trễ C2→CISD, khoảng giá đã đi/ATR lúc biết, invalidation/expiry/superseded, MFE/MAE và phản ứng sau xác nhận theo horizon cố định. Precision/recall cần nhãn C2/CISD riêng, không chấm bằng nhãn HH/MSS rồi coi là cùng tác vụ. Tỷ lệ CISD xác nhận không phải win rate.

Chọn cùng các khoảng liên tục trên XAUUSD M15 để chấm, giữ validation/test theo thời gian. Chưa kết luận hữu ích từ vài setup đẹp. Nếu chỉ mô tả cấu trúc, không cần simulator giao dịch; nếu khẳng định lợi thế giao dịch phải thêm mô hình thực thi và chi phí riêng.

## 7. Việc đã hoàn tất trong lượt nghiên cứu

- Tải source nguyên bản và pin commit bằng hash ghi ở trên.
- Đọc công thức, vòng đời, nhánh chọn CISD và các thao tác vẽ/xóa lịch sử.
- Đối chiếu với pivot, hierarchy, resample và kiểm tra nhân quả của lab.
- Lập đặc tả chuyển thể và danh sách kiểm thử trước khi tích hợp.

Chưa thay thuật toán M15, chưa chạy Pine, chưa thêm detector mới vào web, chưa có kết quả benchmark hoặc cam kết cải thiện.
