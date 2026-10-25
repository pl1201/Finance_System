# Plan: chạy thử tiến (forward) chỉ đọc từ MT5 — nến live, nhật ký dự báo, điểm forward

**Trạng thái: đã chốt (25/10/2026)**, đang làm (§9). Người dùng «chốt cả 2»:
(a) nới AGENTS.md từ «không kết nối broker» thành «chỉ đọc dữ liệu nến từ terminal MT5, không gửi lệnh»;
(b) làm song song với gán nhãn tay (hai việc không phụ thuộc nhau).

## 1. Mục tiêu và phạm vi

Đây là cách duy nhất có thêm dữ liệu **ngoài mẫu thật sự** mà không mở đoạn test đang khoá: dự báo của lớp nhận diện
(`ict_structure`, [`thuat_toan_nhan_dien.md`](../algorithms/thuat_toan_nhan_dien.md)) được ghi lại lúc nến đóng, rồi chấm
khi biết kết cục — trên nến chưa ai thấy lúc thiết kế.

| Làm | Không làm |
|---|---|
| Đọc nến **đã đóng** từ terminal MT5 đang mở trên máy | Gửi, sửa, huỷ lệnh; đọc vị thế, lệnh, lịch sử giao dịch, tài khoản |
| Chạy thuật toán tăng dần từng nến (như replay) | Tính P&L, win rate, «tín hiệu» |
| Ghi dự báo **chỉ ghi thêm** (không sửa, không xoá) | Lưu mật khẩu / tài khoản (đăng nhập nằm ở terminal) |
| Chấm forward so với B0, hiện trên giao diện | Trộn nến live vào dataset nghiên cứu |

Dự báo được chấm: khoảng giá 80% / 50% (1h, 4h), xác suất chạm mức, xác suất còn giữ trạng thái, xác suất phá biên range
— đúng bốn loại mà đặc tả gọi là **dự báo** (AGENTS §2.4). Trạng thái vẫn là mô tả.

## 2. Rào chắn

1. **Danh sách hàm MT5 được phép** (`core/data/mt5_source.py`): `initialize`, `shutdown`, `last_error`, `version`,
   `terminal_info`, `symbol_select`, `symbol_info_tick`, `copy_rates_from_pos`, `copy_rates_range`, hằng `TIMEFRAME_*`. Lab
   chỉ gọi MT5 qua một lớp bọc; gọi tên khác → lỗi ngay. Test: lớp bọc từ chối `order_send`, `order_check`, `positions_get`,
   `account_info`…; không file nào ngoài lớp bọc import `MetaTrader5`; mã nguồn lab không chứa `order_send`.
2. Không nhận / lưu mật khẩu: `initialize()` không truyền `login` / `password` / `server` — terminal phải đăng nhập sẵn.
3. Kho live riêng `data/live.sqlite` (đặt lại bằng `MSL_LIVE_DB_PATH`; mặc định theo `MSL_DATA_DIR`), không đụng
   `lab.sqlite`. Bảng nến và bảng dự báo có trigger chặn `UPDATE` / `DELETE`.
4. Dòng chân trang «không kết nối broker, không gửi lệnh» giữ nguyên; chế độ Live ghi rõ «chỉ đọc nến MT5».

## 3. Giờ của nến MT5

`copy_rates_*` trả `time` là **giờ server của broker** viết như epoch, không phải UTC (broker phổ biến: GMT+2 mùa đông /
GMT+3 mùa hè theo lịch đổi giờ Mỹ, để nến ngày mở lúc 17:00 New York). Theo AGENTS §2.2, lab không đoán: người dùng khai
báo khi tạo luồng live:

| Khai báo | Quy đổi |
|---|---|
| `UTC`, `UTC+2`, `UTC-05:00` … | offset cố định (như nhập CSV) |
| `ny+7` | giờ server = giờ New York + 7 (đổi giờ theo Mỹ) → UTC = giờ đó − 7h, quy theo `America/New_York` |

Để người dùng kiểm khai báo, lab hiện **gợi ý** (không tự áp): giờ của tick cuối (`symbol_info_tick`) trừ đồng hồ máy,
làm tròn 30 phút — chỉ có nghĩa khi thị trường đang mở.

> **Phát hiện kèm theo:** hộp «Nhập từ MT5…» hiện ghi «MT5 dùng epoch UTC» và chỉ gắn nhãn múi giờ, không quy đổi. Nếu
> broker dùng giờ server ≠ UTC thì dataset nhập lệch giờ. Chưa sửa trong plan này (chưa có dataset MT5 nào trong DB);
> ghi ở §10 để người dùng quyết.

## 4. Kiến trúc

