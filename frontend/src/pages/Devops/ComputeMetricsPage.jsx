import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  CheckSquare,
  FileDown,
  Info,
  Loader2,
  Lock,
  Search,
  Square,
} from "lucide-react";
import { analyzeService, cicdService, kanbanService } from "../../services/api";
import { downloadBlob, readBlobError } from "../../utils/downloadBlob";

const SECTION_TO_SOURCE = { kanban: "kanban", cicd: "cicd" };

const deriveSection = (pathname) => {
  const first = (pathname || "").split("/").filter(Boolean)[0];
  return SECTION_TO_SOURCE[first] ? first : "kanban";
};

const filterMetrics = (metrics, term) => {
  if (!term) return metrics;
  const q = term.toLowerCase();
  return metrics.filter(
    (m) =>
      (m.name || "").toLowerCase().includes(q) ||
      (m.code || "").toLowerCase().includes(q) ||
      (m.description || "").toLowerCase().includes(q)
  );
};

export default function ComputeMetricsPage() {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const section = deriveSection(location.pathname);
  const sourceType = SECTION_TO_SOURCE[section];
  const service = sourceType === "cicd" ? cicdService : kanbanService;
  const analysisPath = `/${section}/${datasetId}/metrics`;
  const sourcePath = `/${section}/new/live`;

  const [dataset, setDataset] = useState(null);
  const [metricsByCategory, setMetricsByCategory] = useState({});
  const [availableCodes, setAvailableCodes] = useState(new Set());
  const [missingCols, setMissingCols] = useState({});
  const [selected, setSelected] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [computed, setComputed] = useState(null);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [datasetRes, allMetricsRes, availableRes] = await Promise.all([
        analyzeService.getDatasetById(datasetId),
        analyzeService.getMetricsByCategory(sourceType),
        analyzeService.getAvailableMetrics(datasetId),
      ]);
      setDataset(datasetRes);
      setMetricsByCategory(allMetricsRes);
      const availableMetrics = availableRes.metrics || [];
      setAvailableCodes(new Set(availableMetrics.map((m) => m.code)));
      setMissingCols(availableRes.missing_columns_by_metric || {});
    } catch (err) {
      console.error(err);
      setError("Failed to load metrics for this dataset.");
    } finally {
      setLoading(false);
    }
  }, [datasetId, sourceType]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const allMetrics = useMemo(() => {
    return Object.values(metricsByCategory).flat();
  }, [metricsByCategory]);

  const filteredByCategory = useMemo(() => {
    const out = {};
    Object.entries(metricsByCategory).forEach(([cat, metrics]) => {
      const list = filterMetrics(metrics || [], searchTerm);
      if (list.length) out[cat] = list;
    });
    return out;
  }, [metricsByCategory, searchTerm]);

  const toggleMetric = (code) => {
    if (!availableCodes.has(code)) return;
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const selectAllAvailable = () => {
    const allAvailable = allMetrics
      .filter((m) => availableCodes.has(m.code))
      .map((m) => m.code);
    setSelected(selected.length === allAvailable.length ? [] : allAvailable);
  };

  const handleGenerate = async () => {
    if (selected.length === 0) return;
    setGenerating(true);
    setError(null);
    setComputed(null);
    try {
      const data = await service.computeMetrics(datasetId, selected);
      setComputed(data);
    } catch (err) {
      setError(
        err?.response?.data?.error ||
          err?.response?.data?.detail ||
          err?.message ||
          "Failed to compute metrics."
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (selected.length === 0) return;
    setDownloading(true);
    try {
      const blob = await service.downloadMetricsCSV(datasetId, selected);
      const base = (dataset?.filename || `dataset_${datasetId}`).replace(
        /\.csv$/i,
        ""
      );
      downloadBlob(blob, `${base}_metrics.csv`);
    } catch (err) {
      setError(await readBlobError(err, "Failed to download metrics CSV."));
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500 mx-auto mb-3" />
          <p className="text-gray-500">Loading metrics catalogue…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-10">
        <button
          onClick={() => navigate(sourcePath)}
          className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 text-sm mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to sources
        </button>

        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Collect metrics</h1>
            <p className="text-sm text-gray-500">
              Pick which {sourceType.toUpperCase()} metrics to compute on{" "}
              <span className="font-medium text-gray-700">
                {dataset?.filename}
              </span>
              , download them as CSV, then continue to analysis.
            </p>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-4 mt-6 sticky top-2 z-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <CheckSquare className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-xs text-gray-400">Selected</p>
                <p className="text-xl font-bold text-gray-800">
                  {selected.length}
                  <span className="text-sm font-normal text-gray-400 ml-1">
                    metric{selected.length !== 1 ? "s" : ""}
                  </span>
                </p>
              </div>
              <button
                onClick={selectAllAvailable}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium ml-3"
              >
                {selected.length > 0 ? "Clear" : "Select all available"}
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerate}
                disabled={generating || selected.length === 0}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {generating ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <BarChart3 className="w-4 h-4" />
                )}
                Generate metrics
              </button>
              <button
                onClick={handleDownload}
                disabled={downloading || selected.length === 0}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-gray-200 text-gray-700 font-medium hover:bg-gray-50 disabled:opacity-50"
              >
                {downloading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <FileDown className="w-4 h-4" />
                )}
                Download CSV
              </button>
              <button
                onClick={() => navigate(analysisPath)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700"
              >
                Continue to analysis <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {error && (
            <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">
              {error}
            </p>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-4 mt-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search metrics…"
              className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="space-y-4 mt-4">
          {Object.keys(filteredByCategory).length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-xl p-10 text-center text-gray-500">
              No metrics catalogued for {sourceType}.
            </div>
          ) : (
            Object.entries(filteredByCategory).map(([category, metrics]) => (
              <div
                key={category}
                className="bg-white border border-gray-200 rounded-xl p-5"
              >
                <h2 className="font-semibold text-gray-800 mb-3 capitalize">
                  {category}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {metrics.map((metric) => {
                    const isAvailable = availableCodes.has(metric.code);
                    const isSelected = selected.includes(metric.code);
                    const missing = missingCols[metric.code] || [];
                    return (
                      <div
                        key={metric.code}
                        onClick={() => toggleMetric(metric.code)}
                        className={`flex items-start gap-3 p-3 rounded-xl border-2 transition-all ${
                          isAvailable
                            ? isSelected
                              ? "border-blue-400 bg-blue-50/40 cursor-pointer"
                              : "border-gray-200 bg-white hover:border-blue-200 hover:bg-blue-50/20 cursor-pointer"
                            : "border-gray-100 bg-gray-50/60 cursor-not-allowed"
                        }`}
                      >
                        <div className="mt-0.5">
                          {isAvailable ? (
                            isSelected ? (
                              <CheckSquare className="w-5 h-5 text-blue-600" />
                            ) : (
                              <Square className="w-5 h-5 text-gray-300" />
                            )
                          ) : (
                            <Lock className="w-5 h-5 text-gray-300" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p
                            className={`font-medium ${
                              isAvailable ? "text-gray-800" : "text-gray-400"
                            }`}
                          >
                            {metric.name}
                          </p>
                          <p
                            className={`text-xs leading-relaxed mt-0.5 ${
                              isAvailable ? "text-gray-500" : "text-gray-300"
                            }`}
                          >
                            {metric.description}
                          </p>
                          {!isAvailable && missing.length > 0 && (
                            <div className="mt-2 flex items-start gap-1.5 text-xs text-amber-600 bg-amber-50 rounded-lg px-2.5 py-1.5">
                              <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                              <span>
                                Missing columns:{" "}
                                <span className="font-medium">
                                  {missing.join(", ")}
                                </span>
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>

        {computed && (
          <div className="mt-6 bg-white border border-gray-200 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              Computed metrics ({computed.rows?.length || 0} rows)
            </h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-200">
                    <th className="py-2 pr-4">Metric</th>
                    <th className="py-2 pr-4">Statistic</th>
                    <th className="py-2">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {(computed.rows || []).slice(0, 200).map((row, i) => (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="py-1.5 pr-4 text-gray-700">
                        {row.metric_name || row.metric_code}
                      </td>
                      <td className="py-1.5 pr-4 text-gray-500">
                        {row.statistic}
                      </td>
                      <td className="py-1.5 text-gray-700">
                        {row.value === null || row.value === ""
                          ? "—"
                          : String(row.value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {computed.rows && computed.rows.length > 200 && (
                <p className="text-xs text-gray-400 mt-2">
                  Showing first 200 of {computed.rows.length} rows. Download the
                  CSV to see them all.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
