"""
Cliente DEMAS — API de Dados Abertos do Ministério da Saúde.
URL: https://apidadosabertos.saude.gov.br/cnes/estabelecimentos

✅ API PÚBLICA — sem autenticação, sem token, sem cadastro.
Campos reais confirmados por chamada direta à API (junho/2026).
"""
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://apidadosabertos.saude.gov.br"

# ── Códigos IBGE sem dígito verificador (usado pelo DATASUS/CNES)
# IBGE 7 dígitos → remover o último = 6 dígitos
# Ex: Florianópolis 4205407 → 420540
MUNICIPIO_FLORIANOPOLIS = 420540
UF_SC = 42

# Tipos de unidade (código_tipo_unidade)
TIPO_UBS         = 1
TIPO_HOSPITAL    = 5
TIPO_CAPS        = 70
TIPO_CEO         = 36
TIPO_MATERNIDADE = 15

_SESSION = requests.Session()
_SESSION.headers.update({
    "Accept":     "application/json",
    "User-Agent": "SUSSearch/1.0 (mestrado PPGINFOS/UFSC)",
})


def get_estabelecimentos(
    codigo_municipio:            Optional[int] = None,
    codigo_uf:                   Optional[int] = None,
    codigo_tipo_unidade:         Optional[int] = None,
    status:                      Optional[int] = 1,
    possui_centro_obstetrico:    Optional[int] = None,
    possui_centro_cirurgico:     Optional[int] = None,
    possui_atendimento_sus:      Optional[bool] = None,
    limit:                       int = 20,
    offset:                      int = 0,
) -> list[dict]:
    """
    Busca estabelecimentos CNES. Retorna lista de dicts com campos reais da API.
    Sem autenticação — chamada simples GET.

    Campos confirmados no retorno:
      codigo_cnes, nome_fantasia, nome_razao_social,
      codigo_tipo_unidade, codigo_municipio, codigo_uf,
      endereco_estabelecimento, bairro_estabelecimento,
      numero_telefone_estabelecimento,
      latitude_estabelecimento_decimo_grau,
      longitude_estabelecimento_decimo_grau,
      estabelecimento_possui_centro_obstetrico (0/1),
      estabelecimento_possui_centro_cirurgico  (0/1),
      estabelecimento_possui_atendimento_hospitalar (0/1),
      estabelecimento_faz_atendimento_ambulatorial_sus ("SIM"/"NAO"),
      data_atualizacao
    """
    params: dict = {"limit": limit, "offset": offset}

    if codigo_municipio is not None:
        params["codigo_municipio"] = codigo_municipio
    if codigo_uf is not None:
        params["codigo_uf"] = codigo_uf
    if codigo_tipo_unidade is not None:
        params["codigo_tipo_unidade"] = codigo_tipo_unidade
    if status is not None:
        params["status"] = status
    if possui_centro_obstetrico is not None:
        params["estabelecimento_possui_centro_obstetrico"] = possui_centro_obstetrico
    if possui_centro_cirurgico is not None:
        params["estabelecimento_possui_centro_cirurgico"] = possui_centro_cirurgico

    logger.info(f"DEMAS GET /cnes/estabelecimentos params={params}")
    resp = _SESSION.get(f"{BASE_URL}/cnes/estabelecimentos", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # A API retorna {"estabelecimentos": [...]}
    items = (
        data.get("estabelecimentos")
        or data.get("items")
        or data.get("data")
        or (data if isinstance(data, list) else [])
    )
    logger.info(f"DEMAS: {len(items)} estabelecimentos retornados")
    return items


def get_estabelecimento(codigo_cnes: int) -> dict:
    """Busca um estabelecimento específico pelo código CNES."""
    resp = _SESSION.get(
        f"{BASE_URL}/cnes/estabelecimentos/{codigo_cnes}",
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_todos_municipio(
    codigo_municipio: int,
    codigo_tipo_unidade: Optional[int] = None,
    status: int = 1,
    max_pages: int = 100,
) -> list[dict]:
    """Pagina automaticamente e retorna TODOS os estabelecimentos do município."""
    all_items: list[dict] = []
    limit = 20

    for page in range(max_pages):
        items = get_estabelecimentos(
            codigo_municipio=codigo_municipio,
            codigo_tipo_unidade=codigo_tipo_unidade,
            status=status,
            limit=limit,
            offset=page * limit,
        )
        if not items:
            break
        all_items.extend(items)
        logger.info(f"  página {page + 1}: {len(items)} registros (acumulado: {len(all_items)})")
        if len(items) < limit:
            break   # última página

    return all_items


def get_tipos_unidade() -> list[dict]:
    """Retorna todos os tipos de unidade disponíveis."""
    resp = _SESSION.get(f"{BASE_URL}/cnes/tipounidades", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("items", [])


def normalizar(raw: dict) -> dict:
    """Converte um item da API DEMAS para o formato da tabela `terms`."""
    import json

    code  = str(raw.get("codigo_cnes", "")).strip() or None
    name  = (raw.get("nome_fantasia") or raw.get("nome_razao_social") or "").strip()
    if not name:
        return {}

    endereco   = raw.get("endereco_estabelecimento", "")
    numero     = raw.get("numero_estabelecimento", "")
    bairro     = raw.get("bairro_estabelecimento", "")
    telefone   = raw.get("numero_telefone_estabelecimento", "")
    email      = raw.get("endereco_email_estabelecimento", "")
    lat        = raw.get("latitude_estabelecimento_decimo_grau")
    lon        = raw.get("longitude_estabelecimento_decimo_grau")
    cod_mun    = raw.get("codigo_municipio")
    cod_uf     = raw.get("codigo_uf")
    tipo_cod   = raw.get("codigo_tipo_unidade")
    esfera     = raw.get("descricao_esfera_administrativa", "")
    obs        = raw.get("estabelecimento_possui_centro_obstetrico", 0) == 1
    cc         = raw.get("estabelecimento_possui_centro_cirurgico",  0) == 1
    hosp       = raw.get("estabelecimento_possui_atendimento_hospitalar", 0) == 1
    amb_sus    = raw.get("estabelecimento_faz_atendimento_ambulatorial_sus", "") == "SIM"
    dt_atual   = raw.get("data_atualizacao")

    end_fmt = " ".join(filter(None, [endereco, numero]))
    desc = " — ".join(filter(None, [end_fmt, bairro, str(cod_mun) if cod_mun else None]))

    extra: dict = {}
    if bairro:       extra["bairro"]    = bairro
    if telefone:     extra["telefone"]  = telefone
    if email:        extra["email"]     = email
    if lat:          extra["latitude"]  = lat
    if lon:          extra["longitude"] = lon
    if cod_mun:      extra["codigo_municipio"] = cod_mun
    if cod_uf:       extra["codigo_uf"] = cod_uf
    if tipo_cod:     extra["codigo_tipo_unidade"] = tipo_cod
    if obs:          extra["centro_obstetrico"]  = True
    if cc:           extra["centro_cirurgico"]   = True
    if hosp:         extra["atendimento_hospitalar"] = True
    if amb_sus:      extra["atendimento_ambulatorial_sus"] = True
    if esfera:       extra["esfera"] = esfera

    return {
        "code":             code,
        "name":             name,
        "description":      desc or name,
        "source":           "CNES",
        "category":         "Estabelecimento de Saúde",
        "subcategory":      str(cod_mun) if cod_mun else None,
        "additional_info":  json.dumps(extra, ensure_ascii=False),
        "official_url":     (
            f"https://cnes.datasus.gov.br/pages/estabelecimentos/consulta.jsp?codigo={code}"
            if code else "https://cnes.datasus.gov.br"
        ),
        "source_competency": dt_atual,
        "last_updated":      None,
    }
