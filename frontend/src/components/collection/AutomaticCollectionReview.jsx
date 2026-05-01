import { AlertTriangle, Bot, CheckCircle2, Info, Loader2, Sparkles } from "lucide-react";
import { FEATURE_LABELS, KEYWORD_FIELD_LABELS } from "./collectionFeatureConfig";
import {
  LLM_PROVIDERS,
  OPENROUTER_MODELS,
  DEFAULT_OLLAMA_MODEL,
  DEFAULT_OPENROUTER_MODEL,
} from "../../utils/llmConfig";

function AutomaticCollectionReview({
  draft,
  warnings,
  metricLabels,
  generating,
  submitting,
  error,
  onGenerate,
  onApprove,
  prompt,
  onPromptChange,
  llmProvider,
  onProviderChange,
  llmModel,
  onModelChange,
}) {
  const keywordFilters = draft?.cleaning?.filters?.keyword_filters || [];
  const selectedFeatures = draft?.cleaning?.selected_features || [];
  const selectedMetrics = draft?.collection?.selected_metrics || [];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-5">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800">Describe the collection</h3>
            <p className="text-sm text-gray-500">
              Describe what to collect and clean. A draft will be generated for your review before any data is collected.
            </p>
          </div>
        </div>

        {/* LLM Provider & Model selector */}
        <div className="mb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Provider</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  onProviderChange(LLM_PROVIDERS.OPENROUTER);
                  onModelChange(DEFAULT_OPENROUTER_MODEL);
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
                  onProviderChange(LLM_PROVIDERS.OLLAMA);
                  onModelChange(DEFAULT_OLLAMA_MODEL);
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
                onChange={(e) => onModelChange(e.target.value)}
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
                onChange={(e) => onModelChange(e.target.value)}
                placeholder="e.g. deepseek-r1, llama3.2"
                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
          </div>
        </div>

        <label className="block text-xs font-medium text-gray-600 mb-1">
          Prompt
        </label>
        <textarea
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          rows={4}
          placeholder="Collect merged pull requests from the last 6 months on main, then clean for Python files and bug-related titles."
          className="w-full min-h-28 resize-y rounded-xl border border-gray-200 bg-gray-50/60 px-4 py-3 text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />

        <div className="mt-3 p-3 rounded-xl bg-gray-50 border border-gray-200 text-sm text-gray-600 flex items-start gap-2">
          <Info className="w-4 h-4 mt-0.5 shrink-0 text-gray-400" />
          The generated configuration is treated as untrusted until you review and approve it. The next step reuses the same collect-plan validation as manual mode.
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={onGenerate}
            disabled={generating || submitting || !prompt.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {generating ? "Generating draft..." : "Generate draft"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {submitting && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-amber-700" />
            <div>
              <p className="font-medium text-amber-900">Preparing collect plan</p>
              <p className="text-sm text-amber-800">
                Reusing the same validation workflow as manual mode before execution.
              </p>
            </div>
          </div>
        </div>
      )}

      {draft && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Review Generated Draft</h3>
              <p className="text-sm text-gray-600">
                Validate the collection and cleaning configuration before execution.
              </p>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full bg-green-50 px-3 py-1 text-sm font-medium text-green-700">
              <CheckCircle2 className="w-4 h-4" />
              Validation required
            </span>
          </div>

          {warnings?.length > 0 && (
            <div className="mb-5 rounded-xl border border-yellow-200 bg-yellow-50 p-4">
              <div className="flex items-center gap-2 mb-2 text-yellow-800">
                <AlertTriangle className="w-4 h-4" />
                <p className="font-medium">Warnings</p>
              </div>
              <ul className="space-y-2 text-sm text-yellow-900">
                {warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <section className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <h4 className="font-semibold text-gray-900 mb-3">Collection</h4>
              <div className="space-y-3 text-sm text-gray-700">
                <p>
                  <span className="font-medium text-gray-900">Branch:</span>{" "}
                  {draft.collection.branch_name || "Default branch"}
                </p>
                <p>
                  <span className="font-medium text-gray-900">Date range:</span>{" "}
                  {draft.collection.start_date || "Any"} to {draft.collection.end_date || "Any"}
                </p>
                <p>
                  <span className="font-medium text-gray-900">Statuses:</span>{" "}
                  {draft.collection.status?.length > 0
                    ? draft.collection.status.join(", ")
                    : "All"}
                </p>
                <div>
                  <p className="font-medium text-gray-900 mb-2">
                    Metrics ({selectedMetrics.length})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {selectedMetrics.map((metric) => (
                      <span
                        key={metric}
                        className="rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-blue-800"
                      >
                        {metricLabels[metric] || metric}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <h4 className="font-semibold text-gray-900 mb-3">Cleaning</h4>
              <div className="space-y-3 text-sm text-gray-700">
                <p>
                  <span className="font-medium text-gray-900">Refined date range:</span>{" "}
                  {draft.cleaning.start_date || "Any"} to {draft.cleaning.end_date || "Any"}
                </p>
                <p>
                  <span className="font-medium text-gray-900">File extensions:</span>{" "}
                  {draft.cleaning.filters.file_extensions?.length > 0
                    ? draft.cleaning.filters.file_extensions.join(", ")
                    : "No extension filter"}
                </p>
                <p>
                  <span className="font-medium text-gray-900">Authors:</span>{" "}
                  {draft.cleaning.filters.authors?.length > 0
                    ? draft.cleaning.filters.authors.join(", ")
                    : "No author filter"}
                </p>
                <div>
                  <p className="font-medium text-gray-900 mb-2">Keyword filters</p>
                  {keywordFilters.length > 0 ? (
                    <div className="space-y-2">
                      {keywordFilters.map((filter) => (
                        <div key={filter.field} className="rounded-lg bg-white px-3 py-2">
                          <span className="font-medium text-gray-900">
                            {KEYWORD_FIELD_LABELS[filter.field] || filter.field}:
                          </span>{" "}
                          {filter.keywords.join(", ")}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500">No keyword filter</p>
                  )}
                </div>
                <div>
                  <p className="font-medium text-gray-900 mb-2">Selected features</p>
                  {selectedFeatures.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {selectedFeatures.map((feature) => (
                        <span
                          key={feature}
                          className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800"
                        >
                          {FEATURE_LABELS[feature] || feature}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500">All available cleaning features</p>
                  )}
                </div>
              </div>
            </section>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={onApprove}
              disabled={submitting}
              className="rounded-lg bg-green-600 px-4 py-2.5 font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Review collect plan
            </button>
            <p className="text-sm text-gray-500">
              The next step uses the same collect-plan validation as manual mode, with the cleaning draft attached for review.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default AutomaticCollectionReview;
