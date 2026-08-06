import { ExternalLink } from "lucide-react";
import { NewsArticleResponse } from "@/lib/types";
import { SentimentTag, KeywordChips } from "@/components/SentimentTag";

export function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function NewsList({
  articles,
  showSymbol = false,
}: {
  articles: NewsArticleResponse[];
  showSymbol?: boolean;
}) {
  return (
    <ul className="flex flex-col gap-3">
      {articles.map((a) => (
        <li key={a.id}>
          <a
            href={a.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex flex-col gap-1.5 rounded-lg border border-ink-border bg-ink-raised p-3 transition-colors hover:border-brass/50"
          >
            <span className="flex items-start justify-between gap-2 text-sm leading-snug text-ink2 group-hover:text-brass">
              {a.title}
              <ExternalLink size={13} className="mt-0.5 shrink-0 text-muted" />
            </span>
            <span className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
              {showSymbol && <span className="font-mono text-brass tabular">{a.symbol}</span>}
              {showSymbol && (a.source || a.published_at) && <span>·</span>}
              {a.source && <span>{a.source}</span>}
              {a.source && a.published_at && <span>·</span>}
              {a.published_at && <span className="tabular">{timeAgo(a.published_at)}</span>}
              <SentimentTag label={a.sentiment_label} />
            </span>
            <KeywordChips keywords={a.keywords} />
          </a>
        </li>
      ))}
    </ul>
  );
}
