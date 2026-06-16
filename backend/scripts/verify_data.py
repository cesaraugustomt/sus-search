"""
verify_data.py — verifica integridade dos dados após ETL.
Falha com exit code 1 se algo estiver errado.
"""
import os
import sys
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "")
MIN_SIGTAP   = 4000    # mínimo esperado de procedimentos SIGTAP
MIN_CID10    = 1000    # mínimo esperado de códigos CID-10


def log(msg: str) -> None:
    print(msg, flush=True)


def verify() -> bool:
    ok = True
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        log("\n=== Verificação de integridade ===\n")

        # Total por fonte
        rows = conn.execute(text(
            "SELECT source, COUNT(*) as n FROM terms GROUP BY source ORDER BY source"
        )).fetchall()

        totais: dict[str, int] = {}
        for source, n in rows:
            totais[source] = n
            log(f"  {source:10s}: {n:>8,} termos")

        # Cheques mínimos
        sigtap_n = totais.get("SIGTAP", 0)
        cid10_n  = totais.get("CID10",  0)

        if sigtap_n < MIN_SIGTAP:
            log(f"\n  ✗ SIGTAP insuficiente: {sigtap_n} < {MIN_SIGTAP} esperados")
            ok = False
        else:
            log(f"\n  ✓ SIGTAP: {sigtap_n:,} procedimentos (ok)")

        if cid10_n < MIN_CID10:
            log(f"  ✗ CID-10 insuficiente: {cid10_n} < {MIN_CID10} esperados")
            ok = False
        else:
            log(f"  ✓ CID-10: {cid10_n:,} códigos (ok)")

        # Teste de busca FTS
        try:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM terms WHERE "
                "search_vector @@ plainto_tsquery('portuguese', 'consulta')"
            )).scalar()
            if result and result > 0:
                log(f"  ✓ Busca FTS: {result:,} resultados para 'consulta' (ok)")
            else:
                log("  ✗ Busca FTS retornou 0 resultados para 'consulta'")
                ok = False
        except Exception as e:
            log(f"  ✗ Erro no teste FTS: {e}")
            ok = False

        # Metadata das fontes
        log("\n  Fontes (metadata):")
        srcs = conn.execute(text(
            "SELECT code, record_count, loaded_at, competency FROM sources"
        )).fetchall()
        for code, rc, lat, comp in srcs:
            log(f"    {code:10s} {rc:>8,} registros  competência={comp}  carregado={lat}")

    log("\n" + ("✅ Verificação OK" if ok else "❌ Verificação FALHOU"))
    return ok


if __name__ == "__main__":
    if not DATABASE_URL:
        print("DATABASE_URL não configurada")
        sys.exit(1)
    sys.exit(0 if verify() else 1)
