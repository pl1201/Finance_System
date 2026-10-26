"""Test HMM online: warm-up, fit tách khỏi forward, nhân quả."""
from __future__ import annotations

import pytest

hmmlearn = pytest.importorskip("hmmlearn")
numpy = pytest.importorskip("numpy")

from core.algorithms.hmm_online import HmmOnlineAlgorithm
from core.engine import run_algorithm
from core.types import DATA_STATUS_WARMUP, StructureType
from tests.helpers import make_bars, signature


def _trend_series(n: int = 120):
    s = []
    px = 100.0
    for i in range(n):
        px += 0.35 if i < n // 2 else -0.25
        s.append((px - 0.2, px + 0.3, px - 0.3, px))
    return s


def test_hmm_warmup_bang_train_bars():
    algo = HmmOnlineAlgorithm(n_states=2, train_bars=40, seed=1, n_iter=10)
    assert algo.warmup_bars() == 40
    res = run_algorithm(make_bars(_trend_series(30)), algo)
    assert res.events == []
    assert res.data_status == DATA_STATUS_WARMUP


def test_hmm_khong_phat_su_kien_trong_prefix_train():
    algo = HmmOnlineAlgorithm(n_states=2, train_bars=50, seed=7, n_iter=15)
    bars = make_bars(_trend_series(90))
    events = algo.run(bars)
    for e in events:
        assert e.confirmed_bar_index >= 50
        assert e.structure_type == StructureType.HMM_STATE_CHANGE
        assert e.details["khong_dung_smoothing"] is True
        assert e.details["seed"] == 7
        assert "chua_gan_nghia" in (e.details.get("mapped") or "chua_gan_nghia")


def test_hmm_them_du_lieu_sau_T_khong_doi_su_kien_tai_T():
    kw = dict(n_states=2, train_bars=40, seed=3, n_iter=12)
    bars = make_bars(_trend_series(100))
    cut = 70
    prefix = run_algorithm(bars[:cut], HmmOnlineAlgorithm(**kw)).events
    full = [
        e for e in run_algorithm(bars, HmmOnlineAlgorithm(**kw)).events
        if e.confirmed_bar_index < cut
    ]
    assert signature(prefix) == signature(full)
