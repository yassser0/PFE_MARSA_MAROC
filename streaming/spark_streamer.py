"""
streaming/spark_streamer.py
============================
Moteur de traitement de flux Spark Structured Streaming.

Ce script :
1. Surveille /marsa_maroc/bronze/streaming/ pour l'arrivée de nouveaux JSON.
2. Nettoie les données (Couche Silver).
3. Calcule des KPIs glissants (Couche Gold).
4. Exporte les résultats vers un JSON local pour l'API.

Usage :
    python streaming/spark_streamer.py
"""

import os
import json
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, TimestampType

# Configuration Hadoop / HDFS
os.environ.setdefault("PYSPARK_PYTHON", "python")
os.environ.setdefault("HADOOP_USER_NAME", "root")

# Configuration des chemins
HDFS_NAMENODE = os.getenv("HDFS_NAMENODE", "hdfs://localhost:9000")
INPUT_PATH    = f"{HDFS_NAMENODE}/marsa_maroc/bronze/streaming"
CHECKPOINT_DIR = f"{HDFS_NAMENODE}/marsa_maroc/checkpoints/streaming"  # Sur HDFS pour éviter les pb de drive Windows (C:)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_JSON    = os.path.join(BASE_DIR, "data", "gold", "live_kpis.json")

# Schema des données entrantes
schema = StructType([
    StructField("id",             StringType(),  True),
    StructField("size",           IntegerType(), True),
    StructField("weight",         DoubleType(),  True),
    StructField("type",           StringType(),  True),
    StructField("departure_time", StringType(),  True),
    StructField("arrival_time",   StringType(),  True),
    StructField("event_id",       StringType(),  True),
])

def create_spark_session():
    return (
        SparkSession.builder
        .master("local[*]")
        .appName("MarsaMaroc_Streaming_Engine")
        .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE)
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        .config("spark.sql.shuffle.partitions", "2") # Petit pour le streaming local
        .getOrCreate()
    )

def process_stream():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("ERROR")
    
    print(f"🌊 Démarrage du moteur de streaming Spark...")
    print(f"👀 Surveillance de : {INPUT_PATH}")
    
    # ── 1. LECTURE (BRONZE)
    df_raw = (
        spark.readStream
        .schema(schema)
        .json(INPUT_PATH)
    )
    
    # ── 2. NETTOYAGE & TYPAGE (SILVER)
    df_silver = (
        df_raw
        .withColumn("arrival_timestamp", F.to_timestamp("arrival_time"))
        .filter(F.col("weight") > 0) # Règle de nettoyage simple
    )
    
    # ── 3. AGGREGATIONS GLISSANTES (GOLD)
    # On calcule les stats sur les 10 dernières minutes, rafraîchies toutes les 30 secondes
    df_gold = (
        df_silver
        .withWatermark("arrival_timestamp", "1 minute")
        .groupBy(
            F.window("arrival_timestamp", "10 minutes", "30 seconds"),
            "type"
        )
        .agg(
            F.count("*").alias("count"),
            F.round(F.avg("weight"), 2).alias("avg_weight")
        )
    )
    
    # ── 4. ECRITURE (SINK)
    # Pour la démo, on utilise une fonction "foreachBatch" pour écrire un JSON global 
    # que l'API peut lire facilement.
    
    def update_live_kpis(batch_df, batch_id):
        # On récupère les résultats les plus récents (dernière fenêtre de temps)
        results = batch_df.orderBy(F.desc("window.end")).collect()
        
        if not results:
            return
            
        # Formatter les données pour le dashboard
        latest_window = results[0]["window"]
        kpis = {
            "last_update": datetime.now().isoformat(),
            "window_start": latest_window["start"].isoformat(),
            "window_end": latest_window["end"].isoformat(),
            "total_arrivals": sum(row["count"] for row in results if row["window"] == latest_window),
            "by_type": {
                row["type"]: {
                    "count": row["count"],
                    "avg_weight": row["avg_weight"]
                }
                for row in results if row["window"] == latest_window
            }
        }
        
        # Sauvegarder dans le fichier JSON local
        os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
        with open(OUTPUT_JSON, "w") as f:
            json.dump(kpis, f, indent=2)
            
        print(f"  [STREAM] KPIs mis à jour à {datetime.now().strftime('%H:%M:%S')} "
              f"({kpis['total_arrivals']} arrivées dans la fenêtre)")

    query = (
        df_gold.writeStream
        .foreachBatch(update_live_kpis)
        .option("checkpointLocation", CHECKPOINT_DIR)
        .start()
    )
    
    query.awaitTermination()

if __name__ == "__main__":
    process_stream()
