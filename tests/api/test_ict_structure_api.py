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


def test_cham_shift_bang_muc_tieu_ict_shift_va_doi_tang_shift_fvg():
    did = _m15()
    run = _run(did, session_calendar="none")
    ev = run["events"]
    shifts = [e for e in ev if e["structure_type"] in ("SHIFT_UP", "SHIFT_DOWN")]
    assert shifts, "Dataset mô phỏng phải có shift để thử chấm"
    assert all(e["details"]["group_id"] for e in shifts)
    ls = client.post("/api/label-sets", json={
        "dataset_id": did, "annotator": "kiem tra", "version": "1", "rubric_vi": "Shift của run — kiểm tra chấm.",
        "labels": [{"structure_type": e["structure_type"], "bar_index": e["event_bar_index"], "price": e["price"]}
                   for e in shifts],
    })
    assert ls.status_code == 200, ls.text
    end = max(e["confirmed_bar_index"] for e in shifts)
    proto = {"target": "ict_shift", "time_tolerance_bars": 0, "price_tolerance": 0,
             "coverage_start_index": 0, "coverage_end_index": end}
    out = client.post("/api/evaluations", json={"run_ids": [run["run_id"]], "label_set_id": ls.json()["id"],
                                                "save": False, "protocol": proto}).json()
    q = [r for g in out["groups"] for r in g.get("runs", [])][0]["quality"]
    assert q["true_positives"] == len(shifts) and q["false_negatives"] == 0 and q["false_positives"] == 0
    # Chấm tầng SHIFT_FVG thay cho SHIFT (cùng nến displacement): chỉ shift có FVG khớp, không đếm cả hai tầng.
    sfvg = [e for e in ev if e["structure_type"] in ("SHIFT_FVG_UP", "SHIFT_FVG_DOWN") and e["confirmed_bar_index"] <= end]
    proto2 = dict(proto, event_type_map={"SHIFT_FVG_UP": "SHIFT_UP", "SHIFT_FVG_DOWN": "SHIFT_DOWN"})
    out2 = client.post("/api/evaluations", json={"run_ids": [run["run_id"]], "label_set_id": ls.json()["id"],
                                                 "save": False, "protocol": proto2}).json()
    q2 = [r for g in out2["groups"] for r in g.get("runs", [])][0]["quality"]
    assert q2["true_positives"] == len(sfvg) and q2["false_negatives"] == len(shifts) - len(sfvg)


def test_order_flow_v030_trong_run_timeline_thong_ke_va_replay():
    did = _m15()
    run = _run(did, session_calendar="none")
    assert run["algorithm_version"] == "0.4.1"          # order flow có từ 0.3.0; 0.4.0 thêm khung lớn
    tl = run["timeline"]
    assert {"order_flow", "order_flow_since", "order_flow_reason"} <= set(tl[-1])
    assert {p["order_flow"] for p in tl} <= {1, -1, 0, None}
    flows = [e for e in run["events"] if e["structure_type"].startswith("ORDER_FLOW_")]
    assert flows and all(e["confirmed_bar_index"] == e["event_bar_index"] for e in flows)
    of = run["pending_state"]["order_flow"]
    assert (of["trang_thai"], of["tu_nen"], of["ly_do"]) == (
        tl[-1]["order_flow"], tl[-1]["order_flow_since"], tl[-1]["order_flow_reason"])
    st = run["stats"]["chi_so_thuat_toan"]["order_flow"]
    assert st["doi_trang_thai"] == len(flows) and sum(st["theo_ly_do"].values()) == len(flows)
    assert abs(sum(st["ty_le_thoi_gian"].values()) - 1.0) < 1e-9
    rp = client.post("/api/replay", json={"dataset_id": did, "algorithm": "ict_structure",
                                          "params": {"timeframe": "M15", "session_calendar": "none"}})
    assert rp.status_code == 200, rp.text
    sid = rp.json()["session_id"]
    snap = client.post("/api/replay/%s/seek" % sid, json={"index": 400}).json()
    assert snap["algorithm_version"] == "0.4.1"
    of400 = snap["pending_state"]["order_flow"]
    assert (of400["trang_thai"], of400["tu_nen"]) == (tl[400]["order_flow"], tl[400]["order_flow_since"])
    assert snap["timeline"][-1]["order_flow"] == tl[400]["order_flow"]
    client.delete("/api/replay/%s" % sid)


