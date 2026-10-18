# Từ điển thuật ngữ Việt – Anh

Cách dùng: gặp từ lạ trong tài liệu lab hay sách tiếng Anh thì tra ở đây. Cột «Module» chỉ nơi thuật ngữ được giải thích kỹ.
Xếp theo chủ đề, trong mỗi chủ đề theo thứ tự học.

## Dữ liệu giá (module 1)

| Tiếng Việt | English | Module | Một dòng giải thích |
|---|---|---|---|
| Nến OHLC | OHLC bar / candle | 1 | Giá mở, cao nhất, thấp nhất, đóng trong một khoảng thời gian |
| Nến đã đóng | closed bar | 1 | Nến đã hết khoảng thời gian của nó; lab chỉ dùng nến đã đóng |
| Giá Bid / Ask | bid / ask | 1 | Giá người mua trả / người bán đòi; dữ liệu lab chỉ có Bid |
| Chênh lệch mua – bán | spread | 1, 8 | Ask − Bid; một phần chi phí giao dịch |
| Điểm cơ bản | basis point, bp | 1 | 0,01% |
| Giờ New York | America/New_York | 1 | Giờ lab dùng cho phiên, killzone, mốc ngày |
| Ngày giao dịch | trading day | 1 | Từ 17:00 New York hôm trước tới 17:00 hôm nay |
| Đổi giờ mùa hè | daylight saving time, DST | 1 | Làm giờ UTC của các phiên dịch 1 tiếng |
| Khoảng trống | gap | 1 | Hai nến liền nhau cách hơn một bước khung |
| Lịch phiên | session calendar | 1 | Khai báo giờ mở / đóng để phân biệt nghỉ phiên với thiếu dữ liệu |
| Gộp khung | resample / aggregation | 1 | Ghép nến nhỏ thành nến lớn (M15 → H1) |
| Mốc nến | alignment | 1 | Nến lớn bắt đầu lúc nào (vd 17:00 New York) |
| Lợi suất đơn giản / log | simple / log return | 1 | (P₁ − P₀)/P₀ và ln(P₁/P₀); log cộng được qua thời gian |
| Biên độ thật | true range, TR | 1 | max(high, close trước) − min(low, close trước) |
| ATR, làm trơn Wilder | average true range, Wilder smoothing | 1 | Trung bình trượt của TR, lab dùng làm thước đo biến động |

## Thống kê nền (module 2)

| Tiếng Việt | English | Module | Một dòng giải thích |
|---|---|---|---|
| Phân phối | distribution | 2 | Các giá trị có thể có và tần suất của chúng |
| Trung bình, độ lệch chuẩn | mean, standard deviation | 2 | Mức trung tâm và độ phân tán |
| Độ lệch | skewness | 2 | Phân phối lệch về phía nào |
| Kurtosis dư, đuôi dày | excess kurtosis, fat tails | 2 | Cú lớn xảy ra nhiều hơn phân phối chuẩn |
| Ước lượng, sai số chuẩn | estimate, standard error (SE) | 2 | Con số tính từ mẫu và độ dao động của nó |
| Khoảng tin cậy | confidence interval (CI) | 2 | Khoảng chứa giá trị thật trong 95% số lần lặp lại |
| Giả thuyết không | null hypothesis, H₀ | 2 | Giả định «không có gì đặc biệt» để thử bác bỏ |
| p-value | p-value | 2 | Xác suất thấy kết quả cỡ này *nếu* H₀ đúng — không phải xác suất H₀ đúng |
| Mức ý nghĩa | significance level, α | 2 | Ngưỡng p chọn trước, thường 0,05 |
| Kiểm định nhiều lần | multiple testing | 2, 7 | Thử nhiều thứ thì chắc chắn có cái «có ý nghĩa» do may |
| Tỷ lệ phát hiện sai | false discovery rate (FDR) | 2, 7 | Phần các phát hiện là giả; Benjamini–Hochberg kiểm soát nó |
| Bootstrap, bootstrap khối | bootstrap, block bootstrap | 2, 3 | Lấy mẫu lại từ dữ liệu; khối giữ được biến động co cụm |
| Cỡ hiệu ứng | effect size | 2 | Khác biệt lớn bao nhiêu, không chỉ có hay không |
| Lực thống kê | statistical power | 2 | Xác suất phát hiện được hiệu ứng nếu nó có thật |
| Hiệu ứng nhỏ nhất phát hiện được | minimum detectable effect (MDE) | 2 | Nhỏ hơn mức này thì dữ liệu không đủ để thấy |

