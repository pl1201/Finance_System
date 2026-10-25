# Thêm thuật toán mới và hướng tích hợp MT5/MQL5

## 1. Kiến trúc: ba phần tách rời

```
core/data/      adapter dữ liệu   — nạp CSV, kiểm tra, chuẩn hoá thời gian
core/vocab/     từ vựng sự kiện   — loại, mã lý do, câu giải thích (theo họ)
core/algorithms/ lõi thuật toán   — mỗi thuật toán một gói, thuần tính toán
core/engine.py  chạy & replay     — nạp nến tuần tự, gom sự kiện, thống kê
backend/        API + lưu trữ     — FastAPI, SQLite (routers/ → services/ → storage/)
frontend/       giao diện         — HTML/JS tĩnh, không bước build
  js/lib/         dùng chung (dom, format, timeframe, api, labeldraft)
  js/chart/       lõi chart: nến, khung nhìn, marker chung, tooltip; lớp vẽ chung primitives.js; lớp phủ Đánh giá/Gán nhãn
  js/algos/       plugin hiển thị theo thuật toán — phần vẽ/giải thích riêng (Bước 4)
  js/pages/       lab · label · eval — script nhỏ theo tính năng, chung namespace MSL.<trang>
```

Lõi thuật toán **không import** FastAPI, SQLite, pandas, notebook hay
MetaTrader5. `hmm_online` import hmmlearn/numpy **chỉ khi fit**. Nhờ vậy phần
còn lại chạy được khi chưa cài các gói đó.

## 2. Thêm một thuật toán

### Bước 1 — tạo gói `core/algorithms/vi_du/` với lớp con của `StructureAlgorithm`

Mỗi thuật toán là một gói: `__init__.py` xuất lớp, `algorithm.py` chứa lớp. Phần riêng
lớn thì tách thêm file trong gói (mẫu: `dc_atr_structure/` có `detector.py`, `regime.py`, `metrics.py`;
`ict_structure/` có `eval_targets.py`).
Khái niệm dùng chung (lịch phiên / khoảng trống, pivot, phân cấp, thứ tự đỉnh/đáy, dealing range,
displacement, FVG, vùng thanh khoản + vòng đời, shift, killzone, order flow) lấy từ `core/components/` thay vì cài lại — mẫu ghép: `ict_structure/algorithm.py`. Tham số lịch phiên đặt
tên `session_calendar` với mặc định `auto` thì service tự đổi theo mã của dataset.

```python
# core/algorithms/vi_du/algorithm.py   (và __init__.py: from .algorithm import ViDuAlgorithm)
from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.types import Bar, StructureEvent


class ViDuAlgorithm(StructureAlgorithm):
    name = "vi_du"
    display_name_vi = "Thuật toán ví dụ"
    version = "0.1.0"
    description_vi = "Mô tả ngắn hiển thị trên giao diện."

    @classmethod
    def param_specs(cls):
        return (
            ParamSpec("cua_so", "Độ dài cửa sổ", "int", 20, min=2, max=500,
                      help_vi="Số nến dùng để tính."),
        )

    def __init__(self, **params):
        p = self.validate_params(params)
        self.cua_so = p["cua_so"]
        self.params = p
        self.reset()

    def reset(self):
        self._bars = []

    def warmup_bars(self):
        return self.cua_so

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        self._bars.append(bar)
        if len(self._bars) < self.cua_so:
            return []          # chưa đủ warm-up
        return []              # trả về các sự kiện XÁC NHẬN tại chính nến này
```

### Bước 2 — đăng ký

Thêm vào `_ALGORITHMS` trong [`core/registry.py`](../../core/registry.py).
Giao diện tự đọc registry để dựng dropdown và form tham số — thuật toán chỉ phát
sự kiện thì **không cần sửa frontend**. Cần vẽ hoặc giải thích riêng: Bước 4.

### Bước 3 — viết test

