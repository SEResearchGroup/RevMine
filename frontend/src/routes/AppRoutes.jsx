import { Routes, Route } from "react-router-dom";
import Login from "../pages/auth/Login";
import Register from "../pages/auth/Register";
import Dashboard from "../pages/dashboard/Dashboard";
import Workspaces from "../pages/workspaces/Workspaces";
import ProtectedRoute from "./ProtectedRoute";
import LayoutAuth from "../components/layout/LayoutAuth";
import LayoutPublic from "../components/layout/LayoutPublic";
import Projects from "../pages/projects/Projects";
import {
  GitHubCallback,
  GitLabCallback,
  GoogleCallback 
} from "../pages/auth/OAuthCallbacks";
import Profile from "../pages/profile/Profile";

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

        <Route path="/profile" element={<Profile />} />
      </Route>
    </Routes>
  );
};

export default AppRoutes;
