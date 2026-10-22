# Plan: tích hợp nghiên cứu vào `ict_structure`

Bản 1 — 22/10/2026. **Trạng thái: Q1–Q3 đã chốt (người dùng, 22/10/2026 — theo đề xuất); Q4–Q8 chờ.** Bắt đầu đợt 0.

Tài liệu này ánh xạ mọi phát hiện dùng được trong `D:\Finance_System\research_notes` vào hệ thống: đưa **cái gì**, vào
**thành phần nào**, ở **bước nào** trong một nến, dưới **dạng nào** (biến thể, cờ, thành phần mới, script nghiên cứu), ảnh
hưởng **phiên bản** ra sao, và làm theo **thứ tự nào**. Mục tiêu: nhận diện cấu trúc **đúng định nghĩa nguồn** và **khớp
cấu trúc người nhìn thấy** hơn, giữ nguyên nhân quả.

Hệ thống đích: `ict_structure` 0.9.1 — [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md),
lớp nhận diện [`thuat_toan_nhan_dien.md`](../algorithms/thuat_toan_nhan_dien.md), nguồn swing mới
[`thuat_toan_swing_persistence.md`](../algorithms/thuat_toan_swing_persistence.md) (bản nháp), hạ tầng chấm `core/eval/`
và nhãn `core/labels.py`, `backend/app/…/labels`.

---

## 1. Nghiên cứu nguồn

