import React, { useState, useEffect } from "react";
import {
  Upload,
  Search,
  Filter,
  FileText,
  Calendar,
  CheckCircle2,
  Loader2,
  ArrowRight,
  Github,
} from "lucide-react";
import { collectionService } from "../../services/api";

const DatasetSelectionSection = ({ onSelectDataset, onFileSelect }) => {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterOpen, setFilterOpen] = useState(false);

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets =  async () => {
    try {
      setLoading(true);
      const data =  await collectionService.getUserDatasets();
      const cleaned = data.cleaned_datasets || [];
      const mappedDatasets = cleaned.map((cd) => {
        console.log("Mapping cleaned dataset:", cd);
        return {
          id: cd.id,
          dataset_filename: cd.structured_csv_filename,
          created_at: cd.created_at,
          status: cd.status,
          results_count: cd.stats?.pull_requests_count ?? 0,
          repository_name: cd.repository_name,
          repository_full_name: cd.repository_full_name,
          platform: cd.platform,
          repository_url: cd.repository_url,
          collection_id: cd.collection_id,
          workspace_id: cd.workspace_id,
          repository_id: cd.repository_id,
        };
      });

      setDatasets(mappedDatasets);
    } catch (error) {
      console.error("Error loading datasets:", error);
    } finally {
      setLoading(false);
    }
  };

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

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (
        droppedFile.type === "text/csv" ||
        droppedFile.name.endsWith(".csv")
      ) {
        setFile(droppedFile);
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (
        selectedFile.type === "text/csv" ||
        selectedFile.name.endsWith(".csv")
      ) {
        setFile(selectedFile);
      }
    }
  };

  const handleContinueWithFile = () => {
    if (file) {
      onFileSelect(file);
    }
  };

  const filteredDatasets = datasets.filter((dataset) =>
    dataset.dataset_filename
      ?.toLowerCase()
      .includes(searchTerm.toLowerCase()) ||
    dataset.repository_name
      ?.toLowerCase()
      .includes(searchTerm.toLowerCase()) ||
    dataset.repository_full_name
      ?.toLowerCase()
      .includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800 mb-2">
          Data Analysis
        </h1>
        <p className="text-slate-600">
          Upload a new dataset or select from existing analyses
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 mb-6">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
            dragActive
              ? "border-blue-500 bg-blue-50"
              : "border-slate-300 hover:border-slate-400"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <Upload className="w-12 h-12 mx-auto mb-4 text-slate-400" />

          {file ? (
            <div className="space-y-3">
              <div className="flex items-center justify-center space-x-2 text-green-600">
                <FileText className="w-5 h-5" />
                <span className="font-medium">{file.name}</span>
              </div>
              <p className="text-sm text-slate-600">
                {(file.size / 1024).toFixed(2)} KB
              </p>
              <div className="flex justify-center space-x-3">
                <button
                  onClick={() => setFile(null)}
                  className="text-sm text-slate-600 hover:text-slate-700 font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleContinueWithFile}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium flex items-center space-x-2"
                >
                  <span>Continue to Metrics</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-lg font-medium text-slate-700 mb-2">
                Drop your CSV file here or click to browse
              </p>
              <p className="text-sm text-slate-500 mb-4">
                Supports GitHub and GitLab data exports
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer transition-colors"
              >
                Choose File
              </label>
            </>
          )}
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex items-center space-x-3 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="Search datasets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          onClick={() => setFilterOpen(!filterOpen)}
          className="px-4 py-3 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center space-x-2"
        >
          <Filter className="w-5 h-5" />
          <span>Filter</span>
        </button>
      </div>

      {/* Available Datasets */}
      <div>
        <h2 className="text-xl font-semibold text-slate-800 mb-4">
          Available Datasets
        </h2>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : filteredDatasets.length === 0 ? (
          <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
            <FileText className="w-12 h-12 mx-auto mb-4 text-slate-400" />
            <p className="text-slate-600">
              {searchTerm
                ? "No datasets match your search"
                : "No datasets available. Upload your first dataset above."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDatasets.map((dataset) => (
              <div
                key={dataset.id}
                onClick={() => {
                  console.log("Dataset clicked:", {
                    id: dataset.id,
                    collection_id: dataset.collection_id,
                    workspace_id: dataset.workspace_id,
                    repository_id: dataset.repository_id
                  });
                  onSelectDataset(dataset);
                }}

                className="bg-white rounded-lg border border-slate-200 p-5 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer group"
              >
                <div className="flex items-start justify-between mb-3">
                  <FileText className="w-8 h-8 text-blue-600 shrink-0" />
                  {dataset.status === "completed" && (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  )}
                </div>

                <h3 className="font-semibold text-slate-800 mb-2 group-hover:text-blue-600 transition-colors truncate">
                  {dataset.dataset_filename}
                </h3>

                {/* Infos repo une sous l'autre */}
                <div className="space-y-1 text-sm text-slate-600 mb-3">
                  <div className="flex items-center space-x-2">
                    <Github className="w-4 h-4 text-slate-500" />
                    <span className="font-medium truncate">
                      {dataset.repository_name}
                    </span>
                  </div>
                  <p className="text-slate-500 text-xs truncate">
                    {dataset.repository_full_name}
                  </p>
                  <p className="text-slate-500 text-xs capitalize">
                    Platform: {dataset.platform}
                  </p>
                  {dataset.repository_url && (
                    <a
                      href={dataset.repository_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-blue-600 hover:underline break-all"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {dataset.repository_url}
                    </a>
                  )}
                </div>

                <div className="space-y-2 text-sm text-slate-600">
                  <div className="flex items-center space-x-2">
                    <Calendar className="w-4 h-4" />
                    <span>{formatDate(dataset.created_at)}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">
                      {dataset.results_count} charts
                    </span>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        dataset.status === "completed"
                          ? "bg-green-100 text-green-700"
                          : dataset.status === "processing"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {dataset.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DatasetSelectionSection;
