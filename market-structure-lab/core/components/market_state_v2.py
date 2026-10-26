"""[N] Trạng thái mô tả v2: trend lên / trend xuống / range / nhiễu + cờ nén (plan_nhan_dien_v2.md §3).

Hai trục: **hướng / hiệu quả** (bốn trạng thái loại trừ nhau) và **biến động** (cờ ``nen``, đi kèm bất kỳ trạng thái nào).
Sau nến t (chỉ dữ liệu ≤ t; cửa sổ không vắt qua ``gap_before``):

* **Cấu trúc ngược chiều d** (dùng chung cho vào và ra): thứ tự swing khung chạy = −d và mức bảo vệ chưa bị phá, hoặc
  thứ tự = d nhưng mức bảo vệ đã bị phá (CHoCH). **Cùng chiều d**: thứ tự = d chưa bị phá, hoặc thứ tự H1 = d.
* **Trend lên — vào** khi động lượng 8 giờ > 0, cấu trúc không ngược chiều, và một trong: cấu trúc cùng chiều + lực
  (ER 8 giờ ≥ ``er_in`` hoặc ADX ≥ ``ADX_IN`` với +DI > −DI); ER ≥ ``STRONG_ER`` và ADX ≥ ``STRONG_ADX`` cùng chiều DI
  (cấu trúc còn trễ); ER ≥ ``er_strong`` (đường vào của v1). **Ra** (xét theo thứ tự): cấu trúc ngược chiều (CHoCH);
  close thủng đáy ``EXIT_HOURS`` trước (kênh Donchian); lực tắt (ER < ``er_out`` và ADX < ``ADX_OUT``). Trend xuống
  đối xứng.
* **Range — vào** khi không trend và có hộp Donchian ``BOX_HOURS`` rộng ``BOX_WIDTH_ATR``, ER < ``er_strong``, mỗi
  biên được thăm ≥ ``MIN_VISITS`` lần (cách nhau ≥ 2 nến). Biên = max high / min low của cửa sổ phát hiện. **Giữ** tới
  khi ``BREAK_CLOSES`` close liên tiếp ra ngoài biên quá ``BREAK_TOL_ATR``·ATR (phá biên) — cách giữ hộp của Range
  Detector (LuxAlgo). (Nhánh phát hiện kiểu Range Detector đã thử trên dev: trùng gần hết hộp này — bỏ cho gọn.)
* **Nhiễu** — còn lại.
* **Cờ nén**: BB(20, 2) nằm trong KC(20, 1,5·TB TR 20) và độ rộng BB thuộc ``SQZ_PCT`` thấp nhất của ``SQZ_LOOKBACK``
  nến (TTM Squeeze + phân vị độ rộng).

ADX / DI và BB / KC bắt đầu lại khi ``gap_before`` (lớp gọi chọn khoảng trống nào — ``ict_structure`` 0.9.2: khoảng
trống dài không theo lịch phiên, xem ``nhan_dien.LONG_GAP_MINUTES``). Đổi trạng thái: ứng viên phải giữ ``hold`` nến
liên tiếp, trừ lần thoát do sự kiện đã xác nhận (``EXITS``: CHoCH, thủng kênh, phá biên) — đổi ngay, ``details.doi_ngay``.
``details`` ghi các ngưỡng đã dùng (``nguong``) và kênh thoát của nến (``kenh_thoat`` = [max high, min low]). Độ mạnh 0–1 chỉ để hiển thị, không phải xác suất. Thành phần chỉ giữ
trạng thái; thuật toán phát sự kiện.
"""
from __future__ import annotations

from collections import deque
from itertools import islice
from math import sqrt
from typing import Any, NamedTuple, Optional

from core.components.market_state import _spaced
from core.components.rolling_stats import SortedWindow
from core.indicators import RollingHighLow, WilderADX, true_range
from core.types import Bar

