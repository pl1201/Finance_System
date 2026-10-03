"""Metric không cần nhãn cho ``dc_atr_structure`` (mô tả hành vi, KHÔNG phải accuracy).

Chỉ đọc log sự kiện đã xác nhận + bộ đếm nến của lần chạy. Ứng viên không bao
giờ được tính. Precision/recall/F1 và confusion matrix regime chỉ có khi có bộ
nhãn tham chiếu độc lập — module này không tự tạo.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence

from core.eval.metrics import median, percentile_nearest_rank

PIVOT_TYPES = ("DC_HIGH", "DC_LOW")
REGIME_EVENT_TYPES = (
    "DC_REGIME_UP", "DC_REGIME_DOWN", "DC_REGIME_UNKNOWN", "DC_RANGE_START", "DC_RANGE_EXIT",
)

#: Ánh xạ khai báo rõ khi muốn chấm pivot DC (close) với nhãn swing (thường theo
#: wick) bằng protocol đánh giá hiện có. Đây là so sánh CHÉO ĐỊNH NGHĨA — phải ghi
#: rõ khi báo cáo; không phải mặc định của protocol.
DC_CROSS_DEFINITION_EVENT_MAP = {"DC_HIGH": "SWING_HIGH", "DC_LOW": "SWING_LOW"}


def _summary(values: Sequence[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "trung_vi": median(values),
        "p90": percentile_nearest_rank(values, 90),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def dc_run_metrics(
    events: Iterable[dict[str, Any]],
    *,
    n_bars: int,
    n_eligible: int,
    n_gaps: int,
    n_bridged: int = 0,
    gap_policy: str = "reset",
    n_segments: int,
    regime_bars: dict[str, int],
    regime_runs: Sequence[tuple[str, int]],
    step_seconds: int,
) -> dict[str, Any]:
    evs = list(events)
    pivots = [e for e in evs if e["structure_type"] in PIVOT_TYPES]
    regime_evs = [e for e in evs if e["structure_type"] in REGIME_EVENT_TYPES]

    lag_bars = [int(e["confirmation_lag_bars"]) for e in pivots]
    lag_min = [float(e["details"]["lag_seconds"]) / 60.0 for e in pivots]
    rev_atr = [float(e["details"]["reversal_distance_atr"]) for e in pivots]
    amp_atr = [
        float(e["details"]["nhip"]["bien_do_atr"])
        for e in pivots
        if e["details"].get("nhip")
    ]
    labels: dict[str, int] = {}
    for e in pivots:
        lb = e["details"].get("nhan") or "(pivot đầu)"
        labels[lb] = labels.get(lb, 0) + 1

    share: dict[str, Optional[float]] = {}
    for st, n in regime_bars.items():
        share[st] = (n / n_eligible) if n_eligible else None

    run_len_by_state: dict[str, list[int]] = {}
    for st, ln in regime_runs:
        run_len_by_state.setdefault(st, []).append(ln)

    return {
        "so_pivot_xac_nhan": len(pivots),
        "so_dinh": sum(1 for e in pivots if e["structure_type"] == "DC_HIGH"),
        "so_day": sum(1 for e in pivots if e["structure_type"] == "DC_LOW"),
        "mat_do_tren_1000_nen": (1000.0 * len(pivots) / n_eligible) if n_eligible else None,
        "mat_do_ghi_chu_vi": "Mẫu số = nến đã có ATR (sau warm-up mỗi segment); ứng viên không tính.",
        "do_tre_nen": _summary(lag_bars),
        "do_tre_phut": _summary(lag_min),
        "reversal_distance_atr": _summary(rev_atr),
        "reversal_ghi_chu_vi": "|close cực trị − close xác nhận| / ATR tại nến cực trị (candidate ATR).",
        "bien_do_nhip_atr": _summary(amp_atr),
        "bien_do_ghi_chu_vi": (
            "|giá pivot − giá pivot liền trước| / ATR tại pivot ĐẦU nhịp; chỉ trong cùng segment."
        ),
        "nhan_so_sanh": labels,
        "regime_so_nen": dict(regime_bars),
        "regime_ty_le_thoi_gian": share,
        "regime_ghi_chu_vi": (
            "Tỷ lệ trên nến đã có ATR; thời gian gap và warm-up không cộng vào regime."
        ),
        "so_lan_chuyen_trang_thai": len(regime_evs),
        "do_dai_doan_trung_vi_nen": {
            st: median(v) for st, v in sorted(run_len_by_state.items())
        },
        "do_dai_doan_trung_vi_tat_ca": median([ln for _, ln in regime_runs]),
        "so_gap": n_gaps,
        "so_gap_noi": n_bridged,
        "gap_policy": gap_policy,
        "so_segment": n_segments,
        "so_nen": n_bars,
        "so_nen_du_dieu_kien": n_eligible,
        "buoc_khung_giay": step_seconds,
        "nhan_tham_chieu": {
            "co_nhan": False,
            "ghi_chu_vi": (
                "Chưa có nhãn tham chiếu cho swing close hay đoạn regime — không tính "
                "precision/recall/F1 hay confusion matrix. Không dùng output baseline làm ground truth."
            ),
        },
        "ghi_chu_vi": "Các con số mô tả hành vi thuật toán, không phải accuracy hay hiệu quả giao dịch.",
    }
