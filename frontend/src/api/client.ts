/**
 * Typed API client.
 *
 * One place knows about HTTP, tokens and the error envelope. Everything else
 * calls typed functions and handles `ApiError`.
 */

import { firebaseEnabled, getIdToken } from '@/state/firebase';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

const ACCESS_TOKEN_KEY = 'pyforge.access_token';
const REFRESH_TOKEN_KEY = 'pyforge.refresh_token';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {},
    public readonly correlationId?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** Whether retrying the same request could plausibly succeed. */
  get isTransient(): boolean {
    return this.status >= 500 || this.status === 429;
  }
}

export const tokens = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  /** Internal: prevents infinite recursion when the refresh call itself 401s. */
  skipRefresh?: boolean;
}

async function parseError(response: Response): Promise<ApiError> {
  let code = `http_${response.status}`;
  let message = response.statusText || 'Request failed';
  let details: Record<string, unknown> = {};
  let correlationId = response.headers.get('X-Correlation-ID') ?? undefined;
  try {
    const body = await response.json();
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details ?? {};
      correlationId = body.error.correlation_id ?? correlationId;
    }
  } catch {
    // A non-JSON error body (a proxy page, say) — keep the status-derived message.
  }
  return new ApiError(response.status, code, message, details, correlationId);
}

let refreshInFlight: Promise<boolean> | null = null;

/** Exchange the refresh token for a new pair. Concurrent callers share one attempt. */
async function refreshTokens(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  const refresh = tokens.refresh;
  if (!refresh) return false;

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) {
        tokens.clear();
        return false;
      }
      const body = await response.json();
      tokens.set(body.access_token, body.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

/**
 * The bearer token for the next request.
 *
 * With Firebase configured the server verifies Firebase ID tokens directly, so
 * we send one of those and let the Firebase module handle expiry. Otherwise we
 * send the access token this application's own `/api/auth/login` issued.
 */
async function bearerToken(): Promise<string | null> {
  return firebaseEnabled ? getIdToken() : tokens.access;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, skipRefresh = false } = options;

  const url = new URL(`${BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const access = await bearerToken();
  if (access) headers.Authorization = `Bearer ${access}`;

  const response = await fetch(url.toString(), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  // Firebase tokens are refreshed proactively by `getIdToken`, so a 401 there
  // is a real rejection rather than staleness — only the local scheme retries.
  if (!firebaseEnabled && response.status === 401 && !skipRefresh && tokens.refresh) {
    if (await refreshTokens()) {
      return request<T>(path, { ...options, skipRefresh: true });
    }
  }

  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions['query']) => request<T>(path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
