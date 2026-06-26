"""Conversation graph nodes.

Each node is a method on :class:`GraphNodes`, which closes over the domain ports. Nodes
return partial state updates that LangGraph merges into the threaded state.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from autoparkgpt.application.extraction import Intent, classify_intent, extract_slots
from autoparkgpt.application.graphs.state import (
    SLOT_PROMPTS,
    ConversationState,
    get_draft,
    get_history,
    refusal_message,
)
from autoparkgpt.application.prompts import SYSTEM_PROMPT, build_answer_prompt
from autoparkgpt.domain.entities.reservation import (
    Reservation,
    ReservationDraft,
    ReservationSlot,
)
from autoparkgpt.domain.exceptions import (
    InvalidCarNumberError,
    InvalidReservationPeriodError,
    RetrievalError,
)
from autoparkgpt.domain.ports.dynamic_data import DynamicDataPort
from autoparkgpt.domain.ports.embedding import EmbeddingPort
from autoparkgpt.domain.ports.guardrail import GuardrailPort
from autoparkgpt.domain.ports.llm import LLMPort
from autoparkgpt.domain.ports.reservation_repository import ReservationRepositoryPort
from autoparkgpt.domain.ports.vector_store import VectorStorePort
from autoparkgpt.domain.value_objects.car_number import CarNumber
from autoparkgpt.domain.value_objects.chat import ChatMessage
from autoparkgpt.domain.value_objects.reservation_period import ReservationPeriod
from autoparkgpt.infrastructure.config import AppSettings, RetrievalSettings

_logger = structlog.get_logger(__name__)

_HISTORY_WINDOW = 12  # messages of context passed to the model

_RESERVE_INTENT_RE = re.compile(r"\b(reserv\w*|book\w*)\b", re.IGNORECASE)
_CANCEL_RE = re.compile(r"\b(cancel|nevermind|never mind|stop|forget it)\b", re.IGNORECASE)
_MAX_NAME_LEN = 50
_PERIOD_DATETIME_COUNT = 2


@dataclass(slots=True)
class GraphNodes:
    """Holds the ports the nodes operate on."""

    llm: LLMPort
    embedding: EmbeddingPort
    vector_store: VectorStorePort
    dynamic_data: DynamicDataPort
    guardrail: GuardrailPort
    reservation_repo: ReservationRepositoryPort
    retrieval: RetrievalSettings
    app: AppSettings
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    # ----- nodes ------------------------------------------------------------ #
    def ingest_input(self, state: ConversationState) -> ConversationState:
        text = state["user_input"]
        history = [*get_history(state), ChatMessage.user(text)]
        # Reset per-turn ephemeral fields so stale values from a prior turn (which the
        # checkpointer preserves) never leak into this turn's result.
        base: ConversationState = {
            "history": history,
            "retrieved": [],
            "dynamic_context": "",
            "sources": [],
            "reservation_id": None,
        }
        verdict = self.guardrail.check_input(text)
        if not verdict.allowed:
            _logger.info("input_blocked", category=verdict.category)
            return {**base, "blocked": True, "response": refusal_message(verdict.category)}
        return {**base, "blocked": False}

    def classify(self, state: ConversationState) -> ConversationState:
        message = state["user_input"]
        draft = get_draft(state)
        # We are mid-reservation if a slot is awaited or the draft is partially filled.
        in_reservation = state.get("awaiting_slot") is not None or (
            draft != ReservationDraft() and not draft.is_complete
        )
        if in_reservation or _RESERVE_INTENT_RE.search(message):
            # Deterministic routing: stay in (or enter) the reservation flow without
            # depending on the LLM classifier, which previously caused desyncs.
            return {"intent": Intent.RESERVE}
        return {"intent": classify_intent(self.llm, message)}

    def retrieve(self, state: ConversationState) -> ConversationState:
        text = state["user_input"]
        try:
            vector = self.embedding.embed_query(text)
            chunks = self.vector_store.search(
                query_text=text,
                query_vector=vector,
                top_k=self.retrieval.top_k,
                alpha=self.retrieval.hybrid_alpha,
                public_only=True,
            )
        except RetrievalError:
            _logger.warning("retrieval_failed", exc_info=True)
            chunks = []
        return {"retrieved": chunks}

    def fetch_dynamic(self, state: ConversationState) -> ConversationState:
        hours = self.dynamic_data.get_working_hours()
        prices = self.dynamic_data.get_prices()
        availability = self.dynamic_data.get_availability()

        lines: list[str] = []
        if hours:
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            hours_str = ", ".join(
                f"{days[h.day_of_week]}: {'closed' if h.is_closed else f'{h.opens}-{h.closes}'}"
                for h in hours
            )
            lines.append(f"Working hours -> {hours_str}")
        if prices:
            price_str = ", ".join(
                f"{p.label}: {p.amount:.2f} {p.currency}/{p.unit}" for p in prices
            )
            lines.append(f"Prices -> {price_str}")
        if availability:
            avail_str = ", ".join(
                f"Zone {a.zone}: {a.free_spaces}/{a.total_spaces} free" for a in availability
            )
            lines.append(f"Availability -> {avail_str}")
        return {"dynamic_context": "\n".join(lines)}

    def generate(self, state: ConversationState) -> ConversationState:
        intent = state.get("intent", Intent.INFO)
        retrieved = state.get("retrieved", [])
        sources = sorted({c.citation() for c in retrieved})

        if intent is Intent.OTHER:
            system = SYSTEM_PROMPT + "\n\nRespond briefly and helpfully as a parking assistant."
        else:
            context = state.get("dynamic_context", "") or "\n\n".join(
                f"[{c.citation()}] {c.content}" for c in retrieved
            )
            system = SYSTEM_PROMPT + "\n\n" + build_answer_prompt(context)

        history = get_history(state)[-_HISTORY_WINDOW:]
        response = self.llm.generate(history, system=system, max_tokens=None)
        return {"response": response, "sources": sources}

    def reserve(self, state: ConversationState) -> ConversationState:
        message = state["user_input"]
        draft = get_draft(state)
        awaiting: ReservationSlot | None = state.get("awaiting_slot")

        # Allow the user to abandon the reservation flow at any point.
        if awaiting is not None and _CANCEL_RE.search(message):
            return {
                "draft": ReservationDraft(),
                "awaiting_slot": None,
                "response": "No problem — I've cancelled that reservation. Anything else?",
            }

        # 1) Structured extraction (handles rich, multi-field messages).
        slots = extract_slots(self.llm, message, awaiting=awaiting.value if awaiting else None)
        draft, error = self._apply_slots(draft, slots)
        if error is not None:
            return {"draft": draft, "awaiting_slot": awaiting, "response": error}

        # 2) Deterministic fallback: treat a terse reply as the answer to the awaited slot
        #    when extraction didn't already fill it.
        if awaiting is not None:
            draft, error = self._fill_awaited_slot(draft, awaiting, message)
            if error is not None:
                return {"draft": draft, "awaiting_slot": awaiting, "response": error}

        if not draft.is_complete:
            next_slot = draft.missing_slots()[0]
            return {
                "draft": draft,
                "awaiting_slot": next_slot,
                "response": SLOT_PROMPTS[next_slot],
            }

        reservation = draft.to_reservation()
        try:
            reservation.period.validate_window(
                now=self.clock(),
                max_days=self.app.max_reservation_days,
            )
        except InvalidReservationPeriodError as exc:
            return {
                "draft": draft.updated(period=None),
                "awaiting_slot": ReservationSlot.PERIOD,
                "response": f"{exc} Please provide a valid reservation period.",
            }

        saved = self.reservation_repo.add(reservation)
        _logger.info("reservation_created", reservation_id=saved.id)
        return {
            "draft": ReservationDraft(),
            "awaiting_slot": None,
            "reservation_id": saved.id,
            "response": _confirmation(saved),
        }

    def output_guard(self, state: ConversationState) -> ConversationState:
        response = state.get("response", "")
        verdict = self.guardrail.scan_output(response)
        if not verdict.allowed:
            _logger.warning("output_blocked", category=verdict.category)
            response = refusal_message(verdict.category)
        history = [*get_history(state), ChatMessage.assistant(response)]
        return {"response": response, "history": history}

    # ----- helpers ---------------------------------------------------------- #
    def _apply_slots(
        self,
        draft: ReservationDraft,
        slots: dict[str, str],
    ) -> tuple[ReservationDraft, str | None]:
        changes: dict[str, object] = {}
        if "first_name" in slots:
            changes["first_name"] = slots["first_name"]
        if "last_name" in slots:
            changes["last_name"] = slots["last_name"]
        if "car_number" in slots:
            try:
                changes["car_number"] = CarNumber.parse(
                    slots["car_number"], pattern=self.app.car_number_pattern
                )
            except InvalidCarNumberError as exc:
                return draft, f"{exc} Please provide a valid car number."

        start, end = slots.get("period_start"), slots.get("period_end")
        if start and end:
            try:
                changes["period"] = ReservationPeriod(
                    start=_parse_datetime(start),
                    end=_parse_datetime(end),
                )
            except (ValueError, InvalidReservationPeriodError):
                return draft, (
                    "I couldn't understand the reservation period. Please give a start and "
                    "end date & time, e.g. 2030-06-01 09:00 to 2030-06-01 13:00."
                )
        return draft.updated(**changes), None

    def _fill_awaited_slot(
        self,
        draft: ReservationDraft,
        slot: ReservationSlot,
        message: str,
    ) -> tuple[ReservationDraft, str | None]:
        """Interpret a terse reply as the direct answer to the awaited slot.

        Only fills a slot the structured extraction left empty, so rich messages still
        win. Names reject digit-bearing input (e.g. a plate typed at the wrong step).
        """

        text = message.strip()
        match slot:
            case ReservationSlot.FIRST_NAME if draft.first_name is None:
                name = _as_name(text)
                if name:
                    return draft.updated(first_name=name), None
            case ReservationSlot.LAST_NAME if draft.last_name is None:
                name = _as_name(text)
                if name:
                    return draft.updated(last_name=name), None
            case ReservationSlot.CAR_NUMBER if draft.car_number is None:
                try:
                    car = CarNumber.parse(text, pattern=self.app.car_number_pattern)
                except InvalidCarNumberError as exc:
                    return draft, f"{exc} Please provide a valid car number."
                return draft.updated(car_number=car), None
            case ReservationSlot.PERIOD if draft.period is None:
                period = _try_parse_period(text)
                if period is not None:
                    return draft.updated(period=period), None
            case _:
                pass
        return draft, None


def _as_name(text: str) -> str | None:
    """Return a cleaned name, or None if the text isn't a plausible name."""

    cleaned = " ".join(text.split())
    if not cleaned or len(cleaned) > _MAX_NAME_LEN or any(ch.isdigit() for ch in cleaned):
        return None
    if not any(ch.isalpha() for ch in cleaned):
        return None
    return cleaned


def _try_parse_period(text: str) -> ReservationPeriod | None:
    """Best-effort parse of two ISO-like datetimes from free text."""

    matches = re.findall(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", text)
    if len(matches) < _PERIOD_DATETIME_COUNT:
        return None
    try:
        return ReservationPeriod(
            start=_parse_datetime(matches[0]),
            end=_parse_datetime(matches[1]),
        )
    except (ValueError, InvalidReservationPeriodError):
        return None


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime, normalizing naive values to UTC.

    The LLM often returns timezone-naive datetimes (e.g. ``2030-06-01T09:00:00``);
    we assume UTC so they compare safely against the timezone-aware clock.
    """

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _confirmation(reservation: Reservation) -> str:
    period = reservation.period
    return (
        f"Thank you, {reservation.first_name} {reservation.last_name}! "
        f"Your reservation for vehicle {reservation.car_number.value} from "
        f"{period.start:%Y-%m-%d %H:%M} to {period.end:%Y-%m-%d %H:%M} has been created. "
        f"Reference: {reservation.id[:8]} (status: pending approval)."
    )
