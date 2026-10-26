x# Plan: Directional Change theo ATR + phân loại Trend/Range

Ngày: 25/09/2026. Trạng thái: **đặc tả đề xuất để Claude triển khai; chưa phải code đã hoàn thành hoặc phương pháp đã kiểm chứng**.

## 1. Mục tiêu bàn giao

Xây một thuật toán mới trong Market Structure Lab để quan sát bộ khung các nhịp giá XAUUSD M15, giảm các swing nhỏ theo ngưỡng biên độ, rồi diễn giải thành Tăng/Giảm/Range/Chưa rõ. Có chart, replay, giải thích từng quyết định và so với pivot 3/3 hiện tại.

Tên registry: `dc_atr_structure`, version đầu `0.1.0`. Một lựa chọn threshold theo phần trăm cố định được dùng làm đối chứng trong cùng detector. Phần phân loại regime là module riêng, không tác động ngược vào detector DC.

Đây là thuật toán nghiên cứu dựa trên luật. Không gọi là AI, công thức ICT chuẩn, công cụ dự báo đảo chiều hay thuật toán tối ưu. Trend/Range bên dưới là định nghĩa vận hành do dự án đề xuất, không phải chân lý gán nhãn thị trường.

Repo thực tế trên máy lập plan: `D:\Finance_System\market-structure-lab`. Người dùng từng viết `D:\Finance\_System\market-structure-lab`; xác minh repo thực tế trước khi sửa, không tạo bản sao chỉ vì khác cách viết đường dẫn.

## 2. Hướng dẫn cho Claude trước khi code

1. Đọc AGENTS.md áp dụng nếu có, git status và tài liệu `docs/guides/them_thuat_toan.md`.
2. Đọc interface `core/algorithms/base.py`, types, engine, registry, indicators, data validation, API/storage, chart/replay và module đánh giá hiện có.
3. Bảo toàn mọi thay đổi đang có. Không reset/clean, không sửa công thức/version của baseline, không tự commit/push.
4. Giữ C2/CISD như hiện trạng; không mở rộng hoặc chỉnh thuật toán đó trong task này.
5. Triển khai trong stack hiện tại. Không dựng web mới, không migrate framework, không thêm pandas/ML vào core chỉ để thực hiện vòng lặp đơn giản.
6. Tạo `docs/algorithms/thuat_toan_dc_atr_structure.md` từ spec này, lưu các quyết định thực tế và khác biệt nếu phát hiện mâu thuẫn với contract hiện có. Không âm thầm thay công thức.

Nguồn nghiên cứu tham khảo, không phải dependency bắt buộc:

- DC: https://www.bracil.net/finance/papers/Tao-PhD2018.pdf
- ZigZag: https://github.com/jbn/ZigZag — tham khảo nguyên lý; không lấy mặc định đánh dấu đầu/cuối chuỗi làm pivot online.
- Code tham khảo: https://github.com/jbn/ZigZag/blob/main/zigzag/core.pyx

Nếu sao chép/chuyển thể code ngoài, pin commit và giữ license/notice. Bản ATR, chính sách khóa threshold và classifier trong plan là thiết kế của lab, không gán cho tác giả nguồn.

## 3. Kiến trúc và giới hạn MVP

```text
Nến đã đóng → ATR tuần tự → DC detector → pivot xác nhận + nhịp giá
                                           ↓
                               HH/HL/LH/LL/EQ + classifier
                                           ↓
                              log / timeline / API / chart / metric
```

- Tác vụ đầu tiên: một snapshot XAUUSD M15. Thuật toán không hardcode giá XAUUSD nhưng UI chỉ tuyên bố đã thử trên dữ liệu thực sự kiểm tra.
- Giá tìm cực trị là **close**. OHLC chỉ dùng tính ATR và vẽ nến. Pivot close khác pivot wick; UI phải nói rõ.
- Range dùng các swing đã xác nhận; không gán Range chỉ vì không thấy trend.
- Không làm multi-timeframe, protected swing, BOS/MSS, trading simulator, HMM, kernel regression hay tối ưu tự động trong MVP.
- Không đổi k theo regime: giữ DC độc lập để có thể kiểm tra từng lớp.

## 4. Tham số khởi đầu

