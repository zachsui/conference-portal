"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AgendaItem, Session } from "@/lib/types";
import { capacityStatus } from "@/lib/format";

interface Props {
  session: Session;
}

type Mode = "register" | "registered" | "full" | "guest" | "loading";

export function RegisterButton({ session }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const { attendee, ready } = useAuth();
  const [isPending, startTransition] = useTransition();
  const [registrationId, setRegistrationId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) return;
    if (!attendee) {
      setRegistrationId(null);
      return;
    }
    let cancelled = false;
    api
      .getAgenda(attendee.attendee_id)
      .then((items: AgendaItem[]) => {
        if (cancelled) return;
        const existing = items.find(
          (i) => i.session.session_id === session.session_id
        );
        setRegistrationId(existing?.registration_id ?? null);
      })
      .catch(() => {
        // Non-fatal: leave button in default state.
      });
    return () => {
      cancelled = true;
    };
  }, [ready, attendee, session.session_id]);

  const status = capacityStatus(session);
  const mode: Mode = !ready
    ? "loading"
    : !attendee
    ? "guest"
    : registrationId
    ? "registered"
    : status === "full"
    ? "full"
    : "register";

  async function handleRegister() {
    if (!attendee) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const reg = await api.register(attendee.attendee_id, session.session_id);
      setRegistrationId(reg.registration_id);
      setSuccess("You're registered. See you in the room!");
      startTransition(() => router.refresh());
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    if (!registrationId) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      await api.cancelRegistration(registrationId);
      setRegistrationId(null);
      setSuccess("Registration cancelled.");
      startTransition(() => router.refresh());
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const nextParam = encodeURIComponent(pathname || "/sessions");

  return (
    <div className="space-y-3">
      {mode === "loading" && (
        <div className="h-10 w-full animate-pulse rounded-lg bg-ink-100" />
      )}

      {mode === "guest" && (
        <div className="space-y-2">
          <Link
            href={`/login?next=${nextParam}`}
            className="inline-flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
          >
            Sign in to register
          </Link>
          <Link
            href={`/register?next=${nextParam}`}
            className="inline-flex w-full items-center justify-center rounded-lg border border-ink-200 bg-white px-4 py-2.5 text-sm font-semibold text-ink-700 shadow-sm transition hover:border-brand-300 hover:text-brand-700"
          >
            Create an account
          </Link>
        </div>
      )}

      {mode === "register" && (
        <button
          type="button"
          onClick={handleRegister}
          disabled={busy || isPending}
          className="inline-flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-brand-400"
        >
          {busy ? "Registering…" : "Register for this session"}
        </button>
      )}

      {mode === "registered" && (
        <div className="space-y-2">
          <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800 ring-1 ring-emerald-200">
            ✓ You are registered
          </div>
          <button
            type="button"
            onClick={handleCancel}
            disabled={busy || isPending}
            className="inline-flex w-full items-center justify-center rounded-lg border border-ink-200 bg-white px-4 py-2.5 text-sm font-semibold text-ink-700 shadow-sm transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy ? "Cancelling…" : "Cancel registration"}
          </button>
        </div>
      )}

      {mode === "full" && (
        <button
          type="button"
          disabled
          className="inline-flex w-full cursor-not-allowed items-center justify-center rounded-lg bg-ink-200 px-4 py-2.5 text-sm font-semibold text-ink-500"
        >
          Session is full
        </button>
      )}

      {error && (
        <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800 ring-1 ring-rose-200">
          {error}
        </div>
      )}
      {success && !error && (
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 ring-1 ring-emerald-200">
          {success}
        </div>
      )}
    </div>
  );
}
