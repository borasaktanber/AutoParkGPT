#!/usr/bin/env python
"""Enable LangGraph Studio against a local ``langgraph dev`` server (Chrome/Edge).

Why this exists
---------------
Modern Chromium browsers treat a request from the hosted Studio page
(``https://smith.langchain.com``) to a loopback address (``127.0.0.1``) as a
*Private Network Access* (PNA) request and send a CORS preflight carrying
``Access-Control-Request-Private-Network: true``.

Starlette's ``CORSMiddleware`` rejects that preflight with ``400 Disallowed CORS
private-network`` unless it is constructed with ``allow_private_network=True``.
``langgraph-api`` (as of 0.10.0) builds the middleware without that flag, and its
separate ``PrivateNetworkMiddleware`` only appends the allow header to the already-400
response — too late. The flag also cannot be supplied through ``langgraph.json`` because
the ``CorsConfig`` schema omits it and pydantic drops the unknown key.

This script patches the installed ``langgraph_api/server.py`` in the active virtualenv to
pass ``allow_private_network=True`` to the default ``CORSMiddleware``. It is **idempotent**
and **dev-only**; it touches a third-party package inside the venv, so re-run it after any
reinstall/upgrade of ``langgraph-api``. It refuses to run outside a virtualenv as a guard
against patching a system/global install.

Usage
-----
    python scripts/enable_studio_pna.py            # apply (idempotent)
    python scripts/enable_studio_pna.py --check     # report status, change nothing

Then restart ``langgraph dev`` for the change to take effect.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_MARKER = "allow_private_network=True"

# The exact default CORSMiddleware block langgraph-api builds when no custom CORS config
# is supplied (the `langgraph dev` case). We insert the PNA flag right after allow_headers.
_ANCHOR = """                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["""

_REPLACEMENT = """                allow_methods=["*"],
                allow_headers=["*"],
                allow_private_network=True,  # patched: allow Studio PNA preflight (loopback)
                expose_headers=["""


def _server_path() -> Path:
    import langgraph_api  # noqa: PLC0415 - optional dev dependency, imported lazily

    return Path(langgraph_api.__file__).parent / "server.py"


def _in_virtualenv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only report whether the patch is applied; make no changes.",
    )
    args = parser.parse_args()

    if not _in_virtualenv():
        print("Refusing to run: not inside a virtualenv (would patch a global install).")
        return 2

    try:
        path = _server_path()
    except ImportError:
        print("langgraph-api is not installed in this environment; nothing to patch.")
        return 1

    source = path.read_text(encoding="utf-8")

    if _MARKER in source:
        print(f"Already patched: {path}")
        return 0

    if args.check:
        print(f"Not patched: {path}")
        return 1

    if _ANCHOR not in source:
        print(
            "Could not find the expected CORSMiddleware block in "
            f"{path}.\nlanggraph-api's layout likely changed; patch manually by adding "
            f"'{_MARKER}' to its CORSMiddleware(...) call."
        )
        return 1

    backup = path.with_suffix(".py.orig")
    if not backup.exists():
        shutil.copy2(path, backup)

    path.write_text(source.replace(_ANCHOR, _REPLACEMENT, 1), encoding="utf-8")
    print(f"Patched: {path}\nBackup:  {backup}\nRestart `langgraph dev` to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
