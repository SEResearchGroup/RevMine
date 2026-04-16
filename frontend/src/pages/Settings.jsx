import React, { useState } from "react";
import {
  Shield,
  Key,
  Bell,
  Trash2,
  AlertTriangle,
  ChevronRight,
  Lock,
  UserCheck,
  Eye,
  EyeOff,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { authService } from "../services/api";

const Settings = () => {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const handleDeleteAccount = async () => {
    setDeleteLoading(true);
    setDeleteError("");
    try {
      await authService.deleteAccount();
      navigate("/login");
    } catch (err) {
      setDeleteError(
        err.response?.data?.error || "Failed to delete account. Please try again."
      );
    } finally {
      setDeleteLoading(false);
    }
  };

  const sections = [
    {
      title: "Account & Security",
      icon: Shield,
      items: [
        {
          icon: UserCheck,
          label: "Profile information",
          description: "Update your name, email, and position",
          action: () => navigate("/profile"),
        },
        {
          icon: Lock,
          label: "Change password",
          description: "Update your account password",
          action: () => navigate("/profile"),
        },
      ],
    },
    {
      title: "Permissions",
      icon: Key,
      items: [
        {
          icon: Key,
          label: "API tokens & workspaces",
          description: "Manage your GitHub/GitLab tokens and workspace connections",
          action: () => navigate("/workspaces"),
        },
      ],
    },
    {
      title: "Notifications",
      icon: Bell,
      items: [
        {
          icon: Bell,
          label: "Notification preferences",
          description: "Choose what updates you receive",
          action: null,
          badge: "Coming soon",
        },
      ],
    },
  ];

  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-xl sm:text-2xl font-semibold text-gray-800 mb-6">
          <span className="text-blue-600">Settings</span>
        </h1>

        <div className="space-y-6">
          {sections.map((section) => {
            const SectionIcon = section.icon;
            return (
              <div
                key={section.title}
                className="bg-white rounded-xl border border-gray-200 overflow-hidden"
              >
                <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
                  <SectionIcon className="w-4 h-4 text-blue-600" />
                  <h2 className="font-semibold text-gray-800 text-sm">
                    {section.title}
                  </h2>
                </div>
                <div className="divide-y divide-gray-100">
                  {section.items.map((item) => {
                    const ItemIcon = item.icon;
                    return (
                      <button
                        key={item.label}
                        onClick={item.action || undefined}
                        disabled={!item.action}
                        className={`w-full flex items-center justify-between px-5 py-4 text-left transition ${
                          item.action
                            ? "hover:bg-gray-50 cursor-pointer"
                            : "cursor-default opacity-70"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                            <ItemIcon className="w-4 h-4 text-gray-600" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-800">
                              {item.label}
                            </p>
                            <p className="text-xs text-gray-500">
                              {item.description}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {item.badge && (
                            <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">
                              {item.badge}
                            </span>
                          )}
                          {item.action && (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}

          {/* Danger Zone */}
          <div className="bg-white rounded-xl border border-red-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-red-100 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <h2 className="font-semibold text-red-700 text-sm">Danger Zone</h2>
            </div>
            <div className="px-5 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">Delete account</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Permanently delete your account and all associated data. This
                    action cannot be undone.
                  </p>
                </div>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="ml-4 shrink-0 px-4 py-2 border border-red-300 text-red-600 rounded-lg text-sm hover:bg-red-50 transition"
                >
                  Delete account
                </button>
              </div>
              {deleteError && (
                <p className="mt-3 text-sm text-red-600">{deleteError}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <h3 className="font-semibold text-gray-800">Delete account?</h3>
            </div>
            <p className="text-sm text-gray-600 mb-6">
              This will permanently delete your account, all workspaces, and all
              collected data. This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleteLoading}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {deleteLoading ? "Deleting..." : "Delete permanently"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
