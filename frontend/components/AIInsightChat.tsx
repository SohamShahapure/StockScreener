"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Sparkles, X, Send, Loader2, AlertCircle, RotateCw, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { AIInsightSource, ApiError, ChatMessage } from "@/lib/types";

type UiMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: AIInsightSource[];
};

const SUGGESTED = [
  "Why is the trend bullish or bearish?",
  "What do the fundamentals say?",
  "Summarize the news sentiment.",
];

export default function AIInsightChat({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [provider, setProvider] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const generate = useCallback(async () => {
    setInitializing(true);
    setError(null);
    try {
      const res = await api.generateInsight(symbol);
      setProvider(res.provider);
      setMessages([{ role: "assistant", content: res.insight, sources: res.sources }]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong generating the insight.");
    } finally {
      setInitializing(false);
    }
  }, [symbol]);

  // Kick off the grounded insight as soon as the chat opens.
  useEffect(() => {
    generate();
  }, [generate]);

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Auto-scroll to the newest message.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking, initializing]);

  async function send(text: string) {
    const question = text.trim();
    if (!question || thinking || initializing) return;

    const nextMessages: UiMessage[] = [...messages, { role: "user", content: question }];
    setMessages(nextMessages);
    setInput("");
    setThinking(true);
    setError(null);

    // Send the full running conversation so the model has the thread context;
    // the backend re-grounds every turn in the symbol's knowledge base.
    const history: ChatMessage[] = nextMessages.map((m) => ({ role: m.role, content: m.content }));
    try {
      const res = await api.chatInsight(symbol, history);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply, sources: res.sources }]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Try again.");
    } finally {
      setThinking(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`AI insight for ${symbol}`}
    >
      <div
        className="flex h-[88vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl border border-ink-border bg-ink-surface shadow-panel sm:h-[80vh] sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-3 border-b border-ink-border px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brass/10 text-brass">
              <Sparkles size={16} />
            </span>
            <div className="flex flex-col">
              <span className="font-display text-sm text-ink2">
                AI Insight · <span className="font-mono text-brass">{symbol}</span>
              </span>
              <span className="text-[11px] text-muted">
                {provider ? `Grounded RAG · ${provider}` : "Retrieval-augmented analysis"}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close AI insight"
            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-ink-raised hover:text-ink2"
          >
            <X size={18} />
          </button>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {initializing && (
            <div className="flex flex-col gap-1.5 text-sm text-muted">
              <div className="flex items-center gap-2">
                <Loader2 size={16} className="animate-spin text-brass" />
                Reading fundamentals, EMA trend, news &amp; sentiment for {symbol}…
              </div>
              <span className="pl-6 text-[11px] text-muted/80">
                The first analysis after starting the app runs a local model and can take a
                couple of minutes — later ones are much faster.
              </span>
            </div>
          )}

          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} />
          ))}

          {thinking && (
            <div className="flex items-center gap-2 text-sm text-muted">
              <Loader2 size={16} className="animate-spin text-brass" /> Thinking…
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-loss/40 bg-loss/10 px-3 py-2 text-sm text-loss">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <div className="flex-1">
                <p>{error}</p>
                {messages.length === 0 && (
                  <button
                    onClick={generate}
                    className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-loss/40 px-2 py-1 text-xs font-medium text-loss transition-colors hover:bg-loss/10"
                  >
                    <RotateCw size={12} /> Retry
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Suggested follow-ups, only before the user has asked anything */}
          {!initializing && !error && messages.length === 1 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-ink-border bg-ink-raised px-3 py-1.5 text-xs text-ink2 transition-colors hover:border-brass/50 hover:text-brass"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Composer */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex items-center gap-2 border-t border-ink-border px-3 py-3"
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={initializing}
            placeholder={initializing ? "Preparing analysis…" : `Ask about ${symbol}…`}
            className="flex-1 rounded-lg border border-ink-border bg-ink px-3 py-2.5 text-sm text-ink2 placeholder:text-muted focus:border-brass/60 focus:outline-none disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={initializing || thinking || !input.trim()}
            aria-label="Send"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brass text-ink transition-colors hover:bg-brass-bright disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: UiMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "rounded-br-sm bg-brass/15 text-ink2"
            : "rounded-bl-sm border border-ink-border bg-ink-raised text-ink2"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.sources && message.sources.length > 0 && <Sources sources={message.sources} />}
      </div>
    </div>
  );
}

function Sources({ sources }: { sources: AIInsightSource[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2 border-t border-ink-border pt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-[11px] font-medium text-muted transition-colors hover:text-brass"
      >
        <ChevronDown size={12} className={`transition-transform ${open ? "rotate-180" : ""}`} />
        Grounded in {sources.length} source{sources.length === 1 ? "" : "s"}
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5">
          {sources.map((s, i) => (
            <li key={i} className="rounded-md bg-ink px-2 py-1.5 text-[11px] text-muted">
              {s.doc_type && (
                <span className="mr-1.5 rounded bg-ink-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-brass">
                  {s.doc_type}
                </span>
              )}
              {s.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
