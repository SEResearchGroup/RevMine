import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Upload,
  Database,
  FileSpreadsheet,
  ArrowRight,
  Search,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertCircle,
  CloudUpload,
  X,
  Calendar,
  HardDrive,
  Rows3,
  Columns3,
} from "lucide-react";
import { analyzeService } from "../../services/api";

const DatasetSelectionPage = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const loadDatasets = useCallback(async () => {
    try {
      setLoading(true);
      const data = await analyzeService.getDatasets();
      setDatasets(data.results || []);
    } catch (err) {
      console.error("Failed to load datasets:", err);
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
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer?.files?.[0];
    if (file && file.name.endsWith(".csv")) handleUpload(file);
    else setUploadError("Please upload a CSV file.");
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleUpload = async (file) => {
    try {
      setUploading(true);
      setUploadError(null);
      setUploadSuccess(null);
      const data = await analyzeService.uploadDataset(file);
      setUploadSuccess(`"${data.original_filename}" uploaded successfully!`);
      setSelectedDataset(data);
      await loadDatasets();
    } catch (err) {
      setUploadError(err.response?.data?.error || "Upload failed. Try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (datasetId, e) => {
    e.stopPropagation();
    if (!confirm("Delete this dataset?")) return;
    try {
      setDeletingId(datasetId);
      await analyzeService.deleteDataset(datasetId);
      if (selectedDataset?.id === datasetId) setSelectedDataset(null);
      await loadDatasets();
    } catch (err) {
      console.error(err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleContinue = () => {
    if (selectedDataset) {
      navigate(`/analysis/${selectedDataset.id}/metrics`);
    }
  };

  const filteredDatasets = datasets.filter(
    (d) =>
      (d.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (d.original_filename || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (str) => {
    if (!str) return "—";
    return new Date(str).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "—";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200/50">
              <Database className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-800">Analysis</h1>
              <p className="text-sm text-slate-500">
                Step 1 — Select or upload a dataset
              </p>
            </div>
          </div>
        </div>

        {/* Steps indicator */}
        <div className="flex items-center gap-3 mb-8">
          {[
            { n: 1, label: "Dataset", active: true },
            { n: 2, label: "Metrics" },
            { n: 3, label: "Dashboard" },
          ].map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              <div
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  step.active
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-200"
                    : "bg-white text-slate-400 border border-slate-200"
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    step.active
                      ? "bg-white/20 text-white"
                      : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {step.n}
                </span>
                {step.label}
              </div>
              {i < 2 && (
                <div className="w-8 h-px bg-slate-200" />
              )}
            </div>
          ))}
        </div>

        {/* Upload Zone */}
        <div
          className={`relative mb-8 rounded-2xl border-2 border-dashed transition-all duration-300 ${
            dragActive
              ? "border-indigo-400 bg-indigo-50/50 scale-[1.01]"
              : uploading
              ? "border-blue-300 bg-blue-50/30"
              : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/20"
          }`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
        >
          <div className="p-8 text-center">
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
                <p className="text-slate-600 font-medium">Uploading dataset...</p>
              </div>
            ) : (
              <>
                <CloudUpload
                  className={`w-12 h-12 mx-auto mb-3 transition-colors ${
                    dragActive ? "text-indigo-500" : "text-slate-300"
                  }`}
                />
                <p className="text-slate-700 font-semibold mb-1">
                  Drop your CSV file here
                </p>
                <p className="text-slate-400 text-sm mb-4">
                  or{" "}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="text-indigo-600 hover:text-indigo-700 font-medium underline underline-offset-2"
                  >
                    browse files
                  </button>
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={handleFileSelect}
                />
              </>
            )}
          </div>

          {uploadError && (
            <div className="mx-6 mb-6 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {uploadError}
              <button onClick={() => setUploadError(null)} className="ml-auto">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
          {uploadSuccess && (
            <div className="mx-6 mb-6 p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 text-emerald-700 text-sm">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              {uploadSuccess}
              <button onClick={() => setUploadSuccess(null)} className="ml-auto">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Existing Datasets */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60">
          <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">
                Your Datasets
              </h2>
              <p className="text-sm text-slate-400">
                {datasets.length} dataset{datasets.length !== 1 ? "s" : ""} available
              </p>
            </div>
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search datasets..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-slate-50/50"
              />
            </div>
          </div>

          {loading ? (
            <div className="p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">Loading datasets...</p>
            </div>
          ) : filteredDatasets.length === 0 ? (
            <div className="p-12 text-center">
              <FileSpreadsheet className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">
                {searchTerm ? "No matching datasets" : "No datasets yet. Upload a CSV to get started."}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {filteredDatasets.map((dataset) => {
                const isSelected = selectedDataset?.id === dataset.id;
                return (
                  <div
                    key={dataset.id}
                    onClick={() => setSelectedDataset(dataset)}
                    className={`flex items-center gap-4 px-5 py-4 cursor-pointer transition-all ${
                      isSelected
                        ? "bg-indigo-50/60 border-l-4 border-indigo-500"
                        : "hover:bg-slate-50/80 border-l-4 border-transparent"
                    }`}
                  >
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        isSelected
                          ? "bg-indigo-100 text-indigo-600"
                          : "bg-slate-100 text-slate-400"
                      }`}
                    >
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-800 truncate">
                        {dataset.name || dataset.original_filename}
                      </p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(dataset.uploaded_at)}
                        </span>
                        <span className="flex items-center gap-1">
                          <HardDrive className="w-3 h-3" />
                          {formatFileSize(dataset.file_size)}
                        </span>
                        {dataset.row_count != null && (
                          <span className="flex items-center gap-1">
                            <Rows3 className="w-3 h-3" />
                            {dataset.row_count.toLocaleString()} rows
                          </span>
                        )}
                        {dataset.column_count != null && (
                          <span className="flex items-center gap-1">
                            <Columns3 className="w-3 h-3" />
                            {dataset.column_count} cols
                          </span>
                        )}
                      </div>
                    </div>

                    {isSelected && (
                      <CheckCircle2 className="w-5 h-5 text-indigo-500 flex-shrink-0" />
                    )}

                    <button
                      onClick={(e) => handleDelete(dataset.id, e)}
                      disabled={deletingId === dataset.id}
                      className="p-2 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors flex-shrink-0"
                    >
                      {deletingId === dataset.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Continue Button */}
        <div className="mt-8 flex justify-end">
          <button
            onClick={handleContinue}
            disabled={!selectedDataset}
            className="flex items-center gap-2 px-8 py-3.5 bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-xl font-medium shadow-lg shadow-indigo-200/50 hover:from-indigo-700 hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none disabled:cursor-not-allowed transition-all"
          >
            Continue to Metrics
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default DatasetSelectionPage;
