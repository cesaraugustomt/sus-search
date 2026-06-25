/**
 * Hook para perguntas com IA do usuário.
 * Técnica: knowledge injection — legislação SUS verificada injetada no prompt.
 *
 * ATENÇÃO: A legislação abaixo foi curada manualmente e revisada após
 * identificação de alucinações em testes (códigos SIGTAP fabricados,
 * portaria incorreta para meditação, atribuição causal não verificada
 * entre portaria e data de criação de código SIGTAP, CodeSystem FHIR
 * inventado, conhecimento médico genérico preenchendo lacuna de
 * cruzamento CID×SIGTAP). Respostas da IA devem sempre ser verificadas
 * em fontes oficiais: bvsms.saude.gov.br
 *
 * CAMADA DE SEGURANÇA ADICIONAL: filtro determinístico (sanitizeUnverified
 * Claims) que corrige afirmações causais não comprovadas e detecta
 * CodeSystems FHIR fabricados, independente do modelo usado — defesa em
 * profundidade.
 *
 * CAMADA DE REFERÊNCIAS: cada resposta recebe um rodapé "Fontes para
 * verificação" — links de official_url reais (vindos do próprio banco,
 * por código consultado) + portal oficial de legislação para portarias
 * citadas. Nunca fabrica um link específico por portaria — usa apenas
 * URLs já confirmadas (dados do banco) ou o portal genérico verificado.
 */
import { useState } from "react";
import type { AISettings, AIProvider } from "./useAISettings";

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

