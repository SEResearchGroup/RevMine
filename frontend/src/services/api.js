import axios from "axios";

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
      const token = localStorage.getItem("jwt");
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
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem("jwt");
        window.location.href = "/login";
      }
      return Promise.reject(error);
    }
  );

  return instance;
};

export const authApi = createApiInstance("http://localhost:8000/api/auth");
export const workspaceApi = createApiInstance("http://localhost:8000/api/workspaces");

export const authService = {
  register: (email, password, sendUpdates) => {
    return authApi.post("/register", { email, password, sendUpdates });
  },
  login: (email, password) => {
    return authApi.post("/login", { email, password });
  },
  logout: () => {
    return authApi.post("/logout");
  },
};

// Services workspace
export const workspaceService = {
  getAll: () => {
    return workspaceApi.get("/");
  },
  getById: (id) => {
    return workspaceApi.get(`/${id}`);
  },
  create: (data) => {
    return workspaceApi.post("/", data);
  },
  update: (id, data) => {
    return workspaceApi.put(`/${id}`, data);
  },
  delete: (id) => {
    return workspaceApi.delete(`/${id}`);
  },
};

// Vous pouvez ajouter d'autres services ici
export default {
  auth: authService,
  workspace: workspaceService,
};
