export const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://medidiag-production.up.railway.app';

const TOKEN_KEY = 'medidiag_token';
let inMemoryToken = null;
try {
  inMemoryToken = sessionStorage.getItem(TOKEN_KEY);
} catch {
  // sessionStorage unavailable (e.g. private browsing) -- fall back to memory-only.
}

export function getToken() {
  return inMemoryToken;
}

export function setToken(token) {
  inMemoryToken = token || null;
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // sessionStorage unavailable -- token still works for this page load via memory.
  }
}

/**
 * Central fetch wrapper. Attaches the bearer token automatically, parses
 * JSON, and throws a normal Error with the backend's message on failure so
 * every caller can just try/catch and show err.message.
 */
async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errBody = await res.json();
      detail = errBody.detail || detail;
    } catch {
      // response wasn't JSON; keep the generic message
    }
    if (res.status === 401) {
      // Token missing/expired/invalid -- clear it so the app treats the user as logged out.
      setToken(null);
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => request(path, { method: 'GET' }),
  post: (path, body, opts = {}) => request(path, { method: 'POST', body, ...opts }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  delete: (path) => request(path, { method: 'DELETE' }),
};
