export const isTokenExpired = (token) => {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
};

export const isTokenExpiringSoon = (token) => {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const fiveMinutes = 5 * 60 * 1000;
    return payload.exp * 1000 < Date.now() + fiveMinutes;
  } catch {
    return true;
  }
};

// Access token
export const getToken = () => localStorage.getItem('jwt');
export const setToken = (token) => localStorage.setItem('jwt', token);
export const removeToken = () => localStorage.removeItem('jwt');

// Refresh token
export const getRefreshToken = () => localStorage.getItem('refresh_token');
export const setRefreshToken = (token) => localStorage.setItem('refresh_token', token);
export const removeRefreshToken = () => localStorage.removeItem('refresh_token');

export const clearTokens = () => {
  removeToken();
  removeRefreshToken();
};
