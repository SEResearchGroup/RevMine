import React, { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";

// GitHub Callback Component
export const GitHubCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const { login } = useAuth();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const handleCallback = async () => {
      const code = searchParams.get("code");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError("GitHub authentication was cancelled or failed");
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      if (!code) {
        setError("No authorization code received");
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      try {
        const response = await fetch(
          `http://localhost:8000/api/auth/oauth/github/callback?code=${code}`,
          {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.error || "Failed to authenticate with GitHub"
          );
        }

        const data = await response.json();
        login(data.access, data.refresh);
        navigate("/workspaces");
      } catch (err) {
        console.error("GitHub callback error:", err);
        setError(err.message || "Authentication failed");
      }
    };

    handleCallback();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
          <div className="flex items-center gap-3 text-red-600 mb-4">
            <AlertCircle className="w-6 h-6" />
            <h2 className="text-xl font-semibold">Authentication Error</h2>
          </div>
          <p className="text-gray-700 mb-4">{error}</p>
          <p className="text-sm text-gray-500">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full text-center">
        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          Authenticating with GitHub
        </h2>
        <p className="text-gray-600">Please wait...</p>
      </div>
    </div>
  );
};

export const GitLabCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const { login } = useAuth();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const handleCallback = async () => {
      const code = searchParams.get("code");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError("GitLab authentication was cancelled or failed");
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      if (!code) {
        setError("No authorization code received");
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      try {
        const response = await fetch(
          `http://localhost:8000/api/auth/oauth/gitlab/callback?code=${code}`,
          {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.error || "Failed to authenticate with GitLab"
          );
        }

        const data = await response.json();
        login(data.access, data.refresh);
        navigate("/workspaces");
      } catch (err) {
        console.error("GitLab callback error:", err);
        setError(err.message || "Authentication failed");
      }
    };

    handleCallback();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
          <div className="flex items-center gap-3 text-red-600 mb-4">
            <AlertCircle className="w-6 h-6" />
            <h2 className="text-xl font-semibold">Authentication Error</h2>
          </div>
          <p className="text-gray-700 mb-4">{error}</p>
          <p className="text-sm text-gray-500">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full text-center">
        <Loader2 className="w-12 h-12 text-orange-500 animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          Authenticating with GitLab
        </h2>
        <p className="text-gray-600">Please wait...</p>
      </div>
    </div>
  );
};

export const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const { login } = useAuth();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const handleCallback = async () => {
      const code = searchParams.get("code");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError("Google authentication was cancelled or failed");
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      if (!code) {
        setError("No authorization code received");
        setTimeout(() => navigate("/login"), 3000);
        return;
      }

      try {
        const response = await fetch(
          `http://localhost:8000/api/auth/oauth/google/callback?code=${code}`,
          {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.error || "Failed to authenticate with Google"
          );
        }

        const data = await response.json();
        login(data.access, data.refresh);
        navigate("/workspaces");
      } catch (err) {
        console.error("Google callback error:", err);
        setError(err.message || "Authentication failed");
      }
    };

    handleCallback();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full">
          <div className="flex items-center gap-3 text-red-600 mb-4">
            <AlertCircle className="w-6 h-6" />
            <h2 className="text-xl font-semibold">Authentication Error</h2>
          </div>
          <p className="text-gray-700 mb-4">{error}</p>
          <p className="text-sm text-gray-500">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full text-center">
        <Loader2 className="w-12 h-12 text-red-500 animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          Authenticating with Google
        </h2>
        <p className="text-gray-600">Please wait...</p>
      </div>
    </div>
  );
};
