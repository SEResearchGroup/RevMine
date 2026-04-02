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
  Sparkles,
  Bot,
} from "lucide-react";
import { analyzeService } from "../../services/api";

const CATEGORY_META = {
  timeseries: { icon: LineChart, color: "blue", label: "Time Series" },
  distribution: { icon: BarChart3, color: "violet", label: "Distribution" },
  correlation: { icon: ScatterChart, color: "emerald", label: "Correlation" },
  composition: { icon: PieChart, color: "amber", label: "Composition" },
  summary: { icon: Layers, color: "rose", label: "Summary" },
};

const CHART_ICONS = {
  line: LineChart,
  bar: BarChart3,
  pie: PieChart,
  scatter: ScatterChart,
  histogram: BarChart3,
  area: LineChart,
};

const MODE_META = {
  manual: {
    label: "Manual Selection",
    description: "Pick metrics exactly the way the current flow works.",
    icon: BarChart3,
  },
  ai: {
    label: "AI Prompt",
    description: "Describe the analysis in natural language and let the LLM map it.",
    icon: Sparkles,
  },
};

const buildGeneratePayload = (datasetId, analysis) => {
  const payload = {
    dataset_id: datasetId,
    metric_code: analysis.metric_code,
  };
  const config = analysis.config || {};

  if (analysis.chart_type) payload.chart_type = analysis.chart_type;
  if (config.x_axis) payload.x_axis = config.x_axis;
  if (config.y_axis) payload.y_axis = config.y_axis;
  if (config.aggregation) payload.aggregation = config.aggregation;
  if (config.time_aggregation) payload.time_aggregation = config.time_aggregation;
  if (config.filters && Object.keys(config.filters).length > 0) {
    payload.filters = config.filters;
  }

  return payload;
};

const getErrorMessage = (error, fallback) =>
  error?.response?.data?.error ||
  error?.response?.data?.detail?.message ||
  error?.response?.data?.detail ||
  error?.response?.data?.message ||
  error?.message ||
  fallback;

const MetricsSelectionPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();

  const [dataset, setDataset] = useState(null);
  const [allMetricsByCategory, setAllMetricsByCategory] = useState({});
  const [availableCodes, setAvailableCodes] = useState(new Set());
  const [availableMetricsMap, setAvailableMetricsMap] = useState(new Map());
  const [missingCols, setMissingCols] = useState({});
  const [selectionMode, setSelectionMode] = useState("manual");
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [llmPrompt, setLlmPrompt] = useState("");
  const [aiPreview, setAiPreview] = useState(null);

  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedCats, setExpandedCats] = useState({});
  const [creating, setCreating] = useState(false);
  const [creatingMessage, setCreatingMessage] = useState("");
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [datasetRes, allMetricsRes, availableRes] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getMetricsByCategory(),
        analyzeService.getAvailableMetrics(datasetId),
      ]);

      setDataset(datasetRes);
      setAllMetricsByCategory(allMetricsRes);

      const availableMetrics = availableRes.metrics || [];
      setAvailableCodes(new Set(availableMetrics.map((metric) => metric.code)));
      setAvailableMetricsMap(new Map(availableMetrics.map((metric) => [metric.code, metric])));
      setMissingCols(availableRes.missing_columns_by_metric || {});

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

  const toggleMetric = (code) => {
    if (!availableCodes.has(code)) return;
    setSelectedMetrics((prev) =>
      prev.includes(code) ? prev.filter((item) => item !== code) : [...prev, code]
    );
  };

  const toggleCategory = (cat) =>
    setExpandedCats((prev) => ({ ...prev, [cat]: !prev[cat] }));

  const selectAllAvailable = () => {
    const allAvailable = [];
    Object.values(allMetricsByCategory).forEach((metrics) => {
      (Array.isArray(metrics) ? metrics : []).forEach((metric) => {
        if (availableCodes.has(metric.code)) allAvailable.push(metric.code);
      });
    });

    if (selectedMetrics.length === allAvailable.length) setSelectedMetrics([]);
    else setSelectedMetrics(allAvailable);
  };

  const filterMetrics = (metrics) =>
    (Array.isArray(metrics) ? metrics : []).filter(
      (metric) =>
        (metric.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (metric.code || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (metric.description || "").toLowerCase().includes(searchTerm.toLowerCase())
    );

  const runAnalyses = async (analyses) => {
    const results = [];

    for (const analysis of analyses) {
      try {
        const result = await analyzeService.generateChart(
          buildGeneratePayload(datasetId, analysis)
        );
        results.push(result);
      } catch (err) {
        console.error(`Failed metric ${analysis.metric_code}:`, err);
        results.push({
          metric_code: analysis.metric_code,
          chart_type: analysis.chart_type,
          error: true,
          message: getErrorMessage(err, "Failed to generate chart."),
        });
      }
    }

    return results;
  };

  const handleRunAnalysis = async () => {
    const isManual = selectionMode === "manual";
    const manualAnalyses = selectedMetrics.map((metricCode) => ({
      metric_code: metricCode,
      chart_type: availableMetricsMap.get(metricCode)?.default_chart_type,
      config: {},
    }));

    if (isManual && manualAnalyses.length === 0) return;
    if (!isManual && !llmPrompt.trim()) {
      setError("Enter an AI prompt or switch back to manual selection.");
      return;
    }

    try {
      setCreating(true);
      setError(null);

      let analysesToRun = manualAnalyses;
      let preview = aiPreview;

      if (!isManual) {
        setCreatingMessage("Resolving prompt...");
        preview = await analyzeService.previewAnalysisPrompt({
          dataset_id: datasetId,
          prompt: llmPrompt.trim(),
        });
        setAiPreview(preview);
        analysesToRun = preview.analyses || [];

        if (analysesToRun.length === 0) {
          throw new Error("The AI response did not resolve to any runnable metrics.");
        }
      }

      setCreatingMessage("Generating dashboards...");
      const results = await runAnalyses(analysesToRun);

      navigate(`/analysis/${datasetId}/dashboard`, {
        state: {
          results,
          dataset,
          selectionMode,
          automation: preview?.selection || null,
          prompt: preview?.prompt || null,
          warnings: preview?.warnings || [],
        },
      });
    } catch (err) {
      console.error(err);
      if (selectionMode === "ai") {
        setAiPreview(null);
      }
      setError(
        selectionMode === "ai"
          ? `${getErrorMessage(err, "AI prompt analysis failed.")} You can refine the prompt or switch to manual selection.`
          : getErrorMessage(err, "Analysis failed. Try again.")
      );
    } finally {
      setCreating(false);
      setCreatingMessage("");
    }
  };

  const totalSelected =
    selectionMode === "manual"
      ? selectedMetrics.length
      : aiPreview?.analyses?.length || 0;

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
              <h1 className="text-2xl font-bold text-slate-800">Select Metrics</h1>
              <p className="text-sm text-slate-500">
                Step 2 — Choose what to analyze on{" "}
                <span className="font-medium text-slate-700">
                  {dataset?.name || dataset?.original_filename || dataset?.filename}
                </span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 mb-8">
          {[
            { n: 1, label: "Dataset", done: true },
            { n: 2, label: "Metrics", active: true },
            { n: 3, label: "Dashboard" },
          ].map((step, index) => (
            <div key={index} className="flex items-center gap-3">
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
              {index < 2 && <div className="w-8 h-px bg-slate-200" />}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(MODE_META).map(([mode, meta]) => {
              const Icon = meta.icon;
              const isActive = selectionMode === mode;

              return (
                <button
                  key={mode}
                  onClick={() => {
                    setSelectionMode(mode);
                    setError(null);
                  }}
                  className={`text-left rounded-2xl border p-4 transition-all ${
                    isActive
                      ? "border-indigo-300 bg-indigo-50/70 shadow-sm"
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50/70"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        isActive ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800">{meta.label}</p>
                      <p className="text-sm text-slate-500 mt-1">{meta.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-4 mb-6 sticky top-2 z-20">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                  {selectionMode === "manual" ? (
                    <CheckSquare className="w-5 h-5 text-indigo-600" />
                  ) : (
                    <Bot className="w-5 h-5 text-indigo-600" />
                  )}
                </div>
                <div>
                  <p className="text-xs text-slate-400">
                    {selectionMode === "manual" ? "Selected" : "Resolved"}
                  </p>
                  <p className="text-xl font-bold text-slate-800">
                    {totalSelected}
                    <span className="text-sm font-normal text-slate-400 ml-1">
                      chart{totalSelected !== 1 ? "s" : ""}
                    </span>
                  </p>
                </div>
              </div>

              {selectionMode === "manual" ? (
                <button
                  onClick={selectAllAvailable}
                  className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  {selectedMetrics.length === [...availableCodes].length
                    ? "Deselect all"
                    : "Select all available"}
                </button>
              ) : aiPreview?.warnings?.length ? (
                <p className="text-xs text-amber-600">
                  {aiPreview.warnings.length} warning{aiPreview.warnings.length !== 1 ? "s" : ""}
                </p>
              ) : (
                <p className="text-xs text-slate-400">
                  The prompt will be validated before charts run.
                </p>
              )}
            </div>

            <button
              onClick={handleRunAnalysis}
              disabled={
                creating ||
                (selectionMode === "manual" && totalSelected === 0) ||
                (selectionMode === "ai" && !llmPrompt.trim())
              }
              className="flex items-center gap-2 px-6 py-3 bg-linear-to-r from-indigo-600 to-blue-600 text-white rounded-xl font-medium shadow-lg shadow-indigo-200/50 hover:from-indigo-700 hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none disabled:cursor-not-allowed transition-all"
            >
              {creating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {creatingMessage || "Generating..."}
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  {selectionMode === "manual"
                    ? `Run Analysis (${totalSelected})`
                    : "Resolve Prompt & Run"}
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}
        </div>

        {selectionMode === "ai" ? (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-5">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">Describe the analysis</h2>
                  <p className="text-sm text-slate-500">
                    Example: "Show me commits over time for Alice in 2025 as a line chart."
                  </p>
                </div>
              </div>

              <textarea
                value={llmPrompt}
                onChange={(event) => {
                  setLlmPrompt(event.target.value);
                  setAiPreview(null);
                  setError(null);
                }}
                placeholder="Show me commits over time"
                className="w-full min-h-36 rounded-2xl border border-slate-200 bg-slate-50/60 px-4 py-3 text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y"
              />

              <div className="mt-4 p-3 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-600 flex items-start gap-2">
                <Info className="w-4 h-4 mt-0.5 shrink-0 text-slate-400" />
                The prompt goes through the API gateway, gets normalized against this dataset's available metrics, and then runs through the same chart generation pipeline as manual mode.
              </div>
            </div>

            {aiPreview && (
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Bot className="w-5 h-5 text-indigo-600" />
                  <h2 className="text-lg font-semibold text-slate-800">AI Resolution</h2>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
                  <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                    <p className="text-xs font-medium tracking-wide text-slate-400 uppercase mb-2">
                      Metrics
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {(aiPreview.selection?.metrics || []).map((metricCode) => (
                        <span
                          key={metricCode}
                          className="px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-700 text-xs font-medium"
                        >
                          {availableMetricsMap.get(metricCode)?.name || metricCode}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                    <p className="text-xs font-medium tracking-wide text-slate-400 uppercase mb-2">
                      Visualization
                    </p>
                    <p className="text-sm font-medium text-slate-700">
                      {aiPreview.selection?.visualization || "Metric defaults"}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Applied chart type: {aiPreview.selection?.chart_type || "default"}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                    <p className="text-xs font-medium tracking-wide text-slate-400 uppercase mb-2">
                      Filters
                    </p>
                    <p className="text-sm text-slate-700">
                      {(aiPreview.selection?.filters?.authors || []).length} author filter
                      {(aiPreview.selection?.filters?.authors || []).length !== 1 ? "s" : ""}
                    </p>
                    <p className="text-sm text-slate-700">
                      {(aiPreview.selection?.filters?.repositories || []).length} repository filter
                      {(aiPreview.selection?.filters?.repositories || []).length !== 1 ? "s" : ""}
                    </p>
                    <p className="text-sm text-slate-700">
                      {aiPreview.selection?.filters?.date_range ? "Date range applied" : "No date range"}
                    </p>
                  </div>
                </div>

                {aiPreview.warnings?.length > 0 && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                    <p className="text-sm font-medium text-amber-800 mb-2">Warnings</p>
                    <div className="space-y-2">
                      {aiPreview.warnings.map((warning) => (
                        <div
                          key={warning}
                          className="flex items-start gap-2 text-sm text-amber-700"
                        >
                          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                          <span>{warning}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-4 mb-6">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search metrics..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="w-full pl-12 pr-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-slate-50/50 transition-all"
                />
              </div>
            </div>

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
                  const availableInCat = filtered.filter((metric) => availableCodes.has(metric.code));
                  const selectedInCat = filtered.filter((metric) => selectedMetrics.includes(metric.code));

                  return (
                    <div
                      key={category}
                      className="bg-white rounded-2xl border border-slate-200/60 overflow-hidden"
                    >
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
                            const ChartIcon =
                              CHART_ICONS[metric.default_chart_type] || BarChart3;

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

                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <p
                                      className={`font-medium truncate ${
                                        isAvailable ? "text-slate-800" : "text-slate-400"
                                      }`}
                                    >
                                      {metric.name}
                                    </p>
                                    <ChartIcon
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
                                        <span className="font-medium">{missing.join(", ")}</span>
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
          </>
        )}

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
            disabled={
              creating ||
              (selectionMode === "manual" && totalSelected === 0) ||
              (selectionMode === "ai" && !llmPrompt.trim())
            }
            className="flex items-center gap-2 px-8 py-3 bg-linear-to-r from-indigo-600 to-blue-600 text-white rounded-xl font-medium shadow-lg shadow-indigo-200/50 hover:from-indigo-700 hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none disabled:cursor-not-allowed transition-all"
          >
            {creating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {creatingMessage || "Generating..."}
              </>
            ) : (
              <>
                {selectionMode === "manual" ? "Run Analysis" : "Resolve Prompt & Run"}
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
