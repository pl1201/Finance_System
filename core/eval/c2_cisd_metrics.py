"""Thống kê vòng đời setup C2/CISD và MFE/MAE đối chứng — chỉ để ĐÁNH GIÁ.

* ``lifecycle_metrics`` chỉ đọc log sự kiện (dict như ``StructureEvent.to_dict``)
  nên chạy lại được trên run đã lưu. Mẫu số luôn được công bố; setup chưa có
  sự kiện kết thúc khi hết dữ liệu là *censored* — không tính là thất bại hay
  hết hạn.
* ``excursion_metrics`` dùng nến SAU thời điểm biết (confirmed_at) trong một
  horizon cố định. Đây là dữ liệu tương lai, CHỈ dùng cho đánh giá — không
  bao giờ đưa ngược vào detector. Mẫu thiếu horizon (hết dữ liệu hoặc gap
  thời gian) bị bỏ và được đếm.

Không có ô nào gọi là win rate: tỷ lệ có CISD chỉ là tần suất một sự kiện
trong vòng đời setup, không phải kết quả giao dịch.
"""
from __future__ import annotations

import statistics
from typing import Any, Iterable, Optional, Sequence

C2_TYPES = ("C2_CONFIRMED_UP", "C2_CONFIRMED_DOWN")
CISD_TYPES = ("CISD_CONFIRMED_UP", "CISD_CONFIRMED_DOWN")
EARLY_TYPES = ("EARLY_CISD_UP", "EARLY_CISD_DOWN")
TERMINAL_TYPES = ("SETUP_INVALIDATED", "SETUP_EXPIRED", "SETUP_SUPERSEDED", "SETUP_DATA_GAP")

TERMINAL_LABEL_VI = {
    "SETUP_EXTREME_BREACHED": "Thất bại: phá cực trị C2",
    "SETUP_C4_FAIL_AFTER_CISD_IN_C4": "Thất bại: CISD trong C4 rồi C4 không hợp lệ",
    "SETUP_C4_PERIOD_ENDED": "Hết hạn sau C4",
    "SETUP_REPLACED_BY_NEW_C2": "Bị C2 mới cùng hướng thay",
    "SETUP_LTF_GAP": "Dừng do thiếu dữ liệu M15",
}


def _summary(xs: Sequence[float]) -> Optional[dict[str, float]]:
    if not xs:
        return None
    return {
        "n": len(xs),
        "min": round(min(xs), 4),
        "trung_vi": round(float(statistics.median(xs)), 4),
        "trung_binh": round(statistics.fmean(xs), 4),
        "max": round(max(xs), 4),
    }


def _ratio(a: int, b: int) -> Optional[float]:
    return round(a / b, 4) if b else None


