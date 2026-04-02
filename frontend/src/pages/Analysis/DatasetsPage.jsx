import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Upload,
  FileText,
  Search,
  Filter,
  Loader2,
  Database,
  Calendar,
  Trash2,
  Eye,
  BarChart3,
  AlertCircle,
  CheckCircle2,
  X,
  Plus,
  Table,
  RefreshCw,
} from "lucide-react";
import { analyzeService } from "../../services/api";

const DatasetsPage = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const loadDatasets = useCallback(async () => {
    try {
      setLoading(true);
      const data = await analyzeService.getDatasets();
      setDatasets(data);
    } catch (error) {
      console.error("Error loading datasets:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".csv")) {
      setSelectedFile(file);
      setUploadError(null);
    } else {
      setUploadError("Please select a CSV file");
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setUploadError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploadLoading(true);
      setUploadError(null);
      const dataset = await analyzeService.uploadDataset(selectedFile);
      setDatasets((prev) => [dataset, ...prev]);
      setShowUploadModal(false);
      setSelectedFile(null);
      navigate(`/analysis/datasets/${dataset.id}`);
    } catch (error) {
      console.error("Upload error:", error);
      setUploadError(error.response?.data?.error || "Upload failed");
    } finally {
      setUploadLoading(false);
    }
  };

  const handleDelete = async (datasetId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this dataset?")) {
      return;
    }

    try {
      setDeletingId(datasetId);
      await analyzeService.deleteDataset(datasetId);
      setDatasets((prev) => prev.filter((d) => d.id !== datasetId));
    } catch (error) {
      console.error("Delete error:", error);
    } finally {
      setDeletingId(null);
    }
  };

  const filteredDatasets = datasets.filter(
    (dataset) =>
      dataset.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      dataset.original_filename?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleDateString("en-US", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "-";
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
              <Database className="w-8 h-8 text-indigo-600" />
              Datasets
            </h1>
            <p className="text-slate-600 mt-1">
              Manage your datasets and run analyses
            </p>
          </div>
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 px-5 py-3 bg-linear-to-r from-indigo-600 to-blue-600 text-white rounded-xl hover:from-indigo-700 hover:to-blue-700 transition-all shadow-lg shadow-indigo-200 font-medium"
          >
            <Plus className="w-5 h-5" />
            New Dataset
          </button>
        </div>

        {/* Search and Filters */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search for a dataset..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all bg-slate-50/50"
              />
            </div>
            <button
              onClick={loadDatasets}
              className="flex items-center gap-2 px-4 py-3 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors text-slate-700"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Datasets Grid */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mb-4" />
            <p className="text-slate-600">Loading datasets...</p>
          </div>
        ) : filteredDatasets.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200/60 p-16 text-center shadow-sm">
            <div className="w-20 h-20 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Database className="w-10 h-10 text-indigo-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-800 mb-2">
              {searchTerm ? "No results found" : "No datasets"}
            </h3>
            <p className="text-slate-600 mb-6">
              {searchTerm
                ? "Try with different search terms"
                : "Start by uploading your first CSV dataset"}
            </p>
            {!searchTerm && (
              <button
                onClick={() => setShowUploadModal(true)}
                className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors"
              >
                <Upload className="w-5 h-5" />
                Upload a dataset
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredDatasets.map((dataset) => (
              <div
                key={dataset.id}
                onClick={() => navigate(`/analysis/datasets/${dataset.id}`)}
                className="bg-white rounded-2xl border border-slate-200/60 p-6 hover:shadow-xl hover:shadow-indigo-100/50 hover:border-indigo-200 transition-all cursor-pointer group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-linear-to-br from-indigo-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200">
                    <FileText className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/analysis/datasets/${dataset.id}`);
                      }}
                      className="p-2 hover:bg-indigo-50 rounded-lg transition-colors"
                      title="View details"
                    >
                      <Eye className="w-4 h-4 text-indigo-600" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(dataset.id, e)}
                      disabled={deletingId === dataset.id}
                      className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete"
                    >
                      {deletingId === dataset.id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-red-500" />
                      ) : (
                        <Trash2 className="w-4 h-4 text-red-500" />
                      )}
                    </button>
                  </div>
                </div>

                <h3 className="font-semibold text-slate-800 mb-1 truncate group-hover:text-indigo-600 transition-colors">
                  {dataset.name || dataset.original_filename || "Unnamed"}
                </h3>
                <p className="text-sm text-slate-500 mb-4 truncate">
                  {dataset.original_filename}
                </p>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between text-slate-600">
                    <div className="flex items-center gap-2">
                      <Table className="w-4 h-4" />
                      <span>{dataset.row_count || 0} rows</span>
                    </div>
                    <span className="text-slate-400">
                      {dataset.column_count || 0} columns
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <Calendar className="w-4 h-4" />
                    <span>{formatDate(dataset.created_at)}</span>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs text-slate-500">
                    {formatFileSize(dataset.file_size)}
                  </span>
                  <div className="flex items-center gap-1 text-indigo-600 text-sm font-medium">
                    <BarChart3 className="w-4 h-4" />
                    <span>Analyze</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-slate-200">
              <h2 className="text-xl font-semibold text-slate-800">
                New Dataset
              </h2>
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                  setUploadError(null);
                }}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>

            <div className="p-6">
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
                  dragActive
                    ? "border-indigo-500 bg-indigo-50"
                    : "border-slate-300 hover:border-slate-400"
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                {selectedFile ? (
                  <div className="space-y-4">
                    <div className="w-16 h-16 bg-green-100 rounded-xl flex items-center justify-center mx-auto">
                      <CheckCircle2 className="w-8 h-8 text-green-600" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">{selectedFile.name}</p>
                      <p className="text-sm text-slate-500">
                        {(selectedFile.size / 1024).toFixed(2)} KB
                      </p>
                    </div>
                    <button
                      onClick={() => setSelectedFile(null)}
                      className="text-sm text-red-600 hover:text-red-700 font-medium"
                    >
                      Change file
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="w-16 h-16 bg-indigo-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                      <Upload className="w-8 h-8 text-indigo-600" />
                    </div>
                    <p className="font-medium text-slate-800 mb-2">
                      Drag your CSV file here
                    </p>
                    <p className="text-sm text-slate-500 mb-4">or</p>
                    <input
                      type="file"
                      accept=".csv"
                      onChange={handleFileChange}
                      className="hidden"
                      id="file-upload-modal"
                    />
                    <label
                      htmlFor="file-upload-modal"
                      className="inline-block px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer transition-colors"
                    >
                      Browse
                    </label>
                  </>
                )}
              </div>

              {uploadError && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-600">
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <span className="text-sm">{uploadError}</span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 p-6 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                  setUploadError(null);
                }}
                className="px-5 py-2.5 border border-slate-300 rounded-lg hover:bg-slate-100 transition-colors text-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploadLoading}
                className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {uploadLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Upload
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DatasetsPage;