Tất cả là cấu hình thí nghiệm, chưa phải tối ưu. Validate hữu hạn, kiểu đúng, khoảng hợp lệ và lỗi liên trường.

| Tham số | Mặc định | Ý nghĩa |
|---|---:|---|
| `price_source` | `close` | MVP chỉ nhận close, không cho chọn wick chưa triển khai |
| `threshold_mode` | `atr` | `atr` hoặc `percent` |
| `atr_period` | 14 | Số TR cho ATR Wilder; tối thiểu 2 |
| `atr_multiplier` | 1.5 | k > 0 |
| `reversal_pct` | 0.2 | Chỉ ở percent; **0.2 nghĩa là 0,2%**, không phải 20% |
| `label_tolerance_atr` | 0.1 | Dung sai HH/HL/EQ, không âm |
| `range_swings_per_side` | 3 | m ≥ 3 đỉnh và m đáy gần nhất |
| `range_cluster_tolerance_atr` | 0.5 | Độ rộng tối đa của từng cụm đỉnh/đáy, không âm |
| `range_min_width_atr` | 1.0 | Chiều rộng tối thiểu giữa hai biên, > 0 |
| `range_break_buffer_atr` | 0.25 | Buffer close phá range, không âm |

Form chỉ mở tham số có hiệu lực với threshold_mode. Manifest lưu đầy đủ phương pháp seed ATR, timestamp, gap policy, version detector/classifier và params. Không thêm nhiều tham số smoothing/hysteresis trong vòng đầu.

## 5. ATR và chính sách dữ liệu

### 5.1. ATR Wilder chính xác

Với t từ nến thứ hai trong segment liên tục:

```text
TR[t] = max(high[t]-low[t], abs(high[t]-close[t-1]), abs(low[t]-close[t-1]))
ATR_seed = trung bình của n TR đầu tiên có previous close hợp lệ
ATR[t] = ((n-1)*ATR[t-1] + TR[t]) / n
```

Nến đầu segment chỉ thiết lập previous close. Vì vậy cần n+1 nến để có ATR đầu tiên. Nếu helper hiện có khác seed, viết adapter/hàm mới hoặc ghi rõ và kiểm thử; không làm đổi baseline khác.

Cả mode percent cũng warm-up ATR để label/regime dùng cùng chuẩn. Nếu ATR = 0, không khởi tạo detector cho tới ATR > 0. Sau khi đã chạy, threshold khóa vẫn có hiệu lực; khi cần đặt candidate mới mà ATR = 0 thì chuyển về chờ ATR hợp lệ, không phát pivot với threshold bằng 0. Ghi lý do trong pending state.

### 5.2. Dữ liệu

- Chỉ nến đã đóng, timestamp tăng nghiêm ngặt, OHLC hợp lệ và mọi số hữu hạn. Duplicate/out-of-order → lỗi rõ ràng, không tự sắp lại âm thầm trong core.
- MVP `gap_policy=reset`: nếu khoảng thời gian khác bước timeframe, giữ log cũ nhưng kết thúc segment; bỏ candidate, ATR, lịch sử classifier/range và warm-up lại. Không nối swing hoặc tính trend qua gap.
- Gián đoạn phiên/cuối tuần cũng bị reset theo chính sách này. Hiện số segment/gap và giới hạn đó trong UI; chưa tự suy đoán calendar broker.
- Percent mode yêu cầu close > 0; validate dataset phù hợp.

## 6. DC detector: quy tắc tuần tự

### 6.1. Khởi tạo không nhìn tương lai

Sau warm-up, lấy close hiện tại làm anchor, khóa threshold anchor. Trạng thái `SEEK_DIRECTION`.

- Chờ close >= anchor + threshold → `SEEK_HIGH`, candidate high = close hiện tại.
- Chờ close <= anchor - threshold → `SEEK_LOW`, candidate low = close hiện tại.
- Không phát pivot ở anchor; không truy ngược dữ liệu để ép nến đầu thành pivot.
- Nhánh khởi tạo chỉ chọn hướng, không phát reversal trong cùng nến.

Đây là bootstrap có chủ đích, có thể bỏ lỡ swing đầu segment. Không chấm thiếu warm-up/khởi tạo như false negative.

### 6.2. Threshold ứng viên

Tại nến e tạo hoặc cập nhật cực trị:

