"""ict_structure qua API: lịch phiên auto theo mã, lưu → mở lại → CSV/manifest, replay, chấm ITH/ITL."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from core.algorithms.ict_structure import LEGACY_0_9

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


def test_cham_mss_bang_muc_tieu_ict_mss_va_su_kien_doi_huong_mac_dinh():
    """0.10.0: mặc định đổi hướng = MSS (không còn SHIFT_*); MSS chấm được bằng mục tiêu ict_mss (nhãn ở nến phá, giá = mốc)."""
    did = _m15()
    run = _run(did, session_calendar="none")
    ev = run["events"]
    assert not [e for e in ev if e["structure_type"].startswith("SHIFT_")]
    mss = [e for e in ev if e["structure_type"] in ("MSS_UP", "MSS_DOWN")]
    assert mss, "Dataset mô phỏng phải có MSS để thử chấm"
    for e in mss:
        d = e["details"]
        assert d["group_id"] and e["price"] == d["moc_pha"] and e["event_bar_index"] == e["confirmed_bar_index"]
        assert d["nen_moc_pha"] < d["swept"][0]["nen_lay"] <= d["nen_sweep"] <= e["confirmed_bar_index"]
        assert d["chan"]["bien_do_atr"] >= d["chan"]["nguong_atr"] and 1 <= d["chan"]["so_nen"] <= d["chan"]["toi_da_nen"]
    ls = client.post("/api/label-sets", json={
        "dataset_id": did, "annotator": "kiem tra", "version": "1", "rubric_vi": "MSS của run — kiểm tra chấm.",
        "labels": [{"structure_type": e["structure_type"], "bar_index": e["event_bar_index"], "price": e["price"]}
                   for e in mss],
    })
    assert ls.status_code == 200, ls.text
    end = max(e["confirmed_bar_index"] for e in mss)
    out = client.post("/api/evaluations", json={"run_ids": [run["run_id"]], "label_set_id": ls.json()["id"], "save": False,
                                                "protocol": {"target": "ict_mss", "time_tolerance_bars": 0,
                                                             "price_tolerance": 0, "coverage_start_index": 0,
                                                             "coverage_end_index": end}}).json()
    q = [r for g in out["groups"] for r in g.get("runs", [])][0]["quality"]
    assert q["true_positives"] == len(mss) and q["false_negatives"] == 0 and q["false_positives"] == 0
    st = run["stats"]["chi_so_thuat_toan"]
    assert st["mss"]["so"] == len(mss) and "breaker" in st["order_block"]          # OB là PD array (mặc định)


def test_cham_shift_bang_muc_tieu_ict_shift_va_doi_tang_shift_fvg():
    did = _m15()
    run = _run(did, session_calendar="none", **LEGACY_0_9)     # chế độ 0.9.x (đối chiếu)
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
    assert run["algorithm_version"] == "0.10.0"          # order flow có từ 0.3.0; 0.4.0 khung lớn; 0.5.0 OB/OTE; 0.6.x nhận diện; 0.7.0 thời gian; 0.8.0 PDH / PDL chạm; 0.9.0 trạng thái v2; 0.9.1 đường trend; 0.9.2 trạng thái vắt qua nghỉ theo lịch; 0.10.0 MSS + OB là PD array
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
    assert snap["algorithm_version"] == "0.10.0"
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
    assert run["algorithm_version"] == "0.10.0"
    ev = run["events"]
    kinds = {e["structure_type"] for e in ev}
    assert {"HTF_SWING_HIGH", "HTF_SWING_LOW", "HTF_FVG_UP", "HTF_FVG_DOWN", "HTF_PERIOD_HIGH", "HTF_PERIOD_LOW"} <= kinds
    assert kinds & {"PD_RESPECT_UP", "PD_RESPECT_DOWN", "PD_DISRESPECT_UP", "PD_DISRESPECT_DOWN"}
    for e in ev:
        assert e["structure_text_vi"] != e["structure_type"] and e["reason_text_vi"]
        if e["structure_type"].startswith("HTF_"):
            assert "htf" not in e["details"] and e["details"]["khung"] in ("H1", "H4", "D", "W")
        elif e["structure_type"] in ("SWING_HIGH", "SWING_LOW", "FVG_UP", "FVG_DOWN", "FVG_TOUCHED", "FVG_FILLED",
                                     "DISPLACEMENT_UP", "DISPLACEMENT_DOWN", "OB_EXPIRED", "OTE_EXPIRED"):
            assert "htf" not in e["details"]                         # 0.4.1 nguyên liệu, 0.5.0 hết hạn: không mang htf
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


def specs_show_if(params):
    """Tham số cơ bản chỉ hiện theo lựa chọn khác (show_if) — 0.10.0: MSS / shift."""
    return {p["name"]: [p["show_if"]["param"], p["show_if"]["value"]] for p in params
            if p.get("show_if") and not p["advanced"]}


def test_form_tham_so_gon_nhom_nang_cao_va_chu_cho_lua_chon():
    """Form tham số (giao diện tự sinh từ ParamSpec): 11 tham số hay chỉnh ở trên, 20 tham số cấu hình / đối chiếu gom vào
    «Tham số nâng cao»; lựa chọn có chữ tiếng Việt (giá trị gửi đi vẫn là mã); mô tả ngắn, không trích mã quyết định.
    Chỉ đổi hiển thị — chạy với mặc định vẫn nhận đúng mã cũ."""
    algos = {a["name"]: a for a in client.get("/api/algorithms").json()}
    params = algos["ict_structure"]["params"]
    basic = [p["name"] for p in params if not p["advanced"]]
    assert basic == ["pivot_left", "pivot_right", "structure_level", "eq_tol_atr", "k_disp", "body_min", "fvg_min_atr",
                     "min_pen_atr", "sweep_window", "doi_huong", "mss_chan_nen", "mss_chan_atr", "shift_window", "htf_list"]
    assert specs_show_if(params) == {"mss_chan_nen": ["doi_huong", "mss"], "mss_chan_atr": ["doi_huong", "mss"],
                                     "shift_window": ["doi_huong", "shift"]}
    specs = {p["name"]: p for p in params}
    assert specs["timeframe"]["advanced"] and specs["session_calendar"]["advanced"]
    for p in params:
        assert p["help_vi"] and len(p["help_vi"]) <= 170, p["name"]
        assert "plan §" not in p["help_vi"] and "(D" not in p["help_vi"], p["name"]
        if p["type"] == "choice" and p["choice_labels_vi"]:
            assert set(p["choice_labels_vi"]) == set(p["choices"]), p["name"]
    assert specs["gap_policy"]["choice_labels_vi"]["giu_muc_chan_cua_so"].startswith("chặn chỗ thiếu")
    assert specs["htf_events"]["choice_labels_vi"] == {"an": "có (ẩn trên chart)", "khong_phat": "không ghi"}
    # thuật toán khác không khai báo thì giữ như cũ (không nâng cao, không có chữ lựa chọn)
    assert all(p["advanced"] is False and p["choice_labels_vi"] is None for p in algos["swing_pivot"]["params"])


def test_ob_ote_v050_qua_api():
    """0.5.0: order block + OTE qua API — tham số nâng cao có chữ lựa chọn, sự kiện có câu giải thích, cột timeline,
    thống kê, pending_state; replay khớp run; tham số OTE sai → 400."""
    algos = {a["name"]: a for a in client.get("/api/algorithms").json()}
    specs = {p["name"]: p for p in algos["ict_structure"]["params"]}
    assert (specs["ob_bien_the"]["default"], specs["ob_neo"]["default"], specs["ote_tu"]["default"],
            specs["ote_den"]["default"], specs["ote_han"]["default"]) == ("than_chuoi", "shift", 0.62, 0.79, 96)
    assert all(specs[k]["advanced"] for k in ("ob_bien_the", "ob_neo", "ob_lui", "ob_han", "ote_tu", "ote_den",
                                                "ote_nhip_min_atr", "ote_han"))
    did = _m15()
    run = _run(did)
    ev = run["events"]
    new = [e for e in ev if e["structure_type"].startswith(("ORDER_BLOCK_", "OB_", "OTE_"))]
    kinds = {e["structure_type"] for e in new}
    assert {"ORDER_BLOCK_UP", "ORDER_BLOCK_DOWN", "OTE_ENTRY_UP", "OTE_ENTRY_DOWN"} <= kinds
    assert all(e["structure_text_vi"] != e["structure_type"] and e["reason_text_vi"] for e in new)
    tl = run["timeline"]
    assert {"ob_up_hi", "ob_up_lo", "ob_down_hi", "ob_down_lo", "ote_dir", "ote_x", "ote_h", "ote_lo",
            "ote_hi"} <= set(tl[-1])
    st = run["stats"]["chi_so_thuat_toan"]
    assert st["order_block"]["xac_nhan"] == sum(1 for e in new if e["structure_type"].startswith("ORDER_BLOCK_"))
    assert st["ote"]["vao"] == sum(1 for e in new if e["structure_type"].startswith("OTE_ENTRY_"))
    ps = run["pending_state"]
    assert ps["order_block"]["bien_the"] == "than_chuoi" and "dang_cho" in ps["ote"]
    rp = client.post("/api/replay", json={"dataset_id": did, "algorithm": "ict_structure",
                                          "params": {"timeframe": "M15"}})
    sid = rp.json()["session_id"]
    snap = client.post("/api/replay/%s/seek" % sid, json={"index": 500}).json()
    assert snap["timeline"][-1] == tl[500]
    assert snap["events"] == [e for e in ev if e["confirmed_bar_index"] <= 500]
    client.delete("/api/replay/%s" % sid)
    bad = client.post("/api/runs", json={"dataset_id": did, "algorithm": "ict_structure",
                                         "params": {"timeframe": "M15", "ote_tu": 0.8, "ote_den": 0.7}, "save": False})
    assert bad.status_code == 400 and "OTE" in bad.text


def test_nhan_dien_v060_qua_api():
    """0.6.0: lớp nhận diện qua API — tham số nâng cao, sự kiện STATE_* có câu giải thích, cột timeline nd_*, điểm thật
    trong thống kê và pending_state; replay khớp run; tham số sai → 400."""
    algos = {a["name"]: a for a in client.get("/api/algorithms").json()}
    specs = {p["name"]: p for p in algos["ict_structure"]["params"]}
    assert (specs["nd_bat"]["default"], specs["nd_muc_80"]["default"], specs["nd_muc_50"]["default"]) == (True, 0.905, 0.745)
    assert (specs["nd_kieu"]["default"], specs["nd_kieu"]["choices"]) == ("v2", ["v2", "v1"])
    assert all(specs[k]["advanced"] for k in ("nd_bat", "nd_muc_80", "nd_muc_50", "nd_mau_toi_da", "nd_mau_toi_thieu",
                                                "nd_er_nguong", "nd_giu_nen"))
    did = _m15()
    run = _run(did)
    st_ev = [e for e in run["events"] if e["structure_type"].startswith("STATE_")]
    assert st_ev and all(e["structure_text_vi"] != e["structure_type"] and e["reason_text_vi"] for e in st_ev)
    tl = run["timeline"]
    assert {"nd_trang_thai", "nd_tu", "nd_range_hi", "nd_1h_lo80", "nd_4h_hi50", "nd_p_tren_1h", "nd_duong", "nd_nen"} <= set(tl[-1])
    nd = run["stats"]["chi_so_thuat_toan"]["nhan_dien"]
    assert set(nd["khoang_va_cham"]) == {"1h", "4h"} and nd["trang_thai"]["so_lan_doi"] == len(st_ev)
    ps = run["pending_state"]["nhan_dien"]
    assert ps["tam_nen"] == {"1h": 4, "4h": 16} and set(ps["diem_that"]) == {"1h", "4h"}
    rp = client.post("/api/replay", json={"dataset_id": did, "algorithm": "ict_structure",
                                          "params": {"timeframe": "M15"}})
    sid = rp.json()["session_id"]
    snap = client.post("/api/replay/%s/seek" % sid, json={"index": 500}).json()
    assert snap["timeline"][-1] == tl[500]
    client.delete("/api/replay/%s" % sid)
    bad = client.post("/api/runs", json={"dataset_id": did, "algorithm": "ict_structure",
                                         "params": {"timeframe": "M15", "nd_muc_50": 0.95}, "save": False})
    assert bad.status_code == 400 and "Nhận diện" in bad.text
