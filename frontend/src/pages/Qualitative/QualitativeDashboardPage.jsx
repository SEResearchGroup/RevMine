import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import ReactECharts from "echarts-for-react";
import {
  ArrowLeft, Search, Loader2, Sparkles, CheckCircle2, XCircle,
  CornerDownRight, GitCommitHorizontal, Smile, RefreshCw,
} from "lucide-react";
import { qualitativeService, getApiErrorMessage } from "../../services/api";

const CATEGORY_LABELS = {
  general: "General comments",
  inline: "Review comments",
  review_summary: "Review summaries",
  commit_comment: "Commit comments",
};

const PURPLE = "#7c3aed";

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200/70 p-4">
      <p className="text-2xl font-semibold text-gray-800">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      {sub != null && <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function Chart({ title, option, actions }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200/70 p-4">
      <div className="flex items-center justify-between mb-2 gap-2">
        <p className="text-sm font-medium text-gray-700">{title}</p>
        {actions}
      </div>
      <ReactECharts option={option} style={{ height: 220 }} notMerge lazyUpdate />
    </div>
  );
}

function TraceBadges({ c }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {c.is_resolved === true && (
        <span className="inline-flex items-center gap-1 text-[11px] text-green-700 bg-green-50 px-1.5 py-0.5 rounded">
          <CheckCircle2 className="w-3 h-3" /> resolved
        </span>
      )}
      {c.is_resolved === false && (
        <span className="inline-flex items-center gap-1 text-[11px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">
          <XCircle className="w-3 h-3" /> unresolved
        </span>
      )}
      {c.got_reply && (
        <span className="inline-flex items-center gap-1 text-[11px] text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
          <CornerDownRight className="w-3 h-3" /> replied
        </span>
      )}
      {c.code_changed_after && (
        <span className="inline-flex items-center gap-1 text-[11px] text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded">
          <GitCommitHorizontal className="w-3 h-3" /> code changed after
        </span>
      )}
      {c.reactions_count > 0 && (
        <span className="inline-flex items-center gap-1 text-[11px] text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded">
          <Smile className="w-3 h-3" /> {c.reactions_count}
        </span>
      )}
    </div>
  );
}

function CommentCard({ c, onOpen }) {
  return (
    <div
      onClick={() => onOpen(c)}
      className="bg-white rounded-xl border border-gray-200/70 p-4 hover:shadow-md hover:border-purple-200 transition-all cursor-pointer"
    >
      <div className="flex items-center justify-between gap-3 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[11px] font-medium text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded uppercase tracking-wide">
            {CATEGORY_LABELS[c.comment_type] || c.comment_type}
          </span>
          <span className="text-sm font-medium text-gray-700 truncate">{c.author || "unknown"}</span>
          <span className="text-xs text-gray-400">#{c.review_number}</span>
        </div>
        <span className="text-xs text-gray-400 shrink-0">
          {c.created_at ? new Date(c.created_at).toLocaleDateString() : ""}
        </span>
      </div>

      <p className="text-sm text-gray-700 whitespace-pre-wrap">
        {c.body_excerpt}{c.body_truncated ? "…" : ""}
      </p>

      {c.path ? (
        <p className="text-[11px] text-gray-400 mt-1.5 font-mono truncate">
          {c.path}{c.line ? `:${c.line}` : ""}
        </p>
      ) : null}

      {c.diff_hunk_preview ? (
        <pre className="mt-2 text-[11px] bg-gray-50 border border-gray-100 rounded p-2 overflow-x-auto text-gray-600">
{c.diff_hunk_preview}{c.has_more_diff ? "\n…" : ""}
        </pre>
      ) : null}

      <div className="mt-2.5"><TraceBadges c={c} /></div>
    </div>
  );
}

