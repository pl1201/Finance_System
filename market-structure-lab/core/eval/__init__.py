"""Đánh giá thuật toán nhận diện cấu trúc (protocol, matcher, metric)."""
from core.eval.evaluate import evaluate_runs, score_one_run
from core.eval.protocol import (
    EvalProtocol,
    MATCHER_MIN_COST_V1,
    PROTOCOL_VERSION,
    describe_targets,
)
