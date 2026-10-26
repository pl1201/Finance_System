"""Trợ giúp cho bộ tài liệu học quant (`docs/hoc_quant/`): nạp nến và chạy thuật toán của lab — CHỈ ĐỌC database.

Dùng trong bài tập (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe
    >>> import sys; sys.path.insert(0, "research/hoc_quant")
    >>> from hoc import *
    >>> df = nap_nen(XAU_M15, "2024-01-01", "2024-09-01")
    >>> df.head()

Luật giữ nguyên như lab:

* mở ``data/lab.sqlite`` ở chế độ chỉ đọc (``mode=ro``) — bài tập không thể sửa dữ liệu, run hay nhãn;
* **đoạn kiểm tra khoá**: mọi khoảng chạm từ 2024-09-01 trở đi bị từ chối, trừ khi truyền ``mo_doan_kiem_tra=True``
  (bài tập không bao giờ cần);
* thời gian là UTC; nến đã đóng; thứ tự theo ``idx``.

Biến môi trường ``MSL_DB_PATH`` (nếu có) đổi đường dẫn database — vd trỏ vào một bản sao.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import warnings
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DB_PATH = os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite")
DOAN_KIEM_TRA = "2024-09-01"   # đoạn kiểm tra của lab bắt đầu từ đây (AGENTS.md §6.3) — không dùng để học / chọn tham số

# Dataset hay dùng (giá Bid HistData, giờ đã sửa). Bộ ghi «LỆCH GIỜ» và «MÔ PHỎNG» trong DB: KHÔNG dùng.
XAU_M1 = "ds_0d44e89df5fd"        # XAUUSD M1 2024
# M1 từng năm (mỗi năm một dataset): XAU_M1_NAM[2018] … XAU_M1_NAM[2024]; EURUSD tương tự
XAU_M1_NAM = {2018: "ds_ef510eb77ea7", 2019: "ds_c48463e3c905", 2020: "ds_0738ef2ade75", 2021: "ds_0866d7660d81",
              2022: "ds_96f52ae16db4", 2023: "ds_0dea7c8ebb18", 2024: "ds_0d44e89df5fd"}
EUR_M1_NAM = {2018: "ds_056876879fa1", 2019: "ds_4a0fea697508", 2020: "ds_8f479b72086e", 2021: "ds_084a261f98aa",
              2022: "ds_6ac1a1a5f4c0", 2023: "ds_4ee0d2b0c434", 2024: "ds_01e4988cab6f"}
XAU_M5 = "ds_933fa5ec67e2"        # XAUUSD M5 2024
XAU_M5_2018 = "ds_c962af6036a4"   # XAUUSD M5 2018–2021
XAU_M5_2022 = "ds_4624bac8a089"   # XAUUSD M5 2022–2025
XAU_M15 = "ds_db1583cd4dde"       # XAUUSD M15 2024 (dataset chính của lab)
XAU_M15_DAI = "ds_a5212fd37814"   # XAUUSD M15 2018–2025
XAU_H1 = "ds_83abaa3c6eab"        # XAUUSD H1 2018–2025
XAU_H4 = "ds_2c79dddcd829"        # XAUUSD H4 2018–2025 (mốc 17:00 New York)
XAU_D1 = "ds_ba2c0dbea8c0"        # XAUUSD D1 2018–2025 (mốc 17:00 New York)
EUR_M15_DAI = "ds_a9a2a5e4cef5"   # EURUSD M15 2018–2025
EUR_M5_2018 = "ds_a34c46a44233"   # EURUSD M5 2018–2021
EUR_M5_2022 = "ds_17ffe8e4b74d"   # EURUSD M5 2022–2025
EUR_H1 = "ds_ab9f7729cb17"        # EURUSD H1 2018–2025
EUR_H4 = "ds_8e87b4f82dfe"        # EURUSD H4 2018–2025 (mốc 17:00 New York)
EUR_D1 = "ds_370f222212a9"        # EURUSD D1 2018–2025

__all__ = [
    "DB_PATH", "DOAN_KIEM_TRA", "XAU_M1", "XAU_M1_NAM", "EUR_M1_NAM", "XAU_M5", "XAU_M15", "XAU_M15_DAI", "XAU_H1", "XAU_H4", "XAU_D1",
    "EUR_M15_DAI", "EUR_H1", "EUR_D1", "XAU_M5_2018", "XAU_M5_2022", "EUR_M5_2018", "EUR_M5_2022",
    "EUR_H4", "ket_noi", "danh_sach_dataset", "nap_nen", "chay_thuat_toan", "chay_tren_df",
    "nen_tu_gia", "np", "pd",
]


def ket_noi() -> sqlite3.Connection:
    """Kết nối CHỈ ĐỌC tới database của lab."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError("Không thấy database: %s" % DB_PATH)
    return sqlite3.connect("file:%s?mode=ro" % DB_PATH.replace("\\", "/"), uri=True)


