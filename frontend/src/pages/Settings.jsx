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
  Settings as SettingsIcon,
  Palette,
  Globe,
  HelpCircle,
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
      description: "Manage your profile and credentials",
      icon: Shield,
      color: "text-blue-600 bg-blue-50",
      items: [
        {
          icon: UserCheck,
          label: "Profile information",
          description: "Update your name, email, and position",
          action: () => navigate("/profile"),
          iconColor: "text-blue-600 bg-blue-50",
        },
        {
          icon: Lock,
          label: "Change password",
          description: "Update your account password",
          action: () => navigate("/profile"),
          iconColor: "text-blue-600 bg-blue-50",
        },
      ],
    },
    {
      title: "Permissions",
      description: "Tokens, workspaces and access control",
      icon: Key,
      color: "text-green-600 bg-green-50",
      items: [
        {
          icon: Key,
          label: "API tokens & workspaces",
          description: "Manage your GitHub/GitLab tokens and workspace connections",
          action: () => navigate("/workspaces"),
          iconColor: "text-green-600 bg-green-50",
        },
      ],
    },
    {
      title: "Notifications",
      description: "Control how you receive updates",
      icon: Bell,
      color: "text-amber-600 bg-amber-50",
      items: [
        {
          icon: Bell,
          label: "Notification preferences",
          description: "Choose what updates you receive",
          action: null,
          badge: "Coming soon",
          iconColor: "text-amber-600 bg-amber-50",
        },
      ],
    },
    {
      title: "Help & Support",
      description: "Guides and frequently asked questions",
      icon: HelpCircle,
      color: "text-blue-600 bg-blue-50",
      items: [
        {
          icon: HelpCircle,
          label: "Get started guide",
          description: "Learn how to use RevMine step by step",
          action: () => navigate("/help/get-started"),
          iconColor: "text-blue-600 bg-blue-50",
        },
        {
          icon: HelpCircle,
          label: "FAQs",
          description: "Frequently asked questions and answers",
          action: () => navigate("/help/faqs"),
          iconColor: "text-blue-600 bg-blue-50",
        },
      ],
    },
  ];

  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-sm shadow-blue-200">
              <SettingsIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
                Settings
              </h1>
              <p className="text-sm text-gray-500">
                Manage your account, security and preferences
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          {sections.map((section) => {
            const SectionIcon = section.icon;
            return (
              <div
                key={section.title}
                className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-sm transition-shadow duration-200"
              >
                {/* Section header */}
                <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-3">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center ${section.color}`}
                  >
                    <SectionIcon className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="font-semibold text-gray-800 text-sm">
                      {section.title}
                    </h2>
                    <p className="text-[11px] text-gray-400">{section.description}</p>
                  </div>
                </div>

                {/* Items */}
                <div className="divide-y divide-gray-50">
                  {section.items.map((item) => {
                    const ItemIcon = item.icon;
                    return (
                      <button
                        key={item.label}
                        onClick={item.action || undefined}
                        disabled={!item.action}
                        className={`w-full flex items-center justify-between px-5 py-4 text-left transition-colors duration-150 ${
                          item.action
                            ? "hover:bg-gray-50/80 cursor-pointer"
                            : "cursor-default opacity-60"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-9 h-9 rounded-lg flex items-center justify-center ${item.iconColor}`}
                          >
                            <ItemIcon className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-800">
                              {item.label}
                            </p>
                            <p className="text-xs text-gray-400 mt-0.5">
                              {item.description}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 ml-3">
                          {item.badge && (
                            <span className="text-[10px] font-medium px-2.5 py-1 bg-amber-50 text-amber-600 rounded-full border border-amber-100">
                              {item.badge}
                            </span>
                          )}
                          {item.action && (
                            <ChevronRight className="w-4 h-4 text-gray-300" />
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
            <div className="px-5 py-4 border-b border-red-100 flex items-center gap-3">
              <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center">
                <AlertTriangle className="w-4 h-4 text-red-500" />
              </div>
              <div>
                <h2 className="font-semibold text-red-700 text-sm">Danger Zone</h2>
                <p className="text-[11px] text-red-400">
                  Irreversible and destructive actions
                </p>
              </div>
            </div>
            <div className="px-5 py-5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-800">
                    Delete account
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                    Permanently delete your account and all associated data.
                    This action cannot be undone.
                  </p>
                </div>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="shrink-0 px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 hover:border-red-300 transition-colors"
                >
                  Delete account
                </button>
              </div>
              {deleteError && (
                <div className="mt-3 px-3 py-2 bg-red-50 border border-red-100 rounded-lg">
                  <p className="text-sm text-red-600">{deleteError}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 app-modal-backdrop z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-11 h-11 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900">Delete account?</h3>
                <p className="text-xs text-gray-500">This cannot be undone</p>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-6 leading-relaxed">
              This will permanently delete your account, all workspaces, and all
              collected data. This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleteLoading}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition shadow-sm"
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
