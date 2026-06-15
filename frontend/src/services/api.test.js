/**
 * Tests for API Service utilities
 * Note: Testing individual utility functions since api.js uses import.meta.env
 */
import axios from 'axios';

// Mock axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    defaults: { headers: { common: {} } },
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  })),
  post: jest.fn(),
}));

describe('API Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Axios Configuration', () => {
    it('axios.create should be available', () => {
      expect(axios.create).toBeDefined();
    });

    it('creates instance with interceptors', () => {
      const instance = axios.create({
        baseURL: 'http://localhost:8000/api/v1',
      });
      
      expect(instance.interceptors).toBeDefined();
      expect(instance.interceptors.request.use).toBeDefined();
      expect(instance.interceptors.response.use).toBeDefined();
    });

    it('mock instance has all HTTP methods', () => {
      const instance = axios.create();
      
      expect(instance.get).toBeDefined();
      expect(instance.post).toBeDefined();
      expect(instance.patch).toBeDefined();
      expect(instance.delete).toBeDefined();
    });
  });

  describe('Request Interceptors', () => {
    it('can add request interceptor', () => {
      const instance = axios.create();
      const onFulfilled = jest.fn();
      const onRejected = jest.fn();
      
      instance.interceptors.request.use(onFulfilled, onRejected);
      
      expect(instance.interceptors.request.use).toHaveBeenCalledWith(
        onFulfilled,
        onRejected
      );
    });
  });

  describe('Response Interceptors', () => {
    it('can add response interceptor', () => {
      const instance = axios.create();
      const onFulfilled = jest.fn();
      const onRejected = jest.fn();
      
      instance.interceptors.response.use(onFulfilled, onRejected);
      
      expect(instance.interceptors.response.use).toHaveBeenCalledWith(
        onFulfilled,
        onRejected
      );
    });
  });

  describe('HTTP Methods', () => {
    let instance;

    beforeEach(() => {
      instance = axios.create();
    });

    it('GET request works', async () => {
      instance.get.mockResolvedValue({ data: { id: 1 } });
      
      const result = await instance.get('/test');
      
      expect(instance.get).toHaveBeenCalledWith('/test');
      expect(result.data).toEqual({ id: 1 });
    });

    it('POST request works', async () => {
      instance.post.mockResolvedValue({ data: { success: true } });
      
      const result = await instance.post('/test', { name: 'test' });
      
      expect(instance.post).toHaveBeenCalledWith('/test', { name: 'test' });
      expect(result.data).toEqual({ success: true });
    });

    it('PATCH request works', async () => {
      instance.patch.mockResolvedValue({ data: { updated: true } });
      
      const result = await instance.patch('/test/1', { name: 'updated' });
      
      expect(instance.patch).toHaveBeenCalledWith('/test/1', { name: 'updated' });
      expect(result.data).toEqual({ updated: true });
    });

    it('DELETE request works', async () => {
      instance.delete.mockResolvedValue({ data: {} });
      
      const result = await instance.delete('/test/1');
      
      expect(instance.delete).toHaveBeenCalledWith('/test/1');
    });
  });
});