```text
ATR mode:     delta_e = atr_multiplier * ATR[e]
Percent mode: delta_e = abs(close[e]) * reversal_pct / 100
```

Lưu `candidate_price`, `candidate_index`, `candidate_atr`, `delta_e`, `threshold_set_at`.

ATR[e] dùng nến e đã đóng, nên khả dụng tại e. **Khóa delta_e cho tới khi có cực trị nghiêm ngặt mới**. Giá bằng cực trị giữ nến đầu và threshold cũ. ATR giảm/tăng ở nến sau không tự đổi threshold của ứng viên.

### 6.3. Theo dõi đỉnh

Ở `SEEK_HIGH`, sau cập nhật ATR của nến t:

1. Nếu close[t] > candidate_price: cập nhật candidate và delta theo t, không xác nhận trong nhánh này.
2. Nếu không có đỉnh mới và close[t] <= candidate_price - delta_e: phát **DC_HIGH** tại candidate, biết tại close_time[t].
3. Chuyển `SEEK_LOW`, candidate low = close[t], khóa threshold mới tại t. Không kiểm tra thêm một reversal trên cùng nến.

### 6.4. Theo dõi đáy

Đối xứng: cập nhật nếu close thấp hơn nghiêm ngặt; xác nhận DC_LOW khi close[t] >= candidate_price + delta_e; chuyển SEEK_HIGH với candidate close[t].

Chạm ngưỡng đảo chiều là đạt (`<=`, `>=`). Mỗi nến tối đa một pivot. Pivot xác nhận luân phiên high/low. Không ép candidate cuối dataset thành pivot.

### 6.5. Thời gian và sự kiện

- `event_time`: thời gian nến cực trị theo convention dự án.
- `confirmed_at`: close_time của nến làm đủ điều kiện reversal; không thêm trễ t+1.
- Lưu index cực trị và index xác nhận, giá close cực trị, confirmation_close, delta khóa, ATR tại cực trị, lag số nến và lag thời gian thực.
- Candidate nằm trong pending/timeline, không được đếm như event đã xác nhận. Sự kiện đã trả về bất biến cả nội dung lẫn object; ID tất định theo run/segment/type/index.
- `reset()` xóa sạch state. Không phụ thuộc dataset length để sinh ID hoặc chốt pivot cuối chuỗi.

## 7. Nhãn swing và phân loại trạng thái

### 7.1. HH/HL/LH/LL/EQ

Khi pivot mới được xác nhận, so với pivot cùng loại liền trước trong cùng segment. Không so với candidate hoặc cực trị cao nhất toàn trend.

```text
tol = label_tolerance_atr * ATR_at_current_pivot_extreme
cur > prev + tol → HH (đỉnh) / HL (đáy)
cur < prev - tol → LH (đỉnh) / LL (đáy)
còn lại         → EQH / EQL
```

Pivot đầu mỗi loại không có nhãn so sánh. Lưu reference ID, giá trước/sau và tol. Không phát hai sự kiện bị matcher đếm trùng cho cùng một pivot: dùng type/details theo convention có sẵn và khai báo mapping rõ ràng.

### 7.2. Trend evidence

Chỉ xét các pivot đã xác nhận:

- `UPTREND`: hai high gần nhất cho HH và hai low gần nhất cho HL.
- `DOWNTREND`: hai high gần nhất cho LH và hai low gần nhất cho LL.
- Thiếu hai high hoặc hai low → `UNKNOWN`, reason thiếu bằng chứng.
- Đủ dữ liệu nhưng mâu thuẫn (ví dụ HH + LL) hoặc có EQ → chưa đủ trend; kiểm tra Range rồi UNKNOWN.

Nhãn cùng loại dùng tolerance đã khóa tại lúc pivot đó xác nhận, không tính lại bằng ATR mới. Trend evidence được cập nhật khi có pivot mới; không diễn giải current close cao hơn một mức là tự động có trend mới.

### 7.3. Điều kiện nhận diện Range mới

Chỉ thử tạo Range tại một lần xác nhận pivot mới, khi không có trend evidence tăng/giảm:

- Lấy m high và m low xác nhận gần nhất trong segment.
- `A = ATR[t]` tại lúc đánh giá; yêu cầu A > 0.
- `spread_high = max(high_prices) - min(high_prices)`; tương tự low.
- Yêu cầu mỗi spread <= range_cluster_tolerance_atr * A.
- `upper = max(high_prices)`; `lower = min(low_prices)`.
- Yêu cầu `min(high_prices) > max(low_prices)` để hai cụm tách nhau và `upper-lower >= range_min_width_atr * A`.
- Close hiện tại phải nằm trong [lower, upper]. Không dùng bằng chứng cũ để tạo một range mà giá đã rời đi.

Nếu đạt: vào `RANGE`, khóa lower/upper, A, buffer = range_break_buffer_atr * A và danh sách pivot bằng chứng. Các tham số trên chỉ là heuristic thí nghiệm.

### 7.4. Theo dõi và rời Range

- Range đang hoạt động giữ nguyên biên/buffer, không kéo biên đuổi theo giá.
- Mỗi nến đóng: close > upper+buffer hoặc close < lower-buffer → event range exit, trạng thái UNKNOWN với reason phá biên đang chờ cấu trúc. Wick vượt biên không đủ.
- Nến phá biên không được tái tạo range hoặc chuyển ngay thành trend từ cùng bằng chứng cũ.
- Sau breakout, chỉ cho classifier xét lại khi có pivot mới xác nhận ở **nến sau** nến breakout.
- Trong Range chưa phá, pivot mới có thể tạo trend evidence: nếu HH+HL hoặc LH+LL đạt, đóng Range và chuyển trend tại lúc biết pivot. Nếu không đạt, tiếp tục giữ Range và biên cũ.
- Không tạo một range mới mỗi pivot khi range cũ còn hoạt động.
- Nếu ở trend/UNKNOWN: mỗi pivot mới xét trend trước, sau đó Range, cuối cùng UNKNOWN.
- Khi không có pivot mới và không có range exit/gap: giữ trạng thái gần nhất; UI gọi đây là “trạng thái theo swing đã xác nhận”, không giả vờ phản ánh mọi thay đổi intrabar.

### 7.5. Thứ tự tại mỗi nến

1. Validate/gap → reset segment nếu cần, lưu chất lượng dữ liệu.
2. Cập nhật ATR; kiểm tra warm-up.
3. Kiểm tra phá Range cũ bằng close hiện tại, ghi cờ block_reclassify_this_bar nếu có.
4. DC cập nhật candidate hoặc phát pivot; gắn nhãn so sánh.
5. Nếu có pivot và không bị block: classifier xét theo quy tắc trên.
6. Ghi timeline/pending sau nến. Chỉ phát regime event khi trạng thái thực sự đổi; range entry/exit có ID và reason riêng.

Không tô trạng thái ngược về nến cực trị. Tô bắt đầu tại confirmed_at/close_time lúc có bằng chứng.

## 8. Hợp đồng tích hợp

File dự kiến, điều chỉnh theo cấu trúc thực tế nhưng không sửa ngoài phạm vi:

- `core/algorithms/dc_atr_structure.py`: adapter StructureAlgorithm và detector.
- `core/algorithms/dc_regime.py`: classifier tách riêng, unit-test độc lập.
- `core/registry.py`, `core/types.py`: đăng ký, type/reason/description tiếng Việt.
- Helper ATR thuần Python: tái sử dụng nếu khớp spec, nếu không thêm module phù hợp.
- `core/eval/`: metric DC/regime và mapping target khi cần.
- `backend/`: API run, serialization, storage/export và manifest tương thích.
- `frontend/`: form, chart overlay, replay, bảng sự kiện, so sánh và metric.

Khảo sát schema hiện có trước khi thêm cột. Metadata mở rộng không được mất qua save/load/export. Migration nếu có phải mở được các run cũ. Không ép DC/regime thành event C2 hoặc các target ICT không cùng định nghĩa.

## 9. Thiết kế giao diện trên app hiện tại

Áp dụng style và chart library đang có. Không cần tạo trang mới để đạt MVP.

### 9.1. Bố cục

- Thanh cấu hình: dataset, thuật toán, mode ngưỡng, ATR period/k hoặc %, nút Chạy và So sánh baseline.
- Chart chính chiếm phần lớn diện tích, dưới là dải trạng thái theo thời gian.
- Panel chi tiết theo lựa chọn: pivot/range đang chọn, công thức với số thực tế, reference và thời điểm biết.
- Bảng event và metric ở dưới hoặc tab hiện có; không dồn mọi nhãn lên chart.