Tối thiểu: một chuỗi nhỏ có kết quả tính tay, một test warm-up, và một test
"thêm dữ liệu sau T không đổi sự kiện đã xác nhận tại T"
(xem mẫu trong `tests/core/test_replay_causality.py`). Đặt ở `tests/algorithms/test_vi_du.py`;
test qua API (lưu → mở lại → CSV/manifest) ở `tests/api/`.

### Bước 4 — (tuỳ chọn) plugin hiển thị `frontend/js/algos/vi_du.js`

Không có plugin, sự kiện loại mới vẫn hiện trong bảng sự kiện, tooltip và CSV; trên chart nó
được plugin `swing` (fallback) vẽ thành chữ tên loại dưới nến (lớp «Nhãn HH / HL / LH / LL»).
Muốn marker, đường mức, ghi chú, chỉ số… riêng thì viết **một** file plugin — không sửa
`chart/market-chart.js` hay các file trong `pages/`:

```js
/* Plugin hiển thị vi_du: marker VD dưới nến xác nhận. */
(function (MSL) {
  'use strict';

  MSL.algos.register({
    id: 'vi_du',
    algorithms: ['vi_du'],               // tên thuật toán Python plugin phụ trách
    layers: { vi_du: true },             // lớp hiển thị + mặc định (S.layers ở trang Thử nghiệm)
    chart: {
      ownsEvent: function (t) { return t.indexOf('VI_DU_') === 0; },
      marker: function (e, ctx) {
        if (!ctx.layers.vi_du) return;
        ctx.markers.push({
          time: ctx.timeByIndex[e.confirmed_bar_index], position: 'belowBar',
          color: '#90caf9', shape: 'circle', text: 'VD', size: 1
        });
      }
    },
    notes: function (stats, dataStatus) {   // ghi chú dưới banner (ẩn sau nút «Ghi chú» — mặc định tắt); null = ẩn
      return [['info', 'Vi du: mô tả ngắn cách đọc chart.']];
    }
  });
})(window.MSL);
```

Rồi:

1. Thêm `<script src="/app/js/algos/vi_du.js?v=…"></script>` vào **cả bốn** trang
   (`index.html`, `gan-nhan.html`, `danh-gia.html`, `live.html`), sau các plugin khác và **trước**
   `chart/market-chart.js` — chart tạo series của mọi plugin khi khởi tạo.
2. Ô bật/tắt lớp chưa tự sinh: thêm `<label class="check"><input type="checkbox" data-layer="vi_du"
   checked>…</label>` vào `#layer-toggles` trong `index.html`, hoặc một khung riêng rồi khai
   selector của nó trong `panels` (chỉ hiện khi chọn thuật toán này, mẫu `#dc-layers`). Khung dùng ở nhiều trang thì
   để thành mảnh `frontend/partials/<tên>.html` và ghép bằng `<!--#include <tên> -->` (mẫu `#ict-layers`: trang Thử
   nghiệm và trang Live MT5); gắn ô bằng `MSL.layerToggles` (`lib/layers.js`).
   Lớp chỉ có nghĩa khi một lớp khác bật: thêm `data-requires="<lớp>"` vào label và input — trang
   (`lib/layers.js`, trang Thử nghiệm và Live MT5) làm mờ, vô hiệu ô khi lớp đó tắt và giữ nguyên giá trị riêng của ô;
   plugin vẫn tự kiểm cả hai lớp khi vẽ (mẫu: các lớp dưới «Chi tiết» `ict_detail` trong `#ict-layers`).
   Thuật toán chỉ dùng khung riêng thì khai `ownLayersOnly: true` — trang ẩn khung lớp chung `#layer-toggles`
   (swing / BOS…) khi thuật toán này đang chọn (mẫu: `ict_structure.js`).
