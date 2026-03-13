import { X } from "lucide-react";

function CollectPlanModal({ plan, repository, onClose, onStartCollection }) {
  const { summary, collection_plan } = plan;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-semibold">Collect Plan</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Project Info */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-2">Repository</h3>
            <p className="text-gray-700">{summary.repository}</p>
            <p className="text-sm text-gray-500 mt-1">Platform: {summary.platform}</p>
          </div>

          {/* Selected Metrics */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3">
              Selected metrics ({summary.metrics_count})
            </h3>
            <div className="space-y-2">
              {summary.metrics.map((metric) => (
                <div
                  key={metric}
                  className="flex items-center gap-2 bg-blue-50 text-blue-700 px-4 py-2 rounded-lg"
                >
                  <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                  <span>{metric.replace("_", " ").toUpperCase()}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Applied Filters */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3">Applied filters</h3>
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Date Range:</span>
                <span className="font-medium">
                  {summary.filters.start_date || "Any"} to{" "}
                  {summary.filters.end_date || "Any"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className="font-medium">
                  {summary.filters.status.join(", ")}
                </span>
              </div>
            </div>
          </div>

          {/* Info Note */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex gap-3">
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Important:</p>
              <p>
                Once started, the collection will run in the background. You can
                safely navigate away and check the progress later.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onStartCollection}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            Start collection →
          </button>
        </div>
      </div>
    </div>
  );
}

export default CollectPlanModal;
