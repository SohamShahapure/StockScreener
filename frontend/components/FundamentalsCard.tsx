import { CompanyInfo } from "@/lib/types";

function fmtCap(n: number | null) {
  if (n === null) return "—";
  if (n >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  return n.toLocaleString();
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] uppercase tracking-wide text-muted">{label}</span>
      <span className="font-mono text-sm text-ink2 tabular">{value}</span>
    </div>
  );
}

export default function FundamentalsCard({ info }: { info: CompanyInfo }) {
  return (
    <div className="rounded-xl border border-ink-border bg-ink-surface p-4 shadow-panel">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="font-display text-base text-ink2">{info.name ?? info.symbol}</h2>
        <span className="text-xs text-muted">{info.sector ?? "—"}</span>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Stat label="Market cap" value={info.currency ? `${info.currency} ${fmtCap(info.market_cap)}` : fmtCap(info.market_cap)} />
        <Stat label="P/E ratio" value={info.pe_ratio?.toFixed(2) ?? "—"} />
        <Stat label="EPS" value={info.eps?.toFixed(2) ?? "—"} />
        <Stat label="Dividend yield" value={info.dividend_yield ? `${(info.dividend_yield * 100).toFixed(2)}%` : "—"} />
        <Stat label="52w high" value={info.fifty_two_week_high?.toFixed(2) ?? "—"} />
        <Stat label="52w low" value={info.fifty_two_week_low?.toFixed(2) ?? "—"} />
      </div>
    </div>
  );
}