TREND_HOURS = 8
ADX_LEN, ADX_IN, ADX_OUT = 14, 20.0, 18.0
EXIT_HOURS = 4                          # trend lên kết thúc khi close < đáy thấp nhất 4 giờ trước (kênh Donchian)
STRONG_ER, STRONG_ADX = 0.25, 25.0      # đường vào khi cấu trúc còn trễ: ER và ADX cùng mạnh, DI cùng chiều
BOX_HOURS, BOX_WIDTH_ATR, MIN_VISITS, VISIT_ZONE = 6, (1.5, 4.5), 2, 0.25
BREAK_CLOSES, BREAK_TOL_ATR = 2, 0.25
SQZ_LEN, SQZ_BB, SQZ_KC, SQZ_LOOKBACK, SQZ_PCT = 20, 2.0, 1.5, 500, 0.2
#: Trạng thái → chữ ngắn (details, giao diện). Khoá cũng là danh sách trạng thái v2.
TEXT_VI = {"trend_len": "trend lên", "trend_xuong": "trend xuống", "range": "range", "nhieu": "sideway nhiễu"}
TRENDS = ("trend_len", "trend_xuong")
#: Lý do thoát → đổi ngay (sự kiện đã xác nhận) hay chờ giữ ``hold`` nến như mọi ứng viên.
EXITS = {"choch": True, "thung_kenh": True, "pha_bien_len": True, "pha_bien_xuong": True, "luc_tat": False}


class Structure(NamedTuple):
    """Cấu trúc của thuật toán sau nến t: thứ tự swing khung chạy (+1 HH-HL, −1 LH-LL, 0 lẫn lộn, None chưa đủ), mức
    bảo vệ đã bị close phá, thứ tự H1 (None khi tắt khung lớn hoặc khung chạy ≥ H1)."""
    order: Optional[int]
    broken: bool
    order_h1: Optional[int]


NO_STRUCTURE = Structure(None, False, None)


def _against(s: Structure, d: int) -> bool:
    """Cấu trúc ngược chiều d: thứ tự khung chạy = −d (mức bảo vệ còn), hoặc = d nhưng mức bảo vệ đã bị phá (CHoCH)."""
    return (s.order == -d and not s.broken) or (s.order == d and s.broken)


def _with(s: Structure, d: int) -> bool:
    """Cấu trúc cùng chiều d: thứ tự khung chạy = d còn nguyên, hoặc thứ tự H1 = d."""
    return (s.order == d and not s.broken) or s.order_h1 == d


class _Rolling:
    """Tổng và tổng bình phương trượt ``n`` giá trị (trung bình, độ lệch chuẩn quần thể)."""

    __slots__ = ("q", "n", "s", "s2")

    def __init__(self, n: int) -> None:
        self.q: deque[float] = deque()
        self.n, self.s, self.s2 = n, 0.0, 0.0

    def push(self, x: float) -> None:
        self.q.append(x)
        self.s += x
        self.s2 += x * x
        if len(self.q) > self.n:
            y = self.q.popleft()
            self.s -= y
            self.s2 -= y * y

    def mean(self) -> float:
        return self.s / self.n

    def std(self) -> float:
        m = self.mean()
        return sqrt(max(self.s2 / self.n - m * m, 0.0))


