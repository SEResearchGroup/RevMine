import { useNavigate } from "react-router-dom";
import {
  Upload,
  Cloud,
  ChevronRight,
  ArrowLeft,
  Kanban,
} from "lucide-react";

export default function NewKanbanAnalysisPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-indigo-50/30 to-violet-50/40">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <button
          onClick={() => navigate("/kanban/history")}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 text-sm mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Kanban history
        </button>

        <div className="flex items-center gap-4 mb-10">
          <div className="w-14 h-14 rounded-2xl bg-linear-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-200/50">
            <Kanban className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">New Kanban Analysis</h1>
            <p className="text-sm text-slate-500">
              Choose where the board data should come from
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <button
            onClick={() => navigate("/kanban/new/live")}
            className="w-full flex items-center gap-5 p-6 rounded-2xl bg-white border border-slate-200 hover:border-violet-300 hover:shadow-lg hover:shadow-violet-100/50 transition-all group text-left"
          >
            <div className="w-14 h-14 rounded-xl bg-linear-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-200/50 shrink-0">
              <Cloud className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <p className="text-lg font-semibold text-slate-800 group-hover:text-violet-700 transition-colors">
                Live from provider
              </p>
              <p className="text-sm text-slate-500 mt-1">
                Pull issues directly from a GitHub Projects v2 board or a GitLab
                Issue Board. Requires a provider access token.
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-violet-500 transition-colors shrink-0" />
          </button>

          <button
            onClick={() => navigate("/kanban/new/csv")}
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
                Upload a board export CSV (GitHub, Jira, Trello…). Must include
                created_at / closed_at or column / duration_h columns.
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-500 transition-colors shrink-0" />
          </button>
        </div>
      </div>
    </div>
  );
}
