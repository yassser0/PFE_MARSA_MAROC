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
        
        # --- OPTIMISATION : Si c'est le même fichier, on ne lance Spark qu'une seule fois ---
        is_standard_mode = (snapshot_path == arrivals_path)
        
        if is_standard_mode:
            app.state.etl_job["message"] = "Phase unique : Traitement Spark de l'ensemble du fichier..."
            full_res = pipeline.run(snapshot_path)
            snapshot_records = full_res.get("cleaned_records", [])
            arrival_records = snapshot_records # C'est le même set de données
            arrivals_res = full_res # Pour récupérer les KPIs Gold à la fin
        else:
            # --- PHASE 1 : Snapshot (Emplacements fixes) ---
            snapshot_res = pipeline.run(snapshot_path)
            snapshot_records = snapshot_res.get("cleaned_records", [])
        
        snapshot_placed = 0
        snapshot_rescued = 0
        snapshot_failed = 0
        db_containers = []
        rescued_items = []

        # --- NOUVEAUTÉ : TRI PAR NIVEAU (TIER) ---
        # On doit traiter les conteneurs du bas vers le haut pour que l'audit 
        # puisse voir correctement ce qu'il y a en dessous.
        def get_tier_safe(item):
            # Tente d'extraire le tier du slot "A-001-A-01" -> 1
            loc = item.get("slot", "")
            if not loc: return 0
            try:
                return int(loc.split('-')[-1])
            except:
                return 0

        snapshot_records_sorted = sorted(snapshot_records, key=get_tier_safe)

        for item in snapshot_records_sorted:
            if item["id"] in container_registry:
                # Déjà présent (doublon dans le CSV ou rechargement)
                snapshot_failed += 1
                continue
            
            # Récupération et nettoyage de la taille (Robuste)
            try:
                size_int = int(float(item.get("size", 20)))
                item["size"] = size_int # Mise à jour pour le sauvetage (Phase 2)
            except (ValueError, TypeError):
                size_int = 20
                item["size"] = 20
            
            # Vérifier si un slot est spécifié
            loc = item.get("slot")
            if not loc:
                # Pas de slot -> On le sauve via l'optimiseur
                rescued_items.append(item)
                snapshot_rescued += 1
                continue
            
            try:
                coords = Slot.from_localization(loc)
                slot_obj = Slot(**coords)
                
                dt_raw = item["departure_time"]
                dep_dt = datetime.fromisoformat(dt_raw) if isinstance(dt_raw, str) else dt_raw
                from services.optimizer import SIZE_POLICY
                
                # Validation de la stratégie de taille (SÉPARATION 20ft/40ft)
                block_id = loc.split('-')[0]
                policy = SIZE_POLICY.get(size_int, {})
                allowed_blocks = policy.get('primary', []) + policy.get('backup', [])
                
                # RÈGLE DE SAUVETAGE : Si violation de zone, on sauve !
                if allowed_blocks and block_id not in allowed_blocks:
                    print(f"🔄 [RESCUE] {item['id']} ({size_int}ft) -> Mauvaise zone {block_id}. Redirection Optimiseur.")
                    rescued_items.append(item)
                    snapshot_rescued += 1
                    continue

                # --- AUDIT DE QUALITÉ SNAPSHOT (ANTI-REHANDLE) ---
                if slot_obj.tier > 1:
                    # On regarde la pile en dessous
                    stack = yard.get_stack(slot_obj.block_id, slot_obj.bay, slot_obj.row)
                    if stack:
                        below_slot = stack.slots[slot_obj.tier - 2]
                        if not below_slot.is_free:
                            below_cntr = container_registry.get(below_slot.container_id)
                            # Si le conteneur du dessus (snapshot) part APRÈS celui d'en dessous -> REHANDLE
                            if below_cntr and dep_dt > below_cntr.departure_time:
                                print(f"🛡️ [SNAPSHOT AUDIT] {item['id']} à {loc} créerait un rehandle (partant après {below_cntr.id}). Sauvetage...")
                                rescued_items.append(item)
                                snapshot_rescued += 1
                                continue

                container = Container(
                    id=item["id"],
                    size=size_int,
                    weight=item["weight"],
                    departure_time=dep_dt,
                    type=ContainerType(item["type"]),
                )
                
                # Tentative de placement fixe
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
                        "status":         "yard"
                    })
                else:
                    # Slot occupé ou invalide -> On sauve !
                    print(f"🔄 [RESCUE] {item['id']} -> Slot {loc} occupé ou invalide. Redirection Optimiseur.")
                    rescued_items.append(item)
                    snapshot_rescued += 1
            except Exception as e:
                print(f"Erreur placement snapshot {item.get('id')}, redirection: {e}")
                rescued_items.append(item)
                snapshot_rescued += 1

        # --- PHASE 2 : Arrivals (Optimisation) ---
        if is_standard_mode:
            app.state.etl_job["message"] = f"Phase 2 : Placement de {snapshot_placed} fixes + Sauvetage/Optimisation..."
            arrivals_res = full_res
            arrival_records = snapshot_records
            df_global = full_res.get("df_clean")
            final_silver_report = full_res.get("silver_report")
        else:
            app.state.etl_job["message"] = f"Phase 2 : Optimisation de {snapshot_placed} fixes. Sauvetage de {snapshot_rescued} conteneurs..."
            arrivals_res = pipeline.run(arrivals_path)
            arrival_records = arrivals_res.get("cleaned_records", [])
            
            # --- FUSION ANALYTIQUE GLOBALE ---
            df_snap = snapshot_res.get("df_clean")
            df_arr = arrivals_res.get("df_clean")
            
            if df_snap and df_arr:
                df_global = df_snap.union(df_arr)
                from pipeline.gold_layer import GoldLayer
                gold_layer = GoldLayer(pipeline.spark, storage_mode=arrivals_res.get("storage_mode", "local"))
                
                # Fusion des rapports Silver pour la qualité globale
                s1 = snapshot_res.get("silver_report", {})
                s2 = arrivals_res.get("silver_report", {})
                final_silver_report = {
                    "total_raw": s1.get("total_raw", 0) + s2.get("total_raw", 0),
                    "total_cleaned": s1.get("total_cleaned", 0) + s2.get("total_cleaned", 0),
                    "duplicates_removed": s1.get("duplicates_removed", 0) + s2.get("duplicates_removed", 0),
                    "invalid_nulls_removed": s1.get("invalid_nulls_removed", 0) + s2.get("invalid_nulls_removed", 0),
                    "quality_score": round((s1.get("quality_score", 0) + s2.get("quality_score", 0)) / 2, 2)
                }
                
                app.state.etl_job["message"] = "Phase 3 : Calcul des KPIs Globaux du Terminal..."
                global_gold = gold_layer.compute(df_global, final_silver_report)
                global_gold["is_global"] = True # Metadata pour le frontend
                arrivals_res["gold_kpis"] = global_gold
                arrivals_res["silver_report"] = final_silver_report
            else:
                final_silver_report = arrivals_res.get("silver_report")

        # Combine Arrivals + Rescued items from Snapshot
        all_to_optimize = arrival_records + rescued_items
        
        # Trier par EDD (Inverse pour LIFO optimizer)
        sorted_arrivals = sorted(all_to_optimize, key=lambda x: x["departure_time"], reverse=True)
        
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
                "placed_fixed": snapshot_placed,
                "rescued": snapshot_rescued,
                "failed": snapshot_failed
            },
            "arrivals_report": {
                "total_received": len(arrival_records),
                "placed": arrival_placed,
                "failed": arrival_failed
            },
            "gold_kpis": arrivals_res.get("gold_kpis"),
            "silver_report": arrivals_res.get("silver_report"),
            "total_placed": snapshot_placed + arrival_placed,
            "yard_occupancy": f"{yard.occupancy_rate:.1%}",
            "processing_time_ms": duration_ms,
            "message": f"✅ Hybride réussi : {snapshot_placed} fixes + {arrival_placed} optimisés (incluant {snapshot_rescued} sauvés).",
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
    "/latest-kpis",
    summary="[GOLD] Récupérer les derniers KPIs calculés",
    description="Lit le dernier fichier JSON généré dans data/gold pour afficher les statistiques.",
)
async def get_latest_kpis():
    """Charge le JSON le plus récent de la couche Gold."""
    gold_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "gold")
    if not os.path.exists(gold_dir):
        return {"message": "Dossier Gold inexistant"}
    
    files = [f for f in os.listdir(gold_dir) if f.startswith("kpis_") and f.endswith(".json")]
    if not files:
        return {"message": "Aucun KPI Gold trouvé"}
    
    # Trier par date (format kpis_YYYYMMDD_HHMMSS.json)
    latest_file = sorted(files, reverse=True)[0]
    path = os.path.join(gold_dir, latest_file)
    
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Erreur de lecture : {str(e)}"}


@router.get(
    "/upload-status",
    summary="[ETL] Statut ou Résultat du traitement courant",
    description="Permet au frontend de polluler l'état d'avancement du traitement asynchrone.",
)
async def get_upload_status(request: Request):
    """Retourne l'état de `app.state.etl_job`."""
    return request.app.state.etl_job

