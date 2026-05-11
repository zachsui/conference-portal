import Link from "next/link";
import { api } from "@/lib/api";
import { SessionCard } from "@/components/SessionCard";
import type { Session } from "@/lib/types";

export const dynamic = "force-dynamic";

async function safeFetchAll() {
  try {
    const [sessions, tracks] = await Promise.all([
      api.searchSessions(),
      api.listTracks(),
    ]);
    return { sessions, tracks, error: null as string | null };
  } catch (err) {
    return {
      sessions: [] as Session[],
      tracks: [] as string[],
      error:
        err && typeof err === "object" && "detail" in err
          ? typeof (err as { detail: unknown }).detail === "string"
            ? ((err as { detail: string }).detail)
            : ((err as { detail: { message?: string } }).detail?.message ??
              "Could not load sessions.")
          : "Could not load sessions.",
    };
  }
}

export default async function HomePage() {
  const { sessions, tracks, error } = await safeFetchAll();

  const featured = sessions
    .filter((s) =>
      [
        "S011", // Agentic Commerce
        "S006", // Stablecoins for Cross-Border Payouts
        "S017", // LLM-as-a-Judge
        "S041", // Product Strategy in the AI Platform Era
      ].includes(s.session_id)
    )
    .slice(0, 4);

  const stats = [
    { label: "Sessions", value: sessions.length || "—" },
    { label: "Tracks", value: tracks.length || "—" },
    {
      label: "Speakers",
      value: new Set(sessions.map((s) => s.speaker)).size || "—",
    },
    { label: "Days", value: 3 },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <section className="relative mt-10 overflow-hidden rounded-3xl bg-gradient-to-br from-brand-700 via-brand-800 to-ink-900 px-6 py-12 text-white shadow-xl sm:px-12 sm:py-16">
        <div className="absolute inset-0 -z-0 opacity-30 [mask-image:radial-gradient(circle_at_top_right,white,transparent_70%)]">
          <div className="absolute -top-32 right-0 h-96 w-96 rounded-full bg-brand-400 blur-3xl" />
          <div className="absolute bottom-0 -left-20 h-72 w-72 rounded-full bg-fuchsia-500 blur-3xl" />
        </div>

        <div className="relative max-w-3xl">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium uppercase tracking-wider text-brand-100 ring-1 ring-white/20">
            June 9 – 11, 2026 · Moscone West
          </span>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            The conference for builders shaping payments, platforms, and
            agentic AI.
          </h1>
          <p className="mt-4 max-w-2xl text-base text-brand-100 sm:text-lg">
            Three days. Ten tracks. Fifty hand-curated sessions covering
            payments, stablecoins, agentic systems, AI safety, identity, cloud
            infrastructure, data, developer platforms, product strategy, and
            compliance.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/sessions"
              className="inline-flex items-center justify-center rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-brand-800 shadow-sm transition hover:bg-brand-50"
            >
              Browse all sessions
            </Link>
            <Link
              href="/agenda"
              className="inline-flex items-center justify-center rounded-lg border border-white/30 bg-white/10 px-5 py-2.5 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/15"
            >
              View my agenda
            </Link>
          </div>
        </div>

        <dl className="relative mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {stats.map((s) => (
            <div
              key={s.label}
              className="rounded-xl bg-white/10 p-4 backdrop-blur ring-1 ring-white/15"
            >
              <dd className="text-3xl font-semibold tracking-tight">
                {s.value}
              </dd>
              <dt className="mt-1 text-xs uppercase tracking-wide text-brand-100">
                {s.label}
              </dt>
            </div>
          ))}
        </dl>
      </section>

      {error && (
        <div className="mt-8 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800 ring-1 ring-rose-200">
          {error}
        </div>
      )}

      <section className="mt-12">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-ink-900">
              Featured sessions
            </h2>
            <p className="mt-1 text-sm text-ink-600">
              A taste of what{"'"}s drawing the biggest crowds this year.
            </p>
          </div>
          <Link
            href="/sessions"
            className="text-sm font-semibold text-brand-700 hover:text-brand-800"
          >
            See all →
          </Link>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
          {featured.map((s) => (
            <SessionCard key={s.session_id} session={s} />
          ))}
        </div>
      </section>

      <section className="mt-14">
        <h2 className="text-2xl font-semibold tracking-tight text-ink-900">
          Explore by track
        </h2>
        <p className="mt-1 text-sm text-ink-600">
          Ten tracks covering the topics enterprise teams are working on right
          now.
        </p>
        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {tracks.map((track) => {
            const count = sessions.filter((s) => s.track === track).length;
            return (
              <Link
                key={track}
                href={`/sessions?track=${encodeURIComponent(track)}`}
                className="group flex items-center justify-between rounded-xl border border-ink-200/70 bg-white p-4 shadow-card transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-cardHover"
              >
                <div>
                  <div className="font-medium text-ink-900 group-hover:text-brand-700">
                    {track}
                  </div>
                  <div className="text-xs text-ink-500">
                    {count} session{count === 1 ? "" : "s"}
                  </div>
                </div>
                <span className="text-ink-400 group-hover:text-brand-600">
                  →
                </span>
              </Link>
            );
          })}
        </div>
      </section>

      <div className="h-16" />
    </div>
  );
}
