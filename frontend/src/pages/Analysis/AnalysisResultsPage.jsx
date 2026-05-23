import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  BarChart3,
  Download,
  FileDown,
  Maximize2,
  X,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Filter,
  Eye,
  RotateCcw,
  Grid3X3,
  List,
} from "lucide-react";
import { analyzeService } from "../../services/api";
import DynamicChart from "../../components/analysis/DynamicChart";

const AnalysisResultsPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [dataset, setDataset] = useState(null);
  const [analyses, setAnalyses] = useState(location.state?.analyses || []);
  const [loading, setLoading] = useState(!location.state?.analyses);
  const [fullscreenChart, setFullscreenChart] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [viewMode, setViewMode] = useState("grid");
  const [statusFilter, setStatusFilter] = useState("all");
  const [downloadingId, setDownloadingId] = useState(null);
  const [retryingId, setRetryingId] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [datasetData, analysesData] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getAnalyses(datasetId),
      ]);
      setDataset(datasetData);
      
      // Fetch detailed data for completed analyses to get chart_data
      const analysesWithDetails = await Promise.all(
        analysesData.map(async (analysis) => {
          if (analysis.status === "completed" && !analysis.result?.chart_data) {
            try {
              const detailed = await analyzeService.getAnalysisById(analysis.id);
              return detailed;
            } catch (error) {
              console.error(`Error fetching details for analysis ${analysis.id}:`, error);
              return analysis;
            }
          }
          return analysis;
        })
      );
      
      setAnalyses(analysesWithDetails);
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    if (!location.state?.analyses) {
      loadData();
    } else {
      // Load dataset info and fetch detailed data for completed analyses from state
      analyzeService.getDatasetById(datasetId).then(setDataset).catch(console.error);
      
      // Fetch detailed data for completed analyses passed via state
      const fetchDetails = async () => {
        const analysesWithDetails = await Promise.all(
          location.state.analyses.map(async (analysis) => {
            if (analysis.status === "completed" && !analysis.result?.chart_data) {
              try {
                const detailed = await analyzeService.getAnalysisById(analysis.id);
                return detailed;
              } catch (error) {
                console.error(`Error fetching details for analysis ${analysis.id}:`, error);
                return analysis;
              }
            }
            return analysis;
          })
        );
        setAnalyses(analysesWithDetails);
      };
      fetchDetails();
    }
  }, [loadData, datasetId, location.state]);

  // Poll for pending analyses
  useEffect(() => {
    const pendingAnalyses = analyses.filter(
      (a) => a.status === "pending" || a.status === "processing"
    );
    
    if (pendingAnalyses.length === 0) return;

    const interval = setInterval(async () => {
      try {
        const updatedAnalyses = await analyzeService.getAnalyses(datasetId);
        
        // Fetch detailed data for newly completed analyses
        const analysesWithDetails = await Promise.all(
          updatedAnalyses.map(async (analysis) => {
            if (analysis.status === "completed" && !analysis.result?.chart_data) {
              try {
                const detailed = await analyzeService.getAnalysisById(analysis.id);
                return detailed;
              } catch (error) {
                console.error(`Error fetching details for analysis ${analysis.id}:`, error);
                return analysis;
              }
            }
            return analysis;
          })
        );
        
        setAnalyses(analysesWithDetails);
        
        const stillPending = updatedAnalyses.filter(
          (a) => a.status === "pending" || a.status === "processing"
        );
        if (stillPending.length === 0) {
          clearInterval(interval);
        }
      } catch (error) {
        console.error("Polling error:", error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [analyses, datasetId]);

  const handleRetry = async (analysisId) => {
    try {
      setRetryingId(analysisId);
      const updated = await analyzeService.retryAnalysis(analysisId);
      setAnalyses((prev) =>
        prev.map((a) => (a.id === analysisId ? updated : a))
      );
    } catch (error) {
      console.error("Retry error:", error);
    } finally {
      setRetryingId(null);
    }
  };

  const handleDownload = async (analysis) => {
  try {
    setDownloadingId(analysis.id);
    
    if (analysis.result?.chart_image) {
      const link = document.createElement("a");
      link.href = `data:image/png;base64,${analysis.result.chart_image}`;
      link.download = `${analysis.metric_code || analysis.id}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      console.error("No chart image available");
      alert("Image not available for this chart");
    }
  } catch (error) {
    console.error("Download error:", error);
    alert("Download error");
  } finally {
    setDownloadingId(null);
  }
};

  const openFullscreen = (analysis, index) => {
    setFullscreenChart(analysis);
    setCurrentIndex(index);
  };

  const closeFullscreen = () => {
    setFullscreenChart(null);
  };

  const goToPrevious = () => {
    const filtered = filteredAnalyses;
    const newIndex = currentIndex > 0 ? currentIndex - 1 : filtered.length - 1;
    setCurrentIndex(newIndex);
    setFullscreenChart(filtered[newIndex]);
  };

  const goToNext = () => {
    const filtered = filteredAnalyses;
    const newIndex = currentIndex < filtered.length - 1 ? currentIndex + 1 : 0;
    setCurrentIndex(newIndex);
    setFullscreenChart(filtered[newIndex]);
  };

  const filteredAnalyses = analyses.filter((a) => {
    if (statusFilter === "all") return true;
    return a.status === statusFilter;
  });

  const getStatusBadge = (status) => {
    const styles = {
      pending: "bg-amber-100 text-amber-700 border-amber-200",
      processing: "bg-blue-100 text-blue-700 border-blue-200",
      completed: "bg-green-100 text-green-700 border-green-200",
      failed: "bg-red-100 text-red-700 border-red-200",
    };
    const icons = {
      pending: Clock,
      processing: Loader2,
      completed: CheckCircle2,
      failed: AlertCircle,
    };
    const Icon = icons[status] || Clock;

    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.pending}`}
      >
        <Icon className={`w-3 h-3 ${status === "processing" ? "animate-spin" : ""}`} />
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading results...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate(`/analysis/datasets/${datasetId}`)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800 mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to dataset
          </button>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-6">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-green-200">
                  <BarChart3 className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-800">Analysis Results</h1>
                  <p className="text-gray-500 mt-1">
                    {dataset?.name || dataset?.original_filename}
                    {" · "}
                    {analyses.length} graphiques
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={loadData}
                  className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors text-gray-700"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                  Refresh
                </button>
                <button
                  onClick={() => navigate(`/analysis/datasets/${datasetId}/analyze`)}
                  className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-lg shadow-blue-200 font-medium"
                >
                  <BarChart3 className="w-4 h-4" />
                  New analysis
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60 p-4 mb-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-600">Filter by status:</span>
              <div className="flex gap-2">
                {["all", "completed", "processing", "pending", "failed"].map((status) => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      statusFilter === status
                        ? "bg-blue-100 text-blue-700 font-medium"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    {status === "all" ? "All" : status}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode("grid")}
                className={`p-2 rounded-lg transition-colors ${
                  viewMode === "grid"
                    ? "bg-blue-100 text-blue-600"
                    : "text-gray-400 hover:bg-gray-100"
                }`}
              >
                <Grid3X3 className="w-5 h-5" />
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={`p-2 rounded-lg transition-colors ${
                  viewMode === "list"
                    ? "bg-blue-100 text-blue-600"
                    : "text-gray-400 hover:bg-gray-100"
                }`}
              >
                <List className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Results */}
        {filteredAnalyses.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200/60 p-16 text-center">
            <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p className="text-gray-600">No analysis found</p>
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredAnalyses.map((analysis, index) => (
              <div
                key={analysis.id}
                className="bg-white rounded-xl border border-gray-200/60 overflow-hidden hover:shadow-xl hover:shadow-blue-100/50 transition-all"
              >
                <div className="p-5 border-b border-gray-100">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-800">
                        {analysis.metric || analysis.chart_type || "Analyse"}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {new Date(analysis.created_at).toLocaleString("en-US")}
                      </p>
                    </div>
                    {getStatusBadge(analysis.status)}
                  </div>
                </div>

                <div className="p-5">
                  {analysis.status === "completed" && analysis.result?.chart_data ? (
                    <div className="h-64 bg-gray-50 rounded-xl overflow-hidden">
                      <DynamicChart
                        chartData={analysis.result.chart_data}
                        chartType={analysis.result.chart_data?.type || analysis.chart_type}
                        height={256}
                        showControls={false}
                      />
                    </div>
                  ) : analysis.status === "processing" || analysis.status === "pending" ? (
                    <div className="h-64 bg-gray-50 rounded-xl flex items-center justify-center">
                      <div className="text-center">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
                        <p className="text-sm text-gray-600">Processing...</p>
                      </div>
                    </div>
                  ) : analysis.status === "failed" ? (
                    <div className="h-64 bg-red-50 rounded-xl flex items-center justify-center">
                      <div className="text-center">
                        <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
                        <p className="text-sm text-red-600 mb-3">
                          {analysis.error_message || "Analysis failed"}
                        </p>
                        <button
                          onClick={() => handleRetry(analysis.id)}
                          disabled={retryingId === analysis.id}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
                        >
                          {retryingId === analysis.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RotateCcw className="w-4 h-4" />
                          )}
                          Retry
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="h-64 bg-gray-50 rounded-xl flex items-center justify-center">
                      <p className="text-gray-500">No data</p>
                    </div>
                  )}
                </div>

                {analysis.status === "completed" && (
                  <div className="px-5 pb-5 flex items-center justify-end gap-2">
                    <button
                      onClick={() => openFullscreen(analysis, index)}
                      className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors text-sm"
                    >
                      <Maximize2 className="w-4 h-4" />
                      Fullscreen
                    </button>
                    <button
                      onClick={() => handleDownload(analysis)}
                      disabled={downloadingId === analysis.id}
                      className="flex items-center gap-2 px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors text-sm font-medium"
                    >
                      {downloadingId === analysis.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                      Download
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAnalyses.map((analysis, index) => (
              <div
                key={analysis.id}
                className="bg-white rounded-xl border border-gray-200/60 p-6 hover:shadow-lg transition-all"
              >
                <div className="flex flex-col lg:flex-row gap-6">
                  <div className="lg:w-1/3">
                    {analysis.status === "completed" && analysis.result?.chart_data ? (
                      <div className="h-48 bg-gray-50 rounded-xl overflow-hidden">
                        <DynamicChart
                          chartData={analysis.result.chart_data}
                          chartType={analysis.result.chart_data?.type || analysis.chart_type}
                          height={192}
                          showControls={false}
                        />
                      </div>
                    ) : (
                      <div className="h-48 bg-gray-50 rounded-xl flex items-center justify-center">
                        {analysis.status === "processing" || analysis.status === "pending" ? (
                          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                        ) : (
                          <AlertCircle className="w-8 h-8 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>

                  <div className="lg:flex-1 flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="text-xl font-semibold text-gray-800">
                          {analysis.metric || analysis.chart_type || "Analyse"}
                        </h3>
                        {getStatusBadge(analysis.status)}
                      </div>
                      <p className="text-sm text-gray-500">
                        Created on {new Date(analysis.created_at).toLocaleString("en-US")}
                      </p>
                      {analysis.result?.stats && (
                        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                          {Object.entries(analysis.result.stats).slice(0, 4).map(([key, value]) => (
                            <div key={key} className="bg-gray-50 rounded-lg p-3">
                              <p className="text-xs text-gray-500 uppercase">{key}</p>
                              <p className="text-lg font-semibold text-gray-800">
                                {typeof value === "number" ? value.toFixed(2) : value}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-end gap-3 mt-4">
                      {analysis.status === "failed" && (
                        <button
                          onClick={() => handleRetry(analysis.id)}
                          disabled={retryingId === analysis.id}
                          className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          {retryingId === analysis.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RotateCcw className="w-4 h-4" />
                          )}
                          Retry
                        </button>
                      )}
                      {analysis.status === "completed" && (
                        <>
                          <button
                            onClick={() => openFullscreen(analysis, index)}
                            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                          >
                            <Maximize2 className="w-4 h-4" />
                            Fullscreen
                          </button>
                          <button
                            onClick={() => handleDownload(analysis)}
                            disabled={downloadingId === analysis.id}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                          >
                            {downloadingId === analysis.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Download className="w-4 h-4" />
                            )}
                            Download
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Fullscreen Modal */}
      {fullscreenChart && (
        <div className="fixed inset-0 app-modal-backdrop-strong flex items-center justify-center z-50">
          <button
            onClick={closeFullscreen}
            className="absolute top-6 right-6 p-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
          >
            <X className="w-6 h-6 text-white" />
          </button>

          <button
            onClick={goToPrevious}
            className="absolute left-6 top-1/2 -translate-y-1/2 p-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
          >
            <ChevronLeft className="w-6 h-6 text-white" />
          </button>

          <button
            onClick={goToNext}
            className="absolute right-6 top-1/2 -translate-y-1/2 p-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
          >
            <ChevronRight className="w-6 h-6 text-white" />
          </button>

          <div className="w-full max-w-6xl mx-8">
            <div className="bg-white rounded-xl overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-800">
                      {fullscreenChart.metric || fullscreenChart.chart_type || "Analyse"}
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                      {currentIndex + 1} / {filteredAnalyses.length}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDownload(fullscreenChart)}
                    disabled={downloadingId === fullscreenChart.id}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    {downloadingId === fullscreenChart.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4" />
                    )}
                    Download PNG
                  </button>
                </div>
              </div>
              <div className="p-8 bg-gray-50">
                <div className="h-[60vh]">
                  {fullscreenChart.result?.chart_data ? (
                    <DynamicChart
                      chartData={fullscreenChart.result.chart_data}
                      chartType={fullscreenChart.result.chart_data?.type || fullscreenChart.chart_type}
                      height="60vh"
                      showControls={true}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-500">
                      No data available
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisResultsPage;
