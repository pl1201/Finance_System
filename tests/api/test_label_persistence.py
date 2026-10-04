"""Test lưu nhãn: ghi đè có truy vết, xuất/nhập CSV, chặn nhãn sai dataset.

Bổ sung cho ``test_labels.py`` (quy tắc ghép) và ``test_label_page.py``
(trang gán nhãn). Ở đây tập trung vào việc GIỮ ĐƯỢC công sức gán nhãn.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def datasets():
    client.post("/api/datasets/seed-samples")
    ds = client.get("/api/datasets").json()
    xau = [d for d in ds if d["symbol"] == "XAUUSD" and d["timeframe"] == "H1"][0]
    other = [d for d in ds if d["id"] != xau["id"]][0]
    return xau, other


def make_labels(*specs):
    return [
        {"structure_type": t, "bar_index": i, "price": p, "notes": n}
        for (t, i, p, n) in specs
    ]


def create_set(dataset_id, labels, annotator="Nguoi gan A", version="1"):
    r = client.post("/api/label-sets", json={
        "dataset_id": dataset_id, "annotator": annotator,
        "version": version, "rubric_vi": "dinh/day mat thuong", "labels": labels,
    })
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Kiểm tra nhãn thuộc đúng dataset
# ---------------------------------------------------------------------------


def test_nhan_ngoai_pham_vi_nen_bi_tu_choi(datasets):
    xau, _ = datasets
    n = xau["row_count"]
    r = client.post("/api/label-sets", json={
        "dataset_id": xau["id"], "annotator": "A", "version": "1",
        "labels": make_labels(("SWING_HIGH", n + 5, 2000.0, "")),
    })
    assert r.status_code == 400
    assert "ngoài dataset" in r.json()["detail"]
    assert str(n - 1) in r.json()["detail"]


def test_bar_index_am_bi_tu_choi(datasets):
    xau, _ = datasets
    r = client.post("/api/label-sets", json={
        "dataset_id": xau["id"], "annotator": "A",
        "labels": make_labels(("SWING_LOW", -1, 2000.0, "")),
    })
    assert r.status_code == 400


def test_loai_nhan_la_bi_tu_choi_kem_danh_sach_hop_le(datasets):
    xau, _ = datasets
    r = client.post("/api/label-sets", json={
        "dataset_id": xau["id"], "annotator": "A",
        "labels": make_labels(("KHONG_CO_LOAI_NAY", 10, 2000.0, "")),
    })
    assert r.status_code == 400
    assert "SWING_HIGH" in r.json()["detail"]


def test_nhan_trung_bi_gop_va_bao_canh_bao(datasets):
    xau, _ = datasets
    out = create_set(xau["id"], make_labels(
        ("SWING_HIGH", 100, 2010.0, "lan 1"),
        ("SWING_HIGH", 100, 2010.0, "lan 2"),
        ("SWING_LOW", 100, 1990.0, "khac loai nen giu"),
    ))
    assert len(out["labels"]) == 2
    assert any("trùng" in w for w in out["warnings"])


def test_nhan_duoc_sap_theo_nen(datasets):
    xau, _ = datasets
    out = create_set(xau["id"], make_labels(
        ("SWING_HIGH", 300, 2010.0, ""),
        ("SWING_LOW", 100, 1990.0, ""),
        ("SWING_HIGH", 200, 2005.0, ""),
    ))
    assert [l["bar_index"] for l in out["labels"]] == [100, 200, 300]


# ---------------------------------------------------------------------------
# Ghi đè bộ nhãn
# ---------------------------------------------------------------------------


def test_luu_moi_tao_bo_moi_khong_ghi_de(datasets):
    xau, _ = datasets
    a = create_set(xau["id"], make_labels(("SWING_HIGH", 50, 2000.0, "")))
    b = create_set(xau["id"], make_labels(("SWING_HIGH", 60, 2001.0, "")))
    assert a["id"] != b["id"]
    assert a["revision"] == 1 and b["revision"] == 1
    again = client.get("/api/label-sets/%s" % a["id"]).json()
    assert [l["bar_index"] for l in again["labels"]] == [50]


def test_ghi_de_tang_revision_va_thay_noi_dung(datasets):
    xau, _ = datasets
    ls = create_set(xau["id"], make_labels(("SWING_HIGH", 50, 2000.0, "cu")))
    assert ls["revision"] == 1

    r = client.put("/api/label-sets/%s" % ls["id"], json={
        "annotator": "Nguoi gan B", "version": "2", "rubric_vi": "rubric moi",
        "labels": make_labels(
            ("SWING_LOW", 70, 1990.0, "moi"),
            ("SWING_HIGH", 80, 2020.0, "moi"),
        ),
    })
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["revision"] == 2
    assert out["annotator"] == "Nguoi gan B"
    assert out["version"] == "2"
    assert out["rubric_vi"] == "rubric moi"
    assert [l["bar_index"] for l in out["labels"]] == [70, 80]
    assert out["updated_at"] and out["updated_at"] >= out["created_at"]

    # Đọc lại từ DB phải khớp, không còn nhãn cũ.
    again = client.get("/api/label-sets/%s" % ls["id"]).json()
    assert [l["bar_index"] for l in again["labels"]] == [70, 80]
    assert again["revision"] == 2


def test_ghi_de_giu_nguyen_dataset(datasets):
    xau, other = datasets
    ls = create_set(xau["id"], make_labels(("SWING_HIGH", 50, 2000.0, "")))
    client.put("/api/label-sets/%s" % ls["id"], json={
        "annotator": "A", "labels": make_labels(("SWING_HIGH", 60, 2000.0, "")),
    })
    assert client.get("/api/label-sets/%s" % ls["id"]).json()["dataset_id"] == xau["id"]


def test_ghi_de_van_kiem_tra_pham_vi_nen(datasets):
    xau, _ = datasets
    ls = create_set(xau["id"], make_labels(("SWING_HIGH", 50, 2000.0, "")))
    r = client.put("/api/label-sets/%s" % ls["id"], json={
        "annotator": "A",
        "labels": make_labels(("SWING_HIGH", xau["row_count"] + 1, 2000.0, "")),
    })
    assert r.status_code == 400
    # Thất bại thì nội dung cũ phải còn nguyên.
    assert [l["bar_index"] for l in client.get("/api/label-sets/%s" % ls["id"]).json()["labels"]] == [50]


def test_ghi_de_thieu_ten_nguoi_gan_bi_tu_choi(datasets):
    xau, _ = datasets
    ls = create_set(xau["id"], make_labels(("SWING_HIGH", 50, 2000.0, "")))
    r = client.put("/api/label-sets/%s" % ls["id"], json={
        "annotator": "   ", "labels": make_labels(("SWING_HIGH", 60, 2000.0, "")),
    })
    assert r.status_code == 400
    assert "người gán" in r.json()["detail"]


def test_ghi_de_bo_khong_ton_tai(datasets):
    r = client.put("/api/label-sets/lab_khong_co", json={
        "annotator": "A", "labels": []})
    assert r.status_code == 400


def test_ghi_de_bo_da_dung_trong_danh_gia_phai_xac_nhan(datasets):
    xau, _ = datasets
    ls = create_set(xau["id"], make_labels(
        ("SWING_HIGH", 100, 2010.0, ""), ("SWING_LOW", 120, 1990.0, "")))
    run = client.post("/api/runs", json={
        "dataset_id": xau["id"], "algorithm": "swing_pivot", "label": "cho danh gia",
    }).json()

    ev = client.post("/api/evaluations", json={
        "dataset_id": xau["id"], "run_ids": [run["run_id"]],
        "label_set_id": ls["id"], "save": True,
    })
    assert ev.status_code == 200, ev.text
    assert ev.json()["saved"] is True

    # Đánh giá đã lưu phải ghi lại BẢN nhãn đã dùng.
    used = client.get("/api/label-sets/%s" % ls["id"]).json()["used_by_evaluations"]
    assert used and used[0]["label_set_revision"] == 1

    # Ghi đè không xác nhận -> chặn, nội dung giữ nguyên.
    blocked = client.put("/api/label-sets/%s" % ls["id"], json={
        "annotator": "A", "labels": make_labels(("SWING_HIGH", 150, 2010.0, "")),
    })
    assert blocked.status_code == 400
    assert "đánh giá đã lưu" in blocked.json()["detail"]
    assert client.get("/api/label-sets/%s" % ls["id"]).json()["revision"] == 1

    # Xác nhận -> cho ghi đè, nêu rõ kết quả cũ gắn bản cũ.
    ok = client.put("/api/label-sets/%s" % ls["id"], json={
        "annotator": "A", "confirm_overwrite": True,
        "labels": make_labels(("SWING_HIGH", 150, 2010.0, "")),
    })
    assert ok.status_code == 200, ok.text
    assert ok.json()["revision"] == 2
    assert "KHÔNG tự tính lại" in ok.json()["ghi_chu_vi"]


# ---------------------------------------------------------------------------
# Xuất / nhập CSV
# ---------------------------------------------------------------------------


def test_xuat_csv_va_nap_lai_cho_dung_nhan(datasets):
    xau, _ = datasets
    labels = make_labels(
        ("SWING_HIGH", 120, 2011.5, "dinh ro"),
        ("SWING_LOW", 140, 1988.25, ""),
        ("CHOCH_UP", 160, 2005.0, "doi huong"),
    )
    ls = create_set(xau["id"], labels, annotator="Nguoi gan CSV")

    r = client.get("/api/label-sets/%s/export.csv" % ls["id"])
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    text = r.text
    assert "structure_type,bar_index,price,notes" in text
    assert "dataset_checksum=%s" % xau["checksum_sha256"] in text
    assert "annotator=Nguoi gan CSV" in text

    back = client.post("/api/label-sets/parse-csv", json={
        "dataset_id": xau["id"], "csv_text": text,
    })
    assert back.status_code == 200, back.text
    out = back.json()
    assert out["warnings"] == []
    assert [(l["structure_type"], l["bar_index"], l["price"]) for l in out["labels"]] == [
        ("SWING_HIGH", 120, 2011.5),
        ("SWING_LOW", 140, 1988.25),
        ("CHOCH_UP", 160, 2005.0),
    ]
    assert out["labels"][0]["notes"] == "dinh ro"
    assert out["meta_trong_file"]["label_set_id"] == ls["id"]


def test_nap_csv_toi_gian_khong_co_dong_chu_thich(datasets):
    xau, _ = datasets
    csv_text = "structure_type,bar_index,price\nSWING_HIGH,10,2000\nSWING_LOW,20,1990\n"
    out = client.post("/api/label-sets/parse-csv", json={
        "dataset_id": xau["id"], "csv_text": csv_text}).json()
    assert len(out["labels"]) == 2
    assert out["labels"][0]["notes"] == ""


def test_nap_csv_thieu_cot_bao_loi_ro(datasets):
    xau, _ = datasets
    r = client.post("/api/label-sets/parse-csv", json={
        "dataset_id": xau["id"], "csv_text": "structure_type,gia\nSWING_HIGH,2000\n"})
    assert r.status_code == 400
    assert "bar_index" in r.json()["detail"]


def test_nap_csv_rong_bao_loi(datasets):
    xau, _ = datasets
    r = client.post("/api/label-sets/parse-csv", json={
        "dataset_id": xau["id"], "csv_text": "# chi co chu thich\n"})
    assert r.status_code == 400


def test_nap_csv_sai_dataset_thi_canh_bao_hoac_tu_choi(datasets):
    """CSV của dataset khác: hoặc báo lỗi ngoài phạm vi, hoặc cảnh báo checksum."""
    xau, other = datasets
    ls = create_set(xau["id"], make_labels(("SWING_HIGH", 120, 2011.5, "")))
    text = client.get("/api/label-sets/%s/export.csv" % ls["id"]).text

    r = client.post("/api/label-sets/parse-csv", json={
        "dataset_id": other["id"], "csv_text": text})
    if r.status_code == 400:
        assert "ngoài dataset" in r.json()["detail"]
    else:
        assert any("checksum" in w for w in r.json()["warnings"])


def test_nap_csv_khong_tu_luu_vao_kho(datasets):
    xau, _ = datasets
    before = len(client.get("/api/label-sets?dataset_id=%s" % xau["id"]).json())
    client.post("/api/label-sets/parse-csv", json={
        "dataset_id": xau["id"],
        "csv_text": "structure_type,bar_index,price\nSWING_HIGH,10,2000\n"})
    after = len(client.get("/api/label-sets?dataset_id=%s" % xau["id"]).json())
    assert after == before, "parse-csv chỉ đọc vào nháp, không được tự lưu"


def test_xuat_csv_bo_khong_ton_tai():
    assert client.get("/api/label-sets/lab_khong_co/export.csv").status_code == 400
