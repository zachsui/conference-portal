"""Pydantic models for the conference portal API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

TimeOfDay = Literal["morning", "afternoon", "evening"]
Level = Literal["beginner", "intermediate", "advanced"]
CapacityStatus = Literal["available", "almost_full", "full"]


class Session(BaseModel):
    session_id: str
    title: str
    description: str
    track: str
    topic: str
    date: str  # ISO date, e.g. "2026-06-09"
    start_time: str  # 24h "HH:MM"
    end_time: str  # 24h "HH:MM"
    time_of_day: TimeOfDay
    room: str
    speaker: str
    company: str
    level: Level
    capacity: int = Field(ge=1)
    registered_count: int = Field(ge=0)


class CapacityInfo(BaseModel):
    session_id: str
    capacity: int
    registered_count: int
    seats_remaining: int
    status: CapacityStatus


class RegistrationCreate(BaseModel):
    attendee_id: str
    session_id: str


class Registration(BaseModel):
    registration_id: str
    attendee_id: str
    session_id: str
    created_at: str  # ISO timestamp


class AgendaItem(BaseModel):
    registration_id: str
    session: Session


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None


class Attendee(BaseModel):
    attendee_id: str
    email: str
    name: str
    company: Optional[str] = None
    role: Optional[str] = None
    created_at: str  # ISO timestamp


class AttendeeCreate(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    name: str = Field(min_length=1, max_length=120)
    company: Optional[str] = Field(default=None, max_length=120)
    role: Optional[str] = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
