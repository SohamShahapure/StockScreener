type SentimentLabel = "positive" | "negative" | "neutral" | null | undefined;

export function SentimentTag({ label }: { label: SentimentLabel }) {
  if (!label) return null;

  const styles =
    label === "positive"
      ? "bg-gain/10 text-gain"
      : label === "negative"
        ? "bg-loss/10 text-loss"
        : "bg-ink-border/60 text-muted";

  return <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium capitalize ${styles}`}>{label}</span>;
}

export function KeywordChips({ keywords }: { keywords: string[] | null | undefined }) {
  if (!keywords || keywords.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {keywords.slice(0, 4).map((k) => (
        <span key={k} className="rounded-full border border-ink-border px-2 py-0.5 text-[10px] text-muted">
          {k}
        </span>
      ))}
    </div>
  );
}
