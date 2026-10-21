# Plan tích hợp CantoLab C2 Sweep + CISD vào Market Structure Lab

> **Đã gỡ khỏi lab ngày 21/10/2026.** Thuật toán `c2_cisd_research` không còn trong code; tài liệu giữ làm hồ sơ. Code còn trong lịch sử git (commit cuối có nó: `dd9984f`, nhánh `ict-structure/giai-doan-2`).

Ngày lập: 25/09/2026. Trạng thái: **đã triển khai MVP `c2_cisd_research` v0.1.0 (25/09/2026)** — đặc tả và kết quả ở [`thuat_toan_c2_cisd.md`](../algorithms/thuat_toan_c2_cisd.md). **Chưa xác minh parity với Pine** (chưa có trace TradingView, mục 7). Chưa commit/push.

## 1. Chỉ dẫn thực hiện cho Claude

Triển khai thuật toán nghiên cứu `c2_cisd_research` vào ứng dụng hiện có, đầy đủ từ core, API/lưu trữ tới chart, replay và đánh giá. Giữ `swing_pivot` M15 hiện tại làm baseline. Không thay đổi công thức, version hoặc default của các thuật toán cũ để nhường chỗ cho thuật toán mới.

Đường dẫn người dùng nêu: `D:\Finance\_System\market-structure-lab`. Tại máy lập plan, repo thực tế là `D:\Finance_System\market-structure-lab`, còn đường dẫn người dùng nêu chưa tồn tại. Xác định repo bằng cấu trúc file và git remote trước khi sửa; không tạo repo thứ hai chỉ vì khác đường dẫn. Các đường dẫn dưới đây tương đối với repo.

Đọc AGENTS.md áp dụng nếu có, kiểm tra git status và bảo toàn mọi thay đổi đang có. Không reset, clean, ghi đè công việc khác hoặc tự push. Thực hiện lần lượt các mốc bên dưới; không dừng ở việc thêm một mục dropdown hoặc tạo detector chưa nối vào ứng dụng.

Nguồn bắt buộc:

- [Báo cáo nghiên cứu nguồn](../research/nghien_cuu_cantolab_fractal.md).
- [Hợp đồng thêm thuật toán](../guides/them_thuat_toan.md).
- Repo nguồn: https://github.com/cantolab/open-source-fractal
- Commit tham chiếu: `1bb53262deba9456f2b1a85d15c6ac5a5e880cf7`.
- Pine: https://github.com/cantolab/open-source-fractal/blob/1bb53262deba9456f2b1a85d15c6ac5a5e880cf7/openSourceFractal.pine
- Clone tham khảo trên máy lập plan: `D:\Finance_System\research-references\open-source-fractal`.

Nếu clone không tồn tại, lấy đúng commit tham chiếu. Giữ MIT license và copyright notice khi chuyển thể mã; ghi attribution trong tài liệu và nơi phù hợp với cấu trúc dự án.

## 2. Mục tiêu và phạm vi

Cho phép chọn thuật toán mới trên web, chạy XAUUSD M15 kết hợp H4, thấy C2 sweep, mức CISD, xác nhận và vòng đời setup tại đúng thời điểm hệ thống biết. Lưu lịch sử để kiểm tra lại, không chỉ vẽ chart đẹp.

Đây là bản chuyển thể **xử lý tuần tự trên nến đã đóng**, lấy cảm hứng/logic từ commit nguồn. Không quảng bá là port tương đương Pine realtime hoặc đã chứng minh nâng chất lượng swing. CISD không đồng nghĩa MSS/BOS; T-Spot không phải FVG.

Phạm vi nghiệm thu đầu tiên:

