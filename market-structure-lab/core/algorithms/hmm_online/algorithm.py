"""HMM lọc online: fit ngoài vòng quyết định, ``on_bar`` chỉ bước forward.

Đặc tả: ``docs/algorithms/thuat_toan_hmm_online.md``.

State HMM **không** tự mang nghĩa Trend/Range. Bảng ``state_map`` do người
dùng khai báo (mặc định mọi state = ``chua_gan_nghia``).
"""
from __future__ import annotations

import math
from typing import Any, Optional

from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.types import Bar, ReasonCode, StructureEvent, StructureType


def _require_hmmlearn():
    try:
        import numpy as np
        from hmmlearn.hmm import GaussianHMM
    except ImportError as exc:
        raise ValueError(
            "Thuật toán hmm_online cần gói hmmlearn và numpy. "
            "Cài: pip install hmmlearn numpy. Fit không chạy trong on_bar."
        ) from exc
    return np, GaussianHMM


class HmmOnlineAlgorithm(StructureAlgorithm):
    name = "hmm_online"
    display_name_vi = "HMM lọc online (forward, hmmlearn)"
    version = "1.0.0"
    description_vi = (
        "GaussianHMM fit trên prefix train; từ nến sau train chỉ dùng bước "
        "forward (lọc). Không smoothing, không Viterbi toàn chuỗi. "
        "State mặc định chưa gán nghĩa Trend/Range."
    )

    @classmethod
    def param_specs(cls) -> tuple[ParamSpec, ...]:
        return (
            ParamSpec("n_states", "Số state ẩn", "int", 3, min=2, max=8, step=1,
                      help_vi="Không gắn Trend/Range trừ khi bạn điền state_map."),
            ParamSpec("train_bars", "Số nến prefix dùng để fit", "int", 80, min=20, max=20000, step=1,
                      help_vi="Chỉ các nến này được dùng cho fit. Sự kiện chỉ phát SAU mốc này."),
            ParamSpec("seed", "Seed fit", "int", 42, min=0, max=10_000_000, step=1,
                      help_vi="random_state của hmmlearn, lưu cùng lần chạy."),
            ParamSpec("n_iter", "Số vòng EM tối đa", "int", 50, min=5, max=500, step=1),
            ParamSpec(
                "state_map",
                "Ánh xạ state (0=...,1=...,2=...)",
                "str",
                "0=chua_gan_nghia,1=chua_gan_nghia,2=chua_gan_nghia",
                help_vi=(
                    "Không gán Trend/Range trừ khi nhóm đã chốt. "
                    "Mặc định mọi state = chua_gan_nghia."
                ),
            ),
        )

    def __init__(self, **params: Any) -> None:
        p = self.validate_params(params)
        self.n_states: int = p["n_states"]
        self.train_bars: int = p["train_bars"]
        self.seed: int = p["seed"]
        self.n_iter: int = p["n_iter"]
        self.state_map_raw: str = p["state_map"]
        self.state_map: dict[int, str] = self._parse_map(self.state_map_raw)
        self.params: dict[str, Any] = p
        self.reset()

    @staticmethod
    def _parse_map(raw: str) -> dict[int, str]:
        out: dict[int, str] = {}
        for part in (raw or "").replace(";", ",").split(","):
            part = part.strip()
            if not part or "=" not in part:
                continue
            k, v = part.split("=", 1)
            try:
                out[int(k.strip())] = v.strip() or "chua_gan_nghia"
            except ValueError:
                continue
        return out

    def reset(self) -> None:
        self._bars: list[Bar] = []
        self._features: list[list[float]] = []
        self._fitted = False
        self._log_start: Optional[list[float]] = None
        self._log_trans: Optional[list[list[float]]] = None
        self._means: Optional[list[list[float]]] = None
        self._vars: Optional[list[list[float]]] = None
        self._log_alpha: Optional[list[float]] = None
        self._last_state: Optional[int] = None
        self._model_usable_from: Optional[int] = None
        self._emitted_ids: set[str] = set()
        self._last_point: Optional[dict[str, Any]] = None

    def warmup_bars(self) -> int:
        return self.train_bars

    def _feature(self, bar: Bar, prev: Optional[Bar]) -> list[float]:
        ret = 0.0 if prev is None or prev.close == 0 else math.log(bar.close / prev.close)
        rng = 0.0 if bar.close == 0 else (bar.high - bar.low) / abs(bar.close)
        return [ret, abs(ret), rng]

    def _log_gauss(self, obs: list[float], state: int) -> float:
        s = 0.0
        for j, x in enumerate(obs):
            var = max(self._vars[state][j], 1e-12)
            mu = self._means[state][j]
            s += math.log(2.0 * math.pi * var) + (x - mu) ** 2 / var
        return -0.5 * s

    @staticmethod
    def _logsumexp(xs: list[float]) -> float:
        m = max(xs)
        if m == float("-inf"):
            return float("-inf")
        return m + math.log(sum(math.exp(x - m) for x in xs))

    def _forward_step(self, obs: list[float], init: bool) -> list[float]:
        n = self.n_states
        if init or self._log_alpha is None:
            raw = [self._log_start[s] + self._log_gauss(obs, s) for s in range(n)]
        else:
            raw = []
            for s in range(n):
                prevs = [
                    self._log_alpha[sp] + self._log_trans[sp][s]
                    for sp in range(n)
                ]
                raw.append(self._logsumexp(prevs) + self._log_gauss(obs, s))
        z = self._logsumexp(raw)
        return [x - z for x in raw]

    def _fit(self) -> None:
        np, GaussianHMM = _require_hmmlearn()
        X = np.asarray(self._features, dtype=float)
        if len(X) < self.n_states * 5:
            raise ValueError(
                "Prefix train quá ngắn (%d mẫu) cho %d state. Tăng train_bars."
                % (len(X), self.n_states)
            )
        model = GaussianHMM(
            n_components=self.n_states,
            covariance_type="diag",
            n_iter=self.n_iter,
            random_state=self.seed,
            verbose=False,
        )
        model.fit(X)
        self._log_start = [math.log(max(p, 1e-12)) for p in model.startprob_.tolist()]
        self._log_trans = [
            [math.log(max(p, 1e-12)) for p in row]
            for row in model.transmat_.tolist()
        ]
        self._means = [list(row) for row in model.means_.tolist()]
        cov = model.covars_
        # hmmlearn diag: shape (n_states, n_features)
        self._vars = [list(row) for row in np.asarray(cov).reshape(self.n_states, -1).tolist()]
        self._fitted = True
        self._model_usable_from = len(self._bars)
        # Lọc (forward) trên chính tập train để lấy alpha cuối — không phát sự kiện.
        self._log_alpha = None
        for obs in self._features:
            self._log_alpha = self._forward_step(obs, init=self._log_alpha is None)
        self._last_state = max(range(self.n_states), key=lambda s: self._log_alpha[s])

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        if self._bars and bar.index <= self._bars[-1].index:
            raise ValueError(
                "Nến phải được nạp theo thứ tự tăng dần: nhận index=%s sau index=%s"
                % (bar.index, self._bars[-1].index)
            )
        prev = self._bars[-1] if self._bars else None
        self._bars.append(bar)
        self._features.append(self._feature(bar, prev))

        if not self._fitted:
            if len(self._bars) < self.train_bars:
                self._last_point = {
                    "filtered_state": None,
                    "mapped": None,
                    "model_usable": False,
                    "train_remaining": self.train_bars - len(self._bars),
                }
                return []
            self._fit()
            self._last_point = {
                "filtered_state": self._last_state,
                "mapped": self.state_map.get(self._last_state, "chua_gan_nghia"),
                "model_usable": True,
                "probs": [math.exp(x) for x in self._log_alpha],
            }
            return []  # nến train_bars - 1: vừa fit, chưa phải tín hiệu online

        obs = self._features[-1]
        self._log_alpha = self._forward_step(obs, init=False)
        state = max(range(self.n_states), key=lambda s: self._log_alpha[s])
        probs = [math.exp(x) for x in self._log_alpha]
        mapped = self.state_map.get(state, "chua_gan_nghia")
        self._last_point = {
            "filtered_state": state,
            "mapped": mapped,
            "model_usable": True,
            "probs": probs,
            "seed": self.seed,
            "model_usable_from": self._model_usable_from,
        }
        events: list[StructureEvent] = []
        if state != self._last_state:
            eid = "HMM_STATE_CHANGE@%d>%d" % (bar.index, bar.index)
            self._emitted_ids.add(eid)
            events.append(
                StructureEvent(
                    event_id=eid,
                    structure_type=StructureType.HMM_STATE_CHANGE,
                    price=bar.close,
                    event_bar_index=bar.index,
                    event_time=bar.bar_time,
                    event_close_time=bar.close_time,
                    confirmed_bar_index=bar.index,
                    confirmed_at=bar.close_time,
                    algorithm=self.name,
                    algorithm_version=self.version,
                    reason_code=ReasonCode.HMM_FILTERED_STATE_CHANGE,
                    details={
                        "state_truoc": self._last_state,
                        "state_sau": state,
                        "mapped": mapped,
                        "mapped_truoc": self.state_map.get(self._last_state or -1, "chua_gan_nghia"),
                        "probs": probs,
                        "seed": self.seed,
                        "train_bars": self.train_bars,
                        "model_usable_from": self._model_usable_from,
                        "khong_dung_smoothing": True,
                        "khong_dung_viterbi_toan_chuoi": True,
                    },
                )
            )
            self._last_state = state
        return events

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        return dict(self._last_point) if self._last_point else None

    def pending_state(self) -> dict[str, Any]:
        p = self._last_point or {}
        return {
            "so_nen_da_xu_ly": len(self._bars),
            "fitted": self._fitted,
            "filtered_state": p.get("filtered_state"),
            "mapped": p.get("mapped"),
            "seed": self.seed,
            "model_usable_from": self._model_usable_from,
        }
