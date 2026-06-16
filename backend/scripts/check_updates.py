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

# ── detecta se está rodando no GitHub Actions
IS_GH_ACTIONS = "GITHUB_OUTPUT" in os.environ
FORCE         = os.environ.get("FORCE", "false").lower() == "true"
FONTE         = os.environ.get("FONTE", "all")

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
    """Retorna (data_iso, nome_arquivo) do ZIP mais recente no GitHub mirror."""
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
            # Busca data do último commit que tocou a pasta
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
    """Retorna ISO string da última carga de uma fonte no banco."""
    if not DATABASE_URL:
        log("  ⚠ DATABASE_URL não configurado — assumindo que é necessário atualizar")
        return None
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT loaded_at FROM sources WHERE code = :code"),
                {"code": source_code},
            ).fetchone()
            return row[0].isoformat() if row and row[0] else None
    except Exception as e:
        log(f"  ⚠ Erro ao consultar banco: {e}")
        return None


def main() -> None:
    log("\n" + "=" * 55)
    log("  SUS Search — Verificação de atualizações")
    log("=" * 55)

    # ── SIGTAP
    log("\n▶ SIGTAP (GitHub mirror):")
    github_date, arquivo = get_sigtap_github_date()
    db_date              = get_db_loaded_at("SIGTAP")
    log(f"  GitHub mais recente : {github_date} ({arquivo})")
    log(f"  Banco loaded_at     : {db_date or 'nunca carregado'}")

    sigtap_updated = (
        FORCE
        or db_date is None
        or (bool(github_date) and github_date > db_date)
        or FONTE in ("sigtap", "all")
    )
    log(f"  Necessita update    : {sigtap_updated}")
    set_output("sigtap_updated", str(sigtap_updated).lower())
    set_output("sigtap_file",    arquivo)

    # ── CNES (DEMAS — sempre disponível, atualiza mensalmente)
    log("\n▶ CNES (API DEMAS):")
    cnes_date = get_db_loaded_at("CNES")
    log(f"  Banco loaded_at     : {cnes_date or 'nunca carregado'}")

    if cnes_date:
        from datetime import timedelta
        last = datetime.fromisoformat(cnes_date.replace("Z", "+00:00"))
        days_since = (datetime.now(timezone.utc) - last).days
        log(f"  Dias desde última carga: {days_since}")
        cnes_updated = FORCE or days_since >= 30 or FONTE in ("cnes", "all")
    else:
        cnes_updated = True

    log(f"  Necessita update    : {cnes_updated}")
    set_output("cnes_updated", str(cnes_updated).lower())

    log("\n" + "=" * 55)
    log(f"  SIGTAP: {'🔄 atualizar' if sigtap_updated else '✓ sem novidade'}")
    log(f"  CNES:   {'🔄 atualizar' if cnes_updated   else '✓ sem novidade'}")
    log("=" * 55 + "\n")


if __name__ == "__main__":
    main()
