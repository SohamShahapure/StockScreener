"use client";

const SAMPLE = [
  "AAPL 231.40 +1.2%",
  "TSLA 248.91 -0.8%",
  "RELIANCE.NS 2,948 +0.4%",
  "TCS.NS 4,120 +0.6%",
  "NVDA 128.75 +2.1%",
  "MSFT 468.20 +0.3%",
  "INFY.NS 1,845 -0.2%",
  "HDFCBANK.NS 1,712 +0.5%",
];

export default function TickerTape() {
  const row = [...SAMPLE, ...SAMPLE]; // duplicated for a seamless loop

  return (
    <div
      aria-hidden="true"
      className="relative overflow-hidden border-y border-ink-border bg-ink-surface/60 py-2"
    >
      <div className="flex w-max animate-[marquee_32s_linear_infinite] gap-8 whitespace-nowrap px-4">
        {row.map((item, i) => {
          const isUp = item.includes("+");
          return (
            <span key={i} className="font-mono text-xs tabular text-muted">
              {item.split(" ")[0]}{" "}
              <span className="text-ink2">{item.split(" ")[1]}</span>{" "}
              <span className={isUp ? "text-gain" : "text-loss"}>{item.split(" ")[2]}</span>
            </span>
          );
        })}
      </div>
      <style>{`
        @keyframes marquee {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
}
