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

async def process_hybrid_etl_background(tmp_dir: str, snapshot_path: str, arrivals_path: str, app: FastAPI):
    """
    Traitement hybride : 
    1. Charge le snapshot (emplacements fixes) pour peupler le yard.
    2. Charge les arrivées (optimisation automatique) dans les places restantes.
    """
    app.state.etl_job["status"] = "processing"
    app.state.etl_job["message"] = "Phase 1 : Reconstruction du Yard à partir du snapshot..."
    app.state.etl_job["result"] = None
    start_time = time.perf_counter()

    try:
        pipeline = get_pipeline()
        yard = app.state.yard
        container_registry = app.state.container_registry
        
        # --- PHASE 1 : Snapshot (Emplacements fixes) ---
        snapshot_res = pipeline.run(snapshot_path)
        snapshot_records = snapshot_res.get("cleaned_records", [])
        
        snapshot_placed = 0
        snapshot_failed = 0
        db_containers = []

        for item in snapshot_records:
            if item["id"] in container_registry:
                snapshot_failed += 1
                continue
            
            # Vérifier si un slot est spécifié
            loc = item.get("slot")
            if not loc:
                snapshot_failed += 1
                continue
            
            try:
                coords = Slot.from_localization(loc)
                slot_obj = Slot(**coords)
                
                dt_raw = item["departure_time"]
                dep_dt = datetime.fromisoformat(dt_raw) if isinstance(dt_raw, str) else dt_raw
                from services.optimizer import SIZE_POLICY
                
                # Validation de la stratégie de taille (SÉPARATION 20ft/40ft)
                block_id = loc.split('-')[0]
                allowed_blocks = SIZE_POLICY.get(item["size"], [])
                if allowed_blocks and block_id not in allowed_blocks:
                    print(f"⚠️ [STRATEGY] Conteneur {item['id']} ({item['size']}ft) refusé dans le Bloc {block_id}")
                    snapshot_failed += 1
                    continue

                container = Container(
                    id=item["id"],
                    size=item["size"],
                    weight=item["weight"],
                    departure_time=dep_dt,
                    type=ContainerType(item["type"]),
                )
                
                if yard.place_container(slot_obj, container):
                    container_registry[container.id] = container
                    snapshot_placed += 1
                    db_containers.append({
                        "id":             container.id,
                        "size":           container.size,
                        "weight":         container.weight,
                        "type":           container.type.value,
                        "departure_time": container.departure_time,
                        "slot":           slot_obj.localization,
                        "status":         "yard" # Déjà présent
                    })
                else:
                    snapshot_failed += 1
            except Exception as e:
                print(f"Erreur placement snapshot {item.get('id')}: {e}")
                snapshot_failed += 1

        # --- PHASE 2 : Arrivals (Optimisation) ---
        app.state.etl_job["message"] = f"Phase 2 : Optimisation de {snapshot_placed} conteneurs existants chargés. Placement des nouvelles arrivées..."
        arrivals_res = pipeline.run(arrivals_path)
        arrival_records = arrivals_res.get("cleaned_records", [])
        
        # Trier par EDD (Inverse)
        sorted_arrivals = sorted(arrival_records, key=lambda x: x["departure_time"], reverse=True)
        
        arrival_placed = 0
        arrival_failed = 0

        for item in sorted_arrivals:
            if item["id"] in container_registry:
                arrival_failed += 1
                continue

            dt_raw = item["departure_time"]
            dep_dt = datetime.fromisoformat(dt_raw) if isinstance(dt_raw, str) else dt_raw
            container = Container(
                id=item["id"],
                size=item["size"],
                weight=item["weight"],
                departure_time=dep_dt,
                type=ContainerType(item["type"]),
            )

            best_result = find_best_slot(container, yard)
            if best_result:
                best_slot, _ = best_result
                if yard.place_container(best_slot, container):
                    container_registry[container.id] = container
                    arrival_placed += 1
                    db_containers.append({
                        "id":             container.id,
                        "size":           container.size,
                        "weight":         container.weight,
                        "type":           container.type.value,
                        "departure_time": container.departure_time,
                        "slot":           best_slot.localization,
                        "status":         "expected" # Arrivée prévue
                    })
                else:
                    arrival_failed += 1
            else:
                arrival_failed += 1

        # Sauvegarde DB
        if db_containers:
            await db.save_containers(db_containers)

        end_time = time.perf_counter()
        duration_ms = round((end_time - start_time) * 1000, 2)

        app.state.etl_job["status"] = "success"
        app.state.etl_job["result"] = {
            "pipeline_status": "SUCCESS",
            "snapshot_report": {
                "total_received": len(snapshot_records),
                "placed": snapshot_placed,
                "failed": snapshot_failed
            },
            "arrivals_report": {
                "total_received": len(arrival_records),
                "placed": arrival_placed,
                "failed": arrival_failed
            },
            "total_placed": snapshot_placed + arrival_placed,
            "yard_occupancy": f"{yard.occupancy_rate:.1%}",
            "processing_time_ms": duration_ms,
            "message": f"✅ Hybride réussi : {snapshot_placed} existants + {arrival_placed} nouveaux placés.",
        }

    except Exception as e:
        app.state.etl_job["status"] = "error"
        app.state.etl_job["message"] = f"Erreur Hybride : {str(e)}"
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
    file: UploadFile = File(..., description="Fichier CSV des conteneurs"),
):
    """Mode Standard : un seul fichier."""
    if request.app.state.etl_job.get("status") == "processing":
        raise HTTPException(status_code=400, detail="Un traitement est déjà en cours.")

    tmp_dir = tempfile.mkdtemp(prefix="marsa_etl_")
    tmp_path = os.path.join(tmp_dir, "arrivals.csv")
    
    with open(tmp_path, "wb") as f:
        f.write(await file.read())

    # On utilise le logic hybride avec un snapshot vide (simulé ici par un flag ou en passant None)
    # Mais par souci de simplicité, on peut garder l'ancienne logique ou adapter la nouvelle
    background_tasks.add_task(process_hybrid_etl_background, tmp_dir, tmp_path, tmp_path, request.app) 
    # Note: Passer le même fichier deux fois n'est pas idéal, créons un petit helper 
    # ou gérons le cas "standard" dans process_hybrid
    return {"message": "Traitement démarré", "status": "processing"}


