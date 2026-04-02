/**
 * DynamicChart – Universal ECharts-based chart component.
 *
 * Replaces the old Chart.js (InteractiveChart) and Recharts inline code.
 * Receives the standardised backend `chart_data` payload and renders it.
 *
 * Features:
 *  - Supports: bar, line, area, scatter, pie, heatmap, histogram
 *  - Built-in zoom/pan (dataZoom), tooltip, legend
 *  - Axis-swap, chart-type toggle, time-aggregation selector
 *  - Export chart as PNG natively via ECharts
 *  - Fullscreen mode
 */
import React, { useRef, useMemo, useCallback, useState, useEffect, forwardRef, useImperativeHandle } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts/core";
import {
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  HeatmapChart,
} from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  ToolboxComponent,
  TitleComponent,
  VisualMapComponent,
  BrushComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

// Register ECharts modules once
echarts.use([
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  ToolboxComponent,
  TitleComponent,
  VisualMapComponent,
  BrushComponent,
  CanvasRenderer,
]);

/* ------------------------------------------------------------------ */
/*  Colour palette                                                    */
/* ------------------------------------------------------------------ */
const COLORS = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4",
  "#8b5cf6", "#f97316", "#14b8a6", "#ec4899", "#84cc16",
  "#3b82f6", "#a855f7", "#22c55e", "#e11d48", "#0891b2",
];

