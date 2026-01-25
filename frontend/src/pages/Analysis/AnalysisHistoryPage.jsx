// AnalysisHistoryPage.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Clock,
  FileText,
  Trash2,
  Eye,
  AlertCircle,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { analyzeService } from "../../services/api";

const AnalysisHistoryPage = () => {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadAnalyses();
  }, []);

  const loadAnalyses = async () => {
    try {
      setLoading(true);
      const data = await analyzeService.getAnalyses();
      setAnalyses(data);
    } catch (err) {
      setError("Erreur lors du chargement des analyses");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (analysisId) => {
    if (!window.confirm("Êtes-vous sûr de vouloir supprimer cette analyse ?")) {
      return;
    }

    try {
      setDeletingId(analysisId);
      await analyzeService.deleteAnalysis(analysisId);
      setAnalyses((prev) => prev.filter((a) => a.id !== analysisId));
    } catch (err) {
      setError("Erreur lors de la suppression");
      console.error(err);
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case "processing":
        return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <Clock className="w-5 h-5 text-slate-600" />;
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      completed: "bg-green-100 text-green-800",
      processing: "bg-blue-100 text-blue-800",
      failed: "bg-red-100 text-red-800",
      pending: "bg-slate-100 text-slate-800",
    };

    return badges[status] || badges.pending;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("fr-FR", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex justify-center items-center h-64">
            <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-800 mb-2">
              Historique des Analyses
            </h1>
            <p className="text-slate-600">
              Consultez et gérez vos analyses précédentes
            </p>
          </div>
          <button
            onClick={() => navigate("/analysis")}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Nouvelle Analyse
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-red-800 font-medium">Erreur</p>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-600 hover:text-red-700"
            >
              ×
            </button>
          </div>
        )}

        {/* Analyses List */}
        {analyses.length === 0 ? (
          <div className="bg-white rounded-lg shadow-lg p-12 text-center">
            <FileText className="w-16 h-16 mx-auto mb-4 text-slate-400" />
            <h3 className="text-lg font-semibold text-slate-800 mb-2">
              Aucune analyse
            </h3>
            <p className="text-slate-600 mb-6">
              Commencez par créer votre première analyse
            </p>
            <button
              onClick={() => navigate("/analysis")}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Créer une Analyse
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {analyses.map((analysis) => (
              <div
                key={analysis.id}
                className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-3">
                      {getStatusIcon(analysis.status)}
                      <div>
                        <h3 className="text-lg font-semibold text-slate-800">
                          {analysis.dataset?.filename || "Sans nom"}
                        </h3>
                        <p className="text-sm text-slate-600">
                          {formatDate(analysis.created_at)}
                        </p>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBadge(
                          analysis.status
                        )}`}
                      >
                        {analysis.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-slate-600">Lignes</p>
                        <p className="font-semibold text-slate-800">
                          {analysis.dataset?.rows_count?.toLocaleString() ||
                            "N/A"}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-600">Colonnes</p>
                        <p className="font-semibold text-slate-800">
                          {analysis.dataset?.columns_count || "N/A"}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-600">Métriques</p>
                        <p className="font-semibold text-slate-800">
                          {analysis.requested_charts?.length || 0}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-600">Résultats</p>
                        <p className="font-semibold text-slate-800">
                          {analysis.results?.length || 0}
                        </p>
                      </div>
                    </div>

                    {analysis.error_message && (
                      <div className="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded">
                        {analysis.error_message}
                      </div>
                    )}
                  </div>

                  <div className="flex space-x-2 ml-4">
                    {analysis.status === "completed" && (
                      <button
                        onClick={() => navigate(`/analysis/${analysis.id}`)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Voir les résultats"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(analysis.id)}
                      disabled={deletingId === analysis.id}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                      title="Supprimer"
                    >
                      {deletingId === analysis.id ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Trash2 className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisHistoryPage;
