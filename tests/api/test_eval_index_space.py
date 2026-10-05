"""Không gian chỉ số khi chấm: nhãn đếm nến từ đầu dataset, run chạy khoảng con đếm từ nến đầu run.

Lỗi cũ (có từ trước refactor 10/2026): run bắt đầu sau nến 0 bị chấm lệch đúng ``range_start_index``
nến — cùng các pivot với run cả dataset nhưng recall 0. Nay chấm theo chỉ số dataset.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from core.eval.evaluate import _n_scorable_bars
from core.eval.protocol import EvalProtocol

client = TestClient(app)

PIVOTS = ("SWING_HIGH", "SWING_LOW")


def _dataset():
    client.post("/api/datasets/seed-samples")
    ds = [d for d in client.get("/api/datasets").json() if d["symbol"] == "XAUUSD" and d["timeframe"] == "H1"]
    assert ds
    did = ds[0]["id"]
    bars = client.get("/api/datasets/%s/bars" % did).json()["bars"]
    return did, bars


def _run(did, **kw):
    body = {"dataset_id": did, "algorithm": "swing_pivot", "params": {"left": 3, "right": 3}, "save": True}
    body.update(kw)
    r = client.post("/api/runs", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _labels_from(run, lo, hi):
    return [
        {"structure_type": e["structure_type"], "bar_index": e["event_bar_index"], "price": e["price"]}
        for e in run["events"]
        if e["structure_type"] in PIVOTS and lo <= e["event_bar_index"] <= hi
    ]


def _setup():
    did, bars = _dataset()
    full = _run(did)
    sub = _run(did, range_start=bars[600]["bar_time"], range_end=bars[1200]["bar_time"])
    assert full["range_start_index"] == 0 and sub["range_start_index"] == 600
    labels = _labels_from(full, 700, 1100)   # run cả dataset: chỉ số run = chỉ số dataset
    assert len(labels) >= 10
    ls = client.post("/api/label-sets", json={
        "dataset_id": did, "annotator": "kiem tra", "version": "1",
        "rubric_vi": "Pivot 3/3 của run cả dataset — kiểm tra không gian chỉ số.", "labels": labels,
    })
    assert ls.status_code == 200, ls.text
    return did, bars, full, sub, labels, ls.json()["id"]


def test_run_khoang_con_cham_nhu_run_ca_dataset():
    _did, _bars, full, sub, labels, ls_id = _setup()
    # cùng pivot theo thời điểm (khoảng 700..1100 nằm xa biên của run con nên không vướng warm-up)
    t_lab = {(e["structure_type"], e["event_time"]) for e in full["events"]
             if e["structure_type"] in PIVOTS and 700 <= e["event_bar_index"] <= 1100}
    t_sub = {(e["structure_type"], e["event_time"]) for e in sub["events"] if e["structure_type"] in PIVOTS}
    assert t_lab <= t_sub
    out = client.post("/api/evaluations", json={
        "run_ids": [full["run_id"], sub["run_id"]], "label_set_id": ls_id, "save": False,
        "protocol": {"target": "swing_nho", "matcher_version": "min_cost_v1", "time_tolerance_bars": 0,
                     "price_tolerance": 0, "coverage_start_index": 700, "coverage_end_index": 1100},
    })
    assert out.status_code == 200, out.text
    runs = {r["run_id"]: r for g in out.json()["groups"] for r in g.get("runs", [])}
    for rid in (full["run_id"], sub["run_id"]):
        q = runs[rid]["quality"]
        assert q["true_positives"] == len(labels), (rid, q)
        assert q["false_negatives"] == 0 and q["false_positives"] == 0, (rid, q)
        assert q["f1"] == 1.0
    # TP của run con mang chỉ số dataset (trùng nhãn), không phải chỉ số tính từ nến đầu run
    tp_bars = sorted(m["event_bar_index"] for m in runs[sub["run_id"]]["matches"])
    assert tp_bars == sorted(lb["bar_index"] for lb in labels)
    # cùng khoảng chấm → cùng số nến chấm được
    assert runs[sub["run_id"]]["density"]["n_scorable_bars"] == runs[full["run_id"]]["density"]["n_scorable_bars"] == 401


def test_doi_chieu_nhan_o_trang_thu_nghiem_run_khoang_con():
    _did, _bars, _full, sub, labels, ls_id = _setup()
    r = client.post("/api/evaluate", json={
        "run_id": sub["run_id"], "label_set_id": ls_id, "time_tolerance_bars": 0, "price_tolerance": 0,
    })
    assert r.status_code == 200, r.text
    ev = r.json()
    assert ev["true_positives"] == len(labels)
    assert ev["false_negatives"] == 0


def test_nen_tra_kem_chi_so_dataset():
    did, bars = _dataset()
    assert all(b["dataset_index"] == b["index"] for b in bars)   # cả dataset: hai chỉ số trùng
    part = client.get("/api/datasets/%s/bars" % did,
                      params={"start": bars[600]["bar_time"], "end": bars[700]["bar_time"]}).json()["bars"]
    assert part[0]["index"] == 0 and part[0]["dataset_index"] == 600
    assert part[-1]["index"] == 100 and part[-1]["dataset_index"] == 700
    rp = client.post("/api/replay", json={
        "dataset_id": did, "algorithm": "swing_pivot", "params": {"left": 3, "right": 3},
        "range_start": bars[600]["bar_time"], "range_end": bars[700]["bar_time"],
    })
    assert rp.status_code == 200, rp.text
    sid = rp.json()["session_id"]
    rb = client.get("/api/replay/%s/bars" % sid).json()["bars"]
    assert rb[0]["index"] == 0 and rb[0]["dataset_index"] == 600


def test_so_nen_cham_duoc_theo_chi_so_dataset():
    p = EvalProtocol.from_dict({"target": "swing_nho", "coverage_start_index": 120, "coverage_end_index": 200})
    run = {"range_start_index": 100, "bars_processed": 50, "warmup_bars": 5}
    assert _n_scorable_bars(run, p) == 30          # [120, 149]
    p_all = EvalProtocol.from_dict({"target": "swing_nho"})
    assert _n_scorable_bars(run, p_all) == 46      # [100 + 4, 149]
    assert _n_scorable_bars({"bars_processed": 50, "warmup_bars": 5}, p_all) == 46   # run từ nến 0: như cũ
