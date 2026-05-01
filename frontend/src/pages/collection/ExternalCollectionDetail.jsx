import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  Database,
  Download,
  Plus,
  Eye,
  Trash2,
  FileJson,
  FileSpreadsheet,
  Clock,
  Github,
  GitBranch,
  Upload,
} from "lucide-react";
import { collectionService } from "../../services/api";

function ExternalCollectionDetail() {
  const { collectionId } = useParams();
  const navigate = useNavigate();

  const [collection, setCollection] = useState(null);
  const [cleanings, setCleanings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showDeleteCleaningModal, setShowDeleteCleaningModal] = useState(false);
  const [cleanedDataToDelete, setCleanedDataToDelete] = useState(null);
  const [deletingCleanedData, setDeletingCleanedData] = useState(false);

  useEffect(() => {
    fetchData();
  }, [collectionId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [collectionRes, cleanedDataRes] = await Promise.all([
        collectionService.getStatus(collectionId),
        collectionService.getCollectionCleanedData(collectionId),
      ]);
      setCollection(collectionRes.data.collection_plan);
      setCleanings(cleanedDataRes.data.cleaned_data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadJSON = async () => {
    try {
      const response = await collectionService.downloadCollectionJSON(collectionId);
      const filename = collection?.raw_data_filename || `collection_${collectionId}_raw_data.json`;
      const blob = new Blob([response.data], { type: "application/json" });

      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: filename,
            types: [{ description: "JSON Files", accept: { "application/json": [".json"] } }],
          });
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();
          return;
        } catch (err) {
          if (err.name === "AbortError") return;
        }
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert("Error downloading data: " + err.message);
    }
  };

  const handleNewCleaning = () => {
    navigate(`/external/collection/${collectionId}/cleaned-data/new`);
  };

  const handleViewCleanedData = (cleanedDataId) => {
    navigate(`/external/collection/${collectionId}/cleaned-data/${cleanedDataId}`);
  };

  const handleDownloadCleanedDataCSV = async (cleanedDataId, fileType) => {
    try {
      const cleaningItem = cleanings.find((c) => c.id === cleanedDataId);
      const actualFilename =
        fileType === "structured"
          ? cleaningItem?.structured_csv_filename
          : cleaningItem?.statistics_csv_filename;

      if (!actualFilename) {
        alert("File not available");
        return;
      }

      const response = await collectionService.downloadCleanedDataCSV(cleanedDataId, fileType);

      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: actualFilename,
            types: [{ description: "CSV Files", accept: { "text/csv": [".csv"] } }],
          });
          const writable = await handle.createWritable();
          await writable.write(response.data);
          await writable.close();
          return;
        } catch (err) {
          if (err.name === "AbortError") return;
        }
      }

      const url = window.URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = actualFilename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert("Error downloading CSV: " + err.message);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return (
      date.toLocaleDateString() +
      " " +
      date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    );
  };

  const handleDeleteCleanedData = (cleanedData) => {
    setCleanedDataToDelete(cleanedData);
    setShowDeleteCleaningModal(true);
  };

  const confirmDeleteCleanedData = async () => {
    if (!cleanedDataToDelete) return;
    try {
      setDeletingCleanedData(true);
      await collectionService.deleteCleanedData(cleanedDataToDelete.id);
      setCleanings(cleanings.filter((c) => c.id !== cleanedDataToDelete.id));
      setShowDeleteCleaningModal(false);
      setCleanedDataToDelete(null);
    } catch (err) {
      alert("Error deleting cleaned data: " + err.message);
    } finally {
      setDeletingCleanedData(false);
    }
  };

  const getPlatformIcon = () => {
    if (collection?.platform === "github") return <Github className="w-5 h-5" />;
    return <GitBranch className="w-5 h-5" />;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error || !collection) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-500">{error || "Collection not found"}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate("/data-cleaning")}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Data Cleaning</span>
        </button>

        {/* Collection Information */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">
                {collection.repository_name}
              </h1>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                  External Upload
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <Calendar className="w-4 h-4" />
                <span className="text-sm font-medium">Upload Date</span>
              </div>
              <p className="text-gray-900">{formatDate(collection.created_at)}</p>
            </div>

            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                {getPlatformIcon()}
                <span className="text-sm font-medium">Platform</span>
              </div>
              <p className="text-gray-900 capitalize">{collection.platform}</p>
            </div>

            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <Database className="w-4 h-4" />
                <span className="text-sm font-medium">Status</span>
              </div>
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-700">
                {collection.status}
              </span>
            </div>

            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">Items</span>
              </div>
              <p className="text-gray-900">
                {collection.total_items || 0}{" "}
                {collection.platform === "github" ? "PRs" : "MRs"}
              </p>
            </div>
          </div>
        </div>

        {/* Export Raw Data */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Raw Data Export</h2>
          <p className="text-gray-600 mb-4">
            Download the uploaded raw data in JSON format.
          </p>
          <button
            onClick={handleDownloadJSON}
            className="flex items-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <FileJson className="w-5 h-5" />
            Download JSON
          </button>
        </div>

        {/* History of Cleaning */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">History of Cleaning</h2>
            <button
              onClick={handleNewCleaning}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              New Cleaning
            </button>
          </div>

          {cleanings.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No cleaning operations yet</p>
              <p className="text-sm mt-1">
                Start a new cleaning to filter and structure the uploaded data
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Date Created</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Date Range Filter</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">Items</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {cleanings.map((cleaning) => (
                    <tr key={cleaning.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-600 text-sm">
                        {formatDate(cleaning.created_at)}
                      </td>
                      <td className="py-3 px-4 text-gray-600 text-sm">
                        {cleaning.start_date && cleaning.end_date
                          ? `${new Date(cleaning.start_date).toLocaleDateString()} → ${new Date(cleaning.end_date).toLocaleDateString()}`
                          : "All data"}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${
                            cleaning.status === "completed"
                              ? "bg-green-100 text-green-700"
                              : cleaning.status === "in_progress"
                              ? "bg-blue-100 text-blue-700"
                              : cleaning.status === "failed"
                              ? "bg-red-100 text-red-700"
                              : "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {cleaning.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {cleaning.stats?.merge_requests_count || cleaning.stats?.pull_requests_count || 0}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center gap-2">
                          {cleaning.status === "completed" && (
                            <>
                              <button
                                onClick={() => handleDownloadCleanedDataCSV(cleaning.id, "structured")}
                                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                title="Download structured CSV"
                              >
                                <Download className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDownloadCleanedDataCSV(cleaning.id, "statistics")}
                                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                title="Download statistics CSV"
                              >
                                <FileSpreadsheet className="w-4 h-4" />
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => handleViewCleanedData(cleaning.id)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="View details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteCleanedData(cleaning)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Delete cleaning"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Delete Cleaned Data Confirmation Modal */}
      {showDeleteCleaningModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Delete Cleaned Data</h3>
            <p className="text-gray-600 mb-2">
              Are you sure you want to delete this cleaned data?
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Created: {cleanedDataToDelete && formatDate(cleanedDataToDelete.created_at)}
            </p>
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
              <p className="text-red-700 text-sm">
                <strong>Warning:</strong> This will permanently delete all CSV files associated with
                this cleaned data. This action cannot be undone.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteCleaningModal(false);
                  setCleanedDataToDelete(null);
                }}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                disabled={deletingCleanedData}
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteCleanedData}
                disabled={deletingCleanedData}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {deletingCleanedData ? (
                  "Deleting..."
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ExternalCollectionDetail;
