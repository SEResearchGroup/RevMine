import axios from 'axios';
import {
  getToken,
  setToken,
  getRefreshToken,
  clearTokens,
  isTokenExpired
} from '../utils/jwt';

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

const trimTrailingSlash = (value) => value.replace(/\/+$/, "");

export const API_BASE_URL = trimTrailingSlash(
  import.meta.env.VITE_API_URL || "http://localhost:8000/api"
);

const serviceUrl = (path) => `${API_BASE_URL}/${path.replace(/^\/+/, "")}`;

export const AUTH_API_URL = serviceUrl("auth");

export const getApiErrorMessage = (error, fallback = "An unexpected error occurred") => {
  const data = error?.response?.data;

  if (!data || typeof data === "string") {
    return fallback;
  }

  if (data.error || data.message || data.detail) {
    return data.error || data.message || data.detail;
  }

  const fieldErrors = Object.values(data)
    .flat()
    .filter(Boolean)
    .join(" ");

  return fieldErrors || fallback;
};

const createApiInstance = (baseURL) => {
  const instance = axios.create({
    baseURL,
    timeout: 10000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  instance.interceptors.request.use(
    (config) => {
      const token = getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;

      if (!originalRequest) {
        return Promise.reject(error);
      }

      if (originalRequest._retry) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (error.response?.status === 401) {
        const isAuthEndpoint =
          originalRequest?.url?.includes("/login") ||
          originalRequest?.url?.includes("/register") ||
          originalRequest?.url?.includes("/token/refresh") ||
          originalRequest?.url?.includes("/refresh");

        if (isAuthEndpoint) {
          return Promise.reject(error);
        }

        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then(token => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return instance(originalRequest);
            })
            .catch(err => {
              return Promise.reject(err);
            });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        const refreshToken = getRefreshToken();

        if (!refreshToken || isTokenExpired(refreshToken)) {
          clearTokens();
          window.location.href = "/login";
          return Promise.reject(error);
        }

        try {
          const response = await axios.post(`${AUTH_API_URL}/refresh`, {
            refresh: refreshToken
          });

          const { access } = response.data;
          setToken(access);

          instance.defaults.headers.common['Authorization'] = `Bearer ${access}`;
          originalRequest.headers.Authorization = `Bearer ${access}`;

          processQueue(null, access);

          return instance(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          clearTokens();
          window.location.href = "/login";
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      return Promise.reject(error);
    }
  );

  return instance;
};

export const authApi = createApiInstance(AUTH_API_URL);
export const api = createApiInstance(API_BASE_URL);
export const workspaceApi = createApiInstance(serviceUrl("workspaces"));
export const collectionApi = createApiInstance(serviceUrl("collections"));
export const analysisApi = createApiInstance(serviceUrl("analysis"));
export const notificationApi = createApiInstance(serviceUrl("notifications"));

export const authService = {
  register: (email, password, sendUpdates, firstName, lastName, position) => {
    return authApi.post("/register", {
      email,
      password,
      sendUpdates,
      first_name: firstName,
      last_name: lastName,
      position,
    });
  },
  login: (email, password) => {
    return authApi.post("/login", { email, password });
  },
  getOAuthUrl: (provider) => {
    return authApi.get(`/oauth/${provider}`);
  },
  completeOAuth: (provider, code) => {
    return authApi.get(`/oauth/${provider}/callback`, { params: { code } });
  },
  logout: () => {
    return authApi.post("/logout");
  },
  getUserInfo: () => {
    return authApi.get("/me");
  },
  updateProfile: (data) => {
    return authApi.patch('/me/update/', data);
  },
  replaceProfile: (data) => {
      return authApi.put('/me/update/', data);
  },
  changePassword: (oldPassword, newPassword, newPasswordConfirm) => {
    return authApi.post('/me/change-password/', {
      old_password: oldPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    });
  },
  deleteAccount: () => {
    return authApi.delete('/me/delete/');
  },
};

export const workspaceService = {
  getAll: (params = {}) => {
    return workspaceApi.get("/", { params });
  },

  getById: (id) => {
    return workspaceApi.get(`/${id}`);
  },

  testConnection: (data) => {
    return workspaceApi.post("/test/", data);
  },

  create: (data) => {
    return workspaceApi.post("/", data);
  },

  update: (id, data) => {
    return workspaceApi.patch(`/${id}/`, data);
  },

  delete: (id) => {
    return workspaceApi.delete(`/${id}/`);
  },

  getRemoteRepositories: (workspaceId) => {
    return workspaceApi.get(`/${workspaceId}/remote-repositories/`);
  },

  importRepositories: (workspaceId, data) => {
    return workspaceApi.post(`/${workspaceId}/repositories/import/`, data);
  },

  getRepositories: (workspaceId) => {
    return workspaceApi.get(`/${workspaceId}/repositories/`);
  },

  getAllRepositories: (params = {}) => {
    return workspaceApi.get("/repositories/all/", { params });
  },
};

export const collectionService = {
  // Get available metrics WITHOUT creating a collection
  getAvailableMetrics: (repositoryId, platform) => {
    return collectionApi.get(`/metrics/?repository_id=${repositoryId}&platform=${platform}`);
  },

  // Get branches for a repository WITHOUT creating a collection
  getBranchesForRepository: (workspaceId, repositoryId) => {
    return collectionApi.post("/branches/", {
      workspace_id: workspaceId,
      repository_id: repositoryId,
    });
  },

  // Start/create collection plan (only called when user clicks "Go to collect plan")
  startCollection: (workspaceId, repositoryId) => {
    return collectionApi.post("/start/", {
      workspace_id: workspaceId,
      repository_id: repositoryId,
    });
  },

  generateAutomationDraft: (data) => {
    return collectionApi.post("/automation/preview/", data, { timeout: 60000 });
  },

  // Get branches for an existing collection plan
  getBranches: (planId) => {
    return collectionApi.get(`/plans/${planId}/branches/`);
  },

  // Configure metrics, filters, and branch
  configureMetrics: (planId, data) => {
    return collectionApi.post(`/plans/${planId}/configure/`, data);
  },

  // Validate collection plan
  validatePlan: (planId) => {
    return collectionApi.get(`/plans/${planId}/validate/`);
  },

  // Execute collection
  executeCollection: (planId) => {
    return collectionApi.post(`/plans/${planId}/execute/`);
  },

  // Resume collection
  resumeCollection: (planId) => {
    return collectionApi.post(`/plans/${planId}/resume/`);
  },

  // Pause collection (keep data for later resume)
  pauseCollection: (planId) => {
    return collectionApi.post(`/plans/${planId}/pause/`);
  },

  // Get collection status
  getStatus: (planId) => {
    return collectionApi.get(`/plans/${planId}/status/`);
  },

  // Get collected data
  getData: (planId) => {
    return collectionApi.get(`/plans/${planId}/data/`);
  },

  // Data cleaning and structuring
  getCleaningConfig: (planId) => {
    return collectionApi.get(`/plans/${planId}/cleaning-config/`);
  },

  applyFilters: (planId, data) => {
    return collectionApi.post(`/plans/${planId}/apply-filters/`, data);
  },

  // List all plans
  getAllPlans: () => {
    return collectionApi.get("/plans/");
  },

  // Get collection history for a repository
  getHistory: (repositoryId) => {
    return collectionApi.get(`/history/${repositoryId}/`);
  },

  // Collection management
  downloadCollectionJSON: (collectionId) => {
    return collectionApi.get(`/collections/${collectionId}/download/`, {
      responseType: 'blob'
    });
  },

  deleteCollection: (collectionId) => {
    return collectionApi.delete(`/collections/${collectionId}/delete/`);
  },

  // CleanedData operations
  getCollectionCleanedData: (collectionId) => {
    return collectionApi.get(`/collections/${collectionId}/cleaned-data/`);
  },

  createCleanedData: (data) => {
    return collectionApi.post('/cleaned-data/', data, { timeout: 300000 });
  },

  getCleanedDataDetail: (cleanedDataId) => {
    return collectionApi.get(`/cleaned-data/${cleanedDataId}/`);
  },

  deleteCleanedData: (cleanedDataId) => {
    return collectionApi.delete(`/cleaned-data/${cleanedDataId}/`);
  },

  downloadCleanedDataCSV: (cleanedDataId, fileType) => {
    return collectionApi.get(`/cleaned-data/${cleanedDataId}/download/${fileType}/`, {
      responseType: 'blob'
    });
  },

  getUserDatasets: async () => {
    const response = await collectionApi.get('/datasets/');
    return response.data;
  },

  getCleanedForAnalysis: async (search = "") => {
    const params = search ? `?search=${encodeURIComponent(search)}` : "";
    const response = await collectionApi.get(`/cleaned-for-analysis/${params}`);
    return response.data;
  },

  uploadExternalCollection: (file, platform, name, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('platform', platform);
    formData.append('name', name);
    return collectionApi.post('/upload-external/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 1800000, // 30 minutes – large files up to 5 GB
      onUploadProgress,
    });
  },
};

export const analyzeApi = createApiInstance(
  serviceUrl("analysis")
);

export const analyzeService = {
  // ========== DATASETS ==========
  getDatasets: async () => {
    const response = await analyzeApi.get('/datasets/');
    return response.data;
  },

  uploadDataset: async (file, metadata = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    Object.keys(metadata).forEach(key => {
      formData.append(key, metadata[key]);
    });
    const response = await analyzeApi.post('/datasets/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return response.data;
  },

  getDatasetById: async (datasetId) => {
    const response = await analyzeApi.get(`/datasets/${datasetId}/`);
    return response.data;
  },

  deleteDataset: async (datasetId) => {
    const response = await analyzeApi.delete(`/datasets/${datasetId}/`);
    return response.data;
  },

  getDatasetColumns: async (datasetId) => {
    const response = await analyzeApi.get(`/datasets/${datasetId}/columns/`);
    return response.data;
  },

  getAvailableMetrics: async (datasetId) => {
    const response = await analyzeApi.get(`/datasets/${datasetId}/available_metrics/`);
    return response.data;
  },

  getCompatibleAxes: async (datasetId) => {
    const response = await analyzeApi.get(`/datasets/${datasetId}/compatible_axes/`);
    return response.data;
  },

  previewDataset: async (datasetId) => {
    const response = await analyzeApi.get(`/datasets/${datasetId}/preview/`);
    return response.data;
  },

  // ========== METRICS ==========
  getMetrics: async () => {
    const response = await analyzeApi.get('/metrics/');
    return response.data;
  },

  getMetricById: async (metricId) => {
    const response = await analyzeApi.get(`/metrics/${metricId}/`);
    return response.data;
  },

  getMetricCategories: async () => {
    const response = await analyzeApi.get('/metrics/categories/');
    return response.data;
  },

  getMetricsByCategory: async (sourceType) => {
    const url = sourceType
      ? `/metrics/by_category/?source_type=${encodeURIComponent(sourceType)}`
      : '/metrics/by_category/';
    const response = await analyzeApi.get(url);
    return response.data;
  },

  // ========== GENERATE (core endpoint) ==========
  generateChart: async (payload) => {
    const response = await analyzeApi.post('/generate/', payload, { timeout: 120000 });
    return response.data;
  },

  previewAnalysisPrompt: async (payload) => {
    const response = await analyzeApi.post('/automation/preview/', payload, {
      timeout: 60000,
    });
    return response.data;
  },

  // ========== ANALYSES ==========
  getAnalyses: async (datasetId = null) => {
    let url = '/analyses/';
    if (datasetId) url += `?dataset_id=${datasetId}`;
    const response = await analyzeApi.get(url);
    return response.data;
  },

  bulkCreateAnalyses: async (datasetId, analyses) => {
    const response = await analyzeApi.post('/analyses/bulk_create/', {
      dataset_id: datasetId,
      analyses,
    }, { timeout: 300000 });
    return response.data;
  },

  getAnalysisById: async (analysisId) => {
    const response = await analyzeApi.get(`/analyses/${analysisId}/`);
    return response.data;
  },

  deleteAnalysis: async (analysisId) => {
    const response = await analyzeApi.delete(`/analyses/${analysisId}/`);
    return response.data;
  },

  getAnalysisResult: async (analysisId) => {
    const response = await analyzeApi.get(`/analyses/${analysisId}/result/`);
    return response.data;
  },

  retryAnalysis: async (analysisId) => {
    const response = await analyzeApi.post(`/analyses/${analysisId}/retry/`);
    return response.data;
  },

  // ========== HISTORY (panel page) ==========
  getAnalysisHistory: async (workspaceId = null) => {
    let url = '/analyses/history/';
    if (workspaceId) url += `?workspace_id=${workspaceId}`;
    const response = await analyzeApi.get(url);
    return response.data;
  },

  // ========== DATASET SUMMARY ==========
  getDatasetSummary: async (datasetId) => {
    const response = await analyzeApi.get(`/datasets/${datasetId}/summary/`);
    return response.data;
  },
};

// ============================================================
// DevOps: Kanban (GitHub Projects v2 + GitLab Issue Boards)
// ============================================================
export const kanbanService = {
  listBoards: async (payload) => {
    const response = await analyzeApi.post('/devops/kanban/boards/', payload, {
      timeout: 60000,
    });
    return response.data;
  },

  startCollection: async (payload) => {
    // Async: the server kicks off a background job and returns a job
    // descriptor (status + progress fields). Poll getJobStatus until the
    // status is "completed" / "failed".
    const response = await analyzeApi.post('/devops/kanban/collect/', payload, {
      timeout: 60000,
    });
    return response.data;
  },

  getJobStatus: async (jobId) => {
    const response = await analyzeApi.get(`/devops/jobs/${jobId}/status/`);
    return response.data;
  },

  listDatasets: async () => {
    const response = await analyzeApi.get('/devops/datasets/?source_type=kanban');
    return response.data;
  },

  listMetrics: async () => {
    const response = await analyzeApi.get('/metrics/by_category/?source_type=kanban');
    return response.data;
  },

  // List workspaces + their imported repositories. Reuses the existing
  // configuration-service endpoints so the user picks from repos that
  // already have a stored OAuth token.
  listWorkspaceRepos: async () => {
    const response = await workspaceApi.get('/repositories/all/');
    return response.data;
  },

  downloadDataset: async (datasetId, format = 'csv') => {
    const response = await analyzeApi.get(
      `/devops/datasets/${datasetId}/download/?format=${format}`,
      { responseType: 'blob' }
    );
    return response.data; // Blob
  },

  computeMetrics: async (datasetId, metricCodes) => {
    const response = await analyzeApi.post(
      `/devops/datasets/${datasetId}/compute-metrics/`,
      { metric_codes: metricCodes },
      { timeout: 300000 }
    );
    return response.data;
  },

  downloadMetricsCSV: async (datasetId, metricCodes) => {
    const response = await analyzeApi.post(
      `/devops/datasets/${datasetId}/compute-metrics/csv/`,
      { metric_codes: metricCodes },
      { responseType: 'blob', timeout: 300000 }
    );
    return response.data;
  },
};

// ============================================================
// DevOps: CI/CD (GitHub Actions + GitLab CI)
// ============================================================
export const cicdService = {
  listPipelines: async (payload) => {
    const response = await analyzeApi.post('/devops/cicd/pipelines/', payload, {
      timeout: 60000,
    });
    return response.data;
  },

  startCollection: async (payload) => {
    const response = await analyzeApi.post('/devops/cicd/collect/', payload, {
      timeout: 60000,
    });
    return response.data;
  },

  getJobStatus: async (jobId) => {
    const response = await analyzeApi.get(`/devops/jobs/${jobId}/status/`);
    return response.data;
  },

  listDatasets: async () => {
    const response = await analyzeApi.get('/devops/datasets/?source_type=cicd');
    return response.data;
  },

  listMetrics: async () => {
    const response = await analyzeApi.get('/metrics/by_category/?source_type=cicd');
    return response.data;
  },

  listWorkspaceRepos: async () => {
    const response = await workspaceApi.get('/repositories/all/');
    return response.data;
  },

  downloadDataset: async (datasetId, format = 'csv') => {
    const response = await analyzeApi.get(
      `/devops/datasets/${datasetId}/download/?format=${format}`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  computeMetrics: async (datasetId, metricCodes) => {
    const response = await analyzeApi.post(
      `/devops/datasets/${datasetId}/compute-metrics/`,
      { metric_codes: metricCodes },
      { timeout: 300000 }
    );
    return response.data;
  },

  downloadMetricsCSV: async (datasetId, metricCodes) => {
    const response = await analyzeApi.post(
      `/devops/datasets/${datasetId}/compute-metrics/csv/`,
      { metric_codes: metricCodes },
      { responseType: 'blob', timeout: 300000 }
    );
    return response.data;
  },
};

export const notificationService = {
  getAll: (limit = 20, offset = 0) => {
    return notificationApi.get(`/?limit=${limit}&offset=${offset}`);
  },
  getUnreadCount: () => {
    return notificationApi.get("/unread-count");
  },
  markAsRead: (id) => {
    return notificationApi.patch(`/${id}/read`);
  },
  markAllAsRead: () => {
    return notificationApi.patch("/read-all");
  },
  delete: (id) => {
    return notificationApi.delete(`/${id}`);
  },
};

export default {
  auth: authService,
  workspace: workspaceService,
  collection: collectionService,
  analyze: analyzeService,
  kanban: kanbanService,
  cicd: cicdService,
  notification: notificationService,
};
