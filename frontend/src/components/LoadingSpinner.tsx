export function LoadingSpinner() {
  return (
    <div className="loading-wrap" role="status" aria-live="polite" aria-label="Carregando resultados">
      <div className="spinner" aria-hidden="true" />
      <p className="loading-text">Buscando…</p>
    </div>
  );
}
