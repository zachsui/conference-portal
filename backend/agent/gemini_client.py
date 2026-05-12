"""Gemini client + function declarations + system prompt."""
from __future__ import annotations

import os
from typing import List

from google import genai
from google.genai import types

# Default to gemini-3.1-flash-lite — it has the highest free-tier daily
# quota of the lite models and is plenty for tool-calling. Override with
# GEMINI_MODEL in backend/.env (e.g. "gemini-2.5-flash" for stronger reasoning,
# or "gemini-2.5-flash-lite" if you want to compare).
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()


class GeminiNotConfiguredError(RuntimeError):
    """Raised when GEMINI_API_KEY is missing."""


_cached_genai_client: genai.Client | None = None


def get_client() -> genai.Client:
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not set. Add it to backend/.env to enable "
            "the AI assistant. Get a key at https://aistudio.google.com/apikey."
        )
    global _cached_genai_client
    if _cached_genai_client is not None:
        return _cached_genai_client

    client = genai.Client(api_key=api_key)
    try:
        from agent import opik_io

        if opik_io.is_enabled():
            opik_io.ensure_configured()
            from opik.integrations.genai.opik_tracker import track_genai

            client = track_genai(client, project_name=opik_io.project_name())
    except Exception:  # noqa: BLE001 — never break chat if Opik fails
        pass
    _cached_genai_client = client
    return client


# ─────────────── Function declarations (LLM-visible schemas) ───────────────
FUNCTION_DECLARATIONS: List[types.FunctionDeclaration] = [
    types.FunctionDeclaration(
        name="search_sessions",
        description=(
            "Search the conference session catalog with optional filters. "
            "Use this to find candidate sessions by topic, date, time of "
            "day, level, track, or free-text query. Returns at most 20 "
            "matches; refine your filters if 'truncated' is true."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "topic": types.Schema(
                    type=types.Type.STRING,
                    description="Substring match on the session topic.",
                ),
                "date": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "ISO date YYYY-MM-DD. Conference runs "
                        "2026-06-09 → 2026-06-11."
                    ),
                ),
                "time_of_day": types.Schema(
                    type=types.Type.STRING,
                    enum=["morning", "afternoon", "evening"],
                ),
                "level": types.Schema(
                    type=types.Type.STRING,
                    enum=["beginner", "intermediate", "advanced"],
                ),
                "track": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "Substring match on track name. Tracks include: "
                        "Payments & Fintech, Stablecoins & Global Money "
                        "Movement, AI Agents & Automation, AI Safety & "
                        "Agent Evaluation, Cybersecurity & Identity, "
                        "Cloud Infrastructure, Data Engineering & "
                        "Analytics, Developer Platforms, Product "
                        "Leadership, Compliance & Risk."
                    ),
                ),
                "q": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "Full-text search across title, description, "
                        "speaker, company, track, and topic."
                    ),
                ),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_session_detail",
        description="Get the full details for one session by ID.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "session_id": types.Schema(
                    type=types.Type.STRING,
                    description="A session_id from search results, e.g. S017.",
                ),
            },
            required=["session_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="check_capacity",
        description=(
            "Check current capacity for a session: capacity, "
            "registered_count, seats_remaining, and status "
            "(available | almost_full | full). MUST be called for the "
            "exact session_id immediately before register_session."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "session_id": types.Schema(type=types.Type.STRING),
            },
            required=["session_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="register_session",
        description=(
            "Register the current attendee for a session. Returns "
            "{ok: true, registration: {...}} on success or "
            "{ok: false, error: 'session_full' | 'schedule_conflict' | "
            "'not_found', message: '...'} on failure. "
            "ONLY call when (a) you know the exact session_id from a "
            "previous tool call, AND (b) you have just called "
            "check_capacity on that session_id with status != 'full', "
            "AND (c) the user has unambiguously chosen this session."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "attendee_id": types.Schema(
                    type=types.Type.STRING,
                    description="The current attendee's ID.",
                ),
                "session_id": types.Schema(type=types.Type.STRING),
            },
            required=["attendee_id", "session_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="cancel_registration",
        description=(
            "Cancel a registration by its registration_id "
            "(format: REG-XXXXXXXXXX). If the user mentions only a "
            "session name/title, call get_agenda first to find the "
            "matching registration_id. NEVER invent IDs."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "registration_id": types.Schema(
                    type=types.Type.STRING,
                    description="A registration_id like REG-AB12CD34EF.",
                ),
            },
            required=["registration_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_agenda",
        description=(
            "Get all sessions the current attendee is already registered "
            "for, sorted by date and start time. Includes registration_id "
            "for each item — use these for cancel_registration."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "attendee_id": types.Schema(type=types.Type.STRING),
            },
            required=["attendee_id"],
        ),
    ),
]

TOOLS: List[types.Tool] = [
    types.Tool(function_declarations=FUNCTION_DECLARATIONS)
]


SYSTEM_INSTRUCTION = """\
You are the Atlas Conference 2026 attendee assistant.

Conference: June 9–11, 2026 at Moscone West, San Francisco. There are
50 sessions across 10 tracks. You help attendees discover sessions,
check capacity, register, cancel, and view their personal agenda.

Tools:
  - search_sessions    – filter the catalog
  - get_session_detail – one session by ID
  - check_capacity     – seats remaining (REQUIRED before register_session)
  - register_session   – create a registration
  - cancel_registration – cancel by registration_id
  - get_agenda         – list the user's registered sessions

Hard rules (the orchestrator will reject calls that violate these):

1. To register from a topic / title / date / time description, follow this
   order strictly:
       search_sessions  →  check_capacity  →  register_session
2. Never call register_session unless:
     (a) the session_id was returned by a previous search/detail/agenda call,
     (b) check_capacity was just called for that session_id and returned
         status != "full".
3. If search_sessions returns more than one plausible match, present the
   candidates (session_id, title, date, time, room, speaker) and ASK the
   user to pick one. Do NOT register on the user's behalf.
4. If check_capacity returns status="full" or seats_remaining=0, do not
   call register_session. Suggest alternatives instead.
5. If register_session returns ok=false with error="schedule_conflict",
   surface the message verbatim (it tells the user which existing
   session conflicts) and offer to cancel the conflicting session.
6. NEVER claim a registration succeeded unless register_session
   returned ok=true. If a tool returned ok=false, report the failure.
7. To cancel a registration, you need a registration_id (REG-XXXXXXXXXX).
   If the user gives only a session name, call get_agenda first to look
   it up. Never invent or guess registration IDs.
8. Be concise. Always include session_id, title, date, time range, and
   room when surfacing sessions. Do not invent details (speakers,
   capacities, etc.). If something isn't in tool results, say so.

For register_session and get_agenda, always pass the current attendee_id
provided in the system context.
"""
