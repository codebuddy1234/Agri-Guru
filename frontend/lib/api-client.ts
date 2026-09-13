"use client";

import type {
  ApiFailure,
  Farm,
  FarmerProfile,
  PaginatedSuccess,
  PlatformModule,
  Prediction,
  PredictionHistoryItem,
  PredictionInput,
  TokenPair,
  User,
} from "@/types/api";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ACCESS_KEY = "agriguru.access_token";
const REFRESH_KEY = "agriguru.refresh_token";

/**
 * Every failure the UI has to handle, carrying the backend's error code so a
 * component can map it to a translated message rather than showing the raw
 * (English-only) message from the server.
 */
export class ApiClientError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly details: { field: string | null; message: string }[] = [],
    readonly requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiClientError";
  }

  /** Field name -> first message, for attaching errors to form inputs. */
  fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const d of this.details) {
      if (d.field && !(d.field in out)) out[d.field] = d.message;
    }
    return out;
  }
}

// --- token storage -----------------------------------------------------------
// sessionStorage/localStorage is a deliberate Phase 1 choice, documented in
// docs/API.md: httpOnly cookies are the stronger option but need the API and
// the frontend on one origin (or configured SameSite + CSRF protection),
// which is a Phase 2 deployment concern.

export const tokenStore = {
  get access(): string | null {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(ACCESS_KEY);
    } catch {
      return null;
    }
  },
  get refresh(): string | null {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(REFRESH_KEY);
    } catch {
      return null;
    }
  },
  set(tokens: TokenPair) {
    try {
      window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
      window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    } catch {
      /* private mode or blocked storage: the session just will not persist */
    }
  },
  clear() {
    try {
      window.localStorage.removeItem(ACCESS_KEY);
      window.localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* ignore */
    }
  },
};

// --- core request ------------------------------------------------------------

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  /** Internal: prevents an infinite refresh loop. */
  _retried?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, _retried = false } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const token = tokenStore.access;
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // fetch only rejects on a network-level failure, so this is genuinely
    // "cannot reach the server" rather than an application error.
    throw new ApiClientError("NETWORK", "Cannot reach the server.", 0);
  }

  // A 401 on an authenticated call may just be an expired access token.
  // Try the refresh token once before forcing the farmer to sign in again.
  if (response.status === 401 && auth && !_retried && tokenStore.refresh) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return request<T>(path, { ...options, _retried: true });
    }
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiClientError(
      "INTERNAL_ERROR",
      "The server returned an unreadable response.",
      response.status,
    );
  }

  if (!response.ok) {
    const failure = payload as ApiFailure;
    const err = failure?.error;
    throw new ApiClientError(
      err?.code ?? "INTERNAL_ERROR",
      err?.message ?? "Request failed.",
      response.status,
      err?.details ?? [],
      err?.request_id ?? null,
    );
  }

  return payload as T;
}

async function tryRefresh(): Promise<boolean> {
  const refresh_token = tokenStore.refresh;
  if (!refresh_token) return false;
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) {
      tokenStore.clear();
      return false;
    }
    const data = (await res.json()) as { data: { tokens: TokenPair } };
    tokenStore.set(data.data.tokens);
    return true;
  } catch {
    return false;
  }
}

// --- endpoints ---------------------------------------------------------------

interface AuthPayload {
  user: User;
  profile: { full_name: string; preferred_language: string } | null;
  tokens: TokenPair;
}

export const api = {
  async register(input: {
    email: string;
    password: string;
    full_name: string;
    mobile?: string;
    preferred_language: string;
    district?: string;
    taluka?: string;
    village?: string;
  }): Promise<AuthPayload> {
    const res = await request<{ data: AuthPayload }>("/auth/register", {
      method: "POST",
      body: input,
      auth: false,
    });
    tokenStore.set(res.data.tokens);
    return res.data;
  },

  async login(email: string, password: string): Promise<AuthPayload> {
    const res = await request<{ data: AuthPayload }>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    tokenStore.set(res.data.tokens);
    return res.data;
  },

  logout() {
    tokenStore.clear();
  },

  async me(): Promise<{
    user: User;
    full_name: string | null;
    preferred_language: string | null;
    has_profile: boolean;
  }> {
    const res = await request<{ data: any }>("/auth/me");
    return res.data;
  },

  async getProfile(): Promise<FarmerProfile> {
    const res = await request<{ data: FarmerProfile }>("/farmer/profile");
    return res.data;
  },

  async updateProfile(patch: Partial<FarmerProfile>): Promise<FarmerProfile> {
    const res = await request<{ data: FarmerProfile }>("/farmer/profile", {
      method: "PUT",
      body: patch,
    });
    return res.data;
  },

  async listFarms(): Promise<Farm[]> {
    const res = await request<{ data: Farm[] }>("/farmer/farms");
    return res.data;
  },

  async createFarm(input: {
    name: string;
    area_value: number;
    area_unit: string;
    soil_type?: string;
    irrigation_source?: string;
  }): Promise<Farm> {
    const res = await request<{ data: Farm }>("/farmer/farms", {
      method: "POST",
      body: input,
    });
    return res.data;
  },

  async predict(input: PredictionInput): Promise<Prediction> {
    const res = await request<{ data: { prediction: Prediction } }>(
      "/crop-recommendation/predict",
      { method: "POST", body: input },
    );
    return res.data.prediction;
  },

  async history(limit = 20, offset = 0): Promise<PaginatedSuccess<PredictionHistoryItem>> {
    return request<PaginatedSuccess<PredictionHistoryItem>>(
      `/crop-recommendation/history?limit=${limit}&offset=${offset}`,
    );
  },

  async historyDetail(id: string): Promise<Prediction> {
    const res = await request<{ data: { prediction: Prediction } }>(
      `/crop-recommendation/history/${id}`,
    );
    return res.data.prediction;
  },

  async modules(): Promise<PlatformModule[]> {
    const res = await request<{ data: PlatformModule[] }>("/modules");
    return res.data;
  },
};
