import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Mail,
  Lock,
  Chrome,
  Github,
  GitBranch,
  AlertCircle,
  User,
} from "lucide-react";
import { authService } from "../../services/api";

const Register = () => {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [sendUpdates, setSendUpdates] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  const handleSubmit = async () => {
    setError("");

    // Validation du mot de passe
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters long");
      return;
    }

    setLoading(true);

    try {
      await authService.register(
        email,
        password,
        sendUpdates,
        firstName,
        lastName
      );
      navigate("/login?registered=true");
    } catch (err) {
      setError(
        err.response?.data?.message ||
          "An error occurred while creating the account"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSocialRegister = (provider) => {
    console.log("Register with:", provider);
  };

  return (
    <div className="w-full flex items-center justify-center px-4 py-2">
      <div className="w-full max-w-md lg:max-w-lg xl:max-w-xl bg-white rounded-lg shadow-lg p-6 sm:p-8">
        <h2 className="text-xl sm:text-2xl font-bold text-[#008CFF] text-center mb-6 sm:mb-8">
          Create your account
        </h2>

        {error && (
          <div className="mb-4 sm:mb-6 p-3 sm:p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 sm:gap-3">
            <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-500 mt-0.5 flex-shrink-0" />
            <p className="text-xs sm:text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="flex flex-col sm:flex-row justify-around mb-6 sm:mb-8 gap-3 sm:gap-4">
          <button
            onClick={() => handleSocialRegister("Google")}
            className="w-full flex items-center justify-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <Chrome className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="text-sm sm:text-base text-gray-700">Google</span>
          </button>

          <button
            onClick={() => handleSocialRegister("GitLab")}
            className="w-full flex items-center justify-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <GitBranch className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="text-sm sm:text-base text-gray-700">GitLab</span>
          </button>

          <button
            onClick={() => handleSocialRegister("GitHub")}
            className="w-full flex items-center justify-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <Github className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="text-sm sm:text-base text-gray-700">GitHub</span>
          </button>
        </div>

        <div className="relative mb-6 sm:mb-8">
          <div className="relative flex justify-center">
            <span className="px-2 bg-white text-gray-500 text-sm sm:text-base">
              Or
            </span>
          </div>
        </div>

        <div className="space-y-4 sm:space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="First Name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Last Name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                  disabled={loading}
                />
              </div>
            </div>
          </div>

          <div>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                disabled={loading}
              />
            </div>
          </div>

          <div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                disabled={loading}
              />
            </div>
          </div>

          <div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
              <input
                type="password"
                placeholder="Confirm Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                disabled={loading}
              />
            </div>
          </div>

          <div className="flex items-start gap-2 sm:gap-3">
            <input
              type="checkbox"
              id="updates"
              checked={sendUpdates}
              onChange={(e) => setSendUpdates(e.target.checked)}
              className="mt-0.5 sm:mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 flex-shrink-0"
              disabled={loading}
            />
            <label
              htmlFor="updates"
              className="text-xs sm:text-sm text-gray-700"
            >
              Send me news and feature updates
            </label>
          </div>

          <div className="text-xs sm:text-sm text-gray-600">
            By selecting Create my account, I agree to the{" "}
            <a href="#" className="text-[#008CFF] hover:underline font-medium">
              Terms of Service
            </a>{" "}
            and{" "}
            <a href="#" className="text-[#008CFF] hover:underline font-medium">
              Master Services Agreement
            </a>
            , and acknowledge the{" "}
            <a href="#" className="text-[#008CFF] hover:underline font-medium">
              Privacy Policy
            </a>
            .
          </div>

          <button
            onClick={handleSubmit}
            disabled={
              loading ||
              !email ||
              !password ||
              !confirmPassword ||
              !firstName ||
              !lastName
            }
            className="w-full bg-[#008CFF] text-white py-2.5 sm:py-3 text-sm sm:text-base rounded-lg hover:bg-[#007ACC] transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Creating..." : "Create my account"}
          </button>
        </div>

        <p className="text-center text-gray-600 text-xs sm:text-sm mt-4 sm:mt-6">
          Already have an account?{" "}
          <a
            href="/login"
            className="text-[#008CFF] hover:underline font-medium"
          >
            Login
          </a>
        </p>
      </div>
    </div>
  );
};

export default Register;
