"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, Check, Loader2, AlertCircle, LogIn } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import TickerTape from "@/components/TickerTape";
import StockChart from "@/components/StockChart";
import FundamentalsCard from "@/components/FundamentalsCard";
import IndicatorBadges from "@/components/IndicatorBadges";
import RightPanelTabs from "@/components/RightPanelTabs";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ApiError, CompanyInfo, IndicatorsResponse, PricePoint } from "@/lib/types";

type LoadState = "idle" | "loading" | "error" | "ready";

export default function HomePage() {
  const { username } = useAuth();
  const [symbol, setSymbol] = useState<string | null>(null);
  const [state, setState] = useState<LoadState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [candles, setCandles] = useState<PricePoint[]>([]);
  const [info, setInfo] = useState<CompanyInfo | null>(null);
  const [indicators, setIndicators] = useState<IndicatorsResponse | null>(null);
  const [watchlistState, setWatchlistState] = useState<"idle" | "adding" | "added">("idle");

  async function handleSelect(ticker: string) {
    setSymbol(ticker);
    setState("loading");
    setWatchlistState("idle");

    // Fetch independently: the chart (history) is the core view, so one
    // rate-limited fundamentals/indicators call from Yahoo must never blank
    // the whole page. We render as long as the chart loads and just mark the
    // other panels unavailable if they failed.
    const [historyRes, infoRes, indRes] = await Promise.allSettled([
      api.getHistory(ticker, "1y", "1d"),
      api.getInfo(ticker),
      api.getIndicators(ticker),
    ]);

    if (historyRes.status === "fulfilled") {
      setCandles(historyRes.value.candles);
      setInfo(infoRes.status === "fulfilled" ? infoRes.value : null);
      setIndicators(indRes.status === "fulfilled" ? indRes.value : null);
      setState("ready");
    } else {
      const reason = historyRes.reason;
      setErrorMsg(reason instanceof ApiError ? reason.message : "Something went wrong loading that stock.");
      setState("error");
    }
  }

  async function handleAddToWatchlist() {
    if (!symbol) return;
    setWatchlistState("adding");
    try {
      await api.addToWatchlist(symbol);
      setWatchlistState("added");
    } catch {
      setWatchlistState("idle");
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
      <div className="mb-6 flex flex-col items-start gap-4 sm:mb-8">
        <h1 className="font-display text-2xl text-ink2 sm:text-3xl">
          Search any stock, read the tape.
        </h1>
        <SearchBar onSelect={handleSelect} />
      </div>

      {state === "idle" && (
        <div className="overflow-hidden rounded-xl border border-ink-border">
          <TickerTape />
          <div className="flex flex-col items-center justify-center gap-2 bg-ink-surface px-6 py-16 text-center">
            <p className="font-display text-lg text-ink2">Nothing pulled up yet</p>
            <p className="max-w-sm text-sm text-muted">
              Search a ticker above — try AAPL, TSLA, or RELIANCE.NS — to see its chart, fundamentals, and trend read.
            </p>
          </div>
        </div>
      )}

      {state === "loading" && (
        <div className="flex items-center justify-center gap-2 rounded-xl border border-ink-border bg-ink-surface py-24 text-muted">
          <Loader2 size={18} className="animate-spin" />
          Loading {symbol}…
        </div>
      )}

      {state === "error" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-loss/30 bg-loss/5 py-16 text-center">
          <AlertCircle size={20} className="text-loss" />
          <p className="text-sm text-ink2">Couldn&apos;t load {symbol}</p>
          <p className="text-xs text-muted">{errorMsg}</p>
        </div>
      )}

      {state === "ready" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="flex flex-col gap-4 lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              {indicators ? (
                <IndicatorBadges indicators={indicators} />
              ) : (
                <span className="text-xs text-muted">Trend read unavailable (data provider rate-limited — try again shortly)</span>
              )}
              {username ? (
                <button
                  onClick={handleAddToWatchlist}
                  disabled={watchlistState !== "idle"}
                  className="flex items-center gap-2 rounded-xl border border-ink-border bg-ink-surface px-4 py-3 text-sm font-medium text-ink2 transition-colors hover:border-brass/50 disabled:opacity-70"
                >
                  {watchlistState === "added" ? (
                    <>
                      <Check size={16} className="text-gain" /> Added
                    </>
                  ) : watchlistState === "adding" ? (
                    <>
                      <Loader2 size={16} className="animate-spin" /> Adding…
                    </>
                  ) : (
                    <>
                      <Plus size={16} /> Add to watchlist
                    </>
                  )}
                </button>
              ) : (
                <Link
                  href="/watchlist"
                  title="Sign in to save stocks to your watchlist"
                  className="flex items-center gap-2 rounded-xl border border-brass/40 px-4 py-3 text-sm font-medium text-brass transition-colors hover:bg-brass/10"
                >
                  <LogIn size={16} /> Sign in to save
                </Link>
              )}
            </div>

            <div className="rounded-xl border border-ink-border bg-ink-surface p-3 shadow-panel">
              <StockChart candles={candles} />
            </div>

            {info ? (
              <FundamentalsCard info={info} />
            ) : (
              <div className="flex items-center gap-2 rounded-xl border border-ink-border bg-ink-surface px-4 py-4 text-xs text-muted">
                <AlertCircle size={14} className="text-loss" />
                Fundamentals unavailable right now — Yahoo rate-limited this request. The chart above is live; try again in a moment for company details.
              </div>
            )}
          </div>

          <div className="lg:col-span-1">
            <div className="h-[400px] lg:h-full lg:min-h-[600px]">
              <RightPanelTabs symbol={symbol!} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
