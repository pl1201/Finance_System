"""Test tính nhân quả và tính nhất quán của replay.

Đây là nhóm test quan trọng nhất của công cụ: nếu thuật toán nhìn thấy dữ
liệu tương lai thì mọi kết quả nghiên cứu phía sau đều vô nghĩa.
"""
from __future__ import annotations

import pytest

from core.algorithms.swing_pivot import SwingPivotAlgorithm
from core.data.synthetic import SyntheticSpec, generate
from core.engine import ReplaySession, run_algorithm
from core.types import build_bars
from tests.helpers import signature


@pytest.fixture(scope="module")
def bars():
    res = generate(SyntheticSpec(symbol="XAUUSD", timeframe="H1", bars=420, seed=7))
    return build_bars(res["rows"], "H1", "open")


def algo(**kw):
    params = dict(left=3, right=3)
    params.update(kw)
    return SwingPivotAlgorithm(**params)


# ---------------------------------------------------------------------------
# Dữ liệu sau T không được đổi sự kiện đã xác nhận tại T
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cut", [50, 120, 200, 333])
def test_them_du_lieu_sau_T_khong_doi_su_kien_da_xac_nhan_tai_T(bars, cut):
    prefix_events = run_algorithm(bars[:cut], algo()).events
    full_events = run_algorithm(bars, algo()).events
    full_upto_cut = [e for e in full_events if e.confirmed_bar_index < cut]
    assert signature(prefix_events) == signature(full_upto_cut)


def test_sua_du_lieu_sau_T_khong_doi_su_kien_da_xac_nhan_tai_T(bars):
    cut = 200
    base = [e for e in run_algorithm(bars, algo()).events if e.confirmed_bar_index < cut]

    # Thay toàn bộ phần đuôi bằng một chuỗi khác hẳn.
    from dataclasses import replace

    tampered = list(bars[:cut])
    for i, b in enumerate(bars[cut:], start=cut):
        tampered.append(
            replace(b, open=b.open * 2, high=b.high * 2 + 5, low=b.low * 2 - 5, close=b.close * 2)
        )
    after = [e for e in run_algorithm(tampered, algo()).events if e.confirmed_bar_index < cut]
    assert signature(base) == signature(after)


def test_khong_su_kien_nao_xac_nhan_truoc_khi_du_thong_tin(bars):
    """confirmed_bar_index luôn >= event_bar_index + right cho pivot."""
    events = run_algorithm(bars, algo(left=3, right=3)).events
    for e in events:
        if e.structure_type in ("SWING_HIGH", "SWING_LOW"):
            assert e.confirmed_bar_index == e.event_bar_index + 3
        assert e.confirmed_bar_index >= e.event_bar_index


# ---------------------------------------------------------------------------
# ReplaySession: tiến / lùi / reset
# ---------------------------------------------------------------------------


def test_replay_tien_tung_nen_cho_ket_qua_bang_chay_toan_bo(bars):
    session = ReplaySession(bars, algo())
    session.step_forward(len(bars))
    full = run_algorithm(bars, algo()).events
    assert signature(session.events) == signature(full)


@pytest.mark.parametrize("cursor", [0, 10, 99, 250, 419])
def test_replay_seek_bang_chay_prefix(bars, cursor):
    session = ReplaySession(bars, algo())
    session.seek(cursor)
    prefix = run_algorithm(bars, algo(), upto_index=cursor).events
    assert signature(session.events) == signature(prefix)
    assert all(e.confirmed_bar_index <= cursor for e in session.events)


def test_replay_lui_roi_tien_lai_cho_ket_qua_nhat_quan(bars):
    session = ReplaySession(bars, algo())
    session.seek(250)
    snapshot_250 = signature(session.events)

    session.step_forward(80)
    assert len(session.events) >= len(snapshot_250)

    session.step_back(80)
    assert session.cursor == 250
    assert signature(session.events) == snapshot_250

    session.step_forward(80)
    session.seek(250)
    assert signature(session.events) == snapshot_250


def test_replay_reset_ve_trang_thai_rong(bars):
    session = ReplaySession(bars, algo())
    session.step_forward(150)
    assert session.events
    session.reset()
    assert session.cursor == -1
    assert session.events == []
    snap = session.snapshot()
    assert snap["bars_loaded"] == 0
    assert snap["data_status"] == "WARMUP_INSUFFICIENT"

    session.step_forward(150)
    again = signature(session.events)
    fresh = ReplaySession(bars, algo())
    fresh.step_forward(150)
    assert again == signature(fresh.events)


def test_replay_khong_vuot_qua_cuoi_du_lieu(bars):
    session = ReplaySession(bars, algo())
    session.step_forward(len(bars) + 500)
    assert session.cursor == len(bars) - 1
    session.step_forward(10)
    assert session.cursor == len(bars) - 1


def test_replay_lui_qua_dau_du_lieu(bars):
    session = ReplaySession(bars, algo())
    session.step_forward(5)
    session.step_back(50)
    assert session.cursor == -1
    assert session.events == []


def test_replay_timeline_chi_den_con_tro(bars):
    session = ReplaySession(bars, algo())
    session.seek(120)
    snap = session.snapshot()
    assert len(snap["timeline"]) == 121
    assert max(p["bar_index"] for p in snap["timeline"]) == 120


def test_chay_lai_cung_du_lieu_cho_ket_qua_tat_dinh(bars):
    a = run_algorithm(bars, algo()).events
    b = run_algorithm(bars, algo()).events
    assert signature(a) == signature(b)
    assert [e.event_id for e in a] == [e.event_id for e in b]
