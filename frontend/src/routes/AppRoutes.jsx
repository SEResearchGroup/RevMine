import { Routes, Route } from "react-router-dom";
import Login from "../pages/auth/Login";
import Register from "../pages/auth/Register";
import Dashboard from "../pages/dashboard/Dashboard";
import Workspaces from "../pages/workspaces/Workspaces";
import ProtectedRoute from "./ProtectedRoute";
import LayoutAuth from "../components/layout/LayoutAuth";
import LayoutPublic from "../components/layout/LayoutPublic";
import Projects from "../pages/projects/Projects";
import AllProjects from "../pages/projects/AllProjects";
import ProjectDetail from "../pages/collection/ProjectDetail";
import CollectionProgress from "../pages/collection/CollectionProgress";
import CollectionResults from "../pages/collection/CollectionResults";
import CollectionDetail from "../pages/collection/CollectionDetail";
import CleaningDetail from "../pages/collection/CleaningDetail";
import DataCleaning from "../pages/collection/DataCleaning";
import DataCleaningList from "../pages/collection/DataCleaningList";
import ExternalCollectionDetail from "../pages/collection/ExternalCollectionDetail";
import {
  GitHubCallback,
  GitLabCallback,
  GoogleCallback,
} from "../pages/auth/OAuthCallbacks";
import Profile from "../pages/profile/Profile";
import Settings from "../pages/Settings";
import GetStarted from "../pages/help/GetStarted";
import Faq from "../pages/help/Faq";

// Analysis Pages
import DatasetSelectionPage from "../pages/Analysis/DatasetSelectionPage";
import MetricsSelectionPage from "../pages/Analysis/MetricsSelectionPage";
import AnalysisDashboardPage from "../pages/Analysis/AnalysisDashboardPage";
import AnalysisHistoryPage from "../pages/Analysis/AnalysisHistoryPage";
import ProjectAnalysisDetailPage from "../pages/Analysis/ProjectAnalysisDetailPage";
import ProjectSelectionPage from "../pages/Analysis/ProjectSelectionPage";
import NewAnalysisPage from "../pages/Analysis/NewAnalysisPage";
import SingleChartPage from "../pages/Analysis/SingleChartPage";
import DatasetsPage from "../pages/Analysis/DatasetsPage";
import DatasetDetailPage from "../pages/Analysis/DatasetDetailPage";
import CreateAnalysisPage from "../pages/Analysis/CreateAnalysisPage";
import AnalysisResultsPage from "../pages/Analysis/AnalysisResultsPage";

// DevOps: Kanban Pages
import NewKanbanAnalysisPage from "../pages/Kanban/NewKanbanAnalysisPage";
import KanbanSourceSelectionPage from "../pages/Kanban/KanbanSourceSelectionPage";
import KanbanHistoryPage from "../pages/Kanban/KanbanHistoryPage";

// DevOps: CI/CD Pages
import NewCICDAnalysisPage from "../pages/CICD/NewCICDAnalysisPage";
import CICDPipelineSelectionPage from "../pages/CICD/CICDPipelineSelectionPage";
import CICDHistoryPage from "../pages/CICD/CICDHistoryPage";

// Shared DevOps Pages
import ComputeMetricsPage from "../pages/Devops/ComputeMetricsPage";
import DevopsCollectionProgress from "../pages/Devops/DevopsCollectionProgress";

