/**
 * AnalysisHistoryPage – Panel page listing all datasets that have been analysed.
 *
 * Entry point for the Analysis section. Shows:
 *  - "New Analysis" button with two options (CSV upload or workspace/project)
 *  - List of past analysis projects with summary info
 *  - Click a project → ProjectAnalysisDetailPage
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart3,
  Search,
  Plus,
  FileSpreadsheet,
  FolderOpen,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
  ChevronRight,
  Upload,
  Database,
  X,
} from "lucide-react";
import { analyzeService } from "../../services/api";

/* ------------------------------------------------------------------ */
/*  New Analysis modal                                                */
/* ------------------------------------------------------------------ */
const NewAnalysisModal = ({ isOpen, onClose, onChoice }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-800">New Analysis</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="p-5 space-y-3">
          <p className="text-sm text-gray-500 mb-4">
            Choose how you want to start your analysis:
          </p>

          {/* Option 1: External CSV */}
          <button
            onClick={() => onChoice("csv")}
            className="w-full flex items-center gap-4 p-4 rounded-xl border border-gray-200 hover:border-blue-300 hover:bg-blue-50/30 transition-all group text-left"
          >
            <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-200/50">
              <Upload className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">
                From External CSV
              </p>
              <p className="text-sm text-gray-500">
                Upload a CSV file directly for analysis
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-blue-400 transition-colors" />
          </button>

          {/* Option 2: From workspace/project */}
          <button
            onClick={() => onChoice("project")}
            className="w-full flex items-center gap-4 p-4 rounded-xl border border-gray-200 hover:border-green-300 hover:bg-green-50/30 transition-all group text-left"
          >
            <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-green-200/50">
              <FolderOpen className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-800 group-hover:text-green-700 transition-colors">
                From Workspace / Project
              </p>
              <p className="text-sm text-gray-500">
                Select a cleaned dataset from your collections
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-green-400 transition-colors" />
          </button>
        </div>
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  History Card                                                      */
/* ------------------------------------------------------------------ */
const AnalysisProjectCard = ({ item, onClick }) => {
  const { dataset, analysis_summary: summary } = item;

  const formatDate = (iso) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const successRate =
    summary.total_analyses > 0
      ? Math.round((summary.completed / summary.total_analyses) * 100)
      : 0;

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-xl border border-gray-200/60 shadow-sm hover:shadow-md hover:border-blue-200 transition-all p-5 group"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4 flex-1 min-w-0">
          {/* Icon */}
          <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center shadow-md shadow-blue-200/50 shrink-0">
            <FileSpreadsheet className="w-5 h-5 text-white" />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-800 truncate group-hover:text-blue-700 transition-colors">
              {dataset.filename || "Unnamed dataset"}
            </h3>
            <p className="text-sm text-gray-500 mt-0.5">
              {dataset.rows_count?.toLocaleString()} rows · {dataset.columns_count} columns
              {dataset.platform && ` · ${dataset.platform}`}
            </p>

            {/* Metric codes */}
            <div className="flex flex-wrap gap-1.5 mt-2">
              {summary.metric_codes.slice(0, 5).map((code) => (
                <span
                  key={code}
                  className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-[10px] font-medium"
                >
                  {code.replace(/_/g, " ")}
                </span>
              ))}
              {summary.metric_codes.length > 5 && (
                <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[10px] font-medium">
                  +{summary.metric_codes.length - 5} more
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right side stats */}
        <div className="flex items-center gap-6 ml-4 shrink-0">
          {/* Analyses count */}
          <div className="text-center">
            <p className="text-lg font-bold text-gray-800">
              {summary.total_analyses}
            </p>
            <p className="text-[10px] uppercase tracking-wider text-gray-400 font-medium">
              Charts
            </p>
          </div>

          {/* Status indicators */}
          <div className="flex items-center gap-2">
            {summary.completed > 0 && (
              <div className="flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium text-green-600">
                  {summary.completed}
                </span>
              </div>
            )}
            {summary.failed > 0 && (
              <div className="flex items-center gap-1">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium text-red-500">
                  {summary.failed}
                </span>
              </div>
            )}
            {summary.pending > 0 && (
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-medium text-amber-500">
                  {summary.pending}
                </span>
              </div>
            )}
          </div>

          {/* Date */}
          <div className="text-right hidden md:block">
            <p className="text-xs text-gray-400">Last analysis</p>
            <p className="text-sm font-medium text-gray-600">
              {formatDate(summary.last_analysis_date)}
            </p>
          </div>

          <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-blue-400 transition-colors" />
        </div>
      </div>
    </button>
  );
};

/* ================================================================== */
/*  MAIN PAGE                                                         */
/* ================================================================== */
const AnalysisHistoryPage = () => {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showModal, setShowModal] = useState(false);

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      const data = await analyzeService.getAnalysisHistory();
      setHistory(data.results || []);
    } catch (err) {
      console.error("Failed to load analysis history:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleNewAnalysisChoice = (choice) => {
    setShowModal(false);
    if (choice === "csv") {
      navigate("/analysis/new/csv");
    } else {
      navigate("/analysis/new/project");
    }
  };

  const handleProjectClick = (item) => {
    navigate(`/analysis/${item.dataset.id}/detail`);
  };

  const filtered = history.filter((item) => {
    const term = searchTerm.toLowerCase();
    return (
      (item.dataset.filename || "").toLowerCase().includes(term) ||
      (item.dataset.platform || "").toLowerCase().includes(term) ||
      (item.analysis_summary.metric_codes || []).some((c) =>
        c.toLowerCase().includes(term)
      )
    );
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200/50">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                Analysis Panel
              </h1>
              <p className="text-sm text-gray-500">
                {history.length} project{history.length !== 1 ? "s" : ""} analysed
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium shadow-lg shadow-blue-200/50 hover:bg-blue-700 transition-all"
          >
            <Plus className="w-4 h-4" />
            New Analysis
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by filename, platform, metric..."
            className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
          />
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-3" />
            <p className="text-gray-500">Loading analysis history...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200/60 p-16 text-center">
            <Database className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-semibold text-gray-600 mb-2">
              {searchTerm ? "No matching analyses" : "No analyses yet"}
            </h3>
            <p className="text-sm text-gray-400 mb-6">
              {searchTerm
                ? "Try a different search term"
                : "Start by creating a new analysis from a CSV file or workspace project."}
            </p>
            {!searchTerm && (
              <button
                onClick={() => setShowModal(true)}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Create First Analysis
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((item) => (
              <AnalysisProjectCard
                key={item.dataset.id}
                item={item}
                onClick={() => handleProjectClick(item)}
              />
            ))}
          </div>
        )}
      </div>

      {/* New Analysis Modal */}
      <NewAnalysisModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onChoice={handleNewAnalysisChoice}
      />
    </div>
  );
};

export default AnalysisHistoryPage;
