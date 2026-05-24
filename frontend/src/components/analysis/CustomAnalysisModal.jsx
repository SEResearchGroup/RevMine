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

const buildInitialForm = () => {
  return {
    name: "Custom analysis",
    formula: "",
    output_column: "custom_metric",
    aggregation_scope: "mr",
    aggregation: "sum",
    chart_type: "bar",
    x_axis: "",
    time_aggregation: "M",
  };
};

const fieldClass =
  "w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500";

const CustomAnalysisModal = ({
  isOpen,
  columnsMetadata,
  onClose,
  onAdd,
  onSuggest,
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
  const [suggestion, setSuggestion] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

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

  const handleSuggest = async () => {
    if (!prompt.trim()) {
      setError("Describe the custom analysis first.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setWarnings([]);
      const preview = await onSuggest({
        prompt: prompt.trim(),
        llm_provider: provider,
        model,
      });
      const config = preview.suggestion?.config || {};
      const nextForm = {
        ...buildInitialForm(),
        ...config,
        name: config.name || preview.suggestion?.name || "Custom analysis",
        formula: config.formula || preview.suggestion?.formula || "",
        chart_type: preview.suggestion?.chart_type || config.chart_type || "bar",
      };
      setForm(nextForm);
      setSuggestion(preview.suggestion);
      setWarnings(preview.warnings || []);
      setMode("formula");
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.detail ||
          err?.message ||
          "Could not generate a custom formula."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = () => {
    if (!form.name.trim()) {
      setError("Name is required.");
      return;
    }
    if (!form.formula.trim()) {
      setError("Formula is required.");
      return;
    }
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
      config: {
        ...form,
        output_column: slugify(form.output_column || form.name),
        persist_column: true,
      },
    });
  };

  const dateColumns = columns.filter((col) =>
    ["datetime", "datetime_string"].includes(col.type)
  );
  const categoryColumns = columns.filter((col) =>
    ["categorical", "numeric", "numeric_categorical"].includes(col.type)
  );

  const xAxisOptions =
    form.aggregation_scope === "time"
      ? dateColumns
      : form.aggregation_scope === "category"
      ? categoryColumns
      : columns;

  return (
    <div className="fixed inset-0 z-50 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-4xl max-h-[92vh] overflow-hidden rounded-2xl bg-white shadow-2xl border border-gray-200 flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center">
              <Plus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Add Custom Analysis
              </h2>
              <p className="text-sm text-gray-500">
                Create a derived column and run it through the same chart pipeline.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 pt-4">
          <div className="inline-flex rounded-xl bg-gray-100 p-1">
            <button
              onClick={() => setMode("formula")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                mode === "formula"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Calculator className="w-4 h-4" />
              Formula
            </button>
            <button
              onClick={() => setMode("ai")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                mode === "ai"
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Sparkles className="w-4 h-4" />
              Natural language
            </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto">
          {mode === "ai" ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Provider
                  </label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setProvider(LLM_PROVIDERS.OPENROUTER);
                        setModel(DEFAULT_OPENROUTER_MODEL);
                      }}
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
                      onClick={() => {
                        setProvider(LLM_PROVIDERS.OLLAMA);
                        setModel(DEFAULT_OLLAMA_MODEL);
                      }}
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
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Model
                  </label>
                  {provider === LLM_PROVIDERS.OPENROUTER ? (
                    <select
                      value={model}
                      onChange={(event) => setModel(event.target.value)}
                      className={fieldClass}
                    >
                      {OPENROUTER_MODELS.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={model}
                      onChange={(event) => setModel(event.target.value)}
                      className={fieldClass}
                      placeholder="deepseek-r1"
                    />
                  )}
                </div>
              </div>

              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                className={`${fieldClass} min-h-32 resize-y`}
                placeholder="Example: Create a review effort score from commits, discussions, and reviewers, then show the monthly average."
              />

              <button
                onClick={handleSuggest}
                disabled={loading || !prompt.trim()}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Bot className="w-4 h-4" />
                )}
                Generate Formula
              </button>

              {suggestion && (
                <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">
                  Suggested: <span className="font-semibold">{suggestion.name}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-5">
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Name
                    </label>
                    <input
                      value={form.name}
                      onChange={(event) => handleNameChange(event.target.value)}
                      className={fieldClass}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Output column
                    </label>
                    <input
                      value={form.output_column}
                      onChange={(event) =>
                        updateForm({ output_column: slugify(event.target.value) })
                      }
                      className={fieldClass}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Formula
                  </label>
                  <textarea
                    value={form.formula}
                    onChange={(event) => updateForm({ formula: event.target.value })}
                    className={`${fieldClass} min-h-28 resize-y font-mono`}
                    placeholder="([#Commits] + [#Discussions]) / max([#reviewers], 1)"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Aggregation scope
                    </label>
                    <select
                      value={form.aggregation_scope}
                      onChange={(event) => handleScopeChange(event.target.value)}
                      className={fieldClass}
                    >
                      <option value="mr">Per MR</option>
                      <option value="time">By time</option>
                      <option value="category">By column</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Aggregation
                    </label>
                    <select
                      value={form.aggregation}
                      onChange={(event) =>
                        updateForm({ aggregation: event.target.value })
                      }
                      className={fieldClass}
                    >
                      {AGGREGATIONS.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Chart
                    </label>
                    <select
                      value={form.chart_type}
                      onChange={(event) =>
                        updateForm({ chart_type: event.target.value })
                      }
                      className={fieldClass}
                    >
                      {CHART_TYPES.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      X axis
                    </label>
                    <select
                      value={form.x_axis}
                      onChange={(event) => updateForm({ x_axis: event.target.value })}
                      className={fieldClass}
                    >
                      <option value="">Automatic</option>
                      {xAxisOptions.map((column) => (
                        <option key={column.name} value={column.name}>
                          {column.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Time grouping
                    </label>
                    <select
                      value={form.time_aggregation}
                      onChange={(event) =>
                        updateForm({ time_aggregation: event.target.value })
                      }
                      disabled={form.aggregation_scope !== "time"}
                      className={fieldClass}
                    >
                      {TIME_AGGREGATIONS.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
                <p className="text-xs font-semibold text-gray-500 mb-3">
                  Dataset columns
                </p>
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {columns.map((column) => (
                    <button
                      key={column.name}
                      onClick={() => insertColumn(column.name)}
                      className="w-full text-left rounded-lg border border-gray-200 bg-white px-3 py-2 hover:border-blue-200 hover:bg-blue-50"
                    >
                      <span className="block text-sm font-medium text-gray-700 truncate">
                        {column.name}
                      </span>
                      <span className="text-xs text-gray-400">{column.type}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {warnings.length > 0 && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
              {warnings.map((warning) => (
                <div key={warning} className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                  <span>{warning}</span>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-600 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-gray-100 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm font-medium text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            <Check className="w-4 h-4" />
            Add Analysis
          </button>
        </div>
      </div>
    </div>
  );
};

export default CustomAnalysisModal;
