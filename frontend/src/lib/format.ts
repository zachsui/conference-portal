import type { CapacityStatus, Level, Session, TimeOfDay } from "./types";

export function formatDateLong(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export function formatDateShort(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function formatTimeRange(start: string, end: string): string {
  return `${formatTime(start)} – ${formatTime(end)}`;
}

export function formatTime(time: string): string {
  const [hStr, m] = time.split(":");
  const h = Number(hStr);
  const period = h >= 12 ? "PM" : "AM";
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return `${hour12}:${m} ${period}`;
}

export function capacityStatus(session: Session): CapacityStatus {
  if (session.registered_count >= session.capacity) return "full";
  if (session.registered_count / session.capacity >= 0.85) return "almost_full";
  return "available";
}

export function capacityLabel(status: CapacityStatus): string {
  switch (status) {
    case "available":
      return "Available";
    case "almost_full":
      return "Almost Full";
    case "full":
      return "Full";
  }
}

export function capacityClasses(status: CapacityStatus): string {
  switch (status) {
    case "available":
      return "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200";
    case "almost_full":
      return "bg-amber-50 text-amber-700 ring-1 ring-amber-200";
    case "full":
      return "bg-rose-50 text-rose-700 ring-1 ring-rose-200";
  }
}

export function levelLabel(level: Level): string {
  return level.charAt(0).toUpperCase() + level.slice(1);
}

export function levelClasses(level: Level): string {
  switch (level) {
    case "beginner":
      return "bg-sky-50 text-sky-700 ring-1 ring-sky-200";
    case "intermediate":
      return "bg-violet-50 text-violet-700 ring-1 ring-violet-200";
    case "advanced":
      return "bg-fuchsia-50 text-fuchsia-700 ring-1 ring-fuchsia-200";
  }
}

export function timeOfDayLabel(t: TimeOfDay): string {
  return t.charAt(0).toUpperCase() + t.slice(1);
}
