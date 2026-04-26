import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, FolderGit2, ChevronDown, Filter, X, Sparkles } from "lucide-react";
import { workspaceService } from "../../services/api";
import RepositoryCard from "../../components/repositories/RepositoryCard";

const PAGE_SIZE = 20;

function IntelligentCollectionLanding() {
  const navigate = useNavigate();
  const [repositories, setRepositories] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [filterPlatform, setFilterPlatform] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchPage(1, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, filterPlatform]);

  const buildParams = (pageNum) => {
    const params = { page: pageNum, page_size: PAGE_SIZE };
    if (searchTerm) params.search = searchTerm;
    if (filterPlatform) params.platform = filterPlatform;
    return params;
  };

  const fetchPage = async (pageNum, reset = false) => {
    try {
      if (reset) {
        setLoading(true);
        setPage(1);
      } else {
        setLoadingMore(true);
      }
      const response = await workspaceService.getAllRepositories(buildParams(pageNum));
      const data = response.data;
      setTotal(data.total);
      setHasMore(data.has_next);
      setRepositories((prev) => (reset ? data.results : [...prev, ...data.results]));
    } catch (error) {
      console.error("Error loading repositories", error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const handleLoadMore = async () => {
    const nextPage = page + 1;
    setPage(nextPage);
    await fetchPage(nextPage, false);
  };

  const goToIntelligentCollect = (repo) =>
    navigate(`/workspaces/${repo.workspace}/repositories/${repo.id}/collect?mode=automatic`);

  const hasActiveFilters = !!filterPlatform;

  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-7xl mx-auto mb-4 sm:mb-6">
        <h1 className="text-xl sm:text-2xl font-semibold text-gray-800 mb-2">
          <span className="text-blue-600">Collection</span> / Intelligent Collect
        </h1>
        <div className="flex items-start gap-3 bg-gradient-to-br from-sky-50 to-blue-50 border border-sky-100 rounded-xl p-4 mb-6">
          <Sparkles className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-blue-900 font-medium">
              Describe what you want in plain English and let RevMine draft the plan.
            </p>
            <p className="text-sm text-blue-900/80 mt-1">
              Pick a project below. On the next page you'll get an AI-assisted form —
              enter something like "collect pull requests merged in the last 30 days on
              main, focusing on review latency" and we'll preselect branch, date range,
              and metrics for you.
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 mb-3">
          <div className="relative flex-1 max-w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2.5 border rounded-lg flex items-center justify-center gap-2 hover:bg-gray-50 transition ${
              hasActiveFilters
                ? "border-sky-500 text-blue-600 bg-sky-50"
                : "border-gray-300"
            }`}
          >
            <Filter className="w-4 h-4" />
            <span className="hidden sm:inline">Filter</span>
          </button>
        </div>

        {showFilters && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4 flex flex-wrap gap-4 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">Platform</label>
              <select
                value={filterPlatform}
                onChange={(e) => setFilterPlatform(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="">All platforms</option>
                <option value="github">GitHub</option>
                <option value="gitlab">GitLab.com</option>
                <option value="gitlab_self">GitLab Self-Hosted</option>
              </select>
            </div>
            {hasActiveFilters && (
              <button
                onClick={() => setFilterPlatform("")}
                className="flex items-center gap-1 text-sm text-red-600 hover:text-red-700 px-3 py-2"
              >
                <X className="w-4 h-4" />
                Clear filters
              </button>
            )}
          </div>
        )}

        {!loading && (
          <p className="text-sm text-gray-500 mb-4">
            Showing {repositories.length} of {total} project{total !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      <div className="max-w-7xl mx-auto">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading projects...</div>
        ) : repositories.length === 0 ? (
          <div className="text-center py-12">
            <FolderGit2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 text-lg font-medium">No projects found</p>
            <p className="text-gray-400 text-sm mt-1">
              Import repositories from your workspaces first.
            </p>
            <button
              onClick={() => navigate("/workspaces")}
              className="mt-4 px-5 py-2.5 bg-sky-600 text-white rounded-lg hover:bg-sky-700 text-sm"
            >
              Go to Workspaces
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {repositories.map((repo) => (
                <RepositoryCard
                  onClick={() => goToIntelligentCollect(repo)}
                  key={repo.id}
                  repo={repo}
                  showWorkspace
                  onCollect={goToIntelligentCollect}
                />
              ))}
            </div>

            {hasMore && (
              <div className="mt-8 flex justify-center">
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="px-6 py-3 border border-sky-600 text-blue-600 rounded-lg hover:bg-sky-50 transition flex items-center gap-2 disabled:opacity-50"
                >
                  {loadingMore ? (
                    "Loading..."
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4" />
                      Load more
                    </>
                  )}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default IntelligentCollectionLanding;
