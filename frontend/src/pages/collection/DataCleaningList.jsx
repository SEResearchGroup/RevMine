/**
 * frontend/src/pages/collection/DataCleaningList.jsx
 * Page displaying all collections for data cleaning management
 */

import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Database,
  Calendar,
  GitBranch,
  FolderGit2,
  CheckCircle2,
  Clock,
  AlertCircle,
  BarChart3,
  Layers,
  Github,
  FileSpreadsheet,
  ArrowRight,
  Upload,
  X,
} from "lucide-react";
import { collectionService, workspaceService } from "../../services/api";

function DataCleaningList() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState([]);
  const [workspaces, setWorkspaces] = useState({});
  const [repositories, setRepositories] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [stats, setStats] = useState({
    total: 0,
    completed: 0,
    interrupted: 0,
    lastCollectionDate: null,
  });

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadPlatform, setUploadPlatform] = useState("");
  const [uploadName, setUploadName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchAllCollections();
  }, []);

  const fetchAllCollections = async () => {
    try {
      setLoading(true);

      // Get all collection plans
      const plansResponse = await collectionService.getAllPlans();
      // API returns array directly, not wrapped in { plans: [...] }
      const allPlans = Array.isArray(plansResponse.data)
        ? plansResponse.data
        : (plansResponse.data.plans || []);

      console.log("All plans fetched:", allPlans);

      // Filter collections that have data (completed, paused, or interrupted)
      const validStatuses = ["completed", "paused", "in_progress", "failed"];
      const collectionsWithData = allPlans.filter(
        (plan) => validStatuses.includes(plan.status)
      );

      console.log("Collections with valid status:", collectionsWithData);

      // Get all workspaces
      const workspacesResponse = await workspaceService.getAll();
      const workspacesList = workspacesResponse.data || [];

      // Create workspace map
      const workspaceMap = {};
      workspacesList.forEach((ws) => {
        workspaceMap[ws.id] = ws;
      });
      setWorkspaces(workspaceMap);

      // Get repositories for each workspace
      const repoMap = {};
      for (const ws of workspacesList) {
        try {
          const reposResponse = await workspaceService.getRepositories(ws.id);
          const repos = reposResponse.data || [];
          repos.forEach((repo) => {
            repoMap[repo.id] = { ...repo, workspace_id: ws.id };
          });
        } catch (err) {
          console.error(`Error fetching repos for workspace ${ws.id}:`, err);
        }
      }
      setRepositories(repoMap);

      // Fetch cleaned data count for each collection
      const collectionsWithCleanedData = await Promise.all(
        collectionsWithData.map(async (collection) => {
          try {
            const cleanedDataRes = await collectionService.getCollectionCleanedData(
              collection.id
            );
            const cleanedCount = cleanedDataRes.data.cleaned_data?.length || 0;
            return {
              ...collection,
              cleaned_count: cleanedCount,
              is_cleaned: cleanedCount > 0,
            };
          } catch {
            return {
              ...collection,
              cleaned_count: 0,
              is_cleaned: false,
            };
          }
        })
      );

      // Sort by created_at descending
      collectionsWithCleanedData.sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );

      setCollections(collectionsWithCleanedData);

      // Calculate stats
      const cleanedCount = collectionsWithCleanedData.filter(
        (c) => c.is_cleaned
      ).length;
      const completedCount = collectionsWithCleanedData.filter(
        (c) => c.status === "completed"
      ).length;
      const interruptedCount = collectionsWithCleanedData.filter(
        (c) => c.status === "paused" || c.status === "in_progress" || c.status === "failed"
      ).length;
      const lastCollection =
        collectionsWithCleanedData.length > 0
          ? collectionsWithCleanedData[0].created_at
          : null;

      setStats({
        total: collectionsWithCleanedData.length,
        completed: completedCount,
        interrupted: interruptedCount,
        lastCollectionDate: lastCollection,
      });
    } catch (error) {
      console.error("Error fetching collections:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredCollections = collections.filter((collection) => {
    const repo = repositories[collection.repository_id];
    const workspace = repo ? workspaces[repo.workspace_id] : null;

    const searchLower = searchTerm.toLowerCase();
    const repoName = (repo?.name || collection.repository_name || "").toLowerCase();
    const workspaceName = (workspace?.name || "").toLowerCase();
    const platform = (workspace?.platform || collection.platform || "").toLowerCase();
    
    return (
      repoName.includes(searchLower) ||
      workspaceName.includes(searchLower) ||
      platform.includes(searchLower)
    );
  });

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getTimeDiff = (date) => {
    if (!date) return "N/A";
    const now = new Date();
    const past = new Date(date);
    const diffInMinutes = Math.floor((now - past) / (1000 * 60));

    if (diffInMinutes < 60) return `${diffInMinutes} min ago`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays === 1) return "yesterday";
    if (diffInDays < 7) return `${diffInDays} days ago`;
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
    return `${Math.floor(diffInDays / 30)} months ago`;
  };

  const handleCollectionClick = (collection) => {
    if (collection.is_external) {
      navigate(`/external/collection/${collection.id}`);
      return;
    }
    const repo = repositories[collection.repository_id];
    if (repo) {
      navigate(
        `/workspaces/${repo.workspace_id}/repositories/${collection.repository_id}/collection/${collection.id}`
      );
    }
  };

  const getSelectedMetricsCount = (collection) => {
    if (!collection.configuration?.selected_metrics) return 0;
    const metrics = collection.configuration.selected_metrics;
    return Object.values(metrics).flat().length;
  };

  const getPlatformIcon = (platform) => {
    if (platform === "github") {
      return <Github className="w-4 h-4" />;
    }
    return <GitBranch className="w-4 h-4" />;
  };

  const handleUploadSubmit = async () => {
    if (!uploadFile || !uploadPlatform || !uploadName.trim()) {
      setUploadError("Please fill all fields.");
      return;
    }
    setUploading(true);
    setUploadError("");
    setUploadProgress(0);
    try {
      await collectionService.uploadExternalCollection(
        uploadFile,
        uploadPlatform,
        uploadName.trim(),
        (progressEvent) => {
          if (progressEvent.total) {
            setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
          }
        }
      );
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadPlatform("");
      setUploadName("");
      setUploadProgress(0);
      fetchAllCollections();
    } catch (err) {
      setUploadError(err.response?.data?.error || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const openUploadModal = () => {
    setUploadFile(null);
    setUploadPlatform("");
    setUploadName("");
    setUploadError("");
    setShowUploadModal(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="text-gray-600">Loading collections...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
              Data Cleaning
            </h1>
            <p className="text-gray-600">
              Manage and clean your collected data from all projects
            </p>
          </div>
          <button
            onClick={openUploadModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <Upload className="w-4 h-4" />
            Upload External Data
          </button>
        </div>

        {/* Statistics Section */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Database className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                <p className="text-sm text-gray-500">Total Collections</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.completed}</p>
                <p className="text-sm text-gray-500">Completed</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.interrupted}</p>
                <p className="text-sm text-gray-500">Interrupted</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Calendar className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900 truncate">
                  {stats.lastCollectionDate
                    ? getTimeDiff(stats.lastCollectionDate)
                    : "No collections"}
                </p>
                <p className="text-sm text-gray-500">Last Collection</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search by project, workspace, or platform..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Collections Grid */}
        {filteredCollections.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-2">
              {searchTerm
                ? "No collections found matching your search"
                : "No collections yet"}
            </p>
            <p className="text-sm text-gray-400">
              Start a data collection to see it here
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
            {filteredCollections.map((collection) => {
              const repo = repositories[collection.repository_id];
              const workspace = repo ? workspaces[repo.workspace_id] : null;
              const metricsCount = getSelectedMetricsCount(collection);

              return (
                <div
                  key={collection.id}
                  onClick={() => handleCollectionClick(collection)}
                  className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 hover:shadow-lg hover:border-blue-300 transition-all cursor-pointer group flex flex-col h-full"
                >
                  {/* Header with status badge */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                        <FolderGit2 className="w-5 h-5 text-gray-600" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-semibold text-sm text-gray-900 truncate">
                          {repo?.name || collection.repository_name || "Unknown Project"}
                        </h3>
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          {getPlatformIcon(workspace?.platform || collection.platform)}
                          <span className="truncate">
                            {workspace?.name || (collection.is_external ? "External Upload" : "Unknown Workspace")}
                          </span>
                        </div>
                      </div>
                    </div>



                  </div>

                  {/* Collection info */}
                  <div className="space-y-2 text-xs sm:text-sm text-gray-600">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span>{formatDate(collection.created_at)}</span>
                    </div>




                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-gray-400" />
                      <span>
                        {collection.total_items || 0}{" "}
                        {(workspace?.platform || collection.platform) === "github" ? "PRs" : "MRs"}
                      </span>
                    </div>

                    {collection.is_cleaned && (
                      <div className="flex items-center gap-2">
                        <FileSpreadsheet className="w-4 h-4 text-gray-400" />
                        <span>{collection.cleaned_count} cleaned datasets</span>
                      </div>
                    )}
                  </div>

                  {/* Footer with arrow and status - pushed to bottom */}
                  <div className="mt-auto pt-3 border-t border-gray-100 flex items-center justify-between">
                    <span className="text-xs text-gray-400">
                      Click to manage
                    </span>
                    <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600 group-hover:translate-x-1 transition-all" />
                  </div>

                  <div className="flex items-center justify-end gap-1.5 flex-wrap">
                    {collection.status === "completed" ? (
                      <>
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          Completed
                        </span>
                        {collection.is_cleaned ? (
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" />
                            Cleaned
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded-full flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Not Cleaned
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Interrupted
                      </span>
                    )}
                    {collection.is_external && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full flex items-center gap-1">
                        Extern
                      </span>
                    )}
                  </div>
                </div>

              );
            })}
          </div>
        )}

        {/* Upload External Data Modal */}
        {showUploadModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 relative">
              <button
                onClick={() => setShowUploadModal(false)}
                className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>

              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Upload External Collected Data
              </h2>

              <div className="space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Collection Name
                  </label>
                  <input
                    type="text"
                    value={uploadName}
                    onChange={(e) => setUploadName(e.target.value)}
                    placeholder="e.g. my-project-data"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                </div>

                {/* Platform */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Platform
                  </label>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setUploadPlatform("github")}
                      className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                        uploadPlatform === "github"
                          ? "border-blue-500 bg-blue-50 text-blue-700"
                          : "border-gray-300 text-gray-600 hover:border-gray-400"
                      }`}
                    >
                      <Github className="w-4 h-4" />
                      GitHub
                    </button>
                    <button
                      type="button"
                      onClick={() => setUploadPlatform("gitlab")}
                      className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                        uploadPlatform === "gitlab"
                          ? "border-blue-500 bg-blue-50 text-blue-700"
                          : "border-gray-300 text-gray-600 hover:border-gray-400"
                      }`}
                    >
                      <GitBranch className="w-4 h-4" />
                      GitLab
                    </button>
                  </div>
                </div>

                {/* File */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    JSON File
                  </label>
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full px-3 py-4 border-2 border-dashed border-gray-300 rounded-lg text-center cursor-pointer hover:border-blue-400 transition-colors"
                  >
                    {uploadFile ? (
                      <div>
                        <span className="text-sm text-gray-700">{uploadFile.name}</span>
                        <span className="text-xs text-gray-400 ml-2">
                          ({(uploadFile.size / (1024 * 1024)).toFixed(1)} MB)
                        </span>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">
                        Click to select a .json file
                      </span>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json,application/json"
                    className="hidden"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  />
                </div>

                {uploadError && (
                  <p className="text-sm text-red-600">{uploadError}</p>
                )}

                {uploading && (
                  <div>
                    <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                      <span>Uploading{uploadFile ? ` (${(uploadFile.size / (1024 * 1024)).toFixed(1)} MB)` : ''}...</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}

                <button
                  onClick={handleUploadSubmit}
                  disabled={uploading || !uploadFile || !uploadPlatform || !uploadName.trim()}
                  className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Upload
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DataCleaningList;
