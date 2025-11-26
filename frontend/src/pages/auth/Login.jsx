import React, { useState, useEffect } from "react";
import {
  Mail,
  Lock,
  Chrome,
  Github,
  GitBranch,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { authService } from "../../services/api";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSuccess, setShowSuccess] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();
  
  const handleSocialLogin = (provider) => {
    console.log("Login with:", provider);
  };

  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (searchParams.get("registered") === "true") {
      setShowSuccess(true);
      const timer = setTimeout(() => {
        setShowSuccess(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    
    try {
      const response = await authService.login(email, password);
      login(response.data.access);
      navigate("/workspaces");
    } catch (err) {
      setError(err.response?.data?.message || "Incorrect email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full flex items-center justify-center px-4 py-12">
      <div className="w-[45%] bg-white rounded-lg shadow-lg p-8">
        <h2 className="text-2xl font-bold text-[#008CFF] text-center mb-8">
          Login to your account
        </h2>

        {showSuccess && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
            <p className="text-sm text-green-700">
              Your account has been created successfully! Please log in.
            </p>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="flex flex-row justify-around mb-8 gap-4">
          <button
            type="button"
            onClick={() => handleSocialLogin("Google")}
            className="w-full flex items-center justify-center gap-3 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <Chrome className="w-5 h-5" />
            <span className="text-gray-700">Google</span>
          </button>

          <button
            type="button"
            onClick={() => handleSocialLogin("GitLab")}
            className="w-full flex items-center justify-center gap-3 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <GitBranch className="w-5 h-5" />
            <span className="text-gray-700">GitLab</span>
          </button>

          <button
            type="button"
            onClick={() => handleSocialLogin("GitHub")}
            className="w-full flex items-center justify-center gap-3 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <Github className="w-5 h-5" />
            <span className="text-gray-700">GitHub</span>
          </button>
        </div>

        <div className="relative mb-8">
          <div className="relative flex justify-center">
            <span className="px-2 bg-white text-gray-500">Or</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                disabled={loading}
                required
              />
            </div>
          </div>

          <div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                disabled={loading}
                required
              />
            </div>
            <div className="text-right mt-2">
              <a
                href="#"
                className="text-[#008CFF] hover:underline text-sm font-medium"
              >
                Forgot password?
              </a>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full bg-[#008CFF] text-white py-2 rounded-lg hover:bg-[#007ACC] transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Logging in..." : "Sign In"}
          </button>
        </form>

        <p className="text-center text-gray-600 text-sm mt-6">
          Don't have an account?{" "}
          <a
            href="/register"
            className="text-[#008CFF] hover:underline font-medium"
          >
            Register here
          </a>
        </p>
      </div>
    </div>
  );
};

export default Login;