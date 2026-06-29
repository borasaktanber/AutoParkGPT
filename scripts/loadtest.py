# ruff: noqa
"""Stage 4 system / load testing.

Measures latency and throughput for the three subsystems the spec calls out:
  * Chatbot        — concurrent POST /chat
  * Admin workflow — create reservations, then approve them via /admin
  * MCP server     — save_reservation calls through an in-memory MCP session

Prerequisites for the HTTP parts: the app running (uvicorn ... interface.api.main:app),
Weaviate up, and AUTOPARK_ADMIN__API_TOKEN set. Run:

    PYTHONPATH=src python scripts/loadtest.py
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "src")

BASE = os.environ.get("AUTOPARK_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.environ.get("AUTOPARK_ADMIN__API_TOKEN", "local-demo-admin-token")


def _call(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers=headers or {"content-type": "application/json"}
    )
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()
    return (time.perf_counter() - t) * 1000.0


def _pct(values, p):
    values = sorted(values)
    k = max(1, round(p / 100 * len(values)))
    return values[min(k, len(values)) - 1]


def _stats(durations):
    return {
        "runs": len(durations),
        "mean_ms": round(statistics.mean(durations), 1),
        "p50_ms": round(_pct(durations, 50), 1),
        "p95_ms": round(_pct(durations, 95), 1),
    }


def chatbot_load(total=20, workers=4):
    _call("POST", "/chat", {"session_id": "warm", "message": "hello"})  # warm
    def one(i):
        return _call("POST", "/chat", {"session_id": f"load-{i}", "message": "What are your prices?"})
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        durations = list(ex.map(one, range(total)))
    wall = time.perf_counter() - start
    return {**_stats(durations), "workers": workers, "throughput_per_s": round(total / wall, 2)}


def admin_workflow_load(total=10):
    auth = {"X-Admin-Token": TOKEN, "content-type": "application/json"}
    # Create reservations via chat, then approve each via the admin API.
    refs = []
    create_ms = []
    msg = (
        "reserve parking for Load Tester, plate LT{0:04d}, "
        "from 2030-09-01 09:00 to 2030-09-01 12:00"
    )
    for i in range(total):
        t = time.perf_counter()
        req = urllib.request.Request(
            BASE + "/chat",
            data=json.dumps({"session_id": f"adm-{i}", "message": msg.format(i)}).encode(),
            headers={"content-type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read())
        create_ms.append((time.perf_counter() - t) * 1000.0)
        if body.get("reservation_id"):
            refs.append(body["reservation_id"][:8])
    approve_ms = [_call("POST", f"/admin/reservations/{ref}/approve", None, auth) for ref in refs]
    return {
        "create": _stats(create_ms),
        "approve": _stats(approve_ms) if approve_ms else {"runs": 0},
        "approved": len(approve_ms),
    }


def mcp_load(total=50):
    import asyncio
    from datetime import UTC, datetime, timedelta

    from mcp.shared.memory import create_connected_server_and_client_session

    from autoparkgpt.infrastructure.recording import FileReservationRecorder
    from autoparkgpt.mcp_server import build_mcp_server

    import tempfile

    rec = FileReservationRecorder(os.path.join(tempfile.mkdtemp(), "load.txt"))
    server = build_mcp_server(rec)
    start = datetime(2030, 6, 1, 9, 0, tzinfo=UTC)

    async def run():
        durations = []
        async with create_connected_server_and_client_session(server) as session:
            for i in range(total):
                t = time.perf_counter()
                await session.call_tool(
                    "save_reservation",
                    {
                        "name": f"Load {i}",
                        "car_number": f"LD{i:04d}",
                        "period_start": start.isoformat(),
                        "period_end": (start + timedelta(hours=2)).isoformat(),
                    },
                )
                durations.append((time.perf_counter() - t) * 1000.0)
        return durations

    durations = asyncio.run(run())
    wall = sum(durations) / 1000.0
    return {**_stats(durations), "throughput_per_s": round(total / wall, 2) if wall else 0}


def main():
    report = {}
    try:
        report["chatbot"] = chatbot_load()
        report["admin_workflow"] = admin_workflow_load()
    except Exception as exc:  # noqa: BLE001
        report["http_error"] = f"{type(exc).__name__}: {exc} (is the server running?)"
    report["mcp_server"] = mcp_load()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
