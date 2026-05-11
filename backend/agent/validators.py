"""Policy enforcement for agent tool calls.

The orchestrator owns a `PolicyState` per chat turn and consults the
validators below before executing each model-requested tool call. Blocked
calls return a structured policy_violation back to the model so it can
recover gracefully (e.g. "you must check capacity first").
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set

from .schemas import PolicyViolation


class PolicyState:
    """Tracks what the agent has done so far in this turn."""

    def __init__(self, attendee_id: str) -> None:
        self.attendee_id = attendee_id
        self.searched_session_ids: Set[str] = set()
        self.detail_session_ids: Set[str] = set()
        self.capacity_checked: Dict[str, dict] = {}
        self.registered_session_ids: Set[str] = set()
        self.cancelled_registration_ids: Set[str] = set()
        self.agenda_fetched: bool = False
        self.known_registration_ids: Set[str] = set()

    @property
    def known_session_ids(self) -> Set[str]:
        return (
            self.searched_session_ids
            | self.detail_session_ids
            | set(self.capacity_checked.keys())
        )

    def record_search(self, result: dict) -> None:
        for s in result.get("sessions", []) or []:
            sid = s.get("session_id")
            if sid:
                self.searched_session_ids.add(sid)

    def record_detail(self, args: dict, _result: dict) -> None:
        sid = args.get("session_id")
        if sid:
            self.detail_session_ids.add(sid)

    def record_capacity(self, args: dict, result: dict) -> None:
        sid = args.get("session_id")
        if sid and result.get("ok"):
            self.capacity_checked[sid] = result

    def record_register(self, args: dict, result: dict) -> None:
        if result.get("ok"):
            sid = args.get("session_id")
            if sid:
                self.registered_session_ids.add(sid)
            reg = result.get("registration") or {}
            rid = reg.get("registration_id")
            if rid:
                self.known_registration_ids.add(rid)

    def record_cancel(self, args: dict, result: dict) -> None:
        if result.get("ok"):
            rid = args.get("registration_id")
            if rid:
                self.cancelled_registration_ids.add(rid)

    def record_agenda(self, result: dict) -> None:
        self.agenda_fetched = True
        for item in result.get("items", []) or []:
            rid = item.get("registration_id")
            if rid:
                self.known_registration_ids.add(rid)


# ─────────────── Pre-call validation ───────────────
def validate_tool_call(
    tool_name: str,
    arguments: dict,
    state: PolicyState,
) -> Optional[PolicyViolation]:
    """Return a PolicyViolation if the call should be blocked."""

    if tool_name == "register_session":
        sid = arguments.get("session_id")
        if not sid:
            return PolicyViolation(
                rule="register_requires_session_id",
                detail="register_session requires a session_id.",
                tool_name=tool_name,
            )
        # Rule 2: must have searched/looked up the session first
        if sid not in state.known_session_ids:
            return PolicyViolation(
                rule="must_know_session_id",
                detail=(
                    f"Cannot register for {sid}: this ID has not been "
                    "produced by search_sessions, get_session_detail, or "
                    "get_agenda yet. Look it up first."
                ),
                tool_name=tool_name,
            )
        # Rule 2 (continued): capacity must have been checked
        cap = state.capacity_checked.get(sid)
        if cap is None:
            return PolicyViolation(
                rule="must_check_capacity_first",
                detail=(
                    f"Cannot register for {sid}: check_capacity must be "
                    "called for this session_id before register_session."
                ),
                tool_name=tool_name,
            )
        # Rule 4: cannot register if full
        if cap.get("status") == "full" or cap.get("seats_remaining", 0) <= 0:
            return PolicyViolation(
                rule="cannot_register_when_full",
                detail=(
                    f"Cannot register for {sid}: session is full. "
                    "Suggest alternatives."
                ),
                tool_name=tool_name,
            )

    if tool_name == "cancel_registration":
        rid = arguments.get("registration_id")
        if not rid or not isinstance(rid, str):
            return PolicyViolation(
                rule="cancel_requires_registration_id",
                detail=(
                    "cancel_registration requires a registration_id "
                    "(format: REG-XXXXXXXXXX)."
                ),
                tool_name=tool_name,
            )
        if not rid.upper().startswith("REG-"):
            return PolicyViolation(
                rule="cancel_requires_valid_registration_id",
                detail=(
                    f"'{rid}' does not look like a registration_id. "
                    "Call get_agenda first to find the right ID — never "
                    "guess registration IDs."
                ),
                tool_name=tool_name,
            )
        # Rule 7: must have actually seen this registration_id from get_agenda
        # or a successful registration in this turn.
        if rid not in state.known_registration_ids:
            return PolicyViolation(
                rule="cancel_requires_known_registration_id",
                detail=(
                    f"Registration '{rid}' has not been produced by "
                    "get_agenda or a successful register_session in this "
                    "conversation. Call get_agenda first to look up "
                    "the user's actual registration IDs."
                ),
                tool_name=tool_name,
            )

    return None


def bind_attendee_id(
    tool_name: str, arguments: dict, attendee_id: str
) -> dict:
    """Force the attendee_id arg to the request-scoped attendee.

    The LLM must never be able to act on behalf of another attendee, even
    if it hallucinates an ID. We silently overwrite.
    """
    if tool_name in ("register_session", "get_agenda"):
        return {**arguments, "attendee_id": attendee_id}
    return arguments


def update_state_after_tool(
    tool_name: str, arguments: dict, result: Any, state: PolicyState
) -> None:
    if not isinstance(result, dict):
        return
    if tool_name == "search_sessions":
        state.record_search(result)
    elif tool_name == "get_session_detail":
        state.record_detail(arguments, result)
    elif tool_name == "check_capacity":
        state.record_capacity(arguments, result)
    elif tool_name == "register_session":
        state.record_register(arguments, result)
    elif tool_name == "cancel_registration":
        state.record_cancel(arguments, result)
    elif tool_name == "get_agenda":
        state.record_agenda(result)
