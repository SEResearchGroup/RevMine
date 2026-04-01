import { Routes, Route } from "react-router-dom";
import Login from "../pages/auth/Login";
import Register from "../pages/auth/Register";
import Dashboard from "../pages/dashboard/Dashboard";
import Workspaces from "../pages/workspaces/Workspaces";
import ProtectedRoute from "./ProtectedRoute";
import LayoutAuth from "../components/layout/LayoutAuth";
import LayoutPublic from "../components/layout/LayoutPublic";
import Projects from "../pages/projects/Projects";
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

// Analysis Pages
import DatasetSelectionPage from "../pages/Analysis/DatasetSelectionPage";
import MetricsSelectionPage from "../pages/Analysis/MetricsSelectionPage";
import AnalysisDashboardPage from "../pages/Analysis/AnalysisDashboardPage";

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
        <Route path="/data-cleaning" element={<DataCleaningList />} />
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
        <Route path="/analysis/:datasetId/metrics" element={<MetricsSelectionPage />} />
        <Route path="/analysis/:datasetId/dashboard" element={<AnalysisDashboardPage />} />

        <Route path="/profile" element={<Profile />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;