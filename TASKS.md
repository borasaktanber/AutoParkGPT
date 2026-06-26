# AutoParkGPT — Task Plan

> Generated and maintained by Claude per `CLAUDE.md`.
> Legend: ☐ not started · ◐ in progress · ☑ done · ⏸ awaiting approval
>
> **Workflow rule (from `CLAUDE.md` & PROJECT_REQUIREMENTS.md): do not start a stage
> without explicit approval. After each completed task: run tests, update README,
> update this file, and explain design decisions.**

---

## Phase 1 — Requirements Analysis & Design  ◐ (awaiting approval)

- ☑ Read & analyze PROJECT_REQUIREMENTS.md and CLAUDE.md
- ☑ Identify ambiguities + recommend improvements (see `ARCHITECTURE.md` §2)
- ☑ Propose production architecture (Clean Architecture + ports/adapters)
- ☑ Create `ARCHITECTURE.md`
- ☑ Create `TASKS.md`
- ⏸ **Obtain approval to begin Stage 1** ← we are here

---

## Stage 0 — Project Scaffolding  ☑

- ☑ `pyproject.toml`: deps (grouped extras) + ruff, mypy(strict), pytest, coverage
- ☑ Repo layout per `ARCHITECTURE.md` §4
- ☑ `pydantic-settings` config + `.env.example` (no secrets)
- ☑ `structlog` logging setup
- ☑ DI composition root skeleton (`container.py`)
- ☑ `docker-compose.yml` (app + weaviate + postgres) + multi-stage `Dockerfile` (non-root)
- ☑ GitHub Actions CI (format, lint, type-check, test+coverage, docker build, Trivy + gitleaks)
- ☑ Pre-commit hooks

**Exit:** ✅ ruff format/lint clean, `mypy --strict` clean, `pytest` 6 passed @ 98% coverage.

---

## Stage 1 — RAG Chatbot  ☑

> **Stage 1 status: ✅ COMPLETE.** 112 tests passing at 92% coverage; ruff + `mypy --strict` clean. Awaiting approval for Stage 2.

### 1A. Domain  ☑
- ☑ Entities: `Reservation` (+ `ReservationDraft`, `ReservationStatus`), `ChatMessage`
- ☑ Value objects: `CarNumber`, `ReservationPeriod`, knowledge + dynamic-data VOs (validation)
- ☑ Ports (Protocols): `LLMPort`, `EmbeddingPort`, `VectorStorePort`, `DynamicDataPort`, `ReservationRepositoryPort`, `GuardrailPort`
- ☑ Domain exceptions
- ☑ Unit tests (≥2/module)

### 1B. Infrastructure adapters  ☑
- ☑ `AnthropicLLMAdapter` (langchain-anthropic, config-driven tier, capability-aware adaptive thinking)
- ☑ Embedding adapters: HuggingFace `bge-small-en-v1.5` (default) + Voyage `voyage-3` + factory
- ☑ `WeaviateVectorStore`: schema, upsert, hybrid search, public-only metadata filter
- ☑ Document ingestion pipeline + loader: load → chunk → embed → index (configurable)
- ☑ SQLAlchemy models + repos (SQL + in-memory) + dynamic data + Alembic migration + seed
- ☑ `DynamicDataPort` impl (hours/prices/availability)
- ☑ Guardrail pipeline: input validation, injection/jailbreak detection, scope enforcement, output leakage scan
- ☑ Mocked unit tests (injected fakes; no network)

### 1C. Application (LangGraph)  ☑
- ☑ Typed graph state (`ConversationState`)
- ☑ Nodes: input-guardrail → classify → retrieval / dynamic / slot-filling → generation → output-guardrail
- ☑ Reservation slot-filling (collect first/last name, car number, period; ask for missing; validate; persist)
- ☑ Source attribution in responses
- ☑ Checkpointer (MemorySaver; Postgres-backed noted as future enhancement)
- ☑ Use-case + full-graph tests

### 1D. Interface  ☑
- ☑ FastAPI: `/chat`, `/health`; DTOs; `DomainError` exception mapper; lifespan init
- ☑ CLI (Typer): `version`, `ingest`, `chat`
- ☑ API + CLI tests

