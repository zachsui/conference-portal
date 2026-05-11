"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiErrorMessage } from "@/lib/api";

export function RegisterForm() {
  const router = useRouter();
  const search = useSearchParams();
  const { attendee, ready, signUp } = useAuth();
  const next = search.get("next") || "/sessions";

  const [form, setForm] = useState({
    email: "",
    name: "",
    company: "",
    role: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && attendee) {
      router.replace(next);
    }
  }, [ready, attendee, router, next]);

  function onChange(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signUp({
        email: form.email,
        name: form.name,
        company: form.company || undefined,
        role: form.role || undefined,
      });
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
          Create your attendee account
        </h1>
        <p className="mt-1 text-sm text-ink-600">
          Takes about 10 seconds. (Demo mode — no password required.)
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <Field
            label="Email"
            id="email"
            type="email"
            required
            autoComplete="email"
            value={form.email}
            onChange={onChange("email")}
            placeholder="you@company.com"
          />
          <Field
            label="Full name"
            id="name"
            required
            autoComplete="name"
            value={form.name}
            onChange={onChange("name")}
            placeholder="Jane Doe"
          />
          <Field
            label="Company (optional)"
            id="company"
            autoComplete="organization"
            value={form.company}
            onChange={onChange("company")}
            placeholder="Acme, Inc."
          />
          <Field
            label="Role (optional)"
            id="role"
            autoComplete="organization-title"
            value={form.role}
            onChange={onChange("role")}
            placeholder="Staff Engineer"
          />

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
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>

        <div className="mt-5 border-t border-ink-100 pt-4 text-sm text-ink-600">
          Already have an account?{" "}
          <Link
            href={`/login?next=${encodeURIComponent(next)}`}
            className="font-semibold text-brand-700 hover:text-brand-800"
          >
            Sign in
          </Link>
          .
        </div>
      </div>
    </div>
  );
}

interface FieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  id: string;
}

function Field({ label, id, ...rest }: FieldProps) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-ink-800">
        {label}
      </label>
      <input
        id={id}
        {...rest}
        className="mt-1 w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
      />
    </div>
  );
}
