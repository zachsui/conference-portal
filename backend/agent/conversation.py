"""Per-attendee conversation state for the AI assistant.

Holds at most one pending_action per attendee. The orchestrator uses this
to implement deterministic confirmation flow ("Would you register for
S031?" → user replies "yes" → execute), without relying on Gemini to
remember context across turns.

State is in-memory and resets when the backend restarts.
"""
from __future__ import annotations

import re
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

from .schemas import PendingAction


# ─────────────── Confirmation / cancellation phrase matchers ───────────────
# Matched against the FULL normalized user message. We only short-circuit
# when the message is *just* a confirmation — "yes please find an AI
# session" should reach Gemini, not auto-execute.
CONFIRMATION_PHRASES = {
    "yes",
    "y",
    "yep",
    "yeah",
    "yup",
    "confirm",
    "confirmed",
    "proceed",
    "go ahead",
    "do it",
    "register me",
    "sign me up",
    "sure",
    "ok",
    "okay",
    "k",
    "absolutely",
    "please do",
    "yes please",
}

CANCELLATION_PHRASES = {
    "no",
    "n",
    "nope",
    "cancel",
    "never mind",
    "nevermind",
    "stop",
    "don't",
    "do not",
    "no thanks",
    "no thank you",
    "skip",
    "abort",
}

_PUNCT_RE = re.compile(r"[\s.!?,;:'\"]+")


def _normalize(text: str) -> str:
    """Lowercase, strip whitespace and trailing punctuation."""
    if not text:
        return ""
    cleaned = _PUNCT_RE.sub(" ", text.lower()).strip()
    # Collapse interior multi-spaces.
    cleaned = " ".join(cleaned.split())
    return cleaned


def is_confirmation(text: str) -> bool:
    return _normalize(text) in CONFIRMATION_PHRASES


def is_cancellation(text: str) -> bool:
    return _normalize(text) in CANCELLATION_PHRASES


# ─────────────── Pending action store ───────────────
class ConversationStateStore:
    """One pending_action per attendee, with TTL."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Dict[str, PendingAction] = {}

    def get(self, attendee_id: str) -> Optional[PendingAction]:
        """Return the pending action if present and not expired (auto-clears expired)."""
        with self._lock:
            pa = self._state.get(attendee_id)
            if pa is None:
                return None
            if self.is_expired(pa):
                self._state.pop(attendee_id, None)
                return None
            return pa

    def peek_including_expired(
        self, attendee_id: str
    ) -> Optional[PendingAction]:
        """Return the pending action even if expired (used to show the user what expired)."""
        with self._lock:
            return self._state.get(attendee_id)

    def set(self, attendee_id: str, action: PendingAction) -> None:
        with self._lock:
            self._state[attendee_id] = action

    def clear(self, attendee_id: str) -> None:
        with self._lock:
            self._state.pop(attendee_id, None)

    @staticmethod
    def is_expired(action: PendingAction) -> bool:
        try:
            created = datetime.fromisoformat(action.created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        elapsed_min = (
            datetime.now(timezone.utc) - created
        ).total_seconds() / 60.0
        return elapsed_min > action.expires_after_minutes


conversation_store = ConversationStateStore()


# ─────────────── Pending action factory ───────────────
def make_pending_register(
    attendee_id: str,
    session_id: str,
    session_title: Optional[str] = None,
    expires_after_minutes: int = 10,
) -> PendingAction:
    return PendingAction(
        attendee_id=attendee_id,
        action="register_session",
        session_id=session_id,
        session_title=session_title,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_after_minutes=expires_after_minutes,
    )
