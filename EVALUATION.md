# AutoParkGPT — Evaluation Report (Stage 1)

This document describes how AutoParkGPT's RAG system is evaluated, the metrics used, the
gold dataset, and how to reproduce the numbers. The harness lives in [`eval/`](eval/) and
its pure components are unit-tested in `tests/unit/eval/`.

---

## 1. What we measure

### Retrieval quality
The retriever's job is to surface the right knowledge document for a question. We score it
against a gold dataset (query → relevant source documents) with:

- **Precision@K** — fraction of the top-K retrieved chunks that are relevant.
- **Recall@K** — fraction of the relevant documents found within the top-K.
- **MRR (Mean Reciprocal Rank)** — rewards ranking the relevant document higher.

These are the spec-required retrieval metrics; MRR is added because ranking quality
matters for a top-K RAG prompt. Faithfulness / context-precision (RAGAS-style) are
identified as a recommended future addition (see §5).

### Performance
- **Latency** — mean, p50, and p95 wall-clock time per retrieval.
- **Throughput** — operations per second derived from mean latency.

---

## 2. Gold dataset

`eval/dataset.py` defines 8 queries spanning the four static documents
(`general_info.md`, `location.md`, `reservation_process.md`, `rules.md`). Each query is
labelled with the source file that should answer it. Retrieval is scored by whether the
correct **source document** appears in the top-K results (chunks carry their source
filename as metadata).

The dataset is intentionally small and human-curated for Stage 1; it is structured so it
can grow without code changes.

---

## 3. How to reproduce

The headline numbers require the running stack (Weaviate + the embedding model), because
they exercise real hybrid retrieval over real embeddings:

```bash
# 1. Start dependencies
docker compose up -d weaviate

# 2. Install the full stack and ingest the knowledge base
uv pip install --python .venv ".[all]"
autoparkgpt ingest data/static

# 3. Run the evaluation harness
python -m eval.run
```

`eval/run.py` prints a JSON report. **Measured results** (Weaviate 1.27 hybrid search +
local `bge-small-en-v1.5` embeddings, `top_k=4`, `alpha=0.5`, 8-query gold set):

```json
{
  "retrieval_quality": {
    "num_queries": 8,
    "top_k": 4,
    "precision_at_k": 0.4375,
    "recall_at_k": 1.0,
    "mrr": 1.0
  },
  "retrieval_latency": {
    "runs": 20,
    "mean_ms": 25.1,
    "p50_ms": 24.1,
    "p95_ms": 32.7,
    "throughput_per_s": 39.9
  }
}
```

**Interpretation:**
- **Recall@4 = 1.0** and **MRR = 1.0** — the correct document is retrieved within the top-4
  for every query, and ranked first every time. These are the meaningful quality signals
  for this corpus.
- **Precision@4 = 0.44** is expected and not a concern: each query has ~one relevant
  *document*, but retrieval returns four *chunks*, so precision is naturally bounded
  (often 1–2 of the 4 chunks come from the relevant document). Document-level recall and
  MRR are the right lens here.
- **Latency** is single-digit-tens of milliseconds (p95 ≈ 33 ms) for retrieval on a local
  single-node Weaviate — comfortably interactive; end-to-end `/chat` latency is dominated
  by the LLM call.

The metric **logic** is also unit-tested and deterministic (`tests/unit/eval/`).

---

## 4. Expected behaviour and tuning levers

With `bge-small-en-v1.5` embeddings, hybrid search (`alpha=0.5`), and `top_k=4` over four
well-separated documents, we expect high Recall@4 and MRR on this dataset (the documents
are topically distinct). The tunable levers exposed via configuration:

- `AUTOPARK_RETRIEVAL__TOP_K` — retrieval depth.
- `AUTOPARK_RETRIEVAL__HYBRID_ALPHA` — dense vs keyword weighting (1.0 = pure vector).
- `AUTOPARK_RETRIEVAL__CHUNK_SIZE` / `CHUNK_OVERLAP` — chunk granularity.
- `AUTOPARK_EMBEDDING__PROVIDER` — swap to Voyage `voyage-3` for higher embedding quality.

---

## 5. System performance (end-to-end, measured)

Measured against the running stack (FastAPI `/chat` over HTTP → guardrails → intent
routing → Weaviate retrieval → real Claude `claude-haiku-4-5`), warm cache, local
single-node Weaviate. Each non-reservation turn makes **two** Claude calls (intent
classification + answer generation).

| Path | Runs | Mean | p50 | p95 |
|---|---|---|---|---|
| INFO (retrieve + generate) | 10 | 3455 ms | 3161 ms | 5691 ms |
| DYNAMIC (SQL + generate) | 6 | 2526 ms | 2399 ms | 3414 ms |

| Throughput | Result |
|---|---|
| Sequential (1 client) | 0.29 req/s |
| Concurrent (4 workers, 12 reqs) | 1.59 req/s (~5.5× scaling) |

**Analysis:**
- **The LLM call dominates end-to-end latency.** Retrieval is ~25 ms (p95 33 ms, §3); the
  multi-second response time is almost entirely Claude generation. INFO is slower than
  DYNAMIC mainly because of longer generated answers.
- **Throughput scales well with concurrency** (~5.5× from 1→4 workers) because requests are
  I/O-bound waiting on the model API — the app itself is not the bottleneck.
- **Two Claude calls per turn** (classify + generate) is the largest controllable cost/latency
  lever. Concrete optimizations (future work): make intent routing deterministic/cheaper or
  fold it into the generation call; enable prompt caching of the system prompt + retrieved
  context; and use a faster/cheaper tier or streaming for perceived latency.

Numbers are environment-dependent (model tier, hardware, network); reproduce with the
snippet pattern in §3 against your own deployment.

## 6. Recommended future metrics

- **Faithfulness / hallucination detection** — does the answer stay grounded in the
  retrieved context? Implementable with a RAGAS-style LLM judge, runnable offline.
- **Context precision/recall** (RAGAS) — finer-grained than document-level scoring.
- **Answer-quality** — an LLM-graded rubric over a labelled Q&A set.
- **End-to-end latency** — measure the full `/chat` turn (guardrails + routing + retrieval
  + generation), not just retrieval, once an API key is configured.
