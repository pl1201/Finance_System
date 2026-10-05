"""Chuẩn ngẫu nhiên khi đánh giá (core/eval/null_baseline.py) — ca tính tay, tất định, không đổi số thật."""
from __future__ import annotations

import copy
import random
from datetime import datetime, timedelta, timezone

import pytest

from core.eval.evaluate import evaluate_runs, score_one_run
from core.eval.matcher import match_labels
from core.eval.null_baseline import NullWindow, _count_tp, _ny_hour, _sample, null_baseline
from core.eval.protocol import MATCHER_GREEDY_LABEL_ORDER_V1, MATCHER_MIN_COST_V1, EvalProtocol
from core.labels import ReferenceLabel
from tests.helpers import make_bars


def _ohlc(n):
    out = []
    for i in range(n):
        o = 100.0 + 0.1 * i
        out.append((o, o + 1.0 + 0.01 * (i % 7), o - 1.0 - 0.01 * (i % 5), o + 0.3))
    return out


def _run(bars, idxs, rid="r1", price="high"):
    evs = []
    for k, i in enumerate(idxs):
        b = bars[i]
        evs.append({
            "event_id": "%s:e%d" % (rid, k), "structure_type": "SWING_HIGH", "event_bar_index": i,
            "confirmed_bar_index": i + 1, "confirmation_lag_bars": 1, "price": getattr(b, price),
        })
    return {"run_id": rid, "dataset_id": "ds", "events": evs, "bars_processed": len(bars), "warmup_bars": 0,
            "timeframe": "H1", "symbol": "X"}


def _proto(**kw):
    base = {"target": "swing_nho", "time_tolerance_bars": 0, "price_tolerance": 0, "null_mode": "uniform_v1",
            "null_n": 1000, "null_seed": 1}
    base.update(kw)
    return EvalProtocol.from_dict(base)


def _label(bars, i, seq=0, price="high"):
    return ReferenceLabel("SWING_HIGH", i, getattr(bars[i], price), seq=seq)


def test_cua_so_mot_nen_luon_trung():
    bars = make_bars(_ohlc(10))
    # xác nhận ở nến 5 > nến cuối khoảng chấm → phải tắt quy tắc «bỏ đuôi chưa xác nhận» để giữ sự kiện
    out = score_one_run(_run(bars, [4]), labels=[_label(bars, 4)], bars=bars,
                        protocol=_proto(null_n=50, coverage_start_index=4, coverage_end_index=4,
                                        exclude_unconfirmed_tail=False))
    nb = out["null_baseline"]
    assert nb["status"] == "ok" and nb["eligible_bars"] == 1
    assert nb["f1"]["mean"] == 1.0 and nb["f1"]["p5"] == 1.0
    assert nb["n_ge_real"] == 50 and nb["p_ge"] == pytest.approx(1.0)


@pytest.mark.parametrize("tol_bars,tol_price,expected", [
    (0, 0, 0.1),        # 1/10 nến trúng
    (1, 1e9, 0.3),      # nến 3, 4, 5 đều ghép được khi không xét giá
    (1, 0, 0.1),        # nến 3, 5 lệch giá high → chỉ nến 4
])
def test_mot_nhan_mot_su_kien_tren_10_nen(tol_bars, tol_price, expected):
    bars = make_bars(_ohlc(10))
    out = score_one_run(
        _run(bars, [4]), labels=[_label(bars, 4)], bars=bars,
        protocol=_proto(time_tolerance_bars=tol_bars, price_tolerance=tol_price, coverage_start_index=0,
                        coverage_end_index=9, exclude_unconfirmed_tail=False),
    )
    nb = out["null_baseline"]
    assert nb["status"] == "ok" and nb["eligible_bars"] == 10 and nb["price_rule"] == {"SWING_HIGH": "high"}
    se = (expected * (1 - expected) / 1000) ** 0.5
    assert abs(nb["f1"]["mean"] - expected) < 4 * se          # F1 lượt = 1 nếu trúng, 0 nếu trượt


