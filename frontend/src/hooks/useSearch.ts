import { useState, useCallback, useRef } from "react";
import { searchTerms } from "../services/api";
import type { SearchResponse, SourceCode } from "../types";

interface UseSearchState {
  data: SearchResponse | null;
  loading: boolean;
  error: string | null;
  query: string;
  source: SourceCode | "";
  page: number;
}

interface UseSearchActions {
  search: (q: string, src?: SourceCode | "", pg?: number) => void;
  setPage: (pg: number) => void;
  setSource: (src: SourceCode | "") => void;
  reset: () => void;
}

export function useSearch(): UseSearchState & UseSearchActions {
  const [state, setState] = useState<UseSearchState>({
    data: null, loading: false, error: null, query: "", source: "", page: 1,
  });
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback(
    async (q: string, src: SourceCode | "" = state.source, pg: number = 1) => {
      if (!q.trim() || q.trim().length < 2) return;
      abortRef.current?.abort();
      abortRef.current = new AbortController();
      setState((prev) => ({ ...prev, loading: true, error: null, query: q, source: src, page: pg }));
      try {
        const data = await searchTerms({ q: q.trim(), source: src || undefined, page: pg });
        setState((prev) => ({ ...prev, data, loading: false }));
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        const message = err instanceof Error ? err.message : "Erro desconhecido";
        setState((prev) => ({ ...prev, error: message, loading: false }));
      }
    },
    [state.source]
  );

  const setPage = useCallback(
    (pg: number) => search(state.query, state.source, pg),
    [search, state.query, state.source]
  );

  const setSource = useCallback(
    (src: SourceCode | "") => {
      if (state.query) search(state.query, src, 1);
      else setState((prev) => ({ ...prev, source: src }));
    },
    [search, state.query]
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null, query: "", source: "", page: 1 });
  }, []);

  return { ...state, search, setPage, setSource, reset };
}