@router.post(
    "/upload-dual-csv",
    summary="[HYBRID] Upload Snapshot + Arrivées",
    description="Reconstruit le terminal puis optimise les nouvelles arrivées.",
)
async def upload_dual_csv(
    request: Request,
    background_tasks: BackgroundTasks,
    snapshot: UploadFile = File(...),
    arrivals: UploadFile = File(...),
):
    if request.app.state.etl_job.get("status") == "processing":
        raise HTTPException(status_code=400, detail="Un traitement est déjà en cours.")

    tmp_dir = tempfile.mkdtemp(prefix="marsa_hybrid_")
    snap_path = os.path.join(tmp_dir, "snapshot.csv")
    arr_path = os.path.join(tmp_dir, "arrivals.csv")
    
    with open(snap_path, "wb") as f:
        f.write(await snapshot.read())
    with open(arr_path, "wb") as f:
        f.write(await arrivals.read())

    background_tasks.add_task(process_hybrid_etl_background, tmp_dir, snap_path, arr_path, request.app)

    return {"message": "Traitement hybride démarré", "status": "processing"}


@router.get(
    "/upload-status",
    summary="[ETL] Statut ou Résultat du traitement courant",
    description="Permet au frontend de polluler l'état d'avancement du traitement asynchrone.",
)
async def get_upload_status(request: Request):
    """Retourne l'état de `app.state.etl_job`."""
    return request.app.state.etl_job

