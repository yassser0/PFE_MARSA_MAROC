"""
pipeline/silver_layer_spark.py
================================
Couche Silver — Nettoyage et validation des donnees via PySpark.

Stockage : HDFS reel (hdfs://namenode:9000/marsa_maroc/silver/) ou local.

Transformations :
1. Cast des types (string -> int, float, timestamp)
2. Suppression des valeurs nulles obligatoires
3. Deduplication par ID (window function)
4. Validation des domaines metier (poids 1-50, taille 20/40, type valide)
5. Normalisation du champ type (minuscule)
6. Persistance Parquet

Auteur  : PFE Marsa Maroc
Version : 3.0 (PySpark + HDFS Docker)
"""

import os
from datetime import datetime
from typing import Tuple, Dict, Any, List

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, DoubleType, IntegerType
from pyspark.sql.window import Window


# Chemins de stockage
HDFS_NAMENODE = os.getenv("HDFS_NAMENODE", "hdfs://localhost:9000")
HDFS_SILVER   = f"{HDFS_NAMENODE}/marsa_maroc/silver"
LOCAL_SILVER  = os.path.join(os.path.dirname(__file__), "..", "data", "silver")
HDFS_ANOMALIES = f"{HDFS_NAMENODE}/marsa_maroc/anomalies"
LOCAL_ANOMALIES = os.path.join(os.path.dirname(__file__), "..", "data", "anomalies")

ALLOWED_TYPES = ["import", "export", "transshipment"]