```text
terminal MT5 ──(lớp bọc chỉ đọc)──► Mt5Reader.closed_rates() ──► LiveFeed (một luồng / mã / khung)
                                                                 │  nến mới (đã đóng, đã quy UTC, đã kiểm)
                                                                 ▼
                                live.sqlite: live_bar (chỉ ghi thêm) ──► ReplaySession (core/engine, nến nối dần)
                                                                 │  pending_state + timeline của nến mới
                                                                 ▼
                                live.sqlite: live_forecast (chỉ ghi thêm, bản ghi dự báo + giờ ghi)
                                                                 │
                         core/eval/forward.py: chấm bản ghi khi đủ h nến sau ──► /api/live/{id}/forward ──► giao diện
```

* **Tạo luồng** (`POST /api/live`): mã lab (vd XAUUSD — chọn lịch phiên), tên mã ở broker (vd `XAUUSDm`), khung (mặc định
  M15), khai báo giờ server, số nến lịch sử (mặc định 20 000 ≈ 10 tháng M15 — đủ cho mẫu 600 / giờ NY của khoảng giá), tham
  số thuật toán (mặc định của `ict_structure`). Lấy lịch sử → ghi `live_bar` → chạy thuật toán hết lịch sử.
  `forward_tu` = giờ đóng của nến lịch sử cuối: chỉ nến **sau** mốc này có bản ghi dự báo.
* **Mỗi lần hỏi** (mặc định 10 giây, một luồng nền cho mọi luồng live): lấy vài nến gần nhất, bỏ nến đang hình thành, quy
  UTC. Nến trùng giờ nến đã lưu mà OHLC khác → ghi `live_revision` (broker sửa lịch sử), **không** sửa nến đã lưu. Nến mới
  phải: OHLC hợp lệ, số hữu hạn, giờ tăng ngặt, đúng bước khung — sai thì ghi lỗi dữ liệu, dừng nạp tới khi người dùng xem
  (không gộp thành «không có dữ liệu»). Nến hợp lệ → nạp vào thuật toán → ghi bản ghi dự báo.
* **Khởi động lại backend**: luồng đang chạy được dựng lại bằng cách nạp lại toàn bộ nến đã lưu (tất định). Bản ghi dựng lại
  phải **trùng** bản ghi đã lưu — khác là lỗi nghiêm trọng (dừng luồng, báo). Phiên bản thuật toán trong code khác phiên
  bản của luồng → luồng «hết hiệu lực»: vẫn xem được nến và điểm, không ghi dự báo mới; muốn tiếp thì tạo luồng mới.
* Mất kết nối / terminal đóng: ghi lỗi, thử lại với giãn cách tăng dần (tối đa 5 phút); nến bị lỡ được lấy bù khi nối lại
  (bản ghi của chúng là «ghi bù», §5).

## 5. Nhật ký dự báo và chấm forward

**Bản ghi của nến t** (JSON, đọc ở `pending_state.nhan_dien` + timeline của chính nến t): close, ATR, trạng thái; mỗi tầm
1h / 4h: khoảng (lo/hi 80, 50; qu/qd 80 theo ATR; **B0**), mức (loại, phía, giá, p, **p0**), phá biên (lo, hi, p, **p0**),
còn giữ (p, **p0**). Kèm `ghi_luc` (đồng hồ máy), phiên bản thuật toán, sha256 tham số.

**Kịp thời**: bản ghi có `ghi_luc` ≤ giờ đóng của nến t + một bước khung (ghi trước khi nến kế tiếp đóng — trước khi biết
bất kỳ phần kết cục nào). Bản ghi «ghi bù» (lab tắt rồi bật lại) vẫn nhân quả nhưng tách riêng, không vào điểm chính.

**Kết cục** (đúng §6 của đặc tả — đọc từ `live_bar`, không từ thuật toán): cửa sổ = h nến kế tiếp theo chỉ số (s, s+h];
cửa sổ có khoảng trống dài (hai nến liền nhau cách > 180 phút) → không chấm.

| Dự báo | Kết cục |
|---|---|
| Khoảng 80% / 50% | max high (s, s+h] ≤ cận trên **và** min low ≥ cận dưới; pinball hai biên ở mức `nd_muc_80` so với B0 |
| Chạm mức | high ≥ mức (phía trên) / low ≤ mức (phía dưới) trong cửa sổ; Brier so với p0 |
| Phá biên range | có close trong cửa sổ > biên trên hoặc < biên dưới; Brier so với p0 |
| Còn giữ | trạng thái ở mọi nến (s, s+h] (đọc ở bản ghi của các nến đó) bằng trạng thái ở s; có nến «chưa đủ nến» → không chấm; Brier so với p0 |

**Kiểm chéo**: chạy thuật toán trên một dataset, lấy bản ghi mọi nến, chấm bằng `core/eval/forward.py` → phải ra **đúng**
số dự báo, số chạm / phủ / phá / giữ và tổng Brier (sai số dấu phẩy động) như điểm thật trong lần chạy (`diem_that`). Đây
là test chứng minh bản ghi đủ thông tin và bộ chấm forward đúng định nghĩa.

