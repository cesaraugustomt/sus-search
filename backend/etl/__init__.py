"""
ETL package — importadores das bases SUS (SIGTAP, CID-10, CNES).

Uso via run_all:
    python -m etl.run_all               # todas as fontes
    python -m etl.run_all --source cnes # fonte específica
"""
from etl.sigtap import SIGTAPEtl
from etl.cnes import CNESEtl

__all__ = ["SIGTAPEtl", "CNESEtl"]
