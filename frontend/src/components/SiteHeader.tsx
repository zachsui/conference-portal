"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/sessions", label: "Sessions" },
  { href: "/agenda", label: "My Agenda" },
  { href: "/assistant", label: "Assistant" },
];

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-30 border-b border-ink-200/60 bg-white/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <span
            aria-hidden
            className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-brand-600 to-brand-800 text-sm font-bold text-white shadow-sm"
          >
            AT
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-ink-900">
              Atlas Conference
            </div>
            <div className="text-xs text-ink-500">Attendee Portal · 2026</div>
          </div>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={
                  "rounded-md px-3 py-2 text-sm font-medium transition-colors " +
                  (active
                    ? "bg-brand-50 text-brand-700"
                    : "text-ink-600 hover:bg-ink-100 hover:text-ink-900")
                }
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <UserMenu />
      </div>

      <nav className="flex items-center gap-1 overflow-x-auto border-t border-ink-100 px-4 py-2 md:hidden">
        {NAV.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors " +
                (active
                  ? "bg-brand-50 text-brand-700"
                  : "text-ink-600 hover:bg-ink-100 hover:text-ink-900")
              }
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}

function UserMenu() {
  const { attendee, ready, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [open]);

  if (!ready) {
    return (
      <div className="h-9 w-28 animate-pulse rounded-full bg-ink-100" />
    );
  }

  if (!attendee) {
    return (
      <div className="flex items-center gap-2">
        <Link
          href={`/login?next=${encodeURIComponent(pathname || "/")}`}
          className="rounded-md px-3 py-1.5 text-sm font-medium text-ink-700 hover:bg-ink-100"
        >
          Sign in
        </Link>
        <Link
          href={`/register?next=${encodeURIComponent(pathname || "/")}`}
          className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
        >
          Create account
        </Link>
      </div>
    );
  }

  const initials = attendee.name
    .split(/\s+/)
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full border border-ink-200 bg-white px-2.5 py-1 text-sm shadow-sm transition hover:border-brand-300"
      >
        <span
          aria-hidden
          className="grid h-7 w-7 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-[11px] font-semibold text-white"
        >
          {initials || "·"}
        </span>
        <span className="hidden max-w-[140px] truncate text-ink-800 sm:inline">
          {attendee.name}
        </span>
        <span aria-hidden className="text-ink-400">
          ▾
        </span>
      </button>

      {open && (
        <div
          className="absolute right-0 z-40 mt-2 w-72 origin-top-right rounded-xl border border-ink-200 bg-white p-1 shadow-xl ring-1 ring-black/5"
          role="menu"
        >
          <div className="px-3 py-2.5">
            <div className="text-sm font-semibold text-ink-900">
              {attendee.name}
            </div>
            <div className="truncate text-xs text-ink-500">
              {attendee.email}
            </div>
            {(attendee.company || attendee.role) && (
              <div className="mt-1 truncate text-xs text-ink-500">
                {[attendee.role, attendee.company]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
            )}
            <div className="mt-2 font-mono text-[10px] text-ink-400">
              {attendee.attendee_id}
            </div>
          </div>
          <div className="my-1 h-px bg-ink-100" />
          <Link
            href="/agenda"
            onClick={() => setOpen(false)}
            className="block rounded-md px-3 py-2 text-sm text-ink-700 hover:bg-ink-100"
            role="menuitem"
          >
            My agenda
          </Link>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              signOut();
              router.push("/");
              router.refresh();
            }}
            className="block w-full rounded-md px-3 py-2 text-left text-sm text-rose-700 hover:bg-rose-50"
            role="menuitem"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
