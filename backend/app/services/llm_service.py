"""
Serviço LLM — 3 ferramentas integradas.

Proteções contra loop:
  - max_iters = 3
  - parallel_tool_calls = False
  - resultados truncados a 1.200 chars
  - 5 resultados por busca
"""
import json
import logging
import unicodedata
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.term_repository import TermRepository

settings = get_settings()
logger   = logging.getLogger(__name__)

MAX_ITERS        = 3
MAX_RESULT_CHARS = 1200
SEARCH_LIMIT     = 5

_MUNICIPIO_CODIGO: dict[str, int] = {
    "florianópolis":      420540, "florianopolis":      420540,
    "joinville":          420910, "blumenau":           420270,
    "são josé":           421740, "sao jose":           421740,
    "criciúma":           420460, "criciuma":           420460,
    "chapecó":            420400, "chapeco":            420400,
    "itajaí":             420820, "itajai":             420820,
    "lages":              420930, "palhoça":            421190,
    "palhoca":            421190, "balneário camboriú": 420200,
    "balneario camboriu": 420200, "são paulo":          355030,
    "sao paulo":          355030, "rio de janeiro":     330455,
    "curitiba":           410690, "porto alegre":       431490,
    "belo horizonte":     310620, "manaus":             130260,
    "salvador":           292740, "fortaleza":          230440,
    "recife":             261160, "brasília":           530010,
    "brasilia":           530010,
}
_TIPO_UNIDADE_CODIGO: dict[str, int] = {
    "UBS": 1, "HOSPITAL": 5, "CAPS": 70, "CEO": 36, "MATERNIDADE": 15,
}


def _normalizar(nome: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", nome.strip().lower())
        if unicodedata.category(c) != "Mn"
    )


def _truncar(obj, max_chars: int = MAX_RESULT_CHARS) -> str:
    s = json.dumps(obj, ensure_ascii=False)
    if len(s) > max_chars:
        s = s[:max_chars] + '... [truncado]"'
    return s


# ──────────────────────────────────────────────────────────── tools

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_terms",
            "description": (
                "Busca termos no banco SUS Search (SIGTAP, CID-10, CNES). "
                "Use UMA VEZ com a query mais relevante. Retorna até 5 resultados."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo em português."},
                    "source": {
                        "type": "string",
                        "enum": ["SIGTAP", "CID10", "CNES"],
                        "description": "SIGTAP=procedimentos, CID10=doenças, CNES=estabelecimentos.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sources_metadata",
            "description": (
                "Retorna metadados de todas as fontes de dados: "
                "total de registros, competência (mês/ano de referência oficial) "
                "e data em que os dados foram carregados no banco. "
                "Use para perguntas sobre 'última atualização', 'competência atual', "
                "'quando foi atualizado', 'quantos registros existem'."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_cnes_demas",
            "description": "Busca estabelecimentos AO VIVO na API DEMAS (pública). Use para 'OBS em X', 'UBS em Y', 'CAPS em Z'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "municipio": {"type": "string", "description": "Nome do município."},
                    "tipo_unidade": {"type": "string", "enum": ["UBS", "HOSPITAL", "CAPS", "CEO", "MATERNIDADE", "TODOS"]},
                    "possui_centro_obstetrico": {"type": "boolean"},
                    "possui_centro_cirurgico":  {"type": "boolean"},
                },
                "required": ["municipio"],
            },
        },
    },
]

