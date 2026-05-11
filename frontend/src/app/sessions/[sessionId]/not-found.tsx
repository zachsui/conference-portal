import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-24 text-center sm:px-6 lg:px-8">
      <h1 className="text-4xl font-semibold tracking-tight text-ink-900">
        Session not found
      </h1>
      <p className="mt-3 text-ink-600">
        This session ID isn{"'"}t on the schedule. Browse the catalog to find
        another talk.
      </p>
      <Link
        href="/sessions"
        className="mt-6 inline-flex items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
      >
        Back to all sessions
      </Link>
    </div>
  );
}
