"use client";

import { useState } from "react";
import { LogIn, Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/types";

export default function SignIn({ heading = "Sign in to continue", subtext }: { heading?: string; subtext?: string }) {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), passphrase.trim() || undefined);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't sign in. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm rounded-xl border border-ink-border bg-ink-surface p-6 shadow-panel">
      <h2 className="font-display text-lg text-ink2">{heading}</h2>
      <p className="mt-1 text-sm text-muted">
        {subtext ?? "Pick any username to keep your watchlist yours. New name = new account. A passphrase is optional but protects your name."}
      </p>

      <form onSubmit={submit} className="mt-4 flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-xs text-muted">
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            maxLength={40}
            placeholder="e.g. soham"
            className="rounded-lg border border-ink-border bg-ink px-3 py-2.5 text-sm text-ink2 placeholder:text-muted focus:border-brass/60 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted">
          Passphrase <span className="text-muted/70">(optional)</span>
          <input
            type="password"
            value={passphrase}
            onChange={(e) => setPassphrase(e.target.value)}
            placeholder="leave blank for a quick open account"
            className="rounded-lg border border-ink-border bg-ink px-3 py-2.5 text-sm text-ink2 placeholder:text-muted focus:border-brass/60 focus:outline-none"
          />
        </label>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-loss/40 bg-loss/10 px-3 py-2 text-xs text-loss">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={busy || !username.trim()}
          className="flex items-center justify-center gap-2 rounded-lg bg-brass px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-brass-bright disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />}
          Continue
        </button>
      </form>
    </div>
  );
}
