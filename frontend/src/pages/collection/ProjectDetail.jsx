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
  AlertCircle,
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

  // Available metrics
  const availableMetrics = [
    { value: "pull_requests", label: "Pull Requests / Merge Requests" },
    { value: "commits", label: "Commits" },
    { value: "issues", label: "Issues" },
    { value: "comments", label: "Comments" },
    { value: "reviews", label: "Reviews (GitHub only)" },
  ];

  // Selected metrics
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [searchMetric, setSearchMetric] = useState("");

  // Filters
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedStatus, setSelectedStatus] = useState(["open", "closed", "merged"]);

  // Modal
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [collectionPlan, setCollectionPlan] = useState(null);

  useEffect(() => {
    fetchData();
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
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
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

  const filteredMetrics = availableMetrics.filter((m) =>
    m.label.toLowerCase().includes(searchMetric.toLowerCase())
  );

  const toggleMetric = (value) => {
    if (selectedMetrics.includes(value)) {
      setSelectedMetrics(selectedMetrics.filter((m) => m !== value));
    } else {
      setSelectedMetrics([...selectedMetrics, value]);
    }
  };

  const toggleStatus = (status) => {
    if (selectedStatus.includes(status)) {
      setSelectedStatus(selectedStatus.filter((s) => s !== status));
    } else {
      setSelectedStatus([...selectedStatus, status]);
    }
  };

  const handleGoToPlan = async () => {
    if (selectedMetrics.length === 0) {
      alert("Please select at least one metric");
      return;
    }

    try {
      // Create collection plan
      const startRes = await collectionService.startCollection(
        workspaceId,
        repositoryId
      );

      const planId = startRes.data.collection_plan.id;

      // Configure metrics
      await collectionService.configureMetrics(planId, {
        selected_metrics: selectedMetrics,
        start_date: startDate || null,
        end_date: endDate || null,
        status: selectedStatus,
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
      const planId = collectionPlan.collection_plan.id;
      await collectionService.executeCollection(planId);
      
      // Navigate to progress page
      navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planId}/progress`);
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
              {workspace?.platform === "github" ? (
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

        {/* Configure Data Collection */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold mb-6">Configure data collection</h2>

          {/* Select Metrics */}
          <div className="mb-8">
            <h3 className="text-lg font-medium mb-4">Select Metrics</h3>
            
            {/* Search bar */}
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search for Metrics, Endpoints..."
                value={searchMetric}
                onChange={(e) => setSearchMetric(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Metrics list */}
            <div className="space-y-2 max-h-64 overflow-y-auto border border-gray-200 rounded-lg p-4">
              {filteredMetrics.map((metric) => (
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

            <p className="text-sm text-gray-500 mt-2">
              {selectedMetrics.length} metric{selectedMetrics.length !== 1 ? "s" : ""} selected
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
            disabled={selectedMetrics.length === 0}
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