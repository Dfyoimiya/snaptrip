import axios from 'axios';
import { getToken, getRefreshToken, setToken, setRefreshToken, clearAuth, isTokenExpired } from './auth';
import { message } from 'antd';

// ── Key conversion utilities ──────────────────────────────────────────────

function snakeToCamel(key: string): string {
  return key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

function camelToSnake(key: string): string {
  return key.replace(/([A-Z])/g, '_$1').toLowerCase();
}

function deepConvertKeys(obj: unknown, converter: (k: string) => string): unknown {
  if (Array.isArray(obj)) return obj.map((v) => deepConvertKeys(v, converter));
  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[converter(key)] = deepConvertKeys(value, converter);
    }
    return result;
  }
  return obj;
}

// ── Token refresh state ───────────────────────────────────────────────────

let isRefreshing = false;
let pendingRequests: Array<{ resolve: (token: string) => void; reject: (e: Error) => void }> = [];

async function doRefreshToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error('No refresh token');
  const res = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
  const { access_token, refresh_token } = res.data.data;
  setToken(access_token);
  setRefreshToken(refresh_token);
  return access_token;
}

// ── Axios instance ────────────────────────────────────────────────────────

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
});

// Request interceptor: attach token + convert camelCase → snake_case
request.interceptors.request.use(async (config) => {
  // Convert request body keys: camelCase → snake_case
  if (config.data && typeof config.data === 'object') {
    config.data = deepConvertKeys(config.data, camelToSnake);
  }
  // Convert query params too
  if (config.params && typeof config.params === 'object') {
    config.params = deepConvertKeys(config.params, camelToSnake);
  }

  const token = getToken();
  if (token && isTokenExpired(token) && !config.url?.includes('/auth/refresh')) {
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingRequests.push({
          resolve: (newToken: string) => {
            config.headers.Authorization = `Bearer ${newToken}`;
            resolve(config);
          },
          reject,
        });
      });
    }
    isRefreshing = true;
    try {
      const newToken = await doRefreshToken();
      isRefreshing = false;
      pendingRequests.forEach((r) => r.resolve(newToken));
      pendingRequests = [];
      config.headers.Authorization = `Bearer ${newToken}`;
    } catch {
      isRefreshing = false;
      pendingRequests.forEach((r) => r.reject(new Error('Token refresh failed')));
      pendingRequests = [];
      clearAuth();
      window.location.href = '#/login';
      return Promise.reject(new Error('Token expired'));
    }
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: convert snake_case → camelCase
request.interceptors.response.use(
  (response) => {
    const res = response.data;
    if (res.code !== 0) {
      message.error(res.message || 'Request failed');
      return Promise.reject(new Error(res.message));
    }
    if (res.data) {
      res.data = deepConvertKeys(res.data, snakeToCamel);
    }
    return res;
  },
  async (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/refresh')) {
      clearAuth();
      message.error('Login expired, please re-login');
      window.location.href = '#/login';
    } else {
      message.error(error.response?.data?.message || 'Network error');
    }
    return Promise.reject(error);
  },
);

export default request;
