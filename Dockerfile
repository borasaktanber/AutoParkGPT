# syntax=docker/dockerfile:1
# Multi-stage build for the AutoParkGPT application image.

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# --------------------------------------------------------------------------- #
# Builder: install dependencies into a virtualenv.
# --------------------------------------------------------------------------- #
FROM base AS builder
WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src ./src

# Install the full application stack (llm + rag + sql + api).
RUN pip install --upgrade pip && pip install ".[all]"

# --------------------------------------------------------------------------- #
# Runtime: copy the venv and source, run as a non-root user.
# --------------------------------------------------------------------------- #
FROM base AS runtime
WORKDIR /app

# Create an unprivileged user.
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src ./src
COPY pyproject.toml README.md ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src"

USER appuser
EXPOSE 8000

# Stage 1D wires the FastAPI app; until then this is the documented entry point.
CMD ["uvicorn", "autoparkgpt.interface.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
