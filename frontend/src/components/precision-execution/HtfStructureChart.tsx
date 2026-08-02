import { useEffect, useRef } from "react";
import { echarts } from "@/lib/echarts";
import { getChartTheme } from "@/lib/chart-theme";
import { useDarkMode } from "@/hooks/useDarkMode";
import type { HtfStructureCandle, HtfStructureMarker } from "@/data/precision-execution";

export function HtfStructureChart({ candles, markers }: { candles: HtfStructureCandle[]; markers: HtfStructureMarker[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const { dark } = useDarkMode();
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const theme = getChartTheme();
    chart.setOption({ backgroundColor: "transparent", tooltip: { trigger: "axis", axisPointer: { type: "cross" }, backgroundColor: theme.tooltipBg, borderColor: theme.tooltipBorder, textStyle: { color: theme.tooltipText } }, grid: { left: 16, right: 16, top: 30, bottom: 48, containLabel: true }, xAxis: { type: "category", data: candles.map((item) => item.time), axisLabel: { color: theme.textColor, fontSize: 9 }, axisLine: { lineStyle: { color: theme.axisColor } } }, yAxis: { scale: true, axisLabel: { color: theme.textColor, fontSize: 9 }, splitLine: { lineStyle: { color: theme.gridColor } } }, dataZoom: [{ type: "inside", start: 0, end: 100 }, { type: "slider", bottom: 8, height: 18 }], series: [{ type: "candlestick", data: candles.map((item) => [item.open, item.close, item.low, item.high]), itemStyle: { color: theme.upColor, color0: theme.downColor, borderColor: theme.upColor, borderColor0: theme.downColor }, markPoint: { symbol: "pin", symbolSize: 52, data: markers.map((marker) => ({ coord: [marker.time, marker.price], value: marker.type, name: `${marker.type} ${marker.direction}\n${marker.detail}`, itemStyle: { color: marker.type === "BOS" ? "#10b981" : "#f59e0b" }, label: { color: "#fff", fontSize: 9, fontWeight: "bold" } })) } }] });
    const observer = new ResizeObserver(() => chart.resize()); observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [candles, markers, dark]);
  return <div ref={ref} className="h-[380px] w-full" aria-label="HTF candlestick chart with BOS and CHOCH markers" />;
}