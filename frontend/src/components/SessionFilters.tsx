"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";

interface FilterOptions {
  tracks: string[];
  dates: string[];
}

const TIME_OF_DAY = [
  { value: "morning", label: "Morning" },
  { value: "afternoon", label: "Afternoon" },
  { value: "evening", label: "Evening" },
];

const LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

interface Props {
  options: FilterOptions;
}

export function SessionFilters({ options }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const initial = useMemo(
    () => ({
      q: searchParams.get("q") ?? "",
      track: searchParams.get("track") ?? "",
      topic: searchParams.get("topic") ?? "",
      date: searchParams.get("date") ?? "",
      time_of_day: searchParams.get("time_of_day") ?? "",
      level: searchParams.get("level") ?? "",
    }),
    [searchParams]
  );

  const [state, setState] = useState(initial);

  useEffect(() => {
    setState(initial);
  }, [initial]);

  function update(patch: Partial<typeof state>) {
    const next = { ...state, ...patch };
    setState(next);
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(next)) {
      if (value) params.set(key, value);
    }
    const qs = params.toString();
    startTransition(() => {
      router.replace(qs ? `/sessions?${qs}` : "/sessions");
    });
  }

  function clearAll() {
    setState({
      q: "",
      track: "",
      topic: "",
      date: "",
      time_of_day: "",
      level: "",
    });
    startTransition(() => router.replace("/sessions"));
  }

  const activeCount = Object.values(state).filter(Boolean).length;

  return (
    <div className="rounded-xl border border-ink-200/70 bg-white p-4 shadow-card">
      <div className="flex flex-col gap-3">
        <div className="relative">
          <input
            type="search"
            value={state.q}
            onChange={(e) => update({ q: e.target.value })}
            placeholder="Search sessions, speakers, companies, topics…"
            className="w-full rounded-lg border border-ink-200 bg-white px-4 py-2.5 pr-10 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
          />
          <span
            aria-hidden
            className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-400"
          >
            ⌕
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Select
            label="Track"
            value={state.track}
            onChange={(v) => update({ track: v })}
            options={options.tracks.map((t) => ({ value: t, label: t }))}
          />
          <input
            value={state.topic}
            onChange={(e) => update({ topic: e.target.value })}
            placeholder="Topic"
            className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
          />
          <Select
            label="Date"
            value={state.date}
            onChange={(v) => update({ date: v })}
            options={options.dates.map((d) => ({
              value: d,
              label: new Date(`${d}T00:00:00`).toLocaleDateString(undefined, {
                weekday: "short",
                month: "short",
                day: "numeric",
              }),
            }))}
          />
          <Select
            label="Time of day"
            value={state.time_of_day}
            onChange={(v) => update({ time_of_day: v })}
            options={TIME_OF_DAY}
          />
          <Select
            label="Level"
            value={state.level}
            onChange={(v) => update({ level: v })}
            options={LEVELS}
          />
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-ink-500">
            {activeCount === 0
              ? "No filters applied"
              : `${activeCount} filter${activeCount === 1 ? "" : "s"} applied`}
            {isPending ? " · updating…" : ""}
          </span>
          {activeCount > 0 && (
            <button
              type="button"
              onClick={clearAll}
              className="rounded-md px-2 py-1 text-sm font-medium text-brand-700 hover:bg-brand-50"
            >
              Clear all
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface SelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}

function Select({ label, value, options, onChange }: SelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200"
    >
      <option value="">All {label.toLowerCase()}s</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
