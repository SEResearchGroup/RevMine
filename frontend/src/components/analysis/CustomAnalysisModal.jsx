import { useMemo, useState } from "react";
import {
  AlertCircle,
  Bot,
  Calculator,
  Check,
  Loader2,
  Plus,
  Sparkles,
  X,
  Zap,
  ChevronRight,
} from "lucide-react";
import {
  DEFAULT_OLLAMA_MODEL,
  DEFAULT_OPENROUTER_MODEL,
  LLM_PROVIDERS,
  OPENROUTER_MODELS,
} from "../../utils/llmConfig";

const AGGREGATIONS = ["sum", "mean", "median", "count", "min", "max", "std"];
const TIME_AGGREGATIONS = [
  { value: "D", label: "Daily" },
  { value: "W", label: "Weekly" },
  { value: "M", label: "Monthly" },
  { value: "Q", label: "Quarterly" },
  { value: "Y", label: "Yearly" },
];
const CHART_TYPES = ["bar", "line", "area", "scatter"];

const SCENARIO_LABELS = {
  csv_existing: "Existing columns",
  csv_derived: "Derived metric",
  raw_json: "Raw data needed",
};
const SCENARIO_COLORS = {
  csv_existing: "bg-emerald-100 text-emerald-700",
  csv_derived: "bg-blue-100 text-blue-700",
  raw_json: "bg-amber-100 text-amber-700",
};

const columnType = (meta) =>
  typeof meta === "object" && meta !== null
    ? meta.type || meta.dtype || "unknown"
    : String(meta || "unknown");

const slugify = (value) => {
  const cleaned = (value || "custom_metric")
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return /^[0-9]/.test(cleaned) ? `custom_${cleaned}` : cleaned || "custom_metric";
};

const buildInitialForm = () => ({
  name: "Custom analysis",
  formula: "",
  output_column: "custom_metric",
  aggregation_scope: "mr",
  aggregation: "sum",
  chart_type: "bar",
  x_axis: "",
  time_aggregation: "M",
});

const fieldClass =
  "w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500";

/**
 * CustomAnalysisModal
 *
 * Props
 * -----
 * isOpen            – boolean
 * columnsMetadata   – dataset column schema
 * onClose           – () => void
 * onAdd             – (analysis) => void   — old formula-queue flow
 * onSuggest         – (payload) => Promise  — preview-formula flow (old AI tab)
 * onDirectGenerate  – (payload) => Promise  — new one-shot NL→chart pipeline
 * onDirectResult    – (result)  => void    — called when user accepts direct result
 */
