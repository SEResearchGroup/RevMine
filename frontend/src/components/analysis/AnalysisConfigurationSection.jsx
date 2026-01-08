import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  CheckSquare,
  Square,
  Sparkles,
  BarChart3,
  Loader2,
  FileText, 
} from "lucide-react";
import { analyzeService } from "../../services/api";

const AVAILABLE_METRICS = [
  {
    id: "commits_over_time",
    label: "Commits Over Time",
    description: "Visualize commit frequency over time",
  },
  {
    id: "mr_creation_timeline",
    label: "MR Creation Timeline",
    description: "Track merge request creation patterns",
  },
  {
    id: "lead_time_distribution",
    label: "Lead Time Distribution",
    description: "Analyze time from commit to merge",
  },
  {
    id: "commits_distribution",
    label: "Commits Distribution",
    description: "Distribution of commits across MRs",
  },
  {
    id: "commiters_analysis",
    label: "Committers Analysis",
    description: "Analyze contributor activity",
  },
  {
    id: "commit_time_analysis",
    label: "Commit Time Analysis",
    description: "When commits are made",
  },
  {
    id: "code_churn",
    label: "Code Churn",
    description: "Lines added vs removed over time",
  },
  {
    id: "churn_scatter",
    label: "Churn Scatter Plot",
    description: "Scatter plot of code changes",
  },
  {
    id: "mr_size_analysis",
    label: "MR Size Analysis",
    description: "Analyze merge request sizes",
  },
  {
    id: "discussions_analysis",
    label: "Discussions Analysis",
    description: "Discussion patterns in MRs",
  },
  {
    id: "collaboration_metrics",
    label: "Collaboration Metrics",
    description: "Team collaboration patterns",
  },
  {
    id: "comments_analysis",
    label: "Comments Analysis",
    description: "Comment patterns and frequency",
  },
  {
    id: "files_modified",
    label: "Files Modified",
    description: "Files changed in MRs",
  },
  {
    id: "filetypes_distribution",
    label: "File Types Distribution",
    description: "Distribution of file types",
  },
  {
    id: "entropy_analysis",
    label: "Entropy Analysis",
    description: "Code complexity analysis",
  },
  {
    id: "state_distribution",
    label: "State Distribution",
    description: "MR state distribution",
  },
  {
    id: "rework_analysis",
    label: "Rework Analysis",
    description: "Code rework patterns",
  },
  {
    id: "correlation_matrix",
    label: "Correlation Matrix",
    description: "Metric correlations",
  },
  {
    id: "mr_complexity",
    label: "MR Complexity",
    description: "Complexity analysis of merge requests",
  },
  {
    id: "project_comparison",
    label: "Project Comparison",
    description: "Compare multiple projects",
  },
];

const AnalysisConfigurationSection = ({
  dataset,
  uploadedFile,
  analysisResults,
  onChangeDataset,
}) => {
  const [useLLM, setUseLLM] = useState(false);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [llmQuery, setLLMQuery] = useState("");
  const [results, setResults] = useState(analysisResults?.results || []);
  const [loading, setLoading] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState("pending");
  const [pollInterval, setPollInterval] = useState(null);

  useEffect(() => {
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [pollInterval]);

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

  const startPolling = (id) => {
    const interval = setInterval(async () => {
      try {
        const response = await analyzeService.getAnalysisById(id);
        setAnalysisStatus(response.status);

        if (response.status === "completed") {
          setResults(response.results || []);
          setLoading(false);
          clearInterval(interval);
          setPollInterval(null);
        } else if (response.status === "failed") {
          setLoading(false);
          clearInterval(interval);
          setPollInterval(null);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 3000);

    setPollInterval(interval);

    setTimeout(() => {
      clearInterval(interval);
      setPollInterval(null);
      if (analysisStatus === "processing") {
        setLoading(false);
      }
    }, 600000);
  };

  const handleStartAnalysis = async () => {
    if (useLLM) {
      console.log("LLM Query:", llmQuery);
    } else {
      if (selectedMetrics.length === 0) return;

      setLoading(true);
      setAnalysisStatus("processing");

      try {
        const formData = new FormData();

        // Si c'est un nouveau fichier uploadé, on l'ajoute au formData
        if (uploadedFile) {
          formData.append("csv_file", uploadedFile);
        }

        // Ajouter les métriques sélectionnées
        for (const metric of selectedMetrics) {
          formData.append("requested_charts", metric);
        }

        const response = await analyzeService.createAnalysis(formData);

        setAnalysisStatus(response.status);
        startPolling(response.id);
      } catch (error) {
        console.error("Analysis error:", error);
        setLoading(false);
        setAnalysisStatus("failed");
      }
    }
  };

  const datasetName = dataset
    ? dataset.dataset_filename
    : uploadedFile
    ? uploadedFile.name
    : "Dataset";

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={onChangeDataset}
          className="flex items-center space-x-2 text-slate-600 hover:text-slate-800 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Change Dataset</span>
        </button>

        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-slate-800">
                  {datasetName}
                </h1>
                <p className="text-sm text-slate-600 mt-1">
                  {uploadedFile
                    ? "New dataset - ready to analyze"
                    : `${dataset?.results_count || 0} charts available`}
                </p>
              </div>
            </div>
            <button
              onClick={onChangeDataset}
              className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Change Dataset
            </button>
          </div>
        </div>
      </div>

      {/* Analysis Mode Toggle */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 mb-6">
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
                onClick={handleStartAnalysis}
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
                onClick={handleStartAnalysis}
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

      {/* Loading State */}
      {(analysisStatus === "processing" || loading) && (
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-12">
          <div className="text-center">
            <Loader2 className="w-16 h-16 animate-spin mx-auto mb-4 text-blue-600" />
            <p className="text-lg font-medium text-slate-700">
              Processing your data...
            </p>
            <p className="text-sm text-slate-600 mt-2">
              This may take a few minutes
            </p>
            <div className="mt-4 flex justify-center">
              <div className="flex space-x-2">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results Display */}
      {analysisStatus === "completed" && results.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-800">
            Analysis Results
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {results.map((result) => {
              const metric = AVAILABLE_METRICS.find(
                (m) => m.id === result.chart_type
              );
              return (
                <div
                  key={result.id}
                  className="bg-white rounded-lg border border-slate-200 p-6 hover:shadow-lg transition-shadow"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-800">
                        {metric?.label || result.chart_type}
                      </h3>
                      <p className="text-sm text-slate-600">
                        {metric?.description}
                      </p>
                    </div>
                    <BarChart3 className="w-6 h-6 text-blue-600" />
                  </div>
                  <div className="bg-slate-50 rounded-lg p-4 overflow-hidden">
                    <img
                      src={`data:image/png;base64,${result.chart_image}`}
                      alt={metric?.label}
                      className="w-full h-auto"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisConfigurationSection;
