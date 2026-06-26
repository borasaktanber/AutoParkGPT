"""Heuristic patterns for the guardrail pipeline.

These are intentionally simple, fast, and well-tested. The pipeline is structured so a
heavier ML-based classifier (e.g. an ``llm-guard``/``rebuff`` adapter) can be layered in
later without changing the port or the application layer.
"""

from __future__ import annotations

import re
from re import Pattern

# Sentinel embedded in the system prompt; if it ever appears in output, the model has
# leaked its instructions and the response must be blocked.
SYSTEM_PROMPT_SENTINEL = "APGPT_SYSTEM_PROMPT_DO_NOT_REVEAL"

# Prompt-injection / jailbreak heuristics (case-insensitive).
_INJECTION_SOURCES: tuple[str, ...] = (
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|messages)",
    r"disregard\s+(all\s+)?(previous|prior|above|the)\s+.*(instructions|rules)",
    r"forget\s+(all\s+)?(previous|prior|your)\s+(instructions|rules|prompt)",
    r"you\s+are\s+now\s+",
    r"developer\s+mode",
    r"\bDAN\b",
    r"jailbreak",
    r"reveal\s+(your\s+)?(the\s+)?(system\s+)?(prompt|instructions)",
    r"(print|show|repeat|output|dump)\s+(your\s+|the\s+)?(system\s+)?(prompt|instructions)",
    r"what\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions)",
    r"(dump|export|list|show)\s+(the\s+|all\s+)?(database|vector|embeddings|documents|index)",
    r"(internal|private|confidential)\s+(docs|documents|data|information)",
    r"pretend\s+(to\s+be|you\s+are)",
    r"bypass\s+(the\s+)?(rules|filter|guardrail|safety)",
    r"override\s+(the\s+)?(system|rules|instructions)",
)

INJECTION_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(src, re.IGNORECASE) for src in _INJECTION_SOURCES
)

# Output-leakage heuristics: internal markers and secret-looking tokens.
_LEAKAGE_SOURCES: tuple[str, ...] = (
    re.escape(SYSTEM_PROMPT_SENTINEL),
    r"begin\s+system\s+prompt",
    r"\bvisibility\s*[:=]\s*internal\b",
    r"\bINTERNAL[-_\s]?ONLY\b",
    r"sk-ant-[a-zA-Z0-9_-]{8,}",  # Anthropic API key shape
    r"\bsk-[a-zA-Z0-9]{20,}\b",  # generic secret-key shape
)

LEAKAGE_PATTERNS: tuple[Pattern[str], ...] = tuple(
    re.compile(src, re.IGNORECASE) for src in _LEAKAGE_SOURCES
)
