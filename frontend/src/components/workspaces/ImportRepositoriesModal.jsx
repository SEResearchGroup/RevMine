import React, { useState, useEffect } from "react";
import { workspaceService } from "../../services/api";

const ImportRepositoriesModal = ({ workspaceId, onClose }) => {
  const [activeTab, setActiveTab] = useState("workspace");
  const [remoteRepos, setRemoteRepos] = useState([]);
  const [selectedRepos, setSelectedRepos] = useState([]);
  const [importedRepoIds, setImportedRepoIds] = useState([]);
  const [directRepositoryId, setDirectRepositoryId] = useState("");
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importComplete, setImportComplete] = useState(false);
  const [importedCount, setImportedCount] = useState(0);

  useEffect(() => {
    loadData();
  }, [workspaceId]);

  const loadData = async () => {
    setIsLoadingRepos(true);
    try {
      const importedResponse = await workspaceService.getRepositories(
        workspaceId
      );
      const importedRepos = importedResponse.data || [];
      const importedIds = importedRepos.map((repo) => String(repo.external_id));
      setImportedRepoIds(importedIds);

      const remoteResponse = await workspaceService.getRemoteRepositories(
        workspaceId
      );
      const allRepos = remoteResponse.data.repositories || [];
      setRemoteRepos(allRepos);

      setSelectedRepos(
        allRepos
          .filter((repo) => importedIds.includes(String(repo.id)))
          .map((repo) => String(repo.id))
      );
    } catch (error) {
      console.error("Error loading repositories:", error);
      alert("Error loading repositories");
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const handleImportRepositories = async () => {
    const trimmedDirectRepositoryId = directRepositoryId.trim();
    const repositoryIdsToImport =
      activeTab === "workspace"
        ? selectedRepos.filter((repoId) => !importedRepoIds.includes(repoId))
        : trimmedDirectRepositoryId
        ? [trimmedDirectRepositoryId]
        : [];

    if (repositoryIdsToImport.length === 0) {
      alert(
        activeTab === "workspace"
          ? "No new repositories to import"
          : "Please enter a repository ID"
      );
      return;
    }

    if (
      activeTab === "direct" &&
      importedRepoIds.includes(trimmedDirectRepositoryId)
    ) {
      alert("This repository is already imported");
      return;
    }

    setIsImporting(true);
    try {
      const response = await workspaceService.importRepositories(workspaceId, {
        repository_ids: repositoryIdsToImport,
      });
      setImportedCount(
        response.data?.imported_count ?? repositoryIdsToImport.length
      );
      setImportComplete(true);
    } catch (error) {
      console.error("Error importing repositories:", error);
      alert(error.response?.data?.message || "Error importing repositories");
    } finally {
      setIsImporting(false);
    }
  };

  const toggleRepoSelection = (repoId) => {
    const normalizedRepoId = String(repoId);

    if (importedRepoIds.includes(normalizedRepoId)) {
      return;
    }

    setSelectedRepos((prev) =>
      prev.includes(normalizedRepoId)
        ? prev.filter((id) => id !== normalizedRepoId)
        : [...prev, normalizedRepoId]
    );
  };

  const toggleSelectAll = () => {
    const selectableRepos = remoteRepos.filter(
      (repo) => !importedRepoIds.includes(String(repo.id))
    );
    const selectableIds = selectableRepos.map((repo) => String(repo.id));

    const allSelectableSelected = selectableIds.every((id) =>
      selectedRepos.includes(id)
    );

    if (allSelectableSelected) {
      setSelectedRepos(
        selectedRepos.filter((id) => importedRepoIds.includes(id))
      );
    } else {
      setSelectedRepos([...importedRepoIds, ...selectableIds]);
    }
  };

  const handleClose = () => {
    onClose();
  };

  const newSelectedCount = selectedRepos.filter(
    (id) => !importedRepoIds.includes(id)
  ).length;
  const trimmedDirectRepositoryId = directRepositoryId.trim();
  const isDirectRepoAlreadyImported =
    trimmedDirectRepositoryId.length > 0 &&
    importedRepoIds.includes(trimmedDirectRepositoryId);
  const readyToImportCount =
    activeTab === "workspace"
      ? newSelectedCount
      : trimmedDirectRepositoryId && !isDirectRepoAlreadyImported
      ? 1
      : 0;

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
              <strong>{importedCount}</strong> repository(s) imported
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
                {readyToImportCount} repository(s) ready to import
                {importedRepoIds.length > 0 && (
                  <span className="text-blue-600">
                    {" "}
                    ({importedRepoIds.length} already imported)
                  </span>
                )}
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
          <div className="inline-flex rounded-lg bg-gray-100 p-1 mb-6">
            <button
              type="button"
              onClick={() => setActiveTab("workspace")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === "workspace"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Workspace repositories
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("direct")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === "direct"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Import by ID
            </button>
          </div>

          {activeTab === "workspace" && isLoadingRepos ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600 text-sm">Loading repositories...</p>
            </div>
          ) : activeTab === "workspace" && remoteRepos.length === 0 ? (
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
              <p className="text-gray-600">No repositories available</p>
              <p className="text-sm text-gray-500 mt-2">
                No repositories found to import
              </p>
            </div>
          ) : activeTab === "direct" ? (
            <div className="space-y-5">
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                <p className="text-sm text-blue-900">
                  Import a repository by entering its GitHub or GitLab external
                  ID, even if it does not appear in this workspace list.
                </p>
              </div>

              <div>
                <label
                  htmlFor="direct-repository-id"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Repository ID
                </label>
                <input
                  id="direct-repository-id"
                  type="text"
                  value={directRepositoryId}
                  onChange={(event) =>
                    setDirectRepositoryId(event.target.value)
                  }
                  placeholder="Example: 123456789"
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
                <p className="text-xs text-gray-500 mt-2">
                  Use the external repository ID from the Git provider.
                </p>
              </div>

              {isDirectRepoAlreadyImported && (
                <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
                  This repository is already imported in the workspace.
                </div>
              )}

              {!isDirectRepoAlreadyImported && trimmedDirectRepositoryId && (
                <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
                  Repository <strong>{trimmedDirectRepositoryId}</strong> is
                  ready to import.
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                {remoteRepos.length > 0 && (
                  <button
                    onClick={toggleSelectAll}
                    className="px-3 sm:px-4 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    {remoteRepos
                      .filter((r) => !importedRepoIds.includes(String(r.id)))
                      .every((r) => selectedRepos.includes(String(r.id)))
                      ? "Deselect All"
                      : "Select All"}
                  </button>
                )}
              </div>

              <div className="space-y-3 max-h-[60vh] overflow-y-auto">
                {remoteRepos.map((repo) => {
                  const isImported = importedRepoIds.includes(String(repo.id));

                  const isSelected = selectedRepos.includes(String(repo.id));
                  return (
                    <div
                      key={repo.id}
                      onClick={() => toggleRepoSelection(repo.id)}
                      className={`p-3 sm:p-4 border-2 rounded-lg transition-all ${
                        isImported
                          ? "border-green-600 bg-green-50 cursor-not-allowed"
                          : isSelected
                          ? "border-blue-600 bg-blue-50 cursor-pointer"
                          : "border-gray-200 hover:border-gray-300 cursor-pointer"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <h4 className="font-semibold text-gray-900 text-sm sm:text-base truncate">
                              {repo.name}
                            </h4>
                            {isImported && (
                              <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded font-medium">
                                Already Imported
                              </span>
                            )}
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
                            checked={isSelected}
                            disabled={isImported}
                            onChange={() => {}}
                            className={`w-5 h-5 rounded focus:ring-blue-500 ${
                              isImported
                                ? "text-green-600 cursor-not-allowed"
                                : "text-blue-600 cursor-pointer"
                            }`}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
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
            disabled={isImporting || readyToImportCount === 0}
            className="px-4 sm:px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base"
          >
            {isImporting
              ? "Importing..."
              : `Import ${readyToImportCount > 0 ? `(${readyToImportCount})` : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImportRepositoriesModal;
