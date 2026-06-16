interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  limit: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pages, total, limit, onPageChange }: PaginationProps) {
  if (pages <= 1) return null;

  const from = (page - 1) * limit + 1;
  const to = Math.min(page * limit, total);

  const pageNumbers = () => {
    const nums: (number | "…")[] = [];
    if (pages <= 7) {
      for (let i = 1; i <= pages; i++) nums.push(i);
    } else {
      nums.push(1);
      if (page > 3) nums.push("…");
      for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) nums.push(i);
      if (page < pages - 2) nums.push("…");
      nums.push(pages);
    }
    return nums;
  };

  return (
    <nav className="pagination" aria-label="Paginação dos resultados">
      <p className="pagination-info">
        Exibindo {from}–{to} de {total.toLocaleString("pt-BR")} resultados
      </p>
      <div className="pagination-controls">
        <button
          className="page-btn"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          aria-label="Página anterior"
        >
          ‹
        </button>

        {pageNumbers().map((n, i) =>
          n === "…" ? (
            <span key={`sep-${i}`} className="page-sep">…</span>
          ) : (
            <button
              key={n}
              className={`page-btn${page === n ? " active" : ""}`}
              onClick={() => onPageChange(n as number)}
              aria-current={page === n ? "page" : undefined}
            >
              {n}
            </button>
          )
        )}

        <button
          className="page-btn"
          onClick={() => onPageChange(page + 1)}
          disabled={page === pages}
          aria-label="Próxima página"
        >
          ›
        </button>
      </div>
    </nav>
  );
}
