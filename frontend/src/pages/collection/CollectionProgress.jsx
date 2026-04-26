import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  Github,
  GitBranch,
  FolderGit2,
  AlertCircle,
  ArrowLeft,
  RefreshCw,
  Play,
  AlertTriangle,
  WifiOff,
  Loader2,
  Pause,
  Trash2,
  StopCircle,
} from "lucide-react";
import { collectionService, workspaceService } from "../../services/api";
import {
  clearAutomaticWorkflow,
  readAutomaticWorkflow,
  sanitizeAutomaticCleaningDraft,
} from "../../components/collection/automaticWorkflow";

const getApiErrorMessage = (error, fallbackMessage) =>
  error?.response?.data?.error ||
  error?.response?.data?.detail?.message ||
  error?.response?.data?.detail ||
  error?.message ||
  fallbackMessage;

const getCollectionStatusValue = (status) =>
  status?.collection_plan?.status || status?.status;

/**
 * Round a number up to the nearest "nice" ceiling for approximate display.
 * e.g., 8942 → 8950, 342 → 350, 12 → 15, 1234 → 1250
 */
const roundUpApproximate = (n) => {
  if (n <= 10) return n + 5;
  if (n <= 100) return Math.ceil(n / 10) * 10;
  if (n <= 1000) return Math.ceil(n / 50) * 50;
  return Math.ceil(n / 50) * 50;
};

/**
 * Format the total items for display, accounting for approximate totals.
 */
const formatTotalItems = (status) => {
  if (!status?.total_items) return "...";
  const isApproximate =
    status.is_total_approximate ||
    status.collection_plan?.is_total_approximate;
  if (isApproximate) {
    return `≤ ${roundUpApproximate(status.total_items)}`;
  }
  return status.total_items;
};

