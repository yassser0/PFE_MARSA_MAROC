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

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field, field_validator

from models.container import Container, ContainerType
from models.yard import Slot
from services.optimizer import find_best_slot
from services.silver_layer import SilverLayer
from api.database import db
from pipeline.etl_pipeline import get_pipeline

router = APIRouter(prefix="/containers", tags=["Conteneurs"])


# ---------------------------------------------------------------------------
# Schémas Pydantic (Request / Response)
# ---------------------------------------------------------------------------

class ContainerRequest(BaseModel):

    size: int = Field(
        ...,
        description="Taille du conteneur en pieds (20 ou 40 EVP)",
        examples=[20, 40],
    )
    weight: float = Field(
        ...,
        description="Poids du conteneur en tonnes (5.0 à 30.0)",
        ge=1.0,
        le=50.0,
        examples=[12.5],
    )
    type: ContainerType = Field(
        ...,
        description="Type opérationnel du conteneur",
        examples=["import"],
    )
    departure_time: datetime = Field(
        ...,
        description="Date et heure prévues de départ (ISO 8601)",
        examples=["2026-03-20T10:00:00"],
    )

    id: Optional[str] = Field(
        None,
        description="Identifiant unique du conteneur (ex: HLX-4458). Si omis, un ID sera généré.",
        examples=["CNTR-001"],
    )
    zones_20ft: Optional[list[str]] = Field(
        None,
        description="Liste des blocs dédiés aux conteneurs 20ft (ex: ['A', 'B'])",
    )
    zones_40ft: Optional[list[str]] = Field(
        None,
        description="Liste des blocs dédiés aux conteneurs 40ft (ex: ['C', 'D'])",
    )

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        if v not in (20, 40):
            raise ValueError("La taille doit être 20 ou 40 EVP.")
        return v

class PlacementBatchResponse(BaseModel):
    """Réponse pour l'insertion en masse de données (Pipeline)."""
    total_received: int
    containers_placed: int
    failed_placements: int
    yard_occupancy: str
    processing_time_ms: float
    silver_report: Optional[dict] = None
    message: str

PlacementBatchResponse.model_rebuild()


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




@router.post(
    "/place_batch",
    response_model=PlacementBatchResponse,
    summary="Pipeline Data : Placer un lot de conteneurs (Batch)",
    description="""
Accepte une liste entière de conteneurs entrants (ex: fichier portuaire Excel).
**Optimisation magique** : La route trie d'abord les conteneurs par `departure_time` décroissant (EDD inverse).
Les conteneurs partant le plus tard sont donc empilés au fond en premier, garantissant mathématiquement **zéro rehandle**.
    """
)
async def place_containers_batch(
    requests: List[ContainerRequest],
):
    import time
    import uuid
    from api.main import app as _app

    yard = _app.state.yard
    container_registry = _app.state.container_registry

    start_time = time.perf_counter()

    # 1. Pipeline Silver Layer : Nettoyage et Validation Haute Performance
    # On transforme les requêtes (Pydantic) en liste de dicts pour le Silver Layer
    raw_data = [req.model_dump() for req in requests]
    cleaned_data, silver_report = SilverLayer.process(raw_data)

    if not cleaned_data and silver_report.get("error"):
        raise HTTPException(status_code=400, detail=silver_report["error"])

    # 2. Trier la pipeline par Date de Départ Inverse (EDD)
    # Les conteneurs partant le plus tard (departure_time le plus grand) sont placés en premier.
    # Note: On utilise cleaned_data (liste de dicts)
    sorted_items = sorted(cleaned_data, key=lambda x: x['departure_time'], reverse=True)

    placed_count = 0
    failed_count = 0
    db_containers = []

    for item in sorted_items:
        # Utiliser l'id fourni
        cntr_id = item['id']

        # Vérification des doublons : Ne pas placer si l'ID existe déjà dans le yard
        if cntr_id in container_registry:
            failed_count += 1
            continue
        
        dt_raw = item['departure_time']
        dep_dt = datetime.fromisoformat(dt_raw) if isinstance(dt_raw, str) else dt_raw

        container = Container(
            id=cntr_id,
            size=item['size'],
            weight=item['weight'],
            departure_time=dep_dt,
            type=ContainerType(item['type']),
        )

        allowed_blocks = None
        if container.size == 20 and item.get('zones_20ft'):
            allowed_blocks = [z.upper() for z in item['zones_20ft']]
        elif container.size == 40 and item.get('zones_40ft'):
            allowed_blocks = [z.upper() for z in item['zones_40ft']]

        best_result = find_best_slot(container, yard, allowed_blocks=allowed_blocks)
        
        if best_result is None:
            failed_count += 1
            continue

        best_slot, _ = best_result
        success = yard.place_container(best_slot, container)
        
        if success:
            container_registry[container.id] = container
            placed_count += 1
            # Préparation pour la sauvegarde MongoDB
            db_containers.append({
                "id": container.id,
                "size": container.size,
                "weight": container.weight,
                "type": container.type.value,
                "departure_time": container.departure_time,
                "slot": best_slot.localization
            })
        else:
            failed_count += 1

    # 3. Sauvegarde asynchrone dans MongoDB
    if db_containers:
        await db.save_containers(db_containers)

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000

    return PlacementBatchResponse(
        total_received=len(requests),
        containers_placed=placed_count,
        failed_placements=failed_count,
        yard_occupancy=f"{yard.occupancy_rate:.1%}",
        processing_time_ms=round(duration_ms, 2),
        silver_report=silver_report,
        message=f"{placed_count}/{len(requests)} placés avec succès."
    )


