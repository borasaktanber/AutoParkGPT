"""Performance measurement: latency percentiles and throughput."""

from __future__ import annotations

import time
from collections.abc import Callable
from statistics import mean

from pydantic import BaseModel


class LatencyReport(BaseModel):
    """Latency / throughput statistics for a repeated operation."""

    runs: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    throughput_per_s: float


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    # Nearest-rank percentile.
    rank = max(1, round(pct / 100.0 * len(sorted_values)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


def measure_latency(operation: Callable[[], object], *, runs: int = 20) -> LatencyReport:
    """Run ``operation`` ``runs`` times and report latency percentiles + throughput."""

    if runs <= 0:
        raise ValueError("runs must be positive.")
    durations_ms: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        operation()
        durations_ms.append((time.perf_counter() - start) * 1000.0)

    ordered = sorted(durations_ms)
    mean_ms = mean(durations_ms)
    return LatencyReport(
        runs=runs,
        mean_ms=mean_ms,
        p50_ms=_percentile(ordered, 50),
        p95_ms=_percentile(ordered, 95),
        throughput_per_s=(1000.0 / mean_ms) if mean_ms > 0 else 0.0,
    )
