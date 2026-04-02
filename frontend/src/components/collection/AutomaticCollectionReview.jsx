import { AlertTriangle, Bot, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { FEATURE_LABELS, KEYWORD_FIELD_LABELS } from "./collectionFeatureConfig";

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
}) {
  const keywordFilters = draft?.cleaning?.filters?.keyword_filters || [];
  const selectedFeatures = draft?.cleaning?.selected_features || [];
  const selectedMetrics = draft?.collection?.selected_metrics || [];

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-sky-200 bg-sky-50 p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-sky-600">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-sky-950">Automatic Mode</h3>
            <p className="text-sm text-sky-900/80">
            Describe what to collect and clean. We will generate a draft, show it for validation, then reuse the existing workflow after you approve it.
            </p>
          </div>
        </div>

        <label className="block text-sm font-medium text-sky-950 mb-2">
          Prompt
        </label>
        <textarea
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          rows={4}
          placeholder="Collect merged pull requests from the last 6 months on main, then clean for Python files and bug-related titles."
          className="w-full resize-y rounded-lg border border-sky-200 bg-white px-4 py-3 text-gray-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
        />

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={onGenerate}
            disabled={generating || submitting || !prompt.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 font-medium text-white transition-colors hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {generating ? "Generating draft..." : "Generate draft"}
          </button>
          <p className="text-sm text-sky-900/75">
            The generated configuration is treated as untrusted until you review and approve it.
          </p>
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
                        className="rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-800"
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
                          className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-800"
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
              className="rounded-lg bg-emerald-600 px-4 py-2.5 font-medium text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
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
