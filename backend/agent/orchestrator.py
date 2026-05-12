"""Agent orchestration loop.

Talks to Gemini, executes tool calls (with policy enforcement),
records a full trace, and returns a structured ChatResponse.

Adds a deterministic confirmation flow on top of the LLM:
  1. Before calling Gemini, check whether the user message is a pure
     "yes"/"no" reply to a previously-proposed action.
  2. If yes  → run check_capacity → register_session ourselves and
     return without calling Gemini.
  3. If no   → clear pending and acknowledge.
  4. After the LLM loop, if the model produced a single likely candidate
     and proposed registering, store a pending_action so the next "yes"
     resolves correctly.
"""
from __future__ import annotations

import logging
import time
from typing import Any, List, Optional, Tuple

from google.genai import types

from .conversation import (
    ConversationStateStore,
    conversation_store,
    is_cancellation,
    is_confirmation,
    make_pending_register,
)
from .gemini_client import (
    GEMINI_MODEL,
    SYSTEM_INSTRUCTION,
    TOOLS,
    GeminiNotConfiguredError,
    get_client,
)
from .schemas import ChatResponse, PendingAction, PolicyViolation, ToolCallTrace
from .tools import TOOL_FUNCTIONS, check_capacity, register_session
from .traces import trace_store
from .validators import (
    PolicyState,
    bind_attendee_id,
    update_state_after_tool,
    validate_tool_call,
)

logger = logging.getLogger("conference_portal.agent")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(levelname)s:     [agent] %(message)s")
    )
    logger.addHandler(_handler)
    logger.propagate = False


MAX_ROUNDS = 6  # Up to N model round-trips per chat turn.

# Hints in the model's final answer that suggest a pending registration.
_PROPOSAL_HINTS = (
    "would you like to register",
    "would you like me to register",
    "do you want to register",
    "do you want me to register",
    "want me to register",
    "shall i register",
    "shall i sign you up",
    "should i register",
    "should i sign you up",
    "should i go ahead",
    "shall i go ahead",
    "ready to register",
    "register you for",
    "sign you up",
    "let me know if you'd like",
    "let me know if you want",
    "confirm if you'd like",
    "confirm if you want",
)


# ─────────────── Helpers ───────────────
def _normalize_id_args(args: dict) -> dict:
    """Canonicalize ID-shaped args before validator + tool dispatch.

    Sessions are stored as 'S###' (uppercase) and registrations as
    'REG-XXXX' (uppercase). LLMs occasionally echo them in lowercase
    or with surrounding whitespace; normalize so downstream lookups
    and policy state comparisons all use the canonical form.
    """
    if not isinstance(args, dict):
        return args
    normalized = dict(args)
    sid = normalized.get("session_id")
    if isinstance(sid, str):
        normalized["session_id"] = sid.strip().upper()
    rid = normalized.get("registration_id")
    if isinstance(rid, str):
        normalized["registration_id"] = rid.strip().upper()
    return normalized


