import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  GitBranch,
  Database,
  Download,
  Plus,
  Eye,
  Trash2,
  FileJson,
  FileSpreadsheet,
  Clock,
} from "lucide-react";
import { collectionService, workspaceService } from "../../services/api";

function CollectionDetail() {
  const { workspaceId, repositoryId, collectionId } = useParams();
  const navigate = useNavigate();

  const [collection, setCollection] = useState(null);
  const [repository, setRepository] = useState(null);
  const [cleanings, setCleanings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Delete cleaning modal state
  const [showDeleteCleaningModal, setShowDeleteCleaningModal] = useState(false);
  const [cleanedDataToDelete, setCleanedDataToDelete] = useState(null);
  const [deletingCleanedData, setDeletingCleanedData] = useState(false);

  useEffect(() => {
    fetchCollectionData();
  }, [collectionId]);

  const fetchCollectionData = async () => {
    try {
      setLoading(true);
      const [collectionRes, reposRes, cleanedDataRes] = await Promise.all([
        collectionService.getStatus(collectionId),
        workspaceService.getRepositories(workspaceId),
        collectionService.getCollectionCleanedData(collectionId),
      ]);

      setCollection(collectionRes.data.collection_plan);
      const repo = reposRes.data.find((r) => r.id === parseInt(repositoryId));
      setRepository(repo);
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
      
      // Use filename from collection data (loaded from API) or fallback to header/default
      let filename = collection?.raw_data_filename || `collection_${collectionId}_raw_data.json`;
      
      // Try to get from Content-Disposition header as fallback
      if (!collection?.raw_data_filename) {
        const contentDisposition = response.headers['content-disposition'];
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?([^";\n]+)"?/);
          if (filenameMatch && filenameMatch[1]) {
            filename = filenameMatch[1];
          }
        }
      }
      
      const blob = new Blob([response.data], { type: 'application/json' });
      
      // Check if showSaveFilePicker is available (modern browsers)
      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: filename,
            types: [{
              description: 'JSON Files',
              accept: { 'application/json': ['.json'] },
            }],
          });
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();
          return;
        } catch (err) {
          // User cancelled or API not supported, fallback to download
          if (err.name === 'AbortError') return;
        }
      }
      
      // Fallback for browsers that don't support showSaveFilePicker
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
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
    navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}/cleaned-data/new`);
  };

  const handleViewCleanedData = (cleanedDataId) => {
    navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}/cleaned-data/${cleanedDataId}`);
  };

  const handleDownloadCleanedDataCSV = async (cleanedDataId, fileType) => {
    try {
      // Find the cleaning object to get the actual filename
      const cleaningItem = cleanings.find(c => c.id === cleanedDataId);
      const actualFilename = fileType === 'structured' 
        ? cleaningItem?.structured_csv_filename 
        : cleaningItem?.statistics_csv_filename;
      
      if (!actualFilename) {
        alert('File not available');
        return;
      }

      const response = await collectionService.downloadCleanedDataCSV(cleanedDataId, fileType);
      
      // Try to use File System Access API for "Save As" dialog
      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: actualFilename,
            types: [{
              description: 'CSV Files',
              accept: { 'text/csv': ['.csv'] }
            }]
          });
          const writable = await handle.createWritable();
          await writable.write(response.data);
          await writable.close();
          return;
        } catch (err) {
          // User cancelled or API not supported, fall back to regular download
          if (err.name === 'AbortError') return;
        }
      }
      
      // Fallback for browsers that don't support File System Access API
      const url = window.URL.createObjectURL(response.data);
      const a = document.createElement('a');
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
    return date.toLocaleDateString() + " " + date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
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
      setCleanings(cleanings.filter(c => c.id !== cleanedDataToDelete.id));
      setShowDeleteCleaningModal(false);
      setCleanedDataToDelete(null);
    } catch (err) {
      alert("Error deleting cleaned data: " + err.message);
    } finally {
      setDeletingCleanedData(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error || !collection || !repository) {
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
          onClick={() => navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collect`)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to {repository.name}</span>
        </button>

        {/* Collection Information */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h1 className="text-2xl font-semibold text-gray-900 mb-6">
            Collection Details
          </h1>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <Calendar className="w-4 h-4" />
                <span className="text-sm font-medium">Collection Date</span>
              </div>
              <p className="text-gray-900">
                {formatDate(collection.completed_at || collection.started_at)}
              </p>
            </div>

            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <GitBranch className="w-4 h-4" />
                <span className="text-sm font-medium">Branch</span>
              </div>
              <p className="text-gray-900">{collection.branch_name || "-"}</p>
            </div>

            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <Database className="w-4 h-4" />
                <span className="text-sm font-medium">Status</span>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                collection.status === 'completed' ? 'bg-green-100 text-green-700' :
                collection.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                collection.status === 'failed' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {collection.status}
              </span>
            </div>

            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">Data Range</span>
              </div>
              <p className="text-gray-900">
                {(() => {
                  const parseDate = (dateStr) => {
                    if (!dateStr) return null;
                    // Handle DD/MM/YYYY format
                    if (dateStr.includes('/')) {
                      const parts = dateStr.split('/');
                      if (parts.length === 3) {
                        // Assume DD/MM/YYYY format
                        return new Date(parts[2], parts[1] - 1, parts[0]);
                      }
                    }
                    // Handle ISO format or other standard formats
                    return new Date(dateStr);
                  };
                  
                  const startDate = collection.filters?.start_date || collection.stats?.start_date;
                  const endDate = collection.filters?.end_date || collection.stats?.end_date;
                  if (startDate) {
                    const parsedStart = parseDate(startDate);
                    const parsedEnd = parseDate(endDate);
                    const startStr = parsedStart && !isNaN(parsedStart) ? parsedStart.toLocaleDateString() : startDate;
                    const endStr = parsedEnd && !isNaN(parsedEnd) ? parsedEnd.toLocaleDateString() : (endDate || "Now");
                    return `${startStr} → ${endStr}`;
                  }
                  return "All time";
                })()}
              </p>
            </div>
          </div>

          {/* Statistics */}
          {collection.stats && Object.keys(collection.stats).length > 0 && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Statistics</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(collection.stats).map(([key, value]) => {
                  if (key.includes('_count')) {
                    const label = key.replace('_count', '').replace(/_/g, ' ');
                    return (
                      <div key={key} className="bg-gray-50 rounded-lg p-4">
                        <div className="text-2xl font-bold text-gray-900">{value}</div>
                        <div className="text-sm text-gray-600 capitalize">{label}</div>
                      </div>
                    );
                  }
                  return null;
                })}
              </div>
            </div>
          )}
        </div>

        {/* Export Raw Data */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Raw Data Export
          </h2>
          <p className="text-gray-600 mb-4">
            Download the complete raw data collected from the repository in JSON format.
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
            <h2 className="text-xl font-semibold text-gray-900">
              History of Cleaning
            </h2>
            <button
              onClick={handleNewCleaning}
              disabled={collection.status !== 'completed'}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
                Start a new cleaning to filter and structure the collected data
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Date Created
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Date Range Filter
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Status
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      Items
                    </th>
                    <th className="text-center py-3 px-4 font-medium text-gray-700">
                      Actions
                    </th>
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
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          cleaning.status === 'completed' ? 'bg-green-100 text-green-700' :
                          cleaning.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          cleaning.status === 'failed' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {cleaning.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-900">
                        {cleaning.stats?.merge_requests_count || cleaning.stats?.pull_requests_count || 0}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center gap-2">
                          {cleaning.status === 'completed' && (
                            <>
                              <button
                                onClick={() => handleDownloadCleanedDataCSV(cleaning.id, 'structured')}
                                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                                title="Download structured CSV"
                              >
                                <Download className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDownloadCleanedDataCSV(cleaning.id, 'statistics')}
                                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                title="Download statistics CSV"
                              >
                                <FileSpreadsheet className="w-4 h-4" />
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => handleViewCleanedData(cleaning.id)}
                            className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
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
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Delete Cleaned Data
            </h3>
            <p className="text-gray-600 mb-2">
              Are you sure you want to delete this cleaned data?
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Created: {cleanedDataToDelete && formatDate(cleanedDataToDelete.created_at)}
            </p>
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
              <p className="text-red-700 text-sm">
                <strong>Warning:</strong> This will permanently delete all CSV files associated with this cleaned data. This action cannot be undone.
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

export default CollectionDetail;
