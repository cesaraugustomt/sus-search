import { useState, useRef, useEffect } from "react";
import { useAsk } from "../hooks/useAsk";

const EXAMPLES = [
  "Quais procedimentos de acupuntura existem no SUS?",
  "Qual a última atualização de terminologias?",
  "O que é o CID J18.9?",
  "Quais atendimentos tenho disponível em Florianópolis?",
  "Quantos procedimentos de saúde mental existem?",
  "Quais PICS estão registradas no SIGTAP?",
];

export function AskPanel() {
  const { history, loading, ask, reset } = useAsk();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, loading]);

  const send = (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput("");
    ask(q);
  };

  return (
    <div className="ask-panel">
      {history.length === 0 ? (
        <div className="ask-empty">
          <span className="ask-empty-icon">💬</span>
          <p className="ask-empty-title">Pergunte sobre o SUS em linguagem natural</p>
          <p className="ask-empty-sub">
            O assistente consulta os dados do banco e responde com base nas fontes oficiais.
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
              {msg.role === "assistant" && msg.tools && msg.tools.length > 0 && (
                <div className="ask-tools-used">
                  {msg.tools.map((t) => (
                    <span key={t} className="ask-tool-tag">⚙ {t}</span>
                  ))}
                </div>
              )}
              <p className="ask-bubble-text">{msg.content}</p>
            </div>
          ))}

          {loading && (
            <div className="ask-bubble ask-bubble--assistant">
              <div className="ask-typing">
                <span /><span /><span />
              </div>
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
        <button
          className="ask-send-btn"
          onClick={() => send()}
          disabled={loading || !input.trim()}
        >
          {loading ? "…" : "Enviar"}
        </button>
        {history.length > 0 && (
          <button className="ask-clear-btn" onClick={reset} title="Limpar conversa">
            ↺
          </button>
        )}
      </div>
    </div>
  );
}
