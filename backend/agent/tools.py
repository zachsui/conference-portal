"""LLM-callable tools.

Each tool is a plain Python function that:
  - Accepts only JSON-serializable kwargs.
  - Returns a JSON-serializable dict.
  - Catches all expected business errors and surfaces them as
    {"ok": False, "error": "...", "message": "..."} so the model can react.

These tools wrap the in-memory store directly. They never expose
internal artifacts (e.g. email sending) to the caller — emails are still
fired in the background, but the tool result only reports the business
outcome (registration created, capacity, etc.).
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, Optional

from app.email import email_service
from app.models import Session
from app.store import (
    ConflictError,
    FullSessionError,
    NotFoundError,
    store,
)

logger = logging.getLogger("conference_portal.agent.tools")

MAX_SEARCH_RESULTS = 20


def _session_summary(s: Session) -> dict:
    return {
        "session_id": s.session_id,
        "title": s.title,
        "track": s.track,
        "topic": s.topic,
        "date": s.date,
        "start_time": s.start_time,
        "end_time": s.end_time,
        "time_of_day": s.time_of_day,
        "room": s.room,
        "speaker": s.speaker,
        "company": s.company,
        "level": s.level,
        "capacity": s.capacity,
        "registered_count": s.registered_count,
    }


def _send_async(fn: Callable, *args: Any) -> None:
    """Fire-and-forget email send so the agent loop is never blocked."""

    def _run() -> None:
        try:
            fn(*args)
        except Exception as exc:  # noqa: BLE001 — keep agent loop healthy
            logger.warning("Background email send failed: %s", exc)

    threading.Thread(target=_run, daemon=True).start()


# ─────────────── Tools ───────────────
def search_sessions(
    *,
    topic: Optional[str] = None,
    date: Optional[str] = None,
    time_of_day: Optional[str] = None,
    level: Optional[str] = None,
    track: Optional[str] = None,
    q: Optional[str] = None,
) -> dict:
    sessions = store.list_sessions(
        topic=topic,
        date=date,
        time_of_day=time_of_day,
        level=level,
        track=track,
        q=q,
    )
    truncated = len(sessions) > MAX_SEARCH_RESULTS
    return {
        "ok": True,
        "count": len(sessions),
        "truncated": truncated,
        "sessions": [_session_summary(s) for s in sessions[:MAX_SEARCH_RESULTS]],
    }


def get_session_detail(*, session_id: str) -> dict:
    try:
        s = store.get_session(session_id)
    except NotFoundError as exc:
        return {"ok": False, "error": "not_found", "message": str(exc)}
    return {"ok": True, "session": _session_summary(s)}


def check_capacity(*, session_id: str) -> dict:
    try:
        info = store.get_capacity(session_id)
    except NotFoundError as exc:
        return {"ok": False, "error": "not_found", "message": str(exc)}
    return {"ok": True, **info.model_dump()}


def register_session(*, attendee_id: str, session_id: str) -> dict:
    try:
        registration = store.create_registration(attendee_id, session_id)
    except NotFoundError as exc:
        return {"ok": False, "error": "not_found", "message": str(exc)}
    except FullSessionError as exc:
        return {"ok": False, "error": "session_full", "message": str(exc)}
    except ConflictError as exc:
        return {
            "ok": False,
            "error": "schedule_conflict",
            "message": str(exc),
        }

    try:
        attendee = store.get_attendee(attendee_id)
        session_obj = store.get_session(session_id)
        _send_async(
            email_service.send_registration_confirmation,
            attendee,
            session_obj,
            registration,
        )
    except NotFoundError:
        pass

    return {"ok": True, "registration": registration.model_dump()}


def cancel_registration(*, registration_id: str) -> dict:
    try:
        cancelled = store.cancel_registration(registration_id)
    except NotFoundError as exc:
        return {"ok": False, "error": "not_found", "message": str(exc)}

    try:
        attendee = store.get_attendee(cancelled.attendee_id)
        session_obj = store.get_session(cancelled.session_id)
        _send_async(
            email_service.send_registration_cancelled,
            attendee,
            session_obj,
            cancelled,
        )
    except NotFoundError:
        pass

    return {"ok": True, "cancelled": cancelled.model_dump()}


def get_agenda(*, attendee_id: str) -> dict:
    items = store.get_agenda(attendee_id)
    return {
        "ok": True,
        "count": len(items),
        "items": [
            {
                "registration_id": item.registration_id,
                "session": _session_summary(item.session),
            }
            for item in items
        ],
    }


TOOL_FUNCTIONS: Dict[str, Callable[..., dict]] = {
    "search_sessions": search_sessions,
    "get_session_detail": get_session_detail,
    "check_capacity": check_capacity,
    "register_session": register_session,
    "cancel_registration": cancel_registration,
    "get_agenda": get_agenda,
}
