import type { SearchParams, SearchResponse, Source, HealthResponse } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "";
const API_PREFIX = `${BASE_URL}/api/v1`;

async function request<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${API_PREFIX}${path}`, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const resp = await fetch(url.toString(), {
    headers: { "Accept": "application/json" },
    signal: AbortSignal.timeout(15_000),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`API ${resp.status}: ${text || resp.statusText}`);
  }

  return resp.json() as Promise<T>;
}

// ── endpoints

export async function searchTerms(params: SearchParams): Promise<SearchResponse> {
  return request<SearchResponse>("/search", {
    q: params.q,
    source: params.source || undefined,
    page: params.page ?? 1,
    limit: params.limit ?? 20,
  });
}

export async function fetchSources(): Promise<Source[]> {
  return request<Source[]>("/sources");
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}
