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
  Calendar,
  Plus,
  Tag,
  BarChart3,
  Check,
  Square,
  CheckSquare
} from "lucide-react";
import { collectionService, workspaceService } from "../../services/api";
import {
  COLLECTION_FEATURES_CONFIG as FEATURES_CONFIG,
  KEYWORD_FIELD_LABELS,
} from "../../components/collection/collectionFeatureConfig";

function DataCleaning() {
  const { workspaceId, repositoryId, collectionId } = useParams();
  const navigate = useNavigate();

  const [repository, setRepository] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [collection, setCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [processing, setProcessing] = useState(false);

  // Available options
  const [availableAuthors, setAvailableAuthors] = useState([]);
  const [availableExtensions, setAvailableExtensions] = useState([]);
  const [totalItems, setTotalItems] = useState(0);

  // Selected filters
  const [selectedExtensions, setSelectedExtensions] = useState([]);
  const [selectedAuthors, setSelectedAuthors] = useState([]);

  // Keyword filters - now an array of {field, keywords}
  const [keywordFilters, setKeywordFilters] = useState([]);
  const [currentKeywordField, setCurrentKeywordField] = useState("");
  const [currentKeywords, setCurrentKeywords] = useState("");

  // Available keyword fields for selection
  const allKeywordFields = ["title", "description", "comments", "commit_message"];
  const availableKeywordFields = allKeywordFields.filter(
    field => !keywordFilters.some(filter => filter.field === field)
  );

  // Date range for cleaning (subset of collection data)
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // Feature selection
  const [selectedFeatures, setSelectedFeatures] = useState(
    FEATURES_CONFIG.map(f => f.id) // All selected by default
  );
  const [featureSearchQuery, setFeatureSearchQuery] = useState("");

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
      const isExternal = workspaceId === "0" || !workspaceId;

      const promises = [
        collectionService.getStatus(collectionId),
        collectionService.getCleaningConfig(collectionId),
      ];
      if (!isExternal) {
        promises.push(
          workspaceService.getById(workspaceId),
          workspaceService.getRepositories(workspaceId)
        );
      }

      const results = await Promise.all(promises);
      const collectionRes = results[0];
      const cleaningRes = results[1];

      setCollection(collectionRes.data.collection_plan);

      if (!isExternal) {
        setWorkspace(results[2].data);
        const repo = results[3].data.find((r) => r.id === parseInt(repositoryId));
        setRepository(repo);
      } else {
        // For external collections, create a minimal repository-like object from collection data
        const col = collectionRes.data.collection_plan;
        setRepository({ name: col.repository_name, full_name: col.repository_full_name || col.repository_name, platform: col.platform });
      }

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
      setFetchError(err.message);
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

  const handleAddKeywordFilter = () => {
    if (!currentKeywordField || !currentKeywords.trim()) return;

    const keywordsList = currentKeywords
      .split(",")
      .map((k) => k.trim())
      .filter((k) => k);

    if (keywordsList.length === 0) return;

    setKeywordFilters([
      ...keywordFilters,
      { field: currentKeywordField, keywords: keywordsList }
    ]);
    setCurrentKeywordField("");
    setCurrentKeywords("");
  };

  const handleRemoveKeywordFilter = (fieldToRemove) => {
    setKeywordFilters(keywordFilters.filter(f => f.field !== fieldToRemove));
  };

  const getFieldLabel = (field) => {
    return KEYWORD_FIELD_LABELS[field] || field;
  };

  // Feature selection helpers
  const filteredFeatures = FEATURES_CONFIG.filter(feature =>
    feature.label.toLowerCase().includes(featureSearchQuery.toLowerCase()) ||
    feature.description.toLowerCase().includes(featureSearchQuery.toLowerCase()) ||
    feature.category.toLowerCase().includes(featureSearchQuery.toLowerCase())
  );

  const toggleFeature = (featureId) => {
    if (selectedFeatures.includes(featureId)) {
      setSelectedFeatures(selectedFeatures.filter(f => f !== featureId));
    } else {
      setSelectedFeatures([...selectedFeatures, featureId]);
    }
  };

  const toggleAllFeatures = () => {
    if (selectedFeatures.length === FEATURES_CONFIG.length) {
      setSelectedFeatures([]);
    } else {
      setSelectedFeatures(FEATURES_CONFIG.map(f => f.id));
    }
  };

  const isAllSelected = selectedFeatures.length === FEATURES_CONFIG.length;
  const isSomeSelected = selectedFeatures.length > 0 && selectedFeatures.length < FEATURES_CONFIG.length;

  const handleApplyFilters = async () => {
    try {
      setProcessing(true);

      const response = await collectionService.createCleanedData({
        collection_id: parseInt(collectionId),
        start_date: startDate || null,
        end_date: endDate || null,
        filters: {
          file_extensions: selectedExtensions,
          authors: selectedAuthors,
          keyword_filters: keywordFilters,
        },
        selected_features: selectedFeatures,
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (fetchError || !repository) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{fetchError || "Failed to load collection data"}</p>
          <button
            onClick={() => { setFetchError(null); fetchData(); }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
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
                onClick={() => navigate(workspaceId === "0" || !workspaceId ? `/external/collection/${collectionId}` : `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}`)}
                className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                Back to Collection
              </button>
              {createdCleanedData && (
                <button
                  onClick={() => navigate(workspaceId === "0" || !workspaceId ? `/external/collection/${collectionId}/cleaned-data/${createdCleanedData.id}` : `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}/cleaned-data/${createdCleanedData.id}`)}
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
              workspaceId === "0" || !workspaceId
                ? `/external/collection/${collectionId}`
                : `/workspaces/${workspaceId}/repositories/${repositoryId}/collection/${collectionId}`
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
                Search in {itemTerm} titles, descriptions, comments, or commit messages. You can add multiple filters.
              </p>

              {/* Applied Keyword Filters */}
              {keywordFilters.length > 0 && (
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Applied Filters:
                  </label>
                  <div className="flex flex-wrap gap-3">
                    {keywordFilters.map((filter) => (
                      <div
                        key={filter.field}
                        className="bg-purple-50 border border-purple-200 rounded-lg p-3 flex items-start gap-3"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Tag className="w-4 h-4 text-purple-600" />
                            <span className="font-medium text-purple-900">
                              {getFieldLabel(filter.field)}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {filter.keywords.map((keyword, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-sm"
                              >
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>
                        <button
                          onClick={() => handleRemoveKeywordFilter(filter.field)}
                          className="text-purple-400 hover:text-purple-600 transition-colors"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Add New Filter */}
              {availableKeywordFields.length > 0 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select field to search in:
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {availableKeywordFields.map((field) => (
                        <button
                          key={field}
                          onClick={() => setCurrentKeywordField(field)}
                          className={`px-4 py-2 rounded-lg border transition-colors ${
                            currentKeywordField === field
                              ? "bg-purple-100 border-purple-300 text-purple-700"
                              : "bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100"
                          }`}
                        >
                          {getFieldLabel(field)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {currentKeywordField && (
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Keywords for {getFieldLabel(currentKeywordField)} (comma-separated):
                      </label>
                      <div className="flex gap-3">
                        <input
                          type="text"
                          value={currentKeywords}
                          onChange={(e) => setCurrentKeywords(e.target.value)}
                          placeholder="e.g., bug, feature, refactor"
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleAddKeywordFilter();
                            }
                          }}
                        />
                        {currentKeywords.trim() && (
                          <button
                            onClick={handleAddKeywordFilter}
                            className="px-4 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2"
                          >
                            <Plus className="w-4 h-4" />
                            Apply
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {availableKeywordFields.length === 0 && keywordFilters.length > 0 && (
                <p className="text-sm text-gray-500 italic">
                  All keyword filter fields have been applied.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Feature Selection Section */}
        <div className="mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <BarChart3 className="w-5 h-5 text-indigo-600" />
              <h3 className="text-lg font-semibold">Feature Selection</h3>
              <span className="ml-auto text-sm text-gray-500">
                {selectedFeatures.length} of {FEATURES_CONFIG.length} selected
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Select which metrics to include in the statistics CSV. Only selected features will be calculated.
            </p>

            {/* Search and Select All */}
            <div className="flex flex-col sm:flex-row gap-4 mb-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={featureSearchQuery}
                  onChange={(e) => setFeatureSearchQuery(e.target.value)}
                  placeholder="Search features..."
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <button
                onClick={toggleAllFeatures}
                className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                {isAllSelected ? (
                  <CheckSquare className="w-5 h-5 text-indigo-600" />
                ) : isSomeSelected ? (
                  <div className="w-5 h-5 border-2 border-indigo-600 rounded flex items-center justify-center">
                    <div className="w-2 h-0.5 bg-indigo-600" />
                  </div>
                ) : (
                  <Square className="w-5 h-5 text-gray-400" />
                )}
                <span className="font-medium">
                  {isAllSelected ? "Deselect All" : "Select All"}
                </span>
              </button>
            </div>

            {/* Features Table */}
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="max-h-80 overflow-y-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="w-12 px-4 py-3 text-left"></th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Feature</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 hidden md:table-cell">Description</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 hidden lg:table-cell">Category</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {filteredFeatures.map((feature) => (
                      <tr
                        key={feature.id}
                        onClick={() => toggleFeature(feature.id)}
                        className={`cursor-pointer transition-colors ${
                          selectedFeatures.includes(feature.id)
                            ? "bg-indigo-50 hover:bg-indigo-100"
                            : "hover:bg-gray-50"
                        }`}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-center">
                            {selectedFeatures.includes(feature.id) ? (
                              <CheckSquare className="w-5 h-5 text-indigo-600" />
                            ) : (
                              <Square className="w-5 h-5 text-gray-300" />
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-sm font-medium ${
                            selectedFeatures.includes(feature.id)
                              ? "text-indigo-900"
                              : "text-gray-900"
                          }`}>
                            {feature.label}
                          </span>
                          <p className="text-xs text-gray-500 md:hidden mt-1">
                            {feature.description}
                          </p>
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell">
                          <span className="text-sm text-gray-600">{feature.description}</span>
                        </td>
                        <td className="px-4 py-3 hidden lg:table-cell">
                          <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                            feature.category === 'Time Metrics' ? 'bg-blue-100 text-blue-700' :
                            feature.category === 'Code Metrics' ? 'bg-green-100 text-green-700' :
                            feature.category === 'Collaboration' ? 'bg-purple-100 text-purple-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {feature.category}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {filteredFeatures.length === 0 && (
              <p className="text-center text-gray-500 py-4">
                No features match your search.
              </p>
            )}
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