const LEGISLACAO_SUS = `
═══ LEGISLAÇÃO DO SUS — VERIFICADA (fontes: bvsms.saude.gov.br) ═══

▸ DISTINÇÃO CRÍTICA — o que é documentalmente certo × o que NÃO é:

  CERTO (pode afirmar com confiança):
  A portaria X INCLUI a prática Y na Política Nacional de Práticas
  Integrativas e Complementares (PNPIC). Isso é o ato normativo.

  NÃO COMPROVADO (proibido afirmar como fato):
  - A data exata em que um código SIGTAP foi criado na tabela.
  - Se a criação do código ocorreu "antes" ou "depois" da portaria.
  - Que o código foi "criado para operacionalizar" a portaria.

  PALAVRAS E EXPRESSÕES PROIBIDAS ao relacionar portaria com código
  SIGTAP (não use estas nem variações próximas):
  "foi criado posteriormente", "criado depois", "criado para
  operacionalizar", "em resposta a essa inclusão", "instituído pelo
  SIGTAP", "conforme instituído pelo SIGTAP".

  FORMULAÇÃO OBRIGATÓRIA quando precisar mencionar o código SIGTAP junto
  da portaria: "o código SIGTAP [X] corresponde a essa prática na tabela
  do sistema — não há dados disponíveis aqui sobre a data ou o ato
  técnico de sua criação." Apenas isso, sem elaborar mais sobre a
  relação temporal.

▸ PICS — HISTÓRICO CORRETO DAS PORTARIAS (sem códigos — ver DADOS DO BANCO):

  Portaria GM/MS nº 971, de 3 de maio de 2006 (PNPIC original):
  Inclui na Política Nacional de Práticas Integrativas e Complementares
  (PNPIC) as seguintes práticas: Medicina Tradicional Chinesa/Acupuntura,
  Homeopatia, Plantas Medicinais e Fitoterapia, Medicina Antroposófica,
  Termalismo Social/Crenoterapia.

  Portaria GM/MS nº 849, de 27 de março de 2017:
  Inclui 14 novas práticas na PNPIC. IMPORTANTE: foi esta portaria
  (849/2017), não a 702/2018, que incluiu: Arteterapia, Ayurveda,
  Biodança, Dança Circular, Meditação, Musicoterapia, Naturopatia,
  Osteopatia, Quiropraxia, Reflexoterapia, Reiki, Shantala,
  Terapia Comunitária Integrativa e Yoga.

  Portaria GM/MS nº 702, de 21 de março de 2018:
  Inclui PRÁTICAS DIFERENTES das da Portaria 849/2017 (não inclui
  meditação nem yoga, que já estavam na 849/2017). Amplia o total de
  práticas reconhecidas na PNPIC para 29.

  ATENÇÃO: não tenho memorizada a lista completa de códigos SIGTAP de
  cada prática de PICS. Para qualquer pergunta sobre QUAL é o código de
  uma prática, ou SEU VALOR, use exclusivamente a seção DADOS DO BANCO.

▸ FINANCIAMENTO DO SUS:
  PAB (Piso de Atenção Básica) — Portaria GM/MS 648/2006 (PNAB). Transferência
  federal direta para municípios. Procedimentos PAB = responsabilidade municipal.
  MAC (Média e Alta Complexidade) — financiado por produção (AIH/APAC).
  FAEC — procedimentos estratégicos e transplantes.
  Lei 8.080/1990 (Lei Orgânica da Saúde) — princípios do SUS: universalidade,
  integralidade, equidade.
  Lei 8.142/1990 — participação social e transferências intergovernamentais.

▸ SIGTAP:
  Portaria SAS/MS 342/2002 — institui o sistema SIGTAP em si (a
  infraestrutura de tabela). A portaria institui o SISTEMA, não cada
  código individual.
  Competência = mês/ano de referência da tabela (ex: 202606 = junho/2026).
  Grupos: 01=Promoção/Prevenção, 02=Diagnóstico, 03=Clínica, 04=Tratamento.

▸ GRANULARIDADE DE CÓDIGOS CID NO CRUZAMENTO COM SIGTAP:
  A tabela de compatibilidade procedimento×CID do SIGTAP frequentemente
  vincula procedimentos a subcódigos CID de 4 caracteres (ex: J180,
  J181, J189), não ao código-categoria de 3 caracteres (ex: J18). Se a
  pergunta for sobre um código de 3 caracteres e os DADOS DO BANCO não
  mostrarem nenhum "Procedimentos SUS:" para ele, isso pode significar
  apenas que a busca pegou o código genérico, não um subcódigo
  específico — NÃO SIGNIFICA que não há cobertura do SUS.
  NESSE CASO: diga explicitamente que não há dados de cruzamento para
  esse código específico nos resultados retornados, e sugira tentar um
  subcódigo mais específico (ex: "tente buscar J180, J181 ou J189").
  NUNCA substitua a ausência desse dado por conhecimento médico geral
  (exames, medicamentos, exemplos de tratamento) apresentado como se
  fosse cobertura confirmada do SUS — isso não está nos DADOS DO BANCO
  e deve ser claramente rotulado como conhecimento geral, não como dado
  do SUS Search, se for mencionado.

▸ CIAP-2 E SUA RELAÇÃO COM O CID-10 NO BRASIL:
  A CIAP-2 (Classificação Internacional de Atenção Primária, 2ª edição,
  WONCA) é a classificação OFICIAL adotada pelo e-SUS APS e pelo
  Prontuário Eletrônico do Cidadão (PEC) para o registro de atendimentos
  na Atenção Básica do SUS. É de uso OBRIGATÓRIO desde a implantação do
  e-SUS APS (Portaria GM/MS 1.412/2013), usada por mais de 50 mil equipes
  de Saúde da Família em todo o Brasil.
  CID-10 e CIAP-2 são COMPLEMENTARES e podem ser usados no mesmo
  atendimento: a CIAP-2 captura a perspectiva do paciente (motivo de
  consulta, antes do diagnóstico), enquanto o CID-10 registra o
  diagnóstico formal.

▸ SAÚDE MENTAL:
  Lei 10.216/2001 — Reforma Psiquiátrica brasileira.
  Portaria GM/MS 3.088/2011 — institui a RAPS (Rede de Atenção Psicossocial).
  Portaria GM/MS 336/2002 — CAPS I, II, III, CAPSad, CAPSi.

▸ CNES:
  Portaria SAS/MS 376/2000 — institui o CNES.

▸ ATENÇÃO: Para portarias específicas não listadas aqui, seja transparente
  sobre a incerteza e indique verificar em:
  https://bvsms.saude.gov.br/bvs/saudelegis/gm/
═══ FIM DA LEGISLAÇÃO ═══`;

