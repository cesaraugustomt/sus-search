import { useState, useRef, type KeyboardEvent, type FormEvent } from "react";

interface SearchBarProps {
  initialValue?: string;
  loading?: boolean;
  onSearch: (query: string) => void;
}

export function SearchBar({ initialValue = "", loading = false, onSearch }: SearchBarProps) {
  const [value, setValue] = useState(initialValue);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (value.trim().length >= 2) onSearch(value.trim());
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setValue("");
      inputRef.current?.focus();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="search-form" role="search">
      <div className="search-input-wrap">
        <span className="search-icon" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </span>
        <input
          ref={inputRef}
          type="search"
          className="search-input"
          placeholder="Buscar procedimento, CID-10, estabelecimento…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Campo de busca"
          autoComplete="off"
          autoFocus
          minLength={2}
        />
        {value && (
          <button
            type="button"
            className="search-clear"
            aria-label="Limpar busca"
            onClick={() => { setValue(""); inputRef.current?.focus(); }}
          >
            ×
          </button>
        )}
      </div>
      <button
        type="submit"
        className="search-btn"
        disabled={loading || value.trim().length < 2}
        aria-busy={loading}
      >
        {loading ? "Buscando…" : "Buscar"}
      </button>
    </form>
  );
}
