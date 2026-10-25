"""Live chỉ đọc từ MT5 (plan_mt5_live.md): lớp bọc chỉ đọc, giờ server, luồng live với terminal giả, kho chỉ ghi thêm,
sửa lịch sử, lỗi dữ liệu, dựng lại khi khởi động, route API."""
from __future__ import annotations

import bisect
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.errors import ServiceError
from backend.app.main import app
from backend.app.services import live
from core.algorithms.ict_structure import IctStructureAlgorithm
from core.data.mt5_source import Mt5SourceError, ReadOnlyMt5, server_offset, utc_converter
from tests.helpers import cal_bars, u

M15 = timedelta(minutes=15)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ORDER_CALLS = ("order_send", "order_check", "order_calc_margin", "order_calc_profit", "orders_get", "orders_total",
               "positions_get", "positions_total", "history_orders_get", "history_deals_get")
ACCOUNT_CALLS = ("account_info", "login")          # tên chung, có trong chú thích lab → chỉ kiểm ở lớp bọc


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class FakeTerminal:
    """Terminal giả: nến UTC của ``cal_bars`` trả theo giờ server (UTC + ``offset_h``), gồm nến đang hình thành; có cả
    hàm lệnh / tài khoản để chắc lab không gọi tới."""

    TIMEFRAME_M15 = 15

    def __init__(self, rows, clock, offset_h=3):
        self.rows, self.clock, self.offset = list(rows), clock, offset_h * 3600
        self.calls = []

    def initialize(self, *args, **kwargs):
        self.calls.append(("initialize", args, kwargs))
        return True

    def shutdown(self):
        self.calls.append(("shutdown",))

    def last_error(self):
        return (1, "ok")

    def symbol_select(self, symbol, _enable):
        return symbol == "XAUUSD"

    def symbol_info_tick(self, _symbol):
        return SimpleNamespace(time=int(self.clock().timestamp()) + self.offset)

    def copy_rates_from_pos(self, _symbol, _tf, start, count):
        assert start == 0
        avail = [r for r in self.rows if r["bar_time"] <= self.clock()]
        return [{"time": int(r["bar_time"].timestamp()) + self.offset, "open": r["open"], "high": r["high"],
                 "low": r["low"], "close": r["close"], "tick_volume": 7} for r in avail[-count:]]

    def __getattr__(self, name):
        if name in ORDER_CALLS + ACCOUNT_CALLS:
            raise AssertionError("lab gọi %s" % name)
        raise AttributeError(name)


ROWS, _BARS = cal_bars(u(2024, 1, 2), u(2024, 2, 24), seed=3)
OPENS = [r["bar_time"] for r in ROWS]
#: Nến lịch sử cuối = ROWS[HIST − 1], có nến sau liền bước (nến vị trí 0 của MT5 chỉ được nhận khi nến sau đã mở)
HIST = next(i for i in range(2500, len(ROWS)) if OPENS[i] - OPENS[i - 1] == M15)


def _expect(polls, have=HIST):
    """(số nến, số bản ghi kịp thời) sau các lần hỏi ở ``polls``: nhận nến i khi nến i+1 đã mở (bỏ nến vị trí 0)."""
    timely = 0
    for t in polls:
        k = bisect.bisect_right(OPENS, t) - 1
        timely += sum(t <= OPENS[i] + 2 * M15 for i in range(have, k))
        have = max(have, k)
    return have, timely


@pytest.fixture
def env(monkeypatch):
    clock = Clock(ROWS[HIST - 1]["bar_time"] + M15 + timedelta(seconds=5))     # nến lịch sử cuối vừa đóng
    term = FakeTerminal(ROWS, clock)
    path = os.path.join(tempfile.mkdtemp(prefix="msl_live_"), "live.sqlite")
    mgr = live.LiveManager(store_path=path, api=term, clock=clock)
    monkeypatch.setattr(live.LiveManager, "_ensure_thread", lambda self: None)    # test tự gọi poll
    return SimpleNamespace(clock=clock, term=term, mgr=mgr, path=path)


def _create(env, **kw):
    args = dict(symbol="XAUUSD", mt5_symbol="XAUUSD", timeframe="M15", server_tz="UTC+3", history_bars=HIST)
    args.update(kw)
    return env.mgr.create(**args)


def _advance(env, n=1):
    env.clock.now += n * M15
    return env.mgr.poll(env.fid)


