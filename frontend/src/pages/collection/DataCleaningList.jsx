/**
 * frontend/src/pages/collection/DataCleaningList.jsx
 * Page displaying all collections for data cleaning management
 */

import { useState, useEffect } from "react";
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
    const repoName = repo?.name?.toLowerCase() || "";
    const workspaceName = workspace?.name?.toLowerCase() || "";
    const platform = workspace?.platform?.toLowerCase() || "";
    
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
        <div className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
            Data Cleaning
          </h1>
          <p className="text-gray-600">
            Manage and clean your collected data from all projects
          </p>
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
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Calendar className="w-6 h-6 text-purple-600" />
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
                          {repo?.name || "Unknown Project"}
                        </h3>
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          {workspace && getPlatformIcon(workspace.platform)}
                          <span className="truncate">
                            {workspace?.name || "Unknown Workspace"}
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
                        {workspace?.platform === "github" ? "PRs" : "MRs"}
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

                  <div className="flex items-center justify-end">
                    {collection.status === "completed" ? (
                      collection.is_cleaned ? (
                        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          Cleaned
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          Completed
                        </span>
                      )
                    ) : (
                      <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Interrupted
                      </span>
                    )}
                  </div>
                </div>
                
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default DataCleaningList;