3. Dòng trạng thái / chú giải riêng bằng chữ đặt trong cột phủ `.chart-overlay-col` của `index.html` (cùng cột với
   khung «Thuật toán đang làm gì», theo luồng nên không chồng nhau khi xuống dòng); bật/tắt bằng hook `syncLegend`,
   kiểm phần tử có tồn tại vì trang Gán nhãn / Đánh giá không có. Ưu tiên chữ ngay trên đối tượng + một dòng trạng
   thái (mẫu: `#ict-status` — 2 hàng, cắt «…», nội dung theo nến dưới chuột qua hook `onCrosshair`) hơn chú giải ký
   hiệu màu (mẫu cũ: `#dc-legend`). Phần tử nào phủ lên chart (dòng trạng thái, khung giải thích, nút) thì gắn
   thuộc tính `data-chart-reserve`: nhãn do `MSL.primitives` vẽ sẽ tránh vùng đó
   (`MSL.primitives.reservedRects(mc.container)` làm `reserved` của `Segments`).
4. Đối tượng neo (nến, giá) — đoạn ngang có chữ, hộp giá × thời gian, dải theo nến — dùng lớp vẽ chung
   [`frontend/js/chart/primitives.js`](../../frontend/js/chart/primitives.js) thay vì series riêng: tạo
   `new MSL.primitives.Segments(opts)` / `Boxes(opts)` / `Band(opts)` trong hook `chart.init` rồi
   `mc.attachPrimitive(p)`; mỗi lần vẽ đưa mảng đối tượng thuần qua `setItems` / `setBars`. Toạ độ ngang là chỉ số
   logic: đổi chỉ số nến bằng `mc.logicalOf(index)` (vượt nến cuối = vùng tương lai). Đối tượng có `id` thì rê chuột
   trúng sẽ gọi hook `chart.tooltipObject`. Nhãn có `priority` (nhỏ đặt trước), `strict`, `fallback` (ký hiệu gọn khi
   hết chỗ); `autoscale: 'near'` để mức ở xa không giãn trục giá. Chú thích đủ ở đầu file; mẫu: `ict_structure.js` +
   phần dựng hình thuần `ict_structure_view.js` (kiểm bằng node — `tests/frontend/test_ict_display.py`).
   `primitives.js` đã nạp ở cả bốn trang, trước `algos/registry.js`.

Danh sách hook đầy đủ ở đầu [`frontend/js/algos/registry.js`](../../frontend/js/algos/registry.js);
cách lõi chart gọi hook vẽ ở đầu [`frontend/js/chart/market-chart.js`](../../frontend/js/chart/market-chart.js).
Hay dùng:

| Hook | Dùng cho | Mẫu |
|---|---|---|
| `chart.init` / `clear` / `draw` | series riêng (đường mức, dải, histogram) — tạo một lần, vẽ lại mỗi `setEvents` | `dc_atr.js`, `ict_structure.js` |
| `chart.ownsEvent` / `marker` / `finish` | marker theo sự kiện đã xác nhận tại con trỏ | `swing.js`, `baseline.js` |
| `chart.tooltipBar` / `tooltipEvent` | dòng thêm trong tooltip (đọc `details`, timeline) | `dc_atr.js` |
| `chart.tooltipObject` | tooltip riêng khi chuột trúng đối tượng `id` của primitive (MarketChart tự gọi `hitTest` đúng vị trí chuột — `hoveredObjectId` của LWC 4.2.3 trễ một nhịp); trả `''` nếu không phải của mình | `ict_structure.js` |
| `chart.onCrosshair` | mỗi lần crosshair đổi, `bar` = nến dưới chuột (null khi rời chart) — vd dòng trạng thái theo nến đang rê | `ict_structure.js` |
| `mc.attachPrimitive`, `mc.logicalOf` | gắn primitive (`MSL.primitives`) lên series nến + đăng ký hitTest; đổi chỉ số nến → chỉ số logic | `ict_structure.js` |
| `notes`, `runWarning`, `statsHtml`, `afterStats` | ghi chú, cảnh báo sau khi chạy, khối chỉ số ở tab Thống kê | `dc_atr.js`, `ict_structure.js` (`afterStats`: chưa plugin nào dùng) |
| `pendingHtml`, `explain` | trạng thái nội bộ khi replay, khung «Thuật toán đang làm gì» | `dc_atr.js` |
| `eventDetail`, `selectEventOnChart` | panel chi tiết sự kiện được chọn | `dc_atr.js` |
| `labelTypes`, `labelPrice` | loại nhãn tay ở trang Gán nhãn (id trùng `label_types` của lớp Python) | `ict_structure.js` |
| `layerHints`, `panels`, `ownLayersOnly` | câu gợi ý dưới khung lớp, khung lớp riêng, ẩn khung lớp chung | `swing.js`, `dc_atr.js`, `ict_structure.js` |
| `syncLegend` | chú giải / dòng trạng thái riêng trên chart (ẩn khi không phải thuật toán của mình / chưa có kết quả) | `dc_atr.js`, `ict_structure.js` |
| `forwardRows` | trang Live MT5: hàng điểm forward của một tầm (`core/eval/forward.py`) | `ict_structure.js` |
| `pane` | khung phụ ngay dưới chart chính ở trang Thử nghiệm và trang Live MT5 ([`chart/pane-host.js`](../../frontend/js/chart/pane-host.js), [`chart/sub-pane.js`](../../frontend/js/chart/sub-pane.js) — cùng chuỗi nến, cuộn / zoom / crosshair đồng bộ): `{layer, title, has, init, points, legend}` — `init` tạo series (`addHistogram`; thang dọc qua `autoscaleInfoProvider` của LWC), `points` trả `{key series: một phần tử mỗi nến của ctx.bars từ ctx.from}` (replay tiến một nến: chỉ nến mới — trang tự thêm vào cuối), không vượt `ctx.cursor`; `legend` trả html dòng chú giải; hợp đồng đủ ở đầu `registry.js` | `ict_structure.js` (khung trạng thái, lớp `ict_nd_pane`) |

Quy tắc: plugin chỉ **đọc** `details`, `timeline_point`, `pending_state` mà lõi đã tính — không
tính lại logic thuật toán ở frontend; replay chỉ vẽ tới con trỏ (`ctx.cursor`). `ctx` của `begin` / `draw` có sẵn
`events`, `timeline` và `pendingState` (`pending_state` lõi tại con trỏ — nến cuối của lần chạy hoặc con trỏ replay). Mục tiêu chấm
khai ở `eval_targets` (Python) tự hiện trong ô «Mục tiêu» của trang Đánh giá.

### Hợp đồng bắt buộc

| Yêu cầu | Lý do |
|---|---|
| `on_bar` chỉ dùng nến đã nạp | Không rò rỉ dữ liệu tương lai |
| Không sửa/thu hồi sự kiện đã trả về | Lịch sử quyết định bất biến |
| `confirmed_at == bar.close_time` của nến đang xử lý | Phân biệt thời điểm sự kiện và thời điểm biết |
| Tất định với cùng chuỗi nến | Tái lập được; nếu có ngẫu nhiên phải lưu seed |
| `reset()` xoá sạch trạng thái | Replay lùi dựa vào việc dựng lại từ đầu |

### Tuỳ chọn

* `pending_state()` — trạng thái tạm thời để hiển thị (không phải sự kiện).
* `timeline_point(bar)` — giá trị vẽ overlay theo từng nến (mức swing, xác suất
  regime…). Engine gọi ngay sau `on_bar` nên chuỗi này cũng tôn trọng nhân quả.
* `check_dataset(timeframe, params)` (classmethod) — từ chối dataset không hợp
  (vd sai timeframe) bằng `ValueError`; service đổi thành lỗi 400. Mặc định nhận mọi dataset.
