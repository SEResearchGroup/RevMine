/**
 * SingleChartPage – Full-page view for a single analysis chart.
 *
 * Features: chart-type toggle, axis swap, time aggregation, export image,
 * fullscreen, statistics display.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  BarChart3,
  LineChart,
  PieChart,
  ScatterChart,
  Loader2,
  AlertCircle,
  Image,
  RefreshCw,
  Maximize2,
  X,
  ChevronDown,
} from "lucide-react";
import { analyzeService } from "../../services/api";
import DynamicChart from "../../components/analysis/DynamicChart";

const TIME_AGG_LABELS = { D: "Daily", W: "Weekly", M: "Monthly", Q: "Quarterly", Y: "Yearly" };

/* ------------------------------------------------------------------ */
/*  Fullscreen overlay                                                */
/* ------------------------------------------------------------------ */
const FullscreenOverlay = ({ result, activeType, onChartTypeChange, onClose }) => {
  if (!result) return null;
  const chartData = result.chart_data;
  const options = chartData?.options || {};
  const title =
    options.title ||
    result.metric_code?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) ||
    "Chart";

  return (
    <div className="fixed inset-0 z-50 app-modal-backdrop-strong flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-800">{title}</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="p-6">
          <DynamicChart
            chartData={chartData}
            chartType={activeType}
            height={550}
            showControls={true}
            onChartTypeChange={onChartTypeChange}
          />
        </div>
      </div>
    </div>
  );
};

/* ================================================================== */
/*  MAIN                                                              */
/* ================================================================== */
export default function SingleChartPage() {
  const { datasetId, analysisId } = useParams();
  const navigate = useNavigate();

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeType, setActiveType] = useState(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [timeAgg, setTimeAgg] = useState("M");
  const [timeChanging, setTimeChanging] = useState(false);
  const chartRef = useRef(null);

  const loadResult = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await analyzeService.getAnalysisResult(analysisId);
      setResult(res);
      const type = res.chart_data?.type || res.chart_type || "bar";
      setActiveType((prev) => prev || type);
      setTimeAgg(res.time_aggregation || "M");
    } catch (err) {
      console.error("Failed to load analysis result:", err);
      setError("Failed to load chart data.");
    } finally {
      setLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    loadResult();
  }, [loadResult]);

  const chartData = result?.chart_data;
  const options = chartData?.options || {};
  const title =
    options.title ||
    result?.metric_code?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) ||
    "Chart";

  const originalType = chartData?.type || result?.chart_type || "bar";
  const isTimeseries =
    originalType === "line" ||
    originalType === "area" ||
    (chartData?.data?.labels || []).some((l) => /\d{4}/.test(l));

  const handleExportImage = () => {
    if (chartRef.current?.exportImage) {
      const url = chartRef.current.exportImage();
      if (url) {
        const link = document.createElement("a");
        link.download = `${result?.metric_code || "chart"}.png`;
        link.href = url;
        link.click();
        return;
      }
    }
    if (result?.image_base64 || result?.chart_image) {
      const link = document.createElement("a");
      link.download = `${result?.metric_code || "chart"}.png`;
      link.href = `data:image/png;base64,${result.image_base64 || result.chart_image}`;
      link.click();
    }
  };

  const handleRetry = async () => {
    if (!result?.analysis_id) return;
    setRetrying(true);
    try {
      const res = await analyzeService.retryAnalysis(result.analysis_id);
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setRetrying(false);
    }
  };

  const handleTimeAggChange = async (newAgg) => {
    setTimeAgg(newAgg);
    setTimeChanging(true);
    try {
      const payload = {
        dataset_id: datasetId,
        time_aggregation: newAgg,
        metric_code: result.metric_code,
        chart_type: result.chart_type,
      };
      const newRes = await analyzeService.generateChart(payload);
      setResult(newRes);
    } catch (err) {
      console.error("Time aggregation change failed:", err);
    } finally {
      setTimeChanging(false);
    }
  };

  const ChartIcon =
    activeType === "line" ? LineChart
    : activeType === "pie" ? PieChart
    : activeType === "scatter" ? ScatterChart
    : BarChart3;

  /* ---- loading / error states ---- */
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading chart...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
        <AlertCircle className="w-12 h-12 text-red-400 mb-3" />
        <p className="text-gray-600">{error || "Chart not found"}</p>
        <button
          onClick={() => navigate(`/analysis/${datasetId}/detail`)}
          className="mt-4 px-4 py-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          Back to project
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => navigate(`/analysis/${datasetId}/detail`)}
            className="p-2 rounded-xl hover:bg-white hover:shadow-sm transition-all"
          >
            <ArrowLeft className="w-5 h-5 text-gray-500" />
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <ChartIcon className="w-5 h-5 text-blue-500" />
              <h1 className="text-xl font-bold text-gray-800 truncate">{title}</h1>
              <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[10px] uppercase tracking-wider font-medium">
                {activeType}
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-0.5">
              {result.metric_code?.replace(/_/g, " ")}
              {result.created_at && ` · ${new Date(result.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`}
            </p>
          </div>
        </div>

        {/* Chart card */}
        <div className="bg-white rounded-xl border border-gray-200/60 shadow-sm overflow-hidden mb-6">
          {/* Toolbar */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
            <div className="flex items-center gap-2 text-sm text-gray-600 font-medium">
              <ChartIcon className="w-4 h-4 text-blue-500" />
              {title}
            </div>
            <div className="flex items-center gap-1">
              {isTimeseries && (
                <div className="relative mr-2">
                  <select
                    value={timeAgg}
                    onChange={(e) => handleTimeAggChange(e.target.value)}
                    disabled={timeChanging}
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
                onClick={handleExportImage}
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                title="Download image"
              >
                <Image className="w-4 h-4" />
              </button>
              <button
                onClick={() => setFullscreen(true)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                title="Fullscreen"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
              <button
                onClick={handleRetry}
                disabled={retrying}
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                title="Refresh"
              >
                <RefreshCw className={`w-4 h-4 ${retrying ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>

          {/* Chart body */}
          <div className="p-6">
            {timeChanging ? (
              <div className="h-[420px] flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
              </div>
            ) : result.error ? (
              <div className="h-[420px] flex flex-col items-center justify-center text-red-400 gap-2">
                <AlertCircle className="w-10 h-10" />
                <p className="text-sm">{result.message || "Chart generation failed"}</p>
              </div>
            ) : (
              <DynamicChart
                ref={chartRef}
                chartData={chartData}
                chartType={activeType}
                height={420}
                showControls={true}
                onChartTypeChange={(newType) => setActiveType(newType)}
              />
            )}
          </div>
        </div>

        {/* Statistics */}
        {result.statistics && Object.keys(result.statistics).length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200/60 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4">
              Statistics
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(result.statistics).map(([key, val]) => (
                <div key={key} className="bg-gray-50 rounded-xl p-4 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-gray-400 font-medium whitespace-nowrap mb-1">
                    {key.replace(/_/g, " ")}
                  </p>
                  <p className="text-lg font-bold text-gray-700">
                    {typeof val === "number"
                      ? val.toLocaleString(undefined, { maximumFractionDigits: 2 })
                      : String(val)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Fullscreen */}
      {fullscreen && (
        <FullscreenOverlay
          result={result}
          activeType={activeType}
          onChartTypeChange={(newType) => setActiveType(newType)}
          onClose={() => setFullscreen(false)}
        />
      )}
    </div>
  );
}
