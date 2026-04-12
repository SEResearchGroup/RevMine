import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import AuthContext from "./AuthContext";
import {
  getToken,
  isTokenExpired,
  setToken,
  setRefreshToken,
  getRefreshToken,
  clearTokens,
  isTokenExpiringSoon
} from "../utils/jwt";
import { authApi } from "../services/api";

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();
  const logout = () => {
    clearTokens();
    setIsAuthenticated(false);
    setUser(null);
    navigate("/login");
  };

  useEffect(() => {
    const checkToken = async () => {
      const token = getToken();
      const refreshToken = getRefreshToken();

      if (token && !isTokenExpired(token)) {
        const payload = JSON.parse(atob(token.split(".")[1]));
        setUser(payload.user || payload);
        setIsAuthenticated(true);
      } else if (refreshToken && !isTokenExpired(refreshToken)) {
        try {
          const response = await authApi.post("/refresh", {
            refresh: refreshToken
          });
          const { access } = response.data;
          setToken(access);

          const payload = JSON.parse(atob(access.split(".")[1]));
          setUser(payload.user || payload);
          setIsAuthenticated(true);
        } catch (error) {
          console.error("Error refreshing token:", error);
          clearTokens();
          setUser(null);
          setIsAuthenticated(false);
        }
      } else {
        clearTokens();
        setUser(null);
        setIsAuthenticated(false);
      }

      setLoading(false);
    };

    checkToken();
  }, []);


  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(async () => {
      const token = getToken();
      const refreshToken = getRefreshToken();

      if (token && isTokenExpiringSoon(token) && refreshToken) {
        try {
          const response = await authApi.post("/refresh", {
            refresh: refreshToken
          });
          const { access } = response.data;
          setToken(access);

          const payload = JSON.parse(atob(access.split(".")[1]));
          setUser(payload.user || payload);
        } catch (error) {
          console.error("Proactive token refresh failed:", error);
          logout();
        }
      }
    }, 4 * 60 * 1000);

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const login = (accessToken, refreshToken) => {
    setToken(accessToken);
    setRefreshToken(refreshToken);

    const payload = JSON.parse(atob(accessToken.split(".")[1]));
    setUser(payload.user || payload);
    setIsAuthenticated(true);
    navigate("/workspaces");
  };



  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
