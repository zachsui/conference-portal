"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  ChatResponse,
  PendingAction,
  PolicyViolation,
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

export default function AssistantPage() {
  const { attendee, ready } = useAuth();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
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
    setInput("");
    setTurns((prev) => [...prev, { role: "user", text: message }]);
    setBusy(true);
    try {
      const res = await api.chatWithAgent(attendee.attendee_id, message);
      setTurns((prev) => [...prev, { role: "assistant", response: res }]);
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        { role: "error", text: apiErrorMessage(err) },
      ]);
    } finally {
      setBusy(false);
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
      <div className="mt-8 flex items-end justify-between">
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
            .
          </p>
        </div>
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
        <div className="whitespace-pre-wrap leading-relaxed">
          {response.final_answer}
        </div>
      </div>

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
