// ── Tipos de domínio do SUS Search

export type SourceCode = "SIGTAP" | "CID10" | "CNES" | "CIAP2";

export interface Term {
  id: number;
  code: string | null;
  name: string;
  description: string | null;
  source: SourceCode;
  category: string | null;
  subcategory: string | null;
  additional_info: Record<string, unknown>;
  official_url: string | null;
  source_competency: string | null;
  last_updated: string | null;
  created_at: string | null;
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  limit: number;
  pages: number;
  results: Term[];
}

export interface Source {
  code: SourceCode;
  name: string;
  description: string | null;
  official_url: string | null;
  competency: string | null;
  record_count: number;
  loaded_at: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  total_terms: number;
}

export interface SearchParams {
  q: string;
  source?: SourceCode | "";
  page?: number;
  limit?: number;
}