def _to_jsonable(value: Any) -> Any:
    """Coerce google-genai/proto values into plain JSON-friendly Python."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    try:
        return {k: _to_jsonable(v) for k, v in dict(value).items()}
    except Exception:  # noqa: BLE001
        try:
            return [_to_jsonable(v) for v in list(value)]
        except Exception:  # noqa: BLE001
            return str(value)


def _safe_text(response: Any) -> str:
    try:
        return response.text or ""
    except Exception:  # noqa: BLE001
        return ""


def _classify_status(
    final_answer: str,
    tool_traces: List[ToolCallTrace],
    violations: List[PolicyViolation],
    pending_after: Optional[PendingAction],
) -> str:
    """Heuristic post-classification of the final status."""
    successful_register = any(
        t.tool_name == "register_session"
        and t.success
        and isinstance(t.result, dict)
        and t.result.get("ok")
        for t in tool_traces
    )
    successful_cancel = any(
        t.tool_name == "cancel_registration"
        and t.success
        and isinstance(t.result, dict)
        and t.result.get("ok")
        for t in tool_traces
    )
    if successful_register or successful_cancel:
        return "completed"
    if pending_after is not None:
        return "clarification_needed"
    text = (final_answer or "").strip().lower()
    if text.endswith("?") or any(
        kw in text
        for kw in (
            "which one",
            "which would",
            "could you specify",
            "could you clarify",
            "please choose",
            "please pick",
            "which session",
        )
    ):
        return "clarification_needed"
    return "completed"


def _save_and_return(
    response: ChatResponse, attendee_id: str
) -> ChatResponse:
    """Persist the trace (with pending fields) and return the response."""
    trace_store.save(
        response.trace_id,
        response.model_dump() | {"attendee_id": attendee_id},
    )
    logger.info(
        "[%s] done status=%s tools=%d violations=%d "
        "confirmation=%s pending_before=%s pending_after=%s",
        response.trace_id,
        response.status,
        len(response.tool_calls),
        len(response.policy_violations),
        response.confirmation_detected,
        response.pending_action_before.session_id
        if response.pending_action_before
        else None,
        response.pending_action_after.session_id
        if response.pending_action_after
        else None,
    )
    from agent import opik_io

    opik_io.annotate_chat_trace(response, attendee_id)
    return response


# ─────────────── Pending-action detection ───────────────
def _detect_pending_register(
    attendee_id: str,
    tool_traces: List[ToolCallTrace],
    final_answer: str,
) -> Optional[PendingAction]:
    """If the model proposed registering for one likely session, return it."""
    # If a registration already succeeded this turn, no pending needed.
    successful_register = any(
        t.tool_name == "register_session"
        and t.success
        and isinstance(t.result, dict)
        and t.result.get("ok")
        for t in tool_traces
    )
    if successful_register:
        return None

    # If the model already attempted register and was blocked, don't propose
    # the same thing again — it'd just loop.
    attempted_register = any(
        t.tool_name == "register_session" for t in tool_traces
    )
    if attempted_register:
        return None

    text = (final_answer or "").lower()
    proposal_signal = any(hint in text for hint in _PROPOSAL_HINTS)

    # Find the most recent single-match candidate from search/detail.
    candidate_id: Optional[str] = None
    candidate_title: Optional[str] = None
    for t in reversed(tool_traces):
        if not t.success or not isinstance(t.result, dict):
            continue
        if t.tool_name == "search_sessions":
            sessions = t.result.get("sessions") or []
            if len(sessions) == 1:
                candidate_id = sessions[0].get("session_id")
                candidate_title = sessions[0].get("title")
                break
            # Multiple results → never auto-pick; user must clarify.
            if len(sessions) > 1:
                return None
        elif t.tool_name == "get_session_detail":
            session = t.result.get("session") or {}
            if session.get("session_id"):
                candidate_id = session.get("session_id")
                candidate_title = session.get("title")
                break
        elif t.tool_name == "check_capacity":
            sid = t.arguments.get("session_id") if isinstance(t.arguments, dict) else None
            if sid and not candidate_id:
                candidate_id = sid

    if not candidate_id:
        return None
    # We only set pending when the model's wording suggests confirmation.
    # Otherwise it might just be answering an info question.
    if not proposal_signal:
        return None

    return make_pending_register(
        attendee_id=attendee_id,
        session_id=candidate_id,
        session_title=candidate_title,
    )


# ─────────────── Confirmation short-circuit ───────────────
def _execute_pending_register(
    *,
    trace_id: str,
    attendee_id: str,
    user_message: str,
    pending: PendingAction,
) -> ChatResponse:
    """Deterministically run check_capacity → register_session. No LLM call."""
    tool_traces: List[ToolCallTrace] = []
    step = 0

    # Step 1 — check_capacity
    step += 1
    start = time.perf_counter()
    cap_result = check_capacity(session_id=pending.session_id)
    cap_latency = int((time.perf_counter() - start) * 1000)
    tool_traces.append(
        ToolCallTrace(
            step_number=step,
            tool_name="check_capacity",
            arguments={"session_id": pending.session_id},
            result=cap_result,
            success=bool(cap_result.get("ok", False)),
            latency_ms=cap_latency,
        )
    )

    label = pending.session_title or pending.session_id

    if not cap_result.get("ok"):
        # Session vanished or backend error — clear and explain.
        conversation_store.clear(attendee_id)
        return ChatResponse(
            trace_id=trace_id,
            user_message=user_message,
            tool_calls=tool_traces,
            final_answer=(
                f"I couldn't look up '{label}' to confirm: "
                f"{cap_result.get('message', 'unknown error')}. "
                "Please try searching again."
            ),
            status="failed",
            policy_violations=[],
            pending_action_before=pending,
            pending_action_after=None,
            confirmation_detected=True,
        )

    is_full = (
        cap_result.get("status") == "full"
        or int(cap_result.get("seats_remaining", 0) or 0) <= 0
    )
    if is_full:
        conversation_store.clear(attendee_id)
        return ChatResponse(
            trace_id=trace_id,
            user_message=user_message,
            tool_calls=tool_traces,
            final_answer=(
                f"Sorry — '{label}' is now full, so I didn't register you. "
                "Want me to look for similar sessions?"
            ),
            status="completed",
            policy_violations=[],
            pending_action_before=pending,
            pending_action_after=None,
            confirmation_detected=True,
        )

    # Step 2 — register_session
    step += 1
    start = time.perf_counter()
    reg_result = register_session(
        attendee_id=attendee_id, session_id=pending.session_id
    )
    reg_latency = int((time.perf_counter() - start) * 1000)
    tool_traces.append(
        ToolCallTrace(
            step_number=step,
            tool_name="register_session",
            arguments={
                "attendee_id": attendee_id,
                "session_id": pending.session_id,
            },
            result=reg_result,
            success=bool(reg_result.get("ok", False)),
            latency_ms=reg_latency,
        )
    )

    if not reg_result.get("ok"):
        conversation_store.clear(attendee_id)
        err = reg_result.get("error")
        msg = reg_result.get("message", "Registration failed.")
        if err == "schedule_conflict":
            answer = (
                f"I couldn't register you for '{label}' — schedule conflict: "
                f"{msg}"
            )
        elif err == "session_full":
            answer = (
                f"Just missed it — '{label}' filled up before I could "
                "register you."
            )
        elif err == "not_found":
            answer = f"I couldn't find '{label}' anymore: {msg}"
        else:
            answer = f"Registration failed for '{label}': {msg}"
        return ChatResponse(
            trace_id=trace_id,
            user_message=user_message,
            tool_calls=tool_traces,
            final_answer=answer,
            status="failed" if err != "session_full" else "completed",
            policy_violations=[],
            pending_action_before=pending,
            pending_action_after=None,
            confirmation_detected=True,
        )

    # Success — clear pending, surface registration_id.
    conversation_store.clear(attendee_id)
    reg_obj = reg_result.get("registration") or {}
    reg_id = reg_obj.get("registration_id", "")
    return ChatResponse(
        trace_id=trace_id,
        user_message=user_message,
        tool_calls=tool_traces,
        final_answer=(
            f"You're registered for '{label}'. "
            f"Confirmation ID: {reg_id}."
        ),
        status="completed",
        policy_violations=[],
        pending_action_before=pending,
        pending_action_after=None,
        confirmation_detected=True,
    )


def _try_short_circuit(
    *, trace_id: str, attendee_id: str, message: str
) -> Tuple[Optional[ChatResponse], Optional[PendingAction]]:
    """Handle deterministic yes/no replies before we ever call Gemini.

    Returns (response, pending_before).
      - response is non-None iff we handled the turn entirely.
      - pending_before is whatever pending state existed coming into the
        turn (used for tracing even on the LLM path).
    """
    # Peek raw first so we can distinguish "expired" from "never had one".
    raw = conversation_store.peek_including_expired(attendee_id)
    expired = raw is not None and ConversationStateStore.is_expired(raw)
    pending_before: Optional[PendingAction] = None if expired else raw

    confirmation = is_confirmation(message)
    cancellation = is_cancellation(message)

    if not (confirmation or cancellation):
        # If pending expired, clean it up silently — the LLM turn doesn't
        # need to know about it.
        if expired:
            conversation_store.clear(attendee_id)
        return None, pending_before

    # User said "yes" / "no" — handle deterministically.
    if cancellation:
        if pending_before is None:
            if expired:
                # Expired and the user said no — just clear and acknowledge.
                conversation_store.clear(attendee_id)
            return (
                ChatResponse(
                    trace_id=trace_id,
                    user_message=message,
                    tool_calls=[],
                    final_answer=(
                        "OK — nothing to cancel right now. Let me know "
                        "what you'd like to do."
                    ),
                    status="completed",
                    policy_violations=[],
                    pending_action_before=None,
                    pending_action_after=None,
                    confirmation_detected=True,
                ),
                None,
            )
        label = pending_before.session_title or pending_before.session_id
        conversation_store.clear(attendee_id)
        return (
            ChatResponse(
                trace_id=trace_id,
                user_message=message,
                tool_calls=[],
                final_answer=(
                    f"Got it — I won't register you for '{label}'. "
                    "Anything else I can help with?"
                ),
                status="completed",
                policy_violations=[],
                pending_action_before=pending_before,
                pending_action_after=None,
                confirmation_detected=True,
            ),
            pending_before,
        )

    # confirmation == True
    if expired and raw is not None:
        # Surface the expired suggestion so the user knows what was lost.
        conversation_store.clear(attendee_id)
        label = raw.session_title or raw.session_id
        return (
            ChatResponse(
                trace_id=trace_id,
                user_message=message,
                tool_calls=[],
                final_answer=(
                    f"My pending suggestion for '{label}' expired "
                    f"(it was older than {raw.expires_after_minutes} "
                    "minutes). Could you repeat what you'd like me to "
                    "register you for?"
                ),
                status="clarification_needed",
                policy_violations=[],
                pending_action_before=raw,
                pending_action_after=None,
                confirmation_detected=True,
            ),
            None,
        )

    if pending_before is None:
        return (
            ChatResponse(
                trace_id=trace_id,
                user_message=message,
                tool_calls=[],
                final_answer=(
                    "I don't have a pending action to confirm. What would "
                    "you like me to do? You can ask me to search for "
                    "sessions or register for a specific one."
                ),
                status="clarification_needed",
                policy_violations=[],
                pending_action_before=None,
                pending_action_after=None,
                confirmation_detected=True,
            ),
            None,
        )

    response = _execute_pending_register(
        trace_id=trace_id,
        attendee_id=attendee_id,
        user_message=message,
        pending=pending_before,
    )
    return response, pending_before


# ─────────────── Main entry ───────────────
def _run_chat_impl(attendee_id: str, message: str) -> ChatResponse:
    trace_id = trace_store.new_trace_id()
    logger.info("[%s] user=%s msg=%r", trace_id, attendee_id, message[:200])

    # 1) Pre-LLM short-circuit: handle "yes"/"no" deterministically.
    short, pending_before = _try_short_circuit(
        trace_id=trace_id, attendee_id=attendee_id, message=message
    )
    if short is not None:
        return _save_and_return(short, attendee_id)

    # 2) Otherwise, run the normal Gemini loop.
    state = PolicyState(attendee_id)
    tool_traces: List[ToolCallTrace] = []
    violations: List[PolicyViolation] = []
    final_answer = ""
    status = "completed"
    step_counter = 0

    try:
        client = get_client()
    except GeminiNotConfiguredError as exc:
        response = ChatResponse(
            trace_id=trace_id,
            user_message=message,
            tool_calls=[],
            final_answer=str(exc),
            status="failed",
            policy_violations=[],
            pending_action_before=pending_before,
            pending_action_after=pending_before,
            confirmation_detected=False,
        )
        return _save_and_return(response, attendee_id)

    # Surface any pending action to the model so it stays consistent.
    pending_note = ""
    if pending_before is not None:
        pending_note = (
            "\n\nPending proposal from the previous turn (still open): "
            f"register_session for session_id={pending_before.session_id} "
            f"(title: {pending_before.session_title!r}). If the user "
            "declines or asks something different, drop it. If the user "
            "confirms, follow the standard search→capacity→register flow."
        )

    contents: List[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)],
        )
    ]
    config = types.GenerateContentConfig(
        system_instruction=(
            SYSTEM_INSTRUCTION
            + f"\n\nThe current attendee_id is: {attendee_id}\n"
            + pending_note
        ),
        tools=TOOLS,
        temperature=0.2,
    )

    try:
        for round_num in range(MAX_ROUNDS):
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            function_calls = list(response.function_calls or [])
            logger.info(
                "[%s] round=%d function_calls=%d",
                trace_id,
                round_num + 1,
                len(function_calls),
            )

            if not function_calls:
                final_answer = _safe_text(response).strip()
                if not final_answer:
                    final_answer = (
                        "I wasn't able to produce a response — please try "
                        "rephrasing your request."
                    )
                break

            if response.candidates and response.candidates[0].content:
                contents.append(response.candidates[0].content)

            tool_response_parts: List[types.Part] = []
            for fc in function_calls:
                step_counter += 1
                tool_name = fc.name or ""
                args = _to_jsonable(fc.args or {}) or {}
                if not isinstance(args, dict):
                    args = {}
                args = bind_attendee_id(tool_name, args, attendee_id)
                args = _normalize_id_args(args)

                logger.info(
                    "[%s] step=%d tool=%s args=%s",
                    trace_id,
                    step_counter,
                    tool_name,
                    args,
                )

                violation = validate_tool_call(tool_name, args, state)
                if violation:
                    violations.append(violation)
                    rejected = {
                        "ok": False,
                        "error": "policy_violation",
                        "rule": violation.rule,
                        "message": violation.detail,
                    }
                    tool_traces.append(
                        ToolCallTrace(
                            step_number=step_counter,
                            tool_name=tool_name,
                            arguments=args,
                            result=rejected,
                            success=False,
                            latency_ms=0,
                            error=violation.rule,
                        )
                    )
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=tool_name, response=rejected
                        )
                    )
                    continue

                func = TOOL_FUNCTIONS.get(tool_name)
                if func is None:
                    err = f"Unknown tool: {tool_name}"
                    rejected = {"ok": False, "error": "unknown_tool", "message": err}
                    tool_traces.append(
                        ToolCallTrace(
                            step_number=step_counter,
                            tool_name=tool_name,
                            arguments=args,
                            result=rejected,
                            success=False,
                            latency_ms=0,
                            error=err,
                        )
                    )
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=tool_name, response=rejected
                        )
                    )
                    continue

                start = time.perf_counter()
                error_msg = None
                try:
                    result = func(**args)
                    success = (
                        bool(result.get("ok", True))
                        if isinstance(result, dict)
                        else True
                    )
                except TypeError as exc:
                    result = {
                        "ok": False,
                        "error": "bad_arguments",
                        "message": f"Tool argument error: {exc}",
                    }
                    success = False
                    error_msg = str(exc)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Tool %s raised", tool_name)
                    result = {
                        "ok": False,
                        "error": "tool_exception",
                        "message": str(exc),
                    }
                    success = False
                    error_msg = str(exc)
                latency_ms = int((time.perf_counter() - start) * 1000)

                update_state_after_tool(tool_name, args, result, state)

                tool_traces.append(
                    ToolCallTrace(
                        step_number=step_counter,
                        tool_name=tool_name,
                        arguments=args,
                        result=result,
                        success=success,
                        latency_ms=latency_ms,
                        error=error_msg,
                    )
                )
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name, response=result
                    )
                )

            contents.append(
                types.Content(role="user", parts=tool_response_parts)
            )
        else:
            status = "failed"
            final_answer = (
                "I had to stop after several steps without reaching a clear "
                "answer. Could you rephrase or narrow the request?"
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[%s] agent error: %s", trace_id, exc)
        status = "failed"
        msg_lower = str(exc).lower()
        if "429" in msg_lower or "resource_exhausted" in msg_lower or "rate" in msg_lower:
            final_answer = (
                "Gemini rate limit reached. Please wait a moment and try "
                "again, or set GEMINI_MODEL to a model with higher quota."
            )
        else:
            final_answer = (
                "The assistant encountered an error talking to Gemini. "
                f"({type(exc).__name__})"
            )

    # 3) Update pending state from the LLM result.
    pending_after: Optional[PendingAction] = None
    if status != "failed":
        # Did the model successfully register? If so, clear any pending.
        successful_register = any(
            t.tool_name == "register_session"
            and t.success
            and isinstance(t.result, dict)
            and t.result.get("ok")
            for t in tool_traces
        )
        if successful_register:
            conversation_store.clear(attendee_id)
            pending_after = None
        else:
            new_pending = _detect_pending_register(
                attendee_id=attendee_id,
                tool_traces=tool_traces,
                final_answer=final_answer,
            )
            if new_pending is not None:
                conversation_store.set(attendee_id, new_pending)
                pending_after = new_pending
            else:
                # Keep any prior pending alive in store; but for THIS
                # response, surface what's currently stored (may be the old
                # one). If the LLM completely changed topic without a new
                # pending, we leave the old one untouched so user can still
                # confirm later (within TTL).
                pending_after = conversation_store.get(attendee_id)

    if status != "failed":
        status = _classify_status(
            final_answer, tool_traces, violations, pending_after
        )

    chat_response = ChatResponse(
        trace_id=trace_id,
        user_message=message,
        tool_calls=tool_traces,
        final_answer=final_answer,
        status=status,
        policy_violations=violations,
        pending_action_before=pending_before,
        pending_action_after=pending_after,
        confirmation_detected=False,
    )
    return _save_and_return(chat_response, attendee_id)


def run_chat(attendee_id: str, message: str) -> ChatResponse:
    """Public entry — wraps `_run_chat_impl` with optional Opik tracing."""
    from agent import opik_io

    if not opik_io.is_enabled():
        return _run_chat_impl(attendee_id, message)
    return opik_io.run_chat_tracked(_run_chat_impl, attendee_id, message)
