"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  capacityClasses,
  capacityLabel,
  capacityStatus,
  formatDateShort,
  formatTimeRange,
  levelClasses,
  levelLabel,
} from "@/lib/format";
import type {
  ChatResponse,
  PendingAction,
  PolicyViolation,
  Session,
  ToolCallTrace,
} from "@/lib/types";

type Turn =
  | { role: "user"; text: string }
  | { role: "assistant"; response: ChatResponse }
  | { role: "error"; text: string };

const SUGGESTIONS = [
  "What AI safety sessions are happening this afternoon?",
  "Help me register for a stablecoin session on June 9.",
  "Show my agenda.",
  "I want to register for the LLM-as-a-judge talk.",
];

const STORAGE_PREFIX = "assistant.history.v1.";
const MAX_PERSISTED_TURNS = 50;

function storageKeyFor(attendeeId: string): string {
  return `${STORAGE_PREFIX}${attendeeId}`;
}

function loadTurns(attendeeId: string): Turn[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKeyFor(attendeeId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as Turn[]) : [];
  } catch {
    return [];
  }
}

function saveTurns(attendeeId: string, turns: Turn[]): void {
  if (typeof window === "undefined") return;
  try {
    const trimmed =
      turns.length > MAX_PERSISTED_TURNS
        ? turns.slice(turns.length - MAX_PERSISTED_TURNS)
        : turns;
    window.localStorage.setItem(
      storageKeyFor(attendeeId),
      JSON.stringify(trimmed),
    );
  } catch {
    // Quota exceeded or storage disabled — silently ignore.
  }
}

// ─────────────────── Module-level chat store ───────────────────
// Lives outside React, so an in-flight request survives navigating to
// another route. Without this, leaving the /assistant tab unmounts the
// component, the `fetch` orphans, "Thinking…" disappears, and the
// response can never reach the UI.
type ChatState = { turns: Turn[]; busy: boolean };
type Listener = () => void;

const chatStores = new Map<
  string,
  { state: ChatState; listeners: Set<Listener> }
>();

function getChatStore(attendeeId: string) {
  let store = chatStores.get(attendeeId);
  if (!store) {
    store = {
      state: { turns: loadTurns(attendeeId), busy: false },
      listeners: new Set(),
    };
    chatStores.set(attendeeId, store);
  }
  return store;
}

function setChatState(attendeeId: string, patch: Partial<ChatState>) {
  const store = getChatStore(attendeeId);
  store.state = { ...store.state, ...patch };
  if (patch.turns) saveTurns(attendeeId, store.state.turns);
  store.listeners.forEach((l) => l());
}

function appendTurn(attendeeId: string, turn: Turn) {
  const store = getChatStore(attendeeId);
  const nextTurns = [...store.state.turns, turn];
  store.state = { ...store.state, turns: nextTurns };
  saveTurns(attendeeId, nextTurns);
  store.listeners.forEach((l) => l());
}

function useChatStore(attendeeId: string | undefined): ChatState {
  const [, force] = useState(0);
  useEffect(() => {
    if (!attendeeId) return;
    const store = getChatStore(attendeeId);
    const listener = () => force((n) => n + 1);
    store.listeners.add(listener);
    return () => {
      store.listeners.delete(listener);
    };
  }, [attendeeId]);
  return attendeeId
    ? getChatStore(attendeeId).state
    : { turns: [], busy: false };
}