* `run_stats(events)` — thống kê riêng của thuật toán, chỉ đọc log; engine lưu vào
  `stats.chi_so_thuat_toan`. Mặc định không có.
* `manifest_info(params)` (classmethod) — thông tin thêm cho manifest (nguồn,
  giấy phép, alignment). Ví dụ: `ict_structure`, `dc_atr_structure`.
* `ParamSpec(..., show_if=("ten_tham_so", "gia_tri"))` — form chỉ hiện tham số khi
  tham số kia bằng giá trị đó (vd `reversal_pct` chỉ khi `threshold_mode=percent`).
  Chỉ ảnh hưởng hiển thị; validate vẫn chạy mọi tham số. Ví dụ: `dc_atr_structure`.
* `ParamSpec(..., advanced=True)` — tham số ít khi cần chỉnh (cấu hình dữ liệu, chỉ để đối chiếu, gần như không đổi kết
  quả) nằm trong mục «Tham số nâng cao» gập sẵn của form. `choice_labels_vi=(("ma", "chữ hiện"), …)` — chữ tiếng Việt
  cho từng lựa chọn của tham số `choice`; giá trị lưu và gửi đi vẫn là mã. `help_vi` nên là **một câu lời thường** nói
  «tăng / giảm thì sao» (form chỉ hiện nó khi đang ở ô đó và trong tooltip); định nghĩa đầy đủ để ở đặc tả. Mẫu:
  `ict_structure`.
* Replay có `POST /api/replay/{sid}/next-event` (tiến từng nến tới sự kiện kế
  tiếp) — dùng được cho mọi thuật toán, không cần code riêng. Mọi thao tác replay
  nhận `since` (tuỳ chọn): server chỉ trả sự kiện/timeline sau `delta_since` —
  thuật toán mới không cần làm gì, miễn giữ hợp đồng nhân quả.
* `label_types` (thuộc tính lớp) — loại nhãn tham chiếu mới thuật toán mang vào kho nhãn
  (ngoài swing/BOS/CHoCH dựng sẵn). Danh sách gộp: `core.labels.label_types()`.
* `eval_targets` (thuộc tính lớp) — mục tiêu chấm riêng (`core.eval.targets.EvalTarget`:
  loại nhãn, phía đỉnh/đáy, ánh xạ). Trang Đánh giá đọc bảng gộp `all_targets()`.
  Mẫu: `ict_structure/eval_targets.py`.
* `evaluation_metrics(events, bars, **options)` (classmethod) — chỉ số đánh giá cần nến
  SAU lúc biết (vd MFE/MAE), chỉ để đánh giá; API `GET /api/runs/{id}/metrics?…`.
  Mặc định `None` (không có). Hiện chưa thuật toán nào dùng; mẫu cũ `c2_cisd_research` đã gỡ (xem lịch sử git).
* Loại sự kiện / mã lý do mới: khai trong `core/vocab/<họ>.py` (lớp loại, lớp lý do,
  câu giải thích tiếng Việt) rồi thêm họ vào `core/vocab/__init__.py::FAMILIES`;
  `core/types.py` tự ghép. Thêm lớp badge `.b-<TYPE>` trong `frontend/css/app.css`
  nếu muốn có màu riêng.

## 3. Ghi chú cho HMM và BOCD

**HMM:** đã triển khai `hmm_online` v1.0.0 — xem [`thuat_toan_hmm_online.md`](../algorithms/thuat_toan_hmm_online.md).
Fit trên prefix `train_bars` bằng hmmlearn; `on_bar` chỉ bước forward. State
mặc định `chua_gan_nghia` (không tự gắn Trend/Range).

**BOCD (Adams–MacKay)** chưa triển khai.

Hai ứng viên trong tài liệu nhóm khớp với interface này, nhưng cần lưu ý:

**HMM (hmmlearn).** Phải tách rõ **fit** và **lọc online**:

