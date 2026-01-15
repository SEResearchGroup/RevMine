import React, { useState } from "react";
import { AVAILABLE_METRICS } from "../../utils/constants";
import {
  Download,
  FileDown,
  Maximize2,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import InteractiveChart from "./InteractiveChart";

const ResultsDisplay = ({ results = [], onExportAll, onExportSingle, exportLoading }) => {
  const [fullscreenChart, setFullscreenChart] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [expandedStats, setExpandedStats] = useState({});

  const openFullscreen = (result, index) => {
    setFullscreenChart(result);
    setCurrentIndex(index);
  };

  const closeFullscreen = () => {
    setFullscreenChart(null);
  };

  const goToPrevious = () => {
    const newIndex = currentIndex > 0 ? currentIndex - 1 : results.length - 1;
    setCurrentIndex(newIndex);
    setFullscreenChart(results[newIndex]);
  };

  const goToNext = () => {
    const newIndex = currentIndex < results.length - 1 ? currentIndex + 1 : 0;
    setCurrentIndex(newIndex);
    setFullscreenChart(results[newIndex]);
  };

  const toggleStats = (resultId) => {
    setExpandedStats(prev => ({
      ...prev,
      [resultId]: !prev[resultId]
    }));
  };

  if (!results || results.length === 0) {
    return null;
  }

  return (
    <>
      <div className="space-y-6">
        {/* Header with Export Button */}
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-slate-800">
            Résultats d'Analyse ({results.length})
          </h2>
          <button
            onClick={onExportAll}
            disabled={exportLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-slate-400"
          >
            {exportLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Exportation...
              </>
            ) : (
              <>
                <FileDown className="w-4 h-4" />
                Exporter tout en PDF
              </>
            )}
          </button>
        </div>

        {/* Results Stack - One per row */}
        <div className="space-y-6">
          {results.map((result, index) => {
            const metric = AVAILABLE_METRICS.find(
              (m) => m.id === result.chart_type
            );
            const isStatsExpanded = expandedStats[result.id];

            return (
              <div
                key={result.id}
                className="bg-white rounded-lg border border-slate-200 overflow-hidden hover:shadow-lg transition-shadow"
              >
                {/* Chart Header */}
                <div className="flex justify-between items-start p-6 pb-4 border-b border-slate-100">
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-slate-800">
                      {metric?.label || result.chart_type}
                    </h3>
                    <p className="text-sm text-slate-600 mt-1">
                      {metric?.description}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openFullscreen(result, index)}
                      className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Voir en plein écran"
                    >
                      <Maximize2 className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => onExportSingle(result)}
                      className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Exporter ce graphique"
                    >
                      <Download className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Large Chart Display */}
                <div className="p-6">
                  <div className="bg-slate-50 rounded-lg p-6 h-96">
                    {result.chart_data ? (
                      <InteractiveChart
                        chartData={{ data: result.chart_data }}
                        chartType={result.chart_type}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-slate-400">
                        Aucune donnée de graphique disponible
                      </div>
                    )}
                  </div>
                </div>

                {/* Statistics Toggle Button & Content */}
                {result.chart_data?.stats && (
                  <div className="border-t border-slate-100">
                    <button
                      onClick={() => toggleStats(result.id)}
                      className="w-full px-6 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors"
                    >
                      <span className="text-sm font-semibold text-slate-700">
                        Statistiques détaillées
                      </span>
                      {isStatsExpanded ? (
                        <ChevronUp className="w-5 h-5 text-slate-600" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-600" />
                      )}
                    </button>
                    
                    {isStatsExpanded && (
                      <div className="px-6 pb-6 pt-2">
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                          {Object.entries(result.chart_data.stats).map(([key, value]) => (
                            <div key={key} className="p-3 bg-blue-50 rounded-lg">
                              <div className="text-xs text-slate-600 capitalize mb-1">
                                {key.replace('_', ' ')}
                              </div>
                              <div className="text-lg font-bold text-slate-800">
                                {typeof value === "number"
                                  ? value.toFixed(2)
                                  : value}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Fullscreen Modal */}
      {fullscreenChart && (
        <div className="fixed inset-0 bg-black bg-opacity-95 z-50 flex items-center justify-center">
          <button
            onClick={closeFullscreen}
            className="absolute top-4 right-4 p-2 bg-white rounded-full hover:bg-slate-100 transition-colors z-10"
            title="Fermer"
          >
            <X className="w-6 h-6 text-slate-800" />
          </button>

          {/* Navigation Arrows */}
          {results.length > 1 && (
            <>
              <button
                onClick={goToPrevious}
                className="absolute left-4 p-3 bg-white rounded-full hover:bg-slate-100 transition-colors z-10"
                title="Précédent"
              >
                <ChevronLeft className="w-6 h-6 text-slate-800" />
              </button>
              <button
                onClick={goToNext}
                className="absolute right-4 p-3 bg-white rounded-full hover:bg-slate-100 transition-colors z-10"
                title="Suivant"
              >
                <ChevronRight className="w-6 h-6 text-slate-800" />
              </button>
            </>
          )}

          {/* Fullscreen Chart */}
          <div className="w-full h-full max-w-7xl max-h-[90vh] p-8 flex flex-col">
            <div className="bg-white rounded-lg p-6 mb-4">
              <h2 className="text-2xl font-bold text-slate-800">
                {AVAILABLE_METRICS.find((m) => m.id === fullscreenChart.chart_type)?.label || fullscreenChart.chart_type}
              </h2>
              <p className="text-slate-600 mt-1">
                {AVAILABLE_METRICS.find((m) => m.id === fullscreenChart.chart_type)?.description}
              </p>
            </div>
            
            <div className="flex-1 bg-white rounded-lg p-6 overflow-auto">  
              <InteractiveChart
                chartData={{ data: fullscreenChart.chart_data }}
                chartType={fullscreenChart.chart_type}
              />
            </div>

            {fullscreenChart.chart_data?.stats && (
              <div className="bg-white rounded-lg p-6 mt-4">
                <h3 className="text-lg font-semibold text-slate-800 mb-3">
                  Statistiques Détaillées
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  {Object.entries(fullscreenChart.chart_data.stats).map(([key, value]) => (
                    <div key={key} className="p-3 bg-blue-50 rounded-lg">
                      <div className="text-sm text-slate-600 capitalize mb-1">
                        {key.replace('_', ' ')}
                      </div>
                      <div className="text-xl font-bold text-slate-800">
                        {typeof value === "number" ? value.toFixed(2) : value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Chart Counter */}
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-white px-4 py-2 rounded-full">
            <span className="text-sm font-medium text-slate-800">
              {currentIndex + 1} / {results.length}
            </span>
          </div>
        </div>
      )}
    </>
  );
};

export default ResultsDisplay;