const CustomAnalysisModal = ({
  isOpen,
  columnsMetadata,
  onClose,
  onAdd,
  onSuggest,
  onDirectGenerate,
  onDirectResult,
}) => {
  const columns = useMemo(
    () =>
      Object.entries(columnsMetadata || {}).map(([name, meta]) => ({
        name,
        type: columnType(meta),
      })),
    [columnsMetadata]
  );

  const [mode, setMode] = useState("formula");
  const [form, setForm] = useState(() => buildInitialForm());
  const [prompt, setPrompt] = useState("");
  const [provider, setProvider] = useState(LLM_PROVIDERS.OPENROUTER);
  const [model, setModel] = useState(DEFAULT_OPENROUTER_MODEL);

  // Old preview-formula flow
  const [suggestion, setSuggestion] = useState(null);
  const [loading, setLoading] = useState(false);

  // New direct-generate flow
  const [directLoading, setDirectLoading] = useState(false);
  const [directResult, setDirectResult] = useState(null);

  const [warnings, setWarnings] = useState([]);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const resetAiState = () => {
    setSuggestion(null);
    setDirectResult(null);
    setWarnings([]);
    setError(null);
  };

  const updateForm = (patch) => {
    setForm((prev) => ({ ...prev, ...patch }));
    setError(null);
  };

  const handleNameChange = (name) => {
    updateForm({
      name,
      output_column:
        !form.output_column || form.output_column === slugify(form.name)
          ? slugify(name)
          : form.output_column,
    });
  };

  const handleScopeChange = (scope) => {
    const firstDate = columns.find((col) =>
      ["datetime", "datetime_string"].includes(col.type)
    );
    const firstCategory = columns.find((col) =>
      ["categorical", "numeric_categorical"].includes(col.type)
    );
    updateForm({
      aggregation_scope: scope,
      chart_type: scope === "time" ? "line" : "bar",
      x_axis:
        scope === "time"
          ? firstDate?.name || ""
          : scope === "category"
          ? firstCategory?.name || ""
          : "",
    });
  };

  const insertColumn = (columnName) => {
    updateForm({
      formula: `${form.formula}${form.formula.trim() ? " " : ""}[${columnName}]`,
    });
  };

  // --- Old flow: preview formula, then edit in Formula tab ---
  const handleSuggest = async () => {
    if (!prompt.trim()) {
      setError("Describe the custom analysis first.");
      return;
    }
    try {
      setLoading(true);
      resetAiState();
      const preview = await onSuggest({ prompt: prompt.trim(), llm_provider: provider, model });
      const config = preview.suggestion?.config || {};
      setForm({
        ...buildInitialForm(),
        ...config,
        name: config.name || preview.suggestion?.name || "Custom analysis",
        formula: config.formula || preview.suggestion?.formula || "",
        chart_type: preview.suggestion?.chart_type || config.chart_type || "bar",
      });
      setSuggestion(preview.suggestion);
      setWarnings(preview.warnings || []);
      setMode("formula");
    } catch (err) {
      setError(
        err?.response?.data?.error || err?.message || "Could not generate a formula."
      );
    } finally {
      setLoading(false);
    }
  };

  // --- New flow: one-shot NL→chart, returns complete result ---
  const handleDirectGenerate = async () => {
    if (!prompt.trim()) {
      setError("Describe the analysis first.");
      return;
    }
    if (!onDirectGenerate) {
      setError("Direct generation is not configured.");
      return;
    }
    try {
      setDirectLoading(true);
      resetAiState();
      const result = await onDirectGenerate({ prompt: prompt.trim(), provider, model });
      setDirectResult(result);
      setWarnings(result.warnings || []);
    } catch (err) {
      setError(
        err?.response?.data?.error || err?.message || "Could not generate the chart."
      );
    } finally {
      setDirectLoading(false);
    }
  };

  // --- Old formula submit ---
  const handleSubmit = () => {
    if (!form.name.trim()) { setError("Name is required."); return; }
    if (!form.formula.trim()) { setError("Formula is required."); return; }
    if (form.aggregation_scope === "time" && !form.x_axis) {
      setError("Choose a date column for time aggregation.");
      return;
    }
    if (form.aggregation_scope === "category" && !form.x_axis) {
      setError("Choose a grouping column for category aggregation.");
      return;
    }
    onAdd({
      metric_code: "custom_formula",
      name: form.name.trim(),
      chart_type: form.chart_type,
      config: { ...form, output_column: slugify(form.output_column || form.name), persist_column: true },
    });
  };

  const dateColumns = columns.filter((col) => ["datetime", "datetime_string"].includes(col.type));
  const categoryColumns = columns.filter((col) =>
    ["categorical", "numeric", "numeric_categorical"].includes(col.type)
  );
  const xAxisOptions =
    form.aggregation_scope === "time"
      ? dateColumns
      : form.aggregation_scope === "category"
      ? categoryColumns
      : columns;

  const anyLoading = loading || directLoading;

  return (
    <div className="fixed inset-0 z-50 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-4xl max-h-[92vh] overflow-hidden rounded-2xl bg-white shadow-2xl border border-gray-200 flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center">
              <Plus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-800">Add Custom Analysis</h2>
              <p className="text-sm text-gray-500">
                Build a formula manually or generate a chart directly from natural language.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode tabs */}
        <div className="px-6 pt-4">
          <div className="inline-flex rounded-xl bg-gray-100 p-1">
            <button
              onClick={() => setMode("formula")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                mode === "formula" ? "bg-white text-blue-600 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Calculator className="w-4 h-4" />
              Formula
            </button>
            <button
              onClick={() => setMode("ai")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                mode === "ai" ? "bg-white text-blue-600 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Sparkles className="w-4 h-4" />
              Natural language
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {mode === "ai" ? (
            <div className="space-y-4">
              {/* Provider + Model */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Provider</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => { setProvider(LLM_PROVIDERS.OPENROUTER); setModel(DEFAULT_OPENROUTER_MODEL); }}
                      className={`flex-1 rounded-xl border px-3 py-2 text-sm font-medium ${
                        provider === LLM_PROVIDERS.OPENROUTER
                          ? "border-blue-500 bg-blue-600 text-white"
                          : "border-gray-200 bg-gray-50 text-gray-700"
                      }`}
                    >
                      OpenRouter
                    </button>
                    <button
                      type="button"
                      onClick={() => { setProvider(LLM_PROVIDERS.OLLAMA); setModel(DEFAULT_OLLAMA_MODEL); }}
                      className={`flex-1 rounded-xl border px-3 py-2 text-sm font-medium ${
                        provider === LLM_PROVIDERS.OLLAMA
                          ? "border-blue-500 bg-blue-600 text-white"
                          : "border-gray-200 bg-gray-50 text-gray-700"
                      }`}
                    >
                      Ollama
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Model</label>
                  {provider === LLM_PROVIDERS.OPENROUTER ? (
                    <select value={model} onChange={(e) => setModel(e.target.value)} className={fieldClass}>
                      {OPENROUTER_MODELS.map((item) => (
                        <option key={item.id} value={item.id}>{item.name}</option>
                      ))}
                    </select>
                  ) : (
                    <input value={model} onChange={(e) => setModel(e.target.value)} className={fieldClass} placeholder="deepseek-r1" />
                  )}
                </div>
              </div>

              {/* Prompt */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Prompt</label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className={`${fieldClass} min-h-28 resize-y`}
                  placeholder="Example: Average review effort score per author combining commits, discussions and reviewers, shown as a bar chart by author."
                />
              </div>

              {/* Action buttons */}
              <div className="flex flex-wrap gap-2">
                {/* Old flow: preview formula for editing */}
                <button
                  onClick={handleSuggest}
                  disabled={anyLoading || !prompt.trim()}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-blue-200 bg-white text-blue-700 text-sm font-medium hover:bg-blue-50 disabled:opacity-40"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                  Preview Formula
                </button>

                {/* New flow: one-shot chart generation */}
                {onDirectGenerate && (
                  <button
                    onClick={handleDirectGenerate}
                    disabled={anyLoading || !prompt.trim()}
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300"
                  >
                    {directLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                    Generate Chart Now
                  </button>
                )}
              </div>

              {/* Old flow: brief suggestion acknowledgement */}
              {suggestion && !directResult && (
                <div className="rounded-xl border border-blue-100 bg-blue-50 p-3 flex items-center gap-2 text-sm text-blue-800">
                  <Check className="w-4 h-4 text-blue-600 shrink-0" />
                  Formula for <span className="font-semibold mx-1">{suggestion.name}</span>
                  loaded in Formula tab — review and add from there.
                  <ChevronRight className="w-4 h-4 ml-auto text-blue-400" />
                </div>
              )}

              {/* New flow: direct result plan card */}
              {directResult && (
                <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50/50 p-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-emerald-500 text-white flex items-center justify-center shrink-0">
                        <Zap className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="font-semibold text-gray-800">{directResult.plan?.name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{directResult.plan?.explanation}</p>
                      </div>
                    </div>
                    <span className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full ${
                      SCENARIO_COLORS[directResult.scenario] || "bg-gray-100 text-gray-600"
                    }`}>
                      {SCENARIO_LABELS[directResult.scenario] || directResult.scenario}
                    </span>
                  </div>

                  {directResult.plan?.formula && (
                    <div className="rounded-lg border border-emerald-200 bg-white p-2.5">
                      <p className="text-xs font-medium text-gray-500 mb-1">Formula</p>
                      <code className="text-xs font-mono text-blue-700 break-all">
                        {directResult.plan.formula}
                      </code>
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                    <span className="px-2 py-0.5 rounded-full bg-gray-100">{directResult.plan?.aggregation_scope}</span>
                    <span>·</span>
                    <span>{directResult.plan?.aggregation}</span>
                    <span>·</span>
                    <span>{directResult.plan?.chart_type} chart</span>
                    {directResult.plan?.x_axis && (
                      <>
                        <span>·</span>
                        <span>x: {directResult.plan.x_axis}</span>
                      </>
                    )}
                  </div>

                  {(directResult.warnings || []).length > 0 && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 space-y-1">
                      {directResult.warnings.map((w) => (
                        <div key={w} className="flex items-start gap-1.5 text-xs text-amber-700">
                          <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <p className="text-xs text-emerald-700 font-medium">
                    Chart generated successfully — click "Add to Dashboard" below to include it.
                  </p>
                </div>
              )}
            </div>
          ) : (
            /* Formula mode — unchanged */
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-5">
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
                    <input value={form.name} onChange={(e) => handleNameChange(e.target.value)} className={fieldClass} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Output column</label>
                    <input
                      value={form.output_column}
                      onChange={(e) => updateForm({ output_column: slugify(e.target.value) })}
                      className={fieldClass}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Formula</label>
                  <textarea
                    value={form.formula}
                    onChange={(e) => updateForm({ formula: e.target.value })}
                    className={`${fieldClass} min-h-28 resize-y font-mono`}
                    placeholder="([#Commits] + [#Discussions]) / max([#reviewers], 1)"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Aggregation scope</label>
                    <select value={form.aggregation_scope} onChange={(e) => handleScopeChange(e.target.value)} className={fieldClass}>
                      <option value="mr">Per MR</option>
                      <option value="time">By time</option>
                      <option value="category">By column</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Aggregation</label>
                    <select value={form.aggregation} onChange={(e) => updateForm({ aggregation: e.target.value })} className={fieldClass}>
                      {AGGREGATIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Chart</label>
                    <select value={form.chart_type} onChange={(e) => updateForm({ chart_type: e.target.value })} className={fieldClass}>
                      {CHART_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">X axis</label>
                    <select value={form.x_axis} onChange={(e) => updateForm({ x_axis: e.target.value })} className={fieldClass}>
                      <option value="">Automatic</option>
                      {xAxisOptions.map((col) => <option key={col.name} value={col.name}>{col.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Time grouping</label>
                    <select
                      value={form.time_aggregation}
                      onChange={(e) => updateForm({ time_aggregation: e.target.value })}
                      disabled={form.aggregation_scope !== "time"}
                      className={fieldClass}
                    >
                      {TIME_AGGREGATIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              {/* Column palette */}
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
                <p className="text-xs font-semibold text-gray-500 mb-3">Dataset columns</p>
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {columns.map((col) => (
                    <button
                      key={col.name}
                      onClick={() => insertColumn(col.name)}
                      className="w-full text-left rounded-lg border border-gray-200 bg-white px-3 py-2 hover:border-blue-200 hover:bg-blue-50"
                    >
                      <span className="block text-sm font-medium text-gray-700 truncate">{col.name}</span>
                      <span className="text-xs text-gray-400">{col.type}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
              {warnings.map((w) => (
                <div key={w} className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-600 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-gray-100 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm font-medium text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>

          {/* Show "Add to Dashboard" when we have a direct result */}
          {directResult && onDirectResult ? (
            <button
              onClick={() => onDirectResult(directResult)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700"
            >
              <Check className="w-4 h-4" />
              Add to Dashboard
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
            >
              <Check className="w-4 h-4" />
              Add Analysis
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default CustomAnalysisModal;