# ---------------------------------------------------------------------------
# Endpoint 2 : Upload CSV → Pipeline ETL Bronze / Silver / Gold → Placement
# ---------------------------------------------------------------------------

@router.post(
    "/upload-csv",
    response_model=ETLUploadResponse,
    summary="🏭 Pipeline ETL : Upload CSV → Bronze → Silver → Gold → Placement",
    description="""
Accepte un fichier CSV (multipart/form-data) et le traite via la pipeline ETL complète :

1. **Bronze** : Ingestion brute du CSV, stockage Parquet dans `data/bronze/`
2. **Silver** : Nettoyage, déduplication, validation via **PySpark** (mode Hadoop local),
   stockage Parquet dans `data/silver/`
3. **Gold** : Calcul des KPIs analytiques (distribution type/taille, poids moyen...),
   stockage Parquet dans `data/gold/`
4. **Placement** : Les données nettoyées sont injectées dans le moteur d'optimisation
   du yard et sauvegardées dans MongoDB.
    """,
)
async def upload_csv_etl(
    file: UploadFile = File(..., description="Fichier CSV des conteneurs (colonnes: id,size,weight,departure_time,type)"),
):
    """Pipeline ETL complète déclenchée par upload de fichier CSV."""
    from api.main import app as _app

    # Validation du type de fichier
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .csv sont acceptés.")

    start_time = time.perf_counter()

    # ── 1. Sauvegarder le fichier uploadé dans un répertoire temporaire
    tmp_dir = tempfile.mkdtemp(prefix="marsa_etl_")
    tmp_csv_path = os.path.join(tmp_dir, file.filename)
    try:
        with open(tmp_csv_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # ── 2. Lancer la pipeline ETL (Bronze → Silver → Gold)
        pipeline = get_pipeline()
        etl_result = pipeline.run(tmp_csv_path)

    finally:
        # Nettoyage du fichier temporaire
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Gestion des erreurs pipeline
    if etl_result["pipeline_status"] == "ERROR":
        raise HTTPException(
            status_code=500,
            detail=f"Erreur pipeline ETL : {etl_result.get('error', 'Erreur inconnue')}"
        )

    if etl_result["pipeline_status"] == "EMPTY":
        return ETLUploadResponse(
            pipeline_status="EMPTY",
            bronze_report=etl_result.get("bronze_report"),
            silver_report=etl_result.get("silver_report"),
            gold_kpis={},
            message="Aucun conteneur valide trouvé dans le fichier CSV.",
        )

    # ── 3. Placement des conteneurs nettoyés dans le Yard
    yard = _app.state.yard
    container_registry = _app.state.container_registry
    cleaned_records = etl_result["cleaned_records"]

    # Trier par Date de Départ Inverse (EDD — optimisation anti-rehandle)
    sorted_items = sorted(cleaned_records, key=lambda x: x["departure_time"], reverse=True)

    placed_count = 0
    failed_count = 0
    db_containers = []

    for item in sorted_items:
        cntr_id = item["id"]

        # Éviter les doublons dans le yard
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

    # ── 4. Sauvegarde asynchrone dans MongoDB
    if db_containers:
        await db.save_containers(db_containers)

    end_time = time.perf_counter()
    duration_ms = round((end_time - start_time) * 1000, 2)

    return ETLUploadResponse(
        pipeline_status="SUCCESS",
        bronze_report=etl_result["bronze_report"],
        silver_report=etl_result["silver_report"],
        gold_kpis=etl_result["gold_kpis"],
        total_received=etl_result["bronze_report"].get("total_rows_ingested", 0),
        containers_placed=placed_count,
        failed_placements=failed_count,
        yard_occupancy=f"{yard.occupancy_rate:.1%}",
        processing_time_ms=duration_ms,
        message=f"✅ Pipeline ETL réussie — {placed_count}/{len(cleaned_records)} conteneurs placés en {duration_ms:.0f}ms.",
    )

