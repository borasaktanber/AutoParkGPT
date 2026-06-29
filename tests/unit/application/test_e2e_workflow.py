"""End-to-end test of the unified Stage 4 flow: chat create -> admin approve -> recorded.

Exercises the real wiring — the chat reserve node starts the orchestration workflow, and
the admin approval resumes the same workflow run (which records via the recorder and
notifies the user) — then the user reads the decision back through the chat STATUS intent.
"""

from __future__ import annotations

from datetime import UTC, datetime

from autoparkgpt.application.factory import build_chat_service, build_reservation_workflow
from autoparkgpt.application.use_cases import AdminApprovalService
from autoparkgpt.infrastructure.config import AppSettings, RetrievalSettings
from autoparkgpt.infrastructure.persistence import InMemoryReservationRepository
from tests.fakes import (
    AllowAllGuardrail,
    FakeDynamicData,
    FakeEmbedding,
    FakeVectorStore,
    RecordingAdminNotifier,
    RecordingReservationRecorder,
    RecordingUserNotifier,
)
from tests.unit.application.test_chat_graph import ScriptedLLM

_NOW = datetime(2030, 1, 1, tzinfo=UTC)
_FULL = (
    '{"first_name": "Ada", "last_name": "Lovelace", "car_number": "AB123CD", '
    '"period_start": "2030-06-01T09:00:00+00:00", "period_end": "2030-06-01T13:00:00+00:00"}'
)


def test_unified_create_approve_record_status() -> None:
    repo = InMemoryReservationRepository()
    admin_notifier = RecordingAdminNotifier()
    user_notifier = RecordingUserNotifier()
    recorder = RecordingReservationRecorder()

    workflow = build_reservation_workflow(
        reservation_repo=repo,
        admin_notifier=admin_notifier,
        user_notifier=user_notifier,
        recorder=recorder,
        max_reservation_days=30,
        clock=lambda: _NOW,
    )
    chat = build_chat_service(
        llm=ScriptedLLM(intent="RESERVE", slot_replies=[_FULL]),
        embedding=FakeEmbedding(),
        vector_store=FakeVectorStore(),
        dynamic_data=FakeDynamicData(),
        guardrail=AllowAllGuardrail(),
        reservation_repo=repo,
        admin_notifier=admin_notifier,
        retrieval=RetrievalSettings(),
        app=AppSettings(),
        clock=lambda: _NOW,
        workflow=workflow,
    )
    approval = AdminApprovalService(repo, user_notifier, recorder=recorder, workflow=workflow)

    # 1. User books via chat -> orchestration starts, persists pending, notifies admin, pauses.
    created = chat.respond("sess", "reserve a spot, details attached")
    ref = created.reservation_id[:8]
    assert [r.id for r in admin_notifier.notified] == [created.reservation_id]
    assert workflow.is_pending(created.reservation_id)

    # 2. User checks status before a decision -> pending.
    pending = chat.respond("sess", f"is reservation {ref} approved?")
    assert "pending" in pending.message.lower()

    # 3. Admin approves -> resumes the SAME workflow run -> records + notifies user.
    approval.approve(ref)
    assert [r.id for r in recorder.recorded] == [created.reservation_id]
    assert [r.id for r in user_notifier.decisions] == [created.reservation_id]
    assert not workflow.is_pending(created.reservation_id)

    # 4. Decision flows back to the user through the chat agent.
    approved = chat.respond("sess", f"is reservation {ref} approved?")
    assert "approved" in approved.message.lower()
