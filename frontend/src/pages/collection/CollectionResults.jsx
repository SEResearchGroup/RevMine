import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Github,
  GitBranch,
  FolderGit2,
  CheckCircle,
  FileJson,
  FileSpreadsheet,
  Database,
  Download,
  ArrowLeft,
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

  const handleExport = (format) => {
    // TODO: Implement actual export functionality
    alert(`Export to ${format} - Coming soon!`);
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

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate(`/workspaces/${workspaceId}`)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to workspace</span>
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

        {/* Success Message */}
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-center mb-4 flex items-left justify-left gap-2">
            <CheckCircle className="w-8 h-8 text-green-600" />
             Collection completed successfully
          </h2>

          {/* Success Card */}
          <div className="bg-green-50 border border-green-200 rounded-xl p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-green-900 mb-2">
                  Data Collection Complete!
                </h3>
                <p className="text-green-800 mb-4">
                  Successfully collected data from{" "}
                  <strong>{stats.pull_requests_count || 0} pull requests</strong>{" "}
                  spanning {stats.start_date || "N/A"} - {stats.end_date || "N/A"}
                </p>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>{stats.commits_count || 0} commits</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>{stats.comments_count || 0} comments</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>{stats.reviews_count || 0} reviewers</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>Raw data stored</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>Structured dataset created</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-4 h-4" />
                    <span>{stats.issues_count || 0} issues</span>
                  </div>
                </div>
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
            {/* JSON */}
            <button
              onClick={() => handleExport("JSON")}
              className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow text-left"
            >
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mb-4">
                <FileJson className="w-6 h-6 text-yellow-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">JSON</h4>
              <p className="text-sm text-gray-600 mb-3">Complete raw format</p>
              <p className="text-xs text-gray-500">~ 2.3 MB</p>
              <div className="mt-4 flex items-center gap-2 text-blue-600 font-medium">
                <Download className="w-4 h-4" />
                <span>Download</span>
              </div>
            </button>

            {/* CSV */}
            <button
              onClick={() => handleExport("CSV")}
              className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow text-left"
            >
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                <FileSpreadsheet className="w-6 h-6 text-green-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">CSV</h4>
              <p className="text-sm text-gray-600 mb-3">Table format</p>
              <p className="text-xs text-gray-500">~ 1.9 MB</p>
              <div className="mt-4 flex items-center gap-2 text-blue-600 font-medium">
                <Download className="w-4 h-4" />
                <span>Download</span>
              </div>
            </button>

            {/* SQL */}
            <button
              onClick={() => handleExport("SQL")}
              className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow text-left"
            >
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <Database className="w-6 h-6 text-purple-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">SQL</h4>
              <p className="text-sm text-gray-600 mb-3">Insert script</p>
              <p className="text-xs text-gray-500">~ 2.1 MB</p>
              <div className="mt-4 flex items-center gap-2 text-blue-600 font-medium">
                <Download className="w-4 h-4" />
                <span>Download</span>
              </div>
            </button>
          </div>
        </div>

        {/* Data Overview (Optional) */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-xl font-semibold mb-4">Data Overview</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(stats).map(([key, value]) => {
              if (key.includes("_count")) {
                const metricName = key.replace("_count", "").replace("_", " ");
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