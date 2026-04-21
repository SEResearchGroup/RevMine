import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Upload,
  FileJson,
  FileSpreadsheet,
  Github,
  GitBranch,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  X,
} from "lucide-react";
import { collectionService } from "../../services/api";

const PLATFORM_OPTIONS = [
  { value: "github", label: "GitHub", icon: Github },
  { value: "gitlab", label: "GitLab.com", icon: GitBranch },
  { value: "gitlab_self", label: "GitLab Self-Hosted", icon: GitBranch },
];

const ACCEPTED_EXTENSIONS = [".json", ".csv"];

function ImportDataset() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [platform, setPlatform] = useState("");
  const [name, setName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const acceptFile = (candidate) => {
    if (!candidate) return;
    const lower = candidate.name.toLowerCase();
    const ok = ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
    if (!ok) {
      setError("Only .json and .csv files are supported.");
      return;
    }
    setError("");
    setFile(candidate);
    if (!name.trim()) {
      setName(candidate.name.replace(/\.[^/.]+$/, ""));
    }
  };

  const handleFilePicked = (e) => {
    acceptFile(e.target.files?.[0]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    acceptFile(e.dataTransfer.files?.[0]);
  };

  const handleSubmit = async () => {
    if (!file || !platform || !name.trim()) {
      setError("Please select a file, choose the platform, and give the dataset a name.");
      return;
    }
    setUploading(true);
    setError("");
    setProgress(0);
    setResult(null);
    try {
      const response = await collectionService.uploadExternalCollection(
        file,
        platform,
        name.trim(),
        (evt) => {
          if (evt.total) {
            setProgress(Math.round((evt.loaded * 100) / evt.total));
          }
        }
      );
      setResult(response.data);
    } catch (err) {
      const apiError =
        err?.response?.data?.error ||
        err?.response?.data?.detail ||
        err?.message ||
        "Upload failed. Please try again.";
      setError(apiError);
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setPlatform("");
    setName("");
    setProgress(0);
    setError("");
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const collectionId = result?.collection?.id || result?.id;

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-xl sm:text-2xl font-semibold text-gray-800 mb-2">
          <span className="text-blue-600">Data Management</span> / Import dataset
        </h1>
        <p className="text-gray-600 mb-6">
          Upload an existing collection exported from GitHub or GitLab (JSON) or a
          pre-structured CSV. Imported datasets appear in Data Cleaning, where you
          can filter and generate a structured CSV for analysis.
        </p>

        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">1. Choose a file</h2>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragOver
                ? "border-blue-500 bg-blue-50"
                : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,.csv"
              className="hidden"
              onChange={handleFilePicked}
            />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                {file.name.toLowerCase().endsWith(".csv") ? (
                  <FileSpreadsheet className="w-8 h-8 text-green-600" />
                ) : (
                  <FileJson className="w-8 h-8 text-yellow-600" />
                )}
                <div className="text-left">
                  <div className="font-medium text-gray-900">{file.name}</div>
                  <div className="text-xs text-gray-500">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  className="ml-4 p-1 rounded hover:bg-gray-200"
                  aria-label="Remove file"
                >
                  <X className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            ) : (
              <>
                <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-700 font-medium">
                  Drop a .json or .csv file here, or click to browse
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Max upload size 5 GB
                </p>
              </>
            )}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">2. Platform</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {PLATFORM_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const selected = platform === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setPlatform(opt.value)}
                  className={`flex items-center gap-2 px-4 py-3 border rounded-lg transition ${
                    selected
                      ? "border-blue-600 bg-blue-50 text-blue-700"
                      : "border-gray-300 hover:border-gray-400"
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{opt.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">3. Dataset name</h2>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. kubernetes-2024-q1"
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {error && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 mb-4">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="text-sm">{error}</div>
          </div>
        )}

        {uploading && (
          <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4">
            <div className="flex items-center justify-between mb-2 text-sm text-gray-700">
              <span>Uploading {file?.name}</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {result && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-4 flex items-start gap-3">
            <CheckCircle2 className="w-6 h-6 text-green-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-green-900">Upload complete</p>
              <p className="text-sm text-green-800">
                Your dataset has been imported. You can now clean it or start an analysis.
              </p>
              <div className="flex flex-wrap gap-2 mt-3">
                {collectionId && (
                  <button
                    onClick={() => navigate(`/external/collection/${collectionId}`)}
                    className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                  >
                    Open dataset <ArrowRight className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => navigate("/data-cleaning")}
                  className="px-3 py-1.5 border border-green-600 text-green-700 rounded-lg hover:bg-green-100 text-sm"
                >
                  Go to Data Cleaning
                </button>
                <button
                  onClick={reset}
                  className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm"
                >
                  Upload another
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-3">
          <button
            onClick={() => navigate("/data-cleaning")}
            className="px-4 py-2.5 text-gray-700 hover:text-gray-900"
            disabled={uploading}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={uploading || !file || !platform || !name.trim()}
            className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            {uploading ? "Uploading..." : "Import dataset"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ImportDataset;
