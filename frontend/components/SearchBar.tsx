"use client";

import { useEffect, useRef, useState } from "react";
import { Search, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { TickerSearchResult } from "@/lib/types";

export default function SearchBar({
  onSelect,
  placeholder = "Search a ticker or company — AAPL, Reliance, Tesla…",
}: {
  onSelect: (symbol: string) => void;
  placeholder?: string;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TickerSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.trim().length === 0) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    const handle = setTimeout(async () => {
      try {
        const data = await api.searchTickers(query);
        setResults(data);
        setOpen(true);
        setActiveIndex(-1);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250); // debounce so we don't fire a request per keystroke

    return () => clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function selectResult(symbol: string) {
    onSelect(symbol);
    setQuery("");
    setResults([]);
    setOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      selectResult(results[activeIndex].symbol);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-xl">
      <div className="flex items-center gap-2 rounded-xl border border-ink-border bg-ink-surface px-4 py-3 shadow-panel focus-within:ring-2 focus-within:ring-brass">
        <Search size={18} className="text-muted shrink-0" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder={placeholder}
          className="w-full bg-transparent text-sm text-ink2 placeholder:text-muted focus:outline-none"
          aria-label="Search stocks"
          aria-autocomplete="list"
        />
        {loading && <Loader2 size={16} className="animate-spin text-muted shrink-0" />}
      </div>

      {open && results.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-30 mt-2 w-full overflow-hidden rounded-xl border border-ink-border bg-ink-raised shadow-panel"
        >
          {results.map((r, i) => (
            <li key={r.symbol}>
              <button
                role="option"
                aria-selected={i === activeIndex}
                onClick={() => selectResult(r.symbol)}
                onMouseEnter={() => setActiveIndex(i)}
                className={`flex w-full items-center justify-between px-4 py-2.5 text-left text-sm transition-colors ${
                  i === activeIndex ? "bg-ink-surface" : ""
                }`}
              >
                <span>
                  <span className="font-mono text-brass tabular">{r.symbol}</span>
                  <span className="ml-2 text-muted">{r.name}</span>
                </span>
                <span className="text-xs uppercase text-muted">{r.exchange}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
