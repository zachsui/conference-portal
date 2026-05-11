"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiErrorMessage } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const { attendee, ready, signIn } = useAuth();
  const next = search.get("next") || "/agenda";

  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && attendee) {
      router.replace(next);
    }
  }, [ready, attendee, router, next]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email);
      router.replace(next);
      router.refresh();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16 sm:px-6">
      <div className="rounded-2xl border border-ink-200/70 bg-white p-7 shadow-card">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
          Sign in
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          Enter the email you registered with. (Demo mode — no password
          required.)
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-ink-800"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="mt-1 w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
            />
          </div>

          {error && (
            <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800 ring-1 ring-rose-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="inline-flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:bg-brand-400"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="mt-5 border-t border-ink-100 pt-4 text-sm text-ink-600">
          New here?{" "}
          <Link
            href={`/register?next=${encodeURIComponent(next)}`}
            className="font-semibold text-brand-700 hover:text-brand-800"
          >
            Create an account
          </Link>
          .
        </div>

        <div className="mt-3 rounded-lg bg-ink-50 px-3 py-2 text-xs text-ink-600">
          <span className="font-semibold">Demo tip:</span> the seeded account{" "}
          <span className="font-mono">alex.demo@atlasconf.example</span> is
          always available.
        </div>
      </div>
    </div>
  );
}
