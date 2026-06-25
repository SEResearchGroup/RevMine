import React, { useState, useEffect } from "react";
import {
  ChevronDown,
  ChevronRight,
  Home,
  Database,
  Grid3x3,
  FolderOpen,
  BarChart3,
  MessageSquareText,
  Settings,
  HelpCircle,
  Menu,
  Kanban,
  Workflow,
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
    kanbanAnalysis: false,
    cicdAnalysis: false,
    settings: false,
    help: false,
  });

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setIsOpen(false);
      } else {
        setIsOpen(true);
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

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
      path: "/",
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
      subItems: ["Manual Collect", "Intelligent collect"],
    },
    {
      id: "dataManagement",
      icon: FolderOpen,
      label: "Data Management",
      subItems: ["Export collect results", "Import dataset", "Data Cleaning"],
    },
    {
      id: "analysis",
      icon: BarChart3,
      label: "Analysis",
      subItems: ["History", "New Analysis"],
    },
    {
      id: "qualitative",
      icon: MessageSquareText,
      label: "Qualitative Analysis",
      path: "/qualitative",
    },
    {
      id: "kanbanAnalysis",
      icon: Kanban,
      label: "Kanban Analysis",
      subItems: ["New Kanban Analysis", "Kanban History"],
    },
    {
      id: "cicdAnalysis",
      icon: Workflow,
      label: "CI/CD Analysis",
      subItems: ["New CI/CD Analysis", "CI/CD History"],
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
      subItems: ["Get started",  "FAQs"],
    },
  ];

  const handleSubItemClick = (e, subItem) => {
    e.preventDefault();
    switch (subItem) {
      case "Workspaces":
        navigate("/workspaces");
        break;
      case "Projects":
        navigate("/projects");
        break;
      case "Manual Collect":
        navigate("/collection/manual");
        break;
      case "Intelligent collect":
        navigate("/collection/intelligent");
        break;
      case "Import dataset":
        navigate("/collection/import");
        break;
      case "Data Cleaning":
        navigate("/data-cleaning");
        break;
      case "New Analysis":
        navigate("/analysis/new");
        break;
      case "History":
        navigate("/analysis/history");
        break;
      case "New Kanban Analysis":
        navigate("/kanban/new");
        break;
      case "Kanban History":
        navigate("/kanban/history");
        break;
      case "New CI/CD Analysis":
        navigate("/cicd/new");
        break;
      case "CI/CD History":
        navigate("/cicd/history");
        break;
      case "Export collect results":
        navigate("/data-cleaning");
        break;
      case "Security & Permissions":
        navigate("/settings");
        break;
      case "Profile":
        navigate("/profile");
        break;
      case "Get started":
        navigate("/help/get-started");
        break;
      case "FAQs":
        navigate("/help/faqs");
        break;
      default:
        break;
    }
  };

  return (
    <div
      className={`${
        isOpen ? "w-64" : "w-16"
      } h-screen bg-white border-r border-gray-200 transition-all duration-300 flex flex-col`}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        {isOpen && (
          <div
            className="flex items-center gap-2 cursor-pointer"
            onClick={() => {
              navigate("/");
            }}
          >
            <img src={logo} alt="RevMine Logo" className="w-40" />
          </div>
        )}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-1 hover:bg-gray-100 rounded transition cursor-pointer"
        >
          <Menu className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Menu items */}
      <div className="flex-1 overflow-y-auto py-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isExpanded = expandedSections[item.id];
          const hasSubItems = item.subItems && item.subItems.length > 0;
          return (
            <div key={item.id} className="mb-1">
              <button
                onClick={() => item.path ? navigate(item.path) : toggleSection(item.id)}
                className={`w-full flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 transition group cursor-pointer`}
                title={!isOpen ? item.label : ""}
              >

                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 text-gray-600" />
                  {isOpen && (
                    <span className="text-gray-700 font-medium">
                      {item.label}
                    </span>
                  )}
                </div>
                {isOpen && hasSubItems && (
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
                      onClick={(e) => handleSubItemClick(e, subItem)}
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
