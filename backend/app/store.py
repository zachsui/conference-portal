"""In-memory data store and business logic for the conference portal.

This is a phase-1 mock store: data is held in process memory and is
reset on every server start. It is intentionally simple but enforces
the business rules required by the API.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.data.sessions import build_sessions
from app.models import (
    AgendaItem,
    Attendee,
    CapacityInfo,
    Registration,
    Session,
)


class ConflictError(Exception):
    """Raised when a registration conflicts with an existing one."""


class FullSessionError(Exception):
    """Raised when a session has no remaining capacity."""


class NotFoundError(Exception):
    """Raised when a referenced entity does not exist."""


class DuplicateError(Exception):
    """Raised when an entity already exists (e.g. duplicate email)."""


class InvalidInputError(Exception):
    """Raised for semantically invalid input (e.g. malformed email)."""


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_session_id(session_id: Optional[str]) -> str:
    if not session_id:
        return ""
    return session_id.strip().upper()


def _normalize_registration_id(registration_id: Optional[str]) -> str:
    if not registration_id:
        return ""
    return registration_id.strip().upper()


def _is_valid_email(email: str) -> bool:
    if "@" not in email:
        return False
    local, _, domain = email.partition("@")
    if not local or not domain or "." not in domain:
        return False
    return True


def _capacity_status(capacity: int, registered: int) -> str:
    if registered >= capacity:
        return "full"
    if registered / capacity >= 0.85:
        return "almost_full"
    return "available"


def _times_overlap(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    """Half-open interval overlap on HH:MM strings."""
    return a_start < b_end and b_start < a_end


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, Session] = {
            s.session_id: s for s in build_sessions()
        }
        self._registrations: Dict[str, Registration] = {}
        self._attendees: Dict[str, Attendee] = {}
        self._attendee_seq = 0
        self._seed_attendees()

    # ─────────────── Attendees ───────────────
    def _seed_attendees(self) -> None:
        """Seed a default attendee so the demo default ID keeps working."""
        now = datetime.now(timezone.utc).isoformat()
        seed = Attendee(
            attendee_id="attendee_001",
            email="alex.demo@atlasconf.example",
            name="Alex Demo",
            company="Atlas Conference",
            role="Demo Account",
            created_at=now,
        )
        self._attendees[seed.attendee_id] = seed
        self._attendee_seq = 1

    def _next_attendee_id(self) -> str:
        self._attendee_seq += 1
        return f"attendee_{self._attendee_seq:03d}"

    def list_attendees(self) -> List[Attendee]:
        return sorted(
            self._attendees.values(), key=lambda a: a.created_at
        )

    def get_attendee(self, attendee_id: str) -> Attendee:
        attendee = self._attendees.get(attendee_id)
        if attendee is None:
            raise NotFoundError(f"Attendee '{attendee_id}' not found")
        return attendee

    def find_attendee_by_email(self, email: str) -> Optional[Attendee]:
        target = _normalize_email(email)
        for a in self._attendees.values():
            if a.email == target:
                return a
        return None

    def create_attendee(
        self,
        *,
        email: str,
        name: str,
        company: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Attendee:
        with self._lock:
            normalized = _normalize_email(email)
            if not _is_valid_email(normalized):
                raise InvalidInputError(
                    "Please enter a valid email address (e.g. you@company.com)."
                )
            if self.find_attendee_by_email(normalized) is not None:
                raise DuplicateError(
                    "An account with that email already exists. "
                    "Try signing in instead."
                )
            attendee = Attendee(
                attendee_id=self._next_attendee_id(),
                email=normalized,
                name=name.strip(),
                company=(company or "").strip() or None,
                role=(role or "").strip() or None,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._attendees[attendee.attendee_id] = attendee
            return attendee

    def login_attendee(self, email: str) -> Attendee:
        normalized = _normalize_email(email)
        if not _is_valid_email(normalized):
            raise InvalidInputError("Please enter a valid email address.")
        attendee = self.find_attendee_by_email(normalized)
        if attendee is None:
            raise NotFoundError(
                "No account found with that email. Register to create one."
            )
        return attendee

    # ─────────────── Sessions ───────────────
    def list_sessions(
        self,
        *,
        topic: Optional[str] = None,
        date: Optional[str] = None,
        time_of_day: Optional[str] = None,
        level: Optional[str] = None,
        track: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[Session]:
        results: List[Session] = []
        topic_l = topic.lower().strip() if topic else None
        track_l = track.lower().strip() if track else None
        q_l = q.lower().strip() if q else None

        for session in self._sessions.values():
            if topic_l and topic_l not in session.topic.lower():
                continue
            if date and session.date != date:
                continue
            if time_of_day and session.time_of_day != time_of_day.lower():
                continue
            if level and session.level != level.lower():
                continue
            if track_l and track_l not in session.track.lower():
                continue
            if q_l:
                hay = " ".join(
                    [
                        session.title,
                        session.description,
                        session.speaker,
                        session.company,
                        session.track,
                        session.topic,
                    ]
                ).lower()
                if q_l not in hay:
                    continue
            results.append(session)

        results.sort(key=lambda s: (s.date, s.start_time, s.session_id))
        return results

    def get_session(self, session_id: str) -> Session:
        normalized = _normalize_session_id(session_id)
        session = self._sessions.get(normalized)
        if session is None:
            raise NotFoundError(f"Session '{session_id}' not found")
        return session

    def get_capacity(self, session_id: str) -> CapacityInfo:
        session = self.get_session(session_id)
        remaining = max(0, session.capacity - session.registered_count)
        return CapacityInfo(
            session_id=session.session_id,
            capacity=session.capacity,
            registered_count=session.registered_count,
            seats_remaining=remaining,
            status=_capacity_status(session.capacity, session.registered_count),
        )

    def list_tracks(self) -> List[str]:
        return sorted({s.track for s in self._sessions.values()})

    def list_dates(self) -> List[str]:
        return sorted({s.date for s in self._sessions.values()})

    # ─────────────── Registrations ───────────────
    def create_registration(
        self, attendee_id: str, session_id: str
    ) -> Registration:
        with self._lock:
            if attendee_id not in self._attendees:
                raise NotFoundError(
                    f"Attendee '{attendee_id}' not found. "
                    "Please sign in or register an account first."
                )
            session = self.get_session(session_id)
            session_id = session.session_id

            if session.registered_count >= session.capacity:
                raise FullSessionError(
                    f"Session '{session.title}' is full. "
                    "Please choose another session or join the waitlist."
                )

            for reg in self._registrations.values():
                if reg.attendee_id != attendee_id:
                    continue
                if reg.session_id == session_id:
                    raise ConflictError(
                        "You are already registered for this session."
                    )
                other = self._sessions.get(reg.session_id)
                if other is None:
                    continue
                if other.date == session.date and _times_overlap(
                    session.start_time,
                    session.end_time,
                    other.start_time,
                    other.end_time,
                ):
                    raise ConflictError(
                        f"This session overlaps with '{other.title}' "
                        f"({other.date} {other.start_time}–{other.end_time}). "
                        "Cancel that registration first if you'd like to switch."
                    )

            registration = Registration(
                registration_id=f"REG-{uuid.uuid4().hex[:10].upper()}",
                attendee_id=attendee_id,
                session_id=session_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._registrations[registration.registration_id] = registration

            updated = session.model_copy(
                update={"registered_count": session.registered_count + 1}
            )
            self._sessions[session_id] = updated

            return registration

    def cancel_registration(self, registration_id: str) -> Registration:
        with self._lock:
            normalized = _normalize_registration_id(registration_id)
            reg = self._registrations.get(normalized)
            if reg is None:
                raise NotFoundError(
                    f"Registration '{registration_id}' not found"
                )
            session = self._sessions.get(reg.session_id)
            if session is not None:
                updated = session.model_copy(
                    update={
                        "registered_count": max(0, session.registered_count - 1)
                    }
                )
                self._sessions[reg.session_id] = updated
            del self._registrations[normalized]
            return reg

    def get_agenda(self, attendee_id: str) -> List[AgendaItem]:
        items: List[AgendaItem] = []
        for reg in self._registrations.values():
            if reg.attendee_id != attendee_id:
                continue
            session = self._sessions.get(reg.session_id)
            if session is None:
                continue
            items.append(
                AgendaItem(registration_id=reg.registration_id, session=session)
            )
        items.sort(key=lambda i: (i.session.date, i.session.start_time))
        return items


store = Store()
