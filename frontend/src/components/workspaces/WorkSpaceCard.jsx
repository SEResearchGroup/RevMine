import React from "react";
import {
  Settings,
  Trash2,
  Eye,
  FolderGit2,
  Github,
  GitBranch,
  Clock,
  Lock,
  BarChart3,
} from "lucide-react";

const WorkspaceCard = ({ workspace, onView, onEdit, onDelete }) => {
  const getTimeDiff = (dateString) => {
    if (!dateString) return "never";
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    return diff === 0
      ? "today"
      : `${diff} day${diff > 1 ? "s" : ""} ago`;
  };

  const handleSettingsClick = (e) => {
    e.stopPropagation();
    onEdit();
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete();
  };

  const handleViewClick = (e) => {
    e.stopPropagation();
    onView();
  };

  return (
    <div
      onClick={onView}
      className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 hover:shadow-lg transition-shadow cursor-pointer"
    >
      <div className="flex items-start gap-3 mb-4">
        <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
          {workspace.platform === "github" ? (
            <Github className="w-5 h-5 sm:w-6 sm:h-6" />
          ) : (
            <GitBranch className="w-5 h-5 sm:w-6 sm:h-6" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm sm:text-base text-gray-900 truncate">
            {workspace.name}
          </h3>
        </div>
      </div>

      <p className="text-gray-600 text-xs sm:text-sm mb-4 line-clamp-2 min-h-[2.5rem]">
        {workspace.description || "Aucune description"}
      </p>

      <div className="space-y-2 text-xs sm:text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <FolderGit2 className="w-4 h-4 flex-shrink-0" />
          <span>
            {workspace.projects_count ?? 0} Project
            {workspace.projects_count > 1 ? "s" : ""}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 flex-shrink-0" />
          <span>
            {workspace.analyses_count ?? 0} analysis
            {workspace.analyses_count > 1 ? "es" : ""}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">
            Edited {getTimeDiff(workspace.updated_at)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Lock className="w-4 h-4 flex-shrink-0" />
          <span className="capitalize">{workspace.visibility || "Public"}</span>
        </div>
      </div>

      <div className="flex justify-between items-center mt-4 sm:mt-5 pt-4 border-t border-gray-200">
        <div className="flex gap-1">
          <button
            onClick={handleSettingsClick}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            <Settings className="w-4 h-4 text-gray-600" />
          </button>
          <button
            onClick={handleDeleteClick}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            <Trash2 className="w-4 h-4 text-red-600" />
          </button>
        </div>
        <button
          onClick={handleViewClick}
          className="p-2 hover:bg-gray-100 rounded-lg transition"
        >
          <Eye className="w-4 h-4 text-blue-600" />
        </button>
      </div>
    </div>
  );
};

export default WorkspaceCard;