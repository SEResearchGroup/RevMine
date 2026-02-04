/**
 * Unit Tests for JWT Utility Functions
 */
import {
  isTokenExpired,
  isTokenExpiringSoon,
  getToken,
  setToken,
  removeToken,
  getRefreshToken,
  setRefreshToken,
  clearTokens,
} from './jwt.js';

describe('JWT Utilities', () => {
  beforeEach(() => {
    // Clear the mock localStorage
    global.localStorage.getItem.mockClear();
    global.localStorage.setItem.mockClear();
    global.localStorage.removeItem.mockClear();
  });

  describe('isTokenExpired', () => {
    it('returns true for null token', () => {
      expect(isTokenExpired(null)).toBe(true);
    });

    it('returns true for undefined token', () => {
      expect(isTokenExpired(undefined)).toBe(true);
    });

    it('returns true for empty token', () => {
      expect(isTokenExpired('')).toBe(true);
    });

    it('returns true for expired token', () => {
      // Token with exp in the past
      const expiredPayload = { exp: Math.floor(Date.now() / 1000) - 3600 };
      const expiredToken = `header.${btoa(JSON.stringify(expiredPayload))}.signature`;
      expect(isTokenExpired(expiredToken)).toBe(true);
    });

    it('returns false for valid token', () => {
      // Token with exp in the future
      const validPayload = { exp: Math.floor(Date.now() / 1000) + 3600 };
      const validToken = `header.${btoa(JSON.stringify(validPayload))}.signature`;
      expect(isTokenExpired(validToken)).toBe(false);
    });

    it('returns true for malformed token', () => {
      expect(isTokenExpired('invalid-token')).toBe(true);
    });
  });

  describe('isTokenExpiringSoon', () => {
    it('returns true for token expiring within 5 minutes', () => {
      const soonPayload = { exp: Math.floor(Date.now() / 1000) + 120 }; // 2 minutes
      const soonToken = `header.${btoa(JSON.stringify(soonPayload))}.signature`;
      expect(isTokenExpiringSoon(soonToken)).toBe(true);
    });

    it('returns false for token not expiring soon', () => {
      const laterPayload = { exp: Math.floor(Date.now() / 1000) + 3600 }; // 1 hour
      const laterToken = `header.${btoa(JSON.stringify(laterPayload))}.signature`;
      expect(isTokenExpiringSoon(laterToken)).toBe(false);
    });
  });

  describe('Token Storage Functions', () => {
    it('getToken retrieves from localStorage', () => {
      localStorage.getItem.mockReturnValue('test-token');
      expect(getToken()).toBe('test-token');
      expect(localStorage.getItem).toHaveBeenCalledWith('jwt');
    });

    it('setToken stores in localStorage', () => {
      setToken('new-token');
      expect(localStorage.setItem).toHaveBeenCalledWith('jwt', 'new-token');
    });

    it('removeToken removes from localStorage', () => {
      removeToken();
      expect(localStorage.removeItem).toHaveBeenCalledWith('jwt');
    });

    it('getRefreshToken retrieves refresh token', () => {
      localStorage.getItem.mockReturnValue('refresh-token');
      expect(getRefreshToken()).toBe('refresh-token');
      expect(localStorage.getItem).toHaveBeenCalledWith('refresh_token');
    });

    it('setRefreshToken stores refresh token', () => {
      setRefreshToken('new-refresh');
      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'new-refresh');
    });

    it('clearTokens removes both tokens', () => {
      clearTokens();
      expect(localStorage.removeItem).toHaveBeenCalledWith('jwt');
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token');
    });
  });
});
