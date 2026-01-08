import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Filter,
  FileCode,
  User,
  Search,
  CheckCircle,
  X,
  Github,
  GitBranch,
  FolderGit2,
  Calendar
} from "lucide-react";
import { collectionService, workspaceService } from "../../services/api";

function DataCleaning() {
  const { workspaceId, repositoryId, collectionId } = useParams();
  const navigate = useNavigate();

  const [repository, setRepository] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [collection, setCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  // Available options
  const [availableAuthors, setAvailableAuthors] = useState([]);
  const [availableExtensions, setAvailableExtensions] = useState([]);
  const [totalItems, setTotalItems] = useState(0);

  // Selected filters
  const [selectedExtensions, setSelectedExtensions] = useState([]);
  const [selectedAuthors, setSelectedAuthors] = useState([]);
  const [keywordField, setKeywordField] = useState("title");
  const [keywords, setKeywords] = useState("");
  
  // Date range for cleaning (subset of collection data)
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // Results
  const [previewData, setPreviewData] = useState(null);
  const [showResults, setShowResults] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  const [createdCleanedData, setCreatedCleanedData] = useState(null);

  useEffect(() => {
    fetchData();
  }, [collectionId]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [wsRes, reposRes, collectionRes, cleaningRes] = await Promise.all([
        workspaceService.getById(workspaceId),
        workspaceService.getRepositories(workspaceId),
        collectionService.getStatus(collectionId),
        collectionService.getCleaningConfig(collectionId),
      ]);

      setWorkspace(wsRes.data);
      const repo = reposRes.data.find((r) => r.id === parseInt(repositoryId));
      setRepository(repo);
      setCollection(collectionRes.data.collection_plan);

      setAvailableAuthors(cleaningRes.data.available_filters.authors);
      setAvailableExtensions(cleaningRes.data.available_filters.file_extensions);
      setTotalItems(cleaningRes.data.total_items);
      
      // Set default date range from collection filters
      if (collectionRes.data.collection_plan.filters) {
        setStartDate(collectionRes.data.collection_plan.filters.start_date || "");
        setEndDate(collectionRes.data.collection_plan.filters.end_date || "");
      }
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleExtension = (ext) => {
    if (selectedExtensions.includes(ext)) {
      setSelectedExtensions(selectedExtensions.filter((e) => e !== ext));
    } else {
      setSelectedExtensions([...selectedExtensions, ext]);
    }
  };

  const toggleAuthor = (author) => {
    if (selectedAuthors.includes(author)) {
      setSelectedAuthors(selectedAuthors.filter((a) => a !== author));
    } else {
      setSelectedAuthors([...selectedAuthors, author]);
    }
  };

  const handleApplyFilters = async () => {
    try {
      setProcessing(true);

      const keywordsList = keywords
        .split(",")
        .map((k) => k.trim())
        .filter((k) => k);

      const response = await collectionService.createCleanedData({
        collection_id: parseInt(collectionId),
        start_date: startDate || null,
        end_date: endDate || null,
        filters: {
          file_extensions: selectedExtensions,
          authors: selectedAuthors,
          keyword_field: keywordField,
          keywords: keywordsList,
        }
      });

      // Show success message instead of redirecting
      setSuccessMessage(response.data.message || "Cleaning and Filtering Successful");
      setCreatedCleanedData(response.data.cleaned_data);
      setShowResults(true);
    } catch (err) {
      alert("Error creating cleaned data: " + err.message);
    } finally {
      setProcessing(false);
    }
  };

  const platform = repository?.platform || "github";
  const itemTerm = platform === "github" ? "PR" : "MR";

  if (loading || !repository) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  // Show success result page
  if (showResults && successMessage) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          {/* Success Message */}
          <div className="bg-green-50 border border-green-200 rounded-xl p-8 mb-6">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-green-900">{successMessage}</h2>
                <p className="text-green-700 mt-1">Your data has been cleaned and filtered successfully.</p>
              </div>
            </div>

            {createdCleanedData && (
              <div className="bg-white rounded-lg p-4 mb-6">
                <h3 className="font-semibold text-gray-900 mb-3">CleanedData Details</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">ID:</span>
                    <span className="ml-2 font-medium">{createdCleanedData.id}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Status:</span>
                    <span className="ml-2 px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                      {createdCleanedData.status}
                    </span>
                  </div>
                  {createdCleanedData.stats && (
                    <>
                      <div>
                        <span className="text-gray-600">Items:</span>
                        <span className="ml-2 font-medium">
                          {createdCleanedData.stats.merge_requests_count || createdCleanedData.stats.pull_requests_count || 0}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            <div className="flex gap-4">
              <button
                onClick={() => navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}`)}
                className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                Back to Collection
              </button>
              {createdCleanedData && (
                <button
                  onClick={() => navigate(`/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}/cleaned-data/${createdCleanedData.id}`)}
                  className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  View CleanedData Details
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <button
          onClick={() =>
            navigate(
              `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}`
            )
          }
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to collection</span>
        </button>

        {/* Project Info */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
              {platform === "github" ? (
                <Github className="w-8 h-8" />
              ) : (
                <GitBranch className="w-8 h-8" />
              )}
            </div>

            <div className="flex-1">
              <h1 className="text-2xl font-semibold text-gray-900 mb-2">
                {repository.name}
              </h1>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <FolderGit2 className="w-4 h-4" />
                <span>{repository.full_name}</span>
              </div>
              <p className="text-gray-600 mt-2">
                Total {itemTerm}s collected: <strong>{totalItems}</strong>
              </p>
            </div>
          </div>
        </div>

        {/* Data Cleaning & Filtering */}
        <div className="mb-6">
          <h2 className="text-2xl font-semibold mb-6">Data Cleaning & Filtering</h2>

          {/* Date Range Section */}
          {collection && collection.filters && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
              <div className="flex items-center gap-3 mb-4">
                <Calendar className="w-5 h-5 text-blue-600" />
                <h3 className="text-lg font-semibold">Date Range Filter</h3>
              </div>
              <p className="text-sm text-gray-700 mb-4">
                Collection data range: {collection.filters.start_date ? new Date(collection.filters.start_date).toLocaleDateString() : "Not set"} → {collection.filters.end_date ? new Date(collection.filters.end_date).toLocaleDateString() : "Now"}
              </p>
              <p className="text-sm text-gray-600 mb-4">
                You can narrow down this range for the cleaning operation:
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Start Date (optional)
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    min={collection.filters.start_date || ""}
                    max={endDate || collection.filters.end_date || ""}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    End Date (optional)
                  </label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    min={startDate || collection.filters.start_date || ""}
                    max={collection.filters.end_date || ""}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Filter Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Filter 1: File Extensions */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <FileCode className="w-5 h-5 text-blue-600" />
                <h3 className="text-lg font-semibold">Filter by File Extensions</h3>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Include only {itemTerm}s that modified specific file types
              </p>

              <div className="flex flex-wrap gap-2">
                {availableExtensions.map((ext) => (
                  <button
                    key={ext}
                    onClick={() => toggleExtension(ext)}
                    className={`px-3 py-1.5 rounded-lg border ${
                      selectedExtensions.includes(ext)
                        ? "bg-blue-100 border-blue-300 text-blue-700"
                        : "bg-gray-50 border-gray-300 text-gray-700"
                    }`}
                  >
                    {ext}
                  </button>
                ))}
              </div>
            </div>

            {/* Filter 2: Authors */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <User className="w-5 h-5 text-green-600" />
                <h3 className="text-lg font-semibold">Filter by Authors</h3>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Choose authors of {itemTerm}s
              </p>

              <div className="max-h-48 overflow-y-auto">
                {availableAuthors.map((author) => (
                  <label
                    key={author}
                    className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded-lg cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedAuthors.includes(author)}
                      onChange={() => toggleAuthor(author)}
                      className="w-5 h-5 text-blue-600"
                    />
                    <span className="text-gray-700">{author}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Filter 3: Keywords */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 md:col-span-2">
              <div className="flex items-center gap-3 mb-4">
                <Search className="w-5 h-5 text-purple-600" />
                <h3 className="text-lg font-semibold">Filter by Keywords</h3>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Search in {itemTerm} titles, descriptions, or commit messages
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Search in:
                  </label>
                  <div className="flex gap-4">
                    {["title", "description", "comments"].map((field) => (
                      <label key={field} className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="keyword_field"
                          value={field}
                          checked={keywordField === field}
                          onChange={(e) => setKeywordField(e.target.value)}
                          className="w-4 h-4 text-blue-600"
                        />
                        <span className="text-gray-700 capitalize">{field}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Keywords (comma-separated):
                  </label>
                  <input
                    type="text"
                    value={keywords}
                    onChange={(e) => setKeywords(e.target.value)}
                    placeholder="e.g., bug, feature, refactor"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Apply Button */}
        <button
          onClick={handleApplyFilters}
          disabled={processing}
          className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
        >
          {processing ? (
            "Creating cleaning..."
          ) : (
            <>
              <Filter className="w-5 h-5" />
              Create New Cleaning
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default DataCleaning;