Điểm hiện ra (mỗi tầm): số dự báo đã chấm (kịp thời), độ phủ 80% / 50%, skill pinball so với B0, Brier chạm (gộp như
`cham_tong` + từng loại) so với B0, còn giữ, phá biên; số bản ghi ghi bù, số đang chờ kết cục, số lần broker sửa lịch sử.
Như tooltip hiện có: chỉ kết luận khi ≥ 100 dự báo đã chấm.

## 6. Lõi: `ict_structure` 0.9.3 — chỉ thêm vào `pending_state`

`pending_state` hiện bỏ B0 của từng dự báo (`khoang` bỏ `b0`, `muc` không có `p0`, còn giữ không lộ B0). Thêm:
`khoang.<tầm>.b0`, `muc[].p0_<tầm>`, `thoi_gian.pha_bien.p0`, `thoi_gian.con_giu.giu_b0`. Sự kiện, timeline, `run_stats`
không đổi — chứng minh bằng hồi quy run đã lưu + so timeline với code 0.9.2.

## 7. Giao diện (trang Thử nghiệm)

* Nút chế độ thứ ba **«Live (MT5)»** cạnh «Toàn lịch sử» / «Replay từng nến». Chọn luồng có sẵn hoặc «Tạo luồng…» (hộp
  thoại: mã lab, tên mã broker, khung, giờ server + gợi ý lệch giờ, số nến lịch sử).
* Chart = replay ghim ở nến cuối: dùng lại toàn bộ lớp vẽ, khung trạng thái, bảng nhận diện; nến mới tự nối (hỏi backend
  mỗi 5 giây theo `since`). Không có nút tiến / lùi; muốn xem lại từng nến thì dùng Replay trên dataset.
* Thanh Live: trạng thái kết nối (chưa cài gói / terminal chưa mở / đang chạy / lỗi dữ liệu / hết hiệu lực), nến cuối đóng
  lúc …, lần hỏi gần nhất, số nến forward.
* Tab Thống kê trong chế độ Live = **điểm forward** (§5), kèm câu «điểm thật trên nến chưa từng thấy; chưa đủ 100 thì chưa
  kết luận».

## 8. Kiểm thử

* Lõi 0.9.3: hồi quy run đã lưu (`scripts/regression_saved_runs.py`) + timeline giống hệt code 0.9.2 trên dữ liệu dev.
* `core/eval/forward.py`: tính tay (khoảng, chạm, phá, giữ, khoảng trống, kịp thời) + kiểm chéo với `diem_that`.
* MT5: lớp bọc từ chối hàm ngoài danh sách; quy đổi giờ (`UTC+3`, `ny+7` hai mùa); bỏ nến đang hình thành.
* Live (MT5 giả lập trong test): tạo luồng, nến mới → bản ghi; trigger chặn sửa / xoá; sửa lịch sử → `live_revision`;
  nến lỗi → dừng; khởi động lại → dựng lại trùng bản ghi; đổi phiên bản → hết hiệu lực; nhân quả (bản ghi của nến t không
  đổi khi thêm nến sau).
* Trình duyệt thật trên bản sao DB, MT5 **giả lập** (phát lại dataset dev với đồng hồ tua nhanh, ghi rõ MÔ PHỎNG — chỉ ở
  script trong thư mục tạm, không có trong code lab): chế độ Live tự nối nến, tab điểm forward, không lỗi JS.
* Chạy thật với terminal: **cần người dùng** — máy này chưa cài MT5 (không thấy terminal / thư mục MetaQuotes), gói
  `MetaTrader5` chưa cài trong `.venv`.

## 9. Thứ tự làm (mỗi khối: simplify → code-review → chạy thật → commit + push `rieng`)

| Khối | Việc | Trạng thái |
|---|---|---|
| L0 | Plan này + AGENTS.md (nới quy tắc, ghi quyết định) | đang làm |
| L1 | Lõi 0.9.3 (B0 trong pending) + `core/eval/forward.py` + test kiểm chéo | |
| L2 | `Mt5Reader` (lớp bọc, giờ server) + kho live + dịch vụ / route live + test MT5 giả lập | |
| L3 | Giao diện chế độ Live + điểm forward + chạy trình duyệt (MT5 giả lập) | |

## 10. Giới hạn, chưa làm

* Lịch phiên khai báo theo CME / fx_spot; giờ nghỉ của broker có thể lệch vài phút → khoảng trống nhỏ có thể bị gọi «bất
  thường». Chỉ ảnh hưởng hiển thị gap (luật khoảng trống dài > 180 phút không đổi).
* Tick volume của MT5 được lưu nhưng thuật toán hiện chưa dùng volume.
* Chưa xuất luồng live thành dataset nghiên cứu (làm sau nếu cần: snapshot chỉ đọc, có checksum).
* Hộp «Nhập từ MT5…» chưa quy đổi giờ server (§3) — chờ người dùng quyết sửa.
