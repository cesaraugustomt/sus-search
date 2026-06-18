import { useState, useEffect } from "react";

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

interface Props {
  source: string;
  code: string;
  name: string;
  onClose: () => void;
}

type Tab = "resource" | "lookup" | "valueset";

const SOURCE_FHIR: Record<string, string> = {
  SIGTAP: "sigtap",
  CID10:  "icd-10",
  CNES:   "cnes",
};
const RESOURCE_TYPE: Record<string, string> = {
  SIGTAP: "Procedure",
  CID10:  "Condition",
  CNES:   "Organization",
};

export function FHIRModal({ source, code, name, onClose }: Props) {
  const [tab, setTab]       = useState<Tab>("resource");
  const [json, setJson]     = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied]   = useState(false);

  const fhirSource = SOURCE_FHIR[source] ?? source.toLowerCase();

  const endpoints: Record<Tab, string> = {
    resource:  `${API_BASE}/api/v1/fhir/resource/${fhirSource}/${code}`,
    lookup:    `${API_BASE}/api/v1/fhir/CodeSystem/${fhirSource}/$lookup?code=${code}`,
    valueset:  `${API_BASE}/api/v1/fhir/ValueSet/$expand?filter=${encodeURIComponent(name.split(" ").slice(0,2).join(" "))}&source=${source}&count=10`,
  };

  useEffect(() => {
    setLoading(true);
    setJson("");
    fetch(endpoints[tab])
      .then((r) => r.json())
      .then((d) => setJson(JSON.stringify(d, null, 2)))
      .catch((e) => setJson(`{"error": "${e.message}"}`))
      .finally(() => setLoading(false));
  }, [tab, code, source]);

  const handleCopy = () => {
    navigator.clipboard.writeText(json).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box fhir-modal" onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="modal-header">
          <div>
            <h2 className="modal-title">
              🔗 FHIR R4 — {RESOURCE_TYPE[source] ?? source}
            </h2>
            <p className="fhir-modal-subtitle">
              <code>{source}</code> <code>{code}</code> · {name.substring(0, 50)}{name.length > 50 ? "…" : ""}
            </p>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Fechar">×</button>
        </div>

        {/* Tabs */}
        <div className="fhir-tabs">
          <button
            className={`fhir-tab${tab === "resource" ? " active" : ""}`}
            onClick={() => setTab("resource")}
          >
            {RESOURCE_TYPE[source] ?? "Resource"}
          </button>
          <button
            className={`fhir-tab${tab === "lookup" ? " active" : ""}`}
            onClick={() => setTab("lookup")}
          >
            $lookup
          </button>
          <button
            className={`fhir-tab${tab === "valueset" ? " active" : ""}`}
            onClick={() => setTab("valueset")}
          >
            ValueSet $expand
          </button>
        </div>

        {/* URL do endpoint */}
        <div className="fhir-endpoint-bar">
          <code className="fhir-endpoint-url">{endpoints[tab].replace(API_BASE, "")}</code>
          <a
            href={endpoints[tab]}
            target="_blank"
            rel="noopener noreferrer"
            className="fhir-endpoint-link"
            title="Abrir no browser"
          >
            ↗
          </a>
        </div>

        {/* JSON viewer */}
        <div className="fhir-json-wrap">
          {loading ? (
            <div className="fhir-loading">
              <div className="spinner" style={{ width: 24, height: 24 }} />
            </div>
          ) : (
            <pre className="fhir-json">{json}</pre>
          )}
        </div>

        {/* Ações */}
        <div className="fhir-actions">
          <button className="modal-btn" onClick={handleCopy} disabled={!json || loading}>
            {copied ? "✅ Copiado!" : "📋 Copiar JSON"}
          </button>
          <a
            href={`https://validator.fhir.org`}
            target="_blank"
            rel="noopener noreferrer"
            className="modal-btn"
          >
            🧪 Validar no FHIR Validator
          </a>
          <a
            href="https://rnds-guia.saude.gov.br"
            target="_blank"
            rel="noopener noreferrer"
            className="modal-btn"
          >
            📖 Guia RNDS
          </a>
        </div>
      </div>
    </div>
  );
}
