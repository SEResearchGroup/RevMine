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

      if (originalRequest._retry) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (error.response?.status === 401) {
        const isAuthEndpoint =
          originalRequest?.url?.includes("/login") ||
          originalRequest?.url?.includes("/register") ||
          originalRequest?.url?.includes("/token/refresh");

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
          const response = await axios.post(`${baseURL}/token/refresh/`, {
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

export const authApi = createApiInstance("http://localhost:8000/api/auth");
export const api = createApiInstance(import.meta.env.VITE_API_URL || 'http://localhost:8000/api');
export const workspaceApi = createApiInstance(
  "http://localhost:8000/api/workspaces"
);
export const collectionApi = createApiInstance(
  "http://localhost:8000/api/collections"
);
export const analysisApi = createApiInstance(
  "http://localhost:8000/api/analysis"
);

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
  getAll: () => {
    return workspaceApi.get("/");
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
    return collectionApi.post("/start", {
      workspace_id: workspaceId,
      repository_id: repositoryId,
    });
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
    return collectionApi.post('/cleaned-data/', data);
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
};

export const analyzeApi = createApiInstance(
  "http://localhost:8003/api/analyze"
);

export const analyzeService = {
  // Create new analysis
  createAnalysis: async (formData) => {
    const response = await analysisApi.post("/create/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  // Get all analyses with optional filters
  getAnalyses: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.workspace_id)
      params.append("workspace_id", filters.workspace_id);
    if (filters.repository_id)
      params.append("repository_id", filters.repository_id);
    if (filters.status) params.append("status", filters.status);

    const response = await analysisApi.get(
      `/${params.toString() ? "?" + params.toString() : ""}`
    );
    return response.data;
  },

  // Get specific analysis details with results
  getAnalysisById: async (analysisId) => {
    const response = await analysisApi.get(`/${analysisId}/`);
    return response.data;
  },

  // Delete an analysis
  deleteAnalysis: async (analysisId) => {
    const response = await analysisApi.delete(`/${analysisId}/`);
    return response.data;
  },

  // Get all datasets with optional filters
  getDatasets: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.workspace_id)
      params.append("workspace_id", filters.workspace_id);
    if (filters.repository_id)
      params.append("repository_id", filters.repository_id);

    const response = await analysisApi.get(
      `/datasets/${params.toString() ? "?" + params.toString() : ""}`
    );
    return response.data;
  },

  // Get specific dataset
  getDatasetById: async (datasetId) => {
    const response = await analysisApi.get(`/datasets/${datasetId}/`);
    return response.data;
  },

  // Delete a dataset
  deleteDataset: async (datasetId) => {
    const response = await analysisApi.delete(`/datasets/${datasetId}/`);
    return response.data;
  },

  // Get specific result
  getResultById: async (resultId) => {
    const response = await analysisApi.get(`/results/${resultId}/`);
    return response.data;
  },

  exportSingleChart: async (analysisId) => {
    const response = await analysisApi.get(`/analyses/${analysisId}/export/`);
    return response.data;
  },

  exportPdfReport: async (analysisId) => {
    const response = await analysisApi.get(`/analyses/${analysisId}/export/`);
    return response.data;
  },
};

export default {
  auth: authService,
  workspace: workspaceService,
  collection: collectionService,
  analyze: analyzeService,
};
