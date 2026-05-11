import Link from "next/link";
import { notFound } from "next/navigation";
import { api, apiErrorMessage } from "@/lib/api";
import { RegisterButton } from "@/components/RegisterButton";
import {
  capacityClasses,
  capacityLabel,
  capacityStatus,
  formatDateLong,
  formatTimeRange,
  levelClasses,
  levelLabel,
  timeOfDayLabel,
} from "@/lib/format";
import type { ApiError } from "@/lib/types";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function SessionDetailPage({ params }: PageProps) {
  const { sessionId } = await params;
  let session;
  let capacity;
  try {
    [session, capacity] = await Promise.all([
      api.getSession(sessionId),
      api.getSessionCapacity(sessionId),
    ]);
  } catch (err) {
    if (typeof err === "object" && err && "status" in err) {
      const apiErr = err as ApiError;
      if (apiErr.status === 404) {
        notFound();
      }
    }
    throw new Error(apiErrorMessage(err));
  }

  const status = capacityStatus(session);
  const pct = Math.min(
    100,
    Math.round((session.registered_count / session.capacity) * 100)
  );

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
      <nav className="mt-8 flex items-center gap-2 text-sm text-ink-500">
        <Link href="/sessions" className="hover:text-brand-700">
          Sessions
        </Link>
        <span>›</span>
        <span className="text-ink-700">{session.session_id}</span>
      </nav>

      <div className="mt-4 grid grid-cols-1 gap-8 lg:grid-cols-3">
        <article className="lg:col-span-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-700">
              {session.track}
            </span>
            <span
              className={
                "rounded-full px-3 py-1 text-xs font-semibold " +
                levelClasses(session.level)
              }
            >
              {levelLabel(session.level)}
            </span>
            <span
              className={
                "rounded-full px-3 py-1 text-xs font-semibold " +
                capacityClasses(status)
              }
            >
              {capacityLabel(status)}
            </span>
          </div>

          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink-900 sm:text-4xl">
            {session.title}
          </h1>

          <div className="mt-3 text-sm text-ink-600">
            {formatDateLong(session.date)}
            <span className="text-ink-400"> · </span>
            {formatTimeRange(session.start_time, session.end_time)}
            <span className="text-ink-400"> · </span>
            {session.room}
          </div>

          <div className="prose prose-ink mt-6 max-w-none">
            <p className="text-base leading-relaxed text-ink-700">
              {session.description}
            </p>
          </div>

          <section className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Stat label="Topic" value={session.topic} />
            <Stat
              label="Time of day"
              value={timeOfDayLabel(session.time_of_day)}
            />
            <Stat label="Speaker" value={session.speaker} />
            <Stat label="Company" value={session.company} />
            <Stat label="Room" value={session.room} />
            <Stat label="Session ID" value={session.session_id} mono />
          </section>
        </article>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-2xl border border-ink-200/70 bg-white p-5 shadow-card">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-ink-500">
              Capacity
            </h3>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-semibold tracking-tight text-ink-900">
                {capacity.seats_remaining}
              </span>
              <span className="text-sm text-ink-500">seats remaining</span>
            </div>
            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-ink-100">
              <div
                className={
                  "h-full rounded-full transition-all " +
                  (status === "full"
                    ? "bg-rose-500"
                    : status === "almost_full"
                    ? "bg-amber-500"
                    : "bg-emerald-500")
                }
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="mt-2 flex justify-between text-xs text-ink-500">
              <span>
                {session.registered_count} / {session.capacity} registered
              </span>
              <span>{pct}% full</span>
            </div>

            <div className="mt-5">
              <RegisterButton session={session} />
            </div>

            <div className="mt-5 border-t border-ink-100 pt-4 text-xs text-ink-500">
              <p>
                Overlap with another session you{"'"}ve already added? You
                {"'"}ll need
                to cancel that registration first.
              </p>
            </div>
          </div>
        </aside>
      </div>

      <div className="h-16" />
    </div>
  );
}

function Stat({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-xl border border-ink-200/70 bg-white p-4">
      <div className="text-xs uppercase tracking-wide text-ink-400">
        {label}
      </div>
      <div
        className={
          "mt-1 text-sm text-ink-800 " + (mono ? "font-mono text-xs" : "")
        }
      >
        {value}
      </div>
    </div>
  );
}
