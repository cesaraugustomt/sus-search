"""
Serviço de perguntas em linguagem natural — sem dependência de LLM externo.
NLU baseada em regras. Sem Groq, sem rate limits.
"""
import json
import re
import unicodedata
import logging
from typing import Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.repositories.term_repository import TermRepository

logger = logging.getLogger(__name__)

_MUNICIPIOS: dict[str, int] = {
    "florianópolis": 420540, "florianopolis": 420540,
    "joinville":     420910, "blumenau":      420270,
    "são josé":      421740, "sao jose":      421740,
    "criciúma":      420460, "criciuma":      420460,
    "chapecó":       420400, "chapeco":       420400,
    "itajaí":        420820, "itajai":        420820,
    "lages":         420930, "palhoça":       421190,
    "palhoca":       421190,
    "balneário camboriú": 420200, "balneario camboriu": 420200,
    "são paulo":     355030, "sao paulo":     355030,
    "rio de janeiro":330455, "curitiba":      410690,
    "porto alegre":  431490, "belo horizonte":310620,
    "manaus":        130260, "salvador":      292740,
    "fortaleza":     230440, "recife":        261160,
    "brasília":      530010, "brasilia":      530010,
}
_MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]


def _norm(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower().strip())
        if unicodedata.category(c) != "Mn"
    )


def _fmt_comp(raw: str) -> str:
    if not raw or not re.match(r"^\d{6}$", raw.strip()):
        return ""
    try:
        m, a = int(raw[4:6]) - 1, raw[0:4]
        return f"{_MESES[m]}/{a}" if 0 <= m < 12 else ""
    except Exception:
        return ""


def _parse_info(term) -> dict:
    try:
        ai = term.additional_info
        return (ai if isinstance(ai, dict) else json.loads(ai or "{}")) or {}
    except Exception:
        return {}


def _extrair_termo(question: str) -> str:
    """
    Extrai o termo de busca real de uma pergunta de cruzamento.

    Estratégia: extrai o que vem DEPOIS das palavras-chave de cruzamento,
    não remove as palavras-chave em si (que quebra o contexto).

    Exemplos:
      "quais CIDs são compatíveis com acupuntura?"  → "acupuntura"
      "quais procedimentos tratam pneumonia?"        → "pneumonia"
      "procedimentos para saúde mental"              → "saude mental"
      "o que trata o CID J18?"                       → "J18"
    """
    q = _norm(question)

    # Padrões em ordem de prioridade (extrai o que vem DEPOIS)
    patterns = [
        r"compativeis com (.+)",
        r"compativeis ao (.+)",
        r"para (?:o cid |cid )?([a-z0-9][^\?!]+)",
        r"tratam (.+)",
        r"trata (?:o |a )?(.+)",
        r"cobrem (.+)",
        r"cobre (.+)",
        r"do procedimento (.+)",
        r"do cid (.+)",
        r"com (.+)",
        r"de (.+)",
    ]

    for pat in patterns:
        m = re.search(pat, q)
        if m:
            termo = m.group(1).strip().rstrip("?!.,")
            # Filtra termos muito curtos ou só preposições
            if len(termo) >= 2 and termo not in {"o", "a", "os", "as", "um", "uma"}:
                return termo

    # Fallback: remove palavras de pergunta e retorna o núcleo
    _STOPWORDS = {
        "quais","qual","cids","cid","sao","que","cobrem","tratam","tratar",
        "existem","disponiveis","procedimentos","procedimento","compativeis",
        "compativel","o","a","os","as","um","uma","para","de","da","do",
        "e","ou","com","em","no","na","nos","nas","pelo","pela",
    }
    words = [
        w.rstrip("?!.,") for w in q.split()
        if w.rstrip("?!.,") not in _STOPWORDS
    ]
    return " ".join(words[:4]).strip() or question.strip()


# ─────────────────────────────────────── detecção de intenção

