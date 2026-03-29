"""
pipeline/gold_layer.py
=======================
Couche Gold — Agregations et KPIs analytiques finaux.

Stockage HDFS : hdfs://namenode:9000/marsa_maroc/gold/ (Parquet agrege)
Stockage local : data/gold/ (JSON des KPIs — pour l'API FastAPI)

Metriques calculees :
1. Distribution par type de conteneur
2. Distribution par taille (20ft / 40ft)
3. Statistiques de poids (avg/min/max/stddev)
4. Fenetre temporelle (date min/max departure)
5. Score de qualite pipeline (herite de Silver)

Auteur  : PFE Marsa Maroc
Version : 3.0 (PySpark + HDFS Docker)
"""

import os
import json
from datetime import datetime
from typing import Dict, Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F


# Chemins HDFS et local
HDFS_NAMENODE = os.getenv("HDFS_NAMENODE", "hdfs://localhost:9000")
HDFS_GOLD     = f"{HDFS_NAMENODE}/marsa_maroc/gold"
LOCAL_GOLD    = os.path.join(os.path.dirname(__file__), "..", "data", "gold")


class GoldLayer:
    """
    Couche Gold PySpark : KPIs analytiques + persistance HDFS.
    """

    def __init__(self, spark: SparkSession, storage_mode: str = "local"):
        self.spark = spark
        self.storage_mode = storage_mode

    def _get_parquet_path(self, timestamp_str: str) -> str:
        if self.storage_mode == "hdfs":
            return f"{HDFS_GOLD}/kpis_{timestamp_str}"
        base = os.path.abspath(LOCAL_GOLD)
        os.makedirs(base, exist_ok=True)
        return f"file:///{base.replace(os.sep, '/')}/kpis_{timestamp_str}"

    def compute(self, df_clean: DataFrame, silver_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcule les KPIs et les persiste.
        - Parquet agrege : HDFS (ou local)
        - JSON KPIs      : toujours local (pour l'API FastAPI)
        """
        processing_time = datetime.now()
        timestamp_str   = processing_time.strftime("%Y%m%d_%H%M%S")

        total = df_clean.count()
        if total == 0:
            return {"layer": "GOLD", "status": "EMPTY", "message": "Aucune donnee valide."}

        # KPI 1 : Distribution par type
        type_dist_rows = (
            df_clean.groupBy("type")
            .agg(F.count("*").alias("cnt"),
                 F.round(F.avg("weight"), 2).alias("avg_weight_t"))
            .orderBy(F.desc("cnt"))
            .collect()
        )
        type_distribution = {
            row["type"]: {
                "count":        int(row["cnt"]),
                "percentage":   round(int(row["cnt"]) / total * 100, 1),
                "avg_weight_t": float(row["avg_weight_t"]) if row["avg_weight_t"] else 0.0,
            }
            for row in type_dist_rows
        }

        # KPI 2 : Distribution par taille
        size_dist_rows = (
            df_clean.groupBy("size")
            .agg(F.count("*").alias("cnt"),
                 F.round(F.avg("weight"), 2).alias("avg_weight_t"))
            .orderBy("size")
            .collect()
        )
        size_distribution = {
            f"{row['size']}ft": {
                "count":        int(row["cnt"]),
                "percentage":   round(int(row["cnt"]) / total * 100, 1),
                "avg_weight_t": float(row["avg_weight_t"]) if row["avg_weight_t"] else 0.0,
            }
            for row in size_dist_rows
        }

        # KPI 3 : Statistiques de poids
        ws = df_clean.agg(
            F.round(F.avg("weight"),    2).alias("avg"),
            F.round(F.min("weight"),    2).alias("min_w"),
            F.round(F.max("weight"),    2).alias("max_w"),
            F.round(F.stddev("weight"), 2).alias("stddev"),
        ).collect()[0]

        weight_stats = {
            "avg_t":    float(ws["avg"])    if ws["avg"]    else 0.0,
            "min_t":    float(ws["min_w"])  if ws["min_w"]  else 0.0,
            "max_t":    float(ws["max_w"])  if ws["max_w"]  else 0.0,
            "stddev_t": float(ws["stddev"]) if ws["stddev"] else 0.0,
        }

        # KPI 4 : Fenetre temporelle
        tw = df_clean.agg(
            F.min("departure_time_iso").alias("earliest"),
            F.max("departure_time_iso").alias("latest"),
        ).collect()[0]
        time_window = {
            "earliest_departure": str(tw["earliest"]) if tw["earliest"] else None,
            "latest_departure":   str(tw["latest"])   if tw["latest"]   else None,
        }

        # KPI 5 : Qualite pipeline
        pipeline_quality = {
            "total_raw_ingested": silver_report.get("total_raw", 0),
            "total_after_silver": silver_report.get("total_cleaned", 0),
            "duplicates_removed": silver_report.get("duplicates_removed", 0),
            "invalid_removed": (
                silver_report.get("invalid_nulls_removed", 0) +
                silver_report.get("invalid_domain_removed", 0)
            ),
            "quality_score_pct": silver_report.get("quality_score", 0.0),
        }

        # ── Persistance Parquet : agregation directe Spark (sans createDataFrame)
        parquet_path = self._get_parquet_path(timestamp_str)
        (
            df_clean.groupBy("type", "size")
            .agg(
                F.count("*").alias("count"),
                F.round(F.avg("weight"), 2).alias("avg_weight_t"),
                F.round(F.min("weight"), 2).alias("min_weight_t"),
                F.round(F.max("weight"), 2).alias("max_weight_t"),
            )
            .write.mode("overwrite")
            .parquet(parquet_path)
        )

        # ── JSON local (toujours — pour l'API FastAPI)
        os.makedirs(os.path.abspath(LOCAL_GOLD), exist_ok=True)
        json_path = os.path.join(os.path.abspath(LOCAL_GOLD), f"kpis_{timestamp_str}.json")
        kpis_data = {
            "computed_at":       processing_time.isoformat(),
            "total_containers":  total,
            "storage_mode":      self.storage_mode,
            "type_distribution": type_distribution,
            "size_distribution": size_distribution,
            "weight_stats":      weight_stats,
            "time_window":       time_window,
            "pipeline_quality":  pipeline_quality,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(kpis_data, f, ensure_ascii=False, indent=2)

        storage_label = f"HDFS : {parquet_path}" if self.storage_mode == "hdfs" else f"LOCAL : {parquet_path}"
        print(f"  [GOLD]   {total} conteneurs analyses -> {storage_label}")
        print(f"  [GOLD]   KPIs JSON -> {json_path}")

        return {
            "layer":  "GOLD",
            "status": "SUCCESS",
            **kpis_data,
            "parquet_path": parquet_path,
            "json_path":    json_path,
        }
