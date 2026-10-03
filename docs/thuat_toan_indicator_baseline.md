# Đặc tả baseline chỉ báo (đối chứng)

**Mã thuật toán:** `indicator_baseline`
**Phiên bản:** `1.0.0`
**File:** [`core/algorithms/indicator_baseline/algorithm.py`](../core/algorithms/indicator_baseline/algorithm.py),
công thức thành phần [`core/indicators.py`](../core/indicators.py)

Đây là **đối chứng đơn giản** (mục 13 tài liệu nhóm): độ dốc đường trung bình
chuẩn hoá ATR, ADX, bề rộng vùng giá. Nó **không** phải bộ phân loại Trend/Range
của sản phẩm, không có accuracy, không có P&L.

Không dùng TA-Lib. Mọi smoothing viết bằng thư viện chuẩn để đối chiếu được
với MQL5 (`iMA MODE_SMA`, `iATR`, `iADX`).

---

## 1. Tham số và warm-up

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `sma_period` | 20 | SMA của **close** |
| `slope_lookback` | 5 | `slope = SMA[t] − SMA[t − lookback]` |
| `atr_period` | 14 | ATR Wilder |
| `adx_period` | 14 | ADX / +DI / −DI Wilder |
| `range_period` | 20 | Donchian: max(high) − min(low) |
| `slope_min` | 0.15 | `|slope| / ATR` tối thiểu để gắn up/down |
| `adx_trend_min` | 20 | ADX tối thiểu để gắn up/down |
| `range_narrow_max` | 3.0 | `Donchian/ATR` tối đa **và** ADX dưới ngưỡng → range |

**Warm-up (số nến đóng tối thiểu):**

```
max(sma_period + slope_lookback, atr_period, 2 * adx_period, range_period)
```

Trước mốc này không sinh sự kiện; `data_status = WARMUP_INSUFFICIENT` nếu cả
chuỗi ngắn hơn.

## 2. Công thức smoothing — chỗ hay lệch MQL5

### SMA (`iMA`, `MODE_SMA`)

```
SMA[t] = (close[t-n+1] + … + close[t]) / n
```

**Không** dùng EMA (`MODE_EMA`, α = 2/(n+1)) và **không** dùng SMMA.

### True Range

```
TR[0] = high[0] − low[0]
TR[t] = max(high−low, |high − close[t-1]|, |low − close[t-1]|)
```

### ATR Wilder (`iATR`)

```
ATR[period-1] = SMA(TR, period)          # seed
ATR[t]        = (ATR[t-1] * (period-1) + TR[t]) / period
```

Đây **không** phải EMA α=2/(n+1). Lệch so với MQL5 thường do nhầm hai công thức
này, hoặc do nến đang hình thành (lab chỉ dùng nến đóng).

Giá trị ATR đầu: index `atr_period - 1`.

### ADX Wilder (`iADX`)

Với nến t ≥ 1:

```
up   = high[t] − high[t-1]
down = low[t-1] − low[t]
+DM  = up   nếu up > down và up > 0,   ngược lại 0
−DM  = down nếu down > up và down > 0, ngược lại 0
TR   = True Range
```

+DM, −DM, TR được làm mượt Wilder (seed = SMA `period` mẫu, rồi bước Wilder).

```
+DI = 100 * s+DM / sTR
−DI = 100 * s−DM / sTR
DX  = 100 * |+DI − −DI| / (+DI + −DI)   (0 nếu mẫu số 0)
ADX seed = SMA(DX, period)
ADX[t]   = (ADX[t-1] * (period-1) + DX[t]) / period
```

Nến index 0 chỉ lưu OHLC, chưa có DM. ADX đầu tiên tại index `2 * adx_period - 1`.

### Donchian width

```
width[t] = max(high[t-n+1 … t]) − min(low[t-n+1 … t])
width_norm = width / ATR
```

Không nội suy khoảng trống.

## 3. Quy tắc phân loại

Khi ATR, ADX, SMA (đủ lookback) và Donchian đều có giá trị:

| Điều kiện (theo thứ tự) | Lớp | `structure_type` |
|---|---|---|
| `ADX ≥ adx_trend_min` **và** `|slope|/ATR ≥ slope_min` **và** slope > 0 | up | `BASELINE_UP` |
| như trên, slope < 0 | down | `BASELINE_DOWN` |
| `width/ATR ≤ range_narrow_max` **và** `ADX < adx_trend_min` | range | `BASELINE_RANGE` |
| còn lại | uncertain | `BASELINE_UNCERTAIN` |

Sự kiện chỉ phát khi **lớp đổi** so với nến trước (kể cả lần hợp lệ đầu tiên
sau warm-up). `event_bar_index = confirmed_bar_index`, độ trễ 0: chỉ báo dùng
close của chính nến đang đóng.

Ngưỡng mặc định là điểm xuất phát để đối chứng, **không** phải ngưỡng đã tối ưu
trên XAUUSD.

## 4. Giới hạn

* Không phải tín hiệu vào lệnh. Không có precision/recall trừ khi có nhãn
  tham chiếu gán tay.
* ADX/ATR Wilder trên chuỗi rất ngắn (period=2) hữu ích cho test tính tay, không
  phản ánh tham số thực tế.
* `timeline_point` vẽ được SMA/ATR/ADX nếu giao diện đọc các trường đó; marker
  sự kiện là đổi lớp.
