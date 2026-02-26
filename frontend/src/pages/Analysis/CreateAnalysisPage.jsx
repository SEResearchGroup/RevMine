import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  BarChart3,
  Play,
  CheckSquare,
  Square,
  Sparkles,
  Database,
  Filter,
  Search,
  ChevronDown,
  ChevronUp,
  Info,
  AlertCircle,
} from "lucide-react";
import { analyzeService } from "../../services/api";

const CreateAnalysisPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();

  const [dataset, setDataset] = useState(null);
  const [availableMetrics, setAvailableMetrics] = useState([]);
  const [metricsByCategory, setMetricsByCategory] = useState({});
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedCategories, setExpandedCategories] = useState({});
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [datasetData, metricsData] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getAvailableMetrics(datasetId),
      ]);
      setDataset(datasetData);
      
      // Group metrics by category
      const metrics = metricsData.available_metrics || [];
      const grouped = {};
      metrics.forEach((metric) => {
        const category = metric.category || "Other";
        if (!grouped[category]) {
          grouped[category] = [];
        }
        grouped[category].push(metric);
      });
      setMetricsByCategory(grouped);
      setAvailableMetrics(metrics);
      
      // Expand all categories by default
      const expanded = {};
      Object.keys(grouped).forEach((cat) => {
        expanded[cat] = true;
      });
      setExpandedCategories(expanded);
    } catch (error) {
      console.error("Error loading data:", error);
      setError("Error loading data");
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const toggleMetric = (metricCode) => {
    setSelectedMetrics((prev) =>
      prev.includes(metricCode)
        ? prev.filter((code) => code !== metricCode)
        : [...prev, metricCode]
    );
  };

  const toggleCategory = (category) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  const selectAllInCategory = (category) => {
    const categoryMetrics = metricsByCategory[category] || [];
    const categoryCodes = categoryMetrics.map((m) => m.code);
    const allSelected = categoryCodes.every((code) => selectedMetrics.includes(code));
    
    if (allSelected) {
      setSelectedMetrics((prev) => prev.filter((code) => !categoryCodes.includes(code)));
    } else {
      setSelectedMetrics((prev) => [...new Set([...prev, ...categoryCodes])]);
    }
  };

  const selectAll = () => {
    if (selectedMetrics.length === availableMetrics.length) {
      setSelectedMetrics([]);
    } else {
      setSelectedMetrics(availableMetrics.map((m) => m.code));
    }
  };

  const handleCreateAnalysis = async () => {
    if (selectedMetrics.length === 0) return;

    try {
      setCreating(true);
      setError(null);

      // Create analyses for each selected metric with correct field names
      const analyses = selectedMetrics.map((metricCode) => ({
        metric_code: metricCode,
        chart_type: availableMetrics.find(m => m.code === metricCode)?.default_chart_type || 'bar',
        config: {},
      }));

      const result = await analyzeService.bulkCreateAnalyses(datasetId, analyses);
      
      // Navigate to results page
      if (result && result.length > 0) {
        navigate(`/analysis/datasets/${datasetId}/results`, {
          state: { analyses: result },
        });
      }
    } catch (error) {
      console.error("Error creating analysis:", error);
      setError(error.response?.data?.error || "Error creating analysis");
    } finally {
      setCreating(false);
    }
  };

  const filteredMetricsByCategory = Object.entries(metricsByCategory).reduce(
    (acc, [category, metrics]) => {
      const filtered = metrics.filter(
        (m) =>
          (m.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.code || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
          (m.description || "").toLowerCase().includes(searchTerm.toLowerCase())
      );
      if (filtered.length > 0) {
        acc[category] = filtered;
      }
      return acc;
    },
    {}
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-slate-600">Loading metrics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate(`/analysis/datasets/${datasetId}`)}
            className="flex items-center gap-2 text-slate-600 hover:text-slate-800 mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to dataset
          </button>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-200">
                <BarChart3 className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-800">Create Analysis</h1>
                <p className="text-slate-500 mt-1">
                  <span className="font-medium text-slate-700">{dataset?.name || dataset?.original_filename}</span>
                  {" · "}
                  Select metrics to analyze
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Selection Summary */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-4 mb-6 sticky top-4 z-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <CheckSquare className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Selected</p>
                  <p className="text-xl font-bold text-slate-800">
                    {selectedMetrics.length}{" "}
                    <span className="text-sm font-normal text-slate-500">
                      / {availableMetrics.length}
                    </span>
                  </p>
                </div>
              </div>
              <button
                onClick={selectAll}
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                {selectedMetrics.length === availableMetrics.length
                  ? "Deselect all"
                  : "Select all"}
              </button>
            </div>
            <button
              onClick={handleCreateAnalysis}
              disabled={selectedMetrics.length === 0 || creating}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-xl hover:from-indigo-700 hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 disabled:cursor-not-allowed transition-all shadow-lg shadow-indigo-200 font-medium"
            >
              {creating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Run analysis
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-600">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}
        </div>

        {/* Search */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-4 mb-6">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search for a metric..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-slate-50/50"
            />
          </div>
        </div>

        {/* Metrics by Category */}
        <div className="space-y-4">
          {Object.entries(filteredMetricsByCategory).length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200/60 p-12 text-center">
              <BarChart3 className="w-12 h-12 mx-auto mb-4 text-slate-400" />
              <p className="text-slate-600">
                {searchTerm
                  ? "No metrics match your search"
                  : "No metrics available for this dataset"}
              </p>
            </div>
          ) : (
            Object.entries(filteredMetricsByCategory).map(([category, metrics]) => {
              const isExpanded = expandedCategories[category];
              const categoryCodes = metrics.map((m) => m.code);
              const selectedInCategory = categoryCodes.filter((code) =>
                selectedMetrics.includes(code)
              ).length;

              return (
                <div
                  key={category}
                  className="bg-white rounded-2xl shadow-sm border border-slate-200/60 overflow-hidden"
                >
                  <div
                    onClick={() => toggleCategory(category)}
                    className="flex items-center justify-between p-5 cursor-pointer hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-gradient-to-br from-indigo-100 to-blue-100 rounded-lg flex items-center justify-center">
                        <BarChart3 className="w-5 h-5 text-indigo-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-slate-800">{category}</h3>
                        <p className="text-sm text-slate-500">
                          {selectedInCategory}/{metrics.length} selected
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          selectAllInCategory(category);
                        }}
                        className="text-sm text-indigo-600 hover:text-indigo-700 font-medium px-3 py-1 rounded-lg hover:bg-indigo-50 transition-colors"
                      >
                        {selectedInCategory === metrics.length ? "Deselect" : "All"}
                      </button>
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="border-t border-slate-100 p-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {metrics.map((metric) => {
                          const metricCode = metric.code;
                          const isSelected = selectedMetrics.includes(metricCode);

                          return (
                            <div
                              key={metricCode}
                              onClick={() => toggleMetric(metricCode)}
                              className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                                isSelected
                                  ? "border-indigo-500 bg-indigo-50/50"
                                  : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                              }`}
                            >
                              <div className="flex items-start gap-3">
                                <div className="mt-0.5">
                                  {isSelected ? (
                                    <CheckSquare className="w-5 h-5 text-indigo-600" />
                                  ) : (
                                    <Square className="w-5 h-5 text-slate-400" />
                                  )}
                                </div>
                                <div className="flex-1">
                                  <h4 className="font-medium text-slate-800">
                                    {metric.name}
                                  </h4>
                                  {metric.description && (
                                    <p className="text-sm text-slate-500 mt-1">
                                      {metric.description}
                                    </p>
                                  )}
                                  <span className="inline-block mt-2 px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">
                                    {metric.default_chart_type}
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default CreateAnalysisPage;
