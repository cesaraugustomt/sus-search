/**
 * Hook para perguntas com IA do usuário.
 * Técnica: knowledge injection — legislação SUS verificada injetada no prompt.
 *
 * ATENÇÃO: A legislação abaixo foi curada manualmente. Respostas da IA devem
 * ser verificadas em fontes oficiais: bvsms.saude.gov.br / saude.gov.br
 */
import { useState } from "react";
import type { AISettings, AIProvider } from "./useAISettings";

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

// ─── Legislação verificada — corrigida após validação com fontes primárias
const LEGISLACAO_SUS = `
═══ LEGISLAÇÃO DO SUS — VERIFICADA (fontes: bvsms.saude.gov.br) ═══

▸ PICS — HISTÓRICO CORRETO DAS PORTARIAS:

  Portaria GM/MS nº 971, de 3 de maio de 2006 (PNPICS original):
  Institui a Política Nacional de Práticas Integrativas e Complementares no SUS.
  Práticas incluídas: Medicina Tradicional Chinesa/Acupuntura, Homeopatia,
  Plantas Medicinais e Fitoterapia, Medicina Antroposófica, Termalismo Social/Crenoterapia.
  Códigos SIGTAP relacionados: grupo 0408 (acupuntura: 0408030014, 0408030022, 0408030030, 0408030049),
  homeopatia (0301080038), fitoterapia (0301050052).

  Portaria GM/MS nº 849, de 27 de março de 2017:
  Inclui 14 novas PICS ao SUS. IMPORTANTE: foi esta portaria (849/2017), não a 702/2018,
  que incluiu: Arteterapia, Ayurveda, Biodança, Dança Circular, Geoterapia, Hipnoterapia,
  Meditação (0101050070), Musicoterapia, Naturopatia, Osteopatia, Quiropraxia,
  Reflexoterapia, Reiki, Shiatsu, Terapia Comunitária Integrativa, Yoga (0101050046),
  Lian Gong/Qi Gong, Termalismo Social.

  Portaria GM/MS nº 702, de 21 de março de 2018:
  Inclui 10 PRÁTICAS DIFERENTES das da Portaria 849/2017 (não inclui meditação nem yoga,
  que já estavam na 849/2017). Novas práticas da 702/2018: Apiterapia, Aromaterapia,
  Bioenergética, Constelação Familiar, Cromopuntura, Imposição de Mãos, entre outras.
  Total acumulado: 29 PICS no SUS.

▸ FINANCIAMENTO DO SUS:
  PAB (Piso de Atenção Básica) — Portaria GM/MS 648/2006 (PNAB). Transferência federal
  direta para municípios. Procedimentos PAB = responsabilidade municipal.
  MAC (Média e Alta Complexidade) — financiado por produção (AIH/APAC).
  FAEC — procedimentos estratégicos e transplantes.
  Lei 8.080/1990 (Lei Orgânica da Saúde) — princípios do SUS: universalidade, integralidade, equidade.
  Lei 8.142/1990 — participação social e transferências intergovernamentais.

▸ SIGTAP:
  Portaria SAS/MS 342/2002 — institui o SIGTAP.
  Competência = mês/ano de referência da tabela (ex: 202606 = junho/2026).
  Grupos: 01=Promoção/Prevenção, 02=Diagnóstico, 03=Clínica, 04=Tratamento.
  Subcódigos do grupo 01: 0101050xxx = ações coletivas/individuais de promoção à saúde.

▸ SAÚDE MENTAL:
  Lei 10.216/2001 — Reforma Psiquiátrica brasileira.
  Portaria GM/MS 3.088/2011 — institui a RAPS (Rede de Atenção Psicossocial).
  Portaria GM/MS 336/2002 — CAPS I, II, III, CAPSad, CAPSi.

▸ CNES:
  Portaria SAS/MS 376/2000 — institui o CNES.

▸ ATENÇÃO: Para informações sobre portarias específicas, verifique sempre em:
  https://bvsms.saude.gov.br/bvs/saudelegis/gm/
═══ FIM DA LEGISLAÇÃO ═══`;