export default function AssistantPage() {
  const { attendee, ready } = useAuth();
  const { turns, busy } = useChatStore(attendee?.attendee_id);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, busy]);

  async function send(text?: string) {
    const message = (text ?? input).trim();
    if (!message || !attendee || busy) return;
    const attendeeId = attendee.attendee_id;
    setInput("");
    appendTurn(attendeeId, { role: "user", text: message });
    setChatState(attendeeId, { busy: true });
    try {
      const res = await api.chatWithAgent(attendeeId, message);
      appendTurn(attendeeId, { role: "assistant", response: res });
    } catch (err) {
      appendTurn(attendeeId, { role: "error", text: apiErrorMessage(err) });
    } finally {
      setChatState(attendeeId, { busy: false });
    }
  }

  function clearHistory() {
    if (!attendee) return;
    setChatState(attendee.attendee_id, { turns: [] });
    if (typeof window !== "undefined") {
      try {
        window.localStorage.removeItem(storageKeyFor(attendee.attendee_id));
      } catch {
        /* noop */
      }
    }
  }

  if (!ready) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-16">
        <div className="h-72 animate-pulse rounded-2xl bg-white shadow-card" />
      </div>
    );
  }

  if (!attendee) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:px-6">
        <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
          Sign in to chat with the assistant
        </h1>
        <p className="mt-2 text-sm text-ink-600">
          The assistant uses your attendee account to register, cancel, and
          look up your agenda.
        </p>
        <Link
          href="/login?next=%2Fassistant"
          className="mt-6 inline-flex items-center justify-center rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
        >
          Sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
      <div className="mt-8 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
            Conference Assistant
          </h1>
          <p className="mt-1 text-sm text-ink-600">
            Powered by Gemini with real tool calling. Search, register, cancel,
            and view your agenda in plain English. Acting as{" "}
            <span className="font-mono text-ink-800">
              {attendee.attendee_id}
            </span>
            . Conversation history is saved on this device.
          </p>
        </div>
        {turns.length > 0 && (
          <button
            type="button"
            onClick={clearHistory}
            className="shrink-0 rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-xs font-semibold text-ink-700 shadow-sm transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700"
            title="Clear all messages in this conversation"
          >
            Clear conversation
          </button>
        )}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
        {/* Chat column */}
        <div className="flex h-[640px] min-h-[480px] flex-col rounded-2xl border border-ink-200/70 bg-white shadow-card">
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-5">
            {turns.length === 0 ? (
              <EmptyState onPick={send} />
            ) : (
              <ul className="space-y-4">
                {turns.map((turn, idx) => {
                  const isLatest = idx === turns.length - 1;
                  return (
                    <li key={idx}>
                      {turn.role === "user" && <UserBubble text={turn.text} />}
                      {turn.role === "assistant" && (
                        <AssistantBubble
                          response={turn.response}
                          isLatest={isLatest && !busy}
                          onQuickReply={send}
                        />
                      )}
                      {turn.role === "error" && (
                        <ErrorBubble text={turn.text} />
                      )}
                    </li>
                  );
                })}
                {busy && <ThinkingBubble />}
              </ul>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="flex items-center gap-2 border-t border-ink-100 p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about sessions, your agenda, or registrations…"
              disabled={busy}
              className="flex-1 rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-brand-400"
            >
              Send
            </button>
          </form>
        </div>

        {/* Side panel: latest trace summary */}
        <SidePanel turns={turns} />
      </div>

      <div className="h-16" />
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md">
        ✦
      </div>
      <h2 className="mt-4 text-xl font-semibold text-ink-900">
        Ask in natural language
      </h2>
      <p className="mt-1 max-w-md text-sm text-ink-600">
        The assistant uses Gemini function calling to chain real APIs:
        search → check capacity → register, all enforced by server-side policy.
      </p>
      <div className="mt-6 grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-lg border border-ink-200 bg-white px-3 py-2 text-left text-sm text-ink-700 shadow-sm transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-800"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
        {text}
      </div>
    </div>
  );
}

// ─────────────────── Tool-result → session extraction ───────────────────
type ExtractedSessions =
  | { kind: "search"; sessions: Session[] }
  | { kind: "detail"; session: Session }
  | { kind: "agenda"; items: { registration_id: string; session: Session }[] }
  | { kind: "registered"; session: Session; registration_id: string }
  | { kind: "cancelled"; session: Session };

