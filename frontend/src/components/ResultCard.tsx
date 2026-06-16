import type { Term } from "../types";

const SOURCE_COLORS: Record<string, string> = {
  SIGTAP: "#0ea5e9",
  CID10:  "#10b981",
  CNES:   "#8b5cf6",
};
const SOURCE_LABELS: Record<string, string> = {
  SIGTAP: "SIGTAP", CID10: "CID-10", CNES: "CNES",
};
const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];

function formatCompetencia(raw: string | null | undefined): string {
  if (!raw) return "";
  const s = raw.trim();
  if (!/^\d{6}$/.test(s)) return "";
  const mes = parseInt(s.substring(4, 6)) - 1;
  const ano = s.substring(0, 4);
  return mes >= 0 && mes < 12 ? `${MESES[mes]}/${ano}` : "";
}

// Campos extraídos de additional_info para exibição
const SIGTAP_META_FIELDS = [
  { key: "complexidade",       label: "Complexidade",    icon: "🏥" },
  { key: "tipo_financiamento", label: "Financiamento",   icon: "💰" },
  { key: "valor_ambulatorial", label: "Valor Amb.",      icon: "💵" },
  { key: "valor_hospitalar",   label: "Valor Hosp.",     icon: "💵" },
  { key: "faixa_etaria",       label: "Faixa etária",    icon: "👤" },
  { key: "sexo_compativel",    label: "Gênero",          icon: "⚤"  },
  { key: "qt_maxima_execucao", label: "Qtd. máx./comp.", icon: "🔢" },
];
const CID_META_FIELDS = [
  { key: "capitulo", label: "Capítulo CID", icon: "📋" },
];
const CNES_META_FIELDS = [
  { key: "municipio", label: "Município", icon: "📍" },
  { key: "telefone",  label: "Telefone",  icon: "📞" },
  { key: "bairro",    label: "Bairro",    icon: "🏘️"  },
];

interface ResultCardProps { term: Term }

export function ResultCard({ term }: ResultCardProps) {
  const color       = SOURCE_COLORS[term.source] ?? "#6b7280";
  const sourceLabel = SOURCE_LABELS[term.source] ?? term.source;
  const competencia = formatCompetencia(term.source_competency);

  const showDescription =
    term.description &&
    term.description.trim().toLowerCase() !== term.name.trim().toLowerCase();

  // Parse additional_info
  let info: Record<string, unknown> = {};
  try {
    info = typeof term.additional_info === "object"
      ? (term.additional_info as Record<string, unknown>) ?? {}
      : JSON.parse(term.additional_info as string ?? "{}");
  } catch { /* ignora JSON inválido */ }

  const metaFields =
    term.source === "SIGTAP" ? SIGTAP_META_FIELDS :
    term.source === "CID10"  ? CID_META_FIELDS    :
    term.source === "CNES"   ? CNES_META_FIELDS   : [];

  const visibleMeta = metaFields.filter(
    (f) => info[f.key] !== undefined && info[f.key] !== null && info[f.key] !== ""
  );

  // Cruzamento procedimento↔CID
  const cidsCompativeis  = (info.cids_compativeis  as string[] | undefined) ?? [];
  const nCids            = (info.n_cids_compativeis as number  | undefined) ?? cidsCompativeis.length;
  const procsExemplos    = (info.procedimentos_exemplos as string[] | undefined) ?? [];
  const nProcs           = (info.n_procedimentos   as number  | undefined) ?? procsExemplos.length;

  return (
    <article className="result-card">
      {/* ── Header */}
      <div className="card-header">
        <span
          className="source-badge"
          style={{ backgroundColor: `${color}18`, color, borderColor: `${color}40` }}
        >
          {sourceLabel}
        </span>
        {term.code && <code className="term-code">{term.code}</code>}
        {competencia && (
          <span className="competency-tag" title={`Competência de referência: ${competencia}`}>
            {competencia}
          </span>
        )}
      </div>

      {/* ── Nome */}
      <h3 className="term-name">{term.name}</h3>

      {/* ── Descrição diferente do nome */}
      {showDescription && (
        <p className="term-description">{term.description}</p>
      )}

      {/* ── Classificação básica */}
      {(term.category || term.subcategory) && (
        <div className="card-meta">
          {term.category && (
            <span className="meta-item">
              <span className="meta-label">Categoria:</span> {term.category}
            </span>
          )}
          {term.subcategory && (
            <span className="meta-item">
              <span className="meta-label">Tipo:</span> {term.subcategory}
            </span>
          )}
        </div>
      )}

      {/* ── Metadados clínicos (complexidade, valores, etc.) */}
      {visibleMeta.length > 0 && (
        <div className="card-extra">
          {visibleMeta.map((f) => (
            <span key={f.key} className="extra-tag" title={f.label}>
              <span className="extra-icon">{f.icon}</span>
              <span className="extra-label">{f.label}:</span>
              <span className="extra-value">{String(info[f.key])}</span>
            </span>
          ))}
        </div>
      )}

      {/* ── Cruzamento SIGTAP → CIDs compatíveis */}
      {term.source === "SIGTAP" && cidsCompativeis.length > 0 && (
        <div className="card-compat">
          <span className="compat-label">
            🔗 CIDs compatíveis
            {nCids > cidsCompativeis.length && (
              <span className="compat-total"> ({nCids} total)</span>
            )}:
          </span>
          <div className="compat-codes">
            {cidsCompativeis.map((cid) => (
              <code key={cid} className="compat-code cid-code" title={`CID ${cid}`}>
                {cid}
              </code>
            ))}
            {nCids > cidsCompativeis.length && (
              <span className="compat-more">+{nCids - cidsCompativeis.length}</span>
            )}
          </div>
        </div>
      )}

      {/* ── Cruzamento CID → procedimentos disponíveis */}
      {term.source === "CID10" && nProcs > 0 && (
        <div className="card-compat">
          <span className="compat-label">
            🔗 Procedimentos SUS disponíveis:
            <strong className="compat-total"> {nProcs} procedimento(s)</strong>
          </span>
          {procsExemplos.length > 0 && (
            <div className="compat-codes">
              {procsExemplos.map((p) => (
                <code key={p} className="compat-code proc-code" title={`Procedimento SIGTAP ${p}`}>
                  {p}
                </code>
              ))}
              {nProcs > procsExemplos.length && (
                <span className="compat-more">+{nProcs - procsExemplos.length} mais</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Link fonte oficial */}
      {term.official_url && (
        <a href={term.official_url} target="_blank" rel="noopener noreferrer" className="card-link">
          Ver na fonte oficial →
        </a>
      )}
    </article>
  );
}