def _kiem_khoang(tu: str, den: str, mo_doan_kiem_tra: bool) -> None:
    if pd.Timestamp(den, tz="UTC") > pd.Timestamp(DOAN_KIEM_TRA, tz="UTC") and not mo_doan_kiem_tra:
        raise ValueError("Khoảng %s → %s chạm đoạn kiểm tra (từ %s). Bài tập chỉ dùng đoạn phát triển; "
                         "đổi «den» thành «%s» hoặc sớm hơn." % (tu, den, DOAN_KIEM_TRA, DOAN_KIEM_TRA))


def danh_sach_dataset() -> pd.DataFrame:
    """Mọi dataset trong DB: id, mã, khung, tên, số nến, khoảng thời gian, loại giá, có phải mô phỏng không."""
    with ket_noi() as con:
        return pd.read_sql_query(
            "select id, symbol as ma, timeframe as khung, name as ten, row_count as so_nen, "
            "substr(start_time,1,10) as tu, substr(end_time,1,10) as den, price_type as loai_gia, is_synthetic as mo_phong "
            "from datasets order by symbol, timeframe, start_time", con)


def nap_nen(dataset: str, tu: str, den: str, mo_doan_kiem_tra: bool = False) -> pd.DataFrame:
    """Nến của ``dataset`` trong ``[tu, den)`` (chuỗi ngày ``YYYY-MM-DD`` hoặc ISO, UTC).

    Trả DataFrame index = thời gian mở nến (UTC), cột ``open high low close volume idx``.
    ``volume`` của HistData luôn là 0 (nguồn đã bỏ volume).
    """
    _kiem_khoang(tu, den, mo_doan_kiem_tra)
    with ket_noi() as con:
        ten = (con.execute("select name from datasets where id=?", (dataset,)).fetchone() or [""])[0]
        if "LỆCH GIỜ" in ten or "MÔ PHỎNG" in ten:
            warnings.warn("Dataset %s là bộ «%s» — chỉ dùng làm ví dụ dữ liệu xấu / thử giao diện, không dùng để phân tích."
                          % (dataset, "LỆCH GIỜ" if "LỆCH GIỜ" in ten else "MÔ PHỎNG"), stacklevel=2)
        df = pd.read_sql_query(
            "select idx, bar_time, open, high, low, close, volume from bars "
            "where dataset_id=? and bar_time>=? and bar_time<? order by idx", con, params=(dataset, tu, den))
    if df.empty:
        raise ValueError("Không có nến nào: dataset %s, %s → %s" % (dataset, tu, den))
    df["bar_time"] = pd.to_datetime(df["bar_time"], utc=True)
    return df.set_index("bar_time")


def _tham_so_mac_dinh(ten: str, tham_so: dict[str, Any] | None, khung: str, lich: str) -> dict[str, Any]:
    """Tự điền ``timeframe`` / ``session_calendar`` cho thuật toán nào có hai tham số đó (người học không phải nhớ)."""
    from core.registry import get_algorithm_class

    p = dict(tham_so or {})
    co = {s.name for s in get_algorithm_class(ten).param_specs()}
    if "timeframe" in co:
        p.setdefault("timeframe", khung)
    if "session_calendar" in co:
        p.setdefault("session_calendar", lich)
    return p