@dataclass
class Intent:
    kind: str
    source: Optional[str]         = None
    query: Optional[str]          = None
    cross_dir: Optional[str]      = None
    municipio_nome: Optional[str] = None
    municipio_codigo: Optional[int] = None
    filtros_cnes: dict = field(default_factory=dict)


def detect_intent(question: str) -> Intent:
    q = _norm(question)

    # ── Metadados
    if any(kw in q for kw in [
        "atualizacao","atualizado","competencia","ultima atualizacao",
        "quando foi","quantos registros","total de","fontes disponiveis","dados disponiveis",
    ]):
        return Intent(kind="metadata")

    # ── Cruzamento proc→CID
    if any(kw in q for kw in [
        "cids compativeis","cids para","cids do procedimento","quais cids","diagnosticos possiveis",
    ]):
        return Intent(kind="cross_ref", cross_dir="proc→cid", source="SIGTAP", query=question)

    # ── Cruzamento CID→proc
    if any(kw in q for kw in [
        "procedimentos para","procedimentos que cobrem","procedimentos do cid",
        "quais procedimentos","tratamentos para","o que trata","como tratar",
    ]):
        return Intent(kind="cross_ref", cross_dir="cid→proc", source="CID10", query=question)

    # ── Localização (CNES via DEMAS)
    for nome, codigo in _MUNICIPIOS.items():
        if _norm(nome) in q:
            filtros: dict = {}
            if any(w in q for w in ["obs","obstetrico","obstetricia","maternidade","parto"]):
                filtros["possui_centro_obstetrico"] = 1
            elif any(w in q for w in ["cirurgia","cirurgico"]):
                filtros["possui_centro_cirurgico"] = 1
            elif any(w in q for w in ["ubs","basica","unidade basica","atencao basica"]):
                filtros["codigo_tipo_unidade"] = 1
            elif any(w in q for w in ["caps","saude mental","psicossocial"]):
                filtros["codigo_tipo_unidade"] = 70
            elif any(w in q for w in ["hospital","internacao"]):
                filtros["codigo_tipo_unidade"] = 5
            elif any(w in q for w in ["ceo","odontologia"]):
                filtros["codigo_tipo_unidade"] = 36
            return Intent(kind="cnes", municipio_nome=nome, municipio_codigo=codigo, filtros_cnes=filtros)

    # ── Busca FTS (fallback)
    source = None
    if any(w in q for w in ["procedimento","sigtap","sessao","cirurgia","consulta","terapia","pratica"]):
        source = "SIGTAP"
    elif any(w in q for w in ["cid","doenca","diagnostico"]):
        source = "CID10"
    return Intent(kind="search", source=source, query=question.strip())


# ─────────────────────────────────────── formatadores

def _resposta_metadata(db: Session) -> str:
    repo    = TermRepository(db)
    sources = repo.list_sources()
    total   = repo.count_all()
    linhas  = [f"**SUS Search** — {total:,} termos indexados no total\n"]
    for s in sources:
        comp     = _fmt_comp(s.competency or "")
        comp_str = f"competência {comp}" if comp else "sem competência registrada"
        dt       = s.loaded_at.strftime("%d/%m/%Y %H:%M") if s.loaded_at else "nunca"
        n        = f"{s.record_count:,}" if s.record_count else "0"
        if s.code == "SIGTAP":
            linhas.append(
                f"📋 **SIGTAP** — Tabela de Procedimentos do SUS\n"
                f"   {n} procedimentos | {comp_str}\n"
                f"   Atualização mensal (DATASUS) | carregado em {dt}\n"
                f"   🔗 sigtap.datasus.gov.br\n"
            )
        elif s.code == "CID10":
            linhas.append(
                f"🏥 **CID-10** — Classificação Internacional de Doenças\n"
                f"   {n} códigos | {comp_str}\n"
                f"   Via tabela SIGTAP | carregado em {dt}\n"
                f"   🔗 rts.saude.gov.br\n"
            )
        elif s.code == "CNES":
            linhas.append(
                f"🏢 **CNES** — Estabelecimentos de Saúde\n"
                f"   {n} estabelecimentos | carregado em {dt}\n"
                f"   🔗 API pública DEMAS (apidadosabertos.saude.gov.br)\n"
            )
        else:
            linhas.append(f"📄 **{s.code}** — {n} registros | carregado em {dt}\n")
    linhas.append("\n*Para dados ao vivo: 'OBS em Florianópolis', 'UBS em Joinville'*")
    return "\n".join(linhas)