function CollectionProgress() {
  const { workspaceId, repositoryId, planId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const initialAutomaticWorkflow =
    location.state?.automaticWorkflow || readAutomaticWorkflow(planId);

  const [repository, setRepository] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isResuming, setIsResuming] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [automaticWorkflow, setAutomaticWorkflow] = useState(
    initialAutomaticWorkflow
  );
  const [automaticCleaning, setAutomaticCleaning] = useState({
    running: false,
    error: null,
    message: "",
    warnings: [],
  });
  const [showStopModal, setShowStopModal] = useState(false);
  const [isStopping, setIsStopping] = useState(false);

  const consecutiveErrorsRef = useRef(0);
  const automaticTransitionStartedRef = useRef(false);
  const completionNavigationStartedRef = useRef(false);
  const automaticWorkflowRef = useRef(initialAutomaticWorkflow);
  const MAX_CONSECUTIVE_ERRORS = 3;

  const isAutomaticWorkflow = automaticWorkflow?.type === "automatic";
  const collectionStatusValue = getCollectionStatusValue(status);
  const itemLabel = repository?.platform === "github" ? "PRs" : "MRs";

  useEffect(() => {
    if (location.state?.automaticWorkflow) {
      setAutomaticWorkflow(location.state.automaticWorkflow);
    }
  }, [location.state]);

  useEffect(() => {
    automaticWorkflowRef.current = automaticWorkflow;
  }, [automaticWorkflow]);

  useEffect(() => {
    fetchInitialData();
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [planId]);

  const fetchInitialData = async () => {
    try {
      const [wsRes, reposRes] = await Promise.all([
        workspaceService.getById(workspaceId),
        workspaceService.getRepositories(workspaceId),
      ]);

      setWorkspace(wsRes.data);
      const repo = reposRes.data.find((r) => r.id === parseInt(repositoryId, 10));
      setRepository(repo);

      await pollStatus();
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  };

  const navigateToResults = () => {
    if (completionNavigationStartedRef.current) {
      return;
    }

    completionNavigationStartedRef.current = true;
    setTimeout(() => {
      navigate(
        `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planId}/results`
      );
    }, 1000);
  };

  const runAutomaticCleaning = async () => {
    if (automaticTransitionStartedRef.current) {
      return;
    }

    const workflow = automaticWorkflowRef.current || readAutomaticWorkflow(planId);
    if (!workflow?.draft?.cleaning) {
      navigateToResults();
      return;
    }

    automaticTransitionStartedRef.current = true;
    setAutomaticCleaning({
      running: true,
      error: null,
      message: "Preparing cleaning filters...",
      warnings: [],
    });

    try {
      const cleaningConfigRes = await collectionService.getCleaningConfig(planId);
      const { payload, runtimeWarnings } = sanitizeAutomaticCleaningDraft(
        workflow.draft.cleaning,
        cleaningConfigRes.data
      );

      setAutomaticCleaning({
        running: true,
        error: null,
        message: "Running automatic cleaning...",
        warnings: runtimeWarnings,
      });

      const cleanedDataRes = await collectionService.createCleanedData({
        ...payload,
        collection_id: parseInt(planId, 10),
      });

      clearAutomaticWorkflow(planId);
      completionNavigationStartedRef.current = true;

      navigate(
        `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planId}/cleaned-data/${cleanedDataRes.data.cleaned_data.id}`
      );
    } catch (err) {
      automaticTransitionStartedRef.current = false;
      setAutomaticCleaning((previousState) => ({
        ...previousState,
        running: false,
        error: getApiErrorMessage(
          err,
          "Automatic cleaning failed after collection completed."
        ),
      }));
    }
  };

  const pollStatus = async () => {
    try {
      const res = await collectionService.getStatus(planId);
      const nextStatus = res.data;
      const statusValue = getCollectionStatusValue(nextStatus);

      setStatus(nextStatus);
      consecutiveErrorsRef.current = 0;
      setConnectionError(false);

      if (statusValue === "completed") {
        if (automaticWorkflowRef.current?.type === "automatic") {
          runAutomaticCleaning();
        } else {
          navigateToResults();
        }
      }

      if (statusValue === "failed" || statusValue === "paused") {
        setErrorMessage(
          nextStatus?.collection_plan?.error_message ||
            nextStatus?.error_message ||
            "The collection was interrupted."
        );
        setShowErrorModal(true);
      }
    } catch (err) {
      console.error("Error polling status:", err);
      consecutiveErrorsRef.current += 1;

      if (consecutiveErrorsRef.current >= MAX_CONSECUTIVE_ERRORS) {
        setConnectionError(true);
        setErrorMessage(
          "Connection lost. The server may be unavailable or the collection container may have stopped."
        );
        setShowErrorModal(true);
      }
    }
  };

  const handleGoToProject = () => {
    navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collect`, {
      state: {
        interruptedCollection: {
          id: planId,
          collected_items: status?.collected_items || 0,
          total_items: status?.total_items || 0,
          progress_percentage: status?.progress_percentage || 0,
          last_collected_item:
            status?.last_collected_item ||
            status?.collection_plan?.last_collected_item_id,
          can_resume: status?.can_resume,
        },
      },
    });
  };

  const handleContinueCollection = async () => {
    try {
      setIsResuming(true);
      setShowErrorModal(false);
      await collectionService.resumeCollection(planId);
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

  const handleOpenManualCleaning = () => {
    clearAutomaticWorkflow(planId);
    navigate(
      `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planId}/cleaned-data/new`
    );
  };

  const handleRetryAutomaticCleaning = () => {
    automaticTransitionStartedRef.current = false;
    setAutomaticCleaning({
      running: false,
      error: null,
      message: "",
      warnings: [],
    });
    runAutomaticCleaning();
  };

  const handlePauseCollection = async () => {
    try {
      setIsStopping(true);
      await collectionService.pauseCollection(planId);
      setShowStopModal(false);
      navigate(
        `/workspaces/${workspaceId}/repositories/${repositoryId}/collect`,
        {
          state: {
            interruptedCollection: {
              id: planId,
              collected_items: status?.collected_items || 0,
              total_items: status?.total_items || 0,
              progress_percentage: status?.progress_percentage || 0,
              last_collected_item:
                status?.last_collected_item ||
                status?.collection_plan?.last_collected_item_id,
              can_resume: true,
            },
          },
        }
      );
    } catch (err) {
      setErrorMessage(
        getApiErrorMessage(err, "Failed to pause collection")
      );
      setShowStopModal(false);
      setShowErrorModal(true);
    } finally {
      setIsStopping(false);
    }
  };

  const handleCancelCollection = async () => {
    try {
      setIsStopping(true);
      await collectionService.deleteCollection(planId);
      setShowStopModal(false);
      navigate(
        `/workspaces/${workspaceId}/repositories/${repositoryId}/collect`
      );
    } catch (err) {
      setErrorMessage(
        getApiErrorMessage(err, "Failed to cancel collection")
      );
      setShowStopModal(false);
      setShowErrorModal(true);
    } finally {
      setIsStopping(false);
    }
  };

  if (loading || !repository) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  const progressTitle = automaticCleaning.running
    ? "Automatic Workflow in Progress"
    : "Collection in Progress";
  const progressDescription = automaticCleaning.running
    ? automaticCleaning.message
    : isAutomaticWorkflow
      ? "Please wait while we collect your code review data. Cleaning will start automatically when collection is complete."
      : "Please wait while we collect your code review data";

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <button
          onClick={() =>
            navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collect`)
          }
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Project</span>
        </button>

        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center shrink-0">
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

        <div className="bg-white rounded-xl border border-gray-200 p-8">
          <h2 className="text-2xl font-semibold text-center mb-2">
            {progressTitle}
          </h2>
          <p className="text-center text-gray-600 mb-8">{progressDescription}</p>

          {status && (
            <>
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
                  <span>
                    Started at{" "}
                    {status.collection_plan?.started_at
                      ? new Date(
                          status.collection_plan.started_at
                        ).toLocaleTimeString()
                      : "-"}
                  </span>
                  <span>
                    {status.collected_items} / {formatTotalItems(status)} items
                  </span>
                </div>
              </div>

              {isAutomaticWorkflow && (
                <div className="mb-6 rounded-xl border border-sky-200 bg-sky-50 p-5">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {automaticCleaning.running ? (
                        <Loader2 className="w-5 h-5 animate-spin text-blue-700" />
                      ) : (
                        <Play className="w-5 h-5 text-blue-700" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-blue-950 mb-1">
                        Automatic collection + cleaning workflow
                      </p>
                      <p className="text-sm text-blue-900">
                        {collectionStatusValue === "completed"
                          ? automaticCleaning.running
                            ? automaticCleaning.message
                            : automaticCleaning.error
                              ? "Collection finished, but the automatic cleaning step needs attention."
                              : "Collection finished. Starting automatic cleaning."
                          : "This flow uses the same collection progress screen as manual mode, then continues directly into cleaning."}
                      </p>

                      {automaticCleaning.warnings.length > 0 && (
                        <div className="mt-3 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
                          <p className="text-sm font-medium text-yellow-900 mb-1">
                            Cleaning adjustments
                          </p>
                          <ul className="space-y-1 text-sm text-yellow-800">
                            {automaticCleaning.warnings.map((warning, index) => (
                              <li key={`${warning}-${index}`}>{warning}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {automaticCleaning.error && (
                        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-4">
                          <p className="text-sm font-medium text-red-900 mb-2">
                            Automatic cleaning could not complete
                          </p>
                          <p className="text-sm text-red-800">
                            {automaticCleaning.error}
                          </p>
                          <div className="mt-4 flex flex-wrap gap-3">
                            <button
                              onClick={handleRetryAutomaticCleaning}
                              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                            >
                              Retry automatic cleaning
                            </button>
                            <button
                              onClick={handleOpenManualCleaning}
                              className="px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-100 transition-colors"
                            >
                              Open manual cleaning
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

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

              <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4 flex gap-3">
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">Note:</p>
                  <p>
                    {isAutomaticWorkflow
                      ? "You can safely navigate away. Collection continues in the background, and automatic cleaning will run the next time this workflow page is opened after collection completes."
                      : "You can safely navigate away. The collection will continue in the background."}
                  </p>
                </div>
              </div>

              {collectionStatusValue === "in_progress" && (
                <div className="mt-4 flex justify-center">
                  <button
                    onClick={() => setShowStopModal(true)}
                    className="flex items-center gap-2 px-5 py-2.5 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                  >
                    <StopCircle className="w-4 h-4" />
                    Stop Collection
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {showStopModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <StopCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900">
                Stop Collection
              </h3>
            </div>

            {status && (status.collected_items > 0 || status.total_items > 0) && (
              <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Current progress</span>
                  <span className="font-medium text-gray-900">
                    {status.collected_items} / {formatTotalItems(status)} {itemLabel}
                  </span>
                </div>
              </div>
            )}

            <p className="text-gray-600 mb-6">
              Choose how you want to stop the collection:
            </p>

            <div className="flex flex-col gap-3">
              <button
                onClick={handlePauseCollection}
                disabled={isStopping}
                className="w-full flex items-center gap-3 px-4 py-3 border border-yellow-300 bg-yellow-50 text-yellow-900 rounded-lg hover:bg-yellow-100 transition-colors disabled:opacity-50"
              >
                <Pause className="w-5 h-5 text-yellow-600 shrink-0" />
                <div className="text-left">
                  <p className="font-medium">Pause &amp; keep data</p>
                  <p className="text-xs text-yellow-700">
                    Stop now and resume later from where it left off
                  </p>
                </div>
              </button>

              <button
                onClick={handleCancelCollection}
                disabled={isStopping}
                className="w-full flex items-center gap-3 px-4 py-3 border border-red-300 bg-red-50 text-red-900 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-5 h-5 text-red-600 shrink-0" />
                <div className="text-left">
                  <p className="font-medium">Cancel &amp; delete</p>
                  <p className="text-xs text-red-700">
                    Stop and permanently delete all collected data
                  </p>
                </div>
              </button>

              <button
                onClick={() => setShowStopModal(false)}
                disabled={isStopping}
                className="w-full px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Continue collecting
              </button>
            </div>

            {isStopping && (
              <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin" />
                Stopping collection...
              </div>
            )}
          </div>
        </div>
      )}

      {showErrorModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center ${
                  connectionError
                    ? "bg-orange-100"
                    : status?.can_resume
                      ? "bg-yellow-100"
                      : "bg-red-100"
                }`}
              >
                {connectionError ? (
                  <WifiOff className="w-6 h-6 text-orange-600" />
                ) : status?.can_resume ? (
                  <AlertTriangle className="w-6 h-6 text-yellow-600" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-red-600" />
                )}
              </div>
              <h3 className="text-xl font-semibold text-gray-900">
                {connectionError
                  ? "Connection Lost"
                  : status?.can_resume
                    ? "Collection Interrupted"
                    : "Collection Failed"}
              </h3>
            </div>

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
                    className={`h-2 rounded-full ${
                      connectionError
                        ? "bg-orange-500"
                        : status?.can_resume
                          ? "bg-yellow-500"
                          : "bg-red-500"
                    }`}
                    style={{ width: `${status.progress_percentage}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>
                    {status.collected_items} / {formatTotalItems(status)} {itemLabel} collected
                  </span>
                  {(status.last_collected_item ||
                    status.collection_plan?.last_collected_item_id) && (
                    <span>
                      Last: #
                      {status.last_collected_item ||
                        status.collection_plan?.last_collected_item_id}
                    </span>
                  )}
                </div>
              </div>
            )}

            <div className="mb-6">
              <p className="text-gray-600 mb-3">
                {connectionError
                  ? "Unable to reach the server. The collection may still be running in the background, or the service may have stopped."
                  : status?.can_resume
                    ? "The collection was interrupted but can be resumed from where it stopped."
                    : "An error occurred during the data collection:"}
              </p>
              {errorMessage && (
                <div
                  className={`border rounded-lg p-3 ${
                    connectionError
                      ? "bg-orange-50 border-orange-200"
                      : status?.can_resume
                        ? "bg-yellow-50 border-yellow-200"
                        : "bg-red-50 border-red-200"
                  }`}
                >
                  <p
                    className={`text-sm font-mono ${
                      connectionError
                        ? "text-orange-800"
                        : status?.can_resume
                          ? "text-yellow-800"
                          : "text-red-800"
                    }`}
                  >
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
                  {connectionError
                    ? "Back to Project"
                    : status?.can_resume
                      ? "Continue Later"
                      : "Back to Project"}
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
