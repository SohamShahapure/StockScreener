"use client";

import { useEffect, useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { ApiError, NewsArticleResponse } from "@/lib/types";
import NewsList from "@/components/NewsList";

type PanelState = "loading" | "error" | "empty" | "ready";

export default function NewsPanel({ symbol }: { symbol: string }) {
  const [state, setState] = useState<PanelState>("loading");
  const [articles, setArticles] = useState<NewsArticleResponse[]>([]);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    let cancelled = false;
    setState("loading");

    api
      .getNews(symbol)
      .then((data) => {
        if (cancelled) return;
        setArticles(data);
        setState(data.length === 0 ? "empty" : "ready");
      })
      .catch((e) => {
        if (cancelled) return;
        setErrorMsg(e instanceof ApiError ? e.message : "Couldn't load news.");
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [symbol]);

  if (state === "loading") {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-10 text-muted">
        <Loader2 size={18} className="animate-spin" />
        <span className="text-sm">Loading news…</span>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="flex flex-col items-center gap-2 py-10 text-center">
        <AlertCircle size={18} className="text-loss" />
        <p className="text-sm text-ink2">Couldn&apos;t load news</p>
        <p className="max-w-xs text-xs text-muted">{errorMsg}</p>
      </div>
    );
  }

  if (state === "empty") {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
        <p className="text-sm text-ink2">No recent news found for {symbol}</p>
      </div>
    );
  }

  return <NewsList articles={articles} />;
}
