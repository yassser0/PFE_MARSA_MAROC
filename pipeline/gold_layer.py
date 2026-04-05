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

    def _get_output_path(self, timestamp_str: str) -> str:
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
            F.min("departure_time").alias("earliest"),
            F.max("departure_time").alias("latest"),
        ).collect()[0]
        time_window = {
            "earliest_departure": str(tw["earliest"].isoformat()) if tw["earliest"] else None,
            "latest_departure":   str(tw["latest"].isoformat())   if tw["latest"]   else None,
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

        # ── KPI 6 : Analyse du Dwell Time (Temps de séjour) ─────────────────────
        # Dwell Time = departure_time - _ingestion_time (exprimé en jours)
        df_dwell = df_clean.withColumn(
            "dwell_bits", 
            F.unix_timestamp(F.col("departure_time")) - F.unix_timestamp(F.col("_ingestion_time").cast("timestamp"))
        ).withColumn(
            "dwell_days", 
            F.round(F.greatest(F.lit(0.0), F.col("dwell_bits") / 86400).cast("double"), 1)
        )

        dwell_stats_rows = (
            df_dwell.groupBy("type")
            .agg(F.round(F.avg("dwell_days"), 1).alias("avg_dwell"))
            .collect()
        )
        dwell_analytics = {
            row["type"]: float(row["avg_dwell"]) if row["avg_dwell"] else 0.0
            for row in dwell_stats_rows
        }

        # ── KPI 7 : Efficacité de Gerbage (Stacking Efficiency) ────────────────
        # Nécessite l'analyse des colonnes 'slot' (ex: A-001-A-01)
        advanced_analytics = {"rehandle_risk_count": 0, "efficiency_score": 100.0}
        
        if "slot" in df_clean.columns:
            from pyspark.sql.window import Window
            
            # Parse du slot : Bloc-Travée-Rangée-Niveau (ex: A-001-A-01)
            # On simplifie pour l'analyse Big Data : (Bloc, Bay, Row) = Pile
            df_stack = df_clean.withColumn("slot_parts", F.split(F.col("slot"), "-"))
            if df_stack.filter(F.size(F.col("slot_parts")) >= 4).count() > 0:
                df_stack = df_stack.withColumn("b_id", F.col("slot_parts").getItem(0)) \
                                   .withColumn("bay",  F.col("slot_parts").getItem(1)) \
                                   .withColumn("row",  F.col("slot_parts").getItem(2)) \
                                   .withColumn("tier", F.col("slot_parts").getItem(3).cast("int"))
                
                # Fenêtre par pile, triée par niveau (sol vers haut)
                win_stack = Window.partitionBy("b_id", "bay", "row").orderBy("tier")
                
                # Un risque de rehandle existe si le conteneur du dessous part APRÈS celui du dessus
                # rehandle if departure_time(tier N) < departure_time(tier N+1)
                df_risk = df_stack.withColumn(
                    "next_departure", 
                    F.lead("departure_time").over(win_stack)
                ).withColumn(
                    "is_rehandle_risk",
                    F.when(
                        (F.col("next_departure").isNotNull()) & 
                        (F.col("departure_time") > F.col("next_departure")), # Celui du dessous part après (OK)
                        0
                    ).when(
                        (F.col("next_departure").isNotNull()) & 
                        (F.col("departure_time") < F.col("next_departure")), # Celui du dessous part avant (BLOQUÉ)
                        1
                    ).otherwise(0)
                )
                
                rehandle_count = df_risk.filter(F.col("is_rehandle_risk") == 1).count()
                efficiency = round(max(0, 100 - (rehandle_count / total * 100)), 1)
                
                advanced_analytics = {
                    "rehandle_risk_count": rehandle_count,
                    "efficiency_score":    efficiency,
                    "details_per_block":   {
                        row["b_id"]: row["count"] 
                        for row in df_risk.filter(F.col("is_rehandle_risk") == 1).groupBy("b_id").count().collect()
                    }
                }

        # ── Persistance Delta Lake (Data Lakehouse)
        try:
            parquet_path = self._get_output_path(timestamp_str)
            (
                df_clean.groupBy("type", "size")
                .agg(
                    F.count("*").alias("count"),
                    F.round(F.avg("weight"), 2).alias("avg_weight_t"),
                    F.round(F.min("weight"), 2).alias("min_weight_t"),
                    F.round(F.max("weight"), 2).alias("max_weight_t"),
                )
                .write.format("delta")
                .mode("overwrite")
                .save(parquet_path)
            )
            storage_label = f"HDFS : {parquet_path}" if self.storage_mode == "hdfs" else f"LOCAL : {parquet_path}"
        except Exception as e:
            # Sur Windows sans winutils, Delta/Parquet peut crasher. 
            # On ignore pour sauver l'essentiel : le JSON des KPIs.
            print(f"  [GOLD]   ⚠️ Échec écriture Delta/Parquet (Normal sur Windows dégradé) : {e}")
            parquet_path = "N/A (Spark/Filesystem Issue)"
            storage_label = "FAILED (Delta/Parquet)"

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
            "dwell_analytics":   dwell_analytics,
            "advanced_analytics": advanced_analytics,
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
