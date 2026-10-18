# Bối cảnh cho tầng regime: yêu cầu AI Trading Copilot và dự án `regime-aware-ai-trading`

Ngày: 07/10/2026. Tài liệu nền cho [`plan_bias_regime.md`](../plans/plan_bias_regime.md). Chỉ đọc, không chạy mã
nào của repo cũ. Đường dẫn ngoài repo ghi dạng chữ (không phải liên kết) vì các thư mục đó không đi theo repo này:

- `[C]` = `D:\Finance_System\` (tài liệu sản phẩm AI Trading Copilot)
- `[R]` = `D:\Finance_System\regime-aware-ai-trading\` (dự án cũ; `[S]` = `[R]src\algo_trading\`, `[P]` = `[R]production\`)

---

## 1. Yêu cầu sản phẩm: regime phục vụ cái gì

**Ba tầng** (`[C]AI_Trading_Copilot_Moi_Truong_Thu_Nghiem_Cau_Truc_Thi_Truong.md` §2):

| Tầng | Câu hỏi | Đầu ra |
|---|---|---|
| Cấu trúc và đặc trưng giá (lab này) | Giá đang hình thành cấu trúc gì? | Đỉnh/đáy, thứ tự, phá vỡ, độ dốc, biên độ |
| Regime | Bằng chứng cho thấy trạng thái nào? | Trend, Range, Breakout, Uncertain |
| Router | Chiến lược nào đủ điều kiện? | Trend Pullback, Range Mean Reversion, No Trade |

- «`Event-risk` … cần bằng chứng sự kiện phù hợp; không mặc định suy ra được từ OHLC.»
- «`No Trade` là quyết định của tầng chọn chiến lược. Lỗi dữ liệu phải có trạng thái riêng, không được gộp thành
  Range, Uncertain hoặc "không có cơ hội".» (trùng `AGENTS.md` §2.2)

**Quy tắc ra quyết định** (`[C]AI_Trading_Copilot_Luong_He_Thong.md` §4; router có 5 trạng thái: Trend, Range,
Breakout, Event-risk, Uncertain):

| Trường hợp | Kết quả |
|---|---|
| Trend, Trend Pullback đủ bằng chứng, tài khoản cho phép | Đề xuất Trend Pullback |
| Range, Mean Reversion đủ bằng chứng | Đề xuất Mean Reversion |
| Breakout nhưng chưa có bot tương ứng | No Trade |
| Uncertain hoặc tín hiệu xung đột vượt ngưỡng | No Trade |
| Giá cũ, thông số sai, tài khoản chưa rõ | Chặn lệnh mới (lỗi dữ liệu, không phải No Trade do thị trường) |

**Bộ đánh giá phải có nhiều regime** (`…Moi_Truong_Thu_Nghiem…` §5.8, §8.2):
- Không gắn «vàng = trend»; phân loại theo từng cửa sổ và khung (có thể trend M15 nhưng range H4).
- Nhóm tình huống: trend tăng/giảm; range biến động thấp/cao; range → trend (trễ breakout, báo sớm sai); trend suy
  yếu → range/đảo; phá vỡ thất bại, spike rồi quay lại; cửa sổ sự kiện, spread giãn.
- Tập liên tục (tỷ lệ tự nhiên, ngoài mẫu) + tập tình huống (tiêu chí công bố trước, báo riêng) + bảng độ bao phủ
  (mã × khung: số đoạn, thời lượng) + nhãn tham chiếu độc lập (không tự chứng minh).
- Tiêu chí chất lượng: độ trễ, tín hiệu sai, bỏ sót, độ ổn định, **tỷ lệ Uncertain**, độ bền theo giai đoạn/cặp/khung.
  Nhãn tay → kiểm đồng thuận người gán. Nhãn nhìn tương lai chỉ để đánh giá hồi cứu.
- Giá trị cho Copilot (P&L) đo bằng chuỗi E0 (từng chiến lược) → E1 (router luật + No Trade) → E2 (HMM online)…
  ở repo giao dịch, cùng chi phí và cách khớp (`[C]AI_Trading_Copilot_Ke_Hoach_Update_Va_Tich_Hop_Research.md` §7).
  Lab không đo P&L (`AGENTS.md` §2.4) — ranh giới này giữ nguyên.

**Hợp đồng dữ liệu đích** (`[R]docs\REFACTOR_PLAN_AI_TRADING_COPILOT.md` §4):
- `MarketSnapshot`: snapshot_id, as_of, available_at, nguồn/hash, bar closed, quality, features version.
- `RegimeEstimate`: estimator/version, filtered probabilities, state mapping, uncertainty, train cutoff.
- `Decision`: candidates, selected/rejected reasons; `Outcome` ∈ PROPOSED, NO_TRADE, BLOCKED_DATA, BLOCKED_RISK, ERROR.

Chưa chốt phía sản phẩm (`…Luong_He_Thong.md` §14, `…Ke_Hoach…` §3): mã/khung đầu tiên, điều kiện vào/thoát của
hai chiến lược, phí, split và tiêu chí giữ/loại.

---

## 2. Dự án cũ `regime-aware-ai-trading`: làm gì, cái gì dùng lại được

Bot crypto BTCUSDT (dữ liệu train Binance spot, live OKX swap). Luồng: OHLCV → chỉ báo + đa khung → regime (HMM 4
trạng thái hoặc luật) → Mixture-of-Experts / mô hình theo regime → lọc → risk → lệnh. Một commit + một đợt refactor
chưa commit; 78 test đạt nhưng không test nào chạm regime, nhãn hay tính nhân quả; dữ liệu và model không có trong
repo nên không tái lập được kết quả nào.

### 2.1. Regime trong repo cũ

- Luôn là `trending / ranging / volatile / calm` (id 0..3), có ≥ 10 biến thể định nghĩa: HMM 4 trạng thái
  (`[S]market_models\regime.py:287-479`), luật MACD/RSI/BB/ATR (`:482-516`), bỏ phiếu 4 luật + HMM
  (`[S]strategies\ml\regime_ensemble_strategy.py:543-650`), ADX (`[P]train_h1_proper.py:104-122`), tertile độ lệch
  chuẩn return (`[R]scripts\train_moe_v2_m15.py:153-159` — đây là «regime» thật dùng để train MoE M15).
- **Không có Breakout theo cấu trúc giá, không có lớp Uncertain** — chỉ có cơ chế chặn lệnh (entropy xác suất regime
  > 0.85, xác suất tối đa < 0.6).
- **Gộp hướng vào regime:** «trending» trong các luật chỉ là xu hướng tăng; xu hướng giảm bị xếp vào ranging/calm
  (`regime_ensemble_strategy.py:586`). Ngưỡng MACD theo USD (phụ thuộc thang giá).
- **Không có nhãn regime và không đánh giá regime** — chỉ gián tiếp qua P&L.

### 2.2. Lỗi phương pháp (bài học trực tiếp cho lab)

| Lỗi | Vị trí | Bài học |
|---|---|---|
| HMM Viterbi / forward–backward trên cả chuỗi; fit và suy luận trên cùng cửa sổ | `regime.py:192-195, 320-329`; `[P]evaluate_h1_full.py:162-200` | Chỉ lọc forward, fit trên train, đóng băng ánh xạ trạng thái |
| Nến H4/D1 gắn nhãn đầu kỳ rồi ffill/bfill → rò tới 23 giờ | `[S]features\multi_timeframe.py:85-89, 220-262`; `[S]ml\h1_enhanced_model.py:182-230` | Khung lớn chỉ dùng nến đã chốt (lab: `known_at`, giai đoạn 3) |
| Pivot cửa sổ trung tâm (`center=True`) | `[S]indicators\ict.py:29-30` | Pivot phải có trễ xác nhận (lab đã làm) |
| Quantile / chuẩn hoá trên toàn dữ liệu; `bfill` khi khởi động | `train_moe_v2_m15.py:154-156`; `regime.py:86` | Ngưỡng theo phân vị **dev**, cố định trước |
| Random split; chọn cấu hình trên test | `[R]train_model.py:13`; `train_h1_proper.py:202-266` | Khoá đoạn kiểm tra (lab: §6.3 AGENTS) |
| Lọc regime bằng nến cuối cho cả chuỗi | `regime_ensemble_strategy.py:867-886` | Quyết định theo từng nến |

**Kết quả:** các con số «đẹp» trong README/PDF (WR 93–95%, PF 8–37) gần như chắc do rò rỉ. Artifact M15 thật duy nhất
cho PF ≈ 1.0 **trước phí** (0.07–1 bp/tín hiệu), thấp hơn nhiều so với chi phí chính repo giả định (10–16 bp/vòng).
Mọi model `accepted_for_production: false`.

### 2.3. Đáng giữ

1. **Bỏ phiếu nhiều bằng chứng + làm mượt + hysteresis + entropy → không giao dịch**
   (`regime_ensemble_strategy.py:543-650`: EWM span 5; chỉ đổi regime khi P(mới) > P(cũ) + 0.15). Khung này hợp
   với Trend/Range/Breakout/Uncertain nếu mỗi phiếu là một nhóm bằng chứng cấu trúc.
2. **Ngữ cảnh đa khung** (`[P]algo_trading\features\mtf_context_m15.py:55-68`): `regime`, `regime_confidence`,
   `direction`, `trend_aligned`, `tradeable`, `risk_mode` — hình mẫu gần nhất của «bias + regime + có nên đứng ngoài».
3. **Router luật đơn giản làm baseline** (`[P]algo_trading\ml\h1_hybrid_model.py:93-119`: ADX > 25 → mô hình xu
   hướng; còn lại → hồi quy về trung bình khi RSI cực trị).
4. Báo cáo trung thực: `acceptance_checks`, `wf_summary`, `accepted_for_production` (`[P]models\*`).
5. «Cost/move ratio M15 40% vs H1 12%» (`[P]README.md:129-135`): chọn khung sao cho biên độ kỳ vọng lớn hơn hẳn chi
   phí — liên quan khi chọn khung chạy regime cho router.
6. Chính repo cũ đã tự đặt hướng mới trùng ý lab: «một symbol, hai chiến lược Trend Pullback và Range Mean
   Reversion, router luật làm baseline, No Trade có lý do… HMM là nhánh so sánh nghiên cứu»
   (`[R]docs\REFACTOR_PLAN_AI_TRADING_COPILOT.md:16`).

### 2.4. Hàm ý cho lab

- **Tách ba thứ:** bias có hướng (tăng / giảm / không rõ) — regime (Trend / Range / Breakout / Uncertain; Trend lấy
  chiều từ bias) — router (ở repo giao dịch).
- **Uncertain là lớp chính danh có lý do**, không phải phần còn lại; báo tỷ lệ Uncertain song song mọi số đo.
- **Đánh giá regime tách khỏi P&L** (độ bền, trễ, độ phủ, quan hệ với biên độ/biến động tương lai có null). Router đo
  sau, ở repo giao dịch, cùng dữ liệu và chi phí.
- Lab xuất một bản «RegimeEstimate» (phiên bản, trạng thái, lý do, độ bất định, mốc dev đã dùng để chốt ngưỡng) để
  repo giao dịch dùng cho E1.
