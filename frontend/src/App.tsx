import { useState } from "react";
import { SearchBar }     from "./components/SearchBar";
import { SearchResults } from "./components/SearchResults";
import { SourceFilter }  from "./components/SourceFilter";
import { AskPanel }      from "./components/AskPanel";
import { useSearch }     from "./hooks/useSearch";

type Mode = "search" | "ask";

export default function App() {
  const [mode, setMode] = useState<Mode>("search");
  const {
    data, loading, error, query, source, page,
    search, setPage, setSource, reset,
  } = useSearch();

  const hasSearched = Boolean(query) && mode === "search";

  const handleModeChange = (next: Mode) => {
    setMode(next);
    if (next === "search") reset();
  };

  return (
    <div className={`app${hasSearched ? " app--results" : ""}`}>
      <header className="app-header">
        <div className="logo-wrap">
          <span className="logo-icon" aria-hidden="true">🔬</span>
          <h1 className="logo-title">SUS Search</h1>
          {!hasSearched && mode === "search" && (
            <p className="logo-subtitle">
              Mecanismo de busca unificado para terminologias oficiais do SUS
            </p>
          )}
        </div>

        <div className="mode-toggle" role="group" aria-label="Modo de interação">
          <button
            className={`mode-btn${mode === "search" ? " active" : ""}`}
            onClick={() => handleModeChange("search")}
            aria-pressed={mode === "search"}
          >
            🔍 Buscar
          </button>
          <button
            className={`mode-btn${mode === "ask" ? " active" : ""}`}
            onClick={() => handleModeChange("ask")}
            aria-pressed={mode === "ask"}
          >
            💬 Perguntar
          </button>
        </div>

        {mode === "search" && (
          <>
            <SearchBar
              initialValue={query}
              loading={loading}
              onSearch={(q) => search(q, source, 1)}
            />
            {hasSearched && (
              <SourceFilter selected={source} onChange={setSource} />
            )}
          </>
        )}
      </header>

      {/* Hero — tela inicial */}
      {!hasSearched && mode === "search" && (
        <section className="hero-sources">
          <p className="hero-label">Fontes indexadas</p>
          <div className="hero-chips">
            <span className="hero-chip sigtap">SIGTAP — Procedimentos SUS</span>
            <span className="hero-chip cid10">CID-10 — Classificação de Doenças</span>
            <span className="hero-chip ciap2">CIAP-2 — Atenção Primária</span>
            <span className="hero-chip cnes">CNES — Estabelecimentos</span>
          </div>
          <p className="hero-hint">
            Busque por nome, código ou descrição — ex: "pneumonia", "J18", "P76", "0309050022"
          </p>
        </section>
      )}

      <main className="app-main">
        {mode === "search" && (
          <SearchResults
            data={data}
            loading={loading}
            error={error}
            query={query}
            page={page}
            onPageChange={setPage}
          />
        )}
        {mode === "ask" && <AskPanel />}
      </main>

      <footer className="app-footer">
        <p>
          Dados: SIGTAP · CID-10 · CIAP-2 · CNES — Ministério da Saúde / WONCA ·{" "}
          <a href="/api/v1/health" target="_blank" rel="noopener noreferrer">
            API Status
          </a>
        </p>
        <p className="footer-academic">
          <a
            href="https://github.com/cesaraugustomt/SUS-Search"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/cesaraugustomt/SUS-Search
          </a>
          {" "}· PPGINFOS/UFSC · GNU AGPL v3
        </p>
      </footer>
    </div>
  );
}