export default function QualitativeDashboardPage() {
  const { datasetId } = useParams();
  const navigate = useNavigate();

  const [dataset, setDataset] = useState(null);
  const [facets, setFacets] = useState({ authors: [], types: [], reviewers: [], review_numbers: [] });
  const [comments, setComments] = useState({ results: [], count: 0, page: 1, num_pages: 1 });
  const [loading, setLoading] = useState(true);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisMsg, setAnalysisMsg] = useState(null);

  const [filters, setFilters] = useState({
    type: "", role: "reviewer", author: "", q: "", resolved: "", include_non_human: false, page: 1,
  });
  const [searchInput, setSearchInput] = useState("");
  const [granularity, setGranularity] = useState("month");
  const [timeseries, setTimeseries] = useState([]);

  const loadMeta = useCallback(async () => {
    try {
      const [d, f] = await Promise.all([
        qualitativeService.getDataset(datasetId),
        qualitativeService.getFacets(datasetId),
      ]);
      setDataset(d);
      setFacets(f);
    } catch (e) {
      setError(getApiErrorMessage(e, "Failed to load dataset"));
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  const loadComments = useCallback(async () => {
    setListLoading(true);
    try {
      const params = { page: filters.page, page_size: 20 };
      if (filters.type) params.type = filters.type;
      if (filters.role) params.role = filters.role;
      if (filters.author) params.author = filters.author;
      if (filters.q) params.q = filters.q;
      if (filters.resolved !== "") params.resolved = filters.resolved;
      if (filters.include_non_human) params.include_non_human = true;
      const data = await qualitativeService.getComments(datasetId, params);
      setComments(data);
    } catch (e) {
      setError(getApiErrorMessage(e, "Failed to load comments"));
    } finally {
      setListLoading(false);
    }
  }, [datasetId, filters]);

  const loadTimeseries = useCallback(async () => {
    try {
      const params = { granularity };
      if (filters.role) params.role = filters.role;
      if (filters.include_non_human) params.include_non_human = true;
      const data = await qualitativeService.getTimeseries(datasetId, params);
      setTimeseries(data.series || []);
    } catch {
      setTimeseries([]);
    }
  }, [datasetId, granularity, filters.role, filters.include_non_human]);

  useEffect(() => { loadMeta(); }, [loadMeta]);
  useEffect(() => { loadComments(); }, [loadComments]);
  useEffect(() => { loadTimeseries(); }, [loadTimeseries]);

  const stats = useMemo(() => dataset?.stats || {}, [dataset]);
  const categories = useMemo(() => Object.keys(stats.by_category || {}), [stats]);
  const personOptions = useMemo(() => {
    if (filters.role === "reviewer") return facets.reviewers || [];
    if (filters.role === "author") return facets.authors || [];
    return [...new Set([...(facets.reviewers || []), ...(facets.authors || [])])].sort();
  }, [filters.role, facets]);

  const setFilter = (patch) => setFilters((f) => ({ ...f, ...patch, page: patch.page ?? 1 }));

  const startAnalysis = async () => {
    setAnalysisMsg(null);
    try {
      const res = await qualitativeService.startAnalysis(datasetId);
      setAnalysisMsg(res.detail || "Analysis queued.");
    } catch (e) {
      setAnalysisMsg(getApiErrorMessage(e, "Could not start analysis"));
    }
  };

  const categoryChart = {
    tooltip: { trigger: "item" },
    series: [{
      type: "pie", radius: ["45%", "70%"],
      data: categories.map((k) => ({ name: CATEGORY_LABELS[k] || k, value: stats.by_category[k] })),
      label: { fontSize: 11 },
    }],
  };
  const timeChart = {
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 16, top: 16, bottom: 28 },
    xAxis: { type: "category", data: timeseries.map((d) => d.period), axisLabel: { fontSize: 10 } },
    yAxis: { type: "value" },
    series: [{ type: "line", smooth: true, areaStyle: {}, color: PURPLE, data: timeseries.map((d) => d.count) }],
  };
  const reviewers = stats.top_reviewers || [];
  const authorsChart = {
    tooltip: { trigger: "axis" },
    grid: { left: 80, right: 16, top: 8, bottom: 24 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: reviewers.map((a) => a.login).reverse(), axisLabel: { fontSize: 10 } },
    series: [{ type: "bar", color: PURPLE, data: reviewers.map((a) => a.count).reverse() }],
  };

  if (loading) {
    return <div className="p-8 flex items-center gap-2 text-gray-500"><Loader2 className="w-4 h-4 animate-spin" /> Loading…</div>;
  }
  if (!dataset) {
    return <div className="p-8 text-red-600">{error || "Dataset not found"}</div>;
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <Link to="/qualitative" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-purple-600 mb-4">
        <ArrowLeft className="w-4 h-4" /> All projects
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">{dataset.repository_full_name}</h1>
          <p className="text-sm text-gray-500 uppercase tracking-wide">{dataset.platform} · qualitative dataset</p>
        </div>
        <button
          onClick={startAnalysis}
          disabled={dataset.status !== "ready"}
          className="inline-flex items-center gap-2 bg-purple-600 text-white px-4 py-2.5 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50"
        >
          <Sparkles className="w-4 h-4" /> Start automatic analysis
        </button>
      </div>
      {analysisMsg && (
        <div className="mt-3 p-3 rounded-lg bg-purple-50 border border-purple-200 text-sm text-purple-800">{analysisMsg}</div>
      )}
      {error && (
        <div className="mt-3 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
      )}

      {/* Stats strip */}
      <div className="mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Reviews (PR/MR)" value={stats.reviews_count ?? 0} />
        <StatCard label="Human comments" value={stats.comments_human ?? 0} sub={`${stats.by_role?.reviewer ?? 0} reviewer · ${stats.by_role?.author ?? 0} author`} />
        <StatCard label="Threads" value={stats.threads_count ?? 0} sub={`${stats.threads_with_replies ?? 0} with replies`} />
        <StatCard label="Participants" value={stats.participants_count ?? 0} />
        <StatCard label="Resolved threads" value={stats.resolved_threads ?? 0} sub={`${stats.unresolved_threads ?? 0} unresolved`} />
        <StatCard label="Reactions" value={stats.reactions_count ?? 0} />
      </div>

      {/* Charts */}
      <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Chart title="Comments by category" option={categoryChart} />
        <Chart
          title="Comments over time"
          option={timeChart}
          actions={
            <div className="flex gap-1">
              {["day", "week", "month"].map((g) => (
                <button key={g} onClick={() => setGranularity(g)}
                  className={`px-2 py-0.5 text-[11px] rounded border capitalize ${
                    granularity === g ? "bg-purple-600 text-white border-purple-600" : "bg-white text-gray-500 border-gray-300 hover:border-purple-400"
                  }`}>
                  {g}
                </button>
              ))}
            </div>
          }
        />
        <Chart title="Top reviewers" option={authorsChart} />
      </div>

      {/* Search + filters */}
      <div className="mt-6 bg-white rounded-xl border border-gray-200/70 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <form
            onSubmit={(e) => { e.preventDefault(); setFilter({ q: searchInput }); }}
            className="flex items-center gap-2 flex-1 min-w-[220px]"
          >
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search comment text…"
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </form>

          <select value={filters.role} onChange={(e) => setFilter({ role: e.target.value, author: "" })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="reviewer">Reviewers</option>
            <option value="author">Change authors</option>
            <option value="">All actors</option>
          </select>

          <select value={filters.author} onChange={(e) => setFilter({ author: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="">
              {filters.role === "author" ? "All authors" : filters.role === "reviewer" ? "All reviewers" : "All people"}
            </option>
            {personOptions.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>

          <select value={filters.resolved} onChange={(e) => setFilter({ resolved: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            <option value="">Any resolution</option>
            <option value="true">Resolved</option>
            <option value="false">Unresolved</option>
          </select>

          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" checked={filters.include_non_human}
              onChange={(e) => setFilter({ include_non_human: e.target.checked })} className="w-4 h-4" />
            Show bot/system
          </label>

          <button onClick={() => { setSearchInput(""); setFilters({ type: "", role: "reviewer", author: "", q: "", resolved: "", include_non_human: false, page: 1 }); }}
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-purple-600">
            <RefreshCw className="w-3.5 h-3.5" /> Reset
          </button>
        </div>

        {/* Category tabs */}
        <div className="mt-3 flex flex-wrap gap-2">
          <Tab active={filters.type === ""} onClick={() => setFilter({ type: "" })} label="All" />
          {categories.map((k) => (
            <Tab key={k} active={filters.type === k} onClick={() => setFilter({ type: k })}
              label={`${CATEGORY_LABELS[k] || k} (${stats.by_category[k]})`} />
          ))}
        </div>
      </div>

      {/* Card list */}
      <div className="mt-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm text-gray-500">{comments.count} comments</p>
          {listLoading && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
        </div>
        <div className="space-y-3">
          {comments.results.map((c) => (
            <CommentCard key={c.id} c={c} onOpen={(cm) => navigate(`/qualitative/${datasetId}/comments/${cm.id}`)} />
          ))}
          {comments.results.length === 0 && !listLoading && (
            <div className="text-center py-12 text-gray-400">No comments match these filters.</div>
          )}
        </div>

        {/* Pagination */}
        {comments.num_pages > 1 && (
          <div className="mt-5 flex items-center justify-center gap-3">
            <button disabled={comments.page <= 1} onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40">Previous</button>
            <span className="text-sm text-gray-500">Page {comments.page} / {comments.num_pages}</span>
            <button disabled={comments.page >= comments.num_pages} onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40">Next</button>
          </div>
        )}
      </div>
    </div>
  );
}

function Tab({ active, onClick, label }) {
  return (
    <button onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
        active ? "bg-purple-600 text-white border-purple-600" : "bg-white text-gray-600 border-gray-300 hover:border-purple-400"
      }`}>
      {label}
    </button>
  );
}
