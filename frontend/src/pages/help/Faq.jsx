import React, { useState } from "react";
import { ChevronDown, ChevronRight, HelpCircle } from "lucide-react";

const faqs = [
  {
    category: "Getting started",
    items: [
      {
        q: "What is RevMine?",
        a: "RevMine is a software engineering analytics platform. It connects to your GitHub or GitLab repositories, collects development metrics (commits, pull requests, issues, etc.), and helps you analyse contributor activity, detect trends, and estimate effort.",
      },
      {
        q: "Is RevMine free to use?",
        a: "RevMine is currently available to registered users during its beta phase. Contact the team for access or licensing information.",
      },
      {
        q: "Which platforms are supported?",
        a: "RevMine supports GitHub, GitLab.com, and self-hosted GitLab instances.",
      },
    ],
  },
  {
    category: "Tokens & Authentication",
    items: [
      {
        q: "What is a personal access token?",
        a: "A personal access token (PAT) is a credential string generated from your GitHub or GitLab account settings. It allows RevMine to authenticate with the platform API on your behalf without storing your password.",
      },
      {
        q: "What permissions does my token need?",
        a: "For GitHub: grant the 'repo' scope (or use a fine-grained token with read access to Contents, Metadata, Pull Requests, and Issues). For GitLab: grant the 'read_api' scope.",
      },
      {
        q: "Is my token stored securely?",
        a: "Yes. Your token is encrypted using AES-256 before being stored in the database. It is never returned in plain text through the API.",
      },
      {
        q: "Can I revoke or update my token?",
        a: "Yes. Open the workspace settings and update the token. RevMine will test the new token before saving it.",
      },
    ],
  },
  {
    category: "Workspaces & Projects",
    items: [
      {
        q: "What is a workspace?",
        a: "A workspace is a connection to one GitHub or GitLab account. It holds your encrypted token and organises the repositories (projects) you imported from that account.",
      },
      {
        q: "Can I have multiple workspaces?",
        a: "Yes. You can create one workspace per GitHub account or GitLab instance. This is useful if you work across multiple organisations.",
      },
      {
        q: "What is a project?",
        a: "A project is an individual repository imported into a workspace. Each project can have its own collection plans, cleaned datasets, and analyses.",
      },
      {
        q: "How do I import repositories?",
        a: "Open a workspace, click 'Import repositories', and select the repositories you want to track. RevMine will fetch the list directly from the platform using your token.",
      },
    ],
  },
  {
    category: "Data Collection",
    items: [
      {
        q: "What data can RevMine collect?",
        a: "RevMine can collect commits (message, author, date, files changed), pull requests, issues, branches, and code churn metrics depending on the platform.",
      },
      {
        q: "How long does a collection take?",
        a: "It depends on the repository size and the date range you select. Small repositories complete in seconds; large repositories with years of history may take several minutes.",
      },
      {
        q: "Can I limit the data collection to a specific period?",
        a: "Yes. When configuring a collection plan, you can set a start date and an end date to limit the data to a specific time window.",
      },
      {
        q: "What happens if the collection fails?",
        a: "RevMine will display an error message with the reason. Common causes are an expired token or a rate-limit from the platform API. You can retry the collection after resolving the issue.",
      },
    ],
  },
  {
    category: "Analysis",
    items: [
      {
        q: "What analyses are available?",
        a: "Currently you can visualise commits over time, identify top contributors, analyse code churn, and view pull-request metrics. More analyses are being added.",
      },
      {
        q: "Can I export my data?",
        a: "Yes. After a collection and cleaning step, you can export the dataset as a CSV file for use in external tools such as Jupyter Notebook, Excel, or R.",
      },
      {
        q: "What is data cleaning?",
        a: "Data cleaning removes noise from the raw collected data: bot commits, merge commits without intent, duplicate entries, and outliers. This improves the quality of the resulting analyses.",
      },
    ],
  },
  {
    category: "DevOps (Kanban & CI/CD)",
    items: [
      {
        q: "What is the Kanban analysis track?",
        a: "Open Kanban → New analysis → Live from provider, then pick a GitHub Projects v2 board or a GitLab Issue Board. RevMine fetches the issues, normalises them into a dataset, and unlocks Kanban-specific metrics: lead time, cycle time, throughput, WIP, cumulative flow diagram, time per column, blocked ratio, and assignee load.",
      },
      {
        q: "What is the CI/CD analysis track?",
        a: "Open CI/CD → New analysis → Live from provider, then pick a GitHub Actions workflow or a GitLab CI project. RevMine pulls recent runs and computes success rate, build duration, failure rate by job, MTTR, deploy frequency, queue time, runner utilisation, and flaky-jobs detection.",
      },
      {
        q: "Do I need a separate token for Kanban / CI/CD?",
        a: "No. If the source repository is already imported under a workspace, RevMine resolves the stored OAuth token automatically. The “Manual token” tab is only needed for ad-hoc sources (for example, a self-hosted GitLab project that is not yet connected as a workspace).",
      },
      {
        q: "What does “Collect metrics & download CSV” do?",
        a: "After a Kanban or CI/CD collection finishes, the new “Collect metrics” step lets you tick the metrics you want, runs them in one shot against the collected dataset, previews the computed statistics, and gives you a metrics CSV (one row per metric × statistic). Use it for spreadsheets, BI tools, or sharing summaries without exporting the full raw dataset.",
      },
      {
        q: "What is the difference between “Download raw CSV” and the metrics CSV?",
        a: "The raw CSV contains every issue / pipeline run that was collected (one row per item). The metrics CSV contains the computed statistics for the metrics you picked (one row per metric × statistic), so it stays compact even when the raw dataset is large.",
      },
      {
        q: "After generating metrics, where do I see the charts?",
        a: "Click “Continue to analysis” from the metrics page. You land in the regular analysis service where the metric catalogue is filtered to the dataset's domain (Kanban or CI/CD), and you can build interactive dashboards.",
      },
    ],
  },
];

const FaqItem = ({ item }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-gray-100 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition"
      >
        <span className="text-sm font-medium text-gray-800 pr-4">{item.q}</span>
        {open ? (
          <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
        )}
      </button>
      {open && (
        <div className="px-5 pb-4">
          <p className="text-sm text-gray-600 leading-relaxed">{item.a}</p>
        </div>
      )}
    </div>
  );
};

const Faq = () => {
  return (
    <div className="min-h-screen p-4 sm:p-6">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-sm font-medium mb-4">
            <HelpCircle className="w-4 h-4" />
            FAQs
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-3">
            Frequently asked questions
          </h1>
          <p className="text-gray-500">
            Everything you need to know about using RevMine.
          </p>
        </div>

        <div className="space-y-6">
          {faqs.map((section) => (
            <div
              key={section.category}
              className="bg-white rounded-xl border border-gray-200 overflow-hidden"
            >
              <div className="px-5 py-4 border-b border-gray-100">
                <h2 className="font-semibold text-gray-800 text-sm">
                  {section.category}
                </h2>
              </div>
              <div>
                {section.items.map((item) => (
                  <FaqItem key={item.q} item={item} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Faq;
