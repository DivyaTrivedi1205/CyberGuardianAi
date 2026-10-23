export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
export const AUTH_TOKEN_KEY = 'cyberguardian-auth-token';
export const AUTH_USER_KEY = 'cyberguardian-auth-user';

export async function readJsonResponse(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const headers = {};
  
  // Set json content type only if body is not FormData
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  // Merge custom headers overriding defaults
  Object.assign(headers, options.headers || {});
  
  if (headers['Content-Type'] === undefined) {
    delete headers['Content-Type'];
  }

  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const payload = await readJsonResponse(response);

  if (!response.ok) {
    const message = payload?.detail || payload?.message || 'Something went wrong.';
    throw new Error(message);
  }

  return payload;
}
