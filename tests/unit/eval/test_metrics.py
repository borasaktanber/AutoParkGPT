"""Tests for retrieval metrics and performance measurement."""

from __future__ import annotations

from math import log2

import pytest

from eval.performance import measure_latency
from eval.retrieval_metrics import (
    average_precision_at_k,
    dcg_at_k,
    f1_at_k,
    hit_rate_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
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


def test_f1_at_k() -> None:
    # precision@2 = 0.5, recall@2 = 1.0 -> F1 = 2*.5*1/(1.5)
    assert f1_at_k(["a.md", "b.md"], {"a.md"}, 2) == pytest.approx(2 * 0.5 * 1.0 / 1.5)
    assert f1_at_k(["x.md", "y.md"], {"a.md"}, 2) == 0.0  # no overlap -> 0


def test_hit_rate_at_k() -> None:
    assert hit_rate_at_k(["a.md", "b.md", "c.md"], {"c.md"}, 3) == 1.0
    assert hit_rate_at_k(["a.md", "b.md", "c.md"], {"c.md"}, 2) == 0.0  # hit is below k
    assert hit_rate_at_k(["a.md"], {"x.md"}, 1) == 0.0


def test_average_precision_at_k() -> None:
    # Two relevant items at ranks 1 and 3: (1/1 + 2/3) / 2
    ap = average_precision_at_k(["a", "x", "b", "y"], {"a", "b"}, 4)
    assert ap == pytest.approx((1.0 + 2 / 3) / 2)
    # Perfect ranking -> 1.0; no relevant -> 0.0
    assert average_precision_at_k(["a", "b", "x"], {"a", "b"}, 3) == pytest.approx(1.0)
    assert average_precision_at_k(["x", "y"], set(), 2) == 0.0


def test_dcg_and_ndcg_at_k() -> None:
    # Relevant at ranks 1 and 3: DCG = 1/log2(2) + 1/log2(4) = 1 + 0.5
    assert dcg_at_k(["a", "x", "b"], {"a", "b"}, 3) == pytest.approx(1.0 + 0.5)
    # Ideal (both relevant first): 1/log2(2) + 1/log2(3); nDCG = DCG/IDCG
    ideal = 1.0 + 1.0 / log2(3)
    assert ndcg_at_k(["a", "x", "b"], {"a", "b"}, 3) == pytest.approx(1.5 / ideal)
    # Perfectly ranked -> 1.0; no relevant set -> 0.0
    assert ndcg_at_k(["a", "b", "x"], {"a", "b"}, 3) == pytest.approx(1.0)
    assert ndcg_at_k(["a"], set(), 1) == 0.0


def test_invalid_k_raises() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        precision_at_k(["a"], {"a"}, 0)
    with pytest.raises(ValueError, match="k must be positive"):
        recall_at_k(["a"], {"a"}, 0)
    with pytest.raises(ValueError, match="k must be positive"):
        hit_rate_at_k(["a"], {"a"}, 0)
    with pytest.raises(ValueError, match="k must be positive"):
        average_precision_at_k(["a"], {"a"}, 0)
    with pytest.raises(ValueError, match="k must be positive"):
        dcg_at_k(["a"], {"a"}, 0)


def test_measure_latency() -> None:
    report = measure_latency(lambda: sum(range(100)), runs=5)
    assert report.runs == 5
    assert report.mean_ms >= 0.0
    assert report.p95_ms >= report.p50_ms
    assert report.throughput_per_s >= 0.0


def test_measure_latency_invalid_runs() -> None:
    with pytest.raises(ValueError, match="runs must be positive"):
        measure_latency(lambda: None, runs=0)
