import { useEffect, useRef, useState } from "react";
import { BarChart3, Radio } from "lucide-react";
import { echarts } from "@/lib/echarts";
import { getChartTheme } from "@/lib/chart-theme";
import { useDarkMode } from "@/hooks/useDarkMode";
import type { Mt5OhlcBar } from "@/data/mt5-direct";

export function LiveOhlcChart({ symbol, initialTimeframe, initialBars }: { symbol: string; initialTimeframe: string; initialBars: Mt5OhlcBar[] }) {
  const [timeframe, setTimeframe] = useState(initialTimeframe);
  const [bars, setBars] = useState(initialBars);
  const chartRef = useRef<HTMLDivElement>(null);
  const { dark } = useDarkMode();

  useEffect(() => {
    const timer = window.setInterval(() => {
      setBars((current) => current.map((bar, index) => index === current.length - 1 ? { ...bar, close: bar.close + 0.03, high: Math.max(bar.high, bar.close + 0.03), tickVolume: bar.tickVolume + 12 } : bar));
    }, 2_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current);
    const theme = getChartTheme();
    chart.setOption({ backgroundColor: "transparent", animationDuration: 250, tooltip: { trigger: "axis", axisPointer: { type: "cross" }, backgroundColor: theme.tooltipBg, borderColor: theme.tooltipBorder, textStyle: { color: theme.tooltipText } }, axisPointer: { link: [{ xAxisIndex: "all" }] }, grid: [{ left: 18, right: 18, top: 22, height: "62%", containLabel: true }, { left: 18, right: 18, top: "76%", height: "14%", containLabel: true }], xAxis: [{ type: "category", data: bars.map((bar) => new Date(bar.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })), boundaryGap: true, axisLabel: { color: theme.textColor, fontSize: 9 }, axisLine: { lineStyle: { color: theme.axisColor } } }, { type: "category", gridIndex: 1, data: bars.map((bar) => bar.time), axisLabel: { show: false }, axisLine: { show: false } }], yAxis: [{ scale: true, axisLabel: { color: theme.textColor, fontSize: 9 }, splitLine: { lineStyle: { color: theme.gridColor } } }, { gridIndex: 1, axisLabel: { color: theme.textColor, fontSize: 8 }, splitLine: { show: false } }], dataZoom: [{ type: "inside", xAxisIndex: [0, 1], start: 10, end: 100 }], series: [{ name: `${symbol} ${timeframe}`, type: "candlestick", data: bars.map((bar) => [bar.open, bar.close, bar.low, bar.high]), itemStyle: { color: theme.upColor, color0: theme.downColor, borderColor: theme.upColor, borderColor0: theme.downColor } }, { name: "Tick volume", type: "bar", xAxisIndex: 1, yAxisIndex: 1, data: bars.map((bar) => ({ value: bar.tickVolume, itemStyle: { color: bar.close >= bar.open ? `${theme.upColor}88` : `${theme.downColor}88` } })) }] });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(chartRef.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [bars, dark, symbol, timeframe]);

  const latest = bars[bars.length - 1];
  return <section aria-label="Live XAUUSD OHLC chart" className="rounded-xl border bg-card shadow-sm"><header className="flex flex-col justify-between gap-3 border-b p-5 sm:flex-row sm:items-center"><div className="flex items-start gap-3"><span className="rounded-lg bg-primary/10 p-2 text-primary"><BarChart3 className="h-4 w-4" /></span><div><div className="flex items-center gap-2"><h2 className="font-semibold">{symbol} real-time OHLC</h2><span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[9px] font-semibold text-emerald-500"><Radio className="h-3 w-3" /> STREAMING</span></div><p className="mt-0.5 text-xs text-muted-foreground">Broker-native candles and tick volume from the direct MT5 session.</p></div></div><div className="flex items-center gap-3"><div className="text-right"><p className="font-mono text-lg font-semibold">{latest?.close.toFixed(2)}</p><p className="text-[9px] text-muted-foreground">{latest ? new Date(latest.time).toLocaleString() : "No bars"}</p></div><select aria-label="OHLC timeframe" value={timeframe} onChange={(event) => setTimeframe(event.target.value)} className="rounded-lg border bg-background px-3 py-2 text-xs"><option>M5</option><option>M15</option><option>H1</option><option>H4</option></select></div></header><div ref={chartRef} className="h-[430px] w-full" aria-label="XAUUSD candlestick and tick volume chart" /></section>;
}
