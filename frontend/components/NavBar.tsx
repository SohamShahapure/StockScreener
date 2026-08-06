"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LineChart, ListChecks, MessagesSquare, User, LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/", label: "Screener", icon: LineChart },
  { href: "/watchlist", label: "Watchlist", icon: ListChecks },
  { href: "/insights", label: "Insights", icon: MessagesSquare },
];

export default function NavBar() {
  const pathname = usePathname();
  const { username, logout, loading } = useAuth();

  return (
    <>
      {/* Desktop / tablet top bar */}
      <header className="hidden sm:flex sticky top-0 z-40 items-center justify-between border-b border-ink-border bg-ink/90 backdrop-blur px-6 py-3">
        <Link href="/" className="flex items-center gap-2 font-display text-lg tracking-tight text-ink2">
          <span className="text-brass">◆</span> Ticker<span className="text-brass">Boom</span>
        </Link>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active ? "bg-ink-raised text-brass" : "text-muted hover:text-ink2 hover:bg-ink-surface"
                }`}
              >
                <Icon size={16} strokeWidth={2} />
                {label}
              </Link>
            );
          })}

          <div className="ml-2 border-l border-ink-border pl-2">
            {!loading && username ? (
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1.5 rounded-lg bg-ink-raised px-2.5 py-1.5 text-xs font-medium text-ink2">
                  <User size={13} className="text-brass" />
                  {username}
                </span>
                <button
                  onClick={logout}
                  title="Sign out"
                  aria-label="Sign out"
                  className="rounded-lg p-1.5 text-muted transition-colors hover:bg-loss/10 hover:text-loss"
                >
                  <LogOut size={15} />
                </button>
              </div>
            ) : (
              <Link
                href="/watchlist"
                className="flex items-center gap-1.5 rounded-lg border border-brass/40 px-2.5 py-1.5 text-xs font-medium text-brass transition-colors hover:bg-brass/10"
              >
                <User size={13} /> Sign in
              </Link>
            )}
          </div>
        </nav>
      </header>

      {/* Mobile bottom tab bar */}
      <nav
        className="sm:hidden fixed bottom-0 left-0 right-0 z-40 flex items-stretch border-t border-ink-border bg-ink-surface/95 backdrop-blur pb-[env(safe-area-inset-bottom)]"
        aria-label="Primary"
      >
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium ${
                active ? "text-brass" : "text-muted"
              }`}
            >
              <Icon size={20} strokeWidth={active ? 2.5 : 2} />
              {label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