- C2 hai hướng, chọn mức CISD, early confirmation, C3/C4, invalidation, expiry, superseded.
- HTF aggregator tuần tự, sự kiện bất biến, replay, lưu/xuất kết quả và UI tối thiểu đầy đủ.
- Metric vòng đời setup và hạ tầng chấm nhãn C2/CISD đúng loại.
- Không thêm ML/LLM, đặt lệnh, tối ưu tham số tự động hay đổi bộ pivot.
- T-Spot, projections và chiến lược kết hợp swing là giai đoạn sau. Không để chúng trì hoãn bản core có kiểm chứng.

## 3. Đặc tả phải chốt trước khi viết detector

Tạo `docs/algorithms/thuat_toan_c2_cisd.md`, ghi các quyết định dưới đây và bảng đối chiếu nhánh Python ↔ Pine. Các điểm chưa rõ phải đọc lại code nguồn, không suy diễn từ tên ICT.

### 3.1. C2 sweep

C1 là nến HTF hoàn tất ngay trước C2:

```text
bullish = low(C2) < low(C1) and close(C2) > low(C1)
bearish = high(C2) > high(C1) and close(C2) < high(C1)
```

- So sánh strict, không thêm tolerance mặc định.
- Không yêu cầu màu C2 hoặc close nằm hoàn toàn trong range C1.
- Outside bar có thể đạt cả hai: giữ hai setup độc lập, gắn cờ ambiguity; không chọn hướng bằng dữ liệu về sau.
- Mặc định bias Neutral. Nếu cho chọn Bullish/Bearish, lưu trong params/manifest; không gọi đó là bias suy luận tự động.

### 3.2. HTF và thời điểm biết

- MVP hỗ trợ cặp M15–H4; từ chối cấu hình chưa hỗ trợ bằng lỗi rõ ràng.
- Tái sử dụng quy ước Bar/timezone hiện có. Không đọc OHLC cuối H4 cho các nến M15 trước khi H4 đó hoàn tất.
- Lưu alignment trong manifest. Mặc định dùng quy ước UTC epoch hiện có, hiển thị rõ; không tuyên bố khớp broker/TradingView khi chưa đối chiếu.
- Chỉ chấp nhận bucket đủ các nến M15 kỳ vọng, liên tiếp, đúng timestamp. Không tự bù nến thiếu. Bucket đầu/cuối không đủ và gap được báo chất lượng dữ liệu.
- Không nối C1/C2 qua bucket bị thiếu/không hợp lệ. Sau gap phải warm-up lại ngữ cảnh cần thiết; chốt cách vô hiệu ngữ cảnh đang hoạt động và ghi lý do data gap, không chấm thành giá phá setup.
- Khi M15 cuối cùng đóng đúng biên H4 và bucket đủ, có thể hoàn tất C2 ngay lúc đó. Đây là quy ước của bản closed-bar, phải ghi khác biệt với trigger Pine ở bar đầu kỳ sau.
- Định nghĩa rõ C3/C4 theo khoảng HTF thực tế; không lệch một kỳ do thời điểm phát sự kiện.

### 3.3. Chọn mức và xác nhận CISD

- Port đủ nhánh trực tiếp, tìm ngược 2–10 nến, doji và fallback trong Pine. Không thay bằng quy tắc phá swing hoặc open của một nến tùy chọn.
- Đọc lại thứ tự câu lệnh, phạm vi vòng lặp, cập nhật extreme và các biến mức tồn tại qua kỳ. Báo cáo nghiên cứu chỉ là bản đồ tới source, không thay source.
- Mỗi mức phải truy được nến nguồn, giá mức, hướng, lúc xác lập và revision. Thay mức bằng sự kiện mới; không sửa mức trong sự kiện đã phát.
- Mặc định giữ cách chọn mức/persistence của nguồn khi đã xác định rõ; không tự thêm TTL hoặc chặn scan tại biên H4 rồi gọi là faithful. Nếu cần sửa, nêu quyết định trong spec và manifest/version.
- Pine kiểm tra `close[1]`: bản đầu giữ độ trễ phát hiện này để dễ kiểm toán; lưu riêng nến cung cấp close vượt mức và nến hiện tại nơi detector phát hiện. `confirmed_at` luôn bằng close_time của nến đang xử lý theo hợp đồng lab. Không tự dịch nhãn về quá khứ để trông sớm hơn.
- Early CISD trong C2 là bằng chứng sớm của candidate, chưa phải C2 setup đã xác nhận. Chỉ liên kết với setup sau khi C2 đóng và thỏa sweep. Candidate không thành C2 vẫn được phân biệt rõ, không tính vào số setup C2 xác nhận.
- So sánh reclaim CISD strict theo hướng nguồn. Khoá rõ mức nào có hiệu lực trước khi kiểm tra close trước đó; phải có fixture chống sử dụng mức mới như thể đã biết ở nến cũ.