const FHIR_MODELING_RULES = `
═══ REGRAS DE SINTAXE FHIR R4 (use ao modelar recursos) ═══
• clinicalStatus e verificationStatus em Condition são CodeableConcept
  (objeto com "coding"), NUNCA uma string solta:
    CORRETO:   "clinicalStatus": {"coding":[{"system":"http://terminology.hl7.org/CodeSystem/condition-clinical","code":"active"}]}
    INCORRETO: "clinicalStatus": "active"
• category em Procedure classifica o TIPO de procedimento — nunca repita
  o code principal dentro de category.
• CodeSystems canônicos a usar (não invente URLs):
    SIGTAP → http://www.saude.gov.br/fhir/r4/CodeSystem/sigtap
    CID-10 → http://hl7.org/fhir/sid/icd-10
    CIAP-2 → http://hl7.org/fhir/sid/icpc-2
    CNES   → http://www.saude.gov.br/fhir/r4/CodeSystem/cnes
• Use sempre o código exato vindo de DADOS DO BANCO — nunca de memória.

• PROIBIDO inventar um CodeSystem que não está na lista acima. Em
  especial, NUNCA crie URLs como ".../CodeSystem/procedure-category" ou
  qualquer outro path sob saude.gov.br que não seja /sigtap ou /cnes —
  isso já foi observado como fabricação em testes. Se precisar de uma
  "category" em Procedure e não tiver um CodeSystem confirmado, use
  category.text (texto livre), NUNCA category.coding.system inventado.

• Em campos de referência a pessoa/profissional (performer.actor,
  subject, etc.), o campo "reference" deve ser uma referência relativa
  a um recurso (ex: "Practitioner/example-1"), NUNCA texto descritivo
  livre como "reference": "Praticante de Acupuntura". Texto descritivo
  vai em "display", nunca em "reference".

• QUALQUER código (CID, SIGTAP, CIAP-2) usado dentro de um JSON de
  exemplo (reasonCode, subject, etc.) que NÃO veio de DADOS DO BANCO
  deve ser claramente identificado como ilustrativo. Adicione, fora do
  bloco de código, uma frase explícita como: "O código CID usado em
  reasonCode neste exemplo é apenas ilustrativo — não foi confirmado nos
  dados do banco para esta consulta." NUNCA apresente um código de
  exemplo como se fosse um dado real e verificado.
═══ FIM DAS REGRAS FHIR ═══`;

const SYSTEM_PROMPT = `Você é o assistente do SUS Search — sistema de busca de terminologias do SUS brasileiro.

FONTES DISPONÍVEIS (em ordem de prioridade):
1. DADOS DO BANCO: dados reais do DATASUS/SIGTAP/CID/CIAP-2/CNES
2. LEGISLAÇÃO VERIFICADA: portarias confirmadas em fontes primárias
3. SEU CONHECIMENTO: contexto clínico, epidemiológico e estrutural (FHIR)

REGRA MAIS IMPORTANTE — NUNCA VIOLE:
Qualquer código (SIGTAP, CID-10, CIAP-2, CNES) citado DEVE vir
literalmente de DADOS DO BANCO. Se não aparecer ali, diga que não foi
possível confirmar — nunca cite um código de memória.

REGRA DE HONESTIDADE EPISTÊMICA — NUNCA VIOLE:
Nunca afirme relação TEMPORAL ou CAUSAL entre dois fatos por inferência
lógica própria. Use as PALAVRAS PROIBIDAS listadas na seção LEGISLAÇÃO
como lista de bloqueio literal — se a frase que você ia escrever contém
qualquer uma delas, reescreva usando a FORMULAÇÃO OBRIGATÓRIA indicada.

ORDEM DE RESPOSTA quando a pergunta envolver portaria + código:
  1º Responda com confiança: qual prática o código representa e qual
     portaria a incluiu na política.
  2º Só depois, se relevante, use a FORMULAÇÃO OBRIGATÓRIA da seção
     LEGISLAÇÃO para o código — nunca elabore além dela.
  NUNCA abra com "não é possível confirmar" se você TEM prática+portaria.

OUTRAS INSTRUÇÕES:
• Use os DADOS DO BANCO para códigos, valores e classificações
• Se faltar valor monetário nos DADOS DO BANCO, diga que não tem esse
  dado em tempo real — não estime
• Se a pergunta pedir uma lista de procedimentos/cruzamentos e os DADOS
  DO BANCO não mostrarem esse cruzamento para o código exato perguntado,
  diga isso explicitamente (ver GRANULARIDADE DE CÓDIGOS CID abaixo) —
  NUNCA substitua por conhecimento médico geral apresentado como se
  fosse cobertura confirmada do SUS
• Ao modelar FHIR, siga as REGRAS DE SINTAXE FHIR R4 abaixo
• Responda SEMPRE inteiramente em português brasileiro, sem misturar
  palavras em inglês
• Cite o número da portaria correta quando souber` + LEGISLACAO_SUS + FHIR_MODELING_RULES;

// ─────────────────────────────────────────────────────────────────────
// CAMADA DE SEGURANÇA DETERMINÍSTICA — defesa em profundidade
//
// Mesmo com prompt bem escrito, modelos (especialmente via Groq/Llama)
// podem reintroduzir os mesmos padrões problemáticos. Estas verificações
// rodam DEPOIS da resposta da IA, independente do modelo/provedor usado.
// ─────────────────────────────────────────────────────────────────────
const UNVERIFIED_CAUSAL_PATTERNS: RegExp[] = [
  /foi criado posteriormente/i,
  /criado(?:s)?\s+depois/i,
  /para operacionalizar essa inclus[ãa]o/i,
  /em resposta a essa inclus[ãa]o/i,
  /conforme institu[íi]do pelo SIGTAP/i,
  /institu[íi]do pelo SIGTAP/i,
];

