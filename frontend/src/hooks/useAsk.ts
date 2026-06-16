import { useState, useRef } from "react";

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

interface AskResult {
  answer: string;
  tools_used: string[];
  question: string;
}

async function postAsk(question: string): Promise<AskResult> {
  const resp = await fetch(`${API_BASE}/api/v1/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal: AbortSignal.timeout(60_000),
  });
  if (!resp.ok) {
    const body = await resp.text().catch(() => "");
    throw new Error(`API ${resp.status}: ${body || resp.statusText}`);
  }
  return resp.json();
}

interface UseAskState {
  history: Array<{ role: "user" | "assistant"; content: string; tools?: string[] }>;
  loading: boolean;
  error: string | null;
}

export function useAsk() {
  const [state, setState] = useState<UseAskState>({ history: [], loading: false, error: null });
  const abortRef = useRef<AbortController | null>(null);

  const ask = async (question: string) => {
    if (!question.trim() || state.loading) return;
    setState((prev) => ({
      ...prev,
      loading: true,
      error: null,
      history: [...prev.history, { role: "user", content: question }],
    }));
    try {
      const result = await postAsk(question.trim());
      setState((prev) => ({
        ...prev,
        loading: false,
        history: [
          ...prev.history,
          { role: "assistant", content: result.answer, tools: result.tools_used },
        ],
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro desconhecido";
      setState((prev) => ({
        ...prev,
        loading: false,
        error: message,
        history: [
          ...prev.history,
          { role: "assistant", content: `Erro: ${message}`, tools: [] },
        ],
      }));
    }
  };

  const reset = () => setState({ history: [], loading: false, error: null });

  return { ...state, ask, reset };
}
