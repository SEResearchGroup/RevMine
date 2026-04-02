/**
 * ProjectAnalysisDetailPage – Shows detailed info about a dataset's analyses.
 *
 * Displays:
 *  - Dataset overview (filename, platform, rows, columns)
 *  - Summary statistics (date range, state distribution, key numeric summaries)
 *  - List of all analyses run on the dataset (with status)
 *  - Quick actions: view dashboard, re-run analysis, add metrics
 */
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileSpreadsheet,
  BarChart3,
  Calendar,
  Database,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Columns3,
  LayoutGrid,
  Play,
  Plus,
  ChevronRight,
  Hash,
  TrendingUp,
  GitMerge,
  Timer,
  ArrowDownUp,
} from "lucide-react";
import { analyzeService } from "../../services/api";

/* ------------------------------------------------------------------ */
/*  Stat Card                                                         */
/* ------------------------------------------------------------------ */
const StatCard = ({ icon: Icon, label, value, color = "indigo", sub }) => {
  const colorMap = {
    indigo: "from-indigo-500 to-blue-600 shadow-indigo-200/50",
    emerald: "from-emerald-500 to-teal-600 shadow-emerald-200/50",
    amber: "from-amber-500 to-orange-600 shadow-amber-200/50",
    rose: "from-rose-500 to-pink-600 shadow-rose-200/50",
    violet: "from-violet-500 to-purple-600 shadow-violet-200/50",
    cyan: "from-cyan-500 to-sky-600 shadow-cyan-200/50",
  };
  return (
    <div className="bg-white rounded-xl border border-slate-200/60 p-4 flex items-center gap-3">
      <div
        className={`w-10 h-10 rounded-xl bg-linear-to-br ${colorMap[color]} flex items-center justify-center shadow-lg shrink-0`}
      >
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">
          {label}
        </p>
        <p className="text-lg font-bold text-slate-800 truncate">{value}</p>
        {sub && <p className="text-xs text-slate-500 truncate">{sub}</p>}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Analysis row                                                      */
/* ------------------------------------------------------------------ */
const AnalysisRow = ({ analysis, onClick }) => {
  const statusConfig = {
    completed: { icon: CheckCircle2, class: "text-emerald-500 bg-emerald-50", label: "Completed" },
    processing: { icon: Loader2, class: "text-blue-500 bg-blue-50 animate-spin", label: "Processing" },
    pending: { icon: Clock, class: "text-amber-500 bg-amber-50", label: "Pending" },
    failed: { icon: AlertCircle, class: "text-red-500 bg-red-50", label: "Failed" },
  };
  const st = statusConfig[analysis.status] || statusConfig.pending;
  const StatusIcon = st.icon;

  const formatDate = (iso) =>
    iso
      ? new Date(iso).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "—";

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 px-4 py-3 hover:bg-slate-50 transition-colors rounded-xl text-left group"
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${st.class}`}>
        <StatusIcon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-700 truncate group-hover:text-indigo-700 transition-colors">
          {(analysis.metric_code || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </p>
        <p className="text-xs text-slate-400">{formatDate(analysis.created_at)}</p>
      </div>
      <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] font-medium uppercase">
        {analysis.chart_type || "auto"}
      </span>
      <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-400 transition-colors" />
    </button>
  );
};

/* ================================================================== */
/*  MAIN PAGE                                                         */
/* ================================================================== */
const ProjectAnalysisDetailPage = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();

  const [dataset, setDataset] = useState(null);
  const [summary, setSummary] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [dsData, summaryData, analysesData] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getDatasetSummary(datasetId).catch(() => null),
        analyzeService.getAnalyses(datasetId),
      ]);
      setDataset(dsData);
      setSummary(summaryData);
      setAnalyses(analysesData.results || analysesData || []);
    } catch (err) {
      console.error("Failed to load project detail:", err);
      setError("Failed to load dataset details.");
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const completedAnalyses = analyses.filter((a) => a.status === "completed");
  const failedAnalyses = analyses.filter((a) => a.status === "failed");
  const pendingAnalyses = analyses.filter(
    (a) => a.status === "pending" || a.status === "processing"
  );

  const formatDate = (iso) =>
    iso
      ? new Date(iso).toLocaleDateString("en-US", {
          month: "long",
          day: "numeric",
          year: "numeric",
        })
      : "—";

  if (loading) {
    return (
      <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error || !dataset) {
    return (
      <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 flex flex-col items-center justify-center">
        <AlertCircle className="w-12 h-12 text-red-400 mb-3" />
        <p className="text-slate-600">{error || "Dataset not found"}</p>
        <button
          onClick={() => navigate("/analysis/history")}
          className="mt-4 px-4 py-2 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
        >
          Back to History
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Back button + header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate("/analysis/history")}
            className="p-2 rounded-xl hover:bg-white hover:shadow-sm transition-all"
          >
            <ArrowLeft className="w-5 h-5 text-slate-500" />
          </button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-slate-800">
              {dataset.filename || "Unnamed Dataset"}
            </h1>
            <p className="text-sm text-slate-500">
              Uploaded {formatDate(dataset.uploaded_at)}
              {dataset.platform && ` · ${dataset.platform}`}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate(`/analysis/${datasetId}/metrics`)}
              className="flex items-center gap-2 px-4 py-2.5 border border-slate-200 bg-white text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Metrics
            </button>
            <button
              onClick={() => navigate(`/analysis/${datasetId}/dashboard`)}
              className="flex items-center gap-2 px-5 py-2.5 bg-linear-to-r from-indigo-600 to-blue-600 text-white rounded-xl text-sm font-medium shadow-lg shadow-indigo-200/50 hover:from-indigo-700 hover:to-blue-700 transition-all"
            >
              <BarChart3 className="w-4 h-4" />
              View Dashboard
            </button>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
          <StatCard
            icon={Hash}
            label="Total Rows"
            value={(dataset.rows_count || 0).toLocaleString()}
            color="indigo"
          />
          <StatCard
            icon={Columns3}
            label="Columns"
            value={dataset.columns_count || 0}
            color="cyan"
          />
          <StatCard
            icon={BarChart3}
            label="Analyses"
            value={analyses.length}
            color="violet"
          />
          <StatCard
            icon={CheckCircle2}
            label="Completed"
            value={completedAnalyses.length}
            color="emerald"
          />
          <StatCard
            icon={AlertCircle}
            label="Failed"
            value={failedAnalyses.length}
            color="rose"
          />
          <StatCard
            icon={Clock}
            label="Pending"
            value={pendingAnalyses.length}
            color="amber"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Summary info */}
          <div className="lg:col-span-1 space-y-4">
            {/* Dataset Info Card */}
            <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5">
              <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4">
                Dataset Info
              </h2>
              <div className="space-y-3">
                <InfoRow label="Platform" value={dataset.platform || "—"} />
                <InfoRow label="Filename" value={dataset.filename || "—"} />
                <InfoRow
                  label="Uploaded"
                  value={formatDate(dataset.uploaded_at)}
                />
                {dataset.workspace_id && (
                  <InfoRow label="Workspace ID" value={dataset.workspace_id} />
                )}
                {dataset.repository_id && (
                  <InfoRow label="Repository ID" value={dataset.repository_id} />
                )}
              </div>
            </div>

            {/* Summary Stats Card */}
            {summary && (
              <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5">
                <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4">
                  Data Summary
                </h2>
                <div className="space-y-3">
                  {summary.date_range && (
                    <>
                      <InfoRow
                        label="Date Range Start"
                        value={formatDate(summary.date_range.start)}
                      />
                      <InfoRow
                        label="Date Range End"
                        value={formatDate(summary.date_range.end)}
                      />
                    </>
                  )}
                  {summary.total_mrs != null && (
                    <InfoRow
                      label="Total MRs"
                      value={summary.total_mrs.toLocaleString()}
                    />
                  )}
                  {/* State distribution */}
                  {summary.state_distribution &&
                    Object.entries(summary.state_distribution).map(([state, count]) => (
                      <InfoRow
                        key={state}
                        label={`State: ${state}`}
                        value={count.toLocaleString()}
                      />
                    ))}
                </div>
              </div>
            )}

            {/* Numeric summaries */}
            {summary?.numeric_summaries &&
              Object.keys(summary.numeric_summaries).length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5">
                  <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4">
                    Numeric Summaries
                  </h2>
                  <div className="space-y-4">
                    {Object.entries(summary.numeric_summaries).map(
                      ([col, stats]) => (
                        <div key={col}>
                          <p className="text-xs font-semibold text-slate-600 mb-1.5">
                            {col.replace(/_/g, " ")}
                          </p>
                          <div className="grid grid-cols-2 gap-y-1 gap-x-4">
                            {Object.entries(stats).map(([k, v]) => (
                              <div key={k} className="flex justify-between text-xs">
                                <span className="text-slate-400">{k}</span>
                                <span className="font-medium text-slate-700">
                                  {typeof v === "number"
                                    ? v.toLocaleString(undefined, {
                                        maximumFractionDigits: 2,
                                      })
                                    : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}
          </div>

          {/* Right: Analyses list */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm">
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
                <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
                  Analyses ({analyses.length})
                </h2>
                <button
                  onClick={() => navigate(`/analysis/${datasetId}/dashboard`)}
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                >
                  Open Dashboard
                  <ChevronRight className="w-3 h-3" />
                </button>
              </div>

              {analyses.length === 0 ? (
                <div className="p-10 text-center">
                  <LayoutGrid className="w-10 h-10 mx-auto mb-3 text-slate-300" />
                  <p className="text-sm text-slate-500 mb-4">
                    No analyses have been run on this dataset yet.
                  </p>
                  <button
                    onClick={() => navigate(`/analysis/${datasetId}/metrics`)}
                    className="px-5 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
                  >
                    Select Metrics &amp; Analyse
                  </button>
                </div>
              ) : (
                <div className="divide-y divide-slate-100/80">
                  {analyses.map((a) => (
                    <AnalysisRow
                      key={a.id}
                      analysis={a}
                      onClick={() =>
                        navigate(`/analysis/${datasetId}/chart/${a.id}`)
                      }
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* Small helper */
const InfoRow = ({ label, value }) => (
  <div className="flex justify-between items-center">
    <span className="text-xs text-slate-400">{label}</span>
    <span className="text-sm font-medium text-slate-700 text-right max-w-[60%] truncate">
      {value}
    </span>
  </div>
);

export default ProjectAnalysisDetailPage;
