import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  FileText,
  Table,
  BarChart3,
  Calendar,
  Database,
  Eye,
  Download,
  Trash2,
  Play,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertCircle,
  Columns3,
  Filter,
  RefreshCw,
} from "lucide-react";
import { analyzeService } from "../../services/api";

const DatasetDetailPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  
  const [dataset, setDataset] = useState(null);
  const [columns, setColumns] = useState(null);
  const [preview, setPreview] = useState(null);
  const [availableMetrics, setAvailableMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const loadDataset = useCallback(async () => {
    try {
      setLoading(true);
      const [datasetData, columnsData, metricsData] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getDatasetColumns(datasetId),
        analyzeService.getAvailableMetrics(datasetId),
      ]);
      setDataset(datasetData);
      setColumns(columnsData);
      setAvailableMetrics(metricsData);
    } catch (error) {
      console.error("Error loading dataset:", error);
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    loadDataset();
  }, [loadDataset]);

  const loadPreview = async () => {
    try {
      const previewData = await analyzeService.previewDataset(datasetId);
      setPreview(previewData);
      setShowPreviewModal(true);
    } catch (error) {
      console.error("Error loading preview:", error);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this dataset?")) {
      return;
    }
    try {
      await analyzeService.deleteDataset(datasetId);
      navigate("/analysis/datasets");
    } catch (error) {
      console.error("Delete error:", error);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleDateString("en-US", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-slate-600">Loading dataset...</p>
        </div>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-slate-800 font-medium">Dataset not found</p>
          <button
            onClick={() => navigate("/analysis/datasets")}
            className="mt-4 text-indigo-600 hover:text-indigo-700"
          >
            Back to datasets
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate("/analysis/datasets")}
            className="flex items-center gap-2 text-slate-600 hover:text-slate-800 mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to datasets
          </button>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-6">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200">
                  <Database className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-800">
                    {dataset.name || dataset.original_filename}
                  </h1>
                  <p className="text-slate-500 mt-1">{dataset.original_filename}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={loadPreview}
                  className="flex items-center gap-2 px-4 py-2.5 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors text-slate-700"
                >
                  <Eye className="w-4 h-4" />
                  Preview
                </button>
                <button
                  onClick={handleDelete}
                  className="flex items-center gap-2 px-4 py-2.5 border border-red-200 rounded-xl hover:bg-red-50 transition-colors text-red-600"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
                <button
                  onClick={() => navigate(`/analysis/datasets/${datasetId}/analyze`)}
                  className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-xl hover:from-indigo-700 hover:to-blue-700 transition-all shadow-lg shadow-indigo-200 font-medium"
                >
                  <BarChart3 className="w-4 h-4" />
                  Run analysis
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-slate-200/60 p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Table className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{dataset.row_count || 0}</p>
                <p className="text-sm text-slate-500">Rows</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200/60 p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <Columns3 className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{dataset.column_count || 0}</p>
                <p className="text-sm text-slate-500">Columns</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200/60 p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {availableMetrics?.available_metrics?.length || 0}
                </p>
                <p className="text-sm text-slate-500">Available metrics</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200/60 p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                <Calendar className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-800">{formatDate(dataset.created_at)}</p>
                <p className="text-sm text-slate-500">Creation date</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 overflow-hidden">
          <div className="border-b border-slate-200">
            <nav className="flex">
              {[
                { id: "overview", label: "Overview", icon: Database },
                { id: "columns", label: "Columns", icon: Columns3 },
                { id: "metrics", label: "Available metrics", icon: BarChart3 },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-4 text-sm font-medium transition-colors border-b-2 ${
                    activeTab === tab.id
                      ? "text-indigo-600 border-indigo-600 bg-indigo-50/50"
                      : "text-slate-600 border-transparent hover:text-slate-800 hover:bg-slate-50"
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === "overview" && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 mb-4">Information</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-600">File name</span>
                        <span className="font-medium text-slate-800">{dataset.original_filename}</span>
                      </div>
                      <div className="flex justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-600">Size</span>
                        <span className="font-medium text-slate-800">
                          {dataset.file_size ? `${(dataset.file_size / 1024).toFixed(2)} KB` : "-"}
                        </span>
                      </div>
                      <div className="flex justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-600">Created on</span>
                        <span className="font-medium text-slate-800">{formatDate(dataset.created_at)}</span>
                      </div>
                      <div className="flex justify-between py-2 border-b border-slate-100">
                        <span className="text-slate-600">Modified on</span>
                        <span className="font-medium text-slate-800">{formatDate(dataset.updated_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 mb-4">Columns</h3>
                    <div className="max-h-64 overflow-y-auto">
                      {columns?.columns?.slice(0, 10).map((col, idx) => (
                        <div key={idx} className="flex items-center gap-3 py-2 border-b border-slate-100">
                          <span className="w-6 h-6 bg-slate-100 rounded text-xs flex items-center justify-center text-slate-600">
                            {idx + 1}
                          </span>
                          <span className="font-medium text-slate-800">{col}</span>
                        </div>
                      ))}
                      {columns?.columns?.length > 10 && (
                        <p className="text-sm text-slate-500 mt-2">
                          And {columns.columns.length - 10} more columns...
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "columns" && (
              <div>
                <h3 className="text-lg font-semibold text-slate-800 mb-4">
                  All columns ({columns?.columns?.length || 0})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {columns?.columns?.map((col, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                      <span className="w-8 h-8 bg-indigo-100 rounded-lg text-sm flex items-center justify-center text-indigo-600 font-medium">
                        {idx + 1}
                      </span>
                      <div>
                        <p className="font-medium text-slate-800">{col}</p>
                        {columns?.columns_metadata?.[col] && (
                          <p className="text-xs text-slate-500">
                            {columns.columns_metadata[col].type || "string"}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === "metrics" && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-slate-800">
                    Available metrics ({availableMetrics?.available_metrics?.length || 0})
                  </h3>
                  <button
                    onClick={() => navigate(`/analysis/datasets/${datasetId}/analyze`)}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                  >
                    <Play className="w-4 h-4" />
                    Create analysis
                  </button>
                </div>
                
                {availableMetrics?.available_metrics?.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {availableMetrics.available_metrics.map((metric, idx) => (
                      <div
                        key={idx}
                        className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl"
                      >
                        <div className="flex items-start gap-3">
                          <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
                          <div>
                            <h4 className="font-semibold text-slate-800">{metric.name || metric}</h4>
                            {metric.description && (
                              <p className="text-sm text-slate-600 mt-1">{metric.description}</p>
                            )}
                            {metric.category && (
                              <span className="inline-block mt-2 px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                                {metric.category}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-500">
                    <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No metrics available for this dataset</p>
                  </div>
                )}

                {availableMetrics?.missing_columns_by_metric && 
                  Object.keys(availableMetrics.missing_columns_by_metric).length > 0 && (
                  <div className="mt-8">
                    <h4 className="text-md font-semibold text-slate-700 mb-4">
                      Unavailable metrics (missing columns)
                    </h4>
                    <div className="space-y-3">
                      {Object.entries(availableMetrics.missing_columns_by_metric).map(([metric, missingCols]) => (
                        <div
                          key={metric}
                          className="p-4 bg-amber-50 border border-amber-200 rounded-xl"
                        >
                          <div className="flex items-start gap-3">
                            <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                            <div>
                              <h4 className="font-medium text-slate-800">{metric}</h4>
                              <p className="text-sm text-amber-700 mt-1">
                                Missing columns: {missingCols.join(", ")}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      {showPreviewModal && preview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-slate-200">
              <div>
                <h2 className="text-xl font-semibold text-slate-800">Data preview</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Showing {preview.rows?.length || 0} of {preview.total_rows} rows
                </p>
              </div>
              <button
                onClick={() => setShowPreviewModal(false)}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <ChevronDown className="w-5 h-5 text-slate-500" />
              </button>
            </div>
            <div className="overflow-auto max-h-[70vh]">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    {preview.columns?.map((col, idx) => (
                      <th
                        key={idx}
                        className="px-4 py-3 text-left font-semibold text-slate-700 whitespace-nowrap border-b border-slate-200"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows?.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 border-b border-slate-100">
                      {preview.columns?.map((col, colIdx) => (
                        <td
                          key={colIdx}
                          className="px-4 py-3 text-slate-600 whitespace-nowrap max-w-xs truncate"
                        >
                          {String(row[col] ?? "-")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DatasetDetailPage;
