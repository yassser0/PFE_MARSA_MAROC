"""
api/routes/containers.py
=========================
Route FastAPI pour le placement des conteneurs.

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from models.container import Container, ContainerType
from models.yard import Slot
from services.optimizer import find_best_slot
from api.database import db

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
    message: str


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

    # 1. Trier la pipeline par Date de Départ Inverse (EDD)
    # Les conteneurs partant le plus tard (departure_time le plus grand) sont placés en premier.
    sorted_requests = sorted(requests, key=lambda r: r.departure_time, reverse=True)

    placed_count = 0
    failed_count = 0
    db_containers = []

    for req in sorted_requests:
        # Utiliser l'id fourni ou générer un nouveau
        cntr_id = req.id if req.id else f"B-{uuid.uuid4().hex[:8].upper()}"
        
        container = Container(
            id=cntr_id,
            size=req.size,
            weight=req.weight,
            departure_time=req.departure_time,
            type=req.type,
        )

        allowed_blocks = None
        if container.size == 20 and req.zones_20ft:
            allowed_blocks = [z.upper() for z in req.zones_20ft]
        elif container.size == 40 and req.zones_40ft:
            allowed_blocks = [z.upper() for z in req.zones_40ft]

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
        message=f"{placed_count}/{len(requests)} placés avec succès en {duration_ms:.0f}ms."
    )