def test_nhan_theo_close_su_kien_theo_high_luon_0_khong_phai_none():
    bars = make_bars(_ohlc(10))
    out = score_one_run(_run(bars, [4]), labels=[_label(bars, 4, price="close")], bars=bars,
                        protocol=_proto(null_n=100, coverage_start_index=0, coverage_end_index=9))
    nb = out["null_baseline"]
    assert out["quality"]["f1"] is None                       # thực tế: TP 0
    assert nb["f1"]["mean"] == 0.0 and nb["f1"]["p95"] == 0.0  # mỗi lượt F1 = 0, không phải None
    assert nb["n_ge_real"] == 100                              # thực tế tính là 0 khi so


def test_khong_suy_duoc_quy_tac_gia_thi_khong_ap_dung():
    bars = make_bars(_ohlc(10))
    run = _run(bars, [4])
    run["events"][0]["price"] = 12345.0                        # vd một mức tính ra, không phải OHLC
    out = score_one_run(run, labels=[_label(bars, 4)], bars=bars, protocol=_proto(null_n=20))
    assert out["null_baseline"]["status"] == "khong_ap_dung"
    assert "SWING_HIGH" in out["null_baseline"]["note_vi"]


def test_chua_co_nhan():
    bars = make_bars(_ohlc(10))
    out = score_one_run(_run(bars, [4]), labels=[], bars=bars, protocol=_proto(null_n=20))
    assert out["null_baseline"]["status"] == "chua_co_nhan"
    assert "f1" not in out["null_baseline"]


def test_vuot_gioi_han_khoi_luong():
    p = _proto(null_n=1000)
    ev = [{"event_id": str(i), "structure_type": "SWING_HIGH", "event_bar_index": i, "price": 1.0} for i in range(2000)]
    lb = [ReferenceLabel("SWING_HIGH", i, 1.0, seq=i) for i in range(2000)]
    with pytest.raises(ValueError, match="quá nặng"):
        null_baseline([NullWindow(0, 1999, ev, lb)], bars=[], offset=0, protocol=p, rule_events=ev,
                      real={"tp": 0, "fp": 0, "fn": 0, "precision": None, "recall": None, "f1": None})


def test_bat_chuan_ngau_nhien_khong_doi_so_cua_run_that():
    bars = make_bars(_ohlc(60))
    labels = [_label(bars, i, seq=k) for k, i in enumerate((5, 12, 20, 33, 47))]
    run = _run(bars, [5, 13, 20, 30, 47, 55])
    run_copy, labels_copy = copy.deepcopy(run), copy.deepcopy(labels)
    off = score_one_run(run, labels=labels, bars=bars, protocol=_proto(null_mode="off", time_tolerance_bars=1))
    on = score_one_run(run, labels=labels, bars=bars, protocol=_proto(null_n=50, time_tolerance_bars=1))
    assert run == run_copy and labels == labels_copy            # không sửa đầu vào
    for d in (off, on):
        d["performance"].pop("evaluation_ms")
    on.pop("null_baseline")
    assert on == off


def test_tat_dinh_theo_seed_va_doc_lap_voi_cac_run_khac():
    bars = make_bars(_ohlc(60))
    labels = [_label(bars, i, seq=k) for k, i in enumerate((5, 12, 20, 33, 47))]
    a, b = _run(bars, [5, 13, 20, 30, 47], "A"), _run(bars, [6, 7, 8, 40], "B")
    p = _proto(null_n=40, time_tolerance_bars=1)
    one = score_one_run(a, labels=labels, bars=bars, protocol=p)["null_baseline"]
    again = score_one_run(a, labels=labels, bars=bars, protocol=p)["null_baseline"]
    assert one == again
    res = evaluate_runs([b, a], protocol=p, labels=labels, bars_by_run={"A": bars, "B": bars})
    a_in_group = next(r for g in res["groups"] for r in g["runs"] if r["run_id"] == "A")
    assert a_in_group["null_baseline"] == one                   # thêm / đổi thứ tự run không đổi null của A
    assert _sample(list(range(100)), 10, "1|x") != _sample(list(range(100)), 10, "2|x")