def _resposta_cross_ref(question: str, direction: str, db: Session) -> str:
    repo  = TermRepository(db)
    termo = _extrair_termo(question)   # ← extrai "acupuntura" de "quais CIDs compatíveis com acupuntura?"

    logger.info(f"[cross_ref] direction={direction} termo extraído='{termo}' (de '{question}')")

    src = "SIGTAP" if direction == "proc→cid" else "CID10"
    terms, total = repo.search(query=termo, source=src, page=1, limit=5)

    if total == 0:
        return (
            f"Não encontrei **{'procedimentos' if src=='SIGTAP' else 'códigos CID'}** "
            f"para '{termo}'.\n"
            f"*Tente buscar diretamente: {termo}*"
        )

    linhas = []
    for t in terms:
        info  = _parse_info(t)
        comp  = _fmt_comp(t.source_competency or "")

        if direction == "proc→cid":
            cids   = info.get("cids_compativeis", [])
            n_cids = info.get("n_cids_compativeis", len(cids))
            linha  = f"📋 **{t.name}** `{t.code}`"
            if comp: linha += f" | {comp}"
            if cids:
                linha += f"\n   🔗 {n_cids} CID(s) compatível(is): {' '.join(cids[:15])}"
                if n_cids > 15: linha += f" +{n_cids-15}"
            else:
                linha += "\n   _(sem CIDs na tabela de compatibilidade)_"
        else:
            n_procs = info.get("n_procedimentos", 0)
            procs   = info.get("procedimentos_exemplos", [])
            capitulo= info.get("capitulo", "")
            linha   = f"🏥 **{t.name}** `{t.code}`"
            if capitulo: linha += f"\n   _{capitulo}_"
            if n_procs:
                linha += f"\n   🔗 {n_procs} procedimento(s) SUS disponível(is)"
                if procs: linha += f": {' '.join(procs[:5])}" + (f" +{n_procs-5}" if n_procs>5 else "")
            else:
                linha += "\n   _(sem procedimentos associados no SIGTAP)_"

        linhas.append(linha)

    dir_label = "procedimento → CIDs" if direction == "proc→cid" else "CID → procedimentos SUS"
    return (
        f"Cruzamento **{dir_label}** para '{termo}' — {total} resultado(s):\n\n"
        + "\n".join(linhas)
        + "\n\n*Fonte: rl_procedimento_cid.txt — SIGTAP/DATASUS*"
    )


def _resposta_cnes(municipio_nome: str, municipio_codigo: int, filtros: dict) -> str:
    from etl.demas_client import get_estabelecimentos
    tipo_labels = {1:"UBS",5:"Hospital",70:"CAPS",36:"CEO",15:"Maternidade"}
    try:
        items = get_estabelecimentos(codigo_municipio=municipio_codigo, status=1, limit=20, **filtros)
    except Exception as exc:
        return f"Erro ao consultar a API DEMAS: {exc}"
    if not items:
        return (f"Não encontrei estabelecimentos em **{municipio_nome.title()}** com os filtros informados.\n"
                f"*Tente sem filtro: 'estabelecimentos em {municipio_nome.title()}'*")
    tipo_str = tipo_labels.get(filtros.get("codigo_tipo_unidade", 0), "de saúde")
    obs_str  = " com OBS"  if filtros.get("possui_centro_obstetrico") else ""
    cc_str   = " com CC"   if filtros.get("possui_centro_cirurgico")  else ""
    linhas   = [f"Encontrei **{len(items)} estabelecimento(s)** {tipo_str}{obs_str}{cc_str} em **{municipio_nome.title()}**:\n"]
    for e in items:
        nome  = e.get("nome_fantasia") or e.get("nome_razao_social") or "Sem nome"
        cnes  = e.get("codigo_cnes","")
        bairro= e.get("bairro_estabelecimento","")
        fone  = e.get("numero_telefone_estabelecimento","")
        tags  = []
        if e.get("estabelecimento_possui_centro_obstetrico")==1: tags.append("🏥 OBS")
        if e.get("estabelecimento_possui_centro_cirurgico") ==1: tags.append("🔪 CC")
        if e.get("estabelecimento_faz_atendimento_ambulatorial_sus")=="SIM": tags.append("✅ SUS")
        linha = f"• **{nome}** (CNES {cnes})"
        if bairro: linha += f" — {bairro}"
        if fone:   linha += f" | ☎ {fone}"
        if tags:   linha += f" | {' '.join(tags)}"
        linhas.append(linha)
    linhas.append("\n*Fonte: apidadosabertos.saude.gov.br — dados em tempo real*")
    return "\n".join(linhas)