SYSTEM_PROMPT = """Você é o assistente do SUS Search, especializado no Sistema Único de Saúde do Brasil.

REGRA ANTI-LOOP (CRÍTICA):
Chame NO MÁXIMO UMA ferramenta por rodada. Após receber o resultado, responda IMEDIATAMENTE.
NUNCA repita a mesma ferramenta. NUNCA entre em loop.

━━━ FERRAMENTAS ━━━
• search_terms(query, source?)   → busca no banco de terminologias do SUS
• get_sources_metadata()         → totais, competências e datas de carga de TODAS as fontes
• search_cnes_demas(municipio)   → estabelecimentos ao vivo via API DEMAS

━━━ COMO RESPONDER PERGUNTAS SOBRE ATUALIZAÇÃO ━━━
Quando o usuário perguntar sobre "última atualização", "competência atual", etc.:
→ Chame get_sources_metadata() UMA VEZ
→ Apresente TODAS as fontes com contexto explicativo:

Exemplo de resposta boa:
"As terminologias do SUS Search estão na competência 06/2026 (junho de 2026):

📋 SIGTAP — Tabela de Procedimentos do SUS
   Fonte: sigtap.datasus.gov.br
   Competência: 06/2026 | 4.994 procedimentos indexados
   Atualização mensal pelo DATASUS.

🏥 CID-10 / RTS — Classificação Internacional de Doenças
   Fonte: rts.saude.gov.br  
   Competência: 06/2026 | 14.242 códigos indexados
   Os CIDs são extraídos da tabela de compatibilidade do SIGTAP.

🏢 CNES — Estabelecimentos de Saúde
   Fonte: API DEMAS (apidadosabertos.saude.gov.br)
   2.000 estabelecimentos carregados em [data de carga]
   Para dados ao vivo, use 'buscar estabelecimentos em [município]'.

A competência indica o mês/ano de referência da tabela oficial do Ministério da Saúde."

━━━ OUTROS EXEMPLOS ━━━
"quantos procedimentos de saúde mental?"
→ search_terms(query="saúde mental", source="SIGTAP") → liste os encontrados

"OBS em Florianópolis?"
→ search_cnes_demas(municipio="Florianópolis", possui_centro_obstetrico=true)

━━━ FORMATO ━━━
Português brasileiro, claro. Liste resultados com nome, código e detalhe relevante.
Para portarias/legislação em tempo real: sugira saude.gov.br e diariooficial.gov.br."""


# ──────────────────────────────────────────────────────────── executor

def execute_tool(name: str, args: dict, db: Session) -> str:
    repo = TermRepository(db)

    if name == "search_terms":
        query  = args.get("query", "").strip()
        source = args.get("source")
        if not query:
            return _truncar({"total": 0, "results": []})
        terms, total = repo.search(query=query, source=source, page=1, limit=SEARCH_LIMIT)
        logger.info(f"[search_terms] q={query!r} source={source} total={total}")
        return _truncar({
            "total":   total,
            "query":   query,
            "results": [
                {"code": t.code, "name": t.name, "source": t.source, "category": t.category}
                for t in terms
            ],
        })

    if name == "get_sources_metadata":
        from app.db.session import engine
        from sqlalchemy import text
        sources = repo.list_sources()
        data = []
        for s in sources:
            data.append({
                "code":            s.code,
                "name":            s.name,
                "record_count":    s.record_count,
                "competency":      s.competency,
                "loaded_at":       s.loaded_at.isoformat() if s.loaded_at else None,
                "official_url":    s.official_url,
                "descricao":       {
                    "SIGTAP": "Tabela de Procedimentos, Medicamentos e OPM do SUS — atualização mensal pelo DATASUS",
                    "CID10":  "Classificação Internacional de Doenças 10ª revisão — via tabela de compatibilidade SIGTAP",
                    "CNES":   "Cadastro Nacional de Estabelecimentos de Saúde — API pública DEMAS",
                }.get(s.code, ""),
            })
        return _truncar(data)

    if name == "search_cnes_demas":
        return _truncar(_execute_demas(args))

    return json.dumps({"error": f"Ferramenta desconhecida: {name}"})


