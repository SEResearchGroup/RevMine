export const isTokenExpired = (token) => {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
};

export const getToken = () => localStorage.getItem('jwt');
export const setToken = (token) => localStorage.setItem('jwt', token);
export const removeToken = () => localStorage.removeItem('jwt');