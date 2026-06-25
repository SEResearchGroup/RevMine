import React, { useState, useEffect } from "react";
import { analyzeService } from "../../services/api";
import { AVAILABLE_METRICS } from "../../utils/constants";
import {
  ArrowLeft,
  Loader2,
  FileText,
} from "lucide-react";
import jsPDF from "jspdf";
import MetricSelection from "./MetricSelection";
import ResultsDisplay from "./ResultsDisplay";
import CustomAnalysisResult from "./CustomAnalysisResult";

const AnalysisConfigurationSection = ({
  dataset,
  uploadedFile,
  analysisResults,
  onChangeDataset,
}) => {
  const [results, setResults] = useState(analysisResults?.results || []);
  const [loading, setLoading] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState("pending");
  const [pollInterval, setPollInterval] = useState(null);
  const [analysisId, setAnalysisId] = useState(analysisResults?.id || null);
  const [exportLoading, setExportLoading] = useState(false);

  // Custom DSL-First result (separate from the legacy polling flow)
  const [customResult, setCustomResult] = useState(null);
  const [customNlQuery, setCustomNlQuery] = useState("");

  useEffect(() => {
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [pollInterval]);

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
  };

  const handleStartAnalysis = async (config) => {
  setLoading(true);
  setAnalysisStatus("processing");

  try {
    const formData = new FormData();
    if (uploadedFile) {
      formData.append("csv_file", uploadedFile);
      console.log("Using uploaded file");
    }
    else if (dataset) {
      console.log("Using existing dataset:", dataset);
      formData.append("cleaned_data_id", dataset.id);
      formData.append("collection_id", dataset.collection_id);

      formData.append("workspace_id", dataset.workspace_id);
      formData.append("repository_id", dataset.repository_id);

      formData.append("file_type", "statistics");
      if (dataset.platform) {
        formData.append("platform", dataset.platform);
      }
    }

    // DSL-First custom analysis — result already computed in MetricSelection
    if (config.type === 'custom_dsl') {
      setCustomResult(config.result);
      setCustomNlQuery(config.result?.nl_query || "");
      setLoading(false);
      setAnalysisStatus("completed");
      return;
    }

    if (config.type === 'metrics') {
      for (const metric of config.metrics) {
        formData.append("requested_charts", metric);
      }
    } else {
      setCustomNlQuery(config.query || "");
      formData.append("llm_query", config.query);
    }

    // Logs pour debugging
    console.log("FormData content:");
    for (let [key, value] of formData.entries()) {
      console.log(`${key}:`, value);
    }

    const response = await analyzeService.createAnalysis(formData);
    console.log("Analysis created:", response);

    setAnalysisId(response.id);
    setAnalysisStatus(response.status);
    startPolling(response.id);
  } catch (error) {
    console.error("Analysis error:", error);
    setLoading(false);
    setAnalysisStatus("failed");
  }
};

  const handleExportAll = async () => {
    if (!analysisId) {
      alert("No analysis ID available");
      return;
    }

    setExportLoading(true);

    try {
      const exportData = await analyzeService.exportPdfReport(analysisId);

      const pdf = new jsPDF("p", "mm", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 15;
      const imageWidth = pageWidth - margin * 2;
      const imageHeight = 120;

      exportData.charts.forEach((chart, index) => {
        if (index > 0) {
          pdf.addPage();
        }

        // Add title
        const metric = AVAILABLE_METRICS.find((m) => m.id === chart.chart_type);
        pdf.setFontSize(16);
        pdf.setFont(undefined, "bold");
        pdf.text(metric?.label || chart.chart_type, margin, margin);

        // Add description
        pdf.setFontSize(10);
        pdf.setFont(undefined, "normal");
        pdf.text(metric?.description || "", margin, margin + 7);

        // Add image (static matplotlib chart)
        if (chart.chart_image) {
          pdf.addImage(
            `data:image/png;base64,${chart.chart_image}`,
            "PNG",
            margin,
            margin + 15,
            imageWidth,
            imageHeight
          );
        }

        // Add footer with timestamp
        pdf.setFontSize(8);
        pdf.text(
          `Generated: ${new Date(chart.created_at).toLocaleString()}`,
          margin,
          pageHeight - 10
        );
      });

      // Save PDF
      pdf.save(`analysis-report-${analysisId}.pdf`);
    } catch (error) {
      console.error("Export failed:", error);
      alert("Failed to export analysis results");
    } finally {
      setExportLoading(false);
    }
  };


  const handleExportSingleChart = async (result) => {
    if (!analysisId) {
      alert("No analysis ID available");
      return;
    }

    try {
      const exportData = await analyzeService.exportSingleChart(analysisId);

      const chartData = exportData.charts.find(
        (c) => c.chart_type === result.chart_type
      );

      if (chartData && chartData.chart_image) {
        // Create a temporary link to download the image
        const link = document.createElement("a");
        link.href = `data:image/png;base64,${chartData.chart_image}`;
        link.download = `${result.chart_type}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch (error) {
      console.error("Export failed:", error);
      alert("Failed to export chart");
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
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-800 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Change Dataset</span>
        </button>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-800">
                  {datasetName}
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  {uploadedFile
                    ? "New dataset - ready to analyze"
                    : `${dataset?.results_count || 0} charts available`}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metric Selection Section */}
      <div className="mb-6">
        <MetricSelection
          onStartAnalysis={handleStartAnalysis}
          loading={loading}
          datasetId={dataset?.id || null}
        />
      </div>

      {/* Custom DSL-First Analysis Result */}
      {customResult && (
        <div className="mb-6">
          <CustomAnalysisResult
            result={customResult}
            nlQuery={customNlQuery}
            onRerun={() => {
              setCustomResult(null);
            }}
          />
        </div>
      )}

      {/* Loading State */}
      {(analysisStatus === "processing" || loading) && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">
          <div className="text-center">
            <Loader2 className="w-16 h-16 animate-spin mx-auto mb-4 text-blue-600" />
            <p className="text-lg font-medium text-gray-700">
              Processing your data...
            </p>
            <p className="text-sm text-gray-600 mt-2">
              This may take a few minutes
            </p>
          </div>
        </div>
      )}

      {analysisStatus === "completed" && results.length > 0 && (
        <ResultsDisplay
          results={results}
          onExportAll={handleExportAll}
          onExportSingle={handleExportSingleChart}
          exportLoading={exportLoading}
        />
      )}
    </div>
  );
};

export default AnalysisConfigurationSection;
