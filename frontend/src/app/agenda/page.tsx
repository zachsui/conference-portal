"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AgendaItem } from "@/lib/types";
import {
  formatDateLong,
  formatTimeRange,
  levelClasses,
  levelLabel,
} from "@/lib/format";
import { CancelRegistrationButton } from "@/components/CancelRegistrationButton";

function groupByDate(items: AgendaItem[]) {
  const map = new Map<string, AgendaItem[]>();
  for (const i of items) {
    const arr = map.get(i.session.date) ?? [];
    arr.push(i);
    map.set(i.session.date, arr);
  }
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
}

export default function AgendaPage() {
  const { attendee, ready } = useAuth();
  const [items, setItems] = useState<AgendaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!attendee) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAgenda(attendee.attendee_id);
      setItems(data);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [attendee]);

  useEffect(() => {
    if (!ready) return;
    if (!attendee) {
      setLoading(false);
      setItems([]);
      return;
    }
    load();
  }, [ready, attendee, load]);

  if (!ready || loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="h-8 w-48 animate-pulse rounded bg-ink-100" />
        <div className="mt-6 space-y-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded-xl bg-white shadow-card"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!attendee) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:px-6 lg:px-8">
        <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
          Sign in to view your agenda
        </h1>
        <p className="mt-2 text-sm text-ink-600">
          Your registered sessions are tied to your attendee account.
        </p>
        <div className="mt-6 flex flex-col items-center justify-center gap-2 sm:flex-row">
          <Link
            href="/login?next=%2Fagenda"
            className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
          >
            Sign in
          </Link>
          <Link
            href="/register?next=%2Fagenda"
            className="inline-flex items-center justify-center rounded-lg border border-ink-200 bg-white px-5 py-2.5 text-sm font-semibold text-ink-700 shadow-sm hover:border-brand-300 hover:text-brand-700"
          >
            Create account
          </Link>
        </div>
      </div>
    );
  }

  const grouped = groupByDate(items);

  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
      <div className="mt-8 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
            My agenda
          </h1>
          <p className="mt-1 text-sm text-ink-600">
            Sessions registered to{" "}
            <span className="font-semibold text-ink-800">{attendee.name}</span>{" "}
            <span className="font-mono text-ink-500">
              ({attendee.attendee_id})
            </span>
            .
          </p>
        </div>
        <Link
          href="/sessions"
          className="rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm font-semibold text-ink-700 shadow-sm hover:border-brand-300 hover:text-brand-700"
        >
          Add more sessions
        </Link>
      </div>

      {error && (
        <div className="mt-6 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800 ring-1 ring-rose-200">
          {error}
        </div>
      )}

      {items.length === 0 && !error && (
        <div className="mt-10 rounded-2xl border border-dashed border-ink-300 bg-white px-6 py-16 text-center">
          <h3 className="text-lg font-semibold text-ink-900">
            Your agenda is empty
          </h3>
          <p className="mt-1 text-sm text-ink-600">
            Browse the catalog and register for sessions to start building your
            schedule.
          </p>
          <Link
            href="/sessions"
            className="mt-5 inline-flex items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
          >
            Browse sessions
          </Link>
        </div>
      )}

      <div className="mt-8 space-y-10">
        {grouped.map(([date, dayItems]) => (
          <section key={date}>
            <div className="mb-4 flex items-center gap-3">
              <h2 className="text-xl font-semibold tracking-tight text-ink-900">
                {formatDateLong(date)}
              </h2>
              <span className="text-sm text-ink-500">
                {dayItems.length} session{dayItems.length === 1 ? "" : "s"}
              </span>
            </div>

            <ol className="relative space-y-3 border-l-2 border-brand-100 pl-6">
              {dayItems.map(({ session, registration_id }) => (
                <li
                  key={registration_id}
                  className="relative rounded-xl border border-ink-200/70 bg-white p-4 shadow-card"
                >
                  <span
                    aria-hidden
                    className="absolute -left-[31px] top-5 grid h-5 w-5 place-items-center rounded-full border-2 border-white bg-brand-600 text-[10px] font-bold text-white shadow"
                  >
                    ●
                  </span>

                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">
                        {formatTimeRange(session.start_time, session.end_time)}{" "}
                        · {session.room}
                      </div>
                      <Link
                        href={`/sessions/${session.session_id}`}
                        className="mt-1 block text-lg font-semibold leading-snug text-ink-900 hover:text-brand-700"
                      >
                        {session.title}
                      </Link>
                      <div className="mt-1 text-sm text-ink-600">
                        {session.speaker} · {session.company} · {session.track}
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span
                          className={
                            "inline-flex rounded-full px-2 py-0.5 text-xs font-medium " +
                            levelClasses(session.level)
                          }
                        >
                          {levelLabel(session.level)}
                        </span>
                        <span className="font-mono text-[11px] text-ink-400">
                          {registration_id}
                        </span>
                      </div>
                    </div>

                    <CancelRegistrationButton
                      registrationId={registration_id}
                      onCancelled={load}
                    />
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      <div className="h-16" />
    </div>
  );
}