| Thư mục `research_notes\` | Ghi chú | Đóng góp chính cho hệ thống |
|---|---|---|
| `Định nghĩa cấu trúc thị trường` | `ict_primary` (41 phụ đề ICT, có mốc), `smc_community`, `classical_schools`, `academic_quant`; báo cáo `reports\Định nghĩa cấu trúc thị trường.md` | Định nghĩa gốc từng thời kỳ: swing, ITH/LTH, **MSS 2022**, displacement, order flow 2022, dealing range, IRL/ERL; quy tắc SMC kiểm được (valid pullback, strong/weak); Williams (inside / outside, xác nhận sớm), Wyckoff, Brooks, Dow, Market Profile; persistence ≡ DC; Bry–Boschan; ER dưới random walk |
| `Tài liệu ICT và quant` | `event_detection_evaluation`, `ict_smc_quant_tests`, `open_source_tools`, `gold_fx_microstructure`; báo cáo `reports\Tài liệu ICT và quant.md` | Chấm hai đồng hồ, đồng thuận người gán, null giữ mùa vụ, test nhân quả, đa kiểm định; kiểm định ICT 2026 (null); bản cài có thiết kế nhân quả (MIT); fix / tin / rollover |
| `Mô hình giao dịch hot 2026` | `tradingview_github`, `mql5_ecosystem`, `ml_dl_regime_models`, `llm_agents`, `foundation_models` | Bản cài phổ biến làm **đối chứng ngoài**; TCPDBench (mốc tầm thường mạnh ngang thuật toán); đánh đổi số lần đổi trạng thái ↔ trễ (jump model); mốc regime (Choppiness, JM, HSMM); cảnh báo LLM / VLM gán nhãn |

Phần không dùng (mô hình nền chuỗi thời gian, DL dự báo, agent LLM, engine backtest, P&L…) liệt kê ở §9.

## 2. Hệ thống hiện có và chỗ nghiên cứu chạm vào

| Tầng / thành phần (file) | Hiện tại | Nghiên cứu chỉ ra | Tích hợp |
|---|---|---|---|
| [G] lịch phiên, khoảng trống (`session_gap.py`) | Phân loại khoảng trống theo lịch | Hiệu ứng theo giờ gắn với **fix** và **tin**; rollover 16:00–18:00 ET < 0,6% khối lượng FX; ngày nửa phiên | **T0** |
| [P1] STH/STL (`swing_source.py`) | Pivot strict 1/1; bằng giá → không là pivot (D15) | Đúng ICT; Williams bỏ inside day, xác nhận sớm khi phá nến cực trị; «nến sớm thắng» (persistence, MrOwl1011); valid pullback (SMC) | **S1–S4** |
| [S1] ITH/LTH (`hierarchy.py`) | Lồng kiểu Williams | ICT 2022 thêm ITH do FVG được rebalance; stop run / failure swing là hai dạng swing «institutional» | **S5** |
| [S2] thứ tự, mức được bảo vệ (`structure_order.py`) | Đáy/đỉnh cấu trúc gần nhất | Không khớp ICT (key high = ITH rebalance) lẫn SMC (swing đã khởi phát lần phá) | **L5** |
| [S3]/[E2] vùng thanh khoản (`liquidity.py`) | Vùng **chỉ từ ITH/ITL** (+ H1/H4/D/W); lấy ≥ 0,1·ATR; sweep = close quay lại trong 3 nến | MSS 2022 chạy qua **STH**; Brooks thêm tiêu chí **khoảng cách**; Wyckoff cho W = 0 và cần ngữ cảnh range; sweep một nến (wick qua, thân không qua) | **L1–L3** |
| [S4] dealing range (`dealing_range.py`) | Từ swing cấu trúc | ICT 06/2022: «taken out buy side then … sell side» | **L4** |
| [E3] shift (`shift.py`) | Sweep + **một nến** displacement **đóng cửa** vượt lại **mức vừa quét** trong 3 nến | MSS 2022: stop run → phá **STL trước cú chạy** bằng displacement là **một đoạn**; «does not need to close»; phá ITL «significant»; bias HTF phủ quyết | **E1** |
| [OF] order flow (`order_flow.py`) | Run + shift | ICT 2022: «up closed candles should keep price from going higher», key high không bị vi phạm | **E2** |
| [N] nhận diện v2 (`market_state_v2.py`) | Trend khi cấu trúc cùng chiều + ER 8 giờ ≥ 0,18 hoặc ADX | Random walk 32 nến: ER ≥ 0,18 ở 42–50% cửa sổ; phạt chuyển / hysteresis hiệu quả hơn chỉnh ngưỡng; Dow «line», value area theo TPO (không cần volume) | **N1–N4** |
| Chấm (`core/eval/`) | Ghép theo chỉ số nến ±τ; trễ chỉ là trễ của sự kiện; null `matched_hour_atr_v1` | Null hiện chia ba nhóm theo **ATR thô của từng cửa sổ** (`null_baseline.py:316–323`) → giờ và ATR lẫn nhau; thiếu trễ so với nhãn, F1(τ), thước nhãn đoạn, null căn chỉnh, đa kiểm định phụ thuộc | **V2, V3, V6** |
| Nhãn (`core/labels.py`, `schema.py`) | Chỉ `bar_index`, `price`, loại; một người mỗi bộ; ghi đè revision; không coverage; loại nhãn swing / BOS / CHoCH / SHIFT | Cần coverage, «không chắc», người gán, phiên bản rubric, bản chụp, nhãn đoạn, **nhãn MSS hai mốc** | **V1, V4** |

## 3. Quyết định cần chốt

| # | Câu hỏi | Đề xuất / **đã chốt** |
|---|---|---|
| Q1 | Định nghĩa mới vào **biến thể** hay đổi mặc định ngay? | **Chốt: biến thể** có tên, mặc định không đổi; đổi mặc định ở đợt 4 khi có số trên nhãn (§6) |
| Q2 | Thêm vùng thanh khoản từ **STH** (`sweep_nguon = sth`) — STH ~40 / ngày, nhiều vùng hơn ITH ~4 lần | **Chốt: phương án (a)** — tầng riêng `STH`, **chỉ dùng để tìm shift / MSS**: không vào order flow, DOL, `liq_above/below`, hiển thị Gọn; chỉ bật trong biến thể; đo thời gian chạy |
| Q3 | Đổi schema nhãn (thêm cột / bảng, tương thích ngược — AGENTS §4.6) | **Chốt: đồng ý** — chỉ thêm cột (cho phép trống) và bảng; bộ nhãn, lần chấm cũ mở và cho số như cũ |
| Q4 | Người gán thứ hai; tự gán lại | Một thành viên nhóm gán độc lập; tự gán lại sau ~2 tuần, xáo thứ tự cửa sổ |
| Q5 | Lịch fix / tin khai báo tay (BLS lưu trữ theo năm, ECB, LBMA, WMR, Tokyo) | Đồng ý; giờ FOMC chưa xác minh → để trống tới khi có nguồn chính thức |
| Q6 | Thêm `hypothesis` vào phụ thuộc test | Đồng ý (chỉ test) |
| Q7 | Thứ tự rằng buộc ở §7 | Đợt 0 (chấm + nhãn) trước hoặc song song đợt 1 |
| Q8 | Khoảng cách dev / test | Embargo ≥ trễ xác nhận lớn nhất (LTH ~23 nến; làm tròn 1 ngày) |

## 4. Ánh xạ nghiên cứu → hệ thống

Ký hiệu dạng: **BT** = biến thể tham số (mặc định = hiện tại) · **C** = cờ / thuộc tính trong `details` + timeline (không
lọc) · **TP** = thành phần mới · **TT** = thuật toán riêng · **NC** = script `research/` (ngoài lõi) · **HT** = hạ tầng chấm /
nhãn. Mọi BT / C / TP làm output mặc định giữ nguyên sự kiện cũ, chỉ thêm khoá → tăng minor (AGENTS §5.3).

### 4.1. Tầng 0 — cờ thời điểm (bước 1 [G] → chụp vào `details` và timeline)

| ID | Tích hợp | Nguồn | Đặt ở | Dạng |
|---|---|---|---|---|
| T0-1 | Lịch sự kiện khai báo theo **giờ London / New York / Tokyo** (đổi giờ mùa hè từng nơi): LBMA 10:30, 15:00 London; WMR 16:00 London (cửa sổ 5 phút từ 15/02/2015); Tokyo fix 09:55 JST; ECB fix 14:15 CET; tin Mỹ 08:30 / 10:00 ET (trang lưu trữ BLS theo năm); ECB quyết định 07:45→08:15 ET và họp báo 08:30→08:45 ET từ **21/07/2022** | GFX Q3–Q4, Q7; Krohn 2024; Evans 2018; Elder 2012 | `data/calendars/su_kien/*.json` + `core/components/event_flags.py` | TP + C |
| T0-2 | Cờ `nen_tin`: nến 08:30–08:45 ET và nến kế; cờ `nhieu_su_kien` (họp báo ECB trước 2022 trùng tin Mỹ 08:30) | GFX Q3 | như trên | C |
| T0-3 | Cờ `thanh_khoan_mong` 16:45–18:15 ET; cờ `nua_phien` (ngày đóng sớm, từ lịch CME đã có) | GFX Q1, Q5; OSS §3 | như trên | C |
| T0-4 | Cờ `cuoi_thang` (EURUSD quanh WMR) | Evans 2018 | như trên | C |
| T0-5 | Cờ `jump` (|r| / σ theo giờ, σ chỉ từ quá khứ) tách khỏi `nen_tin` | Lahaye 2011 | như trên | C (sau) |

Dùng: chấm tách F1 theo cờ (displacement ≥ 1,5·ATR do tin có thể sinh shift giả; spread rollover sinh STH / sweep giả); rubric
gán nhãn ghi cùng cờ (§4.6).

### 4.2. Tầng 1 — swing (bước 9 [P1] → [S1])

| ID | Tích hợp | Nguồn | Đặt ở | Dạng |
|---|---|---|---|---|
| S1 | Thuật toán `swing_persistence` (ba cấp × ATR, `duong_oc`) | academic §2; đặc tả đã viết | `core/components/persistence_source.py`, `core/algorithms/swing_persistence/` | TT |
| S2 | `inside_bar` ∈ {`giu`, `bo`}: inside = high < high trước **và** low > low trước, loại khỏi chuỗi trước khi so 1/1; chuỗi inside so với **nến mẹ** | Williams 1999 tr. 16–17; True SMC | `swing_source.py` | BT |
| S3 | `xac_nhan_pivot` ∈ {`nen_phai` (hiện tại), `pha_nen_cuc_tri`}: STH biết khi giá xuống dưới low của nến có higher high (Williams); trễ theo ca | Williams tr. 21; Begashvili | `swing_source.py` | BT |
| S4 | `bang_gia` ∈ {`strict` (D15), `nen_som`}: so nghiêm ngặt với nến cũ, ≥ với nến mới | persistence; MrOwl1011 (MIT) | `swing_source.py` | BT |
| S5 | Nguồn `pullback` (valid pullback SMC: nến sau quét hoặc đóng qua nến trước; inside bị bỏ; wick / close) | smc §1 | nguồn swing mới, cùng kiểu `Pivot` | BT |
| S6 | Thuộc tính `rebalance` trên ITH/ITL (swing hình thành lúc một FVG cũ được rebalance — ICT tự nhận «pioneered») và `kieu_swing` ∈ {`stop_run`, `failure_swing`} (lần hai không lấy được mức) | `8GkQfdAXZP0` 0:13:24, 0:22:55; `xRjKtUEKkSE` 0:01:32 | `hierarchy.py`, đọc FVG [P2] đã biết | C |

Cắm `swing_persistence` làm `swing_source` của `ict_structure` cần thay `Pivot.members` (đọc ở `algorithm.py` dòng 745,
1126) — để sau đợt 4, chỉ khi số liệu ủng hộ.

### 4.3. Tầng 2 — thanh khoản, dealing range, mức được bảo vệ (bước 3 [E2], bước 8 [S2]/[S4])

| ID | Tích hợp | Nguồn | Đặt ở | Dạng |
|---|---|---|---|---|
| L1 | `sweep_nguon` ∈ {`ith` (hiện tại), `sth`}: thêm vùng từ STH, tầng riêng `STH` (hạng thấp nhất trong `TIER_RANK`). **Q2 (a):** sweep tầng `STH` chỉ sinh ứng viên shift / MSS; run, sweep tầng `STH` không vào order flow, DOL, `liq_above/below`, hiển thị Gọn | `Bkt8B3kLATQ` 0:18:37 («the initial short-term high»); `UrS-mtGHtAA` 0:00:39 | `liquidity.py` (heap mỗi phía × tầng — đã có) | BT |
| L2 | `sweep_kieu` ∈ {`close_W` (hiện tại), `mot_nen` (wick qua, thân không qua)}; lưới `sweep_window` {0, 2, 3, 5}; `run_sau_atr` = k: xuyên > k·ATR → run ngay | rpanchyk (MIT); Brooks «extends too far»; Wyckoff (W = 0) | `liquidity.py` | BT |
| L3 | Thuộc tính `irl_erl` cho mỗi lần lấy (theo dealing range đang có); `xuyen_atr` đã có → phân tầng khi chấm | `npL3ZXJ5zOU` 0:00:35 | `liquidity.py` | C |
| L4 | `dealing_kieu` ∈ {`swing` (hiện tại), `bsl_roi_ssl`}: biên = cực trị của nến lấy BSL và nến lấy SSL, đổi khi một phía mới bị lấy | `s-iqN0h2Fgg` 0:01:33 | `dealing_range.py` | BT |
| L5 | `muc_bao_ve` ∈ {`gan_nhat` (hiện tại), `khoi_phat_pha` (swing đã khởi phát lần phá — SMC «strong»), `key_rebalance` (ITH/ITL có `rebalance` — ICT)}; hạ cấp là sự kiện mới, không sửa cũ | smc §1 LuxAlgo; `8GkQfdAXZP0` 0:50:42 | `structure_order.py` | BT |
| L6 | Vùng đối chứng: số tròn (XAU $10 / $50 / $100; EUR 00 / 50 pip), đỉnh/đáy phiên Á; so P(run \| lấy) theo loại vùng với vùng giả cùng khoảng cách, cùng giờ | Aggarwal & Lucey 2007; ICT Structure Visualizer (MQL5 78062) | `research/khao_sat_vung_doi_chung.py` | NC |

### 4.4. Tầng 3 — shift ↔ MSS, order flow (bước 6 [E3], 6b [OF])

| ID | Tích hợp | Nguồn | Đặt ở | Dạng |
|---|---|---|---|---|
| E1a | `shift_ref` ∈ {`muc_quet` (hiện tại), `stl_truoc` (STL cuối cùng có cực trị **trước nến X** của cú quét), `itl_truoc`}; cửa sổ tuỳ chọn mở tới khi X bị vượt | `Bkt8B3kLATQ` 0:18:11, 0:20:52; `8GkQfdAXZP0` 0:31:15 | `shift.py` (đọc STL/ITL đã xác nhận trước t) | BT |
| E1b | `disp_kieu` ∈ {`mot_nen` (hiện tại), `doan` (biên độ từ X tới **mức tham chiếu** ≥ a·ATR **và** thân mạnh nhất của đoạn ≥ b·ATR, ATR đo **trước** cú chạy), `fvg` (đoạn để lại FVG cùng chiều — trễ +1 nến)} | `Bkt8B3kLATQ` 0:20:52–0:21:16; MrOwl1011 DESIGN.md | `shift.py`, `displacement.py` | BT |
| E1c | `shift_xac_nhan` ∈ {`close` (hiện tại), `wick`} | `nQfHZ2DEJ8c` 0:13:47 («does not need to close») | `shift.py` | BT |
| E1d | Thuộc tính `nguoc_bias_htf` (ngược thứ tự H4 / ngày đã chốt) và `con_eq_doi_dien`; biến thể chấm `loc_htf` chỉ lọc khi chấm, lõi không lọc (D9 / D11: khung lớn là đặc trưng) | `s-iqN0h2Fgg` 0:02:33; `FBxxYUvNaY4` 0:39:40 | `shift.py`, đọc `details.htf` | C |
| E2 | Trạng thái `of_2022` (còn nguyên / bị vô hiệu): close vượt nến OB (đã có `OB_FAIL`) hoặc vượt key high/low (L5 `key_rebalance`) | `8GkQfdAXZP0` 0:48:36, 0:50:42 | `order_flow.py` | C (mô tả) |
| E3 | `thu_tu = pha_truoc` (Brooks MTR: phá trước, test cực trị sau) | classical §3 | `shift.py` | BT (thấp) |

Không bỏ shift hiện tại: nó là định nghĩa riêng của lab (gần spring + SOS của Wyckoff). Nếu nhãn MSS 2022 chọn biến thể khác,
đặt tên rõ «MSS ICT 2022» cho biến thể đó; shift hiện tại giữ tên «sweep có displacement».

### 4.5. Lớp nhận diện (bước 13 [N])

| ID | Tích hợp | Nguồn | Đặt ở | Dạng |
|---|---|---|---|---|
| N1 | Ngưỡng ER theo **bội nền nhiễu**: `nd_er_*` hiểu là bội của 1/√n (n = số nến cửa sổ) | academic §3; mô phỏng (ER ≥ 0,18: 42–50% cửa sổ random walk) | `market_state_v2.py` | BT |
| N2 | Phạt chuyển / hysteresis kiểu jump model (λ); chấm theo **đường cong số lần đổi ↔ trễ biên** thay vì một điểm | Shu et al. 2024 (ml Q4) | `market_state_v2.py` | BT |
| N3 | Range kiểu **Dow line** (chuỗi close trong biên hẹp, phá bằng close) và **value area theo TPO** (theo thời gian, không cần volume); báo tỷ lệ «không phân loại được» | Hamilton 1922; Steidlmayer; Firich 2012 (71,4%) | `market_state_v2.py` | BT |
| N4 | Mốc so sánh regime: Choppiness (38,2 / 61,8), jump model `predict_online` (Apache-2.0), HSMM 4 trạng thái — vai trò null «chỉ biến động» mà v2 phải thắng | mql5 §2 C5–C6; ml Q4 | `research/` | NC |

### 4.6. Hạ tầng chấm và nhãn (để mọi mục trên kiểm được)

| ID | Tích hợp | Nguồn | Đặt ở | Dạng |
|---|---|---|---|---|
| V1 | Schema nhãn **thêm**: coverage mỗi bộ; `khong_chac` với ba chế độ chấm (tính / bỏ / don't care); `annotator_id`, `guideline_version`, `labelled_at`, `confidence`, `visible_right_context_bars`; bản chụp mỗi revision; **nhãn đoạn** (bắt đầu, kết thúc, lớp); **nhãn MSS hai mốc** `t_xuyen` (wick đầu tiên qua STL) và `t_dong` (close đầu tiên qua) + thuộc tính `thuyet_phuc`, `co_fvg`, `cap_muc` (STL / ITL), `nguoc_bias_htf`, `con_eq_doi_dien`; nhãn ITH thêm `rebalance`, `kieu_swing`; `theo_sau` | EDE (b); defs #8, #11, #12 | `schema.py` (migrate), `services/labels.py`, trang Gán nhãn | HT |
| V2 | Chấm hai đồng hồ: trễ so với nhãn (TP), sai số vị trí có dấu, F1(τ) với τ ∈ {0, 1, 2, 3, 5} + diện tích dưới đường; F1(h) với h bắt đầu từ **trễ lý thuyết tối thiểu** của từng loại; dung sai giá theo ATR; `max_lag_bars` thành trục riêng; vùng don't-care sát biên coverage; thước nhãn đoạn (collar đầu = τ\*, collar cuối = max(τ\*, 20% độ dài); boundary-F1; covering; WindowDiff; số lần đổi; trễ biên); chấm cùng detector tại `event_time` và tại `confirmed_at` (đo «look-ahead inflation»); **không dùng** point-adjust, affiliation, VUS cho sự kiện nhị phân | EDE (a), (d); TSB-AD; DCASE; TCPDBench | `core/eval/`, `PROTOCOL_VERSION` 1.1.0 (chỉ thêm trường) | HT |
| V3 | Null: `matched_hour_atrnorm_v2` (ATR chia trung vị ATR cùng giờ NY, phân vị trên toàn dev — sửa chỗ giờ / ATR lẫn nhau của v1); dịch vòng chuỗi sự kiện k × 96 nến; interval jitter ±J; N tới 10 000 (`NULL_N_MAX` hiện 1 000); null đoạn (lớp đa số, «không đổi», null chỉ biến động N4); kiểm size của null bằng detector ngẫu nhiên có tụ cụm (tỷ lệ bác bỏ ≈ 5%) | EDE (c); Tangirala 2026; TCPDBench | `core/eval/null_baseline.py` | HT |
| V4 | Đồng thuận người–người: so hai bộ nhãn bằng **chính matcher** (nhãn bọc thành sự kiện) trên phần giao coverage; τ\* = P90 lệch vị trí; script `research/`: γ Mathet (`pygamma-agreement`, ghi tham số dissimilarity), Krippendorff α_u; κ chỉ cho nhãn đoạn (không dùng κ từng nến cho sự kiện hiếm) | EDE (b) | `core/eval/`, endpoint, trang Đánh giá | HT |
| V5 | Test tính chất (Hypothesis): đổi nến tương lai không đổi sự kiện có `confirmed_at ≤ t`; `event_time ≤ confirmed_at ≤ t` và trễ ≥ biên lý thuyết; bất biến với biến đổi affine giá, dịch bội số tuần; máy trạng thái (streaming = batch); ca biên: bằng giá, inside bar, doji, cuối tuần, thiếu nến, đổi giờ; **cài rò rỉ có chủ đích** (high của t+1, `center=True`, resample nhãn phải, ATR toàn chuỗi) để đo tỷ lệ test bắt được | EDE (d); OSS §1 | `tests/algorithms/` | HT — điều kiện «xong» của mọi BT |
| V6 | Đa kiểm định: BY hoặc Romano–Wolf maxT trên **cùng** các lượt rút null (biến thể phụ thuộc dương mạnh — BH chưa đủ); persistence qua các tiểu giai đoạn dev; báo p thô và đã điều chỉnh; embargo dev / test (Q8); test mở một lần | EDE (d); Bajgrowicz–Scaillet 2012 | `research/`, sổ thử | HT |

**Rubric gán nhãn** (văn bản, đi cùng V1 — `docs/guides/rubric_nhan_ict.md`): swing theo **high / low** (cấm tắt wick), nhãn ở
nến giữa, không đòi nến thứ 4; ITH lồng nhau; MSS 2022 = stop run (qua STH hoặc ITH) → phá STL trước cú chạy, ghi hai mốc,
không đòi FVG, không đòi close; chỉ gán MSS (MSB ngoài phạm vi); phá mà không có stop run không phải MSS; quét IRL trong nhịp
hồi không phải MSS; ghi bias ngày **một lần trước khi gán**; **không** ghi các ngưỡng của lab (1,5·ATR, 0,1·ATR, 3 nến) để
tránh chấm vòng tròn; gán ở chế độ replay (không nhìn tương lai) hoặc ghi `theo_sau`. Mỗi quy tắc dẫn mốc video trong
`research_notes\Định nghĩa cấu trúc thị trường\ict_primary.md`.

**Quy trình gán:** pilot 2–3 người trên 10–20 cửa sổ → sửa rubric → gán chính trên **cửa sổ phân tầng giờ × ATR × regime**
(không chỉ hai tuần liền nhau), trình bày ngẫu nhiên, ≥ 20% cửa sổ chồng lấn suốt giai đoạn; tự gán lại sau ~2 tuần; IAA thấp
thì chấm theo từng người và theo consensus. **Không** dùng LLM / VLM làm người gán hay gợi ý nhãn (VLM chủ yếu ngoại suy trend
— llm Q4).

### 4.7. Đối chứng ngoài (chỉ `research/`, không bao giờ thành mặc định)

| Bản cài | Giấy phép | Dùng thế nào |
|---|---|---|
| Swing / sweep một dòng (cực trị cuộn N nến; phá đỉnh/đáy N nến rồi đóng ngược) | lab tự viết | Mốc tầm thường (Wu & Keogh 2021) |
| MrOwl1011/Smc_ZOB_CISD | MIT (`af253a86bf`) | Đối chiếu định nghĩa displacement theo đoạn, swing «nến sớm thắng»; chuyển thể được, ghi nguồn |
| carreypro/ict-trading-model | MIT (`7162437e28`) | Đối chiếu MSS theo close; có lookahead batch — chỉ so định nghĩa |
| rpanchyk (MQL5) | MIT | Sweep một nến |
| LuxAlgo SMC (internal 5 / swing 50) | CC BY-NC-SA 4.0 | **Chỉ đọc**; cài lại độc lập từ mô tả định nghĩa trong `research/`, không chép mã |
| MQL5 78551 (fractal N = 5, BOS/CHoCH theo close), 78062 (ICT Structure Visualizer) | không ghi | Chỉ đọc mô tả; mật độ tham chiếu (78062: ~1,1 setup / ngày XAUUSD M15) |
| `smartmoneyconcepts` (joshyattridge) | MIT | **Không** dùng làm mốc: bốn chỗ nhìn tương lai (`shift(-…)`, `pip_range` toàn dataset, UTC cố định) — chỉ làm ví dụ rò rỉ cho V5 |

## 5. Kiến trúc tích hợp

**Nguyên tắc.** Khái niệm mới là thành phần trong `core/components/` (AGENTS §4.2); tham số mới mặc định bằng hành vi hiện tại;
sự kiện mới chỉ **thêm**, `details` chỉ thêm khoá; mỗi đợt một minor + hồi quy run đã lưu (mặc định trùng tuyệt đối, thuật
toán khác 100%); plugin chỉ đọc lõi.

**Vị trí trong thứ tự một nến** (đặc tả §4.1):

```text
1  [G]   kiểm nến, khoảng trống            + T0 cờ thời điểm (lịch sự kiện khai báo)
3  [E2]  vùng thanh khoản: lấy → sweep/run + L1 tầng STH, L2 sweep_kieu / run_sau_atr, L3 irl_erl
6  [E3]  shift                              + E1 shift_ref / disp_kieu / shift_xac_nhan / nguoc_bias_htf
6b [OF]  order flow                         + E2 of_2022 (mô tả)
8  [S2]/[S4] mức được bảo vệ, dealing range + L4 dealing_kieu, L5 muc_bao_ve
9  [P1]→[S1] pivot → ITH/LTH                + S2 inside_bar, S3 xac_nhan_pivot, S4 bang_gia, S5 pullback, S6 rebalance / kieu_swing
13 [N]   nhận diện                          + N1 ER theo nền nhiễu, N2 phạt chuyển, N3 Dow line / TPO
```

Thứ tự 1–13 không đổi; mục mới chỉ đọc trạng thái mà bước đó vốn được đọc (vd E1a đọc STL / ITL đã xác nhận **trước** t, E1d đọc
ngữ cảnh khung lớn sau t − 1).

**Hiệu năng.** Ngân sách: mặc định không chậm hơn; biến thể L1 (`sth`) ≤ +30% trên XAUUSD M15 01/2018–08/2024 (157 592 nến; 0.4.0
đo 9,2 s, đo lại mốc 0.9.1 trước đợt 1). Đo ở mỗi đợt.

**Hiển thị.** Đợt 1–3 chỉ thêm chữ vào tooltip / dòng trạng thái (cờ T0, `nguoc_bias_htf`, `rebalance`); vẽ riêng cho biến thể để
sau khi có số (§7 đợt 4).

## 6. Chuỗi thí nghiệm (khai trước — chỉ dev)

| H | Giả thuyết | Cấu hình | Thước |
|---|---|---|---|
| H1 | Biến thể MSS 2022 (`sweep_nguon = sth`, `shift_ref = stl_truoc`) khớp nhãn MSS hơn shift hiện tại | E1a × L1 | F1(τ\*) theo `t_xuyen` và `t_dong` |
| H2 | `disp_kieu = doan` bắt được MSS mà bản một nến bỏ sót | E1b | recall, trễ |
| H3 | Ít nhất một nguồn swing khác (persistence, `inside_bar = bo`, `pullback`, `bang_gia = nen_som`) khớp nhãn ITH ngang hoặc hơn, trễ thấp hơn | S1–S5 | F1(τ\*), trễ so với nhãn |
| H4 | Phần lớn tỷ lệ trend của v2 vẫn còn trên chuỗi giả (ER sát nền nhiễu) | N1 | % trend thật / giả (GSBB chu kỳ 96, khối ngày nối bằng return) |
| H5 | Take → run trên dữ liệu thật khác chuỗi giả (Mahadzva: sweep dự báo tiếp diễn) | L2 | P(run \| take) thật − giả |
| H6 | EQH/EQL: P(run \| k lần chạm) so với P(bật \| k) — đối nghịch Garzarelli 2014 | L6 | ước lượng (n + 1)/(N + 2) theo k |
| H7 | Vùng swing không khác vùng số tròn | L6 | P(run \| take) theo loại vùng |
| H8 | Lỗi detector dồn vào nến có cờ tin / rollover | T0 | F1 tách theo cờ |

**Luật đổi mặc định** (đợt 4): biến thể thay mặc định khi (1) F1(τ\*) cao hơn ≥ 0,05, CI bootstrap khối tuần không chứa 0, còn ý
nghĩa sau BY / maxT **và** giữ dấu ở mọi tiểu giai đoạn dev; (2) tham số lân cận cũng tốt (vùng phẳng, không phải đỉnh nhọn); (3)
trễ so với nhãn P90 tăng ≤ 2 nến; (4) thắng null v2 **và** null dịch vòng. **Mục tiêu:** F1 ≥ 0,9 × F1 người–người cùng τ\*; trần
người–người báo trước, không đặt số tuyệt đối. (Osler 2000 ~30% là độ trùng mức S/R dự báo giữa các hãng, không phải trần nhãn
swing — không dùng làm mốc.)

**Sổ thử:** mọi cấu hình đã chạy (kể cả bỏ) ghi trong `docs/research/khao_sat/` kèm số lượng.

## 7. Thứ tự thực hiện

| Đợt | Phiên bản | Nội dung | Xong khi |
|---|---|---|---|
| **0** | `PROTOCOL_VERSION` 1.1.0; migrate nhãn | V1 schema + trang Gán nhãn (nhãn đoạn, MSS hai mốc), V2 chấm hai đồng hồ + thước đoạn, V3 null v2 + dịch vòng + jitter, V4 đồng thuận, rubric | Chấm lại các lần chấm đã lưu ra đúng số cũ; test tính tay trường mới; ảnh trang Gán nhãn |
| **1** | `ict_structure` 0.10.0 | T0 cờ thời điểm; E1 (a–d); L1, L2; V5 test tính chất cho mọi phần mới | Mặc định trùng tuyệt đối 0.9.1; hiệu năng trong ngân sách |
| **2** | 0.11.0; `swing_persistence` 0.1.0 | S1–S6; L3–L5 | như trên |
| **3** | 0.12.0 | N1–N3 (sau khảo sát nền nhiễu H4) | như trên |
| song song | — | Gán nhãn theo quy trình §4.6 (người); `research/`: nền nhiễu (H4, H5), vùng đối chứng (H6, H7), đối chứng ngoài §4.7, mốc regime N4 | JSON + bảng trong `docs/research/khao_sat/` |
| **4** | tăng theo luật §6 | Chấm dev mọi biến thể (§6) → đổi mặc định nếu đạt → cập nhật đặc tả, plugin vẽ biến thể được chọn → mở test **một lần** | Sổ thử đầy đủ; đặc tả và lịch sử phiên bản cập nhật |

Mỗi khối code: `/simplify` → `/code-review` → `/run` (web thật, bản sao DB, ảnh chụp); chạy toàn bộ test; hồi quy run đã lưu;
commit + push `rieng` sau mỗi phần.

## 8. Việc bắt đầu ngay (sau khi duyệt)

1. ~~V3: `matched_hour_atrnorm_v2` + báo `fallback_events` trên trang Đánh giá~~ — **xong 22/10/2026**: chế độ mới (ATR
   chia trung vị cùng giờ NY của hồ sơ = gộp đoạn dev, truyền từ `score_one_run`), v1 / đồng đều trùng tuyệt đối code cũ
   (60/60 ca + số ghim trong test), chẩn đoán hiện ở trang Đánh giá; 520 test. Dịch vòng, jitter, N tới 10 000 còn lại.
2. V2: trễ so với nhãn, F1(τ), sai số có dấu — chỉ thêm trường; test chấm lại cho số cũ.
3. V1: migrate coverage, `khong_chac`, bản chụp revision; loại nhãn MSS hai mốc.
4. Rubric `docs/guides/rubric_nhan_ict.md` (bạn duyệt) → pilot 10–20 cửa sổ.
5. T0-1 lịch sự kiện khai báo (dữ liệu + thành phần, chưa nối vào lõi).
6. E1a + L1 (biến thể MSS 2022) trên nhánh, đo tần suất / độ trùng với shift hiện tại trên dev (mô tả, chưa chấm).

## 9. Không làm

* **Đoán hướng:** không thêm khảo sát đoán hướng cho tín hiệu ICT (đã null nhiều lần trong lab và trong Mahadzva / Tangirala 2026);
  không đưa các xác suất Brooks 80%, MTR 40–50%, poor high bị quay lại thành giả thuyết. Không P&L.
* **Khái niệm:** IDM (ba vai trò mâu thuẫn), CISD, SMT / xác nhận chéo kiểu Dow (lab không có DXY), initial balance (Dalton đã bỏ cho
  thị trường 24 giờ), Elliott; Wyckoff theo volume (dữ liệu pipeline không có volume — TPO thì làm được, N3).
* **Công cụ:** mô hình nền chuỗi thời gian, DL dự báo, agent LLM, LLM / VLM gán nhãn; `smartmoneyconcepts` làm mốc; `ruptures` hay
  `hmmlearn.predict` / xác suất smoothed làm đặc trưng (chỉ dùng offline làm nhãn chẩn đoán, báo tách khỏi nhãn người).
* **Thứ tự trong nến bằng dữ liệu M1 / M5** (thay giả định open → close): cần nạp luồng khung nhỏ song song — đổi kiến trúc engine,
  để sau và cần quyết định riêng.

## 10. Rủi ro

* Nhãn ít → CI rộng (shift ~0,87 / ngày); trần người–người thấp (ICT tự nhận swing «some measure of subjectivity»).
* Định nghĩa ICT trôi theo thời kỳ (MSS bản 2020 chỉ là phá STH) — rubric ghi rõ «ICT 2022».
* Nhãn nhìn thấy tương lai, detector thì không — gán ở replay hoặc ghi `theo_sau`.
* `inside_bar = bo` trên M15 có thể đổi mạnh mật độ swing (inside bar trên M15 dày hơn ~7,6% của nến ngày).
* Nhiều biến thể → quá khớp dev: BY / maxT, persistence, vùng phẳng, test một lần.
* L1 tăng số vùng ~4 lần → hiệu năng và hiển thị; giữ trong biến thể tới khi có số.
