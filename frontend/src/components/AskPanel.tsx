import { useState, useRef, useEffect } from "react";
import { useAsk }        from "../hooks/useAsk";
import { useAIAsk }      from "../hooks/useAIAsk";
import { useAISettings } from "../hooks/useAISettings";
import { AIConfigModal } from "./AIConfigModal";

const EXAMPLES = [
  "Quais procedimentos de acupuntura existem no SUS?",
  "Qual a última atualização de terminologias?",
  "O que é o CID J18.9?",
  "Quais atendimentos tenho disponível em Florianópolis?",
  "Quais procedimentos tratam pneumonia?",
  "Quais PICS estão registradas no SIGTAP?",
];

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Claude",
  openai:    "GPT",
  groq:      "Llama/Groq",
  gemini:    "Gemini",
};

export function AskPanel() {
  const [input, setInput]         = useState("");
  const [showModal, setShowModal] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Configuração de IA do usuário (localStorage)
  const { settings, save, remove } = useAISettings();

  // ── Modo NLU local (sem chave)
  const localAsk = useAsk();

  // ── Modo IA do usuário (com chave)
  const aiAsk = useAIAsk(settings);

  // Usa o modo adequado
  const isAI     = Boolean(settings?.apiKey);
  const history  = isAI ? aiAsk.history  : localAsk.history;
  const loading  = isAI ? aiAsk.loading  : localAsk.loading;
  const doReset  = isAI ? aiAsk.reset    : localAsk.reset;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading]);

  const send = (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput("");
    if (isAI) {
      aiAsk.ask(q);
    } else {
      localAsk.ask(q);
    }
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
        {/* Barra de modo e botão de configuração */}
        <div className="ask-mode-bar">
          <div className="ask-mode-indicator">
            {isAI ? (
              <span className="ask-mode-ai">
                🤖 {PROVIDER_LABELS[settings!.provider]} · {settings!.model.split("-")[0]}
              </span>
            ) : (
              <span className="ask-mode-local">
                ⚙ Modo local (NLU baseada em regras)
              </span>
            )}
          </div>
          <button
            className="ask-config-btn"
            onClick={() => setShowModal(true)}
            title={isAI ? "Alterar configurações de IA" : "Configurar IA própria"}
          >
            {isAI ? "✏ IA configurada" : "🤖 Usar IA própria"}
          </button>
        </div>

        {/* Histórico de mensagens */}
        {history.length === 0 ? (
          <div className="ask-empty">
            <span className="ask-empty-icon">{isAI ? "🧠" : "💬"}</span>
            <p className="ask-empty-title">
              {isAI
                ? `Pergunte qualquer coisa — resposta via ${PROVIDER_LABELS[settings!.provider]}`
                : "Pergunte sobre o SUS em linguagem natural"}
            </p>
            <p className="ask-empty-sub">
              {isAI
                ? "A IA usa os dados do SUS Search como contexto para respostas mais precisas."
                : "O assistente consulta os dados do banco e responde com base nas fontes oficiais."}
            </p>
            <div className="ask-examples">
              {EXAMPLES.map((ex) => (
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
                {"tools" in msg && (msg as { tools?: string[] }).tools && (msg as { tools?: string[] }).tools!.length > 0 && (
                  <div className="ask-tools-used">
                    {(msg as { tools?: string[] }).tools!.map((t) => (
                      <span key={t} className="ask-tool-tag">⚙ {t}</span>
                    ))}
                  </div>
                )}
                {"provider" in msg && (msg as { provider?: string }).provider && (
                  <div className="ask-tools-used">
                    <span className="ask-tool-tag ai-tag">
                      🤖 {PROVIDER_LABELS[(msg as { provider?: string }).provider!]}
                    </span>
                  </div>
                )}
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

        {/* Input */}
        <div className="ask-input-row">
          <input
            className="ask-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder={
              isAI
                ? "Pergunte qualquer coisa sobre o SUS…"
                : "Faça uma pergunta sobre o SUS…"
            }
            disabled={loading}
            autoFocus
          />
          <button
            className="ask-send-btn"
            onClick={() => send()}
            disabled={loading || !input.trim()}
          >
            {loading ? "…" : "Enviar"}
          </button>
          {history.length > 0 && (
            <button className="ask-clear-btn" onClick={doReset} title="Limpar conversa">
              ↺
            </button>
          )}
        </div>
      </div>
    </>
  );
}
