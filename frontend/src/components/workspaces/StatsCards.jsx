import React from "react";
import { BarChart3, GitPullRequest, Package, Layers } from "lucide-react";

const StatsCards = ({ stats }) => {
  const statsConfig = [
    {
      label: "Analysis this month",
      value: stats.analysisThisMonth,
      icon: BarChart3,
      bgColor: "bg-purple-100",
      iconColor: "text-purple-600",
    },
    {
      label: "PRs/MRs collected",
      value: stats.prsCollected,
      icon: GitPullRequest,
      bgColor: "bg-red-100",
      iconColor: "text-red-600",
    },
    {
      label: "Quota API used",
      value: `${stats.quotaUsed}%`,
      icon: Package,
      bgColor: "bg-teal-100",
      iconColor: "text-teal-600",
    },
    {
      label: "Active Workspaces",
      value: stats.activeWorkspaces,
      icon: Layers,
      bgColor: "bg-orange-100",
      iconColor: "text-orange-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
      {statsConfig.map((stat, index) => (
        <div
          key={index}
          className="bg-white rounded-lg sm:rounded-xl border border-gray-200 p-3 sm:p-4 flex items-center justify-between"
        >
          <div className="min-w-0 flex-1">
            <p className="text-xs sm:text-sm text-gray-500 mb-1 truncate">
              {stat.label}
            </p>
            <p className="text-xl sm:text-2xl font-semibold text-gray-900">
              {stat.value}
            </p>
          </div>
          <div
            className={`w-10 h-10 sm:w-12 sm:h-12 ${stat.bgColor} rounded-full flex items-center justify-center shrink-0 ml-2`}
          >
            <stat.icon className={`w-5 h-5 sm:w-6 sm:h-6 ${stat.iconColor}`} />
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatsCards;
