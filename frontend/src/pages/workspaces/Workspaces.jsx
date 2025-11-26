import React, { useState, useEffect } from "react";
import {
  Search,
  Settings,
  Trash2,
  Eye,
  Plus,
  FolderGit2,
  Github,
  GitBranch,
  Clock,
  Lock,
  BarChart3,
  GitPullRequest,
  Package,
  Layers,
} from "lucide-react";
import { workspaceService } from "../../services/api";
const Workspaces = () => {
  const [workspaces, setWorkspaces] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);

  const [stats] = useState({
    analysisThisMonth: 10,
    prsCollected: 45,
    quotaUsed: 85,
    activeWorkspaces: 4,
  });

  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    platform: "gitlab",
    hostingType: "gitlab.com",
    url: "",
    token: "",
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
      console.error("Erreur lors du chargement des workspaces", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredWorkspaces = workspaces.filter((ws) =>
    ws.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getTimeDiff = (dateString) => {
    if (!dateString) return "jamais";
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    return diff === 0
      ? "aujourd'hui"
      : `il y a ${diff} jour${diff > 1 ? "s" : ""}`;
  };
  const [testResult, setTestResult] = useState(null);
  const [testMessage, setTestMessage] = useState("");
  const [isTestLoading, setIsTestLoading] = useState(false);
  const [remoteRepos, setRemoteRepos] = useState([]);
  const [selectedRepos, setSelectedRepos] = useState([]);
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);
  const [createdWorkspaceId, setCreatedWorkspaceId] = useState(null);

  const handleTestConnection = async () => {
    setIsTestLoading(true);
    setTestResult(null);
    try {
      const testData = {
        platform: formData.platform,
        token: formData.token,
      };

      if (formData.platform === "gitlab") {
        testData.hosting_type = formData.hostingType;
        if (formData.hostingType === "self-hosted") {
          testData.url = formData.url;
        }
      }

      const response = await workspaceService.testConnection(testData);

      if (response.data.success) {
        setTestResult("success");
        setTestMessage(response.data.user_data?.login || "Connexion réussie");
      }
    } catch (error) {
      setTestResult("error");
      setTestMessage(
        error.response?.data?.message ||
          "Erreur lors du test de connexion. Vérifiez vos identifiants."
      );
    } finally {
      setIsTestLoading(false);
    }
  };

  const handleCreateWorkspaceAndLoadRepos = async () => {
    setIsCreatingWorkspace(true);
    try {
      const workspaceData = {
        name: formData.name,
        description: formData.description,
        platform: formData.platform,
        token: formData.token,
      };

      if (formData.platform === "gitlab") {
        workspaceData.hosting_type = formData.hostingType;
        if (formData.hostingType === "self-hosted") {
          workspaceData.url = formData.url;
        }
      }

      // Créer le workspace
      const response = await workspaceService.create(workspaceData);
      const workspaceId = response.data.workspace.id;
      setCreatedWorkspaceId(workspaceId);

      // Charger les repositories distants
      setIsLoadingRepos(true);
      const reposResponse = await workspaceService.getRemoteRepositories(
        workspaceId
      );
      setRemoteRepos(reposResponse.data.repositories);
      setIsLoadingRepos(false);

      // Passer à l'étape d'importation
      setStep(3);
    } catch (error) {
      alert(
        error.response?.data?.message ||
          "Erreur lors de la création du workspace"
      );
      setIsLoadingRepos(false);
    } finally {
      setIsCreatingWorkspace(false);
    }
  };

  const handleImportRepositories = async () => {
    if (selectedRepos.length === 0) {
      setStep(4);
      return;
    }

    setIsImporting(true);
    try {
      await workspaceService.importRepositories(createdWorkspaceId, {
        repository_ids: selectedRepos,
      });
      setStep(4); 
    } catch (error) {
      alert(
        error.response?.data?.message ||
          "Erreur lors de l'importation des repositories"
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

  const handleNext = () => {
    if (step === 1) {
      if (!formData.name || !formData.platform) {
        alert("Veuillez remplir tous les champs obligatoires");
        return;
      }
      setStep(2);
    } else if (step === 2) {
      if (!formData.token) {
        alert("Le token est obligatoire");
        return;
      }
      if (
        formData.platform === "gitlab" &&
        formData.hostingType === "self-hosted" &&
        !formData.url
      ) {
        alert("L'URL du serveur GitLab est obligatoire");
        return;
      }
      handleCreateWorkspaceAndLoadRepos();
    }
  };

  const handleBack = () => {
    if (step === 2) {
      setStep(1);
      setTestResult(null);
      setTestMessage("");
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setStep(1);
    setFormData({
      name: "",
      description: "",
      platform: "",
      hostingType: "gitlab.com",
      url: "",
      token: "",
    });
    setTestResult(null);
    setTestMessage("");
    setRemoteRepos([]);
    setSelectedRepos([]);
    setCreatedWorkspaceId(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto mb-6">
        <h1 className="text-2xl font-semibold text-gray-800 mb-6">
          <span className="text-blue-600">Data Sources</span> / Workspaces
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Analysis this month</p>
              <p className="text-3xl font-semibold text-gray-900">
                {stats.analysisThisMonth}
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-purple-600" />
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">PRs/MRs collected</p>
              <p className="text-3xl font-semibold text-gray-900">
                {stats.prsCollected}
              </p>
            </div>
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <GitPullRequest className="w-6 h-6 text-red-600" />
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Quota API used</p>
              <p className="text-3xl font-semibold text-gray-900">
                {stats.quotaUsed}%
              </p>
            </div>
            <div className="w-12 h-12 bg-teal-100 rounded-full flex items-center justify-center">
              <Package className="w-6 h-6 text-teal-600" />
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Active Workspaces</p>
              <p className="text-3xl font-semibold text-gray-900">
                {stats.activeWorkspaces}
              </p>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
              <Layers className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>

        {/* Search and Actions */}
        <div className="flex flex-row items-center justify-between gap-3 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search for Repository, Project"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex flex-row space-x-4">
            <button className="px-4 py-2.5 border border-gray-300 rounded-lg flex items-center gap-2 hover:bg-gray-50">
              <Settings className="w-4 h-4" />
              Filter
            </button>

            <button
              onClick={() => setShowModal(true)}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-lg flex items-center gap-2 hover:bg-blue-700"
            >
              <Plus className="w-5 h-5" />
              New Workspace
            </button>
          </div>
        </div>
      </div>

      {/* Liste des workspaces */}
      <div className="max-w-7xl mx-auto">
        {loading ? (
          <div className="text-center py-12 text-gray-500">
            Chargement des workspaces...
          </div>
        ) : filteredWorkspaces.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            Aucun workspace trouvé
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {filteredWorkspaces.map((ws) => (
              <div
                key={ws.id}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg transition-shadow cursor-pointer"
              >
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                    {ws.platform === "github" ? (
                      <Github className="w-6 h-6" />
                    ) : (
                      <GitBranch className="w-6 h-6" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-base text-gray-900 truncate">
                      {ws.name}
                    </h3>
                  </div>
                </div>

                <p className="text-gray-600 text-sm mb-4 line-clamp-2 min-h-[2.5rem]">
                  {ws.description || "Aucune description"}
                </p>

                <div className="space-y-2.5 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <FolderGit2 className="w-4 h-4 flex-shrink-0" />
                    <span>
                      {ws.projects_count ?? 0} Project
                      {ws.projects_count > 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 flex-shrink-0" />
                    <span>
                      {ws.analyses_count ?? 0} analyse
                      {ws.analyses_count > 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">
                      Edited {getTimeDiff(ws.updated_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 flex-shrink-0" />
                    <span className="capitalize">
                      {ws.visibility || "Public"}
                    </span>
                  </div>
                </div>

                <div className="flex justify-between items-center mt-5 pt-4 border-t border-gray-200">
                  <div className="flex gap-1">
                    <button className="p-2 hover:bg-gray-100 rounded-lg transition">
                      <Settings className="w-4 h-4 text-gray-600" />
                    </button>
                    <button className="p-2 hover:bg-gray-100 rounded-lg transition">
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                  <button className="p-2 hover:bg-gray-100 rounded-lg transition">
                    <Eye className="w-4 h-4 text-blue-600" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-5 border-b border-gray-200 sticky top-0 bg-white z-10">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900">
                  {step === 1 && "Créer un nouveau workspace"}
                  {step === 2 && "Configuration de la plateforme"}
                  {step === 3 && "Importer des repositories"}
                  {step === 4 && "Workspace créé !"}
                </h2>
                <button
                  onClick={handleCloseModal}
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

              <div className="flex gap-2 mt-4">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className={`h-2 flex-1 rounded-full transition-colors ${
                      step >= i ? "bg-blue-600" : "bg-gray-200"
                    }`}
                  />
                ))}
              </div>
            </div>

            <div className="px-6 py-8">
              {step === 1 && (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nom du workspace <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Mon super workspace"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description (facultatif)
                    </label>
                    <textarea
                      rows={3}
                      value={formData.description}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          description: e.target.value,
                        })
                      }
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      placeholder="À quoi sert ce workspace..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Plateforme <span className="text-red-500">*</span>
                    </label>
                    <div className="grid grid-cols-2 gap-4">
                      <button
                        onClick={() =>
                          setFormData({
                            ...formData,
                            platform: "gitlab",
                            hostingType: "gitlab.com",
                          })
                        }
                        className={`p-6 border-2 rounded-lg flex flex-col items-center gap-3 transition-all ${
                          formData.platform === "gitlab"
                            ? "border-blue-600 bg-blue-50"
                            : "border-gray-300 hover:border-gray-400"
                        }`}
                      >
                        <svg
                          className="w-10 h-10"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z" />
                        </svg>
                        <span className="font-medium">GitLab</span>
                      </button>

                      <button
                        onClick={() =>
                          setFormData({ ...formData, platform: "github" })
                        }
                        className={`p-6 border-2 rounded-lg flex flex-col items-center gap-3 transition-all ${
                          formData.platform === "github"
                            ? "border-blue-600 bg-blue-50"
                            : "border-gray-300 hover:border-gray-400"
                        }`}
                      >
                        <svg
                          className="w-10 h-10"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                        </svg>
                        <span className="font-medium">GitHub</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-6">
                  {formData.platform === "gitlab" && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-3">
                        Type d'hébergement GitLab
                      </label>
                      <div className="grid grid-cols-2 gap-4">
                        <button
                          onClick={() =>
                            setFormData({
                              ...formData,
                              hostingType: "gitlab.com",
                            })
                          }
                          className={`py-3 border-2 rounded-lg transition-all ${
                            formData.hostingType === "gitlab.com"
                              ? "border-blue-600 bg-blue-50"
                              : "border-gray-300 hover:border-gray-400"
                          }`}
                        >
                          GitLab.com
                        </button>
                        <button
                          onClick={() =>
                            setFormData({
                              ...formData,
                              hostingType: "self-hosted",
                            })
                          }
                          className={`py-3 border-2 rounded-lg transition-all ${
                            formData.hostingType === "self-hosted"
                              ? "border-blue-600 bg-blue-50"
                              : "border-gray-300 hover:border-gray-400"
                          }`}
                        >
                          Self-hosted
                        </button>
                      </div>
                    </div>
                  )}

                  {formData.platform === "gitlab" &&
                    formData.hostingType === "self-hosted" && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          URL du serveur GitLab{" "}
                          <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="url"
                          value={formData.url}
                          onChange={(e) =>
                            setFormData({ ...formData, url: e.target.value })
                          }
                          placeholder="https://gitlab.monsociete.com"
                          className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Token d'accès personnel{" "}
                      <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.token}
                      onChange={(e) => {
                        setFormData({ ...formData, token: e.target.value });
                        setTestResult(null); // Reset test result when token changes
                      }}
                      placeholder={
                        formData.platform === "github" ? "ghp_..." : "glpat-..."
                      }
                      className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="mt-2 text-sm text-gray-500">
                      {formData.platform === "github"
                        ? "GitHub → Settings → Developer settings → Personal access tokens"
                        : "GitLab → User Settings → Access Tokens (scopes : api, read_repository)"}
                    </p>
                  </div>

                  {/* Bouton de test de connexion */}
                  <div>
                    <button
                      onClick={handleTestConnection}
                      disabled={isTestLoading || !formData.token}
                      className="w-full px-4 py-3 border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isTestLoading
                        ? "Test en cours..."
                        : "Tester la connexion"}
                    </button>
                  </div>

                  {/* Résultat du test */}
                  {testResult === "success" && (
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3">
                      <svg
                        className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <div>
                        <p className="font-medium text-green-900">
                          Connexion réussie !
                        </p>
                        <p className="text-sm text-green-700 mt-1">
                          {testMessage}
                        </p>
                      </div>
                    </div>
                  )}

                  {testResult === "error" && (
                    <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                      <svg
                        className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <div>
                        <p className="font-medium text-red-900">
                          Échec de connexion
                        </p>
                        <p className="text-sm text-red-700 mt-1">
                          {testMessage}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {step === 3 && (
                <div className="space-y-6">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-lg font-semibold">
                        Importer des repositories
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {selectedRepos.length} repository(s) sélectionné(s)
                      </p>
                    </div>
                    {remoteRepos.length > 0 && (
                      <button
                        onClick={toggleSelectAll}
                        className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                      >
                        {selectedRepos.length === remoteRepos.length
                          ? "Tout désélectionner"
                          : "Tout sélectionner"}
                      </button>
                    )}
                  </div>

                  {isLoadingRepos ? (
                    <div className="text-center py-12">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                      <p className="text-gray-600">
                        Chargement des repositories...
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
                      <p className="text-gray-600">Aucun repository trouvé</p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {remoteRepos.map((repo) => (
                        <div
                          key={repo.id}
                          onClick={() => toggleRepoSelection(repo.id)}
                          className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                            selectedRepos.includes(repo.id)
                              ? "border-blue-600 bg-blue-50"
                              : "border-gray-200 hover:border-gray-300"
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="font-semibold text-gray-900">
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
                              <p className="text-sm text-gray-500 mb-2">
                                {repo.description || "Pas de description"}
                              </p>
                              <p className="text-xs text-gray-400">
                                Branche par défaut:{" "}
                                <span className="font-medium">
                                  {repo.default_branch}
                                </span>
                              </p>
                            </div>
                            <div className="ml-4">
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
                  )}
                </div>
              )}

              {step === 4 && (
                <div className="text-center py-12">
                  <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                    <svg
                      className="w-12 h-12 text-green-600"
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
                  <h3 className="text-2xl font-semibold mb-3">
                    Workspace créé avec succès !
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Votre workspace <strong>"{formData.name}"</strong> est
                    maintenant disponible.
                  </p>
                  {selectedRepos.length > 0 && (
                    <p className="text-gray-600 mb-8">
                      <strong>{selectedRepos.length}</strong> repository(s)
                      importé(s)
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-between sticky bottom-0 bg-white">
              <button
                onClick={step === 4 ? handleCloseModal : handleBack}
                className={`px-5 py-2 border rounded-lg ${
                  step === 1 || step === 3 || step === 4
                    ? "opacity-50 cursor-not-allowed border-gray-300"
                    : "border-gray-300 hover:bg-gray-50"
                }`}
                disabled={step === 1 || step === 3 || step === 4}
              >
                {step === 4 ? "Fermer" : "Retour"}
              </button>

              {step === 3 && (
                <button
                  onClick={handleImportRepositories}
                  disabled={isImporting}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isImporting
                    ? "Importation..."
                    : selectedRepos.length > 0
                    ? `Importer (${selectedRepos.length})`
                    : "Passer"}
                </button>
              )}

              {step < 3 && (
                <button
                  onClick={handleNext}
                  disabled={isCreatingWorkspace}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {step === 2 && isCreatingWorkspace
                    ? "Création..."
                    : "Suivant"}
                </button>
              )}

              {step === 4 && (
                <button
                  onClick={handleCloseModal}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Terminer
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Workspaces;
