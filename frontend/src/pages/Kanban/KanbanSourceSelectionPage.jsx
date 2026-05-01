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
import { kanbanService } from "../../services/api";

// When the user picks a repo from a connected workspace, the backend can
// resolve the stored OAuth token via Kafka. The frontend only sends
// workspace_id + the provider-specific identifiers — no secrets.
//
// The "Manual token" path remains for providers we haven't fully wired up
// into the OAuth flow (e.g. self-hosted GitLab with a personal token).
const MODE_WORKSPACE = "workspace";
const MODE_TOKEN = "token";

export default function KanbanSourceSelectionPage() {
  const navigate = useNavigate();

  const [mode, setMode] = useState(MODE_WORKSPACE);
  const [provider, setProvider] = useState("github");
  const [token, setToken] = useState("");
  const [owner, setOwner] = useState("");
  const [projectId, setProjectId] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://gitlab.com");

  const [repos, setRepos] = useState([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [selectedRepoId, setSelectedRepoId] = useState(null);

  const [boards, setBoards] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (mode !== MODE_WORKSPACE) return;
    setReposLoading(true);
    kanbanService
      .listWorkspaceRepos()
      .then((data) => {
        // API may return { repositories: [...] }, { results: [...] }, or an array.
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

  const buildPayload = ({ includeBoardId = null } = {}) => {
    const payload = { provider };
    if (mode === MODE_TOKEN) {
      payload.token = token;
      if (provider === "github") payload.owner = owner;
      if (provider === "gitlab") {
        payload.project_id = projectId;
        payload.base_url = baseUrl;
      }
    } else if (selectedRepo) {
      payload.workspace_id = selectedRepo.workspace || selectedRepo.workspace_id;
      payload.repository_id = selectedRepo.id;
      if (provider === "github") {
        payload.owner = (selectedRepo.full_name || "").split("/")[0];
      }
      if (provider === "gitlab") {
        payload.project_id = selectedRepo.external_id || selectedRepo.id;
        payload.base_url = selectedRepo.web_url_base || "https://gitlab.com";
      }
    }
    if (includeBoardId) payload.board_id = includeBoardId;
    return payload;
  };

  // Keep provider in sync with selected repo's platform so the user can't
  // mix GitHub repo with GitLab endpoints.
  useEffect(() => {
    if (selectedRepo?.platform || selectedRepo?.workspace_platform) {
      setProvider(selectedRepo.platform || selectedRepo.workspace_platform);
    }
  }, [selectedRepo]);

  const handleListBoards = async () => {
    setLoading(true);
    setError(null);
    setBoards(null);
    try {
      const data = await kanbanService.listBoards(buildPayload());
      setBoards(data.boards || []);
    } catch (err) {
      setError(err?.response?.data?.error || err.message || "Failed to list boards");
    } finally {
      setLoading(false);
    }
  };

  const handleCollect = async (board) => {
    setLoading(true);
    setError(null);
    try {
      const payload = buildPayload({ includeBoardId: board.id });
      payload.name = board.title;
      const job = await kanbanService.startCollection(payload);
      if (job?.id) {
        // Async flow: jump straight to the progress page. The user can leave
        // and they'll get a WebSocket notification when the job finishes.
        navigate(`/kanban/jobs/${job.id}/progress`, { state: { job } });
      } else {
        setError("Collection did not return a job id.");
      }
    } catch (err) {
      setError(err?.response?.data?.error || err.message || "Collection failed");
    } finally {
      setLoading(false);
    }
  };

  const canListBoards =
    (mode === MODE_TOKEN &&
      token &&
      (provider === "github" ? !!owner : !!projectId)) ||
    (mode === MODE_WORKSPACE && selectedRepo);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate("/kanban/new")}
          className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <h1 className="text-2xl font-bold text-gray-800 mb-2">
          Connect to a Kanban board
        </h1>
        <p className="text-sm text-gray-500 mb-8">
          Pick a repository from one of your connected workspaces — Revmine will
          use the stored OAuth token. Or paste a personal token manually.
        </p>

        {/* Mode tabs */}
        <div className="flex gap-2 mb-5 bg-white border border-gray-200 rounded-xl p-1">
          <button
            onClick={() => setMode(MODE_WORKSPACE)}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm ${
              mode === MODE_WORKSPACE
                ? "bg-blue-50 text-blue-700 font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <LinkIcon className="w-4 h-4" /> From workspace
          </button>
          <button
            onClick={() => setMode(MODE_TOKEN)}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm ${
              mode === MODE_TOKEN
                ? "bg-blue-50 text-blue-700 font-medium"
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
                    className="text-blue-600 hover:underline"
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
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  <Github className="w-4 h-4" /> GitHub Projects
                </button>
                <button
                  onClick={() => setProvider("gitlab")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border ${
                    provider === "gitlab"
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  <GitMerge className="w-4 h-4" /> GitLab Boards
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
                    Owner (user or org)
                  </label>
                  <input
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                    placeholder="octocat"
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

          <button
            onClick={handleListBoards}
            disabled={loading || !canListBoards}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 text-white font-medium disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
            List boards
          </button>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
              {error}
            </p>
          )}
        </div>

        {boards && (
          <div className="mt-8 bg-white border border-gray-200 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              {boards.length} board(s) found
            </h2>
            {boards.length === 0 ? (
              <p className="text-sm text-gray-500">No boards available for this account.</p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {boards.map((board) => (
                  <li
                    key={board.id}
                    className="py-3 flex items-center justify-between"
                  >
                    <span className="text-gray-700 font-medium">
                      {board.title || board.name || `Board #${board.id}`}
                    </span>
                    <button
                      onClick={() => handleCollect(board)}
                      disabled={loading}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 text-sm hover:bg-blue-100 disabled:opacity-50"
                    >
                      Collect <ArrowRight className="w-3.5 h-3.5" />
                    </button>
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