## Ngẫu nhiên và null (module 3)

| Tiếng Việt | English | Module | Một dòng giải thích |
|---|---|---|---|
| Bước ngẫu nhiên | random walk | 3 | Giá đi bằng các cú xóc độc lập |
| Không có nhớ | martingale | 3 | Dự báo tốt nhất cho giá sau là giá hiện tại |
| Thị trường hiệu quả dạng yếu | weak-form efficiency | 3 | Giá quá khứ không cho lợi nhuận vượt trội sau chi phí |
| Null | null model / null baseline | 3 | Mô hình «không có gì» để so |
| Xác suất chạm biên | gambler's ruin / first-passage probability | 3 | P(chạm trên trước) = d_dưới / (d_trên + d_dưới) |
| Xu hướng (trôi) | drift | 3 | Trung bình lợi suất khác 0 |
| Biến động co cụm | volatility clustering | 3, 4 | Biến động lớn đi theo cụm |
| Chuẩn ngẫu nhiên ghép cặp | matched null | 3 | Null cùng giờ × cùng tầng ATR, như `matched_hour_atr_v1` |
| Directional change, overshoot | directional change (DC), overshoot (OS) | 3, 5 | Đổi chiều khi giá đi ngược θ từ cực trị; phần đi tiếp sau đó |

## Chuỗi thời gian và biến động (module 4)

| Tiếng Việt | English | Module | Một dòng giải thích |
|---|---|---|---|
| Tự tương quan | autocorrelation | 4 | Tương quan của chuỗi với chính nó lùi k bước |
| Variance ratio | variance ratio (Lo–MacKinlay) | 4 | Kiểm bước ngẫu nhiên ở nhiều thang cùng lúc |
| Mùa vụ trong ngày | intraday seasonality / periodicity | 4 | Biến động đổi theo giờ phiên |
| Biến động thực hiện | realized variance (RV) | 4 | Tổng bình phương lợi suất trong ngày, tính từ nến nhỏ |
| Parkinson, Garman–Klass, Rogers–Satchell | range-based volatility estimators | 4 | Ước lượng biến động từ OHLC |
| HAR-RV | heterogeneous autoregressive RV | 4 | Dự báo biến động từ trung bình ngày / tuần / tháng |
| Hồi quy về trung bình | mean reversion | 4 | Đi xa mức thường thì có xu hướng quay lại |

## Cấu trúc định lượng (module 5)

| Tiếng Việt | English | Module | Một dòng giải thích |
|---|---|---|---|
| Định nghĩa vận hành | operational definition | 5 | Luật đủ rõ để máy và người cho cùng một đáp án |
| Đỉnh / đáy ngắn hạn, trung hạn | STH / STL, ITH / ITL | 5 | Pivot 1/1; pivot của chuỗi pivot |
| Nến sự kiện, nến xác nhận | event bar, confirmation bar | 5 | Lúc xảy ra và lúc hệ thống biết |
| Độ trễ xác nhận | confirmation lag | 5 | Số nến từ sự kiện tới lúc biết |
| Nhìn tương lai | look-ahead bias | 5, 8 | Dùng thông tin chưa có ở thời điểm đó |
| Vẽ lại | repaint | 5 | Indicator sửa quá khứ khi có nến mới |
| Nhãn hậu kiểm | hindsight label | 5, 7 | Nhãn dựng khi nhìn cả chuỗi; chỉ để chấm |
| Thanh khoản phía mua / bán | buy-side / sell-side liquidity (BSL / SSL) | 5 | Vùng trên đỉnh / dưới đáy cũ |
| Lấy, sweep, run | take, sweep, run | 5 | Xuyên mức; xuyên rồi quay lại; xuyên rồi đi tiếp |
| Phép thử tiền tố | prefix test | 5, 7 | Chạy tới t phải bằng chạy trọn rồi cắt ở t |

## Regime (module 6)

