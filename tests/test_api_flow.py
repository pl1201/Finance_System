"""Test luồng hoàn chỉnh qua API: nạp dữ liệu → chạy → replay → lưu → mở lại
→ so sánh → xuất kết quả.

Dùng thư mục dữ liệu tạm (xem ``conftest.py``) nên không ảnh hưởng ``data/``.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def dataset_id():
    r = client.post("/api/datasets/seed-samples")
    assert r.status_code == 200, r.text
    ds = client.get("/api/datasets").json()
    xau = [d for d in ds if d["symbol"] == "XAUUSD" and d["timeframe"] == "H1"]
    assert xau, "Phải có dataset XAUUSD H1 mô phỏng"
    return xau[0]["id"]


# ---------------------------------------------------------------------------
# Hệ thống và dữ liệu
# ---------------------------------------------------------------------------


def test_health_canh_bao_khong_phai_he_thong_giao_dich():
    h = client.get("/api/health").json()
    assert h["status"] == "ok"
    assert "không gửi lệnh" in h["canh_bao_vi"]


def test_danh_sach_thuat_toan_co_mo_ta_tham_so():
    algos = client.get("/api/algorithms").json()
    names = [a["name"] for a in algos]
    assert "swing_pivot" in names
    sp = [a for a in algos if a["name"] == "swing_pivot"][0]
    params = {p["name"]: p for p in sp["params"]}
    assert params["left"]["default"] == 3 and params["right"]["default"] == 3
    assert all(p["label_vi"] for p in sp["params"])


def test_dataset_mau_duoc_danh_dau_mo_phong(dataset_id):
    ds = client.get("/api/datasets/%s" % dataset_id).json()
    assert ds["is_synthetic"] is True
    assert "MÔ PHỎNG" in ds["name"]
    assert "MÔ PHỎNG" in ds["notes"]
    assert ds["source_timezone"] == "UTC+00:00"
    assert ds["timestamp_convention"] == "open"
    assert ds["checksum_sha256"]
    assert ds["quality"]["rows_out"] == ds["row_count"]


def test_seed_lai_khong_tao_ban_sao(dataset_id):
    before = len(client.get("/api/datasets").json())
    out = client.post("/api/datasets/seed-samples").json()
    after = len(client.get("/api/datasets").json())
    assert after == before
    assert all(c.get("skipped") for c in out["created"])


def test_import_thieu_khai_bao_bi_tu_choi():
    csv = "time,open,high,low,close\n2024-01-02 00:00:00,1,2,0.5,1.5\n"
    files = {"file": ("x.csv", io.BytesIO(csv.encode()), "text/csv")}
    r = client.post(
        "/api/datasets/import",
        files=files,
        data={"symbol": "XAUUSD", "source_timezone": "UTC", "timestamp_convention": "auto"},
    )
    assert r.status_code == 400
    assert "MỞ nến" in r.json()["detail"]


def test_import_va_xoa_dataset_thuc():
    lines = ["time,open,high,low,close,volume"]
    for i in range(80):
        base = 1.08 + i * 0.0002
        lines.append(
            "2024-01-02 %02d:%02d:00,%.5f,%.5f,%.5f,%.5f,100"
            % (i // 4, (i % 4) * 15, base, base + 0.0008, base - 0.0008, base + 0.0003)
        )
    csv = "\n".join(lines) + "\n"
    files = {"file": ("eurusd.csv", io.BytesIO(csv.encode()), "text/csv")}
    r = client.post(
        "/api/datasets/import",
        files=files,
        data={
            "symbol": "EURUSD", "timeframe": "M15", "source": "test",
            "source_timezone": "UTC+2", "timestamp_convention": "close",
            "price_type": "bid", "name": "EURUSD test",
        },
    )
    assert r.status_code == 200, r.text
    ds = r.json()
    assert ds["row_count"] == 80
    assert ds["is_synthetic"] is False
    assert ds["source_timezone"] == "UTC+02:00"
    assert ds["timestamp_convention"] == "close"
    # UTC+2 -> nến 00:00 giờ nguồn thành 22:00 ngày hôm trước theo UTC.
    assert ds["start_time"].startswith("2024-01-01T22:00")

    # Nhập lại đúng nội dung đó phải bị chặn vì trùng checksum.
    files = {"file": ("eurusd.csv", io.BytesIO(csv.encode()), "text/csv")}
    dup = client.post(
        "/api/datasets/import",
        files=files,
        data={"symbol": "EURUSD", "timeframe": "M15", "source_timezone": "UTC+2",
              "timestamp_convention": "close"},
    )
    assert dup.status_code == 400 and "trùng" in dup.json()["detail"]

    assert client.delete("/api/datasets/%s" % ds["id"]).status_code == 200
    assert client.get("/api/datasets/%s" % ds["id"]).status_code == 404


def test_preview_csv_de_xuat_anh_xa():
    csv = (
        "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\n"
        "2024.01.02\t00:00:00\t2000\t2005\t1998\t2003\t10\n"
        "2024.01.02\t01:00:00\t2003\t2008\t2001\t2006\t12\n"
    )
    files = {"file": ("mt5.csv", io.BytesIO(csv.encode()), "text/csv")}
    pv = client.post("/api/datasets/preview", files=files).json()
    assert pv["delimiter"] == "\t"
    assert pv["needs_manual_mapping"] is False
    assert pv["suggested_mapping"]["high"] == "HIGH"


# ---------------------------------------------------------------------------
# Chạy, lưu, mở lại
# ---------------------------------------------------------------------------


def test_chay_thu_va_luu(dataset_id):
    r = client.post("/api/runs", json={
        "dataset_id": dataset_id, "algorithm": "swing_pivot",
        "params": {"left": 3, "right": 3}, "label": "baseline 3/3",
    })
    assert r.status_code == 200, r.text
    run = r.json()
    assert run["saved"] is True
    assert run["events"], "Phải có sự kiện"
    assert run["stats"]["tong_su_kien"] == len(run["events"])
    assert len(run["timeline"]) == run["bars_processed"]
    # Không được bịa các chỉ số chưa có cơ sở: kiểm tra KHOÁ thống kê,
    # không kiểm tra chuỗi văn bản (câu ghi chú có nhắc các từ này).
    cam_keys = {"accuracy", "win_rate", "winrate", "pnl", "profit", "sharpe", "precision", "recall"}
    assert cam_keys.isdisjoint(k.lower() for k in run["stats"])
    assert "không báo cáo accuracy" in run["stats"]["ghi_chu_vi"]


def test_chay_indicator_baseline_co_su_kien_va_sma_warmup_null(dataset_id):
    r = client.post("/api/runs", json={
        "dataset_id": dataset_id, "algorithm": "indicator_baseline", "save": False,
    })
    assert r.status_code == 200, r.text
    run = r.json()
    assert run["events"], "Baseline phải phát sự kiện sau warm-up"
    kinds = {e["structure_type"] for e in run["events"]}
    assert kinds <= {
        "BASELINE_UP", "BASELINE_DOWN", "BASELINE_RANGE", "BASELINE_UNCERTAIN",
    }
    assert run["timeline"][0]["sma"] is None
    assert any(p.get("sma") is not None for p in run["timeline"])


def test_mo_lai_thi_nghiem_sau_khi_luu(dataset_id):
    created = client.post("/api/runs", json={
        "dataset_id": dataset_id, "params": {"left": 4, "right": 2}, "label": "4/2",
    }).json()
    run_id = created["run_id"]

    got = client.get("/api/runs/%s" % run_id).json()
    assert got["label"] == "4/2"
    assert got["params"] == created["params"]
    assert len(got["events"]) == len(created["events"])
    assert got["events"][0]["event_id"] == created["events"][0]["event_id"]
    assert got["dataset_checksum"] == created["dataset_checksum"]

    # Chạy lại đúng cấu hình đã lưu phải cho kết quả giống hệt.
    again = client.post("/api/runs", json={
        "dataset_id": got["dataset_id"], "algorithm": got["algorithm"],
        "params": got["params"], "range_start": got["range_start"],
        "range_end": got["range_end"], "save": False,
    }).json()
    assert [e["event_id"] for e in again["events"]] == [e["event_id"] for e in got["events"]]
    assert [e["confirmed_at"] for e in again["events"]] == [e["confirmed_at"] for e in got["events"]]


def test_manifest_du_de_chay_lai(dataset_id):
    run_id = client.post("/api/runs", json={"dataset_id": dataset_id}).json()["run_id"]
    m = client.get("/api/runs/%s/manifest" % run_id).json()
    assert m["run"]["params"]["left"] == 3
    assert m["dataset"]["checksum_sha256"]
    assert m["run"]["algorithm_version"]


def test_khoang_thoi_gian_gioi_han_du_lieu(dataset_id):
    ds = client.get("/api/datasets/%s" % dataset_id).json()
    full = client.post("/api/runs", json={"dataset_id": dataset_id, "save": False}).json()
    part = client.post("/api/runs", json={
        "dataset_id": dataset_id, "save": False,
        "range_start": ds["start_time"], "range_end": "2024-02-01T00:00:00+00:00",
    }).json()
    assert part["bars_processed"] < full["bars_processed"]
    assert part["range_end"] <= "2024-02-01T00:00:00+00:00"


def test_tham_so_sai_tra_loi_400(dataset_id):
    r = client.post("/api/runs", json={"dataset_id": dataset_id, "params": {"left": 0}})
    assert r.status_code == 400
    assert "left" in r.json()["detail"]

    r2 = client.post("/api/runs", json={"dataset_id": dataset_id, "algorithm": "khong_ton_tai"})
    assert r2.status_code == 400

    r3 = client.post("/api/runs", json={"dataset_id": "ds_khong_co"})
    assert r3.status_code == 400


def test_khoang_rong_bao_loi_ro_rang(dataset_id):
    r = client.post("/api/runs", json={
        "dataset_id": dataset_id,
        "range_start": "2030-01-01T00:00:00+00:00",
        "range_end": "2030-02-01T00:00:00+00:00",
    })
    assert r.status_code == 400
    assert "không có nến" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Replay qua API
# ---------------------------------------------------------------------------


def test_replay_qua_api_khong_ro_ri_tuong_lai(dataset_id):
    full = client.post("/api/runs", json={"dataset_id": dataset_id, "save": False}).json()

    snap = client.post("/api/replay", json={"dataset_id": dataset_id}).json()
    sid = snap["session_id"]
    assert snap["cursor"] == -1 and snap["events"] == []

    at300 = client.post("/api/replay/%s/seek" % sid, json={"index": 300}).json()
    assert at300["cursor"] == 300
    assert all(e["confirmed_bar_index"] <= 300 for e in at300["events"])

    expected = [e["event_id"] for e in full["events"] if e["confirmed_bar_index"] <= 300]
    assert [e["event_id"] for e in at300["events"]] == expected

    fwd = client.post("/api/replay/%s/step" % sid, json={"n": 60}).json()
    assert fwd["cursor"] == 360
    back = client.post("/api/replay/%s/back" % sid, json={"n": 60}).json()
    assert back["cursor"] == 300
    assert [e["event_id"] for e in back["events"]] == expected

    reset = client.post("/api/replay/%s/reset" % sid).json()
    assert reset["cursor"] == -1 and reset["events"] == []
    assert reset["data_status"] == "WARMUP_INSUFFICIENT"

    bars = client.get("/api/replay/%s/bars" % sid).json()["bars"]
    assert len(bars) == full["bars_processed"]

    assert client.delete("/api/replay/%s" % sid).status_code == 200
    assert client.get("/api/replay/%s" % sid).status_code == 400


def test_replay_phien_khong_ton_tai_bao_loi_ro():
    r = client.post("/api/replay/rp_khong_co/step", json={"n": 1})
    assert r.status_code == 400
    assert "không còn tồn tại" in r.json()["detail"]


# ---------------------------------------------------------------------------
# So sánh và xuất
# ---------------------------------------------------------------------------


def test_so_sanh_hai_cau_hinh_tren_cung_dataset(dataset_id):
    a = client.post("/api/runs", json={
        "dataset_id": dataset_id, "params": {"left": 3, "right": 3}, "label": "3/3"}).json()
    b = client.post("/api/runs", json={
        "dataset_id": dataset_id, "params": {"left": 6, "right": 6}, "label": "6/6"}).json()

    c = client.post("/api/compare", json={"run_id_a": a["run_id"], "run_id_b": b["run_id"]}).json()
    assert c["canh_bao"] == []
    assert c["so_su_kien_chung"] >= 0
    assert c["chi_co_o_a"] > 0
    types = {r["structure_type"] for r in c["so_sanh_theo_loai"]}
    assert "SWING_HIGH" in types
    cam_keys = {"accuracy", "win_rate", "pnl", "profit", "sharpe"}
    assert cam_keys.isdisjoint(k.lower() for k in c)
    assert "nhãn tham chiếu" in c["ghi_chu_vi"]


def test_so_sanh_khac_khoang_thoi_gian_co_canh_bao(dataset_id):
    a = client.post("/api/runs", json={"dataset_id": dataset_id}).json()
    b = client.post("/api/runs", json={
        "dataset_id": dataset_id, "range_end": "2024-02-01T00:00:00+00:00"}).json()
    c = client.post("/api/compare", json={"run_id_a": a["run_id"], "run_id_b": b["run_id"]}).json()
    assert any("KHOẢNG THỜI GIAN KHÁC NHAU" in w for w in c["canh_bao"])


def test_xuat_csv_su_kien(dataset_id):
    run = client.post("/api/runs", json={"dataset_id": dataset_id, "label": "export"}).json()
    r = client.get("/api/runs/%s/export.csv" % run["run_id"])
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().split("\n")
    assert len(lines) == len(run["events"]) + 1
    header = lines[0].split(",")
    for col in ("event_time", "confirmed_at", "confirmation_lag_bars", "reason_code",
                "algorithm_version", "reference_event_id"):
        assert col in header


def test_lich_su_va_xoa_lan_chay(dataset_id):
    run = client.post("/api/runs", json={"dataset_id": dataset_id, "label": "sẽ xoá"}).json()
    ids = [r["run_id"] for r in client.get("/api/runs").json()]
    assert run["run_id"] in ids

    by_ds = client.get("/api/runs?dataset_id=%s" % dataset_id).json()
    assert all(r["dataset_id"] == dataset_id for r in by_ds)

    assert client.delete("/api/runs/%s" % run["run_id"]).status_code == 200
    assert client.get("/api/runs/%s" % run["run_id"]).status_code == 404
    assert client.get("/api/runs/%s/export.csv" % run["run_id"]).status_code == 400


def test_khong_luu_khi_save_false(dataset_id):
    before = len(client.get("/api/runs").json())
    out = client.post("/api/runs", json={"dataset_id": dataset_id, "save": False}).json()
    assert out["saved"] is False
    assert len(client.get("/api/runs").json()) == before
    assert client.get("/api/runs/%s" % out["run_id"]).status_code == 404


def test_giao_dien_duoc_phuc_vu():
    r = client.get("/")
    assert r.status_code == 200
    assert "Market Structure Lab" in r.text
    assert client.get("/app/js/app.js").status_code == 200
    assert client.get("/app/vendor/lightweight-charts.standalone.production.js").status_code == 200