/* ------------------------------------------------------------------ */
/*  Helper: build ECharts option from backend chart_data               */
/* ------------------------------------------------------------------ */
function buildOption(chartData, overrideType, swapAxes, colorOffset = 0) {
  if (!chartData) return {};

  const raw = chartData.data || chartData;
  const opts = chartData.options || {};
  const type = overrideType || chartData.type || "bar";
  const labels = raw.labels || [];
  const datasets = raw.datasets || [];

  // Tooltip
  const tooltip = {
    trigger: type === "pie" ? "item" : "axis",
    backgroundColor: "rgba(255,255,255,0.96)",
    borderColor: "#e2e8f0",
    borderWidth: 1,
    textStyle: { color: "#334155", fontSize: 12 },
    confine: true,
  };

  // Legend
  const legend = {
    type: "scroll",
    bottom: 0,
    textStyle: { color: "#64748b", fontSize: 11 },
  };

  /* ---- PIE chart ---- */
  if (type === "pie") {
    const ds = datasets[0] || {};
    const pieData = labels.map((name, i) => ({
      name,
      value: Array.isArray(ds.data) ? ds.data[i] : 0,
    }));
    return {
      tooltip: { ...tooltip, trigger: "item", formatter: "{b}: {c} ({d}%)" },
      legend: { ...legend, orient: "vertical", right: 10, top: "center" },
      color: COLORS,
      series: [
        {
          type: "pie",
          radius: ["40%", "70%"],
          center: ["40%", "50%"],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
          label: { show: true, formatter: "{b}\n{d}%" },
          data: pieData,
        },
      ],
    };
  }

  /* ---- HEATMAP (correlation matrix) ---- */
  if (type === "heatmap") {
    const heatLabels = raw.labels || [];
    const heatValues = raw.values || [];
    const heatData = [];
    for (let i = 0; i < heatValues.length; i++) {
      for (let j = 0; j < heatValues[i].length; j++) {
        heatData.push([j, i, parseFloat((heatValues[i][j] || 0).toFixed(2))]);
      }
    }
    return {
      tooltip: {
        ...tooltip,
        trigger: "item",
        formatter: (p) =>
          `${heatLabels[p.value[1]]} × ${heatLabels[p.value[0]]}: ${p.value[2]}`,
      },
      grid: { left: 120, right: 60, top: 40, bottom: 80 },
      xAxis: {
        type: "category",
        data: heatLabels,
        axisLabel: { rotate: 45, fontSize: 10 },
        splitArea: { show: true },
      },
      yAxis: {
        type: "category",
        data: heatLabels,
        axisLabel: { fontSize: 10 },
        splitArea: { show: true },
      },
      visualMap: {
        min: -1,
        max: 1,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        inRange: { color: ["#3b82f6", "#f1f5f9", "#ef4444"] },
      },
      series: [
        {
          type: "heatmap",
          data: heatData,
          label: { show: true, fontSize: 10 },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.3)" } },
        },
      ],
    };
  }

  /* ---- SCATTER ---- */
  if (type === "scatter") {
    const ds = datasets[0] || {};
    const scatterData = Array.isArray(ds.data)
      ? ds.data.map((pt) =>
          typeof pt === "object" ? [pt.x, pt.y] : [pt, 0]
        )
      : [];

    const xLabel = swapAxes ? (opts.yLabel || "Y") : (opts.xLabel || "X");
    const yLabel = swapAxes ? (opts.xLabel || "X") : (opts.yLabel || "Y");
    const finalData = swapAxes ? scatterData.map(([x, y]) => [y, x]) : scatterData;

    return {
      tooltip: {
        ...tooltip,
        trigger: "item",
        formatter: (p) => `${xLabel}: ${p.value[0]}<br/>${yLabel}: ${p.value[1]}`,
      },
      legend,
      grid: { left: 60, right: 40, top: 40, bottom: 60 },
      xAxis: {
        type: "value",
        name: xLabel,
        nameLocation: "middle",
        nameGap: 30,
        splitLine: { lineStyle: { type: "dashed", color: "#f1f5f9" } },
      },
      yAxis: {
        type: "value",
        name: yLabel,
        nameLocation: "middle",
        nameGap: 50,
        splitLine: { lineStyle: { type: "dashed", color: "#f1f5f9" } },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0 },
        { type: "inside", yAxisIndex: 0 },
      ],
      series: [
        {
          name: ds.label || "Data",
          type: "scatter",
          data: finalData,
          symbolSize: 8,
          itemStyle: { color: COLORS[0], opacity: 0.7 },
        },
      ],
    };
  }

  /* ---- BAR / LINE / AREA ---- */
  const xData = swapAxes ? undefined : labels;
  const xLabel = swapAxes ? (opts.yLabel || "") : (opts.xLabel || "");
  const yLabel = swapAxes ? (opts.xLabel || "") : (opts.yLabel || "");

  // Shift colour palette so each chart card gets a distinct primary colour
  const shiftedColors = [...COLORS.slice(colorOffset % COLORS.length), ...COLORS.slice(0, colorOffset % COLORS.length)];

  const series = datasets.map((ds, idx) => {
    const values = Array.isArray(ds.data) ? ds.data : [];
    const base = {
      name: ds.label || `Series ${idx + 1}`,
      data: swapAxes
        ? values.map((v, i) => [v, labels[i]])
        : values,
      itemStyle: { color: shiftedColors[idx % shiftedColors.length] },
      emphasis: { focus: "series" },
    };

    if (type === "line") {
      return {
        ...base,
        type: "line",
        smooth: true,
        showSymbol: values.length <= 50,
        symbolSize: 6,
        lineStyle: { width: 2.5 },
        areaStyle: undefined,
      };
    }

    if (type === "area") {
      return {
        ...base,
        type: "line",
        smooth: true,
        showSymbol: values.length <= 50,
        symbolSize: 6,
        lineStyle: { width: 2.5 },
        areaStyle: { opacity: 0.15 },
      };
    }

    // Default: bar
    return {
      ...base,
      type: "bar",
      barMaxWidth: 50,
      itemStyle: {
        ...base.itemStyle,
        borderRadius: [4, 4, 0, 0],
      },
    };
  });

  const needsDataZoom = labels.length > 15;

  const option = {
    tooltip,
    legend: datasets.length > 1 ? legend : undefined,
    grid: {
      left: 60,
      right: 30,
      top: 30,
      bottom: needsDataZoom ? 80 : 40,
      containLabel: false,
    },
    xAxis: swapAxes
      ? {
          type: "value",
          name: xLabel,
          nameLocation: "middle",
          nameGap: 30,
          splitLine: { lineStyle: { type: "dashed", color: "#f1f5f9" } },
        }
      : {
          type: "category",
          data: xData,
          name: xLabel,
          nameLocation: "middle",
          nameGap: 30,
          axisLabel: {
            rotate: labels.length > 8 ? 45 : 0,
            fontSize: 11,
            color: "#64748b",
          },
          axisTick: { alignWithLabel: true },
        },
    yAxis: swapAxes
      ? {
          type: "category",
          data: labels,
          axisLabel: { fontSize: 11, color: "#64748b" },
        }
      : {
          type: "value",
          name: yLabel,
          nameLocation: "middle",
          nameGap: 50,
          splitLine: { lineStyle: { type: "dashed", color: "#f1f5f9" } },
          axisLabel: { fontSize: 11, color: "#64748b" },
        },
    dataZoom: needsDataZoom
      ? [
          { type: "slider", bottom: 10, height: 20, textStyle: { fontSize: 10 } },
          { type: "inside" },
        ]
      : [{ type: "inside" }],
    series,
    color: shiftedColors,
  };

  return option;
}

