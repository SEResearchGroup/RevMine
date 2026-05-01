import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  AlertCircle,
  Bell,
  CheckCircle2,
  Loader2,
  Rocket,
} from "lucide-react";
import { cicdService, kanbanService } from "../../services/api";

const SECTION_TO_SOURCE = { kanban: "kanban", cicd: "cicd" };
const POLL_INTERVAL_MS = 2000;

const deriveSection = (pathname) => {
  const first = (pathname || "").split("/").filter(Boolean)[0];
  return SECTION_TO_SOURCE[first] ? first : "kanban";
};

const STATUS_PALETTE = {
  pending: {
    label: "Queued",
    bar: "bg-gray-400",
    chip: "bg-gray-100 text-gray-600",
  },
  in_progress: {
    label: "In progress",
    bar: "bg-blue-500",
    chip: "bg-blue-100 text-blue-700",
  },
  completed: {
    label: "Completed",
    bar: "bg-green-500",
    chip: "bg-green-100 text-green-700",
  },
  failed: {
    label: "Failed",
    bar: "bg-red-500",
    chip: "bg-red-100 text-red-700",
  },
};

export default function DevopsCollectionProgress() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const section = deriveSection(location.pathname);
  const service = section === "cicd" ? cicdService : kanbanService;

  const [job, setJob] = useState(location.state?.job || null);
  const [error, setError] = useState(null);
  const consecutiveErrorsRef = useRef(0);
  const navigatedRef = useRef(false);

  const poll = useCallback(async () => {
    try {
      const data = await service.getJobStatus(jobId);
      setJob(data);
      consecutiveErrorsRef.current = 0;

      if (data.status === "completed" && !navigatedRef.current) {
        navigatedRef.current = true;
        const datasetId = data.dataset?.id;
        const next = datasetId
          ? `/${section}/${datasetId}/collect-metrics`
          : `/${section}/history`;
        // Small delay so the user can see the 100% bar before redirect.
        setTimeout(() => navigate(next), 1200);
      }
    } catch (err) {
      consecutiveErrorsRef.current += 1;
      if (consecutiveErrorsRef.current >= 3) {
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            "Lost connection to the collection job."
        );
      }
    }
  }, [jobId, navigate, section, service]);

  useEffect(() => {
    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [poll]);

  const status = job?.status || "pending";
  const palette = STATUS_PALETTE[status] || STATUS_PALETTE.pending;
  const percent = Math.max(0, Math.min(100, job?.progress_percent ?? 0));
  const message = job?.progress_message || palette.label;
  const isTerminal = status === "completed" || status === "failed";

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate(`/${section}/history`)}
          className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to {section} history
        </button>

        <div className="bg-white border border-gray-200 rounded-xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                status === "completed"
                  ? "bg-green-50 text-green-600"
                  : status === "failed"
                  ? "bg-red-50 text-red-600"
                  : "bg-blue-50 text-blue-600"
              }`}
            >
              {status === "completed" ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : status === "failed" ? (
                <AlertCircle className="w-6 h-6" />
              ) : (
                <Rocket className="w-6 h-6" />
              )}
            </div>
            <div className="flex-1">
              <h1 className="text-xl font-bold text-gray-800">
                {section === "cicd" ? "CI/CD" : "Kanban"} collection
              </h1>
              <p className="text-sm text-gray-500">
                {job?.label || job?.provider || jobId}
              </p>
            </div>
            <span
              className={`text-xs font-semibold px-2.5 py-1 rounded-full ${palette.chip}`}
            >
              {palette.label}
            </span>
          </div>

          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-gray-600">{message}</span>
            <span className="text-gray-500 font-medium">{percent}%</span>
          </div>
          <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${palette.bar}`}
              style={{ width: `${percent}%` }}
            />
          </div>

          {job && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
              <Stat label="Provider" value={job.provider || "—"} />
              <Stat label="Rows so far" value={job.collected_items ?? 0} />
              <Stat
                label="Started"
                value={
                  job.started_at
                    ? new Date(job.started_at).toLocaleTimeString()
                    : "—"
                }
              />
              <Stat
                label="Finished"
                value={
                  job.completed_at
                    ? new Date(job.completed_at).toLocaleTimeString()
                    : "—"
                }
              />
            </div>
          )}

          {!isTerminal && (
            <div className="mt-6 flex items-start gap-2.5 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 text-sm text-blue-800">
              <Bell className="w-4 h-4 mt-0.5 shrink-0" />
              <p className="leading-relaxed">
                Feel free to navigate away — the collection keeps running in
                the background. You'll get a notification in the bell icon when
                it finishes, with a link straight to the metrics step.
              </p>
            </div>
          )}

          {error && (
            <p className="mt-5 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
              {error}
            </p>
          )}

          {status === "failed" && job?.error_message && (
            <p className="mt-5 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
              <span className="font-medium">Error:</span> {job.error_message}
            </p>
          )}

          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            {status === "completed" && job?.dataset?.id ? (
              <button
                onClick={() =>
                  navigate(`/${section}/${job.dataset.id}/collect-metrics`)
                }
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700"
              >
                Continue to metrics <ArrowRight className="w-4 h-4" />
              </button>
            ) : status === "failed" ? (
              <button
                onClick={() => navigate(`/${section}/new/live`)}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700"
              >
                Try another collection
              </button>
            ) : (
              <>
                <button
                  onClick={() => navigate(`/${section}/history`)}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border border-gray-200 text-gray-700 font-medium hover:bg-gray-50"
                >
                  Browse {section} history
                </button>
                <button
                  onClick={() => navigate("/workspaces")}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border border-gray-200 text-gray-700 font-medium hover:bg-gray-50"
                >
                  Back to workspaces
                </button>
              </>
            )}
          </div>

          {!isTerminal && (
            <div className="mt-4 flex items-center justify-center gap-2 text-xs text-gray-400">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Polling every {POLL_INTERVAL_MS / 1000}s
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50/60 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-gray-400 font-medium">
        {label}
      </p>
      <p className="text-sm text-gray-700 font-medium mt-0.5 truncate">
        {value}
      </p>
    </div>
  );
}
