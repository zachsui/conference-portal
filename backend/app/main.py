"""FastAPI application entry point for the conference portal backend."""
from __future__ import annotations

from typing import List, Literal, Optional

from dotenv import load_dotenv

# Load .env before anything that reads env vars (e.g. email service).
load_dotenv()

from fastapi import (  # noqa: E402
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from agent.orchestrator import run_chat  # noqa: E402
from agent.schemas import (  # noqa: E402
    ChatRequest,
    ChatResponse,
    TraceSummary,
)
from agent.traces import trace_store  # noqa: E402
from app.email import email_service  # noqa: E402
from app.models import (  # noqa: E402
    AgendaItem,
    Attendee,
    AttendeeCreate,
    CapacityInfo,
    LoginRequest,
    Registration,
    RegistrationCreate,
    Session,
)
from app.store import (  # noqa: E402
    ConflictError,
    DuplicateError,
    FullSessionError,
    InvalidInputError,
    NotFoundError,
    store,
)

app = FastAPI(
    title="Atlas Conference 2026 — Attendee Portal API",
    version="0.1.0",
    description=(
        "Backend for the Atlas Conference attendee portal. "
        "Phase 1: in-memory mock data, no persistence."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "conference-portal-api"}


@app.get("/tracks", tags=["meta"], response_model=List[str])
def list_tracks() -> List[str]:
    return store.list_tracks()


@app.get("/dates", tags=["meta"], response_model=List[str])
def list_dates() -> List[str]:
    return store.list_dates()


@app.get(
    "/sessions/search",
    tags=["sessions"],
    response_model=List[Session],
    summary="Search and filter sessions",
)
def search_sessions(
    topic: Optional[str] = Query(
        None, description="Substring match on the session topic."
    ),
    date: Optional[str] = Query(
        None, description="ISO date filter, e.g. 2026-06-09."
    ),
    time_of_day: Optional[Literal["morning", "afternoon", "evening"]] = Query(
        None
    ),
    level: Optional[Literal["beginner", "intermediate", "advanced"]] = Query(
        None
    ),
    track: Optional[str] = Query(
        None, description="Substring match on the track name."
    ),
    q: Optional[str] = Query(
        None,
        description=(
            "Full-text search across title, description, speaker, "
            "company, track, and topic."
        ),
    ),
) -> List[Session]:
    return store.list_sessions(
        topic=topic,
        date=date,
        time_of_day=time_of_day,
        level=level,
        track=track,
        q=q,
    )


@app.get(
    "/sessions/{session_id}",
    tags=["sessions"],
    response_model=Session,
    responses={404: {"description": "Session not found"}},
)
def get_session(session_id: str) -> Session:
    try:
        return store.get_session(session_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@app.get(
    "/sessions/{session_id}/capacity",
    tags=["sessions"],
    response_model=CapacityInfo,
    responses={404: {"description": "Session not found"}},
)
def get_session_capacity(session_id: str) -> CapacityInfo:
    try:
        return store.get_capacity(session_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@app.post(
    "/registrations",
    tags=["registrations"],
    response_model=Registration,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Session not found"},
        409: {"description": "Conflict: full session or overlapping schedule"},
    },
)
def create_registration(
    payload: RegistrationCreate, background: BackgroundTasks
) -> Registration:
    try:
        registration = store.create_registration(
            attendee_id=payload.attendee_id, session_id=payload.session_id
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc
    except FullSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "session_full", "message": str(exc)},
        ) from exc
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "schedule_conflict", "message": str(exc)},
        ) from exc

    try:
        attendee = store.get_attendee(registration.attendee_id)
        session_obj = store.get_session(registration.session_id)
        background.add_task(
            email_service.send_registration_confirmation,
            attendee,
            session_obj,
            registration,
        )
    except NotFoundError:
        pass

    return registration


@app.delete(
    "/registrations/{registration_id}",
    tags=["registrations"],
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def cancel_registration(
    registration_id: str, background: BackgroundTasks
) -> Response:
    try:
        cancelled = store.cancel_registration(registration_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc

    try:
        attendee = store.get_attendee(cancelled.attendee_id)
        session_obj = store.get_session(cancelled.session_id)
        background.add_task(
            email_service.send_registration_cancelled,
            attendee,
            session_obj,
            cancelled,
        )
    except NotFoundError:
        pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/attendees/{attendee_id}/agenda",
    tags=["attendees"],
    response_model=List[AgendaItem],
)
def get_agenda(attendee_id: str) -> List[AgendaItem]:
    return store.get_agenda(attendee_id)


@app.get("/attendees", tags=["attendees"], response_model=List[Attendee])
def list_attendees() -> List[Attendee]:
    return store.list_attendees()


@app.post(
    "/attendees",
    tags=["attendees"],
    response_model=Attendee,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid input"},
        409: {"description": "Email already registered"},
    },
)
def create_attendee(
    payload: AttendeeCreate, background: BackgroundTasks
) -> Attendee:
    try:
        attendee = store.create_attendee(
            email=payload.email,
            name=payload.name,
            company=payload.company,
            role=payload.role,
        )
    except InvalidInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_input", "message": str(exc)},
        ) from exc
    except DuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "email_taken", "message": str(exc)},
        ) from exc

    background.add_task(email_service.send_welcome, attendee)
    return attendee


@app.post(
    "/attendees/login",
    tags=["attendees"],
    response_model=Attendee,
    responses={
        400: {"description": "Invalid input"},
        404: {"description": "No account with that email"},
    },
)
def login_attendee(payload: LoginRequest) -> Attendee:
    try:
        return store.login_attendee(email=payload.email)
    except InvalidInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_input", "message": str(exc)},
        ) from exc
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


@app.get(
    "/attendees/{attendee_id}",
    tags=["attendees"],
    response_model=Attendee,
    responses={404: {"description": "Attendee not found"}},
)
def get_attendee(attendee_id: str) -> Attendee:
    try:
        return store.get_attendee(attendee_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc


# ─────────────── Agent (Gemini tool calling) ───────────────
@app.post(
    "/agent/chat",
    tags=["agent"],
    response_model=ChatResponse,
    summary="Chat with the AI assistant (Gemini tool calling).",
)
def agent_chat(payload: ChatRequest) -> ChatResponse:
    try:
        store.get_attendee(payload.attendee_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(exc)},
        ) from exc
    return run_chat(payload.attendee_id, payload.message)


@app.get(
    "/agent/traces",
    tags=["agent"],
    response_model=List[TraceSummary],
    summary="List recent assistant conversation traces (most recent first).",
)
def list_agent_traces() -> List[TraceSummary]:
    summaries: List[TraceSummary] = []
    for t in trace_store.list():
        summaries.append(
            TraceSummary(
                trace_id=t["trace_id"],
                attendee_id=t.get("attendee_id"),
                user_message=t["user_message"],
                final_answer=t["final_answer"],
                status=t["status"],
                tool_call_count=len(t.get("tool_calls", [])),
                policy_violation_count=len(t.get("policy_violations", [])),
                created_at=t.get("created_at", ""),
            )
        )
    return summaries


@app.get(
    "/agent/traces/{trace_id}",
    tags=["agent"],
    summary="Fetch a single assistant trace by ID.",
)
def get_agent_trace(trace_id: str) -> dict:
    trace = trace_store.get(trace_id)
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Trace '{trace_id}' not found"},
        )
    return trace