function extractSessionsFromTrace(
  calls: ToolCallTrace[],
): ExtractedSessions | null {
  // Walk in reverse — the LATEST useful tool result wins.
  for (let i = calls.length - 1; i >= 0; i--) {
    const c = calls[i];
    if (!c.success || typeof c.result !== "object" || c.result === null)
      continue;
    const r = c.result as Record<string, unknown>;
    if (!r.ok) continue;

    if (c.tool_name === "register_session") {
      const reg = r.registration as Record<string, unknown> | undefined;
      const sessionId = (reg?.session_id ?? "") as string;
      const regId = (reg?.registration_id ?? "") as string;
      const session = findSessionInCalls(calls, sessionId);
      if (session && regId) {
        return { kind: "registered", session, registration_id: regId };
      }
    }
    if (c.tool_name === "cancel_registration") {
      const cancelled = r.cancelled as Record<string, unknown> | undefined;
      const sessionId = (cancelled?.session_id ?? "") as string;
      const session = findSessionInCalls(calls, sessionId);
      if (session) return { kind: "cancelled", session };
    }
    if (c.tool_name === "get_agenda") {
      const items = (r.items as Array<Record<string, unknown>> | undefined) ?? [];
      const parsed = items
        .map((it) => ({
          registration_id: (it.registration_id as string) ?? "",
          session: it.session as Session,
        }))
        .filter((it) => !!it.session);
      if (parsed.length > 0) return { kind: "agenda", items: parsed };
    }
    if (c.tool_name === "get_session_detail") {
      const s = r.session as Session | undefined;
      if (s) return { kind: "detail", session: s };
    }
    if (c.tool_name === "search_sessions") {
      const sessions = (r.sessions as Session[] | undefined) ?? [];
      if (sessions.length > 0) return { kind: "search", sessions };
    }
  }
  return null;
}

function findSessionInCalls(
  calls: ToolCallTrace[],
  sessionId: string,
): Session | null {
  if (!sessionId) return null;
  for (let i = calls.length - 1; i >= 0; i--) {
    const c = calls[i];
    if (!c.success || typeof c.result !== "object" || c.result === null)
      continue;
    const r = c.result as Record<string, unknown>;
    if (c.tool_name === "search_sessions") {
      const sessions = (r.sessions as Session[] | undefined) ?? [];
      const hit = sessions.find((s) => s.session_id === sessionId);
      if (hit) return hit;
    }
    if (c.tool_name === "get_session_detail") {
      const s = r.session as Session | undefined;
      if (s && s.session_id === sessionId) return s;
    }
    if (c.tool_name === "get_agenda") {
      const items = (r.items as Array<Record<string, unknown>> | undefined) ?? [];
      for (const it of items) {
        const s = it.session as Session | undefined;
        if (s && s.session_id === sessionId) return s;
      }
    }
  }
  return null;
}

