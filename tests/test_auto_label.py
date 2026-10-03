"""Auto label hybrid: thuật toán đề xuất, người duyệt.

Kiểm tra:
* đề xuất chỉ nằm trong khoảng nến đã chọn và khớp đúng sự kiện thuật toán;
* đề xuất KHÔNG tự vào kho nhãn;
* nhãn chấp nhận từ đề xuất giữ nguồn gốc qua lưu / ghi đè / CSV;
* trang Đánh giá cảnh báo khi chấm thuật toán trên nhãn do chính nó đề xuất.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.service import load_bars
from core.engine import run_algorithm
from core.registry import create_algorithm

client = TestClient(app)


@pytest.fixture(scope="module")
def xau():
    client.post("/api/datasets/seed-samples")
    ds = client.get("/api/datasets").json()
    return [d for d in ds if d["symbol"] == "XAUUSD" and d["timeframe"] == "H1"][0]


def suggest(ds_id, **kw):
    body = {"dataset_id": ds_id, "algorithm": "swing_pivot"}
    body.update(kw)
    return client.post("/api/auto-label/suggest", json=body)


# ---------------------------------------------------------------------------
# Thuật toán nào đề xuất được
# ---------------------------------------------------------------------------


def test_chi_thuat_toan_sinh_nhan_cau_truc_moi_dung_duoc():
    algos = {a["name"]: a["label_types"] for a in client.get("/api/auto-label/algorithms").json()}
    assert "swing_pivot" in algos and "swing_hierarchy" in algos
    assert "indicator_baseline" not in algos and "hmm_online" not in algos
    assert "SWING_HIGH_L2" in algos["swing_hierarchy"]
    assert "CHOCH_UP" in algos["swing_pivot"]
    # HH/LH không phải loại nhãn tham chiếu -> không được đề xuất.
    assert "HH" not in algos["swing_pivot"]


def test_thuat_toan_khong_sinh_nhan_cau_truc_bi_tu_choi(xau):
    r = suggest(xau["id"], algorithm="indicator_baseline")
    assert r.status_code == 400
    assert "swing_pivot" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Khoảng nến
# ---------------------------------------------------------------------------


def test_de_xuat_chi_nam_trong_khoang_da_chon(xau):
    out = suggest(xau["id"], start_index=200, end_index=400).json()
    assert out["start_index"] == 200 and out["end_index"] == 400
    assert out["suggestions"], "Khoảng 200 nến phải có đề xuất"
    assert all(200 <= s["bar_index"] <= 400 for s in out["suggestions"])


def test_de_xuat_khop_dung_su_kien_thuat_toan(xau):
    """Đề xuất = đúng các sự kiện thuật toán sinh ra, lọc theo khoảng và loại."""
    out = suggest(xau["id"], start_index=300, end_index=700,
                  params={"left": 4, "right": 2}).json()
    _, bars, _ = load_bars(xau["id"])
    events = run_algorithm(bars, create_algorithm("swing_pivot", {"left": 4, "right": 2})).events
    label_types = set(out["types"])
    expected = sorted(
        {(e.structure_type, e.event_bar_index, round(e.price, 8))
         for e in events
         if e.structure_type in label_types and 300 <= e.event_bar_index <= 700}
    )
    got = sorted((s["structure_type"], s["bar_index"], round(s["price"], 8))
                 for s in out["suggestions"])
    assert got == expected


def test_loc_theo_loai_nhan(xau):
    out = suggest(xau["id"], types=["SWING_HIGH"]).json()
    assert out["suggestions"]
    assert {s["structure_type"] for s in out["suggestions"]} == {"SWING_HIGH"}


def test_loai_thuat_toan_khong_sinh_duoc_canh_bao(xau):
    out = suggest(xau["id"], types=["SWING_HIGH", "SWING_HIGH_L2"]).json()
    assert any("SWING_HIGH_L2" in w for w in out["warnings"])
    assert {s["structure_type"] for s in out["suggestions"]} == {"SWING_HIGH"}


def test_swing_hierarchy_de_xuat_duoc_dinh_day_cap_2(xau):
    out = suggest(xau["id"], algorithm="swing_hierarchy",
                  types=["SWING_HIGH_L2", "SWING_LOW_L2"]).json()
    assert out["suggestions"]
    assert {s["structure_type"] for s in out["suggestions"]} <= {"SWING_HIGH_L2", "SWING_LOW_L2"}


@pytest.mark.parametrize("start,end", [(-1, 10), (10, 5), (0, 10**6)])
def test_khoang_khong_hop_le_bi_tu_choi(xau, start, end):
    r = suggest(xau["id"], start_index=start, end_index=end)
    assert r.status_code == 400
    assert "không hợp lệ" in r.json()["detail"]


def test_khoang_cham_cuoi_dataset_co_canh_bao(xau):
    n = xau["row_count"]
    out = suggest(xau["id"], start_index=n - 20, end_index=n - 1).json()
    assert any("nến cuối" in w for w in out["warnings"])


def test_tham_so_sai_bao_loi(xau):
    r = suggest(xau["id"], params={"left": 0})
    assert r.status_code == 400


def test_de_xuat_ghi_ro_nguon_va_tham_so(xau):
    out = suggest(xau["id"], params={"left": 5, "right": 5}, start_index=0, end_index=500).json()
    s = out["suggestions"][0]
    assert s["source"] == "auto_accepted"
    assert s["source_algorithm"] == "swing_pivot"
    assert '"left": 5' in s["source_detail"] and "v1." in s["source_detail"]
    assert s["confirmed_bar_index"] >= s["bar_index"]


# ---------------------------------------------------------------------------
# Người duyệt: đề xuất không tự vào kho; nhãn chấp nhận giữ nguồn gốc
# ---------------------------------------------------------------------------


def test_de_xuat_khong_tu_luu_vao_kho(xau):
    before = len(client.get("/api/label-sets?dataset_id=%s" % xau["id"]).json())
    suggest(xau["id"])
    after = len(client.get("/api/label-sets?dataset_id=%s" % xau["id"]).json())
    assert after == before


def _accepted_set(ds_id, n_auto=6):
    sugs = suggest(ds_id, start_index=100, end_index=500, types=["SWING_HIGH", "SWING_LOW"]).json()["suggestions"]
    labels = [dict(s) for s in sugs[:n_auto]]
    labels.append({"structure_type": "SWING_HIGH", "bar_index": 900, "price": 2000.0})
    r = client.post("/api/label-sets", json={
        "dataset_id": ds_id, "annotator": "Nguoi duyet", "labels": labels})
    assert r.status_code == 200, r.text
    return r.json()


def test_luu_giu_nguon_goc_tung_nhan(xau):
    ls = _accepted_set(xau["id"])
    srcs = [l["source"] for l in ls["labels"]]
    assert srcs.count("auto_accepted") == 6 and srcs.count("human") == 1
    auto = [l for l in ls["labels"] if l["source"] == "auto_accepted"]
    assert all(l["source_algorithm"] == "swing_pivot" and l["source_detail"] for l in auto)

    listed = [s for s in client.get("/api/label-sets?dataset_id=%s" % xau["id"]).json()
              if s["id"] == ls["id"]][0]
    assert listed["n_auto"] == 6


def test_ghi_de_giu_nguon_goc(xau):
    ls = _accepted_set(xau["id"])
    r = client.put("/api/label-sets/%s" % ls["id"], json={
        "annotator": "Nguoi duyet", "labels": ls["labels"]})
    assert r.status_code == 200
    assert sum(1 for l in r.json()["labels"] if l["source"] == "auto_accepted") == 6


def test_csv_giu_nguon_goc(xau):
    ls = _accepted_set(xau["id"])
    text = client.get("/api/label-sets/%s/export.csv" % ls["id"]).text
    assert "source,source_algorithm,source_detail" in text
    back = client.post("/api/label-sets/parse-csv", json={
        "dataset_id": xau["id"], "csv_text": text}).json()
    assert sum(1 for l in back["labels"] if l["source"] == "auto_accepted") == 6


def test_csv_cu_khong_co_cot_nguon_la_nguoi_gan(xau):
    out = client.post("/api/label-sets/parse-csv", json={
        "dataset_id": xau["id"],
        "csv_text": "structure_type,bar_index,price\nSWING_HIGH,10,2000\n"}).json()
    assert out["labels"][0]["source"] == "human"


def test_nguon_khong_hop_le_bi_tu_choi(xau):
    r = client.post("/api/label-sets", json={
        "dataset_id": xau["id"], "annotator": "A",
        "labels": [{"structure_type": "SWING_HIGH", "bar_index": 10, "price": 1.0,
                    "source": "auto_chua_duyet"}]})
    assert r.status_code == 400


def test_nhan_auto_phai_ghi_thuat_toan(xau):
    r = client.post("/api/label-sets", json={
        "dataset_id": xau["id"], "annotator": "A",
        "labels": [{"structure_type": "SWING_HIGH", "bar_index": 10, "price": 1.0,
                    "source": "auto_accepted"}]})
    assert r.status_code == 400
    assert "source_algorithm" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Đánh giá: cảnh báo nhãn không độc lập
# ---------------------------------------------------------------------------


def test_danh_gia_canh_bao_khi_cham_chinh_thuat_toan_de_xuat(xau):
    ls = _accepted_set(xau["id"])
    run = client.post("/api/runs", json={"dataset_id": xau["id"], "algorithm": "swing_pivot"}).json()
    ev = client.post("/api/evaluations", json={
        "dataset_id": xau["id"], "run_ids": [run["run_id"]],
        "label_set_id": ls["id"], "save": False}).json()
    assert ev["canh_bao_nguon_nhan"]
    assert "6/7" in ev["canh_bao_nguon_nhan"][0]
    assert ev["nguon_nhan"]["auto_theo_thuat_toan"] == {"swing_pivot": 6}

    tab = client.post("/api/evaluate", json={
        "run_id": run["run_id"], "label_set_id": ls["id"]}).json()
    assert tab["canh_bao_nguon_nhan"]


def test_khong_canh_bao_khi_cham_thuat_toan_khac(xau):
    ls = _accepted_set(xau["id"])
    run = client.post("/api/runs", json={
        "dataset_id": xau["id"], "algorithm": "swing_hierarchy"}).json()
    ev = client.post("/api/evaluations", json={
        "dataset_id": xau["id"], "run_ids": [run["run_id"]],
        "label_set_id": ls["id"], "save": False}).json()
    assert ev["canh_bao_nguon_nhan"] == []


def test_bo_nhan_toan_nguoi_gan_khong_canh_bao(xau):
    ls = client.post("/api/label-sets", json={
        "dataset_id": xau["id"], "annotator": "A",
        "labels": [{"structure_type": "SWING_HIGH", "bar_index": 50, "price": 2000.0}]}).json()
    run = client.post("/api/runs", json={"dataset_id": xau["id"], "algorithm": "swing_pivot"}).json()
    ev = client.post("/api/evaluations", json={
        "dataset_id": xau["id"], "run_ids": [run["run_id"]],
        "label_set_id": ls["id"], "save": False}).json()
    assert ev["canh_bao_nguon_nhan"] == []
    assert ev["nguon_nhan"]["nguoi_gan"] == 1


def test_trang_gan_nhan_co_khung_auto_label():
    html = client.get("/gan-nhan").text
    for el in ('id="auto-algo"', 'id="auto-start"', 'id="auto-end"', 'id="auto-range-view"',
               'id="auto-run"', 'id="auto-accept"', 'id="auto-reject"',
               'id="auto-accept-all"', 'id="auto-table"'):
        assert el in html, el


# ---------------------------------------------------------------------------
# Nhãn auto được người sửa sau khi chấp nhận
# ---------------------------------------------------------------------------


def test_nhan_auto_nguoi_da_sua_duoc_luu_va_dem_rieng(xau):
    sugs = suggest(xau["id"], start_index=100, end_index=500,
                   types=["SWING_HIGH"]).json()["suggestions"]
    accepted = [dict(s) for s in sugs[:4]]
    edited = dict(sugs[4])
    edited["bar_index"] += 1          # người dời sang nến bên cạnh
    edited["source"] = "auto_edited"
    ls = client.post("/api/label-sets", json={
        "dataset_id": xau["id"], "annotator": "Nguoi sua",
        "labels": accepted + [edited]}).json()
    srcs = sorted(l["source"] for l in ls["labels"])
    assert srcs == ["auto_accepted"] * 4 + ["auto_edited"]

    run = client.post("/api/runs", json={"dataset_id": xau["id"], "algorithm": "swing_pivot"}).json()
    ev = client.post("/api/evaluations", json={
        "dataset_id": xau["id"], "run_ids": [run["run_id"]],
        "label_set_id": ls["id"], "save": False}).json()
    prov = ev["nguon_nhan"]
    assert prov["auto_da_duyet"] == 4 and prov["auto_da_sua"] == 1
    assert prov["auto_sua_theo_thuat_toan"] == {"swing_pivot": 1}
    assert len(ev["canh_bao_nguon_nhan"]) == 2
    assert "người sửa" in ev["canh_bao_nguon_nhan"][1]
