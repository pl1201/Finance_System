"""[N] Lớp nhận diện của ``ict_structure`` (0.6.0; thời gian 0.7.0): nối ``price_band`` (khoảng giá, xác suất chạm,
phá biên), ``market_state`` (trạng thái) và ``state_clock`` (còn giữ, thời gian còn lại) vào thuật toán — tham số
``nd_*``, bước 13 trong nến, cột timeline ``nd_*``, ``pending_state.nhan_dien``, ``run_stats.nhan_dien``. Đặc tả:
docs/algorithms/thuat_toan_nhan_dien.md.

Thuật toán chỉ giữ ``Optional[NdLayer]`` (None khi tắt ``nd_bat`` → output như 0.5.0) và tự phát sự kiện ``STATE_*``
(cùng ``event_id`` / ``details.htf`` như mọi sự kiện khác).
"""
from __future__ import annotations

from typing import Any, Optional

from core.algorithms.base import ParamSpec
from core.components.market_state import MarketState
from core.components.market_state_v2 import MarketStateV2, Structure
from core.components.price_band import PriceBand
from core.components.state_clock import StateClock
from core.data.htf_stream import NY_TZ
from core.types import Bar, ReasonCode, StructureType

#: Tầm dự báo (giây) — số nến = tầm / khung chạy, chỉ khi chia hết.
HORIZONS = (("1h", 3600), ("4h", 4 * 3600))
#: Khoảng trống dài (cuối tuần, lễ) cắt mẫu biên và cửa sổ trạng thái — như khảo sát (> 3 giờ).
LONG_GAP_MINUTES = 180
#: Loại mức gộp vào ``cham_tong`` (ô tiêu đề): như 0.6.1–0.7.0. PDH / PDL (0.8.0) báo riêng — phần lớn ở xa (p ≈ 0),
#: gộp vào sẽ kéo Brier gộp xuống mà dự báo không tốt hơn; khi trùng giá vùng gần nhất còn bị đếm hai lần.
TOUCH_TOTAL_KINDS = ("vung_tren", "vung_duoi", "range_tren", "range_duoi")
#: B0 của từng xác suất «thời gian» (giao diện ghi kèm điểm thật).
TIME_B0_VI = {"con_giu": "tỷ lệ nến của cùng mẫu đoạn mà đoạn còn kéo dài thêm ≥ tầm (bỏ điều kiện tuổi)",
              "pha_bien": "mẫu chung mọi giờ"}
#: Trạng thái → (loại sự kiện, mã lý do, chiều) — theo kiểu trạng thái (``nd_kieu``).
STATE_EVENT_V2 = {
    "trend_len": (StructureType.STATE_TREND_UP, ReasonCode.STATE_TREND_STRUCTURE, "up"),
    "trend_xuong": (StructureType.STATE_TREND_DOWN, ReasonCode.STATE_TREND_STRUCTURE, "down"),
    "range": (StructureType.STATE_RANGE, ReasonCode.STATE_RANGE_BOX, None),
    "nhieu": (StructureType.STATE_CHOP, ReasonCode.STATE_CHOP_NO_BOX, None),
}
STATE_EVENT = {
    "trend_len": (StructureType.STATE_TREND_UP, ReasonCode.STATE_ER_HIGH, "up"),
    "trend_xuong": (StructureType.STATE_TREND_DOWN, ReasonCode.STATE_ER_HIGH, "down"),
    "range": (StructureType.STATE_RANGE, ReasonCode.STATE_RANGE_EDGES, None),
    "nen": (StructureType.STATE_SQUEEZE, ReasonCode.STATE_SQUEEZE_CONVERGE, None),
    "nhieu": (StructureType.STATE_CHOP, ReasonCode.STATE_ER_LOW, None),
}
#: Cột timeline của mỗi tầm, dựng một lần: (tầm, ((khoá dự báo, cột), …), cột p chạm trên, cột p chạm dưới,
#: cột còn giữ, cột phá biên).
_TL_COLS = tuple((k, tuple((c, "nd_%s_%s" % (k, c)) for c in ("lo80", "hi80", "lo50", "hi50")),
                  "nd_p_tren_" + k, "nd_p_duoi_" + k, "nd_giu_" + k, "nd_pha_" + k) for k, _sec in HORIZONS)