const SYSTEM_PROMPT = `Você é o assistente do SUS Search — sistema de busca de terminologias do SUS brasileiro.

FONTES DISPONÍVEIS (use em ordem de prioridade):
1. LEGISLAÇÃO VERIFICADA: seção acima com portarias confirmadas em fontes primárias
2. DADOS DO BANCO: seção abaixo com dados do DATASUS/SIGTAP
3. SEU CONHECIMENTO: contexto clínico e epidemiológico

INSTRUÇÕES:
• Use a LEGISLAÇÃO VERIFICADA acima para responder sobre portarias — ela foi curada manualmente
• Nunca diga "não sei sobre portarias" — a legislação está na seção acima
• Use os DADOS DO BANCO para confirmar códigos, valores e classificações
• Se houver dúvida sobre uma portaria não listada acima, seja transparente e indique verificar em bvsms.saude.gov.br
• Responda em português brasileiro, de forma direta e precisa
• Cite o número da portaria correta quando souber` + LEGISLACAO_SUS;

// ─── Extração inteligente de termos de busca
function extractSearchTerms(question: string): string {
  const sigtapCode = question.match(/\b(\d{10})\b/);
  if (sigtapCode) return sigtapCode[1];

  const cidCode = question.match(/\b([A-Za-z]\d{2,3}\.?\d*)\b/);
  if (cidCode) return cidCode[1].toUpperCase();

  const stopwords = new Set([
    "que", "qual", "quais", "como", "para", "tem", "são", "foi", "pelo",
    "pela", "este", "esse", "essa", "isso", "com", "sem", "uma", "por",
    "mais", "mas", "não", "sim", "código", "cid", "procedimento",
    "existe", "existem", "pode", "deve", "portaria", "qual", "incluído",
    "inserido", "inserida", "incluída",
  ]);
  const words = question
    .toLowerCase()
    .replace(/[?!.,;:]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 3 && !stopwords.has(w));

  return words.slice(0, 3).join(" ");
}

// ─── Busca contexto real do banco
async function fetchSUSContext(question: string): Promise<string> {
  try {
    const terms = extractSearchTerms(question);
    if (!terms) return "";

    const resp = await fetch(
      `${API_BASE}/api/v1/search?q=${encodeURIComponent(terms)}&limit=5`
    );
    if (!resp.ok) return "";

    const data = await resp.json();
    if (!data.results?.length) return "";

    const items = data.results.map((r: {
      source: string; code?: string; name: string;
      category?: string; subcategory?: string; source_competency?: string;
      additional_info?: {
        complexidade?: string; tipo_financiamento?: string;
        valor_ambulatorial?: string; valor_hospitalar?: string;
        faixa_etaria?: string; sexo_compativel?: string;
        qt_maxima_execucao?: number; capitulo?: string;
        cids_compativeis?: string[]; n_cids_compativeis?: number;
        n_procedimentos?: number; procedimentos_exemplos?: string[];
      };
    }) => {
      const info = r.additional_info ?? {};
      const d: string[] = [];
      if (info.complexidade)       d.push(`Complexidade: ${info.complexidade}`);
      if (info.tipo_financiamento) d.push(`Financiamento: ${info.tipo_financiamento}`);
      if (info.valor_ambulatorial) d.push(`Valor ambulatorial: ${info.valor_ambulatorial}`);
      if (info.valor_hospitalar)   d.push(`Valor hospitalar: ${info.valor_hospitalar}`);
      if (info.faixa_etaria)       d.push(`Faixa etária: ${info.faixa_etaria}`);
      if (info.sexo_compativel)    d.push(`Gênero: ${info.sexo_compativel}`);
      if (info.qt_maxima_execucao) d.push(`Qtd máx/competência: ${info.qt_maxima_execucao}`);
      if (info.capitulo)           d.push(`Capítulo CID: ${info.capitulo}`);
      if (info.cids_compativeis?.length)
        d.push(`CIDs compatíveis (${info.n_cids_compativeis}): ${info.cids_compativeis.slice(0, 10).join(", ")}`);
      if (info.n_procedimentos)
        d.push(`Procedimentos SUS: ${info.n_procedimentos} (ex: ${(info.procedimentos_exemplos ?? []).slice(0, 3).join(", ")})`);

      return [
        `[${r.source}] Código: ${r.code ?? "—"} | Nome: ${r.name}`,
        r.category    ? `  Categoria: ${r.category}` : "",
        r.subcategory ? `  Tipo: ${r.subcategory}` : "",
        r.source_competency ? `  Competência: ${r.source_competency}` : "",
        ...d.map((x) => `  ${x}`),
      ].filter(Boolean).join("\n");
    });

    return (
      `\n\n═══ DADOS CONFIRMADOS DO BANCO (busca: "${terms}", ${data.total} resultado(s)) ═══\n` +
      items.join("\n\n") +
      `\n═══ FIM DOS DADOS DO BANCO ═══`
    );
  } catch {
    return "";
  }
}

