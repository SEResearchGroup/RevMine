import React, { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Home,
  Database,
  Grid3x3,
  FolderOpen,
  BarChart3,
  Settings,
  HelpCircle,
  Menu,
} from "lucide-react";
import logo from "../../assets/images/logo_v1.png";
import { useNavigate } from "react-router-dom";
const Sidebar = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(true);
  const [expandedSections, setExpandedSections] = useState({
    home: false,
    dataSources: false,
    collection: false,
    dataManagement: false,
    analysis: false,
    settings: false,
    help: false,
  });

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const menuItems = [
    {
      id: "home",
      icon: Home,
      label: "Home",
      subItems: ["Getting started guide"],
    },
    {
      id: "dataSources",
      icon: Database,
      label: "Data Sources",
      subItems: ["Workspaces", "Projects"],
    },
    {
      id: "collection",
      icon: Grid3x3,
      label: "Collection",
      subItems: ["Manual Collect", "Intelligent collect", "Plan validation"],
    },
    {
      id: "dataManagement",
      icon: FolderOpen,
      label: "Data Management",
      subItems: ["Export collect results", "Import dataset", "data cleaning"],
    },
    {
      id: "analysis",
      icon: BarChart3,
      label: "Analysis",
      subItems: ["Insights selection", "Intelligent insight", "visualizations"],
    },
    {
      id: "settings",
      icon: Settings,
      label: "Settings",
      subItems: ["Security & Permissions", "Profile"],
    },
    {
      id: "help",
      icon: HelpCircle,
      label: "Help",
      subItems: ["FAQs", "Contact Support"],
    },
  ];

  return (
    <div
      className={`${
        isOpen ? "w-64" : "w-16"
      } h-screen bg-white border-r border-gray-200 transition-all duration-300 flex flex-col`}
    >
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        {isOpen && (
          <div
            className="flex items-center gap-2 cursor-pointer"
            onClick={() => {
              navigate("/");
            }}
          >
            <img src={logo} alt="RevMine Logo" />
          </div>
        )}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-1 hover:bg-gray-100 rounded transition"
        >
          <Menu className="w-5 h-5 text-gray-600" />
        </button>
      </div>{" "}
      <div className="flex-1 overflow-y-auto py-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isExpanded = expandedSections[item.id];

          return (
            <div key={item.id} className="mb-1">
              <button
                onClick={() => toggleSection(item.id)}
                className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 transition group"
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 text-gray-600" />
                  {isOpen && (
                    <span className="text-gray-700 font-medium">
                      {item.label}
                    </span>
                  )}
                </div>
                {isOpen && (
                  <div>
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                )}
              </button>

              {isOpen && isExpanded && (
                <div className="bg-gray-50">
                  {item.subItems.map((subItem, idx) => (
                    <a
                      key={idx}
                      href="#"
                      className="flex items-center gap-2 px-4 py-2 pl-12 text-sm text-gray-600 hover:text-blue-600 hover:bg-gray-100 transition"
                    >
                      <span className="text-gray-400">›</span>
                      <span>{subItem}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Sidebar;