// Detecta CodeSystems sob saude.gov.br que NÃO são os dois canônicos
// (sigtap, cnes) — pega fabricações como ".../CodeSystem/procedure-category"
const FABRICATED_CODESYSTEM_PATTERN =
  /saude\.gov\.br\/fhir\/r4\/CodeSystem\/(?!sigtap|cnes)([\w-]+)/i;

function detectFabricatedCodeSystem(text: string): string | null {
  const m = text.match(FABRICATED_CODESYSTEM_PATTERN);
  return m ? m[1] : null;
}

function sanitizeUnverifiedClaims(text: string): string {
  const violated     = UNVERIFIED_CAUSAL_PATTERNS.some((re) => re.test(text));
  const fabricatedCS = detectFabricatedCodeSystem(text);

  if (!violated && !fabricatedCS) return text;

  const notes: string[] = [];

  if (violated) {
    notes.push(
      "🛡️ **Correção automática (filtro de honestidade epistêmica):** " +
      "a resposta acima pode sugerir uma relação temporal ou causal entre " +
      "a portaria e a criação do código SIGTAP que **não está comprovada** " +
      "nas fontes disponíveis neste sistema. O que é certo: a portaria " +
      "citada inclui a prática na PNPIC. O código SIGTAP é mantido " +
      "separadamente na tabela do sistema — não há dados aqui sobre a " +
      "data exata ou o ato técnico específico de sua criação."
    );
  }

  if (fabricatedCS) {
    notes.push(
      `⚠️ **Aviso automático:** a resposta usa um CodeSystem ` +
      `(".../CodeSystem/${fabricatedCS}") que **não está confirmado** ` +
      `como canônico para este projeto. Os únicos CodeSystems verificados ` +
      `sob saude.gov.br neste sistema são /sigtap e /cnes — qualquer outro ` +
      `path pode ser uma invenção do modelo. Verifique antes de usar este ` +
      `JSON em produção.`
    );
  }

  return text + "\n\n---\n" + notes.join("\n\n");
}

// ─────────────────────────────────────────────────────────────────────
// CAMADA DE REFERÊNCIAS — rodapé estilo "fontes para verificação"
//
// REGRA DE OURO: nunca fabricar uma URL específica. Só usamos:
//   (a) official_url que já vem do próprio banco de dados (real, por item)
//   (b) o portal genérico de legislação (verificado, sempre correto)
// ─────────────────────────────────────────────────────────────────────
interface BankItem {
  source: string;
  code?: string;
  name: string;
  official_url?: string;
}

const PORTARIA_PATTERN = /Portaria\s+(?:GM\/MS|SAS\/MS)?\s*n[ºo°]?\s*([\d.]+)[,/](?:\s*de\s*)?([^.;\n]{0,40})?/gi;

function extractPortariasCitadas(text: string): string[] {
  const found = new Set<string>();
  let m: RegExpExecArray | null;
  const re = new RegExp(PORTARIA_PATTERN);
  while ((m = re.exec(text)) !== null) {
    const numero = m[1]?.trim();
    if (numero) found.add(numero);
  }
  return Array.from(found);
}

function buildReferenceFooter(answerText: string, items: BankItem[]): string {
  const lines: string[] = [];

  const seen = new Set<string>();
  for (const it of items) {
    if (!it.official_url || seen.has(it.official_url)) continue;
    seen.add(it.official_url);
    const label = it.code ? `${it.source} ${it.code}` : it.source;
    lines.push(`• [${label}] ${it.name} — ${it.official_url}`);
  }

  const portarias = extractPortariasCitadas(answerText);
  if (portarias.length) {
    lines.push(
      `• Legislação citada (Portaria ${portarias.join(", ")}) — consulte o ` +
      `texto oficial na Biblioteca Virtual em Saúde: ` +
      `https://bvsms.saude.gov.br/bvs/saudelegis/gm/ (busque pelo número e ano)`
    );
  }

  if (!lines.length) return "";

  return "\n\n---\n📚 **Fontes para verificação**\n" + lines.join("\n");
}

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

