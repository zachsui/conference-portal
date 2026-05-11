import Link from "next/link";
import type { Session } from "@/lib/types";
import {
  capacityClasses,
  capacityLabel,
  capacityStatus,
  formatDateShort,
  formatTimeRange,
  levelClasses,
  levelLabel,
} from "@/lib/format";

interface Props {
  session: Session;
}

export function SessionCard({ session }: Props) {
  const status = capacityStatus(session);
  const remaining = Math.max(0, session.capacity - session.registered_count);
  const pct = Math.min(
    100,
    Math.round((session.registered_count / session.capacity) * 100)
  );

  return (
    <Link
      href={`/sessions/${session.session_id}`}
      className="group block rounded-xl border border-ink-200/70 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-cardHover"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-brand-700">
          {session.track}
        </span>
        <span
          className={
            "rounded-full px-2.5 py-1 text-xs font-semibold " +
            capacityClasses(status)
          }
        >
          {capacityLabel(status)}
        </span>
      </div>

      <h3 className="mt-3 text-lg font-semibold leading-snug text-ink-900 group-hover:text-brand-700">
        {session.title}
      </h3>

      <p className="mt-2 line-clamp-2 text-sm text-ink-600">
        {session.description}
      </p>

      <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm">
        <div>
          <dt className="text-xs uppercase tracking-wide text-ink-400">
            When
          </dt>
          <dd className="text-ink-700">
            {formatDateShort(session.date)}
            <span className="text-ink-400"> · </span>
            {formatTimeRange(session.start_time, session.end_time)}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-ink-400">
            Where
          </dt>
          <dd className="text-ink-700">{session.room}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-ink-400">
            Speaker
          </dt>
          <dd className="text-ink-700">
            {session.speaker}
            <span className="text-ink-400"> · </span>
            {session.company}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-ink-400">
            Level
          </dt>
          <dd>
            <span
              className={
                "inline-flex rounded-full px-2 py-0.5 text-xs font-medium " +
                levelClasses(session.level)
              }
            >
              {levelLabel(session.level)}
            </span>
          </dd>
        </div>
      </dl>

      <div className="mt-4">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
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
        <div className="mt-1.5 flex justify-between text-xs text-ink-500">
          <span>
            {session.registered_count} / {session.capacity} registered
          </span>
          <span>
            {remaining > 0 ? `${remaining} seats left` : "No seats remaining"}
          </span>
        </div>
      </div>
    </Link>
  );
}
