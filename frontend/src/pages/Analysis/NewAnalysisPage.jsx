import { useNavigate } from "react-router-dom";
import {
  Upload,
  FolderOpen,
  ChevronRight,
  ArrowLeft,
  FlaskConical,
} from "lucide-react";

export default function NewAnalysisPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
      <div className="max-w-2xl mx-auto px-6 py-12">
        {/* Back */}
        <button
          onClick={() => navigate("/analysis/history")}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 text-sm mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to history
        </button>

        {/* Header */}
        <div className="flex items-center gap-4 mb-10">
          <div className="w-14 h-14 rounded-2xl bg-linear-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-200/50">
            <FlaskConical className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">New Analysis</h1>
            <p className="text-sm text-slate-500">
              Choose how you want to start your analysis
            </p>
          </div>
        </div>

        {/* Choices */}
        <div className="space-y-4">
          {/* Option 1: External CSV */}
          <button
            onClick={() => navigate("/analysis")}
            className="w-full flex items-center gap-5 p-6 rounded-2xl bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-lg hover:shadow-indigo-100/50 transition-all group text-left"
          >
            <div className="w-14 h-14 rounded-xl bg-linear-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-200/50 shrink-0">
              <Upload className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <p className="text-lg font-semibold text-slate-800 group-hover:text-indigo-700 transition-colors">
                From External CSV
              </p>
              <p className="text-sm text-slate-500 mt-1">
                Upload your own CSV file directly and run analysis on it.
                Ideal when you have data from an external source.
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-indigo-500 transition-colors shrink-0" />
          </button>

          {/* Option 2: From cleaned data */}
          <button
            onClick={() => navigate("/analysis/new/project")}
            className="w-full flex items-center gap-5 p-6 rounded-2xl bg-white border border-slate-200 hover:border-emerald-300 hover:shadow-lg hover:shadow-emerald-100/50 transition-all group text-left"
          >
            <div className="w-14 h-14 rounded-xl bg-linear-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-200/50 shrink-0">
              <FolderOpen className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <p className="text-lg font-semibold text-slate-800 group-hover:text-emerald-700 transition-colors">
                From Cleaned Data
              </p>
              <p className="text-sm text-slate-500 mt-1">
                Pick from your existing cleaned data instances collected from
                workspace projects. No upload needed.
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-emerald-500 transition-colors shrink-0" />
          </button>
        </div>
      </div>
    </div>
  );
}
