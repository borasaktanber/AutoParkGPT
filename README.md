# AutoParkGPT

A production-grade, Retrieval-Augmented-Generation (RAG) parking-reservation chatbot
built with **LangChain**, **LangGraph**, **Weaviate**, and **Claude**. It answers
parking questions (general info, working hours, prices, availability, location) and
interactively collects reservation requests, behind a layered Clean Architecture with a
security guardrail pipeline.

> **Project status:** **Stages 1 & 2 complete** — RAG chatbot + human-in-the-loop
> administrator approval. Stages 3–4 (MCP server, unified LangGraph orchestration) are
> planned — see [`TASKS.md`](TASKS.md). Full design rationale is in
> [`ARCHITECTURE.md`](ARCHITECTURE.md); evaluation methodology in [`EVALUATION.md`](EVALUATION.md).

---

## Highlights

- **Clean Architecture** — domain ports (`Protocol`) with infrastructure adapters; the
  domain has zero framework dependencies. Application logic is a **LangGraph** workflow.
- **Configurable LLM tier** — `claude-haiku-4-5` (default, economy) → `claude-sonnet-4-6`
  → `claude-opus-4-8`, swapped via one env var, no code change. The adapter is
  capability-aware (adaptive thinking is only sent to models that support it).
- **Local-first RAG** — local HuggingFace embeddings (no embeddings API key needed; note
  Claude has no embeddings API) and a single Weaviate container with hybrid (dense + BM25)
  search; Voyage AI is a drop-in production embedding option.
- **Security-first** — a guardrail pipeline blocks prompt injection / jailbreaks on input
  and screens output for system-prompt / internal / secret leakage; retrieval is
  restricted to `public` documents.
- **Fully typed & tested** — `mypy --strict`, `ruff`, **112 tests at 92% coverage**, CI on
  GitHub Actions (format, lint, type-check, tests, Docker build, security scans).

---

## Architecture at a glance

```mermaid
flowchart LR
    Client["FastAPI /chat  ·  CLI"] --> CS[ChatService]
    CS --> G[LangGraph workflow]
    G --> GIN[input guardrails]
    GIN --> R{router}
    R -->|info| RET[hybrid retrieval -> Weaviate]
    R -->|hours/prices/availability| DYN[SQL dynamic data]
    R -->|reservation| SLOT[slot-filling -> SQL]
    RET --> GEN[Claude generation + sources]
    DYN --> GEN
    GEN --> GOUT[output guardrails]
    SLOT --> GOUT
    GOUT --> Client
```

Layers: `domain/` (entities, value objects, ports) ← `application/` (use cases + graph) ←
`infrastructure/` (Claude, Weaviate, embeddings, SQL, guardrails) ← `interface/`
(FastAPI + CLI), wired at the `container.py` DI composition root.

---

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv ".[all,dev]"   # full app + dev tooling
cp .env.example .env                          # then set AUTOPARK_LLM__API_KEY
```

### Run the full stack (Docker Compose)

```bash
export AUTOPARK_LLM__API_KEY=sk-ant-...        # never commit this
docker compose up --build                      # weaviate :8080, postgres :5432, app :8000
```

### Initialise the knowledge base and database

```bash
# Apply DB migrations (Postgres/SQLite)
AUTOPARK_SQL__URL=... .venv/Scripts/python -m alembic upgrade head
# Ingest the static knowledge documents into Weaviate
.venv/Scripts/autoparkgpt ingest data/static
```

---

## Usage

### HTTP API

| Method | Path | Body / Result |
|---|---|---|
| `GET` | `/health` | `{status, name, environment}` |
| `POST` | `/chat` | `{session_id, message}` → `{message, intent, sources, reservation_id, blocked}` |

```bash
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"session_id":"abc","message":"What are your opening hours?"}'
```

Conversation state (history + in-progress reservation) is keyed by `session_id`.

### Administrator approval (Stage 2)

When a reservation is created it enters `pending_approval` and an administrator is
notified. Admin endpoints are secured by `X-Admin-Token` (set `AUTOPARK_ADMIN__API_TOKEN`;
endpoints fail closed if it's unset). The decision flows back to the user — via a webhook
(`AUTOPARK_ADMIN__USER_WEBHOOK_URL`) and by asking the chatbot about the reservation
reference.

A web **admin console** is served at **http://127.0.0.1:8000/admin/ui** — enter the token,
view pending requests, and Approve / Reject (or type a natural-language decision) per row.
The same actions are available as REST endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/reservations` | List pending reservations |
| `POST` | `/admin/reservations/{ref}/approve` | Approve |
| `POST` | `/admin/reservations/{ref}/reject` | Reject |
| `POST` | `/admin/reservations/{ref}/decision` | Approve/reject from a natural-language instruction (LLM admin agent) |

