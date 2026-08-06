"use client";

import { useState } from "react";
import { Newspaper, MessagesSquare } from "lucide-react";
import NewsPanel from "@/components/NewsPanel";
import SocialPanel from "@/components/SocialPanel";

type Tab = "news" | "insights";

export default function RightPanelTabs({ symbol }: { symbol: string }) {
  const [tab, setTab] = useState<Tab>("news");

  return (
    <div className="flex h-full flex-col rounded-xl border border-ink-border bg-ink-surface shadow-panel">
      <div className="flex border-b border-ink-border">
        <TabButton active={tab === "news"} onClick={() => setTab("news")} icon={Newspaper} label="News" />
        <TabButton active={tab === "insights"} onClick={() => setTab("insights")} icon={MessagesSquare} label="Market insights" />
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-4">
        {tab === "news" ? <NewsPanel symbol={symbol} /> : <SocialPanel symbol={symbol} />}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Newspaper;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-1 items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${
        active ? "text-brass border-b-2 border-brass" : "text-muted hover:text-ink2"
      }`}
    >
      <Icon size={15} />
      {label}
    </button>
  );
}
