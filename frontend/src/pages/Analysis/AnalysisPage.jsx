// import React, { useState } from "react";
// import { analyzeService } from "../../services/api";
// import DatasetSelectionSection from "../../components/analysis/DatasetSelectionSection";
// import AnalysisConfigurationSection from "../../components/analysis/AnalysisConfigurationSection";

// const AnalysisPage = () => {
//   const [selectedDataset, setSelectedDataset] = useState(null);
//   const [uploadedFile, setUploadedFile] = useState(null);
//   const [analysisResults, setAnalysisResults] = useState(null);

//   const handleDatasetSelect = (dataset) => {
//     setSelectedDataset(dataset);
//     setUploadedFile(null);
//     loadAnalysisResults(dataset.id);
//   };

//   const handleNewFileSelect = (file) => {
//     setUploadedFile(file);
//     setSelectedDataset(null);
//     setAnalysisResults(null);
//   };

//   const loadAnalysisResults = async (datasetId) => {
//     try {
//       const results = await analyzeService.getAnalysisById(datasetId);
//       setAnalysisResults(results);
//     } catch (error) {
//       console.error("Error loading analysis results:", error);
//     }
//   };

//   const handleDatasetChange = () => {
//     setSelectedDataset(null);
//     setUploadedFile(null);
//     setAnalysisResults(null);
//   };

//   return (
//     <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
//       {!selectedDataset && !uploadedFile ? (
//         <DatasetSelectionSection
//           onSelectDataset={handleDatasetSelect}
//           onFileSelect={handleNewFileSelect}
//         />
//       ) : (
//         <AnalysisConfigurationSection
//           dataset={selectedDataset}
//           uploadedFile={uploadedFile}
//           analysisResults={analysisResults}
//           onChangeDataset={handleDatasetChange}
//         />
//       )}
//     </div>
//   );
// };

// export default AnalysisPage;


import React, { useState } from "react";
import { analyzeService } from "../../services/api";
import DatasetSelectionSection from "../../components/analysis/DatasetSelectionSection";
import AnalysisConfigurationSection from "../../components/analysis/AnalysisConfigurationSection";

const AnalysisPage = () => {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);

  const handleDatasetSelect = (dataset) => {
    console.log("Dataset selected:", dataset);
    setSelectedDataset(dataset);
    setUploadedFile(null);
    // Optionnel: charger les résultats d'analyse existants si disponibles
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