// ─── Busca contexto real do banco — retorna texto + itens estruturados
async function fetchSUSContext(
  question: string
): Promise<{ context: string; items: BankItem[] }> {
  try {
    const terms = extractSearchTerms(question);
    if (!terms) return { context: "", items: [] };

    const resp = await fetch(
      `${API_BASE}/api/v1/search?q=${encodeURIComponent(terms)}&limit=5`
    );
    if (!resp.ok) return { context: "", items: [] };

    const data = await resp.json();
    if (!data.results?.length) {
      return {
        context:
          `\n\n═══ DADOS DO BANCO ═══\n` +
          `Nenhum resultado encontrado para "${terms}" no banco SUS Search.\n` +
          `Se a pergunta depende de um código específico, informe que não foi\n` +
          `possível confirmar esse dado nesta consulta.\n` +
          `═══ FIM DOS DADOS DO BANCO ═══`,
        items: [],
      };
    }

    type RawItem = {
      source: string; code?: string; name: string;
      category?: string; subcategory?: string; source_competency?: string;
      official_url?: string;
      additional_info?: {
        complexidade?: string; tipo_financiamento?: string;
        valor_ambulatorial?: string; valor_hospitalar?: string;
        faixa_etaria?: string; sexo_compativel?: string;
        qt_maxima_execucao?: number; capitulo?: string; componente?: string;
        cids_compativeis?: string[]; n_cids_compativeis?: number;
        n_procedimentos?: number; procedimentos_exemplos?: string[];
      };
    };

    const bankItems: BankItem[] = data.results.map((r: RawItem) => ({
      source: r.source, code: r.code, name: r.name, official_url: r.official_url,
    }));

    const itemsText = data.results.map((r: RawItem) => {
      const info = r.additional_info ?? {};
      const d: string[] = [];
      if (info.complexidade)       d.push(`Complexidade: ${info.complexidade}`);
      if (info.tipo_financiamento) d.push(`Financiamento: ${info.tipo_financiamento}`);
      if (info.valor_ambulatorial) d.push(`Valor ambulatorial: ${info.valor_ambulatorial}`);
      if (info.valor_hospitalar)   d.push(`Valor hospitalar: ${info.valor_hospitalar}`);
      if (info.faixa_etaria)       d.push(`Faixa etária: ${info.faixa_etaria}`);
      if (info.sexo_compativel)    d.push(`Gênero: ${info.sexo_compativel}`);
      if (info.qt_maxima_execucao) d.push(`Qtd máx/competência: ${info.qt_maxima_execucao}`);
      if (info.capitulo)           d.push(`Capítulo: ${info.capitulo}`);
      if (info.componente)         d.push(`Componente CIAP-2: ${info.componente}`);
      if (info.cids_compativeis?.length)
        d.push(`CIDs compatíveis (${info.n_cids_compativeis}): ${info.cids_compativeis.slice(0, 10).join(", ")}`);

      // Sinaliza explicitamente ausência de cruzamento (evita preenchimento
      // com conhecimento genérico — ver GRANULARIDADE DE CÓDIGOS CID)
      if (r.source === "CID10") {
        if (info.n_procedimentos) {
          d.push(`Procedimentos SUS: ${info.n_procedimentos} (ex: ${(info.procedimentos_exemplos ?? []).slice(0, 3).join(", ")})`);
        } else {
          d.push(`Procedimentos SUS: NENHUM cruzamento encontrado para este código exato. Se for um código de 3 caracteres (categoria), sugira tentar um subcódigo de 4 caracteres.`);
        }
      }

      return [
        `[${r.source}] Código: ${r.code ?? "—"} | Nome: ${r.name}`,
        r.category    ? `  Categoria: ${r.category}` : "",
        r.subcategory ? `  Tipo: ${r.subcategory}` : "",
        r.source_competency ? `  Competência: ${r.source_competency}` : "",
        ...d.map((x) => `  ${x}`),
      ].filter(Boolean).join("\n");
    });

    const context =
      `\n\n═══ DADOS CONFIRMADOS DO BANCO (busca: "${terms}", ${data.total} resultado(s)) ═══\n` +
      `Estes são os ÚNICOS códigos que você pode citar nesta resposta.\n\n` +
      itemsText.join("\n\n") +
      `\n═══ FIM DOS DADOS DO BANCO ═══`;

    return { context, items: bankItems };
  } catch {
    return { context: "", items: [] };
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
      const { context, items } = await fetchSUSContext(question);
      const rawAnswer = await callProvider(question, context, settings);
      const sanitized = sanitizeUnverifiedClaims(rawAnswer);
      const footer    = buildReferenceFooter(sanitized, items);
      const answer    = sanitized + footer;
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