### 3.4. Vòng đời và thứ tự xử lý

- Mô hình rõ các trạng thái candidate, C3, C4 và terminal; state hiển thị được suy ra từ log.
- Nến đồng thời breach extreme và đủ close xác nhận: ưu tiên invalidation trước confirmation theo thứ tự nguồn, không đoán đường đi tick từ OHLC.
- Setup mới cùng hướng thay setup đang theo dõi: ghi superseded; giữ log setup cũ. Hai hướng quản lý riêng.
- Phân biệt invalidated, expired, superseded, data-gap termination. Mỗi setup chỉ có một kết thúc terminal theo thứ tự ưu tiên được ghi trong spec.
- Không xóa CISD đã xác nhận khi C4 về sau thất bại. Append invalidation; không sửa lịch sử thành chưa từng xác nhận.
- Chốt timeline ví dụ qua C2→C3→C4→expiry, early confirmation, và cùng nến đổi kỳ có setup mới; viết test từ timeline này.

## 4. Hợp đồng dữ liệu và tương thích

Khảo sát `core/types.py`, engine, serializer, storage và export trước khi thêm trường. Dùng metadata/extension hiện có nếu phù hợp; nếu cần migration phải tương thích dữ liệu cũ.

Mỗi sự kiện cần truy được:

- event_id tất định, setup_id/candidate_id, direction, loại sự kiện, reason code.
- C1/C2, nến cực trị, nến nguồn CISD và nến bằng chứng xác nhận.
- event_time (nến/điểm giá được mô tả), observed_at (lúc detector phát hiện), confirmed_at theo contract lab. Giải thích riêng ý nghĩa các trường, không gộp thời gian nến với thời gian biết.
- Giá mức, extreme, phase, revision và quan hệ reference tới sự kiện trước.
- Thuật toán/version/params, timeframe, HTF alignment và dataset checksum ở event hoặc manifest liên kết.

Loại sự kiện dự kiến: `C2_CONFIRMED`, `CISD_LEVEL_SET`, `EARLY_CISD_CONFIRMED`, `CISD_CONFIRMED`, `SETUP_INVALIDATED`, `SETUP_EXPIRED`, `SETUP_SUPERSEDED`; bổ sung data-quality/termination nếu schema cần. Hướng là trường riêng hoặc type đối xứng theo convention hiện có. Không ép chúng thành HH/HL/MSS để tận dụng UI.

Không phát lặp event mỗi nến. `reset()` xóa sạch state. Thuật toán core không phụ thuộc FastAPI, DB, MT5, frontend hoặc dịch vụ ngoài.

## 5. Các mốc triển khai

### Mốc A — khảo sát và khóa spec

- [x] Đọc source pinned, hợp đồng engine và các thay đổi hiện có.
- [x] Viết spec, sơ đồ state machine, timeline tính tay và bảng khác biệt với Pine.
- [x] Chốt policies timing, gap, mức stale, doji, dual setup và thứ tự xử lý.

### Mốc B — core và dữ liệu

