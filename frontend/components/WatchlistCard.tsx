"use client";

import { useState } from "react";
import { Sparkles, X, TrendingUp, TrendingDown, AlertCircle } from "lucide-react";
import { WatchlistSummaryItem } from "@/lib/types";
import AIInsightChat from "@/components/AIInsightChat";

export default function WatchlistCard({
  item,
  onRemove,
}: {
  item: WatchlistSummaryItem;
  onRemove: () => void;
}) {
  const summary = item.summary;
  const bullish = summary?.indicators.trend_signal === "bullish";
  const bearish = summary?.indicators.trend_signal === "bearish";
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-ink-border bg-ink-surface p-4 shadow-panel">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="font-mono text-sm text-brass tabular">{item.symbol}</span>
        <span className="truncate text-xs text-muted">
          {summary?.company.name ?? (item.error ? "Unavailable right now" : "—")}
        </span>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {item.error ? (
          <span title={item.error} className="flex items-center gap-1 text-xs text-loss">
            <AlertCircle size={14} /> unavailable
          </span>
        ) : summary ? (
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm text-ink2 tabular">
              {summary.indicators.current_price?.toFixed(2) ?? "—"}
            </span>
            {bullish && <TrendingUp size={15} className="text-gain" />}
            {bearish && <TrendingDown size={15} className="text-loss" />}
          </div>
        ) : (
          <span className="text-xs text-muted">—</span>
        )}

        <button
          onClick={() => setChatOpen(true)}
          title={`Generate an AI insight for ${item.symbol}`}
          className="flex items-center gap-1.5 rounded-lg border border-brass/40 px-2.5 py-1.5 text-xs font-medium text-brass transition-colors hover:border-brass hover:bg-brass/10"
        >
          <Sparkles size={14} /> AI insight
        </button>

        <button
          onClick={onRemove}
          aria-label={`Remove ${item.symbol} from watchlist`}
          className="rounded-lg p-1.5 text-muted transition-colors hover:bg-loss/10 hover:text-loss"
        >
          <X size={16} />
        </button>
      </div>

      {chatOpen && <AIInsightChat symbol={item.symbol} onClose={() => setChatOpen(false)} />}
    </div>
  );
}
