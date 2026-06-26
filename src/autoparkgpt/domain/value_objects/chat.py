"""Chat message value objects."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Role(StrEnum):
    """Conversation roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    model_config = ConfigDict(frozen=True)

    role: Role
    content: str

    @classmethod
    def user(cls, content: str) -> ChatMessage:
        return cls(role=Role.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> ChatMessage:
        return cls(role=Role.ASSISTANT, content=content)

    @classmethod
    def system(cls, content: str) -> ChatMessage:
        return cls(role=Role.SYSTEM, content=content)
