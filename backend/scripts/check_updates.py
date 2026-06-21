"""
check_updates.py — verifica se há novos dados disponíveis.

Compara:
  - Data do commit mais recente no GitHub mirror do SIGTAP
  - Data da última carga gravada no banco (sources.loaded_at)

Saída: variáveis de ambiente para o GitHub Actions via GITHUB_OUTPUT.
Uso:  python backend/scripts/check_updates.py
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone

IS_GH_ACTIONS = "GITHUB_OUTPUT" in os.environ
FORCE         = os.environ.get("FORCE", "false").lower() == "true"

# CORRIGIDO: antes, FONTE = os.environ.get("FONTE", "all") fazia com que,
# no disparo agendado (schedule, sem inputs), FONTE virasse sempre "all" e
# a condição `FONTE in ("sigtap","all")` fosse SEMPRE verdadeira — disparando
# o ETL destrutivo do SIGTAP TODO DIA, mesmo sem necessidade. Isso causou
# perda de dados em produção quando o download do ZIP falhava no runner
# (sem cache local) e o delete já tinha sido comitado.
#
# Agora: FONTE só é usada para decidir o ALVO da atualização manual
# (workflow_dispatch). NUNCA força sigtap_updated=True por si só.
FONTE = os.environ.get("FONTE", "")

GITHUB_API    = "https://api.github.com/repos/RenatoKR/SIGTAP/commits"
DATABASE_URL  = os.environ.get("DATABASE_URL", "")


def log(msg: str) -> None:
    print(msg, flush=True)


def set_output(key: str, value: str) -> None:
    if IS_GH_ACTIONS:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"{key}={value}\n")
    log(f"  output: {key}={value}")


def get_sigtap_github_date() -> tuple[str, str]:
    try:
        resp = requests.get(
            "https://api.github.com/repos/RenatoKR/SIGTAP/contents/tabelas",
            timeout=15,
        )
        resp.raise_for_status()
        files = sorted(
            [f for f in resp.json() if f.get("name", "").endswith(".zip")],
            key=lambda f: f["name"],
            reverse=True,
        )
        if files:
            commits = requests.get(
                GITHUB_API,
                params={"path": "tabelas", "per_page": 1},
                timeout=15,
            ).json()
            date = commits[0]["commit"]["committer"]["date"] if commits else ""
            return date, files[0]["name"]
    except Exception as e:
        log(f"  ⚠ Erro ao consultar GitHub: {e}")
    return "", ""


def get_db_loaded_at(source_code: str) -> str | None:
    if not DATABASE_URL:
        log("  ⚠ DATABASE_URL não configurado — assumindo que NÃO é necessário atualizar (seguro por padrão)")
        return "unknown-but-present"
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT loaded_at, record_count FROM sources WHERE code = :code"),
                {"code": source_code},
            ).fetchone()
            if row and row[1] and row[1] > 0:
                return row[0].isoformat() if row[0] else "unknown-but-present"
            return None  # fonte nunca carregada OU com 0 registros
    except Exception as e:
        log(f"  ⚠ Erro ao consultar banco: {e}")
        # Em caso de erro de conexão, NÃO força update — seguro por padrão
        return "unknown-but-present"


def main() -> None:
    log("\n" + "=" * 55)
    log("  SUS Search — Verificação de atualizações")
    log("=" * 55)

    # ── SIGTAP
    log("\n▶ SIGTAP (GitHub mirror):")
    github_date, arquivo = get_sigtap_github_date()
    db_date              = get_db_loaded_at("SIGTAP")
    log(f"  GitHub mais recente : {github_date} ({arquivo})")
    log(f"  Banco loaded_at     : {db_date or 'nunca carregado / vazio'}")

    sigtap_updated = (
        FORCE
        or db_date is None                                          # nunca carregado ou com 0 registros
        or (bool(github_date) and db_date != "unknown-but-present" and github_date > db_date)
        or FONTE == "sigtap"                                         # só força via dispatch explícito
    )
    log(f"  Necessita update    : {sigtap_updated}")
    set_output("sigtap_updated", str(sigtap_updated).lower())
    set_output("sigtap_file",    arquivo)

    # ── CNES
    log("\n▶ CNES (API DEMAS):")
    cnes_date = get_db_loaded_at("CNES")
    log(f"  Banco loaded_at     : {cnes_date or 'nunca carregado / vazio'}")

    if cnes_date and cnes_date != "unknown-but-present":
        from datetime import timedelta
        last = datetime.fromisoformat(cnes_date.replace("Z", "+00:00"))
        days_since = (datetime.now(timezone.utc) - last).days
        log(f"  Dias desde última carga: {days_since}")
        cnes_updated = FORCE or days_since >= 30 or FONTE == "cnes"
    else:
        cnes_updated = cnes_date is None  # só força se nunca carregado/vazio

    log(f"  Necessita update    : {cnes_updated}")
    set_output("cnes_updated", str(cnes_updated).lower())

    log("\n" + "=" * 55)
    log(f"  SIGTAP: {'🔄 atualizar' if sigtap_updated else '✓ sem novidade'}")
    log(f"  CNES:   {'🔄 atualizar' if cnes_updated   else '✓ sem novidade'}")
    log("=" * 55 + "\n")


if __name__ == "__main__":
    main()
