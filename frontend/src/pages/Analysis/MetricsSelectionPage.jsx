import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
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
import { analyzeService, customAnalysisService, smartAnalysisService } from "../../services/api";
import {
  LLM_PROVIDERS,
  OPENROUTER_MODELS,
  DEFAULT_OLLAMA_MODEL,
  DEFAULT_OPENROUTER_MODEL,
} from "../../utils/llmConfig";
import DynamicChart from "../../components/analysis/DynamicChart";

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

// Derive the section ("analysis" | "kanban" | "cicd") + source_type from the
// current URL so the same page can serve all three DevOps domains.
const SECTION_TO_SOURCE = { analysis: null, kanban: "kanban", cicd: "cicd" };
const deriveSection = (pathname) => {
  const first = (pathname || "").split("/").filter(Boolean)[0];
  return SECTION_TO_SOURCE.hasOwnProperty(first) ? first : "analysis";
};

/* ------------------------------------------------------------------ */
/*  AIPlanPreview — shows the resolved plan before execution           */
/* ------------------------------------------------------------------ */
const AIPlanPreview = ({ plan, metricsMap }) => {
  const [showCode, setShowCode] = useState(false);

  if (!plan) return null;

  const modeBadge = {
    predefined:  { label: "Predefined Metrics",  color: "blue" },
    custom_dsl:  { label: "Custom DSL Analysis", color: "violet" },
    python_code: { label: "Python Analysis",      color: "emerald" },
  }[plan.mode] || { label: plan.mode, color: "gray" };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
          plan.mode === "predefined" ? "bg-blue-100 text-blue-600" :
          plan.mode === "custom_dsl" ? "bg-violet-100 text-violet-600" :
          "bg-emerald-100 text-emerald-600"
        }`}>
          <Bot className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-gray-800">Analysis Plan</h2>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            plan.mode === "predefined" ? "bg-blue-100 text-blue-700" :
            plan.mode === "custom_dsl" ? "bg-violet-100 text-violet-700" :
            "bg-emerald-100 text-emerald-700"
          }`}>{modeBadge.label}</span>
        </div>
      </div>

      {/* Predefined plan */}
      {plan.mode === "predefined" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <div className="rounded-xl border border-gray-200 bg-gray-50/70 p-4">
            <p className="text-xs font-medium tracking-wide text-gray-400 uppercase mb-2">Metrics ({plan.analyses.length})</p>
            <div className="flex flex-wrap gap-2">
              {plan.analyses.map((a) => (
                <span key={a.metric_code} className="px-2.5 py-1 rounded-full bg-blue-100 text-blue-700 text-xs font-medium">
                  {metricsMap.get(a.metric_code)?.name || a.metric_code}
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50/70 p-4">
            <p className="text-xs font-medium tracking-wide text-gray-400 uppercase mb-2">Visualization</p>
            <p className="text-sm font-medium text-gray-700">{plan.selection?.visualization || "Metric defaults"}</p>
            <p className="text-xs text-gray-500 mt-1">Chart type: {plan.selection?.chart_type || "default"}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50/70 p-4">
            <p className="text-xs font-medium tracking-wide text-gray-400 uppercase mb-2">Filters</p>
            <p className="text-sm text-gray-700">{(plan.selection?.filters?.authors || []).length} author filter(s)</p>
            <p className="text-sm text-gray-700">{plan.selection?.filters?.date_range ? "Date range applied" : "No date range"}</p>
          </div>
        </div>
      )}

      {/* Custom DSL plan */}
      {plan.mode === "custom_dsl" && plan.dsl_plan && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: "Chart", value: plan.dsl_plan.chart_type },
            { label: "Metric", value: plan.dsl_plan.metric || (plan.dsl_plan.series?.length > 0 ? `${plan.dsl_plan.series.length} series` : "—") },
            { label: "Aggregation", value: plan.dsl_plan.aggregation || "—" },
            {
              label: "Group By",
              value: plan.dsl_plan.group_by
                ? plan.dsl_plan.group_by.type === "time"
                  ? `${plan.dsl_plan.group_by.column} (${plan.dsl_plan.group_by.period})`
                  : plan.dsl_plan.group_by.column
                : "None",
            },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-xl border border-gray-200 bg-gray-50/70 p-3">
              <p className="text-xs font-medium tracking-wide text-gray-400 uppercase mb-1">{label}</p>
              <p className="text-sm font-semibold text-gray-800 capitalize">{value}</p>
            </div>
          ))}

          {plan.dsl_plan.filters?.length > 0 && (
            <div className="col-span-2 lg:col-span-4 rounded-xl border border-gray-200 bg-gray-50/70 p-3">
              <p className="text-xs font-medium tracking-wide text-gray-400 uppercase mb-2">Filters</p>
              <div className="flex flex-wrap gap-2">
                {plan.dsl_plan.filters.map((f, i) => (
                  <span key={i} className="text-xs px-2 py-1 bg-white border border-gray-200 rounded-lg text-gray-700">
                    {f.column} {f.op} {JSON.stringify(f.value)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {plan.dsl_plan.derived_column && (
            <div className="col-span-2 lg:col-span-4 rounded-xl border border-violet-200 bg-violet-50/50 p-3">
              <p className="text-xs font-medium tracking-wide text-violet-400 uppercase mb-1">Derived Column</p>
              <p className="text-sm font-mono text-violet-800">
                {plan.dsl_plan.derived_column.name} = {plan.dsl_plan.derived_column.formula}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Python code plan */}
      {plan.mode === "python_code" && (
        <div>
          {plan.reason && (
            <div className="mb-3 p-3 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-700">
              <strong>Why Python?</strong> {plan.reason}
            </div>
          )}
          <div className="rounded-xl border border-gray-200 overflow-hidden">
            <div
              className="flex items-center justify-between px-4 py-2 bg-gray-900 text-gray-300 text-xs cursor-pointer"
              onClick={() => setShowCode((v) => !v)}
            >
              <span className="font-mono">Generated Python code</span>
              <span>{showCode ? "▲ Hide" : "▼ Show"}</span>
            </div>
            {showCode && (
              <pre className="bg-gray-950 text-green-300 text-xs p-4 overflow-x-auto max-h-72 font-mono leading-relaxed">
                {plan.code}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Warnings */}
      {plan.warnings?.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
          <p className="text-sm font-medium text-amber-800 mb-2">Warnings</p>
          {plan.warnings.map((w) => (
            <div key={w} className="flex items-start gap-2 text-sm text-amber-700">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const MetricsSelectionPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const section = deriveSection(location.pathname);
  const sourceType = SECTION_TO_SOURCE[section];
  const dashboardPath = `/${section}/${datasetId}/dashboard`;
  const entryPath = `/${section}`;

  const [dataset, setDataset] = useState(null);
  const [allMetricsByCategory, setAllMetricsByCategory] = useState({});
  const [availableCodes, setAvailableCodes] = useState(new Set());
  const [availableMetricsMap, setAvailableMetricsMap] = useState(new Map());
  const [missingCols, setMissingCols] = useState({});
  const [selectionMode, setSelectionMode] = useState("manual");
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [llmPrompt, setLlmPrompt] = useState("");
  // planState: null | { mode: "predefined"|"custom_dsl"|"python_code"|"dsl_error", ...data }
  const [planState, setPlanState] = useState(null);
  const [llmProvider, setLlmProvider] = useState(LLM_PROVIDERS.OPENROUTER);
  const [llmModel, setLlmModel] = useState(DEFAULT_OPENROUTER_MODEL);

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
        analyzeService.getMetricsByCategory(sourceType),
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
  }, [datasetId, sourceType]);

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

  // ── Step 1: Resolve prompt → generate plan (no execution) ──────────────
  const handleResolve = async () => {
    if (!llmPrompt.trim()) {
      setError("Enter a prompt first.");
      return;
    }
    try {
      setCreating(true);
      setError(null);
      setPlanState(null);
      setCreatingMessage("Analysing your prompt…");

      const plan = await smartAnalysisService.preview(datasetId, llmPrompt.trim(), {
        model: llmModel,
        llmProvider,
      });

      if (plan.mode === "dsl_error") {
        setError(plan.error || "Could not resolve prompt. Try rephrasing.");
        return;
      }
      setPlanState(plan);
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "AI prompt resolution failed."));
    } finally {
      setCreating(false);
      setCreatingMessage("");
    }
  };

  // ── Step 2: Execute plan → navigate to dashboard ────────────────────────
  const handleExecutePlan = async () => {
    if (!planState) return;
    try {
      setCreating(true);
      setError(null);

      if (planState.mode === "predefined") {
        setCreatingMessage("Generating dashboards…");
        const results = await runAnalyses(planState.analyses);
        navigate(dashboardPath, {
          state: {
            results,
            dataset,
            selectionMode: "ai",
            automation: planState.selection,
            prompt: llmPrompt,
            warnings: planState.warnings || [],
          },
        });

      } else if (planState.mode === "custom_dsl") {
        setCreatingMessage("Executing custom DSL analysis…");
        const result = await customAnalysisService.runFromDsl(
          datasetId,
          planState.dsl_raw,
          llmPrompt.trim()
        );
        if (result.status === "dsl_error") {
          throw new Error(result.error || "DSL execution failed.");
        }
        navigate(dashboardPath, {
          state: {
            results: [{
              ...result,
              metric_code: "custom_dsl",
              is_custom: true,
            }],
            dataset,
            selectionMode: "ai",
            automation: { mode: "custom_dsl", dsl_plan: planState.dsl_plan },
            prompt: llmPrompt,
            warnings: [],
          },
        });

      } else if (planState.mode === "python_code") {
        setCreatingMessage("Executing Python analysis…");
        const result = await smartAnalysisService.runPython(
          datasetId,
          planState.code,
          llmPrompt.trim()
        );
        if (result.status === "python_error") {
          throw new Error(result.error || "Python execution failed.");
        }
        navigate(dashboardPath, {
          state: {
            results: [{
              ...result,
              metric_code: "custom_python",
              is_custom: true,
            }],
            dataset,
            selectionMode: "ai",
            automation: { mode: "python_code" },
            prompt: llmPrompt,
            warnings: [],
          },
        });
      }
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Execution failed. Refine the prompt or try again."));
    } finally {
      setCreating(false);
      setCreatingMessage("");
    }
  };

  // ── Manual mode run ─────────────────────────────────────────────────────
  const handleRunManual = async () => {
    const manualAnalyses = selectedMetrics.map((metricCode) => ({
      metric_code: metricCode,
      chart_type: availableMetricsMap.get(metricCode)?.default_chart_type,
      config: {},
    }));
    if (manualAnalyses.length === 0) return;

    try {
      setCreating(true);
      setError(null);
      setCreatingMessage("Generating dashboards…");
      const results = await runAnalyses(manualAnalyses);
      navigate(dashboardPath, {
        state: { results, dataset, selectionMode: "manual", automation: null, prompt: null, warnings: [] },
      });
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Analysis failed. Try again."));
    } finally {
      setCreating(false);
      setCreatingMessage("");
    }
  };

  const totalSelected =
    selectionMode === "manual"
      ? selectedMetrics.length
      : planState?.mode === "predefined" ? planState.analyses.length : 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading metrics catalogue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-6">
          <button
            onClick={() => navigate(entryPath)}
            className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to datasets
          </button>

          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-200/50">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Select Metrics</h1>
              <p className="text-sm text-gray-500">
                Step 2 — Choose what to analyze on{" "}
                <span className="font-medium text-gray-700">
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
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-200"
                    : step.done
                    ? "bg-green-100 text-green-700 border border-green-200"
                    : "bg-white text-gray-400 border border-gray-200"
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    step.active
                      ? "bg-white/20 text-white"
                      : step.done
                      ? "bg-green-200 text-green-700"
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  {step.done ? "✓" : step.n}
                </span>
                {step.label}
              </div>
              {index < 2 && <div className="w-8 h-px bg-gray-200" />}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 mb-6">
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
                    setPlanState(null);
                  }}
                  className={`text-left rounded-xl border p-4 transition-all ${
                    isActive
                      ? "border-blue-300 bg-blue-50/70 shadow-sm"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50/70"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        isActive ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-800">{meta.label}</p>
                      <p className="text-sm text-gray-500 mt-1">{meta.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 mb-6 sticky top-2 z-20">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  {selectionMode === "manual" ? (
                    <CheckSquare className="w-5 h-5 text-blue-600" />
                  ) : (
                    <Bot className="w-5 h-5 text-blue-600" />
                  )}
                </div>
                <div>
                  <p className="text-xs text-gray-400">
                    {selectionMode === "manual" ? "Selected" : "Resolved"}
                  </p>
                  <p className="text-xl font-bold text-gray-800">
                    {totalSelected}
                    <span className="text-sm font-normal text-gray-400 ml-1">
                      chart{totalSelected !== 1 ? "s" : ""}
                    </span>
                  </p>
                </div>
              </div>

              {selectionMode === "manual" ? (
                <button
                  onClick={selectAllAvailable}
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  {selectedMetrics.length === [...availableCodes].length
                    ? "Deselect all"
                    : "Select all available"}
                </button>
              ) : planState?.warnings?.length ? (
                <p className="text-xs text-amber-600">
                  {planState.warnings.length} warning{planState.warnings.length !== 1 ? "s" : ""}
                </p>
              ) : planState ? (
                <p className="text-xs text-green-600 font-medium">
                  Plan ready — review below and click Run
                </p>
              ) : (
                <p className="text-xs text-gray-400">
                  Resolve your prompt to preview the analysis plan.
                </p>
              )}
            </div>

            {selectionMode === "manual" ? (
              <button
                onClick={handleRunManual}
                disabled={creating || totalSelected === 0}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl font-medium shadow-lg shadow-blue-200/50 hover:bg-blue-700 disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed transition-all"
              >
                {creating ? (
                  <><Loader2 className="w-5 h-5 animate-spin" />{creatingMessage || "Generating..."}</>
                ) : (
                  <><Play className="w-5 h-5" />Run Analysis ({totalSelected})</>
                )}
              </button>
            ) : planState ? (
              <div className="flex gap-2">
                <button
                  onClick={() => setPlanState(null)}
                  disabled={creating}
                  className="flex items-center gap-2 px-4 py-3 border border-gray-200 rounded-xl text-gray-600 text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-all"
                >
                  Revise
                </button>
                <button
                  onClick={handleExecutePlan}
                  disabled={creating}
                  className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-xl font-medium shadow-lg shadow-green-200/50 hover:bg-green-700 disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed transition-all"
                >
                  {creating ? (
                    <><Loader2 className="w-5 h-5 animate-spin" />{creatingMessage || "Running..."}</>
                  ) : (
                    <><Play className="w-5 h-5" />Run Analysis</>
                  )}
                </button>
              </div>
            ) : (
              <button
                onClick={handleResolve}
                disabled={creating || !llmPrompt.trim()}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl font-medium shadow-lg shadow-blue-200/50 hover:bg-blue-700 disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed transition-all"
              >
                {creating ? (
                  <><Loader2 className="w-5 h-5 animate-spin" />{creatingMessage || "Resolving..."}</>
                ) : (
                  <><Sparkles className="w-5 h-5" />Resolve Prompt</>
                )}
              </button>
            )}
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
            <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-5">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-800">Describe the analysis</h2>
                  <p className="text-sm text-gray-500">
                    Example: "Show me commits over time for Alice in 2025 as a line chart."
                  </p>
                </div>
              </div>

              {/* LLM Provider & Model */}
              <div className="mb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Provider</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setLlmProvider(LLM_PROVIDERS.OPENROUTER);
                        setLlmModel(DEFAULT_OPENROUTER_MODEL);
                      }}
                      className={`flex-1 rounded-xl border px-3 py-2 text-sm font-medium transition-all ${
                        llmProvider === LLM_PROVIDERS.OPENROUTER
                          ? "border-blue-400 bg-blue-600 text-white"
                          : "border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      OpenRouter
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setLlmProvider(LLM_PROVIDERS.OLLAMA);
                        setLlmModel(DEFAULT_OLLAMA_MODEL);
                      }}
                      className={`flex-1 rounded-xl border px-3 py-2 text-sm font-medium transition-all ${
                        llmProvider === LLM_PROVIDERS.OLLAMA
                          ? "border-blue-400 bg-blue-600 text-white"
                          : "border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      Ollama (local)
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Model</label>
                  {llmProvider === LLM_PROVIDERS.OPENROUTER ? (
                    <select
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {OPENROUTER_MODELS.map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      placeholder="e.g. deepseek-r1, llama3.2"
                      className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                </div>
              </div>

              <textarea
                value={llmPrompt}
                onChange={(event) => {
                  setLlmPrompt(event.target.value);
                  setPlanState(null);
                  setError(null);
                }}
                placeholder="Show me commits over time"
                className="w-full min-h-36 rounded-xl border border-gray-200 bg-gray-50/60 px-4 py-3 text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
              />

              <div className="mt-4 p-3 rounded-xl bg-blue-50 border border-blue-200 text-sm text-blue-700 flex items-start gap-2">
                <Sparkles className="w-4 h-4 mt-0.5 shrink-0 text-blue-500" />
                The AI tries predefined metrics first, then generates a custom DSL analysis, and falls back to Python code for complex metrics.
              </div>
            </div>

            {planState && <AIPlanPreview plan={planState} metricsMap={availableMetricsMap} />}
          </div>
        ) : (
          <>
            <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 mb-6">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search metrics..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50/50 transition-all"
                />
              </div>
            </div>

            <div className="space-y-4">
              {Object.entries(allMetricsByCategory).length === 0 ? (
                <div className="bg-white rounded-xl border border-gray-200/60 p-12 text-center">
                  <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p className="text-gray-500">No metrics available.</p>
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
                      className="bg-white rounded-xl border border-gray-200/60 overflow-hidden"
                    >
                      <button
                        onClick={() => toggleCategory(category)}
                        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-gray-50/50 transition-colors"
                      >
                        <div
                          className={`w-9 h-9 rounded-lg flex items-center justify-center bg-${catMeta.color || "slate"}-100 text-${catMeta.color || "slate"}-600`}
                        >
                          <CatIcon className="w-5 h-5" />
                        </div>
                        <div className="text-left flex-1">
                          <p className="font-semibold text-gray-800">
                            {catMeta.label || category.charAt(0).toUpperCase() + category.slice(1)}
                          </p>
                          <p className="text-xs text-gray-400">
                            {availableInCat.length} available · {selectedInCat.length} selected
                          </p>
                        </div>
                        {isExpanded ? (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronRight className="w-5 h-5 text-gray-400" />
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
                                      ? "border-blue-400 bg-blue-50/40 shadow-sm cursor-pointer"
                                      : "border-gray-200 bg-white hover:border-blue-200 hover:bg-blue-50/20 cursor-pointer"
                                    : "border-gray-100 bg-gray-50/60 cursor-not-allowed"
                                }`}
                              >
                                <div className="mt-0.5">
                                  {isAvailable ? (
                                    isSelected ? (
                                      <CheckSquare className="w-5 h-5 text-blue-600" />
                                    ) : (
                                      <Square className="w-5 h-5 text-gray-300" />
                                    )
                                  ) : (
                                    <Lock className="w-5 h-5 text-gray-300" />
                                  )}
                                </div>

                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <p
                                      className={`font-medium truncate ${
                                        isAvailable ? "text-gray-800" : "text-gray-400"
                                      }`}
                                    >
                                      {metric.name}
                                    </p>
                                    <ChartIcon
                                      className={`w-4 h-4 shrink-0 ${
                                        isAvailable ? "text-gray-400" : "text-gray-300"
                                      }`}
                                    />
                                  </div>
                                  <p
                                    className={`text-xs leading-relaxed ${
                                      isAvailable ? "text-gray-500" : "text-gray-300"
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
            onClick={() => navigate(entryPath)}
            className="flex items-center gap-2 px-6 py-3 text-gray-600 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          {selectionMode === "manual" ? (
            <button
              onClick={handleRunManual}
              disabled={creating || totalSelected === 0}
              className="flex items-center gap-2 px-8 py-3 bg-blue-600 text-white rounded-xl font-medium shadow-lg shadow-blue-200/50 hover:bg-blue-700 disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed transition-all"
            >
              {creating ? (
                <><Loader2 className="w-5 h-5 animate-spin" />{creatingMessage || "Generating..."}</>
              ) : (
                <>Run Analysis ({totalSelected})<ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          ) : planState ? (
            <button
              onClick={handleExecutePlan}
              disabled={creating}
              className="flex items-center gap-2 px-8 py-3 bg-green-600 text-white rounded-xl font-medium shadow-lg shadow-green-200/50 hover:bg-green-700 disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed transition-all"
            >
              {creating ? (
                <><Loader2 className="w-5 h-5 animate-spin" />{creatingMessage || "Running..."}</>
              ) : (
                <>Run Analysis<ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          ) : (
            <button
              onClick={handleResolve}
              disabled={creating || !llmPrompt.trim()}
              className="flex items-center gap-2 px-8 py-3 bg-blue-600 text-white rounded-xl font-medium shadow-lg shadow-blue-200/50 hover:bg-blue-700 disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed transition-all"
            >
              {creating ? (
                <><Loader2 className="w-5 h-5 animate-spin" />{creatingMessage || "Resolving..."}</>
              ) : (
                <><Sparkles className="w-5 h-5" />Resolve Prompt<ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MetricsSelectionPage;
