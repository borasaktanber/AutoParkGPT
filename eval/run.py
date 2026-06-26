"""Run the evaluation harness against a live stack.

Prerequisites: Weaviate running and knowledge ingested (``autoparkgpt ingest``), and the
embedding provider available. Produces retrieval-quality and retrieval-latency reports.

Usage:
    python -m eval.run
"""

from __future__ import annotations

import json

from autoparkgpt.container import build_container
from eval.dataset import DEFAULT_DATASET
from eval.evaluator import RetrievalEvaluator
from eval.performance import measure_latency


def main() -> None:  # pragma: no cover - integration entry point (needs running stack)
    container = build_container()
    settings = container.settings()
    embedding = container.embedding()
    vector_store = container.vector_store()

    evaluator = RetrievalEvaluator(
        embedding,
        vector_store,
        hybrid_alpha=settings.retrieval.hybrid_alpha,
    )
    quality = evaluator.evaluate(DEFAULT_DATASET, top_k=settings.retrieval.top_k)

    sample_query = DEFAULT_DATASET[0].query

    def _retrieve() -> object:
        return vector_store.search(
            query_text=sample_query,
            query_vector=embedding.embed_query(sample_query),
            top_k=settings.retrieval.top_k,
            alpha=settings.retrieval.hybrid_alpha,
        )

    latency = measure_latency(_retrieve, runs=20)

    print(
        json.dumps(
            {"retrieval_quality": quality.model_dump(), "retrieval_latency": latency.model_dump()},
            indent=2,
        )
    )


if __name__ == "__main__":  # pragma: no cover
    main()
