# AutoParkGPT — Evaluation Report (Stage 1)

This document describes how AutoParkGPT's RAG system is evaluated, the metrics used, the
gold dataset, and how to reproduce the numbers. The harness lives in [`eval/`](eval/) and
its pure components are unit-tested in `tests/unit/eval/`.

---

## 1. What we measure

### Retrieval quality
The retriever's job is to surface the right knowledge document for a question. We score it
against a gold dataset (query → relevant source documents). A retrieved position counts as
relevant when its chunk's **source** is in the relevant set (retrieval returns chunks,
several of which may share a source, so relevance is scored per position).

- **Precision@K** — fraction of the top-K retrieved chunks that are relevant.
- **Recall@K** — fraction of the relevant documents found within the top-K.
- **F1@K** — harmonic mean of Precision@K and Recall@K (a single balanced figure).
- **Hit Rate@K** (Success@K) — did *any* relevant document make the top-K? (coverage,
  ignoring rank).
- **MRR (Mean Reciprocal Rank)** — reciprocal rank of the *first* relevant hit; rewards
  putting a relevant result at the very top.
- **MAP (Mean Average Precision)** — precision averaged over the relevant hits; rewards
  ranking *all* retrieved-relevant chunks highly, not just the first.
- **nDCG@K** — position-discounted ranking quality, normalised to the ideal ordering of
  the retrieved-relevant chunks.

Precision/Recall/MRR are the spec-required metrics; F1, Hit Rate, MAP, and nDCG were added
to characterise ranking quality more fully. MAP and nDCG are normalised by the number of
relevant chunks *retrieved in the top-K*, so both stay bounded in [0, 1] despite a single
relevant document spanning multiple chunks. Faithfulness / answer-quality (LLM-judged) are
recommended future additions (see §6).

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
local `bge-small-en-v1.5` embeddings, `top_k=4`, `alpha=0.5`, 8-query gold set, 4 documents
→ 10 chunks):

```json
{
  "retrieval_quality": {
    "num_queries": 8,
    "top_k": 4,
    "precision_at_k": 0.34375,
    "recall_at_k": 0.875,
    "f1_at_k": 0.4833,
    "hit_rate_at_k": 0.875,
    "mrr": 0.75,
    "map": 0.71875,
    "ndcg_at_k": 0.7674
  },
  "retrieval_latency": {
    "runs": 20,
    "mean_ms": 37.7,
    "p50_ms": 36.9,
    "p95_ms": 44.3,
    "throughput_per_s": 26.5
  }
}
```

**Interpretation:**
- **Hit Rate@4 = Recall@4 = 0.875** — the correct document is retrieved within the top-4 for
  **7 of 8** queries. The single miss is *"How do I get there by public transport?"*: its
  relevant document (`location.md`) is crowded out of the top-4 by `general_info.md` /
  `reservation_process.md` chunks, because the phrase "public transport" isn't strongly
  represented in the location text. This is a concrete, actionable retrieval gap (see §4).
- **MRR = 0.75, MAP = 0.72, nDCG@4 = 0.77** — for most queries the relevant document is
  ranked first, but two ("*where is the garage located*" and "*accessible bay*") place it at
  rank 2, and one misses entirely — so the ranking metrics sit below 1.0. MAP/nDCG being
  close to MRR here reflects that each query has essentially one relevant document.
- **Precision@4 = 0.34** is expected and not a concern: each query has ~one relevant
  *document* but retrieval returns four *chunks*, so precision is naturally bounded (1–2 of
  the 4 chunks typically come from the relevant document). **F1@4 = 0.48** balances this
  chunk-level precision against document recall.
- **Latency** is tens of milliseconds (mean ≈ 38 ms, p95 ≈ 44 ms) for hybrid retrieval on a
  local single-node Weaviate — comfortably interactive; end-to-end `/chat` latency is
  dominated by the LLM call (§5).

Numbers are environment- and corpus-dependent (embedding model, chunking, `alpha`, index
state); reproduce with the steps above. The metric **logic** is unit-tested and
deterministic (`tests/unit/eval/test_metrics.py`).

---

## 4. Expected behaviour and tuning levers

With `bge-small-en-v1.5` embeddings, hybrid search (`alpha=0.5`), and `top_k=4` over four
well-separated documents, we expect high Recall@4 and MRR on this dataset (the documents
are topically distinct). The tunable levers exposed via configuration:

- `AUTOPARK_RETRIEVAL__TOP_K` — retrieval depth. Raising it to 5–6 would recover the
  "public transport" miss (its `location.md` chunk currently sits just outside the top-4).
- `AUTOPARK_RETRIEVAL__HYBRID_ALPHA` — dense vs keyword weighting (1.0 = pure vector).
- `AUTOPARK_RETRIEVAL__CHUNK_SIZE` / `CHUNK_OVERLAP` — chunk granularity.
- `AUTOPARK_EMBEDDING__PROVIDER` — swap to Voyage `voyage-3` for higher embedding quality.

The one retrieval miss (§3) is a useful worked example: the fix is either a larger `top_k`,
or enriching `location.md` with directions/"public transport" wording so its embedding
matches the query — a content change, not a code change.

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
