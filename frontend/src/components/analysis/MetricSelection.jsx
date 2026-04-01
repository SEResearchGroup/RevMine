import { useState } from "react";
import { AVAILABLE_METRICS } from "../../utils/constants";
import {
  CheckSquare,
  Square,
  Sparkles,
  BarChart3,
  Loader2,
} from "lucide-react";


const MetricSelection = ({ onStartAnalysis, loading }) => {
  const [useLLM, setUseLLM] = useState(false);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [llmQuery, setLLMQuery] = useState("");

  const toggleMetric = (metricId) => {
    setSelectedMetrics((prev) =>
      prev.includes(metricId)
        ? prev.filter((id) => id !== metricId)
        : [...prev, metricId]
    );
  };

  const selectAllMetrics = () => {
    if (selectedMetrics.length === AVAILABLE_METRICS.length) {
      setSelectedMetrics([]);
    } else {
      setSelectedMetrics(AVAILABLE_METRICS.map((m) => m.id));
    }
  };

  const handleStart = () => {
    if (useLLM) {
      onStartAnalysis({ type: 'llm', query: llmQuery });
    } else {
      onStartAnalysis({ type: 'metrics', metrics: selectedMetrics });
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
      {/* Analysis Mode Toggle */}
      <div className="flex items-center justify-center space-x-4 mb-6">
        <button
          onClick={() => setUseLLM(false)}
          className={`flex items-center space-x-3 px-6 py-4 rounded-lg border-2 transition-all ${
            !useLLM
              ? "border-green-500 bg-green-50"
              : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <BarChart3 className="w-6 h-6 text-green-600" />
          <div className="text-left">
            <div className="font-semibold text-slate-800">
              Predefined Insights
            </div>
            <div className="text-sm text-slate-600">
              Research-backed analysis templates
            </div>
          </div>
        </button>

        <span className="text-slate-400 font-medium">Or</span>

        <button
          onClick={() => setUseLLM(true)}
          className={`flex items-center space-x-3 px-6 py-4 rounded-lg border-2 transition-all ${
            useLLM
              ? "border-blue-500 bg-blue-50"
              : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <Sparkles className="w-6 h-6 text-blue-600" />
          <div className="text-left">
            <div className="font-semibold text-slate-800">
              Natural Language Query
            </div>
            <div className="text-sm text-slate-600">
              AI-generated custom analysis
            </div>
          </div>
        </button>
      </div>

      {/* LLM Query Input */}
      {useLLM ? (
        <div>
          <textarea
            value={llmQuery}
            onChange={(e) => setLLMQuery(e.target.value)}
            placeholder="Describe your research questions in plain text, and AI will generate custom analysis..."
            className="w-full h-32 p-4 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <div className="mt-4 flex justify-end">
            <button
              onClick={handleStart}
              disabled={!llmQuery.trim() || loading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 flex items-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Generate Analysis</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* Metric Selection */
        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-slate-800">
              Select Analysis Templates
            </h3>
            <button
              onClick={selectAllMetrics}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              {selectedMetrics.length === AVAILABLE_METRICS.length
                ? "Deselect All"
                : "Select All"}
            </button>
          </div>

          <p className="text-sm text-slate-600 mb-4">
            Selected:{" "}
            <span className="font-semibold">{selectedMetrics.length}</span> of{" "}
            {AVAILABLE_METRICS.length} templates
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4 max-h-96 overflow-y-auto pr-2">
            {AVAILABLE_METRICS.map((metric) => (
              <div
                key={metric.id}
                onClick={() => toggleMetric(metric.id)}
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  selectedMetrics.includes(metric.id)
                    ? "border-green-500 bg-green-50"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-start space-x-3">
                  <div className="mt-0.5">
                    {selectedMetrics.includes(metric.id) ? (
                      <CheckSquare className="w-5 h-5 text-green-600" />
                    ) : (
                      <Square className="w-5 h-5 text-slate-400" />
                    )}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-slate-800 text-sm">
                      {metric.label}
                    </h4>
                    <p className="text-xs text-slate-600 mt-1">
                      {metric.description}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleStart}
              disabled={selectedMetrics.length === 0 || loading}
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-slate-300 flex items-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <BarChart3 className="w-5 h-5" />
                  <span>Start Analysis</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default MetricSelection;
