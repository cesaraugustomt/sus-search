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
        {/* Logo */}
        <div className="logo-wrap">
          <span className="logo-icon" aria-hidden="true">🔬</span>
          <h1 className="logo-title">SUS Search</h1>
          {!hasSearched && mode === "search" && (
            <p className="logo-subtitle">
              Mecanismo de busca unificado para informações oficiais do SUS
            </p>
          )}
        </div>

        {/* Toggle de modo */}
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

        {/* Barra de busca — só no modo busca */}
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

      {/* Hero — só na tela inicial do modo busca */}
      {!hasSearched && mode === "search" && (
        <section className="hero-sources">
          <p className="hero-label">Fontes disponíveis</p>
          <div className="hero-chips">
            <span className="hero-chip sigtap">SIGTAP — Procedimentos SUS</span>
            <span className="hero-chip cid10">CID-10 — Classificação de Doenças</span>
            <span className="hero-chip cnes">CNES — Estabelecimentos de Saúde</span>
          </div>
          <p className="hero-hint">
            Busque por nome, código ou descrição — ex: "pneumonia", "J18", "0301010013"
          </p>
        </section>
      )}

      {/* Conteúdo principal */}
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
          Dados: SIGTAP · CID-10 · CNES — Ministério da Saúde ·{" "}
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
