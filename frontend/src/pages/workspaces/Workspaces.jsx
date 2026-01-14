import React, { useState, useEffect } from "react";
import { Search, Settings, Plus } from "lucide-react";
import { workspaceService } from "../../services/api";
import { useNavigate } from "react-router-dom";
import WorkspaceCard from "../../components/workspaces/WorkSpaceCard";
import WorkspaceModal from "../../components/workspaces/WorkspaceModal";
import StatsCards from "../../components/workspaces/StatsCards";

const Workspaces = () => {
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editingWorkspace, setEditingWorkspace] = useState(null);

  const [stats] = useState({
    analysisThisMonth: 10,
    prsCollected: 45,
    quotaUsed: 85,
    activeWorkspaces: 4,
  });

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    try {
      setLoading(true);
      const response = await workspaceService.getAll();
      setWorkspaces(response.data);
    } catch (error) {
      console.error("Error loading workspaces", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredWorkspaces = workspaces.filter((ws) =>
    ws.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCreateWorkspace = () => {
    setEditingWorkspace(null);
    setShowModal(true);
  };

  const handleEditWorkspace = (workspace) => {
    setEditingWorkspace(workspace);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingWorkspace(null);
    loadWorkspaces();
  };

  const handleDeleteWorkspace = async (workspaceId) => {
    if (window.confirm("Are you sure you want to delete this workspace?")) {
      try {
        await workspaceService.delete(workspaceId);
        loadWorkspaces();
      } catch (error) {
        console.error("Error deleting workspace", error);
      }
    }
  };

  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-7xl mx-auto mb-4 sm:mb-6">
        <h1 className="text-xl sm:text-2xl font-semibold text-gray-800 mb-4 sm:mb-6">
          <span className="text-blue-600">Data Sources</span> / Workspaces
        </h1>

        <StatsCards stats={stats} />

        <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 mb-6">
          <div className="relative flex-1 max-w-full sm:max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search for Repository, Project"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex flex-row gap-3 ">
            <button className="flex-1 sm:flex-none px-4 py-2.5 border border-gray-300 rounded-lg flex items-center justify-center gap-2 hover:bg-gray-50">
              <Settings className="w-4 h-4" />
              <span className="hidden sm:inline">Filter</span>
            </button>

            <button
              onClick={handleCreateWorkspace}
              className="flex-1 sm:flex-none px-5 py-2.5 bg-blue-600 text-white rounded-lg flex items-center justify-center gap-2 hover:bg-blue-700"
            >
              <Plus className="w-5 h-5" />
              <span className="hidden sm:inline">New Workspace</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto">
        {loading ? (
          <div className="text-center py-12 text-gray-500">
            Loading workspaces...
          </div>
        ) : filteredWorkspaces.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No workspaces found.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
            {filteredWorkspaces.map((ws) => (
              <WorkspaceCard
                key={ws.id}
                workspace={ws}
                onView={() => navigate(`/workspaces/${ws.id}`)}
                onEdit={() => handleEditWorkspace(ws)}
                onDelete={() => handleDeleteWorkspace(ws.id)}
              />
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <WorkspaceModal
          workspace={editingWorkspace}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};

export default Workspaces;
