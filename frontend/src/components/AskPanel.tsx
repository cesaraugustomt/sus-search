import { useState, useRef, useEffect } from "react";
import { useAsk }        from "../hooks/useAsk";
import { useAIAsk }      from "../hooks/useAIAsk";
import { useAISettings } from "../hooks/useAISettings";
import { AIConfigModal } from "./AIConfigModal";

const EXAMPLE_GROUPS = [
  {
    label: "🌿 PICS no SUS",
    examples: [
      "O código 0309050022 foi incluído por qual portaria? O valor reflete a PNPICS?",
      "Por que acupuntura, yoga e meditação não têm CID vinculado no SIGTAP?",
    ],
  },
  {
    label: "🔬 Clínica e terminologia",
    examples: [
      "Para o CID J18 (pneumonia), quais procedimentos SUS cobrem do diagnóstico ao tratamento?",
      "Qual a diferença entre CID-10 e CIAP-2 para registrar depressão na atenção primária?",
    ],
  },
  {
    label: "🔗 FHIR e interoperabilidade",
    examples: [
      "Como modelar uma consulta de acupuntura (SIGTAP 0309050022) como recurso FHIR R4?",
      "Qual CodeSystem FHIR usar para SIGTAP e CIAP-2 seguindo os perfis da RNDS?",
    ],
  },
  {
    label: "📊 Pesquisa em saúde",
    examples: [
      "Como um mecanismo de busca que cruza SIGTAP, CID-10 e CIAP-2 contribui para a pesquisa em informática em saúde?",
      "Qual a última atualização de terminologias do SUS Search e o que cada fonte representa?",
    ],
  },
];

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Claude", openai: "GPT", groq: "Llama/Groq", gemini: "Gemini",
};

export function AskPanel() {
  const [input, setInput]           = useState("");
  const [showModal, setShowModal]   = useState(false);
  const [activeGroup, setActiveGroup] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { settings, save, remove } = useAISettings();
  const localAsk = useAsk();
  const aiAsk    = useAIAsk(settings);

  const isAI    = Boolean(settings?.apiKey);
  const history = isAI ? aiAsk.history : localAsk.history;
  const loading = isAI ? aiAsk.loading : localAsk.loading;
  const doReset = isAI ? aiAsk.reset   : localAsk.reset;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading]);

  const send = (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput("");
    isAI ? aiAsk.ask(q) : localAsk.ask(q);
  };

  return (
    <>
      {showModal && (
        <AIConfigModal
          current={settings}
          onSave={save}
          onDelete={remove}
          onClose={() => setShowModal(false)}
        />
      )}

      <div className="ask-panel">
        <div className="ask-mode-bar">
          <div className="ask-mode-indicator">
            {isAI ? (
              <span className="ask-mode-ai">
                🤖 {PROVIDER_LABELS[settings!.provider]} · {settings!.model.split("-")[0]}
              </span>
            ) : (
              <span className="ask-mode-local">⚙ Modo local</span>
            )}
          </div>
          <button className="ask-config-btn" onClick={() => setShowModal(true)}>
            {isAI ? "✏ IA configurada" : "🤖 Usar IA própria"}
          </button>
        </div>

        {history.length === 0 ? (
          <div className="ask-empty">
            <span className="ask-empty-icon">{isAI ? "🧠" : "💬"}</span>
            <p className="ask-empty-title">
              {isAI
                ? `Pergunte qualquer coisa — resposta via ${PROVIDER_LABELS[settings!.provider]}`
                : "Pergunte sobre o SUS em linguagem natural"}
            </p>
            <p className="ask-empty-sub">
              Consulta os dados reais do banco: SIGTAP, CID-10, CIAP-2 e CNES.
            </p>

            <div className="ask-group-tabs">
              {EXAMPLE_GROUPS.map((g, i) => (
                <button
                  key={i}
                  className={`ask-group-tab${activeGroup === i ? " active" : ""}`}
                  onClick={() => setActiveGroup(i)}
                >
                  {g.label}
                </button>
              ))}
            </div>

            <div className="ask-examples">
              {EXAMPLE_GROUPS[activeGroup].examples.map((ex) => (
                <button key={ex} className="ask-example-chip" onClick={() => send(ex)}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="ask-history">
            {history.map((msg, i) => (
              <div key={i} className={`ask-bubble ask-bubble--${msg.role}`}>
                {"tools" in msg && (msg as { tools?: string[] }).tools?.length ? (
                  <div className="ask-tools-used">
                    {(msg as { tools?: string[] }).tools!.map((t) => (
                      <span key={t} className="ask-tool-tag">⚙ {t}</span>
                    ))}
                  </div>
                ) : null}
                {"provider" in msg && (msg as { provider?: string }).provider ? (
                  <div className="ask-tools-used">
                    <span className="ask-tool-tag ai-tag">
                      🤖 {PROVIDER_LABELS[(msg as { provider?: string }).provider!]}
                    </span>
                  </div>
                ) : null}
                <p className="ask-bubble-text">{msg.content}</p>
              </div>
            ))}
            {loading && (
              <div className="ask-bubble ask-bubble--assistant">
                <div className="ask-typing"><span /><span /><span /></div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}

        <div className="ask-input-row">
          <input
            className="ask-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Faça uma pergunta sobre o SUS…"
            disabled={loading}
            autoFocus
          />
          <button className="ask-send-btn" onClick={() => send()} disabled={loading || !input.trim()}>
            {loading ? "…" : "Enviar"}
          </button>
          {history.length > 0 && (
            <button className="ask-clear-btn" onClick={doReset} title="Limpar conversa">↺</button>
          )}
        </div>
      </div>
    </>
  );
}
