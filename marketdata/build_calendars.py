"""Sinh lịch phiên KHAI BÁO 2018–2025 vào ``calendars/`` (không suy lịch từ dữ liệu).

* ``cme_globex_metals.json`` — dùng cho XAUUSD. Lấy từ ``pandas_market_calendars``
  (lịch ``CMEGlobex_Gold``): phiên Chủ nhật–Thứ Sáu 18:00 → 17:00 New York, nghỉ 17:00–18:00, ngày
  lễ đóng cửa, đóng sớm ngày lễ Mỹ. Bổ sung một ngoại lệ thư viện thiếu: **24/12 đóng 13:45 NY**
  (12:45 giờ Chicago) theo lịch nghỉ lễ CME (https://www.cmegroup.com/trading-hours.html).
* ``fx_spot.json`` — dùng cho EURUSD. FX giao ngay không có lịch sàn: khai báo theo thông lệ thị
  trường OTC — Chủ nhật 17:00 → Thứ Sáu 17:00 New York, không nghỉ hằng ngày, đóng ngày giao dịch
  25/12 và 01/01.

Cả hai được kiểm lại bằng dữ liệu (``python -m marketdata.histdata build``) và nguồn ngoài
(``python -m marketdata.compare``) — kết quả trong docs/du_lieu_thi_truong.md.

``pandas_market_calendars`` chỉ cần khi sinh lại lịch (không nằm trong requirements chính):

    pip install -r requirements-calendars.txt
    python -m marketdata.build_calendars
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import CAL_DIR as OUT  # noqa: E402
NY = ZoneInfo("America/New_York")
Y0, Y1 = 2018, 2025

#: Ngoại lệ chỉ thêm khi có bằng chứng NGOÀI thư viện (``marketdata.compare yahoo``) và dữ
#: liệu cùng chỉ một giờ đóng. Chỗ chưa xác minh được KHÔNG sửa — ghi ở docs/du_lieu_thi_truong.md §5.
EVIDENCE_OVERRIDES = {
    "2025-07-04": ("13:00", "GC=F (Yahoo, dữ liệu CME) có nến cuối 12:00–13:00 NY, không có nến sau đó; "
                            "dữ liệu nguồn dừng 12:58 NY; thư viện ghi 14:30"),
}


def iso(t: datetime) -> str:
    return t.astimezone(NY).isoformat()


def write(name: str, meta: dict, sessions: list) -> None:
    os.makedirs(OUT, exist_ok=True)
    meta = dict(meta, name=name, timezone="America/New_York", years=[Y0, Y1], so_phien=len(sessions),
                created=date.today().isoformat())
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"meta": meta, "sessions": sessions}, f, ensure_ascii=False, indent=0)
    print("ghi %s: %d phiên" % (name, len(sessions)))


def metals() -> None:
    import pandas_market_calendars as pmc  # noqa: E402 — chỉ cần khi sinh lịch

    cal = pmc.get_calendar("CMEGlobex_Gold")
    sch = cal.schedule("%d-01-01" % Y0, "%d-12-31" % Y1, tz="America/New_York")
    sessions, overrides = [], []
    for day, row in sch.iterrows():
        o, c = row["market_open"].to_pydatetime(), row["market_close"].to_pydatetime()
        kind = "regular" if c.strftime("%H:%M") == "17:00" else "early_close"
        d = day.date()
        if d.month == 12 and d.day == 24 and kind == "regular":
            c = datetime(d.year, 12, 24, 13, 45, tzinfo=NY)
            kind = "early_close"
            overrides.append({"trading_day": d.isoformat(), "close": "13:45",
                              "ly_do": "24/12 kim loại CME đóng 12:45 CT; thư viện thiếu"})
        if d.isoformat() in EVIDENCE_OVERRIDES:
            hhmm, why = EVIDENCE_OVERRIDES[d.isoformat()]
            c = datetime(d.year, d.month, d.day, int(hhmm[:2]), int(hhmm[3:]), tzinfo=NY)
            kind = "early_close"
            overrides.append({"trading_day": d.isoformat(), "close": hhmm, "ly_do": why})
        sessions.append({"trading_day": d.isoformat(), "open": iso(o), "close": iso(c), "kind": kind})
    first, last = date(Y0, 1, 1), date(Y1, 12, 31)
    bdays = {first + timedelta(days=i) for i in range((last - first).days + 1)}
    traded = {s["trading_day"] for s in sessions}
    closed = sorted(d.isoformat() for d in bdays if d.weekday() < 5 and d.isoformat() not in traded)
    write("cme_globex_metals", {
        "dung_cho": ["XAUUSD"],
        "nguon": "pandas_market_calendars %s — lịch CMEGlobex_Gold; ngoại lệ bổ sung ghi ở 'ngoai_le'"
                 % pmc.__version__,
        "nguon_ngoai_le": "https://www.cmegroup.com/trading-hours.html (lịch nghỉ lễ: 24/12 năng lượng, kim "
                          "loại, FX đóng 12:45 CT)",
        "ghi_chu": "XAUUSD giao ngay không giao dịch trên CME; dùng lịch CME Globex kim loại làm lịch "
                   "đại diện vì dữ liệu nguồn nghỉ theo đúng các mốc này.",
        "ngoai_le": overrides, "ngay_dong_cua": closed}, sessions)


def fx_spot() -> None:
    closed_md = {(12, 25), (1, 1)}
    sessions, closed = [], []
    d = date(Y0, 1, 1)
    while d <= date(Y1, 12, 31):
        if d.weekday() < 5:
            if (d.month, d.day) in closed_md:
                closed.append(d.isoformat())
            else:
                prev = d - timedelta(days=1)
                o = datetime(prev.year, prev.month, prev.day, 17, 0, tzinfo=NY)
                c = datetime(d.year, d.month, d.day, 17, 0, tzinfo=NY)
                sessions.append({"trading_day": d.isoformat(), "open": iso(o), "close": iso(c), "kind": "regular"})
        d += timedelta(days=1)
    write("fx_spot", {
        "dung_cho": ["EURUSD"],
        "nguon": "thông lệ thị trường FX giao ngay OTC (không có lịch sàn): Chủ nhật 17:00 → Thứ Sáu 17:00 "
                 "New York; đóng ngày giao dịch 25/12 và 01/01",
        "ghi_chu": "Không có giờ nghỉ hằng ngày (17:00 NY là giờ rollover, thanh khoản mỏng nhưng vẫn có giá). "
                   "Một số nhà cung cấp vẫn báo giá phiên Á sáng 25/12 — được ghi nhận khi kiểm, không sửa lịch.",
        "ngoai_le": [], "ngay_dong_cua": closed}, sessions)


if __name__ == "__main__":
    metals()
    fx_spot()
