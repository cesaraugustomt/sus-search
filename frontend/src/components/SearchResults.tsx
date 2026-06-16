import type { SearchResponse } from "../types";
import { ResultCard } from "./ResultCard";
import { Pagination } from "./Pagination";
import { EmptyState } from "./EmptyState";
import { LoadingSpinner } from "./LoadingSpinner";

interface SearchResultsProps {
  data: SearchResponse | null;
  loading: boolean;
  error: string | null;
  query: string;
  page: number;
  onPageChange: (page: number) => void;
}

export function SearchResults({
  data,
  loading,
  error,
  query,
  page,
  onPageChange,
}: SearchResultsProps) {
  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="error-state" role="alert">
        <p className="error-title">Erro ao buscar resultados</p>
        <p className="error-msg">{error}</p>
        <p className="error-hint">
          Verifique se a API está disponível em{" "}
          <code>/api/v1/health</code> e tente novamente.
        </p>
      </div>
    );
  }

  if (!data) return null;

  if (data.total === 0) return <EmptyState query={query} />;

  return (
    <section className="results-section" aria-label="Resultados da busca">
      <p className="results-summary">
        {data.total.toLocaleString("pt-BR")} resultado
        {data.total !== 1 ? "s" : ""} para <strong>"{data.query}"</strong>
      </p>

      <div className="results-list">
        {data.results.map((term) => (
          <ResultCard key={term.id} term={term} />
        ))}
      </div>

      <Pagination
        page={page}
        pages={data.pages}
        total={data.total}
        limit={data.limit}
        onPageChange={onPageChange}
      />
    </section>
  );
}
