"""Pure retrieval-quality metrics.

All functions operate on the ordered list of *source identifiers* returned by retrieval
and the set of relevant source identifiers from the gold dataset. A retrieved position is
"relevant" when its source is in the relevant set (retrieval returns chunks, several of
which may share a source, so relevance is scored per position).

Metrics implemented:

- **Precision@K** / **Recall@K** — coverage of the relevant documents in the top-K.
- **F1@K** — harmonic mean of Precision@K and Recall@K.
- **Hit Rate@K** (a.k.a. Success@K) — did *any* relevant document make the top-K?
- **MRR** — reciprocal rank of the first relevant hit (early-ranking quality).
- **MAP** (via :func:`average_precision_at_k`) — precision averaged over relevant hits.
- **nDCG@K** — position-discounted ranking quality, normalised to an ideal ordering.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import log2


def precision_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of the top-k retrieved items that are relevant."""

    if k <= 0:
        raise ValueError("k must be positive.")
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for source in top_k if source in relevant)
    return hits / len(top_k)


def recall_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of relevant items that appear within the top-k retrieved items."""

    if k <= 0:
        raise ValueError("k must be positive.")
    if not relevant:
        return 0.0
    found = {source for source in retrieved[:k] if source in relevant}
    return len(found) / len(relevant)


def f1_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    """Harmonic mean of Precision@K and Recall@K (0.0 when either is 0)."""

    precision = precision_at_k(retrieved, relevant, k)
    recall = recall_at_k(retrieved, relevant, k)
    if precision + recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def hit_rate_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    """1.0 if any of the top-k retrieved items is relevant, else 0.0 (Success@K)."""

    if k <= 0:
        raise ValueError("k must be positive.")
    return 1.0 if any(source in relevant for source in retrieved[:k]) else 0.0


def average_precision_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    """Average of Precision@i over the ranks i (≤k) that hold a relevant item.

    Normalised by the number of relevant items *retrieved* in the top-k, so a perfect
    ranking (relevant items ahead of non-relevant ones) scores 1.0. Because retrieval
    returns chunks — several of which may share a relevant source — this counts relevant
    positions, not documents, keeping the metric bounded in [0, 1]. This is the per-query
    term of MAP.
    """

    if k <= 0:
        raise ValueError("k must be positive.")
    if not relevant:
        return 0.0
    hits = 0
    score = 0.0
    for index, source in enumerate(retrieved[:k], start=1):
        if source in relevant:
            hits += 1
            score += hits / index  # precision@index at this hit
    return score / hits if hits else 0.0


def dcg_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    """Discounted Cumulative Gain with binary relevance over the top-k."""

    if k <= 0:
        raise ValueError("k must be positive.")
    return sum(
        1.0 / log2(index + 1)
        for index, source in enumerate(retrieved[:k], start=1)
        if source in relevant
    )


def ndcg_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    """nDCG@K — DCG normalised by the ideal DCG (all retrieved-relevant items ranked first).

    The ideal ordering places every relevant item *retrieved in the top-k* at the front, so
    the score is bounded in [0, 1] even though a relevant source may span several chunks.
    """

    if not relevant:
        return 0.0
    ideal_hits = sum(1 for source in retrieved[:k] if source in relevant)
    ideal = sum(1.0 / log2(index + 1) for index in range(1, ideal_hits + 1))
    if ideal == 0.0:
        return 0.0
    return dcg_at_k(retrieved, relevant, k) / ideal


def reciprocal_rank(retrieved: Sequence[str], relevant: set[str]) -> float:
    """Reciprocal of the rank (1-based) of the first relevant item, or 0.0."""

    for index, source in enumerate(retrieved, start=1):
        if source in relevant:
            return 1.0 / index
    return 0.0


def mean_reciprocal_rank(results: Sequence[tuple[Sequence[str], set[str]]]) -> float:
    """Mean reciprocal rank across a set of (retrieved, relevant) pairs."""

    if not results:
        return 0.0
    return sum(reciprocal_rank(r, rel) for r, rel in results) / len(results)
