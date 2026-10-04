"""Trang Gán nhãn: phục vụ HTML, lưu bộ theo đúng dataset/khung, không bịa F1."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from tests.helpers import assert_page_scripts_served

client = TestClient(app)


def _xau(tf: str) -> str:
    client.post("/api/datasets/seed-samples")
    ds = client.get("/api/datasets").json()
    xau = [d for d in ds if d["symbol"] == "XAUUSD" and d["timeframe"] == tf]
    assert xau, "Phải có dataset XAUUSD %s mô phỏng" % tf
    return xau[0]["id"]


def test_trang_gan_nhan_duoc_phuc_vu():
    r = client.get("/gan-nhan")
    assert r.status_code == 200
    assert "Gán nhãn" in r.text
    assert "Thử nghiệm" in r.text
    assert "Đánh giá thuật toán" in r.text
    assert 'id="tf-switch"' in r.text
    assert 'id="label-chart"' in r.text
    assert "Người gán" in r.text
    assert "M5" in r.text and "M15" in r.text
    srcs = assert_page_scripts_served(client, "/gan-nhan")
    assert srcs[-1] == "/app/js/pages/label/main.js"


def test_nav_ba_trang_co_gan_nhan():
    for path in ("/", "/danh-gia", "/gan-nhan"):
        html = client.get(path).text
        assert 'href="/gan-nhan"' in html
        assert 'href="/danh-gia"' in html


def test_gan_nhan_khong_can_lan_chay():
    ds = _xau("M15")
    bars = client.get("/api/datasets/%s/bars" % ds).json()
    assert bars["dataset"]["timeframe"] == "M15"
    assert len(bars["bars"]) >= 100
    assert "index" in bars["bars"][0]
    assert "high" in bars["bars"][0]


def test_luu_nhan_m15_khong_hien_tren_m5():
    m15 = _xau("M15")
    m5 = _xau("M5")
    bars = client.get("/api/datasets/%s/bars" % m15).json()["bars"]
    b = bars[40]
    ls = client.post("/api/label-sets", json={
        "dataset_id": m15,
        "annotator": "Tester M15",
        "version": "1",
        "rubric_vi": "Đỉnh mắt thường trên nến đóng M15.",
        "labels": [{
            "structure_type": "SWING_HIGH",
            "bar_index": b["index"],
            "price": b["high"],
            "notes": "",
        }],
    }).json()
    assert ls["id"].startswith("lab_")
    assert ls["annotator"] == "Tester M15"
    assert len(ls["labels"]) == 1

    on_m15 = client.get("/api/label-sets", params={"dataset_id": m15}).json()
    on_m5 = client.get("/api/label-sets", params={"dataset_id": m5}).json()
    ids15 = {x["id"] for x in on_m15}
    ids5 = {x["id"] for x in on_m5}
    assert ls["id"] in ids15
    assert ls["id"] not in ids5


def test_luu_nhan_thieu_ten_nguoi_gan_bi_tu_choi():
    ds = _xau("M5")
    r = client.post("/api/label-sets", json={
        "dataset_id": ds,
        "annotator": "  ",
        "version": "1",
        "rubric_vi": "",
        "labels": [],
    })
    assert r.status_code == 400
    assert "người gán" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Nút lưu / giữ nháp (bổ sung v0.3.5)
# ---------------------------------------------------------------------------


def test_hai_trang_deu_nap_module_giu_nhap():
    """`labeldraft.js` phải được nạp ở cả trang chính và trang Gán nhãn."""
    assert client.get("/app/js/lib/labeldraft.js").status_code == 200
    for path in ("/", "/gan-nhan"):
        assert "/app/js/lib/labeldraft.js" in assert_page_scripts_served(client, path), path


def test_tab_nhan_tren_trang_chinh_co_du_nut_luu():
    html = client.get("/").text
    for el in (
        'id="btn-save-labels"',       # lưu thành bộ mới
        'id="btn-update-labels"',     # ghi đè bộ đang mở
        'id="btn-export-labels"',     # xuất CSV
        'id="btn-import-labels"',     # nhập CSV
        'id="label-import-file"',
        'id="label-set-pick"',        # chọn bộ nhãn để tải
        'id="label-draft-status"',    # trạng thái nháp đã lưu hay chưa
    ):
        assert el in html, el


def test_trang_gan_nhan_co_nut_ghi_de_va_csv():
    html = client.get("/gan-nhan").text
    for el in ('id="btn-save"', 'id="btn-update"',
               'id="btn-export-labels"', 'id="btn-import-labels"'):
        assert el in html, el


def test_js_giao_dien_khong_loi_cu_phap():
    """Chặn lỗi cú pháp làm chết toàn bộ JS của một trang.

    Dùng `node --check` nếu máy có Node; không có thì bỏ qua test này.
    """
    import os
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("Máy không có Node.js — bỏ qua kiểm tra cú pháp JS.")

    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))   # tests/frontend/ → gốc repo
    js_dir = os.path.join(repo, "frontend", "js")
    loi = []
    files = sorted(
        os.path.join(root, name)
        for root, _dirs, names in os.walk(js_dir)
        for name in names if name.endswith(".js")
    )
    assert len(files) > 10, files
    for path in files:
        p = subprocess.run([node, "--check", path], capture_output=True, text=True)
        if p.returncode != 0:
            loi.append("%s: %s" % (os.path.relpath(path, js_dir), (p.stderr or "").strip().splitlines()[:3]))
    assert not loi, "JS lỗi cú pháp: %s" % loi
