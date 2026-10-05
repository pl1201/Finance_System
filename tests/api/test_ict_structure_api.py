"""ict_structure qua API: lịch phiên auto theo mã, lưu → mở lại → CSV/manifest, replay, chấm ITH/ITL."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _m15():
    client.post("/api/datasets/seed-samples")
    ds = [d for d in client.get("/api/datasets").json() if d["symbol"] == "XAUUSD" and d["timeframe"] == "M15"]
    assert ds, "Phải có dataset XAUUSD M15 mô phỏng"
    return ds[0]["id"]


def _run(did, **params):
    p = {"timeframe": "M15"}
    p.update(params)
    r = client.post("/api/runs", json={"dataset_id": did, "algorithm": "ict_structure", "params": p, "save": True})
    assert r.status_code == 200, r.text
    return r.json()


def test_dang_ky_va_lich_auto_doi_thanh_lich_cu_the():
    algos = {a["name"]: a for a in client.get("/api/algorithms").json()}
    assert "ict_structure" in algos
    specs = {p["name"]: p for p in algos["ict_structure"]["params"]}
    assert specs["session_calendar"]["default"] == "auto" and specs["structure_level"]["default"] == 2
    run = _run(_m15())
    assert run["params"]["session_calendar"] == "cme_globex_metals"     # XAUUSD → lịch CME kim loại
    types = {e["structure_type"] for e in run["events"]}
    assert {"SWING_HIGH_L2", "SWING_LOW_L2"} <= types
    stats = run["stats"]["chi_so_thuat_toan"]
    assert stats["lich_phien"] == "cme_globex_metals" and stats["so_nen"] == run["bars_processed"]
    assert run["timeline"] and "dealing_hi" in run["timeline"][-1]
    assert run["pending_state"]["ict"] is True


def test_luu_mo_lai_csv_manifest_va_replay():
    did = _m15()
    run = _run(did, session_calendar="none")
    rid = run["run_id"]
    again = client.get("/api/runs/%s" % rid).json()
    assert [e["event_id"] for e in again["events"]] == [e["event_id"] for e in run["events"]]
    csv = client.get("/api/runs/%s/export.csv" % rid)
    assert csv.status_code == 200 and "SWING_HIGH_L2" in csv.text
    man = client.get("/api/runs/%s/manifest" % rid).json()
    info = man["algorithm_info"]
    assert info["spec"] == "docs/algorithms/thuat_toan_ict_structure.md" and info["lich_phien"]["ten"] == "none"
    assert man["run"]["params"]["structure_level"] == 2
    rp = client.post("/api/replay", json={"dataset_id": did, "algorithm": "ict_structure",
                                          "params": {"timeframe": "M15"}})
    assert rp.status_code == 200, rp.text
    sid = rp.json()["session_id"]
    step = client.post("/api/replay/%s/seek" % sid, json={"index": 300})
    assert step.status_code == 200, step.text
    snap = step.json()
    assert snap["params"]["session_calendar"] == "cme_globex_metals"
    assert all(e["confirmed_bar_index"] <= 300 for e in snap["events"])
    assert snap["pending_state"]["ict"] is True
    client.post("/api/replay/%s/seek" % sid, json={"index": 700})
    back = client.post("/api/replay/%s/seek" % sid, json={"index": 300}).json()   # lùi = chạy prefix mới
    assert back["pending_state"] == snap["pending_state"] and back["timeline"] == snap["timeline"]
    client.delete("/api/replay/%s" % sid)


def test_sai_khung_tra_400():
    r = client.post("/api/runs", json={"dataset_id": _m15(), "algorithm": "ict_structure",
                                       "params": {"timeframe": "H1"}, "save": False})
    assert r.status_code == 400 and "không khớp dataset" in r.text


def test_cham_ith_itl_bang_muc_tieu_swing_cau_truc():
    did = _m15()
    run = _run(did, session_calendar="none")
    ith = [e for e in run["events"] if e["structure_type"] in ("SWING_HIGH_L2", "SWING_LOW_L2")][:6]
    ls = client.post("/api/label-sets", json={
        "dataset_id": did, "annotator": "kiem tra", "version": "1", "rubric_vi": "ITH/ITL của run — kiểm tra chấm.",
        "labels": [{"structure_type": e["structure_type"], "bar_index": e["event_bar_index"], "price": e["price"]}
                   for e in ith],
    }).json()
    end = max(e["confirmed_bar_index"] for e in ith)
    out = client.post("/api/evaluations", json={
        "run_ids": [run["run_id"]], "label_set_id": ls["id"], "save": False,
        "protocol": {"target": "swing_cau_truc", "time_tolerance_bars": 0, "price_tolerance": 0,
                     "coverage_start_index": 0, "coverage_end_index": end},
    }).json()
    q = [r for g in out["groups"] for r in g.get("runs", [])][0]["quality"]
    assert q["true_positives"] == len(ith) and q["false_negatives"] == 0
