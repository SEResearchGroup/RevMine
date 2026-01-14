import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  Download,
  FileSpreadsheet,
  Clock,
  Database,
  Settings,
} from "lucide-react";
import { collectionService } from "../../services/api";

function CleaningDetail() {
  const { workspaceId, repositoryId, collectionId, cleanedDataId } = useParams();
  const navigate = useNavigate();

  const [cleanedData, setCleanedData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCleanedDataDetails();
  }, [cleanedDataId]);

  const fetchCleanedDataDetails = async () => {
    try {
      setLoading(true);
      const response = await collectionService.getCleanedDataDetail(cleanedDataId);
      setCleanedData(response.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCSV = async (fileType) => {
    try {
      // Get the actual filename from cleanedData
      const actualFilename = fileType === 'structured' 
        ? cleanedData.structured_csv_filename 
        : cleanedData.statistics_csv_filename;
      
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error || !cleanedData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-500">{error || "Cleaned data not found"}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}`)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Collection</span>
        </button>

        {/* Cleaned Data Information */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h1 className="text-2xl font-semibold text-gray-900 mb-6">
            Cleaned Data Details
          </h1>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">Created At</span>
              </div>
              <p className="text-gray-900">{formatDate(cleanedData.created_at)}</p>
            </div>

            <div>
              <div className="flex items-center gap-2 text-gray-600 mb-2">
                <Database className="w-4 h-4" />
                <span className="text-sm font-medium">Status</span>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                cleanedData.status === 'completed' ? 'bg-green-100 text-green-700' :
                cleanedData.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                cleanedData.status === 'failed' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {cleanedData.status}
              </span>
            </div>
          </div>

          {/* Statistics */}
          {cleanedData.stats && Object.keys(cleanedData.stats).length > 0 && (
            <div className="pt-6 border-t border-gray-200">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Statistics</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(cleanedData.stats).map(([key, value]) => {
                  if (key.includes('_count') || typeof value === 'number') {
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

        {/* Date Range Filter */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-5 h-5 text-gray-700" />
            <h2 className="text-xl font-semibold text-gray-900">Date Range Filter</h2>
          </div>

          {cleanedData.start_date || cleanedData.end_date ? (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Start Date</p>
                  <p className="text-lg font-medium text-gray-900">
                    {cleanedData.start_date
                      ? new Date(cleanedData.start_date).toLocaleDateString()
                      : "Not set"}
                  </p>
                </div>
                <div className="text-gray-400 text-2xl px-4">→</div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">End Date</p>
                  <p className="text-lg font-medium text-gray-900">
                    {cleanedData.end_date
                      ? new Date(cleanedData.end_date).toLocaleDateString()
                      : "Not set"}
                  </p>
                </div>
              </div>
              <p className="text-sm text-gray-600 mt-3">
                Data has been filtered to include only items within this date range
              </p>
            </div>
          ) : (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-gray-600">No date range filter applied - all data included</p>
            </div>
          )}
        </div>

        {/* Configuration */}
        {cleanedData.config && Object.keys(cleanedData.config).length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-5 h-5 text-gray-700" />
              <h2 className="text-xl font-semibold text-gray-900">Configuration</h2>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4">
              <pre className="text-sm text-gray-700 overflow-x-auto">
                {JSON.stringify(cleanedData.config, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* Download Section */}
        {cleanedData.status === 'completed' && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Download Cleaned Data
            </h2>
            <p className="text-gray-600 mb-6">
              Download the processed data in CSV format. Two files are available:
              structured data and statistical summaries.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-gray-200 rounded-lg p-4 hover:border-green-300 transition-colors">
                <div className="flex items-center gap-3 mb-3">
                  <FileSpreadsheet className="w-6 h-6 text-green-600" />
                  <div>
                    <h3 className="font-medium text-gray-900">Structured Data</h3>
                    <p className="text-sm text-gray-600">
                      {cleanedData.structured_csv_filename || "structured_data.csv"}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDownloadCSV('structured')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download className="w-5 h-5" />
                  Download Structured CSV
                </button>
              </div>

              <div className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                <div className="flex items-center gap-3 mb-3">
                  <FileSpreadsheet className="w-6 h-6 text-blue-600" />
                  <div>
                    <h3 className="font-medium text-gray-900">Statistics</h3>
                    <p className="text-sm text-gray-600">
                      {cleanedData.statistics_csv_filename || "statistics.csv"}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDownloadCSV('statistics')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Download className="w-5 h-5" />
                  Download Statistics CSV
                </button>
              </div>
            </div>
            <div className="flex flex-col justify-center items-center border border-gray-200 rounded-lg p-4 hover:border-green-300 transition-colors mt-6">
                <div className="flex items-center items-center gap-3 mb-3">
                  <FileSpreadsheet className="w-6 h-6 text-green-600" />
                  <div className="text-center">
                    <h3 className="font-medium text-gray-900">Analyze the results</h3>
                    <p className="text-sm text-gray-600">
                      {cleanedData.structured_csv_filename || "structured_data.csv"}
                    </p>
                  </div>
                </div>
                <button
                // TODO : change here and implement the revmine analysis link
                  onClick={() => handleDownloadCSV('structured')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <span>📊</span>
                  Analyze in Revmine
                </button>
              </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default CleaningDetail;
