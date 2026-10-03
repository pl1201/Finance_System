"""Nạp dữ liệu do repo ``market-data-pipeline`` dựng (thư mục ``data/`` của repo đó) vào lab.

Thư mục nguồn: ``--source-dir``, hoặc biến môi trường ``MDP_DATA_DIR``, mặc định
``../market-data-pipeline/data`` (hai repo đặt cạnh nhau).

Hai chế độ:

* ``series`` — nạp thẳng file nhiều năm ``{PAIR}_{TF}_2018_2025.csv`` (M5/M15/H1/H4/D1; H4/D1 theo
  ngày giao dịch 17:00 New York). File vượt giới hạn ``MAX_BARS_PER_DATASET`` được chia theo khối năm.
* ``m1-year`` — nạp M1 một năm rồi gộp khung bằng chính ``service.resample_dataset`` của lab (mốc UTC,
  ``emit_available``); ``--supersede`` đánh dấu dataset cũ bị thay (thêm tiền tố tên + ghi chú,
  **không xoá** — run đã lưu vẫn mở lại được, AGENTS §10).

Trước khi ghi: sao lưu DB vào ``data/backup/`` (SQLite backup API). ``--dry-run`` chạy trên bản sao DB
trong thư mục tạm, file CSV gốc cũng ghi vào thư mục tạm — DB và ``data/raw`` thật không bị đụng.

    .\\.venv\\Scripts\\python.exe scripts\\import_market_data.py series --pair XAUUSD --tf M5,M15,H1,H4,D1
    .\\.venv\\Scripts\\python.exe scripts\\import_market_data.py m1-year --pair XAUUSD --year 2024 ^
        --resample M5,M15,H1 --supersede M1=ds_old1,M15=ds_old2
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

DEFAULT_SOURCE = os.environ.get("MDP_DATA_DIR") or os.path.join(ROOT, "..", "market-data-pipeline", "data")
PIPELINE = "market-data-pipeline (python -m marketdata.histdata)"


def backup_db(db_path: str) -> str:
    os.makedirs(os.path.join(ROOT, "data", "backup"), exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = os.path.join(ROOT, "data", "backup", "lab_%s.sqlite" % stamp)
    src, out = sqlite3.connect(db_path), sqlite3.connect(dst)
    with out:
        src.backup(out)
    out.close()
    src.close()
    return dst


def set_name_notes(db_path: str, dataset_id: str, name: str, notes: str) -> None:
    conn = sqlite3.connect(db_path, timeout=30.0)
    with conn:
        conn.execute("UPDATE datasets SET name = ?, notes = ? WHERE id = ?", (name, notes, dataset_id))
    conn.close()


def provenance(manifest: dict, rel: str, extra: str = "") -> str:
    entry = next((f for p in manifest["files"].values() for f in p if f["file"] == rel), None)
    return (
        "Nguồn: HistData.com M1 ASCII (BID), dựng bằng %s — file %s, sha256 %s. Giờ gốc quy đổi sang UTC "
        "theo quy tắc '%s' (%s), đã kiểm bằng Dukascopy, broker FXCM và COMEX — xem repo "
        "market-data-pipeline, docs/du_lieu_thi_truong.md §3. Giờ mất lấp bằng Dukascopy cùng luồng giá (§4). "
        "Timestamp = mốc MỞ nến, UTC. Volume = 0 (HistData không có volume).%s"
        % (PIPELINE, rel, entry["sha256"] if entry else "?", manifest["tz_rule"],
           manifest.get("tz_rule_detail", ""), extra))


def import_text(service, text, **kw):
    """Nạp; nếu nội dung trùng dataset đã có thì báo và bỏ qua."""
    try:
        return service.import_dataset(text=text, **kw), False
    except service.ServiceError as exc:
        if "trùng" in str(exc):
            print("  bỏ qua (đã có):", exc)
            return None, True
        raise


def cmd_series(a, service, config, manifest) -> None:
    limit = config.MAX_BARS_PER_DATASET
    for tf in [t.strip().upper() for t in a.tf.split(",") if t.strip()]:
        rel = "%s/%s_%s_2018_2025.csv" % (a.pair, a.pair, tf)
        lines = open(os.path.join(a.source_dir, rel), encoding="ascii").read().splitlines()
        head, rows = lines[0], [r for r in lines[1:] if a.year_from <= int(r[:4]) <= a.year_to]
        years = sorted({int(r[:4]) for r in rows})
        n_parts = -(-len(rows) // (limit * 9 // 10))                     # chừa 10% biên
        chunk = max(1, -(-len(years) // max(1, n_parts)))                 # chia đều số năm
        for i in range(0, len(years), chunk):
            ys = years[i:i + chunk]
            part = [r for r in rows if ys[0] <= int(r[:4]) <= ys[-1]]
            span = "%d–%d" % (ys[0], ys[-1]) if len(ys) > 1 else str(ys[0])
            note = " Mốc nến H4/D1: ngày giao dịch bắt đầu 17:00 New York." if tf in ("H4", "D1") else ""
            ds, dup = import_text(
                service, head + "\n" + "\n".join(part) + "\n",
                filename="%s_%s_%s.csv" % (a.pair, tf, span.replace("–", "_")),
                name="%s %s · %s · HistData (giờ đã sửa)%s" % (
                    a.pair, tf, span, " · mốc 17:00 NY" if tf in ("H4", "D1") else ""),
                symbol=a.pair, timeframe=tf, source="HistData.com qua " + PIPELINE,
                source_timezone="UTC", timestamp_convention="open", price_type="bid",
                notes=provenance(manifest, rel, note + " Dòng %s→%s của file nguồn." % (ys[0], ys[-1])))
            if ds:
                print("%s %s %s → %s (%d nến)" % (a.pair, tf, span, ds["id"], ds["row_count"]))


def cmd_m1_year(a, service, config, manifest) -> None:
    rel = "%s/M1/%s_M1_%d.csv" % (a.pair, a.pair, a.year)
    tag = "HistData %d · giờ đã sửa" % a.year
    notes = provenance(manifest, rel)
    text = open(os.path.join(a.source_dir, rel), encoding="ascii").read()
    m1, dup = import_text(
        service, text, filename="%s_M1_%d_fixed_tz.csv" % (a.pair, a.year),
        name="%s M1 · %s (nặng — không nên mở chart)" % (a.pair, tag), symbol=a.pair, timeframe="M1",
        source="HistData.com qua " + PIPELINE, source_timezone="UTC", timestamp_convention="open",
        price_type="bid", notes=notes)
    if not m1:
        return
    new = {"M1": m1["id"]}
    print("M1 →", m1["id"], m1["row_count"], "nến")
    for tf in [t.strip().upper() for t in a.resample.split(",") if t.strip()]:
        ds = service.resample_dataset(m1["id"], tf, gap_policy="emit_available")["dataset"]
        set_name_notes(config.DB_PATH, ds["id"], "%s %s · %s (từ M1)" % (a.pair, tf, tag), ds.get("notes") or notes)
        new[tf] = ds["id"]
        print("%s →" % tf, ds["id"], ds["row_count"], "nến")
    for pair in [p for p in a.supersede.split(",") if p.strip()]:
        tf, old_id = (x.strip() for x in pair.split("="))
        old = service.get_dataset_or_error(old_id)
        if old["name"].startswith("[LỆCH GIỜ"):
            print("đã đánh dấu từ trước:", old_id)
            continue
        set_name_notes(
            config.DB_PATH, old_id, "[LỆCH GIỜ — dùng %s] %s" % (new[tf.upper()], old["name"]),
            (old.get("notes") or "") + " || %s: dataset này quy đổi giờ gốc HistData theo New York nên mọi "
            "nến trong các tuần Mỹ–Âu lệch lịch đổi giờ bị sớm 1 giờ. Thay bằng %s. Giữ lại để mở các run cũ."
            % (datetime.now(timezone.utc).date().isoformat(), new[tf.upper()]))
        print("đánh dấu", old_id, "→ thay bằng", new[tf.upper()])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source-dir", default=DEFAULT_SOURCE)
    ap.add_argument("--dry-run", action="store_true", help="chạy trên bản sao DB, không đụng DB/data/raw thật")
    ap.add_argument("--no-backup", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("series")
    s.add_argument("--pair", required=True)
    s.add_argument("--tf", default="M5,M15,H1,H4,D1")
    s.add_argument("--year-from", type=int, default=2018)
    s.add_argument("--year-to", type=int, default=2025)
    m = sub.add_parser("m1-year")
    m.add_argument("--pair", required=True)
    m.add_argument("--year", type=int, required=True)
    m.add_argument("--resample", default="M5,M15,H1")
    m.add_argument("--supersede", default="", help="TF=dataset_id,... — dataset cũ bị thay")
    a = ap.parse_args()
    a.pair = a.pair.upper()
    a.source_dir = os.path.abspath(a.source_dir)
    manifest = json.load(open(os.path.join(a.source_dir, "manifest.json"), encoding="utf-8"))

    tmp = None
    if a.dry_run:
        tmp = tempfile.mkdtemp(prefix="msl_dryrun_")
        src = sqlite3.connect(os.path.join(ROOT, "data", "lab.sqlite"))
        dst = sqlite3.connect(os.path.join(tmp, "lab.sqlite"))
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
        os.environ["MSL_DB_PATH"] = os.path.join(tmp, "lab.sqlite")
    from backend.app import config, service  # noqa: E402 — sau khi đặt MSL_DB_PATH
    if a.dry_run:
        config.RAW_DIR = os.path.join(tmp, "raw")
        os.makedirs(config.RAW_DIR, exist_ok=True)
    print("DB:", config.DB_PATH, "| nguồn:", a.source_dir)
    if not a.dry_run and not a.no_backup:
        print("Sao lưu:", backup_db(config.DB_PATH))
    try:
        (cmd_series if a.cmd == "series" else cmd_m1_year)(a, service, config, manifest)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
            print("(dry-run: đã xoá bản sao tạm)")


if __name__ == "__main__":
    main()