// ─── Chamadas por provedor

async function callAnthropic(q: string, ctx: string, s: AISettings): Promise<string> {
  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "x-api-key": s.apiKey, "anthropic-version": "2023-06-01", "content-type": "application/json" },
    body: JSON.stringify({
      model: s.model, max_tokens: 1024,
      system: SYSTEM_PROMPT + ctx,
      messages: [{ role: "user", content: q }],
    }),
  });
  if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).error?.message ?? `HTTP ${resp.status}`);
  return (await resp.json()).content?.[0]?.text ?? "Sem resposta.";
}

async function callOpenAICompat(base: string, q: string, ctx: string, s: AISettings): Promise<string> {
  const resp = await fetch(`${base}/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${s.apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: s.model, max_tokens: 1024,
      messages: [
        { role: "system", content: SYSTEM_PROMPT + ctx },
        { role: "user",   content: q },
      ],
    }),
  });
  if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).error?.message ?? `HTTP ${resp.status}`);
  return (await resp.json()).choices?.[0]?.message?.content ?? "Sem resposta.";
}

async function callGemini(q: string, ctx: string, s: AISettings): Promise<string> {
  const resp = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${s.model}:generateContent?key=${s.apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: SYSTEM_PROMPT + ctx }] },
        contents: [{ parts: [{ text: q }] }],
        generationConfig: { maxOutputTokens: 1024 },
      }),
    }
  );
  if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).error?.message ?? `HTTP ${resp.status}`);
  return (await resp.json()).candidates?.[0]?.content?.parts?.[0]?.text ?? "Sem resposta.";
}

const BASE_URLS: Record<AIProvider, string> = {
  anthropic: "", openai: "https://api.openai.com/v1",
  groq: "https://api.groq.com/openai/v1", gemini: "",
};

async function callProvider(q: string, ctx: string, s: AISettings): Promise<string> {
  if (s.provider === "anthropic") return callAnthropic(q, ctx, s);
  if (s.provider === "gemini")    return callGemini(q, ctx, s);
  return callOpenAICompat(BASE_URLS[s.provider], q, ctx, s);
}

// ─── Hook público

interface Message {
  role: "user" | "assistant";
  content: string;
  provider?: string;
  error?: boolean;
}

export function useAIAsk(settings: AISettings | null) {
  const [history, setHistory] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const ask = async (question: string) => {
    if (!question.trim() || loading || !settings) return;
    setHistory((h) => [...h, { role: "user", content: question }]);
    setLoading(true);
    try {
      const context = await fetchSUSContext(question);
      const answer  = await callProvider(question, context, settings);
      setHistory((h) => [...h, { role: "assistant", content: answer, provider: settings.provider }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro desconhecido";
      setHistory((h) => [
        ...h,
        { role: "assistant", content: `Erro: ${msg}\n\nVerifique sua chave de API.`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => setHistory([]);
  return { history, loading, ask, reset };
}
