# open-source-fractal (CantoLab) — ghi nhận nguồn

- Repo: https://github.com/cantolab/open-source-fractal
- Commit tham chiếu: `1bb53262deba9456f2b1a85d15c6ac5a5e880cf7`
- Giấy phép: MIT, Copyright (c) 2026 cantolab — toàn văn ở [`LICENSE`](LICENSE)
  (sao nguyên văn từ commit trên).

Market Structure Lab **không** chứa file Pine gốc. Logic C2 sweep, chọn mức CISD,
reclaim/early CISD và vòng đời C3/C4 được chuyển thể sang Python trong
[`core/algorithms/c2_cisd_research.py`](../../core/algorithms/c2_cisd_research.py)
(header module giữ nguyên văn giấy phép). Khác biệt có chủ đích so với Pine:
[`docs/thuat_toan_c2_cisd.md`](../../docs/thuat_toan_c2_cisd.md) mục 9.
Chưa xác minh parity với Pine/TradingView.
