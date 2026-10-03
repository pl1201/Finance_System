"""API đánh giá thuật toán: protocol, F1 không bịa 0, lưu và mở lại."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _xau(tf: str = "H1") -> str:
    client.post("/api/datasets/seed-samples")
    ds = client.get("/api/datasets").json()
    xau = [d for d in ds if d["symbol"] == "XAUUSD" and d["timeframe"] == tf]
    assert xau, "Phải có dataset XAUUSD %s mô phỏng" % tf
    return xau[0]["id"]


def _xau_h1():
    return _xau("H1")


def _run(dataset_id, **kwargs):
    body = {"dataset_id": dataset_id, "algorithm": "swing_pivot", "params": {"left": 3, "right": 3}}
    body.update(kwargs)
    r = client.post("/api/runs", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _first_group(result):
    groups = [g for g in result["groups"] if g.get("comparable") and g.get("runs")]
    assert groups, result.get("groups")
    return groups[0]


def test_trang_danh_gia_duoc_phuc_vu():
    r = client.get("/danh-gia")
    assert r.status_code == 200
    assert "Đánh giá thuật toán" in r.text
    assert "Thử nghiệm" in r.text
    assert 'id="tf-switch"' in r.text
    assert "M5" in r.text and "M15" in r.text
    assert client.get("/app/js/eval.js").status_code == 200


def test_eval_meta_khong_xep_hang():
    m = client.get("/api/eval/meta").json()
    assert m["protocol_version"] == "1.0.0"
    assert "min_cost_v1" in m["matcher_versions"]
    assert "greedy_label_order_v1" in m["matcher_versions"]
    assert "tốt nhất" in m["note_vi"] or "thuật toán tốt nhất" in m["note_vi"]
    ids = [t["id"] for t in m["targets"]]
    assert "swing_nho" in ids and "swing_cau_truc" in ids


def test_danh_gia_khong_nhan_thi_f1_la_none_khong_phai_0():
    ds = _xau_h1()
    a = _run(ds, params={"left": 3, "right": 3}, label="3/3")
    b = _run(ds, params={"left": 6, "right": 6}, label="6/6")
    out = client.post("/api/evaluations", json={
        "run_ids": [a["run_id"], b["run_id"]],
        "protocol": {"target": "swing_nho", "matcher_version": "min_cost_v1"},
        "save": True,
    }).json()
    run = _first_group(out)["runs"][0]
    q = run["quality"]
    assert q["has_labels"] is False
    assert q["precision"] is None and q["recall"] is None and q["f1"] is None
    assert q["true_positives"] is None
    assert "Chưa có nhãn tham chiếu" in q["note_vi"]
    assert run["lag"]["n"] > 0
    assert run["lag"]["p90"] is not None
    assert run["lag"]["median"] is not None
    assert run["density"]["per_100"] is not None
    val = run["validity"]
    assert val["status"] in ("chua_kiem_tra", "co_vi_pham", "dat_kiem_tra")
    assert "pytest" in val["note_vi"].lower() or "test prefix" in val["note_vi"].lower()
    assert out["evaluation_id"].startswith("ev_")
    got = client.get("/api/evaluations/%s" % out["evaluation_id"])
    assert got.status_code == 200
    row = got.json()
    assert row["protocol_hash"] == out["protocol_hash"]
    assert row["protocol"]["matcher_version"] == "min_cost_v1"
    assert row["result"]["protocol_hash"] == out["protocol_hash"]
    md = client.get("/api/evaluations/%s/report.md" % out["evaluation_id"])
    assert md.status_code == 200
    assert "Không phải win-rate" in md.text
    assert out["protocol_hash"] in md.text


def test_danh_gia_co_nhan_tinh_f1_va_pham_vi_khong_thanh_fp():
    ds = _xau_h1()
    run = _run(ds, label="gốc")
    highs = sorted(
        [e for e in run["events"] if e["structure_type"] == "SWING_HIGH"],
        key=lambda e: e["event_bar_index"],
    )
    assert len(highs) >= 4
    kept = highs[:3]
    labels = [
        {
            "structure_type": e["structure_type"],
            "bar_index": e["event_bar_index"],
            "price": e["price"],
            "notes": "gán tay test",
        }
        for e in kept
    ]
    ls = client.post("/api/label-sets", json={
        "dataset_id": ds,
        "annotator": "tester",
        "version": "1",
        "rubric_vi": "Ba đỉnh cấp 1 trùng sự kiện thuật toán — kiểm tra matcher.",
        "labels": labels,
    }).json()
    cov_end = max(e["confirmed_bar_index"] for e in kept)
    outsiders = [e for e in highs if e["event_bar_index"] > cov_end]
    assert outsiders, "Cần ít nhất một đỉnh ngoài khoảng chấm"
    outsider = outsiders[0]

    out = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]],
        "label_set_id": ls["id"],
        "protocol": {
            "target": "swing_nho",
            "matcher_version": "min_cost_v1",
            "time_tolerance_bars": 0,
            "price_tolerance": 0,
            "coverage_start_index": 0,
            "coverage_end_index": cov_end,
        },
        "save": True,
    }).json()
    scored = _first_group(out)["runs"][0]
    q = scored["quality"]
    assert q["has_labels"] is True
    assert q["f1"] is not None
    assert q["true_positives"] == 3
    assert q["false_negatives"] == 0
    assert q["false_positives"] >= 0
    assert scored["counts_ignored"]["outside_coverage"] >= 1
    # Sự kiện ngoài khoảng chấm không được nhét vào FP.
    fp_bars = {e["event_bar_index"] for e in scored["false_positives"]}
    assert outsider["event_bar_index"] not in fp_bars

    again = client.get("/api/evaluations/%s" % out["evaluation_id"]).json()
    assert again["protocol"]["coverage_end_index"] == cov_end
    assert again["result"]["groups"][0]["runs"][0]["quality"]["f1"] == q["f1"]


def test_matcher_khac_nhau_tach_hash():
    ds = _xau_h1()
    run = _run(ds)
    a = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]],
        "protocol": {"target": "swing_nho", "matcher_version": "min_cost_v1"},
        "save": False,
    }).json()
    b = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]],
        "protocol": {"target": "swing_nho", "matcher_version": "greedy_label_order_v1"},
        "save": False,
    }).json()
    assert a["protocol_hash"] != b["protocol_hash"]


def test_danh_gia_thieu_run_tra_400():
    r = client.post("/api/evaluations", json={"run_ids": [], "protocol": {"target": "swing_nho"}})
    assert r.status_code == 400


def test_khong_tu_gan_dat_nhan_qua_cho_moi_run():
    """Trạng thái nhân quả gắn với sự kiện đã lưu của run, không phải suite pytest."""
    ds = _xau_h1()
    run = _run(ds)
    out = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]],
        "protocol": {"target": "swing_nho"},
        "save": False,
    }).json()
    val = _first_group(out)["runs"][0]["validity"]
    assert "Không thay thế test prefix" in val["note_vi"] or "pytest" in val["note_vi"].lower()
    assert val["pham_vi_vi"]


@pytest.mark.parametrize(
    "tf,target,algorithm,event_type",
    [
        ("M5", "swing_nho", "swing_pivot", "SWING_HIGH"),
        ("M15", "swing_nho", "swing_pivot", "SWING_HIGH"),
        ("M5", "swing_cau_truc", "swing_hierarchy", "SWING_HIGH_L2"),
        ("M15", "swing_cau_truc", "swing_hierarchy", "SWING_HIGH_L2"),
    ],
)
def test_danh_gia_m5_m15_do_tre_va_mat_do(tf, target, algorithm, event_type):
    ds = _xau(tf)
    run = _run(ds, algorithm=algorithm, label="%s %s" % (tf, algorithm))
    assert run["timeframe"] == tf
    typed = [e for e in run["events"] if e["structure_type"] == event_type]
    assert typed, "Phải có sự kiện %s trên %s" % (event_type, tf)

    out = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]],
        "protocol": {"target": target, "matcher_version": "min_cost_v1"},
        "save": False,
    }).json()
    assert out["dataset"]["timeframe"] == tf
    scored = _first_group(out)["runs"][0]
    assert scored["timeframe"] == tf
    q = scored["quality"]
    assert q["has_labels"] is False
    assert q["f1"] is None
    assert "Chưa có nhãn tham chiếu" in q["note_vi"]
    assert scored["lag"]["n"] == q["n_events_scored"]
    assert scored["lag"]["n"] >= len(typed)
    assert scored["lag"]["p90"] is not None
    assert tf in scored["lag"]["note_vi"]
    assert scored["density"]["per_100"] is not None


def test_m5_va_h1_khong_cung_nhom_so_sanh():
    h1 = _run(_xau("H1"), label="h1")
    m5 = _run(_xau("M5"), label="m5")
    m15 = _run(_xau("M15"), label="m15")
    out = client.post("/api/evaluations", json={
        "run_ids": [h1["run_id"], m5["run_id"], m15["run_id"]],
        "protocol": {"target": "swing_nho"},
        "save": False,
    }).json()
    comparable = [g for g in out["groups"] if g.get("comparable") and g.get("runs")]
    assert len(comparable) == 3
    tfs = {g["runs"][0]["timeframe"] for g in comparable}
    assert tfs == {"H1", "M5", "M15"}
    for g in comparable:
        ids = {r["dataset_id"] for r in g["runs"]}
        assert len(ids) == 1
        assert "Không so chéo khung" in g["reason_vi"]


def test_danh_gia_m15_co_nhan_khong_tinh_fp_ngoai_khoang():
    ds = _xau("M15")
    run = _run(ds, label="m15 gốc")
    highs = sorted(
        [e for e in run["events"] if e["structure_type"] == "SWING_HIGH"],
        key=lambda e: e["event_bar_index"],
    )
    assert len(highs) >= 4
    kept = highs[:3]
    ls = client.post("/api/label-sets", json={
        "dataset_id": ds,
        "annotator": "tester-m15",
        "version": "1",
        "rubric_vi": "Ba đỉnh cấp 1 trên M15.",
        "labels": [
            {
                "structure_type": e["structure_type"],
                "bar_index": e["event_bar_index"],
                "price": e["price"],
                "notes": "M15",
            }
            for e in kept
        ],
    }).json()
    cov_end = max(e["confirmed_bar_index"] for e in kept)
    outsiders = [e for e in highs if e["event_bar_index"] > cov_end]
    assert outsiders
    out = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]],
        "label_set_id": ls["id"],
        "protocol": {
            "target": "swing_nho",
            "time_tolerance_bars": 0,
            "price_tolerance": 0,
            "coverage_start_index": 0,
            "coverage_end_index": cov_end,
        },
        "save": True,
    }).json()
    scored = _first_group(out)["runs"][0]
    assert scored["timeframe"] == "M15"
    assert scored["quality"]["true_positives"] == 3
    assert scored["quality"]["false_negatives"] == 0
    fp_bars = {e["event_bar_index"] for e in scored["false_positives"]}
    assert outsiders[0]["event_bar_index"] not in fp_bars