- [x] Thêm aggregator tuần tự, ưu tiên module mới thay vì đổi hành vi resample cũ.
- [x] Thêm `core/algorithms/c2_cisd_research.py`, tên `c2_cisd_research`, version đầu `0.1.0`.
- [x] Triển khai C2, CISD và log vòng đời theo spec; đăng ký trong `core/registry.py`.
- [x] Bổ sung types/reasons tiếng Việt và metadata cần thiết; giữ output baseline cũ.
- [x] Hoàn thành fixtures và kiểm tra nhân quả trước khi nối chart.

### Mốc C — API, lưu trữ, chart và replay

- [x] Kiểm tra API chạy thuật toán, lưu/load run, manifest và CSV/JSON chứa đủ sự kiện mới.
- [x] Dropdown/form lấy từ registry; có mô tả đây là bản nghiên cứu closed-bar M15–H4.
- [x] Chart có marker C2 hai hướng, đường CISD và khoảng hiệu lực, marker xác nhận/vô hiệu/kết thúc.
- [x] Tooltip hiện setup_id, giá, nguồn tham chiếu, thời điểm nến và thời điểm biết, trạng thái/reason.
- [x] Replay không hiện sự kiện trước confirmed_at. Marker có thể neo tại cực trị cũ chỉ sau lúc biết; không nối đường như thể mức đã có từ trước.
- [x] Toggle lớp C2/CISD/lịch sử chỉ tác động hiển thị. Setup thất bại vẫn xem được trong bảng và export.
- [x] Hiện cảnh báo dữ liệu thiếu, alignment, warm-up, và trạng thái không có setup một cách phân biệt.
- [x] Kiểm tra trang hiện có trước khi sửa; dùng style hiện tại, không dựng một ứng dụng khác.

### Mốc D — metric và đối chứng

- [x] Thêm thống kê số C2 theo hướng, tỷ lệ có CISD, delay và số setup terminal theo từng lý do.
- [x] Công bố mẫu số và cutoff: setup chưa kết thúc khi hết dataset là censored/đang mở, không tính là thất bại hoặc expiry.
- [x] Early CISD báo riêng; không gộp delay âm với delay sau C2 thành một số trung bình khó hiểu.
- [x] Nếu có nhãn tham chiếu C2/CISD: match một-một, cùng hướng/type, tolerance thời gian/giá cố định; báo precision/recall/F1 riêng từng loại trong khoảng đã gán nhãn. *(Hạ tầng xong: mục tiêu `c2`/`cisd`, phía low = `_UP`, high = `_DOWN`. Chưa có bộ nhãn người gán nên chưa có số.)*
- [x] Nếu chưa có nhãn: hiển thị “chưa có nhãn tham chiếu”; không dựng F1 từ output của chính thuật toán hoặc nhãn HH/MSS.
- [x] MFE/MAE tùy chọn: horizon cố định tính từ thời điểm biết, dữ liệu tương lai chỉ dùng cho đánh giá; bỏ mẫu thiếu horizon và báo số mẫu. Không gọi tỷ lệ CISD là win rate.
- [x] Giữ pivot baseline cố định. Chuẩn bị chạy đối chứng C2-only và C2+CISD trên cùng snapshot; kết hợp swing là thí nghiệm riêng sau MVP, không tự lọc pivot mặc định. *(Đối chứng C2-only vs C2+CISD qua MFE/MAE; kết hợp swing chưa làm — đúng phạm vi.)*

## 6. Kiểm thử bắt buộc và tiêu chí đạt

### Logic

- Sweep tăng/giảm; bằng mức không đạt; xuyên nhưng không reclaim; outside bar hai phía.
- Mỗi nhánh CISD trực tiếp/tìm ngược/fallback/doji, ranh giới lookback, mức cũ qua kỳ và cập nhật mức mới.
- Early trong C2; xác nhận C3/C4; breach trước xác nhận; xác nhận rồi C4 invalid; superseded và expiry.
- Thiếu warm-up, bucket đầu/cuối thiếu, gap giữa kỳ và gián đoạn phiên, biên UTC H4.
- Cùng nến đổi kỳ và xác nhận/invalid/setup mới; mỗi trường hợp có output tính tay độc lập.

