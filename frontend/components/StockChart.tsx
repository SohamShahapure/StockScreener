"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType, IChartApi } from "lightweight-charts";
import { PricePoint } from "@/lib/types";

export default function StockChart({ candles }: { candles: PricePoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8A93A6",
        fontFamily: "var(--font-mono)",
      },
      grid: {
        vertLines: { color: "#2A3345" },
        horzLines: { color: "#2A3345" },
      },
      rightPriceScale: { borderColor: "#2A3345" },
      timeScale: { borderColor: "#2A3345" },
      autoSize: true,
    });

    const series = chart.addCandlestickSeries({
      upColor: "#2DBE7E",
      downColor: "#E5484D",
      borderVisible: false,
      wickUpColor: "#2DBE7E",
      wickDownColor: "#E5484D",
    });

    series.setData(
      candles.map((c) => ({
        time: c.date,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    chart.timeScale().fitContent();
    chartRef.current = chart;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [candles]);

  return <div ref={containerRef} className="h-[320px] w-full sm:h-[420px]" />;
}
