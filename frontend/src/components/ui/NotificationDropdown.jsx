import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  Check,
  CheckCheck,
  Trash2,
  Database,
  BarChart3,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Play,
  ExternalLink,
} from "lucide-react";
import { useNotifications } from "../../hooks/useNotifications";

const ICON_MAP = {
  collection_started: { icon: Play, color: "text-blue-500", bg: "bg-blue-50" },
  collection_completed: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-50" },
  collection_failed: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-50" },
  analysis_requested: { icon: Loader2, color: "text-yellow-500", bg: "bg-yellow-50" },
  analysis_completed: { icon: BarChart3, color: "text-purple-500", bg: "bg-purple-50" },
  devops_kanban_started: { icon: Play, color: "text-blue-500", bg: "bg-blue-50" },
  devops_kanban_completed: { icon: CheckCircle2, color: "text-blue-600", bg: "bg-blue-50" },
  devops_kanban_failed: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-50" },
  devops_cicd_started: { icon: Play, color: "text-green-500", bg: "bg-green-50" },
  devops_cicd_completed: { icon: CheckCircle2, color: "text-green-600", bg: "bg-green-50" },
  devops_cicd_failed: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-50" },
};

const DEFAULT_ICON = { icon: Database, color: "text-gray-500", bg: "bg-gray-50" };

const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString();
};

const NotificationDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const {
    notifications,
    unreadCount,
    loading,
    markAsRead,
    markAllAsRead,
    deleteNotification,
  } = useNotifications();

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 hover:bg-gray-100 rounded-lg transition relative"
      >
        <Bell className="w-5 h-5 text-blue-500" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-125 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-blue-500 hover:text-blue-700 flex items-center gap-1 transition"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div className="overflow-y-auto flex-1">
            {loading && notifications.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-gray-400">
                <Bell className="w-10 h-10 mb-2 opacity-30" />
                <p className="text-sm">No notifications yet</p>
              </div>
            ) : (
              notifications.map((notif) => {
                const iconConfig = ICON_MAP[notif.type] || DEFAULT_ICON;
                const Icon = iconConfig.icon;
                const hasLink = !!notif.link_url;

                const handleClick = () => {
                  if (!notif.read) markAsRead(notif.id);
                  if (hasLink) {
                    setIsOpen(false);
                    navigate(`/${notif.link_url}`);
                  }
                };

                return (
                  <div
                    key={notif.id}
                    className={`flex items-start gap-3 px-4 py-3 border-b border-gray-50 hover:bg-gray-50 transition cursor-pointer ${
                      !notif.read ? "bg-blue-50/40" : ""
                    }`}
                    onClick={handleClick}
                  >
                    <div
                      className={`shrink-0 w-9 h-9 rounded-full ${iconConfig.bg} flex items-center justify-center mt-0.5`}
                    >
                      <Icon className={`w-4.5 h-4.5 ${iconConfig.color}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className={`text-sm ${!notif.read ? "font-semibold text-gray-900" : "text-gray-700"} flex items-center gap-1`}>
                          {notif.title}
                          {hasLink && <ExternalLink className="w-3 h-3 text-gray-400 shrink-0" />}
                        </p>
                        <div className="flex items-center gap-1 ml-2 shrink-0">
                          {!notif.read && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                markAsRead(notif.id);
                              }}
                              className="p-1 hover:bg-blue-100 rounded transition"
                              title="Mark as read"
                            >
                              <Check className="w-3.5 h-3.5 text-blue-500" />
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteNotification(notif.id);
                            }}
                            className="p-1 hover:bg-red-100 rounded transition"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5 text-gray-400 hover:text-red-500" />
                          </button>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">
                        {notif.message}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {formatTime(notif.created_at)}
                      </p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationDropdown;
