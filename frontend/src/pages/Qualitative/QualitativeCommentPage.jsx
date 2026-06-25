import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Loader2, ExternalLink, CheckCircle2, XCircle,
  CornerDownRight, GitCommitHorizontal,
} from "lucide-react";
import { qualitativeService, getApiErrorMessage } from "../../services/api";

const CATEGORY_LABELS = {
  general: "General comment",
  inline: "Review comment",
  review_summary: "Review summary",
  commit_comment: "Commit comment",
};

export default function QualitativeCommentPage() {
  const { datasetId, commentId } = useParams();
  const navigate = useNavigate();
  const [comment, setComment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await qualitativeService.getComment(datasetId, commentId);
        setComment(data);
      } catch (e) {
        setError(getApiErrorMessage(e, "Failed to load comment"));
      } finally {
        setLoading(false);
      }
    })();
  }, [datasetId, commentId]);

  if (loading) {
    return <div className="p-8 flex items-center gap-2 text-gray-500"><Loader2 className="w-4 h-4 animate-spin" /> Loading…</div>;
  }
  if (!comment) {
    return <div className="p-8 text-red-600">{error || "Comment not found"}</div>;
  }

  const r = comment.review || {};
  const thread = comment.thread || {};

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <button onClick={() => navigate(`/qualitative/${datasetId}`)}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-purple-600 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to dashboard
      </button>

      {/* Review context */}
      <div className="bg-white rounded-xl border border-gray-200/70 p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <span className="text-[11px] font-medium text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded uppercase tracking-wide">
              {CATEGORY_LABELS[comment.comment_type] || comment.comment_type}
            </span>
            <h1 className="text-lg font-semibold text-gray-800 mt-1.5">
              #{r.number} {r.title}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              by <span className="font-medium">{r.author}</span>
              {r.reviewers?.length ? <> · reviewers: {r.reviewers.join(", ")}</> : null}
              {r.state ? <> · {r.state}</> : null}
            </p>
          </div>
          {r.url && (
            <a href={r.url} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-purple-600 hover:underline shrink-0">
              Open <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
          {r.changed_files != null && <span>{r.changed_files} files changed</span>}
          {r.additions != null && <span className="text-green-600">+{r.additions}</span>}
          {r.deletions != null && <span className="text-red-600">-{r.deletions}</span>}
          {r.created_at && <span>opened {new Date(r.created_at).toLocaleDateString()}</span>}
        </div>
      </div>

      {/* Traces */}
      <div className="mt-4 flex flex-wrap gap-2">
        {comment.is_resolved === true && <Badge cls="text-green-700 bg-green-50" icon={CheckCircle2} text="Thread resolved" />}
        {comment.is_resolved === false && <Badge cls="text-amber-700 bg-amber-50" icon={XCircle} text="Unresolved" />}
        {comment.got_reply && <Badge cls="text-blue-700 bg-blue-50" icon={CornerDownRight} text="Received a reply" />}
        {comment.code_changed_after && <Badge cls="text-purple-700 bg-purple-50" icon={GitCommitHorizontal} text="Code changed after comment" />}
      </div>

      {/* Diff hunk */}
      {comment.diff_hunk ? (
        <div className="mt-4">
          <p className="text-sm font-medium text-gray-700 mb-1.5">
            Code context {comment.path ? <span className="font-mono text-xs text-gray-400">— {comment.path}{comment.line ? `:${comment.line}` : ""}</span> : null}
          </p>
          <pre className="text-xs bg-gray-900 text-gray-100 rounded-lg p-3 overflow-x-auto">{comment.diff_hunk}</pre>
        </div>
      ) : null}

      {/* Thread conversation */}
      <div className="mt-4">
        <p className="text-sm font-medium text-gray-700 mb-2">Conversation ({thread.comments?.length || 0})</p>
        <div className="space-y-2">
          {(thread.comments || []).map((c) => {
            const isCurrent = String(c.id) === String(comment.id);
            return (
              <div key={c.id}
                className={`rounded-xl border p-3 ${isCurrent ? "border-purple-300 bg-purple-50/40" : "border-gray-200/70 bg-white"}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-700">{c.author || "unknown"}</span>
                  {!c.is_human && <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">bot/system</span>}
                  {c.reply_to_id ? <CornerDownRight className="w-3 h-3 text-gray-300" /> : null}
                  <span className="text-xs text-gray-400 ml-auto">{c.created_at ? new Date(c.created_at).toLocaleString() : ""}</span>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{c.body}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Reactions */}
      {comment.reactions?.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {comment.reactions.map((rx, i) => (
            <span key={i} className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded">
              {rx.content} · {rx.user}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Badge({ cls, icon, text }) {
  const Icon = icon;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded ${cls}`}>
      <Icon className="w-3.5 h-3.5" /> {text}
    </span>
  );
}
