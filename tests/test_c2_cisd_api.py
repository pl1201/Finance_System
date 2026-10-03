"""API → lưu run → mở lại → export/manifest/metric/replay cho ``c2_cisd_research``."""
from __future__ import annotations

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def datasets():
    assert client.post("/api/datasets/seed-samples").status_code == 200
    ds = client.get("/api/datasets").json()
    m15 = [d for d in ds if d["symbol"] == "XAUUSD" and d["timeframe"] == "M15"][0]["id"]
    h1 = [d for d in ds if d["symbol"] == "XAUUSD" and d["timeframe"] == "H1"][0]["id"]
    return {"M15": m15, "H1": h1}


@pytest.fixture(scope="module")
def run(datasets):
    r = client.post("/api/runs", json={"dataset_id": datasets["M15"], "algorithm": "c2_cisd_research",
                                       "params": {}, "label": "test c2"})
    assert r.status_code == 200, r.text
    return r.json()


def test_registry_co_thuat_toan_va_tham_so():
    algos = {a["name"]: a for a in client.get("/api/algorithms").json()}
    a = algos["c2_cisd_research"]
    assert a["version"] == "0.1.0"
    assert {p["name"] for p in a["params"]} == {"ltf", "htf", "bias"}
    assert "C2_CONFIRMED_UP" in a["emits_types"]
    # thuật toán cũ không đổi version/default
    assert algos["swing_pivot"]["version"] and {p["name"]: p["default"] for p in algos["swing_pivot"]["params"]}["left"] == 3


def test_tu_choi_dataset_khong_phai_m15(datasets):
    r = client.post("/api/runs", json={"dataset_id": datasets["H1"], "algorithm": "c2_cisd_research"})
    assert r.status_code == 400
    assert "M15" in r.json()["detail"]
    r = client.post("/api/replay", json={"dataset_id": datasets["H1"], "algorithm": "c2_cisd_research"})
    assert r.status_code == 400


def test_run_luu_va_mo_lai_giu_nguyen_su_kien(run):
    types = {e["structure_type"] for e in run["events"]}
    assert "C2_CONFIRMED_UP" in types or "C2_CONFIRMED_DOWN" in types
    assert run["stats"]["chi_so_thuat_toan"]["tong_setup"] > 0
    assert {"cisd_up", "cisd_down", "setup_up_level", "setup_down_extreme"} <= set(run["timeline"][-1])
    saved = client.get("/api/runs/%s" % run["run_id"]).json()
    assert saved["stats"]["chi_so_thuat_toan"] == run["stats"]["chi_so_thuat_toan"]
    a = [(e["event_id"], e["structure_type"], e["confirmed_at"], e["event_time"], e["price"],
          e["direction"], e["reference_event_id"], e["details"]) for e in run["events"]]
    b = [(e["event_id"], e["structure_type"], e["confirmed_at"], e["event_time"], e["price"],
          e["direction"], e["reference_event_id"], e["details"]) for e in saved["events"]]
    assert a == b


def test_export_csv_va_manifest(run):
    r = client.get("/api/runs/%s/export.csv" % run["run_id"])
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == len(run["events"])
    c2 = [x for x in rows if x["structure_type"].startswith("C2_CONFIRMED")][0]
    det = json.loads(c2["details_json"])
    assert det["setup_id"] and det["htf_alignment"] == "utc_epoch"
    m = client.get("/api/runs/%s/manifest" % run["run_id"]).json()
    info = m["algorithm_info"]
    assert info["nguon"]["commit"] == "1bb53262deba9456f2b1a85d15c6ac5a5e880cf7"
    assert info["nguon"]["license"] == "MIT" and info["parity_pine"] == "CHƯA XÁC MINH"
    assert m["run"]["dataset_checksum"]


