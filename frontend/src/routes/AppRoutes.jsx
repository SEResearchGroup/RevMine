import { Routes, Route } from "react-router-dom";
import Login from "../pages/auth/Login";
import Dashboard from "../pages/dashboard/Dashboard";
import ProtectedRoute from "./ProtectedRoute";
import LayoutAuth from "../components/layout/LayoutAuth";
import LayoutPublic from "../components/layout/LayoutPublic";

const AppRoutes = () => {
  return (
    <Routes>

      <Route element={<LayoutPublic />}>
        <Route path="/login" element={<Login />} />
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
      </Route>

    </Routes>
  );
};

export default AppRoutes;
