"""Optional Opik (Comet) LLM observability for the conference agent.

Enable by setting OPIK_API_KEY and OPIK_WORKSPACE in backend/.env.
If unset, every function here is a no-op and the agent behaves unchanged.

Docs: https://www.comet.com/docs/opik/
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, TypeVar

logger = logging.getLogger("conference_portal.opik")

_configured = False

F = TypeVar("F", bound=Callable[..., Any])


def is_enabled() -> bool:
    return bool(os.getenv("OPIK_API_KEY", "").strip())


def project_name() -> str:
    return os.getenv("OPIK_PROJECT_NAME", "conference-agent-portal").strip()


def ensure_configured() -> None:
    """Idempotent — safe to call from multiple import sites."""
    global _configured
    if not is_enabled():
        return
    if _configured:
        return
    import opik

    ws = (os.getenv("OPIK_WORKSPACE") or "").strip()
    if not ws:
        logger.warning("OPIK_API_KEY is set but OPIK_WORKSPACE is empty — Opik disabled")
        return

    opik.configure(
        api_key=os.getenv("OPIK_API_KEY", "").strip(),
        workspace=ws,
        url_override=(os.getenv("OPIK_URL_OVERRIDE") or "").strip() or None,
        project_name=project_name(),
    )
    _configured = True


def flush() -> None:
    if not is_enabled():
        return
    try:
        import opik

        opik.flush_tracker(timeout=30)
    except Exception:  # noqa: BLE001
        logger.debug("opik flush_tracker failed", exc_info=True)


def annotate_chat_trace(response: Any, attendee_id: str) -> None:
    """Enrich the current root trace with portal-specific metadata.

    Must be called while still inside the @opik.track span for run_chat.
    """
    if not is_enabled():
        return
    try:
        from opik import opik_context

        pa_b = getattr(response, "pending_action_before", None)
        pa_a = getattr(response, "pending_action_after", None)
        violations = getattr(response, "policy_violations", []) or []

        opik_context.update_current_trace(
            metadata={
                "portal_trace_id": response.trace_id,
                "attendee_id": attendee_id,
                "status": response.status,
                "confirmation_detected": response.confirmation_detected,
                "tool_sequence": [t.tool_name for t in response.tool_calls],
                "policy_violation_count": len(violations),
                "policy_rules": [v.rule for v in violations],
                "pending_session_id_before": getattr(pa_b, "session_id", None),
                "pending_session_id_after": getattr(pa_a, "session_id", None),
            },
            output={
                "status": response.status,
                "final_answer_preview": (response.final_answer or "")[:800],
            },
        )
    except Exception:  # noqa: BLE001
        logger.debug("opik annotate_chat_trace failed", exc_info=True)


def run_chat_tracked(impl: Callable[..., Any], attendee_id: str, message: str) -> Any:
    """Wrap `_run_chat_impl` in a root Opik trace."""
    ensure_configured()
    import opik

    tracked = opik.track(
        name="conference_agent_chat",
        type="general",
        project_name=project_name(),
        tags=["conference-portal", "agent", "run_chat"],
    )(impl)
    try:
        return tracked(attendee_id, message)
    finally:
        flush()


def tool_track(tool_name: str) -> Callable[[F], F]:
    """Decorator for agent tool functions (nested spans under run_chat)."""

    def decorator(fn: F) -> F:
        if not is_enabled():
            return fn
        import opik

        ensure_configured()
        return opik.track(
            name=tool_name,
            type="tool",
            project_name=project_name(),
            tags=["conference-portal", "agent-tool"],
        )(fn)

    return decorator
