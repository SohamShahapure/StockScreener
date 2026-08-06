"use client";

import { useEffect, useState } from "react";
import { Loader2, AlertCircle, ExternalLink, ArrowBigUp } from "lucide-react";
import { api } from "@/lib/api";
import { ApiError, SocialPostResponse, SocialSource } from "@/lib/types";
import { timeAgo } from "@/components/NewsList";
import { SentimentTag, KeywordChips } from "@/components/SentimentTag";

type PanelState = "loading" | "error" | "empty" | "ready";

export default function SocialPanel({ symbol }: { symbol: string }) {
  const [source, setSource] = useState<SocialSource>("reddit");
  const [state, setState] = useState<PanelState>("loading");
  const [posts, setPosts] = useState<SocialPostResponse[]>([]);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    let cancelled = false;
    setState("loading");

    api
      .getSocial(symbol, source)
      .then((data) => {
        if (cancelled) return;
        setPosts(data);
        setState(data.length === 0 ? "empty" : "ready");
      })
      .catch((e) => {
        if (cancelled) return;
        setErrorMsg(e instanceof ApiError ? e.message : "Couldn't load posts.");
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, source]);

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="inline-flex self-start rounded-lg border border-ink-border bg-ink-raised p-1">
        {(["reddit", "stocktwits"] as SocialSource[]).map((s) => (
          <button
            key={s}
            onClick={() => setSource(s)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
              source === s ? "bg-ink-surface text-brass" : "text-muted hover:text-ink2"
            }`}
          >
            {s === "stocktwits" ? "StockTwits" : "Reddit"}
          </button>
        ))}
      </div>

      {state === "loading" && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-10 text-muted">
          <Loader2 size={18} className="animate-spin" />
          <span className="text-sm">Loading {source} posts…</span>
        </div>
      )}

      {state === "error" && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-10 text-center">
          <AlertCircle size={18} className="text-loss" />
          <p className="text-sm text-ink2">Couldn&apos;t load {source} posts</p>
          <p className="max-w-xs text-xs text-muted">{errorMsg}</p>
        </div>
      )}

      {state === "empty" && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 py-10 text-center">
          <p className="text-sm text-ink2">No recent {source} posts found for {symbol}</p>
        </div>
      )}

      {state === "ready" && (
        <ul className="flex flex-col gap-3 overflow-y-auto scrollbar-thin">
          {posts.map((p) => (
            <li key={p.id}>
              <a
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col gap-1.5 rounded-lg border border-ink-border bg-ink-raised p-3 transition-colors hover:border-brass/50"
              >
                <span className="flex items-start justify-between gap-2 text-sm leading-snug text-ink2 group-hover:text-brass">
                  {p.content}
                  <ExternalLink size={13} className="mt-0.5 shrink-0 text-muted" />
                </span>
                <span className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
                  {p.author && <span>u/{p.author}</span>}
                  {p.score !== null && (
                    <span className="flex items-center gap-0.5">
                      <ArrowBigUp size={11} />
                      {p.score}
                    </span>
                  )}
                  {p.posted_at && <span className="tabular">{timeAgo(p.posted_at)}</span>}
                  <SentimentTag label={p.sentiment_label} />
                </span>
                <KeywordChips keywords={p.keywords} />
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
