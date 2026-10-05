"""API đánh giá: chuẩn ngẫu nhiên + đoạn phát triển / kiểm tra (khoá đoạn kiểm tra mặc định)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

PIVOTS = ("SWING_HIGH", "SWING_LOW")
LEGACY_KEYS = {
    "version", "target", "matcher_version", "time_tolerance_bars", "price_tolerance", "coverage_start_index",
    "coverage_end_index", "event_type_map", "map_level1_to_structure", "atr_period", "atr_source",
    "exclude_unconfirmed_tail", "max_lag_bars", "min_recall",
}


def _setup():
    client.post("/api/datasets/seed-samples")
    ds = [d for d in client.get("/api/datasets").json() if d["symbol"] == "XAUUSD" and d["timeframe"] == "H1"][0]
    bars = client.get("/api/datasets/%s/bars" % ds["id"]).json()["bars"]
    run = client.post("/api/runs", json={"dataset_id": ds["id"], "algorithm": "swing_pivot",
                                         "params": {"left": 3, "right": 3}, "save": True}).json()
    windows = {"dev": (100, 400), "test": (1000, 1200)}
    labels = [
        {"structure_type": e["structure_type"], "bar_index": e["event_bar_index"], "price": e["price"]}
        for e in run["events"] if e["structure_type"] in PIVOTS
        and any(lo <= e["event_bar_index"] <= hi for lo, hi in windows.values())
    ]
    ls = client.post("/api/label-sets", json={"dataset_id": ds["id"], "annotator": "kiem tra", "version": "1",
                                              "rubric_vi": "Pivot 3/3 ở hai cửa sổ — kiểm tra đoạn.",
                                              "labels": labels}).json()
    segments = [
        {"name": "dev", "role": "dev", "start": bars[100]["bar_time"], "end": bars[401]["bar_time"]},
        {"name": "test", "role": "test", "start": bars[1000]["bar_time"], "end": bars[1201]["bar_time"]},
    ]
    n_dev = sum(1 for lb in labels if 100 <= lb["bar_index"] <= 400)
    return ds["id"], run, ls["id"], segments, n_dev


def _eval(run_id, ls_id, save=False, **proto):
    body = {"target": "swing_nho", "time_tolerance_bars": 1, "price_tolerance": 0}
    body.update(proto)
    return client.post("/api/evaluations", json={"run_ids": [run_id], "label_set_id": ls_id, "save": save,
                                                 "protocol": body})


def _run_of(result):
    return [r for g in result["groups"] for r in g.get("runs", [])][0]


def test_cham_co_chuan_ngau_nhien_va_doan_khoa_kiem_tra():
    _ds, run, ls_id, segments, n_dev = _setup()
    r = _eval(run["run_id"], ls_id, save=True, null_mode="matched_hour_atr_v1", null_n=40, segments=segments)
    assert r.status_code == 200, r.text
    res = r.json()
    assert set(res["protocol"]) == LEGACY_KEYS | {"null_mode", "null_n", "null_seed", "segments", "test_unlocked"}
    out = _run_of(res)
    q = out["quality"]
    assert q["n_labels"] == n_dev                                     # chỉ nhãn của đoạn phát triển
    assert q["false_negatives"] <= 1 and q["f1"] > 0.9               # nhãn chính là pivot của run (trừ đuôi)
    dev_row, test_row = out["by_segment"]
    assert dev_row["status"] == "ok" and test_row["status"] == "khoa" and "quality" not in test_row
    nb = out["null_baseline"]
    assert nb["status"] == "ok" and nb["n"] == 40 and nb["mode"] == "matched_hour_atr_v1"
    assert nb["f1"]["mean"] < q["f1"]                                 # pivot thật hơn đặt ngẫu nhiên
    # lưu → mở lại giữ nguyên kết quả
    again = client.get("/api/evaluations/%s" % res["evaluation_id"]).json()
    assert _run_of(again["result"])["null_baseline"] == nb
    md = client.get("/api/evaluations/%s/report.md" % res["evaluation_id"]).text
    assert "Chuẩn ngẫu nhiên" in md and "Theo đoạn" in md


def test_mo_doan_kiem_tra_co_dau_trong_ghi_chu():
    _ds, run, ls_id, segments, _n = _setup()
    r = _eval(run["run_id"], ls_id, save=True, segments=segments, test_unlocked=True)
    assert r.status_code == 200, r.text
    res = r.json()
    out = _run_of(res)
    assert out["by_segment"][1]["status"] == "ok"
    assert res["note_vi"].startswith("[ĐÃ MỞ ĐOẠN KIỂM TRA]") or "[ĐÃ MỞ ĐOẠN KIỂM TRA]" in res["note_vi"]
    saved = [e for e in client.get("/api/evaluations").json() if e["id"] == res["evaluation_id"]][0]
    assert "[ĐÃ MỞ ĐOẠN KIỂM TRA]" in (saved.get("note_vi") or "")


def test_doan_khong_hop_le_va_qua_nang_tra_400():
    _ds, run, ls_id, segments, _n = _setup()
    bad = [dict(segments[1]), dict(segments[0])]
    bad[0]["role"], bad[1]["role"] = "dev", "test"                    # kiểm tra nằm TRƯỚC phát triển
    r = _eval(run["run_id"], ls_id, segments=bad)
    assert r.status_code == 400 and "sau mọi đoạn phát triển" in r.text
    r = _eval(run["run_id"], ls_id, null_mode="uniform_v1", null_n=5)   # N < 10
    assert r.status_code == 400 and "Số lượt ngẫu nhiên" in r.text
    # Giới hạn khối lượng (N × (nhãn + sự kiện)) kiểm ở tests/core/test_eval_null.py.


def test_protocol_mac_dinh_khong_them_khoa_moi():
    _ds, run, ls_id, _s, _n = _setup()
    res = _eval(run["run_id"], ls_id).json()
    assert set(res["protocol"]) == LEGACY_KEYS
    out = _run_of(res)
    assert "null_baseline" not in out and "by_segment" not in out