def test_lay_mau_khong_lap_trong_tap_va_tat_dinh():
    pool = list(range(10, 60))
    s1 = _sample(pool, 20, "k")
    assert s1 == _sample(pool, 20, "k")
    assert len(set(s1)) == 20 and set(s1) <= set(pool)
    assert sorted(_sample(pool, 999, "k")) == pool              # k > n → lấy hết


def test_gio_new_york_theo_doi_gio_mua_he():
    utc = timezone.utc
    assert _ny_hour(datetime(2024, 3, 10, 6, tzinfo=utc)) == 1    # còn EST (UTC−5)
    assert _ny_hour(datetime(2024, 3, 10, 7, tzinfo=utc)) == 3    # sang EDT, nhảy qua 02:00
    assert _ny_hour(datetime(2024, 11, 3, 5, tzinfo=utc)) == 1    # EDT
    assert _ny_hour(datetime(2024, 11, 3, 6, tzinfo=utc)) == 1    # về EST, 01:00 lặp lại


def test_ghep_cap_chi_dat_su_kien_vao_cung_gio_new_york():
    # 3 ngày nến H1 từ 02/01/2024 (EST): 08:00 New York = 13:00 UTC → nến 13, 37, 61.
    start = datetime(2024, 1, 2, tzinfo=timezone.utc)
    bars = make_bars(_ohlc(72), start=start)
    hour8 = [i for i in range(72) if _ny_hour(start + timedelta(hours=i)) == 8]
    assert hour8 == [13, 37, 61]
    labels = [_label(bars, i, seq=k) for k, i in enumerate(hour8)]
    run = _run(bars, [13, 37])
    kw = dict(time_tolerance_bars=0, price_tolerance=1e9, null_n=200, exclude_unconfirmed_tail=False)
    matched = score_one_run(run, labels=labels, bars=bars, protocol=_proto(null_mode="matched_hour_atr_v1", **kw))
    uniform = score_one_run(run, labels=labels, bars=bars, protocol=_proto(null_mode="uniform_v1", **kw))
    nm, nu = matched["null_baseline"], uniform["null_baseline"]
    # mọi nến 08:00 NY đều có nhãn → sự kiện ngẫu nhiên ghép cặp luôn trúng
    assert nm["precision"]["mean"] == 1.0 and nm["precision"]["p5"] == 1.0
    assert nm["strata"]["n_strata"] >= 1
    assert nu["precision"]["mean"] < 0.3                        # rải đồng đều: hiếm khi trúng giờ 08:00


@pytest.mark.parametrize("matcher", [MATCHER_MIN_COST_V1, MATCHER_GREEDY_LABEL_ORDER_V1])
def test_tach_cum_cho_dung_so_tp_nhu_matcher_goc(matcher):
    rng = random.Random(7)
    for _ in range(300):
        tol = rng.choice([0, 1, 2, 3])
        ptol = rng.choice([0.0, 0.5, 1e9])
        types = ("SWING_HIGH", "SWING_LOW")
        labels = [ReferenceLabel(rng.choice(types), rng.randrange(40), float(rng.randrange(3)), seq=k)
                  for k in range(rng.randrange(0, 12))]
        events = [{"event_id": "e%d" % j, "structure_type": rng.choice(types), "event_bar_index": rng.randrange(40),
                   "price": float(rng.randrange(3))} for j in range(rng.randrange(0, 12))]
        events.sort(key=lambda e: (e["event_bar_index"], e["structure_type"]))
        p = EvalProtocol.from_dict({"target": "swing_nho", "time_tolerance_bars": tol, "price_tolerance": ptol,
                                    "matcher_version": matcher})
        full = len(match_labels(labels, events, time_tolerance_bars=tol, price_tolerance=ptol,
                                matcher_version=matcher).matches)
        assert _count_tp(labels, events, p) == full
