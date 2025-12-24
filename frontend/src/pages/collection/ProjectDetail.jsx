/**
 * frontend/src/pages/collection/ProjectDetail.jsx
 * Updated with categorized metrics and category selection
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Github,
  GitBranch,
  FolderGit2,
  Clock,
  Star,
  GitFork,
  Search,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Download,
  BarChart3,
  Trash2,
} from "lucide-react";
import { workspaceService, collectionService } from "../../services/api";
import CollectPlanModal from "../../components/collection/CollectPlanModal";

function ProjectDetail() {
  const { workspaceId, repositoryId } = useParams();
  const navigate = useNavigate();

  const [repository, setRepository] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Collection plan
  const [planId, setPlanId] = useState(null);
  const [platform, setPlatform] = useState("");

  // Available metrics (categorized)
  const [availableMetrics, setAvailableMetrics] = useState({});

  // Selected metrics (flat list of values)
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [searchMetric, setSearchMetric] = useState("");
  const [selectAll, setSelectAll] = useState(false);

  // Expanded categories
  const [expandedCategories, setExpandedCategories] = useState({});

  // Branches
  const [branches, setBranches] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState("");
  const [showBranchDropdown, setShowBranchDropdown] = useState(false);
  const [loadingBranches, setLoadingBranches] = useState(false);

  // Filters
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedStatus, setSelectedStatus] = useState(["open", "closed", "merged"]);

  // Modal
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [collectionPlan, setCollectionPlan] = useState(null);

  // Collection History
  const [collectionHistory, setCollectionHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    fetchData();
    fetchCollectionHistory();
  }, [workspaceId, repositoryId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [wsRes, reposRes] = await Promise.all([
        workspaceService.getById(workspaceId),
        workspaceService.getRepositories(workspaceId),
      ]);

      setWorkspace(wsRes.data);
      const repo = reposRes.data.find((r) => r.id === parseInt(repositoryId));
      setRepository(repo);
      setPlatform(repo.platform);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchCollectionHistory = async () => {
    try {
      setLoadingHistory(true);
      const res = await collectionService.getHistory(repositoryId);
      setCollectionHistory(res.data.collections || []);
    } catch (err) {
      console.error("Error fetching history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const initializeCollection = async () => {
    try {
      // Create collection plan
      const startRes = await collectionService.startCollection(
        workspaceId,
        repositoryId
      );

      setPlanId(startRes.data.collection_plan.id);
      setAvailableMetrics(startRes.data.available_metrics);
      setPlatform(startRes.data.platform);

      // Expand all categories by default
      const allCategories = {};
      Object.keys(startRes.data.available_metrics).forEach((category) => {
        allCategories[category] = true;
      });
      setExpandedCategories(allCategories);

      // Fetch branches
      await fetchBranches(startRes.data.collection_plan.id);
    } catch (err) {
      setError("Error initializing collection: " + err.message);
    }
  };

  useEffect(() => {
    if (repository) {
      initializeCollection();
    }
  }, [repository]);

  const fetchBranches = async (planIdParam) => {
    try {
      setLoadingBranches(true);
      const res = await collectionService.getBranches(planIdParam);
      setBranches(res.data.branches || []);
      setSelectedBranch(res.data.default_branch || "");
    } catch (err) {
      console.error("Error fetching branches:", err);
    } finally {
      setLoadingBranches(false);
    }
  };

  const getTimeDiff = (date) => {
    const now = new Date();
    const past = new Date(date);
    const diffInDays = Math.floor((now - past) / (1000 * 60 * 60 * 24));

    if (diffInDays === 0) return "today";
    if (diffInDays === 1) return "yesterday";
    if (diffInDays < 7) return `${diffInDays} days ago`;
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
    return `${Math.floor(diffInDays / 30)} months ago`;
  };

  // Get all metric values (flat)
  const getAllMetricValues = () => {
    const allValues = [];
    Object.values(availableMetrics).forEach((metricList) => {
      metricList.forEach((metric) => allValues.push(metric.value));
    });
    return allValues;
  };

  // Toggle individual metric
  const toggleMetric = (value) => {
    if (selectedMetrics.includes(value)) {
      setSelectedMetrics(selectedMetrics.filter((m) => m !== value));
    } else {
      setSelectedMetrics([...selectedMetrics, value]);
    }
  };

  // Toggle entire category
  const toggleCategory = (category) => {
    const categoryMetrics = availableMetrics[category] || [];
    const categoryValues = categoryMetrics.map((m) => m.value);

    const allSelected = categoryValues.every((v) =>
      selectedMetrics.includes(v)
    );

    if (allSelected) {
      // Deselect all in category
      setSelectedMetrics(
        selectedMetrics.filter((m) => !categoryValues.includes(m))
      );
    } else {
      // Select all in category
      const newSelected = [...selectedMetrics];
      categoryValues.forEach((v) => {
        if (!newSelected.includes(v)) {
          newSelected.push(v);
        }
      });
      setSelectedMetrics(newSelected);
    }
  };

  // Check if category is fully selected
  const isCategorySelected = (category) => {
    const categoryMetrics = availableMetrics[category] || [];
    const categoryValues = categoryMetrics.map((m) => m.value);
    return categoryValues.every((v) => selectedMetrics.includes(v));
  };

  // Toggle category expansion
  const toggleCategoryExpansion = (category) => {
    setExpandedCategories({
      ...expandedCategories,
      [category]: !expandedCategories[category],
    });
  };

  const toggleStatus = (status) => {
    if (selectedStatus.includes(status)) {
      setSelectedStatus(selectedStatus.filter((s) => s !== status));
    } else {
      setSelectedStatus([...selectedStatus, status]);
    }
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedMetrics([]);
    } else {
      setSelectedMetrics(getAllMetricValues());
    }
    setSelectAll(!selectAll);
  };

  useEffect(() => {
    const allValues = getAllMetricValues();
    setSelectAll(
      selectedMetrics.length === allValues.length && allValues.length > 0
    );
  }, [selectedMetrics, availableMetrics]);

  const handleGoToPlan = async () => {
    if (selectedMetrics.length === 0) {
      alert("Please select at least one metric");
      return;
    }

    if (!selectedBranch) {
      alert("Please select a branch");
      return;
    }

    try {
      // Configure metrics
      await collectionService.configureMetrics(planId, {
        selected_metrics: selectedMetrics,
        start_date: startDate || null,
        end_date: endDate || null,
        status: selectedStatus,
        branch_name: selectedBranch,
      });

      // Get validation
      const validateRes = await collectionService.validatePlan(planId);
      setCollectionPlan(validateRes.data);
      setShowPlanModal(true);
    } catch (err) {
      alert("Error creating collection plan: " + err.message);
    }
  };

  const handleStartCollection = async () => {
    try {
      const planIdToUse = collectionPlan.collection_plan.id;
      await collectionService.executeCollection(planIdToUse);

      // Navigate to progress page
      navigate(
        `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planIdToUse}/progress`
      );
    } catch (err) {
      alert("Error starting collection: " + err.message);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error || !repository) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-500">{error || "Repository not found"}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate(`/workspaces/${workspaceId}`)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to {workspace?.name}</span>
        </button>

        {/* Project Details Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
              {platform === "github" ? (
                <Github className="w-8 h-8" />
              ) : (
                <GitBranch className="w-8 h-8" />
              )}
            </div>

            <div className="flex-1">
              <h1 className="text-2xl font-semibold text-gray-900 mb-2">
                {repository.name}
              </h1>
              <p className="text-gray-600 mb-4">
                {repository.description || "No description provided"}
              </p>

              <div className="flex flex-wrap items-center gap-6 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <FolderGit2 className="w-4 h-4" />
                  <span>{repository.full_name}</span>
                </div>
                {repository.language && (
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                    <span>{repository.language}</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <Star className="w-4 h-4" />
                  <span>{repository.stars_count || 0}</span>
                </div>
                <div className="flex items-center gap-2">
                  <GitFork className="w-4 h-4" />
                  <span>{repository.forks_count || 0}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>Updated {getTimeDiff(repository.updated_at)}</span>
                </div>
              </div>

              {repository.web_url && (
                <a
                  href={repository.web_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-sm mt-3 inline-block"
                >
                  {repository.web_url}
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Collection History */}
        {collectionHistory.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">History of Collections</h2>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      ID
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Date
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {platform === "github" ? "Pull Requests" : "Merge Requests"}
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Commits
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Comments
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {collectionHistory.map((collection) => (
                    <tr key={collection.id} className="border-b border-gray-100">
                      <td className="py-3 px-4 text-gray-900">#{collection.id}</td>
                      <td className="py-3 px-4 text-gray-600">
                        {new Date(collection.completed_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {collection.stats.pull_requests_count ||
                          collection.stats.merge_requests_count ||
                          0}
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {collection.stats.commits_count || 0}
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {collection.stats.comments_count ||
                          collection.stats.notes_count ||
                          0}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <button
                            disabled
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Analyze (Coming soon)"
                          >
                            <BarChart3 className="w-4 h-4" />
                          </button>
                          <button
                            disabled
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Clean (Coming soon)"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                          <button
                            disabled
                            className="p-2 text-green-600 hover:bg-green-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Download (Coming soon)"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-sm text-gray-900 mt-4">
              <strong>Note:</strong> These are previous collection instances of{" "}
              {repository.name} project
            </p>
          </div>
        )}

        {/* Configure Data Collection */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold mb-6">Configure data collection</h2>

          {/* Branch Selection */}
          <div className="mb-8">
            <h3 className="text-lg font-medium mb-4">Select Branch</h3>

            <div className="relative">
              <button
                onClick={() => setShowBranchDropdown(!showBranchDropdown)}
                disabled={loadingBranches}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg flex items-center justify-between hover:bg-gray-50 disabled:opacity-50"
              >
                <span className="text-gray-700">
                  {loadingBranches
                    ? "Loading branches..."
                    : selectedBranch || "Select a branch"}
                </span>
                <ChevronDown className="w-5 h-5 text-gray-400" />
              </button>

              {showBranchDropdown && (
                <div className="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
                  {branches.map((branch) => (
                    <button
                      key={branch.name}
                      onClick={() => {
                        setSelectedBranch(branch.name);
                        setShowBranchDropdown(false);
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between ${
                        selectedBranch === branch.name ? "bg-blue-50" : ""
                      }`}
                    >
                      <span className="text-gray-700">{branch.name}</span>
                      {branch.protected && (
                        <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded">
                          Protected
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Select Metrics by Category */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">Select Metrics</h3>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectAll}
                  onChange={handleSelectAll}
                  className="w-5 h-5 text-blue-600"
                />
                <span className="text-sm text-gray-700">Select All</span>
              </label>
            </div>

            {/* Search bar */}
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search for Metrics..."
                value={searchMetric}
                onChange={(e) => setSearchMetric(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Metrics by Category */}
            <div className="space-y-2 max-h-96 overflow-y-auto border border-gray-200 rounded-lg p-4">
              {Object.entries(availableMetrics).map(([category, metrics]) => (
                <div key={category} className="border border-gray-200 rounded-lg">
                  {/* Category Header */}
                  <div className="bg-gray-50 px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1">
                      <button
                        onClick={() => toggleCategoryExpansion(category)}
                        className="text-gray-600 hover:text-gray-900"
                      >
                        {expandedCategories[category] ? (
                          <ChevronDown className="w-5 h-5" />
                        ) : (
                          <ChevronRight className="w-5 h-5" />
                        )}
                      </button>
                      <label className="flex items-center gap-3 cursor-pointer flex-1">
                        <input
                          type="checkbox"
                          checked={isCategorySelected(category)}
                          onChange={() => toggleCategory(category)}
                          className="w-5 h-5 text-blue-600"
                        />
                        <span className="font-medium text-gray-900">
                          {category}
                        </span>
                      </label>
                    </div>
                    <span className="text-sm text-gray-500">
                      {metrics.length} metrics
                    </span>
                  </div>

                  {/* Category Metrics */}
                  {expandedCategories[category] && (
                    <div className="p-2">
                      {metrics.map((metric) => (
                        <label
                          key={metric.value}
                          className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedMetrics.includes(metric.value)}
                            onChange={() => toggleMetric(metric.value)}
                            className="w-5 h-5 text-blue-600"
                          />
                          <span className="text-gray-700">{metric.label}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <p className="text-sm text-gray-500 mt-2">
              {selectedMetrics.length} metric{selectedMetrics.length !== 1 ? "s" : ""}{" "}
              selected
            </p>
          </div>

          {/* Apply Filters */}
          <div>
            <h3 className="text-lg font-medium mb-4">Apply Filters</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status
              </label>
              <div className="flex gap-4">
                {["open", "closed", "merged"].map((status) => (
                  <label key={status} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedStatus.includes(status)}
                      onChange={() => toggleStatus(status)}
                      className="w-5 h-5 text-blue-600"
                    />
                    <span className="text-gray-700 capitalize">{status}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Go to Collect Plan button */}
          <button
            onClick={handleGoToPlan}
            disabled={selectedMetrics.length === 0 || !selectedBranch}
            className="mt-8 w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            Go to collect plan →
          </button>
        </div>
      </div>

      {/* Collect Plan Modal */}
      {showPlanModal && collectionPlan && (
        <CollectPlanModal
          plan={collectionPlan}
          repository={repository}
          onClose={() => setShowPlanModal(false)}
          onStartCollection={handleStartCollection}
        />
      )}
    </div>
  );
}

export default ProjectDetail;