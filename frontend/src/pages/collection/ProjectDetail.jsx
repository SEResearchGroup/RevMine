import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
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
  Eye,
  AlertCircle,
  AlertTriangle,
  Play,
  X,
  Loader2,
} from "lucide-react";
import { workspaceService, collectionService } from "../../services/api";
import CollectPlanModal from "../../components/collection/CollectPlanModal";
import AutomaticCollectionReview from "../../components/collection/AutomaticCollectionReview";
import { persistAutomaticWorkflow } from "../../components/collection/automaticWorkflow";

const getApiErrorMessage = (error, fallbackMessage) => {
  return (
    error?.response?.data?.error ||
    error?.response?.data?.detail?.message ||
    error?.response?.data?.detail ||
    error?.message ||
    fallbackMessage
  );
};

function ProjectDetail() {
  const { workspaceId, repositoryId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [repository, setRepository] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [platform, setPlatform] = useState("");

  // Available metrics (categorized) - loaded WITHOUT creating a collection
  const [availableMetrics, setAvailableMetrics] = useState({});

  // Selected metrics (flat list of values)
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [searchMetric, setSearchMetric] = useState("");
  const [selectAll, setSelectAll] = useState(false);

  // Expanded categories
  const [expandedCategories, setExpandedCategories] = useState({});

  // Branches - loaded WITHOUT creating a collection
  const [branches, setBranches] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState("");
  const [showBranchDropdown, setShowBranchDropdown] = useState(false);
  const [loadingBranches, setLoadingBranches] = useState(false);

  // Filters
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedStatus, setSelectedStatus] = useState(["open", "closed", "merged"]);
  const [saveBatchSize, setSaveBatchSize] = useState(1);
  const [editingBatchSize, setEditingBatchSize] = useState(false);
  const [batchSizeDraft, setBatchSizeDraft] = useState(1);
  const [collectionMode, setCollectionMode] = useState("manual");

  // Global date range of MRs/PRs in the repository
  const [dateRange, setDateRange] = useState({ first_date: null, last_date: null });

  // Automatic mode
  const [automationPrompt, setAutomationPrompt] = useState("");
  const [automationDraft, setAutomationDraft] = useState(null);
  const [automationWarnings, setAutomationWarnings] = useState([]);
  const [automationLoading, setAutomationLoading] = useState(false);
  const [automationExecuting, setAutomationExecuting] = useState(false);
  const [automationError, setAutomationError] = useState(null);
  const [automationProvider, setAutomationProvider] = useState("openrouter");
  const [automationModel, setAutomationModel] = useState("openai/gpt-4o-mini");

  // Modal
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [collectionPlan, setCollectionPlan] = useState(null);
  const [collectionPlanMode, setCollectionPlanMode] = useState("manual");
  const [collectionPlanAutomationContext, setCollectionPlanAutomationContext] =
    useState(null);

  // Collection History
  const [collectionHistory, setCollectionHistory] = useState([]);
  // Delete confirmation modal
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [collectionToDelete, setCollectionToDelete] = useState(null);
  const [deletingCollection, setDeletingCollection] = useState(false);

  // Warning modal for incomplete collections
  const [showIncompleteWarning, setShowIncompleteWarning] = useState(false);
  const [incompleteCollections, setIncompleteCollections] = useState([]);

  // Loading state for creating collection
  const [creatingCollection, setCreatingCollection] = useState(false);
  const [pendingActionType, setPendingActionType] = useState(null);

  // Interrupted collection notification (only for paused/failed, NOT in_progress)
  const [interruptedNotifications, setInterruptedNotifications] = useState([]);
  const [resumingCollection, setResumingCollection] = useState(null);

  // Track running collections for real-time status updates
  const [runningCollections, setRunningCollections] = useState(new Set());
  const pollingIntervalRef = useRef(null);

  // Prevent duplicate data fetching
  const dataFetchedRef = useRef(false);

  // Load dismissed notifications from localStorage
  const getDismissedNotifications = () => {
    try {
      const dismissed = localStorage.getItem(`dismissed_collection_warnings_${repositoryId}`);
      return dismissed ? JSON.parse(dismissed) : [];
    } catch {
      return [];
    }
  };

  const dismissNotification = (collectionId) => {
    const dismissed = getDismissedNotifications();
    if (!dismissed.includes(collectionId)) {
      dismissed.push(collectionId);
      localStorage.setItem(`dismissed_collection_warnings_${repositoryId}`, JSON.stringify(dismissed));
    }
    setInterruptedNotifications(prev => prev.filter(n => n.id !== collectionId));
  };

  // Check for interrupted collection from navigation state
  useEffect(() => {
    if (location.state?.interruptedCollection) {
      const interruptedFromNav = location.state.interruptedCollection;
      const dismissed = getDismissedNotifications();

      // Add to notifications if not dismissed
      if (!dismissed.includes(interruptedFromNav.id)) {
        setInterruptedNotifications(prev => {
          // Avoid duplicates
          if (prev.some(n => n.id === interruptedFromNav.id)) return prev;
          return [...prev, interruptedFromNav];
        });
      }

      // Clear the state to prevent showing again on refresh
      window.history.replaceState({}, document.title);
    }
  }, [location.state, repositoryId]);

  useEffect(() => {
    if (!dataFetchedRef.current) {
      dataFetchedRef.current = true;
      fetchData();
      fetchCollectionHistory();
    }

    return () => {
      dataFetchedRef.current = false;
    };
  }, [workspaceId, repositoryId]);

  // Poll running collections to update their progress in real-time
  useEffect(() => {
    if (runningCollections.size > 0) {
      // Start polling every 3 seconds when there are running collections
      pollingIntervalRef.current = setInterval(() => {
        fetchCollectionHistory();
      }, 3000);
    } else {
      // Clear polling when no running collections
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [runningCollections.size]);

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

      // After getting repository, load metrics and branches WITHOUT creating a collection
      await loadMetricsAndBranches(repo.platform);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadMetricsAndBranches = async (repoPlatform) => {
    try {
      // Get available metrics (does NOT create a collection)
      const metricsRes = await collectionService.getAvailableMetrics(
        repositoryId,
        repoPlatform
      );

      setAvailableMetrics(metricsRes.data.available_metrics);

      // If there's already an active collection, restore its settings
      if (metricsRes.data.has_active_collection && metricsRes.data.active_collection) {
        const existingCollection = metricsRes.data.active_collection;

        // Restore selected metrics if any
        if (existingCollection.selected_metrics?.length > 0) {
          setSelectedMetrics(existingCollection.selected_metrics);
        }

        // Restore filters
        const existingFilters = existingCollection.filters || {};
        if (existingFilters.start_date) setStartDate(existingFilters.start_date);
        if (existingFilters.end_date) setEndDate(existingFilters.end_date);
        if (existingFilters.status?.length > 0) setSelectedStatus(existingFilters.status);

        // Restore branch
        if (existingCollection.branch_name) {
          setSelectedBranch(existingCollection.branch_name);
        }
      }

      // Expand all categories by default
      const allCategories = {};
      Object.keys(metricsRes.data.available_metrics).forEach((category) => {
        allCategories[category] = true;
      });
      setExpandedCategories(allCategories);

      // Fetch branches (does NOT create a collection)
      await fetchBranches();
    } catch (err) {
      console.error("Error loading metrics and branches:", err);
      // Non-fatal error - page can still work
    }
  };

  const fetchCollectionHistory = async () => {
    try {
      const res = await collectionService.getHistory(repositoryId);
      const collections = res.data.collections || [];
      setCollectionHistory(collections);

      // Track running collections (in_progress) - no notifications for these
      const runningIds = new Set(
        collections.filter(c => c.status === 'in_progress').map(c => c.id)
      );
      setRunningCollections(runningIds);

      // Load interrupted collections as notifications (paused, failed ONLY - not in_progress)
      const dismissed = getDismissedNotifications();
      const interruptedCollections = collections.filter(
        c => ['paused', 'failed'].includes(c.status) && !dismissed.includes(c.id)
      );

      // Add to notifications without duplicates
      setInterruptedNotifications(prev => {
        const existingIds = new Set(prev.map(n => n.id));
        const newNotifications = interruptedCollections
          .filter(c => !existingIds.has(c.id))
          .map(c => ({
            id: c.id,
            collected_items: c.collected_items,
            total_items: c.total_items,
            progress_percentage: c.progress_percentage || Math.round((c.collected_items / c.total_items) * 100) || 0,
            last_collected_item: c.last_collected_item_id,
            can_resume: c.can_resume,
            status: c.status,
            error_message: c.error_message
          }));
        return [...prev, ...newNotifications];
      });
    } catch (err) {
      console.error("Error fetching history:", err);
    } 
  };

  /**
   * Fetch branches WITHOUT creating a collection.
   * Uses the new endpoint that only needs workspace/repository IDs.
   */
  const fetchBranches = async () => {
    try {
      setLoadingBranches(true);
      const res = await collectionService.getBranchesForRepository(
        workspaceId,
        repositoryId
      );
      setBranches(res.data.branches || []);

      // Store global date range of MRs/PRs
      if (res.data.date_range) {
        setDateRange(res.data.date_range);
      }

      // Only set default branch if not already set (from active collection)
      if (!selectedBranch) {
        setSelectedBranch(res.data.default_branch || "");
      }
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

  const applyAutomationCollectionToForm = (collectionDraft) => {
    if (!collectionDraft) return;

    setSelectedMetrics(collectionDraft.selected_metrics || []);
    setSelectedBranch(collectionDraft.branch_name || "");
    setStartDate(collectionDraft.start_date || "");
    setEndDate(collectionDraft.end_date || "");
    setSelectedStatus(
      collectionDraft.status?.length > 0
        ? collectionDraft.status
        : ["open", "closed", "merged"]
    );
  };

  const buildMetricLabels = () => {
    const labels = {};
    Object.values(availableMetrics).forEach((metricList) => {
      metricList.forEach((metric) => {
        labels[metric.value] = metric.label;
      });
    });
    return labels;
  };

  const buildAutomaticWorkflowPayload = () => {
    if (!automationDraft) {
      return null;
    }

    return {
      type: "automatic",
      prompt: automationPrompt,
      warnings: automationWarnings,
      draft: automationDraft,
    };
  };

  const handleGenerateAutomationDraft = async () => {
    try {
      setAutomationLoading(true);
      setAutomationError(null);
      setAutomationDraft(null);
      setAutomationWarnings([]);

      const response = await collectionService.generateAutomationDraft({
        workspace_id: Number(workspaceId),
        repository_id: Number(repositoryId),
        prompt: automationPrompt,
        llm_provider: automationProvider,
        model: automationModel,
      });

      setAutomationDraft(response.data.draft);
      setAutomationWarnings(response.data.warnings || []);
      applyAutomationCollectionToForm(response.data.draft.collection);
    } catch (err) {
      setAutomationError(
        getApiErrorMessage(err, "Failed to generate an automatic draft.")
      );
    } finally {
      setAutomationLoading(false);
    }
  };

  /**
   * Handle "Go to collect plan" button click.
   * Check for incomplete collections first, then create if confirmed.
   */
  const handleGoToPlan = async () => {
    if (selectedMetrics.length === 0) {
      alert("Please select at least one metric");
      return;
    }

    if (!selectedBranch) {
      alert("Please select a branch");
      return;
    }

    // Check for incomplete collections
    const incomplete = collectionHistory.filter(
      c => ['paused', 'failed', 'in_progress'].includes(c.status)
    );

    if (incomplete.length > 0) {
      setPendingActionType("manual");
      setIncompleteCollections(incomplete);
      setShowIncompleteWarning(true);
      return;
    }

    // No incomplete collections, proceed directly
    await proceedWithNewCollection();
  };

  const handleApproveAutomation = async () => {
    if (!automationDraft) {
      return;
    }

    const incomplete = collectionHistory.filter(
      (collection) => ["paused", "failed", "in_progress"].includes(collection.status)
    );

    if (incomplete.length > 0) {
      setPendingActionType("automatic");
      setIncompleteCollections(incomplete);
      setShowIncompleteWarning(true);
      return;
    }

    await proceedWithAutomaticCollectionPlan();
  };

  /**
   * Actually create the new collection after confirmation
   */
  const proceedWithNewCollection = async () => {
    setShowIncompleteWarning(false);
    setPendingActionType(null);
    setCreatingCollection(true);

    try {
      // Always call startCollection - it will either:
      // 1. Return the existing active collection if it's still valid
      // 2. Mark stale collections as paused and create a new one
      // 3. Create a new collection if none exists
      // alert("Creating collection plan. This may take a few moments...");
      const startRes = await collectionService.startCollection(
        workspaceId,
        repositoryId
      );
      const currentPlanId = startRes.data.collection_plan.id;

      // Configure metrics on the collection
      await collectionService.configureMetrics(currentPlanId, {
        selected_metrics: selectedMetrics,
        start_date: startDate || null,
        end_date: endDate || null,
        status: selectedStatus,
        branch_name: selectedBranch,
        save_batch_size: saveBatchSize,
      });

      // Get validation summary
      const validateRes = await collectionService.validatePlan(currentPlanId);
      setCollectionPlanMode("manual");
      setCollectionPlanAutomationContext(null);
      setCollectionPlan(validateRes.data);
      setShowPlanModal(true);
    } catch (err) {
      alert("Error creating collection plan: " + err.message);
    } finally {
      setCreatingCollection(false);
    }
  };

  const proceedWithAutomaticCollectionPlan = async () => {
    if (!automationDraft) {
      return;
    }

    setShowIncompleteWarning(false);
    setPendingActionType(null);
    setAutomationExecuting(true);
    setAutomationError(null);

    try {
      const startRes = await collectionService.startCollection(
        workspaceId,
        repositoryId
      );
      const currentPlanId = startRes.data.collection_plan.id;

      await collectionService.configureMetrics(currentPlanId, {
        selected_metrics: automationDraft.collection.selected_metrics,
        start_date: automationDraft.collection.start_date || null,
        end_date: automationDraft.collection.end_date || null,
        status: automationDraft.collection.status,
        branch_name: automationDraft.collection.branch_name,
      });

      const validateRes = await collectionService.validatePlan(currentPlanId);
      setCollectionPlanMode("automatic");
      setCollectionPlanAutomationContext(buildAutomaticWorkflowPayload());
      setCollectionPlan(validateRes.data);
      setShowPlanModal(true);
    } catch (err) {
      setAutomationError(
        getApiErrorMessage(err, "Failed to prepare the automatic workflow.")
      );
    } finally {
      setAutomationExecuting(false);
    }
  };

  const handleStartCollection = async () => {
    try {
      const planIdToUse = collectionPlan.collection_plan.id;
      await collectionService.executeCollection(planIdToUse);

      const progressState = {};
      if (collectionPlanMode === "automatic" && collectionPlanAutomationContext) {
        persistAutomaticWorkflow(planIdToUse, collectionPlanAutomationContext);
        progressState.automaticWorkflow = collectionPlanAutomationContext;
      }

      // Navigate to progress page
      navigate(
        `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planIdToUse}/progress`,
        { state: progressState }
      );
    } catch (err) {
      alert("Error starting collection: " + err.message);
    }
  };

  const handleDownloadJSON = async (collectionId) => {
    try {
      const response = await collectionService.downloadCollectionJSON(collectionId);
      const blob = new Blob([response.data], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `collection_${collectionId}_data.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert("Error downloading data: " + err.message);
    }
  };

  const handleDeleteCollection = (collection) => {
    setCollectionToDelete(collection);
    setShowDeleteModal(true);
  };

  const confirmDeleteCollection = async () => {
    if (!collectionToDelete) return;

    setDeletingCollection(true);
    try {
      await collectionService.deleteCollection(collectionToDelete.id);
      // Refresh history
      await fetchCollectionHistory();
      setShowDeleteModal(false);
      setCollectionToDelete(null);
    } catch (err) {
      alert("Error deleting collection: " + err.message);
    } finally {
      setDeletingCollection(false);
    }
  };

  const handleViewCollection = (collection) => {
    // For in-progress collections, navigate to progress page instead of details
    if (collection.status === 'in_progress') {
      navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collection.id}/progress`);
    } else {
      navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collection.id}`);
    }
  };

  // Resume interrupted collection
  const handleResumeCollection = async (collectionId) => {
    try {
      setResumingCollection(collectionId);
      await collectionService.resumeCollection(collectionId);
      // Navigate to progress page
      navigate(
        `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}/progress`,
        { state: { resume: true } }
      );
    } catch (err) {
      alert("Error resuming collection: " + err.message);
    } finally {
      setResumingCollection(null);
    }
  };

  // Resume from notification toast
  const handleResumeFromNotification = (collectionId) => {
    handleResumeCollection(collectionId);
    // Remove notification after resuming
    setInterruptedNotifications(prev => prev.filter(n => n.id !== collectionId));
    // Also remove from dismissed so it doesn't reappear
    const dismissed = getDismissedNotifications();
    if (!dismissed.includes(collectionId)) {
      dismissed.push(collectionId);
      localStorage.setItem(`dismissed_collection_warnings_${repositoryId}`, JSON.stringify(dismissed));
    }
  };

  const formatCollectionDate = (collection) => {
    const startDate = collection.filters?.start_date;
    const endDate = collection.filters?.end_date;

    if (startDate && endDate) {
      return `${new Date(startDate).toLocaleDateString()} → ${new Date(endDate).toLocaleDateString()}`;
    } else if (startDate) {
      return `From ${new Date(startDate).toLocaleDateString()}`;
    } else if (endDate) {
      return `Until ${new Date(endDate).toLocaleDateString()}`;
    }
    return "All data";
  };

  const formatCollectionProgress = (collection) => {
    if (collection.status === 'completed') {
      return "100%";
    } else if (collection.status === 'paused' || collection.status === 'failed' || collection.status === 'in_progress') {
      if (collection.total_items > 0) {
        return `${collection.collected_items} / ${collection.total_items}`;
      }
    }
    return "-";
  };

  // Check if collection is actively running
  const isCollectionRunning = (collection) => {
    return collection.status === 'in_progress';
  };

  // Animated progress indicator component for in-progress collections
  const InProgressIndicator = () => (
    <div className="relative w-full h-1 bg-blue-100 rounded-full overflow-hidden">
      <div
        className="absolute h-full w-1/3 bg-linear-to-r from-blue-400 via-blue-600 to-blue-400 rounded-full animate-slide-progress"
      />
    </div>
  );

  const metricLabels = buildMetricLabels();

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
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center shrink-0">
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
                {dateRange.first_date && dateRange.last_date && (
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-500" />
                    <span>
                      {platform === "github" ? "PRs" : "MRs"}:{" "}
                      {new Date(dateRange.first_date).toLocaleDateString()} → {new Date(dateRange.last_date).toLocaleDateString()}
                    </span>
                  </div>
                )}
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
                      Date & Time
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Data Range
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Progress
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
                    <th className="text-left py-3 px-4 font-medium text-gray-700 text-center">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {collectionHistory.map((collection) => (
                    <tr key={collection.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-600">
                        <div className="text-sm">
                          {collection.completed_at ? (
                            <>
                              <div>{new Date(collection.completed_at).toLocaleDateString()}</div>
                              <div className="text-xs text-gray-500">
                                {new Date(collection.completed_at).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </div>
                            </>
                          ) : isCollectionRunning(collection) ? (
                            <div className="space-y-1.5">
                              <span className="inline-flex items-center gap-1.5 text-blue-600 font-medium">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                In Progress
                              </span>
                              <InProgressIndicator />
                            </div>
                          ) : ['paused', 'failed'].includes(collection.status) ? (
                            <span className="inline-flex items-center gap-1 text-red-600">
                              <AlertCircle className="w-3 h-3" />
                              Interrupted
                            </span>
                          ) : (
                            <span className="text-blue-600">Pending</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-gray-600 text-sm">
                        {formatCollectionDate(collection)}
                      </td>
                      <td className="py-3 px-4 text-gray-900 font-medium">
                        {formatCollectionProgress(collection)}
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {collection.stats.pull_requests_count ||
                          collection.stats.merge_requests_count ||
                          collection.collected_items ||
                          0}
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {collection.stats.commits_count || '-'}
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {collection.stats.comments_count ||
                          collection.stats.notes_count ||
                          '-'}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center gap-2">
                          {/* Resume button for paused/failed collections (NOT for in_progress) */}
                          {collection.can_resume && !isCollectionRunning(collection) && (
                            <button
                              onClick={() => handleResumeCollection(collection.id)}
                              disabled={resumingCollection === collection.id}
                              className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors disabled:opacity-50"
                              title="Continue collection"
                            >
                              {resumingCollection === collection.id ? (
                                <div className="w-4 h-4 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin" />
                              ) : (
                                <Play className="w-4 h-4" />
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => handleDownloadJSON(collection.id)}
                            className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                            title="Download raw data (JSON)"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleViewCollection(collection)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title={isCollectionRunning(collection) ? "View progress" : "View details"}
                          >
                            {isCollectionRunning(collection) ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            disabled
                            className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            title="Analyze (Coming soon)"
                          >
                            <BarChart3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteCollection(collection)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Delete collection"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-sm text-gray-600 mt-4">
              <strong>Note:</strong> These are previous collection instances of{" "}
              {repository.name} project
            </p>
          </div>
        )}

        {/* Configure Data Collection */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold mb-6">
            {collectionHistory.length > 0 ? 'Configure a New Collection' : 'Configure Collection'}
          </h2>

          <div className="mb-8">
            <p className="text-sm font-medium text-gray-700 mb-3">Collection mode</p>
            <div className="inline-flex rounded-xl border border-gray-200 bg-gray-50 p-1">
              <button
                onClick={() => setCollectionMode("manual")}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  collectionMode === "manual"
                    ? "bg-white text-blue-700 shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Manual mode
              </button>
              <button
                onClick={() => setCollectionMode("automatic")}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  collectionMode === "automatic"
                    ? "bg-white text-sky-700 shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                Automatic mode
              </button>
            </div>
          </div>

          {collectionMode === "manual" ? (
            <>
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

                <div className="space-y-2 max-h-96 overflow-y-auto border border-gray-200 rounded-lg p-4">
                  {Object.entries(availableMetrics)
                    .map(([category, metrics]) => {
                      const filteredMetrics = searchMetric
                        ? metrics.filter(
                            (metric) =>
                              metric.label.toLowerCase().includes(searchMetric.toLowerCase()) ||
                              metric.value.toLowerCase().includes(searchMetric.toLowerCase())
                          )
                        : metrics;

                      if (filteredMetrics.length === 0) return null;

                      return (
                        <div key={category} className="border border-gray-200 rounded-lg">
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
                              {filteredMetrics.length} metric{filteredMetrics.length !== 1 ? "s" : ""}
                            </span>
                          </div>

                          {expandedCategories[category] && (
                            <div className="p-2">
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
                          )}
                        </div>
                      );
                    })
                    .filter(Boolean)}
                </div>

                <p className="text-sm text-gray-500 mt-2">
                  {selectedMetrics.length} metric{selectedMetrics.length !== 1 ? "s" : ""}{" "}
                  selected
                </p>
              </div>

              {/* Apply Filters */}
              <div>
                <h3 className="text-lg font-medium mb-4">Apply Filters</h3>

                {dateRange.first_date && dateRange.last_date && (
                  <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-800">
                      <strong>Available {platform === "github" ? "PR" : "MR"} date range:</strong>{" "}
                      {new Date(dateRange.first_date).toLocaleDateString()} → {new Date(dateRange.last_date).toLocaleDateString()}
                    </p>
                    <p className="text-xs text-blue-600 mt-1">
                      Use the date filters below to narrow down the collection period
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      min={dateRange.first_date ? new Date(dateRange.first_date).toISOString().split('T')[0] : undefined}
                      max={endDate || (dateRange.last_date ? new Date(dateRange.last_date).toISOString().split('T')[0] : undefined)}
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
                      min={startDate || (dateRange.first_date ? new Date(dateRange.first_date).toISOString().split('T')[0] : undefined)}
                      max={dateRange.last_date ? new Date(dateRange.last_date).toISOString().split('T')[0] : undefined}
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

                {/* Save Batch Size */}
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Save Batch Size
                  </label>
                  <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-800">
                      <strong>Number of {platform === "github" ? "PRs" : "MRs"} collected before each save to storage.</strong>
                    </p>
                    <p className="text-xs text-blue-600 mt-1">
                      Higher values speed up large collections but risk losing more progress on interruption.
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-600 bg-gray-100 px-2.5 py-1 rounded font-mono">{saveBatchSize}</span>
                    <span className="text-xs text-gray-400">{saveBatchSize === 1 ? "(default)" : "items per save"}</span>
                    {!editingBatchSize ? (
                      <button
                        type="button"
                        onClick={() => { setBatchSizeDraft(saveBatchSize); setEditingBatchSize(true); }}
                        className="px-3 py-1 text-xs font-medium text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                      >
                        Modify
                      </button>
                    ) : null}
                  </div>

                  {editingBatchSize && (
                    <div className="mt-2 max-w-sm p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {[1, 20, 40, 60, 80, 100].map((v) => (
                          <button
                            key={v}
                            type="button"
                            onClick={() => setBatchSizeDraft(v)}
                            className={`px-2.5 py-1 text-xs rounded border transition-colors ${
                              batchSizeDraft === v
                                ? "bg-blue-600 text-white border-blue-600"
                                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
                            }`}
                          >
                            {v}
                          </button>
                        ))}
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min="1"
                          max="100"
                          value={batchSizeDraft}
                          onChange={(e) => {
                            const v = Number(e.target.value);
                            if (v >= 1 && v <= 100) setBatchSizeDraft(v);
                          }}
                          className="w-16 px-2 py-1 border border-gray-300 rounded text-center text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button
                          type="button"
                          onClick={() => { setSaveBatchSize(batchSizeDraft); setEditingBatchSize(false); }}
                          className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                        >
                          Validate
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingBatchSize(false)}
                          className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={handleGoToPlan}
                disabled={selectedMetrics.length === 0 || !selectedBranch || creatingCollection}
                className="mt-8 w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {creatingCollection ? "Creating collection plan..." : "Go to collect plan →"}
              </button>
            </>
          ) : (
            <AutomaticCollectionReview
              draft={automationDraft}
              warnings={automationWarnings}
              metricLabels={metricLabels}
              generating={automationLoading}
              submitting={automationExecuting}
              error={automationError}
              onGenerate={handleGenerateAutomationDraft}
              onApprove={handleApproveAutomation}
              prompt={automationPrompt}
              onPromptChange={setAutomationPrompt}
              llmProvider={automationProvider}
              onProviderChange={setAutomationProvider}
              llmModel={automationModel}
              onModelChange={setAutomationModel}
            />
          )}
        </div>
      </div>

      {/* Collect Plan Modal */}
      {showPlanModal && collectionPlan && (
        <CollectPlanModal
          plan={collectionPlan}
          mode={collectionPlanMode}
          automationDraft={collectionPlanAutomationContext?.draft}
          warnings={collectionPlanAutomationContext?.warnings || []}
          onClose={() => setShowPlanModal(false)}
          onStartCollection={handleStartCollection}
        />
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && collectionToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900">
                Delete Collection?
              </h3>
            </div>

            <div className="mb-6">
              <p className="text-gray-600 mb-3">
                Are you sure you want to delete this collection?
              </p>
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-800">
                  <strong>Warning:</strong> This action cannot be undone. All collected data,
                  cleaning operations, and created files will be permanently deleted.
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setCollectionToDelete(null);
                }}
                disabled={deletingCollection}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteCollection}
                disabled={deletingCollection}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {deletingCollection ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Incomplete Collections Warning Modal */}
      {showIncompleteWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-yellow-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900">
                Incomplete Collections Found
              </h3>
            </div>

            <div className="mb-6">
              <p className="text-gray-600 mb-4">
                You have <strong>{incompleteCollections.length}</strong> incomplete collection{incompleteCollections.length > 1 ? 's' : ''} for this project.
                Do you want to continue one of them or create a new collection?
              </p>

              {/* List of incomplete collections */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 max-h-48 overflow-y-auto">
                {incompleteCollections.map((collection) => (
                  <div key={collection.id} className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900">
                          Collection #{collection.id}
                        </span>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">
                          <AlertCircle className="w-3 h-3" />
                          Interrupted
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Progress: {collection.collected_items} / {collection.total_items} {platform === 'github' ? 'PRs' : 'MRs'}
                        {collection.total_items > 0 && ` (${Math.round((collection.collected_items / collection.total_items) * 100)}%)`}
                      </p>
                    </div>
                    {collection.can_resume && (
                      <button
                        onClick={() => {
                          setShowIncompleteWarning(false);
                          handleResumeCollection(collection.id);
                        }}
                        className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Continue
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowIncompleteWarning(false);
                  setPendingActionType(null);
                }}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (pendingActionType === "automatic") {
                    proceedWithAutomaticCollectionPlan();
                    return;
                  }
                  proceedWithNewCollection();
                }}
                className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Create New Collection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Interrupted Collection Notification Toasts */}
      {interruptedNotifications.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3">
          {interruptedNotifications.map((notification) => (
            <div key={notification.id} className="animate-slide-up">
              <div className="bg-white rounded-xl shadow-2xl border border-red-200 p-4 max-w-sm">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-red-100">
                    <AlertCircle className="w-5 h-5 text-red-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="font-semibold text-gray-900 text-sm">
                        Collection Interrupted
                      </h4>
                      <button
                        onClick={() => dismissNotification(notification.id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Collection #{notification.id}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      Progress: {notification.collected_items} / {notification.total_items}{" "}
                      {platform === "github" ? "PRs" : "MRs"} ({notification.progress_percentage}%)
                    </p>
                    {notification.error_message && (
                      <p className="text-xs text-red-600 mt-1 truncate" title={notification.error_message}>
                        {notification.error_message}
                      </p>
                    )}
                    {notification.can_resume && (
                      <button
                        onClick={() => handleResumeFromNotification(notification.id)}
                        disabled={resumingCollection === notification.id}
                        className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 text-white text-sm rounded-lg transition-colors disabled:opacity-50 bg-red-600 hover:bg-red-700"
                      >
                        {resumingCollection === notification.id ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            Resuming...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4" />
                            Continue Collection
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ProjectDetail;