### Nhân quả và tái lập

- Chạy prefix tới T có cùng event log đã biết tại T như chạy toàn chuỗi rồi lọc confirmed_at ≤ T.
- Sửa/thêm suffix sau T không làm thay đổi log trước T, kể cả giá/ID/reference.
- Chạy batch, feed tuần tự và reset rồi replay cho kết quả giống nhau.
- Giữ bản sao event đã trả về rồi feed thêm để phát hiện mutation object sau phát.
- Thay display history/preview count không đổi output core.
- Không chỉ dựa vào `core/eval/causality.py`: phải thực sự chạy lại detector trên prefix/suffix thay đổi.

### Tích hợp và hồi quy

- API → lưu run → load → export bảo toàn loại sự kiện, ID, thời gian và metadata.
- Các run/nhãn cũ vẫn mở được; kiểm tra tests baseline và ảnh hưởng của schema/migration.
- Smoke test trình duyệt: chọn detector, chạy, replay trước/sau xác nhận, toggle, tooltip, export, mở lại run.
- Chạy bộ test phù hợp theo hướng dẫn repo; ghi lệnh, kết quả và các lỗi có sẵn được xác minh, không tự coi mọi lỗi là ngoài phạm vi.

Không có ngưỡng precision/recall mặc định để tuyên bố thuật toán tốt hơn. MVP đạt khi đúng spec, không leak/repaint log, có thể quan sát và tái lập; hiệu quả nhận diện là kết quả thực nghiệm tiếp theo.

## 7. Đối chiếu Pine và báo cáo bàn giao

Nếu có khả năng chạy TradingView, dùng cùng OHLC, alignment và cấu hình, lấy trace tại lúc sự kiện phát; không chỉ so ảnh chart cuối kỳ. Phân loại sai khác theo feed, thời gian phát, intrabar, logic và sửa đổi có chủ đích.

Nếu chưa có trace, vẫn hoàn thiện bản research với fixtures/tài liệu, ghi rõ **chưa xác minh parity với Pine**.

> Trạng thái 25/09/2026: **chưa có trace TradingView** — chưa đối chiếu. Bảng khác biệt có chủ đích: [`thuat_toan_c2_cisd.md`](../algorithms/thuat_toan_c2_cisd.md) mục 9. Không bịa kết quả chạy TradingView hoặc dữ liệu thật. Dữ liệu synthetic chỉ chứng minh hành vi trên fixture, không chứng minh giá trị thị trường.

Bàn giao cuối cùng gồm:

1. Detector tích hợp vào app hiện có, license/attribution và tài liệu sử dụng.
2. Spec cuối cùng và bảng sai khác có chủ đích so với commit nguồn.
3. Fixtures/tests và kết quả chạy; một run minh họa có nguồn dữ liệu rõ ràng.
4. Hướng dẫn thao tác web/replay/metric, giới hạn còn lại và việc chưa kiểm chứng.
5. Danh sách file thay đổi; cập nhật checklist plan đúng thực tế. Không tự commit/push nếu chưa được yêu cầu.

## 8. Prompt bàn giao ngắn

> Đọc `docs/plans/plan_tich_hop_c2_cisd.md` và `docs/research/nghien_cuu_cantolab_fractal.md`, sau đó triển khai đầy đủ MVP C2 Sweep + CISD theo plan vào repo market-structure-lab hiện có. Xác minh đường dẫn repo, bảo toàn thay đổi đang có, giữ nguyên swing_pivot baseline. Đọc mã Pine tại commit đã pin, khóa spec về timing/state rồi làm core → kiểm thử nhân quả → API/storage → chart/replay → metric. Tiếp tục tới khi có thể chạy end-to-end, cập nhật checklist và báo cáo bằng chứng kiểm thử. Không tuyên bố parity Pine hoặc hiệu quả thị trường khi chưa kiểm chứng; không tự push.
