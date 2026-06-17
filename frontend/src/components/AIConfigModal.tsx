import { useState } from "react";
import type { AIProvider, AISettings } from "../hooks/useAISettings";

const PROVIDERS: { id: AIProvider; label: string; models: string[]; hint: string; keyHint: string; free?: boolean }[] = [
  {
    id: "groq",
    label: "Groq (Llama 3.3)",
    models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"],
    hint: "Gratuito, muito rápido, excelente português",
    keyHint: "console.groq.com → API Keys",
    free: true,
  },
  {
    id: "anthropic",
    label: "Anthropic (Claude)",
    models: ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"],
    hint: "Melhor raciocínio, pode ter restrição CORS no browser",
    keyHint: "console.anthropic.com → API Keys",
  },
  {
    id: "openai",
    label: "OpenAI (GPT)",
    models: ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
    hint: "Amplamente conhecido, pago por uso",
    keyHint: "platform.openai.com → API Keys",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    models: ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    hint: "Gratuito no free tier, ótimo português",
    keyHint: "aistudio.google.com → Get API Key",
    free: true,
  },
];

interface Props {
  current: AISettings | null;
  onSave:   (s: AISettings) => void;
  onDelete: () => void;
  onClose:  () => void;
}

export function AIConfigModal({ current, onSave, onDelete, onClose }: Props) {
  const [provider, setProvider] = useState<AIProvider>(current?.provider ?? "groq");
  const [apiKey,   setApiKey  ] = useState(current?.apiKey ?? "");
  const [model,    setModel   ] = useState(current?.model  ?? PROVIDERS[0].models[0]);
  const [showKey,  setShowKey ] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const selected = PROVIDERS.find((p) => p.id === provider) ?? PROVIDERS[0];

  const handleProviderChange = (p: AIProvider) => {
    setProvider(p);
    const prov = PROVIDERS.find((x) => x.id === p)!;
    setModel(prov.models[0]);
  };

  const handleSave = () => {
    if (!apiKey.trim()) return;
    onSave({ provider, apiKey: apiKey.trim(), model });
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="modal-header">
          <h2 className="modal-title">🤖 Configurar IA própria</h2>
          <button className="modal-close" onClick={onClose} aria-label="Fechar">×</button>
        </div>

        {/* Aviso de segurança */}
        <div className="modal-security-note">
          🔒 Sua chave de API é salva <strong>somente no localStorage do seu browser</strong>.
          Ela nunca é enviada ao nosso servidor. As chamadas à IA saem diretamente do
          seu dispositivo para o provedor escolhido.
        </div>

        {/* Seleção de provedor */}
        <div className="modal-section">
          <label className="modal-label">Provedor</label>
          <div className="provider-grid">
            {PROVIDERS.map((p) => (
              <button
                key={p.id}
                className={`provider-btn${provider === p.id ? " active" : ""}`}
                onClick={() => handleProviderChange(p.id)}
              >
                <span className="provider-name">{p.label}</span>
                {p.free && <span className="provider-free">grátis</span>}
                <span className="provider-hint">{p.hint}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Chave de API */}
        <div className="modal-section">
          <label className="modal-label">
            Chave de API
            <span className="modal-label-hint"> — {selected.keyHint}</span>
          </label>
          <div className="key-input-wrap">
            <input
              type={showKey ? "text" : "password"}
              className="modal-input"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={`Cole sua chave do ${selected.label}`}
              autoComplete="off"
              spellCheck={false}
            />
            <button
              className="key-toggle"
              onClick={() => setShowKey((v) => !v)}
              tabIndex={-1}
            >
              {showKey ? "🙈" : "👁"}
            </button>
          </div>
        </div>

        {/* Modelo */}
        <div className="modal-section">
          <label className="modal-label">Modelo</label>
          <select
            className="modal-select"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {selected.models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        {/* Ações */}
        <div className="modal-actions">
          {current && !confirmDelete && (
            <button
              className="modal-btn modal-btn--danger"
              onClick={() => setConfirmDelete(true)}
            >
              🗑 Apagar chave
            </button>
          )}
          {confirmDelete && (
            <div className="confirm-delete">
              <span>Confirmar exclusão?</span>
              <button
                className="modal-btn modal-btn--danger"
                onClick={() => { onDelete(); onClose(); }}
              >
                Sim, apagar
              </button>
              <button
                className="modal-btn"
                onClick={() => setConfirmDelete(false)}
              >
                Cancelar
              </button>
            </div>
          )}
          <button
            className="modal-btn modal-btn--primary"
            onClick={handleSave}
            disabled={!apiKey.trim()}
          >
            Salvar e usar IA
          </button>
        </div>

        {/* Nota local */}
        <p className="modal-footer-note">
          Para máxima privacidade, rode o SUS Search localmente com{" "}
          <code>docker compose up</code> e use Ollama (modelo local, sem internet).
        </p>
      </div>
    </div>
  );
}