```bash
TOKEN=...   # AUTOPARK_ADMIN__API_TOKEN
curl -s localhost:8000/admin/reservations -H "X-Admin-Token: $TOKEN"
curl -s -X POST localhost:8000/admin/reservations/675e1e8a/approve -H "X-Admin-Token: $TOKEN"
# natural-language decision:
curl -s -X POST localhost:8000/admin/reservations/675e1e8a/decision \
  -H "X-Admin-Token: $TOKEN" -H 'content-type: application/json' \
  -d '{"instruction":"looks good, approve it"}'
```

Then the user can ask the chatbot: *"What's the status of reservation 675e1e8a?"* →
"…has been approved."

### CLI

```bash
autoparkgpt version
autoparkgpt ingest data/static          # index knowledge base
autoparkgpt chat --session-id me        # interactive terminal chat
```

---

## Configuration

All settings come from the environment (or a local `.env`), prefixed `AUTOPARK_` with
`__` as the nesting delimiter — see [`.env.example`](.env.example). **Secrets are injected
via the environment only and never committed.**

| Variable | Default | Purpose |
|---|---|---|
| `AUTOPARK_LLM__MODEL` | `claude-haiku-4-5` | Claude tier (haiku/sonnet/opus) |
| `AUTOPARK_LLM__API_KEY` | — | Anthropic API key (required to run) |
| `AUTOPARK_EMBEDDING__PROVIDER` | `huggingface` | `huggingface` (local) or `voyage` |
| `AUTOPARK_VECTOR_STORE__HOST` | `localhost` | Weaviate host |
| `AUTOPARK_SQL__URL` | SQLite file | SQL DB connection string |
| `AUTOPARK_RETRIEVAL__TOP_K` | `4` | RAG retrieval depth |
| `AUTOPARK_RETRIEVAL__HYBRID_ALPHA` | `0.5` | dense vs keyword weighting |
| `AUTOPARK_ADMIN__API_TOKEN` | — | secures `/admin` endpoints (fail-closed if unset) |
| `AUTOPARK_ADMIN__ADMIN_WEBHOOK_URL` | — | optional: notify admin of new reservations |
| `AUTOPARK_ADMIN__USER_WEBHOOK_URL` | — | optional: notify user of the decision |

---

## Development

```bash
.venv/Scripts/ruff format --check .          # formatting
.venv/Scripts/ruff check .                   # lint
.venv/Scripts/python -m mypy src eval        # strict type-check
.venv/Scripts/python -m pytest               # tests + coverage
```

(macOS/Linux: use `.venv/bin/...`.) Tests run fully offline — the LLM, vector store, and
embeddings are mocked via in-memory fakes (`tests/fakes.py`).

### Evaluation

```bash
docker compose up -d weaviate && autoparkgpt ingest data/static
python -m eval.run        # prints Recall@K, Precision@K, MRR, and latency
```

See [`EVALUATION.md`](EVALUATION.md) for methodology and metrics.

---

## Project structure

```
autoparkgpt/
├── src/autoparkgpt/
│   ├── domain/           # entities, value objects, ports (Protocols), exceptions
│   ├── application/      # prompts, extraction, LangGraph graph, ChatService, DTOs
│   ├── infrastructure/   # llm, embeddings, vectorstore, persistence, guardrails, config
│   ├── interface/        # api (FastAPI) + cli (Typer)
│   └── container.py      # DI composition root
├── alembic/              # SQL migrations
├── data/static/          # knowledge documents (ingested into Weaviate)
├── eval/                 # evaluation harness (metrics, dataset, runner)
├── tests/                # unit + integration tests
├── docker-compose.yml    # app + weaviate + postgres
└── Dockerfile
```

---

## CI/CD & infrastructure

- **CI/CD:** GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs
  formatting, lint, strict type-checking, tests + coverage, a Docker build, and security
  scans (Trivy filesystem + gitleaks secret scanning). Recommended next steps before
  production: publish the image to a registry and gate merges on coverage thresholds.
- **Infrastructure as Code:** **Terraform is not justified yet** — Stage 1 runs entirely
  on Docker Compose with no cloud footprint to provision. Revisit after Stage 4 once a
  deployment target exists (managed Postgres + Weaviate + a container runtime). See
  [`ARCHITECTURE.md`](ARCHITECTURE.md) §8.

---

## License

Proprietary — internal project.
