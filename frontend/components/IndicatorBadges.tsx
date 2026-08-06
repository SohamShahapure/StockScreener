import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { IndicatorsResponse } from "@/lib/types";

export default function IndicatorBadges({ indicators }: { indicators: IndicatorsResponse }) {
  const { current_price, ema50, ema200, trend_signal } = indicators;
  const bullish = trend_signal === "bullish";
  const bearish = trend_signal === "bearish";

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-baseline gap-2 rounded-xl border border-ink-border bg-ink-surface px-4 py-3">
        <span className="text-[11px] uppercase tracking-wide text-muted">Price</span>
        <span className="font-mono text-lg text-ink2 tabular">{current_price?.toFixed(2) ?? "—"}</span>
      </div>

      <div className="flex items-baseline gap-2 rounded-xl border border-ink-border bg-ink-surface px-4 py-3">
        <span className="text-[11px] uppercase tracking-wide text-muted">EMA 50</span>
        <span className="font-mono text-sm text-ink2 tabular">{ema50?.toFixed(2) ?? "—"}</span>
      </div>

      <div className="flex items-baseline gap-2 rounded-xl border border-ink-border bg-ink-surface px-4 py-3">
        <span className="text-[11px] uppercase tracking-wide text-muted">EMA 200</span>
        <span className="font-mono text-sm text-ink2 tabular">{ema200?.toFixed(2) ?? "—"}</span>
      </div>

      {trend_signal && (
        <div
          className={`flex items-center gap-1.5 rounded-xl px-4 py-3 text-sm font-medium ${
            bullish ? "bg-gain/10 text-gain" : bearish ? "bg-loss/10 text-loss" : "bg-ink-surface text-muted"
          }`}
        >
          {bullish ? <TrendingUp size={16} /> : bearish ? <TrendingDown size={16} /> : <Minus size={16} />}
          {bullish ? "Bullish (golden cross)" : bearish ? "Bearish" : "Neutral"}
        </div>
      )}
    </div>
  );
}