const AppRoutes = () => {
  return (
    <Routes>
      <Route element={<LayoutPublic />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/auth/github/callback" element={<GitHubCallback />} />
        <Route path="/auth/gitlab/callback" element={<GitLabCallback />} />
        <Route path="/auth/google/callback" element={<GoogleCallback />} />
      </Route>

      <Route
        element={
          <ProtectedRoute>
            <LayoutAuth />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Workspaces />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/workspaces" element={<Workspaces />} />
        <Route path="/workspaces/:id" element={<Projects />} />
        <Route path="/projects" element={<AllProjects />} />
        <Route path="/data-cleaning" element={<DataCleaningList />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/help/get-started" element={<GetStarted />} />
        <Route path="/help/faqs" element={<Faq />} />
        <Route path="/external/collection/:collectionId" element={<ExternalCollectionDetail />} />
        <Route path="/external/collection/:collectionId/cleaned-data/new" element={<DataCleaning />} />
        <Route path="/external/collection/:collectionId/cleaned-data/:cleanedDataId" element={<CleaningDetail />} />

        <Route
          path="/workspaces/:workspaceId/repositories/:repositoryId/collect"
          element={<ProjectDetail />}
        />
        <Route
          path="/workspaces/:workspaceId/repositories/:repositoryId/collection/:planId/progress"
          element={<CollectionProgress />}
        />
        <Route
          path="/workspaces/:workspaceId/repositories/:repositoryId/collection/:planId/results"
          element={<CollectionResults />}
        />
        <Route
          path="/workspaces/:workspaceId/repositories/:repositoryId/collection/:collectionId"
          element={<CollectionDetail />}
        />
        <Route
          path="/workspaces/:workspaceId/repositories/:repositoryId/collection/:collectionId/cleaned-data/new"
          element={<DataCleaning />}
        />
        <Route
          path="/workspaces/:workspaceId/repositories/:repositoryId/collection/:collectionId/cleaned-data/:cleanedDataId"
          element={<CleaningDetail />}
        />
        
        {/* Analysis Routes */}
        <Route path="/analysis" element={<DatasetSelectionPage />} />
        <Route path="/analysis/new" element={<NewAnalysisPage />} />
        <Route path="/analysis/history" element={<AnalysisHistoryPage />} />
        <Route path="/analysis/new/csv" element={<DatasetSelectionPage />} />
        <Route path="/analysis/new/project" element={<ProjectSelectionPage />} />
        <Route path="/analysis/:datasetId/detail" element={<ProjectAnalysisDetailPage />} />
        <Route path="/analysis/:datasetId/metrics" element={<MetricsSelectionPage />} />
        <Route path="/analysis/:datasetId/chart/:analysisId" element={<SingleChartPage />} />
        <Route path="/analysis/:datasetId/dashboard" element={<AnalysisDashboardPage />} />
        <Route path="/analysis/datasets" element={<DatasetsPage />} />
        <Route path="/analysis/datasets/:datasetId" element={<DatasetDetailPage />} />
        <Route path="/analysis/datasets/:datasetId/analyze" element={<CreateAnalysisPage />} />
        <Route path="/analysis/datasets/:datasetId/results" element={<AnalysisResultsPage />} />

        {/* DevOps: Kanban Analysis */}
        <Route path="/kanban" element={<NewKanbanAnalysisPage />} />
        <Route path="/kanban/new" element={<NewKanbanAnalysisPage />} />
        <Route path="/kanban/new/live" element={<KanbanSourceSelectionPage />} />
        <Route path="/kanban/new/csv" element={<DatasetSelectionPage />} />
        <Route path="/kanban/history" element={<KanbanHistoryPage />} />
        <Route path="/kanban/jobs/:jobId/progress" element={<DevopsCollectionProgress />} />
        <Route path="/kanban/:datasetId/metrics" element={<MetricsSelectionPage />} />
        <Route path="/kanban/:datasetId/collect-metrics" element={<ComputeMetricsPage />} />
        <Route path="/kanban/:datasetId/dashboard" element={<AnalysisDashboardPage />} />
        <Route path="/kanban/:datasetId/chart/:analysisId" element={<SingleChartPage />} />

        {/* DevOps: CI/CD Analysis */}
        <Route path="/cicd" element={<NewCICDAnalysisPage />} />
        <Route path="/cicd/new" element={<NewCICDAnalysisPage />} />
        <Route path="/cicd/new/live" element={<CICDPipelineSelectionPage />} />
        <Route path="/cicd/new/csv" element={<DatasetSelectionPage />} />
        <Route path="/cicd/history" element={<CICDHistoryPage />} />
        <Route path="/cicd/jobs/:jobId/progress" element={<DevopsCollectionProgress />} />
        <Route path="/cicd/:datasetId/metrics" element={<MetricsSelectionPage />} />
        <Route path="/cicd/:datasetId/collect-metrics" element={<ComputeMetricsPage />} />
        <Route path="/cicd/:datasetId/dashboard" element={<AnalysisDashboardPage />} />
        <Route path="/cicd/:datasetId/chart/:analysisId" element={<SingleChartPage />} />

        <Route path="/profile" element={<Profile />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;
