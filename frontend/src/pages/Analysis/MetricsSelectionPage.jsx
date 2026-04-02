import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  LineChart,
  PieChart,
  ScatterChart,
  Search,
  CheckSquare,
  Square,
  Loader2,
  AlertCircle,
  Info,
  Lock,
  ChevronDown,
  ChevronRight,
  Play,
  Layers,
} from "lucide-react";
import { analyzeService } from "../../services/api";

/* ------------------------------------------------------------------ */
/*  Category metadata helpers                                         */
/* ------------------------------------------------------------------ */
const CATEGORY_META = {
  timeseries: { icon: LineChart, color: "blue", label: "Time Series" },
  distribution: { icon: BarChart3, color: "violet", label: "Distribution" },
  correlation: { icon: ScatterChart, color: "emerald", label: "Correlation" },
  composition: { icon: PieChart, color: "amber", label: "Composition" },
  summary: { icon: Layers, color: "rose", label: "Summary" },
};

// const categoryColor = (cat, variant) => {
//   const c = CATEGORY_META[cat]?.color || "slate";
//   const map = {
//     bg: `bg-${c}-50`,
//     bgDark: `bg-${c}-100`,
//     text: `text-${c}-600`,
//     border: `border-${c}-200`,
//     ring: `ring-${c}-400`,
//   };
//   return map[variant] || "";
// };

