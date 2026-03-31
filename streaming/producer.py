"""
streaming/producer.py
======================
Producteur de données en temps réel pour la simulation de flux.

Ce script :
1. Génère un conteneur aléatoire toutes les N secondes.
2. Sauvegarde le conteneur en JSON localement.
3. Téléverse le fichier vers HDFS (/marsa_maroc/bronze/streaming/).

Usage :
    python streaming/producer.py --interval 5
"""

import os
import json
import time
import uuid
import argparse
import subprocess
from datetime import datetime

# Importer le générateur existant
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_generator.generator import generate_containers

# Configuration
BASE_DIR       = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_TEMP_DIR = os.path.join(BASE_DIR, "streaming", "temp_land")
HDFS_DEST_DIR  = "/marsa_maroc/bronze/streaming"

def upload_to_hdfs(local_path, hdfs_path):
    """Utilise la commande hdfs dfs -put pour envoyer le fichier via Docker."""
    try:
        filename = os.path.basename(local_path)
        # 1. On s'assure que /tmp existe dans le container (normalement oui)
        container_temp = f"/tmp/{filename}"
        
        # 2. Copier du Windows vers le Container Docker
        cp_res = subprocess.run(["docker", "cp", local_path, f"marsa_hdfs_namenode:{container_temp}"], capture_output=True, text=True)
        if cp_res.returncode != 0:
            print(f"  [ERREUR CP] {cp_res.stderr}")
            return False
            
        # 3. Déplacer du Container vers HDFS
        # On utilise le chemin complet /marsa_maroc/bronze/streaming/
        put_res = subprocess.run(["docker", "exec", "marsa_hdfs_namenode", "hdfs", "dfs", "-put", "-f", container_temp, f"{hdfs_path}/{filename}"], capture_output=True, text=True)
        if put_res.returncode != 0:
            print(f"  [ERREUR PUT] {put_res.stderr}")
            # On vérifie si c'est un problème de dossier absent
            return False
            
        # 4. Nettoyage dans le container
        subprocess.run(["docker", "exec", "marsa_hdfs_namenode", "rm", container_temp], capture_output=True)
        
        return True
    except Exception as e:
        print(f"  [ERREUR HDFS] {e}")
        return False

def run_producer(interval=5):
    print(f"🚀 Démarrage du producteur de flux (Intervalle: {interval}s)")
    print(f"📂 Zone d'atterrissage HDFS : {HDFS_DEST_DIR}")
    
    if not os.path.exists(LOCAL_TEMP_DIR):
        os.makedirs(LOCAL_TEMP_DIR)

    try:
        count = 0
        while True:
            count += 1
            # 1. Générer 1 conteneur
            container = generate_containers(1)[0]
            
            # Préparer les données pour JSON
            data = {
                "id": container.id,
                "size": container.size,
                "weight": container.weight,
                "type": container.type.value,
                "departure_time": container.departure_time.isoformat(),
                "arrival_time": datetime.now().isoformat(),
                "event_id": str(uuid.uuid4())
            }
            
            # 2. Sauvegarder localement
            filename = f"event_{int(time.time())}_{container.id}.json"
            local_path = os.path.join(LOCAL_TEMP_DIR, filename)
            
            with open(local_path, "w") as f:
                json.dump(data, f)
            
            # 3. Envoyer vers HDFS
            success = upload_to_hdfs(local_path, HDFS_DEST_DIR)
            
            if success:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] #{count} Envoyé : {container.id} ({container.type.value})")
            else:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] #{count} ÉCHEC HDFS pour {container.id}")
            
            # 4. Nettoyage local (optionnel)
            # os.remove(local_path)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nStopping producer...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=5, help="Secondes entre chaque conteneur")
    args = parser.parse_args()
    
    run_producer(args.interval)
