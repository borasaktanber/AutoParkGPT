"""Tests for retrieval metrics and performance measurement."""

from __future__ import annotations

import pytest

from eval.performance import measure_latency
from eval.retrieval_metrics import (
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_precision_at_k() -> None:
    retrieved = ["a.md", "b.md", "c.md", "d.md"]
    assert precision_at_k(retrieved, {"a.md", "c.md"}, 4) == 0.5
    assert precision_at_k(retrieved, {"a.md"}, 2) == 0.5
    assert precision_at_k(retrieved, set(), 4) == 0.0


def test_recall_at_k() -> None:
    retrieved = ["a.md", "b.md"]
    assert recall_at_k(retrieved, {"a.md", "x.md"}, 2) == 0.5
    assert recall_at_k(retrieved, {"a.md", "b.md"}, 2) == 1.0
    assert recall_at_k(retrieved, set(), 2) == 0.0  # guard: no relevant


def test_reciprocal_rank() -> None:
    assert reciprocal_rank(["x", "a", "b"], {"a"}) == pytest.approx(0.5)
    assert reciprocal_rank(["a"], {"a"}) == 1.0
    assert reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_mean_reciprocal_rank() -> None:
    pairs = [(["a", "b"], {"a"}), (["x", "b"], {"b"})]
    assert mean_reciprocal_rank(pairs) == pytest.approx((1.0 + 0.5) / 2)
    assert mean_reciprocal_rank([]) == 0.0


def test_invalid_k_raises() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        precision_at_k(["a"], {"a"}, 0)
    with pytest.raises(ValueError, match="k must be positive"):
        recall_at_k(["a"], {"a"}, 0)


def test_measure_latency() -> None:
    report = measure_latency(lambda: sum(range(100)), runs=5)
    assert report.runs == 5
    assert report.mean_ms >= 0.0
    assert report.p95_ms >= report.p50_ms
    assert report.throughput_per_s >= 0.0


def test_measure_latency_invalid_runs() -> None:
    with pytest.raises(ValueError, match="runs must be positive"):
        measure_latency(lambda: None, runs=0)
