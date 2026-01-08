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
import {
  GitHubCallback,
  GitLabCallback,
  GoogleCallback,
} from "../pages/auth/OAuthCallbacks";
import Profile from "../pages/profile/Profile";
import AnalysisPage from "../pages/Analysis/AnalysisPage";
import AnalysisHistoryPage from "../pages/Analysis/AnalysisHistoryPage";

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
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/analysis/history" element={<AnalysisHistoryPage />} />

        <Route path="/profile" element={<Profile />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;