const CHART_ICONS = {
  line: LineChart,
  bar: BarChart3,
  pie: PieChart,
  scatter: ScatterChart,
  histogram: BarChart3,
  area: LineChart,
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                    */
/* ------------------------------------------------------------------ */
const MetricsSelectionPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();

  // Data
  const [dataset, setDataset] = useState(null);
  const [allMetricsByCategory, setAllMetricsByCategory] = useState({});
  const [availableCodes, setAvailableCodes] = useState(new Set());
  const [missingCols, setMissingCols] = useState({});
  const [compatibleAxes, setCompatibleAxes] = useState(null);

  // Selection
  const [selectedMetrics, setSelectedMetrics] = useState([]);

  // UI
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedCats, setExpandedCats] = useState({});
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  /* ---- load data ---- */
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [datasetRes, allMetricsRes, availableRes, axesRes] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getMetricsByCategory(),
        analyzeService.getAvailableMetrics(datasetId),
        analyzeService.getCompatibleAxes(datasetId),
      ]);
      setDataset(datasetRes);
      setAllMetricsByCategory(allMetricsRes);
      setAvailableCodes(new Set((availableRes.metrics || []).map((m) => m.code)));
      setMissingCols(availableRes.missing_columns_by_metric || {});
      setCompatibleAxes(axesRes);

      // Auto-expand categories that have available metrics
      const expanded = {};
      Object.keys(allMetricsRes).forEach((cat) => {
        expanded[cat] = true;
      });
      setExpandedCats(expanded);
    } catch (err) {
      console.error(err);
      setError("Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  /* ---- metric toggles ---- */
  const toggleMetric = (code) => {
    if (!availableCodes.has(code)) return; // can't select unavailable
    setSelectedMetrics((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const toggleCategory = (cat) =>
    setExpandedCats((p) => ({ ...p, [cat]: !p[cat] }));

  const selectAllAvailable = () => {
    const allAvailable = [];
    Object.values(allMetricsByCategory).forEach((metrics) => {
      (Array.isArray(metrics) ? metrics : []).forEach((m) => {
        if (availableCodes.has(m.code)) allAvailable.push(m.code);
      });
    });
    if (selectedMetrics.length === allAvailable.length) setSelectedMetrics([]);
    else setSelectedMetrics(allAvailable);
  };

  /* ---- submit ---- */
  const totalSelected = selectedMetrics.length;

  const handleRunAnalysis = async () => {
    if (totalSelected === 0) return;
    try {
      setCreating(true);
      setError(null);

      const results = [];

      // Generate predefined metrics via /generate/
      for (const code of selectedMetrics) {
        try {
          const res = await analyzeService.generateChart({
            dataset_id: datasetId,
            metric_code: code,
          });
          results.push(res);
        } catch (err) {
          console.error(`Failed metric ${code}:`, err);
          results.push({ metric_code: code, error: true, message: err.response?.data?.error || err.message });
        }
      }

      navigate(`/analysis/${datasetId}/dashboard`, { state: { results, dataset } });
    } catch (err) {
      setError("Analysis failed. Try again.");
    } finally {
      setCreating(false);
    }
  };

  /* ---- search filter ---- */
  const filterMetrics = (metrics) =>
    (Array.isArray(metrics) ? metrics : []).filter(
      (m) =>
        (m.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (m.code || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (m.description || "").toLowerCase().includes(searchTerm.toLowerCase())
    );

  /* ---- loading / error states ---- */
  if (loading) {
    return (
      <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mx-auto mb-3" />
          <p className="text-slate-500">Loading metrics catalogue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate("/analysis")}
            className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to datasets
          </button>

          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-linear-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-200/50">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-800">
                Select Metrics
              </h1>
              <p className="text-sm text-slate-500">
                Step 2 — Choose what to analyze on{" "}
                <span className="font-medium text-slate-700">
                  {dataset?.name || dataset?.original_filename}
                </span>
              </p>
            </div>
          </div>
        </div>

        {/* Steps */}
        <div className="flex items-center gap-3 mb-8">
          {[
            { n: 1, label: "Dataset", done: true },
            { n: 2, label: "Metrics", active: true },
            { n: 3, label: "Dashboard" },
          ].map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              <div
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  step.active
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
                    : step.done
                    ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
                    : "bg-white text-slate-400 border border-slate-200"
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    step.active
                      ? "bg-white/20 text-white"
                      : step.done
                      ? "bg-emerald-200 text-emerald-700"
                      : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {step.done ? "✓" : step.n}
                </span>
                {step.label}
              </div>
              {i < 2 && <div className="w-8 h-px bg-slate-200" />}
            </div>
          ))}
        </div>

        {/* Sticky selection bar */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-4 mb-6 sticky top-2 z-20">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <CheckSquare className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-400">Selected</p>
                  <p className="text-xl font-bold text-slate-800">
                    {totalSelected}{" "}
                    <span className="text-sm font-normal text-slate-400">
                      chart{totalSelected !== 1 ? "s" : ""}
                    </span>
                  </p>
                </div>
              </div>

              <button
                onClick={selectAllAvailable}
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                {selectedMetrics.length === [...availableCodes].length
                  ? "Deselect all"
                  : "Select all available"}
              </button>
            </div>

            <button
              onClick={handleRunAnalysis}
              disabled={totalSelected === 0 || creating}
              className="flex items-center gap-2 px-6 py-3 bg-linear-to-r from-indigo-600 to-blue-600 text-white rounded-xl font-medium shadow-lg shadow-indigo-200/50 hover:from-indigo-700 hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none disabled:cursor-not-allowed transition-all"
            >
              {creating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Run Analysis ({totalSelected})
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
        </div>

        {/* Search */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-4 mb-6">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
                  type="text"
                  placeholder="Search metrics..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-slate-50/50 transition-all"
                />
              </div>
            </div>

            {/* Metrics grid by category */}
            <div className="space-y-4">
              {Object.entries(allMetricsByCategory).length === 0 ? (
                <div className="bg-white rounded-2xl border border-slate-200/60 p-12 text-center">
                  <BarChart3 className="w-12 h-12 mx-auto mb-4 text-slate-300" />
                  <p className="text-slate-500">No metrics available.</p>
                </div>
              ) : (
                Object.entries(allMetricsByCategory).map(([category, metrics]) => {
                  const filtered = filterMetrics(metrics);
                  if (filtered.length === 0 && searchTerm) return null;
                  const catMeta = CATEGORY_META[category] || {};
                  const CatIcon = catMeta.icon || BarChart3;
                  const isExpanded = expandedCats[category];
                  const availableInCat = filtered.filter((m) => availableCodes.has(m.code));
                  const selectedInCat = filtered.filter((m) => selectedMetrics.includes(m.code));

                  return (
                    <div
                      key={category}
                      className="bg-white rounded-2xl border border-slate-200/60 overflow-hidden"
                    >
                      {/* Category header */}
                      <button
                        onClick={() => toggleCategory(category)}
                        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-slate-50/50 transition-colors"
                      >
                        <div
                          className={`w-9 h-9 rounded-lg flex items-center justify-center bg-${catMeta.color || "slate"}-100 text-${catMeta.color || "slate"}-600`}
                        >
                          <CatIcon className="w-5 h-5" />
                        </div>
                        <div className="text-left flex-1">
                          <p className="font-semibold text-slate-800">
                            {catMeta.label || category.charAt(0).toUpperCase() + category.slice(1)}
                          </p>
                          <p className="text-xs text-slate-400">
                            {availableInCat.length} available · {selectedInCat.length} selected
                          </p>
                        </div>
                        {isExpanded ? (
                          <ChevronDown className="w-5 h-5 text-slate-400" />
                        ) : (
                          <ChevronRight className="w-5 h-5 text-slate-400" />
                        )}
                      </button>

                      {isExpanded && (
                        <div className="px-5 pb-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                          {filtered.map((metric) => {
                            const isAvailable = availableCodes.has(metric.code);
                            const isSelected = selectedMetrics.includes(metric.code);
                            const missing = missingCols[metric.code] || [];
                            const ChIcon = CHART_ICONS[metric.default_chart_type] || BarChart3;

                            return (
                              <div
                                key={metric.code}
                                onClick={() => toggleMetric(metric.code)}
                                className={`relative flex items-start gap-3 p-4 rounded-xl border-2 transition-all ${
                                  isAvailable
                                    ? isSelected
                                      ? "border-indigo-400 bg-indigo-50/40 shadow-sm cursor-pointer"
                                      : "border-slate-200 bg-white hover:border-indigo-200 hover:bg-indigo-50/20 cursor-pointer"
                                    : "border-slate-100 bg-slate-50/60 cursor-not-allowed"
                                }`}
                              >
                                {/* Checkbox */}
                                <div className="mt-0.5">
                                  {isAvailable ? (
                                    isSelected ? (
                                      <CheckSquare className="w-5 h-5 text-indigo-600" />
                                    ) : (
                                      <Square className="w-5 h-5 text-slate-300" />
                                    )
                                  ) : (
                                    <Lock className="w-5 h-5 text-slate-300" />
                                  )}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <p
                                      className={`font-medium truncate ${
                                        isAvailable ? "text-slate-800" : "text-slate-400"
                                      }`}
                                    >
                                      {metric.name}
                                    </p>
                                    <ChIcon
                                      className={`w-4 h-4 shrink-0 ${
                                        isAvailable ? "text-slate-400" : "text-slate-300"
                                      }`}
                                    />
                                  </div>
                                  <p
                                    className={`text-xs leading-relaxed ${
                                      isAvailable ? "text-slate-500" : "text-slate-300"
                                    }`}
                                  >
                                    {metric.description}
                                  </p>

                                  {!isAvailable && missing.length > 0 && (
                                    <div className="mt-2 flex items-start gap-1.5 text-xs text-amber-600 bg-amber-50 rounded-lg px-2.5 py-1.5">
                                      <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                                      <span>
                                        Missing columns:{" "}
                                        <span className="font-medium">
                                          {missing.join(", ")}
                                        </span>
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

        {/* Bottom continue */}
        <div className="mt-8 flex justify-between">
          <button
            onClick={() => navigate("/analysis")}
            className="flex items-center gap-2 px-6 py-3 text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <button
            onClick={handleRunAnalysis}
            disabled={totalSelected === 0 || creating}
            className="flex items-center gap-2 px-8 py-3 bg-linear-to-r from-indigo-600 to-blue-600 text-white rounded-xl font-medium shadow-lg shadow-indigo-200/50 hover:from-indigo-700 hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none disabled:cursor-not-allowed transition-all"
          >
            {creating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                Run Analysis
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MetricsSelectionPage;
