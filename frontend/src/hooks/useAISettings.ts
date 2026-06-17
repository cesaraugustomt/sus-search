/**
 * Hook para gerenciar configurações de IA no localStorage.
 * A chave de API NUNCA sai do browser — fica somente no localStorage.
 */
import { useState, useCallback } from "react";

export type AIProvider = "anthropic" | "openai" | "groq" | "gemini";

export interface AISettings {
  provider: AIProvider;
  apiKey: string;
  model: string;
}

const DEFAULTS: Record<AIProvider, string> = {
  anthropic: "claude-haiku-4-5-20251001",
  openai:    "gpt-4o-mini",
  groq:      "llama-3.3-70b-versatile",
  gemini:    "gemini-2.0-flash",
};

const STORAGE_KEY = "sus_search_ai_settings";

function load(): AISettings | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function useAISettings() {
  const [settings, setSettings] = useState<AISettings | null>(load);

  const save = useCallback((next: AISettings) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSettings(next);
  }, []);

  const remove = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setSettings(null);
  }, []);

  const defaultModel = (p: AIProvider) => DEFAULTS[p];

  return { settings, save, remove, defaultModel };
}
