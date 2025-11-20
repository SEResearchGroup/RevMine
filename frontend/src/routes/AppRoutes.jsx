import { Routes, Route } from "react-router-dom";
import Login from "../pages/auth/Login";
import Register from "../pages/auth/Register";
import Dashboard from "../pages/dashboard/Dashboard";
import Workspaces from "../pages/workspaces/Workspaces";
import ProtectedRoute from "./ProtectedRoute";
import LayoutAuth from "../components/layout/LayoutAuth";
import LayoutPublic from "../components/layout/LayoutPublic";

const AppRoutes = () => {
  return (
    <Routes>

      <Route element={<LayoutPublic />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      <Route
        element={
          <ProtectedRoute>
            <LayoutAuth />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/workspaces" element={<Workspaces />} />
      </Route>

    </Routes>
  );
};

export default AppRoutes;
