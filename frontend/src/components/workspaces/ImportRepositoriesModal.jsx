import React, { useState, useEffect } from "react";
import { workspaceService } from "../../services/api";

const ImportRepositoriesModal = ({ workspaceId, onClose }) => {
  const [remoteRepos, setRemoteRepos] = useState([]);
  const [selectedRepos, setSelectedRepos] = useState([]);
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importComplete, setImportComplete] = useState(false);

  useEffect(() => {
    loadRemoteRepositories();
  }, [workspaceId]);

  const loadRemoteRepositories = async () => {
    setIsLoadingRepos(true);
    try {
      const response = await workspaceService.getRemoteRepositories(workspaceId);
      setRemoteRepos(response.data.repositories || []);
    } catch (error) {
      console.error("Error loading remote repositories:", error);
      alert("Error loading remote repositories");
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const handleImportRepositories = async () => {
    if (selectedRepos.length === 0) {
      alert("Please select at least one repository");
      return;
    }

    setIsImporting(true);
    try {
      await workspaceService.importRepositories(workspaceId, {
        repository_ids: selectedRepos,
      });
      setImportComplete(true);
    } catch (error) {
      console.error("Error importing repositories:", error);
      alert(
        error.response?.data?.message ||
          "Error importing repositories"
      );
    } finally {
      setIsImporting(false);
    }
  };

  const toggleRepoSelection = (repoId) => {
    setSelectedRepos((prev) =>
      prev.includes(repoId)
        ? prev.filter((id) => id !== repoId)
        : [...prev, repoId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedRepos.length === remoteRepos.length) {
      setSelectedRepos([]);
    } else {
      setSelectedRepos(remoteRepos.map((repo) => repo.id));
    }
  };

  const handleClose = () => {
    onClose();
  };

  if (importComplete) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-20 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
          <div className="p-6 sm:p-8 text-center">
            <div className="w-16 h-16 sm:w-20 sm:h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6">
              <svg
                className="w-10 h-10 sm:w-12 sm:h-12 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h3 className="text-xl sm:text-2xl font-semibold mb-3">
              Import successful!
            </h3>
            <p className="text-sm sm:text-base text-gray-600 mb-6">
              <strong>{selectedRepos.length}</strong> repository(s) imported
              successfully
            </p>
            <button
              onClick={handleClose}
              className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Finish
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-20 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-gray-200 sticky top-0 bg-white z-10">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg sm:text-xl font-semibold text-gray-900">
                Import repositories
              </h2>
              <p className="text-xs sm:text-sm text-gray-500 mt-1">
                {selectedRepos.length} repository(s) selected
              </p>
            </div>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-700"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        <div className="px-4 sm:px-6 py-6 sm:py-8">
          {isLoadingRepos ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600 text-sm">
                Loading repositories...
              </p>
            </div>
          ) : remoteRepos.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <svg
                className="w-16 h-16 text-gray-400 mx-auto mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                />
              </svg>
              <p className="text-gray-600">
                No new repositories available
              </p>
              <p className="text-sm text-gray-500 mt-2">
                All repositories have already been imported
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                {remoteRepos.length > 0 && (
                  <button
                    onClick={toggleSelectAll}
                    className="px-3 sm:px-4 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    {selectedRepos.length === remoteRepos.length
                      ? "Deselect All"
                      : "Select All"}
                  </button>
                )}
              </div>

              <div className="space-y-3 max-h-[60vh] overflow-y-auto">
                {remoteRepos.map((repo) => (
                  <div
                    key={repo.id}
                    onClick={() => toggleRepoSelection(repo.id)}
                    className={`p-3 sm:p-4 border-2 rounded-lg cursor-pointer transition-all ${
                      selectedRepos.includes(repo.id)
                        ? "border-blue-600 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <h4 className="font-semibold text-gray-900 text-sm sm:text-base truncate">
                            {repo.name}
                          </h4>
                          {repo.private && (
                            <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-800 rounded">
                              Private
                            </span>
                          )}
                          {repo.language && (
                            <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded">
                              {repo.language}
                            </span>
                          )}
                        </div>
                        <p className="text-xs sm:text-sm text-gray-500 mb-2">
                          {repo.description || "Pas de description"}
                        </p>
                        <p className="text-xs text-gray-400">
                          Default Branch:{" "}
                          <span className="font-medium">
                            {repo.default_branch}
                          </span>
                        </p>
                      </div>
                      <div className="ml-4 flex-shrink-0">
                        <input
                          type="checkbox"
                          checked={selectedRepos.includes(repo.id)}
                          onChange={() => {}}
                          className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="px-4 sm:px-6 py-4 border-t border-gray-200 flex justify-between sticky bottom-0 bg-white">
          <button
            onClick={handleClose}
            className="px-4 sm:px-5 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm sm:text-base"
          >
            Cancel
          </button>

          <button
            onClick={handleImportRepositories}
            disabled={isImporting || selectedRepos.length === 0}
            className="px-4 sm:px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base"
          >
            {isImporting
              ? "Importing..."
              : `Import ${selectedRepos.length > 0 ? `(${selectedRepos.length})` : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImportRepositoriesModal;