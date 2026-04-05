"""
pipeline/etl_pipeline.py
========================
Orchestrateur principal de la Pipeline ETL Medaillon (Bronze -> Silver -> Gold).

Mode HDFS : PySpark se connecte au cluster Hadoop HDFS Docker
  - NameNode : hdfs://namenode:9000
  - Bronze   : hdfs://namenode:9000/marsa_maroc/bronze/
  - Silver   : hdfs://namenode:9000/marsa_maroc/silver/
  - Gold     : hdfs://namenode:9000/marsa_maroc/gold/

Le moteur tourne en mode local[*] (tous les CPU) mais persiste dans HDFS reel.

Auteur  : PFE Marsa Maroc
Version : 3.0 (PySpark + HDFS Docker)
"""

import os
import logging
from typing import Dict, Any

# ── Variables d'environnement Hadoop ─────────────────────────────────────────
# RÉPARATION SPARK : On force l'usage de Python 3.11 (stable) au lieu de 3.13 (flaky)
# car PySpark 3.5 a des bugs de socket connus avec Python 3.13 sur Windows.
PYTHON_311_PATH = r"C:\Users\yassi\AppData\Local\Programs\Python\Python311\python.exe"
if os.path.exists(PYTHON_311_PATH):
    os.environ["PYSPARK_PYTHON"] = PYTHON_311_PATH
    os.environ["PYSPARK_DRIVER_PYTHON"] = PYTHON_311_PATH
else:
    os.environ.setdefault("PYSPARK_PYTHON", "python")

os.environ.setdefault("HADOOP_USER_NAME", "root")  # Acces HDFS en tant que root
logging.getLogger("py4j").setLevel(logging.ERROR)

from pyspark.sql import SparkSession

from pipeline.bronze_layer import BronzeLayer
from pipeline.silver_layer_spark import SilverLayerSpark
from pipeline.gold_layer import GoldLayer

# ── Configuration HDFS ────────────────────────────────────────────────────────
HDFS_NAMENODE   = os.getenv("HDFS_NAMENODE", "hdfs://localhost:9000")
HDFS_BASE_PATH  = f"{HDFS_NAMENODE}/marsa_maroc"
USE_HDFS        = os.getenv("USE_HDFS", "true").lower() == "true"


