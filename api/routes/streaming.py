"""
api/routes/streaming.py
========================
Routes pour l'accès aux données de flux en temps réel (Pillar 1).
"""

import os
import json
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/streaming", tags=["Streaming"])

# Chemin vers le fichier JSON généré par Spark Streamer
LIVE_GOLD_PATH = "data/gold/live_kpis.json"

@router.get("/kpis")
async def get_streaming_kpis():
    """
    Récupère les derniers KPIs calculés par le moteur de streaming Spark.
    """
    if not os.path.exists(LIVE_GOLD_PATH):
        return {
            "status": "waiting",
            "message": "Le moteur de streaming est en cours d'initialisation ou aucune donnée n'a été reçue.",
            "data": None
        }
    
    try:
        with open(LIVE_GOLD_PATH, "r") as f:
            data = json.load(f)
            return {
                "status": "active",
                "data": data
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la lecture des KPIs : {str(e)}")

@router.get("/status")
async def get_streaming_status():
    """
    Vérifie si les services de streaming sont actifs.
    """
    # On pourrait vérifier si les processus existent, mais ici on vérifie 
    # simplement la fraîcheur du fichier Gold.
    if not os.path.exists(LIVE_GOLD_PATH):
        return {"status": "inactive"}
    
    import time
    mtime = os.path.getmtime(LIVE_GOLD_PATH)
    if time.time() - mtime < 60: # Fréquence de 60s max
        return {"status": "running", "last_update_seconds_ago": int(time.time() - mtime)}
    else:
        return {"status": "stale", "last_update_seconds_ago": int(time.time() - mtime)}
