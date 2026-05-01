import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  Github,
  GitMerge,
  Link as LinkIcon,
  Key,
} from "lucide-react";
import { cicdService } from "../../services/api";

const MODE_WORKSPACE = "workspace";
const MODE_TOKEN = "token";

export default function CICDPipelineSelectionPage() {
  const navigate = useNavigate();

  const [mode, setMode] = useState(MODE_WORKSPACE);
  const [provider, setProvider] = useState("github");
  const [token, setToken] = useState("");
  const [repoFullName, setRepoFullName] = useState("");
  const [projectId, setProjectId] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://gitlab.com");
  const [maxRuns, setMaxRuns] = useState(200);

  const [repos, setRepos] = useState([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [selectedRepoId, setSelectedRepoId] = useState(null);

  const [pipelines, setPipelines] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (mode !== MODE_WORKSPACE) return;
    setReposLoading(true);
    cicdService
      .listWorkspaceRepos()
      .then((data) => {
        const list = Array.isArray(data)
          ? data
          : data?.repositories || data?.results || [];
        setRepos(list);
      })
      .catch((err) =>
        setError(err?.response?.data?.error || err.message || "Failed to load repositories")
      )
      .finally(() => setReposLoading(false));
  }, [mode]);

  const selectedRepo = useMemo(
    () => repos.find((r) => r.id === selectedRepoId) || null,
    [repos, selectedRepoId]
  );

  useEffect(() => {
    if (selectedRepo?.platform || selectedRepo?.workspace_platform) {
      setProvider(selectedRepo.platform || selectedRepo.workspace_platform);
    }
  }, [selectedRepo]);

  const buildPayload = () => {
    const payload = { provider, max_runs: maxRuns };
    if (mode === MODE_TOKEN) {
      payload.token = token;
      if (provider === "github") {
        payload.repo_full_name = repoFullName;
        payload.name = repoFullName;
      }
      if (provider === "gitlab") {
        payload.project_id = projectId;
        payload.base_url = baseUrl;
        payload.name = `gitlab-${projectId}`;
      }
    } else if (selectedRepo) {
      payload.workspace_id = selectedRepo.workspace || selectedRepo.workspace_id;
      payload.repository_id = selectedRepo.id;
      if (provider === "github") {
        payload.repo_full_name = selectedRepo.full_name;
        payload.name = selectedRepo.full_name;
      }
      if (provider === "gitlab") {
        payload.project_id = selectedRepo.external_id || selectedRepo.id;
        payload.base_url = selectedRepo.web_url_base || "https://gitlab.com";
        payload.name = selectedRepo.full_name;
      }
    }
    return payload;
  };

  const handleList = async () => {
    setLoading(true);
    setError(null);
    setPipelines(null);
    try {
      const data = await cicdService.listPipelines(buildPayload());
      setPipelines(data.pipelines || []);
    } catch (err) {
      setError(err?.response?.data?.error || err.message || "Failed to list pipelines");
    } finally {
      setLoading(false);
    }
  };

  const handleCollect = async () => {
    setLoading(true);
    setError(null);
    try {
      const job = await cicdService.startCollection(buildPayload());
      if (job?.id) {
        navigate(`/cicd/jobs/${job.id}/progress`, { state: { job } });
      } else {
        setError("Collection did not return a job id.");
      }
    } catch (err) {
      setError(err?.response?.data?.error || err.message || "Collection failed");
    } finally {
      setLoading(false);
    }
  };

  const canRun =
    (mode === MODE_TOKEN &&
      token &&
      (provider === "github" ? !!repoFullName : !!projectId)) ||
    (mode === MODE_WORKSPACE && selectedRepo);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate("/cicd/new")}
          className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <h1 className="text-2xl font-bold text-gray-800 mb-2">
          Connect to a CI/CD provider
        </h1>
        <p className="text-sm text-gray-500 mb-8">
          Pick a connected repository to reuse its stored OAuth token, or paste
          a personal token. We'll pull recent workflow / pipeline runs and jobs
          into a dataset.
        </p>

        <div className="flex gap-2 mb-5 bg-white border border-gray-200 rounded-xl p-1">
          <button
            onClick={() => setMode(MODE_WORKSPACE)}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm ${
              mode === MODE_WORKSPACE
                ? "bg-green-50 text-green-700 font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <LinkIcon className="w-4 h-4" /> From workspace
          </button>
          <button
            onClick={() => setMode(MODE_TOKEN)}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm ${
              mode === MODE_TOKEN
                ? "bg-green-50 text-green-700 font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Key className="w-4 h-4" /> Manual token
          </button>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          {mode === MODE_WORKSPACE ? (
            <>
              {reposLoading ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                </div>
              ) : repos.length === 0 ? (
                <p className="text-sm text-gray-500">
                  No imported repositories found. Go to{" "}
                  <button
                    onClick={() => navigate("/workspaces")}
                    className="text-green-600 hover:underline"
                  >
                    Workspaces
                  </button>{" "}
                  to connect a GitHub or GitLab workspace first.
                </p>
              ) : (
                <>
                  <label className="block text-sm font-medium text-gray-700">
                    Repository
                  </label>
                  <select
                    value={selectedRepoId || ""}
                    onChange={(e) => setSelectedRepoId(Number(e.target.value) || null)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">— choose a repository —</option>
                    {repos.map((r) => (
                      <option key={r.id} value={r.id}>
                        {(r.platform || r.workspace_platform || "?")} · {r.full_name || r.name}
                      </option>
                    ))}
                  </select>
                  {selectedRepo && (
                    <p className="text-xs text-gray-500">
                      Platform: <span className="font-medium text-gray-700">{provider}</span>
                      {" · "}Workspace token will be used automatically.
                    </p>
                  )}
                </>
              )}
            </>
          ) : (
            <>
              <div className="flex gap-3">
                <button
                  onClick={() => setProvider("github")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border ${
                    provider === "github"
                      ? "border-green-500 bg-green-50 text-green-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  <Github className="w-4 h-4" /> GitHub Actions
                </button>
                <button
                  onClick={() => setProvider("gitlab")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border ${
                    provider === "gitlab"
                      ? "border-green-500 bg-green-50 text-green-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  <GitMerge className="w-4 h-4" /> GitLab CI
                </button>
              </div>

              <label className="block text-sm font-medium text-gray-700">
                Access token
              </label>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder={provider === "github" ? "ghp_…" : "glpat-…"}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              />

              {provider === "github" ? (
                <>
                  <label className="block text-sm font-medium text-gray-700">
                    Repository (owner/name)
                  </label>
                  <input
                    value={repoFullName}
                    onChange={(e) => setRepoFullName(e.target.value)}
                    placeholder="octocat/hello-world"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                  />
                </>
              ) : (
                <>
                  <label className="block text-sm font-medium text-gray-700">
                    GitLab project ID
                  </label>
                  <input
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                    placeholder="1234567"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                  />
                  <label className="block text-sm font-medium text-gray-700">
                    GitLab base URL
                  </label>
                  <input
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                  />
                </>
              )}
            </>
          )}

          <label className="block text-sm font-medium text-gray-700">Max runs to fetch</label>
          <input
            type="number"
            value={maxRuns}
            onChange={(e) => setMaxRuns(Number(e.target.value) || 0)}
            min={10}
            max={2000}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-hidden focus:ring-2 focus:ring-blue-500"
          />

          <div className="flex gap-3">
            <button
              onClick={handleList}
              disabled={loading || !canRun}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-white border border-green-500 text-green-700 font-medium disabled:opacity-50"
            >
              Preview pipelines
            </button>
            <button
              onClick={handleCollect}
              disabled={loading || !canRun}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-green-600 text-white font-medium disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowRight className="w-4 h-4" />
              )}
              Collect & analyze
            </button>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
              {error}
            </p>
          )}
        </div>

        {pipelines && (
          <div className="mt-8 bg-white border border-gray-200 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              {pipelines.length} pipeline(s) / workflow(s) detected
            </h2>
            {pipelines.length === 0 ? (
              <p className="text-sm text-gray-500">No pipelines available.</p>
            ) : (
              <ul className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
                {pipelines.slice(0, 50).map((p) => (
                  <li
                    key={p.id}
                    className="py-2.5 flex items-center justify-between text-sm"
                  >
                    <span className="text-gray-700">
                      {p.name || p.ref || `#${p.id}`}
                    </span>
                    <span className="text-gray-400 text-xs">
                      {p.state || p.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
