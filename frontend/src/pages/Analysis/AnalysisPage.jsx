import React, { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { analyzeService } from "../../services/api";
import DatasetSelectionSection from "../../components/analysis/DatasetSelectionSection";
import AnalysisConfigurationSection from "../../components/analysis/AnalysisConfigurationSection";

const AnalysisPage = () => {
  const location = useLocation();
  const [selectedDataset, setSelectedDataset] = useState(location.state?.dataset || null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);

  useEffect(() => {
    const loadInitialResults = async () => {
      if (location.state?.dataset?.analysis_id) {
        try {
          const results = await analyzeService.getAnalysisById(location.state.dataset.analysis_id);
          setAnalysisResults(results);
        } catch (error) {
          console.error("Error loading analysis results:", error);
        }
      }
    };

    loadInitialResults();
  }, []);

  const handleDatasetSelect = (dataset) => {
    console.log("Dataset selected:", dataset);
    setSelectedDataset(dataset);
    setUploadedFile(null);
    if (dataset.analysis_id) {
      loadAnalysisResults(dataset.analysis_id);
    }
  };

  const handleNewFileSelect = (file) => {
    setUploadedFile(file);
    setSelectedDataset(null);
    setAnalysisResults(null);
  };

  const loadAnalysisResults = async (analysisId) => {
    try {
      const results = await analyzeService.getAnalysisById(analysisId);
      setAnalysisResults(results);
    } catch (error) {
      console.error("Error loading analysis results:", error);
    }
  };

  const handleDatasetChange = () => {
    setSelectedDataset(null);
    setUploadedFile(null);
    setAnalysisResults(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {!selectedDataset && !uploadedFile ? (
        <DatasetSelectionSection
          onSelectDataset={handleDatasetSelect}
          onFileSelect={handleNewFileSelect}
        />
      ) : (
        <AnalysisConfigurationSection
          dataset={selectedDataset}
          uploadedFile={uploadedFile}
          analysisResults={analysisResults}
          onChangeDataset={handleDatasetChange}
        />
      )}
    </div>
  );
};

export default AnalysisPage;