### 9.2. Lớp chart

Mặc định bật: nến, đường nối DC đã xác nhận, marker high/low, dải regime. Mặc định tắt: toàn bộ HH/HL text, đường confirmation, baseline, candidate và debug.

- Pivot close phải vẽ ở đúng close, không tự snap lên wick. Tooltip ghi “đỉnh/đáy theo close”.
- Đường nối pivot là mô tả hồi cứu: segment chỉ xuất hiện khi cả hai đầu đã xác nhận. Replay tại T chỉ được dùng event có confirmed_at <= T.
- Candidate và đoạn nối tới candidate dùng nét đứt, ghi “ứng viên, có thể thay đổi”; không trộn vào metric.
- Điểm xác nhận có hình dạng khác marker cực trị; mở qua toggle hoặc khi chọn một pivot.
- Dải regime bắt đầu từ lúc biết. Không dùng nền tô lại quá khứ theo các pivot mới.
- Range box chỉ kéo từ lúc RANGE được xác nhận tới hiện tại/exit, không vẽ như thể range đã được biết từ pivot đầu tiên.
- Dùng hình dạng/nét và chữ ngoài màu; legend, keyboard focus, bảng thay thế cho thông tin chỉ có tooltip. Tránh nhãn đè lên nhau khi zoom xa.
- Zoom/downsample chỉ ở phần vẽ, không làm mất nến đầu vào thuật toán.

### 9.3. Replay và so sánh

- Bước từng nến, chạy/tạm dừng, lùi/reset, nhảy đến lần xác nhận kế tiếp.
- Lùi replay phải khôi phục đúng candidate/threshold/regime tại cursor, không đọc pending state cuối run.
- So baseline bằng hai run cùng checksum và thời gian, một run pivot 3/3 không đổi, một run DC. Dùng overlay bật/tắt có legend hoặc hai panel đồng bộ trục thời gian nếu app đã hỗ trợ.
- Hiện cảnh báo “pivot baseline theo wick, DC theo close” khi đúng cấu hình; không coi chênh giá marker là lỗi máy móc.
- Mọi loading/error/no pivots/warm-up/gap/no labels phải có trạng thái hiển thị riêng.

## 10. Metric và thiết kế thí nghiệm

### 10.1. Không cần nhãn

- Số pivot xác nhận và mật độ / 1.000 nến hợp lệ sau warm-up; ứng viên không tính.
- Lag median/p90 theo nến và thời gian; reversal distance / candidate ATR tại lúc biết; báo sample count.
- Biên độ nhịp giữa hai pivot đã xác nhận, chuẩn hóa bằng ATR tại pivot đầu nhịp. Cách chuẩn hóa phải ghi trong tooltip/export.
- Tỷ lệ thời gian UPTREND/DOWNTREND/RANGE/UNKNOWN sau warm-up, số lần chuyển trạng thái, độ dài đoạn median; không cộng thời gian gap thành thời gian regime.
- Gap count, segment count, nến đủ điều kiện, số run lỗi nhân quả. Những con số này mô tả hành vi, không phải accuracy.

### 10.2. Có nhãn tham chiếu

- Tách nhãn swing và nhãn đoạn regime. Nhãn độc lập với output đang chấm, có rubric/version/annotator và phạm vi đã gán nhãn.
- Swing: match một-một, đúng high/low, tolerance thời gian và giá cố định trước khi so; báo precision/recall/F1 và lỗi vị trí. Đo độ trễ xác nhận riêng, không cho khớp cực trị đẹp che mất việc biết quá muộn.
- Không coi nhãn wick tự động là ground truth close. Nếu dùng nhãn wick để đánh giá độ gần với mắt người, ghi rõ cross-definition và dùng cùng rubric/tolerance cho mọi run.
- Regime: confusion matrix và macro-F1 chỉ khi có nhãn; nêu cách xử lý UNKNOWN và báo coverage để tránh tăng điểm bằng cách không trả lời. So trên timeline lúc biết, không timeline hồi tố.
- Chưa có nhãn → hiện “chưa có nhãn tham chiếu”, không tự tạo F1 hoặc biến output baseline thành ground truth.

