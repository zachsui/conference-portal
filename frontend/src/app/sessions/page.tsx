import { api, apiErrorMessage, type SessionSearchParams } from "@/lib/api";
import { SessionCard } from "@/components/SessionCard";
import { SessionFilters } from "@/components/SessionFilters";
import type { Session } from "@/lib/types";
import { formatDateLong } from "@/lib/format";

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{
    q?: string;
    track?: string;
    topic?: string;
    date?: string;
    time_of_day?: string;
    level?: string;
  }>;
}

function groupByDate(sessions: Session[]): [string, Session[]][] {
  const map = new Map<string, Session[]>();
  for (const s of sessions) {
    const arr = map.get(s.date) ?? [];
    arr.push(s);
    map.set(s.date, arr);
  }
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
}

export default async function SessionsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const filters: SessionSearchParams = {
    q: params.q,
    topic: params.topic,
    date: params.date,
    time_of_day: params.time_of_day,
    level: params.level,
    track: params.track,
  };

  let sessions: Session[] = [];
  let tracks: string[] = [];
  let dates: string[] = [];
  let error: string | null = null;

  try {
    [sessions, tracks, dates] = await Promise.all([
      api.searchSessions(filters),
      api.listTracks(),
      api.listDates(),
    ]);
  } catch (err) {
    error = apiErrorMessage(err);
  }

  const grouped = groupByDate(sessions);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="mt-8">
        <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
          Session catalog
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          Filter and search across every session at Atlas Conference 2026.
        </p>
      </div>

      <div className="mt-6">
        <SessionFilters options={{ tracks, dates }} />
      </div>

      {error && (
        <div className="mt-6 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800 ring-1 ring-rose-200">
          {error}
        </div>
      )}

      <div className="mt-6 text-sm text-ink-600">
        {sessions.length} session{sessions.length === 1 ? "" : "s"} match your
        filters.
      </div>

      {sessions.length === 0 && !error ? (
        <div className="mt-10 rounded-xl border border-dashed border-ink-300 bg-white px-6 py-16 text-center">
          <h3 className="text-lg font-semibold text-ink-900">
            No sessions found
          </h3>
          <p className="mt-1 text-sm text-ink-600">
            Try removing a filter, or search for a different topic.
          </p>
        </div>
      ) : (
        <div className="mt-6 space-y-10">
          {grouped.map(([date, items]) => (
            <section key={date}>
              <div className="mb-4 flex items-center gap-3">
                <h2 className="text-xl font-semibold tracking-tight text-ink-900">
                  {formatDateLong(date)}
                </h2>
                <span className="text-sm text-ink-500">
                  {items.length} session{items.length === 1 ? "" : "s"}
                </span>
              </div>
              <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
                {items.map((s) => (
                  <SessionCard key={s.session_id} session={s} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <div className="h-16" />
    </div>
  );
}
