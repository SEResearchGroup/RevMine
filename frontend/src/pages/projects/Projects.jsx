import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  Star,
  GitFork,
  Eye
} from 'lucide-react';
import { workspaceService } from "../../services/api";

function Projects() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState(null);
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

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
      console.error('Erreur lors du chargement:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredRepositories = repositories.filter(repo =>
    repo.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getTimeDiff = (date) => {
    const now = new Date();
    const past = new Date(date);
    const diffInDays = Math.floor((now - past) / (1000 * 60 * 60 * 24));
    
    if (diffInDays === 0) return 'today';
    if (diffInDays === 1) return 'yesterday';
    if (diffInDays < 7) return `${diffInDays} days ago`;
    if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
    return `${Math.floor(diffInDays / 30)} months ago`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Chargement...</div>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Workspace non trouvé</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header avec retour */}
        <button
          onClick={() => navigate('/workspaces')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          Retour aux workspaces
        </button>

        {/* Section workspace info (comme dans l'image) */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
              {workspace.platform === "github" ? (
                <Github className="w-8 h-8" />
              ) : (
                <GitBranch className="w-8 h-8" />
              )}
            </div>
            
            <div className="flex-1">
              <h1 className="text-2xl font-semibold text-gray-900 mb-2">
                {workspace.name}
              </h1>
              <p className="text-gray-600 mb-4">
                {workspace.description || "Aucune description"}
              </p>
              
              <div className="flex items-center gap-6 text-sm text-gray-600">
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
                  <span className="capitalize">{workspace.visibility || "Public"}</span>
                </div>
              </div>

              {workspace.url && (
                <a
                  href={workspace.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-sm mt-3 inline-block"
                >
                  {workspace.url}
                </a>
              )}
            </div>

            <button className="p-2 hover:bg-gray-100 rounded-lg transition">
              <Settings className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Liste des repositories */}
        {filteredRepositories.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            Aucun repository trouvé
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {filteredRepositories.map((repo) => (
              <div
                key={repo.id}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <FolderGit2 className="w-6 h-6 text-gray-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-base text-gray-900 truncate">
                      {repo.name}
                    </h3>
                  </div>
                </div>

                <p className="text-gray-600 text-sm mb-4 line-clamp-2 min-h-[2.5rem]">
                  {repo.description || "Aucune description"}
                </p>

                <div className="space-y-2.5 text-sm text-gray-600">
                  {repo.language && (
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                      <span>{repo.language}</span>
                    </div>
                  )}
                  
                  <div className="flex items-center gap-4">
                    {repo.stars_count !== undefined && (
                      <div className="flex items-center gap-1">
                        <Star className="w-4 h-4" />
                        <span>{repo.stars_count}</span>
                      </div>
                    )}
                    {repo.forks_count !== undefined && (
                      <div className="flex items-center gap-1">
                        <GitFork className="w-4 h-4" />
                        <span>{repo.forks_count}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">
                      Updated {getTimeDiff(repo.updated_at)}
                    </span>
                  </div>
                </div>

                <div className="flex justify-end items-center mt-5 pt-4 border-t border-gray-200">
                  <button className="p-2 hover:bg-gray-100 rounded-lg transition">
                    <Eye className="w-4 h-4 text-blue-600" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Projects;