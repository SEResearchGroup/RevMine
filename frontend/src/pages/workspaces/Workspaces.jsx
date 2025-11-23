import React, { useState, useEffect } from 'react';
import {
  Search, Settings, Trash2, Eye, Plus,
  FolderGit2, Github, GitBranch, Clock, Lock
} from 'lucide-react';
import { workspaceService } from '../../services/api';
const Workspaces = () => {
  const [workspaces, setWorkspaces] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);

  // Modal steps
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    platform: 'gitlab',          // gitlab | github
    hostingType: 'gitlab.com',   // gitlab.com | self-hosted (seulement pour GitLab)
    url: '',
    token: ''
  });

  // Chargement initial des workspaces
  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    try {
      setLoading(true);
      const response = await workspaceService.getAll();
      setWorkspaces(response.data); // l'API renvoie { data: [...] }
    } catch (error) {
      console.error('Erreur lors du chargement des workspaces', error);
    } finally {
      setLoading(false);
    }
  };

  // Création du workspace
  const handleCreateWorkspace = async () => {
    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        platform: formData.platform,
        token: formData.token,
      };

      // URL uniquement si GitLab self-hosted
      if (formData.platform === 'gitlab' && formData.hostingType === 'self-hosted') {
        payload.url = formData.url.trim();
      }

      await workspaceService.create(payload);
      await loadWorkspaces();      // rafraîchir la liste
      setStep(3);                  // passer à l'étape de succès
    } catch (error) {
      console.error('Erreur création workspace', error);
      alert('Impossible de créer le workspace. Vérifiez les données.');
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setStep(1);
    setFormData({
      name: '',
      description: '',
      platform: 'gitlab',
      hostingType: 'gitlab.com',
      url: '',
      token: ''
    });
  };

  const handleNext = () => {
    // Étape 1 → validation nom
    if (step === 1 && !formData.name.trim()) {
      alert('Le nom du workspace est obligatoire');
      return;
    }

    // Étape 2 → validation token (et url si self-hosted)
    if (step === 2) {
      if (!formData.token.trim()) {
        alert('Le token d’accès est obligatoire');
        return;
      }
      if (formData.platform === 'gitlab' && formData.hostingType === 'self-hosted' && !formData.url.trim()) {
        alert('L’URL du serveur GitLab est obligatoire pour le self-hosted');
        return;
      }

      handleCreateWorkspace(); // création réelle
      return;
    }

    // Étape 3 → on ne va pas plus loin
    if (step < 3) setStep(prev => prev + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep(prev => prev - 1);
  };

  const filteredWorkspaces = workspaces.filter(ws =>
    ws.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getTimeDiff = (dateString) => {
    if (!dateString) return 'jamais';
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    return diff === 0 ? 'aujourd’hui' : `il y a ${diff} jour${diff > 1 ? 's' : ''}`;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1 max-w-md">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Rechercher un workspace..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button className="px-4 py-2 border border-gray-300 rounded-lg flex items-center gap-2 hover:bg-gray-50">
              <Settings className="w-4 h-4" />
              Filtrer
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg flex items-center gap-2 hover:bg-blue-700"
            >
              <Plus className="w-5 h-5" />
              Nouveau Workspace
            </button>
          </div>
        </div>
      </div>

      {/* Liste des workspaces */}
      <div className="max-w-7xl mx-auto">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Chargement des workspaces...</div>
        ) : filteredWorkspaces.length === 0 ? (
          <div className="text-center py-12 text-gray-500">Aucun workspace trouvé</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredWorkspaces.map((ws) => (
              <div
                key={ws.id}
                className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-lg transition-shadow cursor-pointer"
              >
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
                    {ws.platform === 'github' ? (
                      <Github className="w-7 h-7" />
                    ) : (
                      <GitBranch className="w-7 h-7" />
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg">{ws.name}</h3>
                  </div>
                </div>

                <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                  {ws.description || 'Aucune description'}
                </p>

                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <FolderGit2 className="w-4 h-4" />
                    <span>{ws.projects_count ?? 0} projet{ws.projects_count > 1 ? 's' : ''}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    <span>Mis à jour {getTimeDiff(ws.updated_at)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4" />
                    <span>Privé</span>
                  </div>
                </div>

                <div className="flex justify-between items-center mt-6 pt-4 border-t border-gray-200">
                  <div className="flex gap-2">
                    <button className="p-2 hover:bg-gray-100 rounded">
                      <Settings className="w-4 h-4 text-gray-600" />
                    </button>
                    <button className="p-2 hover:bg-gray-100 rounded">
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                  <button className="p-2 hover:bg-gray-100 rounded">
                    <Eye className="w-4 h-4 text-blue-600" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal de création */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold">
                  {step === 1 && 'Créer un nouveau workspace'}
                  {step === 2 && 'Configuration de la plateforme'}
                  {step === 3 && 'Workspace créé !'}
                </h2>
                <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-700">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Barre de progression */}
              <div className="flex gap-2 mt-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className={`h-2 flex-1 rounded-full transition-colors ${step >= i ? 'bg-blue-600' : 'bg-gray-200'}`}
                  />
                ))}
              </div>
            </div>

            {/* Body */}
            <div className="px-6 py-8">
              {/* Étape 1 - Infos générales */}
              {step === 1 && (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nom du workspace <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="À quoi sert ce workspace..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Plateforme <span className="text-red-500">*</span>
                    </label>
                    <div className="grid grid-cols-2 gap-4">
                      <button
                        onClick={() => setFormData({ ...formData, platform: 'gitlab', hostingType: 'gitlab.com' })}
                        className={`p-6 border-2 rounded-lg flex flex-col items-center gap-3 transition-all ${
                          formData.platform === 'gitlab' ? 'border-blue-600 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                        }`}
                      >
                        <GitBranch className="w-10 h-10" />
                        <span className="font-medium">GitLab</span>
                      </button>

                      <button
                        onClick={() => setFormData({ ...formData, platform: 'github' })}
                        className={`p-6 border-2 rounded-lg flex flex-col items-center gap-3 transition-all ${
                          formData.platform === 'github' ? 'border-blue-600 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                        }`}
                      >
                        <Github className="w-10 h-10" />
                        <span className="font-medium">GitHub</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Étape 2 - Token & hébergement */}
              {step === 2 && (
                <div className="space-y-6">
                  {/* GitLab → choix hébergement */}
                  {formData.platform === 'gitlab' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-3">
                        Type d’hébergement GitLab
                      </label>
                      <div className="grid grid-cols-2 gap-4">
                        <button
                          onClick={() => setFormData({ ...formData, hostingType: 'gitlab.com' })}
                          className={`py-3 border-2 rounded-lg transition-all ${
                            formData.hostingType === 'gitlab.com'
                              ? 'border-blue-600 bg-blue-50'
                              : 'border-gray-300 hover:border-gray-400'
                          }`}
                        >
                          GitLab.com
                        </button>
                        <button
                          onClick={() => setFormData({ ...formData, hostingType: 'self-hosted' })}
                          className={`py-3 border-2 rounded-lg transition-all ${
                            formData.hostingType === 'self-hosted'
                              ? 'border-blue-600 bg-blue-50'
                              : 'border-gray-300 hover:border-gray-400'
                          }`}
                        >
                          Self-hosted
                        </button>
                      </div>
                    </div>
                  )}

                  {/* URL si self-hosted */}
                  {formData.platform === 'gitlab' && formData.hostingType === 'self-hosted' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        URL du serveur GitLab <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="url"
                        value={formData.url}
                        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                        placeholder="https://gitlab.monsociete.com"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  )}

                  {/* Token */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Token d’accès personnel <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.token}
                      onChange={(e) => setFormData({ ...formData, token: e.target.value })}
                      placeholder={formData.platform === 'github' ? 'ghp_...' : 'glpat-...'}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="mt-2 text-sm text-gray-500">
                      {formData.platform === 'github'
                        ? 'GitHub → Settings → Developer settings → Personal access tokens'
                        : 'GitLab → User Settings → Access Tokens (scopes : api, read_repository)'}
                    </p>
                  </div>
                </div>
              )}

              {/* Étape 3 - Succès */}
              {step === 3 && (
                <div className="text-center py-12">
                  <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                    <svg className="w-12 h-12 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h3 className="text-2xl font-semibold mb-3">Workspace créé avec succès !</h3>
                  <p className="text-gray-600 mb-8">
                    Votre workspace <strong>“{formData.name}”</strong> est maintenant disponible.
                  </p>
                  <div className="bg-gray-50 rounded-lg p-6 text-left">
                    <p className="text-sm text-gray-600">
                      L’importation automatique des projets depuis votre instance sera disponible très prochainement.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
              <button
                onClick={step === 3 ? handleCloseModal : handleBack}
                className={`px-5 py-2 border rounded-lg ${
                  step === 1 ? 'opacity-50 cursor-not-allowed border-gray-300' : 'border-gray-300 hover:bg-gray-50'
                }`}
                disabled={step === 1}
              >
                {step === 3 ? 'Fermer' : 'Retour'}
              </button>

              <button
                onClick={step === 3 ? handleCloseModal : handleNext}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                {step === 3 ? 'Terminer' : 'Suivant'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Workspaces;