/* ------------------------------------------------------------------ */
/*  DynamicChart component                                            */
/* ------------------------------------------------------------------ */
const DynamicChart = forwardRef(({
  chartData,
  chartType: initialChartType,
  height = 360,
  onChartTypeChange,
  onSwapAxes,
  showControls = true,
  colorIndex = 0,
  className = "",
}, ref) => {
  const chartRef = useRef(null);

  // Expose getEchartsInstance and exportImage to parent via ref
  useImperativeHandle(ref, () => ({
    getEchartsInstance: () => chartRef.current?.getEchartsInstance(),
    exportImage: () => {
      const instance = chartRef.current?.getEchartsInstance();
      if (!instance) return null;
      return instance.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
    },
  }));

  // NOTE: chart type and axis swap are managed externally by the Dashboard.
  // We accept them as props and only pass to buildOption.
  const activeType = initialChartType || chartData?.type || "bar";
  const [swapAxes, setSwapAxes] = useState(false);

  // Determine which chart type toggles to show based on the chart's nature
  const supportedTypes = useMemo(() => {
    if (!chartData) return [];
    const type = chartData.type || "bar";
    if (type === "pie") return ["pie", "bar"];
    if (type === "heatmap") return ["heatmap"];
    if (type === "scatter") return ["scatter"];
    // For bar/line/area types, allow switching between them
    return ["bar", "line", "area"];
  }, [chartData]);

  // Can swap axes for bar/line/area (not pie, heatmap, scatter)
  const canSwapAxes = useMemo(() => {
    return ["bar", "line", "area"].includes(activeType);
  }, [activeType]);

  // Build ECharts option
  const option = useMemo(
    () => buildOption(chartData, activeType, swapAxes, colorIndex),
    [chartData, activeType, swapAxes, colorIndex]
  );

  // Export chart as PNG via ECharts
  const handleExportImage = useCallback(() => {
    const instance = chartRef.current?.getEchartsInstance();
    if (!instance) return;
    const url = instance.getDataURL({
      type: "png",
      pixelRatio: 2,
      backgroundColor: "#fff",
    });
    const link = document.createElement("a");
    link.download = `chart_${Date.now()}.png`;
    link.href = url;
    link.click();
  }, []);

  const handleSwapAxes = useCallback(() => {
    setSwapAxes((prev) => !prev);
    if (onSwapAxes) onSwapAxes(!swapAxes);
  }, [swapAxes, onSwapAxes]);

  if (!chartData) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400 text-sm">
        No data available
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Controls row */}
      {showControls && (
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          {/* Chart type toggles */}
          {supportedTypes.length > 1 && (
            <div className="flex items-center bg-slate-100 rounded-lg p-0.5">
              {supportedTypes.map((t) => (
                <button
                  key={t}
                  onClick={() => onChartTypeChange?.(t)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors capitalize ${
                    activeType === t
                      ? "bg-white text-indigo-600 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          )}

          {/* Swap axes button */}
          {canSwapAxes && (
            <button
              onClick={handleSwapAxes}
              className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors ${
                swapAxes
                  ? "bg-indigo-50 border-indigo-200 text-indigo-600"
                  : "bg-white border-slate-200 text-slate-500 hover:border-indigo-200 hover:text-indigo-600"
              }`}
              title="Swap X / Y axes"
            >
              ⇆ Swap Axes
            </button>
          )}
        </div>
      )}

      {/* Chart */}
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height, width: "100%" }}
        notMerge={true}
        opts={{ renderer: "canvas" }}
      />
    </div>
  );
});

DynamicChart.displayName = "DynamicChart";

/**
 * Utility: get ECharts instance ref for external export.
 * Usage: pass a ref to DynamicChart, then call ref.current.getEchartsInstance()
 */
DynamicChart.getExportImage = (chartRef) => {
  const instance = chartRef?.current?.getEchartsInstance?.();
  if (!instance) return null;
  return instance.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
};

export default DynamicChart;
