import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Github, GitBranch, FolderGit2 } from "lucide-react";
import { collectionService, workspaceService } from "../../services/api";

function CollectionProgress() {
  const { workspaceId, repositoryId, planId } = useParams();
  const navigate = useNavigate();

  const [repository, setRepository] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInitialData();
    const interval = setInterval(pollStatus, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [planId]);

  const fetchInitialData = async () => {
    try {
      const [wsRes, reposRes] = await Promise.all([
        workspaceService.getById(workspaceId),
        workspaceService.getRepositories(workspaceId),
      ]);

      setWorkspace(wsRes.data);
      const repo = reposRes.data.find((r) => r.id === parseInt(repositoryId));
      setRepository(repo);
      
      await pollStatus();
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  };

  const pollStatus = async () => {
    try {
      const res = await collectionService.getStatus(planId);
      setStatus(res.data);

      // If completed or failed, navigate to results
      if (res.data.status === "completed") {
        setTimeout(() => {
          navigate(
            `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planId}/results`
          );
        }, 1000);
      }
    } catch (err) {
      console.error("Error polling status:", err);
    }
  };

  if (loading || !repository) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
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
              <p className="text-gray-600 mb-2">
                {repository.description || "No description provided"}
              </p>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <FolderGit2 className="w-4 h-4" />
                <span>{repository.full_name}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Collection Progress */}
        <div className="bg-white rounded-xl border border-gray-200 p-8">
          <h2 className="text-2xl font-semibold text-center mb-2">
            Collection in Progress
          </h2>
          <p className="text-center text-gray-600 mb-8">
            Please wait while we collect your code review data
          </p>

          {status && (
            <>
              {/* Progress Bar */}
              <div className="mb-6">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    Overall Progress
                  </span>
                  <span className="text-2xl font-bold text-blue-600">
                    {status.progress_percentage}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div
                    className="bg-blue-600 h-4 rounded-full transition-all duration-500"
                    style={{ width: `${status.progress_percentage}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>Started at {new Date(status.collection_plan.started_at).toLocaleTimeString()}</span>
                  <span>{status.collected_items} / {status.total_items || "..."} items</span>
                </div>
              </div>

              {/* Stats Cards */}
              {status.stats && Object.keys(status.stats).length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-8">
                  {Object.entries(status.stats).map(([key, value]) => {
                    if (key.includes("_count")) {
                      const metricName = key.replace("_count", "").replace("_", " ");
                      return (
                        <div
                          key={key}
                          className="bg-gray-50 rounded-lg p-4 text-center"
                        >
                          <div className="text-2xl font-bold text-gray-900">
                            {value}
                          </div>
                          <div className="text-sm text-gray-600 capitalize">
                            {metricName}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  })}
                </div>
              )}

              {/* Info Note */}
              <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4 flex gap-3">
                
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">Note:</p>
                  <p>
                    You can safely navigate away. The collection will continue in
                    the background.
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default CollectionProgress;