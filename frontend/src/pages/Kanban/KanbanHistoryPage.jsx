import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, Kanban, Plus, ArrowRight, FileDown, FileJson } from "lucide-react";
import { kanbanService } from "../../services/api";
import { downloadBlob, readBlobError } from "../../utils/downloadBlob";

export default function KanbanHistoryPage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);

  const handleDownload = async (dataset, format) => {
    setDownloadingId(`${dataset.id}:${format}`);
    try {
      const blob = await kanbanService.downloadDataset(dataset.id, format);
      // Sanity-check: if the backend returned a JSON error with 200, the
      // content-type will say so. Axios puts a Blob in `blob` either way.
      if (blob?.type?.includes("json") && format !== "json") {
        const text = await blob.text();
        try {
          const parsed = JSON.parse(text);
          if (parsed.error) throw new Error(parsed.error);
        } catch (e) { /* fall through: treat as file */ }
      }
      const base = (dataset.filename || `kanban_${dataset.id}`).replace(/\.csv$/i, "");
      downloadBlob(blob, `${base}.${format}`);
    } catch (err) {
      setError(await readBlobError(err, "Download failed"));
    } finally {
      setDownloadingId(null);
    }
  };

  useEffect(() => {
    kanbanService
      .listDatasets()
      .then((data) => setDatasets(data.results || []))
      .catch((err) => setError(err?.response?.data?.error || err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center">
              <Kanban className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Kanban Analysis</h1>
              <p className="text-sm text-gray-500">
                Collected boards and their analyses
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate("/kanban/new")}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" /> New Kanban Analysis
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : error ? (
          <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-4">
            {error}
          </p>
        ) : datasets.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-10 text-center">
            <p className="text-gray-500 mb-4">No Kanban datasets collected yet.</p>
            <Link
              to="/kanban/new"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium"
            >
              <Plus className="w-4 h-4" /> Start your first collection
            </Link>
          </div>
        ) : (
          <ul className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-100">
            {datasets.map((ds) => (
              <li key={ds.id} className="p-5 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="font-medium text-gray-800 truncate">{ds.filename}</p>
                  <p className="text-xs text-gray-500">
                    {ds.rows_count} rows · {ds.platform} ·{" "}
                    {new Date(ds.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleDownload(ds, "csv")}
                    disabled={downloadingId === `${ds.id}:csv`}
                    title="Download CSV"
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-gray-200 text-gray-600 text-xs hover:bg-gray-50 disabled:opacity-50"
                  >
                    {downloadingId === `${ds.id}:csv` ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <FileDown className="w-3.5 h-3.5" />
                    )}
                    CSV
                  </button>
                  <button
                    onClick={() => handleDownload(ds, "json")}
                    disabled={downloadingId === `${ds.id}:json`}
                    title="Download JSON"
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-gray-200 text-gray-600 text-xs hover:bg-gray-50 disabled:opacity-50"
                  >
                    {downloadingId === `${ds.id}:json` ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <FileJson className="w-3.5 h-3.5" />
                    )}
                    JSON
                  </button>
                  <button
                    onClick={() => navigate(`/kanban/${ds.id}/metrics`)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 text-sm hover:bg-blue-100"
                  >
                    Analyze <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
