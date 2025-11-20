import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AuthContext from "./AuthContext";
import { getToken, removeToken, isTokenExpired, setToken } from "../utils/jwt";

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const checkToken = () => {
      const token = getToken();

      if (token && !isTokenExpired(token)) {
        const payload = JSON.parse(atob(token.split(".")[1]));
        setUser(payload.user || payload);
        setIsAuthenticated(true);
      } else {
        removeToken();
        setUser(null);
        setIsAuthenticated(false);
      }

      setLoading(false);
    };

    checkToken();
  }, []);

  const login = (token) => {
    setToken(token);
    const payload = JSON.parse(atob(token.split(".")[1]));
    setUser(payload.user || payload);
    setIsAuthenticated(true);
    navigate("/workspaces");
  };

  const logout = () => {
    removeToken();
    setIsAuthenticated(false);
    setUser(null);
    navigate("/login");
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, loading  }}>
      {children}
    </AuthContext.Provider>
  );
};