def _resposta_busca(terms: list, total: int, query: str, source: Optional[str]) -> str:
    if total == 0:
        return (f"Não encontrei resultados para **'{query}'**.\n"
                f"*Sugestão: tente '{query.split()[0]}' ou verifique a ortografia.*")
    src_label = {
        "SIGTAP":"SIGTAP (procedimentos)","CID10":"CID-10 (doenças)","CNES":"CNES (estabelecimentos)"
    }.get(source or "", "todas as fontes")
    linhas = [f"Encontrei **{total:,} resultado(s)** para '{query}' em {src_label}:\n"]
    for t in terms:
        comp  = _fmt_comp(t.source_competency or "")
        info  = _parse_info(t)
        badge = {"SIGTAP":"📋","CID10":"🏥","CNES":"🏢"}.get(t.source,"•")
        linha = f"{badge} **{t.name}**"
        if t.code:     linha += f" `{t.code}`"
        if comp:       linha += f" | {comp}"
        if t.category: linha += f"\n   _{t.category}_"
        cids   = info.get("cids_compativeis", [])
        n_procs= info.get("n_procedimentos", 0)
        if cids:
            n = info.get("n_cids_compativeis", len(cids))
            linha += f"\n   🔗 {n} CID(s): {' '.join(cids[:8])}" + (f" +{n-8}" if n>8 else "")
        elif n_procs:
            procs = info.get("procedimentos_exemplos", [])
            linha += f"\n   🔗 {n_procs} procedimento(s) SUS"
            if procs: linha += f": {' '.join(procs[:3])}" + (f" +{n_procs-3}" if n_procs>3 else "")
        linhas.append(linha)
    if total > len(terms):
        linhas.append(f"\n*...e mais {total-len(terms):,} resultado(s). Use o modo Buscar para ver todos.*")
    return "\n".join(linhas)


# ─────────────────────────────────────── ponto de entrada

def ask(question: str, db: Session) -> dict:
    intent = detect_intent(question)
    logger.info(f"[ask] intent={intent.kind} cross={intent.cross_dir} q={question!r}")

    if intent.kind == "metadata":
        return {"answer": _resposta_metadata(db), "tools_used": ["get_sources_metadata"], "error": None}

    if intent.kind == "cross_ref":
        return {
            "answer":     _resposta_cross_ref(question, intent.cross_dir or "proc→cid", db),
            "tools_used": ["search_terms", "rl_procedimento_cid"],
            "error":      None,
        }

    if intent.kind == "cnes":
        return {
            "answer":     _resposta_cnes(intent.municipio_nome or "", intent.municipio_codigo or 0, intent.filtros_cnes),
            "tools_used": ["search_cnes_demas"],
            "error":      None,
        }

    repo         = TermRepository(db)
    terms, total = repo.search(query=intent.query or question, source=intent.source, page=1, limit=8)
    return {
        "answer":     _resposta_busca(terms, total, intent.query or question, intent.source),
        "tools_used": ["search_terms"],
        "error":      None,
    }