def chay_thuat_toan(ten: str, dataset: str, tu: str, den: str, tham_so: dict[str, Any] | None = None,
                    mo_doan_kiem_tra: bool = False) -> dict[str, Any]:
    """Chạy thuật toán ``ten`` của lab (vd ``"ict_structure"``, ``"dc_atr_structure"``, ``"swing_pivot"``) nhân quả trên
    khoảng ``[tu, den)``, KHÔNG lưu gì vào DB.

    Trả dict: ``su_kien`` (DataFrame mỗi dòng một sự kiện), ``timeline`` (DataFrame trạng thái sau mỗi nến), ``ket_qua``
    (RunResult gốc), ``nen`` (danh sách Bar của lab). Thống kê thuật toán tự tính (vd tỷ lệ thời gian order flow của
    ``ict_structure``) nằm ở ``ket_qua.stats["chi_so_thuat_toan"]``.
    """
    from core.engine import run_algorithm
    from core.registry import create_algorithm
    from core.types import build_bars

    _kiem_khoang(tu, den, mo_doan_kiem_tra)
    with ket_noi() as con:
        tf, conv, sym = con.execute("select timeframe, timestamp_convention, symbol from datasets where id=?",
                                    (dataset,)).fetchone()
        rows = [{"bar_time": datetime.fromisoformat(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4],
                 "volume": r[5]}
                for r in con.execute("select bar_time, open, high, low, close, volume from bars where dataset_id=? and "
                                     "bar_time>=? and bar_time<? order by idx", (dataset, tu, den))]
    bars = build_bars(rows, tf, conv)
    p = _tham_so_mac_dinh(ten, tham_so, tf, "cme_globex_metals" if sym == "XAUUSD" else "fx_spot")
    res = run_algorithm(bars, create_algorithm(ten, p))
    ev = pd.DataFrame([e.to_dict() for e in res.events])
    tl = pd.DataFrame(res.timeline)
    return {"su_kien": ev, "timeline": tl, "ket_qua": res, "nen": bars}


def chay_tren_df(ten: str, df: pd.DataFrame, khung: str = "M15", tham_so: dict[str, Any] | None = None,
                 lich_phien: str = "none") -> dict[str, Any]:
    """Chạy thuật toán ``ten`` trên một DataFrame nến TỰ TẠO (vd chuỗi mô phỏng bước ngẫu nhiên).

    ``df``: index là thời gian mở nến (UTC, tăng dần, đúng bước ``khung``), cột ``open high low close`` (``volume`` tuỳ ý).
    ``lich_phien``: ``"none"`` cho dữ liệu mô phỏng chạy liên tục (không có phiên); dữ liệu thật dùng ``chay_thuat_toan``.
    Trả cùng dạng với ``chay_thuat_toan``.
    """
    from core.engine import run_algorithm
    from core.registry import create_algorithm
    from core.types import build_bars

    rows = [{"bar_time": t.to_pydatetime(), "open": float(r.open), "high": float(r.high), "low": float(r.low),
             "close": float(r.close), "volume": float(getattr(r, "volume", 0.0) or 0.0)}
            for t, r in df.iterrows()]
    bars = build_bars(rows, khung, "open")
    p = _tham_so_mac_dinh(ten, tham_so, khung, lich_phien)
    res = run_algorithm(bars, create_algorithm(ten, p))
    return {"su_kien": pd.DataFrame([e.to_dict() for e in res.events]), "timeline": pd.DataFrame(res.timeline),
            "ket_qua": res, "nen": bars}


def nen_tu_gia(gia: np.ndarray, bat_dau: str = "2024-01-01", khung_phut: int = 15, so_tick_moi_nen: int = 15) -> pd.DataFrame:
    """Dựng nến OHLC từ một chuỗi giá «tick» liên tục (vd bước ngẫu nhiên): mỗi nến gom ``so_tick_moi_nen`` giá liên tiếp.

    ``len(gia)`` phải chia hết cho ``so_tick_moi_nen``. Index bắt đầu ``bat_dau`` (UTC), cách nhau ``khung_phut`` phút.
    """
    g = np.asarray(gia, dtype=float)
    n = len(g) // so_tick_moi_nen
    g = g[: n * so_tick_moi_nen].reshape(n, so_tick_moi_nen)
    idx = pd.date_range(bat_dau, periods=n, freq="%dmin" % khung_phut, tz="UTC")
    return pd.DataFrame({"open": g[:, 0], "high": g.max(axis=1), "low": g.min(axis=1), "close": g[:, -1], "volume": 0.0},
                        index=idx)


if __name__ == "__main__":
    pd.set_option("display.width", 160)
    print(danh_sach_dataset().to_string(index=False))