PARAMS = (
    ParamSpec("nd_bat", "Nhận diện: bật", "bool", True, advanced=True,
              help_vi="Khoảng giá 80% / 50% cho 1h, 4h; xác suất chạm vùng gần nhất; trạng thái trend / range / "
                      "sideway. Tự chấm điểm thật trong lần chạy. Tắt → output giống 0.5.0."),
    ParamSpec("nd_muc_80", "Nhận diện: phân vị mỗi phía (khoảng 80%)", "float", 0.905, min=0.5, max=0.99, step=0.005,
              advanced=True, help_vi="Chọn trên dev (học 2018, chấm 2019) để cả đường giá nằm trong khoảng ≈ 80%."),
    ParamSpec("nd_muc_50", "Nhận diện: phân vị mỗi phía (khoảng 50%)", "float", 0.745, min=0.5, max=0.99, step=0.005,
              advanced=True, help_vi="Như trên cho khoảng lõi 50%. Phải nhỏ hơn mức của khoảng 80%."),
    ParamSpec("nd_mau_toi_da", "Nhận diện: số mẫu mỗi giờ NY", "int", 600, min=100, max=5000, step=50, advanced=True,
              help_vi="Cửa sổ trượt mẫu biên cho mỗi giờ New York (M15: ≈ 150 ngày giao dịch)."),
    ParamSpec("nd_mau_toi_thieu", "Nhận diện: mẫu tối thiểu mỗi giờ", "int", 60, min=20, max=1000, step=10,
              advanced=True, help_vi="Giờ có ít mẫu hơn thì dùng mẫu chung mọi giờ."),
    ParamSpec("nd_er_nguong", "Nhận diện: ngưỡng ER (trend / đi ngang)", "float", 0.3, min=0.05, max=0.9, step=0.05,
              advanced=True, help_vi="ER ≥ ngưỡng là trend; range và nén cần ER < ngưỡng."),
    ParamSpec("nd_giu_nen", "Nhận diện: giữ trạng thái mới (nến)", "int", 2, min=1, max=10, step=1, advanced=True,
              help_vi="Trạng thái mới phải giữ đủ bấy nhiêu nến liên tiếp mới đổi (chống nhấp nháy)."),
    ParamSpec("nd_kieu", "Nhận diện: kiểu trạng thái", "choice", "v2", choices=("v2", "v1"), advanced=True,
              choice_labels_vi=(("v2", "v2 — cấu trúc + bằng chứng, hộp range bền, cờ nén"), ("v1", "v1 — như 0.6–0.8")),
              help_vi="v2 (0.9.0): trend theo thứ tự cấu trúc + ER / ADX, giữ tới CHoCH; range giữ tới khi phá biên; nén là "
                      "cờ đi kèm. v1: cách cũ, để so (plan_nhan_dien_v2.md)."),
    ParamSpec("nd_er_vao", "Nhận diện v2: ER vào trend (khi cấu trúc cùng chiều)", "float", 0.18, min=0.05, max=0.9,
              step=0.01, advanced=True, show_if=("nd_kieu", "v2"),
              help_vi="Trend vào khi cấu trúc cùng chiều và ER 8 giờ ≥ ngưỡng này (hoặc ADX ≥ 20 cùng chiều DI)."),
    ParamSpec("nd_er_ra", "Nhận diện v2: ER ra khỏi trend", "float", 0.10, min=0.01, max=0.9, step=0.01, advanced=True,
              show_if=("nd_kieu", "v2"), help_vi="Trend kết thúc khi ER 8 giờ < ngưỡng này và ADX < 18 (hoặc khi CHoCH)."),
)


