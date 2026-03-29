"""
pipeline/__init__.py
====================
Package de la pipeline ETL Big Data (Medallion Architecture).

Couches :
- Bronze  : Ingestion brute des données CSV
- Silver  : Nettoyage et validation via PySpark
- Gold    : Agrégations KPIs pour le tableau de bord

Auteur  : PFE Marsa Maroc
Version : 2.0 (PySpark)
"""

from pipeline.etl_pipeline import ETLPipeline

__all__ = ["ETLPipeline"]