# ---------------------------------------------------------------------- rào chắn
def test_lop_boc_chi_lo_ham_doc_nen():
    term = FakeTerminal([], Clock(u(2024, 1, 2)))
    ro = ReadOnlyMt5(term)
    for name in ORDER_CALLS + ACCOUNT_CALLS + ("symbol_info", "market_book_add"):
        with pytest.raises(Mt5SourceError):
            getattr(ro, name)
    assert ro.TIMEFRAME_M15 == 15 and ro.copy_rates_from_pos("XAUUSD", 15, 0, 1) == []
    ro.initialize("C:/mt5/terminal64.exe")
    ro.initialize()
    assert [c[1:] for c in term.calls] == [(("C:/mt5/terminal64.exe",), {}), ((), {})]   # không login / mật khẩu


def test_ma_nguon_lab_khong_goi_ham_lenh_va_chi_mt5_source_import_goi_mt5():
    hits = []
    for top in ("core", "backend", "scripts", "research", "frontend"):
        for dirpath, _dirs, files in os.walk(os.path.join(ROOT, top)):
            for f in files:
                if not f.endswith((".py", ".js", ".html")):
                    continue
                p = os.path.join(dirpath, f)
                text = open(p, encoding="utf-8", errors="replace").read()
                for name in ORDER_CALLS:
                    if re.search(r"\b%s\b" % name, text):
                        hits.append((os.path.relpath(p, ROOT), name))
                if re.search(r"^\s*(import|from)\s+MetaTrader5", text, re.M) and not p.endswith("mt5_source.py"):
                    hits.append((os.path.relpath(p, ROOT), "import MetaTrader5"))
    assert hits == []


def test_gio_server_co_dinh_va_ny_cong_7_theo_mua():
    wall = int(datetime(2024, 7, 1, 10, 0, tzinfo=timezone.utc).timestamp())
    assert utc_converter("UTC+3")(wall) == u(2024, 7, 1, 7)
    assert utc_converter("ny+7")(wall) == u(2024, 7, 1, 7)             # NY mùa hè UTC−4 → server UTC+3
    winter = int(datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc).timestamp())
    assert utc_converter("ny+7")(winter) == u(2024, 1, 15, 8)          # NY mùa đông UTC−5 → server UTC+2
    assert server_offset("ny+7", u(2024, 1, 15)) == timedelta(hours=2)
    with pytest.raises(Mt5SourceError):
        server_offset("Europe/Athens", u(2024, 1, 15))


# ---------------------------------------------------------------------- luồng
def test_tao_luong_ghi_ban_ghi_kip_thoi_cho_nen_moi(env):
    st = _create(env)
    env.fid = st["id"]
    assert (st["status"], st["so_nen"], st["history_bars"], st["so_ban_ghi"]) == ("running", HIST, HIST, 0)
    assert st["forward_from"] == (ROWS[HIST - 1]["bar_time"] + M15).isoformat()
    start = env.clock.now
    n = sum(_advance(env) for _ in range(100))          # hỏi 5 giây sau mỗi mốc 15 phút, 25 giờ (qua một giờ nghỉ)
    have, timely = _expect([start + j * M15 for j in range(1, 101)])
    st = env.mgr.status(env.fid)
    # nến cuối trước giờ nghỉ chỉ tới khi phiên mở lại → ghi bù; mọi nến khác kịp thời
    assert n > 20 and st["so_nen"] == have == HIST + n and st["so_ban_ghi"] == n and st["kip_thoi"] == timely
    assert 0 < n - timely <= 3
    bars = env.mgr.store.get_bars(env.fid)
    assert [b["bar_time"] for b in bars] == [r["bar_time"].isoformat() for r in ROWS[:len(bars)]]   # đúng giờ UTC
    recs = env.mgr.store.get_forecasts(env.fid)
    assert recs[0]["idx"] == HIST and all("tam" in f["record"] for f in recs)
    fw = env.mgr.forward_scores(env.fid)
    assert fw["kip_thoi"] == timely and fw["ghi_bu"] == n - timely
    assert fw["tam"]["1h"]["n"] > 0 and fw["tam"]["4h"]["cho_ket_cuc"] <= 16
    assert env.mgr.forward_scores(env.fid)["tam"] is fw["tam"]              # chưa có nến mới → dùng lại điểm đã chấm


def test_ghi_bu_sau_khi_mat_ket_noi_khong_kip_thoi(env):
    env.fid = _create(env)["id"]
    env.clock.now += 8 * M15                            # lab tắt 2 giờ
    got = env.mgr.poll(env.fid)
    have, timely = _expect([env.clock.now])
    st = env.mgr.status(env.fid)
    assert got == have - HIST > 4 and st["so_ban_ghi"] == got and st["kip_thoi"] == timely <= 1