class MarketStateV2:
    kind = "v2"
    text_vi = TEXT_VI
    vat_qua_nghi_lich = True       # 0.9.2: lớp gọi không đặt gap_before ở nghỉ theo lịch phiên (cuối tuần, lễ)

    def __init__(self, step_seconds: float, er_strong: float = 0.3, hold: int = 2, er_in: float = 0.18,
                 er_out: float = 0.10) -> None:
        if not 0.0 < er_out < er_in <= er_strong < 1.0 or hold < 1:
            raise ValueError("Nhận diện v2: cần 0 < nd_er_ra (%s) < nd_er_vao (%s) ≤ nd_er_nguong (%s) < 1 và nd_giu_nen ≥ 1 "
                             "(hoặc chọn nd_kieu = v1)." % (er_out, er_in, er_strong))
        per_hour = 3600.0 / step_seconds

        def bars(hours: float, floor: int = 5) -> int:
            return max(int(round(hours * per_hour)), floor)

        self.trend_w, self.box_w, self.exit_w = bars(TREND_HOURS), bars(BOX_HOURS), bars(EXIT_HOURS, 2)
        assert max(self.box_w, self.exit_w) <= self.trend_w           # luật chỉ chạy khi đủ trend_w nến từ khoảng trống
        self.er_strong, self.er_in, self.er_out, self.hold = er_strong, er_in, er_out, hold
        self.er_threshold = er_strong                                  # tên chung với v1 (details, manifest)
        self.thresholds = {"er_vao": er_in, "er_ra": er_out, "er_manh": er_strong, "adx_vao": ADX_IN, "adx_ra": ADX_OUT,
                           "er_luc_manh": STRONG_ER, "adx_luc_manh": STRONG_ADX, "pha_bien_close": BREAK_CLOSES,
                           "pha_bien_vuot_atr": BREAK_TOL_ATR}
        self._cap = self.trend_w + 1
        self.reset()

    def windows(self) -> dict[str, Any]:
        return {"trend": self.trend_w, "hop": self.box_w, "nen": SQZ_LEN, "thoat_trend": self.exit_w}

    def timeline_extra(self) -> dict[str, Any]:
        on = self.state is not None
        return {"nd_nen": self.squeeze if on else None, "nd_do_manh": self.strength if on else None,
                "nd_duong": self.trend_line()}

    def trend_line(self) -> Optional[float]:
        """«Đường trend» sau nến t (0.9.1): trend lên = đáy thấp nhất ``exit_w`` nến tới t — close nến sau thủng mức này
        là hết trend (luật thoát «thủng kênh»); trend xuống = đỉnh cao nhất; range = giữa hộp; nhiễu / chưa đủ nến = None."""
        s = self.state
        if s in TRENDS:
            return self._ehl[1] if s == "trend_len" else self._ehl[0]
        if s == "range":
            return (self._box["bien_tren"] + self._box["bien_duoi"]) / 2
        return None

    def stats_extra(self, n_bars: int) -> dict[str, Any]:
        return {"ty_le_co_nen": self.squeeze_bars / n_bars if n_bars else None}

    def reset(self) -> None:
        self._bars: deque[Bar] = deque(maxlen=self._cap)
        self._cum: deque[float] = deque(maxlen=self._cap)              # Σ|ΔC| cộng dồn (cho ER)
        self._run = 0                                                  # số nến liên tiếp từ khoảng trống gần nhất
        self._dmi = WilderADX(ADX_LEN)
        self._box_hl, self._exit_hl = RollingHighLow(self.box_w), RollingHighLow(self.exit_w)
        self._bhl: Optional[tuple[float, float]] = None                # (max high, min low) ``box_w`` nến tới t
        self._ehl: Optional[tuple[float, float]] = None                # (max high, min low) ``exit_w`` nến TRƯỚC t
        self._bb, self._kc_tr = _Rolling(SQZ_LEN), _Rolling(SQZ_LEN)
        self._bbw = SortedWindow(SQZ_LOOKBACK)
        self.squeeze = False
        self.strength: Optional[float] = None
        self.state: Optional[str] = None
        self.since: Optional[int] = None
        self.info: dict[str, Any] = {}
        self._box: Optional[dict[str, Any]] = None                     # hộp range đang giữ
        self._seen_box: Optional[dict[str, Any]] = None                # hộp vừa phát hiện ở nến t
        self._out = [0, 0]                                             # số close liên tiếp ra ngoài biên trên / dưới
        self._pending: Optional[list] = None
        self.counts = dict.fromkeys(TEXT_VI, 0)
        self.changes = 0
        self.squeeze_bars = 0

    # ------------------------------------------------------------------ mỗi nến
    def on_bar(self, bar: Bar, atr: Optional[float], gap_before: bool,
               structure: Structure) -> Optional[tuple[str, Bar, dict[str, Any]]]:
        """Trạng thái sau nến t. Trả (trạng thái mới, nến đầu của nó, info) khi vừa đổi, không thì None."""
        last = self._bars[-1] if self._bars else None
        if gap_before:                                                 # chỉ báo không vắt qua gap_before
            self._run, last = 0, None
            self._dmi = WilderADX(ADX_LEN)
            self._bb, self._kc_tr = _Rolling(SQZ_LEN), _Rolling(SQZ_LEN)
        self._run += 1
        self._cum.append((self._cum[-1] + abs(bar.close - last.close)) if last is not None else 0.0)
        self._bars.append(bar)
        self._indicators(bar, last)
        cand = self._candidate(atr, structure)
        self._ehl = self._exit_hl.push(bar.index, bar.high, bar.low)  # kênh thoát cho nến sau (đẩy SAU khi xét luật)
        changed = None
        if cand is None:
            self.state, self.since, self.info, self._pending, self._box = None, None, {}, None, None
        elif cand[0] == self.state:
            self.info, self._pending = cand[1], None
        else:
            name, info = cand
            now = EXITS.get(info.get("thoat"), False)
            p = self._pending
            p = self._pending = [name, bar, 1] if p is None or p[0] != name else [name, p[1], p[2] + 1]
            if now or p[2] >= self.hold:
                first = bar if now else p[1]
                self.state, self.since, self.info, self._pending = name, first.index, info, None
                self._box = self._seen_box if name == "range" else None
                self._out = [0, 0]
                self.changes += 1
                changed = (name, first, info)
        if self.state is not None:
            self.counts[self.state] += 1
            self.squeeze_bars += self.squeeze
        return changed

    def pending_candidate(self) -> Optional[dict[str, Any]]:
        p = self._pending
        return None if p is None else {"trang_thai": p[0], "trang_thai_vi": TEXT_VI[p[0]], "tu_nen": p[1].index,
                                       "so_nen": p[2], "can": self.hold}

    # ------------------------------------------------------------------ chỉ báo
    def _indicators(self, bar: Bar, last: Optional[Bar]) -> None:
        self._dmi.update(bar.high, bar.low, bar.close)
        self._bhl = self._box_hl.push(bar.index, bar.high, bar.low)
        self._bb.push(bar.close)
        self._kc_tr.push(true_range(bar.high, bar.low, last.close if last is not None else None))
        self.squeeze = False
        if len(self._bb.q) == SQZ_LEN:
            m, sd, kc = self._bb.mean(), self._bb.std(), self._kc_tr.mean()
            width = 2 * SQZ_BB * sd / m if m else 0.0
            # BB trong KC và độ rộng BB thấp hơn (1 − SQZ_PCT) số nến trước trong cửa sổ phân vị
            self.squeeze = (SQZ_BB * sd < SQZ_KC * kc and len(self._bbw) >= SQZ_LEN
                            and 1.0 - self._bbw.at_least(width) <= SQZ_PCT)
            self._bbw.add(width)

    def _er(self, w: int) -> float:
        net = abs(self._bars[-1].close - self._bars[-1 - w].close)
        path = self._cum[-1] - self._cum[-1 - w]
        return net / path if path > 0 else 0.0

    # ------------------------------------------------------------------ luật
    def _candidate(self, atr: Optional[float], structure: Structure) -> Optional[tuple[str, dict[str, Any]]]:
        adx = self._dmi.adx
        if atr is None or atr <= 0 or self._run <= self.trend_w or adx is None:
            return None
        w, c = self.trend_w, self._bars[-1].close
        er = self._er(w)
        mom = (c - self._bars[-1 - w].close) / atr
        self.strength = (min(er / 0.5, 1.0) + min(max((adx - 15.0) / 25.0, 0.0), 1.0) + min(abs(mom) / 6.0, 1.0)) / 3.0
        base = {"kieu": "v2", "cua_so_nen": w, "er": er, "adx": adx, "dong_luong_atr": mom, "cau_truc": structure.order,
                "cau_truc_pha": structure.broken, "cau_truc_h1": structure.order_h1, "do_manh": self.strength,
                "nen": self.squeeze, "kenh_thoat": list(self._ehl), "nguong": self.thresholds}
        s = self.state
        if s in TRENDS:                                               # đang trend: giữ tới CHoCH / thủng kênh / lực tắt
            d = 1 if s == "trend_len" else -1
            if _against(structure, d):
                return self._fresh(atr, base, structure, exclude=s, why="choch")
            if c < self._ehl[1] if d > 0 else c > self._ehl[0]:
                return self._fresh(atr, base, structure, exclude=s, why="thung_kenh")
            if er < self.er_out and adx < ADX_OUT:
                return self._fresh(atr, base, structure, exclude=s, why="luc_tat")
            return s, dict(base, ly_do="giu")
        if s == "range":                                               # đang range: giữ tới khi phá biên
            box, tol = self._box, BREAK_TOL_ATR * atr
            self._out = [self._out[0] + 1 if c > box["bien_tren"] + tol else 0,
                         self._out[1] + 1 if c < box["bien_duoi"] - tol else 0]
            if max(self._out) >= BREAK_CLOSES:
                side = "len" if self._out[0] >= BREAK_CLOSES else "xuong"
                return self._fresh(atr, base, structure, exclude="range", why="pha_bien_" + side)
            return "range", dict(base, **box, ly_do="giu")
        return self._fresh(atr, base, structure)

    def _fresh(self, atr: float, base: dict[str, Any], structure: Structure, exclude: Optional[str] = None,
               why: Optional[str] = None) -> tuple[str, dict[str, Any]]:
        """Trạng thái mới từ đầu (luật vào). ``exclude`` = trạng thái vừa thoát (không vào lại ngay), ``why`` = lý do thoát."""
        er, adx, mom = base["er"], base["adx"], base["dong_luong_atr"]
        extra = {"thoat": why, "doi_ngay": EXITS[why]} if why else {}
        d = (mom > 0) - (mom < 0)
        name = "trend_len" if d > 0 else "trend_xuong"
        if d and name != exclude and not _against(structure, d):    # cùng định nghĩa với luật ra — không vào rồi ra ngay
            di_ok = (self._dmi.plus_di - self._dmi.minus_di) * d > 0
            if er >= self.er_strong:
                return name, dict(base, ly_do="er_manh", **extra)
            if _with(structure, d) and (er >= self.er_in or (adx >= ADX_IN and di_ok)):
                return name, dict(base, ly_do="cau_truc_va_luc", **extra)
            if er >= STRONG_ER and adx >= STRONG_ADX and di_ok:
                return name, dict(base, ly_do="luc_manh", **extra)
        if exclude != "range":
            box = self._seen_box = self._detect(atr, er)
            if box is not None:
                return "range", dict(base, **box, ly_do="hop", **extra)
        return "nhieu", dict(base, ly_do="con_lai", **extra)

    def _detect(self, atr: float, er: float) -> Optional[dict[str, Any]]:
        """Hộp range ở nến t: hộp Donchian ``box_w`` nến, rộng vừa, mỗi biên được thăm lại."""
        if er >= self.er_strong:
            return None
        top, bot = self._bhl
        width = (top - bot) / atr
        if not BOX_WIDTH_ATR[0] <= width <= BOX_WIDTH_ATR[1]:
            return None
        win = list(islice(self._bars, len(self._bars) - self.box_w, None))
        zone = VISIT_ZONE * (top - bot)
        vu = _spaced([b.index for b in win if b.high >= top - zone], 2)
        vd = _spaced([b.index for b in win if b.low <= bot + zone], 2)
        if len(vu) < MIN_VISITS or len(vd) < MIN_VISITS:
            return None
        return {"nen_dau_cua_so": win[0].index, "bien_tren": top, "bien_duoi": bot, "rong_atr": width,
                "tham_tren": vu, "tham_duoi": vd}
