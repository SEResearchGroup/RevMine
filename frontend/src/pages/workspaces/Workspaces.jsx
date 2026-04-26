import React, { useState, useEffect } from "react";
import { Search, Plus, ChevronDown, X, Filter } from "lucide-react";
import { workspaceService } from "../../services/api";
import { useNavigate } from "react-router-dom";
import WorkspaceCard from "../../components/workspaces/WorkSpaceCard";
import WorkspaceModal from "../../components/workspaces/WorkspaceModal";
import StatsCards from "../../components/workspaces/StatsCards";

const PAGE_SIZE = 20;

const Workspaces = ({ openCreateModal }) => {
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [editingWorkspace, setEditingWorkspace] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // Filters
  const [filterPlatform, setFilterPlatform] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const [stats] = useState({
    analysisThisMonth: 10,
    prsCollected: 45,
    quotaUsed: 85,
    activeWorkspaces: 4,
  });

  useEffect(() => {
    fetchPage(1, true);
  }, [searchTerm, filterPlatform, filterDateFrom, filterDateTo]);

  useEffect(() => {
    if (openCreateModal) {
      setEditingWorkspace(null);
      setShowModal(true);
    }
  }, [openCreateModal]);

  const buildParams = (pageNum) => {
    const params = { page: pageNum, page_size: PAGE_SIZE };
    if (searchTerm) params.search = searchTerm;
    if (filterPlatform) params.platform = filterPlatform;
    if (filterDateFrom) params.date_from = filterDateFrom;
    if (filterDateTo) params.date_to = filterDateTo;
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
      const response = await workspaceService.getAll(buildParams(pageNum));
      const data = response.data;
      setTotal(data.total);
      setHasMore(data.has_next);
      setWorkspaces((prev) => (reset ? data.results : [...prev, ...data.results]));
    } catch (error) {
      console.error("Error loading workspaces", error);
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

  const handleCreateWorkspace = () => {
    setEditingWorkspace(null);
    setShowModal(true);
  };

  const handleEditWorkspace = (workspace) => {
    setEditingWorkspace(workspace);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingWorkspace(null);
    fetchPage(1, true);
  };

  const handleDeleteWorkspace = async (workspaceId) => {
    if (window.confirm("Are you sure you want to delete this workspace?")) {
      try {
        await workspaceService.delete(workspaceId);
        fetchPage(1, true);
      } catch (error) {
        console.error("Error deleting workspace", error);
      }
    }
  };

  const clearFilters = () => {
    setFilterPlatform("");
    setFilterDateFrom("");
    setFilterDateTo("");
  };

  const hasActiveFilters = filterPlatform || filterDateFrom || filterDateTo;

  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-7xl mx-auto mb-4 sm:mb-6">
        <h1 className="text-xl sm:text-2xl font-semibold text-gray-800 mb-4 sm:mb-6">
          <span className="text-blue-600">Data Sources</span> / Workspaces
        </h1>

        <StatsCards stats={stats} />

        <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 mb-3">
          <div className="relative flex-1 max-w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search workspaces..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex flex-row gap-3">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex-1 sm:flex-none px-4 py-2.5 border rounded-lg flex items-center justify-center gap-2 hover:bg-gray-50 transition ${
                hasActiveFilters
                  ? "border-blue-500 text-blue-600 bg-blue-50"
                  : "border-gray-300"
              }`}
            >
              <Filter className="w-4 h-4" />
              <span className="hidden sm:inline">Filter</span>
              {hasActiveFilters && (
                <span className="bg-blue-600 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">!</span>
              )}
            </button>

            <button
              onClick={handleCreateWorkspace}
              className="flex-1 sm:flex-none px-5 py-2.5 bg-blue-600 text-white rounded-lg flex items-center justify-center gap-2 hover:bg-blue-700"
            >
              <Plus className="w-5 h-5" />
              <span className="hidden sm:inline">New Workspace</span>
            </button>
          </div>
        </div>

        {showFilters && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4 flex flex-wrap gap-4 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">Platform</label>
              <select
                value={filterPlatform}
                onChange={(e) => setFilterPlatform(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All platforms</option>
                <option value="github">GitHub</option>
                <option value="gitlab">GitLab.com</option>
                <option value="gitlab_self">GitLab Self-Hosted</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">From date</label>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-gray-600">To date</label>
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
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
            Showing {workspaces.length} of {total} workspace{total !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      <div className="max-w-7xl mx-auto">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading workspaces...</div>
        ) : workspaces.length === 0 ? (
          <div className="text-center py-12 text-gray-500">No workspaces found.</div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
              {workspaces.map((ws) => (
                <WorkspaceCard
                  key={ws.id}
                  workspace={ws}
                  onView={() => navigate(`/workspaces/${ws.id}`)}
                  onEdit={() => handleEditWorkspace(ws)}
                  onDelete={() => handleDeleteWorkspace(ws.id)}
                />
              ))}
            </div>

            {hasMore && (
              <div className="mt-8 flex justify-center">
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="px-6 py-3 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition flex items-center gap-2 disabled:opacity-50"
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

      {showModal && (
        <WorkspaceModal workspace={editingWorkspace} onClose={handleCloseModal} />
      )}
    </div>
  );
};

export default Workspaces;