class SilverLayerSpark:
    """
    Couche Silver PySpark : nettoyage, validation et normalisation.
    Stockage Parquet dans HDFS ou local selon storage_mode.
    """

    def __init__(self, spark: SparkSession, storage_mode: str = "local"):
        self.spark = spark
        self.storage_mode = storage_mode

    def _get_output_path(self, timestamp_str: str) -> str:
        if self.storage_mode == "hdfs":
            return f"{HDFS_SILVER}/batch_{timestamp_str}"
        base = os.path.abspath(LOCAL_SILVER)
        os.makedirs(base, exist_ok=True)
        return f"file:///{base.replace(os.sep, '/')}/batch_{timestamp_str}"

    def _get_anomalies_path(self) -> str:
        if self.storage_mode == "hdfs":
            return HDFS_ANOMALIES
        base = os.path.abspath(LOCAL_ANOMALIES)
        os.makedirs(base, exist_ok=True)
        return f"file:///{base.replace(os.sep, '/')}"

    def process(self, df_raw: DataFrame) -> Tuple[DataFrame, Dict[str, Any]]:
        """
        Nettoie et valide le DataFrame brut (issu de Bronze).

        Returns:
            Tuple (DataFrame nettoye, rapport de qualite)
        """
        processing_time = datetime.now()
        timestamp_str   = processing_time.strftime("%Y%m%d_%H%M%S")
        total_raw = df_raw.count()

        # Etape 1 : Cast des types
        df = df_raw.select(
            F.col("id").cast(StringType()),
            F.col("weight").cast(DoubleType()).alias("weight"),
            F.col("size").cast(IntegerType()).alias("size"),
            F.col("departure_time"),
            F.lower(F.trim(F.col("type"))).alias("type"),
            F.col("_ingestion_time"),
            F.col("slot"),
        )

        # Etape 2 : Parse departure_time (multi-format)
        df = df.withColumn(
            "departure_time",
            F.coalesce(
                F.to_timestamp(F.col("departure_time")),  # Auto ISO-8601 (handles microseconds)
                F.to_timestamp(F.col("departure_time"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"),
                F.to_timestamp(F.col("departure_time"), "yyyy-MM-dd'T'HH:mm:ss"),
                F.to_timestamp(F.col("departure_time"), "M/d/yyyy H:mm"),
                F.to_timestamp(F.col("departure_time"), "yyyy-MM-dd HH:mm:ss"),
                F.to_timestamp(F.col("departure_time"), "yyyy-MM-dd"),
            )
        )

        # Etape 3 : Suppression des nulles critiques et capture des anomalies
        df_not_null = df.dropna(subset=["id", "weight", "size", "departure_time"])
        after_null_drop  = df_not_null.count()
        invalid_nulls    = total_raw - after_null_drop

        c_nulls = F.col("id").isNull() | F.col("weight").isNull() | F.col("size").isNull() | F.col("departure_time").isNull()
        df_anomalies_nulls = df.filter(c_nulls).withColumn("anomaly_reason", F.lit("NULL_CRITICAL_COLUMNS"))

        # Etape 4 : Deduplication par ID et capture des anomalies
        window_spec = Window.partitionBy("id").orderBy(F.monotonically_increasing_id())
        df_with_rank = df_not_null.withColumn("_row_num", F.row_number().over(window_spec))

        df_deduped = df_with_rank.filter(F.col("_row_num") == 1).drop("_row_num")
        duplicates_removed = after_null_drop - df_deduped.count()

        df_anomalies_dupes = (
            df_with_rank
            .filter(F.col("_row_num") > 1)
            .drop("_row_num")
            .withColumn("anomaly_reason", F.lit("DUPLICATE_ID"))
        )

        # Etape 5 : Validation domaines metier et capture des anomalies
        valid_cond = (
            (F.col("weight") >= 1.0) & (F.col("weight") <= 50.0) &
            F.col("size").isin(20, 40) &
            F.col("type").isin(ALLOWED_TYPES)
        )
        df_valid = df_deduped.filter(valid_cond)
        
        df_anomalies_domain = df_deduped.filter(~valid_cond).withColumn("anomaly_reason", F.lit("DOMAIN_VIOLATION"))

        # Normalisation type (valeur par defaut = 'import')
        df_clean = df_valid.withColumn(
            "type",
            F.when(F.col("type").isin(ALLOWED_TYPES), F.col("type")).otherwise("import")
        )

        # Colonne ISO string pour compatibilite JSON/FastAPI
        df_clean = df_clean.withColumn(
            "departure_time_iso",
            F.date_format(F.col("departure_time"), "yyyy-MM-dd'T'HH:mm:ss")
        )

        # Etape 6 : Partitionnement technique (Date extraction)
        df_clean = df_clean.withColumn(
            "departure_date", 
            F.to_date(F.col("departure_time"))
        )

        total_clean    = df_clean.count()
        invalid_domain = df_deduped.count() - total_clean

        # Etape 7 : Persistance Delta Lake (HDFS ou local) avec partitionnement
        # Partitionnement par type (faible cardinalite) et date (utile pour filtres temporels)
        output_path = self._get_output_path(timestamp_str)
        (
            df_clean.write.format("delta")
            .mode("overwrite")
            .partitionBy("type", "departure_date")
            .save(output_path)
        )

        quality_score = round((total_clean / total_raw) * 100, 1) if total_raw > 0 else 0.0

        storage_label = f"HDFS Delta : {output_path}" if self.storage_mode == "hdfs" else f"LOCAL Delta : {output_path}"
        print(f"  [SILVER] {total_clean}/{total_raw} lignes valides (Data Lakehouse Delta) -> {storage_label}")

        # Etape 8 : Sauvegarde Historique des Anomalies (Data Governance)
        df_all_anomalies = df_anomalies_nulls.unionByName(df_anomalies_dupes).unionByName(df_anomalies_domain)
        total_anomalies  = invalid_nulls + duplicates_removed + invalid_domain
        anomalies_path   = self._get_anomalies_path()

        if total_anomalies > 0:
            try:
                (
                    df_all_anomalies
                    .withColumn("ingestion_date", F.to_date(F.col("_ingestion_time")))
                    .write.format("delta")
                    .mode("append")
                    .partitionBy("ingestion_date", "anomaly_reason")
                    .save(anomalies_path)
                )
                print(f"  [QUALITY] Rapport : {total_anomalies} anomalies sauvegardées -> {anomalies_path}")
            except Exception as e:
                print(f"  [QUALITY] Erreur sauvegarde anomalies : {e}")
        else:
            print(f"  [QUALITY] Rapport : Aucune anomalie détectée (Score {quality_score}%) !")

        return df_clean, {
            "layer":                   "SILVER",
            "status":                  "SUCCESS",
            "storage_mode":            self.storage_mode,
            "format":                  "delta",
            "total_raw":               total_raw,
            "invalid_nulls_removed":   invalid_nulls,
            "duplicates_removed":      duplicates_removed,
            "invalid_domain_removed":  invalid_domain,
            "total_anomalies_saved":   total_anomalies,
            "total_cleaned":           total_clean,
            "quality_score":           quality_score,
            "output_path":             output_path,
            "anomalies_path":          anomalies_path if total_anomalies > 0 else None,
            "processing_time":         processing_time.isoformat(),
        }

    def to_records(self, df_clean: DataFrame) -> List[Dict[str, Any]]:
        """Convertit le DataFrame Silver en liste de dicts pour le moteur de placement."""
        records = []
        for row in df_clean.collect():
            records.append({
                "id":             row["id"],
                "size":           int(row["size"]),
                "weight":         float(row["weight"]),
                "departure_time": row["departure_time_iso"],
                "type":           row["type"],
                "slot":           row["slot"] if "slot" in row and row["slot"] else None,
            })
        return records
