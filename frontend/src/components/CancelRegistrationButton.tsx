"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { api, apiErrorMessage } from "@/lib/api";

interface Props {
  registrationId: string;
  onCancelled?: () => void | Promise<void>;
}

export function CancelRegistrationButton({
  registrationId,
  onCancelled,
}: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCancel() {
    setBusy(true);
    setError(null);
    try {
      await api.cancelRegistration(registrationId);
      if (onCancelled) {
        await onCancelled();
      }
      startTransition(() => router.refresh());
    } catch (err) {
      setError(apiErrorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleCancel}
        disabled={busy || isPending}
        className="rounded-md border border-ink-200 bg-white px-3 py-1.5 text-xs font-semibold text-ink-700 shadow-sm transition hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busy || isPending ? "Cancelling…" : "Cancel"}
      </button>
      {error && <span className="text-xs text-rose-700">{error}</span>}
    </div>
  );
}
