"""Transactional email via Resend.

Configuration (env vars):
    RESEND_API_KEY   – API key from https://resend.com/api-keys
    RESEND_FROM      – From header, e.g. "Atlas Conference <onboarding@resend.dev>"
                       Default: "Atlas Conference <onboarding@resend.dev>"
                       NOTE: Resend's onboarding sender can only deliver to the
                       email registered on your Resend account. To send to
                       arbitrary addresses you must verify your own domain in
                       Resend → Domains.
    APP_BASE_URL     – Public URL of the frontend, used for links in emails.
                       Default: http://localhost:3000
    RESEND_REPLY_TO  – Optional Reply-To address.

If RESEND_API_KEY is missing, the service logs the email to stdout and
returns "skipped" — the rest of the app keeps working.
"""
from __future__ import annotations

import logging
import os
from html import escape
from typing import Optional

import resend

from app.models import Attendee, Registration, Session

logger = logging.getLogger("conference_portal.email")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(levelname)s:     [email] %(message)s")
    )
    logger.addHandler(_handler)
    logger.propagate = False


def _format_date_long(iso: str) -> str:
    from datetime import datetime

    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
        return d.strftime("%A, %B %-d, %Y")
    except ValueError:
        return iso


def _format_time(t: str) -> str:
    try:
        h, m = t.split(":")
        hour = int(h)
        period = "PM" if hour >= 12 else "AM"
        hour12 = hour % 12 or 12
        return f"{hour12}:{m} {period}"
    except (ValueError, IndexError):
        return t


class EmailService:
    """Thin wrapper around the Resend Python SDK with graceful degradation."""

    def __init__(self) -> None:
        self.api_key = os.getenv("RESEND_API_KEY", "").strip()
        self.from_address = os.getenv(
            "RESEND_FROM",
            "Atlas Conference <onboarding@resend.dev>",
        ).strip()
        self.app_base_url = os.getenv(
            "APP_BASE_URL", "http://localhost:3000"
        ).strip().rstrip("/")
        self.reply_to: Optional[str] = (
            os.getenv("RESEND_REPLY_TO", "").strip() or None
        )

        if self.api_key:
            resend.api_key = self.api_key
            logger.info(
                "EmailService configured (from=%s, reply_to=%s)",
                self.from_address,
                self.reply_to,
            )
        else:
            logger.warning(
                "RESEND_API_KEY not set – emails will be logged but not sent."
            )

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    # ─────────────── Public API ───────────────
    def send_welcome(self, attendee: Attendee) -> str:
        subject = "Welcome to Atlas Conference 2026"
        html = self._render_welcome(attendee)
        text = (
            f"Hi {attendee.name},\n\n"
            "Welcome to Atlas Conference 2026! Your attendee account is "
            f"ready (ID: {attendee.attendee_id}).\n\n"
            f"Browse the catalog: {self.app_base_url}/sessions\n"
            f"Your agenda: {self.app_base_url}/agenda\n\n"
            "See you in San Francisco — June 9–11, 2026."
        )
        return self._send(attendee.email, subject, html, text)

    def send_registration_confirmation(
        self,
        attendee: Attendee,
        session: Session,
        registration: Registration,
    ) -> str:
        subject = f"You're registered: {session.title}"
        html = self._render_confirmation(attendee, session, registration)
        text = (
            f"Hi {attendee.name},\n\n"
            f"You're registered for \"{session.title}\".\n\n"
            f"When:  {_format_date_long(session.date)}, "
            f"{_format_time(session.start_time)}–{_format_time(session.end_time)}\n"
            f"Where: {session.room}\n"
            f"Speaker: {session.speaker} ({session.company})\n"
            f"Track: {session.track}\n\n"
            f"Confirmation ID: {registration.registration_id}\n"
            f"Manage your agenda: {self.app_base_url}/agenda\n"
        )
        return self._send(attendee.email, subject, html, text)

    def send_registration_cancelled(
        self, attendee: Attendee, session: Session, registration: Registration
    ) -> str:
        subject = f"Registration cancelled: {session.title}"
        html = self._render_cancelled(attendee, session, registration)
        text = (
            f"Hi {attendee.name},\n\n"
            f"Your registration for \"{session.title}\" has been cancelled "
            f"(was: {_format_date_long(session.date)}, "
            f"{_format_time(session.start_time)} in {session.room}).\n\n"
            f"Browse other sessions: {self.app_base_url}/sessions\n"
        )
        return self._send(attendee.email, subject, html, text)

    # ─────────────── Internals ───────────────
    def _send(self, to: str, subject: str, html: str, text: str) -> str:
        if not self.enabled:
            logger.info(
                "[email-stub] to=%s subject=%r (set RESEND_API_KEY to send)",
                to,
                subject,
            )
            return "skipped"
        params: dict = {
            "from": self.from_address,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text,
        }
        if self.reply_to:
            params["reply_to"] = self.reply_to
        try:
            response = resend.Emails.send(params)
            email_id = (
                response.get("id") if isinstance(response, dict) else None
            )
            logger.info(
                "Sent %r to %s via Resend (id=%s)", subject, to, email_id
            )
            return email_id or "sent"
        except Exception as exc:
            logger.exception(
                "Resend send failed (to=%s subject=%r): %s", to, subject, exc
            )
            return "failed"

    # ─────────────── Templates ───────────────
    def _shell(self, body_html: str, preheader: str = "") -> str:
        return f"""\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Atlas Conference 2026</title>
  </head>
  <body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,Segoe UI,Roboto,Inter,sans-serif;color:#0f172a;">
    <span style="display:none;visibility:hidden;opacity:0;height:0;width:0;overflow:hidden;mso-hide:all;">
      {escape(preheader)}
    </span>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f1f5f9;padding:32px 12px;">
      <tr><td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(15,23,42,0.08);">
          <tr><td style="background:linear-gradient(135deg,#4338ca 0%,#1e1b4b 100%);padding:24px 32px;">
            <div style="display:inline-block;padding:6px 12px;background:rgba(255,255,255,0.12);border-radius:999px;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#c7d2fe;">
              Atlas Conference 2026
            </div>
            <div style="margin-top:8px;color:#ffffff;font-size:13px;opacity:0.85;">
              June 9–11 · Moscone West, San Francisco
            </div>
          </td></tr>
          <tr><td style="padding:32px;">
            {body_html}
          </td></tr>
          <tr><td style="padding:20px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;color:#64748b;font-size:12px;">
            You are receiving this email because you created an attendee
            account at Atlas Conference 2026. This is a fictional event
            built for portal demos.
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""

    def _button(self, label: str, href: str) -> str:
        return f"""\
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:20px;">
  <tr><td style="border-radius:10px;background:#4f46e5;">
    <a href="{escape(href, quote=True)}"
       style="display:inline-block;padding:11px 20px;font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;">
      {escape(label)}
    </a>
  </td></tr>