def test_metric_vong_doi_va_mfe_mae(run, datasets):
    m = client.get("/api/runs/%s/c2-cisd-metrics?horizon=8" % run["run_id"]).json()
    v = m["vong_doi"]
    assert v["tong_setup"] == sum(v["ket_thuc_theo_ly_do"].values()) + v["censored_dang_mo"]
    x = m["mfe_mae"]
    assert x["horizon_nen"] == 8
    assert x["c2_only"]["tat_ca"]["so_mau"] + x["c2_only"]["tat_ca"]["so_mau_bo_thieu_horizon"] == v["tong_setup"]
    assert "win" not in json.dumps(x).lower().replace("không phải", "")
    sp = client.post("/api/runs", json={"dataset_id": datasets["M15"], "algorithm": "swing_pivot"}).json()
    assert "chi_so_thuat_toan" not in sp["stats"]
    assert client.get("/api/runs/%s/c2-cisd-metrics" % sp["run_id"]).status_code == 400


def test_replay_chi_hien_su_kien_da_biet(run, datasets):
    r = client.post("/api/replay", json={"dataset_id": datasets["M15"], "algorithm": "c2_cisd_research"})
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]
    cursor = 900
    snap = client.post("/api/replay/%s/seek" % sid, json={"index": cursor}).json()
    assert snap["cursor"] == cursor
    expect = [e["event_id"] for e in run["events"] if e["confirmed_bar_index"] <= cursor]
    assert [e["event_id"] for e in snap["events"]] == expect
    assert len(snap["timeline"]) == cursor + 1
    assert "setup_dang_mo" in snap["pending_state"]
    client.delete("/api/replay/%s" % sid)


def test_danh_gia_c2_chua_co_nhan_khong_dung_f1(run):
    out = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]],
        "protocol": {"target": "c2", "matcher_version": "min_cost_v1"},
        "save": False,
    }).json()
    groups = [g for g in out["groups"] if g.get("runs")]
    q = groups[0]["runs"][0]["quality"]
    assert q["has_labels"] is False and q["f1"] is None
    assert "Chưa có nhãn tham chiếu" in q["note_vi"]


def test_danh_gia_c2_mot_mot_cung_huong(run, datasets):
    c2 = [e for e in run["events"] if e["structure_type"] == "C2_CONFIRMED_UP"][:3]
    assert len(c2) == 3
    labels = [{"structure_type": e["structure_type"], "bar_index": e["event_bar_index"],
               "price": e["price"], "notes": "test"} for e in c2]
    # sai hướng: nhãn C2 giảm tại nến của C2 tăng → không được ghép
    labels.append({"structure_type": "C2_CONFIRMED_DOWN", "bar_index": c2[0]["event_bar_index"],
                   "price": c2[0]["price"], "notes": "sai hướng"})
    ls = client.post("/api/label-sets", json={
        "dataset_id": datasets["M15"], "annotator": "tester", "version": "c2",
        "rubric_vi": "C2 ở nến cực trị", "labels": labels,
    })
    assert ls.status_code == 200, ls.text
    cov_end = max(e["confirmed_bar_index"] for e in c2)
    out = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]], "label_set_id": ls.json()["id"],
        "protocol": {"target": "c2", "matcher_version": "min_cost_v1", "time_tolerance_bars": 0,
                     "price_tolerance": 0, "coverage_start_index": 0, "coverage_end_index": cov_end},
        "save": False,
    }).json()
    groups = [g for g in out["groups"] if g.get("runs")]
    q = groups[0]["runs"][0]["quality"]
    assert q["true_positives"] == 3 and q["false_negatives"] == 1
    # cisd: bộ nhãn không có nhãn CISD → không có số
    out2 = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]], "label_set_id": ls.json()["id"],
        "protocol": {"target": "cisd", "matcher_version": "min_cost_v1"}, "save": False,
    }).json()
    q2 = [g for g in out2["groups"] if g.get("runs")][0]["runs"][0]["quality"]
    assert q2["has_labels"] is False and q2["f1"] is None
