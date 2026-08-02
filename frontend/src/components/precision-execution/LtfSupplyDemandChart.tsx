import { useEffect, useRef } from "react";
import { echarts } from "@/lib/echarts";
import { getChartTheme } from "@/lib/chart-theme";
import { useDarkMode } from "@/hooks/useDarkMode";
import type { FvgOverlayZone, HtfStructureCandle, LtfSupplyDemandZone, RacrReversalMarker } from "@/data/precision-execution";

export function LtfSupplyDemandChart({ candles, zones, reversalMarkers, fvgZones }: { candles: HtfStructureCandle[]; zones: LtfSupplyDemandZone[]; reversalMarkers: RacrReversalMarker[]; fvgZones: FvgOverlayZone[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const { dark } = useDarkMode();

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const theme = getChartTheme();
    chart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        backgroundColor: theme.tooltipBg,
        borderColor: theme.tooltipBorder,
        textStyle: { color: theme.tooltipText },
      },
      grid: { left: 16, right: 16, top: 30, bottom: 48, containLabel: true },
      xAxis: { type: "category", data: candles.map((item) => item.time), axisLabel: { color: theme.textColor, fontSize: 9 }, axisLine: { lineStyle: { color: theme.axisColor } } },
      yAxis: { scale: true, axisLabel: { color: theme.textColor, fontSize: 9 }, splitLine: { lineStyle: { color: theme.gridColor } } },
      dataZoom: [{ type: "inside", start: 0, end: 100 }, { type: "slider", bottom: 8, height: 18 }],
      series: [{
        type: "candlestick",
        data: candles.map((item) => [item.open, item.close, item.low, item.high]),
        itemStyle: { color: theme.upColor, color0: theme.downColor, borderColor: theme.upColor, borderColor0: theme.downColor },
        markArea: {
          silent: true,
          data: [...zones.map((zone) => {
            const supply = zone.type === "SUPPLY";
            return [
              { name: `${zone.type} · ${zone.status}`, xAxis: zone.startTime, yAxis: zone.low, itemStyle: { color: supply ? "rgba(244, 63, 94, 0.14)" : "rgba(16, 185, 129, 0.14)", borderColor: supply ? "#f43f5e" : "#10b981", borderWidth: 1 }, label: { show: true, color: supply ? "#f43f5e" : "#10b981", fontSize: 9, fontWeight: "bold", position: "insideTopLeft" } },
              { xAxis: zone.endTime, yAxis: zone.high },
            ];
          }), ...fvgZones.map((zone) => {
            const bullish = zone.direction === "BULLISH";
            return [
              { name: `${zone.direction} FVG · ${zone.status}`, xAxis: zone.startTime, yAxis: zone.low, itemStyle: { color: bullish ? "rgba(14, 165, 233, 0.18)" : "rgba(245, 158, 11, 0.18)", borderColor: bullish ? "#0ea5e9" : "#f59e0b", borderType: "dashed", borderWidth: 1 }, label: { show: true, color: bullish ? "#0ea5e9" : "#f59e0b", fontSize: 8, fontWeight: "bold", position: "insideBottomLeft" } },
              { xAxis: zone.endTime, yAxis: zone.high },
            ];
          })],
        },
        markPoint: {
          symbol: "pin",
          symbolSize: 54,
          data: [...reversalMarkers.map((marker) => ({
            coord: [marker.time, marker.price],
            value: "R-ACR",
            name: `${marker.direction} R-ACR\nSweep ${marker.sweepPrice.toFixed(2)} · reclaim ${marker.reclaimedLevel.toFixed(2)}`,
            itemStyle: { color: marker.direction === "BULLISH" ? "#10b981" : "#f43f5e" },
            label: { color: "#fff", fontSize: 8, fontWeight: "bold" },
          })), ...fvgZones.filter((zone) => zone.acrConfluence && zone.overlapLow !== undefined && zone.overlapHigh !== undefined).map((zone) => ({
            coord: [zone.startTime, (zone.overlapLow! + zone.overlapHigh!) / 2],
            value: "FVG+ACR",
            name: `High confluence\nOverlap ${zone.overlapLow!.toFixed(2)} - ${zone.overlapHigh!.toFixed(2)}`,
            symbol: "diamond",
            symbolSize: 64,
            itemStyle: { color: "#d97706", borderColor: "#fef3c7", borderWidth: 1 },
            label: { color: "#fff", fontSize: 7, fontWeight: "bold" },
          }))],
        },
      }],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [candles, zones, reversalMarkers, fvgZones, dark]);

  return <div ref={ref} className="h-[380px] w-full" aria-label="LTF candlestick chart with Supply and Demand zones" />;
}