### 10.3. Đối chứng có kiểm soát

1. Cố định snapshot, phạm vi, gap policy và warm-up; lưu manifest từng run.
2. Pivot 3/3 giữ nguyên; DC percent làm đối chứng ngưỡng; DC ATR thử k = 1.0 / 1.5 / 2.0, ATR14. Giữ params classifier cố định khi khảo sát DC.
3. Chọn tham số trên đoạn phát triển, kiểm tra trên đoạn theo thời gian chưa dùng để chỉnh. Không mở rộng grid sau khi xem test rồi vẫn gọi là test độc lập.
4. Baseline wick và DC close có hai khác biệt; ghi rõ đây là so sánh trải nghiệm tổng thể. Khi muốn quy nguyên nhân cho ngưỡng DC cần thêm pivot close 3/3 **trong harness thí nghiệm riêng**, không sửa baseline đã lưu.
5. Chọn theo đánh đổi giữ nhịp lớn / giảm nhịp nhỏ / độ trễ / độ ổn định tham số; không có một điểm “tối ưu” tùy tiện hoặc lấy ít pivot nhất làm tốt nhất.

## 11. Test bắt buộc

### Unit detector/ATR

- ATR seed, Wilder update có fixture tính tay; warm-up, ATR0, OHLC không hợp lệ, NaN/inf, timestamp trùng/lùi.
- Chuỗi tăng/giảm đơn điệu: không ép pivot cuối; đoạn đi ngang: không chia 0 hoặc tạo pivot vô hạn.
- Reversal thiếu ngưỡng/đúng ngưỡng/vượt ngưỡng; đỉnh/đáy bằng nhau giữ lần đầu.
- Threshold giữ nguyên khi ATR đổi nhưng candidate không đổi; candidate mới khóa threshold mới.
- ATR và percent cho kết quả tính tay; percent unit 0.2%; high/low wick cực lớn không tự trở thành pivot close.
- Khởi tạo chờ hướng không dùng suffix; pivot luân phiên, mỗi nến tối đa một; gap reset không nối segment.

### Unit classifier

- HH+HL tăng, LH+LL giảm; HH+LL và thiếu pivot → UNKNOWN.
- Equality/tolerance boundaries; reference cùng loại đúng; không dùng candidate.
- Range đủ m mỗi phía, cluster không đủ ổn định, hai cụm chồng nhau, quá hẹp, close đã ngoài biên.
- Range khóa biên/buffer, wick-only breach không thoát, close breach thoát; nến breakout không tái nhập bằng chứng cũ.
- Pivot ở nến sau breakout mới cho phép phân loại lại; range→trend theo bằng chứng mới.
- Gap/reset, state change không phát trùng, không backdate regime.

### Nhân quả

- Thực sự chạy nhiều prefix và so log/timeline tới T với full run lọc theo lúc biết.
- Thêm/sửa suffix sau T không đổi event/ID/reference trước T.
- Giữ deep copy event đã trả về rồi feed thêm để phát hiện mutation.
- Batch feed tuần tự, reset/replay và UI replay cho kết quả tương đương.
- Toggle layer, zoom, số nến preview không thay output core.

### Tích hợp

- Registry/form validation, API→save→load→CSV/JSON/manifest roundtrip.
- Run cũ mở được, thuật toán hiện có không đổi output ngoài thay đổi được giải thích.
- Browser smoke: chạy, replay trước/sau confirmation, chọn pivot xem công thức, đổi params tạo run mới, so baseline, mở lại run và export.
- Chạy tests thích hợp theo hướng dẫn repo; ghi lệnh/kết quả. Lỗi có sẵn phải được xác minh, không tự nhận định để bỏ qua.

## 12. Checklist triển khai và mốc bốn giờ

Thời gian là khung làm việc, không cam kết đủ mọi tính năng. Không bỏ test nhân quả để kịp giờ. Nếu hết bốn giờ, bàn giao phần chạy được cùng checklist thật; phần còn thiếu không được đánh dấu xong.

