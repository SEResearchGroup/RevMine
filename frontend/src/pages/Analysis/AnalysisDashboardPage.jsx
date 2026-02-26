import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  FileText,
  Maximize2,
  Minimize2,
  RefreshCw,
  BarChart3,
  LineChart,
  PieChart,
  ScatterChart,
  Loader2,
  AlertCircle,
  X,
  ChevronDown,
  LayoutGrid,
  LayoutList,
  Clock,
  TrendingUp,
  Calendar,
  Filter,
  Image,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart as RLineChart,
  Line,
  BarChart,
  Bar,
  PieChart as RPieChart,
  Pie,
  Cell,
  ScatterChart as RScatterChart,
  Scatter,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Brush,
} from "recharts";
import jsPDF from "jspdf";
import "jspdf-autotable";
import { analyzeService } from "../../services/api";

/* ------------------------------------------------------------------ */
/*  Color palette                                                     */
/* ------------------------------------------------------------------ */
const COLORS = [
  "#6366f1", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b",
  "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
  "#84cc16", "#a855f7", "#0ea5e9", "#22c55e", "#eab308",
];

const TIME_AGG_LABELS = { D: "Daily", W: "Weekly", M: "Monthly", Q: "Quarterly", Y: "Yearly" };

/* ------------------------------------------------------------------ */
/*  Chart card component                                              */
/* ------------------------------------------------------------------ */
const DashboardChart = ({
  result,
  index,
  onTimeChange,
  onFullscreen,
  onDownloadImage,
  onRetry,
  retrying,
}) => {
  const [localTimeAgg, setLocalTimeAgg] = useState(
    result.time_aggregation || "M"
  );
  const [isChanging, setIsChanging] = useState(false);

  const chartData = result.chart_data;
  const chartType = chartData?.type || result.chart_type || "bar";
  const options = chartData?.options || {};
  const title = options.title || result.metric_code?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "Chart";

  // Check if this is a timeseries chart
  const isTimeseries =
    chartType === "line" ||
    chartType === "area" ||
    (chartData?.data?.labels || []).some((l) => /\d{4}/.test(l));

  // Convert chart.js data to recharts format
  const rechartsData = convertToRechartsData(chartData, chartType);
  const datasetConfigs = chartData?.data?.datasets || [];

  const handleTimeAggChange = async (newAgg) => {
    setLocalTimeAgg(newAgg);
    setIsChanging(true);
    try {
      await onTimeChange(index, newAgg);
    } finally {
      setIsChanging(false);
    }
  };

  const ChartIcon =
    chartType === "line"
      ? LineChart
      : chartType === "pie"
      ? PieChart
      : chartType === "scatter"
      ? ScatterChart
      : BarChart3;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col">
      {/* Card header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
        <div className="flex items-center gap-2 min-w-0">
          <ChartIcon className="w-4 h-4 text-indigo-500" />
          <h3 className="font-semibold text-slate-800 text-sm truncate">{title}</h3>
          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] uppercase tracking-wider font-medium">
            {chartType}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {isTimeseries && (
            <div className="relative mr-2">
              <select
                value={localTimeAgg}
                onChange={(e) => handleTimeAggChange(e.target.value)}
                disabled={isChanging}
                className="appearance-none pl-2 pr-7 py-1 text-xs border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-400 cursor-pointer disabled:opacity-50"
              >
                {Object.entries(TIME_AGG_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
              <ChevronDown className="w-3 h-3 text-slate-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          )}
          <button
            onClick={() => onDownloadImage(index)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
            title="Download image"
          >
            <Image className="w-4 h-4" />
          </button>
          <button
            onClick={() => onFullscreen(index)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
            title="Fullscreen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => onRetry(index)}
            disabled={retrying}
            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${retrying ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Chart body */}
      <div className="flex-1 p-4 min-h-[280px]">
        {isChanging ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
          </div>
        ) : result.error ? (
          <div className="h-full flex flex-col items-center justify-center text-red-400 gap-2">
            <AlertCircle className="w-8 h-8" />
            <p className="text-sm">{result.message || "Chart generation failed"}</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            {renderRechartsChart(chartType, rechartsData, datasetConfigs, options)}
          </ResponsiveContainer>
        )}
      </div>

      {/* Statistics footer */}
      {result.statistics && Object.keys(result.statistics).length > 0 && (
        <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/50">
          <div className="flex flex-wrap gap-4">
            {Object.entries(result.statistics).slice(0, 4).map(([key, val]) => (
              <div key={key} className="text-center">
                <p className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">{key.replace(/_/g, " ")}</p>
                <p className="text-sm font-bold text-slate-700">
                  {typeof val === "number" ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(val)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Data conversion helpers                                           */
/* ------------------------------------------------------------------ */
function convertToRechartsData(chartData, chartType) {
  if (!chartData) return [];

  const raw = chartData.data || chartData;
  const labels = raw.labels || [];
  const datasets = raw.datasets || [];

  if (chartType === "pie") {
    const ds = datasets[0] || {};
    return labels.map((label, i) => ({
      name: label,
      value: Array.isArray(ds.data) ? ds.data[i] : 0,
    }));
  }

  if (chartType === "scatter") {
    const ds = datasets[0] || {};
    if (Array.isArray(ds.data) && ds.data.length > 0 && typeof ds.data[0] === "object") {
      return ds.data.map((pt) => ({ x: pt.x, y: pt.y }));
    }
    return labels.map((l, i) => ({
      x: Array.isArray(ds.data) ? ds.data[i] : 0,
      y: datasets[1] ? datasets[1].data?.[i] : 0,
    }));
  }

  // line, bar, area, histogram
  return labels.map((label, i) => {
    const point = { name: label };
    datasets.forEach((ds, di) => {
      const key = ds.label || `series_${di}`;
      point[key] = Array.isArray(ds.data) ? ds.data[i] : 0;
    });
    return point;
  });
}

function renderRechartsChart(type, data, datasetConfigs, options) {
  const xLabel = options.xLabel || "";
  const yLabel = options.yLabel || "";

  const commonProps = {
    data,
    margin: { top: 5, right: 20, left: 10, bottom: 5 },
  };

  const customTooltip = {
    contentStyle: {
      background: "white",
      border: "1px solid #e2e8f0",
      borderRadius: "12px",
      padding: "8px 12px",
      boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)",
    },
  };

  if (type === "pie") {
    return (
      <RPieChart>
        <Pie data={data} cx="50%" cy="50%" outerRadius={90} innerRadius={45} dataKey="value" nameKey="name" paddingAngle={3} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={{ strokeWidth: 1 }}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip {...customTooltip} />
        <Legend />
      </RPieChart>
    );
  }

  if (type === "scatter") {
    return (
      <RScatterChart {...commonProps}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="x" type="number" name={xLabel || "X"} tick={{ fontSize: 11 }} />
        <YAxis dataKey="y" type="number" name={yLabel || "Y"} tick={{ fontSize: 11 }} />
        <Tooltip {...customTooltip} />
        <Scatter data={data} fill={COLORS[0]} fillOpacity={0.7} r={5} />
      </RScatterChart>
    );
  }

  if (type === "area") {
    const keys = datasetConfigs.map((ds) => ds.label || "value");
    return (
      <AreaChart {...commonProps}>
        <defs>
          {keys.map((k, i) => (
            <linearGradient key={k} id={`grad_${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.3} />
              <stop offset="95%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip {...customTooltip} />
        <Legend />
        {keys.map((k, i) => (
          <Area
            key={k}
            type="monotone"
            dataKey={k}
            stroke={COLORS[i % COLORS.length]}
            fill={`url(#grad_${i})`}
            strokeWidth={2}
          />
        ))}
        {data.length > 15 && <Brush dataKey="name" height={20} stroke="#6366f1" />}
      </AreaChart>
    );
  }

  if (type === "line") {
    const keys = datasetConfigs.length > 0 ? datasetConfigs.map((ds) => ds.label || "value") : Object.keys(data[0] || {}).filter((k) => k !== "name");
    return (
      <RLineChart {...commonProps}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip {...customTooltip} />
        <Legend />
        {keys.map((k, i) => (
          <Line
            key={k}
            type="monotone"
            dataKey={k}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2}
            dot={{ r: 3, fill: COLORS[i % COLORS.length] }}
            activeDot={{ r: 5 }}
          />
        ))}
        {data.length > 15 && <Brush dataKey="name" height={20} stroke="#6366f1" />}
      </RLineChart>
    );
  }

  // bar / histogram
  const keys = datasetConfigs.length > 0 ? datasetConfigs.map((ds) => ds.label || "value") : Object.keys(data[0] || {}).filter((k) => k !== "name");
  return (
    <BarChart {...commonProps}>
      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
      <YAxis tick={{ fontSize: 11 }} />
      <Tooltip {...customTooltip} />
      <Legend />
      {keys.map((k, i) => (
        <Bar
          key={k}
          dataKey={k}
          fill={COLORS[i % COLORS.length]}
          radius={[4, 4, 0, 0]}
          maxBarSize={50}
        />
      ))}
      {data.length > 15 && <Brush dataKey="name" height={20} stroke="#6366f1" />}
    </BarChart>
  );
}

/* ------------------------------------------------------------------ */
/*  Fullscreen overlay                                                */
/* ------------------------------------------------------------------ */
const FullscreenOverlay = ({ result, onClose }) => {
  if (!result) return null;
  const chartData = result.chart_data;
  const chartType = chartData?.type || result.chart_type || "bar";
  const options = chartData?.options || {};
  const title = options.title || result.metric_code?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "Chart";
  const rechartsData = convertToRechartsData(chartData, chartType);
  const datasetConfigs = chartData?.data?.datasets || [];

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-6 border-b border-slate-100">
          <h2 className="text-lg font-bold text-slate-800">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        <div className="p-6" style={{ height: "500px" }}>
          <ResponsiveContainer width="100%" height="100%">
            {renderRechartsChart(chartType, rechartsData, datasetConfigs, options)}
          </ResponsiveContainer>
        </div>
        {result.statistics && Object.keys(result.statistics).length > 0 && (
          <div className="px-6 pb-6">
            <h4 className="text-sm font-semibold text-slate-600 mb-3">Statistics</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(result.statistics).map(([key, val]) => (
                <div key={key} className="bg-slate-50 rounded-xl p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">{key.replace(/_/g, " ")}</p>
                  <p className="text-lg font-bold text-slate-700">
                    {typeof val === "number" ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(val)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/* ================================================================== */
/*  MAIN DASHBOARD PAGE                                               */
/* ================================================================== */
const AnalysisDashboardPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [dataset, setDataset] = useState(location.state?.dataset || null);
  const [results, setResults] = useState(location.state?.results || []);
  const [loading, setLoading] = useState(!location.state?.results);
  const [layout, setLayout] = useState("grid"); // grid | list
  const [fullscreenIdx, setFullscreenIdx] = useState(null);
  const [retryingIdx, setRetryingIdx] = useState(null);
  const [exporting, setExporting] = useState(false);

  /* ---- load from history if no state ---- */
  const loadFromHistory = useCallback(async () => {
    if (location.state?.results) return;
    try {
      setLoading(true);
      const [datasetRes, analysesRes] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getAnalyses(datasetId),
      ]);
      setDataset(datasetRes);

      // Load results for each completed analysis
      const analyses = analysesRes.results || [];
      const loaded = [];
      for (const a of analyses) {
        if (a.status === "completed") {
          try {
            const res = await analyzeService.getAnalysisResult(a.id);
            loaded.push(res);
          } catch {
            loaded.push({ ...a, error: true, message: "Failed to load result" });
          }
        } else {
          loaded.push({ ...a, error: a.status === "failed", message: a.error_message });
        }
      }
      setResults(loaded);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [datasetId, location.state]);

  useEffect(() => {
    loadFromHistory();
  }, [loadFromHistory]);

  /* ---- time aggregation change = re-generate chart ---- */
  const handleTimeChange = async (idx, newAgg) => {
    const r = results[idx];
    if (!r || r.error) return;
    try {
      const payload = {
        dataset_id: datasetId,
        time_aggregation: newAgg,
      };
      if (r.metric_code && r.metric_code !== "custom_chart") {
        payload.metric_code = r.metric_code;
        payload.chart_type = r.chart_type;
      } else {
        payload.x_axis = r.x_axis || r.config?.x_axis;
        payload.y_axis = r.y_axis || r.config?.y_axis;
        payload.chart_type = r.chart_type;
        payload.aggregation = r.aggregation || r.config?.aggregation || "sum";
      }
      const newRes = await analyzeService.generateChart(payload);
      setResults((prev) => prev.map((item, i) => (i === idx ? newRes : item)));
    } catch (err) {
      console.error("Time agg change failed:", err);
    }
  };

  /* ---- retry ---- */
  const handleRetry = async (idx) => {
    const r = results[idx];
    if (!r) return;
    setRetryingIdx(idx);
    try {
      if (r.analysis_id) {
        const res = await analyzeService.retryAnalysis(r.analysis_id);
        setResults((prev) => prev.map((item, i) => (i === idx ? res : item)));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRetryingIdx(null);
    }
  };

  /* ---- download single matplotlib image ---- */
  const handleDownloadImage = (idx) => {
    const r = results[idx];
    if (!r?.image_base64) return;
    const link = document.createElement("a");
    link.download = `${r.metric_code || "chart"}_${idx + 1}.png`;
    link.href = `data:image/png;base64,${r.image_base64}`;
    link.click();
  };

  /* ---- export all to PDF ---- */
  const handleExportPDF = async () => {
    setExporting(true);
    try {
      const pdf = new jsPDF("landscape", "mm", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();

      // Title page
      pdf.setFontSize(24);
      pdf.setTextColor(99, 102, 241); // indigo
      pdf.text("Analysis Report", pageWidth / 2, 40, { align: "center" });
      pdf.setFontSize(14);
      pdf.setTextColor(100, 116, 139);
      pdf.text(dataset?.name || dataset?.original_filename || "Dataset", pageWidth / 2, 55, { align: "center" });
      pdf.setFontSize(10);
      pdf.text(`Generated: ${new Date().toLocaleString()}`, pageWidth / 2, 65, { align: "center" });
      pdf.text(`Total charts: ${results.filter((r) => !r.error).length}`, pageWidth / 2, 72, { align: "center" });

      // Chart pages
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        if (r.error || !r.image_base64) continue;

        pdf.addPage();
        const title = r.chart_data?.options?.title || r.metric_code?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || `Chart ${i + 1}`;

        // Title
        pdf.setFontSize(16);
        pdf.setTextColor(30, 41, 59);
        pdf.text(title, 14, 18);

        // Chart type badge
        pdf.setFontSize(9);
        pdf.setTextColor(100, 116, 139);
        pdf.text(`Type: ${r.chart_type || "chart"}`, 14, 25);

        // Image
        try {
          const imgData = `data:image/png;base64,${r.image_base64}`;
          const maxW = pageWidth - 28;
          const maxH = pageHeight - 60;
          pdf.addImage(imgData, "PNG", 14, 30, maxW, maxH * 0.7);
        } catch {
          pdf.text("Image could not be embedded", 14, 40);
        }

        // Statistics
        if (r.statistics && Object.keys(r.statistics).length > 0) {
          const statsY = pageHeight - 30;
          pdf.setFontSize(10);
          pdf.setTextColor(30, 41, 59);
          pdf.text("Statistics:", 14, statsY);
          const statsText = Object.entries(r.statistics)
            .map(([k, v]) => `${k}: ${typeof v === "number" ? v.toFixed(2) : v}`)
            .join("  |  ");
          pdf.setFontSize(8);
          pdf.setTextColor(100, 116, 139);
          pdf.text(statsText, 14, statsY + 6, { maxWidth: pageWidth - 28 });
        }
      }

      pdf.save(`analysis_report_${datasetId.slice(0, 8)}.pdf`);
    } catch (err) {
      console.error("PDF export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  /* ---- render ---- */
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mx-auto mb-3" />
          <p className="text-slate-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const successResults = results.filter((r) => !r.error);
  const failedResults = results.filter((r) => r.error);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
      <div className="max-w-[1400px] mx-auto px-6 py-6">
        {/* Top bar */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(`/analysis/${datasetId}/metrics`)}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-slate-800">
                Analysis Dashboard
              </h1>
              <p className="text-sm text-slate-500">
                {dataset?.name || dataset?.original_filename}
                {" · "}
                {successResults.length} chart{successResults.length !== 1 ? "s" : ""}
                {failedResults.length > 0 && (
                  <span className="text-red-400">
                    {" · "}{failedResults.length} failed
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Layout toggle */}
            <div className="flex items-center bg-white rounded-xl border border-slate-200 p-1">
              <button
                onClick={() => setLayout("grid")}
                className={`p-1.5 rounded-lg transition-colors ${
                  layout === "grid" ? "bg-indigo-50 text-indigo-600" : "text-slate-400 hover:text-slate-600"
                }`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setLayout("list")}
                className={`p-1.5 rounded-lg transition-colors ${
                  layout === "list" ? "bg-indigo-50 text-indigo-600" : "text-slate-400 hover:text-slate-600"
                }`}
              >
                <LayoutList className="w-4 h-4" />
              </button>
            </div>

            {/* Export PDF */}
            <button
              onClick={handleExportPDF}
              disabled={exporting || successResults.length === 0}
              className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {exporting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              Export PDF
            </button>

            {/* Add more metrics */}
            <button
              onClick={() => navigate(`/analysis/${datasetId}/metrics`)}
              className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-xl text-sm font-medium shadow-sm hover:from-indigo-700 hover:to-blue-700 transition-all"
            >
              <TrendingUp className="w-4 h-4" />
              Add Charts
            </button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total Charts", value: results.length, icon: BarChart3, color: "indigo" },
            { label: "Completed", value: successResults.length, icon: TrendingUp, color: "emerald" },
            { label: "Failed", value: failedResults.length, icon: AlertCircle, color: "red" },
            { label: "Dataset Rows", value: dataset?.row_count?.toLocaleString() || "—", icon: Calendar, color: "blue" },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white rounded-xl border border-slate-200/60 p-4 flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg bg-${color}-50 flex items-center justify-center`}>
                <Icon className={`w-5 h-5 text-${color}-500`} />
              </div>
              <div>
                <p className="text-xs text-slate-400 font-medium">{label}</p>
                <p className="text-lg font-bold text-slate-800">{value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Charts grid */}
        {results.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200/60 p-16 text-center">
            <BarChart3 className="w-12 h-12 mx-auto mb-4 text-slate-300" />
            <p className="text-slate-500 mb-4">No charts generated yet.</p>
            <button
              onClick={() => navigate(`/analysis/${datasetId}/metrics`)}
              className="px-6 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              Select Metrics
            </button>
          </div>
        ) : (
          <div
            className={
              layout === "grid"
                ? "grid grid-cols-1 lg:grid-cols-2 gap-5"
                : "space-y-5"
            }
          >
            {results.map((result, idx) => (
              <DashboardChart
                key={idx}
                result={result}
                index={idx}
                onTimeChange={handleTimeChange}
                onFullscreen={(i) => setFullscreenIdx(i)}
                onDownloadImage={handleDownloadImage}
                onRetry={handleRetry}
                retrying={retryingIdx === idx}
              />
            ))}
          </div>
        )}
      </div>

      {/* Fullscreen */}
      {fullscreenIdx !== null && (
        <FullscreenOverlay
          result={results[fullscreenIdx]}
          onClose={() => setFullscreenIdx(null)}
        />
      )}
    </div>
  );
};

export default AnalysisDashboardPage;
