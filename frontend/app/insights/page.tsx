"use client";

import { useState } from "react";
import { MessagesSquare } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import SocialPanel from "@/components/SocialPanel";

export default function InsightsPage() {
  const [symbol, setSymbol] = useState<string | null>(null);

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
      <h1 className="mb-2 font-display text-2xl text-ink2">Market insights</h1>
      <p className="mb-6 text-sm text-muted">
        Search a stock to see what Reddit and StockTwits are saying about it right now.
      </p>

      <div className="mb-6">
        <SearchBar onSelect={setSymbol} placeholder="Search a ticker — AAPL, Reliance, Tesla…" />
      </div>

      {!symbol ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-ink-border bg-ink-surface px-6 py-20 text-center">
          <MessagesSquare size={24} className="text-muted" />
          <p className="font-display text-lg text-ink2">Nothing selected yet</p>
          <p className="max-w-sm text-sm text-muted">
            Search a ticker above to pull up its Reddit and StockTwits sentiment.
          </p>
        </div>
      ) : (
        <div className="min-h-[420px] rounded-xl border border-ink-border bg-ink-surface p-4 shadow-panel">
          <div className="mb-3 font-mono text-sm text-brass tabular">{symbol}</div>
          <SocialPanel symbol={symbol} />
        </div>
      )}
    </div>
  );
}