* `fit` chỉ được chạy trên phần dữ liệu train, ở ngoài vòng `on_bar`. Thuật toán
  nhận model đã fit qua tham số khởi tạo hoặc một đường dẫn file.
* Trong `on_bar` chỉ được dùng bước **filtering** (forward), tuyệt đối không dùng
  kết quả **smoothing** (Viterbi/forward-backward trên toàn chuỗi) vì nó dùng
  dữ liệu tương lai.
* Nếu có lịch refit, phải ghi rõ thời điểm model mới được phép sử dụng và không
  cho model nhìn thấy dữ liệu sau mốc đó.
* State của HMM không tự mang nghĩa Trend/Range — cần một bảng ánh xạ công bố trước.

**BOCD (Adams–MacKay).** Bản chất là online nên hợp với `on_bar`. Lưu ý:

* Chọn likelihood và hazard rate là lựa chọn mô hình — phải lưu vào tham số.
* Điểm đổi chế độ không tự cho hướng tăng/giảm; đừng biến nó thành tín hiệu lệnh.

**`ruptures`** hướng tới offline. Nếu dùng, chỉ để phân tích hồi cứu; **không**
lấy breakpoint tính trên toàn chuỗi làm tín hiệu online tại thời điểm quá khứ.

## 4. MT5 / MQL5

Đã có `core/data/mt5_source.py` (gói tuỳ chọn) và script
[`mql5/SwingPivotExport.mq5`](../../mql5/SwingPivotExport.mq5). Xem
[`mt5_va_tong_hop_nen.md`](mt5_va_tong_hop_nen.md) và
[`doi_chieu_python_mql5.md`](doi_chieu_python_mql5.md).

Bốn đường tích hợp (tài liệu nhóm):

| Phương án | Cách làm trong dự án này | Giới hạn |
|---|---|---|
| **Lấy dữ liệu qua Python** | `core/data/mt5_source.py` + `POST /api/datasets/import-mt5`. Loại nến đang hình thành. | Gói tuỳ chọn; không thay Strategy Tester. |
| **Chuyển logic sang MQL5** | Script `mql5/SwingPivotExport.mq5` + tab Đối chiếu MQL5 / `POST /api/compare-mql5`. | Cần cùng dataset_checksum. |
| **Xuất mô hình ONNX** | Chỉ áp dụng khi có ML; vòng lặp pivot bằng Python không xuất ONNX được. | ONNX chuyển phần mô hình, không chuyển pandas hay vòng lặp. |
| **Bridge Python–EA** | Ghi kết quả ra file/HTTP cho EA đọc. | `WebRequest` không chạy trong Strategy Tester. Từng hàng kết quả phải được sinh chỉ từ thông tin khả dụng tại thời điểm đó. |

**Đường đề xuất cho nhóm:** giữ Python làm bản tham chiếu; chuyển thuật toán
cấu trúc dùng luật sang MQL5 để quan sát trong MT5; đối chiếu hai bên bằng
CSV sự kiện trên **cùng một snapshot dữ liệu**. Chênh lệch giữa hai feed khác
nhau chưa đủ để kết luận có lỗi code.

### Chuẩn bị sẵn cho việc đối chiếu

Mỗi lần chạy đã lưu đủ thông tin để một bản triển khai khác tái lập:

* `dataset_checksum` — checksum nội dung nến đã chuẩn hoá (không phụ thuộc định
  dạng file), nên bản MQL5 nạp cùng dữ liệu là so được.
* `algorithm_version` + `params` — quy tắc và tham số chính xác.
* `range_start` / `range_end` và `warmup_bars`.
* CSV sự kiện có `event_time`, `confirmed_at`, `confirmation_lag_bars` — đủ để
  kiểm tra cả vị trí lẫn thời điểm xác nhận, không chỉ vị trí.

Gọi `GET /api/runs/{run_id}/manifest` để lấy toàn bộ hồ sơ này dưới dạng JSON.
