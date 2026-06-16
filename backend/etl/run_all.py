"""
Runner central do ETL — executa todos os importadores em sequência.

Uso:
  python -m etl.run_all                  # todos
  python -m etl.run_all --source sigtap  # apenas SIGTAP + CID-10
  python -m etl.run_all --source cnes    # apenas CNES via DEMAS (sem autenticação)
"""
import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging import setup_logging
from app.db.session import SessionLocal, init_db
from etl.sigtap import SIGTAPEtl
from etl.demas_cnes import DEMASCNESEtl      # ← CNES via API pública DEMAS

setup_logging()
logger = logging.getLogger(__name__)

SOURCES = {
    "sigtap": SIGTAPEtl,
    "cnes":   DEMASCNESEtl,   # API pública, sem autenticação
}


def run_etl(source: str = "all") -> dict[str, int]:
    init_db()
    results: dict[str, int] = {}

    with SessionLocal() as db:
        targets = SOURCES if source == "all" else {source: SOURCES[source]}
        for name, EtlClass in targets.items():
            logger.info(f"\n── {name.upper()} {'─'*40}")
            try:
                etl = EtlClass(db)
                count = etl.run()
                results[name] = count
            except Exception as e:
                logger.error(f"Falha no ETL [{name}]: {e}", exc_info=True)
                results[name] = -1

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="SUS Search ETL Runner")
    parser.add_argument(
        "--source",
        choices=["all", "sigtap", "cnes"],
        default="all",
        help="Fonte a importar (padrão: all)",
    )
    args = parser.parse_args()
    logger.info(f"Iniciando ETL para: {args.source}")
    results = run_etl(args.source)

    logger.info("=" * 50)
    for src, count in results.items():
        status = f"{count:,} registros" if count >= 0 else "FALHOU"
        logger.info(f"  {src.upper():<10} → {status}")
    logger.info("=" * 50)

    sys.exit(1 if any(c < 0 for c in results.values()) else 0)


if __name__ == "__main__":
    main()