| Tiếng Việt | English | Module | Một dòng giải thích |
|---|---|---|---|
| Trạng thái thị trường | regime | 6 | Trend / range / biến động cao…; không quan sát trực tiếp |
| Mô hình Markov ẩn | hidden Markov model (HMM) | 6 | Trạng thái ẩn chuyển theo xác suất, sinh ra dữ liệu |
| Lọc forward, làm trơn, Viterbi | filtering, smoothing, Viterbi | 6 | Chỉ dùng quá khứ; dùng cả chuỗi; đường trạng thái tốt nhất cả chuỗi |
| Bộ lọc Kalman, xu hướng tuyến tính cục bộ | Kalman filter, local linear trend | 6 | Ước lượng mức và độ dốc kèm sai số |
| Phát hiện điểm đổi | change-point detection (CUSUM, Page–Hinkley) | 6 | Báo khi thống kê của chuỗi đổi |
| Báo động giả, độ trễ phát hiện | false alarm, detection delay | 6, 7 | Hai mặt của mọi bộ phát hiện |
| Thời gian giữ tối thiểu | minimum hold / hysteresis | 6 | Chống đổi trạng thái lặt vặt, đổi lại thêm trễ |

## Đánh giá và overfit (module 7)

| Tiếng Việt | English | Module | Một dòng giải thích |
|---|---|---|---|
| Nhãn tham chiếu | reference label | 7 | Nhãn độc lập với thuật toán, theo rubric |
| Precision, recall, F1 | precision, recall, F1 | 7 | Đúng trong số đã báo; bắt được trong số có thật; trung bình điều hoà |
| Ghép một – một, dung sai | one-to-one matching, tolerance | 7 | Mỗi nhãn ghép tối đa một sự kiện, lệch tối đa k nến |
| Baseline ngây thơ | naive baseline | 7 | «Không làm gì», «luôn tăng», «theo giờ» |
| Đào dữ liệu | data snooping | 7, 8 | Thử nhiều rồi chọn cái đẹp nhất |
| Xác suất backtest bị overfit | probability of backtest overfitting (PBO) | 7 | Cấu hình tốt nhất trong mẫu nằm dưới trung vị ngoài mẫu bao nhiêu lần |
| Trong mẫu / ngoài mẫu | in-sample / out-of-sample | 7 | Dữ liệu dùng để chọn / dữ liệu để kiểm |
| Đoạn phát triển / kiểm tra | development / test segment | 7 | Lab: test từ 01/09/2024, khoá |
| Walk-forward | walk-forward | 7 | Học trên quá khứ, kiểm trên đoạn kế tiếp, cuốn chiếu |
| Rò rỉ, purge, embargo | leakage, purging, embargo | 7 | Thông tin kiểm lọt vào huấn luyện; cách cắt bỏ |
| Shift test | shift test / circular shift | 7 | Null cho chuỗi trạng thái: dịch vòng giữ cấu trúc |
| Sổ đăng ký, đăng ký trước | trial registry, pre-registration | 7 | Ghi mọi lần thử; chốt kế hoạch trước khi xem kết quả |

## Chiến lược và chi phí (module 8)

| Tiếng Việt | English | Module | Một dòng giải thích |
|---|---|---|---|
| Tín hiệu, vị thế | signal, position | 8 | Quyết định; số lượng đang nắm |
| Chi phí một vòng | round-trip cost | 8 | Spread + hoa hồng + trượt giá cho vào và ra |
| Hoa hồng, trượt giá | commission, slippage | 8 | Phí môi giới; giá khớp lệch giá mong muốn |
| Sharpe | Sharpe ratio | 8 | Lợi suất trung bình / độ lệch chuẩn, năm hoá |
| Drawdown tối đa | maximum drawdown | 8 | Mức sụt lớn nhất từ đỉnh vốn |
| Vòng quay | turnover | 8 | Giao dịch nhiều cỡ nào |
| Time-series momentum | time-series momentum (TSMOM) | 8 | Theo dấu lợi suất quá khứ của chính tài sản |
| Mua giữ, đứng ngoài | buy and hold, stay flat / No Trade | 8 | Hai baseline mọi chiến lược phải thắng |
| Thiên lệch chọn | selection bias | 8 | Chọn cái tốt nhất làm kết quả bị thổi phồng |
| Router | router | 8 | Tầng chọn chiến lược theo regime (repo giao dịch) |