def test_kho_chi_ghi_them(env):
    env.fid = _create(env)["id"]
    _advance(env)
    conn = sqlite3.connect(env.path)
    for sql in ("UPDATE live_bar SET close = 0", "DELETE FROM live_bar", "UPDATE live_forecast SET timely = 1",
                "DELETE FROM live_forecast"):
        with pytest.raises(sqlite3.DatabaseError, match="chỉ ghi thêm"):
            conn.execute(sql)
    conn.close()


def test_broker_sua_lich_su_ghi_mot_lan_khong_sua_nen_da_luu(env):
    env.fid = _create(env)["id"]
    _advance(env)
    i = HIST - 1
    old = dict(ROWS[i])
    env.term.rows[i] = dict(old, high=old["high"] + 1.0)
    _advance(env)
    _advance(env)
    revs = env.mgr.store.get_revisions(env.fid)
    assert len(revs) == 1 and revs[0]["idx"] == i and revs[0]["seen"]["high"] == old["high"] + 1.0
    assert env.mgr.store.get_bars(env.fid)[i]["high"] == old["high"]
    assert env.mgr.status(env.fid)["sua_lich_su"] == 1


def test_nen_loi_dung_nap(env):
    env.fid = _create(env)["id"]
    j = HIST + 1
    env.term.rows[j] = dict(env.term.rows[j], low=env.term.rows[j]["high"] + 1)       # low > high
    for _ in range(12):
        _advance(env)
    st = env.mgr.status(env.fid)
    assert st["status"] == "data_error" and "OHLC" in st["status_note"] and st["so_nen"] == j
    assert env.mgr.poll(env.fid) == 0                   # dừng nạp tới khi người dùng xem


def test_khai_bao_gio_server_sai_bi_tu_choi(env):
    with pytest.raises(ServiceError, match="giờ server"):
        _create(env, server_tz="UTC")                   # server thật UTC+3 → nến «ở tương lai»
    with pytest.raises(ServiceError, match="khai báo giờ server"):
        _create(env, server_tz="  ")                    # bỏ trống: không mặc định UTC
    with pytest.raises(ServiceError, match="≤ H1"):
        _create(env, timeframe="H4")


def test_khai_bao_lech_lon_van_khong_nap_nen_dang_hinh_thanh(env):
    """Khai báo UTC+4 với server UTC+3: theo đồng hồ máy mọi nến «đã đóng», kể cả nến đang chạy — nến vị trí 0 vẫn bị bỏ."""
    env.fid = _create(env, server_tz="UTC+4")["id"]
    bars = env.mgr.store.get_bars(env.fid)
    assert len(bars) == HIST and bars[-1]["bar_time"] == (OPENS[HIST - 1] - timedelta(hours=1)).isoformat()


def test_live_feed_chi_doi_trang_thai(env):
    env.fid = _create(env)["id"]
    conn = sqlite3.connect(env.path)
    for sql in ("UPDATE live_feed SET history_bars = 1", "UPDATE live_feed SET params_json = '{}'",
                "DELETE FROM live_feed"):
        with pytest.raises(sqlite3.DatabaseError, match="live_feed"):
            conn.execute(sql)
    conn.execute("UPDATE live_feed SET status = 'stopped'")
    conn.close()


def test_dung_trong_luc_hoi_mt5_khong_ghi_tiep(env, monkeypatch):
    env.fid = _create(env)["id"]
    real = env.mgr._closed_bars

    def stop_mid_call(*a):
        rows = real(*a)
        env.mgr.stop(env.fid)                          # người dùng bấm Dừng khi luồng nền đang hỏi MT5
        return rows

    monkeypatch.setattr(env.mgr, "_closed_bars", stop_mid_call)
    assert _advance(env, 4) == 0
    assert env.mgr.status(env.fid)["so_nen"] == HIST and env.mgr.store.get_forecasts(env.fid) == []


def _raise_locked(*_a):
    raise sqlite3.OperationalError("database is locked")


def test_loi_giua_lo_bo_luong_roi_dung_lai_tu_kho(env, monkeypatch):
    env.fid = _create(env)["id"]
    real = env.mgr.store.append
    monkeypatch.setattr(env.mgr.store, "append", _raise_locked)
    with pytest.raises(sqlite3.OperationalError):
        _advance(env, 4)
    assert env.fid not in env.mgr._feeds and env.fid in env.mgr._reopen
    monkeypatch.setattr(env.mgr.store, "append", real)
    env.mgr._reopen_feeds(list(env.mgr._reopen))       # luồng nền làm việc này mỗi giây
    assert env.fid in env.mgr._feeds and not env.mgr._reopen
    assert env.mgr.status(env.fid)["so_nen"] == HIST    # không lủng chỉ số: bộ nhớ dựng lại đúng kho
    assert env.mgr.poll(env.fid) > 0 and len(env.mgr.store.get_bars(env.fid)) == env.mgr.status(env.fid)["so_nen"]


