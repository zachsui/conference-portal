import type {
  AgendaItem,
  ApiError,
  Attendee,
  CapacityInfo,
  ChatResponse,
  Registration,
  Session,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export const DEFAULT_ATTENDEE_ID =
  process.env.NEXT_PUBLIC_DEFAULT_ATTENDEE_ID || "attendee_001";

export interface SessionSearchParams {
  topic?: string;
  date?: string;
  time_of_day?: string;
  level?: string;
  track?: string;
  q?: string;
  [key: string]: string | undefined;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "content-type": "application/json",
        accept: "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch {
    throw {
      status: 0,
      detail: {
        error: "network_error",
        message:
          "Could not reach the conference portal API. " +
          "Check that the backend is running at " +
          API_BASE_URL +
          ".",
      },
    } satisfies ApiError;
  }

  if (!res.ok) {
    let detail: ApiError["detail"] = `Request failed with ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // Ignore body parse failures
    }
    throw { status: res.status, detail } satisfies ApiError;
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

function buildQuery(params: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, value);
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  searchSessions: (params: SessionSearchParams = {}) =>
    request<Session[]>(`/sessions/search${buildQuery(params)}`),
  getSession: (sessionId: string) =>
    request<Session>(`/sessions/${encodeURIComponent(sessionId)}`),
  getSessionCapacity: (sessionId: string) =>
    request<CapacityInfo>(
      `/sessions/${encodeURIComponent(sessionId)}/capacity`
    ),
  register: (attendeeId: string, sessionId: string) =>
    request<Registration>(`/registrations`, {
      method: "POST",
      body: JSON.stringify({
        attendee_id: attendeeId,
        session_id: sessionId,
      }),
    }),
  cancelRegistration: (registrationId: string) =>
    request<void>(
      `/registrations/${encodeURIComponent(registrationId)}`,
      { method: "DELETE" }
    ),
  getAgenda: (attendeeId: string) =>
    request<AgendaItem[]>(
      `/attendees/${encodeURIComponent(attendeeId)}/agenda`
    ),
  getAttendee: (attendeeId: string) =>
    request<Attendee>(`/attendees/${encodeURIComponent(attendeeId)}`),
  listAttendees: () => request<Attendee[]>(`/attendees`),
  createAttendee: (input: {
    email: string;
    name: string;
    company?: string;
    role?: string;
  }) =>
    request<Attendee>(`/attendees`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  loginAttendee: (email: string) =>
    request<Attendee>(`/attendees/login`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  listTracks: () => request<string[]>("/tracks"),
  listDates: () => request<string[]>("/dates"),
  chatWithAgent: (attendeeId: string, message: string) =>
    request<ChatResponse>(`/agent/chat`, {
      method: "POST",
      body: JSON.stringify({ attendee_id: attendeeId, message }),
    }),
};

export function apiErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "detail" in err) {
    const detail = (err as ApiError).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      return detail.message;
    }
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong. Please try again.";
}
