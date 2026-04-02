"""
api/routes/containers.py
=========================
Route FastAPI pour le placement des conteneurs.

Endpoints :
- POST /containers/place_batch  : Placement direct via JSON (Pydantic)
- POST /containers/upload-csv   : Upload CSV → Pipeline ETL Bronze/Silver/Gold → Placement

Auteur  : PFE Marsa Maroc
Version : 2.0 (PySpark ETL)
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Request, FastAPI
from pydantic import BaseModel, Field, field_validator

from models.container import Container, ContainerType
from models.yard import Slot
from services.optimizer import find_best_slot
from api.database import db
from pipeline.etl_pipeline import get_pipeline

router = APIRouter(prefix="/containers", tags=["Conteneurs"])


# ---------------------------------------------------------------------------
# Schémas Pydantic (Request / Response)
# ---------------------------------------------------------------------------

class ETLUploadResponse(BaseModel):
    """Réponse pour l'upload CSV avec pipeline ETL Bronze/Silver/Gold."""
    pipeline_status: str
    # Rapports par couche
    bronze_report: Optional[dict] = None
    silver_report: Optional[dict] = None
    gold_kpis: Optional[dict] = None
    # Placement final
    total_received: int = 0
    containers_placed: int = 0
    failed_placements: int = 0
    yard_occupancy: str = "0.0%"
    processing_time_ms: float = 0.0
    message: str = ""

ETLUploadResponse.model_rebuild()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------





# Endpoint 2 : Upload CSV → Pipeline ETL Bronze / Silver / Gold → Placement
# ---------------------------------------------------------------------------

async def process_etl_background(tmp_dir: str, tmp_csv_path: str, app: FastAPI):
    """Logique principale exécutée en tâche de fond pour ne pas bloquer l'API."""
    app.state.etl_job["status"] = "processing"
    app.state.etl_job["message"] = "Analyse PySpark et optimisation automatique en cours..."
    app.state.etl_job["result"] = None
    start_time = time.perf_counter()

    try:
        pipeline = get_pipeline()
        etl_result = pipeline.run(tmp_csv_path)

        if etl_result["pipeline_status"] == "ERROR":
            app.state.etl_job["status"] = "error"
            app.state.etl_job["message"] = f"Erreur ETL : {etl_result.get('error', 'Erreur inconnue')}"
            return

        if etl_result["pipeline_status"] == "EMPTY":
            app.state.etl_job["status"] = "error"
            app.state.etl_job["message"] = "Aucun conteneur valide trouvé dans le CSV."
            return

        yard = app.state.yard
        container_registry = app.state.container_registry
        cleaned_records = etl_result["cleaned_records"]

        # Trier par Date de Départ Inverse (EDD — optimisation anti-rehandle)
        sorted_items = sorted(cleaned_records, key=lambda x: x["departure_time"], reverse=True)

        placed_count = 0
        failed_count = 0
        db_containers = []

        for item in sorted_items:
            cntr_id = item["id"]

            if cntr_id in container_registry:
                failed_count += 1
                continue

            dt_raw = item["departure_time"]
            dep_dt = datetime.fromisoformat(dt_raw) if isinstance(dt_raw, str) else dt_raw

            container = Container(
                id=cntr_id,
                size=item["size"],
                weight=item["weight"],
                departure_time=dep_dt,
                type=ContainerType(item["type"]),
            )

            best_result = find_best_slot(container, yard)
            if best_result is None:
                failed_count += 1
                continue

            best_slot, _ = best_result
            success = yard.place_container(best_slot, container)

            if success:
                container_registry[container.id] = container
                placed_count += 1
                db_containers.append({
                    "id":             container.id,
                    "size":           container.size,
                    "weight":         container.weight,
                    "type":           container.type.value,
                    "departure_time": container.departure_time,
                    "slot":           best_slot.localization,
                })
            else:
                failed_count += 1

        if db_containers:
            import asyncio
            # L'appel à run_coroutine_threadsafe n'est pas nécessaire si process run dans Asyncio event loop
            await db.save_containers(db_containers)

        end_time = time.perf_counter()
        duration_ms = round((end_time - start_time) * 1000, 2)

        app.state.etl_job["status"] = "success"
        app.state.etl_job["result"] = {
            "pipeline_status": "SUCCESS",
            "bronze_report": etl_result.get("bronze_report"),
            "silver_report": etl_result.get("silver_report"),
            "gold_kpis": etl_result.get("gold_kpis"),
            "total_received": etl_result.get("bronze_report", {}).get("total_rows_ingested", 0),
            "containers_placed": placed_count,
            "failed_placements": failed_count,
            "yard_occupancy": f"{yard.occupancy_rate:.1%}",
            "processing_time_ms": duration_ms,
            "message": f"✅ Pipeline ETL réussie — {placed_count}/{len(cleaned_records)} conteneurs placés en {duration_ms:.0f}ms.",
        }

    except Exception as e:
        app.state.etl_job["status"] = "error"
        app.state.etl_job["message"] = str(e)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post(
    "/upload-csv",
    summary="[ETL] Upload CSV manuel Asynchrone (Pipeline)",
    description="Accepte un fichier CSV et le traite via la pipeline ETL en arrière-plan.",
)
async def upload_csv_etl(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Fichier CSV des conteneurs (colonnes: id,size,weight,departure_time,type)"),
):
    """Reçoit le fichier CSV, l'enregistre temporairement, et lance le job ETL en arrière-plan."""
    if request.app.state.etl_job.get("status") == "processing":
        raise HTTPException(status_code=400, detail="Un traitement est déjà en cours. Veuillez patienter.")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .csv sont acceptés.")

    tmp_dir = tempfile.mkdtemp(prefix="marsa_etl_")
    tmp_csv_path = os.path.join(tmp_dir, file.filename)
    
    with open(tmp_csv_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Lancement de PySpark en tâche de fond pour ne pas bloquer l'upload
    background_tasks.add_task(process_etl_background, tmp_dir, tmp_csv_path, request.app)

    return {"message": "Traitement démarré", "status": "processing"}


@router.get(
    "/upload-status",
    summary="[ETL] Statut ou Résultat du traitement courant",
    description="Permet au frontend de polluler l'état d'avancement du traitement asynchrone.",
)
async def get_upload_status(request: Request):
    """Retourne l'état de `app.state.etl_job`."""
    return request.app.state.etl_job