def horizons_for(step_seconds: int) -> dict[str, int]:
    """Số nến của mỗi tầm trên khung chạy (bỏ tầm không chia hết: H4 chỉ còn 4h, D1 không còn tầm nào)."""
    return {k: sec // step_seconds for k, sec in HORIZONS if sec % step_seconds == 0}


def validate(p: dict[str, Any]) -> None:
    """Ràng buộc liên trường của ``nd_*`` — dựng thử thành phần (cùng thông điệp lỗi với lúc chạy)."""
    PriceBand({}, p["nd_muc_80"], p["nd_muc_50"], p["nd_mau_toi_da"], p["nd_mau_toi_thieu"])
    if p["nd_bat"]:                                    # tắt lớp nhận diện → không ràng buộc ngưỡng trạng thái
        _state(p, 900)


def _state(p: dict[str, Any], step_seconds: float):
    if p["nd_kieu"] == "v1":
        return MarketState(step_seconds, p["nd_er_nguong"], p["nd_giu_nen"])
    return MarketStateV2(step_seconds, p["nd_er_nguong"], p["nd_giu_nen"], p["nd_er_vao"], p["nd_er_ra"])


def manifest(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "bat": params.get("nd_bat"), "muc_80": params.get("nd_muc_80"), "muc_50": params.get("nd_muc_50"),
        "mau_toi_da": params.get("nd_mau_toi_da"), "mau_toi_thieu": params.get("nd_mau_toi_thieu"),
        "er_nguong": params.get("nd_er_nguong"), "giu_nen": params.get("nd_giu_nen"), "kieu": params.get("nd_kieu"),
        "er_vao": params.get("nd_er_vao"), "er_ra": params.get("nd_er_ra"),
        "khoang_trong_dai_phut": LONG_GAP_MINUTES,
        "ghi_chu_vi": "Khoảng 1h / 4h theo giờ NY × biến động (ATR), xác suất chạm theo khoảng cách; tự chấm trong lần "
                      "chạy so với B0. Trạng thái là mô tả — docs/algorithms/thuat_toan_nhan_dien.md.",
    }


class NdLayer:
    def __init__(self, p: dict[str, Any], horizons: dict[str, int], step_seconds: float) -> None:
        self.horizons = horizons
        self.band = PriceBand(horizons, p["nd_muc_80"], p["nd_muc_50"], p["nd_mau_toi_da"], p["nd_mau_toi_thieu"],
                              TOUCH_TOTAL_KINDS)
        self.state = _state(p, step_seconds)
        self.clock = StateClock(horizons)
        self.fc: dict[str, Optional[dict[str, Any]]] = {}
        self.t: Optional[int] = None                       # nến của dự báo hiện có (pending đóng dấu nến này)

    def step(self, bar: Bar, atr: Optional[float], gap: Optional[dict[str, Any]], near: dict[str, Any],
             period: Optional[dict[str, Any]], structure: Structure) -> Optional[tuple[str, Bar, dict[str, Any]]]:
        """Bước 13 của nến t: trạng thái sau t, rồi khoảng + xác suất chạm tại t cho vùng còn nguyên gần nhất mỗi phía
        (``near`` = ``LiquidityBook.nearest()``), PDH / PDL chưa bị lấy (``period`` = ngữ cảnh mức theo kỳ; None khi tắt
        khung lớn; tắt ``period_levels`` thì không biết «đã lấy» → không có PDH / PDL) và biên range. ``structure`` = cấu
        trúc của thuật toán (trạng thái v2 dùng, v1 bỏ qua). Trả (trạng thái mới, nến đầu, info) khi vừa đổi."""
        long_gap = gap is not None and gap["khoang_cach_phut"] > LONG_GAP_MINUTES
        st = self.state
        changed = st.on_bar(bar, atr, long_gap, structure)
        levels = [(kind, side, pool.level) for kind, side, pool in
                  (("vung_tren", "up", near["high"]), ("vung_duoi", "down", near["low"])) if pool is not None]
        if period is not None:                     # 0.8.0: mức ngày trước BIẾT còn nguyên (False, không phải None khi
            pdh, pdl = period["pdh"], period["pdl"]    # tắt period_levels) và ở đúng phía giá
            if pdh is not None and period["pdh_taken"] is False and pdh >= bar.close:
                levels.append(("pdh", "up", pdh))
            if pdl is not None and period["pdl_taken"] is False and pdl <= bar.close:
                levels.append(("pdl", "down", pdl))
        edges = None
        if st.state == "range" and st.info["bien_duoi"] <= bar.close <= st.info["bien_tren"]:   # v2: hộp cố định — close
            lo, hi = st.info["bien_duoi"], st.info["bien_tren"]                                # ngoài hộp: không dự báo
            edges = (lo, hi)
            levels += [("range_tren", "up", hi), ("range_duoi", "down", lo)]
        self.fc = self.band.step(bar, atr, bar.bar_time.astimezone(NY_TZ).hour, long_gap, levels, edges)
        self.clock.step(bar.index, st.state, long_gap)
        self.t = bar.index
        return changed

    def event_kind(self, name: str) -> tuple[str, str, Optional[str]]:
        """(loại sự kiện, mã lý do, chiều) của ``STATE_*`` theo kiểu trạng thái."""
        return (STATE_EVENT_V2 if self.state.kind == "v2" else STATE_EVENT)[name]

    def event_details(self, name: str, first: Bar, info: dict[str, Any], order: Optional[int]) -> dict[str, Any]:
        """``details`` của ``STATE_*``: lý do (số thực đã dùng) + thứ tự cấu trúc cùng chiều (chỉ ghi kèm, N-6)."""
        st = self.state
        details: dict[str, Any] = {"trang_thai": name, "trang_thai_vi": st.text_vi[name], "nen_dau": first.index,
                                   "er_nguong": st.er_threshold, "giu_nen": st.hold, **info}
        direction = self.event_kind(name)[2]
        if direction:
            details["thu_tu_cung_chieu"] = order == (1 if direction == "up" else -1)
        return details

    def timeline(self) -> dict[str, Any]:
        """Sau nến t: trạng thái, cửa sổ / biên range, khoảng 80% / 50% mỗi tầm, xác suất chạm vùng gần nhất; 0.7.0: xác
        suất trạng thái còn giữ, thời gian còn lại (trung vị, nến), xác suất phá biên khi range."""
        st, ck = self.state, self.clock.fc
        rng, giu = (st.info if st.state == "range" else {}), (ck["giu"] if ck else {})
        out: dict[str, Any] = {"nd_trang_thai": st.state, "nd_tu": st.since, "nd_range_tu": rng.get("nen_dau_cua_so"),
                               "nd_range_hi": rng.get("bien_tren"), "nd_range_lo": rng.get("bien_duoi"),
                               "nd_con_lai": ck["con_lai_nen"] if ck else None}
        out.update(st.timeline_extra())             # v2 (0.9.0): cờ nén, độ mạnh (0–1, chỉ hiển thị)
        for k, cols, col_up, col_dn, col_giu, col_pha in _TL_COLS:
            f = self.fc.get(k)
            for key, col in cols:
                out[col] = f[key] if f else None
            p = {m["loai"]: m["p"] for m in f["muc"]} if f else {}
            out[col_up], out[col_dn] = p.get("vung_tren"), p.get("vung_duoi")
            out[col_giu] = giu.get(k)
            out[col_pha] = f["pha_bien"]["p"] if f and f["pha_bien"] else None
        return out

    def pending(self) -> dict[str, Any]:
        """Trạng thái (kèm lý do, ứng viên đang chờ), khoảng mỗi tầm, mức kèm xác suất chạm, điểm thật tới nến này."""
        st, ck = self.state, self.clock.fc
        fc = {k: f for k, f in self.fc.items() if f is not None}
        rows: list[dict[str, Any]] = []
        for k, f in fc.items():                    # mọi tầm cùng danh sách mức, cùng thứ tự (step)
            if not rows:
                rows = [{"loai": m["loai"], "phia": m["phia"], "gia": m["gia"], "kc_atr": m["kc_atr"]} for m in f["muc"]]
            for row, m in zip(rows, f["muc"]):
                row["p_" + k] = m["p"]
        pha = {k: f["pha_bien"] for k, f in fc.items() if f["pha_bien"]}
        edge = next(iter(pha.values()), None)          # mọi tầm cùng biên range
        return {
            "nen": self.t,                         # giao diện chỉ dùng mức / điểm thật khi nến này = con trỏ
            "kieu": st.kind,                       # 0.9.0: kiểu trạng thái (v1 / v2)
            "trang_thai": st.state, "trang_thai_vi": st.text_vi.get(st.state), "tu_nen": st.since,
            "chi_tiet": dict(st.info), "ung_vien": st.pending_candidate(),
            "khoang": {k: {kk: v for kk, v in f.items() if kk not in ("b0", "muc", "pha_bien")} for k, f in fc.items()},
            "muc": rows, "diem_that": self.band.brief(), "tam_nen": dict(self.horizons),
            # 0.7.0: còn giữ / thời gian còn lại (state_clock), phá biên khi range (price_band) + điểm thật
            "thoi_gian": {
                "con_giu": dict(ck, giu=dict(ck["giu"])) if ck else None,      # bản sao: người đọc pending không sửa được lõi
                "pha_bien": {"lo": edge["lo"], "hi": edge["hi"], "p": {k: f["p"] for k, f in pha.items()}} if edge else None,
                "diem_that": self._time_scores(),
            },
        }

    def _time_scores(self) -> dict[str, Any]:
        return {"con_giu": self.clock.brief(), "pha_bien": self.band.break_brief()}

    def stats(self, n_bars: int) -> dict[str, Any]:
        st = self.state
        return {
            "khoang_va_cham": self.band.scores(), "tam_nen": dict(self.horizons),
            "thoi_gian": {**self._time_scores(), "b0_vi": dict(TIME_B0_VI),
                          "ghi_chu_vi": "Còn giữ: trạng thái đang hiện vẫn là đoạn đó sau tầm h. Phá biên: close ra ngoài "
                                        "biên range trong tầm h (chỉ dự báo khi đang range)."},
            "muc_80": self.band.q80, "muc_50": self.band.q50,
            "trang_thai": {"ty_le_thoi_gian": {k: v / n_bars for k, v in st.counts.items()} if n_bars else None,
                           "so_lan_doi": st.changes, "trang_thai_vi": dict(st.text_vi), "kieu": st.kind,
                           "cua_so_nen": st.windows(), **st.stats_extra(n_bars)},
            "ghi_chu_vi": "Điểm thật: chỉ khoảng / xác suất đã có kết cục (không vắt khoảng trống > 3 giờ). Khoảng 80% "
                          "phủ đúng khi CẢ đường giá H giờ sau nằm trong khoảng. B0 = cùng cách nhưng bỏ giờ NY. Giao diện "
                          "hiện điểm này (tooltip khoảng / mức, tab Thống kê) — khoảng là dự báo theo AGENTS §2.4. Trạng thái "
                          "là mô tả (chưa có nhãn tay).",
        }
