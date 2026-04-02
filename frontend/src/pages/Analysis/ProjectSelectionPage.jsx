/**
 * ProjectSelectionPage – Select a cleaned collection to start analysis.
 *
 * Shows all completed cleaned data items that have a statistics CSV,
 * grouped by their parent collection (project). User can search by
 * repository / project name and select one to begin the analysis flow.
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  ArrowLeft,
  FolderOpen,
  Calendar,
  Database,
  Loader2,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  GitBranch,
  FileSpreadsheet,
  Filter,
  RefreshCw,
} from "lucide-react";
import { collectionService, analyzeService } from "../../services/api";

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */
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

const platformIcon = (platform) => {
  switch (platform) {
    case "github":
      return "GitHub";
    case "gitlab":
      return "GitLab";
    default:
      return platform;
  }
};

/* ------------------------------------------------------------------ */
/*  Collection Card                                                   */
/* ------------------------------------------------------------------ */
const CollectionCard = ({ item, onSelect, selecting }) => {
  const isSelecting = selecting === item.cleaned_data_id;

  return (
    <button
      onClick={() => onSelect(item)}
      disabled={!!selecting}
      className="w-full text-left bg-white rounded-2xl border border-slate-200/60 shadow-sm hover:shadow-md hover:border-emerald-200 transition-all p-5 group disabled:opacity-60 disabled:cursor-wait"
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="w-11 h-11 rounded-xl bg-linear-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md shadow-emerald-200/50 shrink-0">
          <Database className="w-5 h-5 text-white" />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-800 truncate group-hover:text-emerald-700 transition-colors">
              {item.repository_full_name || item.repository_name}
            </h3>
            <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] font-medium uppercase shrink-0">
              {platformIcon(item.platform)}
            </span>
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-slate-500">
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              Collected {formatDate(item.collection_date)}
            </span>
            <span className="flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" />
              Cleaned {formatDate(item.cleaning_date)}
            </span>
          </div>

          {/* Date range & stats */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-sm text-slate-400">
            {(item.start_date || item.end_date) && (
              <span>
                Range: {item.start_date || "start"} → {item.end_date || "end"}
              </span>
            )}
            {item.stats?.item_count != null && (
              <span className="flex items-center gap-1">
                <FileSpreadsheet className="w-3.5 h-3.5" />
                {item.stats.item_count} items
              </span>
            )}
            {item.selected_features?.length > 0 && (
              <span>{item.selected_features.length} features</span>
            )}
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center shrink-0 ml-2">
          {isSelecting ? (
            <Loader2 className="w-5 h-5 animate-spin text-emerald-500" />
          ) : (
            <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-400 transition-colors" />
          )}
        </div>
      </div>
    </button>
  );
};

/* ------------------------------------------------------------------ */
/*  Main Page                                                         */
/* ------------------------------------------------------------------ */
const ProjectSelectionPage = () => {
  const navigate = useNavigate();

  const [collections, setCollections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selecting, setSelecting] = useState(null); // cleaned_data_id being processed

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const fetchCollections = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await collectionService.getCleanedForAnalysis(debouncedSearch);
      setCollections(data.results || []);
    } catch (err) {
      console.error("Failed to load cleaned collections:", err);
      setError("Failed to load collections. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch]);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  /* -------------------------------------------------------------- */
  /*  Select handler: download CSV → upload to analyze → navigate   */
  /* -------------------------------------------------------------- */
  const handleSelect = async (item) => {
    try {
      setSelecting(item.cleaned_data_id);
      setError(null);

      // 1. Download the statistics CSV from the collection service
      const csvResponse = await collectionService.downloadCleanedDataCSV(
        item.cleaned_data_id,
        "statistics"
      );

      // 2. Create a File object from the blob
      const csvBlob = csvResponse.data;
      const filename = `${item.repository_name}_statistics.csv`;
      const csvFile = new File([csvBlob], filename, { type: "text/csv" });

      // 3. Upload to the analyze service to create a Dataset
      const dataset = await analyzeService.uploadDataset(csvFile, {
        workspace_id: item.workspace_id,
        repository_id: item.repository_id,
        platform: item.platform,
      });

      // 4. Navigate to metrics selection
      navigate(`/analysis/${dataset.id}/metrics`);
    } catch (err) {
      console.error("Failed to start analysis from collection:", err);
      setError(
        err.response?.data?.error ||
          "Failed to process the selected collection. Please try again."
      );
    } finally {
      setSelecting(null);
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-b from-slate-50 to-white">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate("/analysis/history")}
            className="p-2 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              Select a Collection
            </h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Choose a cleaned dataset from your collections to start analysis
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative mb-6">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by repository or project name..."
            className="w-full pl-12 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-700 placeholder-slate-400 focus:outline-none focus:border-emerald-300 focus:ring-2 focus:ring-emerald-100 transition-all"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-lg hover:bg-slate-100"
            >
              <span className="text-xs text-slate-400">Clear</span>
            </button>
          )}
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">{error}</p>
              <button
                onClick={fetchCollections}
                className="text-sm text-red-600 hover:text-red-800 underline mt-1"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mb-3" />
            <p className="text-slate-500 text-sm">Loading collections...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && collections.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
              <FolderOpen className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-700 mb-1">
              {debouncedSearch ? "No matching collections" : "No cleaned collections"}
            </h3>
            <p className="text-sm text-slate-500 max-w-md">
              {debouncedSearch
                ? `No collections match "${debouncedSearch}". Try a different search term.`
                : "You don't have any cleaned collections with statistics yet. Start by collecting and cleaning data from your repositories."}
            </p>
            {debouncedSearch && (
              <button
                onClick={() => setSearchTerm("")}
                className="mt-4 px-4 py-2 text-sm font-medium text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg transition-colors"
              >
                Clear search
              </button>
            )}
          </div>
        )}

        {/* Results List */}
        {!loading && collections.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-slate-500">
                {collections.length} collection{collections.length !== 1 && "s"} available
              </p>
              <button
                onClick={fetchCollections}
                className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4 text-slate-400" />
              </button>
            </div>
            <div className="space-y-3">
              {collections.map((item) => (
                <CollectionCard
                  key={item.cleaned_data_id}
                  item={item}
                  onSelect={handleSelect}
                  selecting={selecting}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ProjectSelectionPage;
