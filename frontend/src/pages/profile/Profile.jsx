import React, { useEffect, useState } from "react";
import {
  Mail,
  Lock,
  User,
  Briefcase,
  Save,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { authService } from "../../services/api";

const Profile = () => {
  const [userInfo, setUserInfo] = useState(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [position, setPosition] = useState("");
  const [customPosition, setCustomPosition] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const response = await authService.getUserInfo();
        setUserInfo(response.data);
        setFirstName(response.data.first_name || "");
        setLastName(response.data.last_name || "");
        setEmail(response.data.email || "");
        setPosition(response.data.position || "");
        if (
          response.data.position &&
          ![
            "",
            "skip",
            "business-owner",
            "product-manager",
            "data-analyst",
            "team-lead",
            "engineering-manager",
            "tech-lead",
            "software-engineer",
            "devops-engineer",
            "project-manager",
            "scrum-master",
            "cto",
          ].includes(response.data.position)
        ) {
          setPosition("other");
          setCustomPosition(response.data.position);
        }
      } catch (error) {
        console.error("Failed to fetch user info:", error);
        setError("Failed to load user information");
      }
    };
    fetchUserInfo();
  }, []);

  const handleSubmit = async () => {
    setError("");
    setSuccess("");

    if (newPassword) {
      if (!currentPassword) {
        setError("Current password is required to set a new password");
        return;
      }
      if (newPassword !== confirmPassword) {
        setError("New passwords do not match");
        return;
      }
      if (newPassword.length < 6) {
        setError("New password must be at least 6 characters long");
        return;
      }
    }

    setLoading(true);

    try {
      const finalPosition =
        position === "other"
          ? customPosition
          : position === "skip"
          ? ""
          : position;

      const updateData = {
        first_name: firstName,
        last_name: lastName,
        email: email,
        position: finalPosition,
      };

      if (newPassword) {
        updateData.current_password = currentPassword;
        updateData.new_password = newPassword;
      }

      await authService.updateProfile(updateData);
      if(newPassword){
        await authService.changePassword(currentPassword, newPassword, confirmPassword);
      }
      setSuccess("Profile updated successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");

      // Refresh user info
      const response = await authService.getUserInfo();
      setUserInfo(response.data);
    } catch (err) {
      setError(
        err.response?.data?.message ||
          "An error occurred while updating the profile"
      );
    } finally {
      setLoading(false);
    }
  };

  if (!userInfo) {
    return (
      <div className="w-full flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-2xl bg-white rounded-lg shadow-lg p-8">
          <p className="text-center text-gray-600">
            Loading user information...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full p-6 sm:p-8">
      <h2 className="text-xl sm:text-2xl font-bold text-[#008CFF] text-center mb-6 sm:mb-8">
        My Profile
      </h2>

      {error && (
        <div className="mb-4 sm:mb-6 p-3 sm:p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 sm:gap-3">
          <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs sm:text-sm text-red-700">{error}</p>
        </div>
      )}

      {success && (
        <div className="mb-4 sm:mb-6 p-3 sm:p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-2 sm:gap-3">
          <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-green-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs sm:text-sm text-green-700">{success}</p>
        </div>
      )}

      <div className="space-y-4 sm:space-y-6">
        <div className="border-b pb-4">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">
            Personal Information
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                First Name
              </label>
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
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Last Name
              </label>
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

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
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
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Position
            </label>
            <div className="relative">
              <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400 pointer-events-none z-10" />
              <select
                value={position}
                onChange={(e) => {
                  setPosition(e.target.value);
                  if (e.target.value !== "other") setCustomPosition("");
                }}
                className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50 appearance-none"
                disabled={loading}
              >
                <option value="">Select your position (optional)</option>
                <option value="business-owner">Business Owner</option>
                <option value="product-manager">Product Manager</option>
                <option value="data-analyst">Data Analyst</option>
                <option value="team-lead">Team Lead</option>
                <option value="engineering-manager">Engineering Manager</option>
                <option value="tech-lead">Tech Lead</option>
                <option value="software-engineer">Software Engineer</option>
                <option value="devops-engineer">DevOps Engineer</option>
                <option value="project-manager">Project Manager</option>
                <option value="scrum-master">Scrum Master</option>
                <option value="cto">CTO</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          {position === "other" && (
            <div className="mt-4">
              <input
                type="text"
                placeholder="Please specify your position"
                value={customPosition}
                onChange={(e) => setCustomPosition(e.target.value)}
                className="w-full px-3 sm:px-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                disabled={loading}
              />
            </div>
          )}
        </div>

        <div className="border-b pb-4">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">
            Change Password
          </h3>
          <p className="text-xs sm:text-sm text-gray-600 mb-4">
            Leave blank if you don't want to change your password
          </p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Current Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
                <input
                  type="password"
                  placeholder="Current Password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                New Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
                <input
                  type="password"
                  placeholder="New Password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Confirm New Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
                <input
                  type="password"
                  placeholder="Confirm New Password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full pl-9 sm:pl-10 pr-3 sm:pr-4 py-2.5 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50"
                  disabled={loading}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="pt-2">
          <div className="text-xs sm:text-sm text-gray-600 mb-4">
            <span className="font-semibold">Member since:</span>{" "}
            {new Date(userInfo.date_joined).toLocaleDateString()}
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading || !firstName || !lastName || !email}
            className="w-full bg-[#008CFF] text-white py-2.5 sm:py-3 text-sm sm:text-base rounded-lg hover:bg-[#007ACC] transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Save className="w-4 h-4 sm:w-5 sm:h-5" />
            {loading ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Profile;
