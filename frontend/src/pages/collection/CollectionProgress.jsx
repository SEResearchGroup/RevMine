import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { Github, GitBranch, FolderGit2, AlertCircle, ArrowLeft, RefreshCw, Play, AlertTriangle, WifiOff } from "lucide-react";
import { collectionService, workspaceService } from "../../services/api";

function CollectionProgress() {
  const { workspaceId, repositoryId, planId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [repository, setRepository] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isResuming, setIsResuming] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const consecutiveErrorsRef = useRef(0);
  const MAX_CONSECUTIVE_ERRORS = 3;
  
  // Check if this is a resume operation
  const isResume = location.state?.resume || false;

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
      consecutiveErrorsRef.current = 0; // Reset error counter on success
      setConnectionError(false);

      // If completed, navigate to results
      if (res.data.status === "completed") {
        setTimeout(() => {
          navigate(
            `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planId}/results`
          );
        }, 1000);
      }
      
      // If failed or paused, show error modal with progress info
      if (res.data.status === "failed" || res.data.status === "paused") {
        setErrorMessage(res.data.error_message || "The collection was interrupted.");
        setShowErrorModal(true);
      }
    } catch (err) {
      console.error("Error polling status:", err);
      consecutiveErrorsRef.current += 1;
      
      // After multiple consecutive errors, show connection lost modal
      if (consecutiveErrorsRef.current >= MAX_CONSECUTIVE_ERRORS) {
        setConnectionError(true);
        setErrorMessage("Connection lost. The server may be unavailable or the collection container may have stopped.");
        setShowErrorModal(true);
      }
    }
  };

  const handleGoToProject = () => {
    // Navigate to project detail with interrupted collection info
    navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collect`, {
      state: {
        interruptedCollection: {
          id: planId,
          collected_items: status?.collected_items || 0,
          total_items: status?.total_items || 0,
          progress_percentage: status?.progress_percentage || 0,
          last_collected_item: status?.last_collected_item,
          can_resume: status?.can_resume
        }
      }
    });
  };

  const handleContinueCollection = async () => {
    try {
      setIsResuming(true);
      setShowErrorModal(false);
      await collectionService.resumeCollection(planId);
      // Continue polling
    } catch (err) {
      setErrorMessage("Failed to resume collection: " + err.message);
      setShowErrorModal(true);
    } finally {
      setIsResuming(false);
    }
  };

  const handleRetry = () => {
    navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collect`);
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

      {/* Error/Interruption Modal */}
      {showErrorModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                connectionError ? 'bg-orange-100' : status?.can_resume ? 'bg-yellow-100' : 'bg-red-100'
              }`}>
                {connectionError ? (
                  <WifiOff className="w-6 h-6 text-orange-600" />
                ) : status?.can_resume ? (
                  <AlertTriangle className="w-6 h-6 text-yellow-600" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-red-600" />
                )}
              </div>
              <h3 className="text-xl font-semibold text-gray-900">
                {connectionError ? 'Connection Lost' : status?.can_resume ? 'Collection Interrupted' : 'Collection Failed'}
              </h3>
            </div>
            
            {/* Progress Info */}
            {status && (status.collected_items > 0 || status.total_items > 0) && (
              <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-gray-600">Progress</span>
                  <span className="text-lg font-bold text-gray-900">
                    {status.progress_percentage}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className={`h-2 rounded-full ${connectionError ? 'bg-orange-500' : status?.can_resume ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${status.progress_percentage}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>
                    {status.collected_items} / {status.total_items} {workspace?.platform === 'github' ? 'PRs' : 'MRs'} collected
                  </span>
                  {status.last_collected_item && (
                    <span>Last: #{status.last_collected_item}</span>
                  )}
                </div>
              </div>
            )}
            
            <div className="mb-6">
              <p className="text-gray-600 mb-3">
                {connectionError 
                  ? 'Unable to reach the server. The collection may still be running in the background, or the service may have stopped.'
                  : status?.can_resume 
                    ? 'The collection was interrupted but can be resumed from where it stopped.'
                    : 'An error occurred during the data collection:'}
              </p>
              {errorMessage && (
                <div className={`border rounded-lg p-3 ${
                  connectionError ? 'bg-orange-50 border-orange-200' : status?.can_resume ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'
                }`}>
                  <p className={`text-sm font-mono ${
                    connectionError ? 'text-orange-800' : status?.can_resume ? 'text-yellow-800' : 'text-red-800'
                  }`}>
                    {errorMessage}
                  </p>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3">
              {connectionError && (
                <button
                  onClick={() => {
                    setShowErrorModal(false);
                    setConnectionError(false);
                    consecutiveErrorsRef.current = 0;
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry Connection
                </button>
              )}
              
              {!connectionError && status?.can_resume && (
                <button
                  onClick={handleContinueCollection}
                  disabled={isResuming}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors disabled:opacity-50"
                >
                  {isResuming ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Resuming...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Continue Collection Now
                    </>
                  )}
                </button>
              )}
              
              <div className="flex gap-3">
                <button
                  onClick={handleGoToProject}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  {connectionError ? 'Back to Project' : status?.can_resume ? 'Continue Later' : 'Back to Project'}
                </button>
                {!connectionError && !status?.can_resume && (
                  <button
                    onClick={handleRetry}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Start New Collection
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CollectionProgress;