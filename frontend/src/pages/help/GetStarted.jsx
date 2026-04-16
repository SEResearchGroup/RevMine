import React from "react";
import {
  GitBranch,
  Database,
  BarChart3,
  Key,
  FolderOpen,
  BookOpen,
  ArrowRight,
  CheckCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

const steps = [
  {
    step: 1,
    icon: Key,
    title: "Connect your repository host",
    description:
      "Create a Workspace by providing your GitHub or GitLab personal access token. RevMine will validate the connection and list your repositories.",
    color: "bg-blue-100 text-blue-600",
  },
  {
    step: 2,
    icon: FolderOpen,
    title: "Import projects",
    description:
      "Select the repositories you want to track. They become Projects inside your Workspace — each project is an independent unit of analysis.",
    color: "bg-purple-100 text-purple-600",
  },
  {
    step: 3,
    icon: Database,
    title: "Collect data",
    description:
      "Launch a collection plan for any project. Choose metrics (commits, pull requests, issues, etc.), set date ranges and branch filters.",
    color: "bg-green-100 text-green-600",
  },
  {
    step: 4,
    icon: BarChart3,
    title: "Analyse & export",
    description:
      "Explore interactive charts, detect trends, identify top contributors, and export clean CSV datasets for further analysis.",
    color: "bg-orange-100 text-orange-600",
  },
];

const concepts = [
  {
    icon: GitBranch,
    term: "Workspace",
    definition:
      "A Workspace is a secure container that holds the connection to one GitHub or GitLab account. It stores your encrypted access token and lists all repositories available under that account.",
  },
  {
    icon: FolderOpen,
    term: "Project",
    definition:
      "A Project is an individual repository imported into a Workspace. It is the unit on which you run collection plans, clean data, and perform analyses.",
  },
  {
    icon: Key,
    term: "GitHub / GitLab Token",
    definition:
      "A personal access token (PAT) is a credentials string generated from your GitHub or GitLab account settings. It grants RevMine read-only access to repository metadata, commits, and pull requests. Your token is stored encrypted and never exposed in plain text.",
  },
  {
    icon: Database,
    term: "Collection plan",
    definition:
      "A collection plan is a configured job that fetches specific metrics from a project for a chosen time period and branch. Each run produces a dataset ready for cleaning and analysis.",
  },
];

const GetStarted = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-4xl mx-auto">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-sm font-medium mb-4">
            <BookOpen className="w-4 h-4" />
            Get started
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
            Welcome to <span className="text-blue-600">RevMine</span>
          </h1>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto">
            RevMine is a software engineering analytics platform that transforms raw
            repository activity into actionable insights — from commits and pull
            requests to contributor trends and effort estimations.
          </p>
          <div className="flex justify-center gap-4 mt-6">
            <button
              onClick={() => navigate("/workspaces")}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm font-medium"
            >
              Create your first workspace
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => navigate("/help/faqs")}
              className="px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium"
            >
              Read FAQs
            </button>
          </div>
        </div>

        {/* How it works */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold text-gray-800 mb-6 text-center">
            How it works
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {steps.map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.step}
                  className="bg-white rounded-xl border border-gray-200 p-5 flex gap-4"
                >
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${s.color}`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-gray-400 uppercase">
                        Step {s.step}
                      </span>
                    </div>
                    <h3 className="font-semibold text-gray-800 text-sm mb-1">
                      {s.title}
                    </h3>
                    <p className="text-xs text-gray-500 leading-relaxed">
                      {s.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Concepts */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold text-gray-800 mb-6 text-center">
            Key concepts
          </h2>
          <div className="space-y-4">
            {concepts.map((c) => {
              const Icon = c.icon;
              return (
                <div
                  key={c.term}
                  className="bg-white rounded-xl border border-gray-200 p-5 flex gap-4"
                >
                  <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
                    <Icon className="w-4 h-4 text-gray-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-800 text-sm mb-1">
                      {c.term}
                    </h3>
                    <p className="text-sm text-gray-500 leading-relaxed">
                      {c.definition}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Quick tips */}
        <div className="bg-blue-50 rounded-xl border border-blue-100 p-6">
          <h2 className="font-semibold text-blue-800 mb-4">Quick tips</h2>
          <ul className="space-y-2">
            {[
              "Use a fine-grained GitHub token with read access to the repositories you want to analyse.",
              "You can have multiple workspaces — one per GitHub account or GitLab instance.",
              "Start with a small date range to test your collection plan before running a full history.",
              "After collection, run data cleaning to remove noise before analysis.",
              "Export your cleaned dataset as CSV for use in external tools like Jupyter Notebook.",
            ].map((tip) => (
              <li key={tip} className="flex items-start gap-2 text-sm text-blue-700">
                <CheckCircle className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                {tip}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default GetStarted;
