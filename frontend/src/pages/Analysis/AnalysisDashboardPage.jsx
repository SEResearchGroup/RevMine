import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Maximize2,
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
  TrendingUp,
  Calendar,
  Image,
  Hash,
  GitMerge,
  CheckCircle2,
} from "lucide-react";
import jsPDF from "jspdf";
import "jspdf-autotable";
import { analyzeService } from "../../services/api";
import DynamicChart from "../../components/analysis/DynamicChart";

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */
const TIME_AGG_LABELS = { D: "Daily", W: "Weekly", M: "Monthly", Q: "Quarterly", Y: "Yearly" };

/* ------------------------------------------------------------------ */
/*  Summary Stat Card                                                 */
/* ------------------------------------------------------------------ */
const SummaryStatCard = ({ icon: Icon, label, value, color = "indigo" }) => {
  const colorMap = {
    indigo: "bg-blue-600",
    emerald: "bg-green-600",
    amber:   "bg-amber-500",
    rose:    "bg-red-500",
    violet:  "bg-blue-600",
    cyan:    "bg-blue-500",
    blue:    "bg-blue-600",
  };
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl ${colorMap[color] || colorMap.indigo} flex items-center justify-center shrink-0`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wider text-gray-400 font-medium">{label}</p>
        <p className="text-lg font-bold text-gray-800 truncate">{value}</p>
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Chart card component (now uses DynamicChart)                      */
/* ------------------------------------------------------------------ */
const DashboardChart = ({
  result,
  index,
  chartTypeOverrides,
  onChartTypeChange,
  onTimeChange,
  onTimeFilter,
  onFullscreen,
  onExportImage,
  onRetry,
  retrying,
  chartRefs,
}) => {
  const [localTimeAgg, setLocalTimeAgg] = useState(
    result.time_aggregation || "M"
  );
  const [localTimeFilter, setLocalTimeFilter] = useState(
    result.chart_data?.options?.histogram?.time_filter || "all"
  );
  const [isChanging, setIsChanging] = useState(false);

  const chartData = result.chart_data;
  const originalType = chartData?.type || result.chart_type || "bar";
  const activeType = chartTypeOverrides?.[index] || originalType;
  const options = chartData?.options || {};
  const title = options.title || result.metric_code?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "Chart";

  // Check if histogram (lead time distribution)
  const isHistogram = options.isHistogram === true;

  // Check if timeseries
  const isTimeseries =
    !isHistogram &&
    (originalType === "line" ||
      originalType === "area" ||
      (chartData?.data?.labels || []).some((l) => /\d{4}/.test(l)));

  const handleTimeAggChange = async (newAgg) => {
    setLocalTimeAgg(newAgg);
    setIsChanging(true);
    try {
      await onTimeChange(index, newAgg);
    } finally {
      setIsChanging(false);
    }
  };

  const handleTimeFilterChange = async (newFilter) => {
    setLocalTimeFilter(newFilter);
    setIsChanging(true);
    try {
      await onTimeFilter(index, newFilter);
    } finally {
      setIsChanging(false);
    }
  };

  const ChartIcon =
    activeType === "line" ? LineChart
    : activeType === "pie" ? PieChart
    : activeType === "scatter" ? ScatterChart
    : BarChart3;

  const TIME_FILTER_LABELS = { all: "All", daily: "24h", weekly: "7d", monthly: "30d" };

  return (
    <div className="bg-white rounded-xl border border-gray-200/60 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col">
      {/* Card header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2 min-w-0">
          <ChartIcon className="w-4 h-4 text-blue-500" />
          <h3 className="font-semibold text-gray-800 text-sm truncate">{title}</h3>
          <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[10px] uppercase tracking-wider font-medium">
            {isHistogram ? "histogram" : activeType}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {/* Histogram time filter – All / 24h / 7d / 30d */}
          {isHistogram && (
            <div className="flex items-center bg-gray-100 rounded-lg p-0.5 mr-2">
              {Object.entries(TIME_FILTER_LABELS).map(([k, v]) => (
                <button
                  key={k}
                  onClick={() => handleTimeFilterChange(k)}
                  disabled={isChanging}
                  className={`px-2 py-1 text-[10px] font-medium rounded-md transition-colors disabled:opacity-50 ${
                    localTimeFilter === k
                      ? "bg-white text-blue-600 shadow-sm"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          )}
          {isTimeseries && (
            <div className="relative mr-2">
              <select
                value={localTimeAgg}
                onChange={(e) => handleTimeAggChange(e.target.value)}
                disabled={isChanging}
                className="appearance-none pl-2 pr-7 py-1 text-xs border border-gray-200 rounded-lg bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-400 cursor-pointer disabled:opacity-50"
              >
                {Object.entries(TIME_AGG_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
              <ChevronDown className="w-3 h-3 text-gray-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          )}
          <button
            onClick={() => onExportImage(index)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
            title="Download image"
          >
            <Image className="w-4 h-4" />
          </button>
          <button
            onClick={() => onFullscreen(index)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
            title="Fullscreen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => onRetry(index)}
            disabled={retrying}
            className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${retrying ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Chart body */}
      <div className="flex-1 p-4 min-h-[300px]">
        {isChanging ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
          </div>
        ) : result.error ? (
          <div className="h-full flex flex-col items-center justify-center text-red-400 gap-2">
            <AlertCircle className="w-8 h-8" />
            <p className="text-sm">{result.message || "Chart generation failed"}</p>
          </div>
        ) : (
          <DynamicChart
            ref={(el) => { if (chartRefs) chartRefs.current[index] = el; }}
            chartData={chartData}
            chartType={activeType}
            height={280}
            showControls={true}
            colorIndex={index}
            onChartTypeChange={(newType) => onChartTypeChange(index, newType)}
          />
        )}
      </div>

      {/* Statistics footer */}
      {result.statistics && Object.keys(result.statistics).length > 0 && (
        <div className="px-5 py-3 border-t border-gray-100 bg-gray-50/50">
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            {Object.entries(result.statistics).slice(0, 4).map(([key, val]) => (
              <div key={key} className="text-center min-w-20">
                <p className="text-[10px] uppercase tracking-wider text-gray-400 font-medium whitespace-nowrap">{key.replace(/_/g, " ")}</p>
                <p className="text-sm font-bold text-gray-700">
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
/*  Fullscreen overlay (ECharts-based)                                */
/* ------------------------------------------------------------------ */
const FullscreenOverlay = ({ result, chartTypeOverride, onChartTypeChange, onClose, colorIndex = 0 }) => {
  if (!result) return null;
  const chartData = result.chart_data;
  const activeType = chartTypeOverride || chartData?.type || result.chart_type || "bar";
  const options = chartData?.options || {};
  const title = options.title || result.metric_code?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "Chart";

  return (
    <div className="fixed inset-0 z-50 app-modal-backdrop-strong flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-800">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="p-6">
          <DynamicChart
            chartData={chartData}
            chartType={activeType}
            height={500}
            showControls={true}
            colorIndex={colorIndex}
            onChartTypeChange={onChartTypeChange}
          />
        </div>
        {result.statistics && Object.keys(result.statistics).length > 0 && (
          <div className="px-6 pb-6">
            <h4 className="text-sm font-semibold text-gray-600 mb-3">Statistics</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(result.statistics).map(([key, val]) => (
                <div key={key} className="bg-gray-50 rounded-xl p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-gray-400 font-medium whitespace-nowrap">{key.replace(/_/g, " ")}</p>
                  <p className="text-lg font-bold text-gray-700">
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
// Derive which section (analysis/kanban/cicd) owns this dashboard so the
// "change metrics" and "project detail" links go back to the right entry.
const DASHBOARD_SECTIONS = new Set(["analysis", "kanban", "cicd"]);
const deriveDashboardSection = (pathname) => {
  const first = (pathname || "").split("/").filter(Boolean)[0];
  return DASHBOARD_SECTIONS.has(first) ? first : "analysis";
};

const AnalysisDashboardPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const section = deriveDashboardSection(location.pathname);

  const [dataset, setDataset] = useState(location.state?.dataset || null);
  const [summary, setSummary] = useState(null);
  const [results, setResults] = useState(
    (location.state?.results || []).filter((r) => r.metric_code !== "custom_chart")
  );
  const [loading, setLoading] = useState(!location.state?.results);
  const [layout, setLayout] = useState("grid"); // grid | list
  const [fullscreenIdx, setFullscreenIdx] = useState(null);
  const [retryingIdx, setRetryingIdx] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [chartTypeOverrides, setChartTypeOverrides] = useState({});

  // Refs for chart instances (used in export)
  const chartRefs = useRef({});

  /* ---- load data ---- */
  const loadData = useCallback(async () => {
    if (location.state?.results) return;
    try {
      setLoading(true);
      const [datasetRes, analysesRes, summaryRes] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getAnalyses(datasetId),
        analyzeService.getDatasetSummary(datasetId).catch(() => null),
      ]);
      setDataset(datasetRes);
      setSummary(summaryRes);

      // Load results for each completed analysis
      const analyses = analysesRes.results || [];
      // Deduplicate analyses by metric_code, keeping only the latest one
      const latestByMetric = new Map();
      for (const a of analyses) {
        const key = a.metric_code || a.id;
        const existing = latestByMetric.get(key);
        if (!existing || new Date(a.created_at) > new Date(existing.created_at)) {
          latestByMetric.set(key, a);
        }
      }
      const deduplicated = [...latestByMetric.values()];

      const loaded = [];
      for (const a of deduplicated) {
        if (a.metric_code === "custom_chart") continue;
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
    loadData();
  }, [loadData]);

  /* ---- chart type change per card ---- */
  const handleChartTypeChange = useCallback((idx, newType) => {
    setChartTypeOverrides((prev) => ({ ...prev, [idx]: newType }));
  }, []);

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

  /* ---- time filter change for histogram charts (filters by Creation_Date) ---- */
  const handleTimeFilter = async (idx, newFilter) => {
    const r = results[idx];
    if (!r || r.error) return;
    try {
      const payload = {
        dataset_id: datasetId,
        metric_code: r.metric_code,
        chart_type: r.chart_type,
        config: {
          ...(r.config || {}),
          time_filter: newFilter,
        },
      };
      const newRes = await analyzeService.generateChart(payload);
      setResults((prev) => prev.map((item, i) => (i === idx ? newRes : item)));
    } catch (err) {
      console.error("Time filter change failed:", err);
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

  /* ---- export single chart as PNG via ECharts ---- */
  const handleExportImage = useCallback((idx) => {
    const chartComponent = chartRefs.current[idx];
    if (chartComponent?.exportImage) {
      const url = chartComponent.exportImage();
      if (url) {
        const link = document.createElement("a");
        link.download = `chart_${results[idx]?.metric_code || idx + 1}.png`;
        link.href = url;
        link.click();
        return;
      }
    }
    // Fallback: use backend base64 image if available
    const r = results[idx];
    if (r?.image_base64) {
      const link = document.createElement("a");
      link.download = `${r.metric_code || "chart"}_${idx + 1}.png`;
      link.href = `data:image/png;base64,${r.image_base64}`;
      link.click();
    } else if (r?.chart_image) {
      const link = document.createElement("a");
      link.download = `${r.metric_code || "chart"}_${idx + 1}.png`;
      link.href = `data:image/png;base64,${r.chart_image}`;
      link.click();
    }
  }, [results]);

  /* ---- export all to PDF ---- */
  const handleExportPDF = async () => {
    setExporting(true);
    try {
      const pdf = new jsPDF("landscape", "mm", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();

      // Title page
      pdf.setFontSize(24);
      pdf.setTextColor(99, 102, 241);
      pdf.text("Analysis Report", pageWidth / 2, 40, { align: "center" });
      pdf.setFontSize(14);
      pdf.setTextColor(100, 116, 139);
      pdf.text(dataset?.filename || dataset?.name || "Dataset", pageWidth / 2, 55, { align: "center" });
      pdf.setFontSize(10);
      pdf.text(`Generated: ${new Date().toLocaleString()}`, pageWidth / 2, 65, { align: "center" });
      pdf.text(`Total charts: ${results.filter((r) => !r.error).length}`, pageWidth / 2, 72, { align: "center" });

      // Chart pages – use ECharts getDataURL or fallback to backend image
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        if (r.error) continue;

        pdf.addPage();
        const title = r.chart_data?.options?.title || r.metric_code?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || `Chart ${i + 1}`;

        pdf.setFontSize(16);
        pdf.setTextColor(30, 41, 59);
        pdf.text(title, 14, 18);
        pdf.setFontSize(9);
        pdf.setTextColor(100, 116, 139);
        pdf.text(`Type: ${chartTypeOverrides[i] || r.chart_data?.type || r.chart_type || "chart"}`, 14, 25);

        // Try to get image data URL from ECharts instance or backend
        let imgData = null;
        
        // Try ECharts ref first
        const chartComponent = chartRefs.current[i];
        if (chartComponent?.exportImage) {
          imgData = chartComponent.exportImage();
        }
        
        // Fallback to backend base64 image
        if (!imgData && r.image_base64) {
          imgData = `data:image/png;base64,${r.image_base64}`;
        } else if (!imgData && r.chart_image) {
          imgData = `data:image/png;base64,${r.chart_image}`;
        }

        if (imgData) {
          try {
            const maxW = pageWidth - 28;
            const maxH = pageHeight - 60;
            pdf.addImage(imgData, "PNG", 14, 30, maxW, maxH * 0.7);
          } catch {
            pdf.text("Image could not be embedded", 14, 40);
          }
        } else {
          pdf.setFontSize(10);
          pdf.setTextColor(100, 116, 139);
          pdf.text("Chart image available via individual download", 14, 40);
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const successResults = results.filter((r) => !r.error);
  const failedResults = results.filter((r) => r.error);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1400px] mx-auto px-6 py-6">
        {/* Top bar */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() =>
                section === "analysis"
                  ? navigate(`/analysis/${datasetId}/detail`)
                  : navigate(`/${section}/history`)
              }
              className="p-2 rounded-xl text-gray-400 hover:text-gray-600 hover:bg-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-gray-800">
                Analysis Dashboard
              </h1>
              <p className="text-sm text-gray-500">
                {dataset?.filename || dataset?.name || dataset?.original_filename}
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
            <div className="flex items-center bg-white rounded-xl border border-gray-200 p-1">
              <button
                onClick={() => setLayout("grid")}
                className={`p-1.5 rounded-lg transition-colors ${
                  layout === "grid" ? "bg-blue-50 text-blue-600" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setLayout("list")}
                className={`p-1.5 rounded-lg transition-colors ${
                  layout === "list" ? "bg-blue-50 text-blue-600" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                <LayoutList className="w-4 h-4" />
              </button>
            </div>

            {/* Export PDF */}
            <button
              onClick={handleExportPDF}
              disabled={exporting || successResults.length === 0}
              className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
              onClick={() => navigate(`/${section}/${datasetId}/metrics`)}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium shadow-sm hover:bg-blue-700 transition-all"
            >
              <TrendingUp className="w-4 h-4" />
              Add Charts
            </button>
          </div>
        </div>

        {/* Summary stats section */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
          <SummaryStatCard icon={BarChart3} label="Total Charts" value={results.length} color="indigo" />
          <SummaryStatCard icon={CheckCircle2} label="Completed" value={successResults.length} color="emerald" />
          <SummaryStatCard icon={AlertCircle} label="Failed" value={failedResults.length} color="rose" />
          <SummaryStatCard
            icon={Hash}
            label="Dataset Rows"
            value={(dataset?.rows_count || dataset?.row_count || 0).toLocaleString()}
            color="blue"
          />
          {summary?.total_mrs != null && (
            <SummaryStatCard icon={GitMerge} label="Total MRs" value={summary.total_mrs.toLocaleString()} color="violet" />
          )}
          {summary?.date_range?.start && (
            <SummaryStatCard
              icon={Calendar}
              label="Date Range"
              value={`${new Date(summary.date_range.start).toLocaleDateString("en-US", { month: "short", year: "numeric" })} – ${new Date(summary.date_range.end).toLocaleDateString("en-US", { month: "short", year: "numeric" })}`}
              color="cyan"
            />
          )}
        </div>

        {/* State distribution (if available) */}
        {summary?.state_distribution && Object.keys(summary.state_distribution).length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {Object.entries(summary.state_distribution).map(([state, count]) => (
              <span
                key={state}
                className="px-3 py-1.5 rounded-lg bg-white border border-gray-200/60 text-xs font-medium text-gray-600"
              >
                {state}: <span className="font-bold text-gray-800">{count.toLocaleString()}</span>
              </span>
            ))}
          </div>
        )}

        {/* Charts grid */}
        {results.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200/60 p-16 text-center">
            <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 mb-4">No charts generated yet.</p>
            <button
              onClick={() => navigate(`/${section}/${datasetId}/metrics`)}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
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
                chartTypeOverrides={chartTypeOverrides}
                onChartTypeChange={handleChartTypeChange}
                onTimeChange={handleTimeChange}
                onTimeFilter={handleTimeFilter}
                onFullscreen={(i) => setFullscreenIdx(i)}
                onExportImage={handleExportImage}
                onRetry={handleRetry}
                retrying={retryingIdx === idx}
                chartRefs={chartRefs}
              />
            ))}
          </div>
        )}
      </div>

      {/* Fullscreen */}
      {fullscreenIdx !== null && (
        <FullscreenOverlay
          result={results[fullscreenIdx]}
          chartTypeOverride={chartTypeOverrides[fullscreenIdx]}
          colorIndex={fullscreenIdx}
          onChartTypeChange={(newType) => handleChartTypeChange(fullscreenIdx, newType)}
          onClose={() => setFullscreenIdx(null)}
        />
      )}
    </div>
  );
};

export default AnalysisDashboardPage;
