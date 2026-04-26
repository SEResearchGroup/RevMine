import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
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

// Derive which DevOps section this dataset flow belongs to from the URL:
// /analysis/... → code, /kanban/... → kanban, /cicd/... → cicd.
// The dataset list/upload pages don't differ across sections today, but the
// "continue" target and history back link must route to the correct section.
const SECTIONS = { analysis: null, kanban: "kanban", cicd: "cicd" };
const deriveSection = (pathname) => {
  const first = (pathname || "").split("/").filter(Boolean)[0];
  return SECTIONS.hasOwnProperty(first) ? first : "analysis";
};

const DatasetSelectionPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const section = deriveSection(location.pathname);
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
      navigate(`/${section}/${selectedDataset.id}/metrics`);
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
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200/50">
              <Database className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Analysis</h1>
              <p className="text-sm text-gray-500">
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
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-200"
                    : "bg-white text-gray-400 border border-gray-200"
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    step.active
                      ? "bg-white/20 text-white"
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  {step.n}
                </span>
                {step.label}
              </div>
              {i < 2 && (
                <div className="w-8 h-px bg-gray-200" />
              )}
            </div>
          ))}
        </div>

        {/* Upload Zone */}
        <div
          className={`relative mb-8 rounded-xl border-2 border-dashed transition-all duration-300 ${
            dragActive
              ? "border-blue-400 bg-blue-50/50 scale-[1.01]"
              : uploading
              ? "border-blue-300 bg-blue-50/30"
              : "border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50/20"
          }`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
        >
          <div className="p-8 text-center">
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
                <p className="text-gray-600 font-medium">Uploading dataset...</p>
              </div>
            ) : (
              <>
                <CloudUpload
                  className={`w-12 h-12 mx-auto mb-3 transition-colors ${
                    dragActive ? "text-blue-500" : "text-gray-300"
                  }`}
                />
                <p className="text-gray-700 font-semibold mb-1">
                  Drop your CSV file here
                </p>
                <p className="text-gray-400 text-sm mb-4">
                  or{" "}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="text-blue-600 hover:text-blue-700 font-medium underline underline-offset-2"
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
              <AlertCircle className="w-4 h-4 shrink-0" />
              {uploadError}
              <button onClick={() => setUploadError(null)} className="ml-auto">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
          {uploadSuccess && (
            <div className="mx-6 mb-6 p-3 bg-green-50 border border-green-200 rounded-xl flex items-center gap-2 text-green-700 text-sm">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              {uploadSuccess}
              <button onClick={() => setUploadSuccess(null)} className="ml-auto">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Existing Datasets */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200/60">
          <div className="p-5 border-b border-gray-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Your Datasets
              </h2>
              <p className="text-sm text-gray-400">
                {datasets.length} dataset{datasets.length !== 1 ? "s" : ""} available
              </p>
            </div>
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search datasets..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50/50"
              />
            </div>
          </div>

          {loading ? (
            <div className="p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">Loading datasets...</p>
            </div>
          ) : filteredDatasets.length === 0 ? (
            <div className="p-12 text-center">
              <FileSpreadsheet className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">
                {searchTerm ? "No matching datasets" : "No datasets yet. Upload a CSV to get started."}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {filteredDatasets.map((dataset) => {
                const isSelected = selectedDataset?.id === dataset.id;
                return (
                  <div
                    key={dataset.id}
                    onClick={() => setSelectedDataset(dataset)}
                    className={`flex items-center gap-4 px-5 py-4 cursor-pointer transition-all ${
                      isSelected
                        ? "bg-blue-50/60 border-l-4 border-blue-500"
                        : "hover:bg-gray-50/80 border-l-4 border-transparent"
                    }`}
                  >
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                        isSelected
                          ? "bg-blue-100 text-blue-600"
                          : "bg-gray-100 text-gray-400"
                      }`}
                    >
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 truncate">
                        {dataset.name || dataset.original_filename}
                      </p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
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
                      <CheckCircle2 className="w-5 h-5 text-blue-500 shrink-0" />
                    )}

                    <button
                      onClick={(e) => handleDelete(dataset.id, e)}
                      disabled={deletingId === dataset.id}
                      className="p-2 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors shrink-0"
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
            className="flex items-center gap-2 px-8 py-3.5 bg-blue-600 text-white rounded-xl font-medium shadow-lg shadow-blue-200/50 hover:bg-blue-700 disabled:bg-gray-300 disabled:shadow-none disabled:cursor-not-allowed transition-all"
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