def _execute_demas(args: dict) -> dict:
    from etl.demas_client import get_estabelecimentos
    municipio_raw  = args.get("municipio", "")
    municipio_norm = _normalizar(municipio_raw)
    codigo = (
        _MUNICIPIO_CODIGO.get(municipio_raw.strip().lower())
        or _MUNICIPIO_CODIGO.get(municipio_norm)
    )
    if not codigo:
        return {
            "aviso": f"Município '{municipio_raw}' não mapeado.",
            "sugestao": "Municípios suportados: Florianópolis, Joinville, Blumenau, São José, São Paulo, Rio de Janeiro, Curitiba...",
        }
    tipo_cod = _TIPO_UNIDADE_CODIGO.get(args.get("tipo_unidade", "TODOS"))
    obs_f = 1 if args.get("possui_centro_obstetrico") else None
    cc_f  = 1 if args.get("possui_centro_cirurgico")  else None
    try:
        items = get_estabelecimentos(
            codigo_municipio=codigo, codigo_tipo_unidade=tipo_cod,
            possui_centro_obstetrico=obs_f, possui_centro_cirurgico=cc_f,
            status=1, limit=10,
        )
        results = [
            {"cnes": e.get("codigo_cnes"),
             "nome": e.get("nome_fantasia") or e.get("nome_razao_social"),
             "bairro": e.get("bairro_estabelecimento"),
             "telefone": e.get("numero_telefone_estabelecimento"),
             "obs": e.get("estabelecimento_possui_centro_obstetrico") == 1,
             "sus": e.get("estabelecimento_faz_atendimento_ambulatorial_sus") == "SIM"}
            for e in items
        ]
        logger.info(f"[DEMAS] {municipio_raw}({codigo}) → {len(results)}")
        return {"municipio": municipio_raw, "count": len(results), "fonte": "DEMAS", "estabelecimentos": results}
    except Exception as exc:
        logger.error(f"[DEMAS] erro: {exc}")
        return {"error": str(exc)}


# ──────────────────────────────────────────────────── cliente LLM

def get_llm_config() -> Optional[dict]:
    base_url = getattr(settings, "LLM_BASE_URL", None)
    api_key  = getattr(settings, "LLM_API_KEY",  None)
    model    = getattr(settings, "LLM_MODEL", "llama-3.3-70b-versatile")
    if not base_url or not api_key:
        return None
    return {"base_url": base_url.rstrip("/"), "api_key": api_key, "model": model}


def ask(question: str, db: Session) -> dict:
    config = get_llm_config()
    if not config:
        return {
            "answer": (
                "Módulo de perguntas não configurado.\n\n"
                "Adicione ao .env:\n"
                "  LLM_BASE_URL=https://api.groq.com/openai/v1\n"
                "  LLM_API_KEY=gsk_sua_chave\n"
                "  LLM_MODEL=llama-3.3-70b-versatile\n\n"
                "Chave gratuita em: console.groq.com"
            ),
            "tools_used": [], "error": "LLM não configurado",
        }

    headers  = {"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    tools_used: list[str] = []

    try:
        with httpx.Client(timeout=60) as client:
            for i in range(MAX_ITERS):
                resp = client.post(
                    f"{config['base_url']}/chat/completions",
                    headers=headers,
                    json={"model": config["model"], "messages": messages, "tools": TOOLS,
                          "max_tokens": 512, "temperature": 0.1, "parallel_tool_calls": False},
                )
                resp.raise_for_status()
                choice = resp.json()["choices"][0]
                finish, msg = choice["finish_reason"], choice["message"]
                messages.append(msg)
                logger.info(f"[LLM] iter={i+1}/{MAX_ITERS} finish={finish}")

                if finish in ("stop", "end_turn", "length"):
                    return {"answer": msg.get("content") or "Sem resposta.", "tools_used": tools_used, "error": None}

                if finish == "tool_calls" and msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        tname = tc["function"]["name"]
                        targs = json.loads(tc["function"].get("arguments") or "{}")
                        tools_used.append(tname)
                        logger.info(f"[LLM] → {tname}({targs})")
                        result = execute_tool(tname, targs, db)
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                    continue

                return {"answer": msg.get("content") or "Resposta incompleta.", "tools_used": tools_used, "error": None}

            # Forçar resposta final ao esgotar iterações
            logger.warning("[LLM] max_iters atingido — forçando resposta")
            final = client.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json={"model": config["model"], "max_tokens": 512, "temperature": 0.1,
                      "messages": messages + [{"role": "user", "content": "Responda de forma direta e concisa com base nas informações acima."}]},
            )
            final.raise_for_status()
            return {"answer": final.json()["choices"][0]["message"].get("content") or "Sem resposta.",
                    "tools_used": tools_used, "error": None}

    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        logger.error(f"[LLM] HTTP {exc.response.status_code}: {body}")
        return {"answer": f"Erro HTTP {exc.response.status_code}:\n{body}", "tools_used": tools_used, "error": str(exc)}
    except Exception as exc:
        logger.error(f"[LLM] erro: {exc}", exc_info=True)
        return {"answer": f"Erro interno: {exc}", "tools_used": tools_used, "error": str(exc)}