// ─────────────────── Prose cleaning + minimal markdown ───────────────────
function cleanProse(text: string, hasCards: boolean): string {
  if (!text) return "";
  // When we render structured cards, drop the LLM's redundant bulleted
  // listing of the same sessions. Keep only lines that don't look like
  // bullets / list items / hyphen-prefixed S0XX entries.
  let lines = text.split(/\r?\n/);
  if (hasCards) {
    lines = lines.filter((raw) => {
      const l = raw.trim();
      if (!l) return true;
      // bullet variants
      if (/^[*•\-]\s+/.test(l)) return false;
      if (/^\d+\.\s+/.test(l)) return false;
      // standalone field labels the LLM sometimes drops
      if (/^(date|time|room|speaker|level|capacity)\s*[:：]/i.test(l))
        return false;
      // S0XX header lines without bullet
      if (/^\*\*S\d{2,}/i.test(l)) return false;
      return true;
    });
  }
  return lines
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function ProseText({ text }: { text: string }) {
  // Tiny markdown renderer: only **bold** and paragraph breaks.
  const paragraphs = text.split(/\n{2,}/);
  return (
    <>
      {paragraphs.map((p, i) => (
        <p key={i} className={i > 0 ? "mt-2 whitespace-pre-wrap" : "whitespace-pre-wrap"}>
          {renderInline(p)}
        </p>
      ))}
    </>
  );
}

function renderInline(text: string): React.ReactNode[] {
  // Split on **bold** while preserving the matched groups.
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    const m = part.match(/^\*\*([^*]+)\*\*$/);
    if (m) {
      return (
        <strong key={i} className="font-semibold text-ink-900">
          {m[1]}
        </strong>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

// ─────────────────── Card components ───────────────────
function AssistantSessionCards({ extracted }: { extracted: ExtractedSessions }) {
  if (extracted.kind === "search") {
    const list = extracted.sessions.slice(0, 8);
    const more = extracted.sessions.length - list.length;
    return (
      <div className="space-y-2">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">
          {extracted.sessions.length === 1
            ? "1 matching session"
            : `${extracted.sessions.length} matching sessions`}
        </div>
        <div className="grid grid-cols-1 gap-2">
          {list.map((s) => (
            <ChatSessionCard key={s.session_id} session={s} />
          ))}
        </div>
        {more > 0 && (
          <div className="text-xs text-ink-500">
            …and {more} more — ask me to narrow it down.
          </div>
        )}
      </div>
    );
  }
  if (extracted.kind === "detail") {
    return (
      <div className="space-y-2">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">
          Session
        </div>
        <ChatSessionCard session={extracted.session} expanded />
      </div>
    );
  }
  if (extracted.kind === "agenda") {
    return (
      <div className="space-y-2">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">
          Your agenda · {extracted.items.length}{" "}
          {extracted.items.length === 1 ? "session" : "sessions"}
        </div>
        <div className="grid grid-cols-1 gap-2">
          {extracted.items.map((it) => (
            <ChatSessionCard
              key={it.registration_id}
              session={it.session}
              registrationId={it.registration_id}
            />
          ))}
        </div>
      </div>
    );
  }
  if (extracted.kind === "registered") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
          <span>Registered</span>
          <span className="rounded-full bg-emerald-50 px-1.5 py-0.5 font-mono text-[10px] text-emerald-700 ring-1 ring-emerald-200">
            {extracted.registration_id}
          </span>
        </div>
        <ChatSessionCard
          session={extracted.session}
          registrationId={extracted.registration_id}
        />
      </div>
    );
  }
  // cancelled
  return (
    <div className="space-y-2">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-rose-700">
        Cancelled
      </div>
      <ChatSessionCard session={extracted.session} dimmed />
    </div>
  );
}

function ChatSessionCard({
  session,
  expanded,
  registrationId,
  dimmed,
}: {
  session: Session;
  expanded?: boolean;
  registrationId?: string;
  dimmed?: boolean;
}) {
  const status = capacityStatus(session);
  const remaining = Math.max(0, session.capacity - session.registered_count);
  const pct = Math.min(
    100,
    Math.round((session.registered_count / session.capacity) * 100),
  );
  return (
    <Link
      href={`/sessions/${session.session_id}`}
      className={
        "group block rounded-xl border bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md " +
        (dimmed
          ? "border-rose-200/60 opacity-70"
          : "border-ink-200/70 hover:border-brand-300")
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-700">
          {session.track}
        </span>
        <span
          className={
            "rounded-full px-2 py-0.5 text-[10px] font-semibold " +
            capacityClasses(status)
          }
        >
          {capacityLabel(status)}
        </span>
        <span
          className={
            "rounded-full px-2 py-0.5 text-[10px] font-medium " +
            levelClasses(session.level)
          }
        >
          {levelLabel(session.level)}
        </span>
        <span className="ml-auto font-mono text-[10px] text-ink-400">
          {session.session_id}
        </span>
      </div>

      <h4 className="mt-2 text-sm font-semibold leading-snug text-ink-900 group-hover:text-brand-700">
        {session.title}
      </h4>

      {expanded && session.description && (
        <p className="mt-1.5 line-clamp-3 text-xs text-ink-600">
          {session.description}
        </p>
      )}

      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-ink-700">
        <div>
          <dt className="text-[10px] uppercase tracking-wide text-ink-400">
            When
          </dt>
          <dd>
            {formatDateShort(session.date)}
            <span className="text-ink-400"> · </span>
            {formatTimeRange(session.start_time, session.end_time)}
          </dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-wide text-ink-400">
            Where
          </dt>
          <dd>{session.room}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-[10px] uppercase tracking-wide text-ink-400">
            Speaker
          </dt>
          <dd>
            {session.speaker}
            <span className="text-ink-400"> · </span>
            {session.company}
          </dd>
        </div>
      </dl>

      <div className="mt-2">
        <div className="h-1 w-full overflow-hidden rounded-full bg-ink-100">
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
        <div className="mt-1 flex justify-between text-[10px] text-ink-500">
          <span>
            {session.registered_count} / {session.capacity} registered
          </span>
          <span>
            {remaining > 0 ? `${remaining} seats left` : "No seats remaining"}
          </span>
        </div>
      </div>

      {registrationId && (
        <div className="mt-2 inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
          <span>Registration</span>
          <span className="font-mono">{registrationId}</span>
        </div>
      )}
    </Link>
  );
}

function ErrorBubble({ text }: { text: string }) {
  return (
    <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm text-rose-800">
      {text}
    </div>
  );
}

function ThinkingBubble() {
  return (
    <li className="flex items-center gap-2 text-sm text-ink-500">
      <span className="inline-flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-500 [animation-delay:-0.2s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-500 [animation-delay:-0.1s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-500" />
      </span>
      Thinking…
    </li>
  );
}

function AssistantBubble({
  response,
  isLatest,
  onQuickReply,
}: {
  response: ChatResponse;
  isLatest: boolean;
  onQuickReply: (text: string) => void;
}) {
  const [showTrace, setShowTrace] = useState(false);
  const status = response.status;
  const pendingAfter = response.pending_action_after ?? null;
  const extracted = extractSessionsFromTrace(response.tool_calls);
  const prose = cleanProse(response.final_answer, extracted !== null);
  return (
    <div className="space-y-2">
      <div className="max-w-[88%] rounded-2xl rounded-tl-sm border border-ink-200 bg-white px-4 py-3 text-sm text-ink-800 shadow-sm">
        <div className="mb-1 flex items-center gap-2">
          <span className="grid h-5 w-5 place-items-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-[10px] font-semibold text-white">
            ✦
          </span>
          <span className="text-xs font-semibold text-ink-500">Assistant</span>
          <StatusPill status={status} />
          {response.confirmation_detected && (
            <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-700 ring-1 ring-violet-200">
              confirmation handled
            </span>
          )}
        </div>
        {prose && (
          <div className="leading-relaxed">
            <ProseText text={prose} />
          </div>
        )}
      </div>

      {extracted && (
        <div className="max-w-[88%]">
          <AssistantSessionCards extracted={extracted} />
        </div>
      )}

      {isLatest && pendingAfter && (
        <PendingActionBanner
          pending={pendingAfter}
          onConfirm={() => onQuickReply("yes")}
          onDecline={() => onQuickReply("no")}
        />
      )}

      {response.policy_violations.length > 0 && (
        <ViolationsPanel violations={response.policy_violations} />
      )}

      {response.tool_calls.length > 0 && (
        <div className="max-w-[88%]">
          <button
            type="button"
            onClick={() => setShowTrace((v) => !v)}
            className="text-xs font-semibold text-brand-700 hover:text-brand-800"
          >
            {showTrace ? "Hide" : "Show"} tool trace ({response.tool_calls.length}{" "}
            call{response.tool_calls.length === 1 ? "" : "s"})
          </button>
          {showTrace && (
            <TracePanel
              calls={response.tool_calls}
              pendingBefore={response.pending_action_before ?? null}
              pendingAfter={response.pending_action_after ?? null}
              confirmationDetected={!!response.confirmation_detected}
            />
          )}
        </div>
      )}
      <div className="font-mono text-[10px] text-ink-400">
        {response.trace_id}
      </div>
    </div>
  );
}

function PendingActionBanner({
  pending,
  onConfirm,
  onDecline,
}: {
  pending: PendingAction;
  onConfirm: () => void;
  onDecline: () => void;
}) {
  const label = pending.session_title || pending.session_id;
  return (
    <div className="max-w-[88%] rounded-xl border border-violet-200 bg-violet-50 p-3">
      <div className="flex items-start gap-3">
        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-violet-600 text-[11px] font-semibold text-white">
          ?
        </div>
        <div className="flex-1 text-sm text-violet-900">
          <div className="font-semibold">Pending registration</div>
          <div className="mt-0.5 text-xs">
            Reply <span className="font-mono">yes</span> to register for{" "}
            <span className="font-semibold">{label}</span> ({pending.session_id})
            or <span className="font-mono">no</span> to drop it. Expires in ~
            {pending.expires_after_minutes} min.
          </div>
        </div>
      </div>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          onClick={onConfirm}
          className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-violet-700"
        >
          Yes, register me
        </button>
        <button
          type="button"
          onClick={onDecline}
          className="rounded-lg border border-violet-300 bg-white px-3 py-1.5 text-xs font-semibold text-violet-800 hover:bg-violet-100"
        >
          No, never mind
        </button>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: ChatResponse["status"] }) {
  const styles: Record<ChatResponse["status"], string> = {
    completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    clarification_needed: "bg-amber-50 text-amber-700 ring-amber-200",
    failed: "bg-rose-50 text-rose-700 ring-rose-200",
  };
  const label: Record<ChatResponse["status"], string> = {
    completed: "completed",
    clarification_needed: "needs clarification",
    failed: "failed",
  };
  return (
    <span
      className={
        "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 " +
        styles[status]
      }
    >
      {label[status]}
    </span>
  );
}

function ViolationsPanel({ violations }: { violations: PolicyViolation[] }) {
  return (
    <div className="max-w-[88%] rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs">
      <div className="mb-1 font-semibold text-amber-900">
        ⚠ Policy guardrails fired ({violations.length})
      </div>
      <ul className="space-y-1 text-amber-900">
        {violations.map((v, i) => (
          <li key={i}>
            <span className="font-mono">{v.rule}</span>
            {v.tool_name ? ` (on ${v.tool_name})` : ""} — {v.detail}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TracePanel({
  calls,
  pendingBefore,
  pendingAfter,
  confirmationDetected,
}: {
  calls: ToolCallTrace[];
  pendingBefore: PendingAction | null;
  pendingAfter: PendingAction | null;
  confirmationDetected: boolean;
}) {
  return (
    <div className="mt-2 space-y-2">
      <PendingStateRow
        before={pendingBefore}
        after={pendingAfter}
        confirmationDetected={confirmationDetected}
      />
      <ol className="space-y-2">
        {calls.map((c) => (
        <li
          key={c.step_number}
          className="rounded-xl border border-ink-200 bg-white p-3 shadow-sm"
        >
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="grid h-5 w-5 place-items-center rounded-full bg-ink-100 text-[10px] font-semibold text-ink-700">
              {c.step_number}
            </span>
            <span className="font-mono text-sm font-semibold text-ink-900">
              {c.tool_name}
            </span>
            <span
              className={
                "rounded-full px-1.5 py-0.5 text-[10px] font-semibold ring-1 " +
                (c.success
                  ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                  : "bg-rose-50 text-rose-700 ring-rose-200")
              }
            >
              {c.success ? "ok" : c.error || "failed"}
            </span>
            <span className="text-[10px] text-ink-400">{c.latency_ms}ms</span>
          </div>
          <details className="mt-2">
            <summary className="cursor-pointer text-[11px] text-ink-500 hover:text-ink-800">
              arguments
            </summary>
            <pre className="mt-1 overflow-x-auto rounded-md bg-ink-50 p-2 font-mono text-[11px] leading-snug text-ink-800">
              {JSON.stringify(c.arguments, null, 2)}
            </pre>
          </details>
          <details className="mt-1">
            <summary className="cursor-pointer text-[11px] text-ink-500 hover:text-ink-800">
              result
            </summary>
            <pre className="mt-1 max-h-64 overflow-x-auto overflow-y-auto rounded-md bg-ink-50 p-2 font-mono text-[11px] leading-snug text-ink-800">
              {JSON.stringify(c.result, null, 2)}
            </pre>
          </details>
        </li>
      ))}
      </ol>
    </div>
  );
}

function PendingStateRow({
  before,
  after,
  confirmationDetected,
}: {
  before: PendingAction | null;
  after: PendingAction | null;
  confirmationDetected: boolean;
}) {
  if (!before && !after && !confirmationDetected) return null;
  return (
    <div className="rounded-xl border border-violet-200 bg-violet-50/60 p-3 text-xs">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-semibold text-violet-900">
          Conversation state
        </span>
        {confirmationDetected && (
          <span className="rounded-full bg-violet-600 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
            confirmation_detected
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <PendingCell label="pending_action_before" value={before} />
        <PendingCell label="pending_action_after" value={after} />
      </div>
    </div>
  );
}

function PendingCell({
  label,
  value,
}: {
  label: string;
  value: PendingAction | null;
}) {
  return (
    <div className="rounded-md bg-white p-2 ring-1 ring-violet-100">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-violet-700">
        {label}
      </div>
      {value ? (
        <pre className="mt-1 overflow-x-auto font-mono text-[11px] leading-snug text-ink-800">
          {JSON.stringify(value, null, 2)}
        </pre>
      ) : (
        <div className="mt-1 font-mono text-[11px] text-ink-400">null</div>
      )}
    </div>
  );
}

function SidePanel({ turns }: { turns: Turn[] }) {
  const lastAssistant = [...turns]
    .reverse()
    .find((t) => t.role === "assistant") as
    | { role: "assistant"; response: ChatResponse }
    | undefined;
  const r = lastAssistant?.response;

  return (
    <aside className="hidden lg:block">
      <div className="sticky top-20 rounded-2xl border border-ink-200/70 bg-white p-4 shadow-card">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          Last turn
        </h3>
        {!r ? (
          <p className="mt-2 text-sm text-ink-500">
            Send a message to see the orchestrator trace.
          </p>
        ) : (
          <div className="mt-3 space-y-3 text-sm">
            <Stat label="Trace ID" value={r.trace_id} mono />
            <Stat label="Status" value={r.status} />
            <Stat
              label="Tool calls"
              value={String(r.tool_calls.length)}
            />
            <Stat
              label="Total latency"
              value={`${r.tool_calls.reduce((a, c) => a + c.latency_ms, 0)} ms`}
            />
            <Stat
              label="Policy violations"
              value={String(r.policy_violations.length)}
            />
            <Stat
              label="Confirmation"
              value={r.confirmation_detected ? "detected" : "—"}
            />
            <PendingSummary
              before={r.pending_action_before ?? null}
              after={r.pending_action_after ?? null}
            />
            {r.tool_calls.length > 0 && (
              <div>
                <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
                  Sequence
                </div>
                <ol className="space-y-1">
                  {r.tool_calls.map((c) => (
                    <li
                      key={c.step_number}
                      className="flex items-center gap-2 rounded-md bg-ink-50 px-2 py-1 text-xs"
                    >
                      <span className="font-mono text-ink-500">
                        {c.step_number}
                      </span>
                      <span className="font-mono text-ink-900">
                        {c.tool_name}
                      </span>
                      <span
                        className={
                          "ml-auto rounded-full px-1.5 py-0.5 text-[10px] font-semibold ring-1 " +
                          (c.success
                            ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                            : "bg-rose-50 text-rose-700 ring-rose-200")
                        }
                      >
                        {c.success ? "ok" : "fail"}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

function PendingSummary({
  before,
  after,
}: {
  before: PendingAction | null;
  after: PendingAction | null;
}) {
  if (!before && !after) {
    return (
      <Stat label="Pending action" value="none" />
    );
  }
  const fmt = (p: PendingAction | null) =>
    p ? `${p.session_id}${p.session_title ? ` · ${p.session_title}` : ""}` : "—";
  return (
    <div className="rounded-lg bg-violet-50 p-2 ring-1 ring-violet-200">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-violet-700">
        Pending action
      </div>
      <div className="mt-1 space-y-0.5 text-[11px] text-violet-900">
        <div>
          <span className="text-violet-500">before: </span>
          <span className="font-mono">{fmt(before)}</span>
        </div>
        <div>
          <span className="text-violet-500">after: </span>
          <span className="font-mono">{fmt(after)}</span>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-ink-500">{label}</span>
      <span
        className={
          "text-right text-sm text-ink-900 " +
          (mono ? "font-mono text-xs" : "font-medium")
        }
      >
        {value}
      </span>
    </div>
  );
}
