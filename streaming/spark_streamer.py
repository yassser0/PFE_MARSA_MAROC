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
from pymongo import MongoClient

# Configuration Hadoop / HDFS
os.environ.setdefault("PYSPARK_PYTHON", "python")
os.environ.setdefault("HADOOP_USER_NAME", "root")

# Configuration des chemins
HDFS_NAMENODE = os.getenv("HDFS_NAMENODE", "hdfs://localhost:9000")
INPUT_PATH    = f"{HDFS_NAMENODE}/marsa_maroc/bronze/streaming"
CHECKPOINT_DIR = f"{HDFS_NAMENODE}/marsa_maroc/checkpoints/streaming"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
OUTPUT_JSON    = os.path.join(BASE_DIR, "data", "gold", "live_kpis.json")

# Connection MongoDB (Sync for Spark Driver)
mongo_client = MongoClient("mongodb://localhost:27017")
db = mongo_client.marsa_maroc

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
        .appName("MarsaMaroc_Streaming_Placement_Engine")
        .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE)
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )

def process_stream():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("ERROR")
    
    from models.yard import Yard
    from models.container import Container, ContainerType
    from services.optimizer import find_best_slot

    print(f"🌊 Démarrage du moteur de placement OPTIMAL Spark...")
    print(f"👀 Surveillance de : {INPUT_PATH}")
    
    df_raw = (
        spark.readStream
        .schema(schema)
        .json(INPUT_PATH)
    )
    
    df_silver = (
        df_raw
        .withColumn("arrival_timestamp", F.to_timestamp("arrival_time"))
        .filter(F.col("weight") > 0)
    )
    
    def place_containers_in_yard(batch_df, batch_id):
        records = batch_df.collect()
        if not records:
            return

        print(f"📦 Batch {batch_id} : Traitement de {len(records)} nouveaux conteneurs...")

        # 1. Charger l'état actuel du Yard (Baseline généreuse pour couvrir les données existantes)
        yard = Yard(n_blocks=4, n_bays=24, n_rows=12, max_height=5)
        
        # Charger les conteneurs déjà présents en base pour éviter les collisions
        existing_docs = list(db.containers.find({"slot": {"$exists": True}}))
        for doc in existing_docs:
            try:
                # On recrée l'objet container pour le registre du yard
                cntr = Container(
                    id=doc["id"],
                    size=doc["size"],
                    weight=doc["weight"],
                    departure_time=doc["departure_time"],
                    type=ContainerType(doc["type"])
                )
                from models.yard import Slot
                slot_info = Slot.from_localization(doc["slot"])
                target_slot = Slot(**slot_info)
                yard.place_container(target_slot, cntr)
            except Exception as e:
                print(f"⚠️ Erreur lors du rechargement du conteneur {doc.get('id')}: {e}")

        # 2. TRIER PAR EDD (Earliest Due Date) - Optimisation Anti-rehandle
        # On trie le batch actuel par date de départ décroissante 
        # (ceux qui partent le plus tard sont placés en bas en premier)
        sorted_records = sorted(records, key=lambda x: x.departure_time, reverse=True)

        new_placements = []
        placed_count = 0

        for row in sorted_records:
            # Vérifier si cet ID est déjà dans le yard (doublon HDFS)
            if row.id in yard.containers_registry:
                continue

            # Créer l'objet Container
            dep_time = datetime.fromisoformat(row.departure_time) if isinstance(row.departure_time, str) else row.departure_time
            container = Container(
                id=row.id,
                size=row.size,
                weight=row.weight,
                departure_time=dep_time,
                type=ContainerType(row.type)
            )

            # 3. TROUVER LE MEILLEUR SLOT (OPTIMISATION)
            best_result = find_best_slot(container, yard)
            
            if best_result:
                best_slot, score = best_result
                success = yard.place_container(best_slot, container)
                if success:
                    placed_count += 1
                    # Préparer le document pour MongoDB
                    new_placements.append({
                        "id": container.id,
                        "size": container.size,
                        "weight": container.weight,
                        "type": container.type.value,
                        "departure_time": container.departure_time,
                        "slot": best_slot.localization,
                        "found_by": "SparkStreaming",
                        "placement_score": score,
                        "imported_at": datetime.now()
                    })
                    print(f"  ✅ {container.id} placé en {best_slot.localization}")
            else:
                print(f"  ❌ Pas de place trouvée pour {container.id}")

        # 4. SAUVEGARDE EN BASE
        if new_placements:
            db.containers.insert_many(new_placements)
            print(f"💾 {len(new_placements)} placements enregistrés dans MongoDB.")

        # 5. Mise à jour du JSON de monitoring pour le frontend
        kpis = {
            "last_update": datetime.now().isoformat(),
            "batch_id": batch_id,
            "total_placed_in_stream": placed_count,
            "yard_occupancy": f"{yard.occupancy_rate:.1%}",
            "last_container": new_placements[-1]["id"] if new_placements else "N/A"
        }
        os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
        with open(OUTPUT_JSON, "w") as f:
            json.dump(kpis, f, indent=2)

    # Lancement du flux
    query = (
        df_silver.writeStream
        .foreachBatch(place_containers_in_yard)
        .option("checkpointLocation", CHECKPOINT_DIR)
        .start()
    )
    
    query.awaitTermination()
    
if __name__ == "__main__":
    process_stream()

