/**
 * frontend/src/pages/projects/Projects.jsx
 * Updated: Navigate to collection page on card click
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Github,
  GitBranch,
  FolderGit2,
  BarChart3,
  Clock,
  Lock,
  Search,
  Settings,
  ArrowLeft,
  Plus,
} from "lucide-react";
import { workspaceService } from "../../services/api";
import WorkspaceModal from "../../components/workspaces/WorkspaceModal";
import ImportRepositoriesModal from "../../components/workspaces/ImportRepositoriesModal";
import RepositoryCard from "../../components/repositories/RepositoryCard";

function Projects() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState(null);
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showEditModal, setShowEditModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  useEffect(() => {
    fetchWorkspaceData();
  }, [id]);

  const fetchWorkspaceData = async () => {
    try {
      setLoading(true);
      const wsResponse = await workspaceService.getById(id);
      setWorkspace(wsResponse.data);
      const reposResponse = await workspaceService.getRepositories(id);
      setRepositories(reposResponse.data);
    } catch (error) {
      console.error("Error loading workspace data:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredRepositories = repositories.filter((repo) =>
    repo.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getTimeDiff = (date) => {
    if (!date) return "";
    const now = new Date();
    const past = new Date(date);
    const diffInDays = Math.floor((now - past) / (1000 * 60 * 60 * 24));
    if (diffInDays === 0) return "today";
    if (diffInDays === 1) return "yesterday";
    if (diffInDays < 7) return `${diffInDays} days ago`;
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
    return `${Math.floor(diffInDays / 30)} months ago`;
  };

  const handleEditClose = () => {
    setShowEditModal(false);
    fetchWorkspaceData();
  };

  const handleImportClose = () => {
    setShowImportModal(false);
    fetchWorkspaceData();
  };


  const handleRepositoryClick = (repoId) => {
    navigate(`/workspaces/${id}/repositories/${repoId}/collect`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Workspace not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header avec retour */}
        <button
          onClick={() => navigate("/workspaces")}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 sm:mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="text-sm sm:text-base">Back to workspaces</span>
        </button>

        {/* Section workspace info */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-6 mb-4 sm:mb-6">
          <div className="flex flex-col sm:flex-row items-start gap-4">
            <div className="w-12 h-12 sm:w-16 sm:h-16 bg-gray-100 rounded-full flex items-center justify-center shrink-0">
              {workspace.platform === "github" ? (
                <Github className="w-6 h-6 sm:w-8 sm:h-8" />
              ) : (
                <GitBranch className="w-6 h-6 sm:w-8 sm:h-8" />
              )}
            </div>

            <div className="flex-1 min-w-0 w-full">
              <h1 className="text-xl sm:text-2xl font-semibold text-gray-900 mb-2">
                {workspace.name}
              </h1>
              <p className="text-sm sm:text-base text-gray-600 mb-3 sm:mb-4">
                {workspace.description || "Aucune description"}
              </p>

              <div className="flex flex-wrap items-center gap-3 sm:gap-6 text-xs sm:text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <FolderGit2 className="w-4 h-4" />
                  <span>{repositories.length} Repositories</span>
                </div>
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  <span>{workspace.analyses_count ?? 0} analyses</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>Edited {getTimeDiff(workspace.updated_at)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4" />
                  <span className="capitalize">
                    {workspace.visibility || "Public"}
                  </span>
                </div>
              </div>

              {workspace.url && (
                <a
                  href={workspace.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-xs sm:text-sm mt-3 inline-block truncate max-w-full"
                >
                  {workspace.url}
                </a>
              )}
            </div>

            <button
              onClick={() => setShowEditModal(true)}
              className="p-2 hover:bg-gray-100 rounded-lg transition self-start"
            >
              <Settings className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>

        {/* Search et Import */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={() => setShowImportModal(true)}
            className="px-5 py-2.5 bg-blue-600 text-white rounded-lg flex items-center justify-center gap-2 hover:bg-blue-700"
          >
            <Plus className="w-5 h-5" />
            <span>Import Repositories</span>
          </button>
        </div>

        {/* Liste des repositories */}
        {filteredRepositories.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <FolderGit2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">
              {searchTerm
                ? "Aucun repository trouvé"
                : "Aucun repository dans ce workspace"}
            </p>
            {!searchTerm && (
              <button
                onClick={() => setShowImportModal(true)}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg inline-flex items-center gap-2 hover:bg-blue-700"
              >
                <Plus className="w-5 h-5" />
                Importer des repositories
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
            {filteredRepositories.map((repo) => (
              <RepositoryCard
                key={repo.id}
                repo={repo}
                platform={workspace.platform}
                onClick={() => handleRepositoryClick(repo.id)}
                onCollect={() => handleRepositoryClick(repo.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Modal d'édition du workspace */}
      {showEditModal && (
        <WorkspaceModal workspace={workspace} onClose={handleEditClose} />
      )}

      {showImportModal && (
        <ImportRepositoriesModal workspaceId={id} onClose={handleImportClose} />
      )}
    </div>
  );
}

export default Projects;