def test_goi_y_lech_gio(env):
    h = env.mgr.hint("XAUUSD", "UTC+3")
    assert (h["lech_giay"], h["khop"], h["tin_duoc"]) == (3 * 3600, True, True)
    assert env.mgr.hint("XAUUSD", "UTC+2")["khop"] is False


def test_khoi_dong_lai_dung_lai_trung_ban_ghi_doi_phien_ban_thi_het_hieu_luc(env, monkeypatch):
    env.fid = _create(env)["id"]
    for _ in range(5):
        _advance(env)
    before = env.mgr.store.get_forecasts(env.fid)
    again = live.LiveManager(store_path=env.path, api=env.term, clock=env.clock)
    st = again.status(env.fid)
    assert st["status"] == "running" and st["so_ban_ghi"] == len(before)
    assert again.snapshot(env.fid)["pending_state"] == env.mgr.snapshot(env.fid)["pending_state"]
    # bản dựng lại khác bản ghi đã lưu → dừng
    real = IctStructureAlgorithm.forecast_record
    monkeypatch.setattr(IctStructureAlgorithm, "forecast_record", lambda self: dict(real(self), close=-1.0))
    assert live.LiveManager(store_path=env.path, api=env.term, clock=env.clock).status(env.fid)["status"] == \
        "rebuild_mismatch"
    monkeypatch.setattr(IctStructureAlgorithm, "forecast_record", real)
    # phiên bản thuật toán đổi → hết hiệu lực, không chạy tiếp được
    other = live.LiveManager(store_path=env.path, api=env.term, clock=env.clock)
    monkeypatch.setattr(IctStructureAlgorithm, "version", "9.9.9")
    with pytest.raises(ServiceError):
        other.resume(env.fid)
    assert other.status(env.fid)["status"] == "outdated"


def test_snapshot_since_kem_nen_moi(env):
    env.fid = _create(env)["id"]
    snap = env.mgr.snapshot(env.fid)
    cur = snap["cursor"]
    _advance(env)
    _advance(env)
    d = env.mgr.snapshot(env.fid, since=cur)
    assert d["cursor"] > cur and d["delta_since"] == cur
    assert [b["index"] for b in d["bars_moi"]] == list(range(cur + 1, d["cursor"] + 1))
    assert d["live"]["so_nen"] == d["cursor"] + 1 and all(e["confirmed_bar_index"] > cur for e in d["events"])
    assert [p["bar_index"] for p in d["timeline"]] == list(range(cur + 1, d["cursor"] + 1))
    full = env.mgr.snapshot(env.fid, since=-5)                                       # since < −1 kẹp về −1
    assert len(full["bars_moi"]) == full["cursor"] + 1 and full["bars_moi"][0]["index"] == 0
    light = env.mgr.snapshot(env.fid, since=d["cursor"])                             # không có nến mới: gói nhẹ
    assert set(light) == {"cursor", "delta_since", "bars_moi", "live"} and light["bars_moi"] == []


def test_route_api_live(env, monkeypatch):
    monkeypatch.setattr(live, "live_manager", env.mgr)
    import backend.app.routers.live as router_mod
    monkeypatch.setattr(router_mod, "live_manager", env.mgr)
    c = TestClient(app)
    r = c.post("/api/live", json={"symbol": "XAUUSD", "server_tz": "UTC+3", "history_bars": HIST})
    assert r.status_code == 200, r.text
    fid = r.json()["id"]
    lst = c.get("/api/live").json()
    assert lst["luong"][0]["id"] == fid and lst["algorithm"] == "ict_structure"
    assert c.get("/api/live/%s/bars" % fid).json()["bars"][-1]["index"] == HIST - 1
    assert c.get("/api/live/%s" % fid).json()["live"]["status"] == "running"
    assert c.get("/api/live/%s/forward" % fid).json()["so_ban_ghi"] == 0
    assert c.post("/api/live/%s/stop" % fid).json()["status"] == "stopped"
    assert c.post("/api/live/%s/resume" % fid).json()["status"] == "running"
    assert c.post("/api/live/hint", json={"mt5_symbol": "XAUUSD", "server_tz": "UTC+3"}).json()["khop"] is True
    assert c.get("/api/live/hint", params={"mt5_symbol": "XAUUSD"}).status_code in (404, 405)    # chỉ POST JSON
    assert c.post("/api/live", json={"symbol": "XAUUSD", "server_tz": "UTC+3", "history_bars": 10}).status_code == 400
    assert c.get("/api/live/lv_khong_co").status_code == 404