class ETLPipeline:
    """
    Pipeline ETL complete : Bronze -> Silver -> Gold avec stockage HDFS.

    Usage :
        pipeline = ETLPipeline()
        result = pipeline.run("/path/to/file.csv")
        pipeline.stop()
    """

    def __init__(self):
        self._spark: SparkSession | None = None

    @property
    def spark(self) -> SparkSession:
        """Cree ou recupere la SparkSession avec configuration HDFS."""
        if self._spark is None or self._spark._jvm is None:
            mode = "HDFS" if USE_HDFS else "LOCAL"
            print(f"  [ETL] Demarrage SparkSession (mode local[*] + stockage {mode})...")

            builder = (
                SparkSession.builder
                .master("local[*]")
                .appName("MarsaMaroc_ETL_Pipeline_HDFS")
                # --- Stabilité Windows & Python 3.13 ---
                .config("spark.driver.memory", "4g")
                .config("spark.python.worker.reuse", "false")  # RÉPARE WinError 10038
                .config("spark.driver.extraJavaOptions", "-Djava.net.preferIPv4Stack=true -Dfile.encoding=UTF-8")
                .config("spark.executor.extraJavaOptions", "-Djava.net.preferIPv4Stack=true -Dfile.encoding=UTF-8")
                # --- Optimisations SQL ---
                .config("spark.sql.shuffle.partitions", "4")
                .config("spark.sql.adaptive.enabled", "true")
                .config("spark.ui.showConsoleProgress", "false")
                .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
                # --- Delta Lake Configuration ---
                .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
                .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
                .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.0.0")
            )

            if USE_HDFS:
                builder = (
                    builder
                    # Point d'entree HDFS
                    .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE)
                    # Le client HDFS utilise le hostname annonce par le DataNode (127.0.0.1)
                    .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
                    # Desactiver la verification Kerberos (mode dev)
                    .config("spark.hadoop.fs.hdfs.impl.disable.cache", "false")
                    # Timeout de connexion HDFS
                    .config("spark.hadoop.ipc.client.connect.timeout", "10000")
                )

            self._spark = builder.getOrCreate()
            self._spark.sparkContext.setLogLevel("ERROR")
            print(f"  [ETL] SparkSession prete (Delta Lake Active). HDFS: {HDFS_BASE_PATH if USE_HDFS else 'desactive'}")
        return self._spark

    def _check_hdfs_available(self) -> bool:
        """Verifie que HDFS est accessible avant de lancer la pipeline."""
        try:
            import socket
            import urllib.parse
            parsed = urllib.parse.urlparse(HDFS_NAMENODE)
            host = parsed.hostname or "localhost"
            port = parsed.port or 9000
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            return True
        except Exception:
            return False

    def run(self, csv_path: str) -> Dict[str, Any]:
        """
        Execute la pipeline ETL complete.

        Args:
            csv_path: Chemin absolu vers le fichier CSV uploade.

        Returns:
            Dict avec : pipeline_status, bronze_report, silver_report,
                        gold_kpis, cleaned_records, storage_mode
        """
        print("\n" + "=" * 60)
        print("  PIPELINE ETL MARSA MAROC — DEMARRAGE")
        print("=" * 60)

        # Verification HDFS si active
        storage_mode = "local"
        if USE_HDFS:
            if self._check_hdfs_available():
                storage_mode = "hdfs"
                print(f"  HDFS detecte : {HDFS_BASE_PATH}")
            else:
                print("  AVERTISSEMENT : HDFS non disponible, bascule vers stockage local.")
                os.environ["USE_HDFS"] = "false"
                storage_mode = "local"

        try:
            spark = self.spark

            # ── BRONZE
            print("\n  [1/3] COUCHE BRONZE — Ingestion CSV...")
            bronze = BronzeLayer(spark, storage_mode=storage_mode)
            df_raw, bronze_report = bronze.ingest(csv_path)

            # ── SILVER
            print("\n  [2/3] COUCHE SILVER — Nettoyage PySpark...")
            silver = SilverLayerSpark(spark, storage_mode=storage_mode)
            df_clean, silver_report = silver.process(df_raw)

            if silver_report.get("total_cleaned", 0) == 0:
                print("  [SILVER] Aucune donnee valide apres nettoyage.")
                return {
                    "pipeline_status": "EMPTY",
                    "storage_mode": storage_mode,
                    "bronze_report": bronze_report,
                    "silver_report": silver_report,
                    "gold_kpis": {},
                    "cleaned_records": [],
                }

            # ── GOLD
            print("\n  [3/3] COUCHE GOLD — Calcul des KPIs...")
            gold = GoldLayer(spark, storage_mode=storage_mode)
            gold_kpis = gold.compute(df_clean, silver_report)

            # Conversion en records pour le moteur de placement
            cleaned_records = silver.to_records(df_clean)

            print("\n" + "=" * 60)
            print(f"  PIPELINE COMPLETE — {len(cleaned_records)} conteneurs prets.")
            print(f"  Stockage : {storage_mode.upper()}")
            print("=" * 60 + "\n")

            return {
                "pipeline_status": "SUCCESS",
                "storage_mode": storage_mode,
                "bronze_report": bronze_report,
                "silver_report": silver_report,
                "gold_kpis": gold_kpis,
                "cleaned_records": cleaned_records,
                "df_clean": df_clean,
            }

        except Exception as e:
            print(f"\n  [ETL] ERREUR PIPELINE : {e}")
            import traceback
            traceback.print_exc()
            return {
                "pipeline_status": "ERROR",
                "error": str(e),
                "storage_mode": storage_mode,
                "bronze_report": {},
                "silver_report": {},
                "gold_kpis": {},
                "cleaned_records": [],
            }

    def stop(self):
        """Arrete la SparkSession proprement."""
        if self._spark:
            self._spark.stop()
            self._spark = None
            print("  [ETL] SparkSession arretee.")


# ── Singleton global ──────────────────────────────────────────────────────────
_pipeline_instance: ETLPipeline | None = None


def get_pipeline() -> ETLPipeline:
    """Retourne l'instance singleton de la pipeline ETL."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = ETLPipeline()
    return _pipeline_instance
