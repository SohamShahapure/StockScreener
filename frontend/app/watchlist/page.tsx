"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import WatchlistCard from "@/components/WatchlistCard";
import NewsList from "@/components/NewsList";
import SignIn from "@/components/SignIn";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { NewsArticleResponse, WatchlistSummaryItem } from "@/lib/types";

const REFRESH_INTERVAL_MS = 30_000;

export default function WatchlistPage() {
  const { username, loading: authLoading } = useAuth();
  const [items, setItems] = useState<WatchlistSummaryItem[]>([]);
  const [news, setNews] = useState<NewsArticleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [, setTick] = useState(0); // re-renders every 5s so "Updated Xs ago" stays live

  const load = useCallback(async (isBackground = false) => {
    if (isBackground) setRefreshing(true);
    try {
      const [summary, latestNews] = await Promise.all([
        api.getWatchlistSummary(),
        api.getWatchlistNews(15),
      ]);
      setItems(summary);
      setNews(latestNews);
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Only load (and poll) once we know who the user is - the endpoints are
  // per-user now and 401 without a token.
  useEffect(() => {
    if (authLoading || !username) {
      setLoading(false);
      return;
    }
    setLoading(true);
    load();
    const interval = setInterval(() => load(true), REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [authLoading, username, load]);

  useEffect(() => {
    const tickInterval = setInterval(() => setTick((t) => t + 1), 5000);
    return () => clearInterval(tickInterval);
  }, []);

  async function handleRemove(symbol: string) {
    setItems((prev) => prev.filter((i) => i.symbol !== symbol));
    try {
      await api.removeFromWatchlist(symbol);
    } finally {
      load(true); // resync summary + news either way, so a failed delete self-corrects
    }
  }

  function updatedLabel(): string {
    if (!lastUpdated) return "";
    const secs = Math.max(0, Math.floor((Date.now() - lastUpdated.getTime()) / 1000));
    if (secs < 5) return "Updated just now";
    if (secs < 60) return `Updated ${secs}s ago`;
    return `Updated ${Math.floor(secs / 60)}m ago`;
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-muted">
        <Loader2 size={18} className="animate-spin" />
      </div>
    );
  }

  if (!username) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-16">
        <h1 className="mb-2 text-center font-display text-2xl text-ink2">Your watchlist</h1>
        <p className="mx-auto mb-6 max-w-sm text-center text-sm text-muted">
          Sign in with a username so your tracked tickers, preferences, and AI insights stay yours every time you visit.
        </p>
        <SignIn heading="Sign in to your watchlist" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl text-ink2">Your watchlist</h1>
        {!loading && items.length > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted tabular">{updatedLabel()}</span>
            <button
              onClick={() => load(true)}
              disabled={refreshing}
              className="flex items-center gap-1.5 rounded-lg border border-ink-border bg-ink-surface px-3 py-1.5 text-xs font-medium text-ink2 transition-colors hover:border-brass/50 disabled:opacity-60"
            >
              <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 py-16 text-muted">
          <Loader2 size={18} className="animate-spin" /> Loading watchlist…
        </div>
      )}

      {!loading && items.length === 0 && (
        <div className="rounded-xl border border-ink-border bg-ink-surface px-6 py-16 text-center">
          <p className="font-display text-lg text-ink2">Nothing here yet</p>
          <p className="mt-1 text-sm text-muted">
            Search a stock on the Screener page and tap &quot;Add to watchlist&quot; to track it here.
          </p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <>
          <div className="mb-8 flex flex-col gap-3">
            {items.map((item) => (
              <WatchlistCard key={item.symbol} item={item} onRemove={() => handleRemove(item.symbol)} />
            ))}
          </div>

          <h2 className="mb-3 font-display text-lg text-ink2">Latest news across your watchlist</h2>
          {news.length === 0 ? (
            <p className="text-sm text-muted">No recent news for your tracked tickers yet.</p>
          ) : (
            <NewsList articles={news} showSymbol />
          )}
        </>
      )}
    </div>
  );
}
