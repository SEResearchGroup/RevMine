import React, { useState } from "react";
import { Mail, Lock, Chrome, Github, GitBranch } from "lucide-react";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = () => {
    console.log("Login:", { email, password });
  };

  const handleSocialLogin = (provider) => {
    console.log("Login with:", provider);
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <div className="flex-grow flex items-center justify-center px-4 py-12">
        <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
          <h2 className="text-3xl font-semibold text-blue-600 text-center mb-6">
            Login to your account
          </h2>

          {/* Boutons de connexion sociale */}
          <div className="space-y-3 mb-6">
            <button
              onClick={() => handleSocialLogin("Google")}
              className="w-full flex items-center justify-center gap-3 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              <Chrome className="w-5 h-5 text-red-500" />
              <span className="text-gray-700">Continue with Google</span>
            </button>

            <button
              onClick={() => handleSocialLogin("GitLab")}
              className="w-full flex items-center justify-center gap-3 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              <GitBranch className="w-5 h-5 text-orange-500" />
              <span className="text-gray-700">Continue with GitLab</span>
            </button>

            <button
              onClick={() => handleSocialLogin("GitHub")}
              className="w-full flex items-center justify-center gap-3 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              <Github className="w-5 h-5 text-gray-800" />
              <span className="text-gray-700">Continue with GitHub</span>
            </button>
          </div>

          {/* Séparateur OR */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">or</span>
            </div>
          </div>

          {/* Inputs */}
          <div className="space-y-4">
            <div>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
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
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                />
              </div>
            </div>

            <button
              onClick={handleSubmit}
              className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition font-medium"
            >
              Sign in
            </button>
          </div>

          {/* Lien d'inscription */}
          <p className="text-center text-gray-600 text-sm mt-6">
            Don't have an account?{" "}
            <a href="#" className="text-blue-600 hover:underline font-medium">
              Register here
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