- [x] **0:00–0:30:** khảo sát, khóa spec, fixture tính tay, danh sách file tác động.
- [x] **0:30–1:30:** ATR + DC + HH/HL + tests detector/nhân quả.
- [x] **1:30–2:15:** classifier trend/range + tests trạng thái và gap.
- [x] **2:15–3:15:** registry/API/storage, chart/replay cơ bản, tooltip giải thích.
- [x] **3:15–4:00:** chạy snapshot, so baseline, regression/smoke, tài liệu kết quả.

Cập nhật 25/09/2026 (triển khai v0.1.0 — chi tiết và khác biệt: [`thuat_toan_dc_atr_structure.md`](../algorithms/thuat_toan_dc_atr_structure.md)):

- [x] Core `dc_atr_structure` + `dc_regime`, ATR seed đúng spec, gap reset, 75 test mới (332/332 test pass).
- [x] Web: form `show_if`, chart close/ứng viên/Range/dải regime, tooltip + panel công thức, replay + «tới xác nhận kế tiếp», overlay baseline 3/3, export/manifest; smoke Chrome headless 23/23.
- [x] 10 run đối chứng tái lập trên XAUUSD M15 thật (dev 01–08/2024, test 09–12/2024) + pivot close 3/3 trong harness.
- [x] v0.2.0: `gap_policy=bridge_short` (nối gap ≤ 2 giờ, mặc định vẫn `reset`), 8 run đối chứng mới; panel baseline đồng bộ; ẩn chữ nhãn khi zoom xa; bàn phím trên bảng sự kiện; ô tích so chéo định nghĩa ở trang Đánh giá. 342/342 test, smoke 23/23 + 19/19.
- [ ] **Chưa làm:** metric có nhãn thật (cần người gán nhãn swing close và giao diện gán nhãn đoạn regime); downsample khi vẽ (chưa cần — chưa đo được vấn đề hiệu năng); gap theo lịch phiên broker (hiện chỉ theo độ dài gap).

MVP phải có core đúng + replay đúng + quan sát được; có thể hoãn layout so sánh hai panel, metric có nhãn chưa tồn tại và tối ưu render. Không hoãn bảo toàn thời điểm biết, export dữ liệu cần kiểm tra hoặc việc ghi rõ giới hạn.

## 13. Tiêu chí nghiệm thu và bàn giao

1. Chạy detector mới end-to-end trong web, không chỉ một notebook/script.
2. Đường swing dễ đọc; phân biệt close/wick, candidate/confirmed, event_time/confirmed_at.
3. Trend/Range có reference giải thích, UNKNOWN đúng nghĩa, range có biên khóa và thời điểm bắt đầu thực.
4. Không dùng tương lai, không đổi log xác nhận; có tests chứng minh trên prefix/suffix.
5. Có một tập run đối chứng tái lập và số liệu thực tế; không tự nhận ATR tốt hơn nếu kết quả chưa ủng hộ.
6. Có tài liệu thuật toán, tham số/gap policy/giới hạn và ảnh hoặc hướng dẫn thao tác. Dữ liệu synthetic phải ghi là synthetic.
7. Báo cáo file thay đổi, tests đã chạy, checklist còn thiếu; không tự push.

## 14. Prompt giao việc cho Claude

> Bạn là coding agent triển khai trong repo Market Structure Lab hiện có. Đọc `docs/plans/plan_dc_atr_trend_range.md` và `docs/guides/them_thuat_toan.md`, kiểm tra AGENTS.md/git status rồi thực hiện plan. Mục tiêu: thêm `dc_atr_structure` v0.1.0 dùng close, DC ngưỡng ATR khóa tại cực trị và mode percent đối chứng; phân loại Trend/Range/UNKNOWN từ swing xác nhận bằng module độc lập; tích hợp chart/replay/API/lưu trữ/export/metric theo spec. Giữ nguyên pivot baseline, không tiếp tục phát triển C2/CISD. Ưu tiên một bản chạy end-to-end trong buổi bốn giờ, có kiểm thử nhân quả, tooltip giải thích và run so sánh tái lập. Không tự đổi công thức hoặc tô trạng thái hồi tố để chart đẹp. Bảo toàn thay đổi đang có, không tạo app mới, không tự commit/push. Tiến hành khảo sát và triển khai, cập nhật checklist đúng thực tế, báo cáo kết quả kiểm thử và phần chưa hoàn tất; không chỉ trả lại một kế hoạch khác.
