"""Pure retrieval-quality metrics: Precision@K, Recall@K, MRR.

All functions operate on the ordered list of *source identifiers* returned by retrieval
and the set of relevant source identifiers from the gold dataset.
"""

from __future__ import annotations

from collections.abc import Sequence


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