</table>"""

    def _render_welcome(self, attendee: Attendee) -> str:
        body = f"""\
<h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;color:#0f172a;">
  Welcome, {escape(attendee.name)} 👋
</h1>
<p style="margin:0 0 12px;font-size:15px;line-height:1.6;color:#334155;">
  Your attendee account for <strong>Atlas Conference 2026</strong> is ready.
  You can now browse 50 sessions across 10 tracks and build a personal agenda.
</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;width:100%;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;">
  <tr><td style="padding:14px 16px;font-size:13px;color:#475569;">
    <div><span style="color:#94a3b8;">Account ID:</span>
      <span style="font-family:ui-monospace,Menlo,monospace;color:#0f172a;">{escape(attendee.attendee_id)}</span></div>
    <div style="margin-top:4px;"><span style="color:#94a3b8;">Email:</span>
      <span style="color:#0f172a;">{escape(attendee.email)}</span></div>
  </td></tr>
</table>
{self._button("Browse sessions", f"{self.app_base_url}/sessions")}
<p style="margin:24px 0 0;font-size:13px;line-height:1.6;color:#64748b;">
  Tip: register for sessions early — popular tracks fill up.
</p>"""
        return self._shell(body, "Your Atlas Conference attendee account is ready.")

    def _render_confirmation(
        self,
        attendee: Attendee,
        session: Session,
        registration: Registration,
    ) -> str:
        body = f"""\
<div style="display:inline-block;padding:4px 10px;border-radius:999px;background:#ecfdf5;color:#047857;font-size:12px;font-weight:600;">
  ✓ Registration confirmed
</div>
<h1 style="margin:12px 0 6px;font-size:22px;line-height:1.3;color:#0f172a;">
  {escape(session.title)}
</h1>
<div style="font-size:13px;color:#64748b;">{escape(session.track)} · {escape(session.level.title())}</div>

<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:18px;width:100%;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;">
  <tr><td style="padding:16px;font-size:14px;color:#334155;">
    <div style="margin-bottom:8px;"><span style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;">When</span><br/>
      {escape(_format_date_long(session.date))} · {escape(_format_time(session.start_time))}–{escape(_format_time(session.end_time))}
    </div>
    <div style="margin-bottom:8px;"><span style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;">Where</span><br/>
      {escape(session.room)}
    </div>
    <div><span style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:0.06em;">Speaker</span><br/>
      {escape(session.speaker)} · {escape(session.company)}
    </div>
  </td></tr>
</table>

<p style="margin:16px 0 0;font-size:13px;color:#475569;">
  Confirmation ID: <span style="font-family:ui-monospace,Menlo,monospace;color:#0f172a;">{escape(registration.registration_id)}</span>
</p>
{self._button("View my agenda", f"{self.app_base_url}/agenda")}
<p style="margin:24px 0 0;font-size:13px;line-height:1.6;color:#64748b;">
  Need to cancel? You can free your seat from the agenda page —
  no penalty, but please do it early so others can join.
</p>"""
        return self._shell(
            body,
            f"You're registered for {session.title} on {session.date}.",
        )

    def _render_cancelled(
        self,
        attendee: Attendee,
        session: Session,
        registration: Registration,
    ) -> str:
        body = f"""\
<div style="display:inline-block;padding:4px 10px;border-radius:999px;background:#fef2f2;color:#b91c1c;font-size:12px;font-weight:600;">
  Registration cancelled
</div>
<h1 style="margin:12px 0 6px;font-size:22px;line-height:1.3;color:#0f172a;">
  {escape(session.title)}
</h1>
<p style="margin:0;font-size:14px;color:#475569;">
  {escape(_format_date_long(session.date))} · {escape(_format_time(session.start_time))} · {escape(session.room)}
</p>
<p style="margin:18px 0 0;font-size:14px;line-height:1.6;color:#334155;">
  We've released your seat. The slot is now back in the pool for other attendees.
  If this was a mistake, you can register again from the session page —
  subject to availability.
</p>
{self._button("Find another session", f"{self.app_base_url}/sessions")}"""
        return self._shell(
            body,
            f"Your registration for {session.title} was cancelled.",
        )


email_service = EmailService()
