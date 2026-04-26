import { useNavigate } from "react-router-dom";
import {
  Upload,
  Cloud,
  ChevronRight,
  ArrowLeft,
  Workflow,
} from "lucide-react";

export default function NewCICDAnalysisPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-emerald-50/30 to-teal-50/40">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <button
          onClick={() => navigate("/cicd/history")}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 text-sm mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to CI/CD history
        </button>

        <div className="flex items-center gap-4 mb-10">
          <div className="w-14 h-14 rounded-2xl bg-linear-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-200/50">
            <Workflow className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">New CI/CD Analysis</h1>
            <p className="text-sm text-slate-500">
              Choose where the pipeline data should come from
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <button
            onClick={() => navigate("/cicd/new/live")}
            className="w-full flex items-center gap-5 p-6 rounded-2xl bg-white border border-slate-200 hover:border-emerald-300 hover:shadow-lg hover:shadow-emerald-100/50 transition-all group text-left"
          >
            <div className="w-14 h-14 rounded-xl bg-linear-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-200/50 shrink-0">
              <Cloud className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <p className="text-lg font-semibold text-slate-800 group-hover:text-emerald-700 transition-colors">
                Live from provider
              </p>
              <p className="text-sm text-slate-500 mt-1">
                Pull workflow runs and jobs directly from GitHub Actions or
                GitLab CI. Requires a token with workflow / api scope.
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-500 transition-colors shrink-0" />
          </button>

          <button
            onClick={() => navigate("/cicd/new/csv")}
            className="w-full flex items-center gap-5 p-6 rounded-2xl bg-white border border-slate-200 hover:border-blue-300 hover:shadow-lg hover:shadow-blue-100/50 transition-all group text-left"
          >
            <div className="w-14 h-14 rounded-xl bg-linear-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-200/50 shrink-0">
              <Upload className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <p className="text-lg font-semibold text-slate-800 group-hover:text-blue-700 transition-colors">
                From CSV export
              </p>
              <p className="text-sm text-slate-500 mt-1">
                Upload a pipeline-runs CSV with job_name, conclusion, duration_s
                and created_at / started_at columns.
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-500 transition-colors shrink-0" />
          </button>
        </div>
      </div>
    </div>
  );
}
