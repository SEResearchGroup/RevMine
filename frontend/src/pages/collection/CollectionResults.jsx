import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Github,
  GitBranch,
  FolderGit2,
  CheckCircle,
  AlertTriangle,
  Download,
  ArrowLeft,
  FileSpreadsheet,
  Filter
} from "lucide-react";
import { collectionService, workspaceService } from "../../services/api";

function CollectionResults() {
  const { workspaceId, repositoryId, planId } = useParams();
  const navigate = useNavigate();

  const [repository, setRepository] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [collectionData, setCollectionData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [planId]);

  const fetchData = async () => {
    try {
      const [wsRes, reposRes, statusRes, dataRes] = await Promise.all([
        workspaceService.getById(workspaceId),
        workspaceService.getRepositories(workspaceId),
        collectionService.getStatus(planId),
        collectionService.getData(planId),
      ]);

      setWorkspace(wsRes.data);
      const repo = reposRes.data.find((r) => r.id === parseInt(repositoryId));
      setRepository(repo);
      setCollectionData({
        status: statusRes.data,
        data: dataRes.data,
      });
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  };

  const [exporting, setExporting] = useState(null);

  const saveBlob = async (blob, suggestedName, mimeType, accept) => {
    if (window.showSaveFilePicker) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName,
          types: [{ description: suggestedName, accept: { [mimeType]: accept } }],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return;
      } catch (err) {
        if (err.name === "AbortError") return;
      }
    }
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = suggestedName;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const extractErrorMessage = async (err, fallback) => {
    const data = err?.response?.data;
    if (data instanceof Blob) {
      try {
        const text = await data.text();
        const parsed = JSON.parse(text);
        return parsed.error || parsed.detail || text || fallback;
      } catch {
        return fallback;
      }
    }
    return data?.error || data?.detail || err?.message || fallback;
  };

  const handleExportJSON = async () => {
    try {
      setExporting("JSON");
      const response = await collectionService.downloadCollectionJSON(planId);
      const suggested =
        response.headers?.["content-disposition"]?.match(/filename="?([^";]+)"?/)?.[1] ||
        `${repository.full_name.replace("/", "_")}_collection${planId}.json`;
      await saveBlob(response.data, suggested, "application/json", [".json"]);
    } catch (err) {
      const msg = await extractErrorMessage(err, "Failed to download JSON");
      alert(`Error downloading JSON: ${msg}`);
    } finally {
      setExporting(null);
    }
  };

  const handleExportCSV = async (fileType) => {
    try {
      setExporting(fileType);
      const listRes = await collectionService.getCollectionCleanedData(planId);
      const items = listRes.data?.cleaned_data || [];
      const completed = items
        .filter((c) => c.status === "completed")
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

      if (completed.length === 0) {
        alert(
          "No cleaned CSV available yet. Please create a structured CSV first using the \"Create Structured CSV\" button above."
        );
        return;
      }

      const cleaned = completed[0];
      const filename =
        fileType === "structured"
          ? cleaned.structured_csv_filename
          : cleaned.statistics_csv_filename;

      if (!filename) {
        alert(
          `The latest cleaned dataset does not include a ${fileType} CSV. Re-run cleaning to generate it.`
        );
        return;
      }

      const response = await collectionService.downloadCleanedDataCSV(
        cleaned.id,
        fileType
      );
      await saveBlob(response.data, filename, "text/csv", [".csv"]);
    } catch (err) {
      const msg = await extractErrorMessage(err, "Failed to download CSV");
      alert(`Error downloading CSV: ${msg}`);
    } finally {
      setExporting(null);
    }
  };

  const handleCreateStructuredCSV = () => {
    navigate(
      `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${planId}/cleaned-data/new`
    );
  };

  if (loading || !repository || !collectionData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  const { status, data } = collectionData;
  const stats = status.stats || {};
  const platform = repository.platform;

  // Platform-specific terminology
  const itemTerm = platform === "github" ? "Pull Request" : "Merge Request";
  const itemTermPlural = platform === "github" ? "Pull Requests" : "Merge Requests";
  const itemAbbr = platform === "github" ? "PR" : "MR";

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <button
          onClick={() => navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collect`)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Project</span>
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

        {/* Warning if collection was paused */}
        {status.collection_plan.status === "paused" && (
          <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <AlertTriangle className="w-6 h-6 text-yellow-600 shrink-0" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-yellow-900 mb-2">
                  Collection was interrupted
                </h3>
                <p className="text-yellow-800 mb-4">
                  The collection was paused at {itemAbbr} #{status.collection_plan.last_collected_item_id}.
                  You collected {status.collected_items} out of {status.total_items} items.
                </p>
                <button
                  onClick={() => collectionService.resumeCollection(planId)}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
                >
                  Click here to continue collection
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Success Message */}
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-center mb-4 flex items-left justify-left gap-2">
            <CheckCircle className="w-8 h-8 text-green-600" />
            Collection completed successfully
          </h2>

          <div className="bg-green-50 border border-green-200 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center shrink-0">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-green-900 mb-2">
                  Data Collection Complete!
                </h3>
                <p className="text-green-800 mb-4">
                  Successfully collected data from{" "}
                  <strong>
                    {stats[platform === "github" ? "pull_requests_count" : "merge_requests_count"] || 0}{" "}
                    {itemTermPlural.toLowerCase()}
                  </strong>{" "}
                  spanning {stats.start_date || "N/A"} - {stats.end_date || "N/A"}
                </p>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>{stats.commits_count || 0} commits</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>
                      {stats[platform === "github" ? "comments_count" : "notes_count"] || 0}{" "}
                      {platform === "github" ? "comments" : "notes"}
                    </span>
                  </div>
                  {platform === "github" && (
                    <div className="flex items-center gap-2 text-green-800">
                      <CheckCircle className="w-4 h-4" />
                      <span>{stats.reviews_count || 0} reviews</span>
                    </div>
                  )}
                  {platform !== "github" && (
                    <div className="flex items-center gap-2 text-green-800">
                      <CheckCircle className="w-4 h-4" />
                      <span>{stats.discussions_count || 0} discussions</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>Raw data stored</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Create Structured CSV */}
        <div className="mb-6">
          <h3 className="text-xl font-semibold mb-4">Data Cleaning & Structuring</h3>
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center shrink-0">
                <Filter className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900 mb-2">
                  Clean and Structure Your Data
                </h4>
                <p className="text-gray-600 mb-4">
                  Apply filters to clean the raw data and create a structured CSV file
                  for analysis. You can filter by file extensions, authors, and keywords.
                </p>
                <button
                  onClick={handleCreateStructuredCSV}
                  className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                >
                  <FileSpreadsheet className="w-5 h-5" />
                  Create Structured CSV
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Export Raw Data */}
        <div className="mb-6">
          <h3 className="text-xl font-semibold mb-4">Export Raw Data</h3>
          <p className="text-gray-600 mb-4">
            Download all collected data in various formats:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={handleExportJSON}
              disabled={exporting !== null}
              className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow text-left disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mb-4">
                <Download className="w-6 h-6 text-yellow-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">JSON</h4>
              <p className="text-sm text-gray-600 mb-3">Complete raw format</p>
              <div className="mt-4 flex items-center gap-2 text-blue-600 font-medium">
                <Download className="w-4 h-4" />
                <span>{exporting === "JSON" ? "Downloading..." : "Download"}</span>
              </div>
            </button>

            <button
              onClick={() => handleExportCSV("structured")}
              disabled={exporting !== null}
              className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow text-left disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                <Download className="w-6 h-6 text-green-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">CSV</h4>
              <p className="text-sm text-gray-600 mb-3">Table format (latest cleaning)</p>
              <div className="mt-4 flex items-center gap-2 text-blue-600 font-medium">
                <Download className="w-4 h-4" />
                <span>{exporting === "structured" ? "Downloading..." : "Download"}</span>
              </div>
            </button>

            <button
              onClick={() => handleExportCSV("statistics")}
              disabled={exporting !== null}
              className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow text-left disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <Download className="w-6 h-6 text-purple-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Statistics CSV</h4>
              <p className="text-sm text-gray-600 mb-3">Project metrics (latest cleaning)</p>
              <div className="mt-4 flex items-center gap-2 text-blue-600 font-medium">
                <Download className="w-4 h-4" />
                <span>{exporting === "statistics" ? "Downloading..." : "Download"}</span>
              </div>
            </button>
          </div>
        </div>

        {/* Data Overview */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-xl font-semibold mb-4">Data Overview</h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(stats).map(([key, value]) => {
              if (key.includes("_count")) {
                let metricName = key.replace("_count", "").replace("_", " ");

                // Platform-specific naming
                if (key === "pull_requests_count") metricName = itemTermPlural;
                if (key === "merge_requests_count") metricName = itemTermPlural;

                return (
                  <div
                    key={key}
                    className="bg-gray-50 rounded-lg p-4 text-center"
                  >
                    <div className="text-3xl font-bold text-gray-900">
                      {value}
                    </div>
                    <div className="text-sm text-gray-600 capitalize mt-1">
                      {metricName}
                    </div>
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default CollectionResults;
