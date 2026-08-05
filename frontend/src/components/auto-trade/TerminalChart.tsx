import { useEffect, useRef } from "react";
import { echarts } from "@/lib/echarts";
import type { Mt5Bar } from "@/lib/trading-terminal-api";

export function TerminalChart({ bars, symbol, timeframe }: { bars: Mt5Bar[]; symbol: string; timeframe: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      backgroundColor: "transparent",
      animationDuration: 220,
      tooltip: { trigger: "axis", axisPointer: { type: "cross" }, backgroundColor: "#111827", borderColor: "#334155", textStyle: { color: "#e2e8f0" } },
      grid: { left: 14, right: 54, top: 18, bottom: 24, containLabel: true },
      xAxis: { type: "category", data: bars.map((bar) => new Date(bar.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })), axisLabel: { color: "#64748b", fontSize: 9 }, axisLine: { lineStyle: { color: "#263244" } } },
      yAxis: { scale: true, position: "right", axisLabel: { color: "#94a3b8", fontSize: 9 }, splitLine: { lineStyle: { color: "#1f293755" } } },
      dataZoom: [{ type: "inside", start: 0, end: 100 }],
      series: [{ name: `${symbol} ${timeframe}`, type: "candlestick", data: bars.map((bar) => [bar.open, bar.close, bar.low, bar.high]), itemStyle: { color: "#26c6a5", color0: "#f05b78", borderColor: "#26c6a5", borderColor0: "#f05b78" }, markArea: { silent: true, data: [[{ xAxis: 0, itemStyle: { color: "#7c2d1222" } }, { xAxis: Math.floor(bars.length / 3) }], [{ xAxis: Math.floor(bars.length / 3), itemStyle: { color: "#854d0e22" } }, { xAxis: Math.floor(bars.length * 2 / 3) }], [{ xAxis: Math.floor(bars.length * 2 / 3), itemStyle: { color: "#1e3a8a22" } }, { xAxis: bars.length - 1 }]] } }],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [bars, symbol, timeframe]);
  return <div ref={ref} className="h-full min-h-[260px] w-full" aria-label={`${symbol} ${timeframe} candlestick chart`} />;
}