### 1E. Evaluation  ☑
- ☑ Gold dataset (query → relevant docs) in `eval/`
- ☑ Retrieval metrics: Recall@K, Precision@K, MRR (pure + tested)
- ☑ Performance: latency p50/p95, throughput
- ☑ Faithfulness / context-precision (RAGAS-style) — documented as recommended next metric
- ☑ `EVALUATION.md` report

### 1F. Stage-1 deliverables (per spec "Outcome")  ☑
- ☑ Update `README.md` (setup, usage, structure, config, env vars, architecture, design decisions, diagrams)
- ☑ Run full test suite + coverage (112 passed, 92%)
- ☑ Evaluation report (`EVALUATION.md`)
- ☑ CI/CD recommendation (documented — GitHub Actions; README + `ARCHITECTURE.md`)
- ☑ Infrastructure recommendation (documented — Terraform deferred, see `ARCHITECTURE.md` §8)
- ☑ **Explain design decisions & request approval for Stage 2**

---

## Stage 2 — Human-in-the-Loop Admin Agent  ☑

> 145 tests passing at 92% coverage; ruff + `mypy --strict` clean. Verified end-to-end
> against the live stack (real Claude + Weaviate + SQLite) and via the secured REST API.

- ☑ Second agent for administrator interaction (`AdminApprovalService` + LLM `AdminApprovalAgent`)
- ☑ Reservation lifecycle: Created → Pending → Review → Approved/Rejected → Notify → user can query status
- ☑ Communication channel: **REST API + webhook** (per project decision); `AdminNotifierPort` / `UserNotifierPort` with logging (default) + webhook adapters
- ☑ Decision routed back to the first agent: `UserNotifierPort` push + new `STATUS` chat intent reading shared state
- ☑ Domain transitions (`approve()`/`reject()` reject non-pending) + repo `update`/`find_by_reference`/`list_by_status` (SQL + in-memory)
- ☑ Secured admin REST router (`/admin/reservations` list/approve/reject/decision), `X-Admin-Token`, fail-closed
- ☑ Tests (domain, service, agent, notifiers, repo, status flow, admin endpoints + auth)
- ☑ Docs (README admin section, `ARCHITECTURE.md` §9 + lifecycle diagram), CI/CD + infra recommendations
- ☑ Note: a mid-turn LangGraph `interrupt` is deferred to Stage 4's unified orchestration (rationale in `ARCHITECTURE.md` §9)

---

## Stage 3 — MCP Server  ☑

> 165 tests passing; ruff + `mypy --strict` clean. Verified end-to-end: approval writes
> the record file, and the MCP tools read/write it.

- ☑ Built our own MCP server on the official `mcp` SDK (`FastMCP`) — rationale in `ARCHITECTURE.md` §10
- ☑ Tools: `save_reservation`, `list_reservations`, `find_reservation`, `health_check`
- ☑ On approval, append to text file: `Name | Car Number | Reservation Period | Approval Time` (`FileReservationRecorder`, append-only, locked, fsync)
- ☑ Security: no client-controlled paths, input validation/normalization, `|`-injection rejected, read-only list/find, stdio transport (HTTP behind auth)
- ☑ Integration: `AdminApprovalService` records on approve (best-effort); DI-wired; `autoparkgpt-mcp` console entry point
- ☑ Tests (recorder format/parse/find, MCP tools + validation, approve-records/reject-doesn't)
- ☑ Docs (README MCP section + Claude Desktop config, `ARCHITECTURE.md` §10, `.env.example`), CI/CD + infra recommendations

---

## Stage 4 — LangGraph Orchestration  ☐ (gated)

- ☐ Unified graph: user input → retrieval → context validation → response → reservation state → human approval → approval result → MCP → persistence → error handling
- ☐ Typed shared state across all components
- ☐ End-to-end workflow tests
- ☐ System testing: load tests (chatbot, admin workflow, MCP), integration, latency/reliability/retrieval-quality measurement
- ☐ Final README, full docs, CI/CD + infra recommendations, design write-up

---

## Definition of Done (every stage)
- All code typed (`mypy --strict`), formatted (ruff), linted.
- ≥2 automated tests per module; LLM/vector-DB/external calls mocked in unit tests.
- README + relevant docs updated; design decisions explained.
- CI green; coverage reported.
- CI/CD and infrastructure recommendations restated.
- Explicit approval obtained before the next stage.
