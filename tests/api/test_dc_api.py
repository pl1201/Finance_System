"""Tích hợp dc_atr_structure qua API: chạy → lưu → mở lại → CSV/manifest → replay."""
from __future__ import annotations

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def m15_id():
    r = client.post("/api/datasets/seed-samples")
    assert r.status_code == 200, r.text
    ds = [d for d in client.get("/api/datasets").json()
          if d["symbol"] == "XAUUSD" and d["timeframe"] == "M15"]
    assert ds, "Cần dataset XAUUSD M15 mô phỏng"
    return ds[0]["id"]


def _run(ds_id, params=None, save=True, algorithm="dc_atr_structure", label=""):
    p = {"timeframe": "M15"}
    if algorithm == "dc_atr_structure":
        p.update(params or {})
    else:
        p = params or {}
    return client.post("/api/runs", json={
        "dataset_id": ds_id, "algorithm": algorithm, "params": p, "save": save, "label": label,
    })


def test_algorithms_co_dc_va_show_if():
    algos = {a["name"]: a for a in client.get("/api/algorithms").json()}
    dc = algos["dc_atr_structure"]
    assert dc["version"] == "0.2.0"
    by = {p["name"]: p for p in dc["params"]}
    assert by["reversal_pct"]["show_if"]["value"] == "percent"
    # Thuật toán cũ không bị đổi phiên bản
    assert algos["swing_pivot"]["version"] == "1.1.0"


def test_tham_so_sai_va_sai_khung_tra_400(m15_id):
    r = _run(m15_id, {"atr_multiplier": 0})
    assert r.status_code == 400
    r = client.post("/api/runs", json={
        "dataset_id": m15_id, "algorithm": "dc_atr_structure", "params": {"timeframe": "H1"},
    })
    assert r.status_code == 400 and "không khớp" in r.json()["detail"]


def test_chay_luu_mo_lai_xuat_csv_manifest(m15_id):
    r = _run(m15_id, {"atr_multiplier": 1.5}, label="dc k1.5")
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["saved"] and res["events"]
    pts = res["timeline"]
    assert len(pts) == res["bars_processed"]
    assert {"regime", "dc_cand_price", "range_upper", "atr"} <= set(pts[-1])
    m = res["stats"]["chi_so_thuat_toan"]
    assert m["so_pivot_xac_nhan"] > 0 and m["so_segment"] == m["so_gap"] + 1
    assert res["pending_state"]["dc"]["phase"]

    saved = client.get("/api/runs/%s" % res["run_id"]).json()
    assert [e["event_id"] for e in saved["events"]] == [e["event_id"] for e in res["events"]]
    piv = [e for e in saved["events"] if e["structure_type"] == "DC_HIGH"][0]
    assert piv["details"]["delta_e"] > 0 and piv["details"]["gia_theo"] == "close"

    # mở lại = chạy lại cùng tham số → khớp hoàn toàn
    again = _run(m15_id, {"atr_multiplier": 1.5}, save=False).json()
    assert [e["event_id"] for e in again["events"]] == [e["event_id"] for e in res["events"]]

    csv_text = client.get("/api/runs/%s/export.csv" % res["run_id"]).text
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(rows) == len(res["events"])
    det = json.loads([x for x in rows if x["structure_type"] == "DC_HIGH"][0]["details_json"])
    assert "cong_thuc_nguong" in det and "nhan" in det

    man = client.get("/api/runs/%s/manifest" % res["run_id"]).json()
    info = man["algorithm_info"]
    assert info["gap_policy"] == "reset" and info["price_source"] == "close"
    assert info["classifier"]["version"] == "0.1.0"
    assert man["run"]["params"]["atr_multiplier"] == 1.5


def test_so_sanh_voi_baseline_pivot_3_3(m15_id):
    dc = _run(m15_id).json()
    base = _run(m15_id, {"left": 3, "right": 3}, algorithm="swing_pivot").json()
    assert base["algorithm_version"] == "1.1.0"
    c = client.post("/api/compare", json={"run_id_a": base["run_id"], "run_id_b": dc["run_id"]}).json()
    assert c["run_a"]["dataset_checksum"] == c["run_b"]["dataset_checksum"]
    types = {r["structure_type"] for r in c["so_sanh_theo_loai"]}
    assert "DC_HIGH" in types and "SWING_HIGH" in types


def test_replay_next_event_va_lui(m15_id):
    r = client.post("/api/replay", json={
        "dataset_id": m15_id, "algorithm": "dc_atr_structure", "params": {"timeframe": "M15"},
    })
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]
    s1 = client.post("/api/replay/%s/next-event" % sid).json()
    assert s1["events"] and s1["cursor"] == s1["events"][-1]["confirmed_bar_index"]
    assert all(e["confirmed_bar_index"] <= s1["cursor"] for e in s1["events"])
    s2 = client.post("/api/replay/%s/seek" % sid, json={"index": 400}).json()
    ps_400 = s2["pending_state"]
    client.post("/api/replay/%s/seek" % sid, json={"index": 900})
    back = client.post("/api/replay/%s/seek" % sid, json={"index": 400}).json()
    assert back["pending_state"] == ps_400
    assert back["timeline"] == s2["timeline"]
    client.delete("/api/replay/%s" % sid)


def _merge(state, snap):
    """Ghép phản hồi replay theo cách frontend làm (cắt phần sau delta_since rồi nối)."""
    s = snap["delta_since"]
    if s is None:
        return {"events": snap["events"], "timeline": snap["timeline"]}
    return {
        "events": [e for e in state["events"] if e["confirmed_bar_index"] <= s] + snap["events"],
        "timeline": [p for p in state["timeline"] if p["bar_index"] <= s] + snap["timeline"],
    }


def test_replay_delta_since_ghep_bang_ban_day_du(m15_id):
    mk = lambda: client.post("/api/replay", json={
        "dataset_id": m15_id, "algorithm": "dc_atr_structure", "params": {"timeframe": "M15"},
    }).json()["session_id"]
    sid, ref = mk(), mk()
    snap = client.post("/api/replay/%s/seek" % sid, json={"index": 300}).json()
    assert snap["delta_since"] is None
    state = _merge(None, snap)
    for body, path, cur in (
        ({"n": 200, "since": 300}, "step", 500),
        ({"since": 500}, "next-event", None),
        ({"n": 60, "since": None}, "back", None),
        ({"index": 120}, "seek", 120),
    ):
        if path == "back":
            body["since"] = snap["cursor"]
        if path == "seek":
            body["since"] = snap["cursor"]
        snap = client.post("/api/replay/%s/%s" % (sid, path), json=body).json()
        if cur is not None:
            assert snap["cursor"] == cur
        assert snap["delta_since"] == min(body["since"], snap["cursor"])
        state = _merge(state, snap)
        full = client.post("/api/replay/%s/seek" % ref, json={"index": snap["cursor"]}).json()
        assert [e["event_id"] for e in state["events"]] == [e["event_id"] for e in full["events"]]
        assert state["timeline"] == full["timeline"]
        assert snap["pending_state"] == full["pending_state"]
    # phản hồi delta nhỏ hơn nhiều so với bản đầy đủ
    small = client.post("/api/replay/%s/step" % sid, json={"n": 1, "since": snap["cursor"]}).json()
    assert len(small["timeline"]) == 1
    for s in (sid, ref):
        client.delete("/api/replay/%s" % s)