def test_khung_lon_v040_trong_run_manifest_replay_va_tu_vung():
    """0.4.0: [T] khung lớn, [S5] PD array, [S6] DOL qua API — sự kiện HTF_* có câu giải thích, details.htf trên sự
    kiện khung chạy, cột timeline, thống kê, pending_state; replay tới nến 600 khớp run; tham số sai → 400."""
    algos = {a["name"]: a for a in client.get("/api/algorithms").json()}
    specs = {p["name"]: p for p in algos["ict_structure"]["params"]}
    assert (specs["htf_list"]["default"], specs["htf_alignment"]["default"], specs["htf_min_coverage"]["default"],
            specs["period_levels"]["default"], specs["pd_respect_mode"]["default"], specs["dol_min_tier"]["default"]) == (
        "H1,H4", "ny_1700", 0.9, True, "strict", "H1")
    assert specs["respect_away_atr"]["show_if"] == {"param": "pd_respect_mode", "value": "strict"}
    did = _m15()
    run = _run(did)
    assert run["algorithm_version"] == "0.4.1"
    ev = run["events"]
    kinds = {e["structure_type"] for e in ev}
    assert {"HTF_SWING_HIGH", "HTF_SWING_LOW", "HTF_FVG_UP", "HTF_FVG_DOWN", "HTF_PERIOD_HIGH", "HTF_PERIOD_LOW"} <= kinds
    assert kinds & {"PD_RESPECT_UP", "PD_RESPECT_DOWN", "PD_DISRESPECT_UP", "PD_DISRESPECT_DOWN"}
    for e in ev:
        assert e["structure_text_vi"] != e["structure_type"] and e["reason_text_vi"]
        if e["structure_type"].startswith("HTF_"):
            assert "htf" not in e["details"] and e["details"]["khung"] in ("H1", "H4", "D", "W")
        elif e["structure_type"] in ("SWING_HIGH", "SWING_LOW", "FVG_UP", "FVG_DOWN", "FVG_TOUCHED", "FVG_FILLED",
                                     "DISPLACEMENT_UP", "DISPLACEMENT_DOWN"):
            assert "htf" not in e["details"]                         # 0.4.1: sự kiện nguyên liệu không mang htf
        else:
            assert set(e["details"]["htf"]) == {"alignment", "H1", "H4", "pd_bias", "dol", "levels"}
    tl = run["timeline"]
    assert {"htf_H1_order", "htf_H4_order", "htf_H4_zone", "htf_H4_range_pos", "pd_bias", "dol_side", "pdh_taken",
            "pdl_taken", "htf_H4_age"} <= set(tl[-1])
    st = run["stats"]["chi_so_thuat_toan"]
    assert st["khung_lon"]["khung"] == ["H1", "H4"] and st["khung_lon"]["moc"] == "ny_1700"
    assert st["pd_array"]["su_kien"] == sum(1 for e in ev if e["structure_type"].startswith("PD_"))
    assert st["dol"]["dat"] == sum(1 for e in ev if e["structure_type"] == "DOL_REACHED")
    ps = run["pending_state"]["khung_lon"]
    assert ps["bat"] and ps["H4"]["cau_truc"] and ps["muc_theo_ky"] is not None and "ngu_canh" in ps
    rid = run["run_id"]
    man = client.get("/api/runs/%s/manifest" % rid).json()
    assert man["algorithm_info"]["khung_lon"]["moc"] == "ny_1700"
    csv = client.get("/api/runs/%s/export.csv" % rid)
    assert csv.status_code == 200 and "HTF_SWING_HIGH" in csv.text
    rp = client.post("/api/replay", json={"dataset_id": did, "algorithm": "ict_structure",
                                          "params": {"timeframe": "M15"}})
    assert rp.status_code == 200, rp.text
    sid = rp.json()["session_id"]
    snap = client.post("/api/replay/%s/seek" % sid, json={"index": 600}).json()
    ctx = snap["pending_state"]["khung_lon"]["ngu_canh"]
    assert (ctx["H4"]["order"], ctx["pd_bias"]["dir"], ctx["dol"]["side"]) == (
        tl[600]["htf_H4_order"], tl[600]["pd_bias"], tl[600]["dol_side"])
    assert snap["timeline"][-1] == tl[600]
    assert snap["events"] == [e for e in ev if e["confirmed_bar_index"] <= 600]
    client.delete("/api/replay/%s" % sid)
    r = client.post("/api/runs", json={"dataset_id": did, "algorithm": "ict_structure",
                                       "params": {"timeframe": "M15", "htf_list": "D"}, "save": False})
    assert r.status_code == 400 and "htf_list" in r.text
