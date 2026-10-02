"""Kiểm chứng múi giờ của HistData bằng Dukascopy (nguồn ghi giờ UTC).

Tải vài ngày nến M1 BID của Dukascopy (``datafeed.dukascopy.com``, file ``.bi5`` nén LZMA,
mỗi bản ghi 24 byte: giây từ đầu ngày, open, close, low, high (số nguyên × hệ số) và volume),
rồi so với M1 HistData đã quy đổi theo từng giả thuyết múi giờ: lệch nào làm hai chuỗi close
khớp nhau nhiều nhất thì đó là quy đổi đúng cho ngày đó.

Dukascopy rất chậm và hay trả 503 từ Việt Nam → thử lại có giãn cách, lưu đệm, chạy lại được.

    python -m marketdata.dukascopy               # ngày mẫu kiểm giờ
    python -m marketdata.dukascopy --gap-days 2  # ngày để lấp giờ mất (2 luồng)
"""
from __future__ import annotations

import http.client
import json
import lzma
import os
import struct
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone

from . import DATA_DIR  # noqa: E402

CACHE = os.path.join(DATA_DIR, "raw", "dukascopy")
HOST = "datafeed.dukascopy.com"
URL = "https://" + HOST + "/datafeed/{sym}/{y}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"
SCALE = {"XAUUSD": 1000.0, "EURUSD": 100000.0}
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "*/*"}

# Ngày mẫu: mùa đông, mùa hè, và hai giai đoạn Mỹ–Âu lệch lịch đổi giờ mỗi năm.
DAYS = [
    "2018-01-10", "2018-03-14", "2018-07-11", "2018-10-31",
    "2021-03-17", "2021-11-03",
    "2024-01-10", "2024-03-13", "2024-07-10", "2024-10-30",
    "2025-03-12", "2025-10-29",
]


_LOCAL = threading.local()


def _conn(reset: bool = False) -> http.client.HTTPSConnection:
    """Một kết nối giữ lâu (keep-alive) cho mỗi luồng: mở kết nối TLS tới Dukascopy mất ~20 s,
    còn mỗi lần tải trên kết nối đã mở chỉ ~0.3 s."""
    if reset or getattr(_LOCAL, "conn", None) is None:
        if getattr(_LOCAL, "conn", None) is not None:
            _LOCAL.conn.close()
        _LOCAL.conn = http.client.HTTPSConnection(HOST, timeout=90)
    return _LOCAL.conn


def fetch(sym: str, day: date, tries: int = 8) -> bytes:
    os.makedirs(os.path.join(CACHE, sym), exist_ok=True)
    path = os.path.join(CACHE, sym, "%s_BID_m1.bi5" % day.isoformat())
    if os.path.exists(path):
        return open(path, "rb").read()
    url = URL.format(sym=sym, y=day.year, m=day.month - 1, d=day.day)  # tháng đánh số từ 0
    wait = 5.0
    for _ in range(tries):
        try:
            c = _conn()
            c.request("GET", url[len("https://" + HOST):], headers=dict(HDR, Connection="keep-alive"))
            r = c.getresponse()
            data = r.read()
            if r.status != 200:
                raise OSError("HTTP %d" % r.status)
            if data:  # ngày không có giao dịch: file rỗng
                lzma.decompress(data, format=lzma.FORMAT_ALONE)  # hỏng thì thử lại
            with open(path, "wb") as f:
                f.write(data)
            return data
        except (http.client.HTTPException, OSError, lzma.LZMAError) as e:
            print("  thử lại %s %s sau %.0fs (%s)" % (sym, day, wait, str(e)[:60]), flush=True)
            _conn(reset=True)
            time.sleep(wait)
            wait = min(wait * 2, 120)
    raise RuntimeError("Không tải được %s %s" % (sym, day))


def decode_ohlc(sym: str, day: date, data: bytes) -> dict:
    """{epoch UTC giờ mở nến: (open, high, low, close)}; bỏ nến «phẳng» volume 0 (thị trường đóng)."""
    raw = lzma.decompress(data, format=lzma.FORMAT_ALONE) if data else b""
    base = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
    out, bad, k = {}, 0, SCALE[sym]
    for i in range(len(raw) // 24):
        t, o, c, lo, h, v = struct.unpack(">5if", raw[i * 24:(i + 1) * 24])
        if not (h >= max(o, c) and lo <= min(o, c)):
            bad += 1
        if v == 0 and o == c == lo == h:
            continue
        out[base + t] = (o / k, h / k, lo / k, c / k)
    if bad:
        raise ValueError("Thứ tự trường OHLC không như giả định (%d bản ghi sai)" % bad)
    return out


def decode(sym: str, day: date, data: bytes) -> dict:
    return {datetime.fromtimestamp(e, timezone.utc): v[3] for e, v in decode_ohlc(sym, day, data).items()}


def gap_days(pair: str, years) -> list:
    """Ngày UTC chạm vào các khoảng trống HistData thuộc diện lấp (``histdata.fillable_windows``)."""
    from . import histdata as fh
    m1, _ = fh.read_pair(pair, years, "histdata")
    days = set()
    for s, e in fh.fillable_windows(m1, pair):
        days.add(datetime.fromtimestamp(s, timezone.utc).date())
        days.add(datetime.fromtimestamp(e - 60, timezone.utc).date())
    return sorted(days)


def fetch_gap_days(workers: int) -> None:
    """Tải (có lưu đệm, chạy lại được) các ngày Dukascopy cần để lấp giờ mất của HistData."""
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(p, d) for p in ("XAUUSD", "EURUSD") for d in gap_days(p, list(range(2019, 2026)))]
    todo = [(p, d) for p, d in jobs
            if not os.path.exists(os.path.join(CACHE, p, "%s_BID_m1.bi5" % d.isoformat()))]
    print("cần %d ngày, còn thiếu %d" % (len(jobs), len(todo)), flush=True)
    done = 0

    def one(job):
        p, d = job
        fetch(p, d, tries=12)
        return job

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for p, d in ex.map(one, todo):
            done += 1
            if done % 10 == 0 or done == len(todo):
                print("  %d/%d (%s %s)" % (done, len(todo), p, d), flush=True)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--gap-days":
        fetch_gap_days(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
        return
    res = {}
    for sym in ("XAUUSD", "EURUSD"):
        for d in DAYS:
            day = date.fromisoformat(d)
            data = fetch(sym, day)
            closes = decode(sym, day, data)
            res.setdefault(sym, {})[d] = {t.strftime("%H:%M"): c for t, c in closes.items()}
            print(sym, d, "nến:", len(closes), flush=True)
            time.sleep(2)
    out = os.path.join(CACHE, "dukascopy_m1_mau.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f)
    print("Đã lưu", out)


if __name__ == "__main__":
    sys.exit(main())
