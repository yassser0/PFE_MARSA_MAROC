"""
pipeline/bronze_layer.py
========================
Couche Bronze — Ingestion brute des donnees.

Stockage : HDFS reel (hdfs://namenode:9000/marsa_maroc/bronze/) ou local.
Le mode est selectionne automatiquement par l'orchestrateur ETL.

Auteur  : PFE Marsa Maroc
Version : 3.0 (PySpark + HDFS Docker)
"""

import os
from datetime import datetime
from typing import Tuple, Dict, Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType


# Chemins de stockage
HDFS_NAMENODE  = os.getenv("HDFS_NAMENODE", "hdfs://localhost:9000")
HDFS_BRONZE    = f"{HDFS_NAMENODE}/marsa_maroc/bronze"
LOCAL_BRONZE   = os.path.join(os.path.dirname(__file__), "..", "data", "bronze")
HDFS_ARCHIVE   = f"{HDFS_NAMENODE}/marsa_maroc/archive"
LOCAL_ARCHIVE  = os.path.join(os.path.dirname(__file__), "..", "data", "archive")

# Schema brut (tout en string — couche Bronze ne transforme pas)
RAW_SCHEMA = StructType([
    StructField("id",             StringType(), nullable=True),
    StructField("size",           StringType(), nullable=True),
    StructField("weight",         StringType(), nullable=True),
    StructField("departure_time", StringType(), nullable=True),
    StructField("type",           StringType(), nullable=True),
    StructField("slot",           StringType(), nullable=True),
])


class BronzeLayer:
    """
    Ingere un fichier CSV brut et le stocke en Parquet.
    Le stockage cible est HDFS (si disponible) ou le disque local.
    """

    def __init__(self, spark: SparkSession, storage_mode: str = "local"):
        self.spark = spark
        self.storage_mode = storage_mode

    def _get_output_path(self, timestamp_str: str) -> str:
        """Retourne le chemin de sortie selon le mode de stockage."""
        if self.storage_mode == "hdfs":
            return f"{HDFS_BRONZE}/batch_{timestamp_str}"
        base = os.path.abspath(LOCAL_BRONZE)
        os.makedirs(base, exist_ok=True)
        return f"file:///{base.replace(os.sep, '/')}/batch_{timestamp_str}"

    def _get_archive_path(self) -> str:
        """Retourne le chemin de la table d'archives globale."""
        if self.storage_mode == "hdfs":
            return HDFS_ARCHIVE
        base = os.path.abspath(LOCAL_ARCHIVE)
        os.makedirs(base, exist_ok=True)
        return f"file:///{base.replace(os.sep, '/')}"

    def ingest(self, csv_path: str) -> Tuple[DataFrame, Dict[str, Any]]:
        """
        Lit un fichier CSV et le persiste en Parquet (Bronze).

        Args:
            csv_path: Chemin absolu vers le fichier CSV source.

        Returns:
            Tuple (DataFrame Spark brut, rapport d'ingestion)
        """
        ingestion_time = datetime.now()
        timestamp_str  = ingestion_time.strftime("%Y%m%d_%H%M%S")

        # Conversion du chemin en URI local si necessaire
        local_csv_uri = csv_path
        if not csv_path.startswith("file://") and not csv_path.startswith("hdfs://"):
            local_csv_uri = f"file:///{csv_path.replace(os.sep, '/')}"

        # 1. Lecture CSV (sans transformation — tout en string)
        df_raw = (
            self.spark.read
            .option("header", "true")
            .option("inferSchema", "false")
            .option("nullValue", "")
            .option("mode", "PERMISSIVE")
            .schema(RAW_SCHEMA)
            .csv(local_csv_uri)
        )

        total_rows = df_raw.count()

        # 2. Ajout metadonnees de traçabilite
        df_with_meta = (
            df_raw
            .withColumn("_ingestion_time", F.lit(ingestion_time.isoformat()))
            .withColumn("_source_file",    F.lit(os.path.basename(csv_path)))
            .withColumn("_storage_mode",   F.lit(self.storage_mode))
        )

        # 3. Persistance Parquet (Batch Bronze Actuel)
        output_path = self._get_output_path(timestamp_str)
        df_with_meta.write.mode("overwrite").parquet(output_path)

        storage_label = f"HDFS : {output_path}" if self.storage_mode == "hdfs" else f"LOCAL : {output_path}"
        print(f"  [BRONZE] {total_rows} lignes ingérees -> {storage_label}")

        # 4. Archivage Historique Immuable (Delta, Append)
        archive_path = self._get_archive_path()
        try:
            (
                df_with_meta.withColumn("ingestion_date", F.to_date(F.col("_ingestion_time")))
                .write.format("delta")
                .mode("append")
                .partitionBy("ingestion_date")
                .save(archive_path)
            )
            print(f"  [ARCHIVES] {total_rows} lignes sauvegardées historiquement -> {archive_path}")
        except Exception as e:
            print(f"  [ARCHIVES] Erreur d'archivage : {e}")

        return df_with_meta, {
            "layer":               "BRONZE",
            "status":              "SUCCESS",
            "storage_mode":        self.storage_mode,
            "source_file":         os.path.basename(csv_path),
            "total_rows_ingested": total_rows,
            "output_path":         output_path,
            "archive_path":        archive_path,
            "ingestion_time":      ingestion_time.isoformat(),
            "columns_detected":    df_raw.columns,
        }