def lifecycle_metrics(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    events = list(events)
    setups: dict[str, dict[str, Any]] = {}
    early_events: dict[str, dict[str, Any]] = {}
    n_incomplete = 0
    n_c4_invalid = 0
    for e in events:
        st = e["structure_type"]
        d = e.get("details") or {}
        if st in C2_TYPES:
            setups[d["setup_id"]] = {
                "direction": e["direction"], "cisd": None, "terminal": None,
                "outside": bool(d.get("outside_bar_ambiguous")),
            }
        elif st in CISD_TYPES:
            s = setups.get(d.get("setup_id"))
            if s is not None:
                s["cisd"] = d
        elif st in EARLY_TYPES:
            early_events[e["event_id"]] = e
        elif st == "SETUP_C4_INVALIDATED":
            n_c4_invalid += 1
        elif st == "HTF_BUCKET_INCOMPLETE":
            n_incomplete += 1
        if st in TERMINAL_TYPES:
            s = setups.get(d.get("setup_id"))
            if s is not None:
                s["terminal"] = e["reason_code"]

    by_dir = {"up": 0, "down": 0}
    cisd_dir = {"up": 0, "down": 0}
    cisd_phase = {"C2": 0, "C3": 0, "C4": 0}
    delay_post: list[float] = []
    early_lead: list[float] = []
    early_before_c2 = 0
    terminal_by_reason: dict[str, int] = {}
    censored = 0
    closed = 0
    closed_with_cisd = 0
    consumed_early: set[str] = set()
    for s in setups.values():
        by_dir[s["direction"]] += 1
        c = s["cisd"]
        if c is not None:
            cisd_dir[s["direction"]] += 1
            cisd_phase[c.get("confirm_phase", "C3")] = cisd_phase.get(c.get("confirm_phase", "C3"), 0) + 1
            if c.get("early"):
                early_lead.append(float(c.get("evidence_bars_before_c2_end", 0)))
                if c.get("reclaim_before_c2"):
                    early_before_c2 += 1
                if c.get("early_cisd_event_id"):
                    consumed_early.add(c["early_cisd_event_id"])
            else:
                delay_post.append(float(c.get("delay_bars_from_c2", 0)))
        if s["terminal"] is None:
            censored += 1
        else:
            closed += 1
            closed_with_cisd += 1 if c is not None else 0
            terminal_by_reason[s["terminal"]] = terminal_by_reason.get(s["terminal"], 0) + 1

    n = len(setups)
    n_cisd = sum(cisd_dir.values())
    return {
        "tong_setup": n,
        "so_c2_theo_huong": by_dir,
        "so_c2_outside_bar": sum(1 for s in setups.values() if s["outside"]),
        "so_cisd_xac_nhan_theo_huong": cisd_dir,
        "so_cisd_theo_pha": cisd_phase,
        "ty_le_co_cisd": {
            "tren_moi_setup": _ratio(n_cisd, n),
            "mau_so_moi_setup": n,
            "tren_setup_da_ket_thuc": _ratio(closed_with_cisd, closed),
            "mau_so_da_ket_thuc": closed,
            "ghi_chu_vi": "Tần suất có CISD trong vòng đời setup — KHÔNG phải win rate.",
        },
        "do_tre_cisd_sau_c2_nen": _summary(delay_post),
        "early_cisd": {
            "so_setup_xac_nhan_early": len(early_lead),
            "so_nen_bang_chung_truoc_cuoi_c2": _summary(early_lead),
            "so_reclaim_truoc_ca_ky_c2": early_before_c2,
            "so_su_kien_early_ung_vien": len(early_events),
            "so_ung_vien_khong_thanh_c2": len(set(early_events) - consumed_early),
            "ghi_chu_vi": "Early báo riêng, không gộp với độ trễ sau C2.",
        },
        "ket_thuc_theo_ly_do": terminal_by_reason,
        "ket_thuc_theo_ly_do_vi": {TERMINAL_LABEL_VI.get(k, k): v for k, v in terminal_by_reason.items()},
        "censored_dang_mo": censored,
        "so_c4_khong_hop_le_chua_ket_thuc": n_c4_invalid,
        "so_ky_htf_thieu_nen": n_incomplete,
        "ghi_chu_vi": (
            "Setup chưa kết thúc khi hết dữ liệu là censored — không tính là thất bại "
            "hay hết hạn. Setup dừng vì thiếu dữ liệu không phải bị giá phá."
        ),
    }


def excursion_metrics(
    events: Iterable[dict[str, Any]], bars: Sequence[Any], horizon_bars: int, ltf_seconds: int = 900,
) -> dict[str, Any]:
    """MFE/MAE trong ``horizon_bars`` nến SAU nến biết sự kiện.

    Nhóm ``c2_only``: neo tại nến C2 được biết (close nến cuối C2).
    Nhóm ``c2_cisd``: chỉ setup có CISD, neo tại nến CISD được biết.
    Giá vào tham chiếu = close nến neo. MFE/MAE theo đơn vị giá, luôn ≥ 0.
    """
    if horizon_bars < 1:
        raise ValueError("horizon phải >= 1 nến.")
    by_index = {b.index: b for b in bars}
    c2_anchor: dict[str, tuple[int, str]] = {}
    cisd_anchor: dict[str, tuple[int, str]] = {}
    for e in events:
        d = e.get("details") or {}
        if e["structure_type"] in C2_TYPES:
            c2_anchor[d["setup_id"]] = (e["confirmed_bar_index"], e["direction"])
        elif e["structure_type"] in CISD_TYPES and d.get("setup_id"):
            cisd_anchor[d["setup_id"]] = (e["confirmed_bar_index"], e["direction"])

    def one(anchor: int, direction: str) -> Optional[tuple[float, float]]:
        a = by_index.get(anchor)
        if a is None:
            return None
        window = []
        prev = a
        for k in range(1, horizon_bars + 1):
            b = by_index.get(anchor + k)
            if b is None or (b.close_time - prev.close_time).total_seconds() != ltf_seconds:
                return None
            window.append(b)
            prev = b
        entry = a.close
        if direction == "up":
            mfe = max(b.high for b in window) - entry
            mae = entry - min(b.low for b in window)
        else:
            mfe = entry - min(b.low for b in window)
            mae = max(b.high for b in window) - entry
        return max(mfe, 0.0), max(mae, 0.0)

    def group(anchors: dict[str, tuple[int, str]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for d in ("up", "down", "tat_ca"):
            mfes, maes, skipped = [], [], 0
            for anchor, direction in anchors.values():
                if d != "tat_ca" and direction != d:
                    continue
                r = one(anchor, direction)
                if r is None:
                    skipped += 1
                    continue
                mfes.append(r[0])
                maes.append(r[1])
            out[d] = {
                "so_mau": len(mfes),
                "so_mau_bo_thieu_horizon": skipped,
                "mfe": _summary(mfes),
                "mae": _summary(maes),
                "so_mau_mfe_lon_hon_mae": sum(1 for x, y in zip(mfes, maes) if x > y),
            }
        return out

    return {
        "horizon_nen": horizon_bars,
        "c2_only": group(c2_anchor),
        "c2_cisd": group(cisd_anchor),
        "ghi_chu_vi": (
            "Dùng nến SAU thời điểm biết, chỉ để đánh giá. Giá tham chiếu = close nến "
            "neo; không có phí/spread/khớp lệnh — không phải kết quả giao dịch. Bỏ mẫu "
            "thiếu đủ horizon (hết dữ liệu hoặc gap thời gian)."
        ),
    }
