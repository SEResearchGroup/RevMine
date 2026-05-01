import React, { useState } from "react";
import {
  GitBranch,
  Database,
  BarChart3,
  Key,
  FolderOpen,
  BookOpen,
  ArrowRight,
  CheckCircle,
  Filter,
  LineChart,
  Sparkles,
  ChevronDown,
  ChevronUp,
  GitMerge,
  GitCommit,
  MessageSquare,
  FileText,
  FileDiff,
  BrainCircuit,
  TrendingUp,
  PieChart,
  Users,
  Clock,
  Layers,
  Lightbulb,
  Kanban,
  Workflow,
  FileDown,
  Cloud,
  Zap,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import logo from "../../assets/images/logo_v1.png";

/* ─── Steps ─── */
const steps = [
  {
    step: 1,
    icon: Key,
    title: "Connect your repository host",
    description:
      "Create a Workspace by providing your GitHub or GitLab personal access token. RevMine validates the connection and lists your repositories.",
    color: "from-blue-500 to-blue-600",
    bg: "bg-blue-50",
    ring: "ring-blue-200",
  },
  {
    step: 2,
    icon: FolderOpen,
    title: "Import projects",
    description:
      "Select the repositories you want to track. They become Projects inside your Workspace — each project is an independent unit of analysis.",
    color: "from-blue-500 to-purple-600",
    bg: "bg-blue-50",
    ring: "ring-purple-200",
  },
  {
    step: 3,
    icon: Database,
    title: "Collect data",
    description:
      "Launch a collection plan for any project. Choose the metrics you need (MR metadata, commits, discussions, notes, file changes), set date ranges and branch filters.",
    color: "from-green-500 to-green-600",
    bg: "bg-green-50",
    ring: "ring-emerald-200",
  },
  {
    step: 4,
    icon: Filter,
    title: "Clean your data",
    description:
      "Apply filters to remove noise — filter by reviewers, committers, date ranges, and more. Generate a clean CSV dataset ready for analysis.",
    color: "from-amber-500 to-amber-600",
    bg: "bg-amber-50",
    ring: "ring-amber-200",
  },
  {
    step: 5,
    icon: LineChart,
    title: "Select metrics & analyse",
    description:
      "Pick from 20+ analysis metrics across code quality, collaboration, distribution, correlation, and time series categories. Launch analyses to generate interactive charts.",
    color: "from-rose-500 to-rose-600",
    bg: "bg-red-50",
    ring: "ring-rose-200",
  },
  {
    step: 6,
    icon: BarChart3,
    title: "Explore & export",
    description:
      "Browse interactive dashboards, detect trends, identify top contributors, and export results for further processing.",
    color: "from-blue-500 to-cyan-600",
    bg: "bg-blue-50",
    ring: "ring-cyan-200",
  },
];

/* ─── Key Concepts ─── */
const concepts = [
  {
    icon: GitBranch,
    term: "Workspace",
    definition:
      "A secure container that holds the connection to one GitHub or GitLab account. It stores your encrypted access token and lists all repositories available under that account.",
    color: "text-blue-600 bg-blue-50",
  },
  {
    icon: FolderOpen,
    term: "Project",
    definition:
      "An individual repository imported into a Workspace. It is the unit on which you run collection plans, clean data, and perform analyses.",
    color: "text-blue-600 bg-blue-50",
  },
  {
    icon: Key,
    term: "GitHub / GitLab Token",
    definition:
      "A personal access token (PAT) generated from your GitHub or GitLab account settings. It grants RevMine read-only access to repository metadata, commits, and merge requests. Tokens are stored encrypted and never exposed in plain text.",
    color: "text-green-600 bg-green-50",
  },
  {
    icon: Database,
    term: "Collection Plan",
    definition:
      "A configured job that fetches specific metrics from a project for a chosen time period and branch. Each run produces a dataset ready for cleaning and analysis.",
    color: "text-amber-600 bg-amber-50",
  },
  {
    icon: Filter,
    term: "Data Cleaning",
    definition:
      "A post-collection step where you apply filters (reviewers, committers, date ranges, etc.) to remove noise and generate a clean CSV for analysis.",
    color: "text-red-600 bg-red-50",
  },
  {
    icon: LineChart,
    term: "Analysis",
    definition:
      "Select metrics and chart types to visualize your cleaned data. RevMine provides 20+ built-in analysis metrics including code churn, collaboration, complexity, time series and more.",
    color: "text-blue-600 bg-blue-50",
  },
];

/* ─── Collection metrics ─── */
const collectionMetricGroups = [
  {
    title: "Merge Request Metadata",
    icon: GitMerge,
    color: "text-blue-600 bg-blue-50",
    metrics: [
      "MR Title",
      "MR Description",
      "MR IID",
      "MR Status",
      "MR State (opened/closed/merged)",
      "MR Author",
      "Creation Date",
      "Merge Date",
      "Close Date",
      "Merged By",
    ],
  },
  {
    title: "Commits",
    icon: GitCommit,
    color: "text-blue-600 bg-blue-50",
    metrics: [
      "Commit ID",
      "Commit Messages",
      "Commit Authors",
      "Commit Dates",
      "File Changes (Diff)",
    ],
  },
  {
    title: "Discussions",
    icon: MessageSquare,
    color: "text-green-600 bg-green-50",
    metrics: ["Discussion ID", "Discussion Notes", "Resolved Status"],
  },
  {
    title: "Notes",
    icon: FileText,
    color: "text-amber-600 bg-amber-50",
    metrics: ["Note Content", "Note Author", "Note Date", "Note Type"],
  },
  {
    title: "Changes",
    icon: FileDiff,
    color: "text-red-600 bg-red-50",
    metrics: [
      "Old File Path",
      "New File Path",
      "File Diff",
      "New File",
      "Renamed File",
      "Deleted File",
    ],
  },
];

/* ─── DevOps tracks (NEW) ─── */
const devopsTracks = [
  {
    title: "Code Reviews",
    icon: GitMerge,
    color: "from-blue-500 to-blue-600",
    bg: "bg-blue-50",
    text: "text-blue-700",
    description:
      "The original RevMine flow: collection plans on a repository produce a cleaned MR/PR dataset for analysis.",
    cta: "Open analysis",
    route: "/analysis",
  },
  {
    title: "Kanban Boards",
    icon: Kanban,
    color: "from-blue-500 to-blue-600",
    bg: "bg-blue-50",
    text: "text-blue-700",
    description:
      "Pull live issues from a GitHub Projects v2 board or a GitLab Issue Board. Compute lead time, cycle time, throughput, WIP, CFD, and more.",
    cta: "New Kanban analysis",
    route: "/kanban/new",
  },
  {
    title: "CI/CD Pipelines",
    icon: Workflow,
    color: "from-green-500 to-green-600",
    bg: "bg-green-50",
    text: "text-green-700",
    description:
      "Pull recent runs from GitHub Actions or GitLab CI. Compute success rate, build duration, MTTR, deploy frequency, queue time, flaky jobs.",
    cta: "New CI/CD analysis",
    route: "/cicd/new",
  },
];

/* ─── DevOps flow (NEW) ─── */
const devopsFlow = [
  {
    step: 1,
    icon: Cloud,
    title: "Pick a source",
    description:
      "From a connected workspace or with a manual access token, choose the Kanban board or CI/CD pipeline you want to ingest.",
    color: "from-blue-500 to-blue-600",
  },
  {
    step: 2,
    icon: Database,
    title: "Collect the raw dataset",
    description:
      "RevMine fetches the issues / runs and saves them as a normalised dataset. Download the raw rows as CSV or JSON whenever you need them.",
    color: "from-blue-500 to-blue-600",
  },
  {
    step: 3,
    icon: Zap,
    title: "Collect metrics & download CSV",
    description:
      "Pick the DevOps metrics you care about, run them in one click, preview the results, then export a metrics CSV for spreadsheets, BI tools, or reports.",
    color: "from-amber-500 to-amber-600",
  },
  {
    step: 4,
    icon: BarChart3,
    title: "Continue to analysis",
    description:
      "Move into the analysis service to turn the same dataset into interactive charts and dashboards. The metric catalogue is filtered to the matching DevOps domain.",
    color: "from-green-500 to-green-600",
  },
];

/* ─── DevOps metric catalogues (NEW) ─── */
const devopsMetricGroups = [
  {
    title: "Kanban metrics",
    icon: Kanban,
    color: "text-blue-600 bg-blue-50",
    metrics: [
      "Lead Time",
      "Cycle Time",
      "Throughput",
      "Work In Progress (WIP)",
      "Cumulative Flow Diagram",
      "Time per Column",
      "Blocked Ratio",
      "Assignee Load",
    ],
  },
  {
    title: "CI/CD metrics",
    icon: Workflow,
    color: "text-green-600 bg-green-50",
    metrics: [
      "Success Rate",
      "Build Duration",
      "Failure Rate by Job",
      "Mean Time To Recovery (MTTR)",
      "Deploy Frequency",
      "Queue Time",
      "Runner Utilisation",
      "Flaky Jobs",
    ],
  },
];

/* ─── Analysis metrics ─── */
const analysisCategories = [
  {
    title: "Code Quality",
    icon: Layers,
    color: "text-blue-600 bg-blue-50",
    border: "border-blue-200",
    metrics: [
      { name: "Code Churn Analysis", charts: "Bar, Histogram" },
      { name: "Files Modified Analysis", charts: "Bar, Histogram" },
      { name: "File Types Distribution", charts: "Bar, Pie" },
      { name: "Historical Entropy", charts: "Histogram, Bar, Box" },
      { name: "Rework Analysis", charts: "Histogram, Bar" },
    ],
  },
  {
    title: "Collaboration",
    icon: Users,
    color: "text-blue-600 bg-blue-50",
    border: "border-purple-200",
    metrics: [
      { name: "Collaboration Metrics", charts: "Bar, Pie" },
      { name: "Comments Analysis", charts: "Bar, Histogram" },
      { name: "Contributors Analysis", charts: "Bar, Pie" },
      { name: "Discussions Analysis", charts: "Bar, Histogram" },
      { name: "Top 10 Committers", charts: "Bar, Pie" },
      { name: "Top Authors", charts: "Bar, Pie" },
      { name: "Top Reviewers", charts: "Bar, Pie" },
    ],
  },
  {
    title: "Correlation",
    icon: TrendingUp,
    color: "text-green-600 bg-green-50",
    border: "border-green-200",
    metrics: [
      { name: "Churn Correlation", charts: "Scatter" },
      { name: "Correlation Matrix", charts: "Heatmap" },
    ],
  },
  {
    title: "Distribution",
    icon: PieChart,
    color: "text-amber-600 bg-amber-50",
    border: "border-amber-200",
    metrics: [
      { name: "Commits Distribution", charts: "Bar, Histogram" },
      { name: "Lead Time Distribution", charts: "Histogram, Box" },
      { name: "MR Size Analysis", charts: "Histogram, Box, Bar" },
    ],
  },
  {
    title: "Overview",
    icon: BarChart3,
    color: "text-red-600 bg-red-50",
    border: "border-rose-200",
    metrics: [
      { name: "MR Complexity", charts: "Pie, Bar" },
      { name: "MR State Distribution", charts: "Pie, Bar" },
      { name: "Project Comparison", charts: "Bar, Line" },
    ],
  },
  {
    title: "Time Series",
    icon: Clock,
    color: "text-blue-600 bg-blue-50",
    border: "border-cyan-200",
    metrics: [
      { name: "Commits Over Time", charts: "Line, Bar, Area" },
      { name: "MR Creation Timeline", charts: "Bar, Line, Area" },
      { name: "MR Creation Time of Day", charts: "Bar, Line" },
    ],
  },
];

/* ─── Collapsible Section ─── */
const CollapsibleSection = ({ title, icon: Icon, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-gray-800 text-sm">{title}</h3>
        </div>
        {open ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
};

/* ─── Main Component ─── */
const GetStarted = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-5xl mx-auto">
        {/* ── Hero ── */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-50 text-blue-600 rounded-full text-sm font-medium mb-6">
            <BookOpen className="w-4 h-4" />
            Getting started guide
          </div>

          <div className="flex justify-center mb-5">
            <img src={logo} alt="RevMine" className="h-14" />
          </div>

          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
            A software engineering analytics platform that transforms raw repository
            activity into actionable insights — from commits and merge requests to
            Kanban flow, CI/CD reliability, and contributor trends.
          </p>

          <div className="flex flex-wrap justify-center gap-3 mt-8">
            <button
              onClick={() => navigate("/workspaces")}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm font-medium shadow-sm shadow-blue-200 transition"
            >
              Create your first workspace
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => navigate("/help/faqs")}
              className="px-6 py-2.5 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium transition"
            >
              Read FAQs
            </button>
          </div>
        </div>

        {/* ── How it works ── */}
        <section className="mb-14">
          <div className="text-center mb-8">
            <h2 className="text-xl font-bold text-gray-900">How it works</h2>
            <p className="text-sm text-gray-500 mt-1">From connection to insights in 6 steps</p>
          </div>

          <div className="relative">
            {/* Vertical connector line */}
            <div className="hidden sm:block absolute left-1/2 top-0 bottom-0 w-px bg-gray-200 -translate-x-1/2" />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {steps.map((s, idx) => {
                const Icon = s.icon;
                return (
                  <div
                    key={s.step}
                    className={`relative bg-white rounded-xl border border-gray-200 p-5 flex gap-4 hover:shadow-md hover:border-gray-300 transition-all duration-200 ${
                      idx % 2 === 0 ? "sm:text-right sm:flex-row-reverse" : ""
                    }`}
                  >
                    <div
                      className={`w-11 h-11 rounded-xl bg-gradient-to-br ${s.color} flex items-center justify-center shrink-0 shadow-sm`}
                    >
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <span className="inline-block text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-1">
                        Step {s.step}
                      </span>
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
        </section>

        {/* ── Intelligent Assistant banner ── */}
        <section className="mb-14">
          <div className="relative overflow-hidden bg-gradient-to-r from-blue-600 via-blue-600 to-cyan-600 rounded-xl p-6 sm:p-8 text-white">
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/3" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-1/3 -translate-x-1/4" />

            <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-5">
              <div className="w-14 h-14 bg-white/15 backdrop-blur rounded-xl flex items-center justify-center shrink-0">
                <BrainCircuit className="w-7 h-7 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold mb-1">Intelligent Assistant</h3>
                <p className="text-sm text-blue-100 leading-relaxed max-w-xl">
                  Skip the manual configuration — describe what you want in natural
                  language and let RevMine handle collection and analysis
                  automatically. For example:{" "}
                  <em className="text-white/90">
                    "Collect all merge requests from the last 6 months and analyse
                    code churn trends."
                  </em>
                </p>
              </div>
              <div className="shrink-0">
                <Sparkles className="w-6 h-6 text-yellow-300 animate-pulse" />
              </div>
            </div>
          </div>
        </section>

        {/* ── Key Concepts ── */}
        <section className="mb-14">
          <div className="text-center mb-8">
            <h2 className="text-xl font-bold text-gray-900">Key concepts</h2>
            <p className="text-sm text-gray-500 mt-1">
              Understand the building blocks of RevMine
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {concepts.map((c) => {
              const Icon = c.icon;
              return (
                <div
                  key={c.term}
                  className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all duration-200"
                >
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${c.color}`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="font-semibold text-gray-800 text-sm mb-1.5">
                    {c.term}
                  </h3>
                  <p className="text-xs text-gray-500 leading-relaxed">
                    {c.definition}
                  </p>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── DevOps tracks (NEW) ── */}
        <section className="mb-14">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-semibold uppercase tracking-wide mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              New
            </div>
            <h2 className="text-xl font-bold text-gray-900">Three analysis tracks</h2>
            <p className="text-sm text-gray-500 mt-1">
              Code reviews are joined by Kanban and CI/CD pipelines — each with its own
              live collector and metric catalogue.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {devopsTracks.map((track) => {
              const TIcon = track.icon;
              return (
                <button
                  key={track.title}
                  onClick={() => navigate(track.route)}
                  className="text-left bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all duration-200 flex flex-col"
                >
                  <div
                    className={`w-11 h-11 rounded-xl bg-gradient-to-br ${track.color} flex items-center justify-center mb-3 shadow-sm`}
                  >
                    <TIcon className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="font-semibold text-gray-800 text-sm mb-1.5">
                    {track.title}
                  </h3>
                  <p className="text-xs text-gray-500 leading-relaxed flex-1">
                    {track.description}
                  </p>
                  <span
                    className={`mt-3 inline-flex items-center gap-1 text-xs font-medium ${track.text}`}
                  >
                    {track.cta}
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        {/* ── DevOps flow (NEW) ── */}
        <section className="mb-14">
          <div className="text-center mb-8">
            <h2 className="text-xl font-bold text-gray-900">
              DevOps flow: collect → metrics → analysis
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              The Kanban and CI/CD tracks share the same four-step pipeline.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {devopsFlow.map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.step}
                  className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col hover:shadow-md transition-all"
                >
                  <div
                    className={`w-11 h-11 rounded-xl bg-gradient-to-br ${s.color} flex items-center justify-center mb-3 shadow-sm`}
                  >
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-1">
                    Step {s.step}
                  </span>
                  <h3 className="font-semibold text-gray-800 text-sm mb-1">
                    {s.title}
                  </h3>
                  <p className="text-xs text-gray-500 leading-relaxed">
                    {s.description}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="mt-5 flex flex-col sm:flex-row items-start sm:items-center gap-3 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
            <FileDown className="w-4 h-4 text-amber-600 shrink-0" />
            <p className="text-xs text-amber-800 leading-relaxed">
              The "Collect metrics" step (new) flattens each metric's statistics into a
              single CSV — handy for sharing summaries without exporting the whole raw
              dataset.
            </p>
          </div>
        </section>

        {/* ── DevOps Metrics (NEW) ── */}
        <section className="mb-14">
          <div className="text-center mb-8">
            <h2 className="text-xl font-bold text-gray-900">DevOps metrics</h2>
            <p className="text-sm text-gray-500 mt-1">
              Available in the metric picker for Kanban / CI/CD datasets.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {devopsMetricGroups.map((group) => {
              const GIcon = group.icon;
              return (
                <div
                  key={group.title}
                  className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-center gap-2.5 mb-3">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center ${group.color}`}
                    >
                      <GIcon className="w-4 h-4" />
                    </div>
                    <h3 className="font-semibold text-gray-800 text-sm">
                      {group.title}
                    </h3>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {group.metrics.map((m) => (
                      <span
                        key={m}
                        className="text-[11px] px-2 py-0.5 bg-gray-50 text-gray-600 rounded-md border border-gray-100"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Collection Metrics ── */}
        <section className="mb-14">
          <div className="text-center mb-8">
            <h2 className="text-xl font-bold text-gray-900">Collection Metrics</h2>
            <p className="text-sm text-gray-500 mt-1">
              Data points you can collect from each repository
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {collectionMetricGroups.map((group) => {
              const GIcon = group.icon;
              return (
                <div
                  key={group.title}
                  className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-center gap-2.5 mb-3">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center ${group.color}`}
                    >
                      <GIcon className="w-4 h-4" />
                    </div>
                    <h3 className="font-semibold text-gray-800 text-sm">
                      {group.title}
                    </h3>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {group.metrics.map((m) => (
                      <span
                        key={m}
                        className="text-[11px] px-2 py-0.5 bg-gray-50 text-gray-600 rounded-md border border-gray-100"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Analysis Metrics ── */}
        <section className="mb-14">
          <div className="text-center mb-8">
            <h2 className="text-xl font-bold text-gray-900">Analysis Metrics</h2>
            <p className="text-sm text-gray-500 mt-1">
              20+ built-in chart types to visualize your data
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {analysisCategories.map((cat) => {
              const CIcon = cat.icon;
              return (
                <div
                  key={cat.title}
                  className={`bg-white rounded-xl border ${cat.border} p-5 hover:shadow-md transition-all duration-200`}
                >
                  <div className="flex items-center gap-2.5 mb-4">
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center ${cat.color}`}
                    >
                      <CIcon className="w-4.5 h-4.5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-800 text-sm">
                        {cat.title}
                      </h3>
                      <span className="text-[10px] text-gray-400">
                        {cat.metrics.length} metric{cat.metrics.length > 1 && "s"}
                      </span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {cat.metrics.map((m) => (
                      <div
                        key={m.name}
                        className="flex items-center justify-between text-xs"
                      >
                        <span className="text-gray-700 font-medium">{m.name}</span>
                        <span className="text-gray-400 ml-2 shrink-0">
                          {m.charts}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Quick tips ── */}
        <section className="mb-8">
          <div className="bg-gradient-to-br from-blue-50 to-blue-50 rounded-xl border border-blue-100 p-6 sm:p-8">
            <div className="flex items-center gap-2.5 mb-5">
              <Lightbulb className="w-5 h-5 text-blue-600" />
              <h2 className="font-bold text-blue-900">Quick tips</h2>
            </div>
            <ul className="space-y-3">
              {[
                "Use a fine-grained GitHub token with read access to the repositories you want to analyse.",
                "You can have multiple workspaces — one per GitHub account or GitLab instance.",
                "Start with a small date range to test your collection plan before running a full history.",
                "After collection, run data cleaning to filter reviewers, committers, and dates before analysis.",
                "Use the Intelligent Assistant to skip manual metric selection — just describe your goal in plain language.",
                "Export your cleaned dataset as CSV for use in external tools like Jupyter Notebook.",
                "For Kanban or CI/CD analyses, use “Collect metrics & download CSV” after collection to get a flat statistics file you can drop straight into a spreadsheet.",
                "Workspace-connected repos auto-resolve their stored OAuth token — no need to paste a personal token for every Kanban / CI/CD collection.",
              ].map((tip) => (
                <li
                  key={tip}
                  className="flex items-start gap-2.5 text-sm text-blue-800"
                >
                  <CheckCircle className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
};

export default GetStarted;
