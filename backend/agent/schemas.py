"""Pydantic models for the AI assistant API."""
from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    attendee_id: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=2000)


class ToolCallTrace(BaseModel):
    step_number: int
    tool_name: str
    arguments: dict
    result: Any
    success: bool
    latency_ms: int
    error: Optional[str] = None


class PolicyViolation(BaseModel):
    rule: str
    detail: str
    tool_name: Optional[str] = None


ChatStatus = Literal["completed", "clarification_needed", "failed"]


class PendingAction(BaseModel):
    """A proposed action awaiting user confirmation in the next turn."""

    attendee_id: str
    action: Literal["register_session"]
    session_id: str
    session_title: Optional[str] = None
    created_at: str  # ISO timestamp
    expires_after_minutes: int = 10


class ChatResponse(BaseModel):
    trace_id: str
    user_message: str
    tool_calls: List[ToolCallTrace] = Field(default_factory=list)
    final_answer: str
    status: ChatStatus
    policy_violations: List[PolicyViolation] = Field(default_factory=list)
    # Pending-action / confirmation flow
    pending_action_before: Optional[PendingAction] = None
    pending_action_after: Optional[PendingAction] = None
    confirmation_detected: bool = False


class TraceSummary(BaseModel):
    trace_id: str
    attendee_id: Optional[str]
    user_message: str
    final_answer: str
    status: ChatStatus
    tool_call_count: int
    policy_violation_count: int
    created